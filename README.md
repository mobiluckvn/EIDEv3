# EIDE v3 — lõi tác tử kỹ sư nhúng

Môi trường phát triển nhúng có một tác tử làm việc **cùng** kỹ sư. Người và tác tử là
hai tác giả bình đẳng trên cùng một bộ hiện vật; mọi con số dùng để quyết định phải
truy vết được tới datasheet; mọi thay đổi là một changeset hoàn tác được.

- **Cài đặt:** [`docs/md/EIDE-CAI-DAT.md`](docs/md/EIDE-CAI-DAT.md)
- **Kiến trúc theo mô hình C4 (mã đang thế nào):** [`docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md`](docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md)
- **Thiết kế (nguồn sự thật):** [`docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md`](docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md)
- **Nhật ký sai lệch mã ↔ tài liệu:** [`docs/md/EIDE-DEV-LOG.md`](docs/md/EIDE-DEV-LOG.md)
- **Bộ đo:** 76 TC usecase + 124 ô giao diện + 1339 ca đơn vị — [`docs/review-v3/test/`](docs/review-v3/test/)
- **Kết quả đo mới nhất (29/09/2026):** [`BAO-CAO-TONG.md`](docs/review-v3/test/BAO-CAO-TONG.md) · [bảng Excel](docs/review-v3/test/Usecase_Test_KET_QUA_29-09-2026.xlsx)
- **Đề tài:** PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI)
- Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — Học viện Công nghệ Bưu chính Viễn thông (PTIT) · Học viên: Vũ Trí Công · GVHD: TS. Nguyễn Trung Hiếu

## Tác tử làm được những gì

**122 công cụ** trong 10 nhóm (113 đăng ký mặc định + 9 công cụ `sch.*` nằm sau cờ
`EIDE_FEATURE_SCHEMATIC`), **7 tác tử con**, **8 skill**, **10 cổng duyệt**, **11 bề mặt**.
Dưới đây là năng lực theo *việc người dùng cần*, không theo cây mã.

| Nhóm công cụ | Số | Làm gì |
|---|---|---|
| Thiết kế | 27 | bản đồ tri thức mạch · cây khối phân cấp · thư viện khối · sơ đồ nguyên lý |
| Tri thức | 20 | nạp và đọc datasheet · trích Fact · hộ chiếu chip · **viết tài liệu ra Word/PPT/Excel/PDF** |
| Store | 19 | yêu cầu · phương án · ADR · mô-đun · BOM · quy trình từng bước |
| Lịch sử | 18 | changeset · hoàn tác · bản ưng ý · nhánh · sổ cái · xuất/nhập dự án |
| Điều phối | 10 | tác tử con · kế hoạch nhiều chặng · tìm và **tự viết công cụ** |
| Tệp & lệnh | 7 | đọc/ghi/sửa tệp trong hộp cát · tìm kiếm |
| Mã nguồn | 8 | **phân tích mã trước khi sửa** · biên dịch · bản đồ bộ nhớ · kiểm thử · độ nhạy bộ kiểm |
| Mạch thật | 6 | dò bo · nạp · đọc ngược · log · gỡ lỗi · đọc khung ảnh |
| Mô phỏng | 4 | tiêu chí trước · chạy · đối chiếu |
| Người & UI | 3 | hỏi người · mở bề mặt · ghi nhận cái chạm |

### Ba điều xuyên suốt, quan trọng hơn danh sách công cụ

- **Mọi con số phải truy được về nguồn** (N1). Tác tử không có đường nào đặt một thông số vào
  kho mà không kèm chỗ nó lấy ra — trang datasheet, dòng tệp cấu hình, hay nguyên văn câu
  người dùng nói.
- **Không có "đạt" nào không có bằng chứng** (N6). Tiêu chí phải nêu **trước** khi chạy;
  đổi ngưỡng sau khi đã có kết quả thì đi qua cổng người duyệt.
- **Mọi thay đổi hoàn tác được** (N9), kể cả sửa của người. Việc không đảo ngược được (nạp
  chip, ghi eFuse) vẫn là một changeset, mang `reversible=false` kèm lý do.

### Năm tầng tin cậy — mỗi con số mang một tầng

Không phải mọi con số đều bằng nhau, nên EIDE không cho chúng đứng cùng một hàng:

| Tầng | Nguồn | Dùng để |
|---|---|---|
| **VÀNG** | datasheet của hãng, đã có người xác nhận | quyết định gì cũng được |
| **BẠC** | mã đọc thẳng từ trang PDF, chưa ai duyệt | dùng được, nhưng hiện nhãn chờ duyệt |
| **NGƯỜI** | người dùng nói ra, có trích nguyên văn | cao nhất khi datasheet im lặng |
| **CẤU HÌNH** | `.ioc`/`sdkconfig`/`.dts`/`.ld`/`.map` — máy đang cấu hình thế | đối chiếu với datasheet để tìm chỗ lệch |
| **ĐỒNG** | suy đoán từ hình, OCR, tên gọi | **chỉ để gợi ý**, không để quyết |

`fact.review` là đường nâng BẠC → VÀNG, và chỉ người mới đi được đường đó.

### 1 · Làm rõ ý tưởng và chốt phương án

`ask_user` hỏi **một cụm** câu thay vì tra tấn từng câu, mỗi câu kèm *vì sao hỏi* và một giả
định sẽ dùng nếu người bỏ qua · `store.req_create` bắt buộc trích **nguyên văn** lời người
dùng vào `source_quote` · `store.option_create` 2–4 phương án rồi `store.option_choose` chốt,
sinh kèm ADR.

Chỗ đáng nói: `store.option_choose` với `quyet_boi="nguoi"` phải **chứng minh được** — câu
trích phải có thật trong sổ cái, phải mang nghĩa lựa chọn, và phải nhắc đúng phương án. Gán
"người quyết" cho một câu họ không hề chọn là giả mạo xuất xứ, và `NGUOI` là tầng tin cậy cao
nhất (xem DEV-291, lỗi L1).

Và **hỏi không phải là dừng**: tác tử làm hết phần không phụ thuộc câu trả lời trước, rồi mới
hỏi phần còn lại. Tối đa hai lần hỏi mỗi lượt; hết thì đi tiếp với giả định và **nói ra giả
định**. Nó dám làm vì mọi thay đổi đều hoàn tác được.

### 2 · Tri thức: datasheet, Fact, hộ chiếu chip

`doc.fetch`/`doc.load` nạp PDF · Office · văn bản · mã nguồn, nhận dạng theo **magic bytes**
chứ không theo đuôi tệp · `doc.read` đọc theo từ khoá/mục/trang · `doc.figures` rút hình kèm
OCR có **điểm tin cậy từng từ** · `doc.language` kiểm máy có gói OCR cho ngôn ngữ ấy chưa.

Trích dẫn theo **đúng loại tài liệu**: PDF theo trang, Word theo đường tiêu đề (vì Word không
có số trang cố định), Excel theo `Sheet!ô`, slide theo số slide, mã nguồn theo dòng.

`fact.extract` đọc số **bằng mã** từ trang PDF (không để mô hình đọc hộ), `fact.review` cho
người nâng BẠC → VÀNG, `fact.assert_human` ghi số người nói thành tầng NGƯỜI,
`fact.cross_check` tìm thông số mà nhiều nguồn cho số khác nhau, `fact.compare` so hai Fact
theo một luật kỹ thuật và **từ chối kết luận** khi thiếu dữ kiện.

Chuẩn hoá ký hiệu kỹ thuật ngay khi đọc: `4R7` → 4,7 Ω · `3V3` → 3,3 V · dải `2.7–3.6 V` giữ
cả hai đầu · `TBD` thành `null` **chứ không thành 0** — một giá trị chưa có mà hoá thành 0 thì
mọi phép tính sau đó đều sai mà không ai biết.

`passport.pin` chỉ ghim được hộ chiếu chip khi đã có tài liệu cho chip đó — ghim khan thì mọi
thứ dựng trên nó đều không truy vết được. `config.load` đọc `.ioc`/`sdkconfig`/`.dts`/`.ld`/
`.map` thành Fact tầng CẤU HÌNH và nói ra chỗ lệch với datasheet.

**Tài liệu có thể chứa lệnh ngầm.** Đoạn nào trong PDF mang hình dạng chỉ dẫn cho tác tử được
đánh dấu và đọc như **dữ liệu**, không như mệnh lệnh — hiện thành cảnh báo đỏ trên tab Tài liệu.

### 3 · Viết tài liệu cho người đọc: Word · PowerPoint · Excel · PDF

Bảy công cụ `doc.*` khác đều là **đọc**. `doc.render` là chiều ngược lại: tác tử viết nguồn
Markdown bằng `fs.write`, rồi dựng ra tệp gửi đi được.

| Định dạng | Hợp với | Nó nói KHÔNG khi |
|---|---|---|
| **`.docx`** Word | tài liệu để đọc và sửa tiếp | — |
| **`.pptx`** PowerPoint | trình bày — **mỗi tiêu đề một slide** | — |
| **`.xlsx`** Excel | số liệu để lọc, sắp xếp, tính | nguồn **không có bảng Markdown** nào |
| **`.pdf`** | bản gửi đi, in ra | máy chưa có LibreOffice |

Vì sao nguồn là Markdown chứ không ghi thẳng nhị phân: **một thay đổi không xem được là một
thay đổi không duyệt được**. Nguồn nằm trong sổ cái nên có diff đọc bằng mắt và hoàn tác được;
tệp render ra là hạng *dựng lại được*, nên gói dự án mang đi không phải cõng theo.

Hai lời từ chối trên là **có chủ ý, không phải sự cố**: một `.xlsx` chứa cả đoạn văn trong ô
`A1` mở lên được nhưng vô dụng, mà thứ vô dụng **trông giống thành công** thì đắt hơn một lỗi
nói thẳng. Xong việc thì nó **mở lại chính tệp vừa tạo** và đếm — bao nhiêu đoạn, bao nhiêu
slide, bao nhiêu trang, bao nhiêu hình — rồi báo con số ấy kèm **đường dẫn đầy đủ**, chứ không
báo "đã ghi 12 KB". *`ok` nói về lời gọi, không nói về kết quả.*

Tệp làm ra nằm trong thư mục dự án và có khối riêng **"Tài liệu tác tử đã tạo"** trên tab *Tài
liệu & Nguồn*, kèm dạng, cỡ và đường dẫn đầy đủ — một tệp người dùng không tìm thấy thì cũng
bằng chưa làm (DEV-304).

### 4 · Sơ đồ là HÌNH, ở cả hai nơi

Khối ```mermaid tác tử viết ra **được vẽ thành hình** — trên Console (kèm nút *Xem mã* để đọc
nguyên văn hoặc chép đi) và thành **ảnh** trong tệp Word · PowerPoint · PDF · Excel. Hai kiểu:
`sequenceDiagram` (ai gọi ai, theo thứ tự nào, chờ đáp ra sao — có `loop`/`alt`, `Note over`,
đánh số bước) và `graph`/`flowchart` (khối nào nối khối nào, kể cả `subgraph`). Kiểu chưa vẽ
được thì hiện mã **kèm một câu nói rõ là chưa vẽ được** — im lặng hiện mã thô sẽ để người dùng
tự đoán xem app hỏng hay sơ đồ sai.

Bộ vẽ **tự viết**, không nhúng `mermaid.js`: EIDE không mở cổng mạng nào và chạy được khi máy
không có Internet. Cái giá là hai bộ đọc cho một cú pháp (SwiftUI cho giao diện, Pillow cho tài
liệu), và cái giá ấy được trả bằng một ca kiểm bắt cả hai phải đọc **cùng một tập sơ đồ thật**
ra cùng số vai, cùng số khối.

Sửa một sơ đồ là **sửa nguồn rồi render lại**, không sửa trong Word: nguồn giữ lịch sử, bản
render dựng lại trong hai giây.

**Định dạng EIDE chưa sinh được thì tác tử TỰ VIẾT LẤY công cụ.** `tool.propose` →
người duyệt qua cổng **G-TOOL** (thẻ hiện **mã nguồn**, không hiện lời hứa) → tác tử viết mã
kèm bộ kiểm vào `.eide/cong-cu/` → `tool.reload` **chạy bộ kiểm**, xanh mới nạp. Đo được
29/09/2026 qua giao diện thật: xin một tệp **PowerPoint**, tác tử tự viết
<!-- tac-tu-viet -->`doc.pptx`<!-- /tac-tu-viet --> (4,5 KB mã + bộ kiểm) rồi xuất ra bản
trình chiếu 4 slide — [`tools/thu_tu_viet_cong_cu.py`](tools/thu_tu_viet_cong_cu.py), 8/8.
Công cụ ấy sống trong `.eide/cong-cu/` của **dự án đó**, không vào sổ đăng ký của EIDE: năng
lực EIDE mang sẵn và năng lực một dự án tự mọc thêm là hai thứ khác nhau, và ranh giới ấy phải
nhìn thấy được.

### 5 · Thiết kế mạch: Bản đồ tri thức mạch (CKM)

`ckm.*` dựng **Bản đồ tri thức mạch**: chip, chân, net, khối, port. `ckm.pinout_set` **từ chối
gán** một chân không có trong Fact đã nạp — không bịa chân. `eda.netlist` đọc netlist KiCad,
`eda.bom_check` đối chiếu BOM với netlist. `board.check` kiểm bốn ràng buộc tính được từ Fact
(ngân sách dòng theo cây, mức logic hai đầu, trở kéo, reset). `khoi.*` thư viện khối tái dùng
ba tầng, mỗi giá trị dẫn xuất có **công thức và nguồn** — thiếu nguồn thì không đặt.

### 6 · Viết mã: phân tích trước · đánh mốc trước · thiết kế trước

Ba luật cứng, cài bằng **mã** chứ không bằng lời dặn:

| Lúc nào | Luật | Mã lỗi khi vi phạm |
|---|---|---|
| Ghi đè một tệp đang có | phải **đọc trọn nó** trong lượt này trước | `E4020` |
| Lần sửa tệp đầu tiên của mỗi lượt | tự đặt một **mốc lùi**, và nói mã mốc cho anh | — |
| Kế hoạch tạo **mã mới** | phải có bước **chọn kiến trúc** và nói **cấu trúc mã** | `E6009` |
| Kế hoạch **sửa mã có sẵn** | phải có bước `code.analyze` | `E6009` |

Ghi đè mù hỏng theo kiểu **im lặng và toàn phần**: không xung đột, không cảnh báo, chỉ có một
tệp ngắn hơn hẳn. Trước đây đó chỉ là một câu gợi ý trong mô tả công cụ, và đo được là nó
không giữ được gì: gọi thẳng `fs.write` lên một `main.c` 200 dòng chưa hề đọc thì **được nhận**.

`code.analyze` trả lời câu `fs.read` không trả lời được: **ai đang dùng ký hiệu của tệp này**,
tức chỗ nào sẽ phải xem lại sau khi sửa. Tài liệu nó sinh ra tách rõ **dữ kiện** (do mã quét:
ký hiệu, phụ thuộc, nơi gọi) khỏi **nhận định** (do tác tử con `code-analyst` đọc hiểu) — một
con số quét ra và một câu suy đoán không đứng cùng một hàng. Và nó ghi thẳng giới hạn của mình
vào tài liệu: phép dò tìm tên trong văn bản, nên **gọi gián tiếp qua con trỏ hàm hay macro thì
nó không thấy** — đó chính là câu hỏi đắt nhất giao cho tác tử con.

### 7 · Biên dịch, mô phỏng, kiểm thử

`build.compile` chọn chuỗi công cụ theo **dự án là gì**, không theo máy có gì — AVR
(`arduino-cli` khi có `.ino`, không thì `avr-gcc`) và ARM bare-metal (`armv6-m`/`armv7-m`/
`armv7e-m`, sinh `.bin` cho bo nạp kiểu ổ đĩa). Lỗi trả về **có toạ độ** tệp:dòng:cột.
`build.map` cho biết symbol nào chiếm chỗ.

**Criteria-first**: `sim.criteria` nêu tiêu chí **trước**, và chính tiêu chí phán xử kết quả
chứ không phải chương trình mô phỏng. `test.run` chạy unit test trên máy chủ kèm độ phủ.

`test.sensitivity` trả lời câu hỏi mà ô xanh không trả lời được: **bộ kiểm có đo gì không?**
Nó phá mã sản phẩm rồi chạy lại — không ca nào đỏ nghĩa là bộ kiểm không nhìn thấy tệp ấy.
Ra đời vì một bộ kiểm sáu ca đầy đủ tên/ngưỡng/báo cáo JSON đã **xanh mãi mãi** do tệp test
tự định nghĩa lại hàm của sản phẩm (DEV-288).

### 8 · Mạch thật

`target.detect` dò bo qua ổ đĩa bộ nạp, cổng nối tiếp, và **ID chip đọc qua SWD** — đối chiếu
ba giá trị `khớp`/`lệch`/`chưa sờ được`, không gộp ba thành hai. `target.flash` (R4, cổng
G-FLASH) nạp. `target.verify` **đọc ngược Flash từ chip** rồi so từng byte — bằng chứng độc
lập, không tin lời công cụ nạp. `target.log` đọc cổng nối tiếp và **nói là im lặng** khi nó
im lặng. `target.screen` đọc bộ nhớ khung ảnh ra PNG để xem chip đã vẽ được gì, kèm đi dọc
11 mắt xích LTDC → DSI → panel. `target.debug` dừng chip, giải mã CFSR/HFSR, đọc khung ngắt,
lấy dấu vết ngăn xếp, lấy mẫu PC, và đọc nguyên nhân reset.

### 9 · Bộ nhớ và ngữ cảnh

`EIDE.md` là bộ nhớ dài hạn của dự án — người và tác tử cùng sửa, tác tử đọc mỗi lượt. Nén
ngữ cảnh bốn mức: `C1` thu gọn cơ học **0 token**, `C2` tóm tắt có kiểm ngược ba câu, `C3`
bậc thang, `C4` khẩn cấp. `memory.undo_compact` huỷ lần nén trong 24 giờ. `memory.forget` xoá
một dòng nhưng **để lại dấu đã quên**. `ledger.query` tra sổ cái để trả lời "ban đầu anh nói
gì", "vì sao chọn MTP".

### 10 · Lịch sử, nhánh, bản ưng ý — ba mức lùi lại

Mọi thứ ghi đều là changeset có phép nghịch đảo, và có **ba mức lùi lại** cho ba tình huống
khác nhau:

| Mức | Lệnh | Lùi tới đâu | Cần duyệt? |
|---|---|---|---|
| Ngay lập tức | `history.undo_30s` · `⌥⌘Z` | việc tác tử **vừa làm** | không |
| Có chọn | `history.undo` một changeset | đúng một thay đổi, kể cả từ lâu | cổng G-HIST |
| Mốc | `snapshot.restore` | một bản ưng ý đã đặt tên | cổng G-HIST |

`snapshot.create` chỉ ghi bản ưng ý với **cái tên người dùng đã nói ra** — tác tử không tự đặt
tên; muốn đề xuất thì dùng `snapshot.propose` rồi dừng lượt cho người quyết. `snapshot.restore`
**không xoá lịch sử**, nó tạo một changeset mới — nên "quay về" cũng là một việc quay lại được.

Sổ cái là **append-only có chuỗi hash**: sửa một dòng cũ thì `ledger.verify` chỉ ra đúng dòng
gãy. Mỗi changeset còn kèm một commit git mang mã của nó, nên `git log` lần ngược ra được
changeset nào sinh ra thay đổi nào.

**Nhánh** thử hai phương án song song, và một nhánh có **hai nửa**: nhánh git cho tệp, bản chụp
kho cho hiện vật. Chuyển nhánh khôi phục cả hai. `branch.merge` mang kết quả về — tệp gộp bằng
git (xung đột thì **huỷ phép gộp**, không để lại cây làm việc dở dang), hiện vật thì so ba bên
và **chỉ lấy phần một bên đổi**. Cả hai bên cùng đổi thì để nguyên và kê ra cho anh quyết: không
phép trộn nào đúng ở đó, và chọn hộ là giả mạo xuất xứ của quyết định.

### 11 · Việc lớn: chia nhiều chặng, ghi từng chặng, rồi hợp nhất

Một việc không xong trong một lượt — viết trọn tài liệu thiết kế một con chip, dựng nhiều khối
firmware — đi theo năm nhịp:

    plan.enter   → KHOÁ mọi công cụ ghi; tác tử chỉ còn đọc, đo và nghĩ
    plan.exit    → nộp 2–20 bước, mã kiểm trước khi người đọc, rồi cổng G-SCOPE
    … mỗi bước một hoặc vài lượt, có thể cách nhau nhiều ngày …
    plan.step_done(so, hien_vat)   → ghi kết quả từng chặng
    plan.merge(ra=…)               → ráp các phần thành một sản phẩm

Mỗi bước khai trước: *làm gì · bằng công cụ nào · để lại hiện vật gì · chạm cổng nào · tốn bao
nhiêu*. Tên công cụ được **kiểm là có thật** trước khi người duyệt — một kế hoạch nêu công cụ
không tồn tại thì đọc rất xuôi tai rồi chỉ hỏng lúc chạy.

**Kế hoạch là hiện vật trên đĩa.** Nó vào `<pending>` mỗi lượt kèm bước nào xong bước nào
chưa, và sống qua cả `kill -9`: mở lại, gõ *"làm tiếp"* là đi tiếp đúng bước, không duyệt lại
(DEV-289). Vào kế hoạch mới khi cái cũ còn dở thì cái cũ **được cất lại**, không mất.

**`plan.step_done` đòi hiện vật MỞ RA XEM ĐƯỢC** — đường dẫn tệp có thật, mã hiện vật trong
kho, hay mã changeset. Một câu kể lại (*"tôi đã viết xong chương 1"*) bị từ chối: dấu tích
"xong" kiểu ấy chỉ nói rằng tác tử **tin là** nó xong.

**`plan.merge` ráp theo đúng thứ tự bước**, sinh mục lục, hạ cấp tiêu đề cho khớp thứ bậc, ghi
rõ mỗi phần lấy từ tệp nào, và **kê ra phần nào không gộp được ngay trong tài liệu**. Nó không
viết lại nội dung: chỗ trùng lặp hay lệch thuật ngữ thì sửa bằng `fs.edit` sau đó, để diff
hiện đúng chỗ đã sửa.

Hai kiểu chia đều hợp lệ, và `plan.exit` **cảnh báo ngay lúc lập kế hoạch** nếu nhiều bước khai
cùng một tệp — lúc ấy sửa còn rẻ:

| | Mỗi bước một tệp rồi gộp | Mọi bước viết dồn một tệp |
|---|---|---|
| Hỏng một bước | làm lại **riêng bước ấy** | làm lại **cả nhóm** dùng chung tệp |
| Bước cuối | `plan.merge` ráp lại | không có gì để gộp — tệp ấy **đã là** bản hợp nhất |

### 12 · Tự kiểm chứng và tự bù năng lực

`task.run` giao việc cho **7 tác tử con**. Mỗi cái có **ngữ cảnh sạch** — nó *không thấy* cuộc
trò chuyện giữa người dùng và tác tử chính, để nó **đọc dữ kiện chứ không đọc kỳ vọng** — và
một tập công cụ hẹp, cắt đúng theo việc nó làm.

| Tác tử con | Việc | Công cụ | Trần | Luật riêng nặng nhất |
|---|---|---|---|---|
| **`datasheet-ingest`** | nạp tài liệu, trích Fact và bản đồ chân | 14 | 12 | *"Tài liệu không viết thì kho không có"* — cấm điền bằng tri thức chung về chip |
| **`firmware`** | viết và biên dịch mã, sửa tới khi sạch lỗi | 13 | 12 | `dat` **chỉ khi** `build.compile` trả về có tệp ảnh — biên dịch xong mới được nói là xong |
| **`design-review`** | soi bản đồ mạch và sơ đồ | 9 | 12 | tìm chỗ **sai**, không khen chỗ đúng; mỗi phát hiện nêu sai ở đâu · vì sao biết · hậu quả nếu để nguyên |
| **`sim-runner`** | nêu tiêu chí, chạy mô phỏng và test | 9 | 12 | *"đo, không phải thuyết phục"* — **không sửa ngưỡng** để một phép thử thành đạt |
| **`verifier`** | kiểm chứng báo cáo của tác tử khác | 10 | 10 | **không biết đề bài** (cố ý), chỉ có công cụ đọc |
| **`code-analyst`** | đọc mã đang có, nói sửa vào đây thì **gãy chỗ nào** | 10 | 14 | chỉ có công cụ đọc; câu đắt nhất giao cho nó là **chỗ gọi gián tiếp** — con trỏ hàm, macro, bảng phân phối — thứ phép quét văn bản mù hẳn |
| **`hardware`** | việc chạm bo thật | 5 | 12 | thao tác chạm bo phải người duyệt; thiếu công cụ thì trả `chua_du_du_kien` **kèm tên thao tác còn thiếu** | thao tác chạm bo phải người duyệt; thiếu công cụ thì trả `chua_du_du_kien` **kèm tên thao tác còn thiếu** |

**Mọi tác tử con kết thúc bằng đúng một dòng JSON** — `tom_tat` · `da_lam` · `bang_chung` ·
`chua_lam` · `ket_luan` · `do_tin` — và lược đồ ấy được kiểm bằng mã. Hai luật cứng trong đó:

* `bang_chung` phải trỏ tới thứ **người khác mở ra xem được**: mã hiện vật, tệp:dòng, mã
  changeset, dòng sổ cái. *"Tôi đã kiểm"* không phải bằng chứng.
* Thiếu dữ kiện thì `ket_luan` là **`chua_du_du_kien`**, không phải `dat`. Ba trạng thái, không
  hai — gộp *"chưa đo được"* vào *"không đạt"* là nói sai về hai tình huống khác hẳn nhau.
* `chua_lam` là phần **cố ý** không làm; để trống nghĩa là khẳng định đã làm hết.

**Hook `SubagentStop` tự gọi `verifier`** khi `firmware` hoặc `sim-runner` tuyên `dat` — hai
cái này tuyên đạt về thứ chạy được, nên chúng là chỗ đậu giả đắt nhất. Verifier mở từng mục
`bang_chung` ra xem nó **có nói đúng thứ báo cáo bảo nó nói không**; bằng chứng không mở được,
không tồn tại, hoặc nói điều khác là phát hiện quan trọng nhất nó có thể tìm ra.

Verifier có `snapshot.list` vì một lý do **đo được**, không vì cho đủ bộ: nó từng được giao
kiểm một bản ưng ý, thử `store.get("snap-01")` và nhận `E5005` — snapshot nằm ở cây riêng,
không nằm trong kho hiện vật chung. Nó kết luận `khong_dat` **vì không có công cụ để nhìn**,
chứ không vì có gì sai. Một người kiểm chứng bị bịt mắt đúng chỗ cần nhìn thì mọi kết luận của
họ đều nói về cái bịt mắt, không nói về sản phẩm.

`tool.propose` + `tool.reload`: khi tác tử thấy EIDE **thiếu một năng lực**, nó xin viết một
công cụ mới cho chính mình (R3, cổng G-TOOL). `tool.reload` **chạy bộ kiểm của công cụ ấy**
trước khi đăng ký — xanh mới nạp. Công cụ tự viết nằm ở `.eide/cong-cu/`, chỉ nạp cái nào có
bộ kiểm đi kèm.

`skill.load` nạp **7 hướng dẫn viết sẵn** theo ngữ cảnh — mỗi tệp khai `tu_khoa` và `khi_nao`,
và chỉ tốn token khi thật sự được nạp: `sim-criteria-first` · `avr-bare-metal` ·
`datasheet-onboarding` · `design-review-checklist` · `hardfault-analysis` ·
`explain-for-humans` · `trinh-bay-bang-hinh` · `chia-viec-lon`.

### 13 · Ba lớp chặn quanh mỗi lời gọi

**Hook S0** (0 token) chặn xác định trước khi tiêu một token nào: STOP, BACKREF, G-OPS,
P-SAFE, P-LAW, P-QUAL, P-INJ. Nhờ nó, "thiết kế thiết bị phá sóng" bị từ chối trong 8 giây và
"hạ tiêu chí xuống cho nó đạt" bị từ chối trong 2,6 giây — không gọi mô hình lần nào.

**Policy** trả `allow` / `ask` (dựng thẻ cổng cho người quyết) / `deny`. Mười cổng: G-DATA ·
G-DESIGN · G-FILE · G-FLASH · G-HIST · G-OPS · G-QUAL · G-SAFE · G-SCOPE · G-TOOL.

**Hook Stop** kiểm trước khi kết thúc lượt: giả định đã nói ra chưa · người vừa sửa đã được
nhắc tới chưa · lượt này có nói gì không · có việc nào chưa ai kiểm chứng không.

### 14 · Giao diện: người dùng làm được gì, không chỉ xem

Giao diện **không quyết gì** (I3) — nó vẽ lại thứ lõi gửi, và gói mọi cái chạm của người thành
một hành vi đi qua **đúng một cửa** (I1). Nhưng nó không phải chỗ chỉ để đọc:

* **11 bề mặt**, mỗi cái trả lời một câu hỏi: Yêu cầu & Giải pháp · Tài liệu & Nguồn · Tri thức
  mạch · Thiết kế · Công cụ · Mã nguồn · Mô phỏng · Mạch thật · Nhật ký · Lịch sử · Dự án & Bộ
  nhớ.
* **Sửa thẳng hiện vật.** Nhiều bảng có ô sửa được — người dùng đổi một giá trị thì đó là một
  changeset **mang tên họ**, không phải của tác tử, và tác tử buộc phải nhắc tới nó ở lượt sau
  (hook Stop chặn nếu nó lờ đi).
* **Nút "Vì sao?"** trên mỗi hiện vật mở đúng sáu trường `explain`: là gì · vì sao thế · dựa
  vào đâu · khác bản trước ở đâu · tiếp theo ai làm gì · tin được tới đâu.
* **Thẻ cổng** hiện **hậu quả trước lựa chọn**, và với công cụ tự viết thì hiện **mã nguồn** —
  duyệt một cái tên và một lời hứa thì không phải là duyệt.
* **Kéo–thả tài liệu** vào khung nhập: tệp được chép vào `tai-lieu/` của dự án rồi mới nạp, nên
  dự án mang đi nơi khác vẫn còn tài liệu (DEV-297).
* **Phím tắt**: `⌘N` dự án mới · `⇧⌘W` đóng dự án · `⌥⌘Z` **hoàn tác việc tác tử vừa làm**
  (khác `⌘Z` vốn là undo của ô văn bản) · `⌘.` dừng khẩn · `⌘R` vẽ lại.
* **Bề rộng Console** ba mức Hẹp / Vừa / Rộng, nhớ theo máy.

### 15 · Dữ liệu dự án: tất cả nằm trong một thư mục

Chép thư mục dự án **là** mang cả dự án đi — không có gì nằm ngoài nó. Tệp `du-an.json` ngay
trong thư mục là tấm thẻ căn cước: dự án của bản nào, chip gì, bao nhiêu yêu cầu, sổ cái toàn
vẹn không, và **phải mang theo cái gì**:

| Hạng | Nghĩa | Mất thì sao |
|---|---|---|
| `ben` | không dựng lại được | **mất hẳn**: sổ cái, kho hiện vật, changeset, blob, `EIDE.md`, `.git` |
| `dung_lai_duoc` | dựng lại từ nguồn | tốn thời gian, không mất thông tin: `.eide/build/`, thư viện hãng |
| `tam` | của phiên chạy | bỏ được ngay |

Phân hạng nằm **trong chính tệp**, không nằm trong đầu người viết công cụ sao lưu. `project.export`
đóng gói `.zip` theo đúng phân hạng ấy — đo trên dự án STM32 thật: **14,4 MB → 2,0 MB**. Nhập
lại thì **kiểm sổ cái trước khi mở**: gói hỏng hoặc bị sửa sẽ bị nói thẳng, chứ không mở im lặng
rồi lộ ra ở một lúc rất xa.

Gói xuất ra **mở được bằng bất kỳ trình giải nén nào** — không có định dạng riêng, vì một định
dạng riêng là một thứ nữa phải bảo trì và một thứ nữa có thể mất khả năng đọc.

### 16 · Lỗi là dữ liệu, không phải tai nạn

Mỗi lỗi mang bốn phần: mã (`E2013`), câu tiếng Việt cho người, **`hint_for_agent`** nói phải
làm gì tiếp, và `alternatives` liệt kê công cụ đi được. Nhờ vậy một lời từ chối không làm tác
tử đứng lại — nó đọc gợi ý rồi đổi hướng.

Đo được: xin xuất Excel từ một tệp không có bảng, `doc.render` trả `E2013`; tác tử đọc gợi ý,
**tự thêm một bảng thật vào nguồn**, xuất lại thành bảng 7 hàng dùng được, và **nói với người
dùng là đã sửa tệp của họ**.

### 17 · Bảo mật và riêng tư — bằng cấu trúc, không bằng lời dặn

* **Chỉ một mô hình.** `ALLOWED_MODELS` chặn ở mức mã: đặt tên mô hình khác thì lõi **từ chối
  ngay khi khởi động**, không phải cảnh báo rồi chạy tiếp.
* **Khoá API chỉ nằm ở `.env`**, ngoài git. Không lệnh nào in nó ra, không tệp tạm nào chép nó.
* **Không mở cổng mạng nào.** App chạy lõi làm **tiến trình con**, nói JSON-RPC trên stdio.
  EIDE là ứng dụng một người trên máy cá nhân.
* **Hộp cát tệp.** Mọi đường dẫn đi qua một hàm duy nhất, kiểm **sau khi** `resolve()` — nên
  `../../..` và symlink trỏ ra ngoài đều không lách được.
* **Không lái giao diện ở mức hệ điều hành.** Bộ kiểm giao diện đi qua một kênh tệp riêng, vì
  `keystroke` của macOS gửi phím tới cửa sổ đang có tiêu điểm — và nó đã từng gõ nhầm vào ứng
  dụng khác của người dùng.
* **Ảnh chụp do chính app tự vẽ**, không dùng `screencapture` theo vùng — chụp theo vùng đã hai
  lần lọt cửa sổ khác vào ảnh, một lần có cả tệp `.env` kèm khoá API.

### Đã đo được gì

| Phép đo | Kết quả | Nguồn |
|---|---|---|
| 76 ca kiểm usecase qua app thật | **68/68 ca đo được đạt (100 %)** | [`BAO-CAO-TONG.md`](docs/review-v3/test/BAO-CAO-TONG.md) · [Excel](docs/review-v3/test/Usecase_Test_KET_QUA_29-09-2026.xlsx) |
| Quét giao diện 11 bề mặt | **124/124 ô** | [`ket-qua-giao-dien/`](docs/review-v3/test/ket-qua-giao-dien/) |
| Tác tử tự viết công cụ cho chính nó | **8/8** | [`thu_tu_viet_cong_cu.py`](tools/thu_tu_viet_cong_cu.py) |
| Xuất tài liệu Word · PowerPoint · Excel · PDF | **13/13** | [`thu_xuat_tai_lieu.py`](tools/thu_xuat_tai_lieu.py) |
| Quy trình lập trình (phân tích · mốc lùi · thiết kế) | **8/8** | [`thu_quy_trinh_code.py`](tools/thu_quy_trinh_code.py) |
| Vẽ sơ đồ mermaid (giao diện + tài liệu) | **18/18** | [`thu_so_do.py`](tools/thu_so_do.py) |
| Chia việc lớn → ghi từng chặng → hợp nhất | **12/14** | [`thu_chia_viec_lon.py`](tools/thu_chia_viec_lon.py) |
| Mã ↔ tài liệu thiết kế | **0 chỗ lệch** trên 15 tệp | `tools/kiem_tai_lieu.py` |
| Ca đơn vị | **1339** | `pytest tests/ -q` |
| Bo thật STM32F469I-DISCO | LCD 800×480 + cảm ứng + FreeRTOS đa tác vụ, đã xác nhận bằng mắt | [`docs/stm32f469-freertos/`](docs/stm32f469-freertos/) |

Mỗi ca kiểm có một tệp log riêng kèm **bảng từng lời gọi công cụ, tham số đầy đủ và mã lỗi**:
[`ket-qua-chay-lai/nhat-ky/`](docs/review-v3/test/ket-qua-chay-lai/nhat-ky/).

Chín lỗi tìm được trong đợt đo ghi ở [`LOI-TIM-DUOC.md`](docs/review-v3/test/LOI-TIM-DUOC.md),
**tách rõ lỗi sản phẩm khỏi lỗi của chính bộ đo** — hai loại ấy dẫn tới hai việc khác hẳn
nhau, và trộn chúng vào một cột là nói sai về sản phẩm.

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
| **HIER-A** | Cây khối phân cấp §2–3: lược đồ v3 có `down()` · Port ở biên khối · net theo phạm vi · `flatten(cây)` = netlist cũ 100 % · sáu bất biến `E8001`–`E8006` | xong |
| **HIER-B** | Fact theo cấp · ERC bốn ràng buộc §4.2 báo theo path (`board.check`) · STALE theo NÚT, nội bộ không lan sang anh em · cây gập/mở A5.9 · giải thích khối 7 câu | xong |
| **HIER-C** | Thư viện khối `block@semver` ba tầng · `instantiate` mọi số có công thức và NGUỒN, thiếu nguồn thì không đặt · trích khối có kiểm khép kín · snapshot ghi `block@semver` | xong |
| **HIER-D** | Sheet phân cấp: mỗi khối một `.kicad_sch`, Port → sheet pin/hierarchical label · đọc lại gói dựng lại ĐÚNG cây (`so_cay`) · `depth > 4` tự chuyển phân cấp | xong |
| **SCH-A** | Cờ + `eide/sch/` + `sch.compose` (khối → hàm SKiDL) · `sch.netlist` kiểm đẳng cấu bằng cách ĐỌC LẠI tệp · `sch.symbols` sinh từ Fact có ghi nguồn · R3 · chốt chặn không đề nghị cài KiCad | xong |
| **SCH-B** | `sch.place` bố cục xác định, tiêu chí đo bằng số · `sch.write` `.kicad_sch` qua kiutils, uuid theo ref · `sch.render` SVG tự vẽ, kiểm chữ không đè | xong |
| **SCH-C** | `sch.export` gói mở được ở máy có KiCad · `sch.import` phân loại ba loại thay đổi (bố cục / giá trị / cấu trúc), cấu trúc thì HỎI và KHÔNG ghi đè bản đồ | xong |
| **SCH-D** | Tiêu chí bố cục đo trên TỪNG sheet + đề nghị phân cấp bằng số (SCH07) · sổ `sch_sheets` + bản ưng ý gói cả nội dung tệp sơ đồ (SCH-16) · ký hiệu sinh từ Fact CHỜ người xác nhận, kiểu chân người sửa thành Fact NGƯỜI (SCH-14/15) · khối A5.8: ảnh bấm được, băng chất lượng từng trang, bảng ký hiệu sửa được | xong |
| **G6** | `env.check`/`tool.install` (G-TOOL) · `build.compile`/`build.map` (lỗi có toạ độ, symbol nào chiếm chỗ) · **criteria-first**: `sim.criteria` nêu tiêu chí TRƯỚC, tiêu chí PHÁN XỬ kết quả chứ không phải chương trình mô phỏng, đổi ngưỡng khi đã có kết quả → G-QUAL · `test.run` + độ phủ · **6 subagent** ngữ cảnh sạch, tool giới hạn, hook SubagentStop tự gọi **verifier** chỉ-đọc · **skill** nạp theo ngữ cảnh | xong |
| **G7-A** | Bo thật STM32F469I-DISCO: `doc.fetch` (tải tài liệu, magic byte, trần ép trong lúc đọc) · nạp tài liệu dạng **văn bản/mã nguồn** trích dẫn theo dòng · `doc.search_web` có backend GitHub của hãng khi `st.com` bị chặn · biên dịch **ARM bare-metal** (`armv6-m`/`armv7-m`/`armv7e-m`, `.bin` cho bo nạp kiểu ổ đĩa) · `target.detect`/`flash` (R4, G-FLASH, đối chiếu chip ba giá trị khop/lech/chua_so_duoc)/`verify` (đọc ngược Flash từ chip, so từng byte)/`log` · tab A9 hiện hash–đích–verify | xong |
| **G7-B** | `target.debug` (giải mã CFSR/HFSR 17 bit · khung ngắt · dấu vết ngăn xếp · lấy mẫu PC theo span · nguyên nhân reset · tra ký hiệu ba trạng thái) · `target.screen` (khung ảnh → PNG + 11 mắt xích LTDC→DSI→panel) · subagent `hardware` | xong |
| **Plan mode** | `plan.enter` khoá mọi công cụ ghi · `plan.exit` kiểm bằng mã rồi người duyệt qua G-SCOPE · kế hoạch là hiện vật, sống qua `kill -9` | xong |
| **Tự bù năng lực** | `tool.propose`/`tool.reload` — tác tử tự viết công cụ cho chính nó, chỉ nạp khi bộ kiểm của nó xanh · `test.sensitivity` đo xem bộ kiểm có đo gì không | xong |

## Cài và chạy

> **Cài lần đầu?** Đọc [**Hướng dẫn cài đặt đầy đủ**](docs/md/EIDE-CAI-DAT.md) — từ máy trắng
> tới lượt chạy đầu tiên, kèm bảng công cụ phần cứng (chỉ cài khi cần) và mục xử lý trục trặc.
> Phần dưới đây là bản rút gọn cho người đã quen.

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
.venv/bin/python tools/kiem_tai_lieu.py              # tài liệu có nói khác mã không (0 token)
.venv/bin/python -m pytest -q                        # 1232 test: hook, policy, công cụ, sổ cái, cây khối, sơ đồ, bo thật
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
.venv/bin/python tools/thu_hier.py                    # 46 ca cây khối + ERC + STALE + thư viện khối
.venv/bin/python tools/thu_g6.py                      # 34 ca biên dịch, tiêu chí, subagent, verifier
EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/thu_sch.py    # 63 ca: sinh sơ đồ, sheet phân cấp, nạp lại, A5.8 + 10 đường hỏng
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_cuoi.py  # bằng chứng SCH-19: 36/36 giống hệt
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_giao_dien.py  # 24/24 — tab Thiết kế không đổi khi chưa sinh sơ đồ
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_g5.py   # bằng chứng SCH-19
.venv/bin/python tools/so_ket_qua.py --hai-che-do tools/thu_ing_a.py   # hồi quy hai chế độ cờ
.venv/bin/python tools/chay_kich_ban.py --lan 5      # bộ 76 TC, mỗi ca 5 lần
.venv/bin/python tools/theo_doi.py --du-an <thư mục> # theo dõi phiên thật qua sổ cái

# Một DỰ ÁN THẬT chạy từ đầu tới cuối, có ảnh chụp làm sở cứ (xem DEV-275):
EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/phien_robot.py        # 12 bước, tác tử thật
.venv/bin/python tools/doi_chieu_robot.py    # so netlist sinh ra với bảng 12/30/33 của tài liệu
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
