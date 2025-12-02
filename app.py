from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from datetime import datetime
import os
import base64

app = Flask(__name__)
app.secret_key = '12345678910'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # app.py がある場所
PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'photos')        # /home/user/mysite/static/photos
os.makedirs(PHOTOS_DIR, exist_ok=True)

def matchuser(un,ps):
    con = sqlite3.connect('ui.db')
    cur = con.cursor()
    cur.execute('select * from user where username=? and password=?',[un,ps])
    result = cur.fetchone()
    return result

# データベース初期化
def init_db():
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    
    # ユーザーテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS user
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL)''')
    
    # TODOテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS todos
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                deleted BOOLEAN NOT NULL DEFAULT 0,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user (id))''')
    
    # 既存のテーブルにdeletedカラムを追加（エラーが出ても無視）
    try:
        c.execute('ALTER TABLE todos ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # カラムが既に存在する場合は無視
    
    # 写真テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS photos
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                image_path TEXT NOT NULL,
                type TEXT NOT NULL,
                date TEXT NOT NULL,
                completed_todos TEXT,
                FOREIGN KEY (user_id) REFERENCES user (id))''')
    
    # 既存のテーブルにcompleted_todosカラムを追加
    try:
        c.execute('ALTER TABLE photos ADD COLUMN completed_todos TEXT')
    except sqlite3.OperationalError:
        pass  # カラムが既に存在する場合は無視
    
    # 豆知識テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS tips_posts
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL)''')
    
    # テストユーザーの追加
    try:
        c.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                 ('test', 'test123'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # ユーザーが既に存在する場合は無視

    conn.commit()
    conn.close()

# アプリ起動時にDB初期化
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        
        # ユーザー名の重複チェック
        c.execute('SELECT * FROM user WHERE username = ?', (username,))
        if c.fetchone() is not None:
            conn.close()
            return render_template('register.html', error='このユーザー名は既に使用されています')
        
        # 新規ユーザーの登録
        c.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                 (username, password))
        conn.commit()
        conn.close()
        
        return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        un = request.form['username']
        ps = request.form['password']
        reda = matchuser(un,ps)
        if reda is not None:
            session['user_id'] = reda[0]  # ユーザーIDをセッションに保存
            return redirect(url_for('main'))  # topをmainに変更
        else:
            return render_template('login.html')

@app.route('/main')
def main():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template('main.html')

@app.route('/todo')
def todo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    # 削除されていないTODOのみ表示
    c.execute('''SELECT t.* FROM todos t
                WHERE t.user_id = ? AND t.deleted = 0
                ORDER BY t.date DESC''', (session['user_id'],))
    todos = [{'id': row[0], 'text': row[2], 'completed': row[3], 'date': row[4]} for row in c.fetchall()]
    conn.close()
    
    return render_template('todo.html', todos=todos)

@app.route('/add_todo', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
        
    data = request.get_json()
    text = data.get('text')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('INSERT INTO todos (user_id, text, completed, date) VALUES (?, ?, ?, ?)',
              (session['user_id'], text, False, date))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/toggle_todo', methods=['POST'])
def toggle_todo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
        
    data = request.get_json()
    todo_id = data.get('id')
    
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('UPDATE todos SET completed = NOT completed WHERE id = ? AND user_id = ?',
              (todo_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/delete_todo', methods=['POST'])
def delete_todo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    data = request.get_json()
    todo_id = data.get('id')

    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', (todo_id, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route("/camera")
def camera():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("camera.html")

@app.route('/save_photo', methods=['POST'])
def save_photo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
        
    data = request.get_json()
    image_data = data['image'].split(',')[1]  # Base64データを取得
    photo_type = request.args.get('type', 'before')  # before/after

    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'photo_{session["user_id"]}_{timestamp}.png'

    # ファイルシステム上の保存先（絶対パス）
    save_path = os.path.join(PHOTOS_DIR, filename)

    # DB に保存するパス（static からの相対パス）
    db_image_path = f'photos/{filename}'

    # 画像を保存
    with open(save_path, 'wb') as f:
        f.write(base64.b64decode(image_data))

    # --- 以降はほぼそのまま。INSERT の image_path だけ変更 ---
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()

    completed_todos = ""
    if photo_type == 'after':
        c.execute('SELECT text FROM todos WHERE user_id = ? AND completed = 1 AND deleted = 0',
                  (session['user_id'],))
        completed_todo_list = [row[0] for row in c.fetchall()]
        completed_todos = ','.join(completed_todo_list)

        c.execute('UPDATE todos SET deleted = 1 WHERE user_id = ? AND completed = 1 AND deleted = 0',
                  (session['user_id'],))

    c.execute('INSERT INTO photos (user_id, image_path, type, date, completed_todos) '
              'VALUES (?, ?, ?, ?, ?)',
              (session['user_id'], db_image_path, photo_type,
               datetime.now().strftime("%Y-%m-%d"), completed_todos))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route("/album")
def album():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('''SELECT id, image_path, type, date, completed_todos
                 FROM photos 
                 WHERE user_id = ?
                 ORDER BY date DESC''', (session['user_id'],))

    photos = []
    for photo_id, image_path, photo_type, photo_date, completed_todos in c.fetchall():
        # 互換対応：もし "static/" から始まっていたら削る
        if image_path.startswith('static/'):
            image_path = image_path[len('static/'):]

        todos = completed_todos.split(',') if completed_todos else []
        todos = [todo.strip() for todo in todos if todo.strip()]

        photos.append({
            'url': url_for('static', filename=image_path),
            'type': photo_type,
            'date': photo_date,
            'time': datetime.strptime(photo_date, '%Y-%m-%d').strftime('%Y年%m月%d日'),
            'todos': todos
        })

    conn.close()
    return render_template("album.html", photos=photos)

@app.route('/tips', methods=['GET', 'POST'])
def tips():
    # 投稿ページ: GET で一覧表示、POST で投稿
    if request.method == 'POST':
        # ログイン必須
        if 'user_id' not in session:
            return redirect(url_for('login'))

        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if title and content:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect('ui.db')
            c = conn.cursor()
            c.execute('INSERT INTO tips_posts (title, content, created_at) VALUES (?, ?, ?)',
                      (title, content, created_at))
            conn.commit()
            conn.close()
            flash('投稿しました')
        return redirect(url_for('tips'))

    # GET: 投稿一覧を取得して表示
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('SELECT id, title, content, created_at FROM tips_posts ORDER BY id DESC')
    posts = [{'id': row[0], 'title': row[1], 'content': row[2], 'created_at': row[3]} for row in c.fetchall()]
    conn.close()
    return render_template('tips.html', posts=posts, year=datetime.now().year)

@app.route('/delete_tip', methods=['POST'])
def delete_tip():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        tip_id = data.get('id')
        
        if tip_id is None:
            return jsonify({'success': False, 'error': 'IDが指定されていません'}), 400
        
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        c.execute('DELETE FROM tips_posts WHERE id = ?', (tip_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'ヒントが削除されました'})
        
    except Exception as e:
        print(f"削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)