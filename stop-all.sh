#!/bin/bash
# ============================================================
# Hospital + HIS One-Key Stop Script (Git Bash/Linux/WSL)
# ============================================================
# This script stops all running services
# ============================================================

echo "============================================================"
echo "  Hospital + HIS Stop Script"
echo "============================================================"

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
echo -e "${YELLOW}Stopping all services...${NC}"

for port in "${PORTS[@]}"; do
    # Find process on port (Linux)
    pid=$(lsof -ti:$port 2>/dev/null || netstat -tulnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1)
    
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null
        service_name=""
        
        case $port in
            8000) service_name="hospital_back" ;;
            5175) service_name="hospital_front" ;;
            3001) service_name="HIS server" ;;
            3002) service_name="HIS client" ;;
        esac
        
        echo -e "  ${GREEN}[OK] Stopped ${service_name} (port ${port}, PID: ${pid})${NC}"
    else
        echo -e "  Port ${port} - no process running"
    fi
done

# Kill any remaining python/node processes for hospital project
echo ""
echo -e "${YELLOW}Cleaning up remaining processes...${NC}"

pkill -f "hospital_back" 2>/dev/null && echo -e "  ${GREEN}Killed hospital_back processes${NC}"
pkill -f "hospital_front" 2>/dev/null && echo -e "  ${GREEN}Killed hospital_front processes${NC}"
pkill -f "his/server" 2>/dev/null && echo -e "  ${GREEN}Killed HIS server processes${NC}"
pkill -f "his/client" 2>/dev/null && echo -e "  ${GREEN}Killed HIS client processes${NC}"

sleep 2

# Verify all services are stopped
echo ""
echo "============================================================"
echo -e "  ${CYAN}Verification${NC}"
echo "============================================================"

all_stopped=true

for port in "${PORTS[@]}"; do
    service_name=""
    
    case $port in
        8000) service_name="hospital_back" ;;
        5175) service_name="hospital_front" ;;
        3001) service_name="HIS server" ;;
        3002) service_name="HIS client" ;;
    esac
    
    # Check if port is still listening
    if netstat -tuln 2>/dev/null | grep -q ":$port " || lsof -i:$port 2>/dev/null | grep -q LISTEN; then
        echo -e "  ${RED}[FAIL] ${service_name} still running on port ${port}${NC}"
        all_stopped=false
    else
        echo -e "  ${GREEN}[OK] ${service_name} stopped${NC}"
    fi
done

echo ""
echo -e "${CYAN}Script completed!${NC}"

if [ "$all_stopped" = true ]; then
    echo -e "${GREEN}All services have been stopped successfully!${NC}"
else
    echo -e "${RED}Some services failed to stop. Manual intervention required:${NC}"
    echo "  Check processes: ps aux | grep hospital"
    echo "  Force kill: pkill -9 -f hospital"
fi