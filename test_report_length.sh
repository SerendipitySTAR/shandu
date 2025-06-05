#!/bin/bash

# 测试报告长度修复效果的脚本

echo "🔍 测试报告长度修复效果"
echo "=================================="
echo ""

# 创建输出目录
mkdir -p output/test_reports

echo "📋 测试1: 标准报告 (约5000字)"
echo "命令: shandu research \"西游记权力体系研究\" --report-detail standard --language zh --output output/test_reports/standard_report.md"
echo ""

echo "📋 测试2: 详细报告 (约10000字)"  
echo "命令: shandu research \"西游记权力体系研究\" --report-detail detailed --language zh --output output/test_reports/detailed_report.md"
echo ""

echo "📋 测试3: 自定义15000字报告"
echo "命令: shandu research \"西游记权力体系研究\" --report-detail custom_15000 --language zh --output output/test_reports/custom_15000_report.md"
echo ""

echo "🎯 建议测试步骤:"
echo "1. 运行上述命令之一"
echo "2. 检查生成的报告长度"
echo "3. 对比修复前后的效果"
echo ""

echo "📊 字数统计命令:"
echo "# 统计中文字符数"
echo "grep -o '[\u4e00-\u9fff]' output/test_reports/standard_report.md | wc -l"
echo ""
echo "# 或者使用Python统计"
echo "python -c \"import re; content=open('output/test_reports/standard_report.md','r',encoding='utf-8').read(); print('中文字符数:', len(re.findall(r'[\u4e00-\u9fff]', content)))\""
echo ""

echo "✅ 预期结果:"
echo "- standard: 约5000字"
echo "- detailed: 约10000字" 
echo "- custom_15000: 约15000字"
echo ""

echo "如果报告仍然过短，请检查:"
echo "1. LLM配置中的max_tokens设置"
echo "2. 网络连接和API响应"
echo "3. 查询的复杂度和深度"
