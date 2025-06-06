#!/usr/bin/env python3
"""
强制扩展报告到指定字数的脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shandu.agents.processors.report_generator import (
    count_chinese_and_english_chars,
    get_word_count_requirements
)
from langchain_openai import ChatOpenAI
from shandu.config import config

async def iterative_expand_report(
    llm: ChatOpenAI,
    report_content: str,
    target_chars: int,
    max_iterations: int = 5
) -> str:
    """通过多次迭代扩展报告到目标字数"""
    
    current_content = report_content
    
    for iteration in range(max_iterations):
        current_chars = count_chinese_and_english_chars(current_content)
        print(f"🔄 迭代 {iteration + 1}/{max_iterations}: 当前字数 {current_chars}")
        
        if current_chars >= target_chars:
            print(f"✅ 已达到目标字数: {current_chars} >= {target_chars}")
            return current_content
        
        needed_chars = target_chars - current_chars
        print(f"📊 需要增加: {needed_chars} 字")
        
        # 构建扩展提示
        expansion_prompt = f"""请将以下报告扩展到至少 {target_chars} 字。当前字数为 {current_chars} 字，需要增加 {needed_chars} 字。

要求：
1. 保持原有结构和逻辑
2. 大幅扩展每个段落的内容
3. 添加更多详细的分析、例证和论述
4. 确保学术质量和连贯性
5. 每个主要章节至少2500字
6. 每个段落至少200字

当前报告内容：
{current_content}

请生成扩展后的完整报告，确保达到 {target_chars} 字的要求："""

        try:
            response = await llm.ainvoke(expansion_prompt)
            expanded_content = response.content.strip()
            
            # 验证扩展效果
            expanded_chars = count_chinese_and_english_chars(expanded_content)
            
            if expanded_chars > current_chars:
                current_content = expanded_content
                print(f"✅ 扩展成功: {current_chars} -> {expanded_chars}")
            else:
                print(f"⚠️ 扩展失败，字数未增加")
                # 尝试不同的扩展策略
                break
                
        except Exception as e:
            print(f"❌ 扩展过程出错: {e}")
            break
    
    return current_content

async def main():
    """主函数"""
    
    # 读取当前报告
    report_path = "output/xiyou_report.md"
    if not os.path.exists(report_path):
        print(f"❌ 报告文件不存在: {report_path}")
        return
    
    with open(report_path, 'r', encoding='utf-8') as f:
        current_report = f.read()
    
    # 统计当前字数
    current_chars = count_chinese_and_english_chars(current_report)
    print(f"📊 当前报告字数: {current_chars}")
    
    # 设置目标字数
    target_chars = 15000
    print(f"🎯 目标字数: {target_chars}")
    
    if current_chars >= target_chars:
        print(f"✅ 报告字数已达标，无需扩展")
        return
    
    # 初始化LLM
    api_config = config.get_section("api")
    llm = ChatOpenAI(
        base_url=api_config.get("base_url"),
        api_key=api_config.get("api_key"),
        model=api_config.get("model", "gpt-4o"),
        temperature=0.6,
        max_tokens=120000
    )
    
    print(f"🚀 开始迭代扩展...")
    
    # 迭代扩展
    expanded_report = await iterative_expand_report(
        llm=llm,
        report_content=current_report,
        target_chars=target_chars,
        max_iterations=5
    )
    
    # 统计最终字数
    final_chars = count_chinese_and_english_chars(expanded_report)
    print(f"📊 最终字数: {final_chars}")
    
    # 保存结果
    if final_chars > current_chars:
        # 备份原文件
        backup_path = "output/xiyou_report_backup_v2.md"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(current_report)
        print(f"💾 原报告已备份到: {backup_path}")
        
        # 保存扩展后的报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(expanded_report)
        print(f"💾 扩展后报告已保存到: {report_path}")
        
        improvement = final_chars - current_chars
        print(f"🎉 扩展完成! 字数增加了 {improvement} 字")
    else:
        print(f"⚠️ 扩展未成功，保持原文件不变")

if __name__ == "__main__":
    asyncio.run(main())
