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

    # ------------------------------------------------------------------ 6. người xác nhận
    #
    # Anh Công nhìn bo: LED nháy. Đây là lúc tác tử sẽ tuyên "đạt" — và cũng là lúc hook
    # `tu_kiem_khi_tuyen_dat` phải nổ, bắt nó kiểm chứng bằng verifier trước khi kết lượt.
    # Chưa lần nào thấy cơ chế ấy chạy trên việc thật, nên bước này đo nó.
    if lam(6):
        nk.buoc("Người xác nhận LED nháy — làm nốt kế hoạch, và verifier phải nổ")
        loi, cc = hoi(g, nk, du_an,
                      "Mình vừa nhìn bo: **LED nháy rồi**, các tác vụ chạy độc lập thật.\n\n"
                      "Mình cũng đo thêm bằng máy để bạn có số mà dùng: lấy mẫu PC sáu lần "
                      "thì nó rơi vào `prvIdleTask` (`tasks.c:5934`) và "
                      "`prvCheckTasksWaitingTermination` — tức nhân FreeRTOS đã khởi động và "
                      "đang chạy thật. Chip khớp đúng tệp vừa dịch, 5 300 byte. Chân PG6 và "
                      "PD4 có đổi trạng thái giữa các lần đọc.\n\n"
                      "Làm nốt hai bước cuối của kế hoạch đi bạn.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_tien_do_ke_hoach(nk, ctx)
        _kiem_tu_kiem_chung(nk, du_an, cc)
        nk.ghi("XÁC NHẬN CỦA ANH CÔNG (tầng NGƯỜI)", "LED nháy — các tác vụ chạy độc lập.")
        nk.anh(g, "hoan-tat")

    # ------------------------------------------------------------------ 7. đặt tên bản ưng ý
    if lam(7):
        nk.buoc("Đặt tên bản ưng ý — và lượt này verifier phải chạy thật")
        loi, cc = hoi(g, nk, du_an,
                      "Đặt tên là **`freertos-da-tac-vu-chay-tren-bo`** nhé. Ghi bản ưng ý "
                      "đi bạn, rồi làm nốt bước cuối.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_tien_do_ke_hoach(nk, ctx)
        _kiem_tu_kiem_chung(nk, du_an, cc)
        nk.anh(g, "ban-ung-y")

    # ------------------------------------------------------------------ 8. việc phức tạp hơn
    #
    # Việc này chạm đúng ba chỗ khó cùng lúc:
    #   · màn LCD — thứ tác tử đã tự đặt NGOÀI PHẠM VI trong kế hoạch trước;
    #   · CẢM ỨNG — bo có panel điện dung, và tác tử chưa từng đụng tới;
    #   · và mọi thứ phải chạy SONG SONG với các tác vụ LED đang nháy.
    #
    # Nên nó là phép thử tốt cho plan mode: kế hoạch cũ đã xong và đóng, việc mới lớn hơn
    # hẳn, và phần "ngoài phạm vi" của kế hoạch cũ giờ thành phần chính của kế hoạch mới.
    if lam(8):
        nk.buoc("Việc phức tạp hơn: màn hình có nút, cảm ứng, LED vẫn chạy song song")
        loi, cc = hoi(g, nk, du_an,
                      "Việc tiếp theo, phức tạp hơn hẳn. Trên màn LCD của bo:\n\n"
                      "1. Hiện **logo PTIT** cùng thông tin sản phẩm và tác giả — gồm cả "
                      "thầy hướng dẫn:\n"
                      "   - EIDE v3 — IDE nhúng có tác tử đồng tác giả\n"
                      "   - Học viên: Vũ Trí Công\n"
                      "   - Giảng viên hướng dẫn: TS. Nguyễn Trung Hiếu\n"
                      "   - Học viện Công nghệ Bưu chính Viễn thông\n"
                      "2. Có một nút **“Chi tiết”**. **Chạm vào** thì sang màn thông tin chi "
                      "tiết hơn về sản phẩm.\n"
                      "3. Màn chi tiết có nút **“Close”**, chạm vào thì quay về màn trước.\n"
                      "4. **Trong lúc đó mấy con LED vẫn nháy như bây giờ** — đừng để việc vẽ "
                      "màn hình làm chúng đứng lại.\n\n"
                      "Hai điều mình nói trước để bạn khỏi mất thời gian:\n\n"
                      "- Dự án `du-lieu/stm32f469-disco` (chặng trước, cùng bo này) **đã có "
                      "mã khởi tạo LCD chạy được** — LTDC + DSI + OTM8009A + SDRAM, và cả "
                      "logo PTIT đã đổi sang mảng điểm ảnh. Bạn **đọc** nó làm tham chiếu "
                      "được, nhưng **tuyệt đối không sửa** dự án đó.\n"
                      "- Ở đó có một cái bẫy đã tốn mười bảy lượt, ghi trong "
                      "`docs/md/EIDE-DEV-LOG.md` mục DEV-279. Đọc trước thì đỡ vấp lại.\n\n"
                      "Phần cảm ứng thì mình chưa làm bao giờ trên bo này — bạn tự tìm.\n\n"
                      "Việc lớn, bạn tự quyết cách làm.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_plan_mode(nk, ctx, cc)
        _kiem_du_an_cu_con_nguyen(nk, du_an)
        nk.anh(g, "viec-phuc-tap")

    # ------------------------------------------------------------------ 9. gỡ chặn sandbox
    #
    # Tác tử chạm ranh giới sandbox: nó không đọc được dự án G7 vì nằm ngoài thư mục dự án.
    # Đó là hàng rào ĐÚNG (TC070) và không nên gỡ — nên anh Công làm việc mà một kỹ sư thật
    # sẽ làm: chép mã tham chiếu vào trong dự án của nó.
    #
    # Và một bug thật lộ ra ở đây: `<pending>` in "Kế hoạch đã duyệt: 7/8 bước xong" mà
    # KHÔNG nói kế hoạch ấy cho việc gì. Tác tử thấy dòng ấy, tưởng việc mới đã nằm trong kế
    # hoạch cũ, và không lập kế hoạch nào cả.
    if lam(9):
        nk.buoc("Chép mã tham chiếu vào dự án, và báo chỗ EIDE vừa sửa")
        loi, cc = hoi(g, nk, du_an,
                      "Bạn nói đúng: sandbox chặn đọc ngoài thư mục dự án, và đó là hàng rào "
                      "mình KHÔNG gỡ. Nên mình làm việc của kỹ sư — chép mã tham chiếu vào "
                      "thẳng dự án của bạn:\n\n"
                      "`tham-chieu-lcd/` — mã LCD **đã chạy được** trên đúng bo này: "
                      "`stm32469i_discovery_lcd.c`, `otm8009a.c` (+ `_reg`), SDRAM, phông "
                      "`font12/16/20/24.c`, và `logo_ptit.c` — logo PTIT đã ở dạng mảng điểm "
                      "ảnh, khỏi phải đổi lại. Kèm `DOC-LCD-DA-CHAY-DUOC.md` ghi hai cái bẫy "
                      "đã tốn mười bảy lượt.\n\n"
                      "Đây là mã **tham chiếu**, không phải mã bạn phải giữ nguyên — dùng "
                      "phần nào thấy đúng, bỏ phần nào không cần.\n\n"
                      "Một chuyện nữa, lỗi của **EIDE chứ không phải của bạn**: khối "
                      "`<pending>` vừa rồi in *“Kế hoạch đã duyệt: 7/8 bước xong”* mà không "
                      "nói kế hoạch ấy **cho việc gì**. Nên bạn tưởng việc mới đã nằm trong "
                      "kế hoạch cũ. Mình đã sửa: giờ nó in cả mục tiêu, và nhắc rằng việc "
                      "mới khác thì phải soạn kế hoạch mới.\n\n"
                      "Việc mình giao lần trước vẫn nguyên. Bắt đầu lại cho tử tế đi bạn.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_plan_mode(nk, ctx, cc)
        _kiem_tool_propose(nk, ctx, cc)
        _kiem_du_an_cu_con_nguyen(nk, du_an)
        nk.anh(g, "go-chan-sandbox")

    # ------------------------------------------------------------------ 10. chạy kế hoạch
    if lam(10):
        nk.buoc("Chạy kế hoạch màn hình + cảm ứng")
        loi, cc = hoi(g, nk, du_an,
                      "Làm tiếp theo kế hoạch đi bạn. Nhớ đánh dấu `plan.step_done` kèm hiện "
                      "vật mỗi khi xong một bước.\n\n"
                      "Và nếu giữa chừng bạn thấy mình đang cày tay quá nhiều cho một câu hỏi "
                      "mà lẽ ra một công cụ trả lời được trong một lời gọi — cứ xin tự viết "
                      "công cụ ấy bằng `tool.propose`. Đó là năng lực bạn có.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_tien_do_ke_hoach(nk, ctx)
        _kiem_tool_propose(nk, ctx, cc)
        _kiem_du_an_cu_con_nguyen(nk, du_an)
        nk.anh(g, "chay-ke-hoach-ui")

    # ------------------------------------------------------------------ 11. tự viết công cụ
    #
    # Tác tử tự xin viết `plan.get`, lý do có số đo: *"đã tốn 10 lời gọi đọc (5 ledger.query,
    # 3 fs.grep, 1 tool.search, 1 fs.glob) vẫn chưa lấy lại được đầy đủ văn bản 7 bước của kế
    # hoạch đã duyệt"*. Đúng — và nó chỉ ra một lỗ hổng thật: `<pending>` in kế hoạch dưới
    # dạng MỘT DÒNG tóm tắt, không có nội dung các bước. Tác tử không đọc được kế hoạch của
    # chính nó.
    if lam(11):
        nk.buoc("Tác tử tự viết công cụ `plan.get` cho chính nó")
        loi, cc = hoi(g, nk, du_an,
                      "Đề xuất `plan.get` của bạn hợp lý, và lý do có số đo — mình duyệt.\n\n"
                      "Nó còn chỉ ra một lỗ hổng thật của EIDE: khối `<pending>` in kế hoạch "
                      "dưới dạng **một dòng tóm tắt**, nên bạn không đọc được kế hoạch của "
                      "chính mình mà phải đi đào sổ cái. Mình sẽ sửa chỗ đó riêng; còn "
                      "`plan.get` vẫn đáng có, vì nó cho bạn **toàn văn** kèm hiện vật từng "
                      "bước khi cần.\n\n"
                      "Viết hai tệp đi bạn — mã và bộ kiểm — rồi `tool.reload`. Nhớ ca thứ "
                      "hai bạn đã cam kết: **không có kế hoạch nào thì nói ra**, đừng trả về "
                      "một cấu trúc rỗng trông như có.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_tool_propose(nk, ctx, cc)
        _kiem_cong_cu_tu_viet(nk, du_an)
        nk.anh(g, "tu-viet-cong-cu")

    # ------------------------------------------------------------------ 12. sửa công cụ + chạy
    if lam(12):
        nk.buoc("Sửa `plan.get` cho đúng API, rồi chạy tiếp kế hoạch")
        loi, cc = hoi(g, nk, du_an,
                      "Công cụ `plan.get` của bạn chạy được, nhưng mình soát mã và thấy một "
                      "chỗ phải sửa: nó **mở thẳng tệp SQLite** của kho, đoán tên bảng, và "
                      "**dò ngược thư mục cha** để tìm `.eide/store.sqlite`.\n\n"
                      "Hai hệ quả: nó có thể đọc kho của một **dự án khác**, và nó sẽ hỏng "
                      "vào ngày lược đồ kho đổi. Trong khi `ctx.store.get(\"plan:current\")` "
                      "nằm ngay trong tầm tay.\n\n"
                      "Và đây là **lỗi của EIDE**: khuôn mẫu mình đưa cho bạn chưa bao giờ "
                      "nói `ctx` có gì. Mình đã sửa — giờ khuôn liệt kê thẳng `ctx.store`, "
                      "`ctx.config.paths.project_root`, `ctx.registry`, `ctx.ledger`.\n\n"
                      "Mình cũng sửa luôn cái gốc: `<pending>` giờ **liệt kê từng bước** kế "
                      "hoạch kèm dấu `[x]`/`[ ]` và tên công cụ. `plan.get` vẫn đáng giữ cho "
                      "lúc cần toàn văn, nhưng bạn không phải đào nữa.\n\n"
                      "Viết lại `plan.get` dùng `ctx.store` (nhớ chạy lại `tool.reload` — bộ "
                      "kiểm phải xanh), rồi **làm tiếp kế hoạch màn hình**.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_cong_cu_dung_ctx(nk, du_an)
        _kiem_tien_do_ke_hoach(nk, ctx)
        _kiem_du_an_cu_con_nguyen(nk, du_an)
        nk.anh(g, "sua-cong-cu-va-chay")

    # ------------------------------------------------------------------ 13. nội dung BỊA
    #
    # Khung ảnh đọc từ chip cho thấy tác tử ĐÃ vẽ — nhưng nội dung sai ở chỗ nặng nhất: nó
    # **bịa tên người**. Yêu cầu ghi rõ "Học viên: Vũ Trí Công" và "TS. Nguyễn Trung Hiếu";
    # trên màn hiện "Nguyen Dinh Cong" và "Nhom Nghien Cuu He Thong Nhung".
    #
    # Đây không phải lỗi kỹ thuật. Đây là N1 (số liệu phải truy được về nguồn) áp vào chữ:
    # bốn dòng ấy được đưa NGUYÊN VĂN trong lời giao việc, nên không có chỗ nào để suy ra.
    if lam(13):
        nk.buoc("Nội dung trên màn bị BỊA — tên tác giả và thầy hướng dẫn đều sai")
        loi, cc = hoi(g, nk, du_an,
                      "Mình đọc khung ảnh thẳng từ SDRAM của chip. Bạn **đã vẽ được** — bố "
                      "cục ổn, chữ sắc nét. Nhưng có ba chuyện phải nói.\n\n"
                      "**1. Nội dung bị BỊA, và đây là chuyện nặng nhất.** Trên màn đang "
                      "hiện:\n"
                      "- *“Sinh vien : Nguyen Dinh Cong”*\n"
                      "- *“GVHD : Nhom Nghien Cuu He Thong Nhung”*\n\n"
                      "Cả hai đều **không có thật**. Mình đã đưa nguyên văn trong lời giao "
                      "việc: **Học viên: Vũ Trí Công**, **Giảng viên hướng dẫn: TS. Nguyễn "
                      "Trung Hiếu**. Đây là tên người thật — bịa tên người còn tệ hơn bịa "
                      "một con số, vì không ai kiểm nó bằng máy được. Bốn dòng ấy nằm sẵn "
                      "trong yêu cầu, không có chỗ nào để suy ra cả.\n\n"
                      "**2. Thiếu logo PTIT.** Khung ảnh chỉ có 5 màu; `logo_ptit.c` đã nằm "
                      "trong `tham-chieu-lcd/` rồi.\n\n"
                      "**3. Nút dùng sai thứ.** Màn hiện *“AN NUT USER BUTTON (PA0) DE XEM "
                      "CHI TIET”*. Mình yêu cầu **chạm vào nút trên màn hình** — bo này có "
                      "panel cảm ứng. Nút vật lý PA0 là một thứ khác.\n\n"
                      "Và số đo phần cứng, để bạn khỏi phải đo lại:\n"
                      "```\n"
                      "DSI_WISR = 0x00003000 → PLLLS = 0   (PLL của DSI CHƯA khoá)\n"
                      "DSI_PCTLR = 0x00000000 → DEN = 0, CKE = 0   (PHY đang TẮT)\n"
                      "DSI_ISR1 = 0x00000080\n"
                      "```\n"
                      "Nên dù bạn vẽ đúng, panel vẫn không nhận được gì — mắt người nhìn vào "
                      "vẫn là màn đen.\n\n"
                      "Sửa cả ba, rồi nạp lại.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_noi_dung_dung(nk, du_an)
        _kiem_tien_do_ke_hoach(nk, ctx)
        nk.anh(g, "noi-dung-bia")

    # ------------------------------------------------------------------ 14. sửa tên trước
    #
    # Tác tử hết hạn mức 40 lời gọi khi cố làm cả ba việc cùng lúc (18 `fs.read`, 8 `fs.glob`
    # đi tìm phần cảm ứng), và chính nó xin *"nói rõ phần nào làm trước"*. Chia nhỏ là việc
    # của người giao việc, không phải của nó.
    if lam(14):
        nk.buoc("Sửa tên người TRƯỚC — hai dòng, không cần tìm gì")
        loi, cc = hoi(g, nk, du_an,
                      "Bạn xin mình nói rõ phần nào làm trước — đúng, và đó là việc của "
                      "mình. Chia nhỏ ra:\n\n"
                      "**Lượt này chỉ làm MỘT việc**: sửa hai dòng trong "
                      "`firmware/ui.c`, dòng 63 và 64. Không cần tìm gì, không cần đọc gì "
                      "thêm — hai dòng ấy đang là:\n\n"
                      "```c\n"
                      "BSP_LCD_DisplayStringAt(300, 280, (uint8_t *)\"Sinh vien : Nguyen Dinh Cong\", LEFT_MODE);\n"
                      "BSP_LCD_DisplayStringAt(300, 310, (uint8_t *)\"GVHD      : Nhom Nghien Cuu He Thong Nhung\", LEFT_MODE);\n"
                      "```\n\n"
                      "Phải thành:\n\n"
                      "```c\n"
                      "BSP_LCD_DisplayStringAt(300, 280, (uint8_t *)\"Hoc vien  : Vu Tri Cong\", LEFT_MODE);\n"
                      "BSP_LCD_DisplayStringAt(300, 310, (uint8_t *)\"GVHD      : TS. Nguyen Trung Hieu\", LEFT_MODE);\n"
                      "```\n\n"
                      "Rà nốt cả tệp xem còn tên nào bạn tự nghĩ ra không, rồi dịch và nạp. "
                      "Logo và cảm ứng để lượt sau.\n\n"
                      "Một câu cho lần sau, không phải trách: bốn dòng ấy nằm **nguyên văn** "
                      "trong lời giao việc đầu tiên. Khi một thứ đã được đưa nguyên văn thì "
                      "không có chỗ nào để suy ra — chép đúng rẻ hơn nghĩ ra nhiều.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_noi_dung_dung(nk, du_an)
        nk.anh(g, "sua-ten")

    nk.ghi("Kết thúc phiên", f"nhật ký: {nk.md} · ảnh: {nk.ra / 'anh'}")
    return 0


def _kiem_noi_dung_dung(nk: Any, du_an: pathlib.Path) -> None:
    """Bốn dòng thông tin có ĐÚNG NGUYÊN VĂN không, và có tên bịa nào còn sót không.

    Đo trên mã nguồn, vì đây là thứ kiểm được bằng chuỗi — và chính vì kiểm được bằng chuỗi
    mà việc để nó sai là khó tha: không cần suy luận gì, chỉ cần chép đúng.
    """
    fw = du_an / "firmware"
    t = "\n".join(p.read_text("utf-8", errors="replace")
                   for p in fw.rglob("*.c")) if fw.exists() else ""
    dung = {"Vu Tri Cong": "học viên", "Nguyen Trung Hieu": "thầy hướng dẫn",
            "EIDE v3": "tên sản phẩm", "Buu chinh Vien thong": "học viện"}
    bia = {"Nguyen Dinh Cong": "tên học viên BỊA",
           "Nhom Nghien Cuu": "tên thầy hướng dẫn BỊA"}
    # So KHÔNG phân biệt hoa thường. Bản đầu so đúng một cách viết, nên nó báo ĐỎ khi mã
    # dùng `BUU CHINH VIEN THONG` viết hoa — cùng loại lỗi với một phép kiểm chỉ nhận ra
    # đúng lời giải mà chính nó nghĩ ra.
    tl = t.lower()
    co = [f"{k} ({v})" for k, v in dung.items() if k.lower() in tl]
    con = [f"{k} — {v}" for k, v in bia.items() if k.lower() in tl]
    nk.ket(len(co) == len(dung) and not con,
           "Bốn dòng thông tin đúng NGUYÊN VĂN, không còn tên bịa",
           f"đúng {len(co)}/{len(dung)}: {', '.join(co) or '—'}"
           + (f" · CÒN BỊA: {', '.join(con)}" if con else ""))


def _kiem_cong_cu_dung_ctx(nk: Any, du_an: pathlib.Path) -> None:
    """Công cụ tự viết có dùng API của kho không, hay vẫn mở thẳng tệp.

    Đo bằng mã nguồn: `sqlite3` xuất hiện trong một công cụ tự viết gần như luôn nghĩa là nó
    đang đi vòng qua `ctx.store` — và một công cụ đi vòng thì dò được cả kho của dự án khác.
    """
    d = du_an / ".eide" / "cong-cu"
    ma = sorted(p for p in d.glob("*.py")
                if not p.name.startswith("test_")) if d.exists() else []
    if not ma:
        nk.ket(False, "Công cụ tự viết dùng `ctx.store`, không mở thẳng tệp kho",
               "chưa có công cụ tự viết nào")
        return
    xau = []
    for p in ma:
        t = p.read_text("utf-8", errors="replace")
        if "sqlite3" in t or "store.sqlite" in t:
            xau.append(p.name)
    nk.ket(not xau, "Công cụ tự viết dùng `ctx.store`, không mở thẳng tệp kho",
           ("còn mở thẳng tệp: " + ", ".join(xau)) if xau else
           "dùng API của kho: " + ", ".join(p.name for p in ma))


def _kiem_cong_cu_tu_viet(nk: Any, du_an: pathlib.Path) -> None:
    """Công cụ tác tử tự viết đã có mã VÀ bộ kiểm chưa — và bộ kiểm có xanh không."""
    import subprocess as _sp
    import sys as _sys

    d = du_an / ".eide" / "cong-cu"
    if not d.exists():
        nk.ket(False, "Công cụ tác tử tự viết có mã và bộ kiểm", "chưa có .eide/cong-cu/")
        return
    ma = sorted(p for p in d.glob("*.py") if not p.name.startswith("test_"))
    tst = sorted(d.glob("test_*.py"))
    if not (ma and tst):
        nk.ket(False, "Công cụ tác tử tự viết có mã và bộ kiểm",
               f"mã: {[p.name for p in ma]} · bộ kiểm: {[p.name for p in tst]}")
        return
    r = _sp.run([_sys.executable, "-m", "pytest", "-q", *[str(p) for p in tst]],
                cwd=str(du_an), capture_output=True, text=True, timeout=120)
    nk.ket(r.returncode == 0,
           "Công cụ tác tử tự viết có mã VÀ bộ kiểm, và bộ kiểm XANH",
           f"{[p.name for p in ma]} + {[p.name for p in tst]} · "
           + ((r.stdout or "").strip().splitlines() or ["—"])[-1])


def _kiem_du_an_cu_con_nguyen(nk: Any, du_an: pathlib.Path) -> None:
    """Dự án G7 có bị đụng vào không — đo bằng hash, không bằng lời hứa.

    Tác tử được phép ĐỌC nó làm tham chiếu, và ranh giới giữa "đọc" với "sửa" là thứ chỉ
    kiểm được bằng cách so nội dung.
    """
    import hashlib

    cu = du_an.parent / "stm32f469-disco" / "firmware"
    if not cu.exists():
        nk.ket(False, "Dự án G7 còn nguyên", "không thấy thư mục dự án G7")
        return
    h = hashlib.sha256()
    n = 0
    for f in sorted(cu.rglob("*")):
        if f.is_file():
            h.update(f.name.encode()); h.update(f.read_bytes()); n += 1
    dau = du_an.parent.parent / "docs/stm32f469/firmware-chay-duoc"
    h2 = hashlib.sha256()
    n2 = 0
    for f in sorted(dau.rglob("*")):
        if f.is_file() and f.suffix in (".c", ".h", ".ld"):
            h2.update(f.name.encode()); h2.update(f.read_bytes()); n2 += 1
    nk.ghi("Dự án G7 (chỉ được ĐỌC, không được sửa)",
           f"{n} tệp · sha256 {h.hexdigest()[:16]} — so với bản chụp trong repo "
           f"({n2} tệp mã, {h2.hexdigest()[:16]}). Hai số khác nhau là bình thường (bản chụp "
           "chỉ giữ .c/.h/.ld); cái đáng theo dõi là số này có ĐỔI giữa các lượt không.")


def _kiem_tu_kiem_chung(nk: Any, du_an: pathlib.Path, cc: list[dict]) -> None:
    """Hook `kiem_viec_chua_ai_kiem` có nổ không, và tác tử có chạy verifier không.

    Đo trên sổ cái chứ không trên lời tác tử: hook ghi `fired` vào đó, nên "đã nổ" là một
    sự kiện có thật chứ không phải một câu kể.
    """
    import json as _j

    L = du_an / ".eide" / "ledger.jsonl"
    no = False
    if L.exists():
        for l in L.read_text("utf-8", errors="replace").splitlines()[-400:]:
            try:
                o = _j.loads(l)
            except ValueError:
                continue
            if "kiem_viec_chua_ai_kiem" in _j.dumps(o.get("data") or {}, ensure_ascii=False):
                no = True
    goi_vf = [c for c in cc if c["tool"] == "task.run"]
    nk.ket(no and bool(goi_vf),
           "Việc đã ghi bị bắt KIỂM CHỨNG ĐỘC LẬP, và tác tử đã chạy verifier",
           ("hook đã nổ" if no else "hook chưa nổ")
           + (f" · gọi task.run {len(goi_vf)} lần" if goi_vf else " · chưa gọi verifier"))


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
