#!/usr/bin/env python3
"""
A5 - 认证错误（错误密码）
验证错误密码时的认证失败处理
专为VirtualBox Ubuntu虚拟机环境设计
假设服务器已经在另一个虚拟机中运行
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径到系统路径
project_path = Path("/home/stepuser/STEP-Project/")
sys.path.insert(0, str(project_path))

from test.vm_test_utils import VMTestConfig, VMTestLogger, VMFileManager, VMNetworkTester, save_vm_test_results

def main():
    print("=== A5 测试：认证错误（错误密码） ===")

    # 初始化测试
    test_name = "A5"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '认证错误测试（错误密码）',
        'start_time': datetime.now().isoformat(),
        'test_cases': []
    }

    try:
        # 检查服务器连接性
        logger.info("检查服务器连接性...")
        if not VMNetworkTester.check_server_connectivity():
            logger.error("服务器连接失败，请确保服务器虚拟机正在运行")
            results['status'] = 'FAILED'
            results['error'] = '服务器连接失败'
            save_vm_test_results(test_name, results)
            return False
            
        logger.info("服务器连接正常")

        # 创建测试文件
        logger.info("创建100KB测试文件...")
        test_file = VMFileManager.create_test_file(
            VMTestConfig.TEST_FILE_SIZE_100KB, 
            "test_auth_error.bin"
        )

        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_vm_test_results(test_name, results)
            return False

        # 使用错误密码进行上传测试
        wrong_student_id = "wrong_user_123"
        logger.info(f"使用错误用户名进行上传测试: {wrong_student_id}")
        test_result = VMNetworkTester.run_client_upload(str(test_file), student_id=wrong_student_id)

        if not test_result:
            logger.error("上传测试执行失败")
            results['status'] = 'FAILED'
            results['error'] = '上传测试执行失败'
            save_vm_test_results(test_name, results)
            return False

        # 记录测试用例结果
        test_case = {
            'name': 'A5_Auth_Error_Upload',
            'file_size': test_file.stat().st_size,
            'duration': test_result['duration'],
            'username_used': wrong_student_id,
            'upload_success': test_result['success'],
            'return_code': test_result['return_code'],
            'stdout_excerpt': test_result['stdout'][-500:] if len(test_result['stdout']) > 500 else test_result['stdout'],
            'stderr_excerpt': test_result['stderr'][-300:] if len(test_result['stderr']) > 300 else test_result['stderr']
        }

        results['test_cases'].append(test_case)

        # 判断测试结果
        # 期望：上传失败（认证错误）
        if not test_result['success']:
            logger.info("✅ A5 测试通过：认证错误正确处理")
            results['status'] = 'PASSED'
            results['final_result'] = '认证错误正确处理'
        else:
            logger.error("❌ A5 测试失败：认证错误时上传不应该成功")
            results['status'] = 'FAILED'
            results['final_result'] = '认证错误处理不正确'

    except Exception as e:
        logger.error(f"A5测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)

    finally:
        # 清理测试文件
        if 'test_file' in locals() and test_file.exists():
            try:
                test_file.unlink()
                logger.info("清理测试文件完成")
            except:
                pass

        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_vm_test_results(test_name, results)

        print(f"=== A5 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)