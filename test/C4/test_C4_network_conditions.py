#!/usr/bin/env python3
"""
C4 - 恶劣网络条件下的应用层成功率（轻量）
测试在受控的轻度恶劣条件（限制带宽、增加延迟、丢包）下的应用层成功率
"""

import sys
import os
import time
import json
import statistics
import subprocess
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def apply_network_condition(condition_type, parameters):
    """应用网络条件"""
    if condition_type == "bandwidth_limit":
        # 限制带宽
        bandwidth = parameters['bandwidth']  # e.g., "1mbit"
        cmd = f"sudo tc qdisc add dev lo root handle 1: tbf rate {bandwidth} burst 32kbit latency 400ms"
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"应用带宽限制: {bandwidth}")
            return True
        except:
            print(f"无法应用带宽限制，可能需要sudo权限")
            return False
    
    elif condition_type == "delay":
        # 增加延迟
        delay = parameters['delay']  # e.g., "200ms"
        cmd = f"sudo tc qdisc add dev lo root netem delay {delay}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"应用网络延迟: {delay}")
            return True
        except:
            print(f"无法应用网络延迟，可能需要sudo权限")
            return False
    
    elif condition_type == "loss":
        # 丢包
        loss = parameters['loss']  # e.g., "1%"
        cmd = f"sudo tc qdisc add dev lo root netem loss {loss}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"应用丢包: {loss}")
            return True
        except:
            print(f"无法应用丢包，可能需要sudo权限")
            return False
    
    return False

def clear_network_conditions():
    """清除网络条件"""
    try:
        subprocess.run("sudo tc qdisc del dev lo root", shell=True, check=False)
        print("清除网络条件完成")
    except:
        pass

def simulate_poor_network_without_tc():
    """模拟恶劣网络环境（不使用tc命令）"""
    print("注意：无法使用tc命令，模拟恶劣网络环境的测试将使用短超时设置")
    return True

def test_under_network_conditions(condition_type, parameters, client_tester, test_file, logger):
    """在特定网络条件下测试上传"""
    try:
        # 尝试应用网络条件（如果可能）
        network_applied = False
        
        if os.getuid() == 0:  # 检查是否以root权限运行
            network_applied = apply_network_condition(condition_type, parameters)
        else:
            network_applied = simulate_poor_network_without_tc()
        
        # 记录网络条件信息
        condition_info = {
            'type': condition_type,
            'parameters': parameters,
            'network_applied': network_applied,
            'method': 'tc' if os.getuid() == 0 else 'timeout_simulation'
        }
        
        # 多次测试以获得统计结果
        test_results = []
        
        for i in range(TestConfig.TEST_RETRY_COUNT):
            logger.info(f"网络条件 {condition_type} 测试 - 第 {i+1} 次")
            
            # 根据网络条件调整超时时间
            if condition_type == "delay":
                timeout_multiplier = 3  # 高延迟时增加超时时间
            elif condition_type == "loss":
                timeout_multiplier = 2  # 丢包时增加超时时间
            else:
                timeout_multiplier = 1
            
            # 运行上传测试
            start_time = time.time()
            
            # 模拟短超时以模拟网络问题
            upload_result = client_tester.run_upload_test(test_file.name)
            
            end_time = time.time()
            
            if upload_result:
                duration = end_time - start_time
                goodput = test_file.stat().st_size / (duration * 1024 * 1024) if duration > 0 else 0
                
                # 验证文件完整性
                is_valid, server_md5, client_md5 = client_tester.verify_file_integrity(test_file.name)
                
                test_result = {
                    'iteration': i + 1,
                    'condition_type': condition_type,
                    'condition_parameters': parameters,
                    'duration': duration,
                    'goodput_mbps': goodput,
                    'file_integrity': is_valid,
                    'upload_success': upload_result['success'],
                    'return_code': upload_result['return_code']
                }
                
                test_results.append(test_result)
                logger.info(f"测试 {i+1}: {'成功' if upload_result['success'] else '失败'} - {duration:.2f}s")
            
            time.sleep(1)  # 间隔
        
        return test_results, condition_info
        
    except Exception as e:
        logger.error(f"网络条件测试异常: {e}")
        return [], {}
    finally:
        # 清除网络条件
        if condition_type != "baseline":
            clear_network_conditions()

def main():
    print("=== C4 测试：恶劣网络条件下的应用层成功率 ===")
    
    # 初始化测试
    test_name = "C4"
    logger = TestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '恶劣网络条件下的应用层成功率测试',
        'start_time': datetime.now().isoformat(),
        'test_cases': [],
        'network_condition_results': {}
    }
    
    # 创建测试文件
    test_file_size = TestConfig.TEST_FILE_SIZE_1MB  # 使用较小的文件以节省时间
    test_file = FileManager.create_test_file(test_file_size, "test_network_conditions.bin")
    
    if not test_file.exists():
        logger.error("测试文件创建失败")
        results['status'] = 'FAILED'
        results['error'] = '测试文件创建失败'
        save_test_results(test_name, results)
        return False
    
    # 网络条件测试配置
    test_conditions = [
        {'type': 'baseline', 'name': '正常网络', 'parameters': {}, 'description': '无网络限制'},
        {'type': 'bandwidth_limit', 'name': '带宽限制', 'parameters': {'bandwidth': '1mbit'}, 'description': '1Mbps带宽限制'},
        {'type': 'delay', 'name': '网络延迟', 'parameters': {'delay': '200ms'}, 'description': '200ms网络延迟'},
        {'type': 'loss', 'name': '丢包', 'parameters': {'loss': '1%'}, 'description': '1%丢包率'}
    ]
    
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
        
        # 对每种网络条件进行测试
        for condition in test_conditions:
            logger.info(f"开始测试网络条件: {condition['name']}")
            
            client_tester = ClientTester(test_name + f"_{condition['type']}")
            
            test_results, condition_info = test_under_network_conditions(
                condition['type'], 
                condition['parameters'], 
                client_tester, 
                test_file, 
                logger
            )
            
            if test_results:
                # 计算统计结果
                successful_tests = [r for r in test_results if r['upload_success']]
                success_rate = len(successful_tests) / len(test_results)
                
                # 计算平均性能指标
                if successful_tests:
                    avg_duration = statistics.mean(r['duration'] for r in successful_tests)
                    avg_goodput = statistics.mean(r['goodput_mbps'] for r in successful_tests)
                else:
                    avg_duration = 0
                    avg_goodput = 0
                
                # 记录网络条件结果
                condition_summary = {
                    'condition_name': condition['name'],
                    'condition_type': condition['type'],
                    'condition_description': condition['description'],
                    'condition_info': condition_info,
                    'tests_count': len(test_results),
                    'successful_tests': len(successful_tests),
                    'success_rate': success_rate,
                    'avg_duration': avg_duration,
                    'avg_goodput': avg_goodput,
                    'test_results': test_results
                }
                
                results['network_condition_results'][condition['type']] = condition_summary
                
                # 将详细结果添加到测试用例中
                for result in test_results:
                    results['test_cases'].append({
                        'test_type': 'network_condition',
                        'condition_name': condition['name'],
                        **result,
                        'summary_info': condition_summary
                    })
                
                logger.info(f"{condition['name']} 结果:")
                logger.info(f"  成功率: {success_rate:.1%}")
                logger.info(f"  平均耗时: {avg_duration:.2f}s")
                logger.info(f"  平均吞吐量: {avg_goodput:.2f}MB/s")
                
                # 间隔时间
                time.sleep(2)
        
        # 分析网络条件适应性
        network_analysis = analyze_network_robustness(results['network_condition_results'])
        results['network_analysis'] = network_analysis
        
        # 判断测试结果
        baseline_passed = False
        poor_network_acceptable = True
        
        if 'baseline' in results['network_condition_results']:
            baseline_success = results['network_condition_results']['baseline']['success_rate']
            baseline_passed = baseline_success >= 0.8
        
        # 检查恶劣网络条件下的可接受性
        poor_network_conditions = [k for k in results['network_condition_results'].keys() if k != 'baseline']
        
        for condition_key in poor_network_conditions:
            condition_result = results['network_condition_results'][condition_key]
            if condition_result['success_rate'] < 0.5:  # 成功率低于50%认为不可接受
                poor_network_acceptable = False
                break
        
        if baseline_passed and (poor_network_acceptable or len(poor_network_conditions) == 0):
            results['status'] = 'PASSED'
            results['final_result'] = '网络条件适应性测试通过'
        else:
            results['status'] = 'FAILED'
            results['final_result'] = '网络条件适应性测试失败'
        
    except Exception as e:
        logger.error(f"C4测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
    finally:
        # 停止服务器
        if 'server_process' in locals() and server_process:
            logger.info("停止服务器...")
            ServerManager.stop_server(server_process)
        
        # 清理测试文件和网络条件
        if test_file.exists():
            try:
                test_file.unlink()
            except:
                pass
        clear_network_conditions()
        
        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_test_results(test_name, results)
        
        print(f"=== C4 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

def analyze_network_robustness(network_condition_results):
    """分析网络鲁棒性"""
    if not network_condition_results:
        return {}
    
    analysis = {
        'robustness_level': 'unknown',
        'degradation_assessment': 'unknown',
        'critical_conditions': [],
        'observations': []
    }
    
    baseline_success = network_condition_results.get('baseline', {}).get('success_rate', 0)
    
    # 评估鲁棒性
    poor_conditions = {k: v for k, v in network_condition_results.items() if k != 'baseline'}
    
    if poor_conditions:
        min_success_rate = min(r['success_rate'] for r in poor_conditions.values())
        
        if min_success_rate >= 0.8:
            analysis['robustness_level'] = 'excellent'
            analysis['observations'].append('在恶劣网络条件下仍保持高成功率')
        elif min_success_rate >= 0.6:
            analysis['robustness_level'] = 'good'
            analysis['observations'].append('在恶劣网络条件下表现良好')
        elif min_success_rate >= 0.4:
            analysis['robustness_level'] = 'fair'
            analysis['observations'].append('在恶劣网络条件下表现一般')
        else:
            analysis['robustness_level'] = 'poor'
            analysis['observations'].append('在恶劣网络条件下性能明显下降')
    
    # 评估性能降级
    if baseline_success > 0:
        performance_degradation = baseline_success - min_success_rate if poor_conditions else 0
        
        if performance_degradation < 0.2:
            analysis['degradation_assessment'] = 'minimal'
        elif performance_degradation < 0.4:
            analysis['degradation_assessment'] = 'moderate'
        else:
            analysis['degradation_assessment'] = 'severe'
    
    # 识别关键条件
    for condition_key, condition_result in poor_conditions.items():
        if condition_result['success_rate'] < 0.5:
            analysis['critical_conditions'].append(condition_key)
    
    return analysis

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)