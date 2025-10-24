document.addEventListener('DOMContentLoaded', function() {
    const apiKeyInput = document.getElementById('api-key');
    const apiProviderSelect = document.getElementById('api-provider');
    const saveBtn = document.getElementById('save-settings-btn');
    const currentProvider = document.getElementById('current-provider');
    const keyStatus = document.getElementById('key-status');

    loadSettings();

    saveBtn.addEventListener('click', function() {
        const apiKey = apiKeyInput.value.trim();
        const provider = apiProviderSelect.value;

        if (!apiKey) {
            alert('请输入 API Key');
            return;
        }

        localStorage.setItem('api_key', apiKey);
        localStorage.setItem('api_provider', provider);

        alert('设置已保存！');
        updateStatus();
    });

    function loadSettings() {
        const savedKey = localStorage.getItem('api_key');
        const savedProvider = localStorage.getItem('api_provider') || 'qiniu';

        if (savedKey) {
            apiKeyInput.value = savedKey;
        }
        apiProviderSelect.value = savedProvider;
        
        updateStatus();
    }

    function updateStatus() {
        const savedKey = localStorage.getItem('api_key');
        const savedProvider = localStorage.getItem('api_provider') || 'qiniu';

        currentProvider.textContent = savedProvider === 'qiniu' ? '七牛 AI' : 'OpenAI';
        keyStatus.textContent = savedKey ? '✅ 已配置' : '❌ 未配置';
        keyStatus.style.color = savedKey ? '#48bb78' : '#f56565';
    }
});
