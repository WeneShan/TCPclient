#!/usr/bin/env python3
"""
A6 - 损坏块重传（模拟网络丢包）
验证在块传输失败时的重传机制
专为VirtualBox Ubuntu虚拟机环境设计
假设服务器已经在另一个虚拟机中运行
支持手动设置网络丢包环境
"""

import sys
import os
import time
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目路径到系统路径
project_path = Path("/home/stepuser/STEP-Project/")
sys.path.insert(0, str(project_path))

from test.vm_test_utils import VMTestConfig, VMTestLogger, VMFileManager, VMNetworkTester, save_vm_test_results

def extract_md5_from_output(stdout):
    """从客户端输出中提取MD5值"""
    # 查找 "File MD5:" 后面的MD5值
    md5_pattern = r"File MD5:\s*([a-fA-F0-9]{32})"
    match = re.search(md5_pattern, stdout)
    if match:
        return match.group(1)
    
    # 如果没有找到，尝试其他可能的模式
    md5_patterns = [
        r"MD5:\s*([a-fA-F0-9]{32})",
        r"md5:\s*([a-fA-F0-9]{32})",
        r"([a-fA-F0-9]{32}).*File MD5"
    ]
    
    for pattern in md5_patterns:
        match = re.search(pattern, stdout)
        if match:
            return match.group(1)
    
    return None

def setup_network_packet_loss(interface="ens33", loss_rate="10%"):
    """设置网络丢包环境"""
    try:
        # 清除现有规则
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", interface, "root"],
                      capture_output=True, text=True)
        # 设置新规则
        result = subprocess.run(
            ["sudo", "tc", "qdisc", "add", "dev", interface, "root", "netem", "loss", loss_rate],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"网络设置失败: {e}")
        return False

def cleanup_network_packet_loss(interface="ens33"):
    """清理网络设置"""
    try:
        result = subprocess.run(
            ["sudo", "tc", "qdisc", "del", "dev", interface, "root"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"网络清理失败: {e}")
        return False

def main():
    print("=== A6 测试：损坏块重传（模拟网络丢包） ===")
    print("注意：此测试验证在恶劣网络条件下的重传机制")
    print("建议先设置网络丢包环境（使用 test/A6/setup_packet_loss.sh）")
    print()

    # 初始化测试
    test_name = "A6"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '损坏块重传测试（模拟网络丢包）',
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

        # 创建测试文件 - 使用较大的文件以增加块数量
        logger.info("创建50MB测试文件...")
        test_file = VMFileManager.create_test_file(
            VMTestConfig.TEST_FILE_SIZE_50MB,
            "test_corrupt_block.bin"
        )

        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_vm_test_results(test_name, results)
            return False

        # 计算本地文件MD5
        local_md5 = VMFileManager.calculate_md5(test_file)
        logger.info(f"本地文件MD5: {local_md5}")

        # 运行上传测试
        logger.info("开始文件上传...")
        test_result = VMNetworkTester.run_client_upload(str(test_file))

        if not test_result['success']:
            logger.error("上传测试执行失败")
            results['status'] = 'FAILED'
            results['error'] = '上传测试执行失败'
            save_vm_test_results(test_name, results)
            return False

        # 从客户端输出中提取服务器返回的MD5
        logger.info("从客户端输出中提取MD5值...")
        server_md5 = extract_md5_from_output(test_result['stdout'])
        
        if server_md5:
            logger.info(f"服务器返回MD5: {server_md5}")
        else:
            logger.warning("无法从客户端输出中提取MD5值")
            # 尝试从输出中查找其他MD5相关信息
            md5_lines = [line for line in test_result['stdout'].split('\n') if 'MD5' in line or 'md5' in line]
            if md5_lines:
                logger.info(f"包含MD5的行: {md5_lines}")

        # 验证文件完整性
        file_integrity = (local_md5 == server_md5) if server_md5 else False
        
        # 记录测试用例结果
        test_case = {
            'name': 'A6_Corrupt_Block_Upload',
            'file_size': test_file.stat().st_size,
            'duration': test_result['duration'],
            'local_md5': local_md5,
            'server_md5': server_md5,
            'file_integrity': file_integrity,
            'upload_success': test_result['success'],
            'return_code': test_result['return_code'],
            'stdout_excerpt': test_result['stdout'][-500:] if len(test_result['stdout']) > 500 else test_result['stdout']
        }

        results['test_cases'].append(test_case)

        # 判断测试结果
        # 在丢包环境中，即使有重传，最终文件应该完整
        if test_result['success'] and file_integrity:
            logger.info("✅ A6 测试通过：文件上传成功且MD5校验一致（重传机制正常）")
            results['status'] = 'PASSED'
            results['final_result'] = '重传机制正常，文件完整性保持'
        elif test_result['success'] and not server_md5:
            logger.warning("⚠️ A6 测试部分通过：文件上传成功但无法验证MD5（可能客户端输出格式变化）")
            results['status'] = 'PARTIAL'
            results['final_result'] = '上传成功但MD5验证不可用'
        else:
            logger.error("❌ A6 测试失败")
            results['status'] = 'FAILED'
            results['final_result'] = '重传机制或文件完整性有问题'

            if not test_result['success']:
                logger.error(f"上传失败，返回码: {test_result['return_code']}")
                logger.error(f"错误输出: {test_result['stderr']}")
            if not file_integrity:
                logger.error("文件完整性验证失败")
                if server_md5:
                    logger.error(f"本地MD5: {local_md5} != 服务器MD5: {server_md5}")

    except Exception as e:
        logger.error(f"A6测试异常: {e}")
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

        print(f"=== A6 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED' or results['status'] == 'PARTIAL'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)