#!/usr/bin/env python3
"""
STEP协议测试工具模块
提供文件创建、日志记录、MD5校验等通用功能
"""

import os
import sys
import time
import json
import hashlib
import logging
import subprocess
from datetime import datetime
from pathlib import Path

class TestConfig:
    """测试配置类"""
    # 服务器配置
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = "1379"
    STUDENT_ID = "testuser123"
    
    # 测试文件配置
    TEST_FILE_SIZE_10MB = 10 * 1024 * 1024  # 10MB
    TEST_FILE_SIZE_1KB = 1024  # 1KB
    TEST_FILE_SIZE_100KB = 100 * 1024  # 100KB
    TEST_FILE_SIZE_1MB = 1024 * 1024  # 1MB
    TEST_FILE_SIZE_50MB = 50 * 1024 * 1024  # 50MB
    
    # 测试次数
    TEST_RETRY_COUNT = 3
    
    # 日志配置
    LOG_LEVEL = logging.INFO

class TestLogger:
    """测试日志记录器"""
    
    def __init__(self, test_name):
        self.test_name = test_name
        self.log_dir = Path(f"test/{test_name}")
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置日志记录器
        self.logger = logging.getLogger(test_name)
        self.logger.setLevel(TestConfig.LOG_LEVEL)
        
        # 清除已存在的处理器
        self.logger.handlers.clear()
        
        # 文件处理器
        log_file = self.log_dir / "test.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(TestConfig.LOG_LEVEL)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(TestConfig.LOG_LEVEL)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def info(self, message):
        self.logger.info(message)
        
    def error(self, message):
        self.logger.error(message)
        
    def warning(self, message):
        self.logger.warning(message)
        
    def debug(self, message):
        self.logger.debug(message)

class FileManager:
    """文件管理工具"""
    
    @staticmethod
    def create_test_file(size, filename):
        """创建指定大小的测试文件"""
        filepath = Path(f"test_data/{filename}")
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'wb') as f:
            # 写入指定大小的随机数据
            chunk_size = 1024 * 1024  # 1MB chunks
            remaining = size
            
            while remaining > 0:
                current_chunk = min(chunk_size, remaining)
                # 创建重复的测试数据模式，便于验证
                pattern = b'A' * 1024 + b'B' * 1024 + b'C' * 1024 + b'D' * 1024
                if len(pattern) > current_chunk:
                    pattern = pattern[:current_chunk]
                elif len(pattern) < current_chunk:
                    pattern = (pattern * (current_chunk // len(pattern) + 1))[:current_chunk]
                
                f.write(pattern)
                remaining -= current_chunk
        
        return filepath
    
    @staticmethod
    def calculate_md5(filepath):
        """计算文件的MD5值"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"MD5计算错误: {e}")
            return None
    
    @staticmethod
    def create_empty_file(filename):
        """创建0字节文件"""
        filepath = Path(f"test_data/{filename}")
        filepath.parent.mkdir(exist_ok=True)
        filepath.touch()
        return filepath
    
    @staticmethod
    def create_1byte_file(filename):
        """创建1字节文件"""
        filepath = Path(f"test_data/{filename}")
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(b'A')
        return filepath

class ServerManager:
    """服务器管理工具"""
    
    @staticmethod
    def start_server():
        """启动服务器"""
        try:
            # 清理旧的日志和临时文件
            subprocess.run(["rm", "-rf", "server/log/*"], check=False)
            subprocess.run(["rm", "-rf", "server/data/*"], check=False) 
            subprocess.run(["rm", "-rf", "server/file/*"], check=False)
            subprocess.run(["rm", "-rf", "server/tmp/*"], check=False)
            
            # # 创建必要的目录
            # os.makedirs("server/log/STEP", exist_ok=True)
            # os.makedirs("server/data", exist_ok=True)
            # os.makedirs("server/file", exist_ok=True)
            # os.makedirs("server/tmp", exist_ok=True)
            
            # 启动服务器（在后台）
            process = subprocess.Popen([
                sys.executable, 
                "server/server.py", 
                "--ip", TestConfig.SERVER_IP,
                "--port", TestConfig.SERVER_PORT
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(2)  # 等待服务器启动
            
            # 检查服务器是否正常运行
            if process.poll() is None:
                return process
            else:
                return None
                
        except Exception as e:
            print(f"服务器启动错误: {e}")
            return None
    
    @staticmethod
    def stop_server(process):
        """停止服务器"""
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

class ClientTester:
    """客户端测试器"""
    
    def __init__(self, test_name):
        self.test_name = test_name
        self.logger = TestLogger(test_name)
        self.results = {}
    
    def run_upload_test(self, filename, student_id=None):
        """运行文件上传测试"""
        if student_id is None:
            student_id = TestConfig.STUDENT_ID
            
        file_path = Path(f"test_data/{filename}")
        if not file_path.exists():
            self.logger.error(f"测试文件不存在: {file_path}")
            return None
        
        # 记录开始时间
        start_time = time.time()
        self.logger.info(f"开始上传测试: {filename}")
        
        try:
            # 准备客户端输入
            inputs = f"{TestConfig.SERVER_IP}\n{student_id}\n{file_path.absolute()}\n\n"
            
            # 运行客户端
            result = subprocess.run([
                sys.executable, 
                "client.py"
            ], 
            input=inputs, 
            text=True, 
            capture_output=True, 
            timeout=300  # 5分钟超时
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录结果
            test_result = {
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'duration': duration,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            self.logger.info(f"上传测试完成，耗时: {duration:.2f}秒")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            self.logger.error("上传测试超时")
            return None
        except Exception as e:
            self.logger.error(f"上传测试错误: {e}")
            return None
    
    def verify_file_integrity(self, uploaded_filename, student_id=None):
        """验证文件完整性"""
        if student_id is None:
            student_id = TestConfig.STUDENT_ID.replace('.', '_')
        
        # 查找服务器上的文件
        server_file_paths = [
            Path(f"server/file/{student_id}/{uploaded_filename}"),
            Path(f"server/tmp/{student_id}/{uploaded_filename}")
        ]
        
        for server_file_path in server_file_paths:
            if server_file_path.exists():
                local_file_path = Path(f"test_data/{uploaded_filename}")
                if local_file_path.exists():
                    local_md5 = FileManager.calculate_md5(local_file_path)
                    server_md5 = FileManager.calculate_md5(server_file_path)
                    
                    if local_md5 == server_md5:
                        self.logger.info(f"文件完整性验证通过: {uploaded_filename}")
                        return True, local_md5, server_md5
                    else:
                        self.logger.warning(f"文件完整性验证失败: {uploaded_filename}")
                        return False, local_md5, server_md5
        
        self.logger.error(f"服务器上未找到文件: {uploaded_filename}")
        return False, None, None

def save_test_results(test_name, results):
    """保存测试结果"""
    results_file = Path(f"test/{test_name}/results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # 测试工具模块
    print("STEP测试工具模块加载完成")