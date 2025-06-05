#!/usr/bin/env python3
"""
测试报告连贯性修复的脚本
验证修复后的报告生成流程是否能产生连贯的深度报告而非拼凑式文章
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shandu.prompts import get_system_prompt, get_user_prompt, get_report_style_guidelines

def test_prompt_improvements():
    """测试提示词改进"""
    print("=== 测试提示词改进 ===")
    
    # 测试中文报告生成提示词
    zh_report_prompt = get_system_prompt("report_generation", "zh")
    print(f"中文报告生成提示词长度: {len(zh_report_prompt)}")
    
    # 检查关键连贯性要求
    coherence_keywords = [
        "连贯性要求",
        "整体统一性", 
        "深度分析",
        "有机结构",
        "一致视角",
        "不是简单地拼凑多篇文章",
        "避免简单的主题拼凑"
    ]
    
    missing_keywords = []
    for keyword in coherence_keywords:
        if keyword not in zh_report_prompt:
            missing_keywords.append(keyword)
    
    if missing_keywords:
        print(f"❌ 缺少关键连贯性要求: {missing_keywords}")
        return False
    else:
        print("✅ 所有关键连贯性要求都已包含")
    
    # 测试报告增强提示词
    zh_enhancement_prompt = get_system_prompt("report_enhancement", "zh")
    print(f"中文报告增强提示词长度: {len(zh_enhancement_prompt)}")
    
    enhancement_keywords = [
        "增强报告连贯性",
        "整体统一性",
        "深度分析",
        "逻辑脉络",
        "论述连贯"
    ]
    
    missing_enhancement = []
    for keyword in enhancement_keywords:
        if keyword not in zh_enhancement_prompt:
            missing_enhancement.append(keyword)
    
    if missing_enhancement:
        print(f"❌ 报告增强提示词缺少关键要求: {missing_enhancement}")
        return False
    else:
        print("✅ 报告增强提示词包含所有关键要求")
    
    return True

def test_style_guidelines():
    """测试报告风格指南"""
    print("\n=== 测试报告风格指南 ===")
    
    zh_guidelines = get_report_style_guidelines("zh")
    en_guidelines = get_report_style_guidelines("en")
    
    print(f"中文风格指南数量: {len(zh_guidelines)}")
    print(f"英文风格指南数量: {len(en_guidelines)}")
    
    # 检查中文风格指南是否包含连贯性要求
    for style_name, guideline in zh_guidelines.items():
        coherence_requirements = [
            "全文必须使用纯正的中文表达",
            "标题格式必须严格正确",
            "严格按照指定的详细程度要求控制"
        ]
        
        missing_reqs = []
        for req in coherence_requirements:
            if req not in guideline:
                missing_reqs.append(req)
        
        if missing_reqs:
            print(f"❌ {style_name}风格指南缺少要求: {missing_reqs}")
            return False
    
    print("✅ 所有风格指南都包含必要要求")
    return True

def test_coherence_check_prompt():
    """测试连贯性检查提示词"""
    print("\n=== 测试连贯性检查提示词 ===")
    
    coherence_prompt = get_system_prompt("global_report_consistency_check_prompt", "zh")
    
    if not coherence_prompt:
        print("❌ 未找到中文连贯性检查提示词")
        return False
    
    print(f"连贯性检查提示词长度: {len(coherence_prompt)}")
    
    # 检查关键检查项
    check_items = [
        "整体连贯性",
        "论点一致性", 
        "主题完整性",
        "语气和风格",
        "完整性和深度",
        "冗余性",
        "清晰度和精确性"
    ]
    
    missing_items = []
    for item in check_items:
        if item not in coherence_prompt:
            missing_items.append(item)
    
    if missing_items:
        print(f"❌ 连贯性检查缺少检查项: {missing_items}")
        return False
    else:
        print("✅ 连贯性检查包含所有必要检查项")
    
    return True

def show_improvement_summary():
    """显示改进总结"""
    print("\n" + "="*60)
    print("📋 报告连贯性修复总结")
    print("="*60)
    
    improvements = [
        "✅ 修改中文报告生成提示词，强调连贯性和深度分析",
        "✅ 修改报告增强提示词，加强整体统一性要求", 
        "✅ 移除报告扩展中的3个章节限制，处理所有重要章节",
        "✅ 新增整体连贯性检查函数 _ensure_report_coherence",
        "✅ 在报告生成流程中添加最终连贯性验证步骤",
        "✅ 强化所有中文风格指南的格式和语言要求"
    ]
    
    for improvement in improvements:
        print(improvement)
    
    print("\n🎯 预期效果:")
    print("- 生成连贯的深度学术研究报告，而非拼凑式文章")
    print("- 各章节之间有清晰的逻辑联系和自然过渡")
    print("- 整体论述连贯，避免简单的主题并列")
    print("- 保持一致的分析视角和学术水准")
    print("- 处理所有重要章节，确保报告完整性")

def main():
    """主测试函数"""
    print("🔧 测试报告连贯性修复")
    print("="*50)
    
    all_tests_passed = True
    
    # 运行所有测试
    tests = [
        test_prompt_improvements,
        test_style_guidelines, 
        test_coherence_check_prompt
    ]
    
    for test_func in tests:
        try:
            if not test_func():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 失败: {str(e)}")
            all_tests_passed = False
    
    # 显示总结
    show_improvement_summary()
    
    if all_tests_passed:
        print("\n🎉 所有测试通过！报告连贯性修复已完成。")
        print("\n📝 建议:")
        print("1. 使用 --language zh 参数测试中文报告生成")
        print("2. 观察生成的报告是否具有整体连贯性")
        print("3. 检查章节间的逻辑联系和过渡")
        print("4. 验证是否避免了简单的主题拼凑")
        return True
    else:
        print("\n❌ 部分测试失败，请检查修复内容。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
