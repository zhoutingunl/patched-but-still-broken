from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
from anime_generator import AnimeGenerator
import threading
import uuid
import jieba
from statistics_db import insert_statistics, update_generation_stats

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

generation_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_anime_async(task_id, novel_path, max_scenes, api_key, provider='qiniu', custom_prompt=None, enable_video=False, use_ai_analysis=True, generate_storyboard=True):
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
            generate_video=enable_video,
            generate_storyboard=generate_storyboard
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/upload', methods=['POST'])
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
        
        insert_statistics(
            session_id=task_id,
            client_address=client_address,
            upload_file_count=upload_file_count,
            upload_text_chars=upload_text_chars,
            upload_content_size=upload_content_size
        )
        
        max_scenes = request.form.get('max_scenes', type=int)
        api_key = request.form.get('api_key', '')
        provider = request.form.get('api_provider', 'qiniu')
        custom_prompt = request.form.get('custom_prompt', '')
        enable_video = request.form.get('enable_video', 'false').lower() == 'true'
        use_ai_analysis = request.form.get('use_ai_analysis', 'true').lower() == 'true'
        generate_storyboard = request.form.get('generate_storyboard', 'true').lower() == 'true'
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': '需要提供 API Key'}), 400
        
        thread = threading.Thread(
            target=generate_anime_async,
            args=(task_id, file_path, max_scenes, api_key, provider, custom_prompt, enable_video, use_ai_analysis, generate_storyboard)
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
                
                if scene_data.get('storyboard_shots'):
                    scene_data['shot_urls'] = []
                    for shot in scene_data['storyboard_shots']:
                        shot_path = shot.get('path', '')
                        if shot_path:
                            shot['url'] = f"/api/file/{shot_path}"
                            scene_data['shot_urls'].append(shot)
                else:
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
    if not os.path.isabs(filepath):
        filepath = os.path.abspath(filepath)
    
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
