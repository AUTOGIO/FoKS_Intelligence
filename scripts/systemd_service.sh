#!/usr/bin/env bash
# FoKS Intelligence - Systemd Service Setup
# Creates a systemd service file for running FoKS Intelligence

PROJECT_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
BACKEND_DIR="$PROJECT_ROOT/backend"
SERVICE_USER=$(whoami)
SERVICE_FILE="/tmp/foks-intelligence.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=FoKS Intelligence Global Interface
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv_foks/bin"
ExecStart=$BACKEND_DIR/.venv_foks/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Systemd service file created at: $SERVICE_FILE"
echo ""
echo "To install the service:"
echo "  sudo cp $SERVICE_FILE /etc/systemd/system/foks-intelligence.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable foks-intelligence"
echo "  sudo systemctl start foks-intelligence"
echo ""
echo "To check status:"
echo "  sudo systemctl status foks-intelligence"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u foks-intelligence -f"

