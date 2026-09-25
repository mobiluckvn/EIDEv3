#!/bin/bash
# Gõ một câu vào ô nhập của app EIDE, như người thật.
#
#   ./go_vao_app.sh "câu cần gõ"
#
# AN TOÀN: kịch bản LUÔN kiểm EIDE có đang ở trước không rồi mới gõ. Thiếu bước đó,
# phím sẽ rơi vào cửa sổ đang có tiêu điểm — nghĩa là gõ vào terminal của người dùng.
# Đã xảy ra một lần; đừng để xảy ra lần nữa.
#
# Cần quyền Accessibility (Cài đặt → Quyền riêng tư & Bảo mật → Trợ năng).
# `keystroke` và `key code` chạy được; `click at` cần quyền cao hơn và thường bị chặn,
# nên kịch bản này chỉ dùng bàn phím.

set -euo pipefail

CAU="${1:?cần một câu để gõ}"

# 1. Đưa EIDE ra trước và ĐỢI cho tới khi hệ thống xác nhận.
osascript -e 'tell application "System Events" to tell process "EIDE" to set frontmost to true' >/dev/null
for _ in $(seq 1 20); do
  TRUOC=$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>/dev/null || echo "?")
  [ "$TRUOC" = "EIDE" ] && break
  sleep 0.25
done

if [ "${TRUOC:-?}" != "EIDE" ]; then
  echo "DỪNG: EIDE không ở trước (đang là '${TRUOC:-?}'). Không gõ để tránh gõ nhầm cửa sổ." >&2
  exit 1
fi

# 2. Gõ. Escape dấu nháy kép và gạch chéo ngược cho AppleScript.
ESC=$(printf '%s' "$CAU" | sed 's/[\\"]/\\&/g')
osascript -e "tell application \"System Events\" to keystroke \"$ESC\"" >/dev/null
sleep 0.4

# 3. Enter để gửi.
osascript -e 'tell application "System Events" to key code 36' >/dev/null
echo "đã gõ: $CAU"
