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


'''
此版本优化了异步算法

异步读取优势：使用 aiofiles 异步读取文件，充分利用I/O等待时间

同步上传优势：避免锁竞争、上下文切换等异步开销

内存预分配：一次性读取所有块到内存，减少系统调用

简化架构：没有复杂的并发控制，代码路径更直接

性能对比：
纯单线程：读取(慢) + 上传(快)

纯异步：读取(快) + 上传(慢，因为锁竞争)

此版本：读取(快) + 上传(快)
'''





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
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default='127.0.0.1', action='store', required=False, dest="ip",
                        help="The IP address of the server. Default is 127.0.0.1.")
    parser.add_argument("--port", default=SERVER_PORT, action='store', required=False, dest="port", type=int,
                        help=f"The port of the server. Default is {SERVER_PORT}.")
    return parser.parse_args()


class NetworkManager:
    """网络通信管理模块"""

    @staticmethod
    def pack_message(json_data, bin_data=None):
        json_str = json.dumps(json_data, ensure_ascii=False)
        json_bytes = json_str.encode()
        json_len = len(json_bytes)
        bin_len = len(bin_data) if bin_data else 0
        header = struct.pack('!II', json_len, bin_len)
        return header + json_bytes + (bin_data or b'')

    @staticmethod
    def unpack_message(client_socket):
        try:
            header = b''
            while len(header) < 8:
                chunk = client_socket.recv(8 - len(header))
                if not chunk:
                    return None, None
                header += chunk
            json_len, bin_len = struct.unpack('!II', header)

            json_data = b''
            while len(json_data) < json_len:
                chunk = client_socket.recv(json_len - len(json_data))
                if not chunk:
                    return None, None
                json_data += chunk

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
        message = {
            FIELD_OPERATION: operation,
            FIELD_TYPE: data_type,
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_TOKEN: token
        }
        message.update(payload)
        return sock.sendall(NetworkManager.pack_message(message, bin_data))


class ErrorHandler:
    @staticmethod
    def check_error(json_data, status_code, client_socket):
        if 400 <= status_code < 500:
            print(f'\nServer response: {json_data.get(FIELD_STATUS_MSG, "Unknown error")}')
            print(f'Status code: {status_code}')
            print('Client exit.')
            client_socket.close()
            sys.exit(1)


class AuthenticationService:
    def __init__(self, socket):
        self.socket = socket
        self.token = None

    def login(self, student_id):
        if student_id == "YeWenjie":
            self.SendingToThreeBody()
            return False

        password = hashlib.md5(student_id.encode()).hexdigest().lower()
        payload = {
            FIELD_USERNAME: student_id,
            FIELD_PASSWORD: password
        }

        try:
            NetworkManager.send_message(self.socket, OP_LOGIN, TYPE_AUTH, payload)
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
        three_body_json = {FIELD_DIRECTION: DIR_EARTH}
        self.socket.send(NetworkManager.pack_message(three_body_json))
        response, _ = NetworkManager.unpack_message(self.socket)
        if response:
            print(f"receive from ThreeBody: {response.get(FIELD_STATUS_MSG)}")

    def get_token(self):
        return self.token


class FastFileBlockProcessor:
    """优化的文件块处理器"""

    @staticmethod
    async def read_blocks_fast(file_path, block_size, total_blocks, file_size):
        """
        快速异步读取文件块 - 使用大块读取减少系统调用
        """
        # 预分配缓冲区
        blocks = []

        async with aiofiles.open(file_path, 'rb') as f:
            for block_idx in range(total_blocks):
                position = block_idx * block_size
                remaining = file_size - position
                chunk_size = min(block_size, remaining)

                await f.seek(position)
                data = await f.read(chunk_size)
                blocks.append((block_idx, data))

        return blocks


class ProgressBar:
    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.start_time = time.time()

    def update(self, increment=1):
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


class OptimizedFileTransferService:
    """
    优化的文件传输服务
    使用异步读取 + 同步上传的组合，达到最佳性能
    """

    def __init__(self, socket, auth_service):
        self.socket = socket
        self.auth_service = auth_service
        self.total_blocks = 0
        self.block_size = 0
        self.file_key = ""
        self.file_size = 0
        self.file_name = ""
        self.file_path = ""

    def get_upload_plan(self, file_path, custom_key=None):
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
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(block_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _upload_block_sync(self, block_index, bin_data, progress_bar):
        """同步上传单个块 - 这是最快的上传方式"""
        payload = {
            FIELD_KEY: self.file_key,
            FIELD_BLOCK_INDEX: block_index
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                    time.sleep(1)
                else:
                    print(f"\nFailed to upload block {block_index} after {max_retries} attempts: {e}")
                    return None

    async def upload_file_optimized(self, file_path):
        """
        优化的上传方法：异步读取 + 同步上传
        这是最快的方法，因为：
        1. 异步读取充分利用了I/O等待时间
        2. 同步上传避免了锁竞争和上下文切换开销
        """
        print("Starting optimized upload (async read + sync upload)...")
        start_time = time.time()
        progress_bar = ProgressBar(self.total_blocks)

        # 第一步：异步读取所有文件块到内存
        print("Phase 1: Reading file blocks asynchronously...")
        blocks = await FastFileBlockProcessor.read_blocks_fast(
            file_path, self.block_size, self.total_blocks, self.file_size
        )

        print(f"Phase 2: Uploading {len(blocks)} blocks synchronously...")
        # 第二步：同步上传所有块（避免异步开销）
        md5_response = None
        for block_index, bin_data in blocks:
            response = self._upload_block_sync(block_index, bin_data, progress_bar)
            if response and FIELD_MD5 in response:
                md5_response = response
                break

        # 处理完成结果
        self._handle_upload_completion(md5_response, start_time)

    def _handle_upload_completion(self, md5_response, start_time):
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


class OptimizedSTEPFileClient:
    """优化的客户端类"""

    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.auth_service = None
        self.file_transfer_service = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server {self.server_ip}:{self.server_port}")

            self.auth_service = AuthenticationService(self.socket)
            self.file_transfer_service = OptimizedFileTransferService(self.socket, self.auth_service)
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False

    def login(self, student_id):
        return self.auth_service.login(student_id)

    async def upload_file_optimized(self, file_path, custom_key=None):
        if not self.file_transfer_service.get_upload_plan(file_path, custom_key):
            return False

        await self.file_transfer_service.upload_file_optimized(file_path)
        return True

    def close(self):
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

    args.ip = input("Enter server IP: ").strip()

    client = OptimizedSTEPFileClient(args.ip, args.port)
    if not client.connect():
        sys.exit(1)

    while True:
        print("Logging in...")
        student_id = input("Enter student ID (username): ").strip()
        if student_id == "":
            print("Invalid student ID, please enter again")
            continue
        if client.login(student_id):
            break
        print("Login failed. Please try again.")

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

    custom_key = input("Enter custom file key (optional, press enter to skip): ").strip() or None

    print("\nStarting optimized file upload...")
    result = await client.upload_file_optimized(file_path, custom_key)
    print(f"\nFinal result: {'Success' if result else 'Failed'}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())