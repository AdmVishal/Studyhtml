#!/bin/sh
# ╔══════════════════════════════════════════════════════════════╗
# ║            StudyHub — Web Server STOP Script                ║
# ║   Gracefully kills python3 http.server  |  iSH Shell        ║
# ╚══════════════════════════════════════════════════════════════╝

# ── Configuration (must match start.sh) ──────────────────────
SERVE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SERVE_DIR/.server.pid"
LOG_FILE="$SERVE_DIR/server.log"
PORT=8080

# ── Colours ───────────────────────────────────────────────────
R='\033[0;31m'
G='\033[0;32m'
Y='\033[0;33m'
C='\033[0;36m'
B='\033[1;37m'
N='\033[0m'

# ── Helper ────────────────────────────────────────────────────
log_entry() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

print_banner() {
    printf "\n"
    printf "${R}  ╔══════════════════════════════════════╗${N}\n"
    printf "${R}  ║   ${B}StudyHub  Web Server  STOP${R}        ║${N}\n"
    printf "${R}  ╚══════════════════════════════════════╝${N}\n"
    printf "\n"
}

print_banner

# ── Locate PID ───────────────────────────────────────────────
if [ ! -f "$PID_FILE" ]; then
    printf "${Y}  ⚠  No PID file found at: $PID_FILE${N}\n"
    printf "${Y}     Attempting to find server by port...${N}\n"

    # Fallback: find by matching python3 + port number in process list
    FOUND_PID=$(ps aux 2>/dev/null | grep "http.server.*${PORT}" | grep -v grep | awk '{print $1}' | head -1)

    if [ -z "$FOUND_PID" ]; then
        # Try alternative ps format (busybox/iSH)
        FOUND_PID=$(ps 2>/dev/null | grep "http.server" | grep -v grep | awk '{print $1}' | head -1)
    fi

    if [ -z "$FOUND_PID" ]; then
        printf "${G}  ✔  No running server found on port ${PORT}.${N}\n\n"
        exit 0
    fi

    TARGET_PID="$FOUND_PID"
    printf "${C}  →  Found server process: PID ${TARGET_PID}${N}\n"
else
    TARGET_PID=$(cat "$PID_FILE" 2>/dev/null)

    if [ -z "$TARGET_PID" ]; then
        printf "${R}  ✗  PID file is empty. Removing stale file.${N}\n"
        rm -f "$PID_FILE"
        exit 1
    fi
fi

# ── Verify process is alive ───────────────────────────────────
if ! kill -0 "$TARGET_PID" 2>/dev/null; then
    printf "${Y}  ⚠  Process PID ${TARGET_PID} is not running.${N}\n"
    printf "${Y}     Cleaning up stale PID file.${N}\n"
    rm -f "$PID_FILE"
    log_entry "WARN: Stale PID $TARGET_PID — server was not running"
    printf "${G}  ✔  Done.${N}\n\n"
    exit 0
fi

# ── Graceful stop (SIGTERM) ───────────────────────────────────
printf "  ${B}Stopping PID ${N}: ${C}${TARGET_PID}${N}\n"
kill -TERM "$TARGET_PID" 2>/dev/null

# Wait up to 5 seconds for clean exit
WAIT=0
while kill -0 "$TARGET_PID" 2>/dev/null && [ $WAIT -lt 5 ]; do
    sleep 1
    WAIT=$((WAIT + 1))
    printf "  ${Y}  waiting... (${WAIT}s)${N}\n"
done

# ── Force kill if still alive ─────────────────────────────────
if kill -0 "$TARGET_PID" 2>/dev/null; then
    printf "  ${Y}  Process still alive — sending SIGKILL...${N}\n"
    kill -9 "$TARGET_PID" 2>/dev/null
    sleep 1
    if kill -0 "$TARGET_PID" 2>/dev/null; then
        printf "${R}  ✗  Could not kill PID ${TARGET_PID}. Try manually:${N}\n"
        printf "${R}     kill -9 ${TARGET_PID}${N}\n\n"
        log_entry "ERROR: Failed to kill PID $TARGET_PID"
        exit 1
    fi
fi

# ── Cleanup ───────────────────────────────────────────────────
rm -f "$PID_FILE"
log_entry "Server stopped  PID=$TARGET_PID"

{
    echo "────────────────────────────────────────────────────────"
    echo "  Server STOPPED  at $(date '+%Y-%m-%d %H:%M:%S')"
    echo "────────────────────────────────────────────────────────"
} >> "$LOG_FILE"

printf "${G}  ✔  Server stopped successfully${N}\n\n"
printf "  ${B}Stopped PID${N}: ${C}${TARGET_PID}${N}\n"
printf "  ${B}Log saved ${N}: ${C}${LOG_FILE}${N}\n"
printf "\n"
printf "  Restart with: ${C}sh start.sh${N}\n\n"
