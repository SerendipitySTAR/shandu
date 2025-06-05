
# 参数说明
# --depth (1-5): 研究深度，控制递归探索层数
# --breadth (2-10): 研究广度，控制并行查询数量
# --output: 保存报告到文件
# --verbose: 显示详细进度
# --strategy: 选择研究策略（langgraph 或 agent）
# --report-type: 报告类型（standard, academic, business, literature_review）
# --report-detail: 详细程度（brief, standard, detailed, 或 custom_WORDCOUNT）

shandu research "西游记中的权力之争" \
    --depth 2 \
    --breadth 3 \
    --output output/xiyou_report.md \
    --verbose \
    --report-type academic \
    --report-detail detailed \
    --language zh
