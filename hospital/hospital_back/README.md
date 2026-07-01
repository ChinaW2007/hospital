# Medicine API Server

这是一个基于 FastAPI 的后端项目，用于摄像头 RTSP/视频接口、传感器接口、AI Agent 接口、前端数据接口和数据库存储。

## 目录结构

- `app.py` - 项目入口，用于启动 FastAPI 应用
- `config.py` - 应用配置文件，用于生成摄像头 RTSP 地址和读取环境变量
- `app/` - 应用主代码目录
  - `app/main.py` - FastAPI 应用实例和路由注册
  - `app/core/config.py` - 全局配置管理
  - `app/api/v1/routers/` - REST API 路由模块
  - `app/db/` - 数据库模型和会话管理
  - `app/schemas/` - Pydantic 请求/响应模型
- `static/index.html` - 前端测试页面
- `app.db` - SQLite 数据库文件（运行时生成）

## 安装依赖

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行项目

```powershell
python app.py
```

然后访问：

```
http://127.0.0.1:8000       
http://127.0.0.1:8000/docs  - swagger文档
```

## 常用接口

### 摄像头接口
- `GET /api/v1/camera/url` - 返回当前 RTSP 地址
- `GET /api/v1/camera/test` - 使用 ffmpeg 测试 RTSP 连接
- `GET /api/v1/camera/proxy` - 启动 RTSP 到 MJPEG 的代理
- `GET /api/v1/camera/opencv/test` - 使用 OpenCV 测试摄像头连接
- `GET /api/v1/camera/opencv` - 使用 OpenCV 生成 MJPEG 视频流

### 传感器接口
- `GET /api/v1/sensors/` - 获取传感器数据列表
- `POST /api/v1/sensors/` - 新增传感器数据

### AI Agent
- `POST /api/v1/agent/query` - 提交 AI 查询并返回结果

### 数据接口
- `GET /api/v1/data/items` - 获取前端数据项列表
- `POST /api/v1/data/items` - 创建前端数据项

## 数据库

默认使用 SQLite：`sqlite:///./app.db`

## 注意事项

- 请确认系统已安装 `ffmpeg`，否则摄像头测试和代理无法正常工作。
- `opencv-python` 在某些平台上对 RTSP 支持有差异，可能需要调整环境或使用 OpenCV 的构建版本。
