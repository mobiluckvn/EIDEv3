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


@dataclass(slots=True)
class KeHoach:
    muc_tieu: str = ""
    buoc: list[Buoc] = field(default_factory=list)
    gia_dinh: list[str] = field(default_factory=list)
    ngoai_pham_vi: list[str] = field(default_factory=list)
    trang_thai: str = "dang_soan"          # dang_soan | cho_duyet | da_duyet | huy
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
