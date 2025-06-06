#!/usr/bin/env python3
"""
测试优化的迭代扩展算法
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shandu.agents.processors.report_generator import (
    advanced_iterative_expansion,
    force_word_count_compliance,
    count_chinese_and_english_chars,
    get_word_count_requirements,
    validate_report_quality
)
from langchain_openai import ChatOpenAI
from shandu.config import config

async def test_optimized_expansion():
    """测试优化的迭代扩展算法"""
    
    print("🚀 测试优化的迭代扩展算法")
    print("=" * 60)
    
    # 读取当前报告
    report_path = "output/xiyou_report.md"
    if not os.path.exists(report_path):
        print(f"❌ 报告文件不存在: {report_path}")
        return
    
    with open(report_path, 'r', encoding='utf-8') as f:
        current_report = f.read()
    
    # 统计当前字数
    current_chars = count_chinese_and_english_chars(current_report)
    print(f"📊 当前报告字数: {current_chars}")
    
    # 设置测试参数
    detail_level = "detailed"
    requirements = get_word_count_requirements(detail_level)
    target_chars = 15000  # 设置更高的目标
    
    print(f"🎯 目标字数: {target_chars}")
    print(f"📋 详细级别要求: {requirements}")
    
    # 初始化LLM
    api_config = config.get_section("api")
    llm = ChatOpenAI(
        base_url=api_config.get("base_url"),
        api_key=api_config.get("api_key"),
        model=api_config.get("model", "gpt-4o"),
        temperature=0.6,
        max_tokens=120000
    )
    
    print("\n🔬 测试1: 直接使用优化迭代扩展算法")
    print("-" * 40)
    
    try:
        expanded_report_v1 = await advanced_iterative_expansion(
            llm=llm,
            report_content=current_report,
            target_chars=target_chars,
            max_iterations=6,
            language="zh"
        )
        
        expanded_chars_v1 = count_chinese_and_english_chars(expanded_report_v1)
        improvement_v1 = expanded_chars_v1 - current_chars
        
        print(f"✅ 直接迭代扩展结果:")
        print(f"   - 扩展前: {current_chars} 字")
        print(f"   - 扩展后: {expanded_chars_v1} 字")
        print(f"   - 提升: +{improvement_v1} 字 ({improvement_v1/current_chars*100:.1f}%)")
        print(f"   - 目标完成度: {expanded_chars_v1/target_chars*100:.1f}%")
        
        # 保存测试结果
        test_output_v1 = "output/xiyou_report_optimized_v1.md"
        with open(test_output_v1, 'w', encoding='utf-8') as f:
            f.write(expanded_report_v1)
        print(f"💾 结果已保存到: {test_output_v1}")
        
    except Exception as e:
        print(f"❌ 直接迭代扩展失败: {e}")
        expanded_report_v1 = current_report
        expanded_chars_v1 = current_chars
    
    print("\n🔬 测试2: 使用集成的强制字数控制")
    print("-" * 40)
    
    try:
        expanded_report_v2 = await force_word_count_compliance(
            llm=llm,
            report_content=current_report,
            detail_level=detail_level,
            language="zh"
        )
        
        expanded_chars_v2 = count_chinese_and_english_chars(expanded_report_v2)
        improvement_v2 = expanded_chars_v2 - current_chars
        
        print(f"✅ 强制字数控制结果:")
        print(f"   - 扩展前: {current_chars} 字")
        print(f"   - 扩展后: {expanded_chars_v2} 字")
        print(f"   - 提升: +{improvement_v2} 字 ({improvement_v2/current_chars*100:.1f}%)")
        print(f"   - 目标完成度: {expanded_chars_v2/target_chars*100:.1f}%")
        
        # 保存测试结果
        test_output_v2 = "output/xiyou_report_optimized_v2.md"
        with open(test_output_v2, 'w', encoding='utf-8') as f:
            f.write(expanded_report_v2)
        print(f"💾 结果已保存到: {test_output_v2}")
        
    except Exception as e:
        print(f"❌ 强制字数控制失败: {e}")
        expanded_report_v2 = current_report
        expanded_chars_v2 = current_chars
    
    print("\n📊 对比分析")
    print("-" * 40)
    
    # 选择最佳结果
    if expanded_chars_v1 > expanded_chars_v2:
        best_report = expanded_report_v1
        best_chars = expanded_chars_v1
        best_method = "直接迭代扩展"
    else:
        best_report = expanded_report_v2
        best_chars = expanded_chars_v2
        best_method = "强制字数控制"
    
    print(f"🏆 最佳方法: {best_method}")
    print(f"📈 最佳字数: {best_chars}")
    print(f"🎯 目标达成: {best_chars/target_chars*100:.1f}%")
    
    # 质量验证
    validation = validate_report_quality(best_report, detail_level)
    print(f"\n🔍 质量验证:")
    print(f"   - 是否达标: {validation['is_valid']}")
    print(f"   - 总字数: {validation['analysis']['total_chars']}")
    print(f"   - 章节数: {len(validation['analysis']['sections'])}")
    
    if validation['issues']:
        print(f"   - 问题: {validation['issues']}")
    if validation['warnings']:
        print(f"   - 警告: {validation['warnings']}")
    
    # 如果最佳结果比当前报告更好，则更新
    if best_chars > current_chars:
        print(f"\n💾 更新主报告文件...")
        
        # 备份当前报告
        backup_path = "output/xiyou_report_backup_optimized.md"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(current_report)
        print(f"📦 原报告已备份到: {backup_path}")
        
        # 更新主报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(best_report)
        print(f"✅ 主报告已更新: {report_path}")
        
        improvement = best_chars - current_chars
        print(f"🎉 优化完成! 字数提升 {improvement} 字 ({improvement/current_chars*100:.1f}%)")
    else:
        print(f"\n⚠️ 优化效果不明显，保持原报告不变")
    
    print("\n" + "=" * 60)
    print("🏁 测试完成")

if __name__ == "__main__":
    asyncio.run(test_optimized_expansion())
