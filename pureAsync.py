import argparse
import socket
import json
import struct
import hashlib
import os
import time
import sys
import asyncio
import aiofiles
from typing import Optional, Tuple, Dict, Any
import threading
from concurrent.futures import ThreadPoolExecutor

# 协议常量定义（与服务器保持一致）
OP_SAVE, OP_DELETE, OP_GET, OP_UPLOAD, OP_DOWNLOAD, OP_BYE, OP_LOGIN, OP_ERROR = (
    'SAVE', 'DELETE', 'GET', 'UPLOAD', 'DOWNLOAD', 'BYE', 'LOGIN', "ERROR"
)
TYPE_FILE, TYPE_DATA, TYPE_AUTH, DIR_EARTH = 'FILE', 'DATA', 'AUTH', 'EARTH'
FIELD_OPERATION, FIELD_DIRECTION, FIELD_TYPE, FIELD_USERNAME, FIELD_PASSWORD, FIELD_TOKEN = (
    'operation', 'direction', 'type', 'username', 'password', 'token'
)
FIELD_KEY, FIELD_SIZE, FIELD_TOTAL_BLOCK, FIELD_MD5, FIELD_BLOCK_SIZE = (
    'key', 'size', 'total_block', 'md5', 'block_size'
)
FIELD_STATUS, FIELD_STATUS_MSG, FIELD_BLOCK_INDEX = 'status', 'status_msg', 'block_index'
DIR_REQUEST, DIR_RESPONSE = 'REQUEST', 'RESPONSE'
SERVER_PORT = 1379
RE_TRANSMISSION_TIME = 20
PROGRESS_BAR_LENGTH = 50  # 进度条长度


def _argparse():
    """
    Parse command line arguments for server configuration
    :return: Parsed arguments containing ip and port
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default='127.0.0.1', action='store', required=False, dest="ip",
                        help="The IP address of the server. Default is 127.0.0.1.")
    parser.add_argument("--port", default=SERVER_PORT, action='store', required=False, dest="port", type=int,
                        help=f"The port of the server. Default is {SERVER_PORT}.")
    return parser.parse_args()


# 异步网络通信管理模块
class AsyncNetworkManager:
    """Handles asynchronous network communication"""

    @staticmethod
    def pack_message(json_data, bin_data=None):
        """
        Pack JSON data and binary data into a network packet
        """
        json_str = json.dumps(json_data, ensure_ascii=False)
        json_bytes = json_str.encode()
        json_len = len(json_bytes)
        bin_len = len(bin_data) if bin_data else 0
        header = struct.pack('!II', json_len, bin_len)
        return header + json_bytes + (bin_data or b'')

    @staticmethod
    async def async_send_message(writer, operation, data_type, payload, bin_data=None, token=None):
        """
        Asynchronously send a message through the socket
        """
        message = {
            FIELD_OPERATION: operation,
            FIELD_TYPE: data_type,
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_TOKEN: token
        }
        message.update(payload)

        packet = AsyncNetworkManager.pack_message(message, bin_data)
        writer.write(packet)
        await writer.drain()

    @staticmethod
    async def async_unpack_message(reader):
        """
        Asynchronously unpack network packet into JSON data and binary data
        """
        try:
            # Read 8-byte header
            header = await reader.readexactly(8)
            json_len, bin_len = struct.unpack('!II', header)

            # Read JSON data
            json_data = await reader.readexactly(json_len)

            # Read binary data if present
            bin_data = await reader.readexactly(bin_len) if bin_len > 0 else b''

            return json.loads(json_data.decode()), bin_data
        except Exception as e:
            print(f"Message parsing error: {str(e)}")
            return None, None


# 错误处理模块
class ErrorHandler:
    """Handles error checking and processing for server responses"""

    @staticmethod
    def check_error(json_data, status_code):
        """
        Check for error status codes and handle accordingly
        """
        if 400 <= status_code < 500:
            print(f'\nServer response: {json_data.get(FIELD_STATUS_MSG, "Unknown error")}')
            print(f'Status code: {status_code}')
            print('Client exit.')
            return True
        return False


# 认证服务模块
class AsyncAuthenticationService:
    """Manages user authentication and token management with async operations"""

    def __init__(self, reader, writer):
        """
        Initialize AsyncAuthenticationService
        """
        self.reader = reader
        self.writer = writer
        self.token = None

    async def login(self, student_id):
        """
        Perform user login and retrieve authentication token asynchronously
        """
        if student_id == "YeWenjie":
            await self.SendingToThreeBody()
            return False

        password = hashlib.md5(student_id.encode()).hexdigest().lower()
        payload = {
            FIELD_USERNAME: student_id,
            FIELD_PASSWORD: password
        }

        try:
            await AsyncNetworkManager.async_send_message(
                self.writer, OP_LOGIN, TYPE_AUTH, payload
            )

            response, _ = await AsyncNetworkManager.async_unpack_message(self.reader)
            if not response:
                print("No login response received")
                return False

            status_code = response.get(FIELD_STATUS)
            if ErrorHandler.check_error(response, status_code):
                return False

            print(f'Server response: {response[FIELD_STATUS_MSG]}')
            print(f'Status code: {status_code}')

            self.token = response.get(FIELD_TOKEN)
            print(f'This is your token: {self.token}')
            return True
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    async def SendingToThreeBody(self):
        """A rudimentary server-side Easter egg collection mechanism """
        three_body_json = {FIELD_DIRECTION: DIR_EARTH}
        packet = AsyncNetworkManager.pack_message(three_body_json)
        self.writer.write(packet)
        await self.writer.drain()

        response, _ = await AsyncNetworkManager.async_unpack_message(self.reader)
        if response:
            print(f"receive from ThreeBody: {response.get(FIELD_STATUS_MSG)}")

    def get_token(self):
        """Get current authentication token"""
        return self.token


# 异步文件块处理模块
class AsyncFileBlockProcessor:
    """Handles asynchronous file block processing"""

    @staticmethod
    async def async_read_blocks(file_path, block_size, total_blocks, file_size):
        """
        Asynchronously read file blocks and yield them asynchronously
        """
        async with aiofiles.open(file_path, 'rb') as f:
            for block_idx in range(total_blocks):
                # 定位到块起始位置
                await f.seek(block_idx * block_size)

                # 计算实际读取大小
                remaining = file_size - block_idx * block_size
                chunk_size = min(block_size, remaining)

                # 读取数据
                data = await f.read(chunk_size)
                yield (block_idx, data)


# 进度条工具类
class ProgressBar:
    """Single-line dynamic progress bar for file upload"""

    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.start_time = time.time()
        self.lock = threading.Lock()

    def update(self, increment=1):
        """Update progress bar atomically"""
        with self.lock:
            self.completed += increment
            progress = (self.completed / self.total) * 100
            elapsed_time = time.time() - self.start_time
            speed = (self.completed * 1024 * 1024) / elapsed_time if elapsed_time > 0 else 0

            filled_length = int(PROGRESS_BAR_LENGTH * self.completed // self.total)
            bar = '█' * filled_length + '-' * (PROGRESS_BAR_LENGTH - filled_length)

            sys.stdout.write(
                f'\rUpload Progress: |{bar}| {progress:.2f}% '
                f'[{self.completed}/{self.total} blocks] '
                f'Speed: {speed:.2f} MB/s '
                f'Elapsed: {elapsed_time:.1f}s'
            )
            sys.stdout.flush()

            if self.completed == self.total:
                sys.stdout.write('\n')
                sys.stdout.flush()


# 异步文件传输服务模块
class AsyncFileTransferService:
    """Manages asynchronous file transfer operations"""

    def __init__(self, reader, writer, auth_service):
        """
        Initialize AsyncFileTransferService
        """
        self.reader = reader
        self.writer = writer
        self.auth_service = auth_service
        self.total_blocks = 0
        self.block_size = 0
        self.file_key = ""
        self.file_size = 0
        self.file_name = ""
        self.file_path = ""

    async def get_upload_plan(self, file_path, custom_key=None):
        """
        Retrieve upload plan from server asynchronously
        """
        self.file_path = file_path
        self.file_name = custom_key or os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)

        payload = {
            FIELD_KEY: self.file_name,
            FIELD_SIZE: self.file_size
        }

        await AsyncNetworkManager.async_send_message(
            self.writer, OP_SAVE, TYPE_FILE, payload,
            token=self.auth_service.get_token()
        )

        response, _ = await AsyncNetworkManager.async_unpack_message(self.reader)
        if not response:
            print("No upload plan response received")
            return False

        status_code = response.get(FIELD_STATUS)
        if ErrorHandler.check_error(response, status_code):
            return False

        print(f'\nServer response: {response[FIELD_STATUS_MSG]}')
        print(f'File key: {response[FIELD_KEY]}')
        print(f'File size: {response[FIELD_SIZE]} bytes')
        print(f'Total blocks: {response[FIELD_TOTAL_BLOCK]}')
        print(f'Block size: {response[FIELD_BLOCK_SIZE]} bytes')
        print(f'Status code: {status_code}\n')

        self.file_key = response[FIELD_KEY]
        self.total_blocks = response[FIELD_TOTAL_BLOCK]
        self.block_size = response[FIELD_BLOCK_SIZE]
        return True

    @staticmethod
    def calculate_local_md5(file_path, block_size=8192):
        """计算本地文件的MD5值"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(block_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    async def upload_block(self, block_index, bin_data, progress_bar, semaphore):
        """
        Upload a single block asynchronously with retry mechanism
        """
        async with semaphore:  # 限制并发数
            payload = {
                FIELD_KEY: self.file_key,
                FIELD_BLOCK_INDEX: block_index
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await AsyncNetworkManager.async_send_message(
                        self.writer, OP_UPLOAD, TYPE_FILE, payload,
                        bin_data=bin_data, token=self.auth_service.get_token()
                    )

                    # 设置读取超时
                    response, _ = await asyncio.wait_for(
                        AsyncNetworkManager.async_unpack_message(self.reader),
                        timeout=RE_TRANSMISSION_TIME
                    )

                    if not response:
                        raise asyncio.TimeoutError("No response received")

                    status_code = response.get(FIELD_STATUS)
                    if ErrorHandler.check_error(response, status_code):
                        return None

                    progress_bar.update(1)
                    return response

                except (asyncio.TimeoutError, Exception) as e:
                    if attempt < max_retries - 1:
                        print(f"\nRetransmitting block {block_index} (attempt {attempt + 1}): {e}")
                        await asyncio.sleep(1)  # 重传前等待
                    else:
                        print(f"\nFailed to upload block {block_index} after {max_retries} attempts: {e}")
                        return None

    async def upload_file_async(self, file_path, max_concurrent_uploads=5):
        """
        Upload file using truly asynchronous operations
        """
        print(f"Starting async upload with {max_concurrent_uploads} concurrent uploads")
        start_time = time.time()
        progress_bar = ProgressBar(self.total_blocks)

        # 使用信号量限制并发上传数量
        semaphore = asyncio.Semaphore(max_concurrent_uploads)

        # 创建上传任务
        upload_tasks = []
        md5_response = None

        async for block_index, bin_data in AsyncFileBlockProcessor.async_read_blocks(
                file_path, self.block_size, self.total_blocks, self.file_size
        ):
            task = asyncio.create_task(
                self.upload_block(block_index, bin_data, progress_bar, semaphore)
            )
            upload_tasks.append(task)

        # 等待所有上传任务完成，并检查MD5响应
        results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # 查找MD5响应
        for result in results:
            if isinstance(result, dict) and FIELD_MD5 in result:
                md5_response = result
                break

        # 处理完成后的MD5验证
        await self._handle_upload_completion(md5_response, start_time)

    async def _handle_upload_completion(self, md5_response, start_time):
        """处理上传完成后的MD5验证和结果输出"""
        if md5_response and FIELD_MD5 in md5_response:
            local_md5 = self.calculate_local_md5(self.file_path)
            server_md5 = md5_response[FIELD_MD5]

            print(f'\n\nFile Upload Completed!')
            print(f'Local file MD5:  {local_md5}')
            print(f'Server file MD5: {server_md5}')

            if local_md5 == server_md5:
                print("MD5 verification succeeded - file transfer is intact")
            else:
                print("WARNING: MD5 verification failed - file may be corrupted during transfer")

            print(f'Total Upload Time: {time.time() - start_time:.2f} seconds')
            print(f'Server response: {md5_response[FIELD_STATUS_MSG]} (Code: {md5_response[FIELD_STATUS]})')
        else:
            print(f'\nUpload completed, but no MD5 verification received from server')


# 主异步客户端类
class AsyncSTEPFileClient:
    """Main async client class coordinating authentication and file transfer services"""

    def __init__(self, server_ip, server_port):
        """
        Initialize AsyncSTEPFileClient
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.auth_service = None
        self.file_transfer_service = None

    async def connect(self):
        """
        Establish async connection to the server
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_ip, self.server_port
            )
            print(f"Connected to server {self.server_ip}:{self.server_port}")

            # Initialize service modules
            self.auth_service = AsyncAuthenticationService(self.reader, self.writer)
            self.file_transfer_service = AsyncFileTransferService(
                self.reader, self.writer, self.auth_service
            )
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False

    async def login(self, student_id):
        """
        Perform user login asynchronously
        """
        return await self.auth_service.login(student_id)

    async def upload_file_async(self, file_path, custom_key=None, max_concurrent=5):
        """
        Complete file upload process using truly asynchronous operations
        """
        if not await self.file_transfer_service.get_upload_plan(file_path, custom_key):
            return False

        await self.file_transfer_service.upload_file_async(file_path, max_concurrent)
        return True

    async def close(self):
        """Close the connection to the server asynchronously"""
        if self.writer:
            try:
                await AsyncNetworkManager.async_send_message(
                    self.writer, OP_BYE, TYPE_AUTH, {},
                    token=self.auth_service.get_token() if self.auth_service else None
                )
            except Exception as e:
                print(f"Error sending bye message: {e}")
            finally:
                self.writer.close()
                await self.writer.wait_closed()
                print("\nConnection closed")


async def main():
    args = _argparse()

    # Get server IP from user input
    args.ip = input("Enter server IP: ").strip()

    # Initialize and connect client
    client = AsyncSTEPFileClient(args.ip, args.port)
    if not await client.connect():
        sys.exit(1)

    # Perform login
    while True:
        print("Logging in...")
        student_id = input("Enter student ID (username): ").strip()
        if student_id == "":
            print("Invalid student ID, please enter again")
            continue
        if await client.login(student_id):
            break
        print("Login failed. Please try again.")

    # Get valid file path from user
    file_path = None
    while True:
        input_path = input("Enter file path to upload (enter 'q' to exit): ").strip()
        if input_path.lower() == 'q':
            print("Exiting...")
            await client.close()
            sys.exit(0)
        if os.path.exists(input_path) and os.path.isfile(input_path):
            file_path = input_path
            print(f"Valid file: {file_path}")
            break
        else:
            print(f"Invalid path: '{input_path}' (not a file or does not exist)")

    # Get optional custom key
    custom_key = input("Enter custom file key (optional, press enter to skip): ").strip() or None

    # Get concurrent upload count
    try:
        max_concurrent = int(input("Enter maximum concurrent uploads (default 5): ").strip() or "5")
    except ValueError:
        max_concurrent = 5
        print("Using default concurrent uploads: 5")

    # Execute upload using truly async method
    print(f"\nStarting file upload with {max_concurrent} concurrent uploads...")
    result = await client.upload_file_async(file_path, custom_key, max_concurrent)
    print(f"\nFinal result: {'Success' if result else 'Failed'}")

    # Close connection
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())