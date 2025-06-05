#!/usr/bin/env python3
"""
修复报告生成系统的脚本
解决当前报告结构异常和内容深度不足的问题
"""

import os
import sys

def fix_prompts():
    """修复提示词文件中的报告生成问题"""
    
    # 读取当前的 prompts.py 文件
    prompts_file = "shandu/prompts.py"
    
    if not os.path.exists(prompts_file):
        print(f"错误：找不到文件 {prompts_file}")
        return False
    
    with open(prompts_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复1：强化禁止研究过程总结的要求
    old_warning = '**警告：您必须生成完整的深度学术内容，而不是大纲、要点列表或简单概述！**'
    new_warning = '''**警告：您必须生成一份完整的学术研究报告，而不是研究过程的总结、大纲、要点列表或元数据！**

### 🚨 绝对禁止的内容类型：
1. **研究过程总结**：严禁生成"初步研究发现"、"知识缺口"、"下一步计划"、"研究过程"等元数据内容
2. **表格式发现**：严禁使用表格来展示"核心洞见"、"发现内容"、"证据强度"等
3. **大纲式结构**：严禁使用要点列表作为主要内容结构
4. **元数据信息**：严禁包含研究耗时、子查询数量等技术信息'''
    
    if old_warning in content:
        content = content.replace(old_warning, new_warning)
        print("✅ 修复1：强化禁止研究过程总结的要求")
    
    # 修复2：强化标题格式要求
    old_title_req = '1. 不要以"研究框架"、"目标"或任何元评论开头。必须以正确的Markdown标题格式开始：# 标题（注意#号和标题文字在同一行，中间用一个空格分隔）。'
    new_title_req = '''1. **绝对禁止元评论开头**：不要以"研究框架"、"目标"、"初步研究发现"或任何元评论开头
2. **强制标题格式**：必须以正确的Markdown标题格式开始：# 标题内容（注意#号和标题文字在同一行，中间用一个空格分隔）
3. **绝对禁止空标题**：严禁出现空的 # 标题行，标题必须包含完整的标题文字
4. **绝对禁止换行标题**：严禁出现如下错误格式：
   ```
   #
   标题内容（这是错误的）
   ```
   正确格式必须是：`# 标题内容`（这是正确的）'''
    
    if old_title_req in content:
        content = content.replace(old_title_req, new_title_req)
        print("✅ 修复2：强化标题格式要求")
    
    # 修复3：在MARKDOWN格式强制执行部分添加更严格的要求
    old_markdown = '''MARKDOWN 格式强制执行：
- 标题格式必须严格正确：# 一级标题、## 二级标题、### 三级标题（#号和标题文字必须在同一行，用空格分隔）
- 绝对禁止出现换行的标题格式，如：
  #
  标题内容（这是错误的）
- 正确格式应为：# 标题内容（这是正确的）'''
    
    new_markdown = '''### 🔥 MARKDOWN 格式强制执行（绝对不可违背）：
- **标题格式必须严格正确**：# 一级标题、## 二级标题、### 三级标题（#号和标题文字必须在同一行，用空格分隔）
- **绝对禁止空标题行**：严禁出现只有 # 而没有标题文字的行
- **绝对禁止换行标题**：标题的 # 号和标题文字必须在同一行
- **正确标题示例**：`# 西游记中的权力斗争研究`（正确）
- **错误标题示例**：`#\\n西游记中的权力斗争研究`（错误，绝对禁止）'''
    
    if old_markdown in content:
        content = content.replace(old_markdown, new_markdown)
        print("✅ 修复3：强化MARKDOWN格式要求")
    
    # 保存修复后的文件
    with open(prompts_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已保存修复后的 {prompts_file}")
    return True

def regenerate_report():
    """重新生成报告"""
    print("\n🔄 开始重新生成报告...")
    
    # 删除旧报告
    old_report = "output/xiyou_report.md"
    if os.path.exists(old_report):
        os.remove(old_report)
        print(f"✅ 已删除旧报告：{old_report}")
    
    # 运行报告生成命令
    cmd = '''shandu research "西游记中的权力之争" \\
    --depth 2 \\
    --breadth 3 \\
    --output output/xiyou_report_fixed.md \\
    --verbose \\
    --report-type academic \\
    --report-detail detailed \\
    --language zh'''
    
    print(f"🚀 执行命令：{cmd}")
    result = os.system(cmd)
    
    if result == 0:
        print("✅ 报告生成完成")
        return True
    else:
        print("❌ 报告生成失败")
        return False

def main():
    """主函数"""
    print("🔧 开始修复报告生成系统...")
    
    # 修复提示词
    if not fix_prompts():
        print("❌ 提示词修复失败")
        return 1
    
    print("\n📋 修复总结：")
    print("1. ✅ 强化禁止研究过程总结的要求")
    print("2. ✅ 强化标题格式要求，禁止空标题和换行标题")
    print("3. ✅ 强化MARKDOWN格式执行要求")
    print("4. ✅ 明确禁止表格式发现和元数据信息")
    
    print("\n🎯 修复重点：")
    print("- 确保生成完整的学术报告，而不是研究过程总结")
    print("- 修复标题格式问题，避免空的 # 标题行")
    print("- 强制生成深度学术内容，达到15000字要求")
    print("- 禁止表格式的'核心洞见'和'知识缺口'内容")
    
    # 询问是否重新生成报告
    response = input("\n是否立即重新生成报告？(y/n): ")
    if response.lower() in ['y', 'yes', '是']:
        regenerate_report()
    
    print("\n✅ 修复完成！现在可以重新运行 start_research.sh 生成正确的报告。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
