# -*- coding: utf-8 -*-
"""Tác tử tự bù năng lực cho chính mình: đề xuất → người duyệt → tự viết → tự kiểm → dùng.

Vì sao chặng này tồn tại, đo được trên phiên bo STM32F469:

Tác tử có `pc = 0x08000db0` và cần biết hàm nào nằm ở đó. Nó gọi **`fs.read` 28 lần**, hết
hạn mức 40 lời gọi của lượt, rồi dừng giữa việc mà vẫn chưa chắc. `arm-none-eabi-addr2line`
trả lời cùng câu hỏi trong **40 ms**. Nó không thiếu thông minh — nó thiếu **cái miệng** để
nói *"tôi cần một công cụ"*. `tool.install` chỉ cài CLI ngoài; không có đường nào để nói
"EIDE thiếu một năng lực".

Toàn phiên: 1078 lời gọi, trong đó **580 (54 %)** là `fs.read`/`fs.grep`/`fs.glob`.

Anh Công, 28/09/2026, chọn hướng đi xa nhất trong ba hướng được trình: *"tự viết tool thật,
qua cổng"*.

## Ranh giới, và vì sao mỗi cái ở đó

Tác tử ghi mã Python chạy trong **chính tiến trình EIDE**. Đó là năng lực mạnh nhất nó có,
nên bốn hàng rào, mỗi cái chặn một kiểu hỏng khác nhau:

1. **Thẻ cổng hiện MÃ NGUỒN, không hiện lời mô tả.** `tool.install` có một dòng chú thích
   đáng chép lại ở đây: *"nếu mô hình được tự soạn lệnh shell thì thẻ cổng đang hỏi người
   dùng duyệt một thứ mà lúc soạn câu hỏi chưa ai đọc kỹ"*. Duyệt một cái tên và một lời hứa
   không phải là duyệt.
2. **Chỉ ghi được vào `.eide/cong-cu/` của DỰ ÁN.** Một thư mục riêng để nguồn gốc của mã
   luôn nhìn thấy được — ai đọc dự án sau này biết ngay tệp nào do tác tử viết. Và mã nguồn
   EIDE không bị chạm tới: bù năng lực khác với đổi năng lực. Ranh giới này không do tôi
   nghĩ ra, nó do **sandbox quyết hộ**: `fs.write` bị chặn ngoài thư mục dự án, nên bản thiết
   kế đầu (ghi vào `src/eide/tools/them/`) sẽ hỏng ngay lời gọi đầu tiên.
3. **Phải có bộ kiểm, và bộ kiểm phải XANH mới được đăng ký.** Đây là hàng rào quan trọng
   nhất. Một công cụ mới là một lời hứa; test là thứ duy nhất biến lời hứa thành sự kiện.
   Không có nó thì ta vừa cho tác tử một cách rất nhanh để tự tin vào một thứ sai.
4. **Là changeset bình thường** — vào sổ cái, hoàn tác được. Không có ngoại lệ nào cho mã
   do tác tử viết; nếu có thì đúng loại mã đáng theo dõi nhất lại là loại không ai theo dõi.
"""

from __future__ import annotations

import re
from typing import Any

# Công cụ tự viết nằm TRONG DỰ ÁN, không trong mã nguồn EIDE.
#
# Không phải để cho gọn — mà vì `fs.write` bị chặn ngoài thư mục dự án (TC070), nên tác tử
# **không ghi nổi** vào `src/eide/`. Bản thiết kế đầu đặt chúng ở đó và sẽ hỏng ngay lời gọi
# đầu tiên. Cái sandbox ấy đúng, và nó vừa quyết hộ một câu hỏi thiết kế:
#
#   · công cụ tự viết là của DỰ ÁN, không của EIDE — dự án khác, nhu cầu khác;
#   · mã nguồn EIDE không bị tác tử chạm vào, kể cả khi nó rất muốn giúp;
#   · hoàn tác một changeset là đủ để gỡ sạch, không phải dọn hai nơi.
THU_MUC = ".eide/cong-cu"
MA_DE_XUAT = "tool-propose:"

# Tên công cụ: `nhom.viec`, chữ thường. Cùng dạng với mọi công cụ sẵn có — một công cụ tên
# lạ sẽ lộ ra là "đồ tác tử tự làm" ngay trong danh sách, và đó không phải điều ta muốn phân
# biệt; thứ đáng phân biệt là *nó có test không*.
_TEN = re.compile(r"^[a-z][a-z0-9_]{1,20}\.[a-z][a-z0-9_]{1,30}$")

# Phần `vì sao` phải mang SỐ ĐO, không mang cảm giác. "Tôi thấy hơi chậm" không đủ để ai
# quyết; "tôi gọi fs.read 28 lần rồi hết hạn mức" thì đủ.
_CO_SO = re.compile(r"\d")

# Nhóm mà công cụ mới được phép thuộc về. Lấy đúng các nhóm đang có, để công cụ tự viết
# không dựng thêm một ngăn riêng trong giao diện.
NHOM_HOP_LE = ("Tệp & lệnh", "Mã nguồn", "Tri thức", "Mạch thật", "Điều phối", "Store",
               "Thiết kế", "Kiểm chứng")


def kiem_de_xuat(ten: str, viec: str, vi_sao: str, test: str,
                 co_cong_cu) -> list[str]:
    """Những chỗ đề xuất chưa dùng được. Rỗng = trình cho người dùng được."""
    loi: list[str] = []
    if not _TEN.match(ten or ""):
        loi.append(f"tên `{ten}` không đúng dạng `nhom.viec` (chữ thường, không dấu).")
    elif co_cong_cu(ten):
        loi.append(f"đã có công cụ tên `{ten}` rồi — đọc lại nó trước khi viết cái mới.")
    if len((viec or "").strip()) < 20:
        loi.append("`viec` quá ngắn: nói rõ công cụ này trả lời câu hỏi nào.")
    if len((vi_sao or "").strip()) < 30 or not _CO_SO.search(vi_sao or ""):
        loi.append("`vi_sao` phải kèm SỐ ĐO — bao nhiêu lời gọi đã tốn, bao lâu, bao nhiêu "
                   "lần thử. Một cảm giác (“hơi chậm”) không đủ để ai quyết.")
    if len((test or "").strip()) < 20:
        loi.append("`test` chưa nói sẽ kiểm những ca nào. Một công cụ mới là một lời hứa; "
                   "test là thứ duy nhất biến lời hứa thành sự kiện.")
    return loi


def duong_ma(ten: str) -> str:
    """Tệp mã của một công cụ tự viết. Chỉ một chỗ, để nguồn gốc luôn nhìn thấy được."""
    return f"{THU_MUC}/{ten.replace('.', '_')}.py"


def duong_test(ten: str) -> str:
    """Bộ kiểm nằm CẠNH mã, trong cùng thư mục.

    Không để ở `tests/` của dự án: thư mục ấy là của người dùng, và trộn bộ kiểm do tác tử
    sinh vào đó sẽ làm `pytest` của họ đỏ vì một công cụ họ chưa từng nghe tới.
    """
    return f"{THU_MUC}/test_{ten.replace('.', '_')}.py"


def khuon_ma(ten: str, nhom: str, viec: str) -> str:
    """Khung tệp để tác tử điền vào — nó phải viết phần thân, không phải phần thủ tục."""
    ham = ten.replace(".", "_")
    return f'''# -*- coding: utf-8 -*-
"""`{ten}` — công cụ do TÁC TỬ tự viết.

{viec}

Tệp này nằm trong `{THU_MUC}/` của dự án vì nó do TÁC TỬ viết, không phải người. Nguồn gốc
ấy phải nhìn thấy được khi ai đó đọc dự án về sau.
"""

from __future__ import annotations

from typing import Any


def dang_ky(r) -> None:
    @r.tool("{ten}", "{nhom}",
            "{viec}",
            {{"type": "object", "properties": {{}}, "required": []}},
            risk="R1", core=False, keywords=[])
    def {ham}(ctx: Any):
        # TODO: phần thân.
        #
        # Nhớ ba điều đã trả giá trong phiên bo STM32F469:
        #   · trả về SỐ ĐO, đừng chỉ trả `ok` — `ok` nói về lời gọi, không nói về kết quả;
        #   · "không đo được" phải khác "đo được và bằng 0";
        #   · mọi hằng số phần cứng tra từ header của hãng, không dựng lại từ trí nhớ.
        raise NotImplementedError
'''


def khuon_test(ten: str, test: str) -> str:
    ham = ten.replace(".", "_")
    return f'''# -*- coding: utf-8 -*-
"""Bộ kiểm cho `{ten}` — công cụ do tác tử tự viết.

Bộ này phải XANH thì `{ten}` mới được đăng ký. Một công cụ mới là một lời hứa; test là thứ
duy nhất biến lời hứa thành sự kiện.

Các ca tác tử đã cam kết sẽ kiểm:
{test}
"""

from __future__ import annotations


def test_{ham}_chua_viet():
    raise AssertionError("chưa viết ca kiểm nào cho {ten}")
'''
