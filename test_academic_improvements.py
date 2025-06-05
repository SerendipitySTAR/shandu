#!/usr/bin/env python3
"""
测试学术质量改进的脚本
验证提示词和功能是否正确实现
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shandu.prompts import get_system_prompt, get_user_prompt

def test_academic_prompts():
    """测试学术提示词改进"""
    print("=== 测试学术提示词改进 ===")
    
    # 测试中文报告生成提示词
    zh_report_prompt = get_system_prompt("report_generation", "zh")
    print(f"中文报告生成提示词长度: {len(zh_report_prompt)}")
    
    # 检查学术水平要求
    academic_keywords = [
        "达到硕士论文或学术期刊水平",
        "学术水平要求（核心标准）",
        "理论深度",
        "方法论严谨", 
        "创新性见解",
        "批判性思维",
        "学术规范",
        "学术结构要求",
        "摘要（200-300字",
        "引言（800-1200字",
        "文献综述（1000-1500字",
        "讨论与分析（800-1200字",
        "结论与展望（600-800字",
        "参考文献（至少20-30个",
        "每个主要章节至少包含1200-2000字",
        "学术品质要求"
    ]
    
    missing_keywords = []
    for keyword in academic_keywords:
        if keyword not in zh_report_prompt:
            missing_keywords.append(keyword)
    
    if missing_keywords:
        print(f"❌ 缺少关键学术要求: {missing_keywords}")
        return False
    else:
        print("✅ 所有关键学术要求都已包含")
    
    # 测试新的学术质量检查提示词
    academic_check_prompt = get_system_prompt("academic_quality_check_prompt", "zh")
    if academic_check_prompt:
        print(f"学术质量检查提示词长度: {len(academic_check_prompt)}")
        
        quality_keywords = [
            "学术质量评估标准",
            "学术结构完整性",
            "理论深度与创新性",
            "文献综述质量",
            "论证逻辑严密性",
            "研究方法科学性",
            "内容深度与广度",
            "学术语言规范性",
            "引用格式规范性",
            "硕士论文或学术期刊的质量标准"
        ]
        
        missing_quality_keywords = []
        for keyword in quality_keywords:
            if keyword not in academic_check_prompt:
                missing_quality_keywords.append(keyword)
        
        if missing_quality_keywords:
            print(f"❌ 缺少关键质量检查要求: {missing_quality_keywords}")
            return False
        else:
            print("✅ 所有关键质量检查要求都已包含")
    else:
        print("❌ 学术质量检查提示词未找到")
        return False
    
    # 测试direct_initial_report_generation提示词
    direct_prompt = get_system_prompt("direct_initial_report_generation", "zh")
    print(f"直接报告生成提示词长度: {len(direct_prompt)}")
    
    direct_keywords = [
        "达到硕士论文或学术期刊水平",
        "强制性学术结构要求",
        "学术内容深度要求",
        "每个主要章节至少1200-2000字",
        "每个子章节至少400-600字",
        "理论分析、实证研究、案例研究",
        "批判性思维和创新性见解"
    ]
    
    missing_direct_keywords = []
    for keyword in direct_keywords:
        if keyword not in direct_prompt:
            missing_direct_keywords.append(keyword)
    
    if missing_direct_keywords:
        print(f"❌ 直接生成提示词缺少关键要求: {missing_direct_keywords}")
        return False
    else:
        print("✅ 直接生成提示词包含所有关键学术要求")
    
    return True

def test_prompt_structure():
    """测试提示词结构完整性"""
    print("\n=== 测试提示词结构完整性 ===")
    
    # 检查所有必要的提示词是否存在
    required_prompts = [
        "report_generation",
        "direct_initial_report_generation", 
        "academic_quality_check_prompt",
        "global_report_consistency_check_prompt"
    ]
    
    missing_prompts = []
    for prompt_name in required_prompts:
        prompt = get_system_prompt(prompt_name, "zh")
        if not prompt:
            missing_prompts.append(prompt_name)
        else:
            print(f"✅ {prompt_name}: {len(prompt)} 字符")
    
    if missing_prompts:
        print(f"❌ 缺少必要的提示词: {missing_prompts}")
        return False
    else:
        print("✅ 所有必要的提示词都存在")
    
    return True

def test_academic_structure_requirements():
    """测试学术结构要求"""
    print("\n=== 测试学术结构要求 ===")
    
    zh_report_prompt = get_system_prompt("report_generation", "zh")
    
    # 检查学术结构要求
    structure_requirements = [
        "摘要",
        "引言", 
        "文献综述",
        "主体章节",
        "讨论与分析",
        "结论与展望",
        "参考文献"
    ]
    
    missing_structures = []
    for structure in structure_requirements:
        if structure not in zh_report_prompt:
            missing_structures.append(structure)
    
    if missing_structures:
        print(f"❌ 缺少学术结构要求: {missing_structures}")
        return False
    else:
        print("✅ 所有学术结构要求都已包含")
    
    # 检查字数要求
    word_count_requirements = [
        "200-300字",  # 摘要
        "800-1200字", # 引言
        "1000-1500字", # 文献综述
        "1200-2000字", # 主要章节
        "600-800字"   # 结论
    ]
    
    missing_word_counts = []
    for word_count in word_count_requirements:
        if word_count not in zh_report_prompt:
            missing_word_counts.append(word_count)
    
    if missing_word_counts:
        print(f"❌ 缺少字数要求: {missing_word_counts}")
        return False
    else:
        print("✅ 所有字数要求都已包含")
    
    return True

def main():
    """主测试函数"""
    print("开始测试学术质量改进...")
    
    tests = [
        test_academic_prompts,
        test_prompt_structure,
        test_academic_structure_requirements
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ 测试 {test.__name__} 失败")
        except Exception as e:
            print(f"❌ 测试 {test.__name__} 出错: {str(e)}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！学术质量改进已成功实现。")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
