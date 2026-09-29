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

# Biểu tượng. `Resources/EIDE.icns` dựng sẵn từ `ui/eide_B_chip_code.png` bằng `iconutil`
# (xem `lam-bieu-tuong.sh`) — dựng ở đây thì mỗi lần đóng gói lại tốn vài giây và cần
# `sips`, mà kết quả không đổi. `AppIcon.png` là cùng ảnh ở dạng PNG, cho bảng Giới thiệu
# đọc lại: `NSApp.applicationIconImage` trả biểu tượng MẶC ĐỊNH của macOS khi chạy bằng
# `swift run`, và hiện nó ra sẽ trông như ứng dụng chưa có biểu tượng.
cp Resources/EIDE.icns Resources/AppIcon.png "$APP/Contents/Resources/"

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
    <key>CFBundleIconFile</key><string>EIDE</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSHumanReadableCopyright</key>
    <string>EIDE v3 — đề tài “Phát triển phần mềm nhúng có ứng dụng trí tuệ nhân tạo (AI)”, luận văn Thạc sĩ Kỹ thuật Điện tử, Học viện Công nghệ Bưu chính Viễn thông. Học viên: Vũ Trí Công. Giảng viên hướng dẫn: TS. Nguyễn Trung Hiếu.</string>
</dict>
</plist>
PLIST

# Ký tạm bằng chữ ký cục bộ: đủ để chạy trên máy này, không cần tài khoản nhà phát triển.
codesign --force --deep --sign - "$APP" 2>/dev/null || true

echo "▸ Xong: $(pwd)/$APP"
echo "  Mở bằng:  open $APP"
