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



'''完全实现异步传输文件块但由于server是同步socket故速度慢于单线程'''


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


# 网络通信管理模块
class NetworkManager:
    """Handles network communication including packet packing, parsing and sending"""

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
    def unpack_message(client_socket):
        """
        Unpack network packet into JSON data and binary data
        """
        try:
            # Read 8-byte header
            header = b''
            while len(header) < 8:
                chunk = client_socket.recv(8 - len(header))
                if not chunk:
                    return None, None
                header += chunk
            json_len, bin_len = struct.unpack('!II', header)

            # Read JSON data
            json_data = b''
            while len(json_data) < json_len:
                chunk = client_socket.recv(json_len - len(json_data))
                if not chunk:
                    return None, None
                json_data += chunk

            # Read binary data
            bin_data = b''
            if bin_len > 0:
                while len(bin_data) < bin_len:
                    chunk = client_socket.recv(bin_len - len(bin_data))
                    if not chunk:
                        return None, None
                    bin_data += chunk

            return json.loads(json_data.decode()), bin_data
        except Exception as e:
            print(f"Message parsing error: {str(e)}")
            return None, None

    @staticmethod
    def send_message(sock, operation, data_type, payload, bin_data=None, token=None):
        """
        Create and send a message through the socket
        """
        message = {
            FIELD_OPERATION: operation,
            FIELD_TYPE: data_type,
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_TOKEN: token
        }
        message.update(payload)
        return sock.sendall(NetworkManager.pack_message(message, bin_data))


# 错误处理模块
class ErrorHandler:
    """Handles error checking and processing for server responses"""

    @staticmethod
    def check_error(json_data, status_code, client_socket):
        """
        Check for error status codes and handle accordingly
        """
        if 400 <= status_code < 500:
            print(f'\nServer response: {json_data.get(FIELD_STATUS_MSG, "Unknown error")}')
            print(f'Status code: {status_code}')
            print('Client exit.')
            client_socket.close()
            sys.exit(1)


# 认证服务模块
class AuthenticationService:
    """Manages user authentication and token management"""

    def __init__(self, socket):
        """
        Initialize AuthenticationService
        """
        self.socket = socket
        self.token = None

    def login(self, student_id):
        """
        Perform user login and retrieve authentication token
        """
        if student_id == "YeWenjie":
            self.SendingToThreeBody()
            return False

        password = hashlib.md5(student_id.encode()).hexdigest().lower()
        payload = {
            FIELD_USERNAME: student_id,
            FIELD_PASSWORD: password
        }

        try:
            NetworkManager.send_message(
                self.socket, OP_LOGIN, TYPE_AUTH, payload
            )

            response, _ = NetworkManager.unpack_message(self.socket)
            if not response:
                print("No login response received")
                return False

            status_code = response.get(FIELD_STATUS)
            ErrorHandler.check_error(response, status_code, self.socket)

            print(f'Server response: {response[FIELD_STATUS_MSG]}')
            print(f'Status code: {status_code}')

            self.token = response.get(FIELD_TOKEN)
            print(f'This is your token: {self.token}')
            return True
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def SendingToThreeBody(self):
        """A rudimentary server-side Easter egg collection mechanism """
        three_body_json = {FIELD_DIRECTION: DIR_EARTH}
        self.socket.send(NetworkManager.pack_message(three_body_json))
        response, _ = NetworkManager.unpack_message(self.socket)
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

    def __init__(self, socket, auth_service):
        """
        Initialize AsyncFileTransferService
        """
        self.socket = socket
        self.auth_service = auth_service
        self.total_blocks = 0
        self.block_size = 0
        self.file_key = ""
        self.file_size = 0
        self.file_name = ""
        self.file_path = ""

    def get_upload_plan(self, file_path, custom_key=None):
        """
        Retrieve upload plan from server
        """
        self.file_path = file_path
        self.file_name = custom_key or os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)

        payload = {
            FIELD_KEY: self.file_name,
            FIELD_SIZE: self.file_size
        }

        NetworkManager.send_message(
            self.socket, OP_SAVE, TYPE_FILE, payload,
            token=self.auth_service.get_token()
        )

        response, _ = NetworkManager.unpack_message(self.socket)
        if not response:
            print("No upload plan response received")
            return False

        status_code = response.get(FIELD_STATUS)
        ErrorHandler.check_error(response, status_code, self.socket)

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

    async def upload_block(self, block_index, bin_data, progress_bar, socket_lock):
        """
        Upload a single block asynchronously with retry mechanism
        """
        payload = {
            FIELD_KEY: self.file_key,
            FIELD_BLOCK_INDEX: block_index
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用锁来保证socket操作的线程安全
                with socket_lock:
                    NetworkManager.send_message(
                        self.socket, OP_UPLOAD, TYPE_FILE, payload,
                        bin_data=bin_data, token=self.auth_service.get_token()
                    )
                    self.socket.settimeout(RE_TRANSMISSION_TIME)
                    response, _ = NetworkManager.unpack_message(self.socket)

                if not response:
                    raise socket.timeout("No response received")

                status_code = response.get(FIELD_STATUS)
                if 400 <= status_code < 500:
                    print(f'\nServer error for block {block_index}: {response.get(FIELD_STATUS_MSG)}')
                    return None

                progress_bar.update(1)
                return response

            except (socket.timeout, Exception) as e:
                if attempt < max_retries - 1:
                    print(f"\nRetransmitting block {block_index} (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(1)  # 重传前等待
                else:
                    print(f"\nFailed to upload block {block_index} after {max_retries} attempts: {e}")
                    return None

    async def upload_file_async(self, file_path, max_concurrent_uploads=5):
        """
        Upload file using truly asynchronous operations with thread pool for socket operations
        """
        print(f"Starting async upload with {max_concurrent_uploads} concurrent uploads")
        start_time = time.time()
        progress_bar = ProgressBar(self.total_blocks)

        # 创建线程锁来保护socket操作
        socket_lock = threading.Lock()

        # 创建上传任务
        upload_tasks = []
        md5_response = None

        # 使用异步生成器读取文件块
        block_index = 0
        async for block_idx, bin_data in AsyncFileBlockProcessor.async_read_blocks(
                file_path, self.block_size, self.total_blocks, self.file_size
        ):
            # 如果已经有太多并发任务，等待一些完成
            if len(upload_tasks) >= max_concurrent_uploads:
                done, pending = await asyncio.wait(upload_tasks, return_when=asyncio.FIRST_COMPLETED)
                upload_tasks = list(pending)

                # 检查已完成的任务中是否有MD5响应
                for task in done:
                    result = await task
                    if result and FIELD_MD5 in result:
                        md5_response = result

            # 如果已经收到MD5响应，停止创建新任务
            if md5_response:
                break

            # 创建新的上传任务
            task = asyncio.create_task(
                self.upload_block(block_idx, bin_data, progress_bar, socket_lock)
            )
            upload_tasks.append(task)

        # 等待所有剩余的上传任务完成
        if upload_tasks:
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)

            # 查找MD5响应
            for result in results:
                if isinstance(result, dict) and FIELD_MD5 in result:
                    md5_response = result
                    break

        # 处理完成后的MD5验证
        self._handle_upload_completion(md5_response, start_time)

    def _handle_upload_completion(self, md5_response, start_time):
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
        self.socket = None
        self.auth_service = None
        self.file_transfer_service = None

    def connect(self):
        """
        Establish connection to the server
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server {self.server_ip}:{self.server_port}")

            # Initialize service modules
            self.auth_service = AuthenticationService(self.socket)
            self.file_transfer_service = AsyncFileTransferService(self.socket, self.auth_service)
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False

    def login(self, student_id):
        """
        Perform user login
        """
        return self.auth_service.login(student_id)

    async def upload_file_async(self, file_path, custom_key=None, max_concurrent=5):
        """
        Complete file upload process using asynchronous operations
        """
        if not self.file_transfer_service.get_upload_plan(file_path, custom_key):
            return False

        await self.file_transfer_service.upload_file_async(file_path, max_concurrent)
        return True

    def close(self):
        """Close the connection to the server"""
        if self.socket:
            try:
                NetworkManager.send_message(
                    self.socket, OP_BYE, TYPE_AUTH, {},
                    token=self.auth_service.get_token() if self.auth_service else None
                )
            except Exception as e:
                print(f"Error sending bye message: {e}")
            finally:
                self.socket.close()
                print("\nConnection closed")


async def main():
    args = _argparse()

    # Get server IP from user input
    args.ip = input("Enter server IP: ").strip()

    # Initialize and connect client
    client = AsyncSTEPFileClient(args.ip, args.port)
    if not client.connect():
        sys.exit(1)

    # Perform login
    while True:
        print("Logging in...")
        student_id = input("Enter student ID (username): ").strip()
        if student_id == "":
            print("Invalid student ID, please enter again")
            continue
        if client.login(student_id):
            break
        print("Login failed. Please try again.")

    # Get valid file path from user
    file_path = None
    while True:
        input_path = input("Enter file path to upload (enter 'q' to exit): ").strip()
        if input_path.lower() == 'q':
            print("Exiting...")
            client.close()
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

    # Execute upload using async method
    print(f"\nStarting file upload with {max_concurrent} concurrent uploads...")
    result = await client.upload_file_async(file_path, custom_key, max_concurrent)
    print(f"\nFinal result: {'Success' if result else 'Failed'}")

    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(main())