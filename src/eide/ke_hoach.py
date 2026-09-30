# -*- coding: utf-8 -*-
"""Plan mode — MDD-40 §B5: *"việc lớn → plan.enter (khoá tool ghi) → kế hoạch (bước, tool,
hiện vật, cổng, chi phí, giả định) → plan.exit → thẻ G-SCOPE → duyệt → kế hoạch thành
system-reminder; Stop hook đối chiếu."*

Vì sao chặng này đáng làm, đo được trên phiên bo STM32F469 (402 lượt, 1078 lời gọi):

* **580 lời gọi (54 %) là `fs.read`/`fs.grep`/`fs.glob`.** Tác tử dò đường bằng cách đọc, và
  người dùng chỉ thấy kết quả sau khi số lời gọi ấy đã tiêu xong.
* Có lượt nó **đốt trọn hạn mức 40 lời gọi rồi dừng giữa việc** — không ai biết trước nó
  định làm gì.
* Nó **sửa một đầu rồi làm hỏng đầu kia** (vá gói DSI dài, làm hỏng gói ngắn) vì không có
  bước nào bắt liệt kê "chỗ này còn chạm tới đâu".
* Và một giả định sai của *người* — "có thể panel hỏng" — đã tốn hai lượt, trong khi anh
  Công biết ngay bo từng chạy tốt. Giả định nằm trên giấy thì bị bác trong ba giây.

Nói gọn: plan mode là chỗ người dùng nhìn thấy **cách làm** trước khi nó tiêu lời gọi, thay
vì nhìn thấy **kết quả** sau khi đã tiêu.

Ba quyết định thiết kế, và lý do của từng cái:

1. **Khoá công cụ GHI lấy từ hợp đồng, không từ danh sách tên.** `writes_artefact` /
   `risk >= R3` là thứ mỗi công cụ tự khai. Một danh sách tên phải nhớ cập nhật, và cái quên
   cập nhật sẽ là cái lọt qua.
2. **`plan.big` tính bằng mã, không hỏi mô hình.** Nếu để tác tử tự khai việc của mình có
   lớn không, nó sẽ khai "nhỏ" đúng lúc nó đang định làm việc lớn.
3. **Kế hoạch đã duyệt là một hiện vật, không phải một câu trong hội thoại.** Nén ngữ cảnh
   sẽ ăn mất một câu; một hiện vật thì còn, và Stop hook đối chiếu được với nó.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MA_KE_HOACH = "plan:current"

# Một kế hoạch dài hơn thế thì không ai đọc hết, và phần không đọc chính là phần sẽ sai.
TOI_DA_BUOC = 20
# Ngắn hơn thế thì không phải kế hoạch, là một câu nói.
TOI_THIEU_BUOC = 2

# Ngưỡng "việc lớn". Là hằng số của mô-đun để bộ kiểm đổi được, và để người đọc thấy ngay
# con số thay vì phải suy ra từ một biểu thức.
BUOC_LA_LON = 5


@dataclass(slots=True)
class Buoc:
    """Một bước của kế hoạch. Mọi trường đều bắt buộc trừ `cong` và `ghi_chu`."""

    viec: str = ""
    cong_cu: str = ""
    hien_vat: str = ""
    cong: str = ""                 # cổng sẽ chạm, rỗng nếu không chạm cổng nào
    chi_phi: str = ""              # ước lượng của tác tử: bao nhiêu lời gọi / bao lâu
    ghi_chu: str = ""
    xong: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"viec": self.viec, "cong_cu": self.cong_cu, "hien_vat": self.hien_vat,
                "cong": self.cong, "chi_phi": self.chi_phi, "ghi_chu": self.ghi_chu,
                "xong": self.xong}


# Sáu trạng thái của một kế hoạch, kèm chữ cho người đọc. Đặt cạnh định nghĩa vì chú thích
# cũ ở `trang_thai` chỉ kể bốn cái, trong khi `plan.step_done` ghi `hoan_thanh` và
# `plan.enter` ghi `da_cat` — một danh sách kể thiếu thì tệ hơn không kể, vì nó trông đủ.
TEN_TRANG_THAI_VI: dict[str, str] = {
    "dang_soan": "đang soạn",
    "cho_duyet": "chờ anh duyệt",
    "da_duyet": "đã duyệt, đang làm",
    "hoan_thanh": "đã xong",
    "huy": "đã bỏ",
    "da_cat": "đã cất để làm việc khác",
}


@dataclass(slots=True)
class KeHoach:
    muc_tieu: str = ""
    buoc: list[Buoc] = field(default_factory=list)
    gia_dinh: list[str] = field(default_factory=list)
    ngoai_pham_vi: list[str] = field(default_factory=list)
    trang_thai: str = "dang_soan"          # xem TEN_TRANG_THAI_VI — đủ SÁU trạng thái
    run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"muc_tieu": self.muc_tieu, "steps": [b.to_dict() for b in self.buoc],
                "gia_dinh": list(self.gia_dinh), "ngoai_pham_vi": list(self.ngoai_pham_vi),
                "trang_thai": self.trang_thai, "run_id": self.run_id}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KeHoach:
        return cls(muc_tieu=str(d.get("muc_tieu") or ""),
                   buoc=[Buoc(**{k: v for k, v in b.items() if k in Buoc.__slots__})
                         for b in (d.get("steps") or [])],
                   gia_dinh=list(d.get("gia_dinh") or []),
                   ngoai_pham_vi=list(d.get("ngoai_pham_vi") or []),
                   trang_thai=str(d.get("trang_thai") or "dang_soan"),
                   run_id=str(d.get("run_id") or ""))


def kiem_ke_hoach(kh: KeHoach, co_cong_cu) -> list[str]:
    """Những chỗ kế hoạch chưa dùng được. Rỗng = dùng được.

    `co_cong_cu(ten) -> bool` do tầng trên đưa vào, để mô-đun này không phải biết registry.

    Phép kiểm quan trọng nhất ở đây là **tên công cụ phải có thật**. Một kế hoạch nêu công cụ
    không tồn tại thì người dùng vẫn duyệt được (nó đọc rất xuôi tai), rồi tới lúc chạy mới
    hỏng — và khi đó thứ đã duyệt không còn là thứ đang chạy.
    """
    loi: list[str] = []
    if not kh.muc_tieu.strip():
        loi.append("thiếu `muc_tieu`: kế hoạch không nói nó nhằm đạt cái gì.")
    if len(kh.buoc) < TOI_THIEU_BUOC:
        loi.append(f"chỉ có {len(kh.buoc)} bước; dưới {TOI_THIEU_BUOC} thì đây là một câu "
                   "nói, không phải kế hoạch.")
    if len(kh.buoc) > TOI_DA_BUOC:
        loi.append(f"{len(kh.buoc)} bước, quá {TOI_DA_BUOC}. Không ai đọc hết, và phần không "
                   "đọc chính là phần sẽ sai. Chia thành nhiều kế hoạch.")
    for i, b in enumerate(kh.buoc, 1):
        if not b.viec.strip():
            loi.append(f"bước {i}: thiếu `viec`.")
        if not b.cong_cu.strip():
            loi.append(f"bước {i}: thiếu `cong_cu` — không nói dùng gì thì không ước được "
                       "chi phí và không biết nó chạm cổng nào.")
        elif not co_cong_cu(b.cong_cu):
            loi.append(f"bước {i}: không có công cụ tên `{b.cong_cu}`. Kế hoạch nêu công cụ "
                       "không tồn tại thì đọc vẫn xuôi tai, và chỉ hỏng lúc chạy.")
        if not b.hien_vat.strip():
            loi.append(f"bước {i}: thiếu `hien_vat` — bước không để lại gì thì không kiểm "
                       "được là đã làm hay chưa.")
    return loi


# Công cụ SINH RA MÃ. Kế hoạch có bước dùng chúng thì là kế hoạch viết mã, và lúc ấy hai
# câu hỏi kiến trúc phải được trả lời TRƯỚC khi tách việc.
CONG_CU_SINH_MA = ("fs.write", "fs.edit", "asset.image_to_c", "code.vendor_fetch",
                   "tool.propose", "khoi.place", "sch.compose", "sch.write")

# Dấu hiệu một bước đang trả lời câu hỏi KIẾN TRÚC (chọn hướng, so phương án, ghi ADR).
_DAU_KIEN_TRUC = ("store.option_create", "store.option_choose", "store.adr_create",
                  "ckm.module_set", "khoi.list", "design.")

# Dấu hiệu một bước đang nói CẤU TRÚC MÃ: tệp nào, mô-đun nào, đặt ở đâu.
_TU_CAU_TRUC = ("cấu trúc", "cây tệp", "mô-đun", "module", "tệp nào", "bố cục mã",
                "phân tầng", "thư mục", "giao diện giữa", "api", "tách tệp")


# Đuôi tệp tính là MÃ. `fs.write` ghi một `.md` thì đó là viết tài liệu, không phải viết mã —
# và bắt một kế hoạch viết tài liệu phải chọn kiến trúc là một báo động giả.
#
# Báo động giả dạy người ta bỏ qua cảnh báo, nên nó đắt hơn hẳn việc không có cảnh báo. Đo
# được ngay khi vá: luật bản đầu làm đỏ 12 ca kiểm, tất cả đều là kế hoạch ghi tệp `.md`.
DUOI_MA = (".c", ".h", ".cpp", ".hpp", ".cc", ".py", ".swift", ".ino", ".s", ".asm",
           ".ld", ".rs", ".go", ".js", ".ts", ".java", ".kt", ".m", ".mm")

# Công cụ mà bản thân nó đã là viết mã, bất kể tên hiện vật.
CONG_CU_LUON_LA_MA = ("asset.image_to_c", "code.vendor_fetch", "tool.propose",
                      "khoi.place", "sch.compose", "sch.write")


def _la_ma(b: Buoc) -> bool:
    """Bước này sinh ra MÃ hay sinh ra tài liệu?

    So ĐÚNG ĐUÔI, không tìm chuỗi con. Bản đầu viết `any(x in hv for x in DUOI_MA)`, và `.m`
    (Objective-C) khớp ngay trong `tai-lieu/1.md` — nên mọi kế hoạch viết tài liệu bị đòi
    chọn kiến trúc. Mười ca kiểm đỏ cùng lúc, và lý do thật thì nằm ở hai ký tự.
    """
    if b.cong_cu in CONG_CU_LUON_LA_MA:
        return True
    for x in b.hien_vat.replace(",", " ").split():
        if Path(x.strip("`'\"").lower()).suffix in DUOI_MA:
            return True
    return False


def thieu_phan_tich(kh: KeHoach, co_adr) -> list[str]:
    """Kế hoạch VIẾT MÃ mà chưa trả lời hai câu kiến trúc thì thiếu gì.

    Yêu cầu của anh Công, 30/09/2026: *"với việc làm mới hoàn toàn thì cần có phân tích và
    thiết kế cẩn thận: phân tích và lựa chọn kiến trúc, phân tích và lựa chọn code structure
    rồi mới tiến hành tách công việc để thực thi"*.

    Trước đây `kiem_ke_hoach` kiểm **hình thức** của kế hoạch — đủ bước, có công cụ có thật,
    mỗi bước để lại hiện vật — mà không hỏi câu nào về **nội dung kỹ thuật**. Nên một kế hoạch
    "viết 8 tệp firmware" đọc rất xuôi tai và được duyệt, rồi kiến trúc thành ra thứ hiện lên
    dần trong lúc gõ.

    Hai câu, không phải một, và chúng khác nhau:

    * **Kiến trúc** — chia theo hướng nào, vì sao hướng này chứ không phải hướng kia. Trả lời
      bằng phương án so sánh được (`store.option_*`) hoặc một ADR.
    * **Cấu trúc mã** — cụ thể sẽ có những tệp/mô-đun nào, ranh giới giữa chúng ở đâu.

    Đây là **danh sách thiếu**, không phải lời từ chối: nơi gọi quyết định chặn hay chỉ cảnh
    báo. Kế hoạch chỉ SỬA mã có sẵn thì không hỏi gì — câu hỏi kiến trúc dành cho việc dựng
    cái chưa có.
    """
    sinh_ma = [b for b in kh.buoc if b.cong_cu in CONG_CU_SINH_MA and _la_ma(b)]
    if not sinh_ma:
        return []

    thieu: list[str] = []
    # Hai câu hỏi cho HAI loại việc khác nhau, và một kế hoạch có thể dính cả hai:
    #   · dựng cái chưa có  → chọn kiến trúc, nói cấu trúc mã
    #   · sửa cái đang có   → phân tích trước, biết ai đang dùng
    tao_moi = [b for b in sinh_ma if b.cong_cu != "fs.edit"]
    chu = " ".join((b.viec + " " + b.ghi_chu + " " + b.hien_vat).lower() for b in kh.buoc)

    # SỬA mã có sẵn thì phải phân tích trước — câu đắt nhất là "ai đang dùng nó".
    #
    # Yêu cầu của anh Công: *"trước khi code phải có tài liệu phân tích code (với trường hợp
    # viết thêm) và đưa ra nội dung sẽ sửa rồi mới tiến hành sửa"*. Đặt luật ở KẾ HOẠCH chứ
    # không ở từng lời gọi `fs.edit`: một dòng sửa vặt mà bắt viết tài liệu thì luật ấy sẽ bị
    # lách, còn một kế hoạch sửa mã thì đủ lớn để xứng đáng.
    if any(b.cong_cu == "fs.edit" for b in kh.buoc) \
            and not any(b.cong_cu == "code.analyze" for b in kh.buoc):
        thieu.append(
            "kế hoạch có bước SỬA mã đang có mà chưa bước nào phân tích nó trước. Thêm một "
            "bước `code.analyze` cho những tệp sắp sửa: nó trả lời câu `fs.read` không trả "
            "lời được — **ai đang dùng ký hiệu của tệp ấy**, tức chỗ nào sẽ phải xem lại.")
    co_kien_truc = any(b.cong_cu.startswith(_DAU_KIEN_TRUC) for b in kh.buoc) or co_adr()
    if tao_moi and not co_kien_truc:
        thieu.append(
            "chưa có bước nào CHỌN KIẾN TRÚC. Việc dựng cái chưa có thì hướng đi phải được "
            "so sánh và chốt trước: `store.option_create` vài hướng rồi `store.option_choose`, "
            "hoặc `store.adr_create` nếu hướng đã rõ. Không có bước ấy thì kiến trúc là thứ "
            "hiện dần ra trong lúc gõ.")
    if tao_moi and not any(t in chu for t in _TU_CAU_TRUC):
        thieu.append(
            "chưa bước nào nói CẤU TRÚC MÃ: sẽ có những tệp/mô-đun nào, ranh giới giữa chúng "
            "ở đâu. Một kế hoạch chỉ nói 'viết firmware' thì tới lúc chạy mới biết nó định "
            "viết mấy tệp.")
    return thieu


def la_viec_lon(kh: KeHoach, spec_cua) -> tuple[bool, str]:
    """Kế hoạch này có phải "việc lớn" không — tính bằng MÃ, không hỏi mô hình.

    Để tác tử tự khai việc của mình có lớn không thì nó sẽ khai "nhỏ" đúng vào lúc nó đang
    định làm việc lớn — không phải vì gian, mà vì nó đang tập trung vào việc chứ không vào
    việc phân loại việc.

    Ba dấu hiệu, mỗi cái đủ một mình:
    """
    ly_do: list[str] = []
    if len(kh.buoc) >= BUOC_LA_LON:
        ly_do.append(f"{len(kh.buoc)} bước (từ {BUOC_LA_LON} trở lên là lớn)")
    for b in kh.buoc:
        sp = spec_cua(b.cong_cu)
        if sp is None:
            continue
        if getattr(sp, "gate", None):
            ly_do.append(f"`{b.cong_cu}` đi qua cổng {sp.gate}")
        if str(getattr(sp, "risk", "R1")) >= "R3":
            ly_do.append(f"`{b.cong_cu}` là {sp.risk}")
    # Bỏ trùng mà giữ thứ tự — người đọc cần thấy lý do đầu tiên trước.
    thay: list[str] = []
    for x in ly_do:
        if x not in thay:
            thay.append(x)
    return bool(thay), "; ".join(thay)


def cong_cu_bi_khoa(spec: Any) -> bool:
    """Trong lúc soạn kế hoạch, công cụ này có bị khoá không?

    Lấy từ **hợp đồng** của công cụ (`writes_artefact`, `risk`), không từ một danh sách tên:
    một công cụ mới thêm vào mà có `writes_artefact` thì tự động bị khoá, không phải nhớ đi
    cập nhật danh sách — và cái quên cập nhật sẽ đúng là cái lọt qua.
    """
    if spec is None:
        return False
    if getattr(spec, "name", "") in KHONG_KHOA:
        return False
    return bool(getattr(spec, "writes_artefact", False)) or str(
        getattr(spec, "risk", "R1")) >= "R3"


# Những công cụ KHÔNG bị khoá dù mang dấu ghi: chính bộ công cụ của plan mode, và việc ghi
# bộ nhớ dài hạn. Khoá `memory.note` trong lúc soạn kế hoạch nghĩa là cấm tác tử ghi lại
# đúng thứ nó vừa học được để soạn kế hoạch ấy.
KHONG_KHOA = ("plan.enter", "plan.exit", "plan.cancel", "plan.step_done", "memory.note")


def doi_chieu(kh: KeHoach, da_goi: list[str]) -> dict[str, Any]:
    """Stop hook: tác tử có đi đúng kế hoạch không.

    Trả về cả hai phía, và **không phía nào bị coi là lỗi**: đi thêm việc ngoài kế hoạch
    thường là dấu hiệu kế hoạch thiếu, chứ không phải tác tử sai. Việc của hàm này là làm cho
    độ lệch **nhìn thấy được**, để người quyết, chứ không phải để phạt.
    """
    trong_kh = [b.cong_cu for b in kh.buoc]
    ngoai = [t for t in dict.fromkeys(da_goi) if t not in trong_kh and t not in KHONG_KHOA]
    chua = [b.cong_cu for b in kh.buoc if not b.xong and b.cong_cu not in da_goi]
    return {"ngoai_ke_hoach": ngoai, "chua_lam": chua,
            "xong": sum(1 for b in kh.buoc if b.xong), "tong": len(kh.buoc),
            "lech": bool(ngoai or chua)}
