#!/usr/bin/env python3
"""
直接测试报告生成功能
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shandu.agents.processors.report_generator import generate_initial_report, count_chinese_and_english_chars
from shandu.config import config
from langchain_openai import ChatOpenAI

async def test_report_generation():
    """测试报告生成功能"""
    
    # 模拟研究发现
    mock_findings = """
    ## 西游记中的权势博弈分析

    ### 神佛体系的权力结构
    在《西游记》中，神佛体系呈现出严格的等级制度。玉皇大帝作为天庭的最高统治者，掌握着天界的绝对权威。如来佛祖则代表着佛教体系的最高权力，两者之间存在着微妙的权力平衡关系。

    ### 妖怪势力的挑战
    妖怪势力在小说中并非简单的反面角色，而是对既有权力秩序的挑战者。牛魔王、红孩儿等妖怪通过各种方式挑战神佛的权威，体现了权力斗争的复杂性。

    ### 师徒关系中的伦理冲突
    唐僧与孙悟空之间的师徒关系充满了伦理冲突。唐僧代表着传统的道德权威，而孙悟空则体现了个体意志的反抗精神。紧箍咒成为了这种权力关系的象征。

    ### 权力与道德的辩证关系
    小说通过各种情节展现了权力与道德之间的复杂关系。神佛虽然拥有绝对权力，但在道德层面并非完美无缺，这种矛盾构成了小说的深层主题。
    """

    # 模拟主题提取
    mock_themes = """
    1. 神佛权力体系的等级制度
    2. 妖怪势力对权威的挑战
    3. 师徒关系中的权力与服从
    4. 道德权威与世俗权力的冲突
    5. 个体意志与集体秩序的矛盾
    """

    # 模拟来源
    mock_sources = [
        "《西游记》原文",
        "中国古典文学研究",
        "明清小说权力叙事研究"
    ]

    # 模拟引用
    mock_citations = """
    [1] 吴承恩. 西游记[M]. 人民文学出版社, 1980.
    [2] 李时人. 西游记的权力叙事研究[J]. 文学评论, 2018(3): 45-52.
    [3] 王明华. 明清小说中的师徒关系研究[M]. 中华书局, 2019.
    """

    # 配置LLM
    api_base = config.get("api", "base_url")
    api_key = config.get("api", "api_key")
    model = config.get("api", "model")
    
    llm = ChatOpenAI(
        base_url=api_base,
        api_key=api_key,
        model=model,
        temperature=0.6,
        max_tokens=32000  # 减少token数量以避免超限
    )

    print("开始生成报告...")
    
    try:
        # 生成报告
        report = await generate_initial_report(
            llm=llm,
            query="西游记神佛妖权势博弈与师徒伦理冲突",
            findings=mock_findings,
            extracted_themes=mock_themes,
            report_title="西游记神佛妖权势博弈与师徒伦理冲突研究",
            selected_sources=mock_sources,
            formatted_citations=mock_citations,
            current_date="2024-06-04",
            detail_level="custom_10000",
            include_objective=True,
            language="zh",
            length_instruction="必须生成10000字的深度学术报告"
        )
        
        # 保存报告
        output_path = "output/test_direct_report.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"报告已生成并保存到: {output_path}")
        
        # 统计字数
        char_count = count_chinese_and_english_chars(report)
        print(f"报告字数: {char_count} 字")
        
        return report
        
    except Exception as e:
        print(f"报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_report_generation())
