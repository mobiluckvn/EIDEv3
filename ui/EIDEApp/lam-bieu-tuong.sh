#!/bin/bash
# Dựng `Resources/EIDE.icns` từ ảnh gốc `ui/eide_B_chip_code.png`.
#
# Chạy lại chỉ khi ảnh gốc đổi. `dong-goi.sh` KHÔNG gọi script này: dựng biểu tượng mỗi lần
# đóng gói tốn vài giây và cần `sips`, trong khi kết quả không đổi — và một bước chậm không
# đổi gì là bước người ta sẽ tìm cách bỏ.
set -euo pipefail
cd "$(dirname "$0")"

GOC="../eide_B_chip_code.png"
[ -f "$GOC" ] || { echo "Không thấy $GOC" >&2; exit 1; }

BO="$(mktemp -d)/EIDE.iconset"; mkdir -p "$BO"
for s in 16 32 64 128 256 512; do
  sips -z $s $s "$GOC" --out "$BO/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$GOC" --out "$BO/icon_${s}x${s}@2x.png" >/dev/null
done
mkdir -p Resources
iconutil -c icns "$BO" -o Resources/EIDE.icns
cp "$GOC" Resources/AppIcon.png
echo "▸ Xong: Resources/EIDE.icns + Resources/AppIcon.png"
