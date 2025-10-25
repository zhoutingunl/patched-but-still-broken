let currentTaskId = null;
let scenes = [];
let currentSceneIndex = 0;
let isPlaying = false;
let audioPlayer = null;

document.addEventListener('DOMContentLoaded', function() {
    audioPlayer = document.getElementById('audio-player');
    checkAuthentication();
    initializeEventListeners();
    restoreFileInfo();
});

function initializeEventListeners() {
    const selectFileBtn = document.getElementById('select-file-btn');
    const novelFile = document.getElementById('novel-file');
    const startGenerateBtn = document.getElementById('start-generate-btn');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const stopBtn = document.getElementById('stop-btn');
    const volumeSlider = document.getElementById('volume-slider');
    const returnHomeBtn = document.getElementById('return-home-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const historyBtn = document.getElementById('history-btn');
    const backToUploadBtn = document.getElementById('back-to-upload-btn');
    const downloadBtn = document.getElementById('download-btn');

    selectFileBtn.addEventListener('click', () => novelFile.click());
    
    novelFile.addEventListener('change', handleFileSelect);
    startGenerateBtn.addEventListener('click', handleStartGenerate);
    playPauseBtn.addEventListener('click', togglePlayPause);
    prevBtn.addEventListener('click', () => navigateScene(-1));
    nextBtn.addEventListener('click', () => navigateScene(1));
    stopBtn.addEventListener('click', stopPlayback);
    volumeSlider.addEventListener('input', handleVolumeChange);
    if (returnHomeBtn) {
        returnHomeBtn.addEventListener('click', returnToHome);
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    if (historyBtn) {
        historyBtn.addEventListener('click', showHistory);
    }
    if (backToUploadBtn) {
        backToUploadBtn.addEventListener('click', () => {
            document.getElementById('history-section').style.display = 'none';
            document.getElementById('upload-section').style.display = 'block';
        });
    }
    if (downloadBtn) {
        downloadBtn.addEventListener('click', handleDownload);
    }

    audioPlayer.addEventListener('ended', handleAudioEnded);

    // Mark navigation to settings to preserve file state
    const settingsLink = document.querySelector('a[href="/settings"]');
    if (settingsLink) {
        settingsLink.addEventListener('click', () => {
            sessionStorage.setItem('navigating_to_settings', 'true');
        });
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('file-info');
        fileInfo.textContent = `已选择: ${file.name}`;
        fileInfo.style.color = '';
        document.getElementById('start-generate-btn').disabled = false;
        // Save file name to sessionStorage for navigation to settings
        sessionStorage.setItem('selected_file_name', file.name);
    }
}

function restoreFileInfo() {
    // Only restore if coming back from settings page
    const fromSettings = sessionStorage.getItem('navigating_to_settings') === 'true';
    
    if (fromSettings) {
        const fileName = sessionStorage.getItem('selected_file_name');
        if (fileName) {
            document.getElementById('file-info').textContent = `之前选择: ${fileName} (请重新选择文件)`;
            document.getElementById('file-info').style.color = '#ff9800';
        }
        // Clear the navigation flag
        sessionStorage.removeItem('navigating_to_settings');
    } else {
        // Clear file info if not from settings (page reload or new visit)
        sessionStorage.removeItem('selected_file_name');
        document.getElementById('file-info').textContent = '';
        document.getElementById('start-generate-btn').disabled = true;
    }
    // Button stays disabled until user selects a file again
}

async function handleStartGenerate() {
    const fileInput = document.getElementById('novel-file');
    const apiKey = localStorage.getItem('api_key');
    const apiProvider = localStorage.getItem('api_provider') || 'qiniu';
    const maxScenes = document.getElementById('max-scenes').value;
    const customPrompt = document.getElementById('custom-prompt').value;

    if (!fileInput.files[0]) {
        alert('请先选择小说文件');
        return;
    }

    if (!apiKey) {
        alert('请先在设置页面配置 API Key');
        window.location.href = '/settings';
        return;
    }

    const enableVideo = document.getElementById('enable-video').checked;
    
    const formData = new FormData();
    formData.append('novel', fileInput.files[0]);
    formData.append('api_key', apiKey);
    formData.append('api_provider', apiProvider);
    formData.append('enable_video', enableVideo ? 'true' : 'false');
    if (maxScenes) {
        formData.append('max_scenes', maxScenes);
    }
    if (customPrompt) {
        formData.append('custom_prompt', customPrompt);
    }

    document.getElementById('upload-section').classList.add('hidden');
    document.getElementById('progress-section').classList.remove('hidden');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            currentTaskId = data.task_id;
            pollStatus();
        } else {
            if (response.status === 401) {
                alert('请先登录');
                window.location.href = '/login';
            } else {
                alert('错误: ' + data.error);
                resetUploadSection();
            }
        }
    } catch (error) {
        alert('上传失败: ' + error.message);
        resetUploadSection();
    }
}

async function pollStatus() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`/api/status/${currentTaskId}`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            updateProgress(data);

            if (data.status === 'processing') {
                setTimeout(pollStatus, 2000);
            } else if (data.status === 'completed') {
                await loadScenes();
            } else if (data.status === 'error') {
                alert('生成失败: ' + data.message);
                resetUploadSection();
            }
        }
    } catch (error) {
        console.error('获取状态失败:', error);
        setTimeout(pollStatus, 2000);
    }
}

function updateProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressFill.style.width = data.progress + '%';
    progressText.textContent = data.message;
}

async function loadScenes() {
    try {
        const response = await fetch(`/api/scenes/${currentTaskId}`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            scenes = data.scenes;
            currentSceneIndex = 0;

            document.getElementById('progress-section').classList.add('hidden');
            document.getElementById('player-section').classList.remove('hidden');

            displayScene(0);
        } else {
            alert('加载场景失败: ' + data.error);
        }
    } catch (error) {
        alert('加载场景失败: ' + error.message);
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

    if (scene.video_url) {
        sceneImage.outerHTML = `<video id="scene-image" src="${scene.video_url}" controls autoplay loop style="width: 100%; height: auto; border-radius: 10px;"></video>`;
    } else {
        if (document.getElementById('scene-image').tagName === 'VIDEO') {
            const imageWrapper = document.querySelector('.scene-image-wrapper');
            imageWrapper.innerHTML = '<img id="scene-image" src="" alt="场景图片">';
        }
        
        sceneImage.src = scene.image_url;
    }
    
    sceneText.textContent = scene.text;
    sceneCounter.textContent = `场景 ${index + 1} / ${scenes.length}`;
    
    if (scene.characters && scene.characters.length > 0) {
        sceneCharacters.textContent = `角色: ${scene.characters.join('、')}`;
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
        console.error('播放失败:', error);
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
    if (isPlaying && currentSceneIndex < scenes.length - 1) {
        navigateScene(1);
        setTimeout(() => {
            startPlayback();
        }, 500);
    } else {
        pausePlayback();
    }
}

function handleVolumeChange(event) {
    const volume = event.target.value;
    audioPlayer.volume = volume / 100;
    document.getElementById('volume-value').textContent = volume + '%';
}

function resetUploadSection() {
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('upload-section').classList.remove('hidden');
}

function returnToHome() {
    if (confirm('确定要返回主页吗?当前播放将被停止。')) {
        stopPlayback();
        
        const fileInput = document.getElementById('novel-file');
        fileInput.value = '';
        document.getElementById('file-info').textContent = '';
        document.getElementById('start-generate-btn').disabled = true;
        
        sessionStorage.removeItem('selected_file_name');
        sessionStorage.removeItem('navigating_to_settings');
        
        currentTaskId = null;
        scenes = [];
        currentSceneIndex = 0;
        
        document.getElementById('player-section').classList.add('hidden');
        document.getElementById('upload-section').classList.remove('hidden');
    }
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

async function showHistory() {
    try {
        const response = await fetch('/api/history', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (response.ok) {
            displayHistory(data.history);
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('history-section').style.display = 'block';
        } else {
            alert('获取历史失败: ' + data.error);
        }
    } catch (error) {
        alert('获取历史失败: ' + error.message);
    }
}

function displayHistory(history) {
    const historyList = document.getElementById('history-list');
    
    if (!history || history.length === 0) {
        historyList.innerHTML = '<p>还没有上传记录</p>';
        return;
    }
    
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead><tr style="background: #f0f0f0;">';
    html += '<th style="padding: 10px; border: 1px solid #ddd;">文件名</th>';
    html += '<th style="padding: 10px; border: 1px solid #ddd;">上传时间</th>';
    html += '<th style="padding: 10px; border: 1px solid #ddd;">操作</th>';
    html += '</tr></thead><tbody>';
    
    history.forEach(record => {
        const uploadTime = record.created_at ? new Date(record.created_at.replace(' ', 'T')).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        }) : '-';
        
        html += '<tr>';
        html += `<td style="padding: 10px; border: 1px solid #ddd;">${record.filename || '-'}</td>`;
        html += `<td style="padding: 10px; border: 1px solid #ddd;">${uploadTime}</td>`;
        html += `<td style="padding: 10px; border: 1px solid #ddd;">`;
        if (record.session_id && record.generated_scene_count > 0) {
            html += `<a href="#" onclick="loadPlayback('${record.session_id}'); return false;" style="color: #007bff; text-decoration: none;">查看作品</a>`;
        } else {
            html += '<span style="color: #999;">生成中</span>';
        }
        html += `</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    historyList.innerHTML = html;
}

async function loadPlayback(sessionId) {
    try {
        const response = await fetch(`/api/scenes/${sessionId}`, {
            credentials: 'include'
        });
        const data = await response.json();

        if (response.ok) {
            scenes = data.scenes;
            currentSceneIndex = 0;
            currentTaskId = sessionId;

            document.getElementById('history-section').style.display = 'none';
            document.getElementById('player-section').classList.remove('hidden');

            displayScene(0);
        } else {
            alert('加载作品失败: ' + data.error);
        }
    } catch (error) {
        alert('加载作品失败: ' + error.message);
    }
}

async function handleDownload() {
    if (!currentTaskId || scenes.length === 0) {
        alert('没有可下载的内容');
        return;
    }

    try {
        const downloadUrl = `/api/download/${currentTaskId}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `anime_${currentTaskId}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (error) {
        alert('下载失败: ' + error.message);
    }
}
