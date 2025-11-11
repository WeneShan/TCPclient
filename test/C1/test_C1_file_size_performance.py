#!/usr/bin/env python3
"""
C1 - 不同文件大小的上传耗时（扩展性）
测试文件大小对上传时间的影响：1KB, 100KB, 1MB, 10MB, 50MB
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
    print("=== C1 测试：不同文件大小的上传耗时（扩展性） ===")
    
    # 初始化测试
    test_name = "C1"
    logger = TestLogger(test_name)
    client_tester = ClientTester(test_name)
    results = {
        'test_name': test_name,
        'test_description': '不同文件大小的上传耗时测试',
        'start_time': datetime.now().isoformat(),
        'test_cases': [],
        'performance_summary': {}
    }
    
    # 测试文件大小配置（字节）
    test_file_sizes = [
        (1024, "1KB"),
        (100 * 1024, "100KB"), 
        (1024 * 1024, "1MB"),
        (10 * 1024 * 1024, "10MB"),
        (50 * 1024 * 1024, "50MB")
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
        
        # 对每种文件大小进行测试
        for size_bytes, size_name in test_file_sizes:
            logger.info(f"开始测试文件大小: {size_name}")
            
            test_results = []
            
            # 每个大小测试多次求平均值
            for i in range(TestConfig.TEST_RETRY_COUNT):
                logger.info(f"第 {i+1}/{TestConfig.TEST_RETRY_COUNT} 次测试")
                
                # 创建测试文件
                test_file = FileManager.create_test_file(size_bytes, f"test_{size_name.lower()}_{i}.bin")
                
                if not test_file.exists():
                    logger.error(f"测试文件创建失败: {size_name}")
                    continue
                
                # 计算本地文件MD5
                local_md5 = FileManager.calculate_md5(test_file)
                
                # 运行上传测试
                start_time = time.time()
                upload_result = client_tester.run_upload_test(test_file.name)
                end_time = time.time()
                
                if upload_result:
                    duration = upload_result['duration']
                    goodput = size_bytes / (duration * 1024 * 1024)  # MB/s
                    
                    # 验证文件完整性
                    is_valid, server_md5, client_md5 = client_tester.verify_file_integrity(test_file.name)
                    
                    test_result = {
                        'iteration': i + 1,
                        'file_size': size_bytes,
                        'file_size_name': size_name,
                        'duration': duration,
                        'goodput_mbps': goodput,
                        'local_md5': local_md5,
                        'server_md5': server_md5,
                        'client_md5': client_md5,
                        'file_integrity': is_valid,
                        'upload_success': upload_result['success']
                    }
                    
                    test_results.append(test_result)
                    logger.info(f"{size_name} - 迭代 {i+1}: {duration:.2f}s, Goodput: {goodput:.2f}MB/s")
                
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
                
                # 记录文件大小的性能摘要
                size_summary = {
                    'file_size': size_bytes,
                    'file_size_name': size_name,
                    'tests_count': len(test_results),
                    'avg_duration': statistics.mean(durations) if durations else 0,
                    'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
                    'avg_goodput': statistics.mean(goodputs) if goodputs else 0,
                    'std_goodput': statistics.stdev(goodputs) if len(goodputs) > 1 else 0,
                    'success_rate': success_rate,
                    'md5_consistency_rate': md5_consistency_rate
                }
                
                results['performance_summary'][size_name] = size_summary
                
                # 将详细结果添加到测试用例中
                for result in test_results:
                    results['test_cases'].append({
                        'test_type': 'file_size_performance',
                        **result,
                        'summary_info': size_summary
                    })
                
                logger.info(f"{size_name} 性能摘要:")
                logger.info(f"  平均耗时: {size_summary['avg_duration']:.2f}±{size_summary['std_duration']:.2f}s")
                logger.info(f"  平均吞吐量: {size_summary['avg_goodput']:.2f}±{size_summary['std_goodput']:.2f}MB/s")
                logger.info(f"  成功率: {success_rate:.1%}")
                logger.info(f"  MD5一致性: {md5_consistency_rate:.1%}")
        
        # 分析整体性能趋势
        performance_analysis = analyze_performance_trends(results['performance_summary'])
        results['performance_analysis'] = performance_analysis
        
        # 判断测试结果
        all_sizes_passed = all(
            summary['success_rate'] >= 0.8 and summary['md5_consistency_rate'] >= 0.8 
            for summary in results['performance_summary'].values()
        )
        
        if all_sizes_passed and len(results['performance_summary']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = '文件大小扩展性测试通过'
        else:
            results['status'] = 'FAILED'
            results['final_result'] = '某些文件大小的上传性能不符合预期'
        
    except Exception as e:
        logger.error(f"C1测试异常: {e}")
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
        
        print(f"=== C1 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

def analyze_performance_trends(performance_summary):
    """分析性能趋势"""
    if not performance_summary:
        return {}
    
    sizes = list(performance_summary.keys())
    goodputs = [performance_summary[size]['avg_goodput'] for size in sizes]
    
    analysis = {
        'size_order': sizes,
        'goodput_trend': 'stable',
        'observations': []
    }
    
    # 检查goodput趋势
    if len(goodputs) >= 2:
        if all(abs(goodputs[i] - goodputs[0]) / goodputs[0] < 0.3 for i in range(1, len(goodputs))):
            analysis['goodput_trend'] = 'stable'
            analysis['observations'].append('吞吐量在不同文件大小下保持相对稳定')
        elif goodputs[-1] > goodputs[0]:
            analysis['goodput_trend'] = 'improving'
            analysis['observations'].append('大文件传输的吞吐量相对较高')
        else:
            analysis['goodput_trend'] = 'degrading'
            analysis['observations'].append('大文件传输的吞吐量相对较低')
    
    return analysis

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)