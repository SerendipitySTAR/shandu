# 报告生成修复脚本
# 用于修复报告生成中的格式和深度问题

def get_enhanced_report_generation_prompt():
    """返回增强的报告生成提示词"""
    return """您必须编写一份综合研究报告。今天的日期是：{{current_date}}。

{{report_style_instructions}}

## 核心任务：创建连贯的深度学术报告

您的任务是创建一份深入、全面、连贯的学术研究报告，而不是简单地拼凑多篇文章。

### 连贯性要求（最重要）：
1. 【整体统一性】报告必须作为一个统一的整体，各部分之间有清晰的逻辑联系和自然过渡
2. 【深度分析】不仅仅是信息的罗列，而是要提供深入的分析、独到的见解和综合性判断
3. 【有机结构】章节安排应自然流畅，避免生硬的主题分割，确保内容的有机融合
4. 【一致视角】整篇报告应保持一致的分析视角、论述风格和学术水准

### 强制性格式和结构要求：
1. 【标题格式】必须以正确的Markdown标题格式开始：# 报告标题（#号和标题文字在同一行，中间用一个空格分隔）
2. 【完整结构】报告必须包含以下完整结构：
   - # 报告标题
   - ## 引言/概述（至少500字）
   - ## 主体章节（至少3-5个主要章节，每个章节包含2-4个子章节）
   - ## 结论（至少300字）
   - ## 参考文献
3. 【子章节要求】每个主要章节必须包含详细的子章节，使用### 三级标题
4. 【内容深度】每个主要章节至少包含800-1200字的深入分析
5. 【参考文献】必须在报告末尾包含完整的"## 参考文献"章节
6. 严格遵循中文表达习惯，避免中英文混杂，确保语言纯粹性

### 严格禁止的格式错误：
❌ 绝对禁止出现换行的标题格式：
```
#
标题内容（这是错误的）
```
✅ 正确格式必须是：
```
# 标题内容（这是正确的）
```

### MARKDOWN 格式强制执行：
- 标题格式必须严格正确：# 一级标题、## 二级标题、### 三级标题（#号和标题文字必须在同一行，用空格分隔）
- 酌情整合表格、粗体、斜体、代码块、块引用和水平分割线
- 保持足够的间距以提高可读性

### 内容量和深度控制：
- 每个主要章节都应全面且详细，包含多个子章节
- 提供详尽的历史背景、理论基础、实际应用和未来展望
- 每个子章节至少包含3-5个段落的深入分析
- 严格按照指定的详细程度要求控制内容篇幅和深度
- 确保报告总体达到指定的字数要求

### 参考文献要求：
- 必须在报告末尾包含"## 参考文献"章节
- 以带括号的数字形式引用 [1], [2] 等
- 参考文献列表必须完整且格式规范

### 质量保证：
- 切勿包含关于研究流程、框架或所用时间的元数据
- 全文必须使用纯正的中文表达，避免任何英文词汇
- 确保每个章节都有实质性内容，避免空洞的标题

## 关键强调

**这必须是一份连贯的深度学术研究报告，具有完整的结构和充实的内容。**

- 避免简单的主题并列，追求深度挖掘和综合分析
- 确保每个章节都有详细的子章节和充实的内容
- 必须包含完整的参考文献部分
- 报告长度必须达到指定的字数要求

{{objective_instruction}}"""

def get_enhanced_length_instructions():
    """返回增强的字数控制指令"""
    return {
        "brief": """【字数要求：约3000字】
🎯 强制性要求：整体报告必须严格控制在约3000字
📝 内容策略：请非常简洁地总结，只关注绝对关键的要点
⚠️ 重要提醒：内容应明显比标准版本更短，严格控制篇幅
✅ 验证标准：确保整体报告约3000字，不得超出太多
📋 结构要求：即使是简要报告也必须包含完整的章节结构和参考文献""",
        
        "standard": """【字数要求：约5000字】
🎯 强制性要求：整体报告必须严格控制在约5000字
📝 内容策略：提供平衡的详细程度，确保内容充实但不冗余
⚠️ 重要提醒：这是标准长度，需要在深度和广度之间找到平衡
✅ 验证标准：确保整体报告约5000字，这是基准要求
📋 结构要求：必须包含完整的章节结构、子章节和参考文献""",
        
        "detailed": """【字数要求：约10000字】
🎯 强制性要求：整体报告必须严格控制在约10000字
📝 内容策略：请高度扩展内容，添加大量深度、更多示例和详细解释
⚠️ 重要提醒：内容应明显比标准版本更长更全面
✅ 验证标准：确保整体报告约10000字，这是必须达到的目标
📋 结构要求：必须包含详细的章节结构、多个子章节和完整的参考文献"""
    }

def get_enhanced_direct_report_template():
    """返回增强的直接报告生成模板"""
    return """创建一份极其全面、详细的研究报告。
标题：{report_title}
基于研究结果：{findings_preview}
主题：{themes}
可用来源：{sources_info}
详细程度：{detail_level}。当前日期：{current_date}。
报告风格指南：{report_style_instructions}

### 强制性结构要求：
1. 必须以正确的Markdown格式开始：# {report_title}
2. 必须包含以下完整结构：
   - # 报告标题
   - ## 引言/概述
   - ## 主体章节（至少3-5个主要章节，每个包含子章节）
   - ## 结论
   - ## 参考文献
3. 每个主要章节必须包含2-4个子章节（### 三级标题）
4. 严格按照指定的详细程度要求控制报告篇幅

### 语言和格式要求：
- 全文必须使用纯正的中文表达，严禁出现英文词汇或中英混杂现象
- 确保语言表达地道、流畅，符合中文写作习惯
- 标题格式必须严格正确：# 标题内容（#号和标题文字在同一行，用空格分隔）
- 绝对禁止换行标题格式

### 引文要求：
- 仅可使用"可用引文来源列表"中提供的引文ID
- 将引文格式化为 [n]，其中 n 是来源的确切ID
- 将引文放在相关句子或段落的末尾
- 确保每个主要主张或统计数据都有适当的引文
- 必须在报告末尾包含完整的"## 参考文献"章节

### 内容深度要求：
- 每个主要章节至少800-1200字
- 每个子章节至少300-500字
- 提供详尽的分析、示例和案例研究
- 确保内容连贯、深入且具有学术价值

至关重要：请勿在报告开头包含原始查询文本。直接从标题开始。"""

if __name__ == "__main__":
    print("报告生成修复脚本已准备就绪")
    print("包含增强的提示词和字数控制指令")
