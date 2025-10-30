import os
import sys
import json
import logging
import threading
import uuid
from functools import wraps
from gevent.pywsgi import WSGIServer

from werkzeug.utils import secure_filename
from anime_generator import AnimeGenerator
from video_merger import VideoMerger

from common import get_base_dir
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, send_file
from flask_cors import CORS
from statistics_db import insert_statistics, update_generation_stats, get_statistics, delete_statistics, share_record, get_shared_records
from user_auth import register_user, login_user, get_user_by_id, get_user_video_count, increment_user_video_count


class FlaskAppWrapper:
    def __init__(self, name, port=5000):
        self.app_ = Flask(name, static_folder='static', template_folder='templates')
        self.app_.secret_key = os.urandom(24)
        CORS(self.app_, supports_credentials=True)
        
        self.port_ = port
        self.upload_folder_ = os.path.join(get_base_dir(), 'uploads')
        self.allowed_extensions_ = {'txt'}
        self.app_.config['UPLOAD_FOLDER'] = self.upload_folder_
        self.app_.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        
        os.makedirs(self.upload_folder_, exist_ok=True)
        self.generation_status_ = {}
        
        self._register_routes()
        logging.info(f"Flask is started on http://127.0.0.1:{self.port_}")
    
    def _register_routes(self):
        self.app_.add_url_rule('/', view_func=self.index, methods=['GET'])
        self.app_.add_url_rule('/home', view_func=self.home_page, methods=['GET'])
        self.app_.add_url_rule('/login', view_func=self.login_page, methods=['GET'])
        self.app_.add_url_rule('/settings', view_func=self.settings, methods=['GET'])
        self.app_.add_url_rule('/square', view_func=self.square_page, methods=['GET'])
        self.app_.add_url_rule('/favicon.ico', view_func=self.get_favicon, methods=['GET'])
        self.app_.add_url_rule('/api/register', view_func=self.register, methods=['POST'])
        self.app_.add_url_rule('/api/login', view_func=self.login, methods=['POST'])
        self.app_.add_url_rule('/api/logout', view_func=self.logout, methods=['POST'])
        self.app_.add_url_rule('/api/current_user', view_func=self.current_user, methods=['GET'])
        self.app_.add_url_rule('/api/history', view_func=self.get_history, methods=['GET'])
        self.app_.add_url_rule('/api/check_payment', view_func=self.check_payment, methods=['POST'])
        self.app_.add_url_rule('/api/upload', view_func=self.upload_novel, methods=['POST'])
        self.app_.add_url_rule('/api/status/<task_id>', view_func=self.get_status, methods=['GET'])
        self.app_.add_url_rule('/api/scenes/<task_id>', view_func=self.get_scenes, methods=['GET'])
        self.app_.add_url_rule('/api/file/<path:filepath>', view_func=self.serve_file, methods=['GET'])
        self.app_.add_url_rule('/api/download/<task_id>', view_func=self.download_content, methods=['GET'])
        self.app_.add_url_rule('/api/delete_history/<session_id>', view_func=self.delete_history, methods=['DELETE'])
        self.app_.add_url_rule('/api/share/<session_id>', view_func=self.share_history, methods=['POST'])
        self.app_.add_url_rule('/api/shared_records', view_func=self.get_shared_records_api, methods=['GET'])
        self.app_.add_url_rule('/get_apk', view_func=self.get_apk, methods=['GET'])

    def get_apk(self):
        return send_from_directory(os.path.join(get_base_dir(), 'apk_dir'), 'novel2video_release.apk', mimetype='application/vnd.android.package-archive')

    def _allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions_
    
    def _login_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': '请先登录'}), 401
            return f(*args, **kwargs)
        return decorated_function
    
    def _generate_anime_async(self, task_id, novel_path, max_scenes, api_key, provider='qiniu', custom_prompt=None, use_ai_analysis=True, use_storyboard=True, user_id=None):
        def update_status(progress, message):
            self.generation_status_[task_id] = {
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
                use_ai_analysis=use_ai_analysis,
                session_id=task_id
            )
            
            update_status(5, '开始分析小说内容...')
            
            metadata = generator.generate_from_novel(
                novel_path, 
                max_scenes=max_scenes, 
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
            
            self.generation_status_[task_id] = {
                'status': 'completed',
                'progress': 100,
                'message': '生成完成',
                'metadata': metadata
            }
        except Exception as e:
            self.generation_status_[task_id] = {
                'status': 'error',
                'progress': 0,
                'message': str(e)
            }
    
    def index(self):
        return redirect(url_for('square_page'))
    
    def home_page(self):
        return render_template('index.html')
    
    def login_page(self):
        return render_template('login.html')
    
    def settings(self):
        return render_template('settings.html')
    
    def square_page(self):
        return render_template('square.html')
    
    def get_favicon(self):
        return send_from_directory(os.path.join(self.app_.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    def register(self):
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        success, message = register_user(username, password)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
    
    def login(self):
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
    
    def logout(self):
        session.clear()
        return jsonify({'message': '已退出登录'}), 200
    
    def current_user(self):
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
            if user:
                return jsonify({'user': {'username': user['username']}}), 200
        return jsonify({'user': None}), 200
    
    def get_history(self):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session.get('username')
        history = get_statistics(username=username, limit=10)
        return jsonify({'history': history}), 200
    
    def delete_history(self, session_id):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session.get('username')
        success = delete_statistics(session_id, username)
        
        if success:
            return jsonify({'message': '删除成功'}), 200
        else:
            return jsonify({'error': '删除失败或记录不存在'}), 404
    
    def share_history(self, session_id):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session.get('username')
        success, message = share_record(session_id, username)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
    
    def get_shared_records_api(self):
        records = get_shared_records(limit=50)
        return jsonify({'records': records}), 200
    
    def check_payment(self):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
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
    
    def upload_novel(self):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        if 'novel' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['novel']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file and self._allowed_file(file.filename):
            filename = secure_filename(file.filename)
            task_id = str(uuid.uuid4())
            file_path = os.path.join(self.app_.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
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
                filename=filename,
                input_text=content if filename == 'novel.txt' else None
            )
            
            max_scenes = request.form.get('max_scenes', type=int)
            api_key = request.form.get('api_key', '')
            provider = request.form.get('api_provider', 'qiniu')
            custom_prompt = request.form.get('custom_prompt', '')
            use_ai_analysis = request.form.get('use_ai_analysis', 'true').lower() == 'true'
            use_storyboard = request.form.get('use_storyboard', 'true').lower() == 'true'
            
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                return jsonify({'error': '需要提供 API Key'}), 400
            
            user_id = session.get('user_id')
            thread = threading.Thread(
                target=self._generate_anime_async,
                args=(task_id, file_path, max_scenes, api_key, provider, custom_prompt, use_ai_analysis, use_storyboard, user_id)
            )
            thread.start()
            
            return jsonify({
                'task_id': task_id,
                'message': '开始处理小说'
            })
        
        return jsonify({'error': '不支持的文件类型'}), 400
    
    def get_status(self, task_id):
        if task_id not in self.generation_status_:
            return jsonify({'error': '任务不存在'}), 404
        
        return jsonify(self.generation_status_[task_id])
    
    def get_scenes(self, task_id):
        metadata = None
        
        if task_id in self.generation_status_:
            status = self.generation_status_[task_id]
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
                    scenes.append(scene_data)
        
        return jsonify({
            'total_scenes': len(scenes),
            'scenes': scenes
        })
    
    def serve_file(self, filepath):
        if not filepath.startswith('/'):
            filepath = '/' + filepath
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        return send_from_directory(directory, filename)
    
    def download_content(self, task_id):
        metadata = None
        
        if task_id in self.generation_status_:
            status = self.generation_status_[task_id]
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
        
        scenes = metadata.get('scenes', [])
        
        if not scenes:
            return jsonify({'error': '没有可下载的内容'}), 404
        
        try:
            scene_folders = [scene_info['folder'] for scene_info in scenes]

            temp_video_dir = os.path.join(get_base_dir(), 'temp_videos')
            os.makedirs(temp_video_dir, exist_ok=True)

            output_video_path = os.path.join(temp_video_dir, f'merged_{task_id}.mp4')

            if os.path.exists(output_video_path):
                return send_file(
                    output_video_path,
                    mimetype='video/mp4',
                    as_attachment=True,
                    download_name=f'anime_{task_id}.mp4'
                )
            
            merger = VideoMerger()
            success = merger.merge_scene_videos(scene_folders, output_video_path)
            
            if not success:
                return jsonify({'error': '视频合并失败'}), 500
            
            return send_file(
                output_video_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f'anime_{task_id}.mp4'
            )
            
        except Exception as e:
            logging.error(f"下载失败: {e}")
            return jsonify({'error': f'下载失败: {str(e)}'}), 500
    
    def run(self, debug=True, host='0.0.0.0'):
        self.app_.run(debug=debug, host=host, port=self.port_)


def main(port):
    server = FlaskAppWrapper('novel_to_anime', port=port)
    WSGIServer(('0.0.0.0', server.port_), server.app_).serve_forever()

if __name__ == '__main__':
    format_config_str = '%(asctime)s %(levelname)-6s [%(threadName)s] %(message)s'
    logging.basicConfig(format=format_config_str, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
    port = 80 if sys.platform == 'linux' else 5005
    main(port)
