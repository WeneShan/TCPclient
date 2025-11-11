#!/usr/bin/env python3
"""
A3 - 文件大小非 block_size 倍数（尾块处理）
测试最后一块小于 block_size 时是否正确处理
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def main():
    print("=== A3 测试：尾块处理（文件大小非block_size倍数） ===")
    
    # 初始化测试
    test_name = "A3"
    logger = TestLogger(test_name)
    client_tester = ClientTester(test_name)
    results = {
        'test_name': test_name,
        'test_description': '文件大小非block_size倍数的尾块处理测试',
        'start_time': datetime.now().isoformat(),
        'test_cases': []
    }
    
    try:
        # 启动服务器
        logger.info("启动服务器...")
        server_process = ServerManager.start_server()
        
        if not server_process:
            logger.error("服务器启动失败")
            results['status'] = 'FAILED'
            results['error'] = '服务器启动失败'
            save_test_results(test_name, results)
            return False
            
        logger.info("服务器启动成功")
        
        # 创建10MB+13KB测试文件（确保不是block_size的倍数）
        # 假设block_size约为20KB，则10MB+13KB肯定不是倍数
        file_size = TestConfig.TEST_FILE_SIZE_10MB + 13 * 1024  # 10MB + 13KB
        
        logger.info(f"创建文件大小: {file_size} 字节 ({file_size/1024/1024:.2f}MB)")
        test_file = FileManager.create_test_file(file_size, "test_non_aligned.bin")
        
        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_test_results(test_name, results)
            return False
        
        # 计算本地文件MD5
        local_md5 = FileManager.calculate_md5(test_file)
        logger.info(f"本地文件MD5: {local_md5}")
        
        # 运行上传测试
        logger.info("开始文件上传...")
        test_result = client_tester.run_upload_test("test_non_aligned.bin")
        
        if not test_result:
            logger.error("上传测试执行失败")
            results['status'] = 'FAILED'
            results['error'] = '上传测试执行失败'
            save_test_results(test_name, results)
            return False
        
        # 验证文件完整性
        logger.info("验证文件完整性...")
        is_valid, server_md5, client_md5 = client_tester.verify_file_integrity("test_non_aligned.bin")
        
        # 分析客户端输出，查找尾块处理相关信息
        last_block_info = None
        if test_result['stdout']:
            # 查找包含"block"和最后一块相关的信息
            lines = test_result['stdout'].split('\n')
            for line in reversed(lines):
                if 'block' in line.lower() and any(word in line for word in ['complete', 'finish', 'total']):
                    last_block_info = line.strip()
                    break
        
        # 记录测试用例结果
        test_case = {
            'name': 'A3_Non_Aligned_Upload',
            'file_size': test_result['file_size'],
            'duration': test_result['duration'],
            'local_md5': local_md5,
            'server_md5': server_md5,
            'client_md5': client_md5,
            'file_integrity': is_valid,
            'upload_success': test_result['success'],
            'return_code': test_result['return_code'],
            'last_block_info': last_block_info,
            'stdout_excerpt': test_result['stdout'][-500:] if len(test_result['stdout']) > 500 else test_result['stdout']
        }
        
        results['test_cases'].append(test_case)
        
        # 判断测试结果
        if (test_result['success'] and is_valid and 
            local_md5 == server_md5 == client_md5):
            logger.info("✅ A3 测试通过：尾块处理正确，文件完整")
            results['status'] = 'PASSED'
            results['final_result'] = '尾块处理正确，MD5校验一致'
        else:
            logger.error("❌ A3 测试失败")
            results['status'] = 'FAILED'
            results['final_result'] = '尾块处理失败或MD5校验失败'
            
            if not test_result['success']:
                logger.error(f"上传失败，返回码: {test_result['return_code']}")
            if not is_valid:
                logger.error("文件完整性验证失败")
        
    except Exception as e:
        logger.error(f"A3测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
    finally:
        # 停止服务器
        if 'server_process' in locals() and server_process:
            logger.info("停止服务器...")
            ServerManager.stop_server(server_process)
        
        # 清理测试文件
        if 'test_file' in locals() and test_file.exists():
            try:
                test_file.unlink()
                logger.info("清理测试文件完成")
            except:
                pass
        
        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_test_results(test_name, results)
        
        print(f"=== A3 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)