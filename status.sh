#!/bin/sh
# ╔══════════════════════════════════════════════════════════════╗
# ║            StudyHub — Web Server STATUS Script              ║
# ║   Shows server health, uptime, and recent log entries       ║
# ╚══════════════════════════════════════════════════════════════╝

# ── Configuration (must match start.sh) ──────────────────────
SERVE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SERVE_DIR/.server.pid"
LOG_FILE="$SERVE_DIR/server.log"
PORT=8080
LOG_LINES=20   # how many recent log lines to show

# ── Colours ───────────────────────────────────────────────────
R='\033[0;31m'
G='\033[0;32m'
Y='\033[0;33m'
C='\033[0;36m'
B='\033[1;37m'
D='\033[0;90m'
N='\033[0m'

# ── Banner ─────────────────────────────────────────────────────
printf "\n"
printf "${C}  ╔══════════════════════════════════════╗${N}\n"
printf "${C}  ║   ${B}StudyHub  Server  STATUS${C}          ║${N}\n"
printf "${C}  ╚══════════════════════════════════════╝${N}\n"
printf "\n"

# ── Server state ───────────────────────────────────────────────
RUNNING=0
TARGET_PID=""

if [ -f "$PID_FILE" ]; then
    TARGET_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$TARGET_PID" ] && kill -0 "$TARGET_PID" 2>/dev/null; then
        RUNNING=1
    fi
fi

# ── Status block ──────────────────────────────────────────────
printf "  ${B}──── Server ────────────────────────────${N}\n"
if [ "$RUNNING" -eq 1 ]; then
    printf "  Status  : ${G}● RUNNING${N}\n"
    printf "  PID     : ${C}${TARGET_PID}${N}\n"
    printf "  Port    : ${C}${PORT}${N}\n"
    printf "  URL     : ${C}http://localhost:${PORT}${N}\n"
    printf "  Dir     : ${C}${SERVE_DIR}${N}\n"
else
    printf "  Status  : ${R}● STOPPED${N}\n"
    if [ -n "$TARGET_PID" ]; then
        printf "  ${Y}  (stale PID file: ${TARGET_PID} — process not found)${N}\n"
    fi
    printf "  Start   : ${Y}sh start.sh${N}\n"
fi

# ── Log file info ─────────────────────────────────────────────
printf "\n  ${B}──── Log File ──────────────────────────${N}\n"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null | awk '{print int($1/1024)}')
    LOG_LINES_TOTAL=$(wc -l < "$LOG_FILE" 2>/dev/null | tr -d ' ')
    printf "  File    : ${C}${LOG_FILE}${N}\n"
    printf "  Size    : ${C}${LOG_SIZE} KB${N}\n"
    printf "  Lines   : ${C}${LOG_LINES_TOTAL}${N}\n"

    # Check for old rotated log
    if [ -f "${LOG_FILE}.old" ]; then
        OLD_SIZE=$(wc -c < "${LOG_FILE}.old" 2>/dev/null | awk '{print int($1/1024)}')
        printf "  Rotated : ${D}server.log.old  (${OLD_SIZE} KB)${N}\n"
    fi
else
    printf "  ${Y}  No log file found yet. Start server first.${N}\n"
fi

# ── PID file ──────────────────────────────────────────────────
printf "\n  ${B}──── Files ─────────────────────────────${N}\n"
if [ -f "$PID_FILE" ]; then
    printf "  PID file: ${C}${PID_FILE}${N}  ${D}($(cat "$PID_FILE"))${N}\n"
else
    printf "  PID file: ${D}not present${N}\n"
fi

# ── Recent log entries ────────────────────────────────────────
if [ -f "$LOG_FILE" ]; then
    printf "\n  ${B}──── Last ${LOG_LINES} Log Entries ─────────────${N}\n\n"
    tail -n "$LOG_LINES" "$LOG_FILE" | while IFS= read -r line; do
        # Colour code by content
        case "$line" in
            *" 200 "*)  printf "  ${G}${line}${N}\n" ;;
            *" 404 "*)  printf "  ${Y}${line}${N}\n" ;;
            *" 500 "*)  printf "  ${R}${line}${N}\n" ;;
            *ERROR*)    printf "  ${R}${line}${N}\n" ;;
            *WARN*)     printf "  ${Y}${line}${N}\n" ;;
            *started*)  printf "  ${G}${line}${N}\n" ;;
            *stopped*)  printf "  ${R}${line}${N}\n" ;;
            *"═"*|*"─"*) printf "  ${D}${line}${N}\n" ;;
            *)          printf "  ${D}${line}${N}\n" ;;
        esac
    done
fi

# ── Quick commands reminder ───────────────────────────────────
printf "\n  ${B}──── Commands ──────────────────────────${N}\n"
printf "  ${C}sh start.sh${N}          ${D}# start server${N}\n"
printf "  ${C}sh stop.sh${N}           ${D}# stop server${N}\n"
printf "  ${C}sh status.sh${N}         ${D}# this screen${N}\n"
printf "  ${C}tail -f server.log${N}   ${D}# live log stream${N}\n"
printf "  ${C}cat server.log${N}       ${D}# full log${N}\n"
printf "\n"
