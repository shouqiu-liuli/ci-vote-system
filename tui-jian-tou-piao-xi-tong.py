import os
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'ci_recommendation_system_secret_key_2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'tui-jian-shu-ju.json')
DB_FILE = os.path.join(BASE_DIR, 'ci_recommendation.db')
CONFIG_FILE = os.path.join(BASE_DIR, 'email_config.json')

# PythonAnywhere上的站点URL，部署后需要修改
SITE_URL = 'https://shouqiu.pythonanywhere.com'

EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'smtp_ssl': True,
    'from_email': '',
    'password': ''
}

# 加载邮箱配置
def load_email_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                EMAIL_CONFIG.update(saved_config)
        except Exception:
            pass

load_email_config()

NOTIFICATION_RECIPIENTS = ['daopeng.yang@cat.com']

def send_email_notification(to_email, subject, html_content):
    if not EMAIL_CONFIG['from_email'] or not EMAIL_CONFIG['password']:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['from_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        if EMAIL_CONFIG.get('smtp_ssl', False):
            server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        else:
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
        server.login(EMAIL_CONFIG['from_email'], EMAIL_CONFIG['password'])
        server.sendmail(EMAIL_CONFIG['from_email'], to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f'邮件发送失败: {e}')
        return False

def send_rating_notification(ci_id, ci_title, rating_user, rating, comment):
    subject = f'【CI评分通知】{ci_id} 收到新评分'
    content = f'''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>CI评分通知</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 18px; text-align: center; border-radius: 10px 10px 0 0; }}
            .header h2 {{ margin: 0; }}
            .content {{ background: white; padding: 25px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }}
            .stars {{ color: #ffc107; font-size: 24px; }}
            .score-box {{ background: #fff9e6; padding: 15px; border-radius: 8px; margin-top: 15px; }}
            .btn {{ display: inline-block; background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>CI评分通知</h2>
            </div>
            <div class="content">
                <p>您好！以下CI收到了新的评分：</p>
                <h3 style="color: #667eea;">{ci_id} - {ci_title}</h3>
                <div class="score-box">
                    <p><strong>评分人：</strong>{rating_user}</p>
                    <p><strong>评分：</strong>
                        <span class="stars">{"★" * rating}{"☆" * (5 - rating)}</span>
                        ({rating}星 = {rating * 20}分)
                    </p>
                    {f'<p><strong>评价：</strong>{comment}</p>' if comment else ''}
                </div>
                <p><a href="{SITE_URL}/ci/{ci_id}" class="btn" target="_blank">查看详情</a></p>
            </div>
        </div>
    </body>
    </html>
    '''
    for email in NOTIFICATION_RECIPIENTS:
        send_email_notification(email, subject, content)

def load_recommendation_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('items', [])
    return []

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            tags TEXT,
            email TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ci_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(ci_id, user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ci_scores (
            ci_id TEXT PRIMARY KEY,
            ai_score REAL NOT NULL,
            adjusted_score REAL,
            last_adjusted_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ci_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            similarity REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(ci_id, user_id)
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, name, department, tags, email, is_admin)
        VALUES ('admin', 'admin123', '管理员', '管理部门', '管理,审核,决策', 'admin@cat.com', 1),
               ('zhang', 'zhang123', '张三', '技术部', '技术,开发,优化', 'zhang@cat.com', 0),
               ('li', 'li123', '李四', '质量部', '质量,检测,改进', 'li@cat.com', 0),
               ('wang', 'wang123', '王五', '生产部', '生产,效率,安全', 'wang@cat.com', 0),
               ('chen', 'chen123', '陈六', '采购部', '采购,成本,供应链', 'chen@cat.com', 0)
    ''')
    conn.commit()
    conn.close()

def calculate_jaccard_similarity(set1, set2):
    set1 = set(set1)
    set2 = set(set2)
    if not set1 and not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0

def get_recommendations_for_user(user_id, user_tags, user_department=None):
    conn = get_db()
    cursor = conn.cursor()
    ci_data = load_recommendation_data()
    recommendations = []
    for ci in ci_data:
        ci_tags = ci.get('tags', [])
        ci_category = ci.get('main_category', '')
        ci_problem_type = ci.get('problem_type', '')
        ci_department = ci.get('department', '')
        
        tag_similarity = calculate_jaccard_similarity(user_tags, ci_tags)
        category_match = 0.3 if any(tag in ci_category for tag in user_tags) else 0
        problem_match = 0.2 if any(tag in ci_problem_type for tag in user_tags) else 0
        dept_match = 0.1 if user_department and user_department in ci_department else 0
        
        similarity = tag_similarity + category_match + problem_match + dept_match
        
        if similarity == 0:
            similarity = 0.05
        
        cursor.execute('SELECT rating FROM ratings WHERE ci_id = ? AND user_id = ?', (ci['ci_id'], user_id))
        user_rating = cursor.fetchone()
        cursor.execute('SELECT AVG(rating) as avg FROM ratings WHERE ci_id = ?', (ci['ci_id'],))
        avg_result = cursor.fetchone()
        avg_rating = round(avg_result['avg'], 1) if avg_result['avg'] else None
        recommendations.append({
            'ci_id': ci['ci_id'],
            'data': ci,
            'similarity': similarity,
            'user_rating': user_rating['rating'] if user_rating else None,
            'avg_rating': avg_rating
        })
    conn.close()
    recommendations.sort(key=lambda x: x['similarity'], reverse=True)
    return recommendations[:20]

def update_ci_score(ci_id, adjusted_score):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO ci_scores (ci_id, ai_score, adjusted_score, last_adjusted_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (ci_id, 0, adjusted_score))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    user_tags = user['tags'].split(',') if user['tags'] else []
    user_department = user['department'] if user['department'] else None
    recommendations = get_recommendations_for_user(session['user_id'], user_tags, user_department)
    return render_template('index.html', user_name=user['name'], recommendations=recommendations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/ci/<ci_id>')
def ci_detail(ci_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ci_data = load_recommendation_data()
    ci_item = next((ci for ci in ci_data if ci['ci_id'] == ci_id), None)
    if not ci_item:
        return 'CI不存在', 404
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    cursor.execute('SELECT * FROM ratings WHERE ci_id = ? AND user_id = ?', (ci_id, session['user_id']))
    user_rating = cursor.fetchone()
    cursor.execute('SELECT AVG(rating) as avg FROM ratings WHERE ci_id = ?', (ci_id,))
    avg_result = cursor.fetchone()
    avg_rating = round(avg_result['avg'], 1) if avg_result['avg'] else None
    cursor.execute('''
        SELECT r.*, u.name as user_name 
        FROM ratings r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.ci_id = ? 
        ORDER BY r.created_at DESC
    ''', (ci_id,))
    all_ratings = cursor.fetchall()
    conn.close()
    return render_template('detail.html', ci_item=ci_item, user_name=user['name'], 
                           user_rating=user_rating, avg_rating=avg_rating, all_ratings=all_ratings)

@app.route('/rate/<ci_id>', methods=['POST', 'DELETE'])
def rate_ci(ci_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    if request.method == 'DELETE':
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ratings WHERE ci_id = ? AND user_id = ?', (ci_id, session['user_id']))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': '评分已取消'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    try:
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '')
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': '评分必须在1-5之间'})
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO ratings (ci_id, user_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (ci_id, session['user_id'], rating, comment))
        
        cursor.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],))
        user_name = cursor.fetchone()['name']
        conn.commit()
        conn.close()
        
        ci_data = load_recommendation_data()
        ci_item = next((ci for ci in ci_data if ci['ci_id'] == ci_id), None)
        ci_title = ci_item['main_category'] if ci_item else '未知CI'
        
        send_rating_notification(ci_id, ci_title, user_name, rating, comment)
        
        return jsonify({'success': True, 'message': '评分成功', 'percent_score': rating * 20})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    if not user or not user['is_admin']:
        return '无权限访问', 403
    cursor.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],))
    user_name = cursor.fetchone()['name']
    cursor.execute('SELECT COUNT(*) as total FROM users')
    total_users = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM ratings')
    total_ratings = cursor.fetchone()['total']
    cursor.execute('SELECT AVG(rating) as avg FROM ratings')
    avg_rating_result = cursor.fetchone()
    avg_rating = round(avg_rating_result['avg'], 1) if avg_rating_result['avg'] else 0
    ci_data = load_recommendation_data()
    total_ci = len(ci_data)
    from collections import Counter
    level_counts = Counter(ci.get('ci_level', '未知') for ci in ci_data)
    level_distribution = []
    for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / total_ci * 100, 1) if total_ci > 0 else 0
        level_distribution.append({'level': level, 'count': count, 'pct': pct})
    stats = {
        'total_ci': total_ci,
        'total_users': total_users,
        'total_ratings': total_ratings,
        'avg_rating': avg_rating,
        'level_distribution': level_distribution
    }
    ci_stats = []
    for ci in ci_data:
        cursor.execute('SELECT AVG(rating) as avg, COUNT(*) as cnt FROM ratings WHERE ci_id = ?', (ci['ci_id'],))
        rating_result = cursor.fetchone()
        user_avg_stars = round(rating_result['avg'], 1) if rating_result['avg'] else None
        user_avg_percent = round(user_avg_stars * 20, 1) if user_avg_stars else None
        cursor.execute('SELECT adjusted_score FROM ci_scores WHERE ci_id = ?', (ci['ci_id'],))
        adjusted_result = cursor.fetchone()
        adjusted_score = round(adjusted_result['adjusted_score'], 1) if adjusted_result else None
        change = round(adjusted_score - ci['total_score'], 1) if adjusted_score else None
        ci_stats.append({
            'ci_id': ci['ci_id'],
            'ai_score': ci['total_score'],
            'user_avg_stars': user_avg_stars,
            'user_avg_percent': user_avg_percent,
            'rating_count': rating_result['cnt'],
            'adjusted_score': adjusted_score,
            'change': change
        })
    adjustment_plan = []
    for ci in ci_data:
        cursor.execute('SELECT AVG(rating) as avg, COUNT(*) as cnt FROM ratings WHERE ci_id = ?', (ci['ci_id'],))
        rating_result = cursor.fetchone()
        user_avg_percent = round(rating_result['avg'] * 20, 1) if rating_result['avg'] else None
        expected_score = None
        if rating_result['cnt'] >= 3 and user_avg_percent:
            expected_score = round(ci['total_score'] * 0.6 + user_avg_percent * 0.4, 1)
        adjustment_plan.append({
            'ci_id': ci['ci_id'],
            'current_score': ci['total_score'],
            'user_avg_percent': user_avg_percent,
            'rating_count': rating_result['cnt'],
            'expected_score': expected_score
        })
    cursor.execute('''
        SELECT u.*, COALESCE(r.cnt, 0) as rating_count 
        FROM users u 
        LEFT JOIN (SELECT user_id, COUNT(*) as cnt FROM ratings GROUP BY user_id) r 
        ON u.id = r.user_id
    ''')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', user_name=user_name, stats=stats, 
                           ci_stats=ci_stats, adjustment_plan=adjustment_plan, users=users)

@app.route('/admin/adjust', methods=['POST'])
def admin_adjust():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    if not user or not user['is_admin']:
        return jsonify({'success': False, 'message': '无权限'})
    ci_data = load_recommendation_data()
    adjusted_count = 0
    for ci in ci_data:
        cursor.execute('SELECT AVG(rating) as avg, COUNT(*) as cnt FROM ratings WHERE ci_id = ?', (ci['ci_id'],))
        rating_result = cursor.fetchone()
        if rating_result['cnt'] >= 3 and rating_result['avg']:
            user_avg_percent = rating_result['avg'] * 20
            new_score = ci['total_score'] * 0.6 + user_avg_percent * 0.4
            cursor.execute('''
                INSERT OR REPLACE INTO ci_scores (ci_id, ai_score, adjusted_score, last_adjusted_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (ci['ci_id'], ci['total_score'], round(new_score, 1)))
            adjusted_count += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'已调整{adjusted_count}个CI评分'})

@app.route('/api/ci-list')
def api_ci_list():
    ci_data = load_recommendation_data()
    return jsonify(ci_data)

@app.route('/api/ratings/<ci_id>')
def api_ratings(ci_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT AVG(rating) as avg, COUNT(*) as cnt FROM ratings WHERE ci_id = ?', (ci_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify({
        'ci_id': ci_id,
        'avg_rating': round(result['avg'], 1) if result['avg'] else None,
        'rating_count': result['cnt']
    })

@app.route('/api/email-config', methods=['POST'])
def api_email_config():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    if not user or not user['is_admin']:
        return jsonify({'success': False, 'message': '无权限'})
    
    EMAIL_CONFIG['from_email'] = request.form.get('from_email', '')
    EMAIL_CONFIG['password'] = request.form.get('password', '')
    return jsonify({'success': True, 'message': '邮件配置已更新'})

@app.route('/api/email-test', methods=['POST'])
def api_email_test():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    if not user or not user['is_admin']:
        return jsonify({'success': False, 'message': '无权限'})
    
    test_email = request.form.get('test_email', 'daopeng.yang@cat.com')
    success = send_email_notification(test_email, '【测试】CI推荐系统邮件通知', 
                                      '<h2>测试邮件</h2><p>邮件通知功能测试成功！</p>')
    return jsonify({'success': success, 'message': '测试邮件发送成功' if success else '测试邮件发送失败'})

# PythonAnywhere WSGI部署：模块加载时初始化数据库
init_db()