import argparse
import socket
import json
import struct
import hashlib
import os
import time
import sys
import mmap
from multiprocessing import Process, Queue

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


# 网络通信管理模块，负责数据包的打包、解析和发送
class NetworkManager:
    """Handles network communication including packet packing, parsing and sending"""

    @staticmethod
    def pack_message(json_data, bin_data=None):
        """
        Pack JSON data and binary data into a network packet
        :param json_data: Dictionary containing metadata
        :param bin_data: Optional binary data
        :return: Bytes object representing the packed packet
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
        :param client_socket: Socket object for receiving data
        :return: Tuple containing (json_data, bin_data) or (None, None) on failure
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
        :param sock: Socket object for communication
        :param operation: Operation type (e.g., OP_LOGIN, OP_UPLOAD)
        :param data_type: Type of data (e.g., TYPE_AUTH, TYPE_FILE)
        :param payload: Dictionary containing message payload
        :param bin_data: Optional binary data
        :param token: Authentication token (optional)
        :return: Result of socket sendall operation
        """
        message = {
            FIELD_OPERATION: operation,
            FIELD_TYPE: data_type,
            FIELD_DIRECTION: DIR_REQUEST,
            FIELD_TOKEN: token
        }
        message.update(payload)
        return sock.sendall(NetworkManager.pack_message(message, bin_data))


# 错误处理模块，集中处理各类错误状态
class ErrorHandler:
    """Handles error checking and processing for server responses"""

    @staticmethod
    def check_error(json_data, status_code, client_socket):
        """
        Check for error status codes and handle accordingly
        :param json_data: Response data from server
        :param status_code: Status code from response
        :param client_socket: Socket object to close on critical errors
        """
        if 400 <= status_code < 500:
            print(f'\nServer response: {json_data.get(FIELD_STATUS_MSG, "Unknown error")}')
            print(f'Status code: {status_code}')
            print('Client exit.')
            client_socket.close()
            sys.exit(1)


# 认证服务模块，处理登录和令牌管理
class AuthenticationService:
    """Manages user authentication and token management"""

    def __init__(self, socket):
        """
        Initialize AuthenticationService
        :param socket: Socket object for server communication
        """
        self.socket = socket
        self.token = None

    def login(self, student_id):
        """
        Perform user login and retrieve authentication token
        :param student_id: Student ID used for login
        :return: True if login successful, False otherwise
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
        """
        Get current authentication token
        :return: Current token string or None if not authenticated
        """
        return self.token


# 文件块处理模块，负责单线程文件读取和索引计算
class FileBlockProcessor:
    """Handles file block processing including single-thread reading and index calculation"""

    @staticmethod
    def calculate_indices(process_num, total_blocks):
        """
        Calculate block index ranges for each process
        :param process_num: Number of processes
        :param total_blocks: Total number of blocks
        :return: Tuple of dictionaries containing start and end indices for each process
        """
        blocks_per_process = total_blocks // process_num
        start_indices = {}
        end_indices = {}

        for i in range(1, process_num + 1):
            if i == 1:
                start_indices[f'process_{i}'] = 0
                end_indices[f'process_{i}'] = blocks_per_process - 1
            elif i == process_num:
                start_indices[f'process_{i}'] = (i - 1) * blocks_per_process
                end_indices[f'process_{i}'] = total_blocks - 1
            else:
                start_indices[f'process_{i}'] = (i - 1) * blocks_per_process
                end_indices[f'process_{i}'] = i * blocks_per_process - 1

        return start_indices, end_indices

    @staticmethod
    def read_blocks_single_thread(start_idx, end_idx, block_size, file_path, file_size):
        """
        单线程读取文件块
        :param start_idx: 起始块索引
        :param end_idx: 结束块索引
        :param block_size: 块大小
        :param file_path: 文件路径
        :param file_size: 文件总大小
        :return: 包含块索引和数据的生成器
        """
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mapped_file:
                for block_idx in range(start_idx, end_idx + 1):
                    mapped_file.seek(block_idx * block_size)
                    remaining = file_size - block_idx * block_size
                    chunk_size = min(block_size, remaining)
                    data = mapped_file.read(chunk_size)
                    yield (block_idx, data)


# 进度条工具类，实现单行动态刷新
class ProgressBar:
    """Single-line dynamic progress bar for file upload"""

    @staticmethod
    def update(completed, total, start_time):
        """
        Update and display progress bar dynamically
        :param completed: Number of completed blocks
        :param total: Total number of blocks
        :param start_time: Start time of the upload
        """
        progress = (completed / total) * 100
        elapsed_time = time.time() - start_time
        speed = (completed * 1024 * 1024) / elapsed_time if elapsed_time > 0 else 0  # MB/s

        # Calculate progress bar components
        filled_length = int(PROGRESS_BAR_LENGTH * completed // total)
        bar = '█' * filled_length + '-' * (PROGRESS_BAR_LENGTH - filled_length)

        # Dynamic refresh (overwrite current line)
        sys.stdout.write(
            f'\rUpload Progress: |{bar}| {progress:.2f}% '
            f'[{completed}/{total} blocks] '
            f'Speed: {speed:.2f} MB/s '
            f'Elapsed: {elapsed_time:.1f}s'
        )
        sys.stdout.flush()

        # Add newline when completed
        if completed == total:
            sys.stdout.write('\n')
            sys.stdout.flush()


# 文件传输服务模块，处理上传计划和文件块上传
class FileTransferService:
    """Manages file transfer operations including upload planning and block uploading"""

    def __init__(self, socket, auth_service):
        """
        Initialize FileTransferService
        :param socket: Socket object for server communication
        :param auth_service: AuthenticationService instance for token management
        """
        self.socket = socket
        self.auth_service = auth_service
        self.total_blocks = 0
        self.block_size = 0
        self.file_key = ""
        self.file_size = 0
        self.file_name = ""
        self.file_path = ""  # 新增：存储文件路径用于计算MD5

    def get_upload_plan(self, file_path, custom_key=None):
        """
        Retrieve upload plan from server including block size and total blocks
        :param file_path: Path to the file to upload
        :param custom_key: Optional custom file key
        :return: True if plan retrieved successfully, False otherwise
        """
        self.file_path = file_path  # 保存文件路径
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
            # 分块读取文件计算MD5，避免大文件占用过多内存
            while chunk := f.read(block_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def upload_file(self, file_path, process_num=3):
        """
        单线程上传文件，使用生成器逐块读取文件
        :param file_path: Path to the file to upload
        :param process_num: 保留参数，用于兼容接口（实际使用单线程）
        """
        start_time = time.time()

        # 使用单线程读取所有块
        block_generator = FileBlockProcessor.read_blocks_single_thread(
            0, self.total_blocks - 1, self.block_size, file_path, self.file_size
        )

        # 上传块数据
        self._upload_blocks_from_generator(block_generator, start_time)

    def _upload_blocks_from_generator(self, block_generator, start_time):
        """
        从生成器上传文件块，支持超时重传和动态进度条
        :param block_generator: 生成器，产生(block_index, data)元组
        :param start_time: 上传开始时间戳
        """
        blocks_uploaded = 0
        last_server_msg = ""  # 存储最后一条服务器响应，避免频繁打印

        for block_index, bin_data in block_generator:
            payload = {
                FIELD_KEY: self.file_key,
                FIELD_BLOCK_INDEX: block_index
            }

            # 处理重传
            while True:
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
                    ErrorHandler.check_error(response, status_code, self.socket)
                    last_server_msg = f"Server response: {response[FIELD_STATUS_MSG]} (Code: {status_code})"
                    break
                except socket.timeout:
                    print(f"\nRetransmitting block {block_index} (timeout)")
                    ProgressBar.update(blocks_uploaded, self.total_blocks, start_time)  # Update the progress bar when retransmitting.

            # 更新进度条
            blocks_uploaded += 1
            ProgressBar.update(blocks_uploaded, self.total_blocks, start_time)

            # 检查是否完成（收到MD5）
            if FIELD_MD5 in response:
                # calculate local MD5 in order to compare with server
                local_md5 = self.calculate_local_md5(self.file_path)
                server_md5 = response[FIELD_MD5]

                print(f'\n\nFile Upload Completed!')
                print(f'Local file MD5:  {local_md5}')
                print(f'Server file MD5: {server_md5}')

                # compare MD5 from  server
                if local_md5 == server_md5:
                    print("MD5 verification succeeded - file transfer is intact")
                else:
                    print("WARNING: MD5 verification failed - file may be corrupted during transfer")

                print(f'Total Upload Time: {time.time() - start_time:.2f} seconds')
                print(last_server_msg)
                break

        # 如果没有在循环中打印完成信息，则打印最后的服务器消息
        if FIELD_MD5 not in locals().get('response', {}):
            print(f'\n{last_server_msg}')


# 主客户端类，协调各模块工作
class STEPFileClient:
    """Main client class coordinating authentication and file transfer services"""

    def __init__(self, server_ip, server_port):
        """
        Initialize STEPFileClient
        :param server_ip: Server IP address
        :param server_port: Server port number
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.auth_service = None
        self.file_transfer_service = None

    def connect(self):
        """
        Establish connection to the server
        :return: True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server {self.server_ip}:{self.server_port}")

            # Initialize service modules
            self.auth_service = AuthenticationService(self.socket)
            self.file_transfer_service = FileTransferService(self.socket, self.auth_service)
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False

    def login(self, student_id):
        """
        Perform user login
        :param student_id: Student ID for authentication
        :return: True if login successful, False otherwise
        """
        return self.auth_service.login(student_id)

    def upload_file(self, file_path, custom_key=None):
        """
        Complete file upload process
        :param file_path: Path to the file to upload
        :param custom_key: Optional custom file key
        :return: True if upload successful, False otherwise
        """
        if not self.file_transfer_service.get_upload_plan(file_path, custom_key):
            return False

        self.file_transfer_service.upload_file(file_path)
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
                print(f"Error sending bye message: {str(e)}")
            finally:
                self.socket.close()
                print("\nConnection closed")


if __name__ == "__main__":
    args = _argparse()

    # Get server IP from user input
    args.ip = input("Enter server IP: ").strip()

    # Initialize and connect client
    client = STEPFileClient(args.ip, args.port)
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

    # Execute upload
    print("\nStarting file upload...")
    result = client.upload_file(file_path, custom_key)
    print(f"\nFinal result: {'Success' if result else 'Failed'}")

    # Close connection
    client.close()