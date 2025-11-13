#!/usr/bin/env python3
"""
STEP协议综合测试图表生成脚本
使用matplotlib生成性能测试结果的可视化图表
"""

import os
import sys
import json
import glob
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime

def load_test_results():
    """加载所有测试结果"""
    results = {}
    
    # 扫描所有测试目录
    test_dirs = [d for d in Path('.').iterdir() if d.is_dir() and d.name.startswith(('A', 'C'))]
    
    for test_dir in test_dirs:
        results_file = test_dir / "results.json"
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    results[test_dir.name] = json.load(f)
            except Exception as e:
                print(f"警告: 无法加载 {test_dir.name} 的结果: {e}")
    
    return results

def load_comprehensive_results():
    """加载综合测试结果"""
    results = {}
    comprehensive_dir = Path("comprehensive_results")
    
    if not comprehensive_dir.exists():
        print("警告: 综合测试结果目录不存在")
        return results
    
    # 加载每个测试的汇总结果
    for summary_file in comprehensive_dir.glob("*_summary.json"):
        test_name = summary_file.stem.replace('_summary', '')
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                results[test_name] = json.load(f)
        except Exception as e:
            print(f"警告: 无法加载 {test_name} 的汇总结果: {e}")
    
    return results

def plot_functional_test_status(results):
    """绘制功能性测试状态图"""
    functional_tests = {k: v for k, v in results.items() if k.startswith('A')}
    
    if not functional_tests:
        print("警告: 没有功能性测试结果")
        return
    
    # 提取测试状态
    test_names = []
    pass_rates = []
    
    for test_name, test_data in functional_tests.items():
        if 'pass_rate' in test_data:
            test_names.append(test_name)
            pass_rates.append(test_data['pass_rate'] * 100)  # 转换为百分比
    
    if not test_names:
        return
    
    # 创建图表
    plt.figure(figsize=(10, 6))
    bars = plt.bar(test_names, pass_rates, color=['green' if rate >= 80 else 'red' for rate in pass_rates])
    
    # 添加数值标签
    for bar, rate in zip(bars, pass_rates):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{rate:.1f}%', ha='center', va='bottom')
    
    plt.title('功能性测试通过率')
    plt.xlabel('测试项目')
    plt.ylabel('通过率 (%)')
    plt.ylim(0, 110)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("comprehensive_results")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'functional_test_pass_rate.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ 功能性测试状态图已生成")

def plot_performance_comparison(results):
    """绘制性能测试对比图"""
    performance_tests = {k: v for k, v in results.items() if k.startswith('C')}
    
    if not performance_tests:
        print("警告: 没有性能测试结果")
        return
    
    # 提取性能数据
    test_data = {}
    
    for test_name, test_info in performance_tests.items():
        # 从原始测试结果加载详细性能数据
        original_results_file = Path(test_name) / "results.json"
        if original_results_file.exists():
            try:
                with open(original_results_file, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                if 'performance_summary' in original_data:
                    test_data[test_name] = original_data['performance_summary']
            except Exception as e:
                print(f"警告: 无法加载 {test_name} 的详细性能数据: {e}")
    
    if not test_data:
        return
    
    # 为每个性能测试创建图表
    for test_name, performance_data in test_data.items():
        if not performance_data:
            continue
            
        # 提取数据
        sizes = []
        goodputs = []
        durations = []
        
        for size_name, data in performance_data.items():
            sizes.append(size_name)
            goodputs.append(data.get('avg_goodput', 0))
            durations.append(data.get('avg_duration', 0))
        
        if not sizes:
            continue
        
        # 创建双Y轴图表
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # 吞吐量柱状图
        bars = ax1.bar(range(len(sizes)), goodputs, alpha=0.7, color='skyblue', label='吞吐量 (MB/s)')
        ax1.set_xlabel('文件大小')
        ax1.set_ylabel('平均吞吐量 (MB/s)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        
        # 耗时折线图
        ax2 = ax1.twinx()
        line = ax2.plot(range(len(sizes)), durations, 'ro-', linewidth=2, markersize=8, label='耗时 (s)')
        ax2.set_ylabel('平均耗时 (s)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        
        # 设置X轴标签
        plt.xticks(range(len(sizes)), sizes, rotation=45)
        
        # 添加图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.title(f'{test_name} - 性能测试结果')
        plt.tight_layout()
        
        # 保存图表
        output_dir = Path("comprehensive_results")
        plt.savefig(output_dir / f'{test_name}_performance.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ {test_name} 性能图表已生成")

def plot_test_execution_timeline(results):
    """绘制测试执行时间线"""
    functional_tests = {k: v for k, v in results.items() if k.startswith('A')}
    performance_tests = {k: v for k, v in results.items() if k.startswith('C')}
    
    if not functional_tests and not performance_tests:
        return
    
    # 创建执行时间图表
    plt.figure(figsize=(12, 8))
    
    # 功能性测试
    func_test_names = []
    func_pass_rates = []
    
    for test_name, test_data in functional_tests.items():
        if 'pass_rate' in test_data:
            func_test_names.append(test_name)
            func_pass_rates.append(test_data['pass_rate'] * 100)
    
    if func_test_names:
        plt.subplot(2, 1, 1)
        bars = plt.bar(func_test_names, func_pass_rates, 
                      color=['green' if rate >= 80 else 'orange' for rate in func_pass_rates])
        plt.title('功能性测试执行结果')
        plt.ylabel('通过率 (%)')
        plt.ylim(0, 110)
        plt.grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bar, rate in zip(bars, func_pass_rates):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{rate:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 性能测试
    perf_test_names = []
    perf_pass_rates = []
    
    for test_name, test_data in performance_tests.items():
        if 'pass_rate' in test_data:
            perf_test_names.append(test_name)
            perf_pass_rates.append(test_data['pass_rate'] * 100)
    
    if perf_test_names:
        plt.subplot(2, 1, 2)
        bars = plt.bar(perf_test_names, perf_pass_rates,
                      color=['green' if rate >= 80 else 'orange' for rate in perf_pass_rates])
        plt.title('性能测试执行结果')
        plt.ylabel('通过率 (%)')
        plt.ylim(0, 110)
        plt.grid(axis='y', alpha=0.3)
        
        # 添加数值标签
        for bar, rate in zip(bars, perf_pass_rates):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{rate:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("comprehensive_results")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'test_execution_summary.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ 测试执行时间线图表已生成")

def generate_overall_summary_chart(results):
    """生成总体汇总图表"""
    if not results:
        print("警告: 没有测试结果数据")
        return
    
    # 计算总体统计
    total_tests = len(results)
    total_passed = sum(1 for test_data in results.values() if test_data.get('pass_rate', 0) >= 0.8)
    total_failed = total_tests - total_passed
    
    # 创建汇总饼图
    plt.figure(figsize=(10, 8))
    
    # 总体通过率
    plt.subplot(2, 2, 1)
    labels = ['通过', '失败']
    sizes = [total_passed, total_failed]
    colors = ['green', 'red']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.title('总体测试通过率')
    
    # 功能性测试 vs 性能测试
    plt.subplot(2, 2, 2)
    functional_count = len([k for k in results.keys() if k.startswith('A')])
    performance_count = len([k for k in results.keys() if k.startswith('C')])
    labels = ['功能性测试', '性能测试']
    sizes = [functional_count, performance_count]
    colors = ['lightblue', 'lightcoral']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.title('测试类型分布')
    
    # 通过率分布
    plt.subplot(2, 2, 3)
    pass_rates = [test_data.get('pass_rate', 0) * 100 for test_data in results.values()]
    plt.hist(pass_rates, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
    plt.xlabel('通过率 (%)')
    plt.ylabel('测试数量')
    plt.title('通过率分布')
    plt.grid(alpha=0.3)
    
    # 测试执行统计
    plt.subplot(2, 2, 4)
    total_runs = sum(test_data.get('total_runs', 0) for test_data in results.values())
    successful_runs = sum(test_data.get('passed', 0) for test_data in results.values())
    failed_runs = total_runs - successful_runs
    
    labels = ['成功运行', '失败运行']
    sizes = [successful_runs, failed_runs]
    colors = ['lightgreen', 'lightcoral']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.title('测试运行统计')
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("comprehensive_results")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'overall_test_summary.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ 总体汇总图表已生成")

def main():
    """主函数"""
    print("STEP协议综合测试图表生成工具")
    print("=" * 50)
    
    # 检查matplotlib是否可用
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("错误: matplotlib未安装，请运行: pip install matplotlib")
        return 1
    
    # 加载结果
    print("加载测试结果...")
    comprehensive_results = load_comprehensive_results()
    
    if not comprehensive_results:
        print("警告: 未找到综合测试结果，尝试加载单个测试结果...")
        comprehensive_results = load_test_results()
    
    if not comprehensive_results:
        print("错误: 未找到任何测试结果")
        return 1
    
    print(f"加载了 {len(comprehensive_results)} 个测试结果")
    
    # 创建输出目录
    output_dir = Path("comprehensive_results")
    output_dir.mkdir(exist_ok=True)
    
    # 生成图表
    try:
        plot_functional_test_status(comprehensive_results)
        plot_performance_comparison(comprehensive_results)
        plot_test_execution_timeline(comprehensive_results)
        generate_overall_summary_chart(comprehensive_results)
        
        print("\n" + "=" * 50)
        print("所有图表生成完成！")
        print(f"图表文件保存在: {output_dir.absolute()}")
        
        # 列出生成的图表文件
        chart_files = list(output_dir.glob("*.png"))
        if chart_files:
            print("\n生成的图表文件:")
            for chart_file in chart_files:
                print(f"  - {chart_file.name}")
        
    except Exception as e:
        print(f"图表生成过程中出现错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)