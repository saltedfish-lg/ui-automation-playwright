# ui-automation-playwright

基于 **Playwright for Python + Pytest** 的 Web UI 自动化测试框架。

目标：

- 结构清晰：PO + Flow + Tests，多层抽象，高内聚、低耦合；
- 稳定可维护：统一配置、统一超时、统一日志、统一失败截图 & Trace；
- 可扩展：支持 UI + API 混合场景、支持 Jenkins 流水线、支持接口 Mock。

---

## 1. 技术栈

- Python 3.11 / 3.12（不建议用太新的 3.14，很多三方库还没完全适配）
- [Playwright](https://playwright.dev/python/)
- Pytest / pytest-html / pytest-xdist
- loguru（日常日志）
- YAML（配置管理）

---

## 2. 项目结构

```text
.
├── configs/                 # 配置文件（多环境）
│   ├── config.yaml          # 基础配置（含 env、app、browser、timeout、account、report 等）
│   ├── config_dev.yaml      # dev 环境覆盖项
│   └── config_test.yaml     # test 环境覆盖项
│
├── framework/
│   ├── core/                # 框架核心能力
│   │   ├── base_flow.py     # 业务流程基类（step()、wait_page_stable() 等）
│   │   ├── base_page.py     # Page 基类（open/fill/click/is_visible/通用断言等）
│   │   ├── config_loader.py # 配置加载与多环境合并（懒加载单例）
│   │   └── logger.py        # loguru 日志初始化
│   │
│   └── fixtures/            # Pytest fixtures
│       ├── browser_fixtures.py  # playwright_instance / browser / page / auth_page
│       └── api_fixtures.py      # api_client（基于 Playwright APIRequestContext 的封装）
│
├── flows/                   # Flow 层：业务流程封装
│   └── login_flow.py        # 登录业务流程（成功 / 失败场景）
│
├── pages/                   # Page Object 层
│   └── login_page.py        # 登录页面 PO（元素定位 + 操作 + 状态判断）
│
├── tests/                   # 测试用例
│   ├── __init__.py
│   └── login/
│       ├── test_login_success.py   # 登录成功用例
│       └── test_login_negative.py  # 登录失败参数化用例 + 一个 debug 用例
│
├── tools/
│   └── generate_storage_state.py   # 生成登录态 storage_state.json 的工具脚本
│
├── utils/                   # 工具类
│   ├── api_client.py        # ApiClient：统一 headers + HTTP + 业务断言
│   ├── network_utils.py     # 简单接口 Mock 工具（基于 Page.route）
│   └── path_utils.py        # 统一管理截图 / trace 输出路径
│
├── conftest.py              # 全局 Pytest 配置：失败截图 + trace + pytest-html 集成
├── Jenkinsfile              # Jenkins 流水线脚本
├── pytest.ini               # Pytest 配置（markers / addopts 等）
├── requirements.txt         # Python 依赖
└── README.md                # 工程说明（当前文件）
```

## 3. 配置说明
### 3.1 基本配置（configs/config.yaml）
```yaml
env: "dev"

app:
  base_url: "http://www.baidu.com"
  login_path: ""               # 如果登录页有 path，可以写成 "/login"

browser:
  type: "chromium"             # Playwright 支持 chromium / firefox / webkit
  headless: false              # 本地调试：false；CI：建议 true
  slow_mo: 0                   # 调试时可以改成 200~500 看步骤执行

timeout:
  short: 3000
  medium: 5000
  long: 10000

account:
  username: "xxx"
  password: "xxx"

report:
  screenshot_dir: "reports/screenshots"
  log_dir: "reports/logs"
  trace_dir: "reports/traces"
```

### 3.2 多环境配置（config_dev.yaml / config_test.yaml）
* config_dev.yaml / config_test.yaml 中只写差异即可，例如：
```yaml
# configs/config_test.yaml
app:
  base_url: "http://xxxxxx"
  login_path: ""
```
* 运行时通过 env 决定加载哪一个覆盖文件：
  * 默认读 config.yaml 中的 env；
  * 也可以通过环境变量覆盖，比如：UI_AUTOMATION_ENV=test。

## 4. 环境准备
### 4.1 创建虚拟环境并安装依赖
```bash
# 1）创建虚拟环境
python -m venv .venv

# 2）激活虚拟环境（Windows PowerShell）
.\.venv\Scripts\Activate.ps1

# 3）安装依赖
pip install -r requirements.txt
```
### 4.2 安装 Playwright 浏览器
```bash
# 仍然在虚拟环境中
python -m playwright install
```
首次安装会下载 Chromium / Firefox / WebKit 及相关组件（需要能访问外网）。

## 5. 运行用例
### 5.1 最简单的方式
在项目根目录：
```bash
pytest
```
默认行为（见 pytest.ini 的 addopts）：
* -s -vv：详细输出 + 不捕获 stdout；
* --html=reports/ui-report.html --self-contained-html：生成独立 HTML 报告。
### 5.2 只跑登录模块
```bash
pytest tests/login
```
### 5.3 使用标记（markers）
在 pytest.ini 中定义了：
```ini
markers =
    smoke: 冒烟用例
    regression: 回归用例
```
示例：
```bash
# 跑所有冒烟用例
pytest -m smoke

# 跑所有回归用例
pytest -m regression
```
如果你在本地使用了 @pytest.mark.debug 的调试用例，可以加：
```bash
pytest -m debug
```
建议在 CI（Jenkins）里默认排除 debug 用例，例如在 pytest.ini 的 addopts 里加上 -m "not debug"。

## 6. 截图、Trace 与 HTML 报告
### 6.1 失败自动截图 & Trace
* conftest.py::pytest_runtest_makereport 钩子会在用例失败时：
  * 截图：保存到 reports/screenshots/<用例名>_时间戳.png
  * trace：保存到 reports/traces/<用例名>_时间戳.zip
  * 并把截图和 trace 下载链接挂到 pytest-html 报告中
### 6.2 查看 HTML 报告
执行完成后在：
```text
reports/ui-report.html
```
用浏览器打开即可。

## 7. Flow + Page 使用示例
### 7.1 登录成功用例
```python
# tests/login/test_login_success.py
from playwright.sync_api import Page
from flows.login_flow import LoginFlow
from pages.login_page import LoginPage

def test_login_success(page: Page):
    flow = LoginFlow(page)
    flow.login_with_default_account()

    # 等待网络空闲，减少页面没加载完就断言的风险
    page.wait_for_load_state("networkidle")

    login_page = LoginPage(page)
    assert login_page.is_logged_in(), "登录成功提示未出现，疑似登录失败"
```
### 7.2 登录失败参数化用例
```python
# tests/login/test_login_negative.py
import pytest
from playwright.sync_api import Page

from flows.login_flow import LoginFlow

@pytest.mark.parametrize(
    "username,password,case_desc",
    [
        ("guang", "wrong_password", "密码错误"),
        ("not_exist", "Aa123456", "账号不存在"),
        ("", "Aa123456", "账号为空"),
        ("guang", "", "密码为空"),
    ],
)
def test_login_fail_cases(page: Page, username: str, password: str, case_desc: str):
    flow = LoginFlow(page)
    flow.login_should_fail(username=username, password=password)
```

## 8. API 客户端（ApiClient）使用说明
ApiClient 封装在 utils/api_client.py，对应的 pytest fixture 在 framework/fixtures/api_fixtures.py 中注册为 api_client。
### 8.1 基本用法
```python
from utils.api_client import ApiClient

def test_get_profile(api_client: ApiClient):
    data = api_client.get("/api/user/profile")
    assert data["data"]["username"] == "guang"
```
ApiClient 特点：
* 自动合并默认 headers（Content-Type 等）
* 自动校验 HTTP 状态码（默认期望 200，可以自定义）
* 自动尝试解析 JSON
* 支持简单的“业务成功”断言（默认检查 code 或 success 字段，可以按项目约定调整）
### 8.2 登录鉴权示例（可选）
可以在 api_fixtures.py 里写登录逻辑，然后调用 client.set_bearer_token(token)，所有接口自动带上 Authorization: Bearer <token>。

## 9. 登录态复用（storage_state）
如果系统登录较重，可以通过 tools/generate_storage_state.py 生成一个登录态文件，然后在 fixture 中用 auth_page 复用登录态。
大致流程：
1. 先运行脚本生成 storage_state.json：
```bash
python -m tools.generate_storage_state
```
2. 在 browser_fixtures.py 里，auth_page fixture 通过：
```python
browser.new_context(storage_state=storage_state_path)
```
启动时加载登录态，后续用例直接基于已登录页面执行。

## 10. Jenkins 集成（简要）
项目根目录有 Jenkinsfile，大致流程：
1. 拉取代码
2. 创建/复用 Python 虚拟环境，安装依赖
3. 执行：
```bash
pytest
```
4. 将 reports/** 归档为构建产物，后续可以在 Jenkins 中参数化：
* UI_AUTOMATION_ENV：选择 dev / test
* UI_ACCOUNT_USERNAME / UI_ACCOUNT_PASSWORD：用 Jenkins Credentials 注入
* 是否开启并发执行（pytest -n auto）等

## 11. TODO / 扩展方向
* 按模块拆分更多 Page / Flow（订单、客户、报表等）
* 把 utils/network_utils.py 的接口 mock 用在不稳定的第三方调用上
* 补充一批基于 ApiClient 的接口用例，并和 UI 用例打通成“接口造数 + UI 校验”的链路

* 引入用例标签（冒烟 / 回归 / 场景 / 跨域等），配合 Jenkins 做更灵活的测试策略
