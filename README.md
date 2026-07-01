# 🏥 Hospital Intelligent Pharmacy System

An intelligent hospital pharmacy management system with real-time prescription tracking, robotic arm integration, and visual dashboard.

## 📋 System Overview

This system integrates HIS (Hospital Information System) with a pharmacy dashboard, enabling:
- Real-time prescription monitoring
- Robotic arm drug dispensing workflow
- QR code verification for drug traceability
- AI-powered voice announcements
- Visual progress tracking

## 🏗️ Architecture

```
hospital/
├── hospital/
│   ├── hospital_back/        # Python FastAPI Backend
│   ├── hospital_front/       # Vue 3 Dashboard (Port 5175)
│   └── his/
│       ├── client/           # React HIS Frontend (Port 3002)
│       └── server/           # Node.js HIS Backend (Port 3001)
└── RosConnectCamara/         # ROS Camera Integration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MySQL (for HIS database)
- ROS (optional, for robot integration)

### One-Key Restart

```powershell
powershell -ExecutionPolicy Bypass -File restart-all.ps1
```

### Manual Start

```bash
# 1. Hospital Backend
cd hospital/hospital_back
pip install -r requirements.txt
python app.py

# 2. Hospital Frontend Dashboard
cd hospital/hospital_front
npm install
npm run dev

# 3. HIS Server
cd hospital/his/server
npm install
npm run dev

# 4. HIS Client
cd hospital/his/client
npm install
npm run dev
```

## 🔗 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Hospital Backend | 8000 | http://localhost:8000 |
| Hospital Dashboard | 5175 | http://localhost:5175 |
| HIS Server | 3001 | http://localhost:3001 |
| HIS Client | 3002 | https://localhost:3002 |

## 🔐 Test Accounts

| Role | Username | Password |
|------|----------|----------|
| Doctor | doctor1 | 123456 |
| Pharmacist | pharmacist1 | 123456 |
| Admin | admin | 123456 |

## 🔄 Workflow Process

```
① HIS Prescription → ② Task Confirmation → ③ QR Verification → ④ Window Delivery
```

| Step | Name | Status Source |
|------|------|---------------|
| 1 | 开具处方 | HIS prescription.status |
| 2 | 任务确认 | ROS running_started |
| 3 | 扫码复合 | Trace code scan2_time |
| 4 | 站台交互 | Trace code scan3_time |

## 📡 ROS Integration

### WebSocket Topics

- `/car01_pub` - Robot status updates
- `/his_sub` - Prescription code publishing

### Status Messages

| ROS Message | Meaning |
|-------------|---------|
| running_started | Task started |
| running_step1_navigate_to_pharmacy | Going to pharmacy |
| running_step2_pick | Picking drugs |
| running_step3_navigate_docter | Going to doctor/patient |
| running_step4_deliver_medicine | Delivering drugs |
| running_step5_return | Returning to start |
| end | Task completed |

## 🔊 Audio Announcements

When `running_started` is received, the camera plays audio announcement via ISAPI:
- Audio ID: 15 (car_can_go)
- Trigger: HTTP PUT to camera ISAPI endpoint

## ⚙️ Configuration

Create `.env` files based on templates:

### Hospital Backend (config.py template)

```python
# Database
database_url = "sqlite:///./app.db"

# HIS MySQL
his_mysql_host = "YOUR_HOST"
his_mysql_port = 3306
his_mysql_user = "YOUR_USER"
his_mysql_pass = "YOUR_PASSWORD"
his_mysql_db = "YOUR_DATABASE"

# Camera
camera_host = "YOUR_CAMERA_IP"
camera_user = "admin"
camera_password = "YOUR_PASSWORD"

# ROS WebSocket
ros_ws_host = "YOUR_ROS_IP"
ros_ws_port = 9090
```

## 📦 Key Features

- ✅ Real-time prescription dashboard
- ✅ HIS system integration
- ✅ ROS robot status monitoring
- ✅ Drug traceability with QR codes
- ✅ Voice announcements on task confirmation
- ✅ One-key restart script
- ✅ WebSocket real-time updates

## 📝 API Documentation

- Hospital Backend: http://localhost:8000/docs

## 🛠️ Technologies

- **Backend**: Python, FastAPI, SQLAlchemy, PyMySQL
- **Frontend**: Vue 3, Vite, React, TypeScript
- **Database**: MySQL, SQLite
- **Integration**: WebSocket, ROS, ISAPI

## 📄 License

MIT License

## 👥 Authors

Hospital Intelligent Pharmacy System Team