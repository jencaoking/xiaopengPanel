# 小鹏面板 (xiaopengPanel)

> 一款功能全面、设计现代化的服务器管理面板。采用液态玻璃 (Glassmorphism) 视觉风格，支持明暗双主题，跨平台运行于 Windows 与 Linux。

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [安全设计](#安全设计)
- [设计系统](#设计系统)
- [测试](#测试)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [FAQ](#faq)
- [许可证](#许可证)

---

## 项目简介

小鹏面板是一个前后端分离的服务器管理工具，旨在提供直观、安全、高效的服务器运维体验。项目涵盖系统监控、文件管理、终端访问、站点管理、数据库管理、防火墙管理、定时任务等核心运维场景，同时具备细粒度 RBAC 权限控制和双因素认证 (2FA) 等企业级安全特性。

### 核心亮点

- **液态玻璃 UI** — 基于 Glassmorphism 设计语言，半透明模糊背景、动态光斑、微妙边框与分层阴影
- **明暗双主题** — 完整的 Light/Dark 模式，CSS 变量驱动，300ms 平滑过渡，自动跟随系统偏好
- **跨平台** — 同时支持 Windows (Service/netsh) 和 Linux (systemd/ufw/iptables/firewalld)
- **企业级安全** — JWT + Refresh Token + 2FA (TOTP) + RBAC 细粒度权限 + IP 白名单 + 速率限制
- **实时通信** — 基于 Flask-SocketIO 的 WebSocket 终端，支持多标签页、命令历史、搜索
- **可定制仪表盘** — 拖拽排序的小组件布局，8 种监控组件自由组合
- **三语国际化** — 简体中文、繁体中文、英文

---

## 功能特性

### 系统监控

| 功能 | 说明 |
|------|------|
| 实时指标 | CPU（含每核）、内存、磁盘、网络使用率，5 秒自动刷新 |
| 历史数据 | SQLite 持久化，支持 1h / 6h / 24h / 7d / 30d 时间范围查询 |
| 磁盘 IO | 读写速度、IOPS、按磁盘分列详情 |
| 网络流量 | 上传/下载速度、累计流量、数据包统计、历史趋势图 |
| GPU 监控 | NVIDIA GPU 利用率、显存、温度（需安装 pynvml，自动降级） |
| 温度监控 | CPU/GPU/磁盘温度传感器读取 |
| 进程排行 | Top N 进程，支持按 CPU / 内存 / IO 排序 |
| 告警系统 | 基于阈值的自动告警，支持查看与解决 |
| 数据导出 | JSON 格式导出监控指标数据 |

### 仪表盘

- **可拖拽布局** — 鼠标拖拽移动组件位置，拖拽右下角调整大小
- **8 种组件** — CPU 环形图、内存环形图、磁盘列表、网络统计、Top 进程、网络趋势图、磁盘 IO 图、历史趋势图
- **编辑模式** — 切换编辑模式可添加/删除/显示隐藏组件
- **布局持久化** — 组件布局保存到后端，跨设备同步
- **时间范围切换** — 1h / 6h / 24h / 7d / 30d

### 文件管理

| 功能 | 说明 |
|------|------|
| 目录浏览 | 白名单目录限制，防止越权访问 |
| 文件操作 | 创建、删除、重命名、移动、复制、批量删除 |
| 在线编辑 | Monaco Editor，支持 60+ 语言语法高亮 |
| 版本控制 | 自动保存历史版本（最多 10 个），支持版本对比与恢复 |
| 断点续传 | 分片上传（1MB chunk），支持大文件，可取消上传 |
| 文件搜索 | 按文件名递归搜索 |
| 压缩解压 | 创建 ZIP 压缩包、解压归档文件 |
| 文件哈希 | 计算 MD5 / SHA1 / SHA256 校验值 |
| 目录大小 | 递归计算目录总大小 |
| 权限查看 | 查看文件权限信息 |

### 终端访问

- **WebSocket 实时终端** — 基于 xterm.js + Flask-SocketIO，支持 WebGL 渲染
- **多标签页** — 创建/切换/关闭/重命名标签页，双击标签名编辑
- **Shell 选择** — 支持选择不同 Shell（bash/sh/zsh 等，自动检测可用 Shell）
- **命令历史** — 按用户存储，支持搜索、点击重用、清空
- **终端搜索** — 正向/反向搜索终端输出内容
- **缩放控制** — 字体大小调节（8px - 32px）
- **全屏模式** — 一键切换全屏终端
- **主题自适应** — 终端配色随明暗主题自动切换（One Dark / Light）
- **心跳保活** — 25 秒间隔心跳，配合后端 30 分钟超时
- **剪贴板集成** — 支持系统剪贴板复制粘贴
- **Web 链接** — 终端中的 URL 可点击打开

### 站点管理

| 功能 | 说明 |
|------|------|
| 虚拟主机 | 创建/编辑/删除站点，支持 Nginx / Apache |
| 域名管理 | 域名绑定、批量删除、DNS 检测 |
| SSL 证书 | 申请/续期/吊销 SSL 证书，查看证书状态 |
| 站点操作 | 启动/停止/重载 Web 服务 |
| 配置管理 | 查看/编辑/验证站点配置文件 |
| 站点备份 | 创建站点备份、下载、删除 |
| 统计信息 | 站点总数、活跃数等统计 |

### 数据库管理

| 功能 | 说明 |
|------|------|
| 多数据库 | 支持配置多个数据库连接（MySQL / PostgreSQL / SQLite） |
| 用户管理 | 数据库用户创建/删除/修改密码/权限管理 |
| 数据库操作 | 查看数据库列表、表列表 |
| SQL 查询 | 在线执行 SQL 查询 |
| 连接测试 | 测试数据库连接是否正常 |
| 备份管理 | 全量/增量/差异备份，支持定时调度（daily/weekly/monthly） |
| 备份恢复 | 验证备份完整性、从备份恢复 |
| 性能监控 | 实时指标、历史趋势、慢查询分析、优化建议 |
| 告警阈值 | 自定义监控告警阈值 |

### 进程管理

- **进程列表** — 查看所有进程的 PID、名称、CPU、内存、IO 信息
- **进程详情** — 查看单个进程的详细信息
- **进程操作** — 终止/暂停/恢复单个进程
- **批量操作** — 批量终止进程

### 服务管理

- **跨平台** — Windows Service / Linux systemd
- **服务列表** — 查看所有服务状态
- **服务操作** — 启动/停止/重启/重载
- **服务日志** — 查看服务日志（systemd journal）
- **Unit 文件** — 查看 systemd unit 文件内容
- **依赖关系** — 查看服务依赖

### 防火墙管理

| 功能 | Linux | Windows |
|------|-------|---------|
| 后端检测 | ufw / firewalld / iptables 自动检测 | netsh advfirewall |
| 启用/禁用 | 支持 | 支持 |
| 规则管理 | 添加/删除/列表 | 添加/删除/列表 |
| 端口放行 | 快速放行/封断端口 | 快速放行/封断端口 |
| 默认策略 | 查看与修改 | 查看与修改 |
| 服务列表 | 预定义服务放行 | 预定义服务放行 |

### 定时任务 (Cron)

- **Cron 表达式** — 标准 5 段 Cron 表达式调度
- **任务管理** — 创建/编辑/删除/启用/禁用任务
- **手动执行** — 一键手动触发任务执行
- **执行历史** — 记录每次执行的结果与输出（每任务最多 50 条）
- **表达式验证** — 创建时验证 Cron 表达式合法性
- **调度器** — 后台线程 30 秒轮询，自动触发到期任务

### 代码编辑器

- **Monaco Editor** — VS Code 同款编辑器内核
- **60+ 语言** — JavaScript / TypeScript / Python / HTML / CSS / SQL / PHP / Go / Rust 等
- **功能** — 语法高亮、智能补全、代码折叠、搜索替换、多文件搜索
- **会话管理** — 编辑会话保存与恢复
- **代码大纲** — 符号大纲导航
- **设置同步** — 编辑器设置保存到后端

### 用户管理

- **用户列表** — 查看所有用户信息与状态
- **用户操作** — 创建/删除用户、修改密码、修改角色
- **状态管理** — 启用/禁用用户账户
- **修改密码** — 用户自行修改密码

### 安全认证

| 功能 | 说明 |
|------|------|
| JWT 认证 | Access Token (1h) + Refresh Token (7d) |
| 双因素认证 | TOTP 标准（Google Authenticator 兼容），含备用验证码 |
| RBAC 权限 | 16 种资源 × 6 种操作的细粒度权限控制 |
| 内置角色 | admin / operator / viewer / auditor |
| 自定义角色 | 管理员可创建自定义角色并分配权限 |
| IP 白名单 | 按角色配置允许访问的 IP |
| 速率限制 | 登录 5 次/分钟，API 100 次/分钟 |
| 登录锁定 | 5 次失败后锁定 5 分钟 |
| 密码策略 | 8-32 位，含大小写字母、数字、特殊字符 |
| 密码加密 | bcrypt 12 轮哈希 |

### 日志管理

- **日志列表** — 查看系统日志文件
- **日志读取** — 在线读取日志内容
- **日志搜索** — 关键字搜索日志
- **过滤读取** — 按级别/时间范围过滤
- **日志导出** — 导出日志为文件下载

### 系统配置

- **在线配置** — 查看/修改系统配置
- **JSON 持久化** — 配置存储在 config.json

### 设计特色

- **液态玻璃效果** — `backdrop-filter: blur(20px) saturate(180%)`，半透明背景 + 模糊 + 微妙边框
- **动态背景光斑** — 3 个浮动渐变球体，20-30 秒缓慢漂移，为玻璃态提供深度
- **明暗双主题** — CSS 变量驱动，`color-scheme` 支持，300ms 平滑过渡动画
- **响应式布局** — Mobile-first 断点（375 / 768 / 1024 / 1440），移动端侧边栏抽屉
- **三语国际化** — 简体中文 / 繁体中文 / 英文
- **微交互** — 按钮按压缩放 (0.96)、卡片悬停上浮、骨架屏加载
- **可访问性** — WCAG AA 对比度、`prefers-reduced-motion` 支持、键盘焦点指示器、44px 触摸目标
- **跨浏览器** — `-webkit-` 前缀、`@supports` 降级、GPU 加速 (`translateZ(0)`)

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 核心语言 |
| Flask | 3.0+ | Web 框架 |
| Flask-SocketIO | 5.3+ | WebSocket 实时通信（终端） |
| Flask-CORS | 4.0+ | 跨域资源共享 |
| psutil | 5.9+ | 系统资源监控 |
| PyJWT | 2.8+ | JWT 令牌生成与验证 |
| bcrypt | 4.1+ | 密码哈希加密 |
| pyotp | 2.9+ | TOTP 双因素认证 |
| qrcode | 7.4+ | 二维码生成（2FA 绑定） |
| pynvml | 11.5+ | NVIDIA GPU 监控（可选，自动降级） |
| croniter | 1.4+ | Cron 表达式解析与调度 |
| python-dotenv | 1.0+ | 环境变量加载 |
| SQLite | 内置 | 数据存储（监控历史、用户、配置） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | 前端框架（组合式 API） |
| Vite | 6.0+ | 构建工具与开发服务器 |
| Vuex | 4.1+ | 状态管理（认证、主题、语言） |
| Vue I18n | 9.14+ | 国际化（zh-CN / zh-TW / en-US） |
| Socket.IO Client | 4.8+ | WebSocket 客户端（终端） |
| Chart.js | 4.5+ | 数据可视化图表 |
| xterm.js | 6.0+ | 终端模拟器 |
| Monaco Editor | 0.52+ | 代码编辑器（VS Code 内核） |
| vuedraggable | 4.1+ | 拖拽排序（仪表盘组件） |
| xterm addons | - | fit / search / web-links / webgl / clipboard |

### 测试

| 技术 | 用途 |
|------|------|
| pytest 8.0+ | 测试框架 |
| pytest-cov | 覆盖率报告（目标 70%+） |
| pytest-mock | Mock 工具 |
| pytest-asyncio | 异步测试支持 |
| faker | 测试数据生成 |

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    浏览器 (用户端)                         │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Vue 3 SPA  │  │  Vuex    │  │  Socket.IO Client  │ │
│  │  (Vite)     │  │  Store   │  │  (Terminal WS)     │ │
│  └──────┬──────┘  └────┬─────┘  └────────┬───────────┘ │
└─────────┼──────────────┼─────────────────┼─────────────┘
          │ HTTP/API     │                 │ WebSocket
          ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────┐
│                 Flask 后端 (端口 5000)                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Flask   │  │  Flask-      │  │  Flask-SocketIO  │  │
│  │  Routes  │  │  CORS        │  │  (Terminal PTY)  │  │
│  └────┬─────┘  └──────────────┘  └────────┬─────────┘  │
│       │                                    │            │
│  ┌────▼────────────────────────────────────▼─────────┐ │
│  │              Modules (16 个功能模块)                │ │
│  │  auth · rbac · middleware · system_monitor        │ │
│  │  file_manager · terminal · site · db_manager      │ │
│  │  firewall · cron · totp · process · service ...   │ │
│  └────┬──────────────────────────────────────────────┘ │
│       │                                                 │
│  ┌────▼──────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  SQLite   │  │  JSON    │  │  System (psutil)   │  │
│  │  (监控历史) │  │  (配置)   │  │  /subprocess       │  │
│  └───────────┘  └──────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 请求流转

```
用户操作 → Vuex dispatch → fetch API → Flask 路由
  → @authenticate (JWT 验证)
  → @ip_whitelist_required (IP 白名单)
  → @require_permission (RBAC 权限)
  → Module 函数 → 返回 JSON
```

### 后端模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 认证 | `auth.py` | JWT 令牌、登录验证、2FA 登录 |
| RBAC | `rbac.py` | 角色定义、权限检查、自定义角色管理 |
| 中间件 | `middleware.py` | IP 白名单、安全响应头、权限装饰器 |
| TOTP | `totp_manager.py` | 2FA 密钥生成、验证、备用码 |
| 系统监控 | `system_monitor.py` | 单例模式指标收集器，SQLite 持久化 |
| 系统信息 | `system_info.py` | OS/硬件/网络信息获取 |
| 进程管理 | `process_manager.py` | 进程列表、详情、终止 |
| 服务管理 | `service_manager.py` | Windows Service / systemd 管理 |
| 文件管理 | `file_manager.py` | 文件操作、上传、版本控制、压缩 |
| 终端 | `terminal_manager.py` | WebSocket PTY 会话管理 |
| 站点 | `site_manager.py` | 虚拟主机、域名、SSL |
| 数据库 | `db_manager.py` | 数据库连接、查询、用户管理 |
| 数据库备份 | `db_backup.py` | 备份配置、调度、恢复 |
| 数据库监控 | `db_monitor.py` | 性能指标、慢查询、优化建议 |
| 防火墙 | `firewall_manager.py` | 跨平台防火墙规则管理 |
| 定时任务 | `cron_manager.py` | Cron 调度器、任务执行、历史记录 |
| 代码编辑器 | `code_editor.py` | Monaco Editor 后端支持 |
| 日志 | `log_manager.py` | 日志读取、搜索、导出 |
| 用户管理 | `user_manager.py` | 用户 CRUD、密码管理 |
| 系统配置 | `system_config.py` | 配置读写 |
| 端口工具 | `port_utils.py` | 端口检测与管理 |

---

## 快速开始

### 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.8+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| npm | 9+ | 包管理（或使用 yarn/pnpm） |

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/xiaopengPanel.git
cd xiaopengPanel
```

#### 2. 安装后端依赖

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

# 开发环境（含测试工具）
pip install -r requirements-dev.txt
```

#### 3. 安装前端依赖

```bash
cd ../frontend-vue
npm install
```

#### 4. 运行项目

**启动后端**（端口 5000）：

```bash
cd backend
python app.py
```

**启动前端开发服务器**（端口 5173）：

```bash
cd frontend-vue
npm run dev
```

访问 `http://localhost:5173` 即可使用小鹏面板。

### 默认登录信息

| 字段 | 值 |
|------|----|
| 用户名 | `admin` |
| 密码 | `Admin123!` |

> 首次登录后请立即修改密码。密码需 8-32 位，包含大小写字母、数字和特殊字符。

### 生成密码哈希

如需修改默认密码，使用哈希工具生成 bcrypt 哈希：

```bash
cd backend
python scripts/hash_password.py
# 输入密码后生成哈希，写入 config/users.json
```

---

## 项目结构

```
xiaopengPanel/
├── backend/                         # Python 后端
│   ├── app.py                       # Flask 应用入口（速率限制器、SocketIO）
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                # API 路由定义（200+ 端点）
│   ├── modules/                     # 核心功能模块（21 个）
│   │   ├── auth.py                  # JWT 认证与登录
│   │   ├── rbac.py                  # 细粒度 RBAC 权限引擎
│   │   ├── middleware.py            # IP 白名单、安全头、权限装饰器
│   │   ├── totp_manager.py          # TOTP 双因素认证
│   │   ├── system_monitor.py        # 系统资源监控（单例）
│   │   ├── system_info.py           # 系统信息获取
│   │   ├── process_manager.py       # 进程管理
│   │   ├── service_manager.py       # 服务管理（Win/Linux）
│   │   ├── file_manager.py          # 文件管理（上传/版本/压缩）
│   │   ├── terminal_manager.py      # WebSocket 终端
│   │   ├── site_manager.py          # 站点/域名/SSL
│   │   ├── db_manager.py            # 数据库管理
│   │   ├── db_backup.py             # 数据库备份
│   │   ├── db_monitor.py            # 数据库监控
│   │   ├── firewall_manager.py      # 防火墙管理（跨平台）
│   │   ├── cron_manager.py          # 定时任务（Cron 调度器）
│   │   ├── code_editor.py           # 代码编辑器后端
│   │   ├── log_manager.py           # 日志管理
│   │   ├── user_manager.py          # 用户管理
│   │   ├── system_config.py         # 系统配置
│   │   └── port_utils.py            # 端口工具
│   ├── scripts/
│   │   └── hash_password.py         # 密码哈希工具
│   ├── tests/                       # 测试套件
│   │   ├── conftest.py              # pytest 配置
│   │   ├── unit/                    # 单元测试
│   │   │   ├── test_auth.py         # 认证测试
│   │   │   └── test_rbac.py         # RBAC 测试
│   │   ├── integration/             # 集成测试
│   │   └── security/                # 安全测试
│   ├── requirements.txt             # 生产依赖
│   ├── requirements-dev.txt         # 开发依赖
│   └── pytest.ini                   # pytest 配置
├── config/                          # 配置文件目录
│   ├── config.py                    # 配置加载器（动态读取 JSON）
│   ├── config.json                  # 主配置文件
│   └── users.json                   # 用户数据（bcrypt 哈希）
├── frontend-vue/                    # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                  # 根组件（侧边栏/顶栏/路由）
│   │   ├── main.js                  # 入口（Vuex store / I18n / 主题）
│   │   ├── style.css                # 全局样式（玻璃态组件）
│   │   ├── styles/
│   │   │   ├── design-system.css    # iOS 设计系统（明暗主题变量）
│   │   │   └── animations.css       # 动画系统
│   │   ├── components/              # 页面组件（18 个）
│   │   │   ├── LoginModern.vue      # 登录页
│   │   │   ├── DashboardEnhanced.vue# 仪表盘
│   │   │   ├── Terminal.vue         # 终端
│   │   │   ├── FileManager.vue      # 文件管理
│   │   │   ├── CodeEditor.vue       # 代码编辑器
│   │   │   ├── Processes.vue        # 进程管理
│   │   │   ├── Services.vue         # 服务管理
│   │   │   ├── Sites.vue            # 站点管理
│   │   │   ├── Databases.vue        # 数据库管理
│   │   │   ├── Firewall.vue         # 防火墙管理
│   │   │   ├── CronManager.vue      # 定时任务
│   │   │   ├── WebService.vue       # Web 服务管理
│   │   │   ├── Logs.vue             # 日志管理
│   │   │   ├── Users.vue            # 用户管理
│   │   │   ├── Config.vue           # 系统配置
│   │   │   └── TwoFactorAuth.vue    # 双因素认证
│   │   ├── components/widgets/      # 仪表盘小组件（10 个）
│   │   │   ├── CpuWidget.vue
│   │   │   ├── MemoryWidget.vue
│   │   │   ├── DiskWidget.vue
│   │   │   ├── NetworkWidget.vue
│   │   │   ├── NetworkChartWidget.vue
│   │   │   ├── DiskIoChartWidget.vue
│   │   │   ├── HistoryChartWidget.vue
│   │   │   ├── TopProcessesWidget.vue
│   │   │   ├── GpuWidget.vue
│   │   │   ├── TemperatureWidget.vue
│   │   │   └── AlertsWidget.vue
│   │   └── locales/                 # 国际化
│   │       ├── zh-CN.js             # 简体中文
│   │       ├── zh-TW.js             # 繁体中文
│   │       └── en-US.js             # 英文
│   ├── index.html
│   ├── vite.config.js               # Vite 配置（代理）
│   └── package.json
└── README.md
```

---

## 配置说明

### 主配置文件 (`config/config.json`)

```json
{
  "server": {
    "port": 5000,
    "host": "0.0.0.0"
  },
  "security": {
    "secret_key": "dev-secret-key",
    "debug": true,
    "ip_whitelist_enabled": true,
    "ip_whitelist": {
      "admin": ["127.0.0.1", "::1"],
      "user": ["127.0.0.1", "::1"]
    }
  },
  "logging": {
    "level": "INFO",
    "dir": "logs"
  },
  "file_manager": {
    "whitelist_dirs": [
      { "path": "/var/www", "name": "Web 目录" },
      { "path": "/etc/nginx", "name": "Nginx 配置" }
    ],
    "upload": {
      "max_size": 10485760,
      "allowed_types": ["txt", "md", "json", "js", "css", "html", "py"],
      "chunk_size": 1048576,
      "temp_dir": "temp_uploads"
    },
    "online_edit": {
      "enabled": true,
      "allowed_extensions": ["txt", "md", "json", "js", "css", "html", "py"],
      "version_control": {
        "enabled": true,
        "max_versions": 10
      }
    }
  }
}
```

### 配置项详解

| 配置路径 | 说明 | 默认值 |
|----------|------|--------|
| `server.port` | 后端监听端口 | 5000 |
| `server.host` | 绑定地址 | 0.0.0.0 |
| `security.secret_key` | JWT 签名密钥 | dev-secret-key |
| `security.debug` | 调试模式 | true |
| `security.ip_whitelist_enabled` | 启用 IP 白名单 | true |
| `security.ip_whitelist` | 按角色的 IP 白名单 | 127.0.0.1 |
| `logging.level` | 日志级别 | INFO |
| `logging.dir` | 日志目录 | logs |
| `file_manager.whitelist_dirs` | 文件管理白名单目录 | - |
| `file_manager.upload.max_size` | 上传文件大小上限 | 10MB |
| `file_manager.upload.chunk_size` | 分片大小 | 1MB |
| `file_manager.online_edit.version_control.max_versions` | 最大版本数 | 10 |

### 前端配置 (`frontend-vue/vite.config.js`)

```javascript
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  }
})
```

### 环境变量

```bash
# 设置端口（覆盖 config.json）
export XIAOPENG_PORT=8080

# 设置密钥
export XIAOPENG_SECRET_KEY=your_secret_key
```

---

## API 文档

API 基础路径：`/api`，所有受保护接口需携带 `Authorization: Bearer <token>` 头。

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | 登录，返回 JWT Token |
| POST | `/api/login/2fa` | 双因素认证登录验证 |
| POST | `/api/refresh-token` | 刷新 Access Token |

### 2FA 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/2fa/status` | 查看当前用户 2FA 状态 |
| POST | `/api/2fa/setup` | 生成 2FA 密钥与二维码 |
| POST | `/api/2fa/enable` | 启用 2FA（验证首次验证码） |
| POST | `/api/2fa/disable` | 禁用 2FA |
| POST | `/api/2fa/backup-codes/regenerate` | 重新生成备用验证码 |

### RBAC 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/roles` | 获取所有角色 |
| GET | `/api/roles/<role_key>` | 获取单个角色详情 |

### 系统监控接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/realtime` | 实时系统指标 |
| GET | `/api/monitor/network/traffic` | 网络流量 |
| GET | `/api/monitor/network/traffic/history` | 网络流量历史 |
| GET | `/api/monitor/disk-io` | 磁盘 IO |
| GET | `/api/monitor/disk-io/history` | 磁盘 IO 历史 |
| GET | `/api/monitor/disk-io/per-disk` | 按磁盘分列 IO |
| GET | `/api/monitor/history/<metric_type>` | 指标历史数据 |
| GET | `/api/monitor/top-processes` | Top 进程 |
| GET | `/api/monitor/process/<pid>/detail` | 进程详情 |
| GET | `/api/monitor/gpu` | GPU 监控 |
| GET | `/api/monitor/temperature` | 温度监控 |
| GET | `/api/monitor/network/interfaces` | 网络接口列表 |
| GET | `/api/monitor/load-average` | 系统负载 |
| GET | `/api/monitor/swap` | 交换分区 |
| POST | `/api/monitor/export` | 导出监控数据 |
| GET | `/api/monitor/alerts/thresholds` | 告警阈值列表 |
| POST | `/api/monitor/alerts/thresholds` | 创建告警阈值 |
| PUT | `/api/monitor/alerts/thresholds/<id>` | 更新告警阈值 |
| DELETE | `/api/monitor/alerts/thresholds/<id>` | 删除告警阈值 |
| GET | `/api/monitor/alerts` | 告警列表 |
| POST | `/api/monitor/alerts/<id>/resolve` | 解决告警 |

### 仪表盘接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/widgets/layout` | 获取组件布局 |
| POST | `/api/dashboard/widgets/layout` | 保存组件布局 |
| GET | `/api/dashboard/widgets/default` | 默认布局 |

### 文件管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/file-manager/whitelist-dirs` | 白名单目录 |
| GET | `/api/file-manager/directory` | 列出目录 |
| POST | `/api/file-manager/directory` | 创建目录 |
| POST | `/api/file-manager/file` | 创建文件 |
| DELETE | `/api/file-manager/file` | 删除文件 |
| GET | `/api/file-manager/file/read` | 读取文件 |
| PUT | `/api/file-manager/file/write` | 写入文件 |
| GET | `/api/file-manager/file/permissions` | 查看权限 |
| POST | `/api/file-manager/upload/init` | 初始化上传 |
| POST | `/api/file-manager/upload/chunk` | 上传分片 |
| POST | `/api/file-manager/upload/complete` | 完成上传 |
| POST | `/api/file-manager/upload/cancel` | 取消上传 |
| GET | `/api/file-manager/upload/status` | 上传状态 |
| GET | `/api/file-manager/download` | 下载文件 |
| GET | `/api/file-manager/file/versions` | 文件版本列表 |
| POST | `/api/file-manager/file/restore-version` | 恢复版本 |
| GET | `/api/file-manager/file/version-diff` | 版本对比 |
| POST | `/api/file-manager/rename` | 重命名 |
| POST | `/api/file-manager/move` | 移动 |
| POST | `/api/file-manager/copy` | 复制 |
| POST | `/api/file-manager/batch-delete` | 批量删除 |
| GET | `/api/file-manager/directory-size` | 目录大小 |
| GET | `/api/file-manager/file/hash` | 文件哈希 |
| GET | `/api/file-manager/search` | 搜索文件 |
| POST | `/api/file-manager/archive/create` | 创建压缩包 |
| POST | `/api/file-manager/archive/extract` | 解压归档 |

### 站点管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sites/stats` | 站点统计 |
| GET | `/api/sites` | 站点列表 |
| POST | `/api/sites` | 创建站点 |
| GET | `/api/sites/<id>` | 站点详情 |
| PUT | `/api/sites/<id>` | 更新站点 |
| DELETE | `/api/sites/<id>` | 删除站点 |
| POST | `/api/sites/batch/delete` | 批量删除 |
| PUT | `/api/sites/<id>/status` | 更新状态 |
| POST | `/api/sites/<id>/start` | 启动站点 |
| POST | `/api/sites/<id>/stop` | 停止站点 |
| POST | `/api/sites/<id>/reload` | 重载站点 |
| GET/PUT | `/api/sites/<id>/config` | 站点配置 |
| POST | `/api/sites/<id>/config/validate` | 验证配置 |
| GET/POST | `/api/domains` | 域名管理 |
| PUT/DELETE | `/api/domains/<id>` | 域名操作 |
| POST | `/api/domains/<id>/check` | DNS 检测 |
| POST | `/api/domains/<id>/ssl/issue` | 申请 SSL |
| POST | `/api/domains/<id>/ssl/renew` | 续期 SSL |
| POST | `/api/domains/<id>/ssl/revoke` | 吊销 SSL |
| GET | `/api/domains/<id>/ssl/status` | SSL 状态 |
| POST | `/api/sites/<id>/backup` | 站点备份 |
| GET | `/api/sites/backups` | 备份列表 |
| DELETE | `/api/sites/backups/<name>` | 删除备份 |
| GET | `/api/sites/backups/<name>/download` | 下载备份 |

### 数据库管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/databases/configs` | 数据库配置管理 |
| GET/PUT/DELETE | `/api/databases/configs/<id>` | 单个配置操作 |
| POST | `/api/databases/configs/<id>/test` | 测试连接 |
| GET | `/api/databases/configs/<id>/databases` | 数据库列表 |
| GET | `/api/databases/configs/<id>/databases/<db>/tables` | 表列表 |
| POST | `/api/databases/configs/<id>/query` | 执行 SQL |
| GET/POST | `/api/databases/configs/<id>/users` | 数据库用户管理 |
| GET/POST | `/api/databases/backups/configs` | 备份配置 |
| POST | `/api/databases/backups/configs/<id>/trigger` | 手动触发备份 |
| GET | `/api/databases/backups/history` | 备份历史 |
| POST | `/api/databases/backups/<id>/verify` | 验证备份 |
| POST | `/api/databases/backups/<id>/restore` | 恢复备份 |
| GET/POST | `/api/databases/monitor/configs` | 监控配置 |
| GET | `/api/databases/monitor/configs/<id>/metrics` | 监控指标 |
| GET | `/api/databases/monitor/slow-queries` | 慢查询 |
| GET | `/api/databases/monitor/optimization` | 优化建议 |

### 防火墙接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/firewall/status` | 防火墙状态 |
| POST | `/api/firewall/enable` | 启用防火墙 |
| POST | `/api/firewall/disable` | 禁用防火墙 |
| POST | `/api/firewall/reload` | 重载规则 |
| POST/DELETE | `/api/firewall/rules` | 规则管理 |
| POST | `/api/firewall/quick-allow` | 快速放行端口 |
| POST | `/api/firewall/quick-block` | 快速封断端口 |
| PUT | `/api/firewall/default-policy` | 默认策略 |
| GET | `/api/firewall/services` | 预定义服务 |

### 定时任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cron/tasks` | 任务列表 |
| POST | `/api/cron/tasks` | 创建任务 |
| GET/PUT/DELETE | `/api/cron/tasks/<id>` | 任务操作 |
| POST | `/api/cron/tasks/<id>/toggle` | 启用/禁用 |
| POST | `/api/cron/tasks/<id>/run` | 手动执行 |
| GET | `/api/cron/tasks/<id>/history` | 执行历史 |
| GET | `/api/cron/history` | 全部历史 |
| POST | `/api/cron/validate` | 验证 Cron 表达式 |

### 终端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/terminal/shells` | 可用 Shell 列表 |
| GET/POST | `/api/terminal/history` | 命令历史 |
| GET | `/api/terminal/history/search` | 搜索历史 |
| GET | `/api/terminal/suggestions` | 命令建议 |
| POST | `/api/terminal/history/clear` | 清空历史 |

WebSocket 事件（`/socket.io` path `/socket.io`）：

| 事件 | 方向 | 说明 |
|------|------|------|
| `create_session` | C→S | 创建终端会话 |
| `terminal_input` | C→S | 发送输入 |
| `terminal_resize` | C→S | 终端大小变化 |
| `ping_session` | C→S | 心跳保活 |
| `session_created` | S→C | 会话创建成功 |
| `terminal_output` | S→C | 终端输出 |
| `session_closed` | S→C | 会话关闭 |
| `error` | S→C | 错误通知 |

### 其他接口

| 分类 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 系统 | GET | `/api/system/info` | 系统信息 |
| 系统 | GET | `/api/system/status` | 系统状态 |
| 进程 | GET | `/api/processes` | 进程列表 |
| 进程 | GET | `/api/processes/<pid>` | 进程详情 |
| 进程 | POST | `/api/processes/<pid>/<action>` | 进程操作 |
| 进程 | POST | `/api/processes/batch/<action>` | 批量操作 |
| 服务 | GET | `/api/services` | 服务列表 |
| 服务 | GET/POST | `/api/services/<name>` | 服务操作 |
| 服务 | GET | `/api/services/<name>/logs` | 服务日志 |
| 日志 | GET | `/api/logs` | 日志列表 |
| 日志 | POST | `/api/logs/read` | 读取日志 |
| 日志 | POST | `/api/logs/search` | 搜索日志 |
| 日志 | POST | `/api/logs/export` | 导出日志 |
| 用户 | GET/POST | `/api/users` | 用户管理 |
| 用户 | PUT | `/api/users/<name>/password` | 修改密码 |
| 用户 | PUT | `/api/users/<name>/role` | 修改角色 |
| 用户 | DELETE | `/api/users/<name>` | 删除用户 |
| 配置 | GET/PUT | `/api/config` | 系统配置 |
| Web 服务 | POST | `/api/web-service/reload` | 重载 Web 服务 |
| Web 服务 | GET | `/api/web-service/status` | Web 服务状态 |
| 编辑器 | GET | `/api/editor/languages` | 支持的语言 |
| 编辑器 | POST | `/api/editor/completions` | 代码补全 |
| 编辑器 | POST | `/api/editor/search` | 代码搜索 |
| 编辑器 | GET/POST | `/api/editor/sessions` | 编辑会话 |

---

## 安全设计

### 认证流程

```
用户登录 → 验证用户名密码 → 检查 2FA 状态
  ├── 未启用 2FA → 返回 Access Token + Refresh Token
  └── 已启用 2FA → 返回 2FA Required
        → 用户输入验证码 → /api/login/2fa
        → 验证 TOTP → 返回 Access Token + Refresh Token
```

### 权限模型

RBAC 权限格式为 `资源:操作`，支持通配符：

```
*:action     — 对所有资源拥有该操作权限
resource:*   — 对该资源拥有全部操作权限
*:*          — 超级权限
```

操作隐含关系：
```
manage → view + create + update + delete + execute
execute → view
create / update / delete → view
```

内置角色：

| 角色 | 权限 | 说明 |
|------|------|------|
| admin | *:* | 超级管理员，全部权限 |
| operator | 大部分操作权限 | 运维操作员，可管理但不可管理用户和角色 |
| viewer | *:view | 只读用户，仅可查看 |
| auditor | log:*, config:view | 审计员，可查看日志和配置 |

### 安全响应头

```http
Content-Security-Policy: default-src 'self'; ...
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
X-Content-Type-Options: nosniff
```

---

## 设计系统

### 液态玻璃参数

```css
--ios-glass-blur: 20px;
--ios-glass-saturate: 180%;
--ios-glass-bg: rgba(28, 28, 30, 0.72);       /* Dark */
--ios-glass-bg: rgba(255, 255, 255, 0.72);     /* Light */
--ios-glass-border: rgba(255, 255, 255, 0.12); /* Dark */
--ios-glass-border: rgba(255, 255, 255, 0.6);  /* Light */
```

### 主题切换

主题通过 `data-theme` 属性控制，CSS 变量自动切换：

```html
<html data-theme="dark">  <!-- 暗色模式 -->
<html data-theme="light"> <!-- 亮色模式 -->
```

用户偏好存储在 `localStorage`，首次访问检测系统 `prefers-color-scheme`。

### 间距系统

基于 4pt/8dp 递增系统：`4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 px`

### 圆角系统

`6 / 8 / 12 / 16 / 20 / 24 / 32 / 9999 px`

### 动画系统

| 名称 | 时长 | 缓动函数 | 用途 |
|------|------|----------|------|
| fast | 200ms | ease-out | 微交互（按钮、悬停） |
| normal | 300ms | ease-out | 标准过渡（主题切换） |
| slow | 400ms | ease-out | 复杂过渡 |
| spring | 300ms | spring | 弹性效果（卡片、模态框） |

---

## 测试

### 测试结构

```
backend/tests/
├── conftest.py          # pytest 配置与 fixtures
├── unit/                # 单元测试（无外部依赖）
│   ├── test_auth.py     # 认证模块测试
│   └── test_rbac.py     # RBAC 权限测试
├── integration/         # 集成测试（API 端点）
└── security/            # 安全测试
```

### 运行测试

```bash
cd backend

# 运行全部测试
python -m pytest

# 仅运行单元测试
python -m pytest tests/unit -m unit

# 仅运行安全测试
python -m pytest tests/security -m security

# 查看覆盖率报告
python -m pytest --cov-report=html:htmlcov
# 打开 htmlcov/index.html 查看详细报告
```

### 测试标记

| 标记 | 说明 |
|------|------|
| `@pytest.mark.unit` | 单元测试（快速，无外部依赖） |
| `@pytest.mark.integration` | 集成测试（API 端点） |
| `@pytest.mark.security` | 安全测试 |
| `@pytest.mark.slow` | 慢速测试 |
| `@pytest.mark.e2e` | 端到端测试 |

### 覆盖率要求

最低覆盖率：**70%**（`--cov-fail-under=70`）

---

## 开发指南

### 前端开发

```bash
cd frontend-vue

# 开发模式（热更新）
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

### 后端开发

```bash
cd backend

# 运行开发服务器
python app.py

# 运行测试
python -m pytest

# 运行特定测试
python -m pytest tests/unit/test_auth.py -v
```

### 代码规范

- **前端**：Vue 3 组合式 API (`<script setup>`)，CSS 变量驱动主题
- **后端**：PEP 8 编码规范，类型注解 (`typing`)
- **提交**：Conventional Commits 规范
  - `feat:` 新功能
  - `fix:` Bug 修复
  - `docs:` 文档
  - `refactor:` 重构
  - `test:` 测试
  - `chore:` 构建/工具

### 分支规范

| 分支 | 用途 |
|------|------|
| `main` | 主分支，稳定版本 |
| `dev` | 开发分支 |
| `feature/*` | 功能分支 |
| `fix/*` | 修复分支 |
| `hotfix/*` | 紧急修复分支 |

### 贡献流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

## 部署指南

### 生产环境构建

```bash
# 构建前端
cd frontend-vue
npm run build
# 产物在 dist/ 目录

# 后端直接运行
cd ../backend
python app.py
```

### Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name panel.example.com;

    # 前端静态资源
    location / {
        root /path/to/frontend-vue/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 安全建议

1. 修改 `config.json` 中的 `secret_key` 为随机强密钥
2. 将 `debug` 设为 `false`
3. 配置正确的 `ip_whitelist`
4. 启用 HTTPS（Let's Encrypt 免费 SSL）
5. 启用 2FA 双因素认证
6. 定期更换 admin 密码

---

## FAQ

### Q: GPU 监控不显示？

GPU 监控需要安装 `pynvml` 包且系统有 NVIDIA GPU。未安装或无 GPU 时自动降级，不影响其他功能。

```bash
pip install pynvml
```

### Q: 终端无法连接？

1. 确认后端 SocketIO 服务正常运行
2. 检查防火墙是否放行 WebSocket 端口
3. 确认 Nginx 反向代理正确配置了 WebSocket 升级
4. 查看浏览器控制台是否有连接错误

### Q: 文件管理看不到目录？

文件管理仅显示 `config.json` 中 `whitelist_dirs` 配置的目录。请添加需要访问的目录到白名单。

### Q: 如何修改默认密码？

```bash
cd backend
python scripts/hash_password.py
# 将输出的哈希值写入 config/users.json
```

### Q: 支持哪些数据库？

数据库管理模块支持 MySQL、PostgreSQL 和 SQLite。可在数据库配置页面添加多个数据库连接。

### Q: 如何添加自定义角色？

通过 RBAC API 创建自定义角色：

```bash
curl -X POST http://localhost:5000/api/roles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "developer", "name": "开发者", "permissions": ["dashboard:view", "terminal:execute", "file:view"]}'
```

---

## 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

```
Copyright 2026 xiaopengPanel

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 致谢

感谢以下开源项目的支持：

- [Flask](https://flask.palletsprojects.com/) — Python Web 框架
- [Vue.js](https://vuejs.org/) — 渐进式 JavaScript 框架
- [Vite](https://vitejs.dev/) — 下一代前端构建工具
- [psutil](https://github.com/giampaolo/psutil) — 跨平台系统监控
- [Socket.IO](https://socket.io/) — 实时通信引擎
- [Chart.js](https://www.chartjs.org/) — 数据可视化
- [xterm.js](https://xtermjs.org/) — 终端模拟器
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) — 代码编辑器
- [pyotp](https://github.com/pyauth/pyotp) — TOTP 双因素认证
- [bcrypt](https://github.com/pyca/bcrypt) — 密码哈希
