#!/bin/bash
# Đóng gói EIDE.app từ tệp thực thi SwiftPM.
#
# Vì sao cần bước này: một tệp thực thi SwiftPM chạy được nhưng macOS không coi nó là
# ứng dụng — không có biểu tượng Dock, cửa sổ không nhận được tiêu điểm bàn phím, và
# menu không hiện. Gói .app chỉ là một thư mục có Info.plist, nên ta tự dựng.
#
#   ./dong-goi.sh            # bản gỡ lỗi (nhanh)
#   ./dong-goi.sh release    # bản phát hành

set -euo pipefail
cd "$(dirname "$0")"

CAU_HINH="${1:-debug}"
echo "▸ Biên dịch ($CAU_HINH)…"
swift build -c "$CAU_HINH"

BIN=".build/$CAU_HINH/EIDE"
APP="EIDE.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/EIDE"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>EIDE</string>
    <key>CFBundleDisplayName</key><string>EIDE</string>
    <key>CFBundleIdentifier</key><string>vn.mobiluck.eide</string>
    <key>CFBundleExecutable</key><string>EIDE</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>3.0.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSHumanReadableCopyright</key>
    <string>EIDE v3 — đề án ThS Kỹ thuật Điện tử, PTIT. Vũ Trí Công.</string>
</dict>
</plist>
PLIST

# Ký tạm bằng chữ ký cục bộ: đủ để chạy trên máy này, không cần tài khoản nhà phát triển.
codesign --force --deep --sign - "$APP" 2>/dev/null || true

echo "▸ Xong: $(pwd)/$APP"
echo "  Mở bằng:  open $APP"
