import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'tui-jian-shu-ju.json')

print(f"BASE_DIR: {BASE_DIR}")
print(f"DATA_FILE: {DATA_FILE}")
print(f"文件存在: {os.path.exists(DATA_FILE)}")

if os.path.exists(DATA_FILE):
    print(f"文件大小: {os.path.getsize(DATA_FILE)} bytes")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"JSON keys: {list(data.keys())}")
            items = data.get('items', [])
            print(f"items数量: {len(items)}")
            if items:
                print(f"第一个item: {items[0]['ci_id']}")
                print(f"可用字段: {list(items[0].keys())}")
    except Exception as e:
        print(f"加载失败: {str(e)}")
        
        with open(DATA_FILE, 'rb') as f:
            first_bytes = f.read(200)
            print(f"文件前200字节: {first_bytes}")