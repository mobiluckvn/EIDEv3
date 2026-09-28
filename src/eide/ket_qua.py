# -*- coding: utf-8 -*-
"""Soi kết quả công cụ: `ok` nói về LỜI GỌI, không nói về KẾT QUẢ.

Bài học trung tâm của phiên bo STM32F469 — cùng một hình dạng xuất hiện **năm lần** ở năm
tầng khác nhau trong một phiên gỡ lỗi duy nhất:

1. `code.vendor_fetch` trả `ok` với **0/26** tệp lấy được.
2. `soi_chip` gộp lệnh openocd vào một `-c` → chạy đúng nhưng **không in kết quả `mdw`**;
   `o_nho` rỗng trong khi người gọi xin bốn địa chỉ.
3. `bsp_otm8009a_write` `return 0` vô điều kiện (firmware).
4. `g_otm8009a_init_ret = 0` vì thế chưa bao giờ có nghĩa (firmware).
5. `HAL_DSI_ShortWrite` trả `HAL_OK` vì nó chỉ **nhận gói vào hàng đợi** — 101 lệnh "thành
   công" mà không lệnh nào tới đích (firmware).

Mô-đun này bắt được loại **1 và 2**: công cụ của chính EIDE trả `ok` mà con số trong kết quả
nói rằng **không có gì chuyển động**. Ba ca còn lại nằm trong firmware của người dùng, và thứ
bắt chúng là verifier đọc bằng chứng — xem `hooks/standard.py`.

Ranh giới quan trọng nhất của mô-đun này là chỗ nó **không** kêu. `0` rất thường là câu trả
lời ĐÚNG và là tin tốt: *0 lỗi biên dịch*, *0 cảnh báo*, *0 tệp lệch*. Một bộ dò kêu ở mọi số
0 sẽ thành máy báo động giả trong một buổi chiều, và báo động giả dạy người ta bỏ qua cảnh
báo — đắt hơn hẳn việc không có nó. Nên điều kiện ở đây hẹp có chủ ý: chỉ kêu khi công cụ
được **xin một lượng cụ thể** và trả về **không gì cả**.
"""

from __future__ import annotations

from typing import Any

# Khoá mang nghĩa "đếm được bao nhiêu thứ đã chuyển động". Tên tiếng Việt vì công cụ EIDE
# đặt tên tiếng Việt; hai tên Anh cuối cho công cụ sinh sau.
_KHOA_DEM = ("so_dat", "so_tep", "so_byte", "so_dong", "so_muc", "so_mau", "so_tim_thay",
             "so_thay_doi", "so_ket_qua", "count", "n")

# Khoá mang nghĩa "những thứ lấy được". Rỗng = không lấy được gì.
_KHOA_TAP = ("o_nho", "ket_qua", "tep", "muc", "ky_hieu", "ung_vien", "tim_thay", "items")

# Khoá trong THAM SỐ nói rằng người gọi **liệt kê đích danh** một tập thứ cần lấy. Chỉ
# những khoá ấy, và chỉ khi giá trị là một DANH SÁCH.
#
# Cố ý KHÔNG có `query`/`pattern`: một phép TÌM không thấy gì **là** câu trả lời, không phải
# sự im lặng. Bản đầu có chúng, và nó báo động giả ngay ở ca kiểm đầu tiên — `fs.glob` với
# `**/*0` không khớp tệp nào bị gắn cờ "không nói gì". Đúng cái bẫy mà chú thích đầu tệp này
# vừa cảnh báo, do chính tệp này mắc.
#
# Cũng cố ý đòi DANH SÁCH: một chuỗi đơn lẻ không nói lên người gọi trông đợi bao nhiêu.
_KHOA_XIN = ("dia_chi", "tep", "files", "paths", "ten", "names", "bien", "symbols")


def khong_noi_gi(args: dict[str, Any], data: Any) -> tuple[bool, str]:
    """Kết quả `ok` này có thật sự nói được điều gì không?

    Trả `(True, lời giải thích)` khi lời gọi **xin một lượng cụ thể** mà kết quả trả về
    **không gì cả**. Mọi trường hợp khác trả `(False, "")` — kể cả khi có số 0 trong đó.
    """
    if not isinstance(data, dict):
        return False, ""

    # Người gọi có xin một lượng cụ thể không?
    xin = 0
    ten_xin = ""
    for k in _KHOA_XIN:
        v = (args or {}).get(k)
        if isinstance(v, (list, tuple)) and v:
            xin, ten_xin = len(v), k
            break
    if not xin:
        return False, ""

    def _so(v: Any) -> bool:
        """Là một con số đếm thật. `bool` bị loại: trong Python nó là con của `int`, nên
        `dat: True` sẽ được tính là "một số lớn hơn 0" và dập tắt cảnh báo — đúng thế, ở
        đúng ca `soi_chip` mà mô-đun này sinh ra để bắt."""
        return isinstance(v, int) and not isinstance(v, bool)

    # Có khoá nào nói "đã lấy được bấy nhiêu" không, và nó có bằng 0 không?
    dem_bang_0 = [k for k in _KHOA_DEM if _so((data or {}).get(k)) and data[k] == 0]
    tap_rong = [k for k in _KHOA_TAP
                if isinstance((data or {}).get(k), (list, dict, tuple))
                and len(data[k]) == 0]
    if not (dem_bang_0 or tap_rong):
        return False, ""

    # Và phải KHÔNG có tiến triển nào khác. Chỉ xét các khoá ĐẾM TIẾN TRIỂN — không xét mọi
    # số trong kết quả: `so_hong: 26` là số thứ HỎNG, nó xác nhận chứ không bác bỏ việc
    # "không có gì chuyển động". Bản đầu xét tất, nên chính con số hỏng lại dập tắt cảnh báo.
    if any(_so((data or {}).get(k)) and data[k] > 0 for k in _KHOA_DEM):
        return False, ""

    cho = ", ".join(dem_bang_0 + tap_rong)
    return True, (f"lời gọi xin {xin} thứ qua `{ten_xin}` nhưng kết quả rỗng ({cho})")


def nhac_nho(tool: str, ly_do: str) -> str:
    """Lời nhắc gửi lại cho mô hình. Nói cái nó cần làm, không mắng nó."""
    return (
        "<system-reminder>\n"
        f"`{tool}` vừa trả về **thành công** nhưng {ly_do}.\n\n"
        "`ok` trả lời câu *“lời gọi có chạy không”*. Câu bạn thực sự cần là *“việc có xong "
        "không”* — hai câu đó khác nhau, và khoảng cách giữa chúng là chỗ lỗi sống lâu nhất.\n\n"
        "Trước khi đi tiếp, trả lời được một trong hai: **vì sao rỗng là đúng ở đây**, hoặc "
        "**gọi lại cách khác**. Đừng dựa vào kết quả này như thể nó đã nói điều gì — trong "
        "một phiên gỡ lỗi bo thật, đúng chỗ này đã làm mất mười bảy lượt.\n"
        "</system-reminder>")
