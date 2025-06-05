#!/usr/bin/env python3
"""
测试 length_instruction 错误修复
验证 expand_short_sections 函数是否正确接受 length_instruction 参数
"""

import sys
import traceback

def test_expand_short_sections_signature():
    """测试 expand_short_sections 函数签名是否包含 length_instruction 参数"""
    print("=== 测试 expand_short_sections 函数签名 ===")
    
    try:
        import inspect
        from shandu.agents.processors.report_generator import expand_short_sections
        
        # 检查函数签名
        sig = inspect.signature(expand_short_sections)
        params = list(sig.parameters.keys())
        
        print(f"函数参数: {params}")
        
        # 检查是否包含 length_instruction 参数
        if "length_instruction" in params:
            print("✅ expand_short_sections 函数包含 length_instruction 参数")
            
            # 检查参数的默认值
            length_param = sig.parameters["length_instruction"]
            print(f"   参数类型: {length_param.annotation}")
            print(f"   默认值: {length_param.default}")
            
            return True
        else:
            print("❌ expand_short_sections 函数缺少 length_instruction 参数")
            return False
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def test_function_call_compatibility():
    """测试函数调用兼容性"""
    print("\n=== 测试函数调用兼容性 ===")
    
    try:
        from shandu.agents.processors.report_generator import expand_short_sections
        import inspect
        
        # 模拟调用参数
        sig = inspect.signature(expand_short_sections)
        
        # 检查是否可以用新的参数调用
        test_params = {
            'llm': None,  # 模拟参数
            'report_content': "测试报告内容",
            'detail_level': "standard",
            'language': "zh",
            'length_instruction': "测试字数控制指令"
        }
        
        # 验证参数匹配
        try:
            sig.bind(**test_params)
            print("✅ 函数调用参数匹配成功")
            return True
        except TypeError as e:
            print(f"❌ 函数调用参数不匹配: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        traceback.print_exc()
        return False

def test_length_instruction_integration():
    """测试字数控制指令集成"""
    print("\n=== 测试字数控制指令集成 ===")
    
    try:
        from shandu.agents.nodes.report_generation import _get_length_instruction
        
        # 测试获取字数指令
        test_levels = ["brief", "standard", "detailed", "custom_8000"]
        
        for level in test_levels:
            instruction = _get_length_instruction(level)
            
            if instruction and len(instruction) > 50:
                print(f"✅ {level} 级别字数指令正常: {len(instruction)}字符")
            else:
                print(f"❌ {level} 级别字数指令异常: {instruction[:50]}...")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 字数指令集成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔧 测试 length_instruction 错误修复")
    print("=" * 50)
    
    tests = [
        test_expand_short_sections_signature,
        test_function_call_compatibility,
        test_length_instruction_integration
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
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！length_instruction 错误已修复")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
