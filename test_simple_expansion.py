#!/usr/bin/env python3
"""
测试简化的迭代扩展算法
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shandu.agents.processors.report_generator import (
    force_word_count_compliance,
    count_chinese_and_english_chars,
    get_word_count_requirements
)
from langchain_openai import ChatOpenAI
from shandu.config import config

async def test_simple_expansion():
    """测试简化的扩展算法"""
    
    print("🚀 测试简化的迭代扩展算法")
    print("=" * 50)
    
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
    
    # 设置目标
    detail_level = "detailed"
    requirements = get_word_count_requirements(detail_level)
    target_chars = requirements['total_target']
    
    print(f"🎯 目标字数: {target_chars}")
    print(f"📋 需要增加: {target_chars - current_chars} 字")
    
    if current_chars >= target_chars:
        print("✅ 已达到目标字数，无需扩展")
        return
    
    # 初始化LLM
    api_config = config.get_section("api")
    llm = ChatOpenAI(
        base_url=api_config.get("base_url"),
        api_key=api_config.get("api_key"),
        model=api_config.get("model", "gpt-4o"),
        temperature=0.6,
        max_tokens=120000
    )
    
    print("\n🔧 开始强制字数扩展...")
    print("-" * 30)
    
    try:
        expanded_report = await force_word_count_compliance(
            llm=llm,
            report_content=current_report,
            detail_level=detail_level,
            language="zh"
        )
        
        expanded_chars = count_chinese_and_english_chars(expanded_report)
        improvement = expanded_chars - current_chars
        
        print(f"\n📊 扩展结果:")
        print(f"   - 扩展前: {current_chars} 字")
        print(f"   - 扩展后: {expanded_chars} 字")
        print(f"   - 提升: +{improvement} 字 ({improvement/current_chars*100:.1f}%)")
        print(f"   - 目标完成度: {expanded_chars/target_chars*100:.1f}%")
        
        if expanded_chars > current_chars:
            # 保存扩展结果
            backup_path = "output/xiyou_report_backup_simple.md"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_report)
            print(f"💾 原报告已备份到: {backup_path}")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(expanded_report)
            print(f"✅ 扩展报告已保存到: {report_path}")
            
            print(f"🎉 扩展成功! 字数提升 {improvement} 字")
        else:
            print(f"⚠️ 扩展效果不明显")
        
    except Exception as e:
        print(f"❌ 扩展失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_expansion())
