# 小鹏面板 (xiaopengPanel)

> 一款现代化的服务器管理面板，采用类 iOS 26 风格设计，支持多平台运行。

## 项目简介

小鹏面板是一个功能完善的服务器管理工具，采用前后端分离架构，提供直观的用户界面和强大的服务器管理功能。项目支持 Windows 和 Linux 平台，具备系统监控、文件管理、终端访问、站点管理等核心功能。

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [开发指南](#开发指南)
- [许可证](#许可证)

## 功能特性

### 核心功能

- **系统监控** - 实时显示 CPU、内存、磁盘、网络使用情况
- **仪表盘** - 可自定义的小组件布局，支持拖拽排序
- **终端访问** - 基于 WebSocket 的实时终端，支持多标签页
- **文件管理** - 在线文件浏览、上传、下载、编辑
- **代码编辑器** - 内置代码编辑器，支持语法高亮（JavaScript/Python/HTML/CSS/SQL）
- **站点管理** - 虚拟主机管理，支持域名绑定、SSL 状态查看
- **进程管理** - 系统进程查看与管理
- **服务管理** - 支持 Windows 服务和 Linux systemd 服务管理
- **数据库管理** - SQLite 数据库管理（支持扩展）

### 设计特色

- **iOS 26 风格** - 液态玻璃效果、圆角系统、弹性动画
- **响应式设计** - 支持桌面端和移动端自适应
- **国际化** - 支持中文和英文两种语言
- **暗色主题** - 默认暗色主题，支持主题切换
- **微交互** - 精心设计的按钮反馈、加载动画

## 技术栈

### 后端

| 技术 | 说明 |
|------|------|
| Python 3 | 核心语言 |
| Flask | Web 框架 |
| Flask-SocketIO | WebSocket 实时通信 |
| Flask-CORS | 跨域支持 |
| psutil | 系统监控 |
| PyJWT | JWT 认证 |
| bcrypt | 密码加密 |
| SQLite | 数据库 |

### 前端

| 技术 | 说明 |
|------|------|
| Vue 3 | 前端框架 |
| Vite | 构建工具 |
| Vuex | 状态管理 |
| Vue I18n | 国际化 |
| Socket.IO Client | WebSocket 客户端 |
| Chart.js | 数据可视化 |
| vuedraggable | 拖拽排序 |

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+
- npm 或 yarn

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/xiaopengPanel.git
cd xiaopengPanel
```

#### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

> 如果 `requirements.txt` 不存在，请安装以下依赖：
> ```bash
> pip install flask flask-cors flask-socketio psutil pyjwt bcrypt
> ```

#### 3. 安装前端依赖

```bash
cd ../frontend-vue
npm install
```

#### 4. 运行项目

启动后端（端口 5000）：

```bash
cd ../backend
python app.py
```

启动前端开发服务器（端口 5173）：

```bash
cd ../frontend-vue
npm run dev
```

访问 `http://localhost:5173` 即可使用小鹏面板。

### 默认登录信息

- **用户名**: `admin`
- **密码**: `Admin123!`

## 项目结构

```
xiaopengPanel/
├── backend/                    # Python 后端
│   ├── app.py                  # Flask 应用入口
│   ├── api/
│   │   └── routes.py           # API 路由定义
│   └── modules/
│       ├── auth.py             # JWT 认证模块
│       ├── system_info.py      # 系统信息获取
│       ├── system_monitor.py   # 系统资源监控
│       ├── terminal_manager.py # WebSocket 终端
│       ├── db_manager.py       # SQLite 数据库管理
│       ├── file_manager.py     # 文件管理
│       ├── site_manager.py     # 网站管理
│       ├── process_manager.py  # 进程管理
│       ├── service_manager.py  # 系统服务管理
│       ├── log_manager.py      # 日志管理
│       └── middleware.py       # 安全中间件
├── config/                     # 配置文件
│   └── config.py               # 全局配置
├── frontend-vue/               # Vue 3 前端
│   ├── src/
│   │   ├── components/         # 页面组件
│   │   │   ├── LoginModern.vue # 登录页
│   │   │   ├── DashboardEnhanced.vue # 仪表盘
│   │   │   ├── Terminal.vue    # 终端
│   │   │   ├── FileManager.vue # 文件管理
│   │   │   ├── CodeEditor.vue  # 代码编辑器
│   │   │   └── Sites.vue       # 站点管理
│   │   ├── styles/             # 样式系统
│   │   │   ├── design-system.css # iOS 26 设计系统
│   │   │   └── animations.css  # 动画系统
│   │   ├── locales/            # 国际化
│   │   │   ├── zh-CN.js        # 中文
│   │   │   └── en-US.js        # 英文
│   │   ├── store/              # Vuex 状态管理
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 入口文件
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md                   # 项目说明文档
```

## 配置说明

### 后端配置

配置文件位于 `config/config.py`，主要配置项包括：

```python
# 服务器配置
SECRET_KEY = 'xiaopeng_panel_secret_key'
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000
LOG_LEVEL = 'INFO'

# 用户配置（密码需使用 bcrypt 加密）
USERS = {
    'admin': {
        'password': '$2b$12$...',  # bcrypt 哈希密码
        'role': 'admin'
    }
}

# 安全配置
IP_WHITELIST_ENABLED = False
CORS_ORIGINS = ['http://localhost:5173']
```

### 前端配置

前端配置位于 `frontend-vue/vite.config.js`：

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

可以通过环境变量覆盖部分配置：

```bash
# 设置端口
export XIAOPENG_PORT=8080

# 设置密钥
export XIAOPENG_SECRET_KEY=your_secret_key
```

## API 文档

### 认证接口

#### 登录

```
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin123!"
}

Response:
{
  "status": "success",
  "token": "eyJ...",
  "user": { "username": "admin", "role": "admin" }
}
```

#### 刷新令牌

```
POST /api/refresh_token
Content-Type: application/json

{
  "username": "admin",
  "token": "eyJ..."
}
```

### 系统监控接口

#### 获取系统信息

```
GET /api/system/info
Authorization: Bearer <token>
```

#### 获取 CPU 使用率

```
GET /api/system/cpu
Authorization: Bearer <token>
```

#### 获取内存使用率

```
GET /api/system/memory
Authorization: Bearer <token>
```

### 文件管理接口

#### 列出目录

```
GET /api/files?path=/var/www
Authorization: Bearer <token>
```

#### 读取文件

```
GET /api/files/read?path=/var/www/index.html
Authorization: Bearer <token>
```

#### 保存文件

```
POST /api/files/save
Authorization: Bearer <token>
Content-Type: application/json

{
  "path": "/var/www/index.html",
  "content": "<!DOCTYPE html>..."
}
```

### 站点管理接口

#### 获取站点列表

```
GET /api/sites
Authorization: Bearer <token>
```

#### 创建站点

```
POST /api/sites
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "example.com",
  "web_server": "nginx",
  "php_version": "7.4",
  "root_dir": "/var/www/example.com"
}
```

### 终端接口

#### 获取终端建议

```
GET /api/terminal/suggestions?partial=ls
Authorization: Bearer <token>
```

#### 保存命令历史

```
POST /api/terminal/history
Authorization: Bearer <token>
Content-Type: application/json

{
  "command": "ls -la"
}
```

## 开发指南

### 前端开发

```bash
cd frontend-vue

# 开发模式
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
```

### 代码规范

- **前端**: 遵循 Vue 3 组合式 API 规范
- **后端**: 遵循 PEP 8 编码规范
- **提交**: 使用 Conventional Commits 规范

## 贡献指南

### 开发环境搭建

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

### 分支规范

- `main` - 主分支，稳定版本
- `dev` - 开发分支
- `feature/*` - 功能分支
- `fix/*` - 修复分支
- `hotfix/*` - 紧急修复分支

## 已知问题

1. 部分组件仍使用模拟数据，需要对接真实 API
2. 移动端体验需进一步优化
3. 大文件编辑可能存在性能问题

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

## 联系方式

- **项目主页**: https://github.com/your-username/xiaopengPanel
- **问题反馈**: https://github.com/your-username/xiaopengPanel/issues
- **邮箱**: your-email@example.com

## 致谢

感谢以下开源项目的支持：

- [Flask](https://flask.palletsprojects.com/)
- [Vue.js](https://vuejs.org/)
- [psutil](https://github.com/giampaolo/psutil)
- [Socket.IO](https://socket.io/)
- [Chart.js](https://www.chartjs.org/)
