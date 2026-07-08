#!/bin/bash

# ============================================================
# Hospital + HIS System Stop Script (Bash)
# ============================================================
# This script stops all services using relative paths
# ============================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Hospital + HIS System Stop Script${NC}"
echo -e "${CYAN}============================================================${NC}"

echo -e "${YELLOW}\n[1/1] Stopping all services...${NC}"

# Define services
declare -A SERVICES=(
    [8000]="hospital_back"
    [5173]="hospital_front"
    [3001]="HIS server"
    [3002]="HIS client"
)

# Function to stop process on a port
stop_service() {
    local port=$1
    local service_name=$2
    
    # Check if port is in use (Windows/Git Bash)
    if command -v netstat >/dev/null 2>&1; then
        if netstat -ano | grep ":$port" | grep "LISTENING" >/dev/null 2>&1; then
            echo -e "${YELLOW}  Stopping $service_name on port $port...${NC}"
            # Get all PIDs listening on this port
            PIDS=$(netstat -ano | grep ":$port" | grep "LISTENING" | awk '{print $5}' | sort -u)
            
            for PID in $PIDS; do
                if [ ! -z "$PID" ] && [ "$PID" != "0" ]; then
                    # Try to kill the process
                    taskkill //F //PID $PID 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}    [OK] Killed process PID: $PID${NC}"
                    else
                        echo -e "${RED}    [FAIL] Could not kill PID: $PID${NC}"
                    fi
                fi
            done
        else
            echo -e "${GRAY}  Port $port ($service_name) - no process running${NC}"
        fi
    else
        # Unix/Linux approach
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo -e "${YELLOW}  Stopping $service_name on port $port...${NC}"
            PIDS=$(lsof -ti:$port)
            
            for PID in $PIDS; do
                if [ ! -z "$PID" ]; then
                    kill -9 $PID 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}    [OK] Killed process PID: $PID${NC}"
                    else
                        echo -e "${RED}    [FAIL] Could not kill PID: $PID${NC}"
                    fi
                fi
            done
        else
            echo -e "${GRAY}  Port $port ($service_name) - no process running${NC}"
        fi
    fi
}

# Stop each service
for port in 8000 5173 3001 3002; do
    stop_service $port "${SERVICES[$port]}"
done

# Additional cleanup: Find and kill Python processes for hospital_back
echo -e "${YELLOW}\nCleaning up remaining processes...${NC}"

if command -v tasklist >/dev/null 2>&1; then
    # Windows approach
    PYTHON_PIDS=$(tasklist | grep "python" | awk '{print $2}')
    if [ ! -z "$PYTHON_PIDS" ]; then
        for PID in $PYTHON_PIDS; do
            # Check if it's related to hospital
            CMDLINE=$(wmic process where "ProcessId=$PID" get CommandLine 2>/dev/null | grep -i "hospital" || true)
            if [ ! -z "$CMDLINE" ]; then
                taskkill //F //PID $PID 2>/dev/null
                echo -e "${GREEN}  Killed hospital Python process (PID: $PID)${NC}"
            fi
        done
    fi
    
    # Kill node processes for hospital/HIS
    NODE_PIDS=$(tasklist | grep "node" | awk '{print $2}')
    if [ ! -z "$NODE_PIDS" ]; then
        for PID in $NODE_PIDS; do
            CMDLINE=$(wmic process where "ProcessId=$PID" get CommandLine 2>/dev/null | grep -i "hospital\|his" || true)
            if [ ! -z "$CMDLINE" ]; then
                taskkill //F //PID $PID 2>/dev/null
                echo -e "${GREEN}  Killed hospital/HIS Node process (PID: $PID)${NC}"
            fi
        done
    fi
else
    # Unix/Linux approach
    PYTHON_PIDS=$(ps aux | grep "python.*hospital" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PYTHON_PIDS" ]; then
        for PID in $PYTHON_PIDS; do
            kill -9 $PID 2>/dev/null
            echo -e "${GREEN}  Killed hospital Python process (PID: $PID)${NC}"
        done
    fi
    
    NODE_PIDS=$(ps aux | grep "node.*hospital\|node.*his" | grep -v grep | awk '{print $2}')
    if [ ! -z "$NODE_PIDS" ]; then
        for PID in $NODE_PIDS; do
            kill -9 $PID 2>/dev/null
            echo -e "${GREEN}  Killed hospital/HIS Node process (PID: $PID)${NC}"
        done
    fi
fi

# Wait a moment for processes to terminate
sleep 2

# Final verification
echo -e "${CYAN}\n============================================================${NC}"
echo -e "${CYAN}  Verification${NC}"
echo -e "${CYAN}============================================================${NC}"

all_stopped=true

for port in 8000 5173 3001 3002; do
    service_name="${SERVICES[$port]}"
    
    if command -v netstat >/dev/null 2>&1; then
        # Windows/Git Bash
        if netstat -ano | grep ":$port" | grep "LISTENING" >/dev/null 2>&1; then
            echo -e "${RED}  [FAIL] $service_name still running on port $port${NC}"
            all_stopped=false
        else
            echo -e "${GREEN}  [OK] $service_name stopped${NC}"
        fi
    else
        # Unix/Linux
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo -e "${RED}  [FAIL] $service_name still running on port $port${NC}"
            all_stopped=false
        else
            echo -e "${GREEN}  [OK] $service_name stopped${NC}"
        fi
    fi
done

echo -e "${CYAN}\n============================================================${NC}"
if $all_stopped; then
    echo -e "${GREEN}All services stopped successfully!${NC}"
else
    echo -e "${RED}Some services may still be running.${NC}"
    echo -e "${YELLOW}Try running the script again or manually kill processes.${NC}"
fi

echo -e "${CYAN}============================================================${NC}"
echo -e "${YELLOW}Script completed!${NC}"