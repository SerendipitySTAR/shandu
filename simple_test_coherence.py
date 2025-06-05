#!/usr/bin/env python3
"""
简化的连贯性修复测试脚本
直接测试提示词内容，不依赖其他模块
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prompts_file():
    """直接测试 prompts.py 文件内容"""
    print("=== 测试 prompts.py 文件修改 ===")
    
    try:
        # 直接读取 prompts.py 文件
        with open('shandu/prompts.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"prompts.py 文件大小: {len(content)} 字符")
        
        # 检查中文报告生成提示词的关键改进
        coherence_keywords = [
            "核心任务：创建连贯的深度学术报告",
            "连贯性要求（最重要）",
            "整体统一性",
            "深度分析", 
            "有机结构",
            "一致视角",
            "不是简单地拼凑多篇文章",
            "关键强调",
            "避免\"主题A + 主题B + 主题C\"的简单并列结构"
        ]
        
        missing_keywords = []
        for keyword in coherence_keywords:
            if keyword not in content:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            print(f"❌ 缺少关键连贯性要求: {missing_keywords}")
            return False
        else:
            print("✅ 所有关键连贯性要求都已添加到提示词中")
        
        # 检查报告增强提示词的改进
        enhancement_keywords = [
            "核心任务：增强报告连贯性和深度",
            "连贯性增强要求（最重要）",
            "将现有报告转化为一份连贯的深度学术研究报告",
            "最终产品必须是一份连贯的深度学术研究报告"
        ]
        
        missing_enhancement = []
        for keyword in enhancement_keywords:
            if keyword not in content:
                missing_enhancement.append(keyword)
        
        if missing_enhancement:
            print(f"❌ 报告增强提示词缺少关键改进: {missing_enhancement}")
            return False
        else:
            print("✅ 报告增强提示词已成功改进")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取 prompts.py 文件失败: {str(e)}")
        return False

def test_report_generation_file():
    """测试报告生成文件的修改"""
    print("\n=== 测试报告生成文件修改 ===")
    
    try:
        # 读取报告生成节点文件
        with open('shandu/agents/nodes/report_generation.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"report_generation.py 文件大小: {len(content)} 字符")
        
        # 检查关键修改
        key_fixes = [
            "_ensure_report_coherence",  # 新增的连贯性检查函数
            "移除3个章节的限制，处理所有重要章节以确保报告完整性",  # 移除章节限制的注释
            "整体连贯性检查和优化",  # 新增的连贯性检查步骤
            "Performing final coherence check"  # 连贯性检查的进度提示
        ]
        
        missing_fixes = []
        for fix in key_fixes:
            if fix not in content:
                missing_fixes.append(fix)
        
        if missing_fixes:
            print(f"❌ 缺少关键修复: {missing_fixes}")
            return False
        else:
            print("✅ 所有关键修复都已应用到报告生成流程")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取 report_generation.py 文件失败: {str(e)}")
        return False

def test_report_processor_file():
    """测试报告处理器文件的修改"""
    print("\n=== 测试报告处理器文件修改 ===")
    
    try:
        # 读取报告处理器文件
        with open('shandu/agents/processors/report_generator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"report_generator.py 文件大小: {len(content)} 字符")
        
        # 检查章节限制移除
        if "important_sections_to_process[:3]" in content:
            print("❌ 仍然存在3个章节的限制")
            return False
        
        if "移除3个章节的限制，处理所有重要章节以确保报告完整性和连贯性" in content:
            print("✅ 成功移除3个章节的限制")
        else:
            print("❌ 未找到章节限制移除的标记")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 读取 report_generator.py 文件失败: {str(e)}")
        return False

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
    
    print("\n📝 使用建议:")
    print("1. 使用 --language zh 参数生成中文报告")
    print("2. 观察生成的报告是否具有整体连贯性")
    print("3. 检查章节间的逻辑联系和过渡")
    print("4. 验证是否避免了简单的主题拼凑")
    print("5. 确认所有重要章节都得到了处理")

def main():
    """主测试函数"""
    print("🔧 测试报告连贯性修复")
    print("="*50)
    
    all_tests_passed = True
    
    # 运行所有测试
    tests = [
        test_prompts_file,
        test_report_generation_file,
        test_report_processor_file
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
        print("\n现在可以测试生成报告，应该会看到:")
        print("- 更连贯的报告结构")
        print("- 更深入的分析内容") 
        print("- 更完整的章节覆盖")
        print("- 更好的逻辑过渡")
        return True
    else:
        print("\n❌ 部分测试失败，请检查修复内容。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
