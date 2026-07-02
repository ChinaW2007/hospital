# 医院智能药房系统 - 数据流向文档

## 一、系统架构概览

本系统由四个子系统组成：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              医院智能药房系统                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  HIS Server │    │ HIS Client  │    │Hospital Back│    │Hospital Front│ │
│  │  (Node.js)  │    │  (React)    │    │ (FastAPI)   │    │   (Vue)     │ │
│  │  Port:3001  │    │  Port:3002  │    │  Port:8000  │    │  Port:5175  │ │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘ │
│         │                  │                  │                  │         │
│         └──────────────────┼──────────────────┼──────────────────┼─────────│
│                            │                  │                  │         │
│                    ┌───────▼───────┐   ┌──────▼──────┐   ┌───────▼───────┐│
│                    │ MySQL Database│   │SQLite(App.db)│   │ROS WebSocket  ││
│                    │192.168.51.133 │   │   Local      │   │192.168.51.12  ││
│                    │   Port:3306   │   │              │   │   Port:9090   ││
│                    └───────────────┘   └──────────────┘   └───────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘

外部设备：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  海康威视摄像头  │    │   ROS机器人     │    │   扫码设备      │
│192.168.51.251   │    │192.168.51.12    │    │   HIS Client    │
│  Port:80/554    │    │  Port:9090      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 二、数据流向详解

### 1. 处方数据流向

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           处方数据完整流向                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  【来源】医生在 HIS Client 开具处方                                        │
│      │                                                                   │
│      ▼                                                                   │
│  HIS Client (React) ──────────► HIS Server API                          │
│      POST /api/prescriptions                                             │
│      │                                                                   │
│      ▼                                                                   │
│  MySQL Database (prescriptions表)                                        │
│      │ status = 'pending'                                                │
│      │ prescription_code = "类型编码+日期+流水号+校验码"                   │
│      │                                                                   │
│      ├─────────────────────► Hospital Back (HIS Sender服务)              │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    ROS WebSocket (/his_sub Topic)                 │
│      │                        │ JSON: {"op":"publish",                   │
│      │                        │        "msg":{"data":"start",            │
│      │                        │                 "prescription_code":"xx"}}│
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    ROS机器人接收处方信息                           │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    ROS机器人执行任务                               │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    ROS WebSocket (/car01_pub Topic)               │
│      │                        │ 状态消息: running_started,               │
│      │                        │          running_step1_navigate_to_pharmacy│
│      │                        │          running_step2_pick               │
│      │                        │          running_step3_navigate_docter    │
│      │                        │          running_step4_deliver_medicine   │
│      │                        │          end                             │
│      │                        │                                          │
│      ├─────────────────────► Hospital Back (ROS Listener服务)            │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    SQLite (prescription_workflow_state表)          │
│      │                        │ 更新节点状态                              │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    Hospital Front API                             │
│      │                        │ GET /api/v1/prescriptions/progress        │
│      │                        │                                          │
│      │                        ▼                                          │
│      │                    Hospital Front (Vue大屏)                       │
│      │                        │ 显示药品运输流程进度条                    │
│      │                        │                                          │
│      ▼                                                                   │
│  HIS Client (药师端) ─────────► HIS Server API                           │
│      PUT /api/prescriptions/:id/review                                   │
│      │ status = 'approved'                                               │
│      │                                                                   │
│      ▼                                                                   │
│  HIS Client (药师端) ─────────► HIS Server API                           │
│      PUT /api/prescriptions/:id/dispense                                 │
│      │ status = 'dispensed'                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2. 处方状态流转

| 状态 | 含义 | 触发者 | 数据去向 |
|------|------|--------|----------|
| `pending` | 待审核 | 医生开具处方 | MySQL → HIS Sender → ROS WebSocket |
| `approved` | 已审核通过 | 药师审核 | MySQL |
| `rejected` | 已驳回 | 药师审核 | MySQL |
| `dispensed` | 已发药 | 药师发药确认 | MySQL |

### 3. 处方编码生成规则

```
处方编码格式: 类型编码(2位) + 日期(8位) + 流水号(3位) + 校验码(2位) = 15位

示例: 01 20260701 001 42

类型编码:
- 01: 普通处方
- 02: 急诊处方
- 03: 儿科处方
- 04: 麻醉精一处方
- 05: 精二处方

校验码算法: (前缀 + 流水号)各位数字之和 mod 97
```

---

### 4. 药品追溯码数据流向

```
┌─────────────────────────────────────────────────────────────────────┐
│                     药品追溯码三次扫码流程                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  【第一次扫码 - 药品识别】                                           │
│      HIS Client 扫码 ───► HIS Server API                           │
│      PUT /api/medicine-trace-codes/:id/scan                         │
│      或 POST /api/medicine-trace-codes/scan-by-code                 │
│      │                                                              │
│      ▼                                                              │
│  MySQL (medicine_trace_codes表)                                     │
│      │ status = 'scanned_identify'                                  │
│      │ scan1_time, scan1_user_id, prescription_id                   │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (节点2 - 任务确认) 显示进度                          │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  【第二次扫码 - 药品出库】                                           │
│      HIS Client 扫码 ───► HIS Server API                           │
│      PUT /api/medicine-trace-codes/:id/scan                         │
│      │                                                              │
│      ▼                                                              │
│  MySQL (medicine_trace_codes表)                                     │
│      │ status = 'scanned_outbound'                                  │
│      │ scan2_time, scan2_user_id                                    │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (节点3 - 扫码复合) 显示进度                          │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  【第三次扫码 - 最终确认】                                           │
│      HIS Client 扫码 ───► HIS Server API                           │
│      PUT /api/medicine-trace-codes/:id/scan                         │
│      │                                                              │
│      ▼                                                              │
│  MySQL (medicine_trace_codes表)                                     │
│      │ status = 'scanned_confirm'                                   │
│      │ scan3_time, scan3_user_id                                    │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (节点4 - 站台交互) 显示进度                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5. 追溯码状态流转

| 状态 | 含义 | 扫码次数 | 数据去向 |
|------|------|----------|----------|
| `pending` | 未扫码 | 0 | MySQL |
| `scanned_identify` | 已识别 | 1 | MySQL → Hospital Front (节点2) |
| `scanned_outbound` | 已出库 | 2 | MySQL → Hospital Front (节点3) |
| `scanned_confirm` | 已确认 | 3 | MySQL → Hospital Front (节点4) |

---

### 6. ROS机器人状态数据流向

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROS机器人状态数据流向                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  【处方发送方向】                                                    │
│      Hospital Back (HIS Sender)                                     │
│      │ 定时轮询 MySQL pending处方                                    │
│      │ 每2秒发送一次                                                 │
│      ▼                                                              │
│  ROS WebSocket (ws://192.168.51.12:9090)                           │
│      │ Topic: /his_sub                                              │
│      │ 消息格式: JSON                                                │
│      │ {"op":"publish",                                             │
│      │  "topic":"/his_sub",                                         │
│      │  "msg":{"data":"start",                                      │
│      │       "prescription_code":"01 20260701 001 42"}}             │
│      │                                                              │
│      ▼                                                              │
│  ROS机器人接收处方 → 启动运输任务                                    │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  【状态反馈方向】                                                    │
│      ROS机器人执行任务                                               │
│      │ 发布状态消息                                                  │
│      ▼                                                              │
│  ROS WebSocket (ws://192.168.51.12:9090)                           │
│      │ Topic: /car01_pub                                            │
│      │ 消息格式: JSON或分隔符                                        │
│      │                                                              │
│      ▼                                                              │
│  Hospital Back (ROS Listener)                                       │
│      │ 订阅 /car01_pub                                              │
│      │ 解析状态消息                                                  │
│      │                                                              │
│      ├──────────────────────► SQLite (prescription_workflow_state)  │
│      │                          │ 更新节点状态                       │
│      │                          │                                   │
│      ├──────────────────────► 摄像头语音播报                         │
│      │                          │ running_started时播放audio_id=15   │
│      │                          │                                   │
│      ▼                                                              │
│  Hospital Front API                                                 │
│      │ GET /api/v1/prescriptions/progress                           │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (Vue大屏)                                           │
│      │ 更新药品运输流程进度条                                        │
│      │ 4节点: 开具处方 → 任务确认 → 扫码复合 → 站台交互              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7. ROS状态映射表

| ROS状态 | 对应节点 | 节点状态 | 节点描述 |
|---------|----------|----------|----------|
| `running_started` | 节点2 | active | 任务已启动 |
| `running_step1_navigate_to_pharmacy` | 节点2 | active | 正在前往药房 |
| `running_step2_pick` | 节点2 | active | 正在抓药 |
| `running_step3_navigate_docter` | 节点3 | active | 前往医生/患者 |
| `running_step4_deliver_medicine` | 节点4 | active | 正在送药 |
| `running_step5_return` | 节点4 | active | 正在返回起点 |
| `end` | 全部 | completed | 任务完成 |
| `error_*` | 当前节点 | active | 错误状态 |

---

### 8. 摄像头语音播报数据流向

```
┌─────────────────────────────────────────────────────────────────────┐
│                   摄像头语音播报数据流向                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ROS Listener 收到 running_started                                  │
│      │                                                              │
│      ▼                                                              │
│  Hospital Back (Audio Service)                                      │
│      │ 检测摄像头端口可达性                                          │
│      │ Port: 80 (HTTP API)                                          │
│      │                                                              │
│      ▼                                                              │
│  海康威视摄像头 ISAPI接口                                            │
│      │ PUT /ISAPI/Event/triggers/notifications/AudioAlarm/15/test   │
│      │ HTTP Digest认证                                              │
│      │                                                              │
│      ▼                                                              │
│  摄像头播放语音 "car_can_go"                                         │
│      │ audio_id = 15                                                │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front API                                                 │
│      │ GET /api/v1/workflow/audio/status                            │
│      │ 返回 last_play_time, last_play_status                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 9. 摄像头视频流数据流向

```
┌─────────────────────────────────────────────────────────────────────┐
│                    摄像头视频流数据流向                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  【海康威视摄像头】                                                  │
│      RTSP流: rtsp://admin:password@192.168.51.251:554/...           │
│      │                                                              │
│      ▼                                                              │
│  Hospital Back (Camera API)                                         │
│      │ GET /api/v1/camera/proxy (ffmpeg转码)                        │
│      │ GET /api/v1/camera/opencv (OpenCV处理)                       │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (CameraFeed.vue)                                    │
│      │ 显示摄像头画面                                                │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  【ROS机器人摄像头】                                                 │
│      MJPEG流: http://192.168.51.12:8080/stream?topic=...            │
│      │                                                              │
│      ▼                                                              │
│  Hospital Back (Camera API)                                         │
│      │ GET /api/v1/camera/robot                                     │
│      │                                                              │
│      ▼                                                              │
│  Hospital Front (CameraFeed.vue)                                    │
│      │ 显示机器人视角                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、数据库表结构

### 1. MySQL数据库 (HIS系统)

| 表名 | 用途 | 主要字段 |
|------|------|----------|
| `users` | 用户表 | id, username, password, real_name, role |
| `patients` | 患者表 | id, name, gender, age, phone, id_card |
| `medicines` | 药品表 | id, name, specification, price, stock |
| `prescriptions` | 处方表 | id, prescription_code, patient_id, doctor_id, status, total_amount |
| `prescription_items` | 处方明细表 | id, prescription_id, medicine_id, dosage, quantity |
| `medicine_trace_codes` | 追溯码表 | id, medicine_id, trace_code, status, scan1_time, scan2_time, scan3_time |
| `medicine_trace_prefixes` | 追溯码前缀表 | medicine_id, prefix |

### 2. SQLite数据库 (Hospital Back)

| 表名 | 用途 | 主要字段 |
|------|------|----------|
| `sensor_records` | 传感器记录 | id, name, value, unit, timestamp |
| `frontend_records` | 前端数据记录 | id, key, value, created_at |
| `prescription_workflow_state` | 处方流程状态 | id, prescription_code, current_node, node2_status, node3_status, node4_status |

---

## 四、数据同步机制

### 1. MySQL连接定期重试机制

```python
# Hospital Back 连接 HIS MySQL
# 每30秒重新检查连接状态
_mysql_check_interval = 30

# 防止连接失败后永久缓存错误状态
def _check_mysql():
    if 缓存有效且未过期:
        return 缓存状态
    # 重新检查连接
    try:
        conn = pymysql.connect(...)
        return True
    except:
        return False
```

### 2. ROS WebSocket定期检测机制

```python
# 每30秒检测端口可达性
ros_check_interval = 30

# 自动重连逻辑
while True:
    if not 端口可达:
        等待30秒重试
        continue
    # 连接WebSocket
    async with websockets.connect(ws_url):
        # 订阅Topic
        # 接收消息
```

### 3. HIS处方发送持续机制

```python
# 每2秒轮询MySQL
POLL_INTERVAL = 2

# 每2秒发送处方编码
SEND_INTERVAL = 2

# 处方编码更新前持续发送
while running:
    new_code = get_latest_pending_prescription()
    if new_code != current_code:
        # 处方编码更新
        current_code = new_code
    if current_code:
        # 持续发送
        send_prescription_to_ros(current_code)
    sleep(2)
```

---

## 五、数据流向图总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                        核心数据流向图                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   医生 ──► HIS Client ──► HIS Server ──► MySQL                      │
│              │              │              │                         │
│              │              │              ▼                         │
│              │              │       Hospital Back (HIS Sender)       │
│              │              │              │                         │
│              │              │              ▼                         │
│              │              │       ROS WebSocket ──► 机器人         │
│              │              │              │                         │
│              │              │              ▼                         │
│              │              │       机器人执行 ──► ROS状态消息       │
│              │              │              │                         │
│              │              │              ▼                         │
│              │              │       Hospital Back (ROS Listener)     │
│              │              │              │                         │
│              │              │              ├─► SQLite (流程状态)     │
│              │              │              │                         │
│              │              │              ├─► 摄像头语音播报        │
│              │              │              │                         │
│              │              │              ▼                         │
│              │              │       Hospital Front API               │
│              │              │              │                         │
│              │              │              ▼                         │
│   药师 ──► HIS Client ──► HIS Server ──► MySQL                      │
│              │              │              │                         │
│              │              │              ▼                         │
│          扫码确认 ──► 追溯码状态 ──► Hospital Front                   │
│              │              │              │                         │
│              │              │              ▼                         │
│         药品运输流程 ──► 4节点进度条 ──► 大屏显示                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 六、配置参数汇总

| 配置项 | 值 | 用途 |
|--------|-----|------|
| HIS MySQL Host | 192.168.51.133 | HIS系统数据库地址 |
| HIS MySQL Port | 3306 | MySQL端口 |
| ROS WebSocket Host | 192.168.51.12 | ROS机器人地址 |
| ROS WebSocket Port | 9090 | ROS WebSocket端口 |
| ROS Topic (订阅) | /car01_pub | 接收机器人状态 |
| ROS Topic (发布) | /his_sub | 发送处方编码 |
| 摄像头 Host | 192.168.51.251 | 海康威视摄像头 |
| 摄像头 RTSP Port | 554 | RTSP视频流端口 |
| 摄像头 HTTP Port | 80 | ISAPI语音播报端口 |
| Audio ID (car_can_go) | 15 | 任务确认语音 |

---

**文档版本**: 1.0  
**更新日期**: 2026-07-01  
**作者**: 系统自动生成