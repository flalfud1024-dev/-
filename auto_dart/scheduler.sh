#!/bin/bash
# macOS launchd 등록 스크립트 — 매일 오전 9시 자동 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.dart.pension.tracker"
PLIST_FILE="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

# 기존 등록 해제 (있을 경우)
if launchctl list | grep -q "$PLIST_LABEL" 2>/dev/null; then
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/.venv/bin/python3</string>
        <string>$SCRIPT_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/dart_tracker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dart_tracker_err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

launchctl load "$PLIST_FILE"
echo "✅ 스케줄러 등록 완료: 매일 오전 9시 자동 실행"
echo ""
echo "유용한 명령어:"
echo "  로그 확인:    tail -f /tmp/dart_tracker.log"
echo "  에러 확인:    tail -f /tmp/dart_tracker_err.log"
echo "  즉시 실행:    launchctl start $PLIST_LABEL"
echo "  자동 실행 해제: launchctl unload $PLIST_FILE"
