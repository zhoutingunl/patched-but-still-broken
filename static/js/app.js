let currentTaskId = null;
let scenes = [];
let currentSceneIndex = 0;
let isPlaying = false;
let audioPlayer = null;

document.addEventListener('DOMContentLoaded', function() {
    audioPlayer = document.getElementById('audio-player');
    initializeEventListeners();
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

    selectFileBtn.addEventListener('click', () => novelFile.click());
    
    novelFile.addEventListener('change', handleFileSelect);
    startGenerateBtn.addEventListener('click', handleStartGenerate);
    playPauseBtn.addEventListener('click', togglePlayPause);
    prevBtn.addEventListener('click', () => navigateScene(-1));
    nextBtn.addEventListener('click', () => navigateScene(1));
    stopBtn.addEventListener('click', stopPlayback);
    volumeSlider.addEventListener('input', handleVolumeChange);

    audioPlayer.addEventListener('ended', handleAudioEnded);
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('file-info').textContent = `已选择: ${file.name}`;
        document.getElementById('start-generate-btn').disabled = false;
    }
}

async function handleStartGenerate() {
    const fileInput = document.getElementById('novel-file');
    const apiKey = document.getElementById('api-key').value;
    const maxScenes = document.getElementById('max-scenes').value;

    if (!fileInput.files[0]) {
        alert('请先选择小说文件');
        return;
    }

    const formData = new FormData();
    formData.append('novel', fileInput.files[0]);
    formData.append('api_key', apiKey);
    if (maxScenes) {
        formData.append('max_scenes', maxScenes);
    }

    document.getElementById('upload-section').classList.add('hidden');
    document.getElementById('progress-section').classList.remove('hidden');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            currentTaskId = data.task_id;
            pollStatus();
        } else {
            alert('错误: ' + data.error);
            resetUploadSection();
        }
    } catch (error) {
        alert('上传失败: ' + error.message);
        resetUploadSection();
    }
}

async function pollStatus() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`/api/status/${currentTaskId}`);
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
        const response = await fetch(`/api/scenes/${currentTaskId}`);
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

    sceneImage.src = scene.image_url;
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
