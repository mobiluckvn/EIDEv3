# -*- coding: utf-8 -*-
"""C2 — nén có kiểm chứng. EIDE-MEM-42 §6.2, §6.4, §6.6.

Ba bước, và thứ tự là toàn bộ ý nghĩa:

    PreCompact  (mã, 0 token)  → sự thật có cấu trúc vào M2 TRƯỚC khi văn bản bị tóm
    Tóm tắt     (mô hình)      → lược đồ 10 mục, nhiệt độ 0
    PostCompact (mã + mô hình) → hỏi ngược 3 câu; sai thì HUỶ

Bước một là bảo hiểm cho P3 "nén không mất": nếu một quyết định đã nằm trong kho thì dù
bản tóm tắt có bỏ sót nó, nó vẫn còn. Bước ba là phép đo: nó biến câu hỏi "nén có làm
mất gì không" từ cảm tính thành một con số 3/3 hoặc một lần huỷ.

Nén là **giao dịch** (§12): bản cũ được giữ nguyên cho tới khi kiểm đạt. Hỏng ở bất kỳ
bước nào — mạng, mô hình, lược đồ sai — thì transcript về đúng như trước, và ta thử lại
ở lượt sau chứ không để nó ở trạng thái "đã cắt nhưng chưa có tóm tắt".
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import summary as sm
from .compact import c1, chi_so_ghim, danh_dau_luot

# §6.2.3 — bao nhiêu lượt gần nhất giữ NGUYÊN VĂN sau khi nén.
K_LUOT = 10
K_GIAM_C3 = 6              # §6.4: phiên rất dài thì hạ xuống 6
K_TANG_KHI_KIEM_TRUOT = 4  # §6.6: kiểm sai thì giữ nhiều hơn rồi thử lại
SO_LAN_THU_LAI = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class KetQuaNen:
    muc: str = "C2"
    ok: bool = False
    truoc: int = 0
    sau: int = 0
    diem_kiem: str = ""
    so_lan_thu: int = 0
    ly_do: str = ""
    khong_co_gi: bool = False      # chưa tới lúc nén ≠ nén trượt
    tom_tat: Any = None
    rut_vao_m2: list[str] = field(default_factory=list)
    chi_tiet_kiem: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"muc": self.muc, "ok": self.ok, "truoc": self.truoc, "sau": self.sau,
                "kiem": self.diem_kiem, "so_lan_thu": self.so_lan_thu,
                "ly_do": self.ly_do, "khong_co_gi": self.khong_co_gi,
                "rut_vao_m2": self.rut_vao_m2,
                "chi_tiet_kiem": self.chi_tiet_kiem}

    def dong_he_thong(self) -> str:
        """Một dòng [Hệ thống] cho người — §4.2 đòi mỗi lần nén phải nói ra."""
        if self.khong_co_gi:
            return f"[Hệ thống] {self.ly_do}"
        if not self.ok:
            return (f"[Hệ thống] Nén KHÔNG qua kiểm ({self.diem_kiem}) — giữ nguyên ngữ "
                    f"cảnh. {self.ly_do}")
        if self.diem_kiem == "KHÔNG kiểm được":
            return (f"[Hệ thống] Đã nén {self.truoc} → {self.sau} ký tự, nhưng **chưa "
                    "kiểm được** — không có câu hỏi nào đủ điều kiện. Nếu thấy tôi quên "
                    "gì, bảo tôi huỷ nén.")
        # NÓI RA đường lui và tên công cụ.
        #
        # Nhánh này là nhánh chạy nhiều nhất, và nó không nhắc gì tới việc huỷ nén được —
        # `memory.undo_compact` chưa nổ lần nào trong toàn bộ lịch sử chạy. Một phép biến đổi
        # không đảo ngược được thì người ta sợ nó; một phép đảo ngược không ai biết là có thì
        # cũng thế.
        return (f"[Hệ thống] Đã nén {self.truoc} → {self.sau} ký tự, giữ {K_LUOT} lượt "
                f"gần nhất, kiểm {self.diem_kiem}."
                + (f" Rút vào bộ nhớ dự án: {', '.join(self.rut_vao_m2)}."
                   if self.rut_vao_m2 else "")
                + " Thấy tôi quên gì thì bảo huỷ nén — `memory.undo_compact` lùi được trong "
                  "24 giờ.")


# =========================================================================== PreCompact
def pre_compact(doan: list[dict[str, Any]], *, store: Any, ledger: Any,
                eide_md: Any) -> dict[str, Any]:
    """Quét đoạn sắp bị nén, tìm sự thật có cấu trúc CHƯA có trong M2.

    Không tự ghi vào kho bằng đường tắt — kho chỉ nhận qua changeset. Cái hàm này làm
    là **liệt kê** để lớp trên ghi đúng đường, và để bản tóm tắt biết nó không phải là
    nơi duy nhất giữ những thứ này.
    """
    co_trong_kho = {a["id"] for a in store.list("adr", limit=200)}
    co_trong_kho |= {a["id"] for a in store.list("req", limit=400)}
    chu_md = (eide_md.path.read_text("utf-8") if eide_md and eide_md.path.exists()
              else "")

    import re

    ma_nhac: set[str] = set()
    for m in doan:
        chu = str(m.get("text") or m.get("result") or "")
        ma_nhac |= set(re.findall(r"\b(?:ADR|FR|NFR|UR)-[A-Z0-9\-]{2,}\b", chu))

    thieu = sorted(m for m in ma_nhac if m not in co_trong_kho and m not in chu_md)
    return {
        "ma_nhac_trong_doan": sorted(ma_nhac),
        "chua_co_trong_M2": thieu,
        "so_message": len(doan),
    }


def bia_mo(ledger: Any) -> list[str]:
    """Nội dung người đã bảo quên — bản tóm tắt không được chứa (P7)."""
    return [str(e.data.get("noi_dung") or "") for e in ledger.read()
            if e.kind == "tombstone"]


# =========================================================================== bộ nén
class BoNen:
    """Chạy C2 trên một danh sách message. Không biết gì về vòng lặp."""

    def __init__(self, *, llm: Any, ledger: Any, store: Any, eide_md: Any,
                 transcript: Any = None):
        self.llm = llm
        self.ledger = ledger
        self.store = store
        self.eide_md = eide_md
        self.transcript = transcript
        self.tom_tat_hien_tai: sm.BanTomTat | None = None
        # §6.2.3 — bản trước khi nén giữ 24 giờ, để huỷ nén được.
        self.ban_truoc_nen: list[dict[str, Any]] | None = None
        self.luc_nen: str = ""

    def huy_nen(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Huỷ lần nén gần nhất — §6.2.3, trong 24 giờ.

        Không có nút này thì nén là một cửa một chiều, và người phải tin rằng nó không
        làm mất gì. Có nút này thì họ kiểm được.
        """
        from datetime import datetime, timedelta, timezone

        if self.ban_truoc_nen is None:
            return {"ok": False,
                    "message_vi": "Chưa nén lần nào trong phiên này nên không có gì để huỷ."}
        try:
            luc = datetime.fromisoformat(self.luc_nen)
            if datetime.now(timezone.utc) - luc > timedelta(hours=24):
                return {"ok": False,
                        "message_vi": ("Lần nén gần nhất đã quá 24 giờ. Bản trước khi "
                                       "nén không còn được giữ.")}
        except ValueError:
            pass
        messages[:] = self.ban_truoc_nen
        if self.transcript is not None:
            self.transcript.thay_toan_bo(list(messages))
        self.ban_truoc_nen = None
        self.tom_tat_hien_tai = None
        self.ledger.append("compact", {"buoc": "huy",
                                       "message_vi": "Người dùng huỷ lần nén gần nhất."})
        return {"ok": True, "message_vi": "Đã khôi phục ngữ cảnh về trước khi nén.",
                "so_message": len(messages)}

    # ------------------------------------------------------------------ chia đoạn
    @staticmethod
    def chia(messages: list[dict[str, Any]], k_luot: int,
             ghim: set[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Tách (phần sẽ nén, phần giữ nguyên văn).

        Giữ nguyên văn = K lượt gần nhất + mọi message được ghim, **đúng thứ tự thời
        gian**. Ghim nằm rải rác trong quá khứ nên không thể chỉ cắt đuôi danh sách.
        """
        danh_dau_luot(messages)
        luot_cuoi = max((m.get("_luot", 0) for m in messages), default=0)
        moc = luot_cuoi - k_luot

        nen: list[dict[str, Any]] = []
        giu: list[dict[str, Any]] = []
        for i, m in enumerate(messages):
            if i in ghim or m.get("_luot", 0) > moc:
                giu.append(m)
            else:
                nen.append(m)
        return nen, giu

    # ------------------------------------------------------------------ một lần thử
    def _goi_tom_tat(self, doan: list[dict[str, Any]], inventory_text: str,
                     tomb: list[str]) -> sm.BanTomTat | None:
        rsp = self.llm.stream(
            system=("Bạn là bộ nén ngữ cảnh của EIDE. Bạn chỉ làm một việc: ghi lại "
                    "đúng những gì đã xảy ra, theo lược đồ, không thêm không bớt."),
            messages=[{"role": "user",
                       "text": sm.prompt_tom_tat(doan, self.tom_tat_hien_tai,
                                                 inventory_text, tomb)}],
            tools=[sm.luoc_do_tom_tat()])
        for c in rsp.tool_calls or []:
            if c.tool == sm.TEN_TOOL_TOM_TAT:
                return sm.BanTomTat.tu_args(
                    c.args, created_at=_now(),
                    model=getattr(self.llm, "name", ""),
                    covers=(0, len(doan)))
        return None

    def _goi_kiem(self, messages_da_nen: list[dict[str, Any]],
                  phieu: list[sm.CauKiem], inventory_text: str = "") -> list[str]:
        """Hỏi trên ngữ cảnh ĐÃ NÉN — và "ngữ cảnh" nghĩa là **đúng thứ mô hình sẽ có**.

        Bản đầu chỉ truyền `messages`, không truyền `<inventory>`. Nó biến phép kiểm
        thành "transcript một mình có chứa X không" — chặt hơn tình huống thật, vì ở
        lượt bình thường mô hình luôn có khối kiểm kê. Đo được trên phiên thật: câu
        "tiêu chí của NFR-01 là gì" bị trả lời "không biết", trong khi con số đó nằm
        trong kho và ở lượt thường thì tra ra ngay.
        
        Sửa chỗ này KHÔNG làm phép kiểm dễ đi: nếu một thứ đã nằm trong M2 thì mất nó
        khỏi transcript là *đúng* — đó chính là điều PreCompact bảo đảm. Cái phép kiểm
        phải bắt là mất thứ **không** còn ở đâu khác.
        """
        ngu_canh = list(messages_da_nen)
        if inventory_text:
            ngu_canh.append({"role": "user", "_he_thong": True,
                             "text": f"<system-reminder>\n{inventory_text}\n"
                                     "</system-reminder>"})
        rsp = self.llm.stream(
            system=("Bạn đang trả lời câu hỏi kiểm tra trí nhớ. Chỉ dùng ngữ cảnh đang "
                    "có. Không biết thì nói không biết."),
            messages=ngu_canh + [
                {"role": "user", "text": sm.prompt_kiem(phieu)}],
            tools=[sm.luoc_do_tra_loi()])
        for c in rsp.tool_calls or []:
            if c.tool == sm.TEN_TOOL_TRA_LOI:
                return [str(x) for x in (c.args.get("tra_loi") or [])]
        return []

    # ------------------------------------------------------------------ C2
    def nen(self, messages: list[dict[str, Any]], *, run_id: str = "",
            inventory_text: str = "", k_luot: int = K_LUOT) -> KetQuaNen:
        """Nén một lần, có kiểm. Trả kết quả; `messages` chỉ bị đổi khi kiểm ĐẠT."""
        kq = KetQuaNen(truoc=sum(len(str(m)) for m in messages))
        # Sao chép TỪNG PHẦN TỬ, không sao chép cái container.
        #
        # `messages` trong sản phẩm là `DanhSachGhiDia` — một `list` con giữ tham chiếu
        # tới `Transcript`, và trong đó có một `threading.Lock` không deepcopy được.
        # `copy.deepcopy(messages)` nổ `TypeError: cannot pickle '_thread.lock' object`,
        # và nổ ở chỗ không ai ngờ: giữa lúc nén, tức đúng lúc ngữ cảnh đang đầy.
        goc = [copy.deepcopy(m) for m in messages]

        danh_dau_luot(messages)
        luot_cuoi = max((m.get("_luot", 0) for m in messages), default=0)
        ghim = chi_so_ghim(messages)
        tomb = bia_mo(self.ledger)
        phieu = sm.lam_phieu_kiem(self.ledger, self.store)

        k = k_luot
        for lan in range(1, SO_LAN_THU_LAI + 2):
            kq.so_lan_thu = lan
            doan, giu = self.chia(messages, k, ghim)
            if not doan:
                # KHÔNG phải "nén trượt" — không có gì để nén. Hai chuyện khác hẳn
                # nhau với người đọc: một cái là "hệ thống nghi ngờ chính nó", cái kia
                # là "chưa tới lúc". Gộp hai thành một câu là làm người lo vô cớ.
                kq.khong_co_gi = True
                kq.ly_do = (f"Chưa có gì để nén: phiên mới {luot_cuoi} lượt, mà C2 giữ "
                            f"{k} lượt gần nhất nguyên văn. Ngữ cảnh còn rộng.")
                kq.sau = kq.truoc
                self.ledger.append("compact", {"run_id": run_id, "buoc": "khong_can",
                                               "so_luot": luot_cuoi, "k_luot": k,
                                               "message_vi": kq.ly_do})
                return kq

            # 1. PreCompact — sự thật vào M2 trước.
            pre = pre_compact(doan, store=self.store, ledger=self.ledger,
                              eide_md=self.eide_md)
            kq.rut_vao_m2 = pre["chua_co_trong_M2"]
            self.ledger.append("compact", {"run_id": run_id, "buoc": "pre",
                                           "lan": lan, **pre})

            # 2. Tóm tắt.
            try:
                tt = self._goi_tom_tat(doan, inventory_text, tomb)
            except Exception as e:                               # noqa: BLE001
                # §12 — mô hình hỏng giữa lúc tóm tắt thì HUỶ, giữ nguyên, thử lượt sau.
                kq.ly_do = f"Gọi mô hình để tóm tắt hỏng: {e}. Ngữ cảnh giữ nguyên."
                self.ledger.append("compact", {"run_id": run_id, "buoc": "loi",
                                               "message_vi": kq.ly_do})
                messages[:] = goc
                kq.sau = kq.truoc
                return kq

            if tt is None or tt.rong():
                kq.ly_do = ("Mô hình không trả về bản tóm tắt đúng lược đồ. "
                            "Giữ nguyên ngữ cảnh.")
                self.ledger.append("compact", {"run_id": run_id, "buoc": "luoc_do_sai",
                                               "lan": lan, "rong": tt is not None,
                                               "message_vi": kq.ly_do})
                messages[:] = goc
                kq.sau = kq.truoc
                return kq

            song_lai = tt.chua_noi_dung_da_quen(tomb)
            if song_lai:
                # P7 — thứ đã quên không được hồi sinh qua bản tóm tắt.
                kq.ly_do = (f"Bản tóm tắt chứa {len(song_lai)} điều người dùng đã bảo "
                            "quên. Huỷ nén.")
                self.ledger.append("compact", {"run_id": run_id, "buoc": "tombstone",
                                               "song_lai": song_lai})
                messages[:] = goc
                kq.sau = kq.truoc
                return kq

            # 3. Lắp lại: tóm tắt + ghim/giữ nguyên văn, đúng thứ tự thời gian.
            moi = [{"role": "user", "_he_thong": True, "_ghim": True,
                    "_tom_tat": True, "text": tt.van_ban()}] + giu

            # 3b. Nén mà PHÌNH thì không nhận.
            #
            # Bản tóm tắt mười mục có khung cố định ~1,3 k ký tự. Nén một đoạn ngắn hơn
            # thế thì ta trả tiền một lần gọi mô hình để làm ngữ cảnh to ra. Kiểm ở đây
            # thay vì tin vào ngưỡng: ngưỡng nói "đã đầy", còn cái này nói "việc này có
            # ích không".
            co_moi = sum(len(str(m)) for m in moi)
            if co_moi >= kq.truoc:
                kq.khong_co_gi = True
                kq.ly_do = (f"Nén xong còn to hơn lúc đầu ({kq.truoc} → {co_moi} ký "
                            "tự) — đoạn cần nén ngắn hơn cả khung bản tóm tắt. "
                            "Giữ nguyên.")
                self.ledger.append("compact", {"run_id": run_id, "buoc": "khong_loi",
                                               "truoc": kq.truoc, "neu_nen": co_moi,
                                               "message_vi": kq.ly_do})
                messages[:] = goc
                kq.sau = kq.truoc
                return kq

            # 4. PostCompact — hỏi ngược trên ngữ cảnh ĐÃ NÉN.
            if not phieu:
                # Không có gì kiểm được thì nói ra, và vẫn nhận nén — nhưng ghi rõ là
                # "không kiểm", không phải "3/3". (N6: đừng biến rỗng thành đạt.)
                kq.diem_kiem = "không có phiếu kiểm"
            else:
                try:
                    tl = self._goi_kiem(moi, phieu, inventory_text)
                except Exception as e:                           # noqa: BLE001
                    kq.ly_do = f"Gọi mô hình để kiểm hỏng: {e}. Giữ nguyên ngữ cảnh."
                    self.ledger.append("compact", {"run_id": run_id, "buoc": "loi_kiem",
                                                   "lan": lan, "message_vi": kq.ly_do})
                    messages[:] = goc
                    kq.sau = kq.truoc
                    return kq
                cham = sm.cham_phieu(phieu, tl)

                # --- Câu hỏi này có CÔNG BẰNG không?
                #
                # Một phép kiểm chỉ đo được "nén làm mất gì" khi câu hỏi trả lời được
                # TRƯỚC khi nén. Nếu mô hình cũng chịu thua trên ngữ cảnh gốc thì câu đó
                # đang đo khả năng của mô hình, không đo mất mát của phép nén — và nó sẽ
                # huỷ mọi lần nén, khiến C2 không bao giờ chạy được.
                #
                # Đo được trên phiên thật: kiểm trượt 2/3 ba lần liên tiếp vì một câu
                # hỏi mà mô hình không trả lời được ở đâu cả.
                #
                # Chỉ tốn thêm một lời gọi, và chỉ khi đã trượt.
                if not cham["qua"]:
                    try:
                        tl_goc = self._goi_kiem(goc, phieu, inventory_text)
                    except Exception:                        # noqa: BLE001
                        tl_goc = []
                    goc_cham = sm.cham_phieu(phieu, tl_goc)
                    giu = [i for i in range(len(phieu))
                           if cham["chi_tiet"][i]["dat"] or goc_cham["chi_tiet"][i]["dat"]]
                    bo = [i for i in range(len(phieu)) if i not in giu]
                    if bo:
                        self.ledger.append("compact", {
                            "run_id": run_id, "buoc": "cau_hoi_bo", "lan": lan,
                            "so_bo": len(bo), "cau": [phieu[i].hoi for i in bo],
                            "message_vi": ("Bỏ câu hỏi kiểm mà mô hình cũng không trả "
                                           "lời được TRƯỚC khi nén — nó đo nhầm thứ.")})
                        phieu = [phieu[i] for i in giu]
                        cham = sm.cham_phieu(phieu, [tl[i] if i < len(tl) else ""
                                                     for i in giu])

                if not phieu:
                    # Không còn câu nào kiểm được. KHÔNG được im lặng coi là đạt —
                    # "không kiểm được" phải hiện ra đúng chữ đó cho người đọc (N6).
                    cham = {"dat": 0, "tong": 0, "diem": "KHÔNG kiểm được",
                            "qua": True, "chi_tiet": []}
                    self.ledger.append("compact", {
                        "run_id": run_id, "buoc": "khong_kiem_duoc", "lan": lan,
                        "message_vi": ("Nén xong nhưng không có câu hỏi nào kiểm được — "
                                       "nhận bản nén, và nói rõ là CHƯA kiểm.")})

                kq.diem_kiem = cham["diem"]
                kq.chi_tiet_kiem = cham["chi_tiet"]
                if not cham["qua"]:
                    self.ledger.append("compact", {
                        "run_id": run_id, "buoc": "kiem_truot", "lan": lan,
                        "diem": cham["diem"], "chi_tiet": cham["chi_tiet"]})
                    if lan <= SO_LAN_THU_LAI and (luot_cuoi - (k + K_TANG_KHI_KIEM_TRUOT)) > 0:
                        k += K_TANG_KHI_KIEM_TRUOT     # giữ nhiều hơn rồi thử lại
                        messages[:] = [copy.deepcopy(m) for m in goc]
                        continue
                    if lan <= SO_LAN_THU_LAI:
                        # Tăng K nữa thì không còn gì để nén, và vòng sau sẽ báo "chưa
                        # tới lúc" — che mất sự thật là **kiểm đã trượt**. Dừng ở đây
                        # và nói đúng chuyện đã xảy ra.
                        kq.ly_do = (f"Kiểm sau nén không đạt ({cham['diem']}) và phiên "
                                    f"chỉ có {luot_cuoi} lượt — giữ nhiều hơn nữa thì "
                                    "không còn gì để nén. Giữ nguyên ngữ cảnh.")
                        self.ledger.append("compact", {
                            "run_id": run_id, "buoc": "bo_cuoc", "lan": lan,
                            "diem": cham["diem"], "so_luot": luot_cuoi,
                            "message_vi": kq.ly_do})
                        messages[:] = goc
                        kq.sau = kq.truoc
                        return kq
                    kq.ly_do = (f"Kiểm sau nén không đạt sau {lan} lần "
                                f"({cham['diem']}). Giữ nguyên ngữ cảnh — thà tốn token "
                                "còn hơn quên mất một quyết định.")
                    self.ledger.append("compact", {"run_id": run_id, "buoc": "bo_cuoc",
                                                   "lan": lan, "diem": cham["diem"],
                                                   "message_vi": kq.ly_do})
                    messages[:] = goc
                    kq.sau = kq.truoc
                    return kq

            # 5. Đạt — chốt giao dịch. Giữ bản trước 24 h để huỷ nén được (§6.2.3).
            self.ban_truoc_nen = goc
            self.luc_nen = _now()
            messages[:] = moi
            if self.transcript is not None:
                self.transcript.thay_toan_bo(list(messages))
            self.tom_tat_hien_tai = tt
            kq.ok = True
            kq.tom_tat = tt
            kq.sau = sum(len(str(m)) for m in messages)
            self.ledger.append("compact", {
                "run_id": run_id, "buoc": "ok", "lan": lan, "k_luot": k,
                "truoc": kq.truoc, "sau": kq.sau, "diem": kq.diem_kiem,
                "tom_tat": tt.to_dict()})
            return kq

        return kq


def nen_c1_truoc(messages: list[dict[str, Any]], **kw: Any) -> dict[str, Any]:
    """Tiện: luôn chạy C1 (0 token) trước khi nghĩ tới C2."""
    return c1(messages, **kw)


# =========================================================================== C4 khẩn cấp
def c4(messages: list[dict[str, Any]], *, ghim: set[int] | None = None) -> dict[str, Any]:
    """§6.5 — ở 95 %: bỏ MỌI tool_result thô, kể cả trong K lượt gần nhất. 0 token.

    Đây là biện pháp cuối, và nó cố ý thô: không gọi mô hình, không tóm tắt, không phán
    xét cái gì quan trọng. Nó chỉ làm một việc — thay mọi kết quả công cụ bằng một dòng
    có `blob_ref` — vì ở mức 95 % thì mỗi lời gọi mô hình thêm vào là một rủi ro hỏng
    giữa chừng.

    Hai thứ C4 **không** chạm, và đó là toàn bộ lý do nó an toàn: message ghim, và câu
    trả lời đang stream. §6.5 nói thẳng "không bao giờ cắt câu trả lời đang stream giữa
    chừng để nhét thêm".
    """
    from .compact import _stub, danh_dau_luot

    ghim = ghim or set()
    danh_dau_luot(messages)
    bc = {"truoc": sum(len(str(m)) for m in messages), "stub": 0}
    for i, m in enumerate(messages):
        if i in ghim or m.get("role") != "tool" or m.get("_stub"):
            continue
        messages[i] = _stub(m, "ngữ cảnh đầy (C4) — giữ lại một dòng")
        bc["stub"] += 1
    bc["sau"] = sum(len(str(m)) for m in messages)
    bc["giam_phan_tram"] = (round(100 * (1 - bc["sau"] / bc["truoc"]), 1)
                            if bc["truoc"] else 0.0)
    return bc
