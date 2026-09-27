# EIDE-DEV-LOG — Nhật ký sai lệch tài liệu ↔ mã

Quy ước (README_REVIEW_BRIEF §8):

```
[DEV-2xx] <ngày> <tệp> — <tài liệu §> nói X; mã làm Y; vì sao; đề nghị cập nhật tài liệu: có/không
```

Tiếp nối dãy hiện có: DEV-183, 200–207, 212, 215, 216 đã dùng ở v1.x → bắt đầu từ **DEV-217**.

Nguyên tắc: tài liệu EIDE-MDD-40 v3.0 là nguồn sự thật. Mọi chỗ mã khác tài liệu phải
nằm ở đây. Không sửa tài liệu thiết kế — chủ sản phẩm cập nhật từ nhật ký này.

---

## Bước G1 — Lõi vòng lặp (25/09/2026)

### [DEV-217] 25/09/2026 · `src/eide/context/constitution.md` — ngân sách hiến pháp

MDD-40 §B2 (bảng ngữ cảnh) cho khối Hiến pháp ngân sách **~2 k token, cache**.
Mã hiện dùng **≈ 2 610 token** (đo bằng `approx_tokens`, 3 ký tự/token cho tiếng Việt).

**Vì sao:** §A3 đòi chín nguyên tắc trở thành *điều khoản hành vi*, §E3.1 đòi bảng sáu
trường của lớp giải thích, §E3.2 đòi năm quy tắc trình bày, và §C1 đòi bảng bốn tầng tin
cậy. Viết đủ bốn thứ đó bằng tiếng Việt, đủ rõ để mô hình theo được, không xuống dưới
2 k. Cắt xuống 2 k phải bỏ bảng bốn tầng hoặc bảng sáu trường — cả hai đều là thứ hook
sẽ kiểm, nên bỏ chúng khỏi hiến pháp là đặt bẫy cho chính mình.

**Chi phí thực tế:** khối này được cache ở đầu ngữ cảnh, nên 600 token dôi ra chỉ tính
tiền một lần cho mỗi phiên.

**Đề nghị cập nhật tài liệu: CÓ** — đổi ngân sách §B2 dòng Hiến pháp thành "~2,6 k, cache".

---

### [DEV-218] 25/09/2026 · `src/eide/rules/s0_rules.yaml`, `hooks/s0.py` — thêm quyết định `warn`

MDD-40 §A3 (N5) nói cổng an toàn "**chặn/hỏi** trước khi mô hình được gọi" — hai kết quả.
Mã có **ba**: `reject` (chặn hẳn), `ask` (thẻ cổng), và `warn` (trả lời an toàn ngay bằng
mã, 0 token, **rồi vẫn cho mô hình chạy tiếp**).

**Vì sao:** hai ca P-SAFE đòi hai thứ mâu thuẫn nhau nếu chỉ có chặn/hỏi.
TC036 ("chip nóng ran") cần câu "NGẮT NGUỒN NGAY" tới **trong vài giây, không chờ mô
hình** — nhưng sau đó người dùng vẫn cần tác tử giúp khoanh vùng nguyên nhân, mà chặn
hẳn thì không giúp được gì. TC069 (điện lưới) y hệt: cảnh báo cách ly phải đứng đầu,
nhưng phần thiết kế vẫn phải làm.

`warn` giải đúng chỗ đó: lời cảnh báo là **mã**, nên nó tất định và không hỏng khi mô
hình hỏng; phần giúp việc là **mô hình**, và nó nhận một chú thích dặn đừng lặp lại
nguyên văn cảnh báo.

**Đề nghị cập nhật tài liệu: CÓ** — §A3 N5 và §B4 dòng UserPromptSubmit nên ghi ba kết
quả: chặn / hỏi / **cảnh báo trước rồi cho đi tiếp**.

---

### [DEV-219] 25/09/2026 · `src/eide/hooks/standard.py` — hook Stop kiểm thêm "đã nói gì chưa"

MDD-40 §B4 liệt kê bốn việc cho hook Stop: giả định chưa nói? hiện vật thiếu explain?
`<human_edits>` chưa được nhắc? thẻ chờ chưa trả lời? Mã thêm việc **thứ năm**:
*lượt này đã nói câu nào với người chưa?*

**Vì sao:** TC057 của đợt đo 23/09 có cột kết quả **trống hoàn toàn** — lượt bị từ chối
bằng E5002 "chuỗi rỗng" và người dùng không nhận được gì. Một lượt kết thúc trong im
lặng là hỏng, bất kể bên trong nó đã làm gì. Suy ra trực tiếp từ §E3.2 quy tắc 4 ("chỉ
ra chỗ cần người") và quy tắc 5 ("không giấu thất bại").

**Đề nghị cập nhật tài liệu: CÓ** — thêm vào danh sách kiểm của Stop ở §B4.

---

### [DEV-220] 25/09/2026 · `src/eide/tools/builtin.py` — G1 không đăng ký công cụ ghi

MDD-40 §B3 liệt kê ≈ 40 công cụ, trong đó nhóm Store (`store.req_*`, `store.option_*`…)
ghi hiện vật. Bước G1 theo Phần G chỉ yêu cầu "10 tool đọc + ask_user", và mã **không
đăng ký công cụ ghi nào**, kể cả dạng rỗng.

**Vì sao:** đăng ký một công cụ hứa làm việc mà chưa làm được sẽ khiến mô hình gọi nó
và nhận về một thành công giả. Đợt đo 23/09 có đúng tiền lệ này: TC070 "an toàn do TAI
NẠN" — hành vi đúng vì một lý do sai. Hệ quả đo được: **TC002 và TC006 không thể đạt ở
G1** và được đánh dấu "Chưa đủ năng lực ở G1" trong bảng kết quả, không phải "Không đạt"
(theo tiền lệ TC061/TC071: gọi một khoảng trống phạm vi là lỗi thì bảng kết quả nói sai
về sản phẩm).

**Đề nghị cập nhật tài liệu: KHÔNG** — đây là ranh giới bước, không phải sai lệch thiết kế.

---

### [DEV-221] 25/09/2026 · `src/eide/policy/engine.py` — điều kiện policy dùng `eval`

MDD-40 §B4 viết điều kiện cấp quyền dưới dạng biểu thức (`when: "!source_quote"`,
`when: "constant_guard.unsourced > 0"`) nhưng không nói dịch chúng bằng gì. Mã dùng
`eval` của Python với không gian tên rỗng, sau khi đổi `&&`→`and`, `||`→`or`, `!`→`not`.

**Vì sao:** viết một bộ phân tích biểu thức riêng cho khoảng 15 điều kiện là công sức
không đổi lấy gì. An toàn ở đây dựa trên một sự thật về nguồn dữ liệu: `policy.yaml` là
tệp **của sản phẩm**, không phải đầu vào của người dùng hay của mô hình.

**Ràng buộc kèm theo đã hiện thực:** điều kiện không tính được sẽ **nổ** (`ValueError`),
không âm thầm thành "cho qua" — có test `test_dieu_kien_sai_cu_phap_thi_no_chu_khong_cho_qua`.

**Đề nghị cập nhật tài liệu: CÓ** — §B4 nên ghi rõ "policy.yaml là tệp của sản phẩm,
không bao giờ nạp từ nguồn không tin cậy".

---

### [DEV-222] 25/09/2026 · `src/eide/llm/gemini.py` — seed cố định

MDD-40 §F3 đòi "tất định"; §B2/§B3 không nói gì về seed. Mã đặt `seed = 7` cho mọi lời
gọi, cùng với `temperature = 0`.

**Vì sao:** yêu cầu cũ ở AGD-32 (Đ6) có câu "nhiệt độ parse/clarify/report = 0, seed cố
định nếu nhà cung cấp hỗ trợ". Gemini hỗ trợ `seed`, và nó làm tăng cơ hội hai lần chạy
cùng đầu vào cho cùng kết quả — đúng thứ §F3 đòi và đúng thứ bộ đo 5 lần/ca cần.
**Không** hứa tất định tuyệt đối: Gemini không đảm bảo điều đó, nên cách chấm "theo lần
chạy đầy đủ, không theo lần đẹp nhất" vẫn giữ nguyên.

**Đề nghị cập nhật tài liệu: CÓ** — đưa câu về seed từ AGD-32 §6 vào MDD-40 §F3.

---

### [DEV-223] 25/09/2026 · `src/eide/loop.py` — hook Stop chỉ được thêm đúng một vòng

MDD-40 §B4 nói hook Stop "cho mô hình thêm một vòng" khi phát hiện sót, nhưng không nói
giới hạn. Mã cho **tối đa một** vòng thêm mỗi lượt.

**Vì sao:** không có giới hạn thì một mô hình cứ lờ lời nhắc sẽ kéo lượt chạy tới khi
hết ngân sách 40 tool/300 s — và người dùng ngồi chờ một vòng lặp không bao giờ hội tụ.
Một vòng nhắc là để sửa sót; hai vòng trở lên nghĩa là mô hình không hiểu lời nhắc, và
lúc đó việc đúng là trả lượt cho người.

**Đề nghị cập nhật tài liệu: CÓ** — ghi giới hạn vào §B4 dòng Stop.

---

### [DEV-224] 25/09/2026 · `src/eide/protocol/ledger.py` — sổ cái có chuỗi hash

MDD-40 §F3 đòi "Toàn vẹn lịch sử: append-only; kiểm hash chuỗi changeset khi mở dự án"
— nói về **changeset**. Mã đưa chuỗi hash xuống **sổ cái sự kiện** (`ledger.jsonl`),
tức một tầng thấp hơn, và `changesets.jsonl` sẽ nằm trên nó ở G2.

**Vì sao:** changeset chỉ là một loại sự kiện trong sổ cái. Nếu chỉ changeset được bảo
vệ thì `human_act`, `gate` và `llm_call` vẫn sửa được — mà CX16 ("phát lại sổ cái +
changesets tái tạo transcript và trạng thái store 100 %") phụ thuộc vào cả bốn loại.
Bảo vệ tầng dưới thì tầng trên được bảo vệ theo.

**Đề nghị cập nhật tài liệu: CÓ** — §F3 đổi "chuỗi changeset" thành "chuỗi sổ cái".

---

### [DEV-225] 25/09/2026 · `src/eide/llm/gemini.py` — phải phát lại `thought_signature` của Gemini 3.x

MDD-40 §B1 mô tả vòng lặp bằng `msgs.append(...)` — một danh sách thông điệp trung tính.
Mã **không** dựng lại lượt của mô hình từ dạng trung tính đó, mà giữ và phát lại **đúng
các part** đã nhận, kèm `thought_signature` (base64 trong `Response.parts`).

**Vì sao — phát hiện khi đo thật, không phải lúc viết:** Gemini 3.x bắt buộc gửi lại
`thought_signature` đi kèm mỗi `functionCall` trong lịch sử. Thiếu nó, lượt gọi mô hình
**thứ hai** — tức lượt ngay sau khi có kết quả công cụ đầu tiên — hỏng:

```
400 INVALID_ARGUMENT: Function call is missing a thought_signature in functionCall parts.
```

Hệ quả đo được ở lần chạy đầu (7 ca × 5 lần, gemini-3.8-flash): tác tử **không bao giờ
đi quá một lời gọi công cụ**. TC003 trượt 0/5; TC001 1/5; TC004 3/5; TC005 3/5. Triệu
chứng dễ đọc nhầm thành "mô hình kém": lần trượt nào cũng ~3 s và ~4 450 token, tức là
nó chết ngay sau lời gọi đầu.

Điều đáng giữ lại từ sự cố này: lớp xử lý sự cố (UC19) **đã làm đúng việc của nó** —
nó không nuốt lỗi, nó nói đúng nguyên nhân ("Dịch vụ mô hình không trả lời được… Mọi thứ
đã làm trong lượt này vẫn còn"), và chính câu đó chỉ thẳng ra chỗ hỏng. Một lớp lỗi im
lặng sẽ để bug này sống tới tận G6.

**Đề nghị cập nhật tài liệu: CÓ** — §B1 nên ghi rõ: lịch sử gửi lại cho mô hình phải giữ
nguyên trạng phần do nhà cung cấp sinh ra, không được dựng lại từ dạng trung tính. Đây là
ràng buộc chung cho mọi adapter, không riêng Gemini.

---

## Cầu giao diện (25/09/2026)

### [DEV-226] 25/09/2026 · `src/eide/loop.py`, `protocol/rpc.py` — `attend` không chạy lượt, không có dòng transcript

MDD-40 §D2 liệt kê `attend` ("chuyển tab / chọn hiện vật") là một trong 13 HumanAct, và
§D1 I2 nói **mỗi HumanAct → đúng một dòng "[Bạn] …"**. Mã làm khác ở hai điểm, chỉ cho
riêng `attend`:

1. **Không gọi mô hình.** Lõi ghi nhận bề mặt người đang nhìn rồi trả lượt ngay.
2. **Không sinh dòng transcript**, không hiện thẻ Run, không vẽ lại bề mặt.

**Vì sao — đo được ngay lần chạy app đầu tiên:** mỗi cú bấm chuyển tab sinh một
`attend`; lõi coi nó như một lượt bình thường và gọi mô hình. Bảy cú bấm thành `run-007`,
mỗi lượt vài nghìn token, để trả lời một câu người dùng **chưa từng hỏi** — transcript
đầy những đoạn "Phần mã nguồn của dự án hiện chưa được triển khai…" mà không ai yêu cầu.

Lý do thiết kế: chuyển tab là **sự chú ý**, không phải **yêu cầu**. Tác tử cần biết người
đang nhìn gì (I4 — lõi chỉ thấy HumanAct kèm xuất xứ), nhưng biết không đồng nghĩa với
phải nói gì đó về nó. Và một dòng "[Bạn] Mở Mã nguồn" cho mỗi cú bấm sẽ nhấn chìm chính
cuộc hội thoại mà Console tồn tại để chứa.

**Điều KHÔNG đánh đổi:** `attend` vẫn được write-ahead vào sổ cái như mọi HumanAct khác,
nên CX16 ("phát lại sổ cái tái tạo transcript và trạng thái 100 %") vẫn đúng — bản phát
lại biết chính xác người đã nhìn gì, vào lúc nào.

**Đề nghị cập nhật tài liệu: CÓ** — §D1 I2 nên nêu ngoại lệ: HumanAct loại điều hướng
(`attend`) được ghi sổ nhưng không hiện thành dòng hội thoại. Và §D2 nên phân nhóm 13
loại thành *yêu cầu* (chạy lượt) và *điều hướng/thiết lập* (giải quyết bằng mã).

---

## Bước G2 — Changeset & lịch sử (25/09/2026)

### [DEV-227] 25/09/2026 · `src/eide/tools/writing.py`, `history.py` — changeset do CÔNG CỤ sinh, không phải hook PostToolUse

MDD-40 §B4 giao cho hook `PostToolUse` việc **"Tạo changeset (inverse ops) + ledger"**.
Mã làm khác: công cụ gọi `history.ghi_kho()` / `history.ghi_tep()`, và chính hàm đó sinh
changeset. Hook `PostToolUse` chỉ ghi sổ cái và bắt lỗi "log rỗng".

**Vì sao:** phép nghịch đảo cần **trạng thái TRƯỚC khi ghi**. Hook `PostToolUse` chạy
*sau* khi công cụ đã ghi xong — lúc đó bản cũ không còn ai cầm. Muốn hook làm được việc
này thì `PreToolUse` phải đoán trước công cụ sắp chạm hiện vật nào, tức phải biết ngữ
nghĩa tham số của từng công cụ một. Đó là chỗ dễ vỡ nhất có thể chọn.

**Ràng buộc §E5.1 vẫn được giữ nguyên** ("không có thay đổi nào ngoài changeset"), và
được giữ bằng **cấu trúc** chứ không bằng kỷ luật: không công cụ ghi nào gọi thẳng
`store.apply` hay ghi tệp; tất cả đi qua `ctx.history`, và chỉ nơi đó mới biết sinh phép
nghịch đảo. Muốn ghi mà không sinh changeset thì phải sửa `history.py` — đủ lộ liễu để
không ai làm nhầm. Ca CX16 kiểm đúng điều này: số sự kiện `changeset` trong sổ cái phải
bằng số dòng trong `changesets.jsonl`.

**Đề nghị cập nhật tài liệu: CÓ** — §B4 nên ghi "PostToolUse: ghi sổ cái, đồng bộ Surface,
đánh dấu STALE, lint log rỗng"; việc tạo changeset thuộc lớp công cụ.

---

### [DEV-228] 25/09/2026 · `src/eide/history.py` — tệp cũng là hiện vật trong kho

MDD-40 §E5.1 chia đôi nơi lưu: **tệp** trong git, **hiện vật có cấu trúc** trong store.
Mã giữ nguyên cách chia đó cho *nội dung*, nhưng thêm một việc: mỗi tệp được ghi cũng
được **đăng ký một bản ghi trong store** (`type: code` hoặc `memory`) chứa đường dẫn,
sha và kích thước.

**Vì sao — phát hiện khi chạy thử, không phải lúc viết:** đồ thị phụ thuộc §E5.4 làm việc
trên *hiện vật*. Lần chạy đầu, người sửa `FR-01` và danh sách STALE ra **rỗng** — vì
`drv_eth.c` chỉ tồn tại trong git, không có mặt trong kho, nên không hạ nguồn nào được
tìm thấy. Ca CX06 lẽ ra phải đỏ, nhưng nó sẽ im lặng xanh nếu ta chỉ kiểm "có STALE
không" thay vì "STALE có ĐÚNG danh sách không".

Git giữ **nội dung**; kho giữ **vị trí của tệp trong mạng lưới phụ thuộc**. Hai vai trò
khác nhau, không chồng lên nhau.

**Đề nghị cập nhật tài liệu: CÓ** — §E5.1 nên nói rõ tệp có bản ghi siêu dữ liệu trong
store để tham gia đồ thị phụ thuộc.

---

### [DEV-229] 25/09/2026 · `src/eide/vcs.py` — kho git phải là của chính dự án

Không phải sai lệch với tài liệu mà là **một lỗi đã xảy ra thật**, ghi lại vì nó thuộc
loại dễ tái phát.

`Vcs.san_sang` ban đầu hỏi `git rev-parse --git-dir`. Lệnh đó **đi ngược lên cây thư
mục**. Dự án mẫu nằm ở `du-lieu/du-an-mau/` bên trong kho git của chính mã nguồn EIDE,
nên lõi kết luận "dự án đã có git" và **không tạo kho riêng** — mọi commit của người
dùng sẽ đi vào kho của EIDE.

Sửa: so `git rev-parse --show-toplevel` với gốc dự án; chỉ coi là có kho riêng khi hai
đường dẫn trùng nhau. Có test `test_du_an_trong_kho_git_khac_van_co_kho_rieng` canh.

**Đề nghị cập nhật tài liệu: KHÔNG** — đây là lỗi hiện thực, không phải sai lệch thiết kế.

---

### [DEV-230] 25/09/2026 · `src/eide/loop.py` — "tác tử đã nhắc tới thay đổi của người" đo bằng chữ thật

MDD-40 §E4 bước 6 nói hook Stop kiểm "mọi changeset human chưa được acknowledged →
bắt mô hình thêm một vòng", nhưng không nói *nhận biết bằng cách nào*.

Mã nhận biết bằng cách tìm **mã changeset hoặc mã hiện vật trong những câu tác tử đã
thật sự nói ra** trong lượt (`ctx.loi_da_noi`, gom từ mọi `console.post` role=agent).

**Vì sao chọn cách máy móc này:** cách còn lại là hỏi mô hình "bạn đã nhắc chưa?", và
đó chính là kiểu tự chấm điểm mà N6 cấm. Ở đây ta kiểm **chữ đã hiện ra cho người đọc**,
không kiểm ý định của mô hình. Ca CX07 dựng hẳn một mô hình cư xử tệ (nó trả lời "Hôm
nay trời đẹp") để chắc rằng lớp này bắt được.

**Đề nghị cập nhật tài liệu: CÓ** — §E4 bước 6 nên ghi rõ tiêu chí acknowledged là sự
xuất hiện của mã hiện vật/changeset trong lời tác tử.

---

## Sau phiên dùng thật 25/09 (33 lượt, dự án "ổ USB Wi-Fi cắm TV")

### [DEV-231] 25/09/2026 · `src/eide/hooks/standard.py` — constant-guard chặn sạch, không cho ghi gì

**Lỗi nghiêm trọng nhất tìm được tới nay, và chỉ lộ ra khi có người dùng thật.**

MDD-40 §A3 N1: "mọi con số để so sánh/quyết định/sinh mã phải truy vết tới tài liệu".
Bản đầu hiện thực câu đó thành: bắt **mọi số ≥ 3 chữ số** trong **mọi tệp**, và coi là
có nguồn chỉ khi số đó khớp một **Fact trong kho**.

Kho Fact rỗng khi bắt đầu một dự án. Hệ quả: `not ctx.store.query_facts(limit=1)` luôn
đúng → **mọi hằng số đều bị coi là không nguồn** → mọi `fs.write` đều bị từ chối.

Đo được trên phiên thật: 33 lượt, hai lần `fs.write` (`scripts/setup_usb_gadget.sh` và
`HD-TRIEN-KHAI.md`), **cả hai bị DENY**, thư mục dự án kết thúc phiên chỉ có `EIDE.md`.
Tác tử đọc lỗi, gọi `fact.query` đúng như hướng dẫn, nhận về rỗng, rồi bó tay — vì ở G2
**chưa có công cụ nào tạo được Fact tầng NGƯỜI**. N1 đã thành một bức tường thay vì một
cái cổng.

**Sửa, bốn phần:**

1. **Thu hẹp phạm vi.** Chỉ soi tệp mã và cấu hình (`.c .h .sh .py .yaml`…). Tài liệu
   hướng dẫn là văn xuôi cho người đọc; con số trong đó thuật lại quyết định đã ghi nơi khác.
2. **Thu hẹp mẫu.** Chỉ bắt số **có đơn vị kỹ thuật** (V, mA, ms, kΩ, MHz…), địa chỉ
   hex ≥ 3 chữ số, và `#define X <số>`. Không bắt `chmod 755`, không bắt số thứ tự bước.
3. **Mở rộng "thế nào là có nguồn"** từ một đường thành bốn: Fact trong kho · `EIDE.md`
   (quyết định và quy ước đã chốt) · `explain.sources` của chính lời gọi · **lời người
   dùng trong phiên**. Cả bốn đều là "truy vết tới một nguồn có tên", đúng tinh thần N1.
4. **Mở đường thoát.** Thêm `fact.assert_human`: ghi con số người dùng vừa nói thành
   Fact tầng NGƯỜI, bắt buộc trích nguyên văn lời họ. Lời từ chối giờ nêu **đúng những
   hằng số nào** chưa có nguồn và ba đường đi tiếp.

**Kiểm lại trên cùng kịch bản:** 2 script được ghi, 2 Fact tầng NGƯỜI được tạo có trích
lời, 1 ADR, 1 quy trình 5 bước. Ba test hồi quy canh cả hai chiều (văn xuôi không bị
chặn; hằng số kỹ thuật trong mã vẫn bị chặn).

**Bài học đáng ghi hơn cả bản sửa:** một cơ chế an toàn quá nhạy không "an toàn hơn" —
nó chỉ khiến sản phẩm không dùng được, và người dùng sẽ tắt nó đi. Mọi lớp chặn phải
kèm một **đường đi tiếp** cụ thể, và lời từ chối phải nói rõ *cái gì* sai.

**Đề nghị cập nhật tài liệu: CÓ** — §A3 N1 nên nói rõ bốn nguồn hợp lệ, và §B4 dòng
constant-guard nên ghi phạm vi là tệp mã.

---

### [DEV-232] 25/09/2026 · `src/eide/loop.py` — báo cáo chi phí là của PHIÊN, không phải của LƯỢT

`_usage_total` được cộng dồn vào `self` và không bao giờ reset. Báo cáo lượt (§E2 dòng
"Báo cáo lượt" — "hết bao nhiêu") in ra tổng cả phiên: `run-018` báo **487.905 token**
trong khi thật sự nó tiêu ~150 k.

Người đọc con số đó không cách nào biết lượt vừa rồi đắt hay rẻ — tức mục "chi phí" của
báo cáo lượt mất hết ý nghĩa. Sửa: tách `ctx.usage_luot` (của lượt) và
`self.usage_phien` (cộng dồn); báo cáo in cả hai.

**Đề nghị cập nhật tài liệu: KHÔNG** — lỗi hiện thực.

---

### [DEV-233] 25/09/2026 · `tools/design.py` — bổ sung nhóm công cụ lưu quyết định thiết kế

Không phải sai lệch mà là **khoảng trống** phiên thật phơi ra.

Người dùng và tác tử chốt xong bo mạch (Raspberry Pi Zero 2 W), dung lượng, nhãn ổ, cơ
chế đồng bộ. Tất cả đi vào `EIDE.md` qua `memory.note` gọi **8 lần**, vì đó là công cụ
ghi duy nhất có. Hệ quả: quyết định không có phiên bản, không có hạ nguồn để đánh dấu
STALE, không hoàn tác riêng được, và sẽ bị nén mất khi ngữ cảnh đầy.

Thêm: `store.option_create`, `store.option_choose` (tự sinh ADR kèm trích lời người),
`store.adr_create`, `store.bom_set`, `store.procedure_set`, `store.procedure_progress`,
`fact.assert_human`. Hiến pháp §10 thêm bảng "chốt cái gì → ghi bằng công cụ nào", và
nói rõ `memory.note` chỉ dành cho mục tiêu / quy ước / §Đừng.

**Đề nghị cập nhật tài liệu: CÓ** — §B3 bảng công cụ thêm nhóm quyết định thiết kế;
§E2 thêm hai loại hiện vật **Script vận hành** và **Quy trình** (xem EIDE-NOTE-42).

---

### [DEV-234] 25/09/2026 · giao diện — dựng markdown khối và ký hiệu toán

`AttributedString(markdown:)` của Foundation chỉ xử lý **inline**. Tiêu đề, bảng, danh
sách, khối mã — tức phần lớn cấu trúc trong câu trả lời kỹ thuật — hiện ra dạng ký tự
thô. Phiên thật cho thấy tác tử dùng rất nhiều bảng so sánh và tiêu đề `###`; người đọc
phải tự giải mã `|---|---|`.

Thêm `Markdown.swift` (tách khối: tiêu đề, danh sách, bảng, khối mã, trích dẫn, đường
kẻ) và `MathText.swift` (LaTeX → Unicode: `\ge`→≥, `\mu`→µ, `x^2`→x², `\frac{a}{b}`→a/b).

Chọn Unicode thay vì dựng bộ sắp chữ TeX vì ba lý do: 95 % công thức trong ngành là ký
hiệu đơn lẻ; ký hiệu Unicode **sao chép dán được** sang Word/email mà không vỡ; và
tiếng Việt kỹ thuật vốn viết ≥, ×, µF, Ω. Phần không đổi được thì hiện nguyên bản kèm
ghi chú, **không giả vờ đã sắp chữ xong** (E3.2 §5).

Hiến pháp cũng được sửa để tác tử **viết thẳng Unicode**, chỉ dùng `$$…$$` cho công
thức thật sự cần đứng riêng.

**Đề nghị cập nhật tài liệu: CÓ** — §E3.2 thêm quy ước viết ký hiệu toán.

---

### [DEV-235] 25/09/2026 · `ui/.../UAP.swift` — hai đầu giao thức khác nhau về "khoá nào bắt buộc"

Bộ giải mã `Codable` Swift tự sinh **không dùng giá trị mặc định của thuộc tính**:
`var data: [String: JSONValue] = [:]` vẫn khiến cả thông điệp hỏng nếu JSON thiếu khoá
`data`. Lõi Python (`HumanAct.from_dict`) thì khoan dung đúng ở những khoá đó.

Hai đầu của một giao thức không được khác nhau về việc cái gì bắt buộc. Hệ quả đo được:
toàn bộ bài kiểm giao diện **im lặng hỏng** — mọi câu gõ vào bị vứt kèm một dòng
"HumanAct không hợp lệ" trong outbox, còn giao diện thì không hiện gì cả. Nhìn từ ngoài
y hệt "tác tử không trả lời".

Sửa: viết `init(from:)` tay cho `HumanAct`, khoan dung với `data`, `origin`, `text`,
`target`, `note` — khớp đúng hành vi của lõi.

**Đề nghị cập nhật tài liệu: CÓ** — §D2 nên ghi rõ khoá nào bắt buộc trong `HumanAct`
(chỉ `kind`; `decide` thêm `gate_id`+`approved`; `edit` thêm `base_version`), để hai
bản hiện thực không tự suy diễn khác nhau.

---

### [DEV-236] 25/09/2026 · `ui/.../UITestChannel.swift` — kênh kiểm thử giao diện

Không phải sai lệch tài liệu, mà là một bổ sung cần ghi lại vì nó chạm vào I1.

Kiểm thử giao diện bằng cách gõ phím qua hệ điều hành (`osascript … keystroke`) gửi
phím tới **cửa sổ đang có tiêu điểm**, không tới một ứng dụng cụ thể. Khi người dùng
làm nhiều việc cùng lúc, việc đưa app ra trước có thể thất bại trong tích tắc và phím
rơi sang ứng dụng khác — đã xảy ra thật: một câu tiếng Việt kèm Enter lọt vào cửa sổ
khác của người dùng.

Thay bằng kênh trong app: `<dự án>/.eide/ui-test/{inbox,outbox}.jsonl`, chỉ bật khi
thư mục đó tồn tại, và khi bật thì giao diện hiện một dải báo rõ.

**I1 vẫn nguyên vẹn:** mọi thứ đọc từ inbox đều đi qua `AppState.gui(_:)`, tức vẫn
thành `HumanAct` gửi qua `console.act`. Kênh này thay **ngón tay người**, không thay
giao thức.

Lợi ích vượt ra ngoài chuyện an toàn: kênh **đọc ngược** được trạng thái giao diện, nên
kiểm được những thứ chỉ đúng khi mã Swift chạy thật — bộ dựng markdown tách ra khối gì,
thẻ cổng hiện mấy dòng hậu quả, tab Mã nguồn có khối quy trình mấy bước. Kiểm ở tầng
giao thức không trả lời được các câu đó.

**Đề nghị cập nhật tài liệu: CÓ** — §F nên có mục "kiểm thử giao diện" mô tả kênh này.

---

## Bước G3 — Hiện vật hai dạng (25/09/2026)

### [DEV-237] 25/09/2026 · `src/eide/hooks/standard.py` — `sources` rỗng là hợp lệ khi không có số

MDD-40 §E1 nói công cụ ghi hiện vật "từ chối nếu thiếu explain hoặc thiếu một trong sáu
trường". Bản đầu hiểu câu đó theo nghĩa đen nhất: `sources: []` bị tính là thiếu.

Nhưng §E3.1 định nghĩa `sources` là *"mỗi số trong summary/why phải có nguồn trong danh
sách"* — nó ràng buộc **con số**, không ràng buộc **sự tồn tại của danh sách**. Một
hiện vật thuần mô tả ("đổi tên khối cho gọn", "ghi quy ước trao đổi tiếng Việt") không
có con số nào để dẫn nguồn.

Bắt chặt hơn thế gây hại theo một cách khó thấy: mô hình bị chặn ở một quy tắc nó không
thể thoả mãn một cách trung thực, nên nó sẽ **nhét một nguồn giả vào cho qua cửa**. Ta
đổi một quy tắc đúng lấy một thói quen sai, và từ đó trở đi `sources` không còn đáng tin.

Sửa: `sources` rỗng chỉ bị từ chối khi `summary` hoặc `why` **có chứa con số kỹ thuật**.
Test `test_CX02_sources_rong_hop_le_khi_khong_co_so` kiểm cả hai chiều.

**Đề nghị cập nhật tài liệu: CÓ** — §E1 nên ghi rõ ngoại lệ này cho `sources`.

---

### [DEV-238] 25/09/2026 · `src/eide/hooks/standard.py` — regex constant-guard thiếu đơn vị thông lượng

`MB/s`, `GB`, `Mbps` không có trong danh sách đơn vị, nên `≥ 5 MB/s` và `32 GB` lọt qua
constant-guard. Với một dự án truyền phim qua mạng thì đó đúng là hai con số quan trọng
nhất — tức lớp canh N1 bỏ sót đúng chỗ nó cần canh nhất.

Thêm nhóm thông lượng và dung lượng, và **đặt biến thể dài trước biến thể ngắn** trong
nhóm lựa chọn: không có thứ tự đó, `MB/s` khớp thành `MB` rồi bỏ rơi phần `/s`.

**Đề nghị cập nhật tài liệu: KHÔNG** — lỗi hiện thực.

---

### [DEV-239] 25/09/2026 · `src/eide/human_edit.py` — Fact tầng NGƯỜI sinh tự động từ sửa của người

MDD-40 §E4 bước 3 nói: "Số mới trong sửa không có nguồn → tạo Fact tầng NGƯỜI với
source = human_act". Mã hiện thực đúng câu đó, và thêm hai điều tài liệu không nói:

1. **Chỉ số MỚI mới tính.** Nếu bản cũ đã có "50 ms" và bản mới vẫn có "50 ms", đó
   không phải con số người vừa đặt ra.
2. **Số đã truy vết được thì bỏ qua**, dùng đúng khối nguồn mà constant-guard dùng
   (Fact + EIDE.md + lời người trong phiên). Hai lớp phải nói cùng một điều về cùng
   một con số, nếu không người sẽ thấy hệ thống tự mâu thuẫn.

Kèm theo: tác tử **nói ra** việc đó bằng lời — "con số này ở tầng NGƯỜI, mọi chỗ dùng
tôi sẽ ghi *(anh cho, chưa có tài liệu)*, muốn tôi tìm tài liệu nâng lên VÀNG không?"
Đo được ở ca CX05 qua giao diện thật.

**Đề nghị cập nhật tài liệu: CÓ** — §E4 bước 3 nên nêu hai điều kiện lọc trên.

---

### [DEV-240] 25/09/2026 · `history.ghi_kho(gay_stale=...)` — sửa trình bày không gây STALE

§E4.1 phân năm loại sửa của người và nói rõ loại "sửa trình bày" thì "nhắc ngắn; không
STALE". Mã hiện thực bằng `human_edit.phan_loai()` + tham số `gay_stale` của
`history.ghi_kho`.

Vì sao đáng có mã riêng thay vì cứ đánh dấu hết cho chắc: nếu đổi tên một khối cũng làm
cả chuỗi hạ nguồn sáng đèn, người sẽ học được rằng **băng cảnh báo không có nghĩa gì**,
và lần STALE thật sự quan trọng sẽ bị bỏ qua. Một cảnh báo mất giá còn tệ hơn không có
cảnh báo. Ca CX08 đo đúng chỗ đó.

Tác tử cũng **nói ra vì sao không có gì phải cập nhật**, để sự im lặng không bị hiểu
thành bỏ sót.

**Đề nghị cập nhật tài liệu: KHÔNG** — đúng như §E4.1 mô tả.

---

## Bước G4 — Nền tri thức (25/09/2026)

### [DEV-241] 25/09/2026 · `knowledge/docs.py` — con số đọc bằng mã, không qua mô hình

MDD-40 §C3 bước 4 đặt ranh giới trong một dấu ngoặc dễ lướt qua:

    "bảng → Fact ứng viên (**giá trị đọc bằng mã**, mô hình chỉ ánh xạ tiêu đề cột lạ
     → key chuẩn)"

Mã giữ đúng ranh giới đó: `trich_fact_ung_vien` tìm tên thông số trong một dòng rồi lấy
các số **có đơn vị trên chính dòng đó** bằng regex. Mô hình không bao giờ chạm vào giá
trị. Nó được phép nói "cột 'Supply Voltage' ứng với khoá `vdd`" và được phép giải thích
ý nghĩa — nhưng 5,5 V phải là thứ mở trang 258 ra đọc thấy.

Đây là khác biệt giữa một hệ thống **kiểm chứng được** và một hệ thống **phải tin lời**.
N1 chỉ có nghĩa khi ranh giới này được giữ.

Kèm theo: quy đổi đơn vị về SI trước khi so sánh (`ve_si`). Không có bước đó thì
`fact.compare` phải so `5000 mV` với `5 V` bằng chuỗi và kết luận sai — đúng loại lỗi
mà một công cụ "so sánh có bằng chứng" không được phép có.

**Đề nghị cập nhật tài liệu: KHÔNG** — đúng như §C3 mô tả.

---

### [DEV-242] 25/09/2026 · `knowledge/ingest.py` — lý do lỗi là một quyết định thiết kế

Năm ca của đợt đo 23/09 trượt không phải vì thiếu năng lực, mà vì **lý do lỗi sai**:
netlist, tệp Altium, zip hỏng và script bash đều nhận chung một câu "không nhận ra định
dạng nén".

Ca nặng nhất là TC070: kịch bản chứa `rm -rf $HOME/eide` **không chạy** — nhưng không
phải vì sandbox chặn hay vì ai đó hỏi, mà vì nó bị nhầm thành tệp nén rồi chết ở đó.
Bảng kết quả ghi "đạt". Đó là an toàn do tai nạn, và tai nạn thì không lặp lại được.

Giờ mỗi loại tệp có một bộ đọc và một lý do riêng, mỗi cảnh báo script mang theo **lý do
đọc được** ("xoá đệ quy thư mục người dùng", "tải rồi chạy thẳng — nội dung không ai
kiểm được trước"). Một cảnh báo không nói vì sao thì người sẽ bấm qua.

Kèm một ca ngược: `test_script_lanh_khong_bi_bao_dong_gia`. Báo động giả cũng là lỗi —
nó dạy người dùng bỏ qua mọi cảnh báo.

**Đề nghị cập nhật tài liệu: CÓ** — §B3 dòng `ingest.file` nên nêu yêu cầu "lý do lỗi
phải trỏ đúng nguyên nhân", vì đó mới là thứ năm ca kia đo.

---

### [DEV-243] 25/09/2026 · `knowledge/passport.py` — bổ sung `armv7-m` vào kho ISA

TC018 phát hiện một khoảng trống thật: kho chỉ có `armv7e-m` (Cortex-M4/M7 có FPU+DSP),
`avr8`, `rv32imac` — **thiếu `armv7-m`**, tức thiếu đúng Cortex-M3 của STM32F103, một
trong những chip phổ biến nhất.

Chọn `armv7e-m` cho M3 không phải là "gần đúng": nó sinh mã mang lệnh DSP mà chip không
có, và lỗi chỉ lộ ra khi nạp vào bo thật. Nên `bao_cao_isa` **từ chối thay thế bằng
kiến trúc gần giống** và nói thẳng khi kho thiếu manifest.

Kho hiện có 10 kiến trúc, gồm cả `aarch64`/`armv6` cho Raspberry Pi — loại dự án mà
phiên làm việc thật 25/09 cho thấy là có thật và MDD-40 chưa mô tả (xem EIDE-NOTE-42).

**Đề nghị cập nhật tài liệu: CÓ** — §C3 bước 6 nên liệt kê kho ISA và nêu rõ quy tắc
"không thay thế bằng kiến trúc gần giống".

---

### [DEV-244] 25/09/2026 · `knowledge/compare.py` — vế ĐỒNG trả về `chua_kiem_chung`, không trả kết luận

N2 nói so sánh chỉ hợp lệ khi cả hai vế ∈ {VÀNG, BẠC, NGƯỜI}. Mã hiện thực bằng cách
**trả về một kết quả loại `chua_kiem_chung`** thay vì trả kết luận kèm nhãn cảnh báo.

Khác biệt tưởng nhỏ nhưng quan trọng: một kết luận "3,3 V không đủ lái mức logic 5 V"
dựa trên con số mô hình nhớ được thì *nghe đúng* — và đó chính là chỗ nguy hiểm, vì nó
sẽ được tin và được dùng để quyết định. Trả nhãn "chưa kiểm chứng" bên cạnh một kết luận
nghe hợp lý là mời người bỏ qua cái nhãn.

Kết quả vẫn trình **cả hai vế kèm nguồn**, để người tự nhìn và tự quyết — chỉ là máy
không quyết hộ.

Đo được qua giao diện thật: tác tử gọi `fact.compare`, nhận `chua_kiem_chung`, và thuật
lại trung thực *"Công cụ so sánh tự động từ chối kết luận do thông số VOH chưa có trong
tài liệu"*.

**Đề nghị cập nhật tài liệu: CÓ** — §C2 nên ghi rõ `fact.compare` trả về một loại kết
quả riêng cho trường hợp này, không phải kết luận + cờ.

---

### [DEV-245] 25/09/2026 · `history.py` — nhánh dựa trên git, không phải copy-on-write

§E5.5 mô tả rẽ nhánh như một bản sao chép-khi-ghi của toàn bộ trạng thái dự án. Bản
dựng hiện tại rẽ nhánh bằng **git branch trên cây tệp** cộng với một checkpoint ngầm
cho phần kho hiện vật, chứ không nhân đôi kho.

Hệ quả thật, cần nói rõ chứ không giấu: **kho hiện vật (`store.sqlite`) không tách theo
nhánh.** Chuyển nhánh thì phần tệp đổi, phần yêu cầu/Fact/ADR thì không. Nó đúng cho
kịch bản §E5.5 nhắm tới ("thử hai cách viết driver"), và sai nếu người dùng muốn hai
nhánh có hai bộ yêu cầu khác nhau.

Không làm copy-on-write ngay vì nó buộc phải đổi khoá chính của mọi bảng trong kho —
một thay đổi lớn hơn toàn bộ G5, cho một tình huống chưa ai gặp. Cách lùi khi cần: ghi
bản ưng ý trước khi chuyển nhánh, rồi khôi phục — đường đó đã chạy và có ca đo.

**Đề nghị cập nhật tài liệu: CÓ** — §E5.5 nên nói rõ phạm vi của nhánh là *cây tệp*, và
bản ưng ý mới là thứ mang toàn bộ trạng thái.

---

### [DEV-246] 25/09/2026 · `choose` — câu trả lời trên thẻ từng rơi mất trước khi tới mô hình

Ba lỗ nối tiếp nhau trên cùng một đường, chỉ lộ ra khi gõ thật qua giao diện:

1. `HumanAct.transcript_line()` cho `choose` đọc `data.choice`, trong khi thẻ làm rõ trả
   về `data.answers` (nhiều câu một lượt). Dòng transcript ra `"Chọn: "` — rỗng. Và vì
   `loop._user_block` lấy `act.text or transcript_line()`, **mô hình không nhận được chữ
   người vừa gõ**. Người đặt tên bản ưng ý, rồi bị hỏi lại đúng câu đó.
2. Thẻ đã trả lời không rời `pending_cards`, nên khối `<pending>` vẫn nhắc "còn thẻ đang
   chờ" ở mọi lượt sau — và lõi cũng không phát `card.resolve`, nên thẻ vẫn nằm trên
   Console.
3. Không có công cụ nào **thực sự ghi** bản ưng ý: `snapshot.propose` chỉ hỏi, còn hai
   loại HumanAct `snapshot` và `branch` chưa ai xử lý. Tên người đặt rơi vào hư không.

Sửa: dòng transcript đọc `answers`; `choose` gỡ thẻ + phát `card.resolve`; chữ người gõ
vào thẻ được tính là **lời người trong phiên** (cùng hạng với câu gõ vào ô nhập); thêm
`snapshot.create` và hai đường xử lý HumanAct `snapshot`/`branch` chạy bằng mã, 0 token.

Kèm theo, `POL-SNAP-name` bị thay: nó khoá trên `args.by == 'agent'` — một tín hiệu **do
chính tác tử khai**, chỉ cần bỏ trường đó là qua. Luật mới `POL-E6-ten-do-nguoi-dat`
khoá trên một sự thật đo được: tên phải xuất hiện trong thứ người đã gõ ở phiên này.

**Đề nghị cập nhật tài liệu: CÓ** — §D nên ghi `choose` mang `answers` (dict), và §E6.2
nên nêu rõ đường ghi bản ưng ý gồm hai lối: người đã đặt tên → ghi thẳng; chưa đặt tên →
thẻ G-SNAP.

---

### [DEV-247] 25/09/2026 · Giao diện — markdown chỉ được dựng ở Console

Người dùng báo: *"Render markdown chưa full vẫn còn các ký tự ** chưa được render trên
màn hình."* Đo lại thì đúng — `SurfaceView.swift` **không gọi bộ dựng ở bất kỳ đâu**:
tóm tắt khối, ô bảng, dòng thời gian, bước quy trình, ô trống trung thực, chữ trên thẻ
cổng/thẻ làm rõ, thông báo và lớp "Vì sao?" đều vẽ bằng `Text` thô. Bộ dựng markdown
viết ở G3 chỉ được nối vào Console rồi dừng ở đó.

Sửa bằng một hàm `TextMd(_:)` dùng cho **chữ do tác tử viết**, và giữ `Text` thường cho
chữ do mã sinh (mã hiệu, số đếm, nhãn cột, đường dẫn) — ở đó `*` và `_` là ký tự thật
của một cái tên, diễn dịch chúng là làm hỏng cái tên. Chữ nhiều dòng (thân mục EIDE.md,
khối `text`, phần giải thích thêm) dùng `MarkdownView` để có cả tiêu đề, bảng, khối mã.

Điểm đáng giữ lại: lỗi này **không thể phát hiện bằng kiểm ở tầng giao thức**, vì lõi
gửi đúng chuỗi markdown — chỉ có tầng Swift làm sai. Nên ảnh chụp giao diện nay trả về
`loi_tac_tu_render` và `chu_da_dung` — chữ **sau khi dựng** — và bài kiểm hỏi đúng câu
người dùng đã hỏi: *trên màn hình còn dấu sao không?* Quét 6 tab, phải sạch.

---

### [DEV-248] 25/09/2026 · Thẻ cổng phát ra với danh sách hậu quả RỖNG

`loop._one_tool` dựng mọi thẻ cổng với `"consequences_vi": []`. `TheCongView` có hẳn một
khối vẽ hậu quả và một dòng bình luận gọi đó là quy tắc số 1 của §E7 — nhưng khối ấy
chưa bao giờ có dữ liệu để vẽ.

Hậu quả: mọi thẻ cổng chỉ còn một câu tóm tắt và hai cái nút. Người bấm mà không biết
mình đổi cái gì lấy cái gì, tức là **cổng chỉ còn tác dụng làm chậm, không còn tác dụng
bảo vệ**. Ca đo bắt được nó ở thẻ G-HIST khi khôi phục — nơi mã đã tính sẵn chính xác
sẽ mất gì (`se_mat_gi_khi_khoi_phuc`) mà không đưa lên thẻ.

`_hau_qua()` nay tính hậu quả từ **trạng thái thật**, theo từng công cụ: khôi phục nêu
đích danh hiện vật sẽ mất và cảnh báo nếu trong đó có sửa của người; thao tác phần cứng
nói rõ không lùi được; mọi việc nặng đều kèm câu "bản ưng ý gần nhất để quay về là gì" —
hoặc nói thẳng là chưa có bản nào.

---

### [DEV-249] 25/09/2026 · Đánh số lại E1003–E1008 của ING-43 thành E1010–E1015

EIDE-ING-43 §7 đặt sáu mã lỗi cho đường ống nạp, bắt đầu từ `E1003`. Mã đó **đã có
nghĩa khác trong sản phẩm đang chạy**: `errors.path_not_found` dùng `E1003` cho "không
có tệp ở đường dẫn" — cụm nguyên nhân lớn nhất của đợt đo 23/09 (11 ca), nơi mô hình bịa
một đường dẫn rồi ném vào tool. `hint_for_agent` của nó là thứ đẩy mô hình sang **hỏi**
thay vì **đoán**, và nó đang nằm trong ca đo xanh.

Đổi nghĩa một mã đang chạy để khớp bảng trong tài liệu là đặt sự gọn gàng của bảng lên
trên chỗ dựa của người đang dùng. Chủ sản phẩm chốt: **cấp mã mới**.

| ING-43 gọi | EIDE dùng | Nghĩa |
|---|---|---|
| E1001 | `E1001` | định dạng không hỗ trợ — trùng nghĩa, giữ nguyên |
| E1002 | `E1002` | tệp cụt/hỏng — trùng nghĩa, giữ nguyên |
| E1003 | **E1010** | tệp có mật khẩu |
| E1004 | **E1011** | vượt trần kích thước/số trang/số tệp |
| E1005 | **E1012** | tỉ lệ nén bất thường (zip bomb) hoặc đường dẫn thoát ra ngoài |
| E1006 | **E1013** | có macro — đã bỏ qua (CẢNH BÁO, không từ chối tệp) |
| E1007 | **E1014** | OCR thất bại |
| E1008 | **E1015** | chuyển đổi LibreOffice thất bại |
| — | `E1003` | **giữ nghĩa cũ**: không có tệp ở đường dẫn |

**Đề nghị cập nhật tài liệu: CÓ** — ING-43 §7 nên dùng bảng ánh xạ này.

---

### [DEV-250] 25/09/2026 · `ARTEFACT_TYPES` vượt 22 dòng của §E2

§E2 của MDD-40 liệt kê 22 loại hiện vật. Mã đang có 25: thêm `doc`, `procedure` và
`classification`.

- `doc` — §C3 nói tới tài liệu nạp theo trang nhưng bảng §E2 không có dòng cho nó, dù
  mọi Fact trích ra đều trỏ về một `doc`. Đây là chỗ thiếu của bảng, không phải mã.
- `procedure` — EIDE-NOTE-42 lập luận vì sao quy trình từng bước phải là hiện vật có
  cấu trúc chứ không phải một tệp `.md`.
- `classification` — mới trong ING-A. Kết quả phân loại được **ghi vào kho**, không chỉ
  trả về cho mô hình, để tab Tài liệu dựng khối A3.6 bằng mã (N3). Nếu nó chỉ sống
  trong một lời gọi tool thì thứ người nhìn thấy phụ thuộc việc mô hình thuật lại có
  đúng không — đúng cái N3 bỏ đi.

**Đề nghị cập nhật tài liệu: CÓ** — §E2 nên có ba dòng này kèm hợp đồng trình bày.

---

### [DEV-251] 25/09/2026 · classify v3 — thứ tự kiểm khác pseudocode của ING-43 §3 ở một chỗ

ING-43 §3 viết `if is_ole2(head): return LEGACY_OFFICE`, và để Altium rơi vào
`BINARY_UNKNOWN` ở nhánh sau. Trên máy thật thì **không tới được nhánh đó**: Altium
`.PcbDoc`/`.SchDoc` là tệp OLE2 thật, nên nó sẽ khớp `is_ole2` trước và bị gửi cho
LibreOffice như một tài liệu Word cũ.

Mã đặt phép kiểm `_KHONG_HO_TRO` theo đuôi **trước** OLE2, rồi trong nhánh OLE2 chỉ nhận
`.doc/.xls/.ppt`. Ca đo `test_ING04_altium_khong_bi_nham_thanh_office_cu` canh đúng chỗ
này.

Đi kèm, hai sửa nhỏ cùng loại:

- **Eagle `.sch`/`.brd` không còn bị từ chối theo đuôi.** Eagle từ v6 lưu XML, mà ING-43
  §2 xếp mức MỘT PHẦN. Bản trước đưa cả hai đuôi vào danh sách "không hỗ trợ", tức là từ
  chối nhầm đúng cái định dạng tài liệu bảo phải đọc. Nay quyết theo **nội dung**: giải
  mã được UTF-8 và có thẻ `<eagle>` → đọc; không giải mã được → mới nói là đời cũ.
- **Ba mức hỗ trợ thay cho `doc_duoc: bool`.** Giữa "đọc được" và "không" có một vùng
  mà người PHẢI biết mình đang ở trong đó — `.pptx`, HTML, `.kicad_sch` đọc được chữ
  nhưng EIDE không tự trích Fact. Một cờ nhị phân khiến người tin số máy tự trích từ
  những nguồn mà chính máy không dám tự trích.

Đo được: `thu_ing_a.py` 29/29 qua giao diện thật; ba bộ E2E cũ (G3 31/31 · G4 23/23 ·
G5 35/35) không hồi quy.

---

### [DEV-252] 25/09/2026 · Mở họ mã lỗi E8xxx cho sơ đồ/EDA

EIDE-SCH-44 §3 dùng `E7001` cho "netlist sinh ra lệch CKM" và `E7002` cho "chưa có
pinout đã duyệt". Cả hai mã **đã mang nghĩa khác**: họ `E7xxx` dành cho lịch sử và
changeset, và `E7001`…`E7007` đã dùng hết cho hoàn tác, khôi phục snapshot, đánh dấu
release, rẽ nhánh, ghi bản ưng ý.

Đây là lần thứ hai một tài liệu bổ sung đặt mã trùng (lần đầu: DEV-249). Chủ sản phẩm
đã chốt cùng một cách xử lý: **cấp mã mới**.

| SCH-44 gọi | EIDE dùng | Nghĩa |
|---|---|---|
| E7001 | **E8001** | netlist sinh ra không đẳng cấu với CKM — dừng, kèm diff |
| E7002 | **E8002** | chưa có pinout đã duyệt cho một ref — không bịa chân |

Họ `E8xxx` để dành cho sơ đồ/EDA, còn chỗ cho SCH-B…D đánh số tiếp. Hôm nay mới **đặt
chỗ trong bảng họ mã** (`errors.py:31–33`); hàm dựng lỗi viết khi SCH-A cần tới.

**Đề nghị cập nhật tài liệu: CÓ** — SCH-44 §3 và §5 nên dùng E8001/E8002.

---

### [DEV-253] 25/09/2026 · SCH-0 — ba thứ hạ tầng mà SCH-44 dựa vào nhưng chưa tồn tại

Rà SCH-44 cho thấy §2.1 và §8 đứng trên ba cơ chế mà bản đang chạy không có. Làm chúng
thành một bước riêng **trước** SCH-A, vì chúng là *bằng chứng* mà quy trình đưa tính
năng vào đòi, không phải phần của tính năng.

**1. Cờ tính năng.** `Features` trong `config.py`, đọc theo thứ tự: mặc định trong mã →
`~/.eide/settings.json` → biến môi trường `EIDE_FEATURE_<TÊN>`.

Điểm cần nói rõ vì dễ nhầm: cờ tính năng **không phải** `ToolSpec.core`. `core=False` là
*nạp trễ* — công cụ vẫn được đăng ký, chỉ giấu khỏi lược đồ cho tới khi `tool.search`
mở ra, nghĩa là mô hình **vẫn gọi được**. §2.1 đòi mạnh hơn: cờ tắt thì công cụ *không
được đăng ký*. Nên `Registry.add()` bỏ qua hẳn spec có `feature` chưa bật, và ghi tên
nó vào `bo_qua_vi_co` để còn kiểm được. Ca đo canh cả đường `tool.search` không moi
được ra.

Mặc định khi không biết cờ nào bật (`features=None`) là **TẮT** — thiếu thông tin thì
nghiêng về phía an toàn, không nghiêng về phía tiện.

**2. Migration cho Store.** Ba bảng đang dựng bằng `CREATE TABLE IF NOT EXISTS`, không
có `PRAGMA user_version`. Hệ quả: **mọi thay đổi lược đồ là thay đổi không quay lại
được** — thêm một bảng xong, muốn gỡ thì chỉ còn cách sửa tay trên kho của người dùng.
SCH-18 đòi `down()`.

Nay có `MIGRATIONS` với `up`/`down`, `nang_cap()` áp phần còn thiếu khi mở kho, và
`ha_cap(den)`. Hai chi tiết có chủ đích: kho cũ chưa đánh số (`user_version = 0`, bảng
đã có sẵn) vẫn nâng cấp được vì `up` của phiên bản 1 là idempotent; và `ha_cap(0)` —
tức xoá sạch kho — **bị từ chối** trừ khi gọi kèm `cho_phep_xoa_goc=True`, vì một lệnh
gỡ tính năng không được phép vô tình xoá cả dự án.

**3. So hai lần chạy.** §8 bước B và C đòi "hồi quy hai chế độ giống 100 %", trong khi
bốn bộ E2E hiện in bảng ra màn hình cho người đọc. Đọc bằng mắt hai bảng 35 dòng thì
bắt được khác biệt lớn; thứ nguy hiểm là **một ô lặng lẽ đổi từ đạt sang không đạt**.

`Bo.ghi_ra()` ghi kết quả ra JSONL, `tools/so_ket_qua.py` so hai tệp và
`--hai-che-do <kịch bản>` chạy một bộ hai lần (cờ tắt / cờ bật) rồi so. Phép so cố ý
**bỏ cột bằng chứng**: bằng chứng chứa lời mô hình sinh ra, đổi mỗi lần chạy, nên đưa
vào sẽ làm mọi lần so đều báo khác — và một phép kiểm luôn kêu là một phép kiểm không
ai đọc nữa. Tệp rỗng hoặc thiếu trả mã thoát 2, không bao giờ báo "giống" (N6).

Đo được: 239 ca đơn vị; `so_ket_qua.py --hai-che-do tools/thu_ing_a.py` → 29/29 khớp
giữa hai chế độ.

---

### [DEV-254] 25/09/2026 · Hiến pháp vượt trần 2 000 token — nâng trần, và đặt người canh

Đồng hồ ngữ cảnh vừa dựng xong đã bắt được một thứ ngay lần chạy thật đầu tiên: khối
hiến pháp **3 503 token** trên trần 2 000 mà MEM-42 §4.1 ghi, kèm ghi chú *"Không xảy ra
(cố định)"*.

Con số 2 000 được ước **trước khi** chín nguyên tắc được viết ra kèm lý do và trước khi
§10 có bảng "chốt cái gì → ghi bằng công cụ nào". Đo lại từng mục: mỗi nguyên tắc ~200
token, §10 là 628.

Chọn cắt hiến pháp cho vừa con số, hay sửa con số? Hai dữ kiện quyết định:

- Bảng §10 là thứ **đo được là đổi hành vi** — nó là lý do tác tử ghi hiện vật thay vì
  kể trong văn xuôi (G3), và ghi bản ưng ý đúng đường (G5). Cắt nó để đạt một mục tiêu
  ngân sách là đổi một hành vi đã đo lấy một dòng trong bảng.
- Khối này **được cache** (prompt caching), nên chi phí mỗi lượt gần như bằng không, và
  3,5 k trên cửa sổ 1 M là 0,35 %.

Nên: trần lên **3 600**. Nhưng một cái trần không ai canh thì không phải là trần — hiến
pháp là khối DUY NHẤT không tự co lại được (EIDE.md và `<facts>` đều có bước cắt). Nên
đi kèm là ca đo `test_hien_phap_khong_duoc_phinh_qua_tran`: thêm chữ vào hiến pháp thì
ca đỏ, và người thêm phải quyết định có đáng không — thay vì lặng lẽ nâng trần lần nữa.

**Đề nghị cập nhật tài liệu: CÓ** — §4.1 nên ghi 3 600 và bỏ ghi chú "không xảy ra".

---

### [DEV-255] 25/09/2026 · MEM-A — kết quả công cụ không còn đi nguyên văn vào ngữ cảnh

MEM-42 §5.1 gọi đây là *"biện pháp quan trọng nhất và rẻ nhất"*. Bản trước không có gì:
`res.to_model()` đi thẳng vào transcript, chỉ `fs.read` tự cắt theo byte và `fs.grep`
cắt 200 ký tự mỗi dòng. `BlobStore` đã có sẵn, content-addressed, đã chạy thật cho
snapshot từ G5 — nhưng chưa bao giờ được nối vào kết quả công cụ.

Nay mỗi kết quả đi qua `ToolResultEnvelope` với bảng chính sách 15 công cụ. Đo trên tệp
3 000 dòng thật: **62 561 → 1 268 token** vào ngữ cảnh, phần dư nguyên văn nằm ở blob.

Ba điều bộ này cố ý **không** làm, và mỗi điều có một ca đo canh:

1. **Không cắt lặng lẽ.** Mọi lần cắt để lại `_cat` nói rõ đã hiện bao nhiêu và gọi gì
   để đọc tiếp. Thiếu kho blob thì phong bì **nói thẳng** "phần dư KHÔNG lưu lại được"
   thay vì im lặng làm mất.
2. **Không cắt cái nhỏ.** Dưới trần thì đi qua nguyên vẹn — bọc mọi thứ chỉ tăng token
   mà không giảm gì.
3. **Không cắt lỗi.** `EideError` mang bốn trường để mô hình đổi hướng (§B3); cắt nó là
   cắt đúng thứ đang cứu lượt.

Kèm `blob.read` — không có nó thì "cắt" thành "mất". Nó có trần cứng 60 k ký tự mỗi lần
gọi, để chính nó không thành cửa sau nhét cả tệp vào ngữ cảnh.

**Một lỗi tìm ra khi chạy thật:** bảng đề mục luôn rỗng, vì `fs.read` trả nội dung **đã
đánh số dòng** (`"  123\tmã"`) còn regex đề mục khớp từ đầu dòng. Hệ quả: mô hình nhận
60 dòng đầu mà không có gì để biết nên đọc tiếp đoạn nào — tức phần "gợi ý range" của
§5.1 mất tác dụng trong im lặng. Ca đơn vị nay canh trên chuỗi **đã đánh số**.

---

### [DEV-256] 25/09/2026 · C1 đếm theo LƯỢT, không đếm message

Bản trước giữ "10 lượt gần nhất" bằng cách giữ **10 message cuối** (`loop._compact`).
Một lượt thật thường là 4–10 message (lời người + lượt mô hình + nhiều kết quả công cụ),
nên "10 message" thực tế là **chưa tới hai lượt**. Đây là lý do người dùng thấy tác tử
quên những thứ vừa nói ở đầu cùng một việc.

Và nó không phải "nén" — nó **vứt**: `self.messages = [head] + self.messages[-10:]`, các
message cũ biến mất không để lại đường nào.

C1 mới (`memory/compact.py`) làm bốn việc của §6.1, tất cả bằng mã, 0 token:
stub kết quả quá 8 **lượt** · dedup lần đọc trùng · supersede khi tệp đã bị sửa · thu
gọn thẻ đã đóng. Nó **không vứt message nào** — chỉ thay ruột bằng một dòng tóm tắt có
`blob_ref`, nên mọi thứ vẫn đọc lại được.

Ghim (§5.4) theo **ý chí của người**, không theo độ mới: một câu người gõ ba mươi lượt
trước vẫn ràng buộc hơn một kết quả công cụ của lượt vừa xong.

Ngưỡng kích hoạt cũng đổi: trước là một mốc 70 %; nay là bốn mốc 60/70/85/95 của §4.2,
và `muc_nen()` trả C0…C4. Ở MEM-A mới có C1; C2 (tóm tắt có cấu trúc) và PostCompact là
việc của MEM-C — tới đó mới có một phép đoán nằm giữa đường và mới cần kiểm ngược.

Đo được: 266 ca đơn vị · MEM-A 21/21 qua giao diện thật · hồi quy G3 31/31, G4 23/23,
G5 35/35, ING-A 29/29 — envelope đổi đường đi của **mọi** kết quả công cụ nên bốn bộ
này là phép kiểm thật sự, không phải hình thức.

---

### [DEV-257] 25/09/2026 · MEM-B — M1 lên đĩa, và ba lỗi im lặng tìm ra trên đường

Trước bước này `Agent.messages` chỉ là một `list` Python. Lõi chết giữa lượt là mất sạch
ngữ cảnh mô hình — **và không ai biết là đã mất**, vì sổ cái vẫn đầy đủ nên giao diện
dựng lại dòng hội thoại như không có chuyện gì.

`DanhSachGhiDia` là một `list` ghi xuyên xuống đĩa. Chọn một lớp thay vì "nhớ gọi thêm
một dòng ở mười chỗ `append`" là có chủ đích: bất biến write-ahead chỉ có giá trị khi
nó đúng ở **mọi** đường, và chỗ quên sẽ là chỗ thêm vào sau này chứ không phải chỗ đang
có hôm nay.

**Ba lỗi tìm ra khi chạy thật, cả ba đều im lặng:**

1. **`ChangesetLog.mark()` xoá sạch chuỗi hash.** Nó đọc lại qua
   `Changeset.from_dict → to_dict`, mà `prev_hash`/`hash` không phải field của dataclass
   nên rụng mất. Một lần tác tử nhắc tới thay đổi của người là đủ để cả tệp mất chữ ký.
   Nay `mark()` đọc JSON thô và chỉ sửa đúng trường được phép.
2. **`verify()` báo "toàn vẹn" cho những dòng KHÔNG có hash.** Đây là đạt giả đúng nghĩa
   N6: "chưa kiểm được" bị đếm thành "đã kiểm và đạt". Ca đo E2E xanh trước khi sửa lỗi
   (1), rồi vẫn xanh sau khi tệp bị sửa tay — nó xanh vì không còn gì để mà lệch. Nay
   dòng chưa ký làm `verify()` trả **False** kèm số lượng.
3. **Hiến pháp dặn mô hình gọi `plan.enter` — một công cụ không tồn tại** trong 49 công
   cụ đã đăng ký. Tìm ra khi phải rút hiến pháp cho vừa trần. Thêm ca đo quét mọi tên
   công cụ nhắc trong hiến pháp và đối chiếu với registry: một chỉ dẫn gọi công cụ không
   có thật là một lời hứa hão với mô hình.

**Về trần hiến pháp:** thêm nội dung MEM-B đẩy nó lên 3 735/3 600 và ca canh (DEV-254)
nổ. Lần này **không nâng trần** — rút được 138 token thật: bỏ chỉ dẫn `plan.enter`, gộp
hai câu lặp ý ở §2 và §5, rút gọn ví dụ ở §7. Còn 3 597/3 600. Đó đúng là công dụng của
một cái trần có người canh: nó buộc một quyết định, và quyết định đó tìm ra một lỗi.

**Còn lại của MEM-B, làm ở MEM-C:** resume đầy đủ (nạp lại M1 vào ngữ cảnh mô hình) và
bộ nhớ người dùng `~/.eide/memory.md` (M3). Bước này mới làm phần *ghi và giữ*; phần
*đọc lại vào ngữ cảnh* đi cùng C2/PostCompact vì hai thứ đó dùng chung đường lắp
transcript.

Đo được: 293 ca đơn vị · MEM-B 20/20 qua giao diện thật · hồi quy G3 31/31, G4 23/23,
G5 35/35, ING-A 29/29, MEM-A 21/21.

---

### [DEV-258] 25/09/2026 · MEM-C — nén có kiểm chứng, và bốn lỗi chỉ lộ khi chạy thật

PostCompact là mục mình đánh giá cao nhất trong cả MEM-42, và lý do nằm ở một câu: nó
biến *"nén có làm mất gì không"* từ cảm tính thành **một con số 3/3 hoặc một lần huỷ**.
Không có nó, cách duy nhất phát hiện mất mát là người dùng phải nhắc lại một quyết định
họ đã nói — tức ta để người đi phát hiện lỗi của mình (TC074).

Ba bước, và thứ tự là toàn bộ ý nghĩa: PreCompact (mã, 0 token) đưa sự thật có cấu trúc
vào M2 **trước** khi văn bản bị tóm → tóm tắt theo lược đồ 10 mục → PostCompact hỏi
ngược trên ngữ cảnh **đã nén**, sai thì khôi phục, K += 4, tối đa 2 lần.

**Bốn lỗi tìm ra khi chạy thật, không lỗi nào bắt được bằng ca đơn vị như mình viết ban đầu:**

1. **`copy.deepcopy(messages)` nổ giữa lúc nén.** `Agent.messages` là `DanhSachGhiDia` —
   một `list` con giữ `Transcript`, trong đó có `threading.Lock` không deepcopy được.
   Lỗi `TypeError: cannot pickle '_thread.lock' object`, và nổ đúng lúc ngữ cảnh đang
   đầy. Ca đơn vị bỏ lọt vì nó truyền `list` thường — **kiểm một container khác với
   container chạy trong sản phẩm**. Nay có ca đo chạy trên `Agent.messages` thật.

2. **`memory.compact` có giá trị mặc định cho `muc`.** Người nói "nén ở mức C2", mô hình
   gọi thiếu tham số, hệ thống lặng lẽ làm C1 rồi báo "đã thu gọn". Người tưởng đã tóm
   tắt, thực ra chưa. Bỏ mặc định: thà mô hình nhận lỗi thiếu tham số còn hơn làm một
   việc khác việc được giao mà không ai biết.

3. **"Chưa tới lúc nén" bị báo thành "nén không qua kiểm".** Hai chuyện khác hẳn nhau
   với người đọc: một cái là *hệ thống nghi ngờ chính nó*, cái kia là *chưa cần làm*.
   Gộp hai thành một câu là làm người lo vô cớ. Nay có cờ `khong_co_gi` riêng, và cả
   trường hợp này cũng ghi sổ cái — người vừa yêu cầu một việc, im lặng là sai.

4. **Nén làm ngữ cảnh TO RA mà vẫn nhận.** Khung bản tóm tắt 10 mục là ~1,3 k ký tự;
   nén một đoạn ngắn hơn thế nghĩa là trả tiền một lần gọi mô hình để làm mọi thứ tệ đi.
   Nay kiểm kích thước **trước** khi gọi PostCompact — không tốn nốt lần gọi thứ hai.

**Ba thứ nén không bao giờ được chạm, mỗi thứ có ca đo riêng:** message ghim theo ý chí
người (`decide`/`edit`/`snapshot`/`set`/`choose`/`undo`); nội dung người đã bảo quên
(bản tóm tắt chứa tombstone → huỷ nén); và bản cũ khi bất kỳ bước nào hỏng — mạng, lược
đồ sai, mô hình chết — transcript về đúng như trước, không bao giờ ở trạng thái "đã cắt
nhưng chưa có tóm tắt".

**Resume (§7.5)** dựng khối `<resume>` bằng mã từ sổ cái, kho và bản tóm tắt phiên trước.
Cách chữa TC065 (`previous_session.summary = null`) ở đây là **bỏ hẳn trường đó**: không
có chỗ nào để null. Chưa có tóm tắt thì khối nói "chưa có", và đó là một câu trả lời
đúng. Khối chỉ tiêm một lần, ở lượt đầu của phiên.

**M3 (§8)** có ba ràng buộc, mỗi cái chặn một kiểu hỏng: danh sách trắng sáu chủ đề
(không có nó thì "nhớ sở thích" trượt dần thành nhớ *về* người dùng); quét bí mật trước
khi ghi; và tác tử chỉ **đề xuất** qua thẻ, người bấm đồng ý mới ghi — một bộ nhớ tự lớn
lên là một bộ nhớ không ai kiểm.

Đo được: 331 ca đơn vị · MEM-C 23/23 qua giao diện thật với mô hình thật (C2 chạy thật,
kiểm ngược có điểm) · hồi quy G3 31/31, G4 23/23, G5 35/35, ING-A 29/29, MEM-A 21/21,
MEM-B 20/20.

---

### [DEV-259] 25/09/2026 · ING-B — bộ đọc Office, và ba lỗi lộ ra trên tệp thật

Phép thử có sức thuyết phục nhất của bước này là nạp **chính tệp yêu cầu nâng cấp của
chủ sản phẩm** (`EIDE-ING-43…docx`). Nó bắt ngay lỗi đầu tiên.

**1. `p.style` là `None`.** Một đoạn Word không có style làm `doc_docx` nổ
`AttributeError`. Tệp mẫu mình tự dựng không có đoạn nào như thế; tệp thật thì có. Một
bộ đọc tài liệu không được phép chết vì một đoạn thiếu định dạng.

**2. Bảng bị đọc như một dòng chữ.** Datasheet đặt đơn vị ở **cột riêng**:
`VDD max | 2.7 | 5.5 | V`. Bộ trích cũ tìm "số kèm đơn vị" trên một dòng, mà `5.5` và
`V` cách nhau một dấu gạch — nên nó trả về **rỗng** trên đúng loại tài liệu nó sinh ra
để đọc. Nay `Trang` mang theo từng ô và tiêu đề cột, và bộ trích đọc bảng như bảng:
cột Min/Typ/Max cho hậu tố khoá, cột Unit cho đơn vị.

**3. Ô Excel chỉ có công thức thì biến mất.** Tệp `.xlsx` chưa từng mở bằng Excel không
có giá trị đã tính; `data_only=True` trả `None`, cả hàng bị coi là rỗng và mất hẳn. Nay
chỗ nào không có giá trị thì lấy công thức làm nội dung — thà hiện `=AVERAGE(B2:B3)`
còn hơn không hiện gì. (Và công thức vẫn là *nguồn của số* theo §4.2.)

**Trích dẫn theo loại** là phần khó, không phải phần đọc chữ. Word **không có số trang
cố định** — nó phụ thuộc phông chữ và khổ giấy, nên trích dẫn theo trang cho Word là một
lời hứa sai với người mở tệp trên máy khác. Đơn vị trích dẫn nay là: `3.2 Electrical >
Bảng 1, dòng 2` cho Word · `Bảng đo!B7` cho Excel · `slide 12` cho PowerPoint. Ai cần số
trang thật thì `doc.to_pdf` sinh bản **phái sinh** cùng `doc_id`, và nói rõ đó là phái
sinh.

**Tầng theo nguồn (ING-19).** `doc.load` nay **bắt buộc** nêu `nguon` — không có mặc
định, vì tầng tin cậy của mọi Fact trích ra phụ thuộc vào nó và đoán sai thì một số nội
bộ đứng ngang hàng datasheet nhà sản xuất. Theo quyết định 25/09: `noi_bo` → **NGƯỜI**,
`nha_san_xuat`/`ben_thu_ba` → BẠC, nguồn lạ → NGƯỜI (phía thận trọng).

---

### [DEV-260] 25/09/2026 · PostCompact phải phân biệt "nén làm mất" với "câu hỏi vô lý"

Chạy MEM-C trên phiên thật cho một kết quả đáng chú ý: kiểm ngược **trượt 2/3 ba lần
liên tiếp**, nên C2 không bao giờ chạy được. Soi ra hai vấn đề riêng biệt, và cả hai đều
làm phép kiểm đo nhầm thứ.

**(a) Phép kiểm bị hỏi trên transcript trần.** Bản đầu chỉ truyền `messages`, không
truyền `<inventory>`. Nó biến câu hỏi thành *"transcript MỘT MÌNH có chứa X không"* —
chặt hơn tình huống thật, vì ở lượt bình thường mô hình luôn có khối kiểm kê. Câu "tiêu
chí của NFR-01 là gì" bị trả lời "không biết", trong khi con số đó nằm trong kho và tra
ra ngay. Sửa chỗ này **không** làm phép kiểm dễ đi: thứ đã nằm trong M2 thì mất nó khỏi
transcript là *đúng* — đó chính là điều PreCompact bảo đảm. Cái phải bắt là mất thứ
**không còn ở đâu khác**.

**(b) Câu hỏi mà mô hình chịu thua ở mọi nơi.** Nếu nó cũng sai trên ngữ cảnh **gốc**
thì nó đang đo khả năng của mô hình, không đo mất mát của phép nén — và nó sẽ huỷ mọi
lần nén. Nay khi kiểm trượt, hệ thống hỏi lại đúng bộ câu đó trên ngữ cảnh chưa nén; câu
nào sai ở cả hai bên thì **bị loại** và ghi sổ cái. Chỉ tốn thêm một lời gọi, và chỉ khi
đã trượt.

Loại hết câu thì sao? **Không được im lặng coi là đạt.** Kết quả ghi đúng chữ "KHÔNG
kiểm được", dòng báo cho người nói rõ "chưa kiểm được — nếu thấy tôi quên gì, bảo tôi
huỷ nén". Đây là N6 áp vào chính phép kiểm.

**Hai lỗi nhỏ hơn cùng đợt:** phép thử lại `K += 4` có thể đẩy K vượt độ dài phiên, và
vòng sau báo "chưa tới lúc nén" — **che mất** sự thật là kiểm đã trượt; nay dừng đúng
chỗ và nói đúng chuyện. Và bốn lối ra của `nen()` trước đây không ghi gì vào sổ cái:
người vừa yêu cầu một việc, im lặng là sai dù kết quả là "không làm gì".

**Một lỗi về phía bài kiểm, không phải sản phẩm:** bộ MEM-C có ba ô bị bỏ qua im lặng
khi C2 không chạy, làm số ca lúc 20 lúc 23 — mà một bộ kiểm đổi số ca giữa hai lần chạy
thì **không so được với chính nó** (SCH-19). Nay luôn chấm, và "C2 không chạy" là một ô
đỏ chứ không phải một ô biến mất.

Đo được: 359 ca đơn vị · ING-B 25/25 và MEM-C 26/26 qua giao diện thật · hồi quy G3
31/31, G4 23/23, G5 35/35, ING-A 29/29, MEM-A 21/21, MEM-B 20/20.

---

### [DEV-261] 26/09/2026 · Tên tầng nằm ở hai chỗ — thêm một tầng giết cả lượt

Thêm tầng **CẤU HÌNH** (ING-10/11) làm hỏng một thứ không ai ngờ: `KeyError: 'CAUHINH'`
trong `Inventory.render()`, tức **cả lượt chết trước khi mô hình được gọi**. Sổ cái ghi
đúng một dòng `incident` và không có `llm_call` nào.

Nguyên nhân: bảng tên tầng cho người đọc bị sao ra **hai chỗ** — `surfaces.py` và
`store/inventory.py`. Mình sửa bản thứ nhất, không biết bản thứ hai tồn tại.

Hai chỗ sửa, và chỗ thứ hai quan trọng hơn:

1. Một nguồn sự thật: `TEN_TANG_VI`, `THU_TU_TANG`, `ten_tang()` đặt ngay cạnh
   `TANG_DUNG_DUOC` trong `knowledge/compare.py` — nơi định nghĩa tầng.
2. **`ten_tang()` không bao giờ nổ.** Tầng lạ thì hiện nguyên mã. Một phép tra *tên hiển
   thị* không được phép có sức mạnh giết một lượt; nếu nó có, thì mỗi lần thêm một giá
   trị enum ta lại đánh cược cả sản phẩm vào việc mình có tìm hết bản sao hay không.

Ca đo `test_ten_tang_KHONG_BAO_GIO_lam_chet_mot_luot` canh cả hai.

Chỉ bắt được vì bài E2E có một ô cho **tác tử thật** làm việc qua giao diện. Ca đơn vị
gọi thẳng công cụ nên không đi qua `Inventory.render()`.

---

### [DEV-262] 26/09/2026 · ING-C — chuẩn hoá bằng mã, và bảng đọc như bảng

§5.2 giao việc này cho mã, không cho mô hình, và lý do đáng nhắc lại: `4R7` là 4,7 Ω,
`3V3` là 3,3 V, `100n` cạnh chữ "tụ" là 100 nF. Một mô hình đọc đúng chín lần rồi sai lần
thứ mười, và lần thứ mười đi thẳng vào một con điện trở người ta đi mua. Quy tắc này hữu
hạn nên nó phải là mã.

Ba quyết định trong `chuan_hoa.py` đáng ghi:

- **`raw` luôn còn.** Người rà soát đối chiếu với tài liệu bằng chuỗi nguyên văn, không
  bằng con số ta đã diễn dịch. Mất `raw` là mất khả năng cãi lại.
- **`—`/`N/A`/`TBD` là null CÓ LÝ DO, không phải 0.** Mỗi ký hiệu mang một lý do khác
  nhau ("nhà sản xuất chưa chốt" khác "không áp dụng"). Biến chúng thành 0 là cách nhanh
  nhất để một mạch chạy sai mà không ai hiểu vì sao.
- **Không đoán đơn vị khi không chắc.** `100n` không có ngữ cảnh thì trả `None` kèm lý
  do, không đoán nF. Một đơn vị sai tệ hơn không có đơn vị.

`M` hoa và `m` thường cách nhau một tỉ lần, nên bảng tiền tố phân biệt hoa/thường và có
ca đo riêng cho chuyện đó.

**Đối chiếu chéo nguồn (§5.3)** cố ý **không** tự hoà giải: nó xếp hạng theo
errata > DS mới > DS cũ > cấu hình > mã, nói vì sao, rồi để người chọn. Một hệ thống tự
chọn bên sẽ đúng phần lớn thời gian — và lần sai thì không ai biết là đã có mâu thuẫn.

---

### [DEV-263] 26/09/2026 · ING-D — tầng CẤU HÌNH giữ bằng cấu trúc, không bằng lời dặn

`.ioc`, `sdkconfig`, `.dts`, `.ld`, `map` nói **dự án đang đặt gì**, không nói **chip
chịu được gì**. Hai câu đó khác nhau về bản chất, và gộp vào một tầng thì phép so sánh
lấy `.ld` khai 64 KB làm sự thật trong khi chip có 32 KB.

Cách hiện thực ING-11 rất gọn và đó là điểm đáng nói: tầng `CAUHINH` **không nằm trong
`TANG_DUNG_DUOC`**, nên `fact.compare` tự động từ chối nó. Không ai phải nhớ quy tắc, vì
phép so sánh không cho lách.

Giá trị thật của tầng này ở chiều ngược lại: `doi_chieu_cau_hinh()` so từng cặp khoá và
phân biệt hai mức — **vượt** (mạch sẽ hỏng, chỉ là chưa biết khi nào) và **dùng gần hết**
(còn chạy nhưng hết chỗ thêm việc). Thông điệp nói thẳng: *"đây là lỗi sẽ không lộ ra lúc
biên dịch — nó lộ ra khi chạy, ở chỗ không ai ngờ"*.

**EDA**: bộ đọc S-expression viết tay 40 dòng thay vì thêm `sexpdata`/`kiutils` — định
dạng KiCad là S-expression thuần và ta chỉ cần `components` + `nets`. Mỗi phụ thuộc là
một thứ phải giải trình khi bảo vệ đề án mà không đổi được kết quả.

`doc_kicad_sch` nối net theo **nhãn**, không theo toạ độ dây, và **nói thẳng giới hạn
đó** trong cảnh báo trả về. Hứa nhiều hơn khả năng ở đây nghĩa là người tin một netlist
thiếu net.

Đối chiếu BOM ↔ netlist (TC062) tách ba loại lệch, và loại thứ ba tệ nhất: **giá trị
khác nhau** — mạch hàn xong *chạy* nhưng sai, nên không ai nghi ngờ nó.

BOM không có cột mã linh kiện thì **từ chối**, không đoán cột nào là cột nào: đoán sai
một cột là so sai cả bảng.

---

### [DEV-264] 26/09/2026 · ING-E — OCR sai không trông như sai

Một PDF hỏng thì báo lỗi. Một OCR sai thì trả về **chữ** — đọc được, có vẻ hợp lý, và
một con số trong đó có thể là `5.5` đọc từ `8.8`. Nên mọi đường ra của `ocr.py` mang ba
thứ: điểm tin cậy theo **từng từ**, trần tầng BẠC (§6, TC044), và kiểm gói ngôn ngữ.

**Gói ngôn ngữ là chỗ quan trọng nhất.** Máy này chỉ có `eng`. Đọc tiếng Việt bằng mô
hình tiếng Anh cho ra chữ nhìn như chữ mà sai, nên `kiem_goi()` **từ chối** và nói rõ
cách cài, thay vì OCR bừa rồi đưa số cho người dùng tin.

Điểm trung bình cả trang che mất chỗ hỏng — một bảng đọc tốt 95 % mà đúng cột số bị mờ
thì trung bình vẫn cao. Nên kết quả giữ cả danh sách từ dưới ngưỡng và liệt kê chúng ra.

**Nhận diện ngôn ngữ viết tay, không thêm phụ thuộc.** Việc cần làm chỉ là *chọn gói
OCR*, và đếm ký tự theo dải Unicode trả lời đúng câu đó — đồng thời giải trình được: ai
đọc mã cũng thấy vì sao nó kết luận "tiếng Việt". Kana thắng Hán vì văn bản tiếng Nhật
có cả hai còn tiếng Trung chỉ có Hán.

**Một ca đo của mình đo sai thứ, đã sửa:** ca OCR ban đầu kiểm "có đọc ra chữ VDD
không". Ảnh phông nhỏ cho ra `voDmaxs5V` điểm 0,16 — và hệ thống **gắn cờ đúng** là dưới
ngưỡng, bắt người rà. Độ chính xác của tesseract không phải việc của ta; việc của ta là
gắn cờ. Ca đo nay đo đúng tính chất đó, nên nó không đỏ theo phông chữ của từng máy.

---

### [DEV-265] 26/09/2026 · MEM-D — C4 thô có chủ đích, và dọn theo tham chiếu

**C4 (§6.5)** cố ý thô: không gọi mô hình, không tóm tắt, không phán xét cái gì quan
trọng. Ở mức 95 % thì mỗi lời gọi mô hình thêm vào là một rủi ro hỏng giữa chừng. Nó chỉ
thay mọi kết quả công cụ bằng một dòng có `blob_ref`. Hai thứ nó không chạm: message
ghim, và câu trả lời đang stream.

**Dọn rác (§7.4) theo THAM CHIẾU, không theo tuổi.** Một blob 400 ngày mà một snapshot có
tên đang trỏ tới là bằng chứng của một bản người dùng sẽ quay về; xoá nó theo tuổi là
biến "khôi phục được" thành một lời hứa suông. `_tham_chieu()` quét rộng tay bằng regex
trên mọi tệp có thể trỏ, thay vì đi theo lược đồ từng loại: giữ thừa một blob tốn vài KB,
xoá thiếu một blob làm một snapshot không khôi phục được.

`memory.gc` mặc định **chỉ đề xuất**; `thuc_hien=true` mới xoá.

**Đo lường (§13) đọc từ SỔ CÁI**, không từ biến đếm trong bộ nhớ: một biến đếm chỉ đúng
khi tiến trình còn sống, mà câu hỏi "bộ nhớ có tốt lên không" là câu hỏi qua nhiều phiên.
Và `dat_khong()` trả **"chưa đủ dữ liệu"** khi chưa đủ mẫu — N6 áp vào chính phép đo:
không có dữ liệu không phải là đạt.

---

### [DEV-266] 26/09/2026 · Một ca đo của mình ĐẬU VÌ LÝ DO SAI

Ô unhappy "tầng CẤU HÌNH làm vế so sánh" xanh — nhưng đọc `giai_thich` thì thấy
`"Không có luật tên 'bo_nho'"`. `fact.compare` trả `chua_kiem_chung` vì **tên luật lạ**,
không vì vế CẤU HÌNH. Tám luật thật tên là `ngan_sach_bo_nho`, không phải `bo_nho`.

Đây đúng loại "an toàn do tai nạn" mà ghi chú đầu `knowledge/ingest.py` nói tới, và nó
lọt vào chính bài kiểm của mình. Sửa: dùng tên luật thật, **và** thêm một câu khẳng định
rằng lý do từ chối không được chứa chữ "luật".

Bài học giữ lại: một ô xanh chưa nói gì cho tới khi biết nó xanh **vì cơ chế nào**.

---

### [DEV-267] 26/09/2026 · Bản đồ tri thức mạch (CKM) — MDD-40 §C2

Bước này lấp khoảng trống mà chính gap report EIDE-GAP-44 §2b.1 nêu: `sch.compose` mở đầu
bằng *"từ CKM đã có"*, nhưng bốn loại hiện vật `ckm`/`pinout`/`netlist`/`block_diagram`
trước đó **chỉ có tên** trong `ARTEFACT_TYPES` — không công cụ nào ghi chúng. Sinh sơ đồ
từ một bản đồ rỗng nghĩa là mô hình phải bịa linh kiện và chân, đúng thứ N1 cấm.

Tám công cụ mới: `ckm.chip_add`, `ckm.module_set`, `ckm.pinout_set`, `ckm.net_set`,
`ckm.import_netlist`, `ckm.graph`, `ckm.build`, `diagram.render`. Lược đồ kho lên v2
(`ckm_nodes`/`ckm_edges`), cộng thêm và có `down()` theo SCH-18.

**ĐƯỢC_GÁN duy nhất nằm trong CHỈ MỤC SQLite, không trong lời nhắc.** §C2 viết quan hệ
ĐƯỢC_GÁN kèm chữ "(duy nhất)" — đó là một bất biến vật lý: một chân làm được đúng một
chức năng. Nếu để phần mềm nhớ luật đó thì mỗi đường ghi mới là một cơ hội quên. Nên luật
là `CREATE UNIQUE INDEX … WHERE loai='DUOC_GAN'`: kho từ chối bản ghi thứ hai kể cả khi
lời nhắc, mô hình và người viết tool đều sai.

**Ba câu trả lời khác nhau cho "không gán được", không gộp.** Chưa nạp bảng chân (E8002)
≠ chip không có chân đó (E8003) ≠ chân chỉ có ở tầng ĐỒNG (E8006). Gộp lại thành "không
gán được" thì người đọc không biết phải làm gì tiếp. Lời từ chối E8003 **liệt kê chân có
thật**, nên nó dạy thay vì chỉ chặn.

**Mermaid do MÃ sinh, và cạnh suy ra từ TÊN tín hiệu.** Hệ quả tốt ngoài tính xác định
(N3, SCH17): nếu hai khối nghĩ khác nhau về tên một tín hiệu thì mũi tên **biến mất** và
người thấy ngay. Một hình do mô hình nối thì luôn đẹp và không bao giờ phát hiện lỗi đó.

### Ba lỗi thiết kế mà việc đo phơi ra

**1. Ghi thẳng vào KG làm hoàn tác nói dối (N9).** Changeset lùi lại bằng cách đặt
`canonical` của hiện vật về bản trước. Nếu KG được ghi trực tiếp thì sau một lần hoàn tác,
hiện vật lùi mà đồ thị vẫn còn chân đã gán — và người dùng nhìn hai chỗ thấy hai câu trả
lời khác nhau về cùng một mạch. Đó là cách tệ nhất để sai: không ai biết bên nào đúng.
Sửa: **hiện vật là sự thật, KG là hình chiếu** (`knowledge/ckm.chieu()`), đúng cách kho
làm với `events` → `artefacts`. `History._ap_nghich_dao` gọi `chieu()` sau khi lùi. Giá:
~12 ms mỗi lần ghi trên bản đồ 200 chân — rẻ hơn nhiều một bản đồ nói dối.

**2. Chân khoá theo tên chip làm một chân vào bản đồ HAI lần.** `pin:ATmega328P.27` do
bảng chân, `pin:U1.27` do netlist, và bản đồ đếm 5 chân trên một chip có 3. Tệ hơn: hai
con ATmega328P trên cùng một bo đè lên nhau, nên `ĐƯỢC_GÁN duy nhất` sẽ **chặn** việc gán
chân 27 của con thứ hai — một lời từ chối hoàn toàn vô nghĩa với người đang vẽ mạch. Sửa:
khoá theo **ref** (bo có thể có hai con cùng loại, nhưng không thể có hai U1); tên chip
thành thuộc tính, và gọi bằng tên chip khi có nhiều con thì **HỎI** (E8008) chứ không đoán.

**3. "6 chân chưa gán chức năng" là một con số thúc người làm sai việc.** Bốn trong sáu
chân đó thuộc một cảm biến **chưa có datasheet**, chúng tồn tại trong bản đồ chỉ vì một
net nhắc tới. Đếm chung là thúc người đi gán chân cho linh kiện họ chưa có tài liệu —
đúng chỗ N1 cấm. Tách thành `chan_chua_gan` (việc làm được) và `chan_khong_co_bang_chan`
(còn thiếu tài liệu).

### Hai chỗ suýt thành lời nói dối trên màn hình

Khối `A5.1` ban đầu khai loại `diagram`, và khối netlist gắn cảnh báo vào trường
`canh_bao`. Giao diện **không biết vẽ** loại `diagram` (nó hiện dòng "giao diện chưa biết
vẽ khối loại…") và **không dựng** `canh_bao` ở cấp khối. Cả hai chỉ lộ ra khi đọc ảnh chụp
màn hình thật. Sửa: bảng là dạng người đọc được ngay, mermaid đi vào khối `code` dán được
ra ngoài, và cảnh báo vào `summary` — chỗ chắc chắn có người đọc. Một cảnh báo ghi vào
trường không ai dựng thì tệ hơn không có cảnh báo.

### Trần token hiến pháp nổ lần thứ tư

Ba dòng mới (khối, gán chân, net) cộng luật "không bịa số chân" đẩy hiến pháp lên 3 746 >
3 600. Trả bằng cách nén chín chỗ diễn giải dài mà **không bỏ một luật nào** → 3 598.
Trần này đã buộc ra một quyết định thật ở cả bốn lần nó nổ.

### Một bộ kiểm làm đứt sổ cái của app

Lần chạy đầu của `tools/thu_ckm.py`: tác tử dành cả lượt báo *"sổ cái bị đứt thứ tự ở
dòng 26"* thay vì làm việc được nhờ. Nó phát hiện **đúng** — `Ledger` ghi nhớ `seq` lúc
khởi tạo và docstring của nó nói rõ chỉ an toàn trong MỘT tiến trình, còn bộ kiểm là người
ghi thứ hai. Sửa ở bộ kiểm (sổ cái riêng `.eide-thu`, kho dùng chung), không ở sản phẩm:
một dự án một tiến trình là ranh giới thiết kế, và phát hiện vi phạm ranh giới đó là hành
vi đúng.

**Số đo:** 46 ca đơn vị mới (tổng 544), `tools/thu_ckm.py` 35/35 qua giao diện thật, hồi
quy chín bộ cũ giữ nguyên. MEM-C có một lần 22/26 rồi xanh lại 26/26: câu hỏi ngược về
tiêu chí đo của NFR-01 bị mô hình trả "không biết", hệ thống **bỏ cuộc và giữ nguyên ngữ
cảnh** — đường an toàn đang chạy, không phải hồi quy. Đã ghi cảnh báo đó vào docstring
của bộ để lần sau không ai đọc nhầm.

---

### [DEV-268] 26/09/2026 · HIER-A — cây khối phân cấp, và một mô hình phẳng vừa ship bị sửa

EIDE-HIER-45 khác ba tài liệu bổ sung trước ở một điểm: nó **sửa** mô hình dữ liệu mà bước
CKM vừa đẩy cùng ngày. Bản đồ phẳng (khối là danh sách, net toàn cục, liên kết suy theo
TÊN chuỗi) thành cây: mạch → khối → khối con → linh kiện (lá), Port ở biên khối, net theo
phạm vi, `flatten(cây)` cấp netlist phẳng cho mọi tool cũ.

**Chỗ đổi quan trọng nhất không phải cái cây — mà là Port.** Trước, hai khối "nối nhau" vì
cùng viết chuỗi `"3V3"` vào `tin_hieu_ra`/`tin_hieu_vao`. Đó là phỏng đoán theo tên, và nó
không trả lời được ba câu: khối này *cấp* hay *nhận* 3V3? chịu bao nhiêu dòng? sửa ruột
khối có làm hỏng người dùng khối không? Port là hợp đồng có hướng, có ràng buộc, có Fact
chống lưng — và nó mua được **đóng gói**, thứ mô hình phẳng không có.

Lược đồ lên v3, cộng thêm, có `down()`: bốn cột `parent_id/kind/path/lib_ref` trên
`ckm_nodes`, hai bảng `ckm_port`/`ckm_connection`, chỉ mục `UNIQUE(path)`.

### Bốn chỗ làm khác tài liệu, mỗi chỗ một lý do

**1. `parent_id` dùng cho MỌI loại nút.** §2.3 tách `module.parent_id` và
`net.scope_module_id`. Cả hai là cùng một quan hệ "nút này nằm trong nút nào": khối → cha,
net → khối sở hữu, Port → khối có nó, chân → lá có nó. Một cột thì `path` tính được cho
mọi thứ bằng một hàm, và **không có chỗ nào để hai cột lệch nhau**.

**2. `ALTER TABLE module` — không có bảng `module`.** Module là hàng trong `ckm_nodes`. Và
`ALTER TABLE ADD COLUMN` không có dạng `IF NOT EXISTS`, nên viết migration thành SQL thuần
sẽ phá luật của chính tệp kho: *"up phải chạy lại được nhiều lần mà không hỏng"*. Luật đó
không hình thức — nó cho phép gọi `nang_cap()` trên một kho không biết đang ở đâu mà không
phải cầu nguyện. Nên `Migration.up/down` nay nhận **cả hàm**, và bậc v3 đi qua
`PRAGMA table_info`.

**3. Bất biến kiểm trong `chieu()`.** §3 nói "kiểm bằng mã sau mỗi thay đổi" mà không nói
ai gọi. `chieu()` là **một cửa duy nhất** mọi thay đổi bản đồ phải đi qua. Vi phạm được
TRẢ VỀ, không nổ — khác với chỉ mục ĐƯỢC_GÁN (kho từ chối ghi), một cái cây lệch vẫn phải
dựng lên được, vì nếu không thì người mất luôn đường nhìn thấy nó lệch ở đâu. `ckm.build`
liệt kê và đặt `du_de_sinh_so_do = false`.

**4. Mã lỗi E9001–E9006 thay vì E8001–E8006.** Ba tài liệu (SCH-44, HIER-45) và mã đang
chạy cùng đánh số E8001–E8006 với ba nghĩa khác nhau; sáu mã E8002–E8008 đã nằm trong ca
đo đã xanh. Anh chốt mở họ mới (26/09) — xem EIDE-GAP-44 §2c.3.

### Năm lỗi thật do việc đo phơi ra

**1. `flatten` để hai net khác nhau cùng tên ĐÈ nhau.** Mỗi khối có một "VDD" cục bộ là
chuyện thường. Nhóm thứ hai ghi lên khoá cũ trong dict ⇒ netlist phẳng **mất một net** và
không ai biết. Nay nhóm trùng tên mang đường đầy đủ.

**2. Di cư đánh mất chân của linh kiện chỉ netlist biết.** U3, U9 chưa có datasheet nên
bước CKM không tạo nút linh kiện nào cho chúng; `_noi_net` bỏ rơi chân của chúng và
`flatten` trả về một mạch **thiếu chân** — mạch trông như đã nối đủ. Nay ref nào có chân
thì có lá, kèm `chua_co_bang_chan: True` để E9004 không kết luận gì về nó (N6).

**3. E9006 mù đúng chỗ nguy hiểm nhất.** Bất biến "sửa nội bộ không thấy được từ ngoài" ban
đầu chỉ so `flatten` sau khi **lọc bỏ chân bên trong khối**. Gỡ Port VDD của khối MCU khỏi
net 3V3 làm khối **mất nguồn**, nhưng `U1.7` là chân bên trong nên phép lọc bỏ nó đi và
phép kiểm kết luận "không có gì đổi" — một câu sai về một mạch không còn chạy được. Nay
E9006 có **hai vế**: chân ngoài khối không đổi, **và** biên khối `{Port: net ở cha}` không
đổi. Vế hai bắt được ngay.

**4. `khoi_con()` trả về cả LÁ.** Một hàm tên "khối con" mà tính cả lá làm mọi phép đếm
khối lệch, và lệch âm thầm: gốc có hai khối + một lá (U2 — linh kiện chưa khối nào nhận) và
phép đếm trả 3. Tách thành `khoi_con` (chỉ khối) và `con_truc_tiep` (kể cả lá, đúng tập mà
một net được phép chạm Port của).

**5. Tiền đề "hộ chiếu chip đã ghim" TỰ THOẢ.** Nó đếm nút `chip`, mà `ckm.chip_add` tạo ra
đúng nút đó — nên tiền đề luôn đúng ngay khi chip vào bản đồ, kể cả khi chưa ai ghim hộ
chiếu. Tệ hơn: `ckm.chip_add` tra hộ chiếu bằng `store.get(chip)`, còn `passport.pin` ghi
hiện vật dưới mã `ns.part@semver` — nên ghim xong, `ckm.build` **vẫn** báo "thiếu hộ chiếu".
Một lời từ chối đúng luật nhưng sai sự thật là loại tệ nhất. Nay đếm chip CÓ hộ chiếu, và
tra theo tên chip.

### Một lỗi bộ kiểm, gặp lần thứ hai cùng ngày

`thu_ing_a` đỏ một ca với bằng chứng *"Sổ cái đang bị lệch thứ tự ở dòng 25"* — đúng triệu
chứng `thu_ckm` đã gặp sáng nay. `Ledger` ghi nhớ `seq` lúc khởi tạo và chỉ an toàn trong
MỘT tiến trình; bộ kiểm là người ghi thứ hai. Lần đầu tôi sửa tại chỗ trong một tệp; lần
này nó quay lại ở tệp khác, nên đã đưa `PathsThu` vào `tools/thu_giao_dien.py` cho mọi bộ
dùng chung. **Bài học: một lỗi sửa tại chỗ là một lỗi sẽ quay lại ở chỗ khác.**

Hai bộ đọc sổ cái của app (`thu_mem_b`, `thu_mem_c`) **không** đổi — với chúng, sổ cái của
app chính là thứ đang đo.

### Số đo

`580 ca đơn vị` (+35 cho cây) · `tools/thu_hier.py` **25/25** qua giao diện thật ·
`flatten(cây sau di cư) == netlist phẳng cũ` **100 %** (HIER01) · lược đồ v3 lên/xuống/lên
lại sạch, gỡ cây không mất Fact hay netlist (HIER-15).

**Hồi quy HIER-18, so bằng `tools/so_ket_qua.py`:** chín bộ **GIỐNG HỆT** (G3 31 · G4 23 ·
G5 35 · ING-A 29 · ING-B 25 · MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36). Bộ thứ mười
(`thu_ckm` 35/35) khác **đúng một tên ca**: "chip chưa ghim hộ chiếu thì nói ra" thành
"chip đã ghim hộ chiếu thì bản đồ ghi nhận" — vì luật siết theo SCH-44 §4, có chủ ý. Không
ca nào đi từ *đạt* sang *không đạt*.

---

### [DEV-269] 26/09/2026 · HIER-B — Fact theo cấp, ERC theo cây, STALE theo nút, UI cây

Bốn phần của HIER-45 §4/§6/§8. Phần nặng nhất **không có trong tài liệu**: HIER-17 nói
*"ERC/BOM/truy vết báo theo path khối"* — giả định đã có `board.check`. Mã chưa có ERC nào
cả: phép kiểm mạch duy nhất là `net_mot_chan()`. Nên HIER-B phải dựng ERC từ đầu.

**Bốn ràng buộc §4.2, và việc khó không phải phép so sánh.** `compare.py` đã biết so hai
Fact; cái thiếu là biết **Fact nào với Fact nào**. Một net nguồn ở gốc chạm chân lá qua hai
tầng Port, nên muốn biết ai cấp và ai tiêu thụ thì phải đi xuống tới lá. Đó là lý do
`knowledge/erc.py` tồn tại thay vì thêm luật vào `compare.py`.

**ERC xét theo NET ĐIỆN, không theo net phạm vi.** Một đường nguồn qua ba khối gồm bốn net
phạm vi; xét từng net thì cùng một ràng buộc bị báo **bốn lần**, và người học được cách bỏ
qua bảng ERC. Thêm `flatten_chi_tiet()` trả kèm `net_id → tên nhóm điện`.

**"Chưa đủ dữ kiện" là một kết luận, không phải một mức nhẹ của "đạt".** Cộng được 12 mA mà
còn một linh kiện chưa có Fact thì tổng THẬT lớn hơn — kết luận "đủ dòng" ở đó là một câu
đúng về một con số sai. Bảng ERC trên tab xếp theo **hậu quả**, và `_ket_luan_vi` dịch
`chua_du_du_kien` thành "chưa đủ dữ kiện" chứ không thành một sắc thái của "đạt".

**STALE theo NÚT, không theo loại hiện vật.** Bảng §6 nói *"sửa nội bộ khối X không lan tới
anh em của X; cha của X chỉ nhận cờ 'con đã đổi'"*. Chuỗi `HA_NGUON` là bảng loại→loại: sửa
một khối làm STALE **mọi** netlist và **mọi** mã. Trên mạch 40 khối, một thay đổi bật đèn ở
40 chỗ — và người học được rằng băng cảnh báo không có nghĩa gì. Đó là cách tệ nhất để mất
một cơ chế an toàn: không phải nó tắt, mà là nó **luôn bật**.

`lan_stale()` trả **hai** thứ khác nhau: `stale` (việc phải làm) và `chi_bao_tin` (chỉ cần
biết). Gộp chúng là biến mười thông tin thành mười việc không có thật. `stale.accept` nhận
cả đường dẫn nút và `ca_nhanh`, và lý do được **giữ** trong `stale_da_chap_nhan` chứ không
xoá trắng — một cảnh báo người đã cân nhắc rồi bỏ qua là thông tin, không phải rác.

**Hai câu của lớp giải thích khối do MÃ dựng** (§8, HIER-14): "giao tiếp gì (Port)" và "gồm
gì (con)" là **dữ liệu**, đọc được từ cây một cách xác định. Bắt mô hình viết chúng là mời
nó mô tả một khối theo trí nhớ — nó sẽ viết đúng chín lần rồi lần thứ mười viết một Port
không tồn tại.

### Bốn lỗi thật do việc đo phơi ra

**1. Khối cấp nguồn bị gate theo HƯỚNG Port.** Port của lá sinh khi di cư mô hình phẳng có
hướng `passive` (cố ý — `_huong_theo_ten` không đoán hướng tín hiệu). Nên một LDO có Fact
`iout_max` hẳn hoi vẫn "không phải khối cấp", và cả ràng buộc im lặng biến thành "chưa đủ
dữ kiện". Sửa: nhận diện bằng **Fact**, hướng Port là dữ liệu bổ trợ có thể chưa biết.

**2. Net khai cả `noi_port` lẫn `chan` thì MẤT CHÂN.** `_noi_net` bỏ qua net nào đã có kết
nối Port, nên phần `chan` bị bỏ hẳn và netlist phẳng thiếu `U1.7`, `U3.3` mà không ai biết.
Hai cách khai là hai **mức chi tiết** của cùng một net, không phải hai net. Sửa kèm: chân
đi qua **Port người đã khai** (`VDD`) thay vì sinh thêm một Port `3V3` trùng vai — một hợp
đồng có hai cửa cho cùng một đường thì không còn là hợp đồng.

**3. `lan_stale` trả RỖNG khi `muc_tieu` không phải nút.** Ba dạng trông giống nhau:
`module:MOD-MCU` (node_id), `/board/MOD-MCU` (đường dẫn), `module:/board/MOD-MCU` (**không
có thật** nhưng trông đúng nhất). Bộ đo của tôi gọi bằng dạng thứ ba và mọi phép lan trả
rỗng — "đổi Port không ảnh hưởng gì", sai và im. Sửa: `tim_nut()` nhận cả ba dạng, và id lạ
thì **NỔ** thay vì trả rỗng. Cùng lỗi với nhánh `req` trong chính hàm đó: `muc_tieu` là mã
REQ chứ không phải node_id, nên phép tra nút ở đầu hàm làm nó lặng lẽ trả rỗng.

**4. Một đường về sớm là một đoạn mã KHÔNG ca đo nào đi qua.** `_ghi_stale_nut` trả rỗng
ngay khi chưa có hiện vật sơ đồ khối, nên **mọi** ca đơn vị gán chân trước đây không bao giờ
chạm tới phép lan STALE. Khi `lan_stale` được làm cho nổ với id lạ, `pinout_set` vẫn gọi nó
bằng id đoán (`linh_kien:U1` trong khi nút thật là `chip:U1`) — và chỉ bộ E2E, nơi có sơ đồ
khối, mới đỏ. Đã thêm ca đơn vị đi qua đúng đường đó.

### Một lỗi không thuộc sản phẩm, nhưng mất 20 phút

Bộ E2E báo *"App không trả 'kenh_mo' sau 60s"* sau khi tôi thêm khối Swift mới. Nguyên nhân:
`swift build` dựng tệp thực thi nhưng **không đóng gói lại `EIDE.app`** — app đang chạy là
bản 21:17 hôm trước. Phải chạy `ui/EIDEApp/dong-goi.sh`. Ba ca đỏ vì lý do đó (dump trả
`None` cho khoá mới) không phải lỗi mã. Ghi lại vì nó sẽ tái diễn: **sửa Swift thì phải
đóng gói lại trước khi chạy bộ đo.**

### Số đo

`622 ca đơn vị` (+43) · `tools/thu_hier.py` **38/38** (từ 25) · `74 công cụ` (thêm
`board.check`, `ckm.port_set`).

**Hồi quy:** mười bộ E2E **GIỐNG HỆT** khi so bằng `tools/so_ket_qua.py` (G3 31 · G4 23 ·
G5 35 · ING-A 29 · ING-B 25 · MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35). Bộ HIER
chỉ **thêm** 13 ca, không ca nào đi từ *đạt* sang *không đạt*.

---

### [DEV-270] 26/09/2026 · SCH-A — sinh sơ đồ: ba bước đầu, và một phép kiểm phải thật

Ba công cụ đầu của đường ống bảy bước (SCH-44 §3): `sch.compose` → `sch.netlist` →
`sch.symbols`, tất cả sau cờ `features.schematic` (mặc định TẮT).

**HIER-45 §7 sửa SCH-44 ở chỗ quan trọng.** SCH-44 bản đầu coi mỗi module là một *vùng trên
sheet*; HIER-45 đổi thành *"mỗi khối → một hàm Python có tham số là các Port"*. Khác biệt
không phải hình thức: một hàm có tham số là một **hợp đồng kiểm được** — khối MCU cần ba
Port thì hàm có ba tham số, và gọi thiếu một cái là lỗi cú pháp Python, phát hiện trước khi
có ai vẽ gì. Một vùng trên sheet không kiểm được gì.

### Chỗ khó nhất: phép kiểm đẳng cấu phải ĐỘC LẬP

SCH-44 bước 2 nói `sch.netlist` chạy SKiDL rồi so netlist sinh ra với netlist CKM. Máy này
không có `skidl` (và cài nó cần thư viện ký hiệu KiCad, mà quyết định 25/09 nói không cài
KiCad). Đường dễ là: viết `.net` từ cây, rồi so với `flatten(cây)`.

**Đường dễ đó so chính mình với chính mình.** Nó **luôn đạt**, và một phép kiểm luôn đạt tệ
hơn không có phép kiểm — nó tạo ra niềm tin không có cơ sở. Đúng loại "đậu vì lý do sai" mà
DEV-266 ghi lại.

Đường thật: **đọc lại tệp SKiDL đã sinh** bằng `ast` (`sch/doc_skidl.py`). Tệp đó là một
hiện vật — mã sinh nó, người có thể sửa nó, và SCH14 nói thẳng mô hình có thể *"sinh net
không có trong CKM"*. Đọc nó rồi so với cây là kiểm đúng thứ cần kiểm.

Không `exec` tệp, và lý do thứ hai mới là lý do thật: chạy một tệp Python mà mô hình có thể
đã sửa là **thực thi mã không kiểm soát**. `ast.parse` đọc cấu trúc mà không gọi gì.

Đổi lại, bộ đọc chỉ hiểu đúng tập con `soan.py` sinh ra — nên gặp gì không hiểu thì **nói
ra** (`khong_hieu`), kể cả câu lệnh ở cấp ngoài cùng. Một dòng bị bỏ qua im lặng là một net
biến mất khỏi phép kiểm; một `import os` chèn vào mà không ai nhắc thì người đọc báo cáo
tưởng tệp vẫn đúng như lúc sinh.

### Bốn quyết định khác, mỗi cái một lý do

**Nạp trễ theo §2.2.** Chỉ `sch.compose` hiện; `sch.netlist`/`sch.symbols` qua `tool.search`.
Đo được: lược đồ tool cờ tắt 17 071 token, cờ bật 17 619 — chênh **548** thay vì ~1 200 nếu
hiện hết.

**Ký hiệu sinh từ Fact ghi rõ nguồn.** §5 gọi đó là "N1 áp vào ký hiệu": `Description` của
symbol mang câu *"Sinh từ DS-328P trang 13 — EIDE"*. Kiểu chân suy từ hướng Port, và chân
chưa rõ thì `passive` — đoán `input` sẽ làm ERC của KiCad báo lỗi **sai** ở máy người khác.

**Thư viện chính thức lệch Fact thì không dùng im lặng** (§5). So theo SỐ chân, không theo
tên: tên chân khác nhau giữa các phiên bản thư viện là chuyện thường (`VCC` vs `VDD`), còn
số chân khác nhau nghĩa là **hai con chip khác nhau**.

**Không ghi `tstamp` bịa vào `.net`.** KiCad dùng nó để khớp linh kiện khi cập nhật PCB; một
giá trị bịa làm lần cập nhật sau gán sai chân. Thiếu thì để KiCad tự sinh.

### SCH-09: cấm bằng lời là cấm không đo được

*"Không đề nghị cài KiCad ở BẤT KỲ thông điệp nào"* là ràng buộc về **thứ không được xuất
hiện**, và loại đó không tự giữ được: mô hình rất dễ "giúp" bằng câu *"anh cài KiCad rồi mở
tệp này"* — đúng lúc nó tưởng đang hữu ích nhất. Một dòng trong hiến pháp sẽ trôi đi sau vài
lần nén, và không ai biết nó đã trôi.

Nên luật nằm ở hook `Stop`, đọc `ctx.loi_da_noi` (mọi câu tác tử nói ra đều đi qua đó). Nó
chặn và **chỉ đường đúng**: `sch.export` để mở ở máy khác. Có ca đo cho cả chiều ngược —
nói *về* định dạng KiCad mà không đề nghị cài thì KHÔNG bị chặn, vì chặn quá tay thì tác tử
không nói được về thứ nó đang làm.

### Ba lỗi do việc đo phơi ra

**1. `requires` che mất câu R3 giàu thông tin hơn.** `check_preconditions` chạy trước thân
công cụ và trả *"thiếu 1 ckm"*; thân công cụ dựng được câu liệt kê đúng thứ đang thiếu, gọi
gì để có, và nhắc rằng sơ đồ khối vẫn dùng được (mức R3, §6). Bỏ `requires` ở `sch.compose`:
hai chỗ kiểm cùng một điều kiện thì chỗ có nhiều ngữ cảnh hơn phải là chỗ nói.

**2. `sch.compose` tin vào giá trị đã GHI NHỚ.** Nó đọc `vi_pham_cay()` — kết quả của lần
chiếu trước. Nếu đồ thị bị đổi bằng đường khác kể từ lúc đó thì nó đang nói về một cái cây
không còn tồn tại. Nay nó **tính lại**: một phép chặn đứng trước bước tốn kém nhất phải được
tính, không được nhớ.

**3. Ca đo SCH14 ĐẬU vì nó không làm gì.** Bộ E2E chèn net bịa bằng mốc chuỗi
`"khoi_board_MOD_MCU(n_3V3)"`; khối có thêm một Port nên lời gọi thành hai tham số, mốc
không khớp, **tệp không bị sửa**, và ca đo báo đạt trong khi nó chẳng kiểm gì. Nay chèn theo
CẤU TRÚC (sau `def mach():`) và ném nếu không tìm thấy chỗ chèn. *Một ca đo đậu vì không làm
gì là ca đo tệ nhất* — nó chiếm chỗ của một phép kiểm thật.

### Số đo

`661 ca đơn vị` (+39) · `tools/thu_sch.py` **21/21** qua giao diện thật · `77 công cụ` khi
cờ bật, **74 khi cờ tắt** (y nguyên).

**Bằng chứng SCH-19 — hồi quy HAI CHẾ ĐỘ, `so_ket_qua.py --hai-che-do`:** G5 **35/35 giống
hệt** · CKM **35/35 giống hệt** · HIER **38/38 giống hệt**. Cờ tắt và cờ bật cho cùng kết
quả từng ca.

Mười một bộ E2E chạy lại với cờ tắt (như người dùng thật) đều giữ nguyên: G3 31 · G4 23 ·
G5 35 · ING-A 29 · ING-B 25 · MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35 · HIER 38.

---

### [DEV-271] 26/09/2026 · SCH-B — bố cục xác định, `.kicad_sch`, và SVG tự vẽ

Ba bước còn lại của phần chính: `sch.place` → `sch.write` → `sch.render`. Sáu công cụ `sch.*`
sau cờ, trong đó **hai** hiện mặc định (`sch.compose`, `sch.render`) đúng như §2.2 đòi.

Quyết định phụ thuộc (anh chốt 26/09): thêm **`kiutils`** cho `.kicad_sch`, **tự viết** bộ vẽ
SVG. `kiutils` là thư viện Python thuần, không phải KiCad — quyết định 25/09 cấm cài KiCad,
không cấm đọc định dạng của nó. Lý do chọn nó cho đúng một việc: round-trip `.kicad_sch` là
chỗ dễ sai **lặng lẽ** nhất, vì một trường bị bỏ khi ghi lại thì KiCad vẫn mở được tệp — nó
chỉ mất thông tin, và người dùng phát hiện ba tuần sau khi bố cục họ sửa biến mất.

### Ba chỗ tôi chọn khó hơn để phép kiểm còn ý nghĩa

**1. Ghi bản ĐÃ CHUẨN HOÁ để round-trip đòi khớp từng ký tự.** `kiutils` chuẩn hoá cách viết
số (`40.0` → `40`), nên bản đầu và bản đọc-lại khác nhau vài ký tự dù **không mất gì**. Hai
cách xử: nới phép kiểm thành "đọc lại được là đủ", hay ghi thẳng điểm bất động. Nới là rẻ
hơn, nhưng nó bỏ đúng thứ phép kiểm sinh ra để bắt — một trường bị mất khi ghi lại vẫn "đọc
lại được". Chọn cách hai: cho kiutils đọc-ghi một lượt rồi lưu kết quả đó.

**2. uuid sinh từ `sha256(ref)`, không phải `uuid4()`** (SCH-20). KiCad dùng uuid để khớp ký
hiệu giữa hai lần mở tệp; uuid ngẫu nhiên nghĩa là lần sinh lại tạo ký hiệu "mới" và KiCad
ném đi mọi thứ người dùng đã sửa. Đây là chỗ mà **tính ngẫu nhiên không phải tính năng mà là
mất dữ liệu**.

**3. Cỡ chữ do lớp BỐ CỤC sở hữu, bộ vẽ đọc lại.** Đo lần đầu: hộp bao chữ cao 1,27 mm trong
khi chữ vẽ ra cao 2,8 mm — phép kiểm "chữ không đè" nói về một hình **khác** hình người thấy,
nên nó luôn đạt. Nay một hằng số (`CAO_CHU_MM`), bố cục dùng nó để giãn nhãn, bộ vẽ đổi sang
px. Hai bên tự đoán riêng là cách một phép kiểm trở thành trang trí.

### Hai giới hạn nói thẳng, không giấu

**Không đi dây giữa các khối.** §4 đề nghị A* trên lưới có phạt gấp; bản này chỉ nối dây khi
hai chân **thẳng hàng trong cùng vùng**, còn lại dùng nhãn net. Lý do: một mạch có dây vẽ sai
tệ hơn một mạch dùng nhãn — nhãn thì người đọc vẫn truy được net, dây sai thì họ tin mắt
mình. Hệ quả đo được: tỉ lệ nhãn cao, và tiêu chí *≤ 70 % net dùng nhãn* của §4 sẽ **cảnh
báo**. Đó là một cảnh báo ĐÚNG, không phải con số cần lách. Đi dây thật là việc của SCH-C.

**Kích thước ký hiệu ước theo số chân**, chưa đọc hình vẽ thật từ `.kicad_sym`. Ước **rộng
tay**: một ký hiệu bị coi nhỏ hơn thực tế sẽ chồng lên cái bên cạnh, và phép kiểm "0 chồng
nhau" sẽ nói đạt trong khi hình vẽ thì không.

### Hai lỗi do việc đo phơi ra

**1. Bố cục xếp mọi lá thành MỘT cột.** Ca đo nhồi 40 điện trở vào một khối: vùng cao hơn cả
khổ A3. Nới vùng 20 % năm lần chỉ làm nó tràn xa hơn — một vùng cao hơn trang không phải "bố
cục chật" mà là bố cục **không dùng được**. Nay cuộn sang cột mới khi hết chiều cao trang.

**2. Tên hàm trùng tên module.** `from eide.sch import bo_cuc` lấy được **hàm** `bo_cuc` chứ
không phải module — và lỗi đó im lặng cho tới khi ai đó gọi `bo_cuc.O(...)`. Đổi hàm thành
`tinh_bo_cuc`.

### Số đo

`679 ca đơn vị` (+18) · `tools/thu_sch.py` **35/35** (từ 21) qua giao diện thật ·
`80 công cụ` khi cờ bật, **74 khi cờ tắt** (y nguyên) · lược đồ tool chênh **988 token**
(vẫn dưới ~1,2 k của §2.2 nhờ nạp trễ).

**Bằng chứng SCH-19 — hồi quy hai chế độ:** HIER **38/38 giống hệt** · CKM **35/35 giống
hệt** · G5 **35/35 giống hệt**. G5 có một lần báo khác biệt rồi chạy lại khớp — ca hội thoại,
mô hình không xác định; ghi lại đúng như thế chứ không gọi là "đã giống hệt ngay từ đầu".

Mười một bộ E2E cũ chạy với cờ tắt đều giữ nguyên: G3 31 · G4 23 · G5 35 · ING-A 29 ·
ING-B 25 · MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35 · HIER 38.

---

### [DEV-272] 26/09/2026 · HIER-C — thư viện khối `block@semver`

§1 lỗ hổng 6 của HIER-45: *"Mỗi dự án vẽ lại LDO, pull-up, reset…"*. Bốn công cụ mới —
`khoi.list` · `khoi.place` · `khoi.extract` · `khoi.upgrade` — cộng ba tầng lưu (dự án →
người dùng → M4).

Việc đóng gói không khó. Hai chỗ **dễ nói dối** mới là nội dung của bước này.

### 1. Số dẫn xuất: con số tính ra trông luôn có vẻ đúng

§5 nói *"đặt vào cây là `instantiate(block, params)` → sinh lá cụ thể (R theo Vout…), mọi số
từ công thức có nguồn — không bịa"*. Một khối LDO đặt với `Vout=3,3 V` sinh hai điện trở chia
áp tính được: `R2 = R1 / (Vout/Vref − 1) = 609,76 Ω`.

Con số đó **có đơn vị, có mấy chữ số thập phân, và không ai hỏi nó ở đâu ra**. Đó là chỗ N1
dễ lách nhất trong cả sản phẩm — dễ hơn cả một hằng số trong mã, vì hằng số thì
`constant-guard` soi, còn một giá trị BOM thì không ai soi.

Nên luật là: **thiếu nguồn cho một tham số thì không sinh lá nào.** Không phải "sinh lá kèm
cảnh báo" — một điện trở tính từ con số không ai biết ở đâu ra là một điện trở **sẽ được hàn
lên bo thật**. Và mọi giá trị dẫn xuất mang theo `GiaTriDanXuat`: công thức, tham số vào, và
nguồn của **từng** tham số. Không có dạng `float` trần nào ra khỏi module này.

**Công thức là danh sách ĐÓNG, không `eval`.** Manifest đến từ một tệp trên đĩa, và §5 nói
khối được chia sẻ giữa các dự án — `eval` trên nội dung tệp là thực thi mã của người lạ. Danh
sách đóng thì công thức lạ bị từ chối **kèm tên các công thức có sẵn**, tức là thông tin cho
người viết khối. Có một ca đo đọc chính mã nguồn để chắc không có `eval`/`exec`.

### 2. Khép kín: hở im lặng thì chỉ sai khi hàn

§5 cuối đòi kiểm tính khép kín trước khi trích khối. Một khối có net chạm ra ngoài mà không
qua Port thì đem sang dự án khác **vẫn đặt được, vẫn vẽ được, và chỉ sai khi hàn**. Nên
`kiem_khep_kin` là cửa duy nhất của `khoi.extract`, và nó nêu đúng chỗ hở kèm cách sửa
(`ckm.port_set`).

### Ba quyết định khác

**Thứ tự ba tầng: dự án thắng người dùng.** Khối trong dự án là khối người dùng đã sửa cho
mạch **này**. Ngược lại thì một lần sửa cục bộ sẽ bị một bản thư viện mới lặng lẽ ghi đè.

**Không có phiên bản thì lấy bản mới nhất và NÓI RA đã chọn bản nào** — im lặng chọn hộ một
phiên bản là chỗ dễ sai nhất của mọi hệ quản gói. Semver so bằng số: `1.10.0 > 1.2.0`.

**Tầng thứ ba (M4) chưa có, và câu trả lời phải nói ra điều đó.** Nó đòi một kênh phát hành
và một chuỗi hash, cả hai chưa tồn tại. `tra_khoi` nói *"chưa có ở hai tầng tra được"* thay vì
"không tồn tại" — một tầng rỗng không được im lặng thành một kết luận.

**`khoi.place`/`khoi.upgrade` đi qua cổng G-DESIGN** (§5). Đặt một khối mang theo linh kiện,
giá trị và cả một cụm Fact vào mạch của người dùng; một công cụ đặt được mà không hỏi sẽ dựng
xong nửa mạch trước khi ai kịp đọc.

**`khoi.upgrade` nói rõ Port có đổi không**, vì §6 dòng cuối làm điều đó quyết định STALE lan
tới đâu: Port đổi thì lan ra cha và anh em nối vào; chỉ đổi bên trong thì không lan.

### Hai lỗi thật do việc đo phơi ra

**1. Fact của lá KHÔNG đi theo khối — và đây là lần thứ ba lẫn ref với tên chip.** `_fact_cua_la`
tra `pin:U3.`, nhưng `fact.extract` ghi Fact chân dưới **tên chip** (`pin:AMS1117.1` — Fact của
một *loại* chip). Khối đóng gói xong có **0 Fact** mà vẫn báo thành công. Cùng chỗ lẫn này đã
gây DEV-267 (#5, hộ chiếu tra sai khoá) và DEV-269 (#1). Nay dùng lại `erc.chu_the_la` — một
nguồn sự thật cho "những chủ thể Fact có thể nói về một lá".

**2. Đặt cùng một khối lần thứ hai làm `UNIQUE(path)` của kho NỔ.** Hai con LDO trên một bo là
chuyện thường, và ref trong gói (`U7`, `R6`…) đã có người dùng. Công cụ chết bằng `E5999` thay
vì làm việc. Nay cấp ref còn trống, **giữ tiền tố chữ** (`R6` → `R10`, không phải `R6_2`, vì
tiền tố là thứ KiCad dùng để tự đánh số và người đọc BOM dùng để biết linh kiện loại gì), và
nói ra ánh xạ `U7→U10` trong kết quả, trên tab, và trong hiện vật.

### Một ghi chú về cách đo

31 ca đơn vị đầu **xanh ngay lần chạy đầu**. Đọc lại thì thấy chưa ca nào đi qua thân
`khoi.extract` với một khối khép kín thật — chỉ có ca *từ chối* khối không kín. **Một bộ đo
toàn màu xanh mà chưa chạm đường thành công là một bộ đo chưa nói gì về đường đó.** Ca thêm vào
(`test_khoi_extract_di_HET_duong_va_dat_lai_duoc_o_du_an_khac`) tìm ra ngay cả hai lỗi ở trên.

### Số đo

`712 ca đơn vị` (+33) · `tools/thu_hier.py` **46/46** (từ 38) qua giao diện thật ·
`78 công cụ` khi cờ sơ đồ tắt, 84 khi bật.

Hồi quy: mười hai bộ E2E đều giữ nguyên — G3 31 · G4 23 · G5 35 · ING-A 29 · ING-B 25 ·
MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35 · HIER 46 · SCH 35.

---

### [DEV-273] 26/09/2026 · HIER-D + SCH-C — sheet phân cấp, và vòng đi–về với KiCad

**Tài liệu:** EIDE-HIER-45 §7 (cây → sheet phân cấp 1-1, `depth > 4` tự chuyển),
EIDE-SCH-44 §3 bước 5 và bước 7, §7 (ba loại thay đổi khi nạp lại). Ca HIER11–13, SCH10–13, SCH16.

Đến bước này EIDE mới **trả sơ đồ lại được cho người dùng rồi nhận lại**: ghi mỗi khối một
`.kicad_sch`, xuất một gói mở được ở máy có KiCad, và khi người dùng sửa xong thì đọc lại và
phân loại họ đã sửa cái gì. Ba tệp mới: `src/eide/sch/phan_cap.py` (ghi/đọc sheet, `so_cay`),
`src/eide/sch/nap_lai.py` (phân loại ba loại), và hai công cụ `sch.export` / `sch.import`.

**Sheet phân cấp giữ được CÂY trong tệp.** Port của khối thành *hierarchical label* trong sheet
của nó và thành *sheet pin* trên hộp sheet ở cha — tức hợp đồng ở biên khối vẫn là hợp đồng sau
khi tệp rời khỏi EIDE. `viet_phan_cap` ghi từ sâu ra ngoài, rồi **đọc lại chính gói vừa ghi** và
so bằng `so_cay`: khối chỉ có ở tệp, khối chỉ có ở kho, Port lệch. Ghi mà không đọc lại thì
"đã ghi phân cấp" chỉ là một lời khai.

**Nạp lại thì ba loại thay đổi làm ba việc khác nhau,** và gộp chúng là làm mất đúng thứ quan
trọng nhất: *bố cục* (người kéo ký hiệu) không làm gì lỗi thời — đánh STALE ở đây thì mỗi lần
họ sắp lại trang là một lần cả chuỗi hạ nguồn sáng đèn, và họ học được rằng băng cảnh báo vô
nghĩa; *giá trị* là một quyết định kỹ thuật của họ, vào BOM và thành Fact tầng NGƯỜI, ERC chạy
lại; *cấu trúc* thì **hỏi** — hai lựa chọn viết bằng hậu quả, kèm câu "EIDE không chọn hộ".
`sch.import` **không ghi gì vào bản đồ** khi có thay đổi cấu trúc; ca E2E đo đúng điều đó bằng
cách so bản đồ trước và sau.

### Bốn lỗi thật, và cả bốn cùng một họ: **hai chỗ tự tính riêng cùng một thứ**

**1. `Sheetname` mang tên hiển thị thì đọc lại KHÔNG dựng lại được cây.** Bên ghi đặt
`Sheetname = "Vi điều khiển"`, bên đọc lại dùng nó làm đoạn path — nên đường dẫn dựng lại là
`/board/Vi điều khiển`, `so_cay` báo lệch toàn bộ. Nay `Sheetname` mang **mã khối**, tên hiển
thị đi trong `EIDE_ten`.

**2. `sch.render` chỉ vẽ sheet gốc — và sheet gốc phân cấp KHÔNG có ký hiệu nào.** Kết quả là
một SVG rỗng được báo là render thành công. Nay `render` vẽ **mọi** sheet, và `ve_svg` vẽ cả
hộp sheet con kèm sheet pin; câu "ảnh rỗng" chỉ phát khi sheet không có *cả* ký hiệu *lẫn* hộp
sheet. Đây lại là N6 áp vào chính cái thước: không đo được thì không được in ra là đạt.

**3. `sch.write` mặc định cứng `hierarchical` — sai với mạch một tầng, và sai với chính bộ đo.**
Nay mặc định là `auto`: **hình tệp đi theo hình thiết kế** — có khối thì phân cấp, một tầng thì
một trang. Ghi `flat` cho một mạch *có* khối vẫn được, nhưng kết quả nói thẳng "cây khối KHÔNG
còn trong tệp".

**4. Một lần nạp lại báo "đổi giá trị" mà không ai đổi gì.** Bên ghi điền trường `Value` bằng
**tên chip** khi lá chưa có `gia_tri` (KiCad cần trường đó có nội dung), còn bên so lấy giá trị
*thô* trong kho — rỗng. Mọi lần `sch.import` đều thấy một thay đổi tưởng tượng. Nay một hàm
`phan_cap.gia_tri_mong_doi()` cho cả hai bên dùng, và `gia_tri_kho` thành **tham số bắt buộc**
của `phan_loai`: một mặc định âm thầm so với cơ sở khác thì tệ hơn là không có mặc định.

### Bài học lặp lại lần thứ năm

Cả bốn lỗi trên đều là **hai chỗ tự tính riêng cùng một quy ước** (tên đoạn path, danh sách
tệp cần vẽ, kiểu ghi mặc định, giá trị mong đợi). Sửa tại chỗ là sửa lại lần nữa ở chỗ khác —
đã thấy ở sổ cái (DEV-266) và ở ref-vs-tên-chip (DEV-267, 269, 272). Cách sửa đúng vẫn là:
**một hàm, hai bên gọi.**

### Số đo

`730 ca đơn vị` (+18) · `tools/thu_sch.py` **48/48** (từ 35) qua giao diện thật, thêm hai mục
F (sheet phân cấp) và G (xuất gói, nạp lại) · `86 công cụ` khi cờ sơ đồ bật, 78 khi tắt.

Hồi quy: mười ba bộ E2E đều giữ nguyên hoặc tăng — G3 31 · G4 23 · G5 35 · ING-A 29 · ING-B 25
· MEM-A 21 · MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35 · HIER 46 · SCH 48.

Bằng chứng SCH-19 (`so_ket_qua.py --hai-che-do tools/thu_cuoi.py`): **36/36 giống hệt** giữa
cờ tắt và cờ bật — so bằng mã, vì thứ nguy hiểm là một ô lặng lẽ đổi từ đạt sang không đạt.

---

### [DEV-274] 26/09/2026 · SCH-D — bố cục từng trang, ký hiệu người xác nhận, và tab Thiết kế thấy được sơ đồ

**Tài liệu:** EIDE-SCH-44 §2.1(4) (bảng `sch_sheets`), §4 (tiêu chí bố cục), §5 (ký hiệu từ
thư viện và từ Fact), §6 (render ba mức), §9 (khối giao diện A5.8), yêu cầu SCH-14, SCH-15,
SCH-16, ca SCH07. Bước cuối của lộ trình SCH.

Bốn việc, và việc thứ tư là việc mà **ba bước SCH trước bỏ trống mà không ai nói ra**: tab
Thiết kế chưa có một khối sơ đồ nào. Cả đường ống sinh được `.kicad_sch`, kiểm được, render
được SVG — nhưng người dùng không có chỗ nào để *xem* nó. §9 liệt kê mười widget của khối
A5.8; trước hôm nay có **không** widget nào.

### 1. Tiêu chí bố cục đo trên TỪNG trang (SCH07)

`tinh_bo_cuc_theo_sheet()` tính một bố cục cho mỗi khối: lá của riêng khối đó (cuộn cột theo
chiều cao trang), hộp sheet cho khối con, nhãn phân cấp cho Port. "Mỗi sheet đạt tiêu chí" là
một đòi hỏi **khác** "cả mạch đạt tiêu chí": một mạch 120 linh kiện chia 4 khối có thể đạt
trên tổng thể mà vẫn có một trang tràn, và một phép đo trên tổng thể rồi kết luận cho từng
trang là phép đo nói nhiều hơn nó biết.

`sch.place` cũng nói ra **khi nào nên chia sheet**, bằng ba lý do đều là số: trang phẳng không
đạt tiêu chí · hơn 50 ký hiệu trên một trang · hơn 70 % net phải dùng nhãn. Và khi cây chỉ có
một khối thì nó nói ngược lại: chia sheet lấy khối làm đơn vị, nên **chia khối trước đã**.

### 2. Sổ đăng ký sheet và bản ưng ý gói được sơ đồ (§2.1(4), SCH-16)

Lược đồ v4: `sch_sheets(id, version, path, tep, lib_versions, layout_hash, explain)`, có
`down()`. Mỗi lần `sch.write` ghi một sheet là một dòng, kèm băm bố cục và phiên bản thư viện
ký hiệu. Bản ưng ý gói **cả nội dung** từng tệp vào blob, không chỉ tên: một bản ưng ý nhớ tên
tệp thì việc quay về được phụ thuộc vào tệp còn nguyên — tức phụ thuộc vào đúng thứ mà người ta
ghi bản ưng ý để **không** phải phụ thuộc vào. Khôi phục đưa tệp về kể cả khi dự án không có git.

### 3. Ký hiệu sinh từ Fact phải có người xác nhận (SCH-14, SCH-15, §9)

Kiểu chân của ký hiệu sinh ra là một phép **suy**: hướng Port → `power_in`/`input`/`passive`,
mà hướng Port lại suy từ tên chân. ERC của KiCad dựa vào kiểu chân, nên một kiểu chân sai làm
người dùng mở tệp ra, thấy ERC báo lỗi nguồn, và tin rằng **mạch** của họ sai. Nay mỗi ký hiệu
sinh từ Fact (hoặc khớp thư viện < 100 %) ở trạng thái "chờ anh xem", `sch.symbols` và
`sch.write` đều nói ra còn bao nhiêu cái chờ, và `sch.symbol_confirm` **đòi lời của chính người
dùng** — trích lời rỗng thì từ chối với `E8009` kèm câu "đừng tự xác nhận hộ". Kiểu chân họ sửa
thành Fact tầng NGƯỜI có trích lời, và nó sống sót qua mọi lần sinh lại ký hiệu.

### 4. Khối A5.8 trên tab Thiết kế (SCH-06, SCH-07, §9)

Bốn khối: **ảnh sơ đồ bấm được** (loại khối `svg` mới, `WKWebView` vẽ đúng tệp SVG mà lõi đã
ghi — không có nhánh vẽ thứ hai để lệch; bấm ký hiệu → hỏi Fact/nguồn, bấm nhãn net → tô sáng
+ ERC, và **câu hỏi do lõi soạn** nên nội dung nó không rải trong mã Swift) · **băng chất lượng
bố cục** một dòng mỗi trang · **bảng ký hiệu sửa được** (`loai_sua: "symbol"`) · **mức render
đang dùng**, nói rõ máy này không cài KiCad.

Khối A5.8 chỉ hiện khi CÓ hiện vật sơ đồ. Cờ bật mà chưa ai sinh sơ đồ thì tab Thiết kế không
đổi một khối nào — nên ở đây không có cả ô trống trung thực, vì một ô trống cũng là một khối mới.

### Bốn lỗi thật, và một phép đo tự lừa mình

**1. Tỉ lệ nhãn chặn MỌI sheet.** Bố cục theo sheet ban đầu bỏ hẳn bước "net nào thành dây, net
nào thành nhãn", nên mọi sheet có tỉ lệ nhãn 100 % và không sheet nào đạt tiêu chí. Hai sửa:
bước đó thành **một hàm, hai chỗ gọi** (trang phẳng và sheet); và trên một sheet, tỉ lệ nhãn là
**cảnh báo** chứ không phải vi phạm — §4 viết hậu quả của ngưỡng đó là *"cảnh báo 'mạch khó
đọc', đề nghị style=hierarchical"*, mà trên một sheet đã phân cấp thì lời đề nghị ấy đã được
nhận, và net rời khỏi khối dùng nhãn phân cấp là **đúng thiết kế**.

**2. `KIEU_CHAN` trùng tên đè lên bảng suy hướng-Port → kiểu-chân.** Hằng mới (danh sách kiểu
người chọn được) trùng tên với bảng cũ (phép suy của máy), nên `_chan_tu_port` gọi `.get()` trên
một tuple — mọi ký hiệu sinh ra đều nổ. Đổi tên thành `KIEU_CHAN_CHON_DUOC`: hai thứ khác nhau
thì không được mang một tên.

**3. Một tệp sheet có HAI dòng trong sổ đăng ký.** Khoá theo `path` khối, nên ghi `flat` rồi ghi
`hierarchical` để lại hai dòng cùng trỏ `sch/mach.kicad_sch` (path `""` và `/board`) — và bản
ưng ý gói tệp đó hai lần trong khi khai rằng nó có 8 sheet. Nay khoá theo **tệp**: một tệp là
một thứ mà bản ưng ý gói và khôi phục.

**4. `sch_dat_sheet` có mặc định rỗng, ghi lần hai xoá dữ liệu lần đầu.** Cùng cái bẫy của
DEV-273 mục 4, cách nhau vài giờ: bốn trường mô tả **lần ghi vừa xảy ra**, nên mặc định rỗng thì
xoá thông tin lần trước, còn "giữ giá trị cũ" thì để lại một `layout_hash` nói về một bố cục
không còn tồn tại. Cả hai tệ hơn việc buộc bên gọi nói ra.

**5. Và một ca đo xanh vì bộ đo tự hỏi chính nó.** Ca "giao diện vẽ được mọi khối" so loại khối
với **một danh sách viết trong Python** — tức nó kiểm rằng *bộ đo* biết loại khối đó, không kiểm
rằng *giao diện* vẽ được. Nay nhánh `default` của bộ vẽ Swift tự ghi tên loại khối nó không vẽ
được, và bộ đo hỏi đúng chỗ đó. Kiểm lại bằng cách **cố tình** gửi một khối loại lạ: ca đo đỏ
đúng chỗ (`A5.ZZ:loai_khong_ton_tai`), rồi gỡ khối giả đi. Một ô xanh chưa nói gì nếu nó chưa
bao giờ đỏ được.

Kèm theo: `ui.sync` giờ gọi được từ kênh kiểm thử (`{"ui": "sync"}`, 0 token). Chuyển tab **không**
vẽ lại — đó là thiết kế (`attend` là sự chú ý, không phải yêu cầu) — nên không có lệnh này thì mọi
phép đo về một khối mới phải tiêu một lượt mô hình để thấy nó.

### Số đo

`755 ca đơn vị` (+25) · `tools/thu_sch.py` **63/63** (từ 48) qua giao diện thật, thêm ba mục:
bố cục từng sheet + bản ưng ý · ký hiệu chờ xác nhận · khối A5.8 · `87 công cụ` khi cờ bật
(+1: `sch.symbol_confirm`), `78` khi tắt.

Hồi quy: mười ba bộ E2E đều giữ nguyên — G3 31 · G4 23 · G5 35 · ING-A 29 · ING-B 25 · MEM-A 21
· MEM-B 20 · MEM-C 26 · CUỐI 36 · CKM 35 · HIER 46 · GIAO DIỆN 24 · SCH 63.

Bằng chứng SCH-19, **hai bộ**: `--hai-che-do tools/thu_cuoi.py` 36/36 giống hệt và
`--hai-che-do tools/thu_giao_dien.py` 24/24 giống hệt — bộ thứ hai quan trọng vì SCH-D thêm khối
vào tab Thiết kế, tức chạm đúng thứ mà bộ đo giao diện đang đo.

---

### [DEV-275] 27/09/2026 · Làm một dự án THẬT từ đầu tới cuối, và bảy lỗ hổng nó phơi ra

**Bối cảnh.** Chủ sản phẩm đưa một tài liệu bàn giao phần cứng có thật — *MOBILUCK Robot hai
bánh tự cân bằng v1.1*, 43 trang, 93 bảng, viết bằng tiếng Việt — và yêu cầu làm trọn vẹn
một dự án: tạo dự án → nạp tài liệu → trích xuất thiết kế → ghim chip → bản đồ mạch → sơ đồ
nguyên lý → firmware → biên dịch → mô phỏng, có ảnh chụp làm sở cứ.

Việc này khác mọi bộ kiểm đã có ở một điểm: **không ai dựng sẵn dữ liệu cho nó.** Mọi bộ
`tools/thu_*.py` đều tự dựng mạch mẫu bằng vài lời gọi công cụ rồi đo phần sau. Ở đây, đầu
vào là một tệp `.docx` của người khác, và mỗi lần EIDE không đọc nổi một thứ gì trong đó thì
đường ống dừng tại chỗ. Bảy lỗ hổng dưới đây đều lộ ra theo cách đó, và **không lỗ nào bị bộ
kiểm nào bắt được trước đó** — vì bộ kiểm nào cũng bắt đầu sau chỗ chúng nằm.

Hạ tầng đo: `tools/phien_robot.py` (đóng vai người dùng gõ từng câu vào app thật, duyệt thẻ
cổng, chụp **đúng cửa sổ EIDE**) + `tools/kich_ban_robot.py` (kịch bản và phép đối chiếu) +
`tools/doi_chieu_robot.py` (so netlist sinh ra với bảng 12/30/33 của tài liệu).

### Bảy lỗ hổng

**1. Bảng bản đồ chân không được nhận là bảng.** Từ điển tên cột chỉ biết datasheet điện
(*parameter/min/typ/max/unit*), nên bảng `Chân | Hướng | Net · khối | Chức năng` bị đọc như
một dòng chữ. Tác tử trích được 7 Fact — không Fact nào là chân — trong khi bảng có 23 chân
nằm ngay đó. Thêm `la_bang_chan()` và trường `loai_bang` trên `Trang`.

**2. Không có công cụ nào trích bản đồ chân.** `fact.extract` đọc **số kèm đơn vị**; bản đồ
chân là **quan hệ** (`D4 → net DIR1, hướng ra`). Ép chân vào khuôn của số thì mất đúng phần
mang thông tin. Thêm `fact.extract_pinout` sinh Fact `pin:<chip>.<chân>` với `ten`/`net`/
`huong`/`af`, mỗi Fact trỏ tới đúng dòng bảng.

**3. Mở lại dự án là mất tài liệu.** `doc.load` giữ tài liệu đã phân tích trong bộ nhớ tiến
trình; đóng app rồi mở lại thì hiện vật `doc` vẫn nằm trong kho và tab Tài liệu vẫn hiện nó,
nhưng mọi công cụ đọc tài liệu trả `E2001 "chưa được nạp"` — tác tử im lặng bỏ dở việc.
`_lay_tai_lieu()` đọc lại từ tệp và **so hash**: tệp đổi thì báo `E2005` chứ không dùng nội
dung mới dưới tên cũ.

**4. Không có đường nào ĐỌC một mục của tài liệu.** Tác tử nạp xong 43 trang, trích được bản
đồ chân, rồi khi được yêu cầu viết firmware nó **dừng lại và hỏi người dùng chép giúp** bảng
quy đổi throttle và các hằng hiệu chuẩn. Nó làm đúng luật N1, nhưng lý do phải hỏi là EIDE
chỉ có hai đường vào tài liệu (trích số, trích chân) — mọi câu văn và mọi bảng khác nằm ngoài
tầm với. Thêm `doc.read` (theo từ khoá, theo mục, theo khoảng), trả nguyên văn kèm trích dẫn.

**5. Chốt hằng số N1 chặn việc viết mã, và ba đường nó gợi ý đều không vừa.** Ghi `main.c`
đầy giá trị thanh ghi thì bị `deny` vì những con số đó chưa là Fact. `fact.query` không có gì
để tìm; `fact.assert_human` sẽ gán cho người dùng một câu họ chưa nói; `ask_user` là bắt họ
chép tay thứ đang nằm sẵn trong tài liệu. Thêm `fact.from_doc`: **mô hình chọn đoạn và đặt
tên, MÃ kiểm giá trị có mặt nguyên văn trong đoạn được trích dẫn**. Sai giá trị thì `E2006`
kèm chính nội dung đoạn đó — không có cửa nào để một con số nhớ được lọt vào kho.

**6. `fact.query` cắt im lặng ở 100 dòng.** Trên dự án có 256 Fact, tác tử đọc `count: 100`
rồi kết luận về "toàn bộ Fact trong kho" — một câu trả lời thiếu 60 % dữ liệu mà không có
dấu hiệu nào cho thấy nó thiếu. Nay trả thêm `tong`, `bi_cat`, và câu "đang xem 100/256, còn
156 Fact nữa" — N6 áp vào một phép tra.

**7. Chưa có công cụ biên dịch hay mô phỏng nào (G6).** Thêm bản tối thiểu:
`build.compile` gọi chuỗi công cụ thật (arduino-cli / avr-gcc), trả lỗi kèm `tệp:dòng:cột`,
kích thước đọc từ `avr-size`, và **"đạt" chỉ khi trình biên dịch trả 0 VÀ có tệp ảnh trên
đĩa**; `sim.run` biên dịch phần logic của firmware bằng trình biên dịch máy chủ rồi chạy nó
trong mô hình vật lý, kết luận đạt/không do **chương trình mô phỏng in ra JSON**. Cả hai xếp
**R2 chứ không R3**: chúng chạy trong dự án, không cài gì, không ra mạng — xếp R3 thì mỗi
vòng sửa–dịch là một thẻ cổng, và người dùng sẽ bấm duyệt theo phản xạ.

### Ba đường im lặng — cùng một hình dạng

Cả ba đều kết thúc bằng việc EIDE đứng im trong khi người dùng đợi:

- **Hết 40 lời gọi công cụ** chỉ treo một băng cảnh báo ở góc. Nay nói trong hội thoại: đã
  gọi bao nhiêu công cụ, nhiều nhất là cái nào, những gì đã ghi vẫn còn, gõ "làm tiếp" để đi
  tiếp.
- **Lượt kết thúc mà mô hình không nói gì** (gọi mười công cụ rồi trả về câu rỗng). Nay lõi
  tự nói thay.
- **Tác tử tìm mãi mà không làm**: một lượt gọi `ledger.query` 21 lần để tìm một tệp nó sắp
  phải tự viết. Mô hình không thấy được lượt của chính nó từ bên ngoài — nó thấy từng lời gọi
  một, mỗi cái đều hợp lý. Nay lõi đếm và nhắc: *"bạn đã gọi `X` 6 lần và chưa ghi được gì —
  dừng tìm lại, chọn một trong ba"*.

### Kết quả đo được trên dự án thật

| Mốc | Kết quả | Đối chiếu với tài liệu |
|---|---|---|
| Bản đồ chân | 22 chân vào kho, mỗi chân có trích dẫn tới dòng bảng | **14/14** chân của bảng 12 khớp |
| Bản đồ mạch | 10 khối, 21 nút, 14 net | **14/14** net nối đúng chân |
| Sơ đồ nguyên lý | 11 sheet phân cấp + SVG + `.net` | **14/14** net khớp (`doi-chieu.md`) |
| Giá trị thanh ghi | 19 Fact có trích dẫn | **19/19** khớp bảng 91 |
| Firmware | `control.c` (logic thuần) + `main.c` (thanh ghi) | 0 cấu trúc bị cấm (bảng 83); MCUSR đọc trước watchdog |
| Biên dịch | `arduino-cli` → `firmware.ino.hex` | Flash 3.520 B / 30.720 B · SRAM 81 B / 2.048 B |

`783 ca đơn vị` (+21 so với DEV-274) · `tools/thu_giao_dien.py` **27/27** · `81 công cụ` khi
cờ sơ đồ tắt (+3), `90` khi bật.

---

### [DEV-276] 27/09/2026 · Dựng bản đồ mạch bằng mã, giao diện vừa mọi khổ, và bốn phép đo tự lừa mình

Tiếp DEV-275 — cùng một dự án robot thật, chạy thêm vài vòng nữa. Lần này thứ lộ ra không
phải chỗ EIDE **thiếu** tính năng, mà chỗ nó **có mà không đúng**.

### 1. Một bước xác định bị giao cho mô hình

Chạy cùng một kịch bản hai lần: lần đầu **14/14** net đúng, lần sau **0/14**. Việc chép 14
net từ bảng bàn giao sang bản đồ mạch được giao cho mô hình qua 14 lời gọi `ckm.net_set`, và
lần thứ hai nó bỏ dở giữa chừng. Nhưng dữ liệu đã nằm sẵn trong kho: `pin:ATmega328P.D4` có
`net=DIR1`, `khoi=A4988 #1`, `huong=ra`. **Một bước xác định mà kết quả phụ thuộc vào lượt
chạy là một bước đặt sai chỗ.**

`ckm.from_pinout` dựng net + khối từ chính những Fact đó. Đo lại: **14/14 ngay lần đầu**, và
sau một lượt hoàn thiện của tác tử thì **19/19 net có đủ hai đầu**. Mô hình vẫn còn phần việc
chỉ nó làm được — đọc chương riêng của từng linh kiện, thêm Port, đặt tên khối cho gọn — và
công cụ nói thẳng phần đó còn thiếu thay vì để người đọc tưởng mạch đã xong.

### 2. Giao diện không vừa khổ màn hình

Chủ sản phẩm báo: *"màn hình thiết kế khi dữ liệu nhiều đang bị mất các control phía bên
phải"*. Đúng, và nguyên nhân là một chuỗi ba lần sửa nối nhau, mỗi lần chữa lỗi trước và tạo
lỗi sau:

| Lần | Sửa gì | Tạo ra lỗi gì |
|---|---|---|
| 1 | Bảng dài cắt bằng `maxHeight` trong `ScrollView(.horizontal)` | Cuộn ngang KHÔNG cắt dọc → bảng 256 dòng **vẽ đè** lên hai khối dưới |
| 2 | Thêm `.fixedSize(vertical:)` + cắt còn 40 dòng | `ScrollView` đòi bề rộng nội tại → **panel hội thoại bị đẩy ra ngoài mép trái** |
| 3 | Cột co theo `beRongKhaDung`, bỏ cuộn ngang | Khối ảnh SVG (`WKWebView`) vẫn đòi bề rộng riêng → **nút "Vì sao?" trôi ra ngoài** |

Chốt lại bằng ba việc cùng lúc: mỗi khối bị **khoá vào bề rộng có thật** của tab (+ clip);
`WKWebView` bị ép bằng `maxWidth: .infinity`; panel hội thoại co theo cửa sổ (trần 38 %). Và
thanh 11 tab rút gọn tên khi chật — *một tab phải cuộn mới thấy là một tab người dùng sẽ
không bấm*. Thêm ca đo ở khổ **nhỏ nhất** (1100×720), vì đó là chỗ giao diện vỡ trước.

### 3. Bốn phép đo báo xanh/đỏ vì lý do không phải sự thật

Tất cả đều là phép đo của chính bộ kiểm, và không cái nào bị phát hiện bởi một phép đo khác:

- **"control.c không phụ thuộc AVR"** so chuỗi `"avr/io.h"` trên cả tệp, nên nó trúng dòng
  **chú thích** *"không include avr/io.h"* và báo ĐỎ cho một tệp sạch. Nay bỏ chú thích rồi
  mới đọc, và đọc chỉ thị `#include` chứ không đọc lời người viết.
- **Phép đếm thanh ghi** chỉ đọc `*.c`, bỏ `*.ino` — đúng chỗ mã thanh ghi nằm khi dự án theo
  chuẩn Arduino. Nó báo 18/19 rồi 0/19 cho cùng một firmware, tuỳ tác tử đặt mã vào tệp nào.
- **`khoi_de_nhau`** (cặp khối vẽ đè) so KHUNG KHAI BÁO, nên nó vẫn rỗng trong khi nội dung
  tràn ra ngoài khung của chính nó. Kiểm lại bằng cách cố tình bỏ giới hạn dòng: vẫn rỗng.
  Giữ lại kèm ghi chú giới hạn, và thêm `cao_khoi`/`rong_khoi` — hai con số này thì đỏ đúng chỗ.
- **Vòng chờ `until ! pgrep -f phien_robot.py`** khớp chính dòng lệnh của nó, nên nó đợi
  chính nó mãi mãi trong khi phiên đã xong từ lâu.

### 4. Công cụ ghi vào kho mà bề mặt không đọc

`sim.run` chạy xong, ghi `sim_result` vào kho, báo ĐẠT — và tab Mô phỏng vẫn hiện *"Chưa có
tiêu chí và chưa chạy mô phỏng lần nào"*. Tương tự với `build:firmware` trên tab Mã nguồn.
**Một công cụ ghi vào kho mà bề mặt không đọc là một nửa tính năng.** Nay cả hai hiện kết
quả thật, kèm câu giới hạn: *"đây là kết quả trên MÔ HÌNH, KHÔNG nói mạch thật sẽ chạy"*.

Và một lỗi hợp đồng cùng họ: khối `kv` đọc `pairs = [[khoá, giá trị], …]`, lõi gửi
`items = [{k, v}, …]` — giao diện vẽ ra **một ô trắng**, không lỗi, không cảnh báo. Ca đo
"giao diện vẽ được mọi loại khối" vẫn xanh, vì *loại* khối thì biết, chỉ có *nội dung* là
mất. Nay khối `kv` rỗng tự nói ra.

### 5. Và một lỗi của chính tôi, nặng hơn tất cả những thứ trên

Ảnh chụp làm sở cứ dùng `screencapture -R` theo **vùng màn hình**. Hai lần nó lọt cửa sổ
riêng của người dùng vào ảnh — một lần có tệp `.env` kèm khoá API. Ảnh đã chụp thì không rút
lại được, nên cách chụp phải **không thể** lấy nhầm, chứ không phải cẩn thận để đừng lấy
nhầm. Nay app **tự vẽ cửa sổ của nó** ra PNG (`cacheDisplay` → `NSBitmapImageRep`); mọi ảnh
cũ đã xoá và chụp lại.

### Số đo cuối

`790 ca đơn vị` (+7) · `thu_giao_dien` **28/28** · `thu_sch` **63/63** · `thu_hier` 46/46 ·
`thu_cuoi` 36/36 · `thu_g3` 31/31 · `82 công cụ` khi cờ sơ đồ tắt, `91` khi bật.

Dự án robot (sở cứ ở `du-lieu/ket-qua/robot/`): 14/14 chân · 14/14 net khớp bảng 12 ·
19/19 net đủ hai đầu · 18/19 thanh ghi khớp bảng 91 · biên dịch thật ra `.hex`
(Flash 2.500 B / 30.720 B, SRAM 72 B / 2.048 B) · mô phỏng vòng kín **ĐẠT**
(góc lớn nhất 3,0°, góc cuối 0,155°, chạy 5 s).
