from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
from anime_generator import AnimeGenerator
import threading
import uuid
import jieba
from statistics_db import insert_statistics, update_generation_stats, get_statistics
from user_auth import register_user, login_user, get_user_by_id, get_or_create_oauth_user
from functools import wraps
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
CORS(app, supports_credentials=True)

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

wechat = oauth.register(
    name='wechat',
    client_id=os.getenv('WECHAT_APP_ID'),
    client_secret=os.getenv('WECHAT_APP_SECRET'),
    authorize_url='https://open.weixin.qq.com/connect/qrconnect',
    access_token_url='https://api.weixin.qq.com/sns/oauth2/access_token',
    client_kwargs={'scope': 'snsapi_login'}
)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

generation_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_anime_async(task_id, novel_path, max_scenes, api_key, provider='qiniu', custom_prompt=None, enable_video=False, use_ai_analysis=True):
    try:
        generation_status[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': '正在解析小说...'
        }
        
        generator = AnimeGenerator(
            openai_api_key=api_key, 
            provider=provider, 
            custom_prompt=custom_prompt, 
            enable_video=enable_video,
            use_ai_analysis=use_ai_analysis
        )
        metadata = generator.generate_from_novel(
            novel_path, 
            max_scenes=max_scenes, 
            generate_video=enable_video
        )
        
        generated_scene_count = len(metadata.get('scenes', []))
        generated_content_size = 0
        for scene_info in metadata.get('scenes', []):
            scene_folder = scene_info['folder']
            if os.path.exists(scene_folder):
                for root, dirs, files in os.walk(scene_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        generated_content_size += os.path.getsize(file_path)
        
        update_generation_stats(task_id, generated_scene_count, generated_content_size)
        
        generation_status[task_id] = {
            'status': 'completed',
            'progress': 100,
            'message': '生成完成',
            'metadata': metadata
        }
    except Exception as e:
        generation_status[task_id] = {
            'status': 'error',
            'progress': 0,
            'message': str(e)
        }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    success, message = register_user(username, password)
    
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    success, user, message = login_user(username, password)
    
    if success:
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'message': message, 'user': {'username': user['username']}}), 200
    else:
        return jsonify({'error': message}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': '已退出登录'}), 200

@app.route('/api/current_user', methods=['GET'])
def current_user():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return jsonify({'user': {'username': user['username']}}), 200
    return jsonify({'user': None}), 200

@app.route('/api/login/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/api/authorize/google')
def google_authorize():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            return redirect('/login?error=google_auth_failed')
        
        oauth_id = user_info.get('sub')
        email = user_info.get('email')
        username = user_info.get('name', email.split('@')[0] if email else None)
        avatar_url = user_info.get('picture')
        
        success, user, message = get_or_create_oauth_user(
            oauth_provider='google',
            oauth_id=oauth_id,
            email=email,
            username=username,
            avatar_url=avatar_url
        )
        
        if success:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            return redirect(f'/login?error={message}')
    except Exception as e:
        return redirect(f'/login?error=google_auth_error')

@app.route('/api/login/wechat')
def wechat_login():
    redirect_uri = url_for('wechat_authorize', _external=True)
    return wechat.authorize_redirect(redirect_uri)

@app.route('/api/authorize/wechat')
def wechat_authorize():
    try:
        token = wechat.authorize_access_token()
        access_token = token.get('access_token')
        openid = token.get('openid')
        
        if not access_token or not openid:
            return redirect('/login?error=wechat_auth_failed')
        
        import requests
        user_info_url = f'https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={openid}'
        resp = requests.get(user_info_url)
        user_info = resp.json()
        
        if user_info.get('errcode'):
            return redirect(f'/login?error=wechat_userinfo_error')
        
        username = user_info.get('nickname')
        avatar_url = user_info.get('headimgurl')
        
        success, user, message = get_or_create_oauth_user(
            oauth_provider='wechat',
            oauth_id=openid,
            username=username,
            avatar_url=avatar_url
        )
        
        if success:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            return redirect(f'/login?error={message}')
    except Exception as e:
        return redirect(f'/login?error=wechat_auth_error')

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    username = session.get('username')
    history = get_statistics(username=username, limit=10)
    return jsonify({'history': history}), 200

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_novel():
    if 'novel' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['novel']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(file_path)
        
        client_address = request.remote_addr
        upload_file_count = 1
        upload_content_size = os.path.getsize(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            upload_text_chars = len(content)
        
        username = session.get('username')
        insert_statistics(
            session_id=task_id,
            client_address=client_address,
            upload_file_count=upload_file_count,
            upload_text_chars=upload_text_chars,
            upload_content_size=upload_content_size,
            username=username,
            filename=filename
        )
        
        max_scenes = request.form.get('max_scenes', type=int)
        api_key = request.form.get('api_key', '')
        provider = request.form.get('api_provider', 'qiniu')
        custom_prompt = request.form.get('custom_prompt', '')
        enable_video = request.form.get('enable_video', 'false').lower() == 'true'
        use_ai_analysis = request.form.get('use_ai_analysis', 'true').lower() == 'true'
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': '需要提供 API Key'}), 400
        
        thread = threading.Thread(
            target=generate_anime_async,
            args=(task_id, file_path, max_scenes, api_key, provider, custom_prompt, enable_video, use_ai_analysis)
        )
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': '开始处理小说'
        })
    
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    if task_id not in generation_status:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(generation_status[task_id])

@app.route('/api/scenes/<task_id>', methods=['GET'])
def get_scenes(task_id):
    if task_id not in generation_status:
        return jsonify({'error': '任务不存在'}), 404
    
    status = generation_status[task_id]
    if status['status'] != 'completed':
        return jsonify({'error': '任务未完成'}), 400
    
    metadata = status.get('metadata', {})
    scenes = []
    
    for scene_info in metadata.get('scenes', []):
        scene_folder = scene_info['folder']
        metadata_path = os.path.join(scene_folder, 'metadata.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                scene_data = json.load(f)
                
                scene_data['image_url'] = f"/api/file/{scene_folder}/scene.png"
                scene_data['audio_url'] = f"/api/file/{scene_folder}/narration.mp3"
                if scene_data.get('video_path'):
                    scene_data['video_url'] = f"/api/file/{scene_folder}/scene.mp4"
                scenes.append(scene_data)
    
    return jsonify({
        'total_scenes': len(scenes),
        'scenes': scenes
    })

@app.route('/api/file/<path:filepath>')
def serve_file(filepath):
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
