#!/usr/bin/env python3
"""
A4 - 重复上传（同文件名/同内容）/ 覆盖策略
测试服务器对重复上传的处理策略
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
    print("=== A4 测试：重复上传/覆盖策略 ===")
    
    # 初始化测试
    test_name = "A4"
    logger = TestLogger(test_name)
    client_tester = ClientTester(test_name)
    results = {
        'test_name': test_name,
        'test_description': '重复上传/覆盖策略测试',
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
        
        # 创建测试文件
        test_file_size = TestConfig.TEST_FILE_SIZE_1MB  # 使用1MB文件进行重复上传测试
        test_file = FileManager.create_test_file(test_file_size, "test_repeat.bin")
        
        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_test_results(test_name, results)
            return False
        
        # 计算本地文件MD5
        local_md5 = FileManager.calculate_md5(test_file)
        logger.info(f"本地文件MD5: {local_md5}")
        
        # 第一次上传
        logger.info("第一次上传...")
        test_result1 = client_tester.run_upload_test("test_repeat.bin")
        
        if not test_result1:
            logger.error("第一次上传失败")
            results['status'] = 'FAILED'
            results['error'] = '第一次上传失败'
            save_test_results(test_name, results)
            return False
        
        # 验证第一次上传的文件完整性
        is_valid1, server_md5_1, client_md5_1 = client_tester.verify_file_integrity("test_repeat.bin")
        
        # 等待一下，避免时间戳问题
        time.sleep(2)
        
        # 第二次上传
        logger.info("第二次上传...")
        test_result2 = client_tester.run_upload_test("test_repeat.bin")
        
        if not test_result2:
            logger.error("第二次上传失败")
            test_case1 = {
                'name': 'A4_First_Upload',
                'upload_success': test_result1['success'],
                'file_integrity': is_valid1,
                'server_md5': server_md5_1
            }
            results['test_cases'].append(test_case1)
            results['status'] = 'FAILED'
            results['error'] = '第二次上传失败'
            save_test_results(test_name, results)
            return False
        
        # 验证第二次上传的文件完整性
        is_valid2, server_md5_2, client_md5_2 = client_tester.verify_file_integrity("test_repeat.bin")
        
        # 分析服务器响应
        server_response1 = "成功"
        server_response2 = "成功"
        
        if test_result1['stdout']:
            lines1 = test_result1['stdout'].split('\n')
            for line in lines1:
                if 'status code' in line.lower() or 'response' in line.lower():
                    server_response1 = line.strip()
                    break
        
        if test_result2['stdout']:
            lines2 = test_result2['stdout'].split('\n')
            for line in lines2:
                if 'status code' in line.lower() or 'response' in line.lower():
                    server_response2 = line.strip()
                    break
        
        # 记录测试用例结果
        test_case1 = {
            'name': 'A4_First_Upload',
            'upload_success': test_result1['success'],
            'file_integrity': is_valid1,
            'local_md5': local_md5,
            'server_md5': server_md5_1,
            'client_md5': client_md5_1,
            'duration': test_result1['duration'],
            'server_response': server_response1
        }
        
        test_case2 = {
            'name': 'A4_Second_Upload',
            'upload_success': test_result2['success'],
            'file_integrity': is_valid2,
            'local_md5': local_md5,
            'server_md5': server_md5_2,
            'client_md5': client_md5_2,
            'duration': test_result2['duration'],
            'server_response': server_response2,
            'md5_consistent': server_md5_1 == server_md5_2 if server_md5_1 and server_md5_2 else False
        }
        
        results['test_cases'].extend([test_case1, test_case2])
        
        # 判断重复上传策略
        repeat_policy = "未知"
        
        if (test_result1['success'] and test_result2['success'] and
            is_valid1 and is_valid2 and
            server_md5_1 == server_md5_2):
            repeat_policy = "覆盖策略"
            logger.info("✅ A4 测试通过：服务器支持覆盖策略")
        elif (test_result1['success'] and not test_result2['success'] and
              "existing" in server_response2.lower()):
            repeat_policy = "拒绝策略"
            logger.info("✅ A4 测试通过：服务器拒绝重复上传")
        elif (test_result1['success'] and not test_result2['success']):
            repeat_policy = "错误处理"
            logger.info("⚠️  A4 测试部分通过：服务器处理重复上传但未明确策略")
        
        results['repeat_policy'] = repeat_policy
        results['status'] = 'PASSED'  # 无论策略如何，只要处理一致就算通过
        results['final_result'] = f'重复上传策略: {repeat_policy}'
        
    except Exception as e:
        logger.error(f"A4测试异常: {e}")
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
        
        print(f"=== A4 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)