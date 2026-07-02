#!/bin/bash
# ============================================
#  一键启动 — HIS + Hospital 前后端
# ============================================

ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  ROOT_WIN="$(cygpath -w "$ROOT")"
else
  ROOT_WIN="$ROOT"
fi

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ensure_his_https_cert() {
  local cert_dir="$ROOT/his/client"
  local key_file="$cert_dir/key.pem"
  local cert_file="$cert_dir/cert.pem"

  if [[ -f "$key_file" && -f "$cert_file" ]]; then
    return 0
  fi

  echo -e "${YELLOW}正在生成 HIS 前端本地 HTTPS 证书...${NC}"
  if ! command -v openssl >/dev/null 2>&1; then
    echo -e "${RED}未找到 openssl，无法生成 HTTPS 证书。请使用 Git Bash 或安装 OpenSSL。${NC}"
    exit 1
  fi

  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$key_file" \
    -out "$cert_file" \
    -days 365 \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1 \
  || openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$key_file" \
    -out "$cert_file" \
    -days 365 \
    -subj "/CN=localhost" >/dev/null 2>&1

  if [[ ! -f "$key_file" || ! -f "$cert_file" ]]; then
    echo -e "${RED}HTTPS 证书生成失败。${NC}"
    exit 1
  fi
}

ensure_npm_deps() {
  local dir="$1"
  local name="$2"
  if [[ -d "$dir/node_modules" ]]; then
    return 0
  fi

  echo -e "${YELLOW}${name} 依赖未安装，正在执行 npm ci...${NC}"
  cd "$dir"
  npm ci || {
    echo -e "${RED}${name} 依赖安装失败。${NC}"
    exit 1
  }
}

port_in_use() {
  local port="$1"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >/dev/null 2>&1
  else
    netstat -ano 2>/dev/null | grep -E "[.:]$port[[:space:]].*LISTEN" >/dev/null 2>&1
  fi
}

port_pids() {
  local port="$1"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique" 2>/dev/null | tr -d '\r'
  else
    netstat -ano 2>/dev/null | awk -v p=":$port" '$0 ~ p && $0 ~ /LISTEN/ { print $NF }' | sort -u
  fi
}

process_info() {
  local pid="$1"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "\$p=Get-CimInstance Win32_Process -Filter 'ProcessId=$pid' -ErrorAction SilentlyContinue; if (\$p) { Write-Output (\$p.Name + ' ' + \$p.CommandLine) }" 2>/dev/null | tr -d '\r'
  else
    ps -p "$pid" -o comm=,args= 2>/dev/null
  fi
}

is_project_process() {
  local info="$1"
  [[ "$info" == *"$ROOT"* ]] && return 0
  [[ "$info" == *"$ROOT_WIN"* ]] && return 0
  [[ "$info" == *"his\\client"* ]] && return 0
  [[ "$info" == *"his\\server"* ]] && return 0
  [[ "$info" == *"hospital_front"* ]] && return 0
  [[ "$info" == *"hospital_back"* ]] && return 0
  return 1
}

stop_pid() {
  local pid="$1"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "function Stop-Tree([int]\$Id) { Get-CimInstance Win32_Process -Filter \"ParentProcessId=\$Id\" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Tree \$_.ProcessId }; Stop-Process -Id \$Id -Force -ErrorAction SilentlyContinue }; Stop-Tree $pid" >/dev/null 2>&1
  else
    kill "$pid" 2>/dev/null
  fi
}

wait_for_port() {
  local port="$1"
  local name="$2"
  local retries=20

  while (( retries > 0 )); do
    if port_in_use "$port"; then
      echo -e "${GREEN}${name} 已就绪。${NC}"
      return 0
    fi
    sleep 1
    retries=$((retries - 1))
  done

  echo -e "${RED}${name} 启动超时，请查看上方日志。${NC}"
  cleanup
}

ensure_port_free() {
  local port="$1"
  local name="$2"
  local pids
  pids="$(port_pids "$port")"

  if [[ -z "$pids" ]]; then
    return 0
  fi

  local pid
  for pid in $pids; do
    local info
    info="$(process_info "$pid")"

    if is_project_process "$info"; then
      echo -e "${YELLOW}${name} 端口 ${port} 被旧项目进程占用，正在关闭 PID ${pid}...${NC}"
      stop_pid "$pid"
    else
      echo -e "${RED}${name} 端口 ${port} 已被其他程序占用，未自动关闭。${NC}"
      echo -e "${YELLOW}PID ${pid}: ${info}${NC}"
      echo -e "${YELLOW}请先关闭该程序，或更换它占用的端口后再运行 start-all.sh。${NC}"
      exit 1
    fi
  done

  sleep 1
  if port_in_use "$port"; then
    echo -e "${RED}${name} 端口 ${port} 仍被占用，请手动检查后重试。${NC}"
    exit 1
  fi
}

find_python() {
  local candidate

  if command -v python >/dev/null 2>&1; then
    candidate="$(command -v python)"
    if [[ "$candidate" != *"WindowsApps"* ]]; then
      echo "$candidate"
      return 0
    fi
  fi

  if command -v python3 >/dev/null 2>&1; then
    candidate="$(command -v python3)"
    if [[ "$candidate" != *"WindowsApps"* ]]; then
      echo "$candidate"
      return 0
    fi
  fi

  if [[ -x "/c/Users/30355/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" ]]; then
    echo "/c/Users/30355/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
    return 0
  fi

  return 1
}

ensure_python_deps() {
  local dir="$1"
  local name="$2"
  local venv_python="$dir/venv/Scripts/python.exe"

  if [[ ! -x "$venv_python" ]]; then
    local base_python
    base_python="$(find_python)" || {
      echo -e "${RED}未找到可用 Python。请安装 Python 3，或关闭 WindowsApps Python 占位符后重试。${NC}"
      exit 1
    }
    echo -e "${YELLOW}${name} 虚拟环境不存在，正在创建 venv...${NC}"
    "$base_python" -m venv "$dir/venv" || {
      echo -e "${RED}${name} 虚拟环境创建失败。${NC}"
      exit 1
    }
  fi

  "$venv_python" -c "import fastapi, uvicorn" >/dev/null 2>&1 && return 0

  echo -e "${YELLOW}${name} Python 依赖未安装，正在执行 pip install...${NC}"
  "$venv_python" -m pip install -r "$dir/requirements.txt" || {
    echo -e "${RED}${name} Python 依赖安装失败。${NC}"
    exit 1
  }
}

cleanup() {
  echo ""
  echo -e "${YELLOW}正在停止所有服务...${NC}"
  for pid in $HIS_FE_PID $HIS_BE_PID $HOSP_FE_PID $HOSP_BE_PID; do
    [[ -n "$pid" ]] && stop_pid "$pid"
  done
  wait $HIS_FE_PID $HIS_BE_PID $HOSP_FE_PID $HOSP_BE_PID 2>/dev/null
  echo -e "${GREEN}所有服务已停止${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}    🏥 一键启动所有服务${NC}"
echo -e "${BLUE}============================================${NC}"

ensure_his_https_cert
ensure_port_free 3001 "HIS 后端"
ensure_port_free 3002 "HIS 前端"
ensure_port_free 8000 "Hospital 后端"
ensure_port_free 5173 "Hospital 前端"
ensure_port_free 5175 "Hospital 前端旧端口"
ensure_npm_deps "$ROOT/his/server" "HIS 后端"
ensure_npm_deps "$ROOT/his/client" "HIS 前端"
ensure_npm_deps "$ROOT/hospital_front" "Hospital 前端"
ensure_python_deps "$ROOT/hospital_back" "Hospital 后端"

# --- HIS 后端 :3001 ---
echo -e "${GREEN}[1/4] 启动 HIS 后端 (Express) → http://localhost:3001${NC}"
cd "$ROOT/his/server"
npm run dev &
HIS_BE_PID=$!
wait_for_port 3001 "HIS 后端"

# --- HIS 前端 :3002 ---
echo -e "${GREEN}[2/4] 启动 HIS 前端 (React)   → https://localhost:3002${NC}"
cd "$ROOT/his/client"
npm run dev -- --host 0.0.0.0 --port 3002 --strictPort &
HIS_FE_PID=$!
wait_for_port 3002 "HIS 前端"

# --- Hospital 后端 :8000 ---
echo -e "${GREEN}[3/4] 启动 Hospital 后端 (FastAPI) → http://localhost:8000${NC}"
cd "$ROOT/hospital_back"
"$ROOT/hospital_back/venv/Scripts/python.exe" app.py &
HOSP_BE_PID=$!
wait_for_port 8000 "Hospital 后端"

# --- Hospital 前端 :5173 ---
echo -e "${GREEN}[4/4] 启动 Hospital 前端 (Vue)   → http://localhost:5173${NC}"
cd "$ROOT/hospital_front"
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort &
HOSP_FE_PID=$!
wait_for_port 5173 "Hospital 前端"

echo ""
echo -e "${YELLOW}============================================${NC}"
echo -e "${GREEN}  所有服务已启动！${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "  HIS 前端       ${BLUE}https://localhost:3002${NC}"
echo -e "  HIS 后端       ${BLUE}http://localhost:3001${NC}"
echo -e "  Hospital 前端  ${BLUE}http://localhost:5173${NC}"
echo -e "  Hospital 后端  ${BLUE}http://localhost:8000${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "  按 ${RED}Ctrl+C${NC} 停止所有服务"
echo ""

wait
