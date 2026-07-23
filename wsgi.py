import os
import sys

# 将应用目录添加到Python路径
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# 使用importlib导入带连字符的模块名
import importlib.util
spec = importlib.util.spec_from_file_location("flask_app", os.path.join(path, "tui-jian-tou-piao-xi-tong.py"))
flask_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_module)

# 暴露WSGI应用对象
application = flask_module.app
