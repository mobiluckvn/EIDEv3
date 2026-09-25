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
