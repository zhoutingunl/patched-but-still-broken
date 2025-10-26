# API 测试文档

本目录包含针对小说转动漫生成器 Web API 的完整测试套件，包括功能测试和压力测试。

## 测试文件

### 1. test_api_functional.py - 功能测试

全面的 API 功能测试，覆盖所有主要端点和边界情况。

#### 测试覆盖范围

**TestAPIFunctional 类（25个测试用例）**

- **页面端点测试** (3个)
  - `test_01_index_endpoint` - 首页访问
  - `test_02_login_page_endpoint` - 登录页面
  - `test_03_settings_page_endpoint` - 设置页面

- **用户注册测试** (4个)
  - `test_04_register_success` - 成功注册
  - `test_05_register_missing_username` - 缺少用户名
  - `test_06_register_missing_password` - 缺少密码
  - `test_07_register_duplicate_user` - 重复用户名

- **用户登录测试** (4个)
  - `test_08_login_success` - 成功登录
  - `test_09_login_invalid_credentials` - 无效凭证
  - `test_10_login_missing_username` - 缺少用户名
  - `test_11_login_missing_password` - 缺少密码

- **会话管理测试** (4个)
  - `test_12_logout_success` - 登出成功
  - `test_13_logout_not_logged_in` - 未登录状态登出
  - `test_14_current_user_logged_in` - 获取已登录用户
  - `test_15_current_user_not_logged_in` - 获取未登录用户

- **历史记录测试** (2个)
  - `test_16_get_history_success` - 成功获取历史
  - `test_17_get_history_not_logged_in` - 未登录获取历史

- **支付检查测试** (3个)
  - `test_18_check_payment_sufficient_quota` - 配额充足
  - `test_19_check_payment_insufficient_quota` - 配额不足
  - `test_20_check_payment_not_logged_in` - 未登录检查

- **文件上传测试** (3个)
  - `test_21_upload_not_logged_in` - 未登录上传
  - `test_22_upload_no_file` - 无文件上传
  - `test_23_upload_invalid_file_type` - 无效文件类型

- **任务状态测试** (2个)
  - `test_24_get_status_invalid_task` - 无效任务ID
  - `test_25_get_scenes_invalid_task` - 无效场景ID

**TestAPIEdgeCases 类（10个测试用例）**

- **边界情况测试** (10个)
  - `test_26_register_empty_json` - 空JSON注册
  - `test_27_login_empty_json` - 空JSON登录
  - `test_28_register_invalid_content_type` - 无效Content-Type注册
  - `test_29_login_invalid_content_type` - 无效Content-Type登录
  - `test_30_register_special_characters` - 特殊字符注册
  - `test_31_login_sql_injection_attempt` - SQL注入尝试
  - `test_32_get_status_sql_injection_attempt` - 状态查询SQL注入
  - `test_33_check_payment_negative_scenes` - 负数场景检查
  - `test_34_check_payment_zero_scenes` - 零场景检查
  - `test_35_check_payment_extremely_large_scenes` - 极大场景数检查

#### 运行功能测试

```bash
# 运行所有功能测试
python -m pytest tests/test_api_functional.py -v

# 或使用 unittest
python tests/test_api_functional.py

# 运行特定测试类
python -m pytest tests/test_api_functional.py::TestAPIFunctional -v
python -m pytest tests/test_api_functional.py::TestAPIEdgeCases -v
```

### 2. test_api_load.py - 压力测试

对关键 API 端点进行并发压力测试，评估系统性能和稳定性。

#### 测试端点

- **GET /** - 首页
- **GET /login** - 登录页面
- **POST /api/register** - 用户注册
- **POST /api/login** - 用户登录
- **POST /api/logout** - 用户登出
- **GET /api/current_user** - 获取当前用户
- **GET /api/history** - 获取历史记录

#### 性能指标

每个端点测试都会收集以下指标：

- **成功率**: 成功请求数 / 总请求数
- **响应时间**:
  - 平均值
  - 中位数
  - 最小值
  - 最大值
  - 95th 百分位
  - 99th 百分位
- **吞吐量**: 每秒请求数 (req/s)
- **错误率**: 失败请求百分比

#### 运行压力测试

```bash
# 使用默认配置运行（100请求，10并发）
python tests/test_api_load.py

# 自定义请求数和并发数
LOAD_TEST_REQUESTS=500 LOAD_TEST_WORKERS=20 python tests/test_api_load.py

# 小规模快速测试
LOAD_TEST_REQUESTS=50 LOAD_TEST_WORKERS=5 python tests/test_api_load.py

# 大规模压力测试
LOAD_TEST_REQUESTS=1000 LOAD_TEST_WORKERS=50 python tests/test_api_load.py
```

#### 环境变量

- `LOAD_TEST_REQUESTS`: 每个端点的请求总数（默认: 100）
- `LOAD_TEST_WORKERS`: 并发工作线程数（默认: 10）

#### 输出结果

测试完成后会：
1. 在控制台显示详细的测试结果
2. 生成 `load_test_results.json` 文件，包含所有测试数据

## 依赖要求

```bash
# 功能测试依赖
pip install pytest pytest-mock

# 如果已有 requirements.txt，确保包含:
# - flask>=3.0.0
# - flask-cors>=4.0.0
```

## 测试最佳实践

### 功能测试
- 在代码更改后运行，确保API功能正常
- 集成到CI/CD流程中
- 关注边界情况和安全测试

### 压力测试
- 在生产部署前运行
- 逐步增加负载，找到系统瓶颈
- 监控数据库连接、内存使用等系统资源
- 建议配置:
  - 开发环境: 50-100请求，5-10并发
  - 测试环境: 500-1000请求，20-50并发
  - 生产验证: 1000+请求，50+并发

## 测试覆盖的API端点

### 公开端点（无需认证）
- `GET /` - 首页
- `GET /login` - 登录页面
- `GET /settings` - 设置页面
- `POST /api/register` - 注册
- `POST /api/login` - 登录
- `GET /api/current_user` - 当前用户状态

### 需要认证的端点
- `POST /api/logout` - 登出
- `GET /api/history` - 获取历史
- `POST /api/check_payment` - 检查支付
- `POST /api/upload` - 上传文件
- `GET /api/status/<task_id>` - 任务状态
- `GET /api/scenes/<task_id>` - 场景信息
- `GET /api/download/<task_id>` - 下载内容

## 已知限制

- 文件上传测试使用临时文件模拟
- 某些测试使用 mock 来避免实际的数据库操作
- 压力测试在测试模式下运行，与生产环境可能有性能差异

## 故障排查

### 功能测试失败
1. 检查数据库连接
2. 验证所有依赖已安装
3. 确认 Flask 应用配置正确

### 压力测试性能差
1. 减少并发数
2. 检查系统资源（CPU、内存）
3. 优化数据库查询
4. 考虑使用缓存

## 后续改进建议

1. **增加集成测试**: 测试完整的工作流程（注册->登录->上传->下载）
2. **数据库测试**: 添加真实数据库的集成测试
3. **性能基准**: 建立性能基准线，监控性能退化
4. **WebSocket测试**: 如果支持实时更新，添加WebSocket测试
5. **安全测试**: 扩展安全测试，包括CSRF、XSS等
6. **API文档**: 使用Swagger/OpenAPI自动生成API文档
