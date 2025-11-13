#!/usr/bin/env python3
"""
A4 - 重复上传（相同文件名）
验证重复上传相同文件名时的错误处理
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

from vm_test_utils import VMTestConfig, VMTestLogger, VMFileManager, VMNetworkTester, save_vm_test_results, verify_file_integrity_vm

def main():
    print("=== A4 测试：重复上传（相同文件名） ===")

    # 初始化测试
    test_name = "A4"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '重复上传测试（相同文件名）',
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
        logger.info("创建1MB测试文件...")
        test_file = VMFileManager.create_test_file(
            VMTestConfig.TEST_FILE_SIZE_1MB, 
            "test_repeat_upload.bin"
        )

        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_vm_test_results(test_name, results)
            return False

        # 第一次上传
        logger.info("第一次上传...")
        first_upload_result = VMNetworkTester.run_client_upload(str(test_file))

        if not first_upload_result:
            logger.error("第一次上传测试执行失败")
            results['status'] = 'FAILED'
            results['error'] = '第一次上传测试执行失败'
            save_vm_test_results(test_name, results)
            return False

        # 等待片刻
        time.sleep(2)

        # 第二次上传（相同文件名）
        logger.info("第二次上传（相同文件名）...")
        second_upload_result = VMNetworkTester.run_client_upload(str(test_file))

        # 记录测试用例结果
        first_test_case = {
            'name': 'A4_First_Upload',
            'file_size': test_file.stat().st_size,
            'duration': first_upload_result['duration'],
            'upload_success': first_upload_result['success'],
            'return_code': first_upload_result['return_code'],
            'stdout_excerpt': first_upload_result['stdout'][-300:] if len(first_upload_result['stdout']) > 300 else first_upload_result['stdout']
        }

        second_test_case = {
            'name': 'A4_Second_Upload',
            'file_size': test_file.stat().st_size,
            'duration': second_upload_result['duration'] if second_upload_result else 0,
            'upload_success': second_upload_result['success'] if second_upload_result else False,
            'return_code': second_upload_result['return_code'] if second_upload_result else -1,
            'stdout_excerpt': second_upload_result['stdout'][-300:] if second_upload_result and len(second_upload_result['stdout']) > 300 else (second_upload_result['stdout'] if second_upload_result else '')
        }

        results['test_cases'].append(first_test_case)
        results['test_cases'].append(second_test_case)

        # 判断测试结果
        # 期望：第一次上传成功，第二次上传失败（重复文件）
        if (first_upload_result['success'] and 
            (not second_upload_result or not second_upload_result['success'])):
            logger.info("✅ A4 测试通过：第一次上传成功，第二次上传正确处理")
            results['status'] = 'PASSED'
            results['final_result'] = '重复上传正确处理'
        else:
            logger.error("❌ A4 测试失败")
            results['status'] = 'FAILED'
            results['final_result'] = '重复上传处理不正确'

            if not first_upload_result['success']:
                logger.error("第一次上传失败")
                logger.error(f"错误输出: {first_upload_result['stderr']}")
            if second_upload_result and second_upload_result['success']:
                logger.error("第二次上传不应该成功")
                logger.error(f"第二次上传输出: {second_upload_result['stdout']}")

    except Exception as e:
        logger.error(f"A4测试异常: {e}")
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

        print(f"=== A4 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)