# OAuth 登录配置指南

本文档说明如何配置 Google 和微信 OAuth 登录功能。

## 功能特性

- ✅ Google 账号一键登录
- ✅ 微信扫码登录
- ✅ 自动创建用户账号
- ✅ 保留原有的用户名/密码登录方式

## 环境变量配置

在 `.env` 文件中添加以下配置：

```env
SECRET_KEY=your_secret_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
WECHAT_APP_ID=your_wechat_app_id_here
WECHAT_APP_SECRET=your_wechat_app_secret_here
```

## Google OAuth 配置步骤

### 1. 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 在侧边栏选择 "API 和服务" > "凭据"

### 2. 配置 OAuth 同意屏幕

1. 点击 "OAuth 同意屏幕"
2. 选择 "外部" 用户类型（如果只为组织内部使用，选择"内部"）
3. 填写应用名称、用户支持电子邮件和开发者联系信息
4. 添加授权域名（例如：`yourdomain.com`）
5. 保存并继续

### 3. 创建 OAuth 2.0 客户端 ID

1. 点击 "创建凭据" > "OAuth 客户端 ID"
2. 应用类型选择 "Web 应用"
3. 添加授权重定向 URI：
   ```
   http://localhost:5000/api/authorize/google  (开发环境)
   https://yourdomain.com/api/authorize/google  (生产环境)
   ```
4. 点击 "创建"
5. 复制客户端 ID 和客户端密钥到 `.env` 文件

## 微信开放平台配置步骤

### 1. 注册开发者账号

1. 访问 [微信开放平台](https://open.weixin.qq.com/)
2. 注册并完成开发者认证（需要企业资质）

### 2. 创建网站应用

1. 登录微信开放平台
2. 进入 "管理中心" > "网站应用" > "创建网站应用"
3. 填写应用基本信息：
   - 应用名称
   - 应用简介
   - 应用官网
   - 应用图标
4. 设置授权回调域：
   ```
   localhost:5000  (开发环境)
   yourdomain.com  (生产环境)
   ```
5. 提交审核（通常需要1-3个工作日）

### 3. 获取配置信息

1. 审核通过后，在应用详情页获取：
   - AppID（应用唯一标识）
   - AppSecret（应用密钥）
2. 将这些信息填入 `.env` 文件

## 数据库表结构

系统会自动创建/更新以下用户表结构：

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,              -- OAuth 用户此字段为空
    oauth_provider TEXT,             -- 'google' 或 'wechat'
    oauth_id TEXT,                   -- OAuth 提供商的用户 ID
    email TEXT,                      -- 用户邮箱（仅 Google）
    avatar_url TEXT,                 -- 用户头像 URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_oauth_provider_id ON users(oauth_provider, oauth_id);
```

## 使用方式

### 用户登录流程

1. 用户访问登录页面 `/login`
2. 可选择以下登录方式：
   - 传统用户名/密码登录
   - Google 账号登录
   - 微信扫码登录

### Google 登录流程

1. 用户点击 "使用 Google 账号登录"
2. 跳转到 Google 授权页面
3. 用户授权后返回应用
4. 系统自动创建/登录用户账号

### 微信登录流程

1. 用户点击 "使用微信扫码登录"
2. 显示微信登录二维码
3. 用户使用微信扫码授权
4. 系统自动创建/登录用户账号

## API 端点

### OAuth 登录端点

- **Google 登录**: `GET /api/login/google`
- **Google 回调**: `GET /api/authorize/google`
- **微信登录**: `GET /api/login/wechat`
- **微信回调**: `GET /api/authorize/wechat`

### 传统登录端点（保持不变）

- **注册**: `POST /api/register`
- **登录**: `POST /api/login`
- **登出**: `POST /api/logout`
- **当前用户**: `GET /api/current_user`

## 安全注意事项

1. **密钥保护**：
   - 不要将 `.env` 文件提交到版本控制系统
   - 在生产环境使用强随机的 `SECRET_KEY`

2. **HTTPS 要求**：
   - 生产环境必须使用 HTTPS
   - OAuth 回调 URL 必须使用 HTTPS

3. **授权域名**：
   - 确保在 Google/微信后台正确配置授权域名
   - 域名必须与实际运行的域名一致

4. **用户数据**：
   - OAuth 用户的 `password_hash` 字段为空
   - 通过 `oauth_provider` 和 `oauth_id` 唯一标识用户

## 开发测试

### 本地测试 Google OAuth

```bash
# 1. 配置 .env 文件
cp .env.example .env
# 编辑 .env 文件，填入 Google OAuth 配置

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python web_app.py

# 4. 访问 http://localhost:5000/login
```

### 本地测试微信 OAuth

微信 OAuth 在本地测试较为困难，因为：
1. 需要企业认证（个人开发者无法使用）
2. 回调域名必须是公网可访问的域名
3. 开发环境建议使用内网穿透工具（如 ngrok）

## 故障排除

### Google 登录失败

1. 检查 `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET` 是否正确
2. 确认回调 URL 在 Google Cloud Console 中已配置
3. 查看浏览器控制台和服务器日志的错误信息

### 微信登录失败

1. 检查 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET` 是否正确
2. 确认应用已通过微信开放平台审核
3. 验证授权回调域名配置是否正确
4. 检查是否使用了 HTTPS（生产环境必需）

### 用户名冲突

如果 OAuth 用户的用户名与现有用户重复，系统会自动在用户名后添加数字后缀（如 `username_1`, `username_2`）。

## 依赖库

本功能使用以下 Python 库：

- `authlib>=1.3.0` - OAuth 客户端库
- `httpx>=0.27.0` - HTTP 客户端（authlib 依赖）
- `flask>=3.0.0` - Web 框架
- `python-dotenv>=1.0.0` - 环境变量管理

## 相关文件

- `user_auth.py` - 用户认证逻辑
- `web_app.py` - Flask 应用和 OAuth 路由
- `templates/login.html` - 登录页面 UI
- `requirements.txt` - Python 依赖
- `.env.example` - 环境变量示例

## 许可

MIT License
