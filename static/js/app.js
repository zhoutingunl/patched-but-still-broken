let currentTaskId = null;
let scenes = [];
let currentSceneIndex = 0;
let isPlaying = false;
let audioPlayer = null;
let currentContextMenuSessionId = null;

document.addEventListener('DOMContentLoaded', function() {
    audioPlayer = document.getElementById('audio-player');
    checkAuthentication();
    initializeEventListeners();
    loadHistoryList();
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
    const uploadNovelBtn = document.getElementById('upload-novel-btn');
    const novelTextInput = document.getElementById('novel-text-input');
    const returnHomeBtnList = document.getElementById('return-home-btn-list');

    if (selectFileBtn) selectFileBtn.addEventListener('click', () => novelFile.click());
    if (novelFile) novelFile.addEventListener('change', handleFileSelect);
    if (startGenerateBtn) startGenerateBtn.addEventListener('click', handleStartGenerate);
    if (playPauseBtn) playPauseBtn.addEventListener('click', togglePlayPause);
    if (prevBtn) prevBtn.addEventListener('click', () => navigateScene(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateScene(1));
    if (stopBtn) stopBtn.addEventListener('click', stopPlayback);
    if (volumeSlider) volumeSlider.addEventListener('input', handleVolumeChange);
    if (returnHomeBtn) returnHomeBtn.addEventListener('click', returnToHome);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
    if (uploadNovelBtn) uploadNovelBtn.addEventListener('click', showUploadSection);
    if (novelTextInput) novelTextInput.addEventListener('input', handleTextInput);
    if (returnHomeBtnList) returnHomeBtnList.addEventListener('click', returnToHome);

    if (audioPlayer) audioPlayer.addEventListener('ended', handleAudioEnded);

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    const settingsLink = document.querySelector('a[href="/settings"]');
    if (settingsLink) {
        settingsLink.addEventListener('click', () => {
            sessionStorage.setItem('navigating_to_settings', 'true');
        });
    }

    document.addEventListener('click', hideContextMenu);

    const deleteHistoryItem = document.getElementById('delete-history-item');
    if (deleteHistoryItem) {
        deleteHistoryItem.addEventListener('click', handleDeleteHistory);
    }
}

async function loadHistoryList() {
    try {
        const response = await fetch('/api/history', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (response.ok) {
            displayHistoryList(data.history);
        }
    } catch (error) {
        console.error('获取历史失败:', error);
    }
}

function displayHistoryList(history) {
    const historyList = document.getElementById('history-list');
    
    if (!history || history.length === 0) {
        historyList.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">暂无历史记录</div>';
        return;
    }
    
    historyList.innerHTML = '';
    
    history.forEach(record => {
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
            displayText = record.filename || '未命名';
            if (displayText.length > 20) displayText = displayText.substring(0, 20) + '...';
        }
        title.textContent = displayText;
        
        const time = document.createElement('div');
        time.className = 'history-item-time';
        const uploadTime = record.created_at ? new Date(record.created_at.replace(' ', 'T')).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }) : '-';
        time.textContent = uploadTime;
        
        item.appendChild(title);
        item.appendChild(time);
        
        item.addEventListener('click', () => {
            if (record.session_id && record.generated_scene_count > 0) {
                loadPlayback(record.session_id, record.input_text);
                document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
            } else {
                alert('该记录还在生成中，请稍后查看');
            }
        });
        
        item.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContextMenu(e, record.session_id);
        });
        
        historyList.appendChild(item);
    });
}

function showContextMenu(event, sessionId) {
    const contextMenu = document.getElementById('context-menu');
    contextMenu.style.display = 'block';
    contextMenu.style.left = event.pageX + 'px';
    contextMenu.style.top = event.pageY + 'px';
    currentContextMenuSessionId = sessionId;
}

function hideContextMenu() {
    const contextMenu = document.getElementById('context-menu');
    if (contextMenu) {
        contextMenu.style.display = 'none';
    }
}

async function handleDeleteHistory() {
    if (!currentContextMenuSessionId) return;
    
    if (!confirm('确定要删除这条历史记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete_history/${currentContextMenuSessionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            loadHistoryList();
            
            if (currentTaskId === currentContextMenuSessionId) {
                returnToHome();
            }
        } else {
            const data = await response.json();
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
    
    hideContextMenu();
}

function showUploadSection() {
    document.getElementById('welcome-section').style.display = 'none';
    document.getElementById('player-section').classList.add('hidden');
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('upload-section').style.display = 'block';
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('file-info');
        fileInfo.textContent = `已选择: ${file.name}`;
        fileInfo.style.color = '';
        document.getElementById('start-generate-btn').disabled = false;
        sessionStorage.setItem('selected_file_name', file.name);
    }
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
        const useStoryboard = document.getElementById('use-storyboard').checked;
        
        const formData = new FormData();
        const blob = new Blob([textContent], { type: 'text/plain' });
        formData.append('novel', blob, 'novel.txt');
        formData.append('api_key', apiKey);
        formData.append('api_provider', apiProvider);
        formData.append('use_storyboard', useStoryboard ? 'true' : 'false');
        if (customPrompt) {
            formData.append('custom_prompt', customPrompt);
        }

        document.getElementById('upload-section').style.display = 'none';
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
        const useStoryboard = document.getElementById('use-storyboard').checked;
        
        const formData = new FormData();
        formData.append('novel', fileInput.files[0]);
        formData.append('api_key', apiKey);
        formData.append('api_provider', apiProvider);
        formData.append('use_storyboard', useStoryboard ? 'true' : 'false');
        if (customPrompt) {
            formData.append('custom_prompt', customPrompt);
        }

        document.getElementById('upload-section').style.display = 'none';
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
                loadHistoryList();
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
            document.getElementById('welcome-section').style.display = 'none';
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

function resetUploadSection() {
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('welcome-section').style.display = 'flex';
}

function returnToHome() {
    stopPlayback();
    
    const fileInput = document.getElementById('novel-file');
    if (fileInput) fileInput.value = '';
    const fileInfo = document.getElementById('file-info');
    if (fileInfo) fileInfo.textContent = '';
    const startBtn = document.getElementById('start-generate-btn');
    if (startBtn) startBtn.disabled = true;
    
    sessionStorage.removeItem('selected_file_name');
    sessionStorage.removeItem('navigating_to_settings');
    
    currentTaskId = null;
    scenes = [];
    currentSceneIndex = 0;
    currentInputText = null;
    
    const headerTextEl = document.getElementById('content-header-text');
    if (headerTextEl) {
        headerTextEl.style.display = 'none';
        headerTextEl.textContent = '';
    }
    
    document.getElementById('player-section').classList.add('hidden');
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('welcome-section').style.display = 'flex';
    
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
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
            document.getElementById('upload-section').style.display = 'none';
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

