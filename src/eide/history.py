# -*- coding: utf-8 -*-
"""Lịch sử: ghi changeset, hoàn tác ba mức, checkpoint ngầm — EIDE-MDD-40 §E5.

Lớp này là nơi duy nhất trong sản phẩm được phép nói "trạng thái đã đổi". Kho (`Store`)
và git (`Vcs`) chỉ biết *ghi*; chúng không biết ai ghi, vì sao ghi, và làm sao lùi lại.
Ba câu hỏi đó sống ở đây.

Quy tắc §E5.2 được cài thẳng vào mã, không để ai quên:

  - Hoàn tác **tạo changeset mới**, không xoá cái cũ. Nhờ vậy hoàn tác cũng hoàn tác được.
  - Hoàn tác của **người** thì luôn được (R0). Hoàn tác do **tác tử** đề xuất phải qua thẻ.
  - Changeset **không hoàn tác được** (flash, eFuse, cài công cụ) thì giữ nguyên khi hoàn
    tác cả lượt, và cảnh báo "bo vẫn đang chạy bản X" — ca CX11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import changeset as cs_mod
from . import deps
from .changeset import BlobStore, Changeset, ChangesetLog
from .vcs import GitKhongSan, Vcs


# Đuôi tệp → loại hiện vật. Dùng để tệp nằm đúng chỗ trong kiểm kê và trong đồ thị
# phụ thuộc. Không đoán bằng nội dung ở đây: việc đó là `ingest.classify` của bước G4,
# và nó có việc khác (nhận ra tệp nén, tệp hỏng, tệp Altium — các ca TC023–026).
_DUOI = {
    # `.sh` nằm ở đây, không phải ở nhóm "tệp khác": một script cấu hình USB gadget
    # hay một script nạp firmware là mã chạy trên thiết bị — nó phải xuất hiện ở tab
    # Mã nguồn, phải bị constant-guard soi, và phải thành STALE khi REQ đổi.
    "code": {".c", ".h", ".cpp", ".cc", ".hpp", ".s", ".asm", ".ino", ".py", ".rs",
             ".go", ".ld", ".mk", ".cmake", ".sh", ".bash", ".zsh", ".service",
             ".dts", ".dtsi"},
    "netlist": {".net", ".kicad_sch", ".kicad_pcb", ".sch"},
    "criteria": {".criteria"},
    "note": {".md", ".txt", ".rst", ".adoc"},
    "config": {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"},
}
_TEN_DAC_BIET = {"Makefile": "code", "CMakeLists.txt": "code", "EIDE.md": "memory"}


def doan_loai(path: str) -> str:
    """Tệp này là loại hiện vật gì.

    Vì sao không để tất cả là `code`: chặng làm việc (§A4) được suy ra từ kiểm kê, và
    "có tệp mã" là điều kiện của chặng C4 Firmware. Nếu một tệp README cũng tính là mã
    thì thanh trạng thái sẽ báo dự án đang ở chặng Firmware trong khi chưa có dòng mã
    nào — một lời nói dối nhỏ nhưng đúng loại mà N3 cấm.
    """
    from pathlib import Path as _P
    p = _P(path)
    if p.name in _TEN_DAC_BIET:
        return _TEN_DAC_BIET[p.name]
    duoi = p.suffix.lower()
    for loai, tap in _DUOI.items():
        if duoi in tap:
            return loai
    return "file"


@dataclass(slots=True)
class KetQuaHoanTac:
    ok: bool
    changeset_moi: str | None = None
    da_lui: list[str] = field(default_factory=list)
    giu_nguyen: list[dict[str, str]] = field(default_factory=list)   # không hoàn tác được
    stale_moi: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    message_vi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "changeset": self.changeset_moi, "da_lui": self.da_lui,
                "giu_nguyen": self.giu_nguyen, "stale": self.stale_moi,
                "canh_bao": self.canh_bao, "message_vi": self.message_vi}


class History:
    def __init__(self, *, paths: Any, store: Any, ledger: Any, ids: Any,
                 eide_md: Any | None = None):
        self.paths = paths
        self.store = store
        self.ledger = ledger
        self.ids = ids
        self.eide_md = eide_md
        self.log = ChangesetLog(paths.changesets)
        self.blobs = BlobStore(paths.blobs)
        from .snapshot import SnapshotStore
        self.snapshots = SnapshotStore(paths.state_dir / "snapshots.jsonl")
        self.vcs = Vcs(paths.project_root)
        self.git_san = False
        try:
            self.vcs.khoi_tao()
            self.git_san = True
        except GitKhongSan:
            # Không có git thì phần tệp mất khả năng revert. Ghi ra để không ai tưởng
            # là có — E3.2 §5 "không giấu thất bại".
            self.ledger.append("incident", {
                "code": "E7001",
                "message_vi": "Không dùng được git trong thư mục dự án. Thay đổi tệp vẫn "
                              "được ghi changeset, nhưng hoàn tác phần tệp sẽ dựa vào bản "
                              "sao nội dung thay vì git."})

    # ================================================================== ghi
    def ghi_kho(self, *, author: str, artefact_id: str, type: str, op: str,
                canonical: dict[str, Any], explain: dict[str, Any],
                run_id: str | None = None, tool_call_id: str | None = None,
                human_act_id: str | None = None, note: str | None = None,
                gay_stale: bool = True) -> Changeset:
        """Ghi một hiện vật vào kho VÀ sinh changeset. Không có đường nào khác để ghi.

        `gay_stale=False` cho các sửa chỉ chạm cách trình bày (§E4.1, ca CX08): đổi tên
        một khối không được làm cả chuỗi hạ nguồn sáng đèn, vì người sẽ học được rằng
        băng cảnh báo không có nghĩa gì và lần STALE thật sẽ bị bỏ qua.
        """
        truoc = self.store.get(artefact_id)
        from_v = truoc["version"] if truoc else None
        canonical_truoc = truoc["canonical"] if truoc else None

        to_v = self.store.apply(artefact_id=artefact_id, type=type, op=op, author=author,
                                canonical=canonical, explain=explain,
                                changeset_id=None)

        cs = cs_mod.for_store_write(
            cs_id=self.ids.next("cs"), author=author, artefact_id=artefact_id, type=type,
            op=op, from_version=from_v, to_version=to_v,
            canonical_truoc=canonical_truoc, canonical_sau=canonical,
            explain=explain, run_id=run_id, tool_call_id=tool_call_id,
            human_act_id=human_act_id, note=note)

        if gay_stale:
            cs.stale_marked = deps.danh_dau_stale(
                self.store, thuong_nguon=[artefact_id], ly_do_cs=cs.id,
                mo_ta=("anh sửa" if author == "human" else "tác tử sửa") + f" {artefact_id}")

        return self._chot(cs)

    def ghi_tep(self, *, author: str, paths: list[str], summary: str,
                explain: dict[str, Any], noi_dung_truoc: dict[str, str] | None = None,
                run_id: str | None = None, tool_call_id: str | None = None,
                human_act_id: str | None = None, note: str | None = None,
                loai: str | None = None) -> Changeset:
        """Commit thay đổi tệp thành một changeset.

        Tệp cũng được đăng ký thành **hiện vật trong kho**, không chỉ nằm trong git.
        Lý do: đồ thị phụ thuộc (§E5.4) làm việc trên hiện vật. Nếu một tệp mã chỉ tồn
        tại trong git thì sửa REQ sẽ không đánh dấu được tệp đó là lỗi thời — và ca
        CX06 ("hạ nguồn STALE đúng danh sách") sẽ im lặng trượt. Git giữ *nội dung*;
        kho giữ *vị trí của nó trong mạng lưới phụ thuộc*.
        """
        # Cấp mã changeset TRƯỚC khi commit: message commit phải mang mã đó, nếu không
        # thì nhìn vào `git log` sẽ không lần ngược ra được changeset nào sinh ra nó.
        cs_id = self.ids.next("cs")
        sha_truoc = self.vcs.sha_hien_tai() if self.git_san else None
        sha = None
        if self.git_san:
            try:
                sha = self.vcs.commit(cs_id=cs_id, author=author, summary=summary,
                                      paths=paths)
            except GitKhongSan as e:
                self.ledger.append("incident", {"code": "E7002", "message_vi": str(e)})

        # Bản sao nội dung cũ theo hash: đường lui khi git không revert được.
        blob_truoc = {p: self.blobs.put(noi_dung_truoc[p])
                      for p in (noi_dung_truoc or {})}

        cs = cs_mod.for_file_write(
            cs_id=cs_id, author=author, paths=paths, sha=sha,
            sha_truoc=sha_truoc, explain=explain, run_id=run_id,
            tool_call_id=tool_call_id, human_act_id=human_act_id, note=note,
            blob_truoc=blob_truoc)

        # Đăng ký tệp thành hiện vật để nó có mặt trong kiểm kê và trong đồ thị phụ thuộc.
        for i, p in enumerate(paths):
            cu = self.store.get(p)
            lp = loai or doan_loai(p)
            v = self.store.apply(
                artefact_id=p, type=lp, op="update" if cu else "create", author=author,
                canonical={"path": p, "sha": sha,
                           "bytes": (self.paths.project_root / p).stat().st_size
                           if (self.paths.project_root / p).exists() else 0},
                explain=explain, changeset_id=cs_id)
            cs.touches[i].type = lp
            cs.touches[i].from_version = cu["version"] if cu else None
            cs.touches[i].to_version = v
            cs.touches[i].op = "update" if cu else "create"

        cs.stale_marked = deps.danh_dau_stale(
            self.store, thuong_nguon=paths, ly_do_cs=cs.id,
            mo_ta=("anh sửa" if author == "human" else "tác tử sửa") + " mã")
        return self._chot(cs)

    def ghi_khong_hoan_tac(self, *, author: str, what: str, reason_vi: str,
                           explain: dict[str, Any], run_id: str | None = None,
                           tool_call_id: str | None = None) -> Changeset:
        return self._chot(cs_mod.irreversible(
            cs_id=self.ids.next("cs"), author=author, what=what, reason_vi=reason_vi,
            explain=explain, run_id=run_id, tool_call_id=tool_call_id))

    def _chot(self, cs: Changeset) -> Changeset:
        self.log.append(cs)
        self.ledger.append("changeset", {
            "id": cs.id, "author": cs.author, "run_id": cs.run_id,
            "touches": [t.artefact_id for t in cs.touches],
            "reversible": cs.reversible, "stale": cs.stale_marked,
            "summary": cs.explain.get("summary", "")})
        return cs

    # ================================================================== checkpoint
    def checkpoint(self, *, ly_do: str, run_id: str | None = None) -> Changeset:
        """§E6.2 — checkpoint ngầm trước mỗi lượt và trước mỗi lần hoàn tác lớn.

        Không tên, không hiện trong danh sách "bản ưng ý". Nó chỉ ghi lại *trạng thái
        đang ở đâu* để lần lùi nào cũng có chỗ quay về.

        Ở bước này checkpoint mới GHI trạng thái; khôi phục từ nó là `snapshot.restore`
        của bước G5. Ghi vẫn có ích ngay: nó là mốc để `history.diff` so từ đó tới nay.
        """
        cs = Changeset(
            id=self.ids.next("cs"), ts=cs_mod._now(), author="eide", run_id=run_id,
            touches=[],
            forward=[{"kind": "checkpoint",
                      "git_sha": self.vcs.sha_hien_tai() if self.git_san else None,
                      "versions": {a["id"]: a["version"]
                                   for a in self.store.list(limit=2000)}}],
            inverse=[],
            explain={"summary": f"Checkpoint ngầm: {ly_do}",
                     "why": "Để lần lùi nào cũng có chỗ quay về.",
                     "sources": [], "diff_prev": "không đổi gì",
                     "next": "—", "confidence": "VANG"})
        return self._chot(cs)

    # ================================================================== hoàn tác
    def hoan_tac_changeset(self, cs_id: str, *, by: str = "human") -> KetQuaHoanTac:
        """§E5.2 mức 1 — áp phép nghịch đảo, tạo changeset MỚI."""
        cs = self.log.get(cs_id)
        if cs is None:
            return KetQuaHoanTac(False, message_vi=f"Không có changeset nào mã {cs_id}.")
        if cs.undone_by:
            return KetQuaHoanTac(
                False, message_vi=f"{cs_id} đã được hoàn tác rồi (bởi {cs.undone_by}).")
        if not cs.reversible:
            return KetQuaHoanTac(
                False, giu_nguyen=[{"id": cs.id, "ly_do": cs.ly_do_khong_hoan_tac() or ""}],
                message_vi=f"{cs_id} không hoàn tác được: {cs.ly_do_khong_hoan_tac()}")

        canh = self._canh_bao_chuoi(cs)
        moi = self._ap_nghich_dao([cs], by=by, mo_ta=f"hoàn tác {cs_id}")
        moi.canh_bao = canh + moi.canh_bao
        return moi

    def hoan_tac_luot(self, run_id: str, *, by: str = "human") -> KetQuaHoanTac:
        """§E5.2 mức 2 — hoàn tác mọi changeset của một lượt, theo thứ tự NGƯỢC."""
        ds = [c for c in self.log.of_run(run_id) if not c.undone_by
              and not any(f.get("kind") == "checkpoint" for f in c.forward)]
        if not ds:
            return KetQuaHoanTac(False, message_vi=f"Lượt {run_id} không thay đổi gì để hoàn tác.")

        self.checkpoint(ly_do=f"trước khi hoàn tác {run_id}", run_id=run_id)

        lui = [c for c in ds if c.reversible]
        giu = [{"id": c.id, "ly_do": c.ly_do_khong_hoan_tac() or "",
                "summary": c.explain.get("summary", "")} for c in ds if not c.reversible]

        kq = self._ap_nghich_dao(list(reversed(lui)), by=by, mo_ta=f"hoàn tác lượt {run_id}")
        kq.giu_nguyen = giu
        if giu:
            # CX11 — phần đã tác động ra ngoài máy không lùi được, và người phải biết.
            kq.canh_bao.append(
                "Những thay đổi sau KHÔNG hoàn tác được và vẫn còn nguyên: "
                + "; ".join(f"{g['id']} ({g['ly_do']})" for g in giu)
                + ". Trạng thái trên máy đã lùi, nhưng thứ ở ngoài thì chưa.")
        return kq

    def _ap_nghich_dao(self, ds: list[Changeset], *, by: str, mo_ta: str) -> KetQuaHoanTac:
        da_lui: list[str] = []
        cham: list[str] = []
        canh: list[str] = []

        for cs in ds:
            for op in cs.inverse:
                try:
                    self._ap_mot(op, cs)
                    cham.extend(t.artefact_id for t in cs.touches)
                except Exception as e:                       # noqa: BLE001
                    canh.append(f"{cs.id}: không áp được phép nghịch đảo ({e})")
                    break
            else:
                da_lui.append(cs.id)

        if not da_lui:
            return KetQuaHoanTac(False, canh_bao=canh,
                                 message_vi="Không hoàn tác được gì. " + " ".join(canh))

        moi = Changeset(
            id=self.ids.next("cs"), ts=cs_mod._now(), author=by,
            touches=[t for cs in ds if cs.id in da_lui for t in cs.touches],
            forward=[o for cs in ds if cs.id in da_lui for o in cs.inverse],
            inverse=[o for cs in ds if cs.id in da_lui for o in cs.forward],
            explain={
                "summary": f"{mo_ta.capitalize()} — {len(da_lui)} thay đổi được lùi lại",
                "why": "Người ra lệnh hoàn tác. Lịch sử không bị xoá: đây là một thay đổi mới.",
                "sources": [{"kind": "changeset", "ref": c, "tier": "VANG"} for c in da_lui],
                "diff_prev": "Trạng thái quay về như trước " + ", ".join(da_lui),
                "next": "Xem lại kết quả; hoàn tác chính lần hoàn tác này nếu cần.",
                "confidence": "VANG"},
            undoes=da_lui[0] if len(da_lui) == 1 else None)

        stale = deps.danh_dau_stale(self.store, thuong_nguon=list(dict.fromkeys(cham)),
                                    ly_do_cs=moi.id, mo_ta=mo_ta)
        moi.stale_marked = stale
        self._chot(moi)
        for c in da_lui:
            self.log.mark(c, undone_by=moi.id)

        return KetQuaHoanTac(
            True, changeset_moi=moi.id, da_lui=da_lui, stale_moi=stale, canh_bao=canh,
            message_vi=f"Đã {mo_ta}: {len(da_lui)} thay đổi được lùi lại bằng changeset {moi.id}."
                       + (f" {len(stale)} hiện vật hạ nguồn được đánh dấu cần cập nhật."
                          if stale else ""))

    def _ap_mot(self, op: dict[str, Any], cs: Changeset) -> None:
        kind = op.get("kind")
        if kind == "store":
            if op["op"] == "delete":
                self.store.apply(artefact_id=op["artefact_id"], type=op["type"],
                                 op="delete", author="eide", canonical={},
                                 explain={"summary": f"gỡ bỏ theo hoàn tác {cs.id}"})
            else:
                self.store.apply(artefact_id=op["artefact_id"], type=op["type"],
                                 op="update", author="eide",
                                 canonical=op.get("canonical") or {},
                                 explain=op.get("explain") or
                                         {"summary": f"khôi phục theo hoàn tác {cs.id}"})
        elif kind == "file":
            self._lui_tep(op, cs)
        elif kind in ("external", "checkpoint"):
            pass          # không có gì để lùi
        else:
            raise ValueError(f"phép nghịch đảo lạ: {kind}")

    def _lui_tep(self, op: dict[str, Any], cs: Changeset) -> None:
        """Ưu tiên git revert; không được thì đặt lại nội dung từ blob đã lưu."""
        if self.git_san and op.get("sha"):
            try:
                self.vcs.revert(op["sha"], cs_id=f"lùi-{cs.id}")
                return
            except GitKhongSan:
                pass
        for path, h in (op.get("blob_truoc") or {}).items():
            data = self.blobs.get(h)
            if data is None:
                raise RuntimeError(f"mất bản sao nội dung cũ của {path}")
            p = self.paths.project_root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        if not op.get("blob_truoc"):
            raise RuntimeError("không có git cũng không có bản sao nội dung cũ")

    def _canh_bao_chuoi(self, cs: Changeset) -> list[str]:
        """CX10 — hoàn tác một changeset ở giữa chuỗi chạm cùng hiện vật."""
        ids = {t.artefact_id for t in cs.touches}
        sau = [c for c in self.log.sau(cs.id)
               if not c.undone_by and ids & {t.artefact_id for t in c.touches}]
        if not sau:
            return []
        return ["Sau {} còn {} thay đổi nữa chạm cùng hiện vật ({}). Hoàn tác riêng {} "
                "có thể làm mất công của những thay đổi đó — cân nhắc hoàn tác cả chuỗi."
                .format(cs.id, len(sau), ", ".join(c.id for c in sau), cs.id)]

    # ================================================================== snapshot
    def tao_snapshot(self, *, ten: str, ghi_chu: str = "", boi: str = "human",
                     kind: str = "named", passed: list[str] | None = None) -> Any:
        """§E6.2 — ghi một bản ưng ý.

        `kind="checkpoint"` cho bản ngầm (không tên, không hiện trong danh sách).
        Người tạo thì `boi="human"` và **luôn được** (R0); tác tử đề xuất thì đã phải
        đi qua thẻ G-SNAP trước khi tới đây, và chính người đặt tên.
        """
        from . import snapshot as sn

        if kind in ("named", "release"):
            if not ten.strip():
                raise ValueError("Bản ưng ý phải có tên — đó là thứ dẫn anh quay về "
                                 "đúng chỗ khi không còn nhớ hôm đó làm gì.")
            trung = self.snapshots.theo_ten(ten)
            if trung is not None:
                raise ValueError(
                    f"Đã có bản ưng ý tên “{ten}” ({trung.id}, {trung.ts[:10]}). "
                    "Đặt tên khác để hai bản không lẫn vào nhau.")

        xuat = sn.xuat_kho(self.store)
        h = self.blobs.put(_json(xuat))
        md = self.paths.eide_md
        tag = None
        if self.git_san:
            sha = self.vcs.sha_hien_tai()
            if sha and kind in ("named", "release"):
                tag = f"snap/{_ten_tag(ten)}"
                try:
                    self.vcs._git("tag", "-f", tag, sha)
                except GitKhongSan:
                    tag = None

        dem = self.store.counts()
        s = sn.Snapshot(
            id=self.ids.next("snap"), ts=sn._now(), kind=kind, name=ten,
            note=ghi_chu, created_by=boi,
            at_changeset=(self.log.all()[-1].id if self.log.all() else None),
            chip=_chip_dang_ghim(self.store),
            passed=passed or [],
            contents={
                "git_tag": tag,
                "git_sha": self.vcs.sha_hien_tai() if self.git_san else None,
                "store_export_hash": h,
                "eide_md_hash": self.blobs.put(md.read_text("utf-8")) if md.exists() else None,
                "docs": [d["id"] for d in self.store.list("doc", limit=50)],
                "facts_tier_counts": self.store.fact_tier_counts(),
                "so_req": dem.get("req", 0),
                "so_tep": dem.get("code", 0) + dem.get("config", 0),
                "so_changeset": len(self.log.all()),
            })
        self.snapshots.ghi(s)
        self.ledger.append("note", {"snapshot": s.id, "kind": kind, "name": ten})
        return s

    def se_mat_gi_khi_khoi_phuc(self, snap_id: str) -> dict[str, Any]:
        """Liệt kê hậu quả TRƯỚC khi hỏi — nội dung thẻ G-HIST (§E6.3)."""
        from . import snapshot as sn

        s = self.snapshots.get(snap_id)
        if s is None:
            return {"ok": False, "message_vi": f"Không có bản ưng ý nào mã {snap_id}."}
        cu = self.blobs.get(s.contents.get("store_export_hash") or "")
        if cu is None:
            return {"ok": False,
                    "message_vi": f"{snap_id} mất bản sao nội dung kho — không khôi phục "
                                  "được. Đây là lỗi toàn vẹn, hãy báo lại."}
        sau = self.log.sau(s.at_changeset) if s.at_changeset else self.log.all()
        return {"ok": True, "snapshot": s.to_dict(),
                **sn.se_mat_gi(sn.xuat_kho(self.store), _unjson(cu), changeset_sau=sau)}

    def khoi_phuc_snapshot(self, snap_id: str, *, by: str = "human",
                           giu_ban_hien_tai: str | None = None) -> KetQuaHoanTac:
        """§E6.3 — khôi phục KHÔNG ghi đè lịch sử: nó tạo một changeset mới.

        `giu_ban_hien_tai` = tên nhánh ⇒ bản hiện tại được ghi lại thành snapshot và
        một nhánh mới được tạo từ đó, rồi mới khôi phục. Đây là gợi ý mà §E6.3 nói thẻ
        G-HIST nên đưa ra khi người dùng có sửa chưa nằm trong bản ưng ý nào.
        """
        s = self.snapshots.get(snap_id)
        if s is None:
            return KetQuaHoanTac(False, message_vi=f"Không có bản ưng ý nào mã {snap_id}.")
        data = self.blobs.get(s.contents.get("store_export_hash") or "")
        if data is None:
            return KetQuaHoanTac(
                False, message_vi=f"{snap_id} mất bản sao nội dung kho — không khôi phục "
                                  "được.")

        canh: list[str] = []
        if giu_ban_hien_tai:
            try:
                cu = self.tao_snapshot(ten=giu_ban_hien_tai,
                                       ghi_chu=f"bản trước khi khôi phục {snap_id}",
                                       boi=by)
                canh.append(f"Bản hiện tại đã được ghi thành “{giu_ban_hien_tai}” ({cu.id}).")
            except ValueError as e:
                canh.append(f"Không ghi lại được bản hiện tại: {e}")

        self.tao_snapshot(ten="", kind="checkpoint",
                          ghi_chu=f"ngầm, trước khi khôi phục {snap_id}", boi="eide")

        xuat = _unjson(data)
        cs_id = self.ids.next("cs")
        cham = self._ap_ban_xuat(xuat, cs_id)

        if self.git_san and s.contents.get("git_sha"):
            try:
                self.vcs._git("checkout", s.contents["git_sha"], "--", ".")
                self.vcs.commit(cs_id=cs_id, author=by,
                                summary=f"khôi phục tệp về {snap_id}")
            except GitKhongSan as e:
                canh.append(f"Phần tệp không khôi phục được bằng git: {e}")

        moi = Changeset(
            id=cs_id, ts=cs_mod._now(), author=by,
            touches=[cs_mod.Touch(i, "artefact", "restore") for i in cham],
            forward=[{"kind": "snapshot_restore", "snapshot": snap_id}],
            inverse=[],
            explain={
                "summary": f"Khôi phục về bản ưng ý “{s.name or snap_id}”",
                "why": f"Người ra lệnh quay về {snap_id} ({s.ts[:10]}).",
                "sources": [{"kind": "changeset", "ref": snap_id, "tier": "VANG"}],
                "diff_prev": f"{len(cham)} hiện vật quay về trạng thái lúc {s.ts[:16]}",
                "next": "Xem lại kết quả; bản trước khi khôi phục vẫn còn trong lịch sử.",
                "confidence": "VANG"})
        self._chot(moi)

        return KetQuaHoanTac(
            True, changeset_moi=moi.id, da_lui=[snap_id], canh_bao=canh,
            message_vi=(f"Đã khôi phục về “{s.name or snap_id}” bằng changeset {moi.id}. "
                        f"{len(cham)} hiện vật đổi. Lịch sử không mất gì — bản trước khi "
                        f"khôi phục vẫn nằm trong dòng thời gian."))

    def _ap_ban_xuat(self, xuat: dict[str, Any], cs_id: str) -> list[str]:
        """Đặt kho về đúng trạng thái trong bản xuất. Trả danh sách hiện vật đã chạm."""
        cham: list[str] = []
        trong_snap = {a["id"] for a in xuat.get("artefacts", [])}

        for a in xuat.get("artefacts", []):
            hien = self.store.get(a["id"])
            if hien is None or hien["canonical"] != a["canonical"]:
                self.store.apply(artefact_id=a["id"], type=a["type"], op="update",
                                 author="eide", canonical=a["canonical"],
                                 explain=a.get("explain") or
                                         {"summary": f"khôi phục theo {cs_id}"},
                                 changeset_id=cs_id)
                cham.append(a["id"])

        # Hiện vật sinh ra SAU bản ưng ý thì không còn trong đó — gỡ bỏ.
        for a in self.store.list(limit=5000):
            if a["id"] not in trong_snap:
                self.store.apply(artefact_id=a["id"], type=a["type"], op="delete",
                                 author="eide", canonical={},
                                 explain={"summary": f"gỡ theo khôi phục {cs_id}"},
                                 changeset_id=cs_id)
                cham.append(a["id"])

        for f in xuat.get("facts", []):
            g = dict(f)
            for k in ("source", "explain"):
                if isinstance(g.get(k), str):
                    try:
                        g[k] = _unjson(g[k].encode())
                    except Exception:                        # noqa: BLE001
                        g[k] = {}
            g["min"], g["typ"], g["max"] = g.get("vmin"), g.get("vtyp"), g.get("vmax")
            self.store.put_fact(g)
        return cham

    def so_sanh_snapshot(self, a_id: str, b_id: str) -> dict[str, Any]:
        """§E6.3 — bảng theo loại hiện vật. `b_id="hien_tai"` để so với trạng thái bây giờ."""
        from . import snapshot as sn

        a = self.snapshots.get(a_id)
        if a is None:
            return {"ok": False, "message_vi": f"Không có bản ưng ý nào mã {a_id}."}
        da = self.blobs.get(a.contents.get("store_export_hash") or "")
        if da is None:
            return {"ok": False, "message_vi": f"{a_id} mất bản sao nội dung kho."}

        if b_id in ("hien_tai", "", None):
            db, ten_b, ts_b = sn.xuat_kho(self.store), "hiện tại", ""
        else:
            b = self.snapshots.get(b_id)
            if b is None:
                return {"ok": False, "message_vi": f"Không có bản ưng ý nào mã {b_id}."}
            raw = self.blobs.get(b.contents.get("store_export_hash") or "")
            if raw is None:
                return {"ok": False, "message_vi": f"{b_id} mất bản sao nội dung kho."}
            db, ten_b, ts_b = _unjson(raw), b.name or b.id, b.ts[:16]

        kb = sn.so_sanh_kho(_unjson(da), db)
        return {"ok": True, "tu": {"id": a_id, "ten": a.name or a_id, "ts": a.ts[:16]},
                "sang": {"id": b_id, "ten": ten_b, "ts": ts_b},
                "khac_biet": [k.to_dict() for k in kb],
                "giong_nhau": not kb,
                "message_vi": ("Hai bản giống hệt nhau." if not kb else
                               "Khác nhau ở: "
                               + ", ".join(f"{k.loai} ({len(k.them)}+/{len(k.bot)}-/"
                                           f"{len(k.doi)}~)" for k in kb))}

    # ================================================================== nhánh
    def tao_nhanh(self, ten: str, *, tu_snapshot: str | None = None) -> dict[str, Any]:
        """§E5.5 — nhánh để thử hai phương án song song.

        Nhánh gồm hai nửa: nhánh git cho tệp, và một **bản xuất kho** ghi lại trạng thái
        hiện vật tại điểm rẽ. Chuyển nhánh sẽ khôi phục nửa thứ hai.

        Đây chưa phải copy-on-write thật như §E5.5 mô tả — xem DEV-245.
        """
        if not self.git_san:
            return {"ok": False,
                    "message_vi": "Dự án không dùng được git nên chưa rẽ nhánh được."}
        try:
            hien = self.vcs._git("rev-parse", "--abbrev-ref", "HEAD").strip()
            self.vcs._git("checkout", "-b", ten)
        except GitKhongSan as e:
            return {"ok": False, "message_vi": f"Không tạo được nhánh: {e}"}

        s = self.tao_snapshot(ten=f"nhanh-{ten}", kind="checkpoint",
                              ghi_chu=f"điểm rẽ nhánh {ten} từ {hien}", boi="eide")
        self.ledger.append("note", {"branch": ten, "tu": hien, "snapshot": s.id})
        return {"ok": True, "nhanh": ten, "tu_nhanh": hien, "snapshot": s.id,
                "message_vi": f"Đã rẽ nhánh “{ten}” từ “{hien}”. Mọi thay đổi từ giờ "
                              f"nằm trên nhánh này; “{hien}” giữ nguyên."}

    def chuyen_nhanh(self, ten: str) -> dict[str, Any]:
        if not self.git_san:
            return {"ok": False, "message_vi": "Dự án không dùng được git."}
        self.tao_snapshot(ten="", kind="checkpoint",
                          ghi_chu=f"ngầm, trước khi chuyển sang nhánh {ten}", boi="eide")
        try:
            self.vcs._git("checkout", ten)
        except GitKhongSan as e:
            return {"ok": False, "message_vi": f"Không chuyển được: {e}"}
        return {"ok": True, "nhanh": ten,
                "message_vi": f"Đang ở nhánh “{ten}”."}

    def nhanh_hien_tai(self) -> str:
        if not self.git_san:
            return "main"
        return self.vcs._git("rev-parse", "--abbrev-ref", "HEAD", check=False).strip() or "main"

    def danh_sach_nhanh(self) -> list[str]:
        if not self.git_san:
            return []
        out = self.vcs._git("branch", "--format=%(refname:short)", check=False)
        return [x.strip() for x in out.splitlines() if x.strip()]

    # ================================================================== đọc
    def danh_sach_snapshot(self, *, gom_checkpoint: bool = False) -> list[dict[str, Any]]:
        ds = self.snapshots.all(gom_checkpoint=gom_checkpoint)
        tong_cs = len(self.log.all())
        ra = []
        for s in ds:
            d = s.to_dict()
            d["tom_tat"] = s.tom_tat()
            d["khoang_cach"] = tong_cs - int(s.contents.get("so_changeset", 0) or 0)
            ra.append(d)
        return ra

    def danh_sach(self, *, limit: int = 60, tac_gia: str | None = None,
                  hien_vat: str | None = None) -> list[dict[str, Any]]:
        ds = self.log.all()
        if tac_gia:
            ds = [c for c in ds if c.author.startswith(tac_gia)]
        if hien_vat:
            ds = [c for c in ds if any(t.artefact_id == hien_vat for t in c.touches)]
        return [self.tom_tat(c) for c in ds[-limit:]]

    def tom_tat(self, cs: Changeset) -> dict[str, Any]:
        return {
            "id": cs.id, "ts": cs.ts, "author": cs.author, "run_id": cs.run_id,
            "tom_tat": cs.tom_tat(),
            "cham": [t.artefact_id for t in cs.touches],
            "hoan_tac_duoc": cs.reversible and not cs.undone_by,
            "ly_do_khong_hoan_tac": cs.ly_do_khong_hoan_tac(),
            "da_hoan_tac_boi": cs.undone_by,
            "stale": cs.stale_marked,
            "cua_nguoi": cs.by_human,
            "da_duoc_nhac": bool(cs.acknowledged_by_agent),
            "la_checkpoint": any(f.get("kind") == "checkpoint" for f in cs.forward),
            "note": cs.note,
        }

    def diff(self, cs_id: str) -> dict[str, Any]:
        cs = self.log.get(cs_id)
        if cs is None:
            return {"ok": False, "message_vi": f"Không có changeset {cs_id}."}
        out: dict[str, Any] = {"ok": True, "id": cs.id, "explain": cs.explain,
                               "cham": [t.to_dict() for t in cs.touches], "diff": []}
        for f in cs.forward:
            if f.get("kind") == "file" and f.get("sha") and self.git_san:
                out["diff"].append({"kind": "file", "patch": self.vcs.diff(f["sha"])})
            elif f.get("kind") == "store":
                out["diff"].append({"kind": "store", "artefact_id": f["artefact_id"],
                                    "version": f.get("version"),
                                    "canonical": f.get("canonical")})
        return out


# =========================================================================== phụ
def _json(o) -> str:
    import json
    return json.dumps(o, ensure_ascii=False, sort_keys=True, default=str)


def _unjson(b) -> dict:
    import json
    return json.loads(b.decode("utf-8") if isinstance(b, (bytes, bytearray)) else b)


def _ten_tag(ten: str) -> str:
    """Tên bản ưng ý → tên tag git hợp lệ. Giữ chữ người đọc được, bỏ ký tự git cấm."""
    import re
    import unicodedata
    t = ten.replace("đ", "d").replace("Đ", "D")
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", t).strip("-.")
    return t or "khong-ten"


def _chip_dang_ghim(store) -> str | None:
    ds = store.list("passport", limit=1)
    return ds[0]["id"] if ds else None
