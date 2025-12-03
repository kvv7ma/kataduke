from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from datetime import datetime, timezone, timedelta
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
    c.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                display_name TEXT)''')
    
    # usersテーブルに新しいカラムを追加（既存テーブル用）
    try:
        c.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    except sqlite3.OperationalError:
        pass  # カラムが既に存在する場合は無視
    
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

    # 既存のテーブルにmarked_for_photoカラムを追加（エラーが出ても無視）
    try:
        c.execute('ALTER TABLE todos ADD COLUMN marked_for_photo BOOLEAN NOT NULL DEFAULT 0')
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
                user_id INTEGER,
                username TEXT,
                created_at TEXT NOT NULL)''')
    
    # tips_postsテーブルに新しいカラムを追加（既存テーブル用）
    try:
        c.execute('ALTER TABLE tips_posts ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass  # カラムが既に存在する場合は無視
    
    try:
        c.execute('ALTER TABLE tips_posts ADD COLUMN username TEXT')
    except sqlite3.OperationalError:
        pass  # カラムが既に存在する場合は無視
    
    # カスタムテンプレートテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS custom_templates
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category_name TEXT NOT NULL,
                tasks TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user (id))''')
    
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
    
    # 古いマークをクリーンアップ（写真保存されずに残ったmarked_for_photoを復元）
    c.execute('UPDATE todos SET marked_for_photo = 0 WHERE user_id = ? AND marked_for_photo = 1 AND deleted = 0',
              (session['user_id'],))
    conn.commit()
    
    # 削除されていない、かつマークされていないTODOのみ表示
    c.execute('''SELECT t.* FROM todos t
                WHERE t.user_id = ? AND t.deleted = 0 AND t.marked_for_photo = 0
                ORDER BY t.date DESC''', (session['user_id'],))
    todos = [{'id': row[0], 'text': row[2], 'completed': row[3], 'date': row[4]} for row in c.fetchall()]
    conn.close()
    
    return render_template('todo.html', todos=todos)


@app.route('/template')
def template_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('template.html')

@app.route('/custom')
def custom_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # ユーザーのカスタムテンプレートを取得
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('''SELECT id, category_name, tasks FROM custom_templates 
                 WHERE user_id = ? ORDER BY created_at DESC''', (session['user_id'],))
    
    templates = []
    for row in c.fetchall():
        template_id, category_name, tasks_str = row
        tasks = tasks_str.split('|||')  # タスクを分割
        templates.append({
            'id': template_id,
            'category_name': category_name,
            'tasks': tasks
        })
    
    conn.close()
    return render_template('custom.html', templates=templates)

@app.route('/add_custom_template', methods=['POST'])
def add_custom_template():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        category_name = data.get('category_name', '').strip()
        tasks = data.get('tasks', [])
        
        if not category_name or not tasks:
            return jsonify({'success': False, 'error': 'カテゴリ名とタスクは必須です'})
        
        # タスクを文字列に結合（区切り文字: |||）
        tasks_str = '|||'.join(tasks)
        
        jst = timezone(timedelta(hours=9))
        created_at = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        c.execute('''INSERT INTO custom_templates (user_id, category_name, tasks, created_at) 
                     VALUES (?, ?, ?, ?)''',
                  (session['user_id'], category_name, tasks_str, created_at))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"add_custom_template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_custom_template', methods=['POST'])
def delete_custom_template():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        template_id = data.get('id')
        
        if template_id is None:
            return jsonify({'success': False, 'error': 'IDが指定されていません'}), 400
        
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        c.execute('DELETE FROM custom_templates WHERE id = ? AND user_id = ?', 
                  (template_id, session['user_id']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"delete_custom_template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_todo', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
        
    data = request.get_json()
    text = data.get('text')
    jst = timezone(timedelta(hours=9))
    date = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('INSERT INTO todos (user_id, text, completed, date) VALUES (?, ?, ?, ?)',
              (session['user_id'], text, False, date))
    conn.commit()
    conn.close()
    
    # 新しいTODOを追加したので完了状態をクリア
    session.pop('all_todos_completed_at', None)
    
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
    
    # すべてのTODOが完了したかチェック
    c.execute('''SELECT COUNT(*) FROM todos 
                 WHERE user_id = ? AND deleted = 0 AND marked_for_photo = 0''',
              (session['user_id'],))
    total = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(*) FROM todos 
                 WHERE user_id = ? AND deleted = 0 AND marked_for_photo = 0 AND completed = 1''',
              (session['user_id'],))
    completed = c.fetchone()[0]
    
    # すべて完了したら完了時刻を記録
    if total > 0 and total == completed:
        jst = timezone(timedelta(hours=9))
        completion_time = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
        session['all_todos_completed_at'] = completion_time
    else:
        # 未完了のTODOがある場合はクリア
        session.pop('all_todos_completed_at', None)
    
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
    
    # TODOを削除したので完了状態をクリア
    session.pop('all_todos_completed_at', None)

    return jsonify({'success': True})


@app.route('/check_todos_status', methods=['GET'])
def check_todos_status():
    """すべてのTODOが完了しているかチェックし、背景画像を決定"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    
    # アクティブなTODO数を取得
    c.execute('''SELECT COUNT(*) FROM todos 
                 WHERE user_id = ? AND deleted = 0 AND marked_for_photo = 0''',
              (session['user_id'],))
    total = c.fetchone()[0]
    
    # 完了したTODO数を取得
    c.execute('''SELECT COUNT(*) FROM todos 
                 WHERE user_id = ? AND deleted = 0 AND marked_for_photo = 0 AND completed = 1''',
              (session['user_id'],))
    completed = c.fetchone()[0]
    
    conn.close()
    
    all_completed = (total > 0 and total == completed)
    completion_time = session.get('all_todos_completed_at', None)
    
    # 朝4時のリセット判定
    should_show_clear = False
    if all_completed and completion_time:
        try:
            jst = timezone(timedelta(hours=9))
            completed_dt = datetime.strptime(completion_time, '%Y-%m-%d %H:%M:%S')
            # JSTタイムゾーン情報を追加
            completed_dt = completed_dt.replace(tzinfo=jst)
            now = datetime.now(jst)
            
            # 完了時刻の翌日の4時を計算
            next_reset = completed_dt.replace(hour=4, minute=0, second=0, microsecond=0)
            if completed_dt.hour >= 4:
                # 4時以降に完了した場合は翌日の4時
                next_reset += timedelta(days=1)
            
            # 現在時刻がリセット時刻より前なら clear を表示
            should_show_clear = (now < next_reset)
            
            # リセット時刻を過ぎていたらセッションをクリア
            if not should_show_clear:
                session.pop('all_todos_completed_at', None)
                
        except Exception as e:
            print(f"時刻判定エラー: {e}")
            should_show_clear = False
    
    background = 'mainback_clear.png' if should_show_clear else 'mainback_dirty.png'
    
    return jsonify({
        'success': True,
        'all_completed': all_completed,
        'background': background,
        'total': total,
        'completed': completed
    })


@app.route('/mark_todos_for_photo', methods=['POST'])
def mark_todos_for_photo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    try:
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        # 完了済みかつ未削除のTODOを次の写真に紐づけるためにマーク（削除はしない）
        c.execute('UPDATE todos SET marked_for_photo = 1 WHERE user_id = ? AND completed = 1 AND deleted = 0',
                  (session['user_id'],))
        conn.commit()
        conn.close()
        
        # マークしたので完了状態をクリア（写真撮影後にリセット）
        session.pop('all_todos_completed_at', None)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"mark_todos_for_photo error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/restore_marked_todos', methods=['POST'])
def restore_marked_todos():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    try:
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        # マーク済みTODOのマークを解除（復元）
        c.execute('UPDATE todos SET marked_for_photo = 0 WHERE user_id = ? AND marked_for_photo = 1',
                  (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"restore_marked_todos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    jst = timezone(timedelta(hours=9))
    timestamp = datetime.now(jst).strftime('%Y%m%d_%H%M%S')
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
        # 先にユーザがOKを押した際にマークされた TODO を写真に紐づける
        c.execute('SELECT text FROM todos WHERE user_id = ? AND marked_for_photo = 1',
                  (session['user_id'],))
        completed_todo_list = [row[0] for row in c.fetchall()]
        completed_todos = ','.join(completed_todo_list)

        # 写真保存成功時にマーク済みTODOを削除し、マークを解除
        c.execute('UPDATE todos SET deleted = 1, marked_for_photo = 0 WHERE user_id = ? AND marked_for_photo = 1',
                  (session['user_id'],))

    c.execute('INSERT INTO photos (user_id, image_path, type, date, completed_todos) '
              'VALUES (?, ?, ?, ?, ?)',
              (session['user_id'], db_image_path, photo_type,
               datetime.now(jst).strftime("%Y-%m-%d"), completed_todos))

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
            'id': photo_id,
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
        
        # ユーザー名設定の処理
        if 'set_username' in request.form:
            display_name = request.form.get('display_name', '').strip()
            if display_name:
                conn = sqlite3.connect('ui.db')
                c = conn.cursor()
                c.execute('UPDATE users SET display_name = ? WHERE id = ?', 
                         (display_name, session['user_id']))
                conn.commit()
                conn.close()
                flash('ユーザー名を設定しました')
            return redirect(url_for('tips'))
        
        # TIPS投稿の処理
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if title and content:
            # ユーザーの表示名を取得
            conn = sqlite3.connect('ui.db')
            c = conn.cursor()
            c.execute('SELECT display_name FROM users WHERE id = ?', (session['user_id'],))
            user_data = c.fetchone()
            display_name = user_data[0] if user_data and user_data[0] else '匿名ユーザー'
            
            jst = timezone(timedelta(hours=9))
            created_at = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
            
            c.execute('INSERT INTO tips_posts (title, content, user_id, username, created_at) VALUES (?, ?, ?, ?, ?)',
                      (title, content, session['user_id'], display_name, created_at))
            conn.commit()
            conn.close()
            flash('投稿しました')
        return redirect(url_for('tips'))

    # GET: 投稿一覧を取得して表示
    conn = sqlite3.connect('ui.db')
    c = conn.cursor()
    c.execute('SELECT id, title, content, username, created_at FROM tips_posts ORDER BY id DESC')
    posts = [{'id': row[0], 'title': row[1], 'content': row[2], 'username': row[3] or '匿名ユーザー', 'created_at': row[4]} for row in c.fetchall()]
    
    # 現在のユーザーの表示名を取得
    current_user_display_name = None
    if 'user_id' in session:
        c.execute('SELECT display_name FROM users WHERE id = ?', (session['user_id'],))
        user_result = c.fetchone()
        if user_result and user_result[0]:
            display_name = user_result[0].strip()
            current_user_display_name = display_name if display_name else None
    
    conn.close()
    return render_template('tips.html', posts=posts, year=datetime.now().year, 
                         current_user_display_name=current_user_display_name)

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

@app.route('/delete_photo', methods=['POST'])
def delete_photo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        photo_id = data.get('id')
        
        if photo_id is None:
            return jsonify({'success': False, 'error': 'IDが指定されていません'}), 400
        
        conn = sqlite3.connect('ui.db')
        c = conn.cursor()
        
        # 削除前に画像パスを取得してファイルも削除
        c.execute('SELECT image_path FROM photos WHERE id = ? AND user_id = ?', (photo_id, session['user_id']))
        result = c.fetchone()
        
        if result:
            image_path = result[0]
            # ファイルシステムから画像ファイルを削除
            if image_path.startswith('static/'):
                file_path = os.path.join(BASE_DIR, image_path)
            else:
                file_path = os.path.join(PHOTOS_DIR, os.path.basename(image_path))
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # データベースからレコードを削除
            c.execute('DELETE FROM photos WHERE id = ? AND user_id = ?', (photo_id, session['user_id']))
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True, 'message': '写真が削除されました'})
        
    except Exception as e:
        print(f"削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)