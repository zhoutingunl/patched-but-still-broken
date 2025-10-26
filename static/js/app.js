let currentTaskId = null;
let scenes = [];
let currentSceneIndex = 0;
let isPlaying = false;
let audioPlayer = null;
let videoPlayer = null;
let isVideoMode = false;

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
    const novelTextInput = document.getElementById('novel-text-input');
    const singleViewBtn = document.getElementById('single-view-btn');
    const listViewBtn = document.getElementById('list-view-btn');
    const playAllVideosBtn = document.getElementById('play-all-videos-btn');
    const downloadBtnList = document.getElementById('download-btn-list');
    const returnHomeBtnList = document.getElementById('return-home-btn-list');

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
    if (novelTextInput) {
        novelTextInput.addEventListener('input', handleTextInput);
    }
    if (singleViewBtn) {
        singleViewBtn.addEventListener('click', () => switchView('single'));
    }
    if (listViewBtn) {
        listViewBtn.addEventListener('click', () => switchView('list'));
    }
    if (playAllVideosBtn) {
        playAllVideosBtn.addEventListener('click', playAllVideos);
    }
    if (downloadBtnList) {
        downloadBtnList.addEventListener('click', handleDownload);
    }
    if (returnHomeBtnList) {
        returnHomeBtnList.addEventListener('click', returnToHome);
    }

    audioPlayer.addEventListener('ended', handleAudioEnded);

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

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

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    document.querySelectorAll('.upload-tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-${tabName === 'file' ? 'upload' : 'input'}-tab`);
    });
    
    const startBtn = document.getElementById('start-generate-btn');
    if (tabName === 'file') {
        const fileInput = document.getElementById('novel-file');
        startBtn.disabled = !fileInput.files[0];
    } else {
        const textInput = document.getElementById('novel-text-input');
        startBtn.disabled = !textInput.value.trim();
    }
}

function handleTextInput() {
    const textInput = document.getElementById('novel-text-input');
    const startBtn = document.getElementById('start-generate-btn');
    startBtn.disabled = !textInput.value.trim();
}

async function handleStartGenerate() {
    const fileInput = document.getElementById('novel-file');
    const textInput = document.getElementById('novel-text-input');
    const apiKey = localStorage.getItem('api_key');
    const apiProvider = localStorage.getItem('api_provider') || 'qiniu';
    const customPrompt = document.getElementById('custom-prompt').value;
    
    const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
    
    if (activeTab === 'file' && !fileInput.files[0]) {
        alert('请先选择小说文件');
        return;
    }
    
    if (activeTab === 'text' && !textInput.value.trim()) {
        alert('请输入小说内容');
        return;
    }

    if (!apiKey) {
        alert('请先在设置页面配置 API Key');
        window.location.href = '/settings';
        return;
    }

    let content = '';
    
    if (activeTab === 'text') {
        content = textInput.value.trim();
        const wordCount = content.length;
        
        try {
            const checkResponse = await fetch('/api/check_payment', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ word_count: wordCount })
            });
            
            const checkData = await checkResponse.json();
            
            if (checkData.requires_payment) {
                const shouldContinue = await showPaymentDialog(checkData.payment_amount, wordCount);
                if (!shouldContinue) {
                    return;
                }
            }
            
            proceedWithTextUpload(content);
        } catch (error) {
            alert('检查付费状态失败: ' + error.message);
        }
        return;
    }
    
    const file = fileInput.files[0];
    const reader = new FileReader();
    
    reader.onload = async function(e) {
        content = e.target.result;
        const wordCount = content.length;
        
        try {
            const checkResponse = await fetch('/api/check_payment', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ word_count: wordCount })
            });
            
            const checkData = await checkResponse.json();
            
            if (checkData.requires_payment) {
                const shouldContinue = await showPaymentDialog(checkData.payment_amount, wordCount);
                if (!shouldContinue) {
                    return;
                }
            }
            
            proceedWithFileUpload();
        } catch (error) {
            alert('检查付费状态失败: ' + error.message);
        }
    };
    
    reader.readAsText(file);
    
    async function proceedWithTextUpload(textContent) {
        const enableVideo = document.getElementById('enable-video').checked;
        const useStoryboard = document.getElementById('use-storyboard').checked;
        
        const formData = new FormData();
        const blob = new Blob([textContent], { type: 'text/plain' });
        formData.append('novel', blob, 'novel.txt');
        formData.append('api_key', apiKey);
        formData.append('api_provider', apiProvider);
        formData.append('enable_video', enableVideo ? 'true' : 'false');
        formData.append('use_storyboard', useStoryboard ? 'true' : 'false');
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
    
    async function proceedWithFileUpload() {
        const enableVideo = document.getElementById('enable-video').checked;
        const useStoryboard = document.getElementById('use-storyboard').checked;
        
        const formData = new FormData();
        formData.append('novel', fileInput.files[0]);
        formData.append('api_key', apiKey);
        formData.append('api_provider', apiProvider);
        formData.append('enable_video', enableVideo ? 'true' : 'false');
        formData.append('use_storyboard', useStoryboard ? 'true' : 'false');
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
    const sceneShotType = document.getElementById('scene-shot-type');
    const sceneMood = document.getElementById('scene-mood');

    if (scene.video_url) {
        if (document.getElementById('scene-image').tagName !== 'VIDEO') {
            const imageWrapper = document.querySelector('.scene-image-wrapper');
            imageWrapper.innerHTML = '<video id="scene-image" controls style="width: 100%; height: auto; border-radius: 10px;"></video>';
        }
        const videoElement = document.getElementById('scene-image');
        videoElement.src = scene.video_url;
        videoPlayer = videoElement;
        isVideoMode = true;
        
        videoElement.onended = function() {
            if (isPlaying && currentSceneIndex < scenes.length - 1) {
                navigateScene(1);
            } else if (currentSceneIndex >= scenes.length - 1) {
                isPlaying = false;
                document.getElementById('play-pause-btn').textContent = '▶️ 播放';
            }
        };
        
        if (isPlaying) {
            videoElement.play();
        }
    } else {
        if (document.getElementById('scene-image').tagName === 'VIDEO') {
            const imageWrapper = document.querySelector('.scene-image-wrapper');
            imageWrapper.innerHTML = '<img id="scene-image" src="" alt="场景图片">';
        }
        
        const imgElement = document.getElementById('scene-image');
        imgElement.src = scene.image_url;
        videoPlayer = null;
        isVideoMode = false;
    }
    
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

    if (!isVideoMode) {
        audioPlayer.src = scene.audio_url;
        audioPlayer.load();
    }

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
    
    if (isVideoMode && videoPlayer) {
        videoPlayer.play().catch(error => {
            console.error('视频播放失败:', error);
            isPlaying = false;
            document.getElementById('play-pause-btn').textContent = '▶️ 播放';
        });
    } else {
        audioPlayer.play().catch(error => {
            console.error('音频播放失败:', error);
            isPlaying = false;
            document.getElementById('play-pause-btn').textContent = '▶️ 播放';
        });
    }
}

function pausePlayback() {
    isPlaying = false;
    if (isVideoMode && videoPlayer) {
        videoPlayer.pause();
    } else {
        audioPlayer.pause();
    }
    document.getElementById('play-pause-btn').textContent = '▶️ 播放';
}

function stopPlayback() {
    isPlaying = false;
    if (isVideoMode && videoPlayer) {
        videoPlayer.pause();
        videoPlayer.currentTime = 0;
    } else {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
    }
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

function resetUploadSection() {
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('upload-section').style.display = 'block';
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
        document.getElementById('upload-section').style.display = 'block';
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
            document.getElementById('upload-section').style.display = 'block';
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

function showPaymentDialog(paymentAmount, wordCount) {
    return new Promise((resolve) => {
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            text-align: center;
        `;
        
        content.innerHTML = `
            <h2 style="margin-top: 0; color: #333;">💰 付费提示</h2>
            <p style="font-size: 16px; color: #666; line-height: 1.6;">
                您已使用完免费的3次视频生成机会。<br>
                本次上传的小说共 <strong>${wordCount}</strong> 字。<br>
                需要支付费用：<strong style="color: #ff6b6b; font-size: 24px;">¥${paymentAmount.toFixed(2)}</strong>
            </p>
            <p style="font-size: 14px; color: #999; margin-top: 20px;">
                💡 提示：当前为内测版本，您可以点击"跳过"按钮继续使用
            </p>
            <div style="margin-top: 30px; display: flex; gap: 15px; justify-content: center;">
                <button id="payment-skip-btn" style="
                    padding: 12px 30px;
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                ">跳过（内测版本）</button>
                <button id="payment-cancel-btn" style="
                    padding: 12px 30px;
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                ">取消</button>
            </div>
        `;
        
        dialog.appendChild(content);
        document.body.appendChild(dialog);
        
        const skipBtn = content.querySelector('#payment-skip-btn');
        const cancelBtn = content.querySelector('#payment-cancel-btn');
        
        skipBtn.onmouseover = () => skipBtn.style.background = '#218838';
        skipBtn.onmouseout = () => skipBtn.style.background = '#28a745';
        cancelBtn.onmouseover = () => cancelBtn.style.background = '#c82333';
        cancelBtn.onmouseout = () => cancelBtn.style.background = '#dc3545';
        
        skipBtn.addEventListener('click', () => {
            document.body.removeChild(dialog);
            resolve(true);
        });
        
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(dialog);
            resolve(false);
        });
    });
}

function switchView(viewType) {
    const singleView = document.getElementById('single-view');
    const listView = document.getElementById('list-view');
    const singleViewBtn = document.getElementById('single-view-btn');
    const listViewBtn = document.getElementById('list-view-btn');
    
    if (viewType === 'single') {
        singleView.style.display = 'block';
        listView.style.display = 'none';
        singleViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
    } else if (viewType === 'list') {
        singleView.style.display = 'none';
        listView.style.display = 'block';
        singleViewBtn.classList.remove('active');
        listViewBtn.classList.add('active');
        renderVideoList();
    }
}

function renderVideoList() {
    const container = document.getElementById('video-list-container');
    container.innerHTML = '';
    
    const videosWithIndex = scenes
        .map((scene, index) => ({ scene, index }))
        .filter(item => item.scene.video_url);
    
    if (videosWithIndex.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #999;">没有视频可显示。请确保在生成时启用了视频生成功能。</p>';
        return;
    }
    
    videosWithIndex.forEach(({ scene, index }) => {
        const card = document.createElement('div');
        card.style.cssText = `
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        `;
        card.onmouseover = () => card.style.transform = 'translateY(-5px)';
        card.onmouseout = () => card.style.transform = 'translateY(0)';
        
        card.innerHTML = `
            <video controls style="width: 100%; height: 200px; object-fit: cover;" preload="metadata">
                <source src="${scene.video_url}" type="video/mp4">
            </video>
            <div style="padding: 15px;">
                <h4 style="margin: 0 0 10px 0; color: #333;">分镜 ${index + 1}</h4>
                <p style="margin: 0; color: #666; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${scene.text || '无描述'}</p>
                ${scene.shot_type ? `<p style="margin: 5px 0 0 0; color: #999; font-size: 12px;">📷 ${scene.shot_type}</p>` : ''}
                <button onclick="playVideoFromList(${index})" style="
                    margin-top: 10px;
                    padding: 8px 16px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    width: 100%;
                ">在单个播放器中查看</button>
            </div>
        `;
        
        container.appendChild(card);
    });
}

function playVideoFromList(index) {
    switchView('single');
    displayScene(index);
}

function playAllVideos() {
    const videosWithIndex = scenes
        .map((scene, index) => ({ scene, index }))
        .filter(item => item.scene.video_url);
    
    if (videosWithIndex.length === 0) {
        alert('没有视频可播放');
        return;
    }
    
    switchView('single');
    displayScene(videosWithIndex[0].index);
    isPlaying = true;
    startPlayback();
}
