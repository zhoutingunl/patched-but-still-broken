from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
from anime_generator import AnimeGenerator
import threading
import uuid

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

def generate_anime_async(task_id, novel_path, max_scenes, api_key, provider='qiniu'):
    try:
        generation_status[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': '正在解析小说...'
        }
        
        generator = AnimeGenerator(openai_api_key=api_key, provider=provider)
        metadata = generator.generate_from_novel(novel_path, max_scenes=max_scenes)
        
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
        
        max_scenes = request.form.get('max_scenes', type=int)
        api_key = request.form.get('api_key', '')
        provider = request.form.get('api_provider', 'qiniu')
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': '需要提供 API Key'}), 400
        
        thread = threading.Thread(
            target=generate_anime_async,
            args=(task_id, file_path, max_scenes, api_key, provider)
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
