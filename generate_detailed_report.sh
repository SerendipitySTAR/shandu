#!/bin/bash

# 生成详细报告的脚本
# 解决报告长度过短的问题

echo "正在生成详细的《西游记》权力体系研究报告..."
echo "目标字数：约10000字"
echo "研究深度：3层"
echo "研究广度：4个并行查询"
echo ""

# 方案1：使用detailed模式（约10000字）
echo "=== 方案1：详细模式（约10000字） ==="
shandu research "西游记中三界权力体系的动态博弈与角色命运关联研究" \
    --depth 3 \
    --breadth 4 \
    --output output/xiyou_detailed_report.md \
    --verbose \
    --chart-theme default \
    --chart-colors "#FF5733,#33FF57,#3357FF" \
    --report-type academic \
    --report-detail detailed \
    --language zh

echo ""
echo "=== 方案2：自定义15000字模式 ==="
# 方案2：使用自定义字数模式（15000字）
shandu research "西游记中三界权力体系的动态博弈与角色命运关联研究" \
    --depth 4 \
    --breadth 5 \
    --output output/xiyou_comprehensive_report.md \
    --verbose \
    --chart-theme default \
    --chart-colors "#FF5733,#33FF57,#3357FF" \
    --report-type academic \
    --report-detail custom_15000 \
    --language zh

echo ""
echo "=== 方案3：超详细20000字模式 ==="
# 方案3：使用更高字数的自定义模式（20000字）
shandu research "西游记中三界权力体系、宗教冲突、等级制度反抗与角色命运的深度关联研究" \
    --depth 4 \
    --breadth 6 \
    --output output/xiyou_comprehensive_20k_report.md \
    --verbose \
    --chart-theme default \
    --chart-colors "#FF5733,#33FF57,#3357FF" \
    --report-type academic \
    --report-detail custom_20000 \
    --language zh

echo ""
echo "报告生成完成！"
echo "生成的文件："
echo "1. output/xiyou_detailed_report.md (约10000字)"
echo "2. output/xiyou_comprehensive_report.md (约15000字)"
echo "3. output/xiyou_comprehensive_20k_report.md (约20000字)"
echo ""
echo "建议使用方案2或方案3的结果，它们应该提供更全面和详细的分析。"
