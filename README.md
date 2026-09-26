# EIDE v3 — lõi tác tử kỹ sư nhúng

Môi trường phát triển nhúng có một tác tử làm việc **cùng** kỹ sư. Người và tác tử là
hai tác giả bình đẳng trên cùng một bộ hiện vật; mọi con số dùng để quyết định phải
truy vết được tới datasheet; mọi thay đổi là một changeset hoàn tác được.

- **Thiết kế (nguồn sự thật):** [`docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md`](docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md)
- **Nhật ký sai lệch mã ↔ tài liệu:** [`docs/md/EIDE-DEV-LOG.md`](docs/md/EIDE-DEV-LOG.md)
- **Bộ đo:** 76 TC + 16 CX — [`docs/review-v3/test/`](docs/review-v3/test/)
- Đề án tốt nghiệp ThS Kỹ thuật Điện tử — PTIT · Vũ Trí Công · GVHD: TS. Nguyễn Trung Hiếu

## Trạng thái

| Bước | Nội dung | Trạng thái |
|---|---|---|
| **G1** | Lõi vòng lặp · hook S0 · tool registry + 10 tool đọc + ask_user · hiến pháp · EIDE.md · `<inventory>` | xong |
| **UI** | App macOS (SwiftUI) + cầu UAP qua stdio · Console · thẻ cổng · 11 bề mặt · thanh trạng thái | xong |
| **G2** | Store event-sourced + git · changeset · history.undo 1–2 · STALE · đường ống người sửa · tab Lịch sử | xong |
| **G3** | Hiện vật hai dạng · explain bắt buộc · nút "Vì sao?" · Fact tầng NGƯỜI tự động · phân loại sửa | xong |
| **G4** | Tri thức: ingest theo magic bytes · tài liệu theo trang · fact.extract/review · hộ chiếu + ISA · compare 8 luật | xong |
| **G5** | Bản ưng ý bất biến · khôi phục không xoá lịch sử · so sánh hai bản · nhánh · release là điều kiện khoá chip | xong |
| **ING-A** | classify v3: Office trước archive · ba mức hỗ trợ · E1010–E1015 · giới hạn archive & zip bomb · cây tệp A3.6 | xong |
| **SCH-0** | Cờ tính năng (tắt = không đăng ký) · migration Store có `down()` · so hồi quy hai chế độ | xong |
| **MEM-A** | Phong bì kết quả công cụ + blob · `blob.read` · đồng hồ ngữ cảnh 10 khối · C1 thu gọn 0 token | xong |
| **MEM-B** | M1 trên đĩa + write-ahead · EIDE.md quy tắc cứng + deny `fs.write` · `memory.forget`/`status` · `ledger.query` · hash chuỗi changeset | xong |
| **MEM-C** | C2 tóm tắt 10 mục · PreCompact/PostCompact kiểm ngược 3 câu · ghim theo ý chí người · resume 5 bước · bộ nhớ người dùng · khối A14.6 | xong |
| **ING-B** | Bộ đọc `.docx`/`.xlsx`/`.pptx` · trích dẫn theo loại (đường tiêu đề · `Sheet!ô` · slide) · tầng theo nguồn · LibreOffice cho định dạng cũ | xong |
| **ING-C** | Chuẩn hoá `4R7`/`3V3`/dải/`TBD`→null · bảng đọc như bảng, điều kiện có cấu trúc · đối chiếu chéo nguồn | xong |
| **ING-D** | Tầng CẤU HÌNH (`.ioc`/`sdkconfig`/`.dts`/`.ld`/`map`) · lệch với datasheet · netlist/`.kicad_sch` · BOM ↔ netlist | xong |
| **ING-E** | Hình → figure · OCR có điểm tin cậy từng từ · nhận ngôn ngữ và kiểm gói OCR · bí danh đa ngữ | xong |
| **MEM-D** | C3 bậc thang · C4 khẩn cấp 0 token · dọn theo tham chiếu · sáu chỉ số §13 | xong |
| **CKM** | Bản đồ tri thức mạch §C2: KG nodes/edges · khối + luồng tín hiệu suy từ tên · pinout không bịa chân, ĐƯỢC_GÁN duy nhất do chỉ mục kho · net/netlist · gộp `ckm.build` | xong |
| **HIER-A** | Cây khối phân cấp §2–3: lược đồ v3 có `down()` · Port ở biên khối · net theo phạm vi · `flatten(cây)` = netlist cũ 100 % · sáu bất biến E9001–E9006 | xong |
| **HIER-B** | Fact theo cấp · ERC bốn ràng buộc §4.2 báo theo path (`board.check`) · STALE theo NÚT, nội bộ không lan sang anh em · cây gập/mở A5.9 · giải thích khối 7 câu | xong |
| HIER-C…D | Thư viện khối `block@semver` · SKiDL/KiCad phân cấp + round-trip | chưa |
| **SCH-A** | Cờ + `eide/sch/` + `sch.compose` (khối → hàm SKiDL) · `sch.netlist` kiểm đẳng cấu bằng cách ĐỌC LẠI tệp · `sch.symbols` sinh từ Fact có ghi nguồn · R3 · chốt chặn không đề nghị cài KiCad | xong |
| **SCH-B** | `sch.place` bố cục xác định, tiêu chí đo bằng số · `sch.write` `.kicad_sch` qua kiutils, uuid theo ref · `sch.render` SVG tự vẽ, kiểm chữ không đè | xong |
| SCH-C…D | Round-trip `sch.import`/`export` · sheet phân cấp · đi dây thật | chưa |
| G6 | Build/Sim + subagent | chưa |
| G7 | Mạch thật | chưa |

## Cài và chạy

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env          # rồi điền GEMINI_API_KEY
```

```bash
# Một lượt, in ra terminal
.venv/bin/python -m eide --du-an du-lieu/du-an-cua-toi --go "Làm bộ chuyển LAN sang USB cho TV"

# Lõi phục vụ giao diện (app Swift chạy lõi làm tiến trình con)
.venv/bin/python -m eide --du-an du-lieu/du-an-cua-toi --stdio

# Lõi phục vụ qua WebSocket localhost
.venv/bin/python -m eide --du-an du-lieu/du-an-cua-toi --ws --cong 8777
```

## Giao diện (macOS)

```bash
cd ui/EIDEApp && ./dong-goi.sh      # biên dịch + đóng gói EIDE.app
open EIDE.app
```

Lần đầu mở: chọn **thư mục dự án** (đây cũng là sandbox của tác tử), gốc mã nguồn EIDE,
và Python. App tự nhớ cho lần sau.

App chạy lõi Python làm **tiến trình con** và nói JSON-RPC 2.0 trên stdio (khung
`Content-Length`). Không mở cổng mạng nào — EIDE là ứng dụng một người trên máy cá nhân.

Hai điều đáng biết khi đọc mã giao diện:

- **Giao diện không quyết gì** (I3). Mọi thứ người nhìn thấy đều đến từ một trong 16
  `UICommand`. Bộ render khối là *chung*: lõi thêm khối mới thì app vẽ được ngay, không
  phải sửa Swift. Lõi gửi loại khối app chưa biết → app **nói ra**, không bỏ qua im lặng.
- **Một cửa vào** (I1). Mọi cái chạm — gõ câu, bấm nút trong thẻ, chuyển tab — đều thành
  một `HumanAct` đi qua `console.act`. Không có đường tắt nào từ giao diện vào lõi.

```
ui/EIDEApp/Sources/EIDE/
├── Protocol/
│   ├── UAP.swift          13 HumanAct · 16 UICommand · SurfaceModel · Card · StatusBar
│   ├── CoreClient.swift   Tiến trình con + khung Content-Length + JSON-RPC
│   └── JSONValue.swift    Giá trị JSON động (để I3 đúng theo nghĩa đen)
├── State/AppState.swift   Hình chiếu của những gì lõi đã gửi — không tự nghĩ ra gì
└── Views/                 Console · thẻ cổng/làm rõ · 11 bề mặt · thanh trạng thái
```

## Kiểm thử

```bash
.venv/bin/python -m pytest -q                        # 135 test: hook, policy, công cụ, sổ cái, vòng lặp
.venv/bin/python tools/kiem_tra_day_du.py --nhanh    # an toàn qua cầu giao thức, 0 token
.venv/bin/python tools/kiem_tra_day_du.py            # một mạch công việc thật, lõi + Gemini
.venv/bin/python tools/thu_giao_dien.py              # 24 ca qua GIAO DIỆN THẬT
.venv/bin/python tools/thu_g3.py                     # 31 ca CX + 8 đường hỏng có chủ đích
.venv/bin/python tools/thu_g4.py                     # 23 ca nền tri thức + 8 đường hỏng
.venv/bin/python tools/thu_g5.py                     # 35 ca bản ưng ý/nhánh + 8 đường hỏng
.venv/bin/python tools/thu_ing_a.py                  # 29 ca phân loại tệp + 8 đường hỏng
.venv/bin/python tools/thu_mem_a.py                  # 21 ca bộ nhớ/nén + 6 đường hỏng
.venv/bin/python tools/thu_mem_b.py                  # 20 ca bộ nhớ dài hạn + 7 đường hỏng
.venv/bin/python tools/thu_ing_b.py                  # 25 ca đọc Office + 6 đường hỏng
.venv/bin/python tools/thu_mem_c.py                  # 26 ca nén có kiểm chứng + 7 đường hỏng
.venv/bin/python tools/thu_cuoi.py                    # 36 ca ING-C/D/E + MEM-D + 9 đường hỏng
.venv/bin/python tools/thu_ckm.py                     # 35 ca bản đồ tri thức mạch + 8 đường hỏng
.venv/bin/python tools/thu_hier.py                    # 38 ca cây khối + ERC + STALE theo cây
EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/thu_sch.py    # 35 ca sinh sơ đồ + 10 đường hỏng
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_g5.py   # bằng chứng SCH-19
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_ing_a.py   # hồi quy hai chế độ cờ
.venv/bin/python tools/chay_kich_ban.py --lan 5      # bộ 76 TC, mỗi ca 5 lần
.venv/bin/python tools/theo_doi.py --du-an <thư mục> # theo dõi phiên thật qua sổ cái
```

### Kiểm thử qua giao diện thật

`thu_giao_dien.py` và `thu_g3.py` **không** gõ phím qua hệ điều hành — cách đó gửi phím
tới cửa sổ đang có tiêu điểm, và khi người dùng làm nhiều việc thì phím rơi nhầm cửa sổ.

Thay vào đó app mở một kênh tại `<dự án>/.eide/ui-test/{inbox,outbox}.jsonl`, chỉ bật
khi thư mục đó tồn tại, và khi bật thì hiện dải báo rõ. Mọi thứ đọc từ inbox vẫn đi qua
`AppState.gui()` → `console.act`, nên **bất biến I1 nguyên vẹn** — kênh thay ngón tay
người, không thay giao thức.

Lợi ích lớn hơn: kênh **đọc ngược** trạng thái giao diện, nên kiểm được những thứ chỉ
đúng khi mã Swift chạy thật — bộ dựng markdown tách ra khối gì, thẻ cổng hiện mấy dòng
hậu quả, tab Mã nguồn có khối quy trình mấy bước.

Ca đo nằm trong `tests/kich_ban/*.yaml`. **Không sửa tiêu chí để ép đạt** (N6): ca không
đạt thì ghi rõ vì sao; ca vượt phạm vi bước hiện tại được đánh dấu riêng, không tính là
"không đạt".

## Kiến trúc

Một vòng lặp, LLM là bộ điều phối duy nhất, mọi năng lực là công cụ có hợp đồng, và
**ba lớp xác định bao quanh mỗi lời gọi công cụ**:

```
HumanAct ──► hook UserPromptSubmit (S0, 0 token) ──► [chặn / hỏi / cảnh báo] ──┐
                                                                               │
   ┌───────────────────────────────────────────────────────────────────────────┘
   ▼
 assemble(hiến pháp + EIDE.md + <inventory> + <facts> + <human_edits> + <pending>)
   │
   ▼
 llm.stream ──► tool_calls ──► PreToolUse ──► policy.decide ──► tools.run ──► PostToolUse
                                 │               │
                            sandbox,         allow / ask (thẻ cổng) / deny
                            explain,
                            constant-guard
   │
   ▼
 hook Stop ──► giả định đã nói? người vừa sửa đã được nhắc? đã nói gì chưa?
```

Không có đường nào đi vòng qua ba lớp đó. Đây là lý do v3 bỏ máy trạng thái S0–S6 của
v1.x: trong kiến trúc cũ một nút hỏng giữa chuỗi làm cả lượt chết tại chỗ; ở đây lỗi
quay về mô hình như **dữ liệu có hướng dẫn** và nó đổi hướng.

## Cây mã

```
src/eide/
├── loop.py              Vòng lặp §B1 — ghép tất cả
├── config.py            Ngân sách, đường dẫn, mức tự chủ, mô hình
├── errors.py            Lỗi có hướng dẫn {code, message_vi, hint_for_agent, alternatives}
├── ids.py               cs-0109, run-43, h-0940 — id người đọc được
├── protocol/            UAP v1.1 §D — một cửa vào
│   ├── humanact.py        13 loại y chí của người
│   ├── uicommand.py       16 lệnh lõi gửi giao diện
│   ├── ledger.py          Sổ cái append-only có chuỗi hash
│   └── rpc.py             JSON-RPC 2.0 trên stdio / WebSocket
├── hooks/               §B4 — nguyên tắc sống trong mã, không trong lời dặn
│   ├── s0.py              Bộ luật chặn xác định
│   └── standard.py        PreToolUse · PostToolUse · Stop
├── rules/s0_rules.yaml  STOP, BACKREF, G-OPS, P-SAFE, P-LAW, P-QUAL, P-INJ
├── policy/              allow | ask (thẻ cổng) | deny
├── context/             §B2 — hiến pháp + sáu khối nhắc
├── store/               Kho event-sourced · EIDE.md · <inventory>
├── changeset.py         Đơn vị thay đổi + phép nghịch đảo + sổ changeset + blob
├── history.py           Ghi changeset · hoàn tác mức 1–2 · checkpoint ngầm
├── deps.py              Đồ thị phụ thuộc + đánh dấu STALE
├── vcs.py               Git cho tệp: commit có cấu trúc, revert, 3-way merge
├── surfaces.py          Dựng SurfaceModel cho 11 bề mặt
├── tools/               Sổ đăng ký + bộ công cụ (đọc + ghi)
└── llm/                 Cổng mô hình (Gemini) + kịch bản/ghi–phát lại
```

### Mọi thay đổi đều hoàn tác được (N9)

Không có đường nào ghi mà không sinh changeset. Công cụ ghi không gọi thẳng kho hay
ghi tệp — tất cả đi qua `history.ghi_kho()` / `history.ghi_tep()`, và chỉ nơi đó mới
biết dựng phép nghịch đảo. Muốn ghi mà không để lại dấu thì phải sửa `history.py`.

- **Kho** (REQ, ADR, Fact…): phép nghịch đảo giữ nguyên `canonical` bản trước.
- **Tệp** (mã, netlist, EIDE.md): một changeset một commit git, message mang mã changeset;
  nghịch đảo là `git revert`. Bản sao nội dung cũ theo hash trong `.eide/blobs` là đường lui.
- **Không đảo ngược được** (nạp chip, ghi eFuse, cài công cụ): vẫn là changeset, mang
  `reversible=false` kèm lý do bằng tiếng Việt. Hoàn tác cả lượt sẽ **giữ nguyên** nó
  và cảnh báo "bo vẫn đang chạy bản cũ".

Sửa của **người** cũng là changeset (`author=human`), cũng có lớp giải thích, và kéo theo
STALE y như sửa của tác tử. Hook `Stop` buộc tác tử phải **nhắc tới** thay đổi của người
trước khi kết thúc lượt — đo bằng chữ đã thật sự hiện ra, không bằng lời mô hình tự khai.

## Ngôn ngữ

Mã và tên biến bằng tiếng Anh. **Mọi thứ người dùng đọc — thông điệp lỗi, thẻ cổng, lớp
giải thích, báo cáo — bằng tiếng Việt có dấu.** Thuật ngữ kỹ thuật giữ nguyên tiếng Anh
kèm giải thích khi lần đầu xuất hiện.
