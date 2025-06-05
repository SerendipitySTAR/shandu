#!/usr/bin/env python3
"""
自动报告质量检查脚本 - 在报告生成后自动运行质量检查和修复
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_and_fix_report(report_path, detail_level="detailed", auto_fix=True):
    """检查并修复报告质量"""
    
    if not os.path.exists(report_path):
        print(f"❌ 报告文件不存在: {report_path}")
        return False
    
    print(f"🔍 开始检查报告: {report_path}")
    
    # 读取报告内容
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_length = len(content)
    print(f"📊 原始字数: {original_length}")
    
    # 导入验证函数
    try:
        from shandu.agents.processors.report_generator import validate_report_quality
        from fix_fake_content import detect_fake_content_patterns, fix_fake_content
        
        # 1. 检查报告质量
        validation = validate_report_quality(content, detail_level)
        
        print(f"📋 质量验证结果:")
        print(f"   是否合格: {'✅' if validation['is_valid'] else '❌'}")
        print(f"   总字数: {validation['analysis']['total_words']}")
        print(f"   章节数: {validation['analysis']['section_count']}")
        
        issues_found = False
        
        if validation['issues']:
            issues_found = True
            print("   ❌ 发现问题:")
            for issue in validation['issues']:
                print(f"     - {issue}")
        
        if validation['warnings']:
            print("   ⚠️ 警告:")
            for warning in validation['warnings']:
                print(f"     - {warning}")
        
        # 2. 检查伪内容
        fake_patterns = detect_fake_content_patterns(content)
        if fake_patterns:
            issues_found = True
            print(f"   🚨 检测到伪内容: {len(fake_patterns)} 个")
            for pattern in fake_patterns[:3]:  # 显示前3个
                if pattern['type'] == 'bullet_only':
                    print(f"     - 要点罗列章节: {pattern['header']}")
                elif pattern['type'] == 'fake_word_count':
                    print(f"     - 虚假字数标注: {pattern['claimed_words']}字")
        
        # 3. 自动修复
        if issues_found and auto_fix:
            print("\n🔧 开始自动修复...")
            
            # 备份原文件
            backup_path = report_path + f".backup_{int(os.path.getmtime(report_path))}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📁 原文件已备份到: {backup_path}")
            
            # 修复伪内容
            if fake_patterns:
                content = fix_fake_content(content)
                print("✅ 伪内容修复完成")
            
            # 保存修复后的文件
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            final_length = len(content)
            print(f"📊 修复后字数: {final_length}")
            print(f"📈 字数增加: {final_length - original_length}")
            
            # 重新验证
            final_validation = validate_report_quality(content, detail_level)
            print(f"\n🎯 最终验证结果:")
            print(f"   是否合格: {'✅' if final_validation['is_valid'] else '❌'}")
            print(f"   总字数: {final_validation['analysis']['total_words']}")
            
            if final_validation['is_valid']:
                print("🎉 报告质量修复成功！")
                return True
            else:
                print("⚠️ 部分问题仍然存在，但报告已得到改善")
                return False
        
        elif not issues_found:
            print("✅ 报告质量良好，无需修复")
            return True
        
        else:
            print("ℹ️ 发现问题但未启用自动修复")
            return False
            
    except ImportError as e:
        print(f"❌ 导入验证函数失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 检查过程中出现错误: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动报告质量检查和修复工具")
    parser.add_argument("report_path", nargs="?", default="output/xiyou_report.md", 
                       help="报告文件路径 (默认: output/xiyou_report.md)")
    parser.add_argument("--detail-level", choices=["brief", "standard", "detailed"], 
                       default="detailed", help="详细程度级别 (默认: detailed)")
    parser.add_argument("--no-fix", action="store_true", 
                       help="只检查不修复")
    
    args = parser.parse_args()
    
    print("🔧 自动报告质量检查工具\n")
    
    auto_fix = not args.no_fix
    
    success = check_and_fix_report(
        args.report_path, 
        args.detail_level, 
        auto_fix
    )
    
    if success:
        print("\n🎯 建议: 报告质量良好，可以使用")
    else:
        print("\n🎯 建议: 考虑重新生成报告或手动调整")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
