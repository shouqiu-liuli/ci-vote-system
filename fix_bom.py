import os

def remove_bom(file_path):
    """移除文件开头的所有BOM字符"""
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # 移除开头的所有BOM字符 (U+FEFF = EF BB BF in UTF-8)
    while content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")

deploy_dir = os.path.dirname(os.path.abspath(__file__))

files_to_fix = [
    'tui-jian-tou-piao-xi-tong.py',
    'wsgi.py',
    'templates/index.html',
    'templates/detail.html',
    'templates/admin.html',
    'templates/login.html',
]

for f in files_to_fix:
    fp = os.path.join(deploy_dir, f)
    if os.path.exists(fp):
        remove_bom(fp)
    else:
        print(f"文件不存在: {fp}")

print("\n所有文件BOM字符已移除！")