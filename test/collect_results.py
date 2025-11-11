#!/usr/bin/env python3
"""
STEP协议测试结果收集和分析脚本
统一收集所有测试结果并生成分析报告
"""

import os
import sys
import json
import glob
import argparse
import statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import pandas as pd

class ResultsCollector:
    """测试结果收集器"""
    
    def __init__(self, test_dir="test"):
        self.test_dir = Path(test_dir)
        self.results = {}
        
    def collect_all_results(self):
        """收集所有测试结果"""
        print("开始收集测试结果...")
        
        # 扫描所有测试目录
        test_dirs = [d for d in self.test_dir.iterdir() if d.is_dir() and d.name.startswith(('A', 'C'))]
        
        for test_dir in test_dirs:
            self.collect_test_dir_results(test_dir)
        
        print(f"收集完成，共处理 {len(self.results)} 个测试结果")
        
    def collect_test_dir_results(self, test_dir):
        """收集单个测试目录的结果"""
        results_file = test_dir / "results.json"
        
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    test_result = json.load(f)
                    self.results[test_dir.name] = test_result
                    print(f"✓ 加载 {test_dir.name} 测试结果")
            except Exception as e:
                print(f"✗ 加载 {test_dir.name} 失败: {e}")
        else:
            print(f"! {test_dir.name} 结果文件不存在")

class ResultsAnalyzer:
    """测试结果分析器"""
    
    def __init__(self, results):
        self.results = results
        
    def generate_summary_report(self):
        """生成汇总报告"""
        summary = {
            'test_execution_time': self._get_execution_time_range(),
            'overall_status': self._get_overall_status(),
            'functional_tests': self._analyze_functional_tests(),
            'performance_tests': self._analyze_performance_tests(),
            'detailed_results': self.results
        }
        
        return summary
    
    def _get_execution_time_range(self):
        """获取测试执行时间范围"""
        start_times = []
        end_times = []
        
        for test_result in self.results.values():
            if 'start_time' in test_result:
                start_times.append(datetime.fromisoformat(test_result['start_time']))
            if 'end_time' in test_result:
                end_times.append(datetime.fromisoformat(test_result['end_time']))
        
        if not start_times or not end_times:
            return "未知"
        
        start_min = min(start_times)
        end_max = max(end_times)
        duration = end_max - start_min
        
        return {
            'start': start_min.isoformat(),
            'end': end_max.isoformat(),
            'total_duration': str(duration)
        }
    
    def _get_overall_status(self):
        """获取总体状态"""
        passed = 0
        failed = 0
        total = len(self.results)
        
        for test_result in self.results.values():
            if test_result.get('status') == 'PASSED':
                passed += 1
            elif test_result.get('status') == 'FAILED':
                failed += 1
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total if total > 0 else 0
        }
    
    def _analyze_functional_tests(self):
        """分析功能性测试"""
        functional_results = {k: v for k, v in self.results.items() if k.startswith('A')}
        
        analysis = {}
        for test_name, test_result in functional_results.items():
            analysis[test_name] = {
                'status': test_result.get('status', 'UNKNOWN'),
                'description': test_result.get('test_description', ''),
                'test_cases_count': len(test_result.get('test_cases', [])),
                'pass_rate': self._calculate_pass_rate(test_result)
            }
        
        return analysis
    
    def _analyze_performance_tests(self):
        """分析性能测试"""
        performance_results = {k: v for k, v in self.results.items() if k.startswith('C')}
        
        analysis = {}
        for test_name, test_result in performance_results.items():
            if 'performance_summary' in test_result:
                analysis[test_name] = {
                    'status': test_result.get('status', 'UNKNOWN'),
                    'description': test_result.get('test_description', ''),
                    'performance_data': test_result['performance_summary'],
                    'performance_analysis': test_result.get('performance_analysis', {})
                }
            elif 'concurrency_results' in test_result:
                analysis[test_name] = {
                    'status': test_result.get('status', 'UNKNOWN'),
                    'description': test_result.get('test_description', ''),
                    'concurrency_data': test_result['concurrency_results'],
                    'concurrency_analysis': test_result.get('concurrency_analysis', {})
                }
            elif 'network_condition_results' in test_result:
                analysis[test_name] = {
                    'status': test_result.get('status', 'UNKNOWN'),
                    'description': test_result.get('test_description', ''),
                    'network_data': test_result['network_condition_results'],
                    'network_analysis': test_result.get('network_analysis', {})
                }
        
        return analysis
    
    def _calculate_pass_rate(self, test_result):
        """计算测试通过率"""
        test_cases = test_result.get('test_cases', [])
        if not test_cases:
            return 0
        
        passed_cases = sum(1 for tc in test_cases if tc.get('upload_success', False))
        return passed_cases / len(test_cases)

class ResultsVisualizer:
    """测试结果可视化器"""
    
    def __init__(self, summary_report, output_dir="test/results"):
        self.summary = summary_report
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def create_visualization_plots(self):
        """创建可视化图表"""
        print("生成可视化图表...")
        
        # 1. 功能测试通过率饼图
        self._plot_functional_test_status()
        
        # 2. 性能测试结果图表
        self._plot_performance_results()
        
        # 3. 测试执行时间线
        self._plot_test_timeline()
        
        print(f"图表已保存到: {self.output_dir}")
    
    def _plot_functional_test_status(self):
        """绘制功能性测试状态"""
        functional_tests = self.summary['functional_tests']
        
        passed = sum(1 for test in functional_tests.values() if test['status'] == 'PASSED')
        failed = sum(1 for test in functional_tests.values() if test['status'] == 'FAILED')
        
        plt.figure(figsize=(8, 6))
        plt.pie([passed, failed], labels=['通过', '失败'], autopct='%1.1f%%', startangle=90)
        plt.title('功能性测试通过率')
        plt.axis('equal')
        plt.savefig(self.output_dir / 'functional_test_status.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_performance_results(self):
        """绘制性能测试结果"""
        performance_tests = self.summary['performance_tests']
        
        if not performance_tests:
            return
        
        # 提取性能数据
        test_names = []
        throughput_values = []
        
        for test_name, test_data in performance_tests.items():
            if 'performance_data' in test_data:
                for size, data in test_data['performance_data'].items():
                    if 'avg_goodput' in data:
                        test_names.append(f"{test_name}-{size}")
                        throughput_values.append(data['avg_goodput'])
        
        if test_names and throughput_values:
            plt.figure(figsize=(12, 6))
            plt.bar(test_names, throughput_values)
            plt.title('性能测试吞吐量对比')
            plt.xlabel('测试项目')
            plt.ylabel('平均吞吐量 (MB/s)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(self.output_dir / 'performance_throughput.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_test_timeline(self):
        """绘制测试执行时间线"""
        execution_time = self.summary['test_execution_time']
        
        if isinstance(execution_time, dict):
            # 简化的时间线图
            plt.figure(figsize=(10, 4))
            plt.text(0.5, 0.5, f"测试执行时间: {execution_time['total_duration']}", 
                    horizontalalignment='center', verticalalignment='center',
                    fontsize=12, transform=plt.gca().transAxes)
            plt.axis('off')
            plt.title('测试执行时间线')
            plt.savefig(self.output_dir / 'test_timeline.png', dpi=300, bbox_inches='tight')
            plt.close()

class HTMLReportGenerator:
    """HTML报告生成器"""
    
    def __init__(self, summary_report, output_file="test/results/test_report.html"):
        self.summary = summary_report
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(exist_ok=True)
        
    def generate_html_report(self):
        """生成HTML报告"""
        html_content = self._build_html_content()
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已生成: {self.output_file}")
    
    def _build_html_content(self):
        """构建HTML内容"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STEP协议测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ background-color: #e7f3ff; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .test-section {{ margin: 20px 0; }}
        .test-item {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .status-pass {{ background-color: #d4edda; border-color: #c3e6cb; }}
        .status-fail {{ background-color: #f8d7da; border-color: #f5c6cb; }}
        .performance-table {{ width: 100%; border-collapse: collapse; }}
        .performance-table th, .performance-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .performance-table th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>STEP协议测试报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="summary">
        <h2>测试概要</h2>
        <p><strong>总体状态:</strong> {self.summary['overall_status']['passed']}/{self.summary['overall_status']['total_tests']} 测试通过</p>
        <p><strong>通过率:</strong> {self.summary['overall_status']['pass_rate']:.1%}</p>
        {self._format_execution_time()}
    </div>

    <div class="test-section">
        <h2>功能性测试结果</h2>
        {self._format_functional_tests()}
    </div>

    <div class="test-section">
        <h2>性能测试结果</h2>
        {self._format_performance_tests()}
    </div>

    <div class="test-section">
        <h2>详细测试数据</h2>
        <p>详细的JSON格式测试数据已保存，可用于进一步分析。</p>
    </div>
</body>
</html>
        """
    
    def _format_execution_time(self):
        """格式化执行时间"""
        exec_time = self.summary['test_execution_time']
        if isinstance(exec_time, dict):
            return f"<p><strong>执行时间:</strong> {exec_time['start']} 至 {exec_time['end']} (总时长: {exec_time['total_duration']})</p>"
        return f"<p><strong>执行时间:</strong> {exec_time}</p>"
    
    def _format_functional_tests(self):
        """格式化功能性测试"""
        functional_tests = self.summary['functional_tests']
        html = ""
        
        for test_name, test_data in functional_tests.items():
            status_class = "status-pass" if test_data['status'] == 'PASSED' else "status-fail"
            html += f"""
            <div class="test-item {status_class}">
                <h3>{test_name}: {test_data['description']}</h3>
                <p><strong>状态:</strong> {test_data['status']}</p>
                <p><strong>测试用例数:</strong> {test_data['test_cases_count']}</p>
                <p><strong>通过率:</strong> {test_data['pass_rate']:.1%}</p>
            </div>
            """
        
        return html
    
    def _format_performance_tests(self):
        """格式化性能测试"""
        performance_tests = self.summary['performance_tests']
        html = ""
        
        for test_name, test_data in performance_tests.items():
            status_class = "status-pass" if test_data['status'] == 'PASSED' else "status-fail"
            html += f"""
            <div class="test-item {status_class}">
                <h3>{test_name}: {test_data['description']}</h3>
                <p><strong>状态:</strong> {test_data['status']}</p>
            """
            
            # 添加性能数据表格
            if 'performance_data' in test_data:
                html += "<table class='performance-table'><tr><th>测试项目</th><th>平均吞吐量 (MB/s)</th><th>成功率</th></tr>"
                for size, data in test_data['performance_data'].items():
                    avg_goodput = data.get('avg_goodput', 0)
                    success_rate = data.get('success_rate', 0)
                    html += f"<tr><td>{size}</td><td>{avg_goodput:.2f}</td><td>{success_rate:.1%}</td></tr>"
                html += "</table>"
            
            html += "</div>"
        
        return html

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='STEP协议测试结果收集和分析')
    parser.add_argument('--test-dir', default='test', help='测试结果目录')
    parser.add_argument('--output-dir', default='test/results', help='输出目录')
    parser.add_argument('--format', choices=['json', 'html', 'both'], default='both', help='输出格式')
    parser.add_argument('--plots', action='store_true', help='生成可视化图表')
    
    args = parser.parse_args()
    
    print("STEP协议测试结果收集和分析工具")
    print("=" * 50)
    
    # 收集结果
    collector = ResultsCollector(args.test_dir)
    collector.collect_all_results()
    
    if not collector.results:
        print("错误: 未找到测试结果文件")
        return 1
    
    # 分析结果
    analyzer = ResultsAnalyzer(collector.results)
    summary_report = analyzer.generate_summary_report()
    
    # 保存汇总报告
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    summary_file = output_dir / "summary_report.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ 汇总报告已保存: {summary_file}")
    
    # 生成可视化图表
    if args.plots:
        try:
            visualizer = ResultsVisualizer(summary_report, args.output_dir)
            visualizer.create_visualization_plots()
        except ImportError:
            print("警告: matplotlib未安装，跳过图表生成")
        except Exception as e:
            print(f"警告: 图表生成失败: {e}")
    
    # 生成HTML报告
    if args.format in ['html', 'both']:
        try:
            html_generator = HTMLReportGenerator(summary_report, output_dir / "test_report.html")
            html_generator.generate_html_report()
        except Exception as e:
            print(f"警告: HTML报告生成失败: {e}")
    
    # 打印摘要信息
    print("\n" + "=" * 50)
    print("测试结果摘要:")
    print(f"总测试数: {summary_report['overall_status']['total_tests']}")
    print(f"通过: {summary_report['overall_status']['passed']}")
    print(f"失败: {summary_report['overall_status']['failed']}")
    print(f"通过率: {summary_report['overall_status']['pass_rate']:.1%}")
    
    print(f"\n所有结果文件已保存到: {output_dir}")
    return 0 if summary_report['overall_status']['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)