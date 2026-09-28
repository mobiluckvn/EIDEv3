#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kịch bản phiên FreeRTOS trên STM32F469I-DISCO — dự án MỚI, cùng một bo.

Khác phiên trước ở hai chỗ, và cả hai đều là chỗ đáng đo:

1. **Đầu vào là thông tin bo đã biết**, không phải một cái bo trống. Anh Công đưa lại đúng
   những gì phiên trước đã đo được, nên tác tử không phải dò lại từ đầu — và ta xem nó có
   dùng được thông tin ấy không, hay vẫn đi cày lại.

2. **Ba năng lực mới lần đầu chạy trên việc thật**: plan mode (§B5), verifier kiểm lời tuyên
   "đạt" của chính tác tử chính, và `tool.propose` để nó tự bù công cụ còn thiếu. Kịch bản
   này KHÔNG bảo nó dùng cái nào — nó chỉ giao việc, rồi đo xem chúng có nổ đúng lúc không.
   Bảo trước thì phép đo mất nghĩa: ta sẽ chỉ biết tác tử làm theo lời, không biết cơ chế có
   tự tìm được đường tới nó hay không.

Việc: tìm bản FreeRTOS **tương thích** với chip này, đưa vào dự án, và viết ứng dụng nhiều
tác vụ chạy được trên phần cứng thật.
"""

from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any

# Thông tin bo, đo được trong phiên trước (DEV-278 → DEV-279). Đưa lại nguyên văn cho tác
# tử làm đầu vào — đây là "thông tin về mạch hiện tại" mà anh Công nói tới.
BO = """\
Bo: **STM32F469I-DISCO** (32F469IDISCOVERY), chip **STM32F469NIH6** — Cortex-M4F, \
2 MB Flash, 324 KB RAM, BGA216.

Những gì đã ĐO được trên chính bo này ở dự án trước (không phải nhớ, mà đọc từ silicon):

- ST-LINK/V2-1 chạy firmware **mass-storage** → ổ `/Volumes/DIS_F469NI`; nạp được bằng cách \
sao tệp `.bin` vào đó. Máy cũng đã có `openocd`, `st-flash`, `st-info`.
- `st-info --probe` đọc từ chip: `dev-type: STM32F46x_F47x`, flash 2 097 152, sram 262 144.
- Cổng `/dev/cu.usbmodem1103` là VCP của ST-LINK nhưng **không nối vào USART nào** — BSP \
không khai COM port. Đừng trông chờ log qua đó.
- **4 LED tích cực THẤP**: LED1 = PG6, LED2 = PD4, LED3 = PD5, LED4 = PK3. \
Nút WAKEUP = PA0, tích cực CAO.
- Màn LCD 800×480 qua LTDC + MIPI DSI + panel **OTM8009A**, framebuffer ở SDRAM ngoài tại \
`0xC0000000`, định dạng ARGB8888.
- Chuỗi công cụ: `arm-none-eabi-gcc` 16.2.0 của Homebrew, **không có newlib** → phải link \
`-nostdlib`. Kiến trúc `armv7e-m`, có FPU.
- `www.st.com` bị chặn ở tầng mạng trên máy này (kết nối reset ~0,6 s). Mã của hãng lấy từ \
**GitHub**; các repo của ST dùng submodule nên HAL, CMSIS và BSP nằm ở kho riêng, và nhánh \
mặc định mỗi kho một khác.
"""


def chay(nk: Any, du_an: pathlib.Path, *, chi_buoc: str = "") -> int:
    from phien_robot import ctx_cua_bo_do, hoi, mo_app

    def lam(n: int) -> bool:
        if not chi_buoc:
            return True
        if "-" in chi_buoc:
            a, b = chi_buoc.split("-")
            return int(a) <= n <= int(b)
        return n == int(chi_buoc)

    # ------------------------------------------------------------------ 1. dự án mới
    nk.buoc("Tạo dự án MỚI cho FreeRTOS trên cùng bo STM32F469I-DISCO")
    (du_an / "README.md").write_text(
        "# FreeRTOS trên STM32F469I-DISCO\n\n"
        "Dự án thứ hai trên cùng một bo. Dự án đầu (`du-lieu/stm32f469-disco`) để nguyên,\n"
        "không đụng tới — nó là hiện vật của chặng G7.\n\n"
        "Việc ở đây: tìm bản FreeRTOS tương thích với STM32F469NIH6, đưa vào dự án, và viết\n"
        "ứng dụng nhiều tác vụ chạy được trên phần cứng thật.\n", "utf-8")
    g = mo_app(du_an)
    ctx = ctx_cua_bo_do(du_an)
    nk.ghi("Thư mục dự án", str(du_an))
    nk.anh(g, "mo-du-an-moi")

    # ------------------------------------------------------------------ 2. đưa thông tin bo
    if lam(2):
        nk.buoc("Đưa thông tin bo đã đo được ở dự án trước làm đầu vào")
        loi, cc = hoi(g, nk, du_an,
                      "Mình mở một dự án MỚI, vẫn trên cái bo cũ. Dự án trước mình để nguyên, "
                      "đừng đụng vào nó.\n\n"
                      "Đây là tất cả những gì đã **đo được** trên chính bo này ở dự án trước "
                      "— không phải trí nhớ, mà đọc từ silicon và từ tài liệu của ST:\n\n"
                      + BO + "\n"
                      "Ghi những gì bạn thấy đáng giữ vào bộ nhớ dài hạn của dự án, rồi nói "
                      "cho mình biết bạn hiểu bo này thế nào — nhất là chỗ nào trong đống "
                      "trên bạn **sẽ phải tự kiểm lại** thay vì tin luôn.",
                      giay=1800)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_ghi_bo_nho(nk, du_an)
        nk.anh(g, "thong-tin-bo")

    # ------------------------------------------------------------------ 3. giao việc lớn
    if lam(3):
        nk.buoc("Giao việc: tìm FreeRTOS TƯƠNG THÍCH và viết ứng dụng chạy trên bo")
        loi, cc = hoi(g, nk, du_an,
                      "Việc của dự án này:\n\n"
                      "1. Tìm bản **FreeRTOS tương thích** với chip STM32F469NIH6 và chuỗi "
                      "công cụ đang có. “Tương thích” là thứ bạn phải **chứng minh**, không "
                      "phải thứ bạn tuyên bố — nói rõ bạn dựa vào đâu.\n"
                      "2. Đưa nó vào dự án.\n"
                      "3. Viết một ứng dụng **nhiều tác vụ** chạy được trên bo, mà anh Công "
                      "nhìn là thấy nó đang chạy thật — không phải một vòng lặp giả vờ.\n"
                      "4. Biên dịch, nạp, và chứng minh nó đang chạy.\n\n"
                      "Việc này lớn. Bạn tự quyết cách làm.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_plan_mode(nk, ctx, cc)
        nk.anh(g, "giao-viec-lon")

    # ------------------------------------------------------------------ 4. trả lời + sửa bug
    #
    # Tác tử hỏi bốn con số để vượt constant-guard — đúng cơ chế, và câu hỏi của nó có kèm
    # "vì sao hỏi" cho từng số. Anh Công trả lời với tư cách kỹ sư.
    #
    # Và một bug của EIDE lộ ra ở đúng chỗ rẽ nhánh: `code.vendor_list` trả
    # *"hết hạn mức GitHub, còn 222 s — có thể repo không tồn tại"*. Gộp hai chuyện dẫn tới
    # hai hành động ngược nhau, nên tác tử tin vế sau và định TỰ GÕ LẠI nhân FreeRTOS.
    if lam(4):
        nk.buoc("Trả lời bốn con số, và báo chỗ EIDE vừa được sửa")
        loi, cc = hoi(g, nk, du_an,
                      "Bốn con số bạn hỏi, mình xác nhận với tư cách kỹ sư:\n\n"
                      "1. **Flash bắt đầu tại `0x08000000`** — vùng nhớ chương trình nội của "
                      "mọi STM32F4.\n"
                      "2. **SRAM bắt đầu tại `0x20000000`**, 320 KB liền mạch (SRAM1 112 KB "
                      "+ SRAM2 16 KB + SRAM3 128 KB + 64 KB CCM ở `0x10000000` — CCM **không "
                      "liền** vùng kia, đừng gộp vào cùng một vùng linker).\n"
                      "3. **HSI = 16 000 000 Hz** khi khởi động.\n"
                      "4. **Heap FreeRTOS = 32768 byte** — đủ cho vài tác vụ, và còn chỗ cho "
                      "ngăn xếp.\n\n"
                      "Một chuyện nữa, và đây là lỗi của **EIDE chứ không phải của bạn**: "
                      "`code.vendor_list` vừa rồi trả về *“hết hạn mức GitHub, còn 222 s — "
                      "có thể repo không tồn tại”*. Hai vế ấy dẫn tới hai hành động ngược "
                      "nhau, và vế sau là sai: repo `FreeRTOS/FreeRTOS-Kernel` **có thật**, "
                      "chỉ là máy này đã dùng hết 60 lượt/giờ của GitHub.\n\n"
                      "Mình đã sửa: giờ nó trả mã lỗi riêng `E3003` kèm số phút phải đợi, và "
                      "nói thẳng là **đừng đổi repo, đừng tự viết lại mã của hãng bằng "
                      "tay**.\n\n"
                      "Nên sửa lại bước 2 trong kế hoạch của bạn: FreeRTOS là mã phải **LẤY** "
                      "từ kho của hãng, không phải mã để nhớ lại. Đợi hết hạn mức rồi lấy "
                      "thật. Trong lúc chờ, làm những bước không cần mạng.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_tool_propose(nk, ctx, cc)
        _kiem_freertos(nk, du_an)
        nk.anh(g, "tra-loi-va-sua-bug")

    # ------------------------------------------------------------------ 5. làm tiếp
    if lam(5):
        nk.buoc("Làm tiếp theo kế hoạch đã duyệt")
        loi, cc = hoi(g, nk, du_an,
                      "Làm tiếp theo kế hoạch đã duyệt đi bạn. Hạn mức GitHub chắc đã hồi, "
                      "nên lấy mã FreeRTOS thật về được rồi.\n\n"
                      "Đừng tốn lượt cho `ledger.query` — kế hoạch đã duyệt hiện ngay trong "
                      "ngữ cảnh mỗi lượt của bạn, và `plan.step_done` là chỗ bạn ghi mình "
                      "đang ở bước nào.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_freertos(nk, du_an)
        _kiem_tool_propose(nk, ctx, cc)
        _kiem_tien_do_ke_hoach(nk, ctx)
        nk.anh(g, "lam-tiep")

    nk.ghi("Kết thúc phiên", f"nhật ký: {nk.md} · ảnh: {nk.ra / 'anh'}")
    return 0


def _kiem_tien_do_ke_hoach(nk: Any, ctx: Any) -> None:
    """Tác tử có đánh dấu tiến độ theo kế hoạch không — hay chỉ làm rồi quên nói tới đâu."""
    from eide.ke_hoach import MA_KE_HOACH, KeHoach

    a = ctx.store.get(MA_KE_HOACH)
    if not a:
        nk.ket(False, "Tiến độ kế hoạch được đánh dấu bằng hiện vật", "không có kế hoạch nào")
        return
    kh = KeHoach.from_dict(a.get("canonical") or {})
    xong = [b for b in kh.buoc if b.xong]
    nk.ket(bool(xong), "Tiến độ kế hoạch được đánh dấu bằng hiện vật (plan.step_done)",
           (f"{len(xong)}/{len(kh.buoc)} bước xong · "
            + "; ".join(f"{i+1}. {b.ghi_chu[:50]}" for i, b in enumerate(kh.buoc) if b.xong))
           if xong else
           f"0/{len(kh.buoc)} bước được đánh dấu — làm rồi mà không ai biết đang ở đâu")


# ==================================================================== đối chiếu bằng mã
def _kiem_ghi_bo_nho(nk: Any, du_an: pathlib.Path) -> None:
    """Tác tử có ghi thông tin bo vào bộ nhớ dài hạn của dự án không.

    Đo được ở phiên trước: `EIDE.md` — thứ tác tử ĐỌC MỖI LƯỢT — gần như trống sau 34 bước,
    và mỗi lượt mới nó lại tiêu 3–10 lời gọi để tự định vị. Cơ chế có sẵn từ đầu; thứ thiếu
    là một lý do cụ thể để dùng nó đúng lúc.
    """
    p = du_an / "EIDE.md"
    if not p.exists():
        nk.ket(False, "Thông tin bo được ghi vào bộ nhớ dài hạn (EIDE.md)", "chưa có EIDE.md")
        return
    t = p.read_text("utf-8", errors="replace")
    moc = [m for m in ("STM32F469", "PG6", "PD4", "PK3", "PA0", "nostdlib", "OTM8009A",
                       "0xC0000000", "armv7e-m", "st.com")
           if m.lower() in t.lower()]
    nk.ket(len(moc) >= 3,
           "Thông tin bo được ghi vào bộ nhớ dài hạn (EIDE.md), không chỉ đọc rồi quên",
           f"{len(moc)}/10 mốc có trong EIDE.md: {', '.join(moc) or '—'}")


def _kiem_plan_mode(nk: Any, ctx: Any, cc: list[dict]) -> None:
    """Việc lớn có đi qua plan mode không — và kế hoạch có nói đủ thứ nó phải nói không.

    Kịch bản KHÔNG bảo tác tử dùng plan mode. Nếu nó tự tìm tới, đó là phép đo có nghĩa; nếu
    không, đó cũng là phép đo có nghĩa — và là việc phải sửa ở mô tả công cụ, không phải ở
    lời giao việc.
    """
    from eide.ke_hoach import MA_KE_HOACH, KeHoach

    goi = [c["tool"] for c in cc]
    vao = "plan.enter" in goi
    a = ctx.store.get(MA_KE_HOACH)
    kh = KeHoach.from_dict(a.get("canonical") or {}) if a else None
    if kh is None:
        nk.ket(False, "Việc lớn đi qua PLAN MODE (tác tử tự tìm tới, không ai bảo)",
               f"không có kế hoạch nào; chuỗi công cụ: {' → '.join(goi[:8]) or '—'}")
        return
    bang = "\n".join(
        f"{i}. {b.viec[:60]:62} {b.cong_cu:18} → {b.hien_vat[:34]}"
        for i, b in enumerate(kh.buoc, 1))
    nk.ket(vao and bool(kh.buoc),
           "Việc lớn đi qua PLAN MODE (tác tử tự tìm tới, không ai bảo)",
           f"trạng thái: {kh.trang_thai} · {len(kh.buoc)} bước\n{bang}"
           + (f"\n\nGiả định đang dựa vào ({len(kh.gia_dinh)}): "
              + "; ".join(kh.gia_dinh[:4]) if kh.gia_dinh else
              "\n\nKhông nêu giả định nào."))


def _kiem_tool_propose(nk: Any, ctx: Any, cc: list[dict]) -> None:
    """Tác tử có tự thấy thiếu công cụ và xin viết không."""
    xin = [c for c in cc if c["tool"] == "tool.propose"]
    nap = [c for c in cc if c["tool"] == "tool.reload"]
    if not xin:
        nk.ghi("Tự bù năng lực",
               "lượt này tác tử không xin viết công cụ nào — không sao, chỉ ghi lại để "
               "biết cơ chế có được dùng hay không.")
        return
    nk.ket(bool(nap), "Tác tử TỰ VIẾT được một công cụ mới cho chính nó",
           "; ".join(json.dumps(c["args"], ensure_ascii=False)[:120] for c in xin + nap))


def _kiem_freertos(nk: Any, du_an: pathlib.Path) -> None:
    """FreeRTOS đã thật sự vào dự án chưa, và có đúng phần cho Cortex-M4F không."""
    fw = du_an / "firmware"
    tep = sorted(p.name for p in fw.rglob("*") if p.is_file()) if fw.exists() else []
    coi = {"tasks.c": "lõi bộ lập lịch", "queue.c": "hàng đợi", "list.c": "danh sách",
           "port.c": "phần phụ thuộc kiến trúc", "FreeRTOSConfig.h": "cấu hình",
           "heap_4.c": "cấp phát bộ nhớ"}
    co = {k: v for k, v in coi.items() if k in tep}
    nk.ket(len(co) >= 4,
           "FreeRTOS thật sự nằm trong dự án (không phải chỉ được nhắc tên)",
           ", ".join(f"{k} ({v})" for k, v in co.items()) or "không thấy tệp nào của FreeRTOS")
    # `port.c` của ARM_CM4F, không phải của kiến trúc khác — đây là chỗ "tương thích" thành
    # một thứ đo được thay vì một lời tuyên bố.
    pc = [p for p in fw.rglob("port.c")] if fw.exists() else []
    if pc:
        t = pc[0].read_text("utf-8", errors="replace")[:4000]
        m4f = "CM4" in t or "FPU" in t or "__FPU_USED" in t
        nk.ket(m4f, "`port.c` là bản cho Cortex-M4F (khớp chip), không phải kiến trúc khác",
               f"{pc[0].relative_to(du_an)} · "
               + ("có nhắc CM4/FPU" if m4f else "KHÔNG thấy dấu hiệu CM4/FPU"))
