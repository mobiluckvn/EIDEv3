# -*- coding: utf-8 -*-
"""Phân tích tĩnh chiều sâu — M2-09. Đồ thị gọi hàm, ngăn xếp, luật ngữ cảnh ngắt.

## Vì sao tệp này phải tồn tại

`phan_tich_ma.py` nói thẳng trong docstring của chính nó: *"Không phân tích ngữ nghĩa, không
dựng đồ thị gọi hàm đúng nghĩa"*. Và chuỗi biên dịch có `-Wall -Wextra` mà **không** có
`-fstack-usage` hay `-fcallgraph-info`. Nên ba câu hỏi mà một người làm nhúng hỏi đầu tiên đều
không ai trả lời:

* *"ngăn xếp sâu nhất bao nhiêu byte"* — RAM của ATmega328P là 2 048 byte, và tràn ngăn xếp
  **không có lỗi nào kêu lên**: nó ghi lên biến toàn cục rồi chương trình sai ở một chỗ khác;
* *"hàm nào gọi hàm nào"*;
* *"trong hàm ngắt có phép chia, `printf`, hay `_delay_ms` không"* — ba thứ làm một ISR 50 kHz
  trượt deadline, và cả ba **biên dịch sạch**.

## Bốn chỗ trình biên dịch thật khác nhau, đo được 09/10/2026

Kế hoạch nêu một định dạng. Đo thật thì có bốn chỗ lệch, và mỗi chỗ làm phép đọc trượt im lặng:

1. **`.su` có hai dạng.** `arm-none-eabi-gcc 16.2.0` ghi `tep.c:DÒNG:CỘT:ham`, Apple clang ghi
   `tep.c:DÒNG:ham` — **thiếu cột**. Đọc một dạng thôi thì công cụ không chạy nổi trên máy chủ,
   mà máy chủ là nơi `test.run` dịch mọi thứ.
2. **clang KHÔNG có `-fcallgraph-info`** (`unknown argument`). Nên trên máy chủ không dựng được
   đồ thị gọi hàm — và điều đó phải được **nói ra**, không trả một đồ thị rỗng.
3. **Tên nút trong `.ci` không nhất quán**: hàm `static` thành `"m2.c:loc"` (có tiền tố tệp),
   hàm `extern` thành `"tinh"` (trần). Không chuẩn hoá thì đồ thị rời ra từng mảnh, im lặng.
4. **Chỗ đặt tệp `.su` khác nhau**: GCC đặt theo tên **nguồn**, clang theo tên **đầu ra**.

## Một nguyên tắc chạy suốt tệp này

Con số ngăn xếp là một **chặn trên** chỉ khi mọi hàm trong chuỗi gọi đều đo được. Gặp một hàm
thư viện (`__aeabi_idiv`, `memcpy`) không có trong `.su` thì con số thành một **chặn dưới**, và
nó phải tự khai như thế. Im lặng coi hàm không đo được bằng 0 là biến một chặn dưới thành một
trần — đúng kiểu ô xanh giả mà cả dự án này đi vá: một con số hợp lý, sai, không gì kêu lên.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# `.su`: `tep.c:DÒNG[:CỘT]:ten\tBYTE\tKIỂU`. Cột là tuỳ chọn — đó là chỗ clang khác GCC.
_RE_SU = re.compile(r"^(?P<tep>[^:]+):(?P<dong>\d+)(?::(?P<cot>\d+))?:(?P<ten>[^\t:]+)\t"
                    r"(?P<byte>\d+)\t(?P<kieu>\S+)\s*$")

# `.ci` (VCG): các cung. `label` là tuỳ chọn — cung tới hàm built-in không có.
_RE_EDGE = re.compile(r'edge:\s*\{\s*sourcename:\s*"(?P<tu>[^"]+)"\s+'
                      r'targetname:\s*"(?P<den>[^"]+)"')

# Hàm CHẶN hoặc quá nặng cho ngữ cảnh ngắt. `printf` kéo cả bộ định dạng vào ISR; `malloc`
# dùng heap mà `main` cũng đang dùng (không reentrant); `_delay_*` chặn hẳn CPU.
_HAM_CHAN = ("_delay_ms", "_delay_us", "printf", "sprintf", "snprintf", "puts",
             "malloc", "calloc", "realloc", "free", "HAL_Delay", "vTaskDelay", "sleep",
             "usleep", "scanf", "fopen", "fprintf")

# Hai lối khai hàm ngắt, và firmware trong repo này dùng CẢ HAI:
#
# * AVR: macro `ISR(TIMER2_COMPA_vect)` — `du-lieu/robot-sinhvien2/firmware/timer.c`;
# * ARM/CMSIS: một hàm thường tên `*_Handler` hoặc `*_IRQHandler` —
#   `docs/rtos-tu-viet/firmware-chay-duoc/startup.c`.
#
# Bắt một lối thôi thì công cụ **mù hẳn** trên một nửa firmware của repo. Đo được 09/10/2026:
# chạy trên dự án RTOS ARM ra `isr: []` dù nó có hàng chục handler.
_RE_ISR = re.compile(r"\bISR\s*\(\s*(\w+)\s*\)")
_RE_ISR_ARM = re.compile(r"^[ \t]*(?:void|static\s+void)\s+(\w+_(?:IRQ)?Handler)\s*\("
                         r"\s*void\s*\)\s*\{", re.M)


def tim_isr(chu: str) -> list[str]:
    """Mọi hàm ngắt trong một tệp nguồn — cả AVR lẫn ARM/CMSIS.

    Chỉ nhận ARM handler **có thân hàm** (`) {`), không nhận khai báo trước (`);`) hay alias
    `__attribute__((weak, alias(...)))`: một handler chỉ khai báo thì không có mã để soi, và
    đưa nó vào danh sách làm con số ISR phình lên mà không thêm phép đo nào.
    """
    ra = {m.group(1) for m in _RE_ISR.finditer(chu or "")}
    ra |= {m.group(1) for m in _RE_ISR_ARM.finditer(chu or "")}
    return sorted(ra)


def do_thi_tu_VAN_BAN(chu: str) -> dict[str, set[str]]:
    """Đồ thị gọi hàm dò bằng VĂN BẢN — đường dự phòng khi không có `.ci`.

    Vì sao bắt buộc có: clang không hỗ trợ `-fcallgraph-info`, nên trên máy chủ `cg` rỗng — và
    `luat_isr` với `cg` rỗng chỉ soi **thân ISR**, không soi hàm ISR gọi tới. Đo được trên
    `robot-sinhvien2`: ISR gọi `motor_step_isr()`, mà phép soi dừng ngay ở dòng gọi.

    Nó **không chính xác** như `.ci`: nó mù với lời gọi qua con trỏ hàm, và nó kêu thừa khi
    một tên hàm xuất hiện trong chú thích. Nhưng kêu thừa ở đây rẻ hơn mù hẳn — và lớp trên
    nói rõ đồ thị này là đồ thị văn bản.
    """
    than: dict[str, tuple[int, int]] = {}
    for m in _RE_HAM.finditer(chu or ""):
        ten = m.group("ten")
        d1, d2 = _than_ham(chu, ten)
        if d1:
            than[ten] = (d1, d2)
    for isr in tim_isr(chu or ""):
        d1, d2 = _than_ham(chu or "", isr)
        if d1:
            than[isr] = (d1, d2)
    dong = (chu or "").splitlines()
    ra: dict[str, set[str]] = {}
    for ten, (d1, d2) in than.items():
        goi = set()
        for i in range(d1 - 1, min(d2, len(dong))):
            for m in re.finditer(r"\b(\w+)\s*\(", _bo_chuoi(dong[i])):
                g = m.group(1)
                if g != ten and (g in than or g in _HAM_CHAN):
                    goi.add(g)
        ra[ten] = goi
    return ra
_RE_HAM = re.compile(
    r"^[ \t]*(?:static\s+|inline\s+|extern\s+|volatile\s+|const\s+|unsigned\s+|signed\s+)*"
    r"[\w\*]+[\s\*]+(?P<ten>\w+)\s*\([^;{]*\)\s*\{", re.M)
_RE_SO_THUC = re.compile(r"\b(float|double)\b")
# Chuỗi và hằng ký tự — thay nội dung bằng khoảng trắng TRƯỚC khi soi toán tử.
#
# Vì sao bắt buộc: `printf("dem=%lu\n", dem)` có `%lu`, và luật "chia/mod trên biến" đọc nó
# là một phép chia. Phép phá đầu tiên của nhiệm vụ này bắt đúng chỗ ấy — và một cảnh báo oan
# ở đây tệ hơn không có, vì nó làm người đọc bỏ qua cả danh sách.
_RE_CHUOI = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")


# Chú thích — cũng phải bỏ, và vì một lý do rất cụ thể.
#
# Luật "chia/mod trên biến" khớp `/` rồi tới một tên biến. Mà `/* ghi chú */ x = 1;` có đúng
# hình dạng ấy: dấu `/` cuối chú thích, khoảng trắng, rồi `x`. Mã firmware của `robot-sinhvien2`
# chú thích **rất dày** bằng tiếng Việt, nên không bỏ chú thích thì phép đo trên nó toàn cảnh
# báo oan — và một danh sách toàn cảnh báo oan thì không ai đọc, kể cả dòng đúng.
_RE_CHU_THICH = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _bo_chuoi(d: str) -> str:
    """Thay nội dung chuỗi VÀ chú thích bằng khoảng trắng, giữ nguyên độ dài dòng.

    Giữ độ dài để số dòng/cột còn đúng — một cảnh báo chỉ sai số dòng là một cảnh báo phải đi
    tìm, và trên một tệp 400 dòng thì nó không được đọc.
    """
    # GIỮ ký tự xuống dòng, chỉ xoá phần còn lại. Thay cả khối bằng khoảng trắng thì ba dòng
    # chú thích thành MỘT dòng, và mọi dòng sau đó dồn lên — tức mọi số dòng báo ra đều lệch.
    # Ca kiểm của chính nhiệm vụ này bắt được: nó báo phép chia ở dòng 4 trong khi nó ở dòng 6.
    d = _RE_CHU_THICH.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), d)
    return _RE_CHUOI.sub(
        lambda m: '"' + re.sub(r"[^\n]", " ", m.group(0)[1:-1]) + '"', d)
# Chia/mod trên BIẾN. Chia cho một **hằng** là phép dịch bit trình biên dịch tự làm — kêu ở đó
# là kêu oan, và kêu oan làm người đọc bỏ qua cả danh sách.
_RE_CHIA = re.compile(r"[/%]\s*(?![\s]*[0-9])(?![/*])\s*[A-Za-z_]\w*")
_RE_TOAN_CUC = re.compile(
    r"^[ \t]*(?!static\b)(?!typedef\b)(?:extern\s+)?"
    r"(?P<volatile>volatile\s+)?(?:unsigned\s+|signed\s+|const\s+)*"
    r"(?:char|short|int|long|float|double|u?int\d+_t|size_t)[\s\*]+(?P<ten>\w+)\s*(?:=|;)", re.M)


# =========================================================================== đọc .su
def doc_su(chu: str) -> dict[str, tuple[int, str]]:
    """`.su` → `{tên hàm: (byte, kiểu)}`.

    Dòng không đúng khuôn thì **bỏ**, không đoán. Một con số ngăn xếp đoán ra còn tệ hơn không
    có — nó đi thẳng vào phép so ngân sách RAM.

    Giữ `kiểu` lại (`static` · `dynamic` · `dynamic,bounded`): ba kiểu nói ba chuyện khác nhau,
    và với một hàm `dynamic` thì con số kia **không phải trần**.
    """
    ra: dict[str, tuple[int, str]] = {}
    for dong in (chu or "").splitlines():
        m = _RE_SU.match(dong)
        if m:
            ra[m.group("ten")] = (int(m.group("byte")), m.group("kieu"))
    return ra


# =========================================================================== đọc .ci
def _ten_nut(x: str) -> str:
    """`"m2.c:loc"` → `loc`; `"main"` → `main`.

    VCG đặt tiền tố tệp cho hàm `static` và bỏ nó cho hàm `extern`. Không chuẩn hoá thì cung
    `tinh → m2.c:loc` không khớp khoá nào của `.su`, và đồ thị rời ra từng mảnh — im lặng.
    """
    return x.rsplit(":", 1)[-1].strip()


def doc_ci(chu: str) -> dict[str, set[str]]:
    """`.ci` (VCG của `-fcallgraph-info`) → `{hàm: {hàm nó gọi}}`."""
    ra: dict[str, set[str]] = {}
    for m in _RE_EDGE.finditer(chu or ""):
        tu, den = _ten_nut(m.group("tu")), _ten_nut(m.group("den"))
        if tu and den:
            ra.setdefault(tu, set()).add(den)
    return ra


# =========================================================================== ngăn xếp
@dataclass(slots=True)
class KetQuaNganXep:
    byte: int = 0
    chuoi: list[str] = field(default_factory=list)
    de_quy: bool = False
    vong: list[str] = field(default_factory=list)
    thieu: list[str] = field(default_factory=list)

    @property
    def la_chan_duoi(self) -> bool:
        """Có hàm không đo được thì con số này là chặn DƯỚI, không phải trần."""
        return bool(self.thieu)

    def to_dict(self) -> dict[str, Any]:
        return {"byte": self.byte, "chuoi": list(self.chuoi), "de_quy": self.de_quy,
                "vong": list(self.vong), "thieu": list(self.thieu),
                "la_chan_duoi": self.la_chan_duoi}


def ngan_xep_toi_da(su: dict[str, tuple[int, str]], cg: dict[str, set[str]],
                    goc: str) -> KetQuaNganXep:
    """Ngăn xếp sâu nhất tính từ `goc`, cộng dồn theo chuỗi gọi. DFS, nhớ đường đang đi.

    Trả **cả chuỗi**: một con số 272 mà không nói đi qua đâu thì không sửa được, còn chuỗi là
    thứ chỉ ra chỗ cắt.

    Đệ quy thì **không có trần**, và hàm này nói ra thế thay vì trả một con số. Trả một con số
    cho một chuỗi gọi đệ quy là trả một lời nói dối có đơn vị byte: nó trông như một trần, và
    người đọc sẽ đem nó so với RAM.
    """
    kq = KetQuaNganXep()
    thieu: set[str] = set()
    vong: set[str] = set()

    def _di(ham: str, dang_di: tuple[str, ...]) -> tuple[int, list[str]]:
        if ham in dang_di:
            kq.de_quy = True
            vong.add(ham)
            return 0, []
        if ham not in su:
            thieu.add(ham)
            return 0, []
        rieng = su[ham][0]
        tot_nhat, duong = 0, []
        for con in sorted(cg.get(ham, ())):
            b, d = _di(con, dang_di + (ham,))
            if b > tot_nhat:
                tot_nhat, duong = b, d
        return rieng + tot_nhat, [ham] + duong

    b, d = _di(goc, ())
    kq.byte, kq.chuoi = b, d
    kq.thieu = sorted(thieu)
    kq.vong = sorted(vong)
    return kq


# =========================================================================== luật ISR
@dataclass(slots=True)
class ViPham:
    loai: str                  # so_thuc · phep_chia · ham_chan · thieu_volatile
    dong: int
    ham: str = ""
    ten: str = ""
    chu: str = ""
    vi_sao: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"loai": self.loai, "dong": self.dong, "ham": self.ham, "ten": self.ten,
                "chu": self.chu[:160], "vi_sao": self.vi_sao}


_VI_SAO = {
    "so_thuc": ("số thực trong ngữ cảnh ngắt: MCU không có FPU thì mỗi phép là một lời gọi "
                "thư viện hàng trăm chu kỳ, và nó tiêu ngăn xếp"),
    "phep_chia": ("phép chia/chia lấy dư trên BIẾN: Cortex-M0 và AVR không có lệnh chia, nên "
                  "nó gọi hàm (`__aeabi_idiv`) — hàng chục chu kỳ và tốn ngăn xếp"),
    "ham_chan": "hàm CHẶN hoặc không reentrant — gọi nó trong ISR là giữ CPU hoặc tranh heap",
    "thieu_volatile": ("biến toàn cục ghi ở CẢ ISR lẫn hàm thường mà không `volatile`: trình "
                       "biên dịch được phép giữ nó trong thanh ghi, nên vòng lặp chính sẽ "
                       "không bao giờ thấy ISR đổi nó. Lỗi này BIÊN DỊCH SẠCH"),
}


def _than_ham(chu: str, ten: str) -> tuple[int, int]:
    """`(dòng đầu, dòng cuối)` của thân hàm `ten` — đếm ngoặc, 1-based. `(0, 0)` nếu không có.

    Đếm ngoặc thay vì dùng thụt lề: một thân hàm viết dồn một dòng (`ISR(X){ dem++; }`) là
    chuyện có thật trong firmware, và thụt lề không nói gì về nó.
    """
    m = _RE_ISR.search(chu) if ten.endswith("_vect") else None
    if m is None:
        for mm in _RE_HAM.finditer(chu):
            if mm.group("ten") == ten:
                m = mm
                break
    else:
        m = next((x for x in _RE_ISR.finditer(chu) if x.group(1) == ten), None)
    if m is None:
        return 0, 0
    i = chu.find("{", m.end() - 1 if ten.endswith("_vect") else m.start())
    if i < 0:
        return 0, 0
    sau = 0
    for j in range(i, len(chu)):
        if chu[j] == "{":
            sau += 1
        elif chu[j] == "}":
            sau -= 1
            if sau == 0:
                return chu[:i].count("\n") + 1, chu[:j].count("\n") + 1
    return chu[:i].count("\n") + 1, chu.count("\n") + 1


def _reachable(cg: dict[str, set[str]], goc: str) -> set[str]:
    thay, hang = {goc}, [goc]
    while hang:
        for con in cg.get(hang.pop(), ()):
            if con not in thay:
                thay.add(con)
                hang.append(con)
    return thay


def luat_isr(nguon_c: str, cg: dict[str, set[str]], isr: str) -> list[ViPham]:
    """Vi phạm ngữ cảnh ngắt trong tập hàm ISR **gọi tới được**.

    Chỉ soi hàm reachable từ ISR: một `printf` trong một hàm chỉ `main` gọi thì không phải lỗi
    của ngữ cảnh ngắt, và báo nó lên là trộn hai chuyện — rồi người đọc bỏ qua cả danh sách.
    """
    chu = nguon_c or ""
    # Bỏ chú thích trên CẢ VĂN BẢN một lần, trước khi tách dòng. Bỏ theo từng dòng thì một
    # `/* … */` trải nhiều dòng không khớp, và các dòng GIỮA nó bị soi như mã — mà chú thích
    # khối nhiều dòng là cách firmware trong repo này viết mọi mục tài liệu. Phép thay giữ
    # nguyên độ dài nên số dòng không lệch.
    chu_sach = _bo_chuoi(chu)
    dong = chu.splitlines()
    dong_sach = chu_sach.splitlines()
    co_the_toi = _reachable(cg, isr)
    ra: list[ViPham] = []

    for ham in sorted(co_the_toi):
        d1, d2 = _than_ham(chu, ham)
        if not d1:
            continue
        for i in range(d1 - 1, min(d2, len(dong))):
            d = dong[i]
            sach = dong_sach[i] if i < len(dong_sach) else ""
            if _RE_SO_THUC.search(sach):
                ra.append(ViPham("so_thuc", i + 1, ham=ham, chu=d.strip(),
                                 vi_sao=_VI_SAO["so_thuc"]))
            if _RE_CHIA.search(sach):
                ra.append(ViPham("phep_chia", i + 1, ham=ham, chu=d.strip(),
                                 vi_sao=_VI_SAO["phep_chia"]))
            for h in _HAM_CHAN:
                if re.search(r"\b" + re.escape(h) + r"\s*\(", sach):
                    ra.append(ViPham("ham_chan", i + 1, ham=ham, ten=h, chu=d.strip(),
                                     vi_sao=_VI_SAO["ham_chan"]))

    # Biến toàn cục ghi ở CẢ ISR lẫn ngoài ISR mà không `volatile`.
    d1, d2 = _than_ham(chu, isr)
    trong_isr = "\n".join(dong_sach[d1 - 1:d2]) if d1 else ""
    ngoai_isr = ("\n".join(dong_sach[:max(0, d1 - 1)] + dong_sach[d2:]) if d1 else chu_sach)
    for m in _RE_TOAN_CUC.finditer(chu_sach):
        if m.group("volatile"):
            continue
        ten = m.group("ten")
        gan = re.compile(r"\b" + re.escape(ten) + r"\s*(?:=[^=]|\+\+|--|\+=|-=|\|=|&=)")
        if gan.search(trong_isr) and gan.search(ngoai_isr):
            ra.append(ViPham("thieu_volatile", chu[:m.start()].count("\n") + 1,
                             ten=ten, chu=m.group(0).strip(),
                             vi_sao=_VI_SAO["thieu_volatile"]))
    return ra


# =========================================================================== chạy thật
# Cờ của LƯỢT PHÂN TÍCH — và chúng là một phần của phép đo, không phải chi tiết nội bộ.
#
# `-O0` có chủ ý, đo được 09/10/2026: với `-O1`, clang inline hai hàm `static` nên `.su` chỉ
# còn `main` và `tinh`, cả hai **0 byte** — tức phép đo biến mất đúng ở chỗ nó cần nói. Và ở
# mọi mức ≥ `-O1`, hàm lá được báo 0 byte vì trình biên dịch dùng lại khung ngăn xếp.
#
# Hệ quả phải NÓI RA: con số `-O0` **lớn hơn** con số của ảnh thật (dựng bằng `-Os`), nên nó là
# một **chặn trên bi quan**. Bi quan là chiều an toàn cho một phép kiểm tràn ngăn xếp — vừa ở
# đây thì chắc chắn vừa ở ảnh thật — nhưng người đọc phải biết, không thì họ đem một con số bi
# quan đi so với RAM rồi kết luận sai. Bài học DEV-349: một cờ biên dịch thêm vào là một phép
# đo khác.
CO_PHAN_TICH = ("-O0", "-std=c11")


def _tim_cc() -> str:
    for x in ("cc", "gcc", "clang"):
        if shutil.which(x):
            return x
    return ""


def chay_phan_tich(goc: Path, nguon: list[Path], *, cc: str = "",
                   them_co: list[Any] | None = None) -> dict[str, Any]:
    """Biên dịch lại vào `.eide/build/tinh/` rồi đọc `.su`/`.ci`.

    **Không chạm ảnh nạp chip.** Kế hoạch cấm đúng chỗ này, và lý do rõ: đổi cờ biên dịch của
    `build.compile` là đổi chính cái ảnh sẽ nạp vào chip. Nên phép phân tích dịch ra một thư
    mục riêng, với cờ riêng, và chỉ `-c` (không liên kết).

    Thiếu trình biên dịch thì `chay_duoc=False` kèm lý do — **không** trả `{}` im lặng. Một
    phép phân tích trả rỗng vì thiếu công cụ sẽ được đọc là *"không có vi phạm nào"*, đúng cái
    N6 cấm.
    """
    cc = cc or _tim_cc()
    if not cc or not shutil.which(cc):
        return {"chay_duoc": False, "co_do_thi": False,
                "vi_sao": (f"không chạy được: thiếu trình biên dịch C "
                           f"({cc or 'cc/gcc/clang'}) trên máy này"),
                "ham": {}, "do_thi": {}, "ngan_xep": {}, "vi_pham": [], "cong_cu_thieu": [cc]}

    ds = [p for p in nguon if Path(p).is_file()]
    if not ds:
        return {"chay_duoc": False, "co_do_thi": False,
                "vi_sao": "không chạy được: không có tệp .c nào để phân tích",
                "ham": {}, "do_thi": {}, "ngan_xep": {}, "vi_pham": [], "cong_cu_thieu": []}

    thu_muc = Path(goc) / ".eide" / "build" / "tinh"
    thu_muc.mkdir(parents=True, exist_ok=True)
    su: dict[str, tuple[int, str]] = {}
    cg: dict[str, set[str]] = {}
    ly_do: list[str] = []
    co_do_thi = False

    for p in ds:
        p = Path(p)
        ra_o = thu_muc / (p.stem + ".o")
        # Thử CÓ `-fcallgraph-info` trước. clang không có cờ ấy (`unknown argument`), và
        # chuyện đó phải lộ ra ở đây chứ không thành một đồ thị rỗng.
        for co_cg in (True, False):
            lenh = [cc, *CO_PHAN_TICH, "-c", "-fstack-usage",
                    *(["-fcallgraph-info=su"] if co_cg else []),
                    *(list(them_co or [])), "-o", str(ra_o), str(p)]
            r = subprocess.run(lenh, cwd=str(thu_muc), capture_output=True, text=True)
            if r.returncode == 0:
                co_do_thi = co_do_thi or co_cg
                break
            if co_cg and "callgraph" in (r.stderr or "").lower():
                ly_do.append(f"{cc} không có `-fcallgraph-info` nên KHÔNG dựng được đồ thị "
                             "gọi hàm (đo được với Apple clang: unknown argument)")
                continue
            ly_do.append(f"{p.name}: không dịch được — {(r.stderr or '')[:200]}")
            break

        # GCC đặt `.su` theo tên NGUỒN, clang theo tên ĐẦU RA. Tìm cả hai, và tìm trong thư
        # mục làm việc lẫn cạnh tệp nguồn.
        # Một tên, không hai: GCC đặt `.su` theo tên NGUỒN và clang theo tên ĐẦU RA, mà ta
        # đặt tên `.o` đúng bằng stem của nguồn — nên hai tên trùng nhau. Giữ hai nhánh ở đây
        # là giữ một nhánh không ca kiểm nào phân biệt được (bài học M4-19).
        for ten in (p.stem + ".su",):
            for cho in (thu_muc, p.parent, Path.cwd()):
                t = cho / ten
                if t.is_file():
                    su.update(doc_su(t.read_text("utf-8", errors="replace")))
                    break
        for cho in (thu_muc, p.parent):
            t = cho / (p.stem + ".ci")
            if t.is_file():
                for k, v in doc_ci(t.read_text("utf-8", errors="replace")).items():
                    cg.setdefault(k, set()).update(v)

    nguon_chu = "\n".join(Path(p).read_text("utf-8", errors="replace") for p in ds)
    isr = tim_isr(nguon_chu)

    # Không có `.ci` thì dò đồ thị bằng VĂN BẢN. Thiếu bước này thì `luat_isr` chỉ soi thân
    # ISR, không soi hàm ISR gọi tới — và trên máy chủ (clang, không có `-fcallgraph-info`)
    # đó là *mọi lúc*. Đo được trên `robot-sinhvien2`: ISR gọi `motor_step_isr()`, phép soi
    # dừng ngay ở dòng gọi.
    do_thi_van_ban = False
    if not cg:
        cg = do_thi_tu_VAN_BAN(nguon_chu)
        do_thi_van_ban = bool(cg)
        if do_thi_van_ban:
            ly_do.append("đồ thị gọi hàm dò bằng VĂN BẢN (trình biên dịch không có "
                         "`-fcallgraph-info`): mù với lời gọi qua con trỏ hàm, và có thể kêu "
                         "thừa — đừng đọc nó như một đồ thị đầy đủ")
    goc_dfs = ["main", *isr]
    nx = {g: ngan_xep_toi_da(su, cg, g).to_dict() for g in goc_dfs if g in su or g in cg}
    vp = [v for g in isr for v in luat_isr(nguon_chu, cg, g)]

    # Hai công cụ ngoài, tuỳ chọn (N-10): thiếu thì NÓI RÕ, không lỗi cứng.
    thieu = [x for x in ("cppcheck", "lizard") if not shutil.which(x)]
    if thieu:
        ly_do.append("không chạy được: thiếu " + ", ".join(thieu)
                     + " (tuỳ chọn — phần còn lại vẫn đo)")

    return {"chay_duoc": bool(su), "co_do_thi": co_do_thi,
            "vi_sao": " · ".join(ly_do),
            "cc": cc, "co_bien_dich": list(CO_PHAN_TICH),
            "bi_quan": True, "do_thi_van_ban": do_thi_van_ban,
            "ham": {k: list(v) for k, v in sorted(su.items())},
            "do_thi": {k: set(v) for k, v in cg.items()},
            "ngan_xep": nx, "isr": isr,
            "vi_pham": [v.to_dict() for v in vp], "cong_cu_thieu": thieu,
            "thu_muc": str(thu_muc)}
