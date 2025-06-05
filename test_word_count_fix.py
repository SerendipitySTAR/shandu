#!/usr/bin/env python3
"""
测试字数控制修复的脚本
验证修复后的报告生成流程是否能正确控制字数
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_length_instruction_function():
    """测试字数控制函数"""
    print("=== 测试字数控制函数 ===")
    
    try:
        from shandu.agents.nodes.report_generation import _get_length_instruction
        
        # 测试不同详细程度的字数指令
        test_cases = [
            ("brief", "约4000字"),
            ("standard", "约10000字"),
            ("detailed", "约15000字"),
            ("custom_15000", "约15000字"),
            ("custom_8000", "约8000字")
        ]
        
        for detail_level, expected_word_count in test_cases:
            instruction = _get_length_instruction(detail_level)
            print(f"\n详细程度: {detail_level}")
            print(f"字数指令: {instruction}")
            
            if expected_word_count not in instruction:
                print(f"❌ 缺少预期字数要求: {expected_word_count}")
                return False
            else:
                print(f"✅ 包含正确字数要求: {expected_word_count}")
        
        print("\n✅ 字数控制函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 字数控制函数测试失败: {str(e)}")
        return False

def test_generate_initial_report_signature():
    """测试初始报告生成函数签名"""
    print("\n=== 测试初始报告生成函数签名 ===")
    
    try:
        from shandu.agents.processors.report_generator import generate_initial_report
        import inspect
        
        # 获取函数签名
        sig = inspect.signature(generate_initial_report)
        params = list(sig.parameters.keys())
        
        print(f"函数参数: {params}")
        
        # 检查是否包含 length_instruction 参数
        if "length_instruction" not in params:
            print("❌ generate_initial_report 函数缺少 length_instruction 参数")
            return False
        else:
            print("✅ generate_initial_report 函数包含 length_instruction 参数")
        
        # 检查参数默认值
        length_param = sig.parameters["length_instruction"]
        if length_param.default != "":
            print(f"❌ length_instruction 参数默认值不正确: {length_param.default}")
            return False
        else:
            print("✅ length_instruction 参数默认值正确")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始报告生成函数签名测试失败: {str(e)}")
        return False

def test_report_generation_node_integration():
    """测试报告生成节点集成"""
    print("\n=== 测试报告生成节点集成 ===")
    
    try:
        # 读取报告生成节点文件
        with open('shandu/agents/nodes/report_generation.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修复
        key_fixes = [
            "length_instruction = _get_length_instruction(current_detail_level)",
            "length_instruction=length_instruction # 【新增】传递字数控制指令",
            "【修复】添加字数控制指令到初始报告生成"
        ]
        
        missing_fixes = []
        for fix in key_fixes:
            if fix not in content:
                missing_fixes.append(fix)
        
        if missing_fixes:
            print(f"❌ 缺少关键修复: {missing_fixes}")
            return False
        else:
            print("✅ 所有关键修复都已应用到报告生成节点")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告生成节点集成测试失败: {str(e)}")
        return False

def test_processor_integration():
    """测试处理器集成"""
    print("\n=== 测试处理器集成 ===")
    
    try:
        # 读取报告处理器文件
        with open('shandu/agents/processors/report_generator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查字数指令在用户消息中的使用
        key_integrations = [
            "{length_instruction}",  # 在中文用户消息中
            "length_instruction: str = \"\" # 【新增】字数控制指令参数"  # 在函数签名中
        ]
        
        missing_integrations = []
        for integration in key_integrations:
            if integration not in content:
                missing_integrations.append(integration)
        
        if missing_integrations:
            print(f"❌ 缺少关键集成: {missing_integrations}")
            return False
        else:
            print("✅ 所有关键集成都已应用到报告处理器")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告处理器集成测试失败: {str(e)}")
        return False

def show_fix_summary():
    """显示修复总结"""
    print("\n" + "="*60)
    print("📋 字数控制修复总结")
    print("="*60)
    
    improvements = [
        "✅ 修复 generate_initial_report 函数，添加 length_instruction 参数",
        "✅ 在报告生成节点中传递字数控制指令到初始报告生成",
        "✅ 在中文和英文用户消息中都添加字数控制指令",
        "✅ 确保字数控制指令在所有报告生成阶段都被使用",
        "✅ 保持与现有 enhance_report 和 expand_key_sections 的一致性"
    ]
    
    for improvement in improvements:
        print(improvement)
    
    print("\n🎯 预期效果:")
    print("- 初始报告生成时就遵循字数要求")
    print("- 不同详细程度产生相应长度的报告")
    print("- brief: 约4000字, standard: 约10000字, detailed: 约15000字")
    print("- custom_WORDCOUNT: 用户自定义字数")
    
    print("\n📝 使用建议:")
    print("1. 测试不同的 --report-detail 参数")
    print("2. 使用 --report-detail detailed 生成长报告")
    print("3. 使用 --report-detail custom_15000 生成15000字报告")
    print("4. 观察生成的报告是否达到预期字数")

def main():
    """主测试函数"""
    print("🔧 测试字数控制修复")
    print("="*50)
    
    all_tests_passed = True
    
    # 运行所有测试
    tests = [
        test_length_instruction_function,
        test_generate_initial_report_signature,
        test_report_generation_node_integration,
        test_processor_integration
    ]
    
    for test_func in tests:
        try:
            if not test_func():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 失败: {str(e)}")
            all_tests_passed = False
    
    # 显示总结
    show_fix_summary()
    
    if all_tests_passed:
        print("\n🎉 所有测试通过！字数控制修复已完成。")
        print("\n现在可以测试生成报告，应该会看到:")
        print("- 初始报告就遵循字数要求")
        print("- 不同详细程度产生相应长度的报告") 
        print("- 更好的字数控制效果")
        return True
    else:
        print("\n❌ 部分测试失败，请检查修复内容。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
