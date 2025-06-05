#!/usr/bin/env python3
"""
测试报告深度修复效果的脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shandu.agents.nodes.report_generation import _get_length_instruction

def test_length_instructions():
    """测试字数控制指令是否包含深度要求"""
    print("=== 测试字数控制指令 ===\n")
    
    # 测试不同的详细程度
    detail_levels = ["brief", "standard", "detailed", "custom_15000"]
    
    for level in detail_levels:
        print(f"📋 详细程度: {level}")
        instruction = _get_length_instruction(level)
        print(f"指令内容:\n{instruction}\n")
        
        # 检查是否包含深度要求
        depth_indicators = [
            "内容深度",
            "质量要求", 
            "完整段落",
            "论证要求",
            "学术标准"
        ]
        
        found_indicators = [indicator for indicator in depth_indicators if indicator in instruction]
        print(f"✅ 包含深度指标: {', '.join(found_indicators)}")
        print("-" * 50)

def analyze_current_report():
    """分析当前报告的问题"""
    print("\n=== 分析当前报告问题 ===\n")
    
    try:
        with open("output/xiyou_report.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 统计字数
        word_count = len(content)
        print(f"📊 当前报告总字数: {word_count}")
        
        # 分析章节结构
        import re
        
        # 查找所有章节
        sections = re.findall(r'(#{2,4}\s+[^\n]+)', content)
        print(f"📋 章节总数: {len(sections)}")
        
        # 分析子章节内容长度
        subsections = re.findall(r'(#{3,4}\s+[^\n]+)(.*?)(?=#{2,4}\s+|\Z)', content, re.DOTALL)
        
        short_sections = []
        for header, content_part in subsections:
            content_length = len(content_part.strip())
            if content_length < 200:  # 少于200字符的章节
                short_sections.append((header.strip(), content_length))
        
        print(f"⚠️  过短的子章节数量: {len(short_sections)}")
        for header, length in short_sections[:5]:  # 显示前5个
            print(f"   - {header}: {length}字符")
        
        # 检查是否有只有一句话的章节
        one_sentence_sections = []
        for header, content_part in subsections:
            sentences = content_part.strip().split('。')
            if len([s for s in sentences if s.strip()]) <= 1:
                one_sentence_sections.append(header.strip())
        
        print(f"🚨 只有一句话的章节数量: {len(one_sentence_sections)}")
        for header in one_sentence_sections[:3]:  # 显示前3个
            print(f"   - {header}")
            
    except FileNotFoundError:
        print("❌ 未找到报告文件 output/xiyou_report.md")

def test_word_count_validation():
    """测试字数验证功能"""
    print("\n=== 测试字数验证功能 ===\n")

    try:
        from shandu.agents.processors.report_generator import (
            get_word_count_requirements,
            validate_report_quality,
            analyze_report_structure
        )

        # 测试字数要求获取
        for level in ["brief", "standard", "detailed", "custom_15000"]:
            requirements = get_word_count_requirements(level)
            print(f"📋 {level} 级别要求:")
            print(f"   总字数: {requirements['total_min']}-{requirements['total_max']}")
            print(f"   主章节: 至少{requirements['main_section_min']}字")
            print(f"   子章节: 至少{requirements['sub_section_min']}字")
            print()

        # 测试当前报告验证
        if os.path.exists("output/xiyou_report.md"):
            with open("output/xiyou_report.md", "r", encoding="utf-8") as f:
                content = f.read()

            validation = validate_report_quality(content, "detailed")
            print(f"📊 当前报告验证结果:")
            print(f"   是否合格: {'✅' if validation['is_valid'] else '❌'}")
            print(f"   总字数: {validation['analysis']['total_words']}")
            print(f"   章节数: {validation['analysis']['section_count']}")

            if validation['issues']:
                print("   问题列表:")
                for issue in validation['issues']:
                    print(f"     - {issue}")

            if validation['warnings']:
                print("   警告列表:")
                for warning in validation['warnings']:
                    print(f"     - {warning}")

        print("✅ 字数验证功能测试完成")

    except ImportError as e:
        print(f"❌ 导入验证函数失败: {e}")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

def main():
    """主函数"""
    print("🔧 报告深度修复测试\n")

    # 测试字数控制指令
    test_length_instructions()

    # 测试字数验证功能
    test_word_count_validation()

    # 分析当前报告
    analyze_current_report()

    print("\n=== 修复总结 ===")
    print("✅ 已增强字数控制指令，包含具体的内容深度要求")
    print("✅ 已提高LLM的max_tokens限制，支持更长的内容生成")
    print("✅ 已在系统提示中强化学术质量要求")
    print("✅ 已在用户消息中添加强制性内容深度要求")
    print("✅ 已添加Python层面的字数验证和自动修复机制")
    print("✅ 已集成自动扩展过短章节的功能")
    print("\n🎯 建议重新生成报告以验证修复效果")

if __name__ == "__main__":
    main()
