import os
from log import logger

def count_lines_in_files(
    directory, 
    extension, 
    exclude_dirs=None, 
    exclude_files=None
):
    """
    统计指定目录及其子目录中特定扩展名文件的总行数，排除指定目录和文件
    
    :param directory: 要搜索的目录路径
    :param extension: 文件扩展名(如'.py', '.txt'), 不区分大小写
    :param exclude_dirs: 要排除的目录名列表（如 ['venv', '.venv', 'site-packages']）
    :param exclude_files: 要排除的文件名列表（如 ['__init__.py', 'setup.py']）
    :return: 总行数
    """
    total_lines = 0
    extension = extension.lower()
    
    # 默认排除的目录
    if exclude_dirs is None:
        exclude_dirs = ['venv', '.venv', 'site-packages', 'dist', 'blivedm']
    
    # 默认排除的文件
    if exclude_files is None:
        exclude_files = ['__init__.py', 'setup.py']
    
    for root, dirs, files in os.walk(directory):
        # 检查当前路径是否包含要排除的目录
        if any(exclude_dir in root for exclude_dir in exclude_dirs):
            continue  # 跳过排除的目录
        
        for file in files:
            # 检查文件扩展名是否匹配
            if not file.lower().endswith(extension):
                continue
            
            # 检查文件名是否在排除列表中
            if file.lower() in [f.lower() for f in exclude_files]:
                continue
            
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)  # 高效逐行计数
                    total_lines += lines
            except (UnicodeDecodeError, PermissionError, IOError) as e:
                logger.error(f"无法读取文件 {file_path}: {str(e)}")
    
    return total_lines

def lines() -> int:
    """
    统计当前工作目录及其子目录中所有.py文件的总行数，排除指定目录和文件
    :return: 总行数
    """

    # 使用当前工作目录作为默认路径
    folder_path = os.getcwd()
    file_extension = ".py"

    if not file_extension.startswith('.'):
        file_extension = '.' + file_extension

    # 自定义要排除的文件（可选）
    custom_exclude_files = "web.py,test.py,test1.py,gift_mapping.py,changelog.py,lines.py".strip()

    exclude_files = None
    if custom_exclude_files:
        exclude_files = [f.strip() for f in custom_exclude_files.split(",")]

    if os.path.isdir(folder_path):
        total = count_lines_in_files(
            folder_path, 
            file_extension,
            exclude_files=exclude_files
        )
        return total
    else:
        return 0