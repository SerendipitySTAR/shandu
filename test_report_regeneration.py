#!/usr/bin/env python3
"""
测试报告重新生成，确保字数达到要求
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
    get_word_count_requirements,
    validate_report_quality
)
from langchain_openai import ChatOpenAI
from shandu.config import config

async def test_report_regeneration():
    """测试报告重新生成"""
    
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
    
    # 获取详细级别的要求
    detail_level = "detailed"  # 根据用户偏好
    requirements = get_word_count_requirements(detail_level)
    print(f"📋 字数要求: {requirements}")
    
    # 验证报告质量
    validation = validate_report_quality(current_report, detail_level)
    print(f"🔍 报告质量验证:")
    print(f"  - 是否达标: {validation['is_valid']}")
    print(f"  - 问题: {validation['issues']}")
    print(f"  - 警告: {validation['warnings']}")
    
    if current_chars < requirements['total_min']:
        print(f"🚨 字数不足，开始强制扩展...")
        
        # 初始化LLM
        api_config = config.get_section("api")
        llm = ChatOpenAI(
            base_url=api_config.get("base_url"),
            api_key=api_config.get("api_key"),
            model=api_config.get("model", "gpt-4o"),
            temperature=0.6,
            max_tokens=120000
        )
        
        # 强制字数扩展
        expanded_report = await force_word_count_compliance(
            llm=llm,
            report_content=current_report,
            detail_level=detail_level,
            language="zh"
        )
        
        # 统计扩展后字数
        expanded_chars = count_chinese_and_english_chars(expanded_report)
        print(f"✅ 扩展后字数: {expanded_chars}")
        
        # 保存扩展后的报告
        backup_path = "output/xiyou_report_backup.md"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(current_report)
        print(f"💾 原报告已备份到: {backup_path}")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(expanded_report)
        print(f"💾 扩展后报告已保存到: {report_path}")
        
        # 重新验证
        final_validation = validate_report_quality(expanded_report, detail_level)
        print(f"🔍 最终验证:")
        print(f"  - 是否达标: {final_validation['is_valid']}")
        print(f"  - 问题: {final_validation['issues']}")
        print(f"  - 警告: {final_validation['warnings']}")
        
    else:
        print(f"✅ 报告字数已达标，无需扩展")

if __name__ == "__main__":
    asyncio.run(test_report_regeneration())
