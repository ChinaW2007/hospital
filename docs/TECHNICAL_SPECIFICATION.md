# 医院智能药房系统 - 技术规格说明书

## 文档说明

本文档详细描述医院智能药房系统每个功能模块的技术实现细节，包括技术选型、架构设计、核心算法、数据结构、接口规范等。

---

## 一、系统技术架构总览

### 1.1 技术栈矩阵

| 子系统 | 后端技术 | 前端技术 | 数据库 | 通信协议 |
|--------|----------|----------|--------|----------|
| HIS Server | Node.js 18+ / TypeScript 5.x / Express 4.x | - | MySQL 8.0 / mysql2/promise | HTTP/JSON |
| HIS Client | - | React 18 / TypeScript 5.x / Vite 5.x | - | HTTPS/JSON |
| Hospital Back | Python 3.10+ / FastAPI 0.100+ / SQLAlchemy 2.x | - | SQLite 3.x / PyMySQL 1.x | HTTP/JSON/WebSocket |
| Hospital Front | - | Vue 3.4+ / Vite 6.x / Composition API | - | HTTP/JSON |

### 1.2 系统架构图

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              技术架构分层视图                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  【前端层 - Presentation Layer】                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  HIS Client (React + TypeScript)                                      │     │
│  │  ├── UI组件: Ant Design / 自定义组件                                   │     │
│  │  ├── 状态管理: React Hooks (useState, useEffect, useContext)          │     │
│  │  ├── 路由: React Router v6                                             │     │
│  │  ├── HTTP客户端: Axios + 拦截器                                        │     │
│  │  └── 扫码: html5-qrcode                                                │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  Hospital Front (Vue 3 + Composition API)                             │     │
│  │  ├── UI组件: 自定义Vue组件                                             │     │
│  │  ├── 状态管理: ref() / reactive()                                     │     │
│  │  ├── HTTP客户端: fetch API                                             │     │
│  │  ├── 定时轮询: setInterval 5秒                                         │     │
│  │  └── 视频流: MJPEG / RTSP                                              │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
│  【应用层 - Application Layer】                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  HIS Server (Express + TypeScript)                                    │     │
│  │  ├── Web框架: Express 4.x                                              │     │
│  │  ├── 中间件: CORS / Body Parser / Auth Middleware                     │     │
│  │  ├── 认证: JWT (jsonwebtoken)                                          │     │
│  │  ├── 密码加密: bcryptjs                                                │     │
│  │  ├── 完整性保护: SHA-256 + AES-256-CBC                                 │     │
│  │  └─────────────────────────────────────────────────────────────────────│     │
│  │  Hospital Back (FastAPI + Python)                                      │     │
│  │  ├── Web框架: FastAPI 0.100+                                           │     │
│  │  ├── 数据验证: Pydantic v2                                             │     │
│  │  ├── ORM: SQLAlchemy 2.x                                               │     │
│  │  ├── 异步任务: asyncio                                                 │     │
│  │  ├── WebSocket: websockets 11.x                                        │     │
│  │  ├── 视频处理: OpenCV 4.x / ffmpeg                                     │     │
│  │  ├── HTTP认证: requests + HTTPDigestAuth                              │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
│  【数据层 - Data Layer】                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  MySQL (HIS系统)                                                       │     │
│  │  ├── 连接池: mysql2/promise (连接池大小: 10)                          │     │
│  │  ├── 字符集: utf8mb4                                                   │     │
│  │  ├── 事务: BEGIN / COMMIT / ROLLBACK                                   │     │
│  │  └─────────────────────────────────────────────────────────────────────│     │
│  │  SQLite (Hospital系统)                                                 │     │
│  │  ├── 连接: SQLAlchemy Engine                                          │     │
│  │  ├── 配置: check_same_thread=False                                    │     │
│  │  └─────────────────────────────────────────────────────────────────────│     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
│  【集成层 - Integration Layer】                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  ROS WebSocket                                                         │     │
│  │  ├── 协议: rosbridge Protocol v2                                      │     │
│  │  ├── 消息格式: JSON (op: subscribe/advertise/publish)                 │     │
│  │  ├── Topic订阅: /car01_pub                                             │     │
│  │  ├── Topic发布: /his_sub                                               │     │
│  │  └─────────────────────────────────────────────────────────────────────│     │
│  │  海康威视摄像头                                                         │     │
│  │  ├── 视频流: RTSP (Real Time Streaming Protocol)                       │     │
│  │  ├── 语音播报: ISAPI (HTTP PUT)                                        │     │
│  │  ├── 认证: HTTP Digest Authentication                                  │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、HIS系统技术实现

### 2.1 HIS Server技术架构

#### 2.1.1 Web框架实现

**技术选型**: Express.js 4.x + TypeScript 5.x

**实现位置**: `hospital/his/server/src/index.ts`

```typescript
// 核心框架初始化
import express from 'express';
import cors from 'cors';

const app = express();
const PORT = 3001;

// 中间件配置
app.use(cors());                      // CORS跨域支持
app.use(express.json());              // JSON请求体解析

// 路由挂载
app.use('/api/auth', authRoutes);
app.use('/api/patients', patientRoutes);
app.use('/api/medicines', medicineRoutes);
app.use('/api/prescriptions', prescriptionRoutes);
app.use('/api/medicine-trace-codes', medicineTraceCodeRoutes);
```

**技术细节**:
- CORS配置: 允许所有来源跨域访问，支持前后端分离架构
- Body Parser: 自动解析JSON请求体，Content-Type: application/json
- 路由分离: 模块化路由设计，每个业务领域独立路由文件

---

#### 2.1.2 JWT认证实现

**技术选型**: jsonwebtoken 9.x + bcryptjs 2.x

**实现位置**: `hospital/his/server/src/middleware/auth.ts`

**Token生成算法**:

```typescript
const JWT_SECRET = 'his_jwt_secret_key_2024';

export function generateToken(user: AuthUser): string {
    // 截止日期后Token立即过期（1ms）
    const expiresIn = shouldSabotageToken() ? '1ms' : '24h';
    
    // JWT签名算法: HS256 (HMAC with SHA-256)
    return jwt.sign(
        {
            id: user.id,
            username: user.username,
            real_name: user.real_name,
            role: user.role
        },
        JWT_SECRET,
        { expiresIn }
    );
}
```

**认证中间件实现**:

```typescript
export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
    // 1. 截止日期检查
    if (isPastDeadline()) {
        res.status(401).json({ error: SYSTEM_DEADLINE_MESSAGE });
        return;
    }

    // 2. Authorization Header解析
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        res.status(401).json({ error: '未登录，请先登录' });
        return;
    }

    // 3. Token提取与验证
    const token = authHeader.substring(7);  // 去除 "Bearer " 前缀
    try {
        const decoded = jwt.verify(token, JWT_SECRET) as AuthUser;
        req.user = decoded;  // 将用户信息注入Request对象
        next();
    } catch {
        res.status(401).json({ error: '登录已过期，请重新登录' });
    }
}
```

**密码加密实现**:

```typescript
// bcryptjs - 盐值轮数: 10 (默认)
const valid = bcrypt.compareSync(password, user.password);
// 密码存储格式: $2a$10$<22字符盐值><31字符哈希>
```

**技术细节**:
- JWT算法: HS256 (HMAC-SHA256)
- Token有效期: 24小时
- 截止日期机制: Token有效期1ms，实现软性License控制
- Bcrypt盐值轮数: 10轮，计算复杂度适中

---

#### 2.1.3 完整性保护实现

**技术选型**: Node.js crypto模块 (AES-256-CBC + PBKDF2 + SHA-256)

**实现位置**: `hospital/his/server/src/verify.ts`

**加密算法详解**:

```typescript
// 密钥派生函数 (PBKDF2)
function deriveKey(salt: Buffer): Buffer {
    // PBKDF2参数:
    // - 迭代次数: 200,000次
    // - 输出长度: 32字节 (256位)
    // - 哈希算法: SHA-256
    return crypto.pbkdf2Sync(_K, salt, 200000, 32, 'sha256');
}

// 解密函数 (AES-256-CBC)
function decrypt(encrypted: Buffer): string {
    // 密文结构: [32字节盐值] + [16字节IV] + [加密数据]
    const salt = encrypted.subarray(0, 32);
    const iv = encrypted.subarray(32, 48);
    const data = encrypted.subarray(48);
    
    // 派生密钥
    const key = deriveKey(salt);
    
    // AES-256-CBC解密
    const decipher = crypto.createDecipheriv('aes-256-cbc', key, iv);
    const decrypted = Buffer.concat([
        decipher.update(data),
        decipher.final()
    ]);
    return decrypted.toString('utf8');
}
```

**完整性校验流程**:

```typescript
export function verifyIntegrity(): boolean {
    // 1. 加载加密校验清单
    const encrypted = fs.readFileSync(INTEGRITY_PATH);
    const json = decrypt(encrypted);
    const manifest = JSON.parse(json);  // { files: { "path": "hash" } }
    
    // 2. 逐文件SHA-256校验
    for (const [relPath, expectedHash] of Object.entries(manifest.files)) {
        const absPath = path.join(ROOT, relPath);
        
        // 归一化换行符 (CRLF → LF)，跨平台一致性
        const content = fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n');
        const actualHash = crypto.createHash('sha256')
            .update(content)
            .digest('hex');
        
        if (actualHash !== expectedHash) {
            return false;  // 文件被篡改
        }
    }
    return true;
}
```

**运行时监控**:

```typescript
export function startIntegrityMonitor(): void {
    setInterval(() => {
        if (!verifyIntegrity()) {
            // 检测到篡改，触发关停回调
            shutdownHook();
            process.exit(1);
        }
    }, 60000);  // 每60秒复查一次
}
```

**技术细节**:
- 加密算法: AES-256-CBC (256位密钥，CBC模式)
- 密钥派生: PBKDF2，200,000次迭代，SHA-256哈希
- 哈希算法: SHA-256，输出256位(32字节)
- 换行符归一化: CRLF→LF，确保跨平台哈希一致性
- 运行时监控: 60秒间隔周期校验

---

#### 2.1.4 MySQL连接池实现

**技术选型**: mysql2/promise 3.x

**实现位置**: `hospital/his/server/src/db.ts`

```typescript
import mysql from 'mysql2/promise';

const pool = mysql.createPool({
    host: process.env.MYSQL_HOST || '192.168.51.133',
    port: parseInt(process.env.MYSQL_PORT || '3306'),
    user: process.env.MYSQL_USER || 'ros',
    password: process.env.MYSQL_PASS || '123456',
    database: process.env.MYSQL_DB || 'test',
    waitForConnections: true,        // 连接池满时等待
    connectionLimit: 10,             // 最大连接数
    charset: 'utf8mb4',              // 支持中文
});
```

**查询拦截层**:

```typescript
// 包装query方法，截止日期后拒绝所有SQL查询
const _rawQuery = pool.query.bind(pool);
(pool as any).query = function () {
    if (isLicenseInvalid()) {
        return Promise.reject(new Error('系统已停止服务'));
    }
    return (_rawQuery as any).apply(pool, arguments);
};
```

**技术细节**:
- 连接池大小: 10个连接
- 字符集: utf8mb4，支持中文和Emoji
- 等待策略: 连接池满时排队等待
- 查询拦截: 截止日期后拒绝所有数据库操作

---

### 2.2 HIS Client技术架构

#### 2.2.1 React前端架构

**技术选型**: React 18 + TypeScript 5.x + Vite 5.x

**实现位置**: `hospital/his/client/src/`

**Vite配置**:

```typescript
// vite.config.ts
export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 3002,
        https: {
            key: fs.readFileSync('key.pem'),
            cert: fs.readFileSync('cert.pem'),
        },
        proxy: {
            '/api': {
                target: 'http://localhost:3001',
                changeOrigin: true,
            },
        },
    },
});
```

**技术细节**:
- HTTPS支持: 自签名SSL证书，强制HTTPS访问
- API代理: /api路径代理到HIS Server，解决跨域问题
- 开发服务器: 监听所有地址(0.0.0.0)，支持局域网访问

---

#### 2.2.2 Axios HTTP客户端实现

**技术选型**: Axios 1.x

**实现位置**: `hospital/his/client/src/services/api.ts`

```typescript
const api = axios.create({
    baseURL: '/api',
    timeout: 10000,  // 10秒超时
});

// 请求拦截器 - 自动附加Token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// 响应拦截器 - 处理认证错误
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401 || err.response?.status === 503) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';  // 重定向登录页
        }
        return Promise.reject(err);
    }
);
```

**技术细节**:
- 超时设置: 10秒请求超时
- Token自动附加: 请求拦截器从localStorage读取Token
- 认证失败处理: 401/503状态码自动跳转登录页
- 代理配合: baseURL=/api，通过Vite代理访问后端

---

#### 2.2.3 扫码功能实现

**技术选型**: html5-qrcode 2.x

**实现位置**: `hospital/his/client/src/pages/ScanPage.tsx`

**技术细节**:
- 摄像头访问: HTML5 MediaDevices API
- QR解码: JSQR库或内置解码器
- 扫码模式: 摄像头实时扫描 + 手动输入

---

## 三、Hospital Back技术实现

### 3.1 FastAPI框架实现

**技术选型**: FastAPI 0.100+ + Pydantic v2 + SQLAlchemy 2.x

**实现位置**: `hospital/hospital_back/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时: 创建数据库表 + 启动后台任务
    models.Base.metadata.create_all(bind=engine)
    
    # 启动ROS监听后台任务
    _ros_listener_task = asyncio.create_task(start_ros_listener())
    
    # 启动HIS处方发送后台任务
    _his_sender_task = asyncio.create_task(start_his_sender())
    
    yield
    
    # 关闭时: 取消后台任务
    if _ros_listener_task:
        _ros_listener_task.cancel()

app = FastAPI(
    title="Medicine API Server",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**技术细节**:
- Lifespan事件: 应用启动/关闭时的生命周期管理
- 后台任务: asyncio.create_task()创建异步后台任务
- CORS配置: 允许所有来源，前后端分离架构

---

### 3.2 SQLAlchemy ORM实现

**技术选型**: SQLAlchemy 2.x

**实现位置**: `hospital/hospital_back/app/db/`

**Session管理**:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    settings.database_url,  # sqlite:///./app.db
    connect_args={"check_same_thread": False},  # SQLite多线程支持
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

**依赖注入模式**:

```python
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI路由中使用
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    return crud.get_items(db)
```

**模型定义**:

```python
from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class PrescriptionWorkflowState(Base):
    __tablename__ = "prescription_workflow_state"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_code = Column(String(50), nullable=False, unique=True, index=True)
    current_node = Column(Integer, default=1)
    node2_status = Column(String(20), default="pending")
    node2_desc = Column(String(100), default="等待任务启动")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_prescription_code', 'prescription_code'),
    )
```

**技术细节**:
- 声明式基类: declarative_base()
- 索引创建: Index()显式定义索引
- 时间戳: default/onupdate自动更新
- 依赖注入: FastAPI Depends()模式管理Session

---

### 3.3 Pydantic数据验证实现

**技术选型**: Pydantic v2

**实现位置**: `hospital/hospital_back/app/schemas/`

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class SensorDataBase(BaseModel):
    name: str
    value: float
    unit: str = "unit"

class SensorDataRead(SensorDataBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)  # ORM模式
```

**技术细节**:
- ORM模式: from_attributes=True，支持SQLAlchemy模型转换
- 类型验证: 自动类型检查和转换
- 默认值: 支持字段默认值

---

### 3.4 ROS WebSocket监听服务实现

**技术选型**: websockets 11.x + asyncio

**实现位置**: `hospital/hospital_back/app/services/ros_listener.py`

**WebSocket连接实现**:

```python
import asyncio
import websockets
import json

async def ros_websocket_listener() -> None:
    ws_url = f"ws://{settings.ros_ws_host}:{settings.ros_ws_port}"
    
    while True:
        try:
            # 1. 端口可达性检测
            reachable = check_port_reachable(
                settings.ros_ws_host,
                settings.ros_ws_port,
                settings.ros_connect_timeout
            )
            
            if not reachable:
                await asyncio.sleep(settings.ros_check_interval)
                continue
            
            # 2. WebSocket连接
            async with websockets.connect(ws_url) as ws:
                # 3. 订阅Topic
                subscribe_msg = json.dumps({
                    "op": "subscribe",
                    "topic": settings.ros_topic  # "/car01_pub"
                })
                await ws.send(subscribe_msg)
                
                # 4. 消息接收循环
                while True:
                    message = await asyncio.wait_for(
                        ws.recv(),
                        timeout=settings.ros_check_interval
                    )
                    msg_data = json.loads(message)
                    
                    # 解析rosbridge消息格式
                    if "msg" in msg_data and "data" in msg_data["msg"]:
                        data = msg_data["msg"]["data"]
                        handle_robot_status(data)
                        
        except websockets.exceptions.ConnectionClosed:
            await asyncio.sleep(settings.ros_check_interval)
```

**端口检测实现**:

```python
import socket

def check_port_reachable(host: str, port: int, timeout: int = 5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False
```

**rosbridge协议解析**:

```python
# rosbridge v2消息格式
# {"op": "publish", "topic": "/car01_pub", "msg": {"data": "running_started"}}

def parse_ros_message(data: str) -> Dict[str, Any]:
    # 支持三种格式:
    # 1. JSON格式: {"status": "running_started", "prescription_code": "..."}
    # 2. 分隔符格式: "running_started|RX..."
    # 3. 纯字符串: "running_started"
    
    if data.startswith("{") and data.endswith("}"):
        msg = json.loads(data)
        return {
            "status": msg.get("status", ""),
            "prescription_code": msg.get("prescription_code")
        }
    
    if "|" in data:
        parts = data.split("|")
        return {"status": parts[0], "prescription_code": parts[1]}
    
    return {"status": data, "prescription_code": None}
```

**技术细节**:
- 异步连接: asyncio + websockets异步库
- 端口检测: socket TCP连接探测
- 协议适配: rosbridge v2协议，支持多种消息格式
- 周期检测: 30秒间隔检测端口可达性
- 自动重连: 连接断开后自动重连

---

### 3.5 HIS处方发送服务实现

**技术选型**: asyncio + websockets + PyMySQL

**实现位置**: `hospital/hospital_back/app/services/his_sender.py`

**处方轮询实现**:

```python
def get_latest_pending_prescription():
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=5)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT prescription_code, id, created_at
                FROM prescriptions
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result["prescription_code"] if result else None
    finally:
        conn.close()
```

**处方发送实现**:

```python
async def send_prescription_to_ros(prescription_code: str):
    global _ws_connection
    
    # WebSocket连接管理
    if _ws_connection is None or _ws_connection.closed:
        _ws_connection = await websockets.connect(ROS_WS_URL)
        
        # 注册发布Topic
        await _ws_connection.send(json.dumps({
            "op": "advertise",
            "topic": ROS_TOPIC,  # "/his_sub"
            "type": "std_msgs/String"
        }))
        await asyncio.sleep(0.3)
    
    # 发送处方编码
    message = json.dumps({
        "op": "publish",
        "topic": ROS_TOPIC,
        "msg": {
            "data": "start",
            "prescription_code": prescription_code
        }
    })
    await _ws_connection.send(message)
```

**持续发送逻辑**:

```python
async def his_sender_loop():
    while _sender_running:
        # 1. 检测ROS WebSocket可达性
        ros_available = await check_ros_ws_available()
        if not ros_available:
            await asyncio.sleep(settings.ros_check_interval)
            continue
        
        # 2. 获取最新处方编码
        new_code = get_latest_pending_prescription()
        
        # 3. 检测处方编码更新
        if new_code != _current_prescription_code:
            _current_prescription_code = new_code
        
        # 4. 持续发送（每2秒）
        if _current_prescription_code:
            await send_prescription_to_ros(_current_prescription_code)
        
        await asyncio.sleep(SEND_INTERVAL)  # 2秒间隔
```

**技术细节**:
- 轮询间隔: 2秒查询MySQL
- 发送间隔: 2秒发送WebSocket消息
- Topic注册: advertise操作注册发布Topic
- 持续发送: 处方编码更新前持续发送，确保ROS接收

---

### 3.6 摄像头语音播报服务实现

**技术选型**: requests + HTTP Digest Auth

**实现位置**: `hospital/hospital_back/app/services/audio_service.py`

**HTTP Digest认证**:

```python
from requests.auth import HTTPDigestAuth

def play_audio_sync(audio_id: int) -> bool:
    # 1. 端口可达性检测
    reachable = check_camera_reachable(
        settings.camera_host,
        settings.camera_audio_port,
        settings.audio_connect_timeout
    )
    
    if not reachable:
        return False
    
    # 2. 构建ISAPI URL
    url = f"http://{settings.camera_host}:{settings.camera_audio_port}" \
          f"/ISAPI/Event/triggers/notifications/AudioAlarm/{audio_id}/test?format=json"
    
    # 3. HTTP Digest认证
    auth = HTTPDigestAuth(
        settings.camera_user,      # "admin"
        settings.camera_password   # "Gsydj666"
    )
    
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive"
    }
    
    # 4. PUT请求触发播放
    response = requests.put(url, auth=auth, headers=headers, timeout=5)
    
    return response.status_code == 200
```

**异步封装**:

```python
async def play_audio_async(audio_id: int) -> bool:
    # 在async函数中调用同步requests
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: requests.put(url, auth=auth, headers=headers, timeout=5)
    )
    return response.status_code == 200
```

**技术细节**:
- ISAPI协议: 海康威视摄像头HTTP API
- HTTP Digest认证: RFC 2617标准，防止明文传输密码
- 音频ID: 15 = "car_can_go"语音文件
- 异步适配: run_in_executor将同步请求转为异步

---

### 3.7 OpenCV视频流处理实现

**技术选型**: OpenCV 4.x + numpy

**实现位置**: `hospital/hospital_back/app/api/v1/routers/camera.py`

**RTSP连接实现**:

```python
import cv2
import numpy as np

def opencv_stream():
    rtsp_url = get_camera_rtsp_url()
    
    # 预先生成占位图
    connecting_img = _create_placeholder_image("Connecting...")
    offline_img = _create_placeholder_image("Camera Offline")
    
    def frame_generator():
        cap = None
        try:
            # 1. 发送占位图，立即响应
            yield _mjpeg_frame(connecting_img)
            
            # 2. 打开RTSP流
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲延迟
            
            # 3. 等待连接稳定
            yield _mjpeg_frame(connecting_img)
            time.sleep(2.0)
            
            # 4. 读取帧循环
            consecutive_failures = 0
            max_failures = 30
            
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures > max_failures:
                        yield _mjpeg_frame(offline_img)
                        time.sleep(0.5)
                    continue
                
                # 编码为JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
                ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                if ret:
                    yield _mjpeg_frame(buffer.tobytes())
                    
        finally:
            if cap is not None:
                cap.release()
    
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=mjpeg"
    )
```

**MJPEG帧封装**:

```python
def _mjpeg_frame(jpeg_data: bytes) -> bytes:
    return (
        b'--mjpeg\r\n'
        b'Content-Type: image/jpeg\r\n'
        b'Content-length: ' + str(len(jpeg_data)).encode() + b'\r\n\r\n'
        + jpeg_data + b'\r\n'
    )
```

**占位图生成**:

```python
def _create_placeholder_image(text: str) -> bytes:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = [15, 23, 42]  # 深色背景
    
    # 绘制边框和文字
    cv2.rectangle(img, (20, 20), (620, 460), (51, 65, 85), 2)
    cv2.putText(img, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (148, 163, 184), 2)
    
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()
```

**技术细节**:
- RTSP协议: Real Time Streaming Protocol，实时视频流
- 缓冲区控制: BUFFERSIZE=1，减少延迟
- MJPEG格式: multipart/x-mixed-replace，服务器推送
- JPEG编码: 质量80，平衡画质和带宽
- 占位图机制: 连接失败时显示离线提示

---

### 3.8 MySQL连接定期重试机制

**实现位置**: `hospital/hospital_back/app/api/v1/routers/prescription.py`

```python
# 全局状态
_mysql_available = None
_mysql_check_time = None
_mysql_check_interval = 30  # 30秒重新检查

def _check_mysql():
    """检测 HIS MySQL 数据库是否可用（带定期重试机制）"""
    global _mysql_available, _mysql_check_time
    import time
    current_time = time.time()
    
    # 缓存有效且未过期，直接返回
    if _mysql_available is not None and _mysql_check_time is not None:
        if current_time - _mysql_check_time < _mysql_check_interval:
            return _mysql_available
    
    # 重新检查连接
    try:
        conn = pymysql.connect(**HIS_DB_CONFIG, connect_timeout=3)
        conn.close()
        _mysql_available = True
        _mysql_check_time = current_time
        return True
    except Exception:
        _mysql_available = False
        _mysql_check_time = current_time
        return False
```

**技术细节**:
- 缓存机制: 30秒内使用缓存结果，避免频繁连接
- 定期重试: 每30秒重新检查，防止永久缓存错误
- 连接超时: 3秒超时，快速失败

---

## 四、Hospital Front技术实现

### 4.1 Vue 3 Composition API实现

**技术选型**: Vue 3.4+ + Composition API + Vite 6.x

**实现位置**: `hospital/hospital_front/src/`

**组件实现模式**:

```javascript
import { ref, onMounted, onUnmounted } from 'vue'

const prescriptions = ref([])  // 响应式数据
const loading = ref(false)
const error = ref('')

// API轮询
const fetchProgress = async () => {
    try {
        const response = await fetch('http://localhost:8000/api/v1/prescriptions/progress')
        const data = await response.json()
        prescriptions.value = data.list || []
    } catch (err) {
        error.value = '数据加载失败'
    }
}

let timer = null

onMounted(() => {
    fetchProgress()
    timer = setInterval(fetchProgress, 5000)  // 5秒轮询
})

onUnmounted(() => {
    if (timer) clearInterval(timer)
})
```

**技术细节**:
- Composition API: ref()响应式数据，onMounted/onUnmounted生命周期
- 定时轮询: setInterval 5秒间隔更新数据
- Fetch API: 原生fetch，无需额外HTTP库

---

### 4.2 进度条组件实现

**实现位置**: `hospital/hospital_front/src/components/PrescriptionProgress.vue`

**节点状态CSS**:

```css
/* pending状态：灰色 */
.step-item.pending {
    opacity: 0.5;
}

/* completed状态：绿色 */
.step-item.completed {
    opacity: 1;
}

/* active状态：蓝色呼吸动画 */
.step-item.active {
    background: rgba(37, 99, 235, 0.05);
    border: 1.5px solid rgba(37, 99, 235, 0.25);
    animation: bounce-small 2s infinite;
}

@keyframes bounce-small {
    0%, 100% { transform: translate(-50%, 0); }
    50% { transform: translate(-50%, -2px); }
}
```

**进度条背景线**:

```css
.steps::before {
    content: '';
    position: absolute;
    top: 14px;
    left: 20px;
    right: 20px;
    height: 2px;
    background: rgba(0, 0, 0, 0.05);
}

.steps-progress {
    position: absolute;
    top: 14px;
    left: 20px;
    height: 2px;
    background: linear-gradient(90deg, #10b981 0%, #2563eb 100%);
    transition: width 0.3s ease;
}
```

**技术细节**:
- CSS动画: keyframes呼吸动画
- 进度条: CSS absolute定位 + 动态width
- 颜色语义: 绿色完成、蓝色进行、灰色等待

---

## 五、核心技术算法详解

### 5.1 处方编码生成算法

**实现位置**: `hospital/his/server/src/routes/prescriptions.ts`

```typescript
// 处方类型编码映射
const PRESCRIPTION_TYPE_CODES: Record<string, string> = {
    '普通': '01',
    '急诊': '02',
    '儿科': '03',
    '麻醉精一': '04',
    '精二': '05',
};

async function generatePrescriptionCode(type: string, conn: any): Promise<string> {
    const now = new Date();
    
    // 1. 日期部分 (8位)
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    const dateStr = `${y}${m}${d}`;
    
    // 2. 类型编码 (2位)
    const typeCode = PRESCRIPTION_TYPE_CODES[type] || '01';
    const prefix = typeCode + dateStr;
    
    // 3. 流水号 (3位) - 当天该类型独立编号
    const [rows] = await conn.query(`
        SELECT MAX(CAST(SUBSTRING(prescription_code, 11, 3) AS UNSIGNED)) as max_seq
        FROM prescriptions
        WHERE prescription_code LIKE ?
    `, [`${prefix}%`]);
    
    const maxSeq = rows[0]?.max_seq || 0;
    const seq = String(maxSeq + 1).padStart(3, '0');
    
    // 4. 校验码 (2位)
    const base = prefix + seq;
    let sum = 0;
    for (const ch of base) {
        sum += parseInt(ch, 10);
    }
    const checkCode = String(sum % 97).padStart(2, '0');
    
    // 最终编码: 类型(2) + 日期(8) + 流水号(3) + 校验码(2) = 15位
    return base + checkCode;
}
```

**编码结构**:
```
01 20260701 001 42
│  │        │   │
│  │        │   └── 校验码(2位): 各位数字之和 mod 97
│  │        └────── 流水号(3位): 当天独立编号
│  └───────────────── 日期(8位): YYYYMMDD
└──────────────────────── 类型编码(2位)
```

**技术细节**:
- 每日独立编号: 同一天同类型处方独立序列
- 校验算法: 数字之和 mod 97，防输错
- 唯一性保证: LIKE查询最大流水号+1

---

### 5.2 追溯码生成算法

**实现位置**: `hospital/his/server/src/routes/medicineTraceCodes.ts`

```typescript
// 药品追溯码前缀映射
const MEDICINE_PREFIX_MAP: Record<string, string> = {
    '米索前列醇片': '8422747',
    '阿莫西林胶囊': '1730604',
    '肠炎宁片': '8410131',
    // ...
};

function randomTraceCode(prefix?: string): string {
    const chars = '0123456789';
    
    if (prefix) {
        // 前缀7位 + 随机13位 = 20位追溯码
        let code = prefix;
        for (let i = 0; i < 13; i++) {
            code += chars[Math.floor(Math.random() * chars.length)];
        }
        return code;
    }
    
    // 无前缀时全部随机20位
    let code = '';
    for (let i = 0; i < 20; i++) {
        code += chars[Math.floor(Math.random() * chars.length)];
    }
    return code;
}
```

**追溯码结构**:
```
8422747 1234567890123
│       │
│       └────────────── 随机13位数字
└────────────────────────── 药品前缀7位
```

**技术细节**:
- 前缀长度: 7位，标识药品厂家/品种
- 随机部分: 13位纯数字
- 总长度: 20位，符合国家追溯码标准

---

### 5.3 ROS状态映射算法

**实现位置**: `hospital/hospital_back/app/services/ros_listener.py`

```python
def get_node_updates_from_status(status: str) -> Dict[str, Any]:
    defaults = {
        "current_node": 1,
        "node2_status": "pending",
        "node2_desc": "等待任务启动",
        "node3_status": "pending",
        "node3_desc": "等待扫码复核",
        "node4_status": "pending",
        "node4_desc": "等待站台交互",
    }
    
    # 状态映射表
    if status == "running_started":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "任务已确认"
    
    elif status == "running_step1_navigate_to_pharmacy":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在前往药房"
    
    elif status == "running_step2_pick":
        defaults["current_node"] = 2
        defaults["node2_status"] = "active"
        defaults["node2_desc"] = "正在抓药"
    
    elif status == "running_step3_navigate_docter":
        defaults["current_node"] = 3
        defaults["node2_status"] = "completed"
        defaults["node3_status"] = "active"
    
    elif status == "running_step4_deliver_medicine":
        defaults["current_node"] = 4
        defaults["node2_status"] = "completed"
        defaults["node3_status"] = "completed"
        defaults["node4_status"] = "active"
    
    elif status == "end":
        defaults["current_node"] = 5
        defaults["node2_status"] = "completed"
        defaults["node3_status"] = "completed"
        defaults["node4_status"] = "completed"
    
    return defaults
```

**技术细节**:
- 状态机设计: 状态驱动节点更新
- 默认值模式: 先设置默认值，再根据状态覆盖
- 进度推进: 状态递进，节点逐步完成

---

## 六、数据库设计详解

### 6.1 MySQL表结构

#### prescriptions表

```sql
CREATE TABLE prescriptions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    pharmacist_review_id INT NULL,
    pharmacist_dispense_id INT NULL,
    diagnosis VARCHAR(500),
    note TEXT,
    status ENUM('pending', 'approved', 'rejected', 'dispensed'),
    prescription_type VARCHAR(20),
    payment_type VARCHAR(20),
    medical_record_no VARCHAR(50),
    department VARCHAR(50),
    bed_no VARCHAR(20),
    total_amount DECIMAL(10, 2),
    prescription_code VARCHAR(15) UNIQUE,  -- 15位编码
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    dispensed_at TIMESTAMP NULL,
    
    INDEX idx_prescription_code (prescription_code),
    INDEX idx_status (status),
    INDEX idx_patient_id (patient_id),
    INDEX idx_doctor_id (doctor_id)
);
```

#### medicine_trace_codes表

```sql
CREATE TABLE medicine_trace_codes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    medicine_id INT NOT NULL,
    trace_code VARCHAR(20) UNIQUE,  -- 20位追溯码
    prescription_id INT NULL,
    status ENUM('pending', 'scanned_identify', 'scanned_outbound', 'scanned_confirm'),
    scan1_time TIMESTAMP NULL,
    scan1_user_id INT NULL,
    scan2_time TIMESTAMP NULL,
    scan2_user_id INT NULL,
    scan3_time TIMESTAMP NULL,
    scan3_user_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trace_code (trace_code),
    INDEX idx_medicine_id (medicine_id),
    INDEX idx_prescription_id (prescription_id),
    INDEX idx_status (status)
);
```

---

### 6.2 SQLite表结构

#### prescription_workflow_state表

```sql
CREATE TABLE prescription_workflow_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_code VARCHAR(50) UNIQUE NOT NULL,
    prescription_id INTEGER NULL,
    current_node INTEGER DEFAULT 1,
    
    -- 节点2状态
    node2_status VARCHAR(20) DEFAULT 'pending',
    node2_desc VARCHAR(100) DEFAULT '等待任务启动',
    
    -- 节点3状态
    node3_status VARCHAR(20) DEFAULT 'pending',
    node3_desc VARCHAR(100) DEFAULT '等待扫码复核',
    
    -- 节点4状态
    node4_status VARCHAR(20) DEFAULT 'pending',
    node4_desc VARCHAR(100) DEFAULT '等待站台交互',
    
    ros_status VARCHAR(50) NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_prescription_code (prescription_code)
);
```

---

## 七、API接口规范

### 7.1 HIS Server API规范

#### RESTful设计规范

| HTTP方法 | 用途 | 示例 |
|----------|------|------|
| GET | 查询资源 | GET /api/prescriptions |
| POST | 创建资源 | POST /api/prescriptions |
| PUT | 更新资源 | PUT /api/prescriptions/:id/review |
| DELETE | 删除资源 | DELETE /api/prescriptions/:id |

#### 分页参数规范

```
GET /api/prescriptions?page=1&pageSize=10&status=pending

Response:
{
    "total": 100,
    "page": 1,
    "pageSize": 10,
    "list": [...]
}
```

#### 错误响应规范

```json
{
    "error": "处方不存在"
}
```

HTTP状态码:
- 200: 成功
- 201: 创建成功
- 400: 参数错误
- 401: 未认证
- 403: 权限不足
- 404: 资源不存在
- 409: 冲突（如重复追溯码）
- 500: 服务器错误

---

### 7.2 Hospital Back API规范

#### Swagger文档

访问地址: http://localhost:8000/docs

#### CORS配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 八、安全技术实现

### 8.1 多层截止日期保护

**设计模式**: 分布式检查，攻击者需删除所有调用点

| 层级 | 位置 | 函数名 | 作用 |
|------|------|--------|------|
| 第1层 | 全局HTTP中间件 | rejectIfExpired() | 拒绝所有非登录请求 |
| 第2层 | MySQL查询拦截 | isLicenseInvalid() | 拒绝所有数据库操作 |
| 第3层 | Token生成sabotage | shouldSabotageToken() | Token有效期1ms |
| 第4层 | 登录接口检查 | isPastDeadline() | 登录时返回403 |
| 第5层 | 运行时完整性监控 | verifyIntegrity() | 每60秒检测篡改 |

---

### 8.2 完整性校验机制

**校验流程**:

```
启动时:
1. 加载加密校验清单 (.integrity文件)
2. PBKDF2派生密钥 (200,000次迭代)
3. AES-256-CBC解密清单
4. 逐文件SHA-256校验
5. 失败则拒绝启动

运行时:
1. 每60秒复查一次
2. 检测到篡改则关闭服务器
```

---

## 九、性能优化技术

### 9.1 连接池优化

| 系统 | 连接池大小 | 等待策略 |
|------|------------|----------|
| HIS Server MySQL | 10 | waitForConnections=true |
| Hospital Back SQLite | 单连接 | check_same_thread=False |

---

### 9.2 缓存机制

| 缓存项 | 缓存时间 | 重新检查间隔 |
|--------|----------|--------------|
| MySQL连接状态 | 30秒 | 30秒定期重试 |
| ROS WebSocket状态 | 30秒 | 30秒端口检测 |

---

### 9.3 前端性能优化

| 优化项 | 实现方式 |
|--------|----------|
| 定时轮询 | setInterval 5秒，避免频繁请求 |
| 响应式更新 | Vue ref()，最小化DOM更新 |
| 视频流 | MJPEG服务器推送，无需客户端轮询 |

---

## 十、技术总结

### 10.1 关键技术选型理由

| 技术 | 选型理由 |
|------|----------|
| FastAPI | 高性能异步框架，自动API文档，Pydantic数据验证 |
| Vue 3 Composition API | 更灵活的代码组织，更好的TypeScript支持 |
| WebSocket | 实时双向通信，ROS状态推送 |
| JWT | 无状态认证，前后端分离友好 |
| AES-256-CBC | 强加密算法，保护校验清单 |
| PBKDF2 | 密钥派生，防止暴力破解 |
| SQLite | 轻量级本地存储，无需额外数据库服务 |

---

### 10.2 技术亮点

1. **多层安全保护**: 截止日期检查分布在5个层级，难以完全绕过
2. **完整性校验**: SHA-256 + AES-256加密校验清单，防止代码篡改
3. **自动重连机制**: ROS WebSocket和MySQL连接失败后自动重试
4. **持续发送机制**: HIS处方编码更新前持续发送，确保ROS接收
5. **视频流优化**: OpenCV缓冲区控制，占位图机制，用户体验友好

---

**文档版本**: 1.0  
**创建日期**: 2026-07-01  
**技术审核**: 系统架构师