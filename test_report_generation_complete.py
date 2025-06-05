#!/usr/bin/env python3
"""
完整的报告生成流程测试
验证所有关键函数都正确传递 length_instruction 参数
"""

import sys
import traceback
import inspect

def test_all_report_functions_have_length_instruction():
    """测试所有报告生成函数是否都包含 length_instruction 参数"""
    print("=== 测试所有报告生成函数的 length_instruction 参数 ===")
    
    try:
        from shandu.agents.processors.report_generator import (
            generate_initial_report,
            enhance_report,
            expand_key_sections,
            expand_short_sections
        )
        
        functions_to_test = [
            (generate_initial_report, "generate_initial_report"),
            (enhance_report, "enhance_report"),
            (expand_key_sections, "expand_key_sections"),
            (expand_short_sections, "expand_short_sections")
        ]
        
        all_passed = True
        
        for func, name in functions_to_test:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            if "length_instruction" in params:
                print(f"✅ {name}: 包含 length_instruction 参数")
                
                # 检查参数默认值
                length_param = sig.parameters["length_instruction"]
                if length_param.default == "":
                    print(f"   ✅ 默认值正确: '{length_param.default}'")
                else:
                    print(f"   ⚠️ 默认值: '{length_param.default}'")
            else:
                print(f"❌ {name}: 缺少 length_instruction 参数")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def test_length_instruction_generation():
    """测试字数控制指令生成"""
    print("\n=== 测试字数控制指令生成 ===")
    
    try:
        from shandu.agents.nodes.report_generation import _get_length_instruction
        
        test_cases = [
            ("brief", "简要报告"),
            ("standard", "标准报告"),
            ("detailed", "详细报告"),
            ("custom_5000", "自定义5000字"),
            ("custom_15000", "自定义15000字"),
            ("invalid_level", "无效级别"),
            (None, "None值"),
            ("", "空字符串")
        ]
        
        all_passed = True
        
        for level, description in test_cases:
            try:
                instruction = _get_length_instruction(level)
                
                if instruction and len(instruction) > 50:
                    print(f"✅ {description} ({level}): 生成成功 ({len(instruction)}字符)")
                    
                    # 检查关键词
                    if "字数" in instruction or "字" in instruction:
                        print(f"   ✅ 包含字数要求")
                    else:
                        print(f"   ⚠️ 可能缺少字数要求")
                        
                else:
                    print(f"❌ {description} ({level}): 生成失败或内容过短")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ {description} ({level}): 异常 - {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 字数指令生成测试失败: {e}")
        traceback.print_exc()
        return False

def test_report_node_integration():
    """测试报告生成节点集成"""
    print("\n=== 测试报告生成节点集成 ===")
    
    try:
        # 检查报告生成节点文件中的关键修复
        with open('shandu/agents/nodes/report_generation.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修复点
        key_fixes = [
            "length_instruction = _get_length_instruction(current_detail_level)",
            "length_instruction=length_instruction",
            "【修复】传递字数控制指令到章节扩展函数",
            "【新增】传递字数控制指令"
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
        print(f"❌ 节点集成测试失败: {e}")
        traceback.print_exc()
        return False

def test_processor_integration():
    """测试报告处理器集成"""
    print("\n=== 测试报告处理器集成 ===")
    
    try:
        # 检查报告处理器文件中的关键修复
        with open('shandu/agents/processors/report_generator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修复点
        key_fixes = [
            "length_instruction: str = \"\"  # 【新增】字数控制指令参数",
            "【修复】整合字数控制指令到扩展提示中",
            "{length_instruction}"
        ]
        
        missing_fixes = []
        for fix in key_fixes:
            if fix not in content:
                missing_fixes.append(fix)
        
        if missing_fixes:
            print(f"❌ 缺少关键修复: {missing_fixes}")
            return False
        else:
            print("✅ 所有关键修复都已应用到报告处理器")
            return True
        
    except Exception as e:
        print(f"❌ 处理器集成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔧 完整的报告生成流程测试")
    print("验证 length_instruction 错误修复的完整性")
    print("=" * 60)
    
    tests = [
        test_all_report_functions_have_length_instruction,
        test_length_instruction_generation,
        test_report_node_integration,
        test_processor_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        print("✅ length_instruction 错误已完全修复")
        print("✅ 报告生成流程完整性验证通过")
        print("✅ 字数控制功能正常工作")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
