#!/usr/bin/env python3
"""
C3 - 并发客户端（低并发，最多 4 个）对应用吞吐的影响
测试1、2、4个客户端同时上传各自的10MB文件
"""

import sys
import os
import time
import json
import statistics
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime

# 添加上级目录到路径以便导入test_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import TestConfig, TestLogger, FileManager, ServerManager, ClientTester, save_test_results

def upload_worker(worker_id, test_file_name, logger):
    """并发上传工作线程"""
    try:
        client_tester = ClientTester(f"C3_worker_{worker_id}")
        
        # 计算本地文件MD5
        test_file_path = Path(f"test_data/{test_file_name}")
        if not test_file_path.exists():
            logger.error(f"工作线程 {worker_id}: 测试文件不存在")
            return None
        
        local_md5 = FileManager.calculate_md5(test_file_path)
        
        # 运行上传测试
        start_time = time.time()
        upload_result = client_tester.run_upload_test(test_file_name)
        end_time = time.time()
        
        if upload_result:
            duration = end_time - start_time
            goodput = test_file_path.stat().st_size / (duration * 1024 * 1024)
            
            # 验证文件完整性
            is_valid, server_md5, client_md5 = client_tester.verify_file_integrity(test_file_name)
            
            result = {
                'worker_id': worker_id,
                'file_name': test_file_name,
                'duration': duration,
                'goodput_mbps': goodput,
                'local_md5': local_md5,
                'server_md5': server_md5,
                'client_md5': client_md5,
                'file_integrity': is_valid,
                'upload_success': upload_result['success']
            }
            
            logger.info(f"工作线程 {worker_id}: 完成上传 - {duration:.2f}s, {goodput:.2f}MB/s")
            return result
        else:
            logger.error(f"工作线程 {worker_id}: 上传失败")
            return None
            
    except Exception as e:
        logger.error(f"工作线程 {worker_id}: 异常 {e}")
        return None

def main():
    print("=== C3 测试：并发客户端对应用吞吐的影响 ===")
    
    # 初始化测试
    test_name = "C3"
    logger = TestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '并发客户端对应用吞吐的影响测试',
        'start_time': datetime.now().isoformat(),
        'test_cases': [],
        'concurrency_results': {}
    }
    
    # 并发级别配置
    concurrency_levels = [1, 2, 4]
    test_file_size = TestConfig.TEST_FILE_SIZE_10MB
    
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
        
        # 对每种并发级别进行测试
        for concurrency in concurrency_levels:
            logger.info(f"开始测试并发级别: {concurrency}")
            
            # 创建测试文件（每个工作线程一个）
            test_files = []
            for i in range(concurrency):
                test_file_name = f"test_concurrent_{concurrency}_{i}.bin"
                test_file = FileManager.create_test_file(test_file_size, test_file_name)
                test_files.append(test_file_name)
                
                if not test_file.exists():
                    logger.error(f"测试文件创建失败: {test_file_name}")
                    break
            
            if len(test_files) != concurrency:
                continue
            
            # 清理之前的测试结果
            time.sleep(2)
            
            # 执行并发上传
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = []
                for i, test_file_name in enumerate(test_files):
                    future = executor.submit(upload_worker, i+1, test_file_name, logger)
                    futures.append(future)
                
                # 收集结果
                concurrent_results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        concurrent_results.append(result)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 分析并发结果
            if concurrent_results:
                successful_uploads = [r for r in concurrent_results if r['upload_success']]
                total_goodput = sum(r['goodput_mbps'] for r in successful_uploads)
                avg_goodput = total_goodput / len(successful_uploads) if successful_uploads else 0
                success_rate = len(successful_uploads) / len(concurrent_results)
                
                # 计算总吞吐和公平性
                max_goodput = max(r['goodput_mbps'] for r in successful_uploads) if successful_uploads else 0
                min_goodput = min(r['goodput_mbps'] for r in successful_uploads) if successful_uploads else 0
                fairness_ratio = min_goodput / max_goodput if max_goodput > 0 else 0
                
                # 记录并发结果
                concurrency_summary = {
                    'concurrency_level': concurrency,
                    'total_uploads': len(concurrent_results),
                    'successful_uploads': len(successful_uploads),
                    'success_rate': success_rate,
                    'total_duration': total_duration,
                    'total_goodput': total_goodput,
                    'avg_goodput_per_client': avg_goodput,
                    'max_goodput': max_goodput,
                    'min_goodput': min_goodput,
                    'fairness_ratio': fairness_ratio,
                    'client_results': concurrent_results
                }
                
                results['concurrency_results'][f"concurrency_{concurrency}"] = concurrency_summary
                
                # 将详细结果添加到测试用例中
                for result in concurrent_results:
                    results['test_cases'].append({
                        'test_type': 'concurrency_test',
                        'concurrency_level': concurrency,
                        **result,
                        'summary_info': concurrency_summary
                    })
                
                logger.info(f"并发级别 {concurrency} 性能摘要:")
                logger.info(f"  成功率: {success_rate:.1%}")
                logger.info(f"  总耗时: {total_duration:.2f}s")
                logger.info(f"  总吞吐: {total_goodput:.2f}MB/s")
                logger.info(f"  平均单客户端吞吐: {avg_goodput:.2f}MB/s")
                logger.info(f"  公平性比例: {fairness_ratio:.2f}")
            
            # 清理测试文件
            for test_file_name in test_files:
                test_file_path = Path(f"test_data/{test_file_name}")
                try:
                    if test_file_path.exists():
                        test_file_path.unlink()
                except:
                    pass
            
            # 等待服务器恢复
            time.sleep(3)
        
        # 分析并发性能
        concurrency_analysis = analyze_concurrency_performance(results['concurrency_results'])
        results['concurrency_analysis'] = concurrency_analysis
        
        # 判断测试结果
        all_levels_passed = all(
            summary['success_rate'] >= 0.8 and summary['fairness_ratio'] >= 0.6
            for summary in results['concurrency_results'].values()
        )
        
        if all_levels_passed and len(results['concurrency_results']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = '并发客户端性能测试通过'
        else:
            results['status'] = 'FAILED'
            results['final_result'] = '某些并发级别的性能不符合预期'
        
    except Exception as e:
        logger.error(f"C3测试异常: {e}")
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
        
        print(f"=== C3 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

def analyze_concurrency_performance(concurrency_results):
    """分析并发性能"""
    if not concurrency_results:
        return {}
    
    analysis = {
        'scalability': 'unknown',
        'fairness_assessment': 'unknown',
        'observations': []
    }
    
    # 检查可扩展性
    single_user_throughput = None
    max_concurrency = max(int(k.split('_')[1]) for k in concurrency_results.keys())
    
    for key, result in concurrency_results.items():
        if result['concurrency_level'] == 1:
            single_user_throughput = result['total_goodput']
            break
    
    if single_user_throughput:
        max_concurrency_throughput = None
        for key, result in concurrency_results.items():
            if result['concurrency_level'] == max_concurrency:
                max_concurrency_throughput = result['total_goodput']
                break
        
        if max_concurrency_throughput:
            scalability_ratio = max_concurrency_throughput / single_user_throughput
            
            if scalability_ratio >= 0.8:
                analysis['scalability'] = 'good'
                analysis['observations'].append(f'并发性能扩展良好 ({scalability_ratio:.2f}x)')
            elif scalability_ratio >= 0.5:
                analysis['scalability'] = 'fair'
                analysis['observations'].append(f'并发性能扩展一般 ({scalability_ratio:.2f}x)')
            else:
                analysis['scalability'] = 'poor'
                analysis['observations'].append(f'并发性能扩展较差 ({scalability_ratio:.2f}x)')
    
    # 评估公平性
    avg_fairness = statistics.mean(r['fairness_ratio'] for r in concurrency_results.values())
    
    if avg_fairness >= 0.8:
        analysis['fairness_assessment'] = 'excellent'
    elif avg_fairness >= 0.6:
        analysis['fairness_assessment'] = 'good'
    elif avg_fairness >= 0.4:
        analysis['fairness_assessment'] = 'fair'
    else:
        analysis['fairness_assessment'] = 'poor'
    
    analysis['avg_fairness'] = avg_fairness
    
    return analysis

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)