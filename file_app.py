from flask import Flask, redirect, request, session
from flask import render_template, send_file
import os, json, time, uuid
from tinydb import TinyDB, where, Query
from functools import wraps

BASE_DIR = os.path.dirname(__file__)
FILES_DIR = BASE_DIR + '/files'
DATA_FILE = BASE_DIR + '/data/data.json'

app = Flask(__name__)
app.secret_key = 'secret key'
MASTER_PW = 'abcd'  #　管理用パスワード

# ユーザー名とパスワードの一覧
USER_LOGIN_LIST = {
    'aaa': 'aaaa',
    'bbb': 'bbbb',
    'ccc': 'cccc',
    'user': 'password'}

# ログインしているかの確認
def is_login():
    return 'login' in session

# ログインを試行する
def try_login(form):
    user = form.get('user', '')
    password = form.get('pw', '')
    if user not in USER_LOGIN_LIST: return False
    if USER_LOGIN_LIST[user] != password:
        return False
    session['login'] = user
    return True

# ユーザー名を得る
def get_user():
    return session['login'] if is_login() else '未ログイン'

# 全ユーザーの情報を得る
def get_allusers():
    return [u for u in USER_LOGIN_LIST ]

# ログアウトする
def try_logout():
    session.pop('login', None)

# ログイン状態を判定するデコレーター
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_login():
            return redirect('/login')
        return func(*args, **kwargs)
    return wrapper

# ログイン画面の表示
@app.route('/login')
def login():      
    return render_template('login_form.html')

@app.route('/login/try', methods=['POST'])
def login_try():
    ok = try_login(request.form)
    if not ok: return msg('ログイン失敗')
    return redirect('/')

@app.route('/logout')
def logout():
    try_logout()
    return msg('ログアウトしました')

 # ファイルの一覧とアップロード画面を表示
@app.route('/')
@login_required 
def index():
    return render_template('index.html',
            files = get_individual(),
            usernames = get_user())

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    # アップロードしたファイルのオブジェクト
    upfile = request.files.get('upfile', None)
    if upfile is None: return msg('アップロード失敗')
    if upfile.filename == '': return msg('アップロード失敗')
    # メタ情報を取得
    meta = {
        'username': get_user(),
        'memo': request.form.get('memo', 'なし'),
        'limit': int(request.form.get('limit', '1')),
        'count': int(request.form.get('count', '0')),
        'filename': upfile.filename       
    }
    if (meta['limit'] == 0):
        return msg('パラメーターが不正です')
    save_file(upfile, meta)
    # ダウンロード先の表示
    return render_template('info.html',
            meta=meta, mode='upload',
            url=request.host_url + 'download/' + meta['id'])

@app.route('/download/<id>')
def download(id):
    # URLが正しいか判定
    meta = get_data(id)
    if meta is None: return msg('パラメーターが不正です')
    # ダウンロードページを表示
    return render_template('info.html',
            meta=meta, mode='download',
            url=request.host_url + 'download_go/' + id)

@app.route('/download_go/<id>', methods=['POST'])
def download_go(id):
    # URLが正しいか判定
    meta = get_data(id)
    if meta is None: return msg('パラメーターが不正です')
    # ダウンロード回数、期限を確認後、ファイルを送信
    meta['count'] = meta['count'] - 1
    if meta['count'] < 0:
        return msg('ダウンロード回数を超えました')
    set_data(id, meta)
    if meta['time_limit'] < time.time():
        return msg('ダウンロードの期限が過ぎています')
    return send_file(meta['path'],
            as_attachment=True,
            download_name=meta['filename'])

# マスターパスワードを確認、全データを表示
@app.route('/admin/list')
def admin_list():
    if request.args.get('pw', '') != MASTER_PW:
        return msg('マスターパスワードが違います')
    return render_template('admin_list.html',
            files=get_all(), pw=MASTER_PW)

# ファイルとデータを削除
@app.route('/admin/remove/<id>')
def admin_remove(id):
    remove_data(id)
    return msg('削除しました')

# エラーメッセージ、ログアウト時メッセージを表示
def msg(s):
    return render_template('error.html', message=s)

# アップロードされたファイルとメタ情報の保存
def save_file(upfile, meta):
    id = 'FS_' + uuid.uuid4().hex
    upfile.save(FILES_DIR + '/' + id)
    db = TinyDB(DATA_FILE)
    meta['id'] = id
    term = meta['limit'] * 60 * 60 * 24
    meta['time_limit'] = time.time() + term
    db.insert(meta)
    return id

# データベースから任意のIDのデータを取り出す
def get_data(id):
    db = TinyDB(DATA_FILE)
    f = db.get(where('id') == id)
    if f is not None:
        f['path'] = FILES_DIR + '/' + id
    return f

# データを更新する
def set_data(id, meta):
    db = TinyDB(DATA_FILE)
    db.update(meta, where('id') == id)

# ユーザーごとのデータを取得する
def get_individual():
    db = TinyDB(DATA_FILE)
    return db.search(Query().username == get_user())

# 全てのデータを取得する
def get_all():
    db = TinyDB(DATA_FILE)
    return db.all()

# アップロードされたファイルとメタ情報の削除
def remove_data(id):
    path = FILES_DIR + '/' + id
    os.remove(path)
    db = TinyDB(DATA_FILE)
    db.remove(where('id') == id)

# 日時フォーマットを簡易表示するフィルター設定
def filter_datetime(tm):
    return time.strftime(
        '%Y/%m/%d %H:%M:%S',
        time.localtime(tm))

# フィルターをテンプレートエンジンに登録
app.jinja_env.filters['datetime'] = filter_datetime




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    


    
