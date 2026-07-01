#!/bin/bash
# ============================================
#  一键启动 — HIS + Hospital 前后端
# ============================================

ROOT="$(cd "$(dirname "$0")" && pwd)"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
  echo ""
  echo -e "${YELLOW}正在停止所有服务...${NC}"
  kill $HIS_FE_PID $HIS_BE_PID $HOSP_FE_PID $HOSP_BE_PID 2>/dev/null
  wait $HIS_FE_PID $HIS_BE_PID $HOSP_FE_PID $HOSP_BE_PID 2>/dev/null
  echo -e "${GREEN}所有服务已停止${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}    🏥 一键启动所有服务${NC}"
echo -e "${BLUE}============================================${NC}"

# --- HIS 后端 :3001 ---
echo -e "${GREEN}[1/4] 启动 HIS 后端 (Express) → http://localhost:3001${NC}"
cd "$ROOT/his/server"
npm run dev &
HIS_BE_PID=$!

# --- HIS 前端 :3000 ---
echo -e "${GREEN}[2/4] 启动 HIS 前端 (React)   → https://localhost:3000${NC}"
cd "$ROOT/his/client"
npm run dev &
HIS_FE_PID=$!

# --- Hospital 后端 :8000 ---
echo -e "${GREEN}[3/4] 启动 Hospital 后端 (FastAPI) → http://localhost:8000${NC}"
cd "$ROOT/hospital_back"
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
python app.py &
HOSP_BE_PID=$!

# --- Hospital 前端 :5173 ---
echo -e "${GREEN}[4/4] 启动 Hospital 前端 (Vue)   → http://localhost:5173${NC}"
cd "$ROOT/hospital_front"
npm run dev &
HOSP_FE_PID=$!

echo ""
echo -e "${YELLOW}============================================${NC}"
echo -e "${GREEN}  所有服务已启动！${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "  HIS 前端       ${BLUE}https://localhost:3000${NC}"
echo -e "  HIS 后端       ${BLUE}http://localhost:3001${NC}"
echo -e "  Hospital 前端  ${BLUE}http://localhost:5173${NC}"
echo -e "  Hospital 后端  ${BLUE}http://localhost:8000${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "  按 ${RED}Ctrl+C${NC} 停止所有服务"
echo ""

wait
