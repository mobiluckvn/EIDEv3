# Sở cứ phiên làm việc trên bo STM32F469I-DISCO

Thư mục này là **bằng chứng**, không phải bản tường thuật. Mọi thứ ở đây do máy ghi trong lúc
một phiên EIDE chạy thật trên bo cắm vào máy anh Công, ngày 27–28/09/2026.

| Tệp | Là gì | Dùng để |
|---|---|---|
| `NHAT-KY.md` | Nhật ký người đọc: từng câu người dùng gõ, từng công cụ tác tử gọi (kèm ok/lỗi), từng kết luận đạt/không đạt | đọc, và trích vào chương thực nghiệm |
| `buoc.jsonl` | Cùng nội dung ở dạng máy đọc | so **bằng mã** giữa hai lần chạy |
| `anh/NN-*.png` | Ảnh cửa sổ EIDE ở từng mốc — do **chính ứng dụng tự render**, không dùng `screencapture` | sở cứ hình ảnh |
| `doi-chieu.md` | Đối chiếu firmware ↔ tài liệu, sinh bởi `tools/doi_chieu_stm32.py` | kiểm chân trong mã có khớp tài liệu không |

## Cách chạy lại

```bash
.venv/bin/python tools/phien_stm32.py              # từ đầu, xoá dự án cũ
.venv/bin/python tools/phien_stm32.py --giu-du-an --buoc 5-10
.venv/bin/python tools/doi_chieu_stm32.py          # sinh lại doi-chieu.md
```

Dự án nằm ở `du-lieu/stm32f469-disco/`.

## Ba điều cần biết khi đọc sở cứ này

**1. Không có đáp án cài sẵn.** Bộ đối chiếu không biết LED1 nối chân nào; nó đọc tài liệu
*trong kho của dự án* rồi so với mã nguồn. Nếu tác tử nạp nhầm tài liệu thì bảng đối chiếu
cũng sai theo — và đó là đúng, vì câu hỏi nó trả lời là *"firmware có khớp với nguồn mà dự án
đang dựa vào không"*, chứ không phải *"firmware có đúng với thứ người viết bộ đo nhớ được
không"*.

**2. Một ô ✅ chỉ có nghĩa khi biết cơ chế nào làm nó xanh.** Các phép kiểm trong
`kich_ban_stm32.py` đều đọc **hiện vật trên đĩa hoặc trong kho**, không đọc lời tác tử kể.
Ví dụ: "biên dịch đạt" đọc từ `store.get("build:firmware")` và đòi có tệp ảnh thật; "nạp đạt"
đòi hash, số byte, và đích.

**3. Phần duy nhất không đo được bằng mã là hành vi của đèn.** Kịch bản cố ý **không tự trả
lời** câu đó — nó ghi ra một câu hỏi cho anh Công. Bo này không có cổng COM nối sẵn vào USART
(header BSP của ST không định nghĩa cổng COM nào), nên `target.log` im lặng là kết quả
**đúng**, không phải dấu hiệu firmware sai.

## Ứng dụng đang nằm trên chip

Bài kiểm bằng tay, hai hành vi khác nhau rõ rệt nên nhìn là biết đúng hay sai:

| Thao tác | Phải thấy |
|---|---|
| Không bấm gì | Bốn đèn sáng **lần lượt vòng quanh**: LED1 xanh lá (PG6) → LED2 cam (PD4) → LED3 đỏ (PD5) → LED4 xanh dương (PK3) |
| Giữ nút USER (nút xanh) | Cả bốn đèn **chớp nháy đồng loạt, nhanh hơn hẳn**; thả ra thì quay về chạy vòng |

Anh Công đã bấm thử và xác nhận đúng (28/09/2026) — mục đầu tiên của dự án đạt ở **tầng
NGƯỜI**. Mọi chân trong firmware đều có Fact kèm trích dẫn (5/5), và mức tích cực của đèn
(sáng ở mức THẤP) đọc từ `BSP_LED_On` trong tệp `.c` của ST, không phải đoán.

## Môi trường đã đo được (không phải giả định)

- Bo: ổ nạp `/Volumes/DIS_F469NI` (ST-LINK kiểu mass-storage, `DETAILS.TXT` Version 0221),
  cổng COM ảo `/dev/cu.usbmodem*`.
- Chuỗi công cụ: `arm-none-eabi-gcc` 16.2.0 (Homebrew, **không kèm newlib**),
  `arm-none-eabi-objcopy`, `arm-none-eabi-size`.
- Mạng: `www.st.com` **bị chặn ở tầng mạng** (kết nối reset ~0,6 s, kể cả khi ép đúng IP
  Akamai và kể cả ngoài sandbox); `github.com` và `ti.com` vào bình thường. Mọi instance
  SearXNG công khai thử được đều chặn bằng anti-bot.
- Vì thế `doc.search_web` tìm trong **tổ chức GitHub của chính hãng**
  (`STMicroelectronics/32f469idiscovery-bsp`) — tài liệu hãng phát hành, nhưng là **mã nguồn**
  chứ không phải PDF. Tầng tin cậy vẫn là `nha_san_xuat`; điều đó được ghi trong hiện vật
  `doc` và hiện trên tab Tài liệu.
