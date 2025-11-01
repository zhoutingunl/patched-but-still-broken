# API 测试文档

本文档描述了针对 Web API 接口的功能测试和压力测试。

## 测试文件

### 1. test_api_functional.py - 功能测试

功能测试文件包含 30 个测试用例，覆盖所有 API 端点的功能验证。

#### 测试覆盖的端点

**页面端点**
- `GET /` - 首页
- `GET /login` - 登录页
- `GET /settings` - 设置页
- `GET /favicon.ico` - 网站图标

**用户认证 API**
- `POST /api/register` - 用户注册
  - 测试成功注册
  - 测试缺失用户名
  - 测试缺失密码
  - 测试重复用户
- `POST /api/login` - 用户登录
  - 测试登录成功
  - 测试错误凭证
- `POST /api/logout` - 用户登出
- `GET /api/current_user` - 获取当前用户信息
  - 测试已登录状态
  - 测试未登录状态

**内容管理 API**
- `GET /api/history` - 获取生成历史
  - 测试需要登录
  - 测试成功获取历史
- `POST /api/check_payment` - 检查支付状态
  - 测试免费额度
  - 测试付费计算
- `POST /api/upload` - 上传小说
  - 测试需要登录
  - 测试无文件上传
  - 测试成功上传
  - 测试无效文件类型
- `GET /api/status/<task_id>` - 获取任务状态
  - 测试不存在的任务
  - 测试存在的任务
- `GET /api/scenes/<task_id>` - 获取场景列表
  - 测试不存在的任务
  - 测试未完成的任务
- `GET /api/download/<task_id>` - 下载生成内容

**其他测试**
- CORS 头部验证
- JSON 内容类型验证
- Session 持久化验证

#### 运行功能测试

```bash
# 运行所有功能测试
python3 -m unittest tests.test_api_functional -v

# 运行单个测试用例
python3 -m unittest tests.test_api_functional.TestAPIFunctional.test_01_index_endpoint -v
```

### 2. test_api_stress.py - 压力测试

压力测试文件包含 15 个测试用例，验证 API 在高并发和持续负载下的性能表现。

#### 测试场景

**并发测试**
- `test_01_concurrent_index_requests` - 50 个并发首页请求
- `test_02_concurrent_register_requests` - 30 个并发注册请求
- `test_03_concurrent_login_requests` - 30 个并发登录请求
- `test_05_concurrent_current_user_requests` - 50 个并发用户信息请求
- `test_06_concurrent_history_requests` - 30 个并发历史查询请求
- `test_08_concurrent_check_payment_requests` - 40 个并发支付检查请求

**性能测试**
- `test_04_sequential_api_calls_response_time` - 响应时间测试（20 次请求）
  - 目标：平均响应时间 < 100ms
- `test_07_rapid_status_check_requests` - 快速状态检查（100 次请求）
  - 目标：5 秒内完成
- `test_11_response_time_under_load` - 负载下的响应时间
  - 目标：平均响应时间 < 200ms，最大响应时间 < 1s

**稳定性测试**
- `test_09_mixed_endpoint_stress_test` - 混合端点压力测试
- `test_10_memory_leak_detection_session_creation` - 内存泄漏检测
- `test_12_status_endpoint_scalability` - 状态端点可扩展性测试
- `test_13_session_isolation_under_concurrent_login` - 并发登录会话隔离测试
- `test_14_sustained_load_test` - 持续负载测试（3 秒持续请求）
  - 目标：成功率 > 95%，QPS > 10
- `test_15_error_rate_under_invalid_requests` - 无效请求错误率测试

#### 运行压力测试

```bash
# 运行所有压力测试
python3 -m unittest tests.test_api_stress -v

# 运行单个压力测试
python3 -m unittest tests.test_api_stress.TestAPIStress.test_01_concurrent_index_requests -v
```

## 性能指标

### 预期性能标准

| 指标 | 目标值 |
|------|--------|
| 单个请求平均响应时间 | < 100ms |
| 负载下平均响应时间 | < 200ms |
| 最大响应时间 | < 1s |
| 并发请求成功率 | > 90% |
| 持续负载成功率 | > 95% |
| 每秒请求数 (QPS) | > 10 |

### 并发测试规模

| 测试类型 | 并发数 | 请求总数 |
|---------|--------|---------|
| 首页访问 | 10 | 50 |
| 用户注册 | 10 | 30 |
| 用户登录 | 10 | 30 |
| 用户信息查询 | 15 | 50 |
| 历史查询 | 10 | 30 |
| 支付检查 | 10 | 40 |
| 状态查询 | 20 | 100 |

## 测试依赖

测试使用的主要依赖库：

```python
unittest                # 测试框架
unittest.mock           # Mock 功能
concurrent.futures      # 并发测试
threading              # 线程测试
tempfile               # 临时文件
time                   # 性能测量
```

所有依赖都是 Python 标准库，无需额外安装。

## 运行所有 API 测试

```bash
# 运行功能测试和压力测试
python3 -m unittest discover tests -p "test_api_*.py" -v

# 使用 pytest（如果已安装）
pip install pytest
python3 -m pytest tests/test_api_functional.py tests/test_api_stress.py -v
```

## Mock 策略

为了避免依赖外部服务和数据库，测试使用了 Mock：

- `user_auth` 模块的所有函数被 Mock
- `statistics_db` 模块的所有函数被 Mock
- `threading.Thread` 在上传测试中被 Mock
- 所有需要 API Key 的操作被 Mock

这确保了测试的：
- **独立性**：不依赖数据库或外部服务
- **速度**：快速执行，无网络延迟
- **可靠性**：不受外部因素影响

## 测试结果示例

### 功能测试输出示例

```
test_01_index_endpoint (__main__.TestAPIFunctional) ... ok
test_02_login_page_endpoint (__main__.TestAPIFunctional) ... ok
test_03_settings_page_endpoint (__main__.TestAPIFunctional) ... ok
...
test_30_session_persistence_after_login (__main__.TestAPIFunctional) ... ok

----------------------------------------------------------------------
Ran 30 tests in 0.523s

OK
```

### 压力测试输出示例

```
test_01_concurrent_index_requests (__main__.TestAPIStress) ... ok
test_02_concurrent_register_requests (__main__.TestAPIStress) ... ok
test_03_concurrent_login_requests (__main__.TestAPIStress) ... ok
...
test_15_error_rate_under_invalid_requests (__main__.TestAPIStress) ... ok

----------------------------------------------------------------------
Ran 15 tests in 8.342s

OK
```

## CI/CD 集成

可以将这些测试集成到 CI/CD 流程中：

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run functional tests
      run: |
        python3 -m unittest tests.test_api_functional -v
    - name: Run stress tests
      run: |
        python3 -m unittest tests.test_api_stress -v
```

## 故障排查

### 常见问题

1. **ImportError: No module named 'web_app'**
   - 确保在项目根目录运行测试
   - 检查 PYTHONPATH 是否正确设置

2. **测试失败：CORS 相关**
   - 检查 Flask-CORS 是否正确安装
   - 确认 web_app.py 中的 CORS 配置

3. **并发测试超时**
   - 系统资源不足时可能发生
   - 可以减少并发数或请求总数

4. **Mock 不生效**
   - 确保 mock 的路径正确
   - 使用 `patch('web_app.function_name')` 而不是 `patch('module.function_name')`

## 扩展测试

如果需要添加更多测试：

### 添加功能测试

```python
def test_31_new_api_endpoint(self):
    response = self.client.get('/api/new_endpoint')
    self.assertEqual(response.status_code, 200)
    data = response.get_json()
    self.assertIn('expected_field', data)
```

### 添加压力测试

```python
def test_16_new_stress_scenario(self):
    num_requests = 50
    results = []
    
    def make_request():
        response = self.client.get('/api/endpoint')
        return response.status_code
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for status in results if status == 200)
    self.assertGreater(success_count, num_requests * 0.9)
```

## 测试覆盖率

当前测试覆盖的 API 端点：

- ✅ 页面端点：3/3 (100%)
- ✅ 用户认证：4/4 (100%)
- ✅ 内容管理：6/6 (100%)
- ✅ 文件服务：部分覆盖

总计：**45 个测试用例**（30 个功能 + 15 个压力）

## 维护建议

1. **定期更新**：当 API 接口变化时及时更新测试
2. **性能基准**：定期运行压力测试，监控性能变化
3. **Mock 更新**：当依赖模块接口变化时更新 Mock
4. **添加新测试**：新增 API 端点时同步添加测试用例
5. **测试数据**：使用有意义的测试数据，提高测试可读性

## 总结

这套 API 测试提供了：

- ✅ **完整的功能覆盖**：所有主要 API 端点
- ✅ **性能验证**：响应时间、并发能力、负载测试
- ✅ **稳定性保障**：内存泄漏检测、会话隔离
- ✅ **易于维护**：使用 Mock，无外部依赖
- ✅ **CI/CD 就绪**：可直接集成到自动化流程

对于生产环境部署前的验证，建议同时运行功能测试和压力测试，确保 API 的正确性和性能。
