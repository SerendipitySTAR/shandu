#!/usr/bin/env python3
"""
测试 length_instruction 错误修复
"""

import sys
import os
import traceback

# 添加项目根目录到 Python 路径
sys.path.insert(0, '/media/sc/data/sc/下载/shandu_v2.5.5')

def test_get_length_instruction():
    """测试 _get_length_instruction 函数的健壮性"""
    print("\n=== 测试 _get_length_instruction 函数 ===")
    
    try:
        from shandu.agents.nodes.report_generation import _get_length_instruction
        
        # 测试正常情况
        test_cases = [
            ("brief", "简要"),
            ("standard", "标准"),
            ("detailed", "详细"),
            ("custom_5000", "自定义5000字"),
            ("custom_15000", "自定义15000字"),
            ("unknown_value", "未知值"),
            (None, "None值"),
            (123, "数字类型"),
            ("", "空字符串"),
            ("  BRIEF  ", "带空格的大写"),
            ("custom_abc", "无效自定义格式"),
            ("custom_", "不完整自定义格式")
        ]
        
        all_passed = True
        for test_value, description in test_cases:
            try:
                result = _get_length_instruction(test_value)
                if result and len(result) > 50:  # 确保返回了有意义的指令
                    print(f"✅ {description} ({test_value}): 成功")
                else:
                    print(f"❌ {description} ({test_value}): 返回内容太短")
                    all_passed = False
            except Exception as e:
                print(f"❌ {description} ({test_value}): 异常 - {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 导入或测试失败: {e}")
        traceback.print_exc()
        return False

def test_function_signatures():
    """测试关键函数是否包含 length_instruction 参数"""
    print("\n=== 测试函数签名 ===")
    
    try:
        import inspect
        from shandu.agents.processors.report_generator import (
            generate_initial_report, 
            enhance_report, 
            expand_key_sections
        )
        
        functions_to_test = [
            (generate_initial_report, "generate_initial_report"),
            (enhance_report, "enhance_report"),
            (expand_key_sections, "expand_key_sections")
        ]
        
        all_passed = True
        for func, name in functions_to_test:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            if "length_instruction" in params:
                print(f"✅ {name}: 包含 length_instruction 参数")
            else:
                print(f"❌ {name}: 缺少 length_instruction 参数")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 函数签名测试失败: {e}")
        traceback.print_exc()
        return False

def test_simple_report_generation():
    """测试简单的报告生成流程"""
    print("\n=== 测试简单报告生成 ===")
    
    try:
        from shandu.agents.nodes.report_generation import _get_length_instruction
        
        # 模拟一个简单的状态
        mock_state = {
            'detail_level': 'standard',
            'query': '人工智能的发展',
            'language': 'zh'
        }
        
        # 测试获取字数指令
        length_instruction = _get_length_instruction(mock_state['detail_level'])
        
        if length_instruction and "10000字" in length_instruction:
            print("✅ 标准详细级别返回正确的字数指令")
            return True
        else:
            print(f"❌ 字数指令不正确: {length_instruction[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ 简单报告生成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("🔧 开始测试 length_instruction 错误修复...")
    
    tests = [
        test_get_length_instruction,
        test_function_signatures,
        test_simple_report_generation
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
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！length_instruction 错误已修复")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
