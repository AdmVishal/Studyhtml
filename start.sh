#!/bin/sh
# ╔══════════════════════════════════════════════════════════════╗
# ║            StudyHub — Web Server START Script               ║
# ║   python3 -m http.server  |  iSH Shell  |  iOS             ║
# ╚══════════════════════════════════════════════════════════════╝

# ── Configuration ────────────────────────────────────────────
PORT=8080
HOST="0.0.0.0"
SERVE_DIR="$(cd "$(dirname "$0")" && pwd)"   # directory of this script
PID_FILE="$SERVE_DIR/.server.pid"
LOG_FILE="$SERVE_DIR/server.log"
MAX_LOG_KB=512                               # rotate log if > 512 KB

# ── Colours (safe for ash/busybox) ───────────────────────────
R='\033[0;31m'  # red
G='\033[0;32m'  # green
Y='\033[0;33m'  # yellow
C='\033[0;36m'  # cyan
B='\033[1;37m'  # bold white
N='\033[0m'     # reset

# ── Helper: timestamped log entry ────────────────────────────
log_entry() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# ── Helper: print banner ─────────────────────────────────────
print_banner() {
    printf "\n"
    printf "${C}  ╔══════════════════════════════════════╗${N}\n"
    printf "${C}  ║   ${B}StudyHub  Web Server${C}              ║${N}\n"
    printf "${C}  ╚══════════════════════════════════════╝${N}\n"
    printf "\n"
}

# ── Log rotation: keep file under MAX_LOG_KB ─────────────────
rotate_log_if_needed() {
    if [ -f "$LOG_FILE" ]; then
        size_kb=$(wc -c < "$LOG_FILE" 2>/dev/null | awk '{print int($1/1024)}')
        if [ "${size_kb:-0}" -ge "$MAX_LOG_KB" ]; then
            mv "$LOG_FILE" "${LOG_FILE}.old"
            printf "${Y}  ⟳  Log rotated → server.log.old${N}\n"
        fi
    fi
}

# ── Check if already running ──────────────────────────────────
check_running() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
            printf "${Y}  ⚠  Server already running  (PID ${OLD_PID})${N}\n"
            printf "${Y}     URL  →  http://localhost:${PORT}${N}\n"
            printf "${Y}     Stop →  sh stop.sh${N}\n\n"
            exit 0
        else
            # Stale PID file — remove it
            rm -f "$PID_FILE"
        fi
    fi
}

# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════

print_banner
rotate_log_if_needed
check_running

# Write startup header to log
{
    echo "════════════════════════════════════════════════════════"
    echo "  StudyHub Server START"
    echo "  Date     : $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Port     : $PORT"
    echo "  Dir      : $SERVE_DIR"
    echo "  PID file : $PID_FILE"
    echo "════════════════════════════════════════════════════════"
} >> "$LOG_FILE"

# Start server — redirect stdout+stderr to log
cd "$SERVE_DIR" || { printf "${R}  ✗  Cannot cd to $SERVE_DIR${N}\n"; exit 1; }

python3 -m http.server "$PORT" --bind "$HOST" \
    >> "$LOG_FILE" 2>&1 &

SERVER_PID=$!

# Brief pause then verify process launched
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    printf "${R}  ✗  Server failed to start. Check log:${N}\n"
    printf "${R}     tail server.log${N}\n\n"
    log_entry "ERROR: Server failed to start (PID $SERVER_PID)"
    exit 1
fi

# Save PID
echo "$SERVER_PID" > "$PID_FILE"
log_entry "Server started  PID=$SERVER_PID  PORT=$PORT  DIR=$SERVE_DIR"

# ── Success output ────────────────────────────────────────────
printf "${G}  ✔  Server started successfully${N}\n\n"
printf "  ${B}PID   ${N}: ${C}${SERVER_PID}${N}\n"
printf "  ${B}URL   ${N}: ${C}http://localhost:${PORT}${N}\n"
printf "  ${B}Dir   ${N}: ${C}${SERVE_DIR}${N}\n"
printf "  ${B}Log   ${N}: ${C}${LOG_FILE}${N}\n"
printf "  ${B}PID f ${N}: ${C}${PID_FILE}${N}\n"
printf "\n"
printf "  ${Y}Useful commands:${N}\n"
printf "    sh stop.sh            ${Y}# stop the server${N}\n"
printf "    sh status.sh          ${Y}# check status + logs${N}\n"
printf "    tail -f server.log    ${Y}# live log stream${N}\n"
printf "\n"
