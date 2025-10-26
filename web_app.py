import os
import sys
import json
import threading
import uuid

from werkzeug.utils import secure_filename
from anime_generator import AnimeGenerator

import jieba
from common import get_base_dir
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from statistics_db import insert_statistics, update_generation_stats, get_statistics
from user_auth import register_user, login_user, get_user_by_id, get_user_video_count, increment_user_video_count
from functools import wraps

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = os.path.join(get_base_dir(), 'uploads')
ALLOWED_EXTENSIONS = {'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

generation_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_anime_async(task_id, novel_path, max_scenes, api_key, provider='qiniu', custom_prompt=None, enable_video=False, use_ai_analysis=True, use_storyboard=True, user_id=None):
    def update_status(progress, message):
        generation_status[task_id] = {
            'status': 'processing',
            'progress': progress,
            'message': message
        }
    
    try:
        update_status(0, '正在解析小说...')
        
        generator = AnimeGenerator(
            openai_api_key=api_key, 
            provider=provider, 
            custom_prompt=custom_prompt, 
            enable_video=enable_video,
            use_ai_analysis=use_ai_analysis,
            session_id=task_id
        )
        
        update_status(5, '开始分析小说内容...')
        
        metadata = generator.generate_from_novel(
            novel_path, 
            max_scenes=max_scenes, 
            generate_video=enable_video,
            use_storyboard=use_storyboard,
            progress_callback=update_status
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
        
        update_generation_stats(task_id, generated_scene_count, generated_content_size, metadata)
        
        if user_id:
            increment_user_video_count(user_id)
        
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


@app.route('/favicon.ico')
def get_favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


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

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    username = session.get('username')
    history = get_statistics(username=username, limit=10)
    return jsonify({'history': history}), 200

@app.route('/api/check_payment', methods=['POST'])
@login_required
def check_payment():
    user_id = session.get('user_id')
    video_count = get_user_video_count(user_id)
    
    if video_count < 3:
        return jsonify({
            'requires_payment': False,
            'video_count': video_count,
            'remaining_free': 3 - video_count
        }), 200
    
    data = request.get_json()
    word_count = data.get('word_count', 0)
    
    payment_amount = round(word_count * 0.001, 2)
    
    return jsonify({
        'requires_payment': True,
        'video_count': video_count,
        'word_count': word_count,
        'payment_amount': payment_amount
    }), 200

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
        use_storyboard = request.form.get('use_storyboard', 'true').lower() == 'true'
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': '需要提供 API Key'}), 400
        
        user_id = session.get('user_id')
        thread = threading.Thread(
            target=generate_anime_async,
            args=(task_id, file_path, max_scenes, api_key, provider, custom_prompt, enable_video, use_ai_analysis, use_storyboard, user_id)
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
    metadata = None
    
    if task_id in generation_status:
        status = generation_status[task_id]
        if status['status'] != 'completed':
            return jsonify({'error': '任务未完成'}), 400
        metadata = status.get('metadata', {})
    else:
        db_record = get_statistics(session_id=task_id)
        if not db_record:
            return jsonify({'error': '任务不存在'}), 404
        
        if not db_record.get('metadata'):
            return jsonify({'error': '任务未完成或元数据不存在'}), 400
        
        metadata = json.loads(db_record['metadata'])
    
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

@app.route('/api/characters/<task_id>', methods=['GET'])
def get_characters(task_id):
    output_dir = os.path.join(get_base_dir(), "anime_output", task_id)
    resume_path = os.path.join(output_dir, 'resume_data.json')
    
    if not os.path.exists(resume_path):
        return jsonify({'error': '角色数据不存在'}), 404
    
    with open(resume_path, 'r', encoding='utf-8') as f:
        resume_data = json.load(f)
    
    character_portraits = resume_data.get('character_portraits', {})
    character_designs = resume_data.get('character_designs', {})
    
    characters = []
    for char_name, portrait_path in character_portraits.items():
        characters.append({
            'name': char_name,
            'image_url': f'/api/file/{portrait_path}',
            'design': character_designs.get(char_name, {})
        })
    
    return jsonify({'characters': characters})

@app.route('/api/characters/<task_id>/upload', methods=['POST'])
def upload_character_image(task_id):
    if 'character_name' not in request.form:
        return jsonify({'error': '缺少角色名称'}), 400
    
    if 'image' not in request.files:
        return jsonify({'error': '没有上传图片'}), 400
    
    char_name = request.form['character_name']
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    output_dir = os.path.join(get_base_dir(), "anime_output", task_id)
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"character_{char_name}_{secure_filename(image_file.filename)}"
    image_path = os.path.join(output_dir, filename)
    image_file.save(image_path)
    
    resume_path = os.path.join(output_dir, 'resume_data.json')
    if os.path.exists(resume_path):
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)
        
        resume_data['character_portraits'][char_name] = image_path
        
        with open(resume_path, 'w', encoding='utf-8') as f:
            json.dump(resume_data, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'message': '图片上传成功',
        'image_url': f'/api/file/{image_path}'
    })

@app.route('/api/generation/resume/<task_id>', methods=['POST'])
def resume_generation(task_id):
    output_dir = os.path.join(get_base_dir(), "anime_output", task_id)
    resume_path = os.path.join(output_dir, 'resume_data.json')
    
    if not os.path.exists(resume_path):
        return jsonify({'error': '恢复数据不存在'}), 404
    
    user_id = session.get('user_id')
    thread = threading.Thread(
        target=resume_generation_async,
        args=(task_id, resume_path, user_id)
    )
    thread.start()
    
    return jsonify({
        'message': '继续生成中',
        'task_id': task_id
    })

def resume_generation_async(task_id, resume_path, user_id=None):
    def update_status(progress, message):
        generation_status[task_id] = {
            'status': 'processing',
            'progress': progress,
            'message': message
        }
    
    try:
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)
        
        api_key = os.getenv('OPENAI_API_KEY')
        provider = 'qiniu'
        enable_video = resume_data.get('generate_video', False)
        
        generator = AnimeGenerator(
            openai_api_key=api_key,
            provider=provider,
            enable_video=enable_video,
            use_ai_analysis=True,
            session_id=task_id
        )
        
        update_status(40, '继续生成分镜和场景...')
        
        metadata = generator.continue_from_characters(
            resume_path=resume_path,
            progress_callback=update_status
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
        
        update_generation_stats(task_id, generated_scene_count, generated_content_size, metadata)
        
        if user_id:
            increment_user_video_count(user_id)
        
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


def main(port):
    app.run(debug=True, host='0.0.0.0', port=port)


if __name__ == '__main__':
    port = 80 if sys.platform == 'linux' else 5000
    main(port)


