#!/usr/bin/env python3
"""
A2 - 0 字节 / 1 字节 文件上传（极小文件）
验证极小文件的处理（0B 是否允许/1B edge-case）
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test.vm_test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def main():
    print("=== A2 测试：0字节和1字节文件上传 ===")
    
    # 初始化测试
    test_name = "A2"
    logger = TestLogger(test_name)
    client_tester = ClientTester(test_name)
    results = {
        'test_name': test_name,
        'test_description': '极小文件上传测试（0字节/1字节）',
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
        
        # 测试案例
        test_cases = [
            {'file': 'empty_file.bin', 'type': '0字节', 'size': 0},
            {'file': 'one_byte_file.bin', 'type': '1字节', 'size': 1}
        ]
        
        for case in test_cases:
            logger.info(f"测试 {case['type']} 文件: {case['file']}")
            
            # 创建测试文件
            if case['size'] == 0:
                test_file = FileManager.create_empty_file(case['file'])
            else:  # 1字节
                test_file = FileManager.create_1byte_file(case['file'])
            
            if not test_file.exists():
                logger.error(f"测试文件创建失败: {case['file']}")
                continue
            
            # 计算本地文件MD5
            local_md5 = FileManager.calculate_md5(test_file)
            logger.info(f"本地文件MD5: {local_md5}")
            
            # 运行上传测试
            logger.info(f"开始上传 {case['type']} 文件...")
            test_result = client_tester.run_upload_test(case['file'])
            
            if not test_result:
                logger.error(f"上传测试执行失败: {case['file']}")
                test_case = {
                    'name': f'A2_{case["type"]}_Upload',
                    'file_size': test_file.stat().st_size,
                    'upload_success': False,
                    'upload_error': '测试执行失败'
                }
                results['test_cases'].append(test_case)
                continue
            
            # 验证文件完整性
            logger.info(f"验证 {case['type']} 文件完整性...")
            is_valid, server_md5, client_md5 = client_tester.verify_file_integrity(case['file'])
            
            # 记录测试用例结果
            test_case = {
                'name': f'A2_{case["type"]}_Upload',
                'file_type': case['type'],
                'file_size': test_result['file_size'],
                'duration': test_result['duration'],
                'local_md5': local_md5,
                'server_md5': server_md5,
                'client_md5': client_md5,
                'file_integrity': is_valid,
                'upload_success': test_result['success'],
                'return_code': test_result['return_code'],
                'stdout_excerpt': test_result['stdout'][-300:] if len(test_result['stdout']) > 300 else test_result['stdout']
            }
            
            results['test_cases'].append(test_case)
            
            # 清理测试文件
            try:
                test_file.unlink()
            except:
                pass
        
        # 分析结果
        all_passed = True
        for test_case in results['test_cases']:
            if test_case['upload_success'] and test_case.get('file_integrity', False):
                logger.info(f"✅ {test_case['name']} 通过")
            else:
                logger.error(f"❌ {test_case['name']} 失败")
                all_passed = False
        
        if all_passed and len(results['test_cases']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = '极小文件上传功能正常'
        else:
            results['status'] = 'FAILED' 
            results['final_result'] = '存在极小文件上传失败'
            
    except Exception as e:
        logger.error(f"A2测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
    finally:
        # 停止服务器
        if 'server_process' in locals() and server_process:
            logger.info("停止服务器...")
            ServerManager.stop_server(server_process)
        
        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_test_results(test_name, results)
        
        print(f"=== A2 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)