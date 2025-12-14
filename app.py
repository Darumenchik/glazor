from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, hashlib, uuid, os, requests, base64

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE = os.path.join(DATA_DIR, 'glazor.db')
IMGBB_API_KEY = 'db05c50c7794b9530a288d478da4eb31'

# ---------- База данных ----------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_avatar TEXT,
            photo_url TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Тестовый пользователь
    cursor.execute('SELECT COUNT(*) FROM users WHERE phone=?', ('7777777777',))
    if cursor.fetchone()[0] == 0:
        admin_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO users (id,name,phone,password_hash,avatar)
            VALUES (?,?,?,?,?)
        ''', (admin_id,'Admin','7777777777',hashlib.sha256('123456'.encode()).hexdigest(),'https://i.ibb.co/0jQjZfV/default-avatar.jpg'))
    conn.commit(); conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def upload_to_imgbb(image_file):
    try:
        img_data = image_file.read()
        if not img_data: return None
        img_b64 = base64.b64encode(img_data).decode()
        res = requests.post('https://api.imgbb.com/1/upload', data={'key':IMGBB_API_KEY,'image':img_b64},timeout=10)
        return res.json()['data']['url'] if res.status_code==200 else None
    except: return None

# ---------- Роуты ----------
@app.route('/')
def index(): return send_from_directory(BASE_DIR, 'index.html')
@app.route('/<path:filename>')
def serve_static(filename):
    path=os.path.join(BASE_DIR,filename)
    return send_from_directory(BASE_DIR,filename) if os.path.exists(path) else send_from_directory(BASE_DIR,'index.html')

# --- Регистрация ---
@app.route('/api/register', methods=['POST'])
def register():
    try:
        conn=get_db(); cursor=conn.cursor()
        if request.content_type.startswith('multipart/form-data'):
            name=request.form.get('name','').strip()
            phone=request.form.get('phone','').strip()
            password=request.form.get('password','')
            avatar_file=request.files.get('avatar')
        else:
            data=request.get_json()
            name=data.get('name','').strip()
            phone=data.get('phone','').strip()
            password=data.get('password','')
            avatar_file=None
        if not name or not phone or not password: return jsonify({"success":False,"message":"Заполни все поля"}),400
        if len(password)<4: return jsonify({"success":False,"message":"Пароль короткий"}),400
        cursor.execute('SELECT id FROM users WHERE phone=?',(phone,))
        if cursor.fetchone(): return jsonify({"success":False,"message":"Телефон уже зарегистрирован"}),400
        avatar_url='https://i.ibb.co/0jQjZfV/default-avatar.jpg'
        if avatar_file: uploaded_url=upload_to_imgbb(avatar_file); avatar_url=uploaded_url if uploaded_url else avatar_url
        user_id=str(uuid.uuid4()); cursor.execute('INSERT INTO users(id,name,phone,password_hash,avatar) VALUES(?,?,?,?,?)',(user_id,name,phone,hash_password(password),avatar_url))
        conn.commit(); conn.close()
        return jsonify({"success":True,"message":"Аккаунт создан!","user":{"id":user_id,"name":name,"avatar":avatar_url}})
    except: return jsonify({"success":False,"message":"Ошибка сервера"}),500

# --- Логин ---
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data=request.get_json(); phone=data.get('phone','').strip(); password=data.get('password','')
        if not phone or not password: return jsonify({"success":False,"message":"Заполни все поля"}),400
        conn=get_db(); cursor=conn.cursor()
        cursor.execute('SELECT id,name,avatar,password_hash FROM users WHERE phone=?',(phone,))
        user=cursor.fetchone(); conn.close()
        if user and user['password_hash']==hash_password(password):
            return jsonify({"success":True,"user":{"id":user['id'],"name":user['name'],"avatar":user['avatar']}})
        return jsonify({"success":False,"message":"Неверный телефон или пароль"}),401
    except: return jsonify({"success":False,"message":"Ошибка сервера"}),500

# --- Посты ---
@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        conn=get_db(); cursor=conn.cursor()
        cursor.execute('''
            SELECT p.*,GROUP_CONCAT(l.user_id) as liked_by_user_ids,COUNT(l.user_id) as like_count
            FROM posts p LEFT JOIN likes l ON p.id=l.post_id
            GROUP BY p.id ORDER BY p.created_at DESC
        ''')
        posts=cursor.fetchall(); result=[]
        for post in posts:
            cursor.execute('SELECT c.* FROM comments c WHERE c.post_id=? ORDER BY c.created_at ASC',(post['id'],))
            comments=cursor.fetchall()
            result.append({
                "id":post['id'],
                "userId":post['user_id'],
                "userName":post['user_name'],
                "userAvatar":post['user_avatar'] or 'https://i.ibb.co/0jQjZfV/default-avatar.jpg',
                "photoUrl":post['photo_url'],
                "likes":post['like_count'] or 0,
                "likedBy":post['liked_by_user_ids'].split(',') if post['liked_by_user_ids'] else [],
                "comments":[{"name":c['user_name'],"text":c['text']} for c in comments],
                "createdAt":post['created_at']
            })
        conn.close(); return jsonify(result)
    except: return jsonify([])

@app.route('/api/posts', methods=['POST'])
def create_post():
    try:
        if 'photo' not in request.files: return jsonify({"success":False,"message":"Нет фото"}),400
        photo_file=request.files['photo']; user_id=request.form.get('userId')
        if not user_id: return jsonify({"success":False,"message":"Нет userId"}),400
        conn=get_db(); cursor=conn.cursor()
        cursor.execute('SELECT name,avatar FROM users WHERE id=?',(user_id,))
        user=cursor.fetchone(); 
        if not user: return jsonify({"success":False,"message":"Пользователь не найден"}),404
        photo_url=upload_to_imgbb(photo_file); 
        if not photo_url: return jsonify({"success":False,"message":"Ошибка загрузки фото"}),500
        post_id=str(uuid.uuid4())
        cursor.execute('INSERT INTO posts(id,user_id,user_name,user_avatar,photo_url) VALUES(?,?,?,?,?)',(post_id,user_id,user['name'],user['avatar'],photo_url))
        conn.commit(); conn.close()
        return jsonify({"success":True,"message":"Пост опубликован"})
    except: return jsonify({"success":False,"message":"Ошибка сервера"}),500

# ---------- Запуск ----------
if __name__=="__main__":
    init_db()
    port=int(os.environ.get("PORT",3000))
    app.run(host='0.0.0.0',port=port)
