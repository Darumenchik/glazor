from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import uuid
import os
import requests
import base64
import tempfile

app = Flask(__name__)
CORS(app)

# Используем временную папку Windows
TEMP_DIR = tempfile.gettempdir()
DATABASE = os.path.join(TEMP_DIR, 'glazor_app.db')

print(f"🔥 Glazor Server")
print(f"📁 База данных: {DATABASE}")
print(f"📁 Temp папка: {TEMP_DIR}")

# ---------- ПРОСТАЯ ИНИЦИАЛИЗАЦИЯ ----------
def init_db_simple():
    """Простая инициализация БД"""
    print("🔧 Инициализация базы данных...")
    
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Простая таблица пользователей
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT UNIQUE,
            password_hash TEXT,
            avatar TEXT
        )
        ''')
        
        # Простая таблица постов
        c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            user_name TEXT,
            photo_url TEXT,
            likes INTEGER DEFAULT 0
        )
        ''')
        
        # Проверяем есть ли пользователь
        c.execute("SELECT COUNT(*) FROM users WHERE phone = '7777777777'")
        if c.fetchone()[0] == 0:
            c.execute('''
            INSERT INTO users (id, name, phone, password_hash, avatar) 
            VALUES (?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                'Admin',
                '7777777777',
                hashlib.sha256('123456'.encode()).hexdigest(),
                'https://i.ibb.co/0jQjZfV/default-avatar.jpg'
            ))
            print("✅ Создан тестовый пользователь")
        
        conn.commit()
        conn.close()
        print(f"✅ База данных готова: {DATABASE}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ---------- РОУТЫ ----------
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/register', methods=['POST'])
def register():
    try:
        print("📝 Регистрация...")
        
        # Пробуем разные форматы
        if request.content_type and 'multipart' in request.content_type:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
        else:
            data = request.json or {}
            name = data.get('name', '').strip()
            phone = data.get('phone', '').strip()
            password = data.get('password', '')
        
        print(f"📱 Данные: {name}, {phone}")
        
        if not name or not phone or not password:
            return jsonify({"success": False, "message": "Заполни все поля"})
        
        conn = get_db()
        c = conn.cursor()
        
        # Проверяем телефон
        c.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if c.fetchone():
            return jsonify({"success": False, "message": "Телефон уже есть"})
        
        # Создаем пользователя
        user_id = str(uuid.uuid4())
        c.execute('''
        INSERT INTO users (id, name, phone, password_hash, avatar) 
        VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            name,
            phone,
            hash_password(password),
            'https://i.ibb.co/0jQjZfV/default-avatar.jpg'
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Зарегистрирован: {name}")
        
        return jsonify({
            "success": True,
            "message": "Аккаунт создан!",
            "user": {
                "id": user_id,
                "name": name,
                "avatar": 'https://i.ibb.co/0jQjZfV/default-avatar.jpg'
            }
        })
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "message": "Ошибка сервера"})

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
        SELECT id, name, avatar, password_hash 
        FROM users WHERE phone = ?
        ''', (phone,))
        
        user = c.fetchone()
        conn.close()
        
        if user and user['password_hash'] == hash_password(password):
            return jsonify({
                "success": True,
                "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "avatar": user['avatar']
                }
            })
        
        return jsonify({"success": False, "message": "Неверные данные"})
        
    except:
        return jsonify({"success": False, "message": "Ошибка сервера"})

@app.route('/api/debug', methods=['GET'])
def debug():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM posts")
    posts = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "status": "working",
        "database": DATABASE,
        "users": users,
        "posts": posts
    })

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    init_db_simple()
    
    print("\n" + "=" * 50)
    print("🌐 Сервер: http://localhost:3000")
    print("👤 Тестовый: 7777777777 / 123456")
    print("=" * 50)
    
    app.run(port=3000, debug=True)