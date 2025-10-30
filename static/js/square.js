let scenes = [];
let currentSceneIndex = 0;
let isPlaying = false;
let audioPlayer = null;
let currentTaskId = null;
let currentInputText = null;

document.addEventListener('DOMContentLoaded', function() {
    audioPlayer = document.getElementById('audio-player');
    checkAuthentication();
    initializeEventListeners();
    loadSharedRecords();
});

function initializeEventListeners() {
    const playPauseBtn = document.getElementById('play-pause-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const stopBtn = document.getElementById('stop-btn');
    const volumeSlider = document.getElementById('volume-slider');
    const logoutBtn = document.getElementById('logout-btn');
    const downloadBtn = document.getElementById('download-btn');
    const backHomeBtn = document.getElementById('back-home-btn');

    if (playPauseBtn) playPauseBtn.addEventListener('click', togglePlayPause);
    if (prevBtn) prevBtn.addEventListener('click', () => navigateScene(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateScene(1));
    if (stopBtn) stopBtn.addEventListener('click', stopPlayback);
    if (volumeSlider) volumeSlider.addEventListener('input', handleVolumeChange);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownload);
    if (backHomeBtn) backHomeBtn.addEventListener('click', () => window.location.href = '/');

    if (audioPlayer) audioPlayer.addEventListener('ended', handleAudioEnded);
}

async function loadSharedRecords() {
    try {
        const response = await fetch('/api/shared_records', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (response.ok) {
            displaySharedList(data.records);
        }
    } catch (error) {
        console.error('获取共享记录失败:', error);
    }
}

function displaySharedList(records) {
    const sharedList = document.getElementById('shared-list');
    
    if (!records || records.length === 0) {
        sharedList.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">暂无分享记录</div>';
        return;
    }
    
    sharedList.innerHTML = '';
    
    records.forEach(record => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.dataset.sessionId = record.session_id;
        item.dataset.inputText = record.input_text || '';
        
        const title = document.createElement('div');
        title.className = 'history-item-title';
        let displayText;
        if (record.input_text) {
            displayText = record.input_text.substring(0, 10).trim();
            if (record.input_text.length > 10) displayText += '...';
        } else {
            displayText = '未命名';
        }
        title.textContent = displayText;
        
        const userInfo = document.createElement('div');
        userInfo.className = 'history-item-time';
        userInfo.textContent = `作者: ${record.username}`;
        
        item.appendChild(title);
        item.appendChild(userInfo);
        
        item.addEventListener('click', () => {
            if (record.session_id && record.generated_scene_count > 0) {
                loadPlayback(record.session_id, record.input_text);
                document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
            }
        });
        
        sharedList.appendChild(item);
    });
}

async function loadPlayback(sessionId, inputText = null) {
    try {
        const response = await fetch(`/api/scenes/${sessionId}`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            scenes = data.scenes;
            currentSceneIndex = 0;
            currentTaskId = sessionId;
            currentInputText = inputText;

            document.getElementById('welcome-section').style.display = 'none';
            document.getElementById('player-section').classList.remove('hidden');

            updateContentHeader();
            displayScene(0);
        } else {
            alert('加载作品失败: ' + data.error);
        }
    } catch (error) {
        alert('加载作品失败: ' + error.message);
    }
}

function displayScene(index) {
    if (index < 0 || index >= scenes.length) return;

    currentSceneIndex = index;
    const scene = scenes[index];

    const sceneImage = document.getElementById('scene-image');
    const sceneText = document.getElementById('scene-text');
    const sceneCounter = document.getElementById('scene-counter');
    const sceneCharacters = document.getElementById('scene-characters');
    const sceneShotType = document.getElementById('scene-shot-type');
    const sceneMood = document.getElementById('scene-mood');

    const imgElement = document.getElementById('scene-image');
    imgElement.src = scene.image_url;
    
    sceneText.textContent = scene.text;
    sceneCounter.textContent = `分镜 ${index + 1} / ${scenes.length}`;
    
    if (sceneShotType && scene.shot_type) {
        sceneShotType.textContent = `📷 ${scene.shot_type}`;
    } else if (sceneShotType) {
        sceneShotType.textContent = '';
    }
    
    if (sceneMood && scene.mood) {
        const moodEmojis = {
            'happy': '😊',
            'sad': '😢',
            'tense': '😰',
            'calm': '😌',
            'surprised': '😲',
            'angry': '😠'
        };
        const emoji = moodEmojis[scene.mood] || '😐';
        sceneMood.textContent = `${emoji} ${scene.mood}`;
    } else if (sceneMood) {
        sceneMood.textContent = '';
    }
    
    if (scene.characters && scene.characters.length > 0) {
        sceneCharacters.textContent = `👥 ${scene.characters.join('、')}`;
    } else {
        sceneCharacters.textContent = '';
    }

    audioPlayer.src = scene.audio_url;

    const sceneCard = document.getElementById('scene-card');
    sceneCard.style.animation = 'none';
    setTimeout(() => {
        sceneCard.style.animation = 'fadeIn 0.5s ease';
    }, 10);
}

function togglePlayPause() {
    if (isPlaying) {
        pausePlayback();
    } else {
        startPlayback();
    }
}

function startPlayback() {
    isPlaying = true;
    document.getElementById('play-pause-btn').textContent = '⏸ 暂停';
    
    audioPlayer.play().catch(error => {
        console.error('音频播放失败:', error);
        isPlaying = false;
        document.getElementById('play-pause-btn').textContent = '▶️ 播放';
    });
}

function pausePlayback() {
    isPlaying = false;
    audioPlayer.pause();
    document.getElementById('play-pause-btn').textContent = '▶️ 播放';
}

function stopPlayback() {
    isPlaying = false;
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    document.getElementById('play-pause-btn').textContent = '▶️ 播放';
}

function navigateScene(direction) {
    const newIndex = currentSceneIndex + direction;
    
    if (newIndex >= 0 && newIndex < scenes.length) {
        stopPlayback();
        displayScene(newIndex);
    }
}

function handleAudioEnded() {
    if (currentSceneIndex < scenes.length - 1) {
        navigateScene(1);
        setTimeout(() => {
            startPlayback();
        }, 500);
    } else {
        isPlaying = false;
        document.getElementById('play-pause-btn').textContent = '▶️ 播放';
    }
}

function handleVolumeChange(event) {
    const volume = event.target.value;
    audioPlayer.volume = volume / 100;
    document.getElementById('volume-value').textContent = volume + '%';
}

async function checkAuthentication() {
    try {
        const response = await fetch('/api/current_user', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.user) {
            document.getElementById('username-display').textContent = `欢迎，${data.user.username}`;
            document.getElementById('logout-btn').style.display = 'inline-block';
        } else {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('验证失败:', error);
        window.location.href = '/login';
    }
}

async function handleLogout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('退出失败:', error);
    }
}

function updateContentHeader() {
    const headerTextEl = document.getElementById('content-header-text');
    if (headerTextEl && currentInputText) {
        headerTextEl.textContent = currentInputText;
        headerTextEl.style.display = 'block';
    } else if (headerTextEl) {
        headerTextEl.style.display = 'none';
    }
}

async function handleDownload() {
    if (!currentTaskId || scenes.length === 0) {
        alert('没有可下载的内容');
        return;
    }

    const progressOverlay = document.createElement('div');
    progressOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    const progressBox = document.createElement('div');
    progressBox.style.cssText = `
        background: white;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        min-width: 300px;
    `;
    
    progressBox.innerHTML = `
        <h3 style="margin-top: 0; color: #333;">正在生成视频...</h3>
        <div style="margin: 20px 0;">
            <div style="width: 100%; height: 30px; background: #f0f0f0; border-radius: 15px; overflow: hidden;">
                <div id="download-progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049); transition: width 0.3s;"></div>
            </div>
        </div>
        <p id="download-progress-text" style="color: #666; margin: 10px 0;">正在合并场景...</p>
    `;
    
    progressOverlay.appendChild(progressBox);
    document.body.appendChild(progressOverlay);
    
    const progressBar = progressBox.querySelector('#download-progress-bar');
    const progressText = progressBox.querySelector('#download-progress-text');
    
    let progress = 0;
    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
            
            if (progress < 30) {
                progressText.textContent = '正在合并场景...';
            } else if (progress < 60) {
                progressText.textContent = '正在处理视频...';
            } else {
                progressText.textContent = '即将完成...';
            }
        }
    }, 500);

    try {
        const downloadUrl = `/api/download/${currentTaskId}`;
        
        const response = await fetch(downloadUrl, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('下载失败');
        }
        
        const blob = await response.blob();
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressText.textContent = '下载完成！';
        
        setTimeout(() => {
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `anime_${currentTaskId}.mp4`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
            
            document.body.removeChild(progressOverlay);
        }, 500);
    } catch (error) {
        clearInterval(progressInterval);
        document.body.removeChild(progressOverlay);
        alert('下载失败: ' + error.message);
    }
}
