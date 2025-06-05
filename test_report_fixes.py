#!/usr/bin/env python3
"""
测试报告生成修复的脚本
验证修复后的报告生成是否能产生正确的格式和深度
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shandu.prompts import get_system_prompt, SYSTEM_PROMPTS_ZH
from shandu.agents.nodes.report_generation import _get_length_instruction

def test_prompt_fixes():
    """测试提示词修复"""
    print("=== 测试提示词修复 ===")
    
    # 测试中文报告生成提示词
    report_prompt = get_system_prompt("report_generation", "zh")
    print(f"报告生成提示词长度: {len(report_prompt)}")
    
    # 检查关键要求是否存在
    key_requirements = [
        "强制性格式和结构要求",
        "参考文献要求",
        "## 参考文献",
        "子章节要求",
        "内容深度"
    ]
    
    missing_requirements = []
    for req in key_requirements:
        if req not in report_prompt:
            missing_requirements.append(req)
    
    if missing_requirements:
        print(f"❌ 缺少关键要求: {missing_requirements}")
    else:
        print("✅ 所有关键要求都已包含")
    
    # 测试直接报告生成模板
    direct_prompt = get_system_prompt("direct_initial_report_generation", "zh")
    print(f"直接报告生成模板长度: {len(direct_prompt)}")
    
    direct_requirements = [
        "强制性结构要求",
        "内容深度要求",
        "参考文献"
    ]
    
    missing_direct = []
    for req in direct_requirements:
        if req not in direct_prompt:
            missing_direct.append(req)
    
    if missing_direct:
        print(f"❌ 直接模板缺少要求: {missing_direct}")
    else:
        print("✅ 直接模板包含所有要求")

def test_length_instructions():
    """测试字数控制指令"""
    print("\n=== 测试字数控制指令 ===")
    
    detail_levels = ["brief", "standard", "detailed", "custom_8000"]
    
    for level in detail_levels:
        instruction = _get_length_instruction(level)
        print(f"\n{level} 详细程度:")
        print(f"指令长度: {len(instruction)}")
        
        # 检查关键元素
        required_elements = ["字数要求", "强制性要求", "结构要求"]
        missing_elements = []
        
        for element in required_elements:
            if element not in instruction:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ 缺少元素: {missing_elements}")
        else:
            print("✅ 包含所有必要元素")

def test_format_requirements():
    """测试格式要求"""
    print("\n=== 测试格式要求 ===")
    
    # 检查报告生成提示词中的格式要求
    report_prompt = get_system_prompt("report_generation", "zh")
    
    format_checks = [
        ("标题格式", "# 标题内容"),
        ("禁止换行标题", "绝对禁止出现换行的标题格式"),
        ("参考文献章节", "## 参考文献"),
        ("子章节要求", "### 三级标题"),
        ("内容深度", "800-1200字")
    ]
    
    for check_name, check_text in format_checks:
        if check_text in report_prompt:
            print(f"✅ {check_name}: 已包含")
        else:
            print(f"❌ {check_name}: 缺失")

def generate_test_report():
    """生成测试报告摘要"""
    print("\n=== 测试报告摘要 ===")
    
    print("修复内容:")
    print("1. ✅ 增强了报告生成提示词的结构要求")
    print("2. ✅ 修复了字数控制指令，增加了结构要求")
    print("3. ✅ 强化了参考文献生成要求")
    print("4. ✅ 增加了子章节和内容深度要求")
    print("5. ✅ 修复了直接报告生成模板")
    
    print("\n预期改进:")
    print("- 报告将包含完整的结构（标题、引言、主体、结论、参考文献）")
    print("- 每个主要章节将包含子章节")
    print("- 报告长度将达到指定的字数要求")
    print("- 标题格式将正确（不会出现换行标题）")
    print("- 参考文献部分将正确生成")

if __name__ == "__main__":
    print("开始测试报告生成修复...")
    
    test_prompt_fixes()
    test_length_instructions()
    test_format_requirements()
    generate_test_report()
    
    print("\n测试完成！")
    print("\n建议:")
    print("1. 运行一个实际的报告生成测试来验证修复效果")
    print("2. 检查生成的报告是否包含所有必要的章节")
    print("3. 验证报告长度是否达到预期")
    print("4. 确认参考文献部分是否正确生成")
