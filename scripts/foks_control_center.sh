#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
BACKEND_SCRIPT="$PROJECT_ROOT/scripts/start_backend.sh"
LOG_FILE="$PROJECT_ROOT/logs/app.log"

while true; do
  clear
  echo "======================="
  echo "  FoKS Control Center  "
  echo "======================="
  echo "1) Start backend (FastAPI)"
  echo "2) Open LM Studio"
  echo "3) Show last 50 log lines"
  echo "4) System snapshot (top)"
  echo "5) Exit"
  echo
  read -rp "Choose an option: " choice

  case "$choice" in
    1)
      echo "[FoKS] Starting backend..."
      /usr/bin/env bash "$BACKEND_SCRIPT"
      read -rp "Press ENTER to return to menu..." _
      ;;
    2)
      echo "[FoKS] Opening LM Studio..."
      open -a "LM Studio"
      read -rp "Press ENTER to return to menu..." _
      ;;
    3)
      echo "[FoKS] Tail logs:"
      echo
      if [ -f "$LOG_FILE" ]; then
        tail -n 50 "$LOG_FILE"
      else
        echo "No log file yet: $LOG_FILE"
      fi
      read -rp "Press ENTER to return to menu..." _
      ;;
    4)
      echo "[FoKS] System snapshot:"
      echo
      top -l 1 | head -n 20
      echo
      read -rp "Press ENTER to return to menu..." _
      ;;
    5)
      echo "Bye."
      exit 0
      ;;
    *)
      echo "Invalid option."
      sleep 1
      ;;
  esac
done

