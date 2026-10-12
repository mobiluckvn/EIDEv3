**EIDE — NGƯỜI SỬA TRỰC TIẾP HIỆN VẬT CỦA AGENT, VÀ HOÀN TÁC NHIỀU TẦNG**

Mọi hiện vật Agent tạo ra đều sửa được ngay trên giao diện · mọi sửa của người là một changeset hoàn tác được · năm tầng lùi · khối diff · duyệt có sửa · bắt sửa từ bên ngoài

*Mã tài liệu EIDE-EDIT-47 · v1.0 · 12/10/2026 · sửa đổi MDD-40 v3.0 §D (UAP v1.1 → v1.2), §E4, §E5, §E6*

| | |
|---|---|
| **Mã tài liệu** | EIDE-EDIT-47 (Human Direct Edit & Multi-level Rollback) v1.0 |
| **Yêu cầu của chủ sản phẩm (12/10/2026)** | *"Các output của Agent người mới chỉ đọc mà chưa thể tương tác trực tiếp việc sửa sản phẩm đó… nếu người sửa trực tiếp thì cần giao diện gì và chúng ta quản lý như thế nào để nếu người sửa có lỗi có thể rollback về trạng thái trước đó."* |
| **Quan hệ** | Mở rộng §E4 (đường ống sửa của người) từ 4 ô bảng lên mọi hiện vật; nối các cơ chế đã có trong `history.py` (hoàn tác lượt, khôi phục snapshot, nhánh) lên giao diện; thêm lệnh `diff.show` vào UAP; thêm nhánh `confirm` vào `loop.py`; thêm changeset `external` do watcher sinh |
| **Tương thích ngược** | 13 loại HumanAct giữ nguyên; `edit` chỉ **thêm** trường tuỳ chọn; 16 lệnh UICommand giữ nguyên, thêm 1 lệnh mới; khối `table` cũ không có `sua_duoc` vẫn vẽ như trước; mọi cơ chế mới nằm sau cờ `EIDE_FEATURE_*` trừ phần thuần giao diện |
| **Ngày** | 12/10/2026 |
| **Đề tài** | PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI) |
| **Khung** | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu |
| **Tác giả** | Vũ Trí Công (đặc tả soạn cùng Claude) |

***Lịch sử sửa đổi***

| Phiên bản | Ngày | Nội dung | Người sửa |
|---|---|---|---|
| v1.0 | 12/10/2026 | Bản đầu: chẩn đoán 7 chỗ đứt; bất biến I7–I10; UAP v1.2; bảy gói DEV-365…DEV-371 kèm đặc tả mã, ca kiểm, tiêu chí chấp nhận; thứ tự làm; chỉ số đo | VTC |

---

## 0 · Hướng dẫn cho Claude Code khi thực hiện tài liệu này

Đọc mục này trước khi chạm vào mã.

1. **Đọc trước:** `README.md` §2–§3 và §10; `docs/md/EIDE-DEV-LOG.md` (ba mục cuối, để quen giọng và quy ước); `src/eide/protocol/humanact.py`; `src/eide/protocol/uicommand.py`; `src/eide/loop.py` từ `_nguoi_sua` (dòng ~1249) tới hết `_nguoi_re_nhanh`; `src/eide/history.py`; `src/eide/human_edit.py`; `ui/EIDEApp/Sources/EIDE/Protocol/UAP.swift`; `ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift` (đặc biệt `OSuaDuoc`, `KhoiBang`, `KhoiChangeset`); `ui/EIDEApp/Sources/EIDE/State/AppState.swift` (`gui`, bộ `switch` lệnh lõi).
2. **Sáu bất biến của UAP (I1–I6, đầu `UAP.swift`) là luật.** Giao diện không tự quyết (I3); mọi cái chạm đi qua `console.act` (I1); chỉ `decide` có `gate_id` mới mở cổng (I6). Tài liệu này thêm bốn bất biến I7–I10 ở §2 — cũng là luật.
3. **Mỗi gói DEV là một lần giao:** mã + ca kiểm + một mục `## [DEV-xxx]` trong `EIDE-DEV-LOG.md` viết theo giọng của log (nói rõ chỗ làm khác đặc tả và vì sao, nói rõ chỗ chưa làm). Làm xong gói nào chạy `.venv/bin/python -m pytest -q` và `cd ui/EIDEApp && swift test` trước khi sang gói sau.
4. **Cờ tính năng:** phần nào đổi *thứ Agent nhìn thấy hoặc làm được mỗi lượt* thì đặt sau cờ trong `Features` (`src/eide/config.py`), mặc định TẮT, có ghi vào `README.md` §8 như mười ba cờ hiện có. Phần thuần giao diện nối vào cơ chế lõi đã có (DEV-365) **không** cần cờ.
5. **Không làm:** không nới `_sua_hien_vat` bằng cách thêm nhánh `if t.type == ...` cho từng loại (xem chú thích trong `_nguoi_sua` về `symbol`) — gói DEV-368 thay cách ấy bằng đường dẫn trường lồng; không để giao diện suy ra ô nào sửa được từ tên cột — lõi khai; không tạo changeset theo từng phím gõ; không ghi đè `EIDE.md` bằng đường ghi tệp thường.
6. **Mỗi gói phải có ít nhất một ca kiểm "đi đúng đường người đi"** (người bấm ở tab → HumanAct → lõi → changeset → lượt sau Agent thấy trong `EIDE.md §Người vừa sửa` và tab A11). Bài học của dự án (README §8): kiểm *thứ làm việc* không thay được kiểm *đường dẫn tới nó*.
7. Nếu một chỗ trong tài liệu này mâu thuẫn với mã đang chạy, **mã đang chạy thắng về dữ kiện, tài liệu thắng về ý định**: giữ ý định, chỉnh chi tiết, và ghi chỗ chỉnh vào DEV-LOG.

---

## 1 · Chẩn đoán: cơ chế có sẵn, đường lên giao diện đứt

Rà ngày 12/10/2026 trên mã hiện tại:

| # | Lõi đã có | Giao diện | Bằng chứng |
|---|---|---|---|
| 1 | `edit` hiện vật theo trường, phân loại sửa, STALE, Fact NGƯỜI | Chỉ **4 bảng**: A2.1 (`text`, `criteria`), A5.8c (`symbol` kiểu chân), A8 (`criteria` ngưỡng), A14 mục EIDE.md; chỉ trường cấp 1 | `surfaces.py:203, 899, 1406, 1702`; `OSuaDuoc` ở `SurfaceView.swift:519` |
| 2 | `_sua_tep` — sửa tệp có `base_version`=hash, 3-way merge, thẻ xung đột | **Không** có trình soạn tệp; khối `code` là `Text(...)` chỉ chọn-copy | `loop.py:1438`; `SurfaceView.swift:195` |
| 3 | `tao_snapshot`, `khoi_phuc_snapshot`, `tao_nhanh`, `chuyen_nhanh`, `gop_nhanh`, `se_mat_gi_khi_khoi_phuc`, `so_sanh_snapshot` | Không có nút nào gửi `snapshot`/`branch`; không có "về bản chốt" | `history.py:421–917`; grep `kind: .snapshot` trong `Views/` = 0 |
| 4 | `hoan_tac_luot(run_id)` | Chỉ "Hoàn tác" từng changeset ở A11 | `history.py:288`; `SurfaceView.swift:1079` |
| 5 | `confirm` ("xác nhận/từ chối/sửa Fact hoặc nguồn" — đường BẠC→VÀNG "chỉ người đi được") | Không gửi; **`loop.py` cũng không có nhánh xử lý** `confirm` | `humanact.py:28`; grep `"confirm"` trong `loop.py` = 0 |
| 6 | `bac_bo` (bác bỏ phát hiện → EIDE.md §Đừng) | Không có nút trên dòng ERC / phân tích | `human_edit.py:75` |
| 7 | Thẻ xung đột có lựa chọn "Để tôi xem diff rồi quyết"; `history.diff(cs_id)`, `vcs.diff` | Không có khối `diff`; `hai_ban` bị cắt 4000 ký tự và hiện như chữ thường | `loop.py:1548`; UICommand không có lệnh diff |
| 8 | Changeset `kind="external"` | Không ai tạo nó — **không có watcher**; sửa bằng VS Code là vô hình với EIDE cho tới khi Agent đọc lại tệp | `changeset.py:385`; grep FSEvents/watchdog = 0 |
| 9 | `set` (đổi thiết lập) | Không gửi; 13 cờ phải sửa `.env` rồi khởi động lại | `humanact.py:31` |

Hệ quả: ≈28 loại hiện vật trong kho (`block_diagram`, `netlist`, `plan`, `option`, `adr`, `doc`, `ui_screen`, `bom`, `pinout`, `procedure`, `report`, `display`…) người chỉ đọc được. Luật nền số 3 của README ("mọi thay đổi gỡ lại được, kể cả do người gõ") hiện chỉ đúng với 4 ô bảng và sai với mọi tệp người sửa bên ngoài.

---

## 2 · Bất biến mới (thêm vào sáu bất biến của UAP)

- **I7 — Sửa trên gốc, không sửa trên bản dựng.** Người chỉ sửa `canonical` của hiện vật hoặc nội dung tệp nguồn; SVG, HTML, Markdown dựng ra, bảng tóm tắt là hình chiếu và không nhận sửa. (Đã đúng với `ui_screen` → HTML/C ở DEV-364; nay áp cho mọi hiện vật.)
- **I8 — Lõi khai ô nào sửa được.** Mỗi khối gửi kèm `sua_duoc` (đặc tả sửa được, §3.2). Giao diện không suy ra từ tên cột, không có bảng trắng phía Swift. Khối không có `sua_duoc` là khối chỉ đọc.
- **I9 — Lưu của người là nguyên tử và luôn được (R0).** Lõi kiểm hợp lệ trước; không hợp lệ thì không có changeset nào và báo lý do; hợp lệ thì đúng một changeset `author=human`. Không có "lưu một nửa". Không cổng nào chắn người sửa hiện vật của họ; cái qua cổng là Agent ghi đè bản người vừa sửa (G-FILE) và Agent hoàn tác sửa của người (G-HIST).
- **I10 — Trước lần sửa đầu tiên của người trong một lượt có một mốc lùi.** Đối xứng với luật Agent "tự đánh mốc lùi ở lần sửa đầu mỗi lượt" (README §4.6). Mốc là `history.checkpoint(ly_do="trước khi anh sửa …")`, không phải snapshot có tên.

---

## 3 · Giao thức UAP v1.2

### 3.1 · `HumanAct kind=edit` — mở rộng `data` (tương thích ngược)

```jsonc
{
  "kind": "edit",
  "target": {"type": "req|criteria|plan|option|adr|bom|pinout|display|ui_screen|block_diagram|…|file|code", "id": "…"},
  "data": {
    "base_version": "v7" /* hiện vật */ | "<sha256 nội dung>" /* tệp */,   // bắt buộc (đã có)

    // --- một trong ba dạng sửa (đúng một) ---
    "fields": {"text": "…"},                      // dạng cũ: trường cấp 1 (giữ nguyên)
    "patch":  [                                   // MỚI — đường dẫn lồng, theo JSON-Pointer rút gọn
      {"path": "assert/2/nguong", "value": 5.0},
      {"path": "steps/0/ten",     "value": "Đọc datasheet"},
      {"path": "elements/3",      "op": "remove"},
      {"path": "elements/-",      "op": "add", "value": {…}},
      {"path": "elements/1",      "op": "move", "to": "elements/4"}
    ],
    "content": "…toàn bộ nội dung tệp mới…",       // dạng tệp (giữ nguyên)

    "summary": "sửa ngưỡng A2 của sim-01",          // tuỳ chọn (đã có)
    "session_id": "es-12",                           // MỚI — phiên sửa, để gom (§5.1 DEV-365)
    "bac_bo": true,                                  // đã có trong lõi, nay giao diện gửi được
    "lock_broken": true                              // đã có
  },
  "origin": {"surface": "simulation", "block": "A8.2", "row": "sim-01"},
  "note": "vì sao anh đổi"
}
```

Luật ở `HumanAct.validate()`: `edit` phải có **đúng một** trong `fields` / `patch` / `content`; `patch[].op` ∈ {`set` (mặc định), `add`, `remove`, `move`}; `path` không được rỗng, không được chứa `..`.

### 3.2 · `sua_duoc` — đặc tả sửa được, đính vào khối (I8)

Lõi (`surfaces.py`) thêm vào bất kỳ khối nào (table, kv, cay, list, sections, code, html) một trường:

```jsonc
"sua_duoc": {
  "loai": "criteria",                 // target.type khi gửi edit
  "id_tu": "row",                     // lấy target.id từ: "row" (cột đầu của dòng) | "block" (block.ma_hien_vat) | "cell"
  "phien_ban_tu": "row_meta.phien_ban",
  "truong": [
    {"path": "assert/{row}/nguong", "cot": "Ngưỡng", "kieu": "so", "don_vi": "tu_tieu_chi",
     "bat_buoc": true, "gay_stale": true, "goi_y": "ngưỡng đo, số thực"},
    {"path": "assert/{row}/ghi_chu", "cot": "Ghi chú", "kieu": "chu", "gay_stale": false}
  ],
  "them_xoa": {"path": "assert", "mau": {"ma": "", "nguong": 0, "so_sanh": ">="}},   // tuỳ chọn: cho phép thêm/xoá dòng
  "bac_bo_duoc": false,               // true ⇒ giao diện vẽ nút "Không phải lỗi" trên dòng
  "xac_nhan_duoc": false              // true ⇒ nút "Xác nhận ✓" (kind=confirm) trên dòng
}
```

`kieu` ∈ `chu` | `van_ban_dai` | `so` | `so_nguyen` | `chon` (kèm `lua_chon: [...]`) | `bool` | `ma` (monospace). Giao diện vẽ ô theo `kieu`, kiểm sơ bộ (số phải là số) nhưng **lõi kiểm lại và quyết** (I9).

`cot_sua` / `editable_fields` cũ giữ để tương thích; lõi sinh `sua_duoc` tương đương từ chúng trong một hàm `_sua_duoc_tu_cot_sua()` để không phải sửa 4 bảng cũ ngay.

### 3.3 · Lệnh lõi mới: `diff.show` (lệnh thứ 17)

```jsonc
{"method": "diff.show", "params": {
  "diff_id": "d-31",
  "tieu_de": "main.c — bản của anh ↔ bản của tác tử",
  "loai": "tep" | "hien_vat",
  "trai":  {"nhan": "Bản của anh (v7)",   "noi_dung": "…", "hash": "…"},
  "phai":  {"nhan": "Bản hiện tại (v8)", "noi_dung": "…", "hash": "…"},
  "goc":   {"nhan": "Bản gốc chung",      "noi_dung": "…"},        // tuỳ chọn, cho 3-way
  "hunks": [ {"dong_trai": 40, "dong_phai": 40, "loai": "doi|them|xoa|xung_dot", "trai": "…", "phai": "…"} ],
  "cho_phep_sua": true,                 // người sửa được cột phải rồi "Lưu" / "Duyệt với bản đã sửa"
  "gan_voi": {"card_id": "card-9"} | {"gate_id": "g-17"} | {"snapshot": "snap-3"} | null
}}
```

Lõi tính `hunks` bằng `difflib` cho hiện vật (so JSON canonical đã in đẹp) và bằng `git diff --no-index` / `difflib` cho tệp. Giao diện chỉ vẽ.

Kết quả của khối diff đi về lõi bằng HumanAct đã có: `edit` (nếu người sửa rồi Lưu), `decide` (nếu gắn cổng, kèm `data.amended_content`/`amended_patch` — §DEV-370), hoặc `choose` (thẻ xung đột).

### 3.4 · `HumanAct kind=confirm` — định nghĩa `data` (lõi chưa xử lý, DEV-368)

```jsonc
{"kind": "confirm", "target": {"type": "fact", "id": "12"},
 "data": {"verdict": "dung" | "sai" | "sua", "gia_tri_moi": "3.3", "nguon": "datasheet p.12"}, "note": "…"}
```

`dung` → nâng tầng BẠC→VÀNG, ghi `confirmed_by=human_act:<id>`; `sai` → tầng ĐỒNG + đánh STALE hạ nguồn; `sua` → Fact mới tầng NGƯỜI thay thế, Fact cũ STALE.

### 3.5 · `HumanAct kind=set` — khoá cho cờ tính năng (DEV-371)

`data.key = "feature.<TEN_CO>"`, `data.value = true|false`. Lõi ghi vào `<dự án>/.eide/settings.json` (không ghi `.env`), áp từ lượt sau, ghi ledger `setting`.

---

## 4 · Ba trình soạn chung (phía Swift)

| Trình soạn | Dùng cho | Nhận đầu vào | Gửi ra |
|---|---|---|---|
| **A. Biểu mẫu / bảng** (`FormEditor`) | mọi hiện vật JSON: req, criteria, option, adr, plan (bước), bom, pinout, display, phần tử `ui_screen`, cây khối (thuộc tính nút) | khối + `sua_duoc` | `edit` với `patch` |
| **B. Văn bản / mã** (`TextEditor` — NSTextView bọc) | tệp ở A7, nguồn Markdown ở A3, `EIDE.md`, Makefile, `.v`, `.c`, `.cst` | `file.open` (RPC mới, §DEV-367) trả nội dung + hash | `edit` với `content` |
| **C. Cấu trúc trên canvas** (`CanvasEditor`) | A4/A5 sơ đồ khối, A15 khung thiết bị | SVG/HTML đã có + `sua_duoc` của phần tử | bước 1: chọn phần tử → mở A ở cạnh; bước 2 (sau): kéo-thả sinh `patch op=move/set` |

Nguyên tắc chung cho cả ba: ô "vì sao anh đổi?" luôn ở cạnh nút Lưu (giữ cách `OSuaDuoc` đang làm); Lưu bị khoá khi giá trị không đổi; sau Lưu hiện **toast** có nút "Hoàn tác" sống 30 giây (§DEV-365); trong lúc đang sửa, khối hiện viền "đang sửa — Agent sẽ không ghi vào đây" (nhận `surface.lock` với `by="human"`).

---

## 5 · Các gói nâng cấp

Mỗi gói: mục tiêu → thay đổi lõi → thay đổi giao diện → ca kiểm → tiêu chí chấp nhận → ước lượng. Số DEV tiếp theo số cuối trong `EIDE-DEV-LOG.md` (DEV-364).

### DEV-365 · Nối nút vào cơ chế lùi đã có — năm tầng hoàn tác

**Mục tiêu.** Người làm được từ giao diện mọi việc `history.py` đã hỗ trợ: ghi bản chốt, rẽ/chuyển nhánh, về bản chốt (có xem trước mất gì), lùi cả lượt, hoàn tác ngay sau khi lưu; và mỗi lần người bắt đầu sửa tự có một mốc (I10). Không cần cờ.

**Lõi.**
- `loop.py`:
  - `_nguoi_hoan_tac`: thêm `t.type == "snapshot"` → `self.history.khoi_phuc_snapshot(t.id, by="human", giu_ban_hien_tai=act.data.get("giu_ban_hien_tai"))`; thêm `t.type == "session"` → hoàn tác mọi changeset có `human_act.session_id == t.id` (duyệt `history.danh_sach(tac_gia="human")`, lọc theo `session_id` ghi trong `explain.sources[0].session`).
  - `_nguoi_re_nhanh`: thêm `action == "merge"` → `self.history.gop_nhanh(ten, by="human")`; trả kết quả xung đột (nếu có) bằng `diff.show` (sau DEV-366; trước đó bằng `console_post`).
  - `_nguoi_sua`: ở đầu, nếu `ctx.run_id` chưa có mốc do người → `self.history.checkpoint(ly_do=f"trước khi anh sửa {t}", run_id=ctx.run_id)`; nhớ trong `self._moc_nguoi_trong_luot: set[str]`, xoá ở đầu mỗi `console_act`.
  - Ghi `session_id` (nếu có) vào `explain.sources[0]["session"]` trong `_explain_cua_nguoi`.
- `uicommand.history_update`: thêm tham số `snapshots: list` và `nhanh: {"hien_tai": str, "danh_sach": [str]}` để giao diện có dữ liệu vẽ nút mà không phải `paint` cả tab.
- RPC mới (read-only, 0 token): `history.preview_restore {snapshot_id}` → trả `history.se_mat_gi_khi_khoi_phuc(snap_id)`.

**Giao diện.**
- Thanh trạng thái (`RootView.swift:328` mục "Bản ưng ý"): bấm → menu: *Ghi bản ưng ý…* (hỏi tên → `HumanAct(kind:.snapshot, data:["name":…,"note":…])`), *Về bản…* (danh sách snapshot → gọi `history.preview_restore` → sheet "Sẽ mất: … · Giữ bản hiện tại thành nhánh? [tên]" → `HumanAct(kind:.undo, target: snapshot:<id>, data:["mode":"restore_branch","giu_ban_hien_tai": tênNhánh?])`), *Nhánh ▸* (tạo / chuyển / gộp → `kind:.branch`).
- Console: cuối mỗi lượt Agent có ≥1 changeset → dòng nhỏ "Lượt này: N thay đổi · **Lùi cả lượt**" → `HumanAct(kind:.undo, target: run:<run_id>, data:["mode":"revert"])`.
- Toast sau mỗi Lưu của người (mọi trình soạn): "Đã ghi `cs-123` · **Hoàn tác**" (30 s) → `kind:.undo, target: changeset:<id>`; nếu có `session_id` thì target `session:<id>`.
- `AppState`: thêm `snapshots`, `nhanh` từ `history.update`; thêm `sessionSua: String?` (sinh `es-<n>` khi mở trình soạn, xoá khi đóng hoặc sau 2 phút không gõ).

**Ca kiểm.**
- `tests/test_edit47_nut_lui.py`: (1) `undo` target `snapshot` → changeset mới, snapshot không bị xoá, `stale_moi` đúng; (2) `undo` target `run` → mọi changeset của lượt lùi, phần `ly_do_khong_hoan_tac` giữ nguyên và được kê; (3) lần `edit` đầu trong lượt sinh đúng 1 checkpoint, lần thứ hai không sinh thêm; (4) `branch action=merge` xung đột → không ghi đè, trả danh sách xung đột; (5) `preview_restore` không tạo changeset nào (đếm `changesets.jsonl` trước/sau).
- `ui/EIDEApp/Tests`: (6) bấm "Ghi bản ưng ý" với tên rỗng → không gửi HumanAct; (7) toast "Hoàn tác" gửi đúng `target` và biến mất sau 30 s; (8) "Lùi cả lượt" chỉ hiện khi lượt có changeset.

**Tiêu chí chấp nhận.** Từ giao diện, không gõ một chữ nào vào ô chat, người làm được: ghi bản chốt → sửa một ô → lùi bằng toast → sửa lại → về bản chốt với xem trước; `ledger.jsonl` ghi đủ `human_act` cho từng bước; A11 hiện đủ.

**Ước lượng.** 1–2 ngày.

---

### DEV-366 · Khối `diff` — thẻ xung đột thật, cổng G-FILE hiện diff, xem trước khôi phục

**Mục tiêu.** Mọi chỗ EIDE đang nói "xem diff" đều có diff để xem. Cờ: không cần (thuần trình bày), nhưng phần "G-FILE kèm diff" nằm sau `EIDE_FEATURE_CONG_CO_DIFF` vì nó đổi nội dung thẻ Agent dựng.

**Lõi.**
- `src/eide/diff_khoi.py` (mới): `dung_diff(*, loai, trai, phai, goc=None, tieu_de, cho_phep_sua, gan_voi) -> dict` tính `hunks` bằng `difflib.SequenceMatcher`; với hiện vật: `json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True)` hai bên rồi diff theo dòng; với 3-way: dùng `vcs.merge_ba_chieu` để đánh dấu hunk `xung_dot`.
- `uicommand.diff_show(**)` + thêm `"diff.show"` vào danh sách 17 lệnh và vào `tests/test_cau_giao_thuc.py`.
- `loop._the_xung_dot`: thay `hai_ban` cắt 4000 ký tự bằng `ctx.emit(uic.diff_show(...gan_voi={"card_id": card_id}, cho_phep_sua=True))`; lựa chọn thứ ba của thẻ đổi thành "Dùng bản tôi vừa sửa trong diff" — giao diện gửi `choose` kèm `answers.chon` và, nếu người sửa, thêm `edit` với `content`/`patch` mới trước khi `choose`.
- Cổng `G-FILE` (nơi dựng thẻ cho `file.write`/`code.*` trong `policy/`): khi cờ bật, kèm `diff_show(trai = nội dung hiện tại trên đĩa, phai = nội dung Agent định ghi, gan_voi={"gate_id"})`.
- `history.preview_restore` (DEV-365) trả thêm `diff_show` tóm tắt theo tệp/hiện vật (chỉ danh sách + số dòng đổi, không toàn văn, để không nặng).

**Giao diện.**
- `ui/EIDEApp/Sources/EIDE/Views/DiffView.swift` (mới): hai cột, số dòng, tô màu hunk, cuộn đồng bộ; cột phải thành NSTextView sửa được khi `cho_phep_sua`; nút theo `gan_voi`: *Lưu* (→ `edit`), *Duyệt với bản đã sửa* / *Duyệt nguyên bản* / *Từ chối* (→ `decide`), *Giữ trái* / *Giữ phải* / *Giữ bản đã sửa* (→ thẻ `choose`).
- `AppState`: `case "diff.show"` → lưu theo `diff_id`; thẻ/cổng có `gan_voi` thì vẽ diff ngay trong thẻ; không gắn thì hiện ở sheet.

**Ca kiểm.** `tests/test_edit47_diff.py`: hunks đúng cho đổi/thêm/xoá; 3-way đánh dấu `xung_dot` đúng đoạn; thẻ xung đột phát `diff.show` có `gan_voi.card_id` trùng `card_id`; cờ tắt → G-FILE không phát `diff.show`, cờ bật → có; `diff.show` là lệnh hợp lệ trong `uicommand` và giao diện không rơi vào nhánh "chưa biết vẽ".

**Tiêu chí chấp nhận.** Dựng lại ca xung đột (người và Agent sửa cùng tệp) trên phiên thật: người thấy hai bản cạnh nhau, sửa cột phải, bấm *Giữ bản đã sửa* → đúng nội dung ấy nằm trên đĩa và trong `blobs/`, một changeset `author=human`.

**Ước lượng.** 2–3 ngày.

---

### DEV-367 · Trình soạn tệp ở A7 / A3 và khoá mềm hai chiều

**Mục tiêu.** Người mở và sửa bất kỳ tệp nào trong thư mục dự án ngay trong EIDE; lưu đi qua `_sua_tep` đã có; trong lúc người đang mở tệp, Agent muốn ghi tệp đó phải qua cổng. Cờ `EIDE_FEATURE_KHOA_NGUOI` cho phần khoá (đổi hành vi Agent).

**Lõi.**
- RPC mới `file.open {path}` → kiểm hộp cát (lớp 3) → trả `{content, hash, size, loai, la_eide_md}`; `path` nằm ngoài gốc dự án → lỗi `E_SANDBOX` như công cụ đọc. Tệp > 2 MB → trả `qua_lon=true`, giao diện chỉ đọc. Ghi ledger `human_act`-ít-tốn: không ghi mỗi lần mở; ghi `attend` do giao diện gửi kèm.
- `EIDE.md`: `file.open` cho mở, nhưng `_sua_tep` với `path == "EIDE.md"` phải đi qua `self.eide_md` (cùng đường công cụ bộ nhớ) chứ không `p.write_text` — giữ luật README §4.10.
- Khoá hai chiều: `self.locks_nguoi: dict[str, str]` (path → session_id). `attend` với `origin.block == "editor"` + `data.path` + `data.dang_sua=true` → thêm khoá, phát `surface_lock("code", block=path, by="human", why="anh đang sửa")`; `dang_sua=false` hoặc hết 10 phút không gõ → bỏ. Hook trước `file.write`/`code.*` (lớp 2): nếu `path in self.locks_nguoi` và cờ bật → cổng `G-FILE` với lý do "anh đang mở tệp này" (kèm diff từ DEV-366). Agent đọc tệp vẫn tự do.
- `_sua_tep`: sau khi ghi, nếu tệp nằm trong `self.locks` (Agent đang giữ) → đường `lock_broken` đã có; ghi thêm `loai=doan_loai(path)` vào `ghi_tep`.
- Hook `E4020` (không ghi đè tệp chưa đọc hết): sau khi người lưu tệp, xoá tệp đó khỏi tập "đã đọc" của Agent trong lượt, để Agent phải đọc lại bản mới trước khi sửa.

**Giao diện.**
- A7.1 và A3 (cây tệp): dòng tệp có nút "Mở" → `TabEditorView` (sheet hoặc cột phải): NSTextView monospaced, số dòng, Cmd+S = Lưu, ô "vì sao" tuỳ chọn, nút *Lưu* gửi `edit{target: file:<path>, base_version: hash, content, summary, session_id}`; mở xong gửi `attend{data.path, dang_sua:true}`, đóng gửi `dang_sua:false`.
- Nhận `surface.lock by="agent"` cho đúng `path` đang mở → băng vàng "Agent đang sửa tệp này — lưu của anh sẽ được gộp 3 chiều".
- Nếu lõi trả `E_VERSION_CONFLICT` → thẻ xung đột (DEV-366) hiện trong chính trình soạn.
- Không highlight cú pháp ở bản đầu (ghi rõ trong DEV-LOG là chưa làm).

**Ca kiểm.** `tests/test_edit47_sua_tep.py`: `file.open` ngoài hộp cát bị chặn; lưu với hash đúng → changeset `author=human`, `noi_dung_truoc` đúng; hash lệch + gốc tìm được + không đụng đoạn → gộp sạch; hash lệch + đụng đoạn → `_XungDot` + `diff.show`; lưu `EIDE.md` đi qua `eide_md` (kiểm bằng dấu trong ledger); cờ bật: Agent `file.write` vào tệp đang khoá người → thẻ G-FILE; cờ tắt → không. Giao diện: Cmd+S gửi đúng `base_version`; đóng trình soạn gửi `dang_sua:false`.

**Tiêu chí chấp nhận.** Mở `main.c` ở A7, sửa một dòng, Cmd+S → A11 có changeset "anh sửa main.c", toast có Hoàn tác, Agent ở lượt sau nói "anh vừa sửa main.c" (từ `EIDE.md §Người vừa sửa`) và phải đọc lại tệp trước khi sửa (E4020 nổ nếu không).

**Ước lượng.** 3–5 ngày.

---

### DEV-368 · `sua_duoc` + trình soạn biểu mẫu lồng + nút "Không phải lỗi" + nhánh `confirm`

**Mục tiêu.** Phủ sửa trực tiếp từ 4 bảng lên mọi hiện vật JSON; xoá nhu cầu viết nhánh riêng cho từng loại; người bác bỏ phát hiện và xác nhận Fact bằng một nút. Cờ `EIDE_FEATURE_SUA_LONG` cho đường `patch` (vì nó đổi thứ Agent thấy ở lượt sau qua STALE), không cờ cho `sua_duoc` thuần trình bày.

**Lõi.**
- `src/eide/human_edit.py`: thêm `ap_patch(canonical: dict, patch: list[dict]) -> dict` (JSON-Pointer rút gọn: `a/b/2/c`, `-` = cuối mảng; `set|add|remove|move`); lỗi đường dẫn → `schema_violation` kèm đường dẫn sai; không bao giờ sửa tại chỗ (trả bản sao). `phan_loai()` nhận thêm `duong_dan_doi: list[str]` để xếp loại theo **đoạn đầu** của đường dẫn (`label/…`, `ghi_chu/…` → trình bày).
- `loop._sua_hien_vat`: nếu `data.patch` → `can = ap_patch(cu["canonical"], patch)`; so phiên bản như cũ; xung đột theo **đường dẫn** thay vì theo trường cấp 1. Xoá nhánh riêng `symbol` trong `_nguoi_sua` bằng cách cho A5.8c dùng `patch path="anh_xa/{ref}/chan/{i}/kieu"` (giữ hàm `_nguoi_xac_nhan_ky_hieu` cho tới khi ca kiểm SCH-14/15 chạy xanh trên đường mới, rồi xoá).
- `surfaces.py`: hàm `sua_duoc(...)` dựng dict §3.2; áp cho: A2.1 (req), A2.2 (option/adr: `chon`, `ly_do`), A2.3 (plan: `steps/{i}/ten|mo_ta|kiem_bang`), A4.x (bom: `so_luong`, `gia_tri`, `ghi_chu`; pinout: `chan/{i}/chuc_nang`), A5.1 (cây khối: `ten`, `mo_ta`), A8 (criteria: `assert/{i}/nguong|so_sanh`, `them_xoa`), A9 (`display`: các trường hồ sơ — **mỗi trường sửa phải kèm `nguon`**, không nguồn → Fact NGƯỜI), A15 (`ui_screen`: `elements/{i}/x|y|w|h|text|font|mau`), A14 mục EIDE.md. ERC/phân tích (A4 bảng phát hiện, A7.2 nhận định): `bac_bo_duoc=true`. A4 bảng Fact: `xac_nhan_duoc=true` cho dòng tầng BẠC.
- `loop.py`: thêm `if act.kind == "confirm": return self._nguoi_xac_nhan_fact(act, ctx)` theo §3.4; dùng `store.put_fact` với `tier` mới, ghi `ghi_kho(type="fact"…)` để có changeset và hoàn tác được; `sai` → `store.mark_stale` hạ nguồn của Fact (tra qua `deps`).
- `bac_bo`: `_sua_hien_vat` với `data.bac_bo=true` → `eide_md.note_dung(...)` (mục §Đừng) + đánh dấu hiện vật `canonical.bac_bo = {"boi": act.id, "ly_do": act.note}`; `surfaces` ẩn dòng bác bỏ sau một nút "hiện N dòng đã bác bỏ".

**Giao diện.**
- `ui/EIDEApp/Sources/EIDE/Views/FormEditor.swift` (mới): nhận `sua_duoc` + dòng/khối → vẽ ô theo `kieu`; gom nhiều ô đổi thành **một** `patch`; "vì sao" chung; thêm/xoá dòng khi có `them_xoa`.
- `KhoiBang`, `KhoiKV`, `KhoiCay`, `KhoiMuc`, `KhoiDanhSach`: nếu `block.sua_duoc != nil` → ô sửa được, thay cho `cotSua` hiện tại (giữ `cotSua` cho tới khi lõi phát `sua_duoc` ở cả 4 bảng cũ).
- Nút "Không phải lỗi" (→ `edit{bac_bo:true}` kèm `note` bắt buộc) và "Xác nhận ✓ / Sai ✗" (→ `confirm`).
- A15: bấm phần tử trong khung 1:1 → `FormEditor` ở cột cạnh (bước 1 của trình soạn C).

**Ca kiểm.** `tests/test_edit47_patch.py`: `ap_patch` 4 op, lỗi đường dẫn, không sửa tại chỗ; phân loại theo đoạn đầu (đổi `label` không STALE — ca CX08 vẫn xanh); xung đột theo đường dẫn: hai người đổi hai nhánh khác nhau của cùng hiện vật → gộp được; `confirm dung` nâng BẠC→VÀNG và có changeset; `confirm sai` STALE hạ nguồn; `bac_bo` ghi EIDE.md §Đừng và dòng biến mất khỏi bảng; `display` sửa không có `nguon` → Fact NGƯỜI (CX05). Giao diện: `FormEditor` gom đúng một `patch`; "Không phải lỗi" không gửi khi thiếu lý do.

**Tiêu chí chấp nhận.** Tỉ lệ loại hiện vật sửa được qua giao diện ≥ 15/≈30 (đo bằng script `tools/dem_sua_duoc.py` mới: đếm khối có `sua_duoc` trên 9 kho mẫu trong `du-lieu/`). SCH-14/15 chạy xanh trên đường `patch`.

**Ước lượng.** 3–5 ngày.

---

<!-- se-co -->

### DEV-369 · Bắt sửa từ bên ngoài (VS Code, KiCad) — changeset `external`

**Mục tiêu.** Luật nền 3 đúng với cách kỹ sư nhúng làm thật: sửa ở editor quen tay vẫn thành changeset hoàn tác được, vẫn kích hoạt `lock_broken` và STALE. Cờ `EIDE_FEATURE_WATCHER` (đổi thứ Agent thấy).

**Lõi.**
- `src/eide/watcher.py` (mới): thread dùng `watchdog` (thêm vào `pyproject.toml` nhóm chính; không có thì fallback quét `mtime` mỗi 2 s). Theo dõi gốc dự án, bỏ qua `.eide/`, `build/`, `.git/`, `.venv/`, `__pycache__/`, tệp > 5 MB, tệp nhị phân (dò bằng mấy byte đầu như ING-43). Gộp sự kiện trong 1,5 s theo tệp.
- Với mỗi tệp đổi: so hash với **blob gần nhất EIDE biết** (`history.blobs` qua changeset cuối chạm tệp; chưa có thì bản tại `sha_hien_tai` của git; chưa có nữa thì coi là tệp mới). Nếu khác và **không** phải do `_sua_tep`/công cụ Agent vừa ghi (đối chiếu `hash` ghi trong 3 s gần nhất — `self._vua_ghi: dict[path, (hash, ts)]`) → `history.ghi_tep(author="human", loai="external", noi_dung_truoc={path: bản cũ}, summary=f"anh sửa {path} bên ngoài EIDE", explain.sources=[{"kind":"external"}])`.
- Nếu `path in self.locks` → chạy đúng đường `lock_broken` (dừng Agent sửa tệp đó, `surface_unlock`, nhắn).
- Đẩy `eide_md.note_human_edit(...)`, `history_update`, `surface_patch("code", "A7.1", …)`, `notice("anh vừa sửa X bên ngoài — đã ghi cs-…", level="info")` có nút Hoàn tác (toast DEV-365).
- Watcher chỉ chạy ở chế độ `--stdio` (có giao diện). Chế độ `--go` một lượt không chạy.

**Giao diện.** Chỉ nhận lệnh đã có. Thêm ở A11 nhãn "ngoài EIDE" cho changeset `loai=external`.

**Ca kiểm.** `tests/test_edit47_watcher.py` (dùng thư mục tạm, fallback quét `mtime` để không phụ thuộc watchdog trong CI): sửa tệp → đúng 1 changeset sau gộp; Agent vừa ghi → không sinh changeset trùng; tệp trong `.eide/` → bỏ qua; tệp nhị phân → bỏ qua; tệp bị khoá bởi Agent → `lock_broken`; hoàn tác changeset external khôi phục đúng nội dung cũ.

**Tiêu chí chấp nhận.** Mở `main.c` bằng VS Code, sửa, lưu → trong 3 s A11 có "anh sửa main.c bên ngoài EIDE", toast Hoàn tác; lượt sau Agent biết.

**Ước lượng.** 2–3 ngày.

---

<!-- /se-co -->

### DEV-370 · Duyệt có sửa, và sửa phương án trước khi chọn

**Mục tiêu.** Bỏ vòng "Không → gõ lời → đợi lượt". Trên thẻ cổng có diff (DEV-366) người sửa thẳng rồi duyệt; trên thẻ "nêu 2–4 cách" người sửa một cách rồi chọn. Cờ `EIDE_FEATURE_DUYET_CO_SUA`.

**Lõi.**
- `HumanAct.validate()`: `decide` nhận thêm `data.amended = {"content": "…"} | {"patch": [...]}`.
- `loop._resolve_gate`: nếu `approved` và có `amended` → **trước khi** chạy lời gọi đang chờ, thay tham số nội dung của lời gọi (`call.args.content` / `canonical`) bằng bản đã sửa; ghi ledger `gate` với `amended=true` và một changeset `author=human` cho phần chênh (để hoàn tác được phần người sửa riêng, không chỉ phần Agent ghi); nhắn mô hình bằng `<system-reminder>`: "Người dùng duyệt nhưng ĐÃ SỬA nội dung: <diff tóm tắt>. Làm tiếp trên bản của họ."
- Thẻ phương án (`option`): A2.2 có `sua_duoc` (DEV-368); thẻ clarify "chọn cách" nhận `choose` sau một `edit` — không cần lõi mới, chỉ cần giao diện gửi hai HumanAct theo thứ tự và lõi đã có `pending_cards` xử lý.

**Giao diện.** `CardViews.swift`: thẻ cổng có `diff` → nút *Duyệt với bản đã sửa* (chỉ sáng khi cột phải đã đổi). Thẻ phương án: mỗi cách có nút "Sửa" mở `FormEditor`; sau Lưu, nút "Chọn cách này" vẫn ở đó.

**Ca kiểm.** `tests/test_edit47_duyet_co_sua.py`: duyệt có `amended` → tệp trên đĩa là bản người sửa, có 2 changeset (Agent + người) đúng thứ tự, hoàn tác changeset người → về bản Agent; cờ tắt → `amended` bị bỏ qua và có `notice` nói rõ; `decide` không `approved` mà có `amended` → lỗi lược đồ.

**Tiêu chí chấp nhận.** Trên phiên thật: Agent đề nghị ghi `Makefile`, người sửa một cờ dịch trong diff, bấm Duyệt với bản đã sửa → `Makefile` đúng bản người sửa, Agent ở lời tiếp theo nhắc đúng chỗ người sửa.

**Ước lượng.** 2–3 ngày (sau DEV-366, DEV-368).

---

<!-- se-co -->

### DEV-371 · Cài đặt dự án qua `set`, gộp thẻ `tool.install`, và hai công cụ chạy

**Mục tiêu.** Ba chỗ người đang phải làm thay máy: sửa `.env` để bật cờ; đóng hàng chục thẻ `tool.install`; gõ `make`/chạy Python hộ Agent.

**Lõi.**
- `set`: nhánh `_dieu_huong` đã nhận `set`; thêm xử lý `key` bắt đầu `feature.` → ghi `.eide/settings.json`, `Features` đọc theo thứ tự **settings.json > biến môi trường > mặc định**; ghi ledger `setting`; `notice` "áp từ lượt sau". A14 thêm khối `kv` "Cài đặt dự án" có `sua_duoc kieu=bool` cho 14 cờ, mỗi dòng kèm một câu giải thích và chi phí (lấy từ `Features` docstring; `PDF_BANG` ghi "×4,3–4,7 thời gian nạp").
- `tool.install`: khoá theo tên gói trong `pending_gates` — cùng gói đang chờ → không dựng thẻ mới, trả cho Agent `E_GATE_PENDING` kèm `gate_id` cũ; thẻ được duyệt thì mọi lời gọi cùng gói trong lượt tự đi (đã có `_da_duyet_roi`).
- Hai công cụ mới, nhóm "Viết mã", qua `G-OPS`, trong hộp cát, có timeout và giới hạn đầu ra: `build.make {target, cwd}` (chạy `make` trong gốc dự án hoặc thư mục con; ghi kết quả vào `.eide/build/` như `build.*` hiện có; nối "kiểm nối" nếu `KIEM_NOI` bật) và `py.run {path, args}` (chạy `.venv/bin/python -I <path>` trong gốc dự án; chặn `path` ngoài hộp cát; stdout/stderr ≤ 64 KB; exit code về cho Agent). Cả hai ghi ledger đầy đủ tham số/kết quả/mã lỗi (lớp 3 chạy xong ghi sổ).

**Giao diện.** A14 khối cài đặt (vẽ bằng `FormEditor` từ DEV-368, `kieu=bool`). Không có gì khác.

**Ca kiểm.** `tests/test_edit47_set_va_cong_cu.py`: `set feature.X=true` → `settings.json` có, `Features` đọc đúng thứ tự ưu tiên; `tool.install` gọi 5 lần cùng gói → 1 thẻ; `build.make` ngoài hộp cát bị chặn, có G-OPS, ghi `.eide/build/`; `py.run` với tệp vỡ → exit ≠ 0 về Agent (không "đã xác minh"); `py.run` không chạy được tệp ngoài gốc dự án.

**Tiêu chí chấp nhận.** Bật `PDF_BANG` từ A14 không khởi động lại lõi; một việc cài `pyserial` chỉ có một thẻ; trong kịch bản FPGA (`tools/phien_fpga.py`) hai chỗ "nhờ người gõ make" biến mất.

**Ước lượng.** 2–3 ngày.

---

<!-- /se-co -->

## 6 · Thứ tự làm và phụ thuộc

```
DEV-365 (nút lùi)  ──► DEV-366 (diff) ──► DEV-367 (trình soạn tệp) ──► DEV-369 (watcher)
                                 │
                                 └──────► DEV-368 (sua_duoc + patch + confirm) ──► DEV-370 (duyệt có sửa)
DEV-371 (set, tool.install, make/py.run) — độc lập, làm xen khi chờ
```

Tổng ≈ 15–24 ngày công. Sau DEV-365 và DEV-366 đã có thể dùng thật và đo; không đợi đủ bảy gói.

---

## 7 · Đo

<!-- se-co -->

Thêm vào `tools/bao_cao_tong.py` và `docs/review-v3/test/BAO-CAO-TONG.md` bốn chỉ số, đo trên 9 kho mẫu trong `du-lieu/` và trên phiên thật tiếp theo:

| Chỉ số | Cách đo | Hiện nay | Đích sau EDIT-47 |
|---|---|---|---|
| Loại hiện vật sửa được qua giao diện | `tools/dem_sua_duoc.py`: số `type` có khối mang `sua_duoc` / tổng `type` có trong kho | 4 / ≈30 | ≥ 20 / 30 |
| Lượt người gõ lời cho việc lẽ ra bấm được | đếm trong ledger: `say` ngay sau `console_post` có từ khoá *sửa/đổi/lùi/về bản* mà hiện vật đích có `sua_duoc` | chưa đo | giảm ≥ 70 % |
| Thời gian sửa → hạ nguồn cập nhật | từ `human_act edit` tới changeset Agent đầu tiên chạm hiện vật STALE tương ứng | chưa đo | có số, và nút "Cập nhật hạ nguồn" làm nó một cú bấm |
| Hoàn tác thành công / thất bại, theo tầng | ledger `undo` + `KetQuaHoanTac.ok` | chỉ tầng 2 | đủ 5 tầng, tỉ lệ ok ≥ 95 % |

<!-- /se-co -->

Thêm bộ ca CX mới `tests/kich_ban/cx_edit47_*.py` theo mẫu CX05/CX08: mỗi gói một ca "đi đúng đường người đi" (§0 mục 6).

---

## 8 · Rủi ro và những thứ cố ý không làm

- **Trình soạn tệp không có highlight cú pháp, không có autocomplete.** EIDE không định thay VS Code; nó cần đường *lưu có dấu*. Watcher (DEV-369) là cách đúng cho người thích editor riêng.
- **Kéo-thả trên canvas (trình soạn C bước 2) để sau.** Bước 1 (bấm phần tử → biểu mẫu) đã cho sửa được mọi thuộc tính; kéo-thả chỉ thêm tiện, và nó là nơi dễ sinh "sửa trên bản dựng" nhất (I7).
- **Watcher có thể tạo changeset rác** khi công cụ ngoài (KiCad, trình dịch) ghi tệp sinh. Danh sách bỏ qua phải nằm trong `EIDE.md §Bỏ qua` của dự án và sửa được từ A14.
- **`patch` cho phép sửa sâu, nên cũng cho phép làm hỏng cấu trúc** (xoá `assert` cuối cùng của một tiêu chí). Lõi kiểm bất biến của từng `type` sau `ap_patch` (tiêu chí ≥ 1 assert; `ui_screen` phần tử trong biên panel bằng `screen.check`); vi phạm → từ chối cả patch (I9).
- **Duyệt có sửa làm mờ ranh giới "ai viết dòng này".** Vì thế phần người sửa là changeset riêng `author=human` (DEV-370), không gộp vào changeset của Agent.
- **Không mở cổng mạng, không thêm tiến trình ngoài** cho bất kỳ gói nào — watcher chạy trong tiến trình lõi.
