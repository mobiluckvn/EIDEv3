# -*- coding: utf-8 -*-
"""Loi la du lieu, khong phai ngoai le chet nguoi.

EIDE-MDD-40 §B3: "Moi cong cu kiem tien de ben trong va tra loi co huong dan
{code, message_vi, hint_for_agent, alternatives[]} — loi la du lieu de mo hinh doi huong."

Hai doc gia cua mot loi:
  - `message_vi`      : nguoi doc. Tieng Viet, noi dung that, khong giau that bai (E3.2 quy tac 5).
  - `hint_for_agent`  : mo hinh doc. Noi CHINH XAC phai lam gi tiep, bang ten tool.
  - `alternatives[]`  : cac duong di khac, de mo hinh khong phai doan.

Bai hoc tu dot do 23/09 (TC023, TC025, TC026, TC070): mot loi DUNG nhung SAI LY DO
con te hon khong co loi — nguoi dung nhan "khong nhan ra dinh dang nen" cho mot tep
netlist, va an toan cua TC070 la do TAI NAN chu khong do thiet ke. Vi vay moi ma loi
o day phai tro dung nguyen nhan, va viec chon ma loi la mot quyet dinh thiet ke.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --------------------------------------------------------------------------- ho ma loi
# E1xxx  dinh dang / noi dung tep      (ingest, classify, parse)
#        E1001 khong ho tro · E1002 hong/cut · E1003 khong co duong dan
#        E1010 mat khau · E1011 qua gioi han · E1012 zip bomb
#        E1013 macro bi bo qua (canh bao) · E1014 OCR hong · E1015 chuyen doi hong
#        (E1010–E1015 = E1003–E1008 cua ING-43, danh so lai — DEV-249)
# E2xxx  thieu tien de                 (tool goi khi chua co cai no can)
# E3xxx  mang / dich vu ben ngoai      (UC19 — phai phan biet voi loi tep)
# E4xxx  cap quyen / cong / sandbox    (N5 — chan co chu dich)
# E5xxx  du lieu / store / lugc do
# E6xxx  mo hinh (LLM)                 (UC19 — qua tai, timeout, tra sai lugc do)
# E7xxx  lich su / changeset / snapshot   (E7001–E7007 da dung het)
# E8xxx  so do / EDA                      (SCH-44; E8001 netlist lech CKM, E8002 thieu
#                                          pinout da duyet — xem DEV-252)
# E_PROTO_*  giao thuc UAP             (MDD-40 §D2)


@dataclass(slots=True)
class EideError(Exception):
    """Mot loi co huong dan. Nem duoc, ma cung serialize duoc de tra cho mo hinh."""

    code: str
    message_vi: str
    hint_for_agent: str = ""
    alternatives: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    # Loi nay co phai loi cua NGUOI DUNG khong (vs loi cua tac tu)? Anh huong cach hien.
    blame: str = "system"  # system | agent | user | external

    def __post_init__(self) -> None:
        Exception.__init__(self, f"[{self.code}] {self.message_vi}")

    def to_tool_result(self) -> dict[str, Any]:
        """Dang mo hinh nhin thay. Giu nguyen 4 truong cua hop dong §B3."""
        out: dict[str, Any] = {
            "ok": False,
            "code": self.code,
            "message_vi": self.message_vi,
            "hint_for_agent": self.hint_for_agent,
            "alternatives": list(self.alternatives),
        }
        if self.details:
            out["details"] = dict(self.details)
        return out

    def to_notice(self) -> dict[str, Any]:
        """Dang nguoi nhin thay (UICommand `notice`)."""
        return {
            "level": "error",
            "code": self.code,
            "text": self.message_vi,
            "alternatives": list(self.alternatives),
        }


# --------------------------------------------------------------------------- cac loi hay dung
# Moi ham duoi day la mot ma loi co NGUYEN NHAN RIENG. Khong gop.


def unsupported_format(path: str, detected: str, supported: list[str]) -> EideError:
    """E1001 — doc duoc tep, nhung dinh dang nay san pham khong lam viec duoc.

    Day la loi cua TC025: tep .PcbDoc phai duoc noi la "dinh dang Altium khong ho tro",
    khong phai "khong nhan ra dinh dang nen".
    """
    return EideError(
        code="E1001",
        message_vi=(
            f"Tệp {path} có định dạng {detected} — EIDE chưa đọc được định dạng này. "
            f"Các định dạng đọc được: {', '.join(supported)}."
        ),
        hint_for_agent=(
            "KHÔNG gọi lại tool này trên cùng tệp. Nói với người dùng định dạng nào đọc được "
            "và đề nghị họ xuất lại từ phần mềm gốc."
        ),
        alternatives=[f"Xin người dùng xuất sang: {', '.join(supported)}"],
        details={"path": path, "detected": detected},
        blame="user",
    )


def corrupt_file(path: str, why: str) -> EideError:
    """E1002 — tep dung dinh dang nhung hong/cut (TC026)."""
    return EideError(
        code="E1002",
        message_vi=f"Tệp {path} bị hỏng hoặc cụt: {why}.",
        hint_for_agent="Nói thật là tệp hỏng. KHÔNG suy đoán phần thiếu chứa gì.",
        alternatives=["Đề nghị người dùng nạp lại tệp", "Hỏi nguồn gốc của tệp"],
        details={"path": path, "why": why},
        blame="user",
    )


def path_not_found(path: str) -> EideError:
    """E1003 — duong dan khong ton tai.

    Cum nguyen nhan lon nhat cua dot do 23/09 (11 ca): duong dan BIA ra tu chinh cau
    nguoi dung roi nem vao tool. Loi nay phai day mo hinh sang HOI, khong phai sang doan.
    """
    return EideError(
        code="E1003",
        message_vi=f"Không có tệp hay thư mục nào ở đường dẫn: {path}",
        hint_for_agent=(
            "Đường dẫn này không tồn tại. TUYỆT ĐỐI không dùng một đường dẫn khác tự đoán ra. "
            "Gọi fs.glob để tìm, hoặc ask_user hỏi đúng đường dẫn."
        ),
        alternatives=["fs.glob để tìm tệp theo mẫu tên", "ask_user hỏi đường dẫn đầy đủ"],
        details={"path": path},
        blame="agent",
    )


# --------------------------------------------------------------------------- nap tai lieu
# EIDE-ING-43 §7 dat sau ma loi E1003–E1008 cho duong ong nap. E1003 o day DA MANG nghia
# khac ("khong co tep o duong dan") va nghia do da di vao thong bao nguoi dung doc, vao
# `hint_for_agent` day mo hinh sang hoi thay vi doan, va vao ca do dang xanh.
#
# Doi nghia mot ma loi dang chay de khop tai lieu la dat su gon gang cua bang ma len tren
# su dung cua nguoi. Chu san pham chot 25/09/2026: **cap ma moi**. Anh xa o DEV-249.


def password_protected(path: str) -> EideError:
    """E1010 — ING-43 goi la E1003. Tep co that, dung dinh dang, nhung bi khoa."""
    return EideError(
        code="E1010",
        message_vi=f"Tệp {path} có mật khẩu bảo vệ — EIDE không mở được.",
        hint_for_agent=(
            "KHÔNG thử đoán mật khẩu và không gọi lại tool. Hỏi người dùng gỡ mật khẩu "
            "rồi nạp lại, hoặc xin bản không khoá."
        ),
        alternatives=["Xin bản không đặt mật khẩu", "ask_user hỏi nguồn gốc tệp"],
        details={"path": path},
        blame="user",
    )


def over_limit(path: str, what: str, gia_tri: Any, tran: Any) -> EideError:
    """E1011 — ING-43 goi la E1004. Vuot tran kich thuoc/so trang/so tep."""
    return EideError(
        code="E1011",
        message_vi=(
            f"{path}: {what} là {gia_tri}, vượt trần {tran} mà EIDE xử lý an toàn được. "
            "Dừng lại ở đây để không treo máy giữa chừng."
        ),
        hint_for_agent=(
            "Đừng lặp lại nguyên lời gọi. Hỏi người dùng thu hẹp phạm vi — khoảng trang, "
            "hoặc chọn vài tệp trong gói — rồi nạp từng phần."
        ),
        alternatives=["Hỏi người dùng phạm vi trang cần đọc",
                      "Nạp từng tệp con thay vì cả gói"],
        details={"path": path, "what": what, "value": gia_tri, "limit": tran},
        blame="user",
    )


def zip_bomb(path: str, ty_le: float, muc: str = "") -> EideError:
    """E1012 — ING-43 goi la E1005. Ti le nen bat thuong: dung TRUOC khi boc."""
    return EideError(
        code="E1012",
        message_vi=(
            f"{path} giải nén ra gấp {ty_le:.0f} lần kích thước tệp"
            + (f" (mục “{muc}”)" if muc else "")
            + ". Tỉ lệ này bất thường — có thể là tệp nén được dựng để làm đầy ổ đĩa. "
            "EIDE dừng trước khi bóc, không bóc thử."
        ),
        hint_for_agent=(
            "KHÔNG bóc tệp này bằng đường nào khác. Báo người dùng và hỏi tệp đến từ đâu."
        ),
        alternatives=["Hỏi nguồn gốc tệp nén", "Đề nghị nạp từng tệp rời"],
        details={"path": path, "ratio": ty_le, "member": muc},
        blame="user",
    )


def macro_ignored(path: str, so_macro: int) -> EideError:
    """E1013 — ING-43 goi la E1006. Day la CANH BAO: du lieu van doc duoc.

    Tra ve mot EideError vi no can day du bon truong, nhung chỗ goi phai dat no vao
    `canh_bao` chu khong dung no de tu choi tep.
    """
    return EideError(
        code="E1013",
        message_vi=(
            f"{path} có {so_macro} macro. EIDE đọc dữ liệu trong tệp và **không chạy "
            "macro** — macro trong tài liệu người khác gửi là mã của người khác."
        ),
        hint_for_agent=(
            "Dữ liệu vẫn dùng được bình thường. Nói cho người dùng biết có macro và "
            "EIDE đã bỏ qua, đừng im lặng."
        ),
        alternatives=[],
        details={"path": path, "macros": so_macro},
        blame="user",
    )


def ocr_failed(path: str, why: str) -> EideError:
    """E1014 — ING-43 goi la E1007."""
    return EideError(
        code="E1014",
        message_vi=f"Không đọc được chữ từ ảnh trong {path}: {why}.",
        hint_for_agent=(
            "Đừng đoán nội dung ảnh. Nói thẳng là không đọc được và xin bản có lớp chữ."
        ),
        alternatives=["Xin bản PDF gốc có lớp chữ", "Hỏi người dùng gõ lại số cần dùng"],
        details={"path": path, "why": why},
        blame="system",
    )


def convert_failed(path: str, den: str, why: str) -> EideError:
    """E1015 — ING-43 goi la E1008. Chuyen doi LibreOffice that bai."""
    return EideError(
        code="E1015",
        message_vi=(
            f"Không chuyển được {path} sang {den}: {why}. "
            "Định dạng cũ cần LibreOffice để đọc."
        ),
        hint_for_agent=(
            "Kiểm xem LibreOffice đã cài chưa (tool.search 'libreoffice'). Nếu chưa, đề "
            "nghị người dùng lưu lại tệp ở định dạng mới (.docx/.xlsx/.pptx)."
        ),
        alternatives=["Xin bản .docx/.xlsx/.pptx", "Đề nghị cài LibreOffice"],
        details={"path": path, "to": den, "why": why},
        blame="system",
    )


def missing_precondition(
    tool: str, needs: str, how_to_get: str = "", *, artefacts_present: list[str] | None = None
) -> EideError:
    """E2001 — thieu tien de. Loi nay la DIEM CONG, khong phai that bai.

    TC009: `diagram.architecture` tu choi ve tu phong doan. Rao chan dung;
    cai sai la khong ai noi cho mo hinh biet phai goi gi TRUOC.
    """
    return EideError(
        code="E2001",
        message_vi=f"Chưa thể chạy {tool}: thiếu {needs}.",
        hint_for_agent=(
            f"{tool} cần {needs}. "
            + (f"Gọi {how_to_get} trước rồi thử lại." if how_to_get else
               "Không có cách tự động lấy thứ này — hỏi người dùng bằng ask_user.")
        ),
        alternatives=[how_to_get] if how_to_get else ["ask_user"],
        details={"tool": tool, "needs": needs, "present": artefacts_present or []},
        blame="agent",
    )


def network_down(service: str, why: str, state_saved: bool = True) -> EideError:
    """E3001 — mat mang. TC072 doi DUNG loai loi nay, khong phai loi tep."""
    return EideError(
        code="E3001",
        message_vi=(
            f"Không kết nối được tới {service}: {why}. "
            + ("Trạng thái làm việc đã được lưu, tiếp tục được khi có mạng." if state_saved else "")
        ),
        hint_for_agent=(
            "Đây là lỗi MẠNG, không phải lỗi tệp hay lỗi tham số. Báo cho người dùng bằng "
            "đúng loại nguyên nhân này và đề nghị thử lại sau."
        ),
        alternatives=["Đợi người dùng nạp tệp thủ công", "Tiếp tục phần việc không cần mạng"],
        details={"service": service, "state_saved": state_saved},
        blame="external",
    )


def denied_by_policy(tool: str, reason: str, gate: str | None = None) -> EideError:
    """E4001 — lop cap quyen tu choi. Loi CO CHU DICH (N5/N8)."""
    return EideError(
        code="E4001",
        message_vi=f"Thao tác {tool} bị từ chối: {reason}",
        hint_for_agent=(
            f"Chính sách từ chối vì: {reason}. Sửa lời gọi cho đúng rồi thử lại — "
            "đừng tìm đường vòng để lách."
        ),
        alternatives=[f"Mở cổng {gate} bằng cách hỏi người dùng"] if gate else [],
        details={"tool": tool, "gate": gate},
        blame="agent",
    )


def outside_sandbox(path: str, roots: list[str]) -> EideError:
    """E4002 — ra ngoai sandbox (TC070). Phai chan VI THIET KE, khong vi tai nan."""
    return EideError(
        code="E4002",
        message_vi=(
            f"Đường dẫn {path} nằm ngoài vùng làm việc cho phép. "
            f"Chỉ được đọc/ghi trong: {', '.join(roots)}."
        ),
        hint_for_agent="Đường dẫn ngoài sandbox. Đừng thử đường dẫn khác ngoài vùng cho phép.",
        alternatives=["Làm việc trong thư mục dự án"],
        details={"path": path, "roots": roots},
        blame="agent",
    )


def gate_pending(gate: str, gate_id: str, summary: str) -> EideError:
    """E4003 — hanh dong dang cho nguoi quyet o mot the cong.

    I6: chi HumanAct kind=decide voi gate_id dang cho moi mo cong. Mot chu "co"
    go trong o nhap KHONG mo cong — de mot cau tra loi khong the mo hai thu.
    """
    return EideError(
        code="E4003",
        message_vi=f"Đang chờ anh quyết ở thẻ {gate}: {summary}",
        hint_for_agent=(
            f"Thẻ cổng {gate} ({gate_id}) đã được phát cho người dùng. DỪNG LẠI, đừng gọi "
            "lại tool này và đừng hỏi lại bằng ask_user. Kết thúc lượt và chờ quyết định."
        ),
        alternatives=["Làm việc khác không chạm cổng này", "Kết thúc lượt"],
        details={"gate": gate, "gate_id": gate_id},
        blame="system",
    )


def schema_violation(what: str, why: str) -> EideError:
    """E5001 — du lieu khong dung lugc do."""
    return EideError(
        code="E5001",
        message_vi=f"{what} không đúng lược đồ: {why}",
        hint_for_agent=f"Sửa tham số cho đúng lược đồ rồi gọi lại. Chi tiết: {why}",
        alternatives=[],
        details={"what": what, "why": why},
        blame="agent",
    )


def missing_explain(tool: str, missing_fields: list[str]) -> EideError:
    """E5002 — ghi hien vat ma thieu lop giai thich (N8).

    MDD-40 §E1: "cong cu ghi hien vat TU CHOI neu thieu explain hoac thieu mot trong
    sau truong". Day la ca CX02.
    """
    return EideError(
        code="E5002",
        message_vi="Không ghi được: hiện vật này chưa có lớp giải thích cho người đọc.",
        hint_for_agent=(
            f"{tool} cần trường `explain` đầy đủ sáu mục. Còn thiếu: {', '.join(missing_fields)}. "
            "Viết explain rồi gọi lại — quy ước ở E3.1: summary ≤ 30 từ, why nêu ràng buộc/REQ/Fact "
            "dẫn tới, sources có tầng, diff_prev bằng lời, next một hành động, confidence là tầng thấp nhất."
        ),
        alternatives=[],
        details={"tool": tool, "missing": missing_fields},
        blame="agent",
    )


def unsourced_constant(constants: list[str]) -> EideError:
    """E5003 — constant-guard: hang so khong nguon di vao ma (N1)."""
    return EideError(
        code="E5003",
        message_vi=(
            "Trong nội dung sắp ghi có con số chưa truy vết được tới tài liệu nào: "
            + ", ".join(constants)
        ),
        hint_for_agent=(
            "Mọi con số dùng để quyết định hoặc sinh mã phải có Fact tầng VÀNG/BẠC/NGƯỜI. "
            "Gọi fact.query tìm nguồn; không có thì hỏi người dùng (tạo Fact tầng NGƯỜI) "
            "hoặc nạp datasheet. Không tự điền một con số."
        ),
        alternatives=["fact.query", "ask_user để lấy số từ người (tầng NGƯỜI)", "doc.search_web"],
        details={"constants": constants},
        blame="agent",
    )


def llm_unavailable(why: str, attempts: int) -> EideError:
    """E6001 — mo hinh loi/qua tai (TC073). Khong duoc mat viec da lam."""
    return EideError(
        code="E6001",
        message_vi=(
            f"Dịch vụ mô hình không trả lời được sau {attempts} lần thử: {why}. "
            "Mọi thứ đã làm trong lượt này vẫn còn, tiếp tục được."
        ),
        hint_for_agent="",
        alternatives=["Thử lại sau", "Tiếp tục bằng các tool xác định không cần mô hình"],
        details={"why": why, "attempts": attempts},
        blame="external",
    )


def budget_exhausted(kind: str, limit: Any) -> EideError:
    """E6002 — het ngan sach luot (40 tool / 300 s).

    UC19: "Qua han luot (300s) tha nguoi dung ra va noi that."
    """
    return EideError(
        code="E6002",
        message_vi=(
            f"Lượt này đã chạm giới hạn {kind} ({limit}). Tôi dừng lại ở đây để anh nhìn thấy "
            "đã làm được tới đâu, thay vì chạy tiếp trong im lặng."
        ),
        hint_for_agent="Hết ngân sách. Tóm tắt đã làm gì, còn gì, rồi kết thúc lượt.",
        alternatives=["Chia nhỏ việc", "Duyệt kế hoạch rồi chạy tiếp"],
        details={"kind": kind, "limit": limit},
        blame="system",
    )


# --------------------------------------------------------------------------- loi giao thuc (D2)
PROTO_CHANNEL = "E_PROTO_CHANNEL"
PROTO_GAP = "E_PROTO_GAP"
PROTO_DUP = "E_PROTO_DUP"
GATE_STALE = "E_GATE_STALE"
CARD_CLOSED = "E_CARD_CLOSED"
VERSION_CONFLICT = "E_VERSION_CONFLICT"
BLOB_MISSING = "E_BLOB_MISSING"


def proto(code: str, message_vi: str, **details: Any) -> EideError:
    return EideError(code=code, message_vi=message_vi, details=details, blame="system")
