# 🏥 医院智能药房系统

一个集成HIS（医院信息系统）的智能药房管理系统，支持实时处方追踪、机器人药品运输、药品追溯码验证和可视化大屏展示。

---

## 📋 系统概述

本系统实现了完整的药品运输流程自动化：

- **医生开具处方** → HIS系统记录处方 → 自动发送到ROS机器人
- **机器人执行任务** → ROS状态实时反馈 → 大屏进度条更新
- **药师审核发药** → 追溯码三次扫码 → 完成药品追溯

### 核心功能

| 功能模块 | 说明 |
|----------|------|
| HIS系统 | 医生开具处方、药师审核发药、药品追溯码管理 |
| 药房大屏 | 实时显示处方进度条、摄像头画面、环境监控 |
| ROS集成 | WebSocket监听机器人状态、自动发送处方编码 |
| 语音播报 | 任务确认时自动播放摄像头语音 |

---

## 🏗️ 系统架构

```
┌───────────────────────────────────────────────────────────────┐
│                     医院智能药房系统                            │
├───────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  HIS Server │  │  HIS Client │  │ Hospital Back│  │Hospital Front│ │
│  │  (Node.js)  │  │   (React)   │  │  (FastAPI)  │  │    (Vue)    │ │
│  │  Port:3001  │  │  Port:3002  │  │  Port:8000  │  │  Port:5175  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │       │
│         └────────────────┼────────────────┼────────────────┼───────│
│                          │                │                │       │
│                  ┌───────▼───────┐  ┌──────▼──────┐  ┌──────▼──────┐│
│                  │ MySQL Database│  │SQLite(App.db)│  │ROS WebSocket ││
│                  │192.168.51.133 │  │    Local     │  │192.168.51.12 ││
│                  │   Port:3306   │  │              │  │  Port:9090   ││
│                  └───────────────┘  └──────────────┘  └──────────────┘│
└───────────────────────────────────────────────────────────────┘

外部设备：
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│海康威视摄像头│    │  ROS机器人  │    │  扫码设备   │
│192.168.51.251│    │192.168.51.12│    │ HIS Client │
│Port:80/554 │    │ Port:9090   │    │            │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 目录结构

```
hospital/
├── hospital/
│   ├── hospital_back/        # Python FastAPI 后端服务
│   │   ├── app/
│   │   │   ├── api/v1/routers/  # API路由
│   │   │   ├── services/        # 后台服务（ROS监听、HIS发送、语音播报）
│   │   │   ├── core/config.py   # 配置文件
│   │   │   └── db/models.py     # 数据模型
│   │   └── app.py               # 启动入口
│   │
│   ├── hospital_front/       # Vue 3 大屏前端
│   │   ├── src/components/   # Vue组件
│   │   └── vite.config.js    # Vite配置
│   │
│   └── his/
│       ├── server/           # Node.js HIS后端
│       │   ├── src/routes/   # API路由
│       │   └── src/db.ts     # MySQL连接
│       │
│       └── client/           # React HIS前端
│           ├── src/pages/    # 页面组件
│           └── vite.config.ts
│
├── RosConnectCamara/         # ROS摄像头集成脚本
│   └── testRos/              # 测试脚本
│
├── docs/                     # 文档目录
│   ├── DATA_FLOW.md          # 数据流向文档
│   ├── FEATURES.md           # 功能清单文档
│   └── API_TEST_RESULTS.md   # API测试结果文档
│
├── restart-all.ps1           # 一键重启脚本
├── README.md                 # 本文档
└── .gitignore                # Git忽略配置
```

---

## 🚀 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+（HIS数据库）
- ROS（可选，用于机器人集成）
- ffmpeg（可选，用于摄像头流转码）

### 一键重启

```powershell
powershell -ExecutionPolicy Bypass -File restart-all.ps1
```

### 手动启动

```bash
# 1. Hospital Backend（药房智能系统后端）
cd hospital/hospital_back
pip install -r requirements.txt
python app.py

# 2. Hospital Frontend（大屏前端）
cd hospital/hospital_front
npm install
npm run dev

# 3. HIS Server（HIS系统后端）
cd hospital/his/server
npm install
npm run dev

# 4. HIS Client（HIS系统前端）
cd hospital/his/client
npm install
npm run dev
```

---

## 🔗 服务端口

| 服务 | 端口 | 访问地址 | 说明 |
|------|------|----------|------|
| Hospital Backend | 8000 | http://localhost:8000 | 药房智能系统API |
| Hospital Dashboard | 5175 | http://localhost:5175 | 药房大屏展示 |
| HIS Server | 3001 | http://localhost:3001 | HIS系统API |
| HIS Client | 3002 | https://localhost:3002 | HIS系统前端 |

### API文档

- Hospital Backend Swagger UI: http://localhost:8000/docs

---

## 🔐 测试账号

| 角色 | 用户名 | 密码 | 权限 |
|------|----------|----------|------|
| 医生 | doctor1 | 123456 | 开具处方、查看自己开具的处方 |
| 药师 | pharmacist1 | 123456 | 审核处方、发药确认、扫码操作 |
| 管理员 | admin | 123456 | 全部权限 |

---

## 🔄 药品运输流程

### 4节点进度条

```
① 开具处方 → ② 任务确认 → ③ 扫码复合 → ④ 站台交互
```

| 节点 | 名称 | 状态来源 | 完成条件 |
|------|------|----------|----------|
| 1 | 开具处方 | HIS prescription.status | 医生开具处方后即为绿色（已完成） |
| 2 | 任务确认 | ROS running_started | ROS机器人启动任务后变为蓝色（进行中） |
| 3 | 扫码复合 | 追溯码 scan2_time | 药品第二次扫码后变为绿色 |
| 4 | 站台交互 | 追溯码 scan3_time | 药品第三次扫码后变为绿色 |

### 节点颜色说明

- **绿色（completed）**: 已完成
- **蓝色（active）**: 进行中，带呼吸动画
- **灰色（pending）**: 等待中

---

## 📡 ROS集成

### WebSocket Topics

| Topic | 方向 | 说明 |
|-------|------|------|
| `/car01_pub` | 接收 | 机器人状态更新 |
| `/his_sub` | 发送 | 处方编码发布 |

### ROS状态消息

| ROS消息 | 对应节点 | 含义 |
|---------|----------|------|
| `running_started` | 节点2 | 任务启动 |
| `running_step1_navigate_to_pharmacy` | 节点2 | 正在前往药房 |
| `running_step2_pick` | 节点2 | 正在抓药 |
| `running_step3_navigate_docter` | 节点3 | 前往医生/患者 |
| `running_step4_deliver_medicine` | 节点4 | 正在送药 |
| `running_step5_return` | 节点4 | 正在返回起点 |
| `end` | 全部完成 | 任务完成 |
| `error_*` | 当前节点 | 错误状态 |

### 处方发送格式

```json
{
    "op": "publish",
    "topic": "/his_sub",
    "msg": {
        "data": "start",
        "prescription_code": "01 20260701 001 42"
    }
}
```

---

## 🔊 语音播报

### 触发条件

当收到 `running_started` ROS消息时，自动触发摄像头播放语音。

### 技术实现

- **摄像头**: 海康威视摄像头 ISAPI接口
- **音频ID**: 15 (car_can_go - 车辆可以通行)
- **认证方式**: HTTP Digest认证
- **API地址**: `PUT /ISAPI/Event/triggers/notifications/AudioAlarm/15/test`

### 测试接口

```powershell
# 手动触发语音播报
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/workflow/audio/play' -Method POST -Body '{"audio_id":15}' -ContentType 'application/json'
```

---

## ⚙️ 配置说明

### 配置模板

项目提供以下配置模板文件：

| 模板文件 | 说明 |
|----------|------|
| `config.template.py` | Hospital Backend配置模板 |
| `.env.template` | HIS Server环境变量模板 |

### Hospital Backend 配置项

```python
# 本地数据库
database_url = "sqlite:///./app.db"

# HIS MySQL数据库
his_mysql_host = "YOUR_HOST"       # MySQL服务器地址
his_mysql_port = 3306              # MySQL端口
his_mysql_user = "YOUR_USER"       # MySQL用户名
his_mysql_pass = "YOUR_PASSWORD"   # MySQL密码
his_mysql_db = "YOUR_DATABASE"     # MySQL数据库名

# 摄像头配置
camera_host = "YOUR_CAMERA_IP"     # 摄像头IP
camera_port = 554                  # RTSP端口
camera_user = "admin"              # 摄像头用户名
camera_password = "YOUR_PASSWORD"  # 摄像头密码
camera_audio_port = 80             # HTTP API端口

# ROS WebSocket配置
ros_ws_host = "YOUR_ROS_IP"        # ROS服务器IP
ros_ws_port = 9090                 # WebSocket端口
ros_topic = "/car01_pub"           # 订阅Topic
ros_check_interval = 30            # 检测间隔（秒）
ros_connect_timeout = 5            # 连接超时（秒）
```

---

## 📦 核心功能清单

### 已实现功能

| 模块 | 功能 | 状态 |
|------|------|------|
| HIS系统 | 用户登录认证 | ✅ |
| HIS系统 | 患者管理 | ✅ |
| HIS系统 | 药品管理 | ✅ |
| HIS系统 | 处方开具（医生） | ✅ |
| HIS系统 | 处方审核（药师） | ✅ |
| HIS系统 | 发药确认（药师） | ✅ |
| HIS系统 | 追溯码三次扫码 | ✅ |
| HIS系统 | 处方编码自动生成 | ✅ |
| Hospital Back | 处方数据同步 | ✅ |
| Hospital Back | ROS WebSocket监听 | ✅ |
| Hospital Back | HIS处方自动发送 | ✅ |
| Hospital Back | 摄像头语音播报 | ✅ |
| Hospital Back | 周期性检测重连 | ✅ |
| Hospital Front | 处方进度条展示 | ✅ |
| Hospital Front | 摄像头画面展示 | ✅ |

### 功能完成率

| 子系统 | 完成率 |
|--------|--------|
| HIS Server | 85% |
| HIS Client | 100% |
| Hospital Back | 95% |
| Hospital Front | 61% |
| **总体** | **76%** |

详细功能清单请参考: [docs/FEATURES.md](docs/FEATURES.md)

---

## 📊 数据流向

完整数据流向请参考: [docs/DATA_FLOW.md](docs/DATA_FLOW.md)

### 核心数据流

```
医生 ──► HIS Client ──► HIS Server ──► MySQL
          │                │                │
          │                │                ▼
          │                │        Hospital Back (HIS Sender)
          │                │                │
          │                │                ▼
          │                │        ROS WebSocket ──► 机器人
          │                │                │
          │                │                ▼
          │                │        机器人执行 ──► ROS状态
          │                │                │
          │                │                ▼
          │                │        Hospital Back (ROS Listener)
          │                │                │
          │                │                ├─► SQLite (流程状态)
          │                │                │
          │                │                ├─► 摄像头语音播报
          │                │                │
          │                │                ▼
          │                │        Hospital Front API
          │                │                │
          │                │                ▼
药师 ──► HIS Client ──► HIS Server ──► MySQL
          │                │                │
          │                │                ▼
      扫码确认 ──► 追溯码状态 ──► Hospital Front
          │                │                │
          │                │                ▼
     药品运输流程 ──► 4节点进度条 ──► 大屏显示
```

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| **HIS Backend** | Node.js, TypeScript, Express, MySQL |
| **HIS Frontend** | React, TypeScript, Vite |
| **Hospital Backend** | Python, FastAPI, SQLAlchemy, PyMySQL, websockets |
| **Hospital Frontend** | Vue 3, Vite |
| **数据库** | MySQL (HIS), SQLite (Hospital) |
| **集成** | WebSocket, ROS rosbridge, 海康威视ISAPI |
| **视频流** | RTSP, MJPEG, ffmpeg, OpenCV |

---

## 📝 文档

| 文档 | 说明 |
|------|------|
| [DATA_FLOW.md](docs/DATA_FLOW.md) | 数据流向详细说明 |
| [FEATURES.md](docs/FEATURES.md) | 功能清单（已实现/未实现） |
| [API_TEST_RESULTS.md](docs/API_TEST_RESULTS.md) | API接口测试结果 |

---

## 📄 许可证

MIT License

---

## 👥 作者

医院智能药房系统开发团队

---

**文档版本**: 2.0  
**更新日期**: 2026-07-01  
**更新内容**: 添加完整架构说明、数据流向、功能清单和API测试结果