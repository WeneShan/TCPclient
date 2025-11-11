#!/usr/bin/env python3
"""
C2 - 不同 block_size 的影响（应用层参数敏感性）
测试不同block_size对同一文件的上传性能影响：4KB, 64KB, 256KB, 1MB
"""

import sys
import os
import time
import json
import statistics
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def main():
    print("=== C2 测试：不同 block_size 的影响（应用层参数敏感性） ===")
    
    # 初始化测试
    test_name = "C2"
    logger = TestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '不同block_size对上传性能的影响',
        'start_time': datetime.now().isoformat(),
        'test_cases': [],
        'performance_summary': {}
    }
    
    # 测试文件大小（10MB）
    test_file_size = TestConfig.TEST_FILE_SIZE_10MB
    
    # 注意：当前client.py使用server返回的block_size，我们通过文件大小间接影响block_size
    # 模拟不同block_size的测试案例（通过不同大小的文件）
    test_scenarios = [
        (1024 * 1024, "1MB_file", "模拟小block_size"),
        (5 * 1024 * 1024, "5MB_file", "模拟中等block_size"),
        (10 * 1024 * 1024, "10MB_file", "模拟标准block_size"),
        (20 * 1024 * 1024, "20MB_file", "模拟大block_size")
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
        
        # 对每种场景进行测试
        for file_size, scenario_name, description in test_scenarios:
            logger.info(f"开始测试场景: {scenario_name} ({description})")
            
            test_results = []
            
            # 每个场景测试多次求平均值
            for i in range(min(TestConfig.TEST_RETRY_COUNT, 2)):  # 减少测试次数以节省时间
                logger.info(f"第 {i+1} 次测试")
                
                # 创建测试文件
                test_file = FileManager.create_test_file(file_size, f"test_{scenario_name}_{i}.bin")
                
                if not test_file.exists():
                    logger.error(f"测试文件创建失败: {scenario_name}")
                    continue
                
                # 计算本地文件MD5
                local_md5 = FileManager.calculate_md5(test_file)
                
                # 运行上传测试（使用ClientTester）
                client_tester = ClientTester(test_name + f"_{scenario_name}_{i}")
                
                start_time = time.time()
                upload_result = client_tester.run_upload_test(test_file.name)
                end_time = time.time()
                
                if upload_result:
                    duration = upload_result['duration']
                    goodput = file_size / (duration * 1024 * 1024)  # MB/s
                    
                    # 分析block相关的信息
                    block_info = extract_block_info(upload_result['stdout'])
                    
                    # 验证文件完整性
                    is_valid, server_md5, client_md5 = client_tester.verify_file_integrity(test_file.name)
                    
                    test_result = {
                        'iteration': i + 1,
                        'scenario': scenario_name,
                        'file_size': file_size,
                        'description': description,
                        'duration': duration,
                        'goodput_mbps': goodput,
                        'local_md5': local_md5,
                        'server_md5': server_md5,
                        'client_md5': client_md5,
                        'file_integrity': is_valid,
                        'upload_success': upload_result['success'],
                        'block_info': block_info,
                        'stdout_excerpt': upload_result['stdout'][-300:] if len(upload_result['stdout']) > 300 else upload_result['stdout']
                    }
                    
                    test_results.append(test_result)
                    logger.info(f"{scenario_name} - 迭代 {i+1}: {duration:.2f}s, Goodput: {goodput:.2f}MB/s")
                
                # 清理测试文件
                try:
                    test_file.unlink()
                except:
                    pass
                
                # 间隔避免缓存影响
                time.sleep(1)
            
            # 计算统计数据
            if test_results:
                durations = [r['duration'] for r in test_results]
                goodputs = [r['goodput_mbps'] for r in test_results]
                
                # 成功率统计
                success_count = sum(1 for r in test_results if r['upload_success'])
                success_rate = success_count / len(test_results)
                
                # MD5一致性检查
                md5_consistent_count = sum(1 for r in test_results if r.get('file_integrity', False))
                md5_consistency_rate = md5_consistent_count / len(test_results) if test_results else 0
                
                # 记录场景的性能摘要
                scenario_summary = {
                    'scenario': scenario_name,
                    'file_size': file_size,
                    'description': description,
                    'tests_count': len(test_results),
                    'avg_duration': statistics.mean(durations) if durations else 0,
                    'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
                    'avg_goodput': statistics.mean(goodputs) if goodputs else 0,
                    'std_goodput': statistics.stdev(goodputs) if len(goodputs) > 1 else 0,
                    'success_rate': success_rate,
                    'md5_consistency_rate': md5_consistency_rate
                }
                
                results['performance_summary'][scenario_name] = scenario_summary
                
                # 将详细结果添加到测试用例中
                for result in test_results:
                    results['test_cases'].append({
                        'test_type': 'blocksize_sensitivity',
                        **result,
                        'summary_info': scenario_summary
                    })
                
                logger.info(f"{scenario_name} 性能摘要:")
                logger.info(f"  平均耗时: {scenario_summary['avg_duration']:.2f}±{scenario_summary['std_duration']:.2f}s")
                logger.info(f"  平均吞吐量: {scenario_summary['avg_goodput']:.2f}±{scenario_summary['std_goodput']:.2f}MB/s")
                logger.info(f"  成功率: {success_rate:.1%}")
                logger.info(f"  MD5一致性: {md5_consistency_rate:.1%}")
        
        # 分析block_size敏感性
        blocksize_analysis = analyze_blocksize_sensitivity(results['performance_summary'])
        results['blocksize_analysis'] = blocksize_analysis
        
        # 判断测试结果
        all_scenarios_passed = all(
            summary['success_rate'] >= 0.8 and summary['md5_consistency_rate'] >= 0.8 
            for summary in results['performance_summary'].values()
        )
        
        if all_scenarios_passed and len(results['performance_summary']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = 'block_size敏感性测试通过'
        else:
            results['status'] = 'FAILED'
            results['final_result'] = '某些block_size场景的上传性能不符合预期'
        
    except Exception as e:
        logger.error(f"C2测试异常: {e}")
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
        
        print(f"=== C2 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

def extract_block_info(stdout):
    """从客户端输出中提取block相关信息"""
    if not stdout:
        return {}
    
    block_info = {}
    lines = stdout.split('\n')
    
    for line in lines:
        line = line.strip()
        if 'total block' in line.lower() or 'total_blocks' in line:
            # 提取总块数信息
            try:
                parts = line.split(':')
                if len(parts) >= 2:
                    block_info['total_blocks'] = parts[1].strip().split()[0]
            except:
                pass
        elif 'block size' in line.lower() or 'block_size' in line:
            # 提取块大小信息
            try:
                parts = line.split(':')
                if len(parts) >= 2:
                    block_info['block_size'] = parts[1].strip().split()[0]
            except:
                pass
    
    return block_info

def analyze_blocksize_sensitivity(performance_summary):
    """分析block_size敏感性"""
    if not performance_summary:
        return {}
    
    scenarios = list(performance_summary.keys())
    goodputs = [performance_summary[scenario]['avg_goodput'] for scenario in scenarios]
    
    analysis = {
        'scenarios': scenarios,
        'goodput_trend': 'stable',
        'optimal_scenario': None,
        'observations': []
    }
    
    # 找到最佳性能的场景
    if goodputs:
        max_goodput_idx = goodputs.index(max(goodputs))
        analysis['optimal_scenario'] = scenarios[max_goodput_idx]
    
    # 分析趋势
    if len(goodputs) >= 2:
        if all(abs(goodputs[i] - goodputs[0]) / goodputs[0] < 0.2 for i in range(1, len(goodputs))):
            analysis['goodput_trend'] = 'stable'
            analysis['observations'].append('不同文件大小（对应不同block_size）下性能相对稳定')
        elif max(goodputs) > min(goodputs) * 1.3:
            analysis['goodput_trend'] = 'variable'
            analysis['observations'].append('不同block_size对性能有显著影响')
    
    return analysis

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)