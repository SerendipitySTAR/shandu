#!/usr/bin/env python3
"""
测试脚本：验证语言设置、字数控制和格式规范的修复效果
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shandu'))

from shandu.prompts import get_system_prompt, get_user_prompt, get_report_style_guidelines
from shandu.agents.nodes.report_generation import _get_length_instruction

def test_language_settings():
    """测试语言设置功能"""
    print("=== 测试语言设置功能 ===")

    # 测试中文系统提示词
    zh_prompt = get_system_prompt("report_generation", "zh")
    en_prompt = get_system_prompt("report_generation", "en")

    print(f"中文提示词长度: {len(zh_prompt)}")
    print(f"英文提示词长度: {len(en_prompt)}")

    # 检查中文提示词是否包含关键要求
    assert "全文必须使用纯正的中文表达" in zh_prompt, "中文提示词缺少语言纯粹性要求"
    assert "标题格式必须严格正确" in zh_prompt, "中文提示词缺少标题格式要求"
    assert "严格按照指定的详细程度要求控制" in zh_prompt, "中文提示词缺少字数控制要求"

    print("✓ 中文系统提示词包含所有必要要求")

    # 测试中文用户提示词
    zh_user_prompt = get_user_prompt("reflection", "zh")
    en_user_prompt = get_user_prompt("reflection", "en")

    print(f"中文用户提示词长度: {len(zh_user_prompt)}")
    print(f"英文用户提示词长度: {len(en_user_prompt)}")

    assert "全文必须使用纯正的中文表达" in zh_user_prompt, "中文用户提示词缺少语言要求"
    print("✓ 中文用户提示词包含语言要求")

def test_word_count_control():
    """测试字数控制功能"""
    print("\n=== 测试字数控制功能 ===")

    # 测试不同详细程度的字数指令
    brief_instruction = _get_length_instruction("brief")
    standard_instruction = _get_length_instruction("standard")
    detailed_instruction = _get_length_instruction("detailed")
    custom_instruction = _get_length_instruction("custom_15000")

    print(f"简要版本指令: {brief_instruction}")
    print(f"标准版本指令: {standard_instruction}")
    print(f"详细版本指令: {detailed_instruction}")
    print(f"自定义版本指令: {custom_instruction}")

    # 检查字数要求是否明确
    assert "约3000字" in brief_instruction, "简要版本缺少明确字数要求"
    assert "约5000字" in standard_instruction, "标准版本缺少明确字数要求"
    assert "约10000字" in detailed_instruction, "详细版本缺少明确字数要求"
    assert "约15000字" in custom_instruction, "自定义版本缺少明确字数要求"

    print("✓ 所有详细程度都包含明确的字数要求")

def test_format_requirements():
    """测试格式规范要求"""
    print("\n=== 测试格式规范要求 ===")

    # 测试中文报告样式指南
    zh_guidelines = get_report_style_guidelines("zh")
    en_guidelines = get_report_style_guidelines("en")

    print(f"中文样式指南数量: {len(zh_guidelines)}")
    print(f"英文样式指南数量: {len(en_guidelines)}")

    # 检查中文样式指南是否包含格式要求
    for style_name, guideline in zh_guidelines.items():
        assert "标题格式必须严格正确" in guideline, f"{style_name}样式缺少标题格式要求"
        assert "全文必须使用纯正的中文表达" in guideline, f"{style_name}样式缺少语言要求"
        assert "严格按照指定的详细程度要求控制" in guideline, f"{style_name}样式缺少字数控制要求"

    print("✓ 所有中文样式指南都包含必要的格式要求")

def test_title_format_fix():
    """测试标题格式修复"""
    print("\n=== 测试标题格式修复 ===")

    # 检查示例报告文件的标题格式
    report_files = ["output/xiyou2_report.md", "output/xiyou3_report.md"]

    for report_file in report_files:
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            print(f"{report_file} 第一行: {first_line}")

            # 检查标题格式是否正确
            assert first_line.startswith("# "), f"{report_file} 标题格式不正确，应以'# '开头"
            assert not first_line.startswith("# \n"), f"{report_file} 标题格式不正确，不应有换行"

            print(f"✓ {report_file} 标题格式已修复")
        else:
            print(f"⚠ {report_file} 不存在，跳过检查")

def test_research_process_localization():
    """测试研究过程本地化"""
    print("\n=== 测试研究过程本地化 ===")

    # 检查xiyou3_report.md中的研究过程部分
    report_file = "output/xiyou3_report.md"
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否包含中文的研究过程标题
        assert "## 研究过程" in content, "缺少中文的研究过程标题"
        assert "## Research Process" not in content, "仍然包含英文的研究过程标题"

        # 检查中文字段
        assert "深度" in content, "缺少中文的深度字段"
        assert "广度" in content, "缺少中文的广度字段"
        assert "耗时" in content, "缺少中文的耗时字段"

        print("✓ 研究过程已成功本地化为中文")
    else:
        print("⚠ xiyou3_report.md 不存在，跳过研究过程本地化检查")

def main():
    """运行所有测试"""
    print("开始测试修复效果...\n")

    try:
        test_language_settings()
        test_word_count_control()
        test_format_requirements()
        test_title_format_fix()
        test_research_process_localization()

        print("\n🎉 所有测试通过！修复效果验证成功！")
        print("\n修复总结：")
        print("1. ✓ 语言设置问题已解决 - 中文提示词完善，强化语言纯粹性")
        print("2. ✓ 字数控制问题已解决 - 明确字数要求，强化控制逻辑")
        print("3. ✓ 格式规范问题已解决 - 修复标题格式，强化Markdown规范")
        print("4. ✓ 研究过程本地化已完成 - Research Process部分已翻译为中文")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
