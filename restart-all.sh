#!/bin/bash
# ============================================================
# Hospital + HIS One-Key Restart Script (Git Bash/Linux/WSL)
# ============================================================
# This script stops and restarts all services in background
# ============================================================

echo "============================================================"
echo "  Hospital + HIS Restart Script"
echo "============================================================"

# Get script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use relative paths from script directory
HOSPITAL_BACK_PATH="${SCRIPT_DIR}/hospital/hospital_back"
HOSPITAL_FRONT_PATH="${SCRIPT_DIR}/hospital/hospital_front"
HIS_SERVER_PATH="${SCRIPT_DIR}/hospital/his/server"
HIS_CLIENT_PATH="${SCRIPT_DIR}/hospital/his/client"

# Ports to check
PORTS=(8000 5175 3001 3002)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop all services
echo ""
echo -e "${YELLOW}[1/2] Stopping all services...${NC}"

for port in "${PORTS[@]}"; do
    # Find process on port (Linux)
    pid=$(lsof -ti:$port 2>/dev/null || netstat -tulnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1)
    
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null
        echo -e "  ${GREEN}Stopped port ${port} process (PID: ${pid})${NC}"
    else
        echo -e "  Port ${port} - no process running"
    fi
done

# Kill any remaining python/node processes
pkill -f "hospital_back" 2>/dev/null
pkill -f "hospital_front" 2>/dev/null
pkill -f "his/server" 2>/dev/null
pkill -f "his/client" 2>/dev/null

sleep 2
echo -e "${GREEN}All services stopped${NC}"

# Start all services
echo ""
echo -e "${YELLOW}[2/2] Starting all services...${NC}"

# 1. hospital_back
echo -e "  ${CYAN}[1/4] Starting hospital_back...${NC}"
cd "$HOSPITAL_BACK_PATH"
nohup python app.py > /tmp/hospital_back.log 2>&1 &
echo -e "    ${GREEN}hospital_back starting (http://localhost:8000)${NC}"

# 2. hospital_front
echo -e "  ${CYAN}[2/4] Starting hospital_front...${NC}"
cd "$HOSPITAL_FRONT_PATH"
nohup npm run dev > /tmp/hospital_front.log 2>&1 &
echo -e "    ${GREEN}hospital_front starting (http://localhost:5175)${NC}"

# 3. HIS server
echo -e "  ${CYAN}[3/4] Starting HIS server...${NC}"
cd "$HIS_SERVER_PATH"
nohup npm run dev > /tmp/his_server.log 2>&1 &
echo -e "    ${GREEN}HIS server starting (http://localhost:3001)${NC}"

# 4. HIS client
echo -e "  ${CYAN}[4/4] Starting HIS client...${NC}"
cd "$HIS_CLIENT_PATH"
nohup npm run dev > /tmp/his_client.log 2>&1 &
echo -e "    ${GREEN}HIS client starting (https://localhost:3002)${NC}"

# Wait for services to start
echo ""
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 15

# Check service status
echo ""
echo "============================================================"
echo -e "  ${CYAN}Service Status${NC}"
echo "============================================================"

all_running=true

for port in "${PORTS[@]}"; do
    service_name=""
    url=""
    
    case $port in
        8000) service_name="hospital_back"; url="http://localhost:8000" ;;
        5175) service_name="hospital_front"; url="http://localhost:5175" ;;
        3001) service_name="HIS server"; url="http://localhost:3001" ;;
        3002) service_name="HIS client"; url="https://localhost:3002" ;;
    esac
    
    # Check if port is listening
    if netstat -tuln 2>/dev/null | grep -q ":$port " || lsof -i:$port 2>/dev/null | grep -q LISTEN; then
        echo -e "  ${GREEN}[OK] ${service_name} running - ${url}${NC}"
    else
        echo -e "  ${RED}[FAIL] ${service_name} not running${NC}"
        all_running=false
    fi
done

echo ""
echo "============================================================"
echo -e "  ${CYAN}Quick Access${NC}"
echo "============================================================"
echo "  Dashboard: http://localhost:5175"
echo "  HIS System: https://localhost:3002"
echo "  API Docs: http://localhost:8000/docs"

echo ""
echo "============================================================"
echo -e "  ${CYAN}HIS Test Accounts${NC}"
echo "============================================================"
echo "  Doctor: doctor1 / 123456"
echo "  Pharmacist: pharmacist1 / 123456"
echo "  Admin: admin / 123456"

echo ""
echo -e "${CYAN}Script completed!${NC}"

if [ "$all_running" = true ]; then
    echo -e "${GREEN}All services are running successfully!${NC}"
else
    echo -e "${YELLOW}Some services failed to start. Check logs:${NC}"
    echo "  tail -f /tmp/hospital_back.log"
    echo "  tail -f /tmp/hospital_front.log"
    echo "  tail -f /tmp/his_server.log"
    echo "  tail -f /tmp/his_client.log"
fi