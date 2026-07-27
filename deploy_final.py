import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PA_USERNAME = 'shouqiu'

def run_pa_command(command):
    url = f'https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}/consoles/'
    headers = {'Authorization': 'Token 733d00f0c74184b9398e4f534641893f825812a0', 'Content-Type': 'application/json'}
    data = {
        'command': f'cd /home/{PA_USERNAME}/ci-vote-system && {command}',
        'expiry': 600
    }
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
        if response.status_code == 201:
            print(f'✅ 命令已提交: {command}')
            return True
        else:
            print(f'❌ 命令失败: {command}')
            print(f'   状态码: {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ 异常: {str(e)[:200]}')
        return False

def restart_app():
    url = f'https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}/webapps/{PA_USERNAME}.pythonanywhere.com/reload/'
    headers = {'Authorization': 'Token 733d00f0c74184b9398e4f534641893f825812a0'}
    try:
        response = requests.post(url, headers=headers, verify=False, timeout=30)
        if response.status_code == 200:
            print('✅ 应用已重启')
            return True
        else:
            print(f'❌ 重启失败: {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ 重启异常: {str(e)[:200]}')
        return False

def main():
    print("=" * 60)
    print("CI推荐投票系统 - 自动部署")
    print("=" * 60)
    
    commands = [
        'git fetch origin',
        'git reset --hard origin/main',
        'git clean -fd',
        'find . -name "__pycache__" -type d -exec rm -rf {} +',
        'rm -rf *.pyc __pycache__'
    ]
    
    for cmd in commands:
        run_pa_command(cmd)
    
    restart_app()
    
    print("\n" + "=" * 60)
    print("请访问 https://shouqiu.pythonanywhere.com/debug")
    print("检查数据文件是否存在")
    print("然后访问 https://shouqiu.pythonanywhere.com")
    print("按 Ctrl+Shift+R 强制刷新")
    print("=" * 60)

if __name__ == '__main__':
    main()