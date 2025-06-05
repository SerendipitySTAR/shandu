def count_characters_in_md(file_path):
    """
    统计Markdown文件中的中文字数和英文字数。
    Args:
    file_path (str): Markdown文件的路径。

    Returns:
    dict: 包含中文字数、英文字数和总字数的字典。
    """

    chinese_count = 0
    english_count = 0

    # 定义中文字符的Unicode范围
    chinese_unicode_range = range(0x4E00, 0x9FFF + 1)

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            for char in line:
                # 统计中文字符
                if ord(char) in chinese_unicode_range:
                    chinese_count += 1
                # 统计英文字符
                elif char.isalpha():
                    english_count += 1

    total_count = chinese_count + english_count
    return {'chinese_characters': chinese_count, 'english_characters': english_count, 'total_characters': total_count}

# 示例用法：
result = count_characters_in_md('/media/sc/data/sc/下载/shandu_v2.5.5/output/test_fixed_report.md')
print(result)
