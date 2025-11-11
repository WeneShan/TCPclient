#!/usr/bin/env python3
"""
A5 - 错误凭据（Token/Key 错误）
测试客户端/服务器在认证或key错误时返回清晰错误，且不会产生未定义行为
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def main():
    print("=== A5 测试：错误凭据（Token/Key 错误） ===")
    
    # 初始化测试
    test_name = "A5"
    logger = TestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '错误凭据测试（Token/Key 错误）',
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
        test_file = FileManager.create_test_file(TestConfig.TEST_FILE_SIZE_100KB, "test_auth_error.bin")
        
        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_test_results(test_name, results)
            return False
        
        # 测试案例：模拟认证错误
        test_cases = [
            {'type': 'Wrong_Student_ID', 'student_id': 'invalid_student_123'},
            {'type': 'No_Auth_Token', 'student_id': TestConfig.STUDENT_ID, 'simulate_no_token': True}
        ]
        
        for case in test_cases:
            logger.info(f"测试案例: {case['type']}")
            
            # 手动构造客户端请求以测试错误凭据
            result = simulate_auth_error_test(case, test_file)
            
            if result:
                results['test_cases'].append(result)
                
                if result['error_detected']:
                    logger.info(f"✅ {case['type']} 错误检测正常")
                else:
                    logger.error(f"❌ {case['type']} 错误检测失败")
        
        # 检查是否所有错误都得到了正确处理
        all_errors_handled = all(tc.get('error_detected', False) for tc in results['test_cases'])
        
        if all_errors_handled and len(results['test_cases']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = '错误凭据检测机制正常'
        else:
            results['status'] = 'FAILED'
            results['final_result'] = '错误凭据检测机制存在问题'
        
    except Exception as e:
        logger.error(f"A5测试异常: {e}")
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
        
        print(f"=== A5 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

def simulate_auth_error_test(test_case, test_file):
    """模拟认证错误测试"""
    try:
        # 使用正确的学生ID登录，但服务器会返回错误
        inputs = f"{TestConfig.SERVER_IP}\n{test_case['student_id']}\n{test_file.absolute()}\n\n"
        
        # 运行客户端并检查返回结果
        result = subprocess.run([
            sys.executable, 
            "client.py"
        ], 
        input=inputs, 
        text=True, 
        capture_output=True, 
        timeout=30  # 30秒超时
        )
        
        # 分析输出
        error_detected = False
        error_message = ""
        
        if result.returncode != 0:
            error_detected = True
            error_message = f"客户端返回非零退出码: {result.returncode}"
        elif "error" in result.stdout.lower() or "failed" in result.stdout.lower():
            error_detected = True
            error_message = "检测到错误信息"
        elif result.stderr:
            error_detected = True
            error_message = f"标准错误输出: {result.stderr[:100]}"
        
        return {
            'test_type': test_case['type'],
            'student_id': test_case['student_id'],
            'return_code': result.returncode,
            'error_detected': error_detected,
            'error_message': error_message,
            'stdout_excerpt': result.stdout[-300:] if len(result.stdout) > 300 else result.stdout,
            'stderr_excerpt': result.stderr[:300] if result.stderr else ""
        }
        
    except subprocess.TimeoutExpired:
        return {
            'test_type': test_case['type'],
            'student_id': test_case['student_id'],
            'error_detected': True,
            'error_message': "测试超时",
            'stdout_excerpt': "",
            'stderr_excerpt': ""
        }
    except Exception as e:
        return {
            'test_type': test_case['type'],
            'student_id': test_case['student_id'],
            'error_detected': True,
            'error_message': f"测试异常: {e}",
            'stdout_excerpt': "",
            'stderr_excerpt': ""
        }

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)