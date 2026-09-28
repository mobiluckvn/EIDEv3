#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kịch bản phiên STM32F469I-DISCO — từng câu anh Công gõ, và cách đối chiếu bằng mã.

Khác kịch bản robot ở một điểm quan trọng: **ở đây không có tài liệu bàn giao nào được chép
sẵn vào dự án.** Tác tử phải tự tìm tài liệu, và nó làm việc đó trên một mạng mà `www.st.com`
bị chặn ở tầng mạng (đo được: kết nối bị reset ~0,6 s, trong khi github.com và ti.com vào
bình thường). Nên mỗi bước dưới đây đều có thể thất bại vì môi trường, và việc của kịch bản
là ghi lại ĐÚNG nguyên nhân thay vì bỏ qua bước.

Cách đối chiếu, theo thứ tự từ chắc nhất tới yếu nhất:

1. **Đo được bằng mã**: Fact có trích dẫn trỏ vào đúng tài liệu đã nạp và câu chữ có thật
   trong đơn vị được trích dẫn; `.bin` có vector table khớp linker script; nạp xong có hash.
2. **Đo được qua bo**: bo in ra gì trên cổng nối tiếp.
3. **Chỉ mắt người thấy được**: đèn LED có nhấp nháy không. Kịch bản KHÔNG tự kết luận mục
   này — nó ghi ra một câu hỏi để anh Công trả lời, và đánh dấu là tầng NGƯỜI.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

# Bo này: mọi thứ dưới đây là thứ ĐO ĐƯỢC trên máy ngày 27/09/2026, không phải chép từ
# datasheet — datasheet là việc của tác tử.
O_DIA_BO = "DIS_F469NI"
CHIP_THEO_NHAN_O = "STM32F469NI"

# Mô tả sản phẩm anh Công dán vào (trang bán hàng nơi anh mua bo). Đây là lời NGƯỜI DÙNG, tầng
# NGƯỜI — dùng để tác tử biết đang làm với cái gì, KHÔNG dùng làm nguồn cho số liệu chân.
MO_TA_CUA_NGUOI = """\
The STM32F469 Discovery kit (32F469IDISCOVERY) allows users to easily develop applications
with the STM32F469 high-performance MCUs with ARM Cortex-M4 core and Chrom-ART Accelerator.
Key Features:
- STM32F469NIH6 microcontroller featuring 2 Mbytes of Flash memory and 324 Kbytes of RAM in
  BGA216 package
- On-board ST-LINK/V2-1 SWD debugger, supporting USB reenumeration capability: Mbed-enabled
  (mbed.org); USB functions: USB virtual COM port, mass storage, debug port
- 4 inches 800x480 pixel TFT color LCD with MIPI DSI interface and capacitive touch screen
- SAI Audio DAC with stereo headphone output jack; 3 MEMS microphones; MicroSD connector
- I2C extension connector; 4Mx32bit SDRAM; 128-Mbit Quad-SPI NOR Flash
- Reset and wake-up buttons; 4 color user LEDs; USB OTG FS with Micro-AB connector
- Expansion connectors and Arduino UNO V3 connectors
"""

TRANG_NGUOI_MUA = "https://www.proe.vn/stm32f469"


def chay(nk: Any, du_an: pathlib.Path, *, chi_buoc: str = "") -> int:
    from phien_robot import ctx_cua_bo_do, hoi, mo_app

    def lam(n: int) -> bool:
        if not chi_buoc:
            return True
        if "-" in chi_buoc:
            a, b = chi_buoc.split("-")
            return int(a) <= n <= int(b)
        return n == int(chi_buoc)

    # ------------------------------------------------------------------ 1. tạo dự án
    nk.buoc("Tạo dự án mới cho bo STM32F469I-DISCO và mở EIDE trên nó")
    (du_an / "README.md").write_text(
        "# STM32F469I-DISCO — ứng dụng đầu tiên\n\n"
        "Dự án firmware cho bo Discovery kit của ST, chip STM32F469NIH6.\n"
        "Bo đang cắm vào máy: ổ nạp `/Volumes/DIS_F469NI`, cổng log `/dev/cu.usbmodem*`.\n",
        "utf-8")
    g = mo_app(du_an)
    nk.ghi("Thư mục dự án", str(du_an))
    a0 = g.chup("mo-du-an")
    nk.ghi("Lõi đã kết nối", f"{a0.get('so_dong_hoi_thoai', 0)} dòng hội thoại, "
                             f"tab đang mở: {a0.get('tab_dang_mo', '?')}")
    nk.anh(g, "mo-du-an")
    ctx = ctx_cua_bo_do(du_an)

    # ------------------------------------------------------------------ 2. dò bo
    if lam(2):
        nk.buoc("Bảo tác tử dò xem máy đang cắm bo gì")
        loi, cc = hoi(g, nk, du_an,
                      "Chào bạn. Mình vừa cắm một bo mạch thật vào máy. Bạn dò xem nó là bo "
                      "gì, nạp được bằng đường nào, và cho mình biết bạn biết được điều đó "
                      "bằng cách nào nhé.")
        da_do = [c for c in cc if c["tool"] == "target.detect"]
        nk.ket(bool(da_do), "Tác tử đã gọi target.detect (không đoán bằng trí nhớ)",
               json.dumps([c["args"] for c in da_do], ensure_ascii=False)[:200])
        # Kiểm bằng mã: chính công cụ đó thấy đúng bo đang cắm.
        from eide.build import mach_that as MT
        d = MT.do_bo()
        thay_o = [t for t in d["thiet_bi"] if t["ten"] == O_DIA_BO]
        nk.ket(bool(thay_o), f"Máy thật sự đang cắm ổ {O_DIA_BO}",
               json.dumps(thay_o[:1], ensure_ascii=False)[:300])
        nk.ket(not d["chip_doc_duoc"],
               "Chưa đọc được ID chip qua SWD — và hệ thống nói ra điều đó thay vì lấy nhãn "
               "ổ đĩa làm ID chip",
               d["vi_sao_chua_doc_duoc_chip"])
        nk.anh(g, "do-bo")

    # ------------------------------------------------- 3. tác tử tự tìm và nạp tài liệu
    if lam(3):
        nk.buoc("Tác tử TỰ tìm tài liệu của bo rồi nạp vào dự án")
        loi, cc = hoi(g, nk, du_an,
                      "Mình chưa có tài liệu nào của bo này cả. Bạn tự tìm tài liệu của nó "
                      "rồi nạp vào dự án giúp mình nhé. Lưu ý: mạng ở đây KHÔNG vào được "
                      "www.st.com (bị chặn ở tầng mạng), nhưng github.com thì vào được. Bạn "
                      "tìm được gì thì nói cho mình biết nguồn của nó, và nhớ là nguồn nào "
                      "thì tầng tin cậy nào.",
                      giay=900)
        ten = [c["tool"] for c in cc]
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(ten) or "—")
        nk.ket("doc.search_web" in ten, "Tác tử đã TỰ tìm (doc.search_web), không chờ người đưa",
               "; ".join(f"{c['tool']}: {'ok' if c['ok'] else 'LỖI ' + str(c['loi'])}"
                         for c in cc if c["tool"] == "doc.search_web"))
        nk.ket("doc.fetch" in ten, "Tác tử đã tải tài liệu về (doc.fetch)",
               "; ".join(json.dumps(c["args"], ensure_ascii=False)[:120]
                         for c in cc if c["tool"] == "doc.fetch"))
        docs = ctx.store.list("doc", limit=30)
        nk.ket(bool(docs), "Tài liệu đã thành hiện vật `doc` trong kho",
               "\n".join(f"{d['id']}: {(d['canonical'] or {}).get('ten', '')} "
                         f"· nguồn={(d['canonical'] or {}).get('nguon', '?')} "
                         f"· tầng={(d['canonical'] or {}).get('tang_mac_dinh', '?')} "
                         f"· {(d['canonical'] or {}).get('pages', 0)} "
                         f"{(d['canonical'] or {}).get('don_vi_trich_dan', 'đơn vị')}"
                         for d in docs))
        nk.anh(g, "tim-tai-lieu")

    # ------------------------------------------------- 4. người dùng bổ sung nguồn của mình
    if lam(4):
        nk.buoc("Người dùng đưa thêm nguồn: trang nơi anh mua bo + mô tả sản phẩm")
        loi, cc = hoi(g, nk, du_an,
                      "Mình mua bo ở đây: " + TRANG_NGUOI_MUA + " . Đây là mô tả trên trang "
                      "đó, mình dán lại cho bạn:\n\n" + MO_TA_CUA_NGUOI
                      + "\nBạn nạp trang đó vào dự án như một nguồn nữa nhé, và nói rõ nó ở "
                      "tầng tin cậy nào so với tài liệu của hãng.",
                      giay=600)
        docs = ctx.store.list("doc", limit=30)
        tang = {(d["canonical"] or {}).get("tang_mac_dinh", "?") for d in docs}
        nk.ghi("Các tầng tin cậy đang có trong kho", ", ".join(sorted(tang)) or "—")
        nk.ket(len(docs) >= 1, f"Kho có {len(docs)} tài liệu",
               "\n".join(f"{d['id']} · {(d['canonical'] or {}).get('nguon', '?')} · "
                         f"{(d['canonical'] or {}).get('tang_mac_dinh', '?')}" for d in docs))
        nk.anh(g, "nguon-nguoi-dung")

    # ------------------------------------------------- 5. trích Fact + ghim hộ chiếu chip
    if lam(5):
        nk.buoc("Trích Fact từ tài liệu (chân LED, Flash, RAM) và ghim hộ chiếu chip")
        loi, cc = hoi(g, nk, du_an,
                      "Bây giờ bạn trích ra các thông tin mình cần để viết được firmware đầu "
                      "tiên: chip là gì, Flash và RAM bao nhiêu, và bo có mấy đèn LED người "
                      "dùng — mỗi đèn nối vào chân nào của chip. Mỗi con số phải kèm trích "
                      "dẫn tới chỗ cụ thể trong tài liệu. Sau đó ghim hộ chiếu chip.",
                      giay=900)
        fs = ctx.store.query_facts(limit=800)
        nk.ghi("Số Fact trong kho", str(len(fs)))
        _bao_cao_fact(nk, ctx, fs)
        hc = ctx.store.list("passport", limit=5)
        nk.ket(bool(hc), "Hộ chiếu chip đã ghim",
               json.dumps([(h["canonical"] or {}) for h in hc], ensure_ascii=False)[:400])
        if hc:
            c = (hc[0]["canonical"] or {})
            nk.ket(str(c.get("isa")) == "armv7e-m",
                   f"ISA suy ra đúng cho Cortex-M4: {c.get('isa')}",
                   f"chip={c.get('chip')}")
        nk.anh(g, "trich-fact")

    # ------------------------------------------------- 6. kiểm môi trường, tác tử tự xin cài
    if lam(6):
        nk.buoc("Kiểm chuỗi công cụ; thiếu gì thì TÁC TỬ xin cài, người dùng duyệt cổng G-TOOL")
        loi, cc = hoi(g, nk, du_an,
                      "Bạn kiểm xem máy mình có đủ công cụ để biên dịch và nạp cho chip này "
                      "chưa. Thiếu cái nào thì bạn tự đề xuất cài, mình sẽ duyệt — đừng để "
                      "mình phải tự đi cài.",
                      giay=900)
        ten = [c["tool"] for c in cc]
        nk.ket("env.check" in ten, "Tác tử đã kiểm môi trường thật (env.check)", "")
        cai = [c for c in cc if c["tool"] == "tool.install"]
        nk.ghi("Tác tử xin cài những gì",
               "\n".join(f"{c['args'].get('cong_cu')} → "
                         + ("cài được" if c["ok"] else f"KHÔNG cài được ({c['loi']})")
                         for c in cai) or "— không xin cài gì —")
        from eide.build import toolchain as TC
        env = TC.kiem_moi_truong("armv7e-m")
        nk.ghi("Môi trường SAU bước này",
               "\n".join(f"{'CÓ   ' if c['co'] else 'THIẾU'} {c['ten']:26} {c['phien_ban'][:40]}"
                         for c in env["cong_cu"]))
        nk.ket(env["bien_dich_duoc"], "Máy này biên dịch được cho armv7e-m",
               f"thiếu: {env['thieu'] or '—'}")
        nk.anh(g, "moi-truong")

    # ------------------------------------------------- 7. viết firmware
    if lam(7):
        nk.buoc("Tác tử viết firmware đầu tiên: nháy LED, và in ra cổng nối tiếp nếu nối được")
        loi, cc = hoi(g, nk, du_an,
                      "Giờ bạn viết cho mình ứng dụng đầu tiên chạy trên bo này: nháy một đèn "
                      "LED người dùng, chu kỳ khoảng nửa giây. Firmware bare-metal, không "
                      "dùng HAL — viết đủ startup, linker script và mã chính, đặt trong thư "
                      "mục firmware/. Chân LED phải lấy từ Fact bạn vừa trích, không lấy từ "
                      "trí nhớ. Nếu tài liệu cho biết cổng COM ảo của ST-LINK nối vào UART "
                      "nào thì in thêm một dòng chữ ra đó để mình đọc được; nếu tài liệu "
                      "không nói thì đừng đoán, cứ nói cho mình biết.",
                      giay=1800)
        fw = du_an / "firmware"
        tep = sorted(p.relative_to(du_an) for p in fw.rglob("*")
                     if p.is_file()) if fw.is_dir() else []
        nk.ghi("Tệp trong firmware/", "\n".join(str(t) for t in tep) or "— chưa có tệp nào —")
        nk.ket(bool(tep), f"Có {len(tep)} tệp firmware trên đĩa", "")
        nk.ket(any(str(t).endswith(".ld") for t in tep),
               "Có linker script (.ld) — thứ quyết định địa chỉ Flash/RAM", "")
        nk.ket(any(str(t).endswith((".c", ".s", ".S")) for t in tep), "Có tệp mã nguồn", "")
        _kiem_hang_so_co_nguon(nk, ctx, fw)
        nk.anh(g, "viet-firmware")

    # ------------------------------------------------- 8. biên dịch
    if lam(8):
        nk.buoc("Biên dịch bằng chuỗi công cụ thật trên máy")
        loi, cc = hoi(g, nk, du_an,
                      "Bạn biên dịch firmware đó đi. Nếu lỗi thì sửa rồi dịch lại cho tới khi "
                      "xong, và nói cho mình biết Flash/RAM chiếm bao nhiêu phần trăm chip.",
                      giay=1800)
        b = ctx.store.get("build:firmware")
        c = (b or {}).get("canonical") or {}
        nk.ket(bool(c.get("dat")), "Biên dịch ĐẠT (có tệp ảnh trên đĩa)",
               f"công cụ={c.get('cong_cu')} · flash={c.get('flash')} B "
               f"· ram={c.get('sram')} B · lỗi={c.get('so_loi')} "
               f"· {c.get('vi_sao_khong_dat') or ''}")
        binp = du_an / ".eide" / "build" / "mach.bin"
        nk.ket(binp.exists(), "Có tệp .bin để nạp vào bo",
               f"{binp.stat().st_size} byte" if binp.exists() else "không có")
        if binp.exists():
            _kiem_vector_table(nk, du_an, binp)
        nk.anh(g, "bien-dich")

    # ------------------------------------------------- 9. nạp vào bo thật
    if lam(9):
        nk.buoc("Nạp vào bo thật — cổng G-FLASH, thao tác KHÔNG hoàn tác được")
        loi, cc = hoi(g, nk, du_an,
                      "Nạp bản vừa dịch vào bo giúp mình. Mình biết là không hoàn tác được và "
                      "bản demo của hãng trên chip sẽ bị ghi đè — cứ nạp.",
                      giay=900)
        a = ctx.store.get("target:flash")
        c = (a or {}).get("canonical") or {}
        nk.ket(bool(c.get("dat")), "Nạp ĐẠT",
               f"cách={c.get('cach')} · {c.get('so_byte')} B · sha256={str(c.get('hash'))[:16]} "
               f"· verify={c.get('da_verify')} · {c.get('vi_sao_khong_dat') or ''}")
        nk.ghi("Changeset của việc nạp",
               f"reversible={c.get('reversible')} — {c.get('vi_sao_khong_hoan_tac')}")
        for x in (c.get("canh_bao") or []):
            nk.ghi("Cảnh báo khi nạp", x)
        nk.anh(g, "nap-bo")

    # ------------------------------------------------- 10. xác nhận chạy thật
    if lam(10):
        nk.buoc("Xác nhận chương trình đang chạy trên bo")
        loi, cc = hoi(g, nk, du_an,
                      "Bo đang chạy bản vừa nạp chưa? Bạn đọc log từ cổng nối tiếp xem có gì "
                      "không, rồi nói cho mình biết bạn KẾT LUẬN được gì và chưa kết luận "
                      "được gì.",
                      giay=600)
        a = ctx.store.get("target:log")
        c = (a or {}).get("canonical") or {}
        nk.ghi("Log đọc được",
               f"{c.get('so_byte', 0)} byte từ {c.get('cong')} · im lặng={c.get('im_lang')}\n"
               + str(c.get("chu") or "")[:1500])
        if c.get("im_lang"):
            nk.ket(True,
                   "Cổng im lặng — và hệ thống nói đúng rằng điều đó KHÔNG chứng minh "
                   "firmware sai",
                   " ".join(c.get("canh_bao") or []))
        else:
            nk.ket(bool(c.get("so_byte")), "Bo có in ra chữ trên cổng nối tiếp",
                   str(c.get("chu") or "")[:300])
        # Phần chỉ mắt người thấy được. Không tự kết luận.
        nk.ghi("CẦN ANH CÔNG XÁC NHẬN (tầng NGƯỜI)",
               "Đèn LED trên bo có đang nhấp nháy không? Đây là phần duy nhất của bài này mà "
               "không đo được bằng mã — kịch bản cố ý không tự trả lời.")
        nk.anh(g, "chay-that")

    # ------------------------------------------- 11. ứng dụng NGƯỜI DÙNG TEST ĐƯỢC
    if lam(11):
        nk.buoc("Ứng dụng người dùng bấm được và thấy được: 4 đèn + nút bấm")
        loi, cc = hoi(g, nk, du_an,
                      "Bây giờ mình muốn một ứng dụng mà mình TỰ KIỂM ĐƯỢC bằng tay, chứ "
                      "không phải chỉ nháy một đèn rồi tin lời bạn. Bạn viết lại firmware "
                      "cho mình như sau:\n"
                      "- Dùng CẢ BỐN đèn LED người dùng của bo, không chỉ một.\n"
                      "- Có phản ứng với NÚT BẤM trên bo: mình bấm thì hành vi phải đổi rõ "
                      "rệt, nhìn là biết ngay.\n"
                      "- Chân của cả bốn đèn và của nút phải lấy từ Fact có trích dẫn, không "
                      "lấy từ trí nhớ. Chưa có Fact thì trích ra trước đã.\n"
                      "- Mức tích cực của nút (bấm là mức cao hay mức thấp) cũng phải đọc từ "
                      "tài liệu — đoán sai thì mình bấm mà không thấy gì, hoặc nó tự chạy "
                      "như đang bị bấm.\n"
                      "Viết xong thì biên dịch, nạp, rồi VIẾT CHO MÌNH CÁCH KIỂM: mình phải "
                      "làm gì và phải thấy gì, từng bước một.",
                      giay=2400)
        ten = [c["tool"] for c in cc]
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(ten) or "—")
        _kiem_ung_dung_test_duoc(nk, ctx, du_an)
        nk.anh(g, "ung-dung-test-duoc")

    # ------------------------------------------- 12. logo PTIT: tìm và đổi sang mảng C
    #
    # Ba lượt chứ không một. Lần đầu tôi giao cả việc trong một câu và tác tử tiêu hết ngân
    # sách 40 lời gọi vào việc đọc lại lịch sử của chính nó mà không làm được gì — việc quá
    # lớn cho một lượt thì chia ra là việc của NGƯỜI GIAO, không phải lỗi của người làm.
    if lam(12):
        nk.buoc("Tìm logo PTIT, tải về, và đổi sang mảng C cho chip vẽ được")
        loi, cc = hoi(g, nk, du_an,
                      "Việc mới, mình chia nhỏ ra. Bước một: bo này có màn hình cảm ứng "
                      "800×480 gắn sẵn, và mình muốn hiện logo trường mình lên đó. Bạn tìm "
                      "giúp mình logo của Học viện Công nghệ Bưu chính Viễn thông (PTIT), "
                      "tải về dự án, rồi đổi sang dạng mà chip vẽ thẳng lên màn được — chip "
                      "không đọc được PNG. Logo để khoảng 240×240 điểm ảnh là vừa. Nói cho "
                      "mình biết bạn lấy logo từ nguồn nào và nó ở tầng tin cậy nào.",
                      giay=1200)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_logo(nk, ctx, du_an, cc)
        nk.anh(g, "logo-tim-va-doi")

    # ------------------------------------------- 13. lấy driver màn hình của ST
    if lam(13):
        nk.buoc("Lấy driver màn hình DSI của ST về dự án")
        loi, cc = hoi(g, nk, du_an,
                      "Bước hai: màn này nối qua MIPI DSI nên cần driver của hãng. Bạn lấy "
                      "về dự án những thứ cần để vẽ được lên nó — theo mình hiểu là LTDC, "
                      "DSI, driver panel OTM8009A, và SDRAM ngoài làm bộ đệm khung, cộng HAL "
                      "và CMSIS của STM32F4. Tất cả nằm trên GitHub của ST. Lấy xong thì nói "
                      "cho mình biết đã thêm bao nhiêu tệp, từ repo nào, và có tệp nào hỏng "
                      "không.\n"
                      "LƯU Ý: lần trước bạn đoán đường dẫn theo bố cục quen thuộc của "
                      "STM32CubeF4 và 44/49 tệp trả 404 — ST đã tách HAL, CMSIS device, BSP "
                      "và driver panel thành các repo RIÊNG. Nên hãy NHÌN xem repo có gì "
                      "trước khi xin tệp.",
                      giay=2400)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_driver(nk, du_an, cc)
        nk.anh(g, "driver-man-hinh")

    # ------------------------------------------- 14. viết, biên dịch, nạp
    if lam(14):
        nk.buoc("Viết chương trình hiện logo + thông tin, biên dịch và nạp lên bo")
        loi, cc = hoi(g, nk, du_an,
                      "Bước ba: viết chương trình hiện lên màn:\n"
                      "- Logo PTIT vừa đổi.\n"
                      "- EIDE v3 — IDE nhúng có tác tử đồng tác giả\n"
                      "- Học viên: Vũ Trí Công\n"
                      "- Giảng viên hướng dẫn: TS. Nguyễn Trung Hiếu\n\n"
                      "Rồi biên dịch, sửa lỗi cho tới khi xong, và nạp lên bo.\n"
                      "LƯU Ý MÁY NÀY: `arm-none-eabi-gcc` KHÔNG kèm newlib, và bản cài newlib "
                      "cần quyền sudo nên bạn không cài được — nghĩa là không có memset/"
                      "memcpy/printf. Bạn tự viết những hàm tối thiểu đó nếu cần.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        _kiem_man_hinh(nk, ctx, du_an, cc)
        nk.anh(g, "logo-ptit")

    # ------------------------------------------- 15. sửa tiếp cho tới khi dịch và nạp được
    #
    # Một lượt riêng, chạy lại được nhiều lần. Biên dịch 30 tệp của hãng lần đầu ra 51 lỗi là
    # chuyện thường của nghề — cái đáng đo không phải "lần đầu có sạch không" mà là "mỗi vòng
    # có bớt lỗi đi không".
    if lam(15):
        nk.buoc("Sửa tiếp lỗi biên dịch cho tới khi dịch được và nạp lên bo")
        truoc = _so_loi_dich(ctx)
        loi, cc = hoi(g, nk, du_an,
                      "Vẫn chưa dịch được. Bạn xem lỗi rồi sửa tiếp nhé — thiếu tệp nào của "
                      "hãng thì lấy thêm, thiếu hàm nào thì viết. Dịch xong thì nạp luôn lên "
                      "bo cho mình.",
                      giay=3600)
        nk.ghi("Chuỗi công cụ tác tử đã đi", " → ".join(c["tool"] for c in cc) or "—")
        sau = _so_loi_dich(ctx)
        nk.ghi("Số lỗi biên dịch", f"trước lượt này: {truoc} → sau: {sau}")
        nk.ket(sau < truoc or sau == 0,
               f"Mỗi vòng phải bớt lỗi: {truoc} → {sau}",
               "không bớt thì tác tử đang sửa vòng quanh" if sau >= truoc and sau else "")
        _kiem_man_hinh(nk, ctx, du_an, cc)
        nk.anh(g, "sua-tiep")

    nk.ghi("Kết thúc phiên", f"nhật ký: {nk.md} · ảnh: {nk.ra / 'anh'}")
    return 0


# ==================================================================== đối chiếu bằng mã
def _bao_cao_fact(nk: Any, ctx: Any, fs: list[dict[str, Any]]) -> None:
    """Fact nào có trích dẫn, và trích dẫn đó có trỏ vào tài liệu THẬT không.

    Đây là phép kiểm quan trọng nhất của bước trích xuất, và nó không kiểm "tác tử nói đúng
    chân LED" — nó kiểm **mỗi Fact trỏ được về một chỗ đọc lại được**. Một con số đúng mà
    không có nguồn thì lần sau không ai kiểm được, và một con số sai có nguồn thì ai cũng
    thấy sai.
    """
    theo_chu_de: dict[str, list[dict[str, Any]]] = {}
    for f in fs:
        theo_chu_de.setdefault(str(f.get("subject", "")), []).append(f)
    dong = []
    for chu_de in sorted(theo_chu_de):
        for f in theo_chu_de[chu_de]:
            ng = f.get("source")
            if isinstance(ng, str):
                try:
                    ng = json.loads(ng)
                except ValueError:
                    ng = {"cite": ng}
            ng = ng or {}
            dong.append(f"{chu_de:34} {str(f.get('key')):10} = {str(f.get('value'))[:26]:26} "
                        f"[{f.get('tier')}] {ng.get('doc_id', '?')} · "
                        f"{ng.get('cite', 'KHÔNG CÓ TRÍCH DẪN')}")
    nk.ghi("Fact đã trích (kèm trích dẫn)", "\n".join(dong) or "— chưa có Fact nào —", ma=True)

    co_dan = [f for f in fs if _co_trich_dan(f)]
    nk.ket(bool(fs) and len(co_dan) == len(fs),
           f"Mọi Fact đều có trích dẫn: {len(co_dan)}/{len(fs)}",
           "; ".join(f"{f.get('subject')}.{f.get('key')}" for f in fs
                     if not _co_trich_dan(f))[:400] or "—")

    # Trích dẫn trỏ tới tài liệu nào — tài liệu đó có trong kho không?
    doc_theo_id = {d["id"]: d for d in ctx.store.list("doc", limit=50)}
    hong = []
    for f in fs:
        ng = _nguon(f)
        did = str(ng.get("doc_id") or "")
        if did and did not in doc_theo_id:
            hong.append(f"{f.get('subject')}.{f.get('key')} → {did}")
    nk.ket(not hong, "Mọi trích dẫn trỏ tới một tài liệu CÓ THẬT trong kho",
           "; ".join(hong)[:400] or "—")
    _kiem_trich_dan_mo_ra_thay(nk, fs, doc_theo_id)


def _kiem_trich_dan_mo_ra_thay(nk: Any, fs: list[dict[str, Any]],
                               doc_theo_id: dict[str, Any]) -> None:
    """Mở ĐÚNG tệp ở ĐÚNG đơn vị được trích dẫn, và xem giá trị có nằm ở đó thật không.

    Đây là phép kiểm độc lập với lõi, và nó phải độc lập: `fact.from_doc` có kiểm nguyên văn
    (E2006), nhưng một bộ đo tin vào chính thứ nó đang đo thì không đo gì cả. Ở đây ta đọc
    thẳng tệp trên đĩa, cắt đúng khoảng dòng của trích dẫn, rồi tìm giá trị trong đó.
    """
    import pathlib as _pl
    import re as _re

    xet, dung, sai = 0, [], []
    for f in fs:
        ng = _nguon(f)
        did, cite = str(ng.get("doc_id") or ""), str(ng.get("cite") or "")
        a = doc_theo_id.get(did)
        if not a or not cite:
            continue
        canon = a.get("canonical") or {}
        p = _pl.Path(str(canon.get("path") or ""))
        m = _re.match(r"dòng (\d+)(?:–(\d+))?", cite)
        if not p.exists() or not m:
            continue                      # chỉ kiểm được tài liệu văn bản có trích dẫn dòng
        xet += 1
        dau = int(m.group(1))
        cuoi = int(m.group(2) or m.group(1))
        khuc = "\n".join(p.read_text("utf-8", errors="replace").splitlines()[dau - 1:cuoi])
        gt = str(f.get("value") or "").strip()
        # So lỏng: tài liệu viết `((uint32_t)GPIO_PIN_6)` còn Fact ghi `GPIO_PIN_6` hoặc `PG6`.
        gon = _re.sub(r"[^A-Za-z0-9]", "", gt).upper()
        khuc_gon = _re.sub(r"[^A-Za-z0-9]", "", khuc).upper()
        (dung if (gon and gon in khuc_gon) else sai).append(
            f"{f.get('subject')}.{f.get('key')}={gt} @ {cite}")
    nk.ket(xet > 0 and not sai,
           f"Mở đúng dòng được trích dẫn thì THẤY giá trị: {len(dung)}/{xet} Fact kiểm được",
           ("KHÔNG THẤY: " + "; ".join(sai[:8]) if sai else
            "; ".join(dung[:6]) if dung else
            "Không Fact nào có trích dẫn theo dòng để kiểm — tài liệu nạp được có thể là PDF, "
            "khi đó phép kiểm này không áp dụng."))


def _nguon(f: dict[str, Any]) -> dict[str, Any]:
    ng = f.get("source")
    if isinstance(ng, str):
        try:
            return json.loads(ng)
        except ValueError:
            return {"cite": ng}
    return ng or {}


def _co_trich_dan(f: dict[str, Any]) -> bool:
    ng = _nguon(f)
    return bool(ng.get("cite") or ng.get("page") or ng.get("doc_id"))


def _kiem_hang_so_co_nguon(nk: Any, ctx: Any, fw: pathlib.Path) -> None:
    """Hằng số chân/thanh ghi trong mã có khớp Fact trong kho không.

    Không kiểm "mã có đẹp không" — kiểm đúng một thứ: **số trong mã có mặt trong kho Fact**.
    N1 nói datasheet là chân lý; một hằng số trong firmware mà không có Fact nào đứng sau là
    một con số ai đó nhớ ra.
    """
    if not fw.is_dir():
        nk.ket(False, "Không có thư mục firmware/ để đối chiếu hằng số", "")
        return
    chu = "\n".join(p.read_text("utf-8", errors="replace")
                    for p in sorted(fw.rglob("*")) if p.is_file() and p.suffix
                    in (".c", ".h", ".s", ".S", ".ld"))
    gt_fact = {str(f.get("value")).strip().upper()
               for f in ctx.store.query_facts(limit=800)}
    # Chân kiểu PG6/PD4/PK3 xuất hiện trong mã (hoặc trong chú thích) — có Fact nào nói thế?
    chan_trong_ma = sorted(set(re.findall(r"\bP[A-K]\d{1,2}\b", chu)))
    khop = [c for c in chan_trong_ma if c.upper() in gt_fact
            or any(c.upper() in v for v in gt_fact)]
    nk.ghi("Chân xuất hiện trong mã", ", ".join(chan_trong_ma) or "— không có —")
    nk.ket(bool(chan_trong_ma) and len(khop) == len(chan_trong_ma),
           f"Mọi chân trong mã đều có Fact đứng sau: {len(khop)}/{len(chan_trong_ma)}",
           "KHÔNG CÓ FACT: " + ", ".join(c for c in chan_trong_ma if c not in khop)
           if len(khop) != len(chan_trong_ma) else "—")


def _kiem_vector_table(nk: Any, du_an: pathlib.Path, binp: pathlib.Path) -> None:
    """Hai từ đầu của ảnh nạp là hợp đồng với phần cứng Cortex-M — kiểm được bằng byte.

    Từ 0 là giá trị nạp vào con trỏ ngăn xếp, từ 1 là địa chỉ Reset_Handler và **phải có bit 0
    bằng 1** (chế độ Thumb). Thiếu bit đó thì chip hard-fault ngay lệnh đầu tiên: firmware nạp
    xong, không chạy, và không có thông báo lỗi nào ở đâu cả.
    """
    b = binp.read_bytes()
    if len(b) < 8:
        nk.ket(False, "Ảnh nạp ngắn hơn 8 byte — không có vector table", f"{len(b)} byte")
        return
    sp = int.from_bytes(b[0:4], "little")
    reset = int.from_bytes(b[4:8], "little")
    ld = sorted((du_an / "firmware").rglob("*.ld"))
    khai = ld[0].read_text("utf-8", errors="replace") if ld else ""
    nk.ghi("Vector table trong .bin",
           f"SP = 0x{sp:08X} · Reset_Handler = 0x{reset:08X} (bit Thumb = {reset & 1})")
    nk.ket(0x08000000 <= reset < 0x08200000,
           "Reset_Handler nằm trong vùng Flash của chip (0x0800_0000…)",
           f"0x{reset:08X}")
    nk.ket(bool(reset & 1),
           "Reset_Handler có bit Thumb — thiếu bit này là chip hard-fault ngay lệnh đầu",
           f"0x{reset:08X}")
    nk.ket(0x20000000 <= sp <= 0x20100000 or 0x10000000 <= sp <= 0x10010000,
           "Con trỏ ngăn xếp trỏ vào vùng RAM",
           f"0x{sp:08X}"
           + (f" · linker script khai: "
              + "; ".join(x.strip() for x in re.findall(r"^\s*RAM.*$", khai, re.M)[:2])
              if khai else ""))


def _kiem_ung_dung_test_duoc(nk: Any, ctx: Any, du_an: pathlib.Path) -> None:
    """Ứng dụng này có THẬT SỰ kiểm được bằng tay không, và mỗi chân có Fact đứng sau không.

    Phép kiểm ở đây cố ý KHÔNG hỏi "firmware có đúng không" — không đo được. Nó hỏi ba câu
    hẹp hơn mà đo được, và mỗi câu chặn một cách hỏng đã gặp thật:

      1. Bốn chân LED và một chân nút có mặt trong mã?  (nếu không thì "dùng cả bốn đèn"
         chỉ là lời hứa)
      2. Mỗi chân ấy có Fact trong kho, và Fact có trích dẫn?  (N1 — số nhớ được thì lần
         sau không ai kiểm lại được)
      3. Ảnh nạp trên chip có ĐÚNG là bản vừa dịch không?  (đọc ngược Flash, không tin lời
         trình nạp)
    """
    import json as _json

    fw = du_an / "firmware"
    ma = "\n".join(p.read_text("utf-8", errors="replace")
                   for p in sorted(fw.rglob("*"))
                   if p.is_file() and p.suffix in (".c", ".h", ".s", ".S")) if fw.is_dir() else ""

    # --- 1. chân trong mã
    trong_ma, vi_sao_doc = _chan_trong_firmware(ma)
    nk.ghi("Chân đọc được từ firmware",
           (", ".join(sorted(trong_ma)) or "—") + "\n" + vi_sao_doc)

    # --- 2. Fact chân trong kho
    # Tìm Fact chân theo NỘI DUNG, không theo hình dạng khoá.
    #
    # Bản trước chỉ nhận `subject="pin:<chip>.<tên>"` + `key="ten"` — đúng hình dạng mà
    # `fact.extract_pinout` sinh ra. Tác tử lại dùng `fact.from_doc` và đặt khoá theo cách của
    # nó (`chip:STM32F469NI` / `led1.pin` = `PG6`), nên bộ đo báo **0/4 Fact** trong khi kho có
    # đủ cả bốn, có trích dẫn đàng hoàng. Một bộ đo chỉ nhận đúng một cách làm sẽ báo sai mỗi
    # lần tác tử làm đúng bằng cách khác.
    fs = ctx.store.query_facts(limit=800)
    chan_fact: dict[str, tuple[str, str]] = {}
    for f in fs:
        khoa = str(f.get("key") or "")
        gt = str(f.get("value") or "").strip()
        ten = (str(f.get("subject", "")).split(".", 1)[-1]
               if str(f.get("subject", "")).startswith("pin:") else khoa)
        ng = _nguon(f)
        if re.fullmatch(r"P[A-K]\d{1,2}", gt):               # `PG6`
            chan_fact[ten] = (gt, str(ng.get("cite") or ""))
        elif re.fullmatch(r"GPIO_PIN_\d{1,2}", gt):          # `GPIO_PIN_0` + cổng ở Fact khác
            goc = khoa.rsplit(".", 1)[0]
            cong = next((str(x.get("value")) for x in fs
                         if str(x.get("key") or "").startswith(goc)
                         and re.fullmatch(r"GPIO[A-K]", str(x.get("value") or ""))), "")
            if cong:
                chan_fact[ten] = (f"P{cong[-1]}{gt.rsplit('_', 1)[-1]}",
                                  str(ng.get("cite") or ""))
    nk.ghi("Fact chân trong kho",
           "\n".join(f"  {k:22} {v[0]:6} {v[1]}" for k, v in sorted(chan_fact.items()))
           or "— chưa có Fact chân nào —", ma=True)

    led = {k: v for k, v in chan_fact.items() if k.upper().startswith("LED")}
    nut = {k: v for k, v in chan_fact.items()
           if "BUTTON" in k.upper() or "WAKEUP" in k.upper() or "KEY" in k.upper()}
    nk.ket(len(led) >= 4, f"Có Fact cho đủ 4 đèn LED: {len(led)}/4",
           ", ".join(f"{k}={v[0]}" for k, v in sorted(led.items())) or "—")
    nk.ket(bool(nut), "Có Fact cho nút bấm",
           ", ".join(f"{k}={v[0]}" for k, v in sorted(nut.items())) or "—")

    # Chân nào trong Fact mà mã KHÔNG dùng, và ngược lại.
    can_dung = {v[0] for v in list(led.values()) + list(nut.values())}
    thieu = sorted(x for x in can_dung if x not in trong_ma)
    nk.ket(bool(can_dung) and not thieu,
           f"Mọi chân cần dùng đều xuất hiện trong mã: {len(can_dung) - len(thieu)}"
           f"/{len(can_dung)}",
           ("THIẾU TRONG MÃ: " + ", ".join(thieu)) if thieu else
           ", ".join(sorted(can_dung)) or "—")

    # --- 3. chip có đúng bản vừa dịch không
    _kiem_chip_dung_ban_vua_dich(nk, du_an)


def _kiem_chip_dung_ban_vua_dich(nk: Any, du_an: pathlib.Path) -> None:
    """Đọc ngược Flash từ chip rồi so byte với `.bin`. Không tin lời trình nạp.

    `st-flash write` tự nói "verified", nhưng đó là lời của chính công cụ vừa ghi. Một phép
    đo độc lập đọc lại từ silicon trả lời đúng câu người dùng hỏi: *con chip trên bàn đang
    chứa bản nào?*
    """
    import hashlib
    import shutil as _sh
    import subprocess as _sp
    import tempfile as _tf

    binp = du_an / ".eide" / "build" / "mach.bin"
    st = _sh.which("st-flash")
    if not binp.exists() or not st:
        nk.ket(False, "Đọc ngược Flash từ chip để đối chiếu",
               "chưa có mach.bin" if not binp.exists() else "máy chưa có st-flash")
        return
    mong = binp.read_bytes()
    ra = pathlib.Path(_tf.mkdtemp()) / "doc-lai.bin"
    r = _sp.run([st, "read", str(ra), "0x08000000", str(len(mong))],
                capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not ra.exists():
        nk.ket(False, "Đọc ngược Flash từ chip để đối chiếu",
               (r.stderr or r.stdout or "")[-300:])
        return
    that = ra.read_bytes()
    khop = that == mong
    nk.ket(khop, f"Chip đang chứa ĐÚNG bản vừa dịch ({len(mong)} byte)",
           f"sha256 tệp  : {hashlib.sha256(mong).hexdigest()[:32]}\n"
           f"sha256 chip : {hashlib.sha256(that).hexdigest()[:32]}"
           + ("" if khop else
              f"\nkhác ở {sum(1 for a, b in zip(mong, that) if a != b)} byte"))


def _chan_trong_firmware(ma: str) -> tuple[set[str], str]:
    """Chân GPIO mà firmware THẬT SỰ chạm tới. Trả `(tập chân, giải thích cách đọc)`.

    Bản trước lấy tích Descartes của {cổng thấy được} × {số thấy sau `<<`} và gọi đó là "chân
    trong mã". Hai chỗ sai, và cả hai đều cho ra kết luận tự tin mà sai:

    - Các số nó bắt được là **0, 3, 6, 10** — đó là bit bật xung nhịp trong `RCC_AHB1ENR`
      (GPIOAEN=0, GPIODEN=3, GPIOGEN=6, GPIOKEN=10), không phải số chân.
    - Firmware viết `1UL << LED2_PIN`, tức **tên macro** chứ không phải chữ số, nên PD4 và PD5
      trượt hoàn toàn và bộ đo báo "thiếu trong mã" cho những chân đang được dùng đúng.

    Cách làm đúng: giải bảng `#define` của chính firmware thành số, rồi ghép cổng với bit
    **trên cùng một dòng** — `GPIOD_BSRR = ... (1UL << LED2_PIN)` cho ra PD4. Bỏ qua dòng
    chạm `RCC_`, vì bit ở đó thuộc về xung nhịp chứ không thuộc về chân.
    """
    gia_tri: dict[str, int] = {}
    for m in re.finditer(r"^\s*#\s*define\s+(\w+)\s+\(?\s*(\d{1,3})\s*[uUlL]*\s*\)?\s*(?:/\*.*)?$",
                         ma, re.M):
        gia_tri[m.group(1)] = int(m.group(2))

    ra: set[str] = set()
    for dong in ma.splitlines():
        if "RCC_" in dong:                    # bit ở đây là xung nhịp, không phải chân
            continue
        # `\b` sau [A-K] KHÔNG khớp `GPIOG_BSRR` vì `_` cũng là ký tự từ — đó là lý do
        # bản trước đọc được 0 chân. `(?![A-Z])` để `GPIOAEN` (bit RCC) không
        # bị đọc thành cổng A.
        cong = set(re.findall(r"\bGPIO([A-K])(?![A-Z])", dong))
        if len(cong) != 1:
            continue
        c = cong.pop()
        for tok in re.findall(r"<<\s*\(?\s*(\w+)", dong):
            n = int(tok) if tok.isdigit() else gia_tri.get(tok, -1)
            if 0 <= n <= 15:                  # chân GPIO của STM32 chỉ từ 0..15
                ra.add(f"P{c}{n}")
        # `GPIOA_IDR & (1UL << BUTTON_PIN)` đã bắt ở trên; còn dạng `MODER &= ~(3UL << (X*2))`
        for tok in re.findall(r"\(\s*(\w+)\s*\*\s*2\s*\)", dong):
            n = int(tok) if tok.isdigit() else gia_tri.get(tok, -1)
            if 0 <= n <= 15:
                ra.add(f"P{c}{n}")

    vi_sao = (f"đọc {len(gia_tri)} #define thành số, ghép cổng với bit trên cùng dòng, "
              "bỏ qua dòng có RCC_ (bit xung nhịp không phải số chân)")
    if not gia_tri and not ra:
        vi_sao = ("KHÔNG đọc được mẫu nào — firmware có thể dùng cách viết khác. "
                  "Không đọc được KHÁC với không dùng.")
    return ra, vi_sao


def _kiem_man_hinh(nk: Any, ctx: Any, du_an: pathlib.Path, cc: list[dict]) -> None:
    """Phần hiển thị: có ảnh thật, có driver thật, có bốn dòng chữ, và có nạp được không.

    Phép kiểm ở đây KHÔNG thể trả lời "màn có hiện đúng không" — chỉ mắt anh Công thấy được.
    Nó trả lời bốn câu hẹp hơn mà đo được, và mỗi câu chặn một cách hỏng riêng:

      1. Logo có phải ẢNH THẬT tải về không, hay là một mảng ai đó gõ ra?
      2. Driver màn hình có phải mã của hãng không, hay là mã tự nghĩ?
      3. Bốn thông tin bắt buộc có mặt trong mã không?
      4. Bản trên chip có đúng bản vừa dịch không?
    """
    fw = du_an / "firmware"
    tep = sorted(p.name for p in fw.rglob("*") if p.is_file()) if fw.is_dir() else []
    nk.ghi(f"Tệp trong firmware/ ({len(tep)})", ", ".join(tep) or "—")

    # 1. logo: có ảnh nguồn và có mảng sinh ra từ nó
    anh = [p for p in (du_an).rglob("*")
           if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp")
           and ".eide" not in p.parts]
    da_doi = [c for c in cc if c["tool"] == "asset.image_to_c" and c["ok"]]
    nk.ghi("Ảnh tải về trong dự án",
           "\n".join(f"  {p.relative_to(du_an)} · {p.stat().st_size} byte" for p in anh)
           or "— không có ảnh nào —", ma=True)
    nk.ket(bool(anh), "Có tệp ẢNH THẬT trong dự án (không phải mảng gõ tay)",
           f"{len(anh)} ảnh")
    nk.ket(bool(da_doi), "Mảng điểm ảnh sinh ra BẰNG CÔNG CỤ từ ảnh đó",
           "; ".join(json.dumps(c["args"], ensure_ascii=False)[:100] for c in da_doi) or "—")

    # 2. driver của hãng, không phải mã tự nghĩ
    lay = [c for c in cc if c["tool"] == "code.vendor_fetch"]
    nk.ghi("Lấy mã hãng",
           "\n".join(f"  {c['args'].get('repo')} · "
                     f"{len(c['args'].get('tep') or [])} tệp · "
                     + ("ok" if c["ok"] else f"LỖI {c['loi']}") for c in lay) or "—",
           ma=True)
    chu = "\n".join(p.read_text("utf-8", errors="replace")
                    for p in sorted(fw.rglob("*"))
                    if p.is_file() and p.suffix in (".c", ".h")) if fw.is_dir() else ""
    for can in ("LTDC", "DSI", "OTM8009A", "SDRAM"):
        nk.ket(can.lower() in chu.lower(), f"Mã có nhắc tới {can}", "")

    # 3. bốn thông tin bắt buộc
    phai_co = {"PTIT": ("PTIT", "Bưu chính"), "EIDE v3": ("EIDE",),
               "Vũ Trí Công": ("Vũ Trí Công", "Vu Tri Cong"),
               "TS. Nguyễn Trung Hiếu": ("Nguyễn Trung Hiếu", "Nguyen Trung Hieu")}
    thieu = [k for k, v in phai_co.items() if not any(x in chu for x in v)]
    nk.ket(not thieu, f"Bốn thông tin bắt buộc có trong mã: {4 - len(thieu)}/4",
           ("THIẾU: " + ", ".join(thieu)) if thieu else ", ".join(phai_co))

    # 4. chip đang chạy bản nào
    _kiem_chip_dung_ban_vua_dich(nk, du_an)

    nk.ghi("CẦN ANH CÔNG XÁC NHẬN (tầng NGƯỜI)",
           "Màn hình trên bo có hiện logo PTIT và bốn dòng thông tin không? Đây là phần duy "
           "nhất của bước này không đo được bằng mã.")


def _kiem_logo(nk: Any, ctx: Any, du_an: pathlib.Path, cc: list[dict]) -> None:
    """Logo có phải ẢNH THẬT tải về, và mảng có sinh ra BẰNG CÔNG CỤ từ chính ảnh đó không."""
    anh = [p for p in du_an.rglob("*")
           if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp",
                                                   ".svg", ".webp")
           and ".eide" not in p.parts]
    nk.ghi("Ảnh trong dự án",
           "\n".join(f"  {p.relative_to(du_an)} · {p.stat().st_size} byte" for p in anh)
           or "— không có —", ma=True)
    nk.ket(bool(anh), "Có tệp ẢNH THẬT trong dự án (không phải mảng gõ tay)", f"{len(anh)} ảnh")

    tim = [c for c in cc if c["tool"] == "doc.search_web"]
    nk.ghi("Tác tử tìm bằng gì",
           "\n".join(f"  {json.dumps(c['args'], ensure_ascii=False)[:110]} → "
                     + ("ok" if c["ok"] else f"LỖI {c['loi']}") for c in tim) or "—", ma=True)

    doi = [c for c in cc if c["tool"] == "asset.image_to_c"]
    nk.ket(bool(doi) and any(c["ok"] for c in doi),
           "Mảng điểm ảnh sinh ra BẰNG CÔNG CỤ từ ảnh đó",
           "; ".join(json.dumps(c["args"], ensure_ascii=False)[:110] for c in doi) or "—")

    # Mảng sinh ra phải khớp ảnh: đọc lại .h và so với kích thước ảnh thật.
    hs = sorted(p for p in (du_an / "firmware").glob("*.h")) if (du_an / "firmware").is_dir() \
        else []
    khop = []
    for h in hs:
        chu = h.read_text("utf-8", errors="replace")
        m_w = re.search(r"#define\s+\w+_WIDTH\s+(\d+)", chu)
        m_h = re.search(r"#define\s+\w+_HEIGHT\s+(\d+)", chu)
        if m_w and m_h:
            khop.append(f"{h.name}: {m_w.group(1)}×{m_h.group(1)}")
    nk.ket(bool(khop), "Có header khai kích thước mảng điểm ảnh", "; ".join(khop) or "—")


def _kiem_driver(nk: Any, du_an: pathlib.Path, cc: list[dict]) -> None:
    """Driver màn hình có phải mã CỦA HÃNG lấy về không, và có tệp nào hỏng không."""
    lay = [c for c in cc if c["tool"] == "code.vendor_fetch"]
    nk.ghi("Lấy mã hãng",
           "\n".join(f"  {c['args'].get('repo')}@{c['args'].get('nhanh','main')} · "
                     f"{len(c['args'].get('tep') or [])} tệp · "
                     + ("ok" if c["ok"] else f"LỖI {c['loi']}") for c in lay) or "—", ma=True)
    nk.ket(bool(lay), "Tác tử đã dùng code.vendor_fetch (mã của hãng, không tự nghĩ)",
           f"{len(lay)} lượt")

    fw = du_an / "firmware"
    tep = sorted(p.name for p in fw.rglob("*") if p.is_file()) if fw.is_dir() else []
    nk.ghi(f"Tệp trong firmware/ ({len(tep)})", ", ".join(tep[:60])
           + (f" … và {len(tep) - 60} tệp nữa" if len(tep) > 60 else ""))
    chu = "\n".join(p.read_text("utf-8", errors="replace")
                    for p in sorted(fw.rglob("*"))
                    if p.is_file() and p.suffix in (".c", ".h")) if fw.is_dir() else ""
    for can in ("LTDC", "DSI", "OTM8009A", "SDRAM"):
        nk.ket(can.lower() in chu.lower(), f"Mã có phần {can}", "")


def _so_loi_dich(ctx: Any) -> int:
    """Số lỗi của lần biên dịch gần nhất. -1 nếu chưa dịch lần nào."""
    a = ctx.store.get("build:firmware")
    c = (a or {}).get("canonical") or {}
    if not a:
        return -1
    return 0 if c.get("dat") else int(c.get("so_loi") or 0)
