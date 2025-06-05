#!/usr/bin/env python3
"""
测试报告生成修复效果的脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
        
        if result.returncode == 0:
            print(f"✅ 命令执行成功")
            if result.stdout:
                print(f"输出:\n{result.stdout}")
        else:
            print(f"❌ 命令执行失败 (返回码: {result.returncode})")
            if result.stderr:
                print(f"错误:\n{result.stderr}")
            if result.stdout:
                print(f"输出:\n{result.stdout}")
                
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ 命令执行超时 (30分钟)")
        return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False

def check_report_quality(report_path):
    """检查报告质量"""
    if not os.path.exists(report_path):
        print(f"❌ 报告文件不存在: {report_path}")
        return False
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 基本质量检查
    word_count = len(content)
    lines = content.split('\n')
    sections = [line for line in lines if line.startswith('##')]
    
    print(f"\n📊 报告质量分析:")
    print(f"   - 总字符数: {word_count}")
    print(f"   - 总行数: {len(lines)}")
    print(f"   - 主要章节数: {len(sections)}")
    
    # 检查是否包含深度内容
    has_depth = False
    for section in sections:
        section_start = content.find(section)
        next_section = content.find('##', section_start + 1)
        if next_section == -1:
            section_content = content[section_start:]
        else:
            section_content = content[section_start:next_section]
        
        section_words = len(section_content)
        if section_words > 1000:  # 如果章节超过1000字符，认为有深度
            has_depth = True
            break
    
    print(f"   - 内容深度: {'✅ 充实' if has_depth else '❌ 过于简短'}")
    
    # 检查是否是大纲格式
    is_outline = False
    if "修复说明" in content or "框架" in content or word_count < 5000:
        is_outline = True
    
    print(f"   - 内容类型: {'❌ 大纲/框架' if is_outline else '✅ 完整报告'}")
    
    return word_count > 8000 and has_depth and not is_outline

def main():
    """主测试函数"""
    print("🚀 开始测试报告生成修复效果")
    
    # 确保在正确的目录
    if not os.path.exists("shandu"):
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 测试用例
    test_cases = [
        {
            "name": "标准深度报告测试",
            "query": "《西游记》中的权力斗争与社会隐喻研究",
            "detail": "standard",
            "output": "output/test_standard_report.md",
            "expected_words": 10000
        },
        {
            "name": "详细深度报告测试", 
            "query": "明代社会结构的制度变迁与文化影响",
            "detail": "detailed",
            "output": "output/test_detailed_report.md",
            "expected_words": 15000
        },
        {
            "name": "自定义字数报告测试",
            "query": "中国古典文学中的政治隐喻分析",
            "detail": "custom_12000",
            "output": "output/test_custom_report.md", 
            "expected_words": 12000
        }
    ]
    
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 测试 {i}/{total_tests}: {test_case['name']}")
        
        # 构建命令
        cmd = f"""python -m shandu research "{test_case['query']}" \
            --depth 3 \
            --breadth 4 \
            --output {test_case['output']} \
            --verbose \
            --report-type academic \
            --report-detail {test_case['detail']} \
            --language zh"""
        
        # 执行测试
        success = run_command(cmd, f"生成{test_case['name']}")
        
        if success:
            # 检查报告质量
            quality_ok = check_report_quality(test_case['output'])
            if quality_ok:
                print(f"✅ {test_case['name']} 通过")
                success_count += 1
            else:
                print(f"❌ {test_case['name']} 质量不达标")
        else:
            print(f"❌ {test_case['name']} 生成失败")
    
    # 总结
    print(f"\n{'='*60}")
    print(f"📋 测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {total_tests}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！报告生成修复成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
