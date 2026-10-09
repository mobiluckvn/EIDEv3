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

---

### [DEV-277] 27/09/2026 · G6 đầy đủ — nền biên dịch–mô phỏng, và ai được quyền nói “đạt”

**Tài liệu:** MDD-40 §G bước G6 (*"build/sim tool; criteria-first; subagent firmware/sim/
verifier; skill"*), §B1 bảng công cụ Build/Sim, §B2 luật `sim.criteria … G-QUAL`, §B5
subagent/skill, §C5 mô phỏng, §E2 dòng 337–338 (bề mặt build và criteria), N6.
Ca đo gốc: TC015–028, TC052–060.

Bước trước (DEV-275) làm **G6 tối thiểu**: một `build.compile` và một `sim.run` đủ để dự án
robot đi hết vòng. Bước này làm phần còn lại, và phần còn lại hoá ra không phải "thêm công
cụ" — nó là **đổi chiều một câu hỏi**: *ai được quyền tuyên bố đạt?*

### 1. Năm công cụ còn thiếu

| Công cụ | Việc | Ca đo |
|---|---|---|
| `env.check` | Máy này có gì, thiếu gì, thiếu thì hỏng việc nào | TC018 |
| `tool.install` | Cài công cụ, R3, cổng G-TOOL | TC018 |
| `build.map` | Section + symbol lớn nhất + đề xuất khi tràn | TC021 |
| `sim.criteria` | Tiêu chí nêu TRƯỚC, có nguồn ngưỡng, có phần không mô phỏng được | TC016, TC019, TC022 |
| `test.run` | Unit test trên máy chủ, đếm ca đạt/hỏng, độ phủ | TC052 |

Hai chỗ đáng nhớ trong số đó:

**`env.check` không bao giờ tự nói "sẵn sàng biên dịch".** TC018 đòi *"không báo biên dịch
thành công giả"*, và cách chắc chắn nhất để không báo giả là không bao giờ tự tuyên bố sẵn
sàng — chỉ liệt kê cái có và cái thiếu. Kiến trúc chưa biết thì nói thẳng, **không chọn một
kiến trúc gần giống**: chọn `armv7e-m` cho một Cortex-M3 sinh ra mã mang lệnh chip không
chạy được, và lỗi đó không lộ ra cho tới khi nạp vào bo.

**Lệnh cài không do mô hình soạn.** Nó lấy từ bảng trong mã — cùng chỗ `env.check` đọc ra cho
người dùng xem trước khi duyệt. Nếu mô hình tự soạn lệnh shell thì thẻ cổng đang hỏi người
dùng duyệt một thứ chưa ai đọc, và *"duyệt cài đặt"* thành *"duyệt chạy một lệnh bất kỳ"*.

### 2. Đổi chiều: tiêu chí phán xử, không phải chương trình mô phỏng

Bản G6 tối thiểu để chương trình mô phỏng tự in `dat: true`. Nghĩa là **thứ được kiểm cũng
là thứ tuyên bố kết quả** — một dòng sửa trong `sim/plant.c` đủ để mọi phép thử "đạt". Nay:

- chương trình chỉ in **số đo** (`do: {A1: 3.0}`); EIDE so với ngưỡng trong tiêu chí;
- **thiếu số đo = chưa đủ dữ kiện**, và cả lần chạy không được gọi là đạt (log rỗng ≠ đạt);
- số đo **thừa** cũng được nói ra: nó nghĩa là một trong hai bên gõ sai mã assert;
- `sim.run` **từ chối chạy** khi chưa có tiêu chí đã xác nhận — chạy trước rồi đặt tiêu chí
  sau là cách đặt tiêu chí vừa khít với kết quả;
- chỉ `trich_loi` của người dùng mới làm tiêu chí thành "đã xác nhận";
- đổi ngưỡng khi **đã có** kết quả → cổng **G-QUAL**, `never_auto`, kèm `A1.nguong: 15.0 →
  45.0`. Một thẻ hỏi "đổi tiêu chí?" mà không nói đổi từ đâu sang đâu thì người dùng bấm
  duyệt theo phản xạ;
- người dùng tự sửa ngưỡng trên bảng thì **không phải hỏi** (cổng là để chặn tác tử), nhưng
  kết quả cũ thành **STALE ngay** — nó được đo bằng một thước đã khác;
- bỏ mất danh sách "không mô phỏng được" giữa hai lần ghi tiêu chí thì **cảnh báo**: đó đúng
  là cách chữ "đạt" bắt đầu trùm lên những thứ chưa ai đo.

### 3. Sáu subagent, và một verifier thật sự độc lập

Ba ràng buộc, cả ba đều dễ bỏ theo hướng có vẻ tiện hơn:

- **Ngữ cảnh sạch** không phải để tiết kiệm token, mà để tác tử con không đọc được đoạn hội
  thoại trong đó người dùng đã nói *"chắc là đạt rồi"*.
- **Verifier chỉ có công cụ đọc.** Ghi được thì nó sửa được cho đạt đúng thứ nó đang đi
  kiểm, và một lớp kiểm tra độc lập biến thành một lớp đóng dấu. Có ca đo chứng minh nó
  không ghi nổi một tệp.
- **Verifier không thấy đề bài**, chỉ thấy báo cáo và bằng chứng (Hình B2: *"verifier chưa
  thấy việc"*). Cho nó đọc đề bài là mời nó suy ra kết luận mong đợi rồi đi tìm cách biện minh.

Hook **SubagentStop** kiểm lược đồ báo cáo (sáu trường; *"đạt" mà không bằng chứng nào* là
không hợp lệ) rồi **tự động** gọi verifier khi firmware/sim tuyên đạt. Tự động chứ không để
mô hình quyết: nếu tuỳ chọn thì nó sẽ gọi đúng những lúc không cần — lúc nó tự tin nhất cũng
là lúc nó ít gọi nhất, mà đó chính là lúc cần nhất. Verifier bác thì kết luận bị **hạ** chứ
không bị nuốt.

### 4. Ba lỗi bộ đo E2E tìm ra ngay lần chạy đầu

- **`build.map` đọc sai cột.** `avr-nm --print-size` in `value size type name` cho symbol có
  kích thước và `value type name` cho symbol không có; không phân biệt thì cột `type` bị đọc
  thành kích thước, và bảng hiện `_etext = 8.388.720 B` đứng đầu danh sách "chiếm chỗ nhiều
  nhất".
- **`test.run` gom cả `control.c` vào rồi báo "không biên dịch được"** (đúng — nó không có
  `main()`), trong khi câu đúng là *"chưa có test nào"*. Một câu trả lời đúng về mặt kỹ
  thuật nhưng trả lời sai câu hỏi.
- **Bỏ mất "phần không mô phỏng được" trong im lặng** — nay cảnh báo (mục 2 ở trên).

Và một lỗi của chính bộ đo: `const char bang_tra[256]` **không dùng tới** bị `-Os` bỏ hẳn,
nên ca đo "bản đồ bộ nhớ thấy bảng tra" đang đo một firmware khác với firmware nó nghĩ.

### Số đo

`836 ca đơn vị` (+24) · `tools/thu_g6.py` **34/34** qua giao diện thật ·
`91 công cụ` khi cờ sơ đồ tắt (+7 so với DEV-276), `100` khi bật.

Hồi quy: GIAO DIỆN 28 · CUỐI 36 · G5 35 · CKM 35 · SCH 63 · HIER 46 — giữ nguyên.
Bằng chứng SCH-19: `--hai-che-do tools/thu_g6.py` **34/34 giống hệt** giữa hai chế độ cờ.

### Còn lại của G6/G7

`plan.enter`/`plan.exit` (§B5 plan mode) chưa làm — nó nằm ở bảng công cụ §B1 chứ không nằm
trong dòng nghiệm thu của G6. `target.*` (nạp chip, đọc log) thuộc **G7** và cần bo thật;
subagent `hardware` đã có khung nhưng sẽ trả `chua_du_du_kien` cho tới khi có những công cụ đó.

---

### [DEV-278] 27/09/2026 · G7 — bo STM32F469 thật, và bốn chỗ luồng "bo mới" bị đứt

Anh Công cắm một **STM32F469I-DISCO** vào máy và yêu cầu: *"tổng hợp toàn bộ thông tin từ mạch
này, sau đó viết một ứng dụng biên dịch và chạy được trên kit"*, với hai điều kiện — **tác tử
tự tìm tài liệu** ("Hãy để agent tự tìm tài liệu và load bạn nhé. Bạn giám sát và fix cho agent
nhé") và **tác tử tự xin cài công cụ** ("Thiếu tool bạn hãy yêu cầu agent cài thêm nhé. Bạn
không làm hộ nhé").

Đây là bước đầu tiên của dự án có phần cứng thật, nên nó không phơi ra lỗi logic mà phơi ra
**bốn chỗ luồng bị đứt hẳn** — mỗi chỗ đều ở dạng "hệ thống nói được là nó đọc được, rồi từ
chối ở bước sau".

#### 1. Không có đường nào tải tài liệu từ URL

`doc.search_web` trả về **ứng viên**; `doc.load` đọc tệp **đã nằm trong dự án**. Giữa hai thứ
đó không có gì cả — người dùng phải tự mở trình duyệt, tự tải, tự chép vào thư mục. Với bo mới
thì đó chính là bước đầu tiên.

→ `doc.fetch` (R3, cổng G-DATA). Hai điều nó cố ý làm khác bản nhanh nhất có thể viết:

- **Không tin phần mở rộng, không tin `Content-Type`** — tin *magic byte*. Trang tài liệu của
  nhiều hãng trả HTML tường cookie cho một URL kết thúc bằng `.pdf`, và lưu khối HTML đó thành
  `datasheet.pdf` là cách chắc chắn nhất để bước trích Fact hỏng ở chỗ không ai nghĩ tới.
- **Không tin `Content-Length`** — nó là lời khai của máy chủ. Trần dung lượng được ép trong
  lúc đọc từng khối, nếu không thì một máy chủ khai 1 KB vẫn đẩy được 4 GB vào đĩa.

Trang web CHÍNH LÀ tài liệu (trang nhà phân phối, wiki) thì nhận được, nhưng phải gọi lại với
`nhan_html=true` — và khi đó lưu **cả hai** tệp: bản HTML gốc để đối chiếu, bản chữ đã bóc để
trích dẫn theo dòng. Không thể vừa đánh số dòng theo chữ đã bóc vừa nói là đang trích dẫn tệp
HTML; trích dẫn chỉ có nghĩa nếu mở đúng tệp đó ra là thấy.

#### 2. `phan_loai` nói mã nguồn đọc được, `doc.load` lại từ chối

Tài liệu chân của bo này mà còn với tới được lại là **header BSP do chính hãng viết**
(`stm32469i_discovery.h`), không phải PDF. `ingest.phan_loai` nhận ra nó là `source` và trả
`doc_duoc=True`; `doc.load` chỉ có nhánh cho PDF và Office. Hệ thống tự trả về hai câu trái
nhau, và tác tử đi vào ngõ cụt giữa chúng.

→ `docs.nap_van_ban()`: nạp mã nguồn / header / linker script / Markdown / log với **đơn vị
trích dẫn là KHOẢNG DÒNG** (`dòng 121–160`), không phải "trang". Tệp văn bản không có trang, và
bịa ra số trang thì người mở tệp ra không kiểm lại được — mất đúng thứ N1 tồn tại để bảo vệ.

Và một lỗi kề bên, chỉ hiện ra sau khi khởi động lại app: đường **đọc lại** tài liệu
(`_lay_tai_lieu`) gửi *mọi* thứ không phải PDF cho bộ đọc Office. Một tài liệu văn bản nạp
được lần đầu, dùng được cả phiên, rồi chết ở phiên sau. Hai bản sao của cùng một phép chọn bộ
đọc đã lệch nhau → dồn về một hàm `_nap_theo_loai`, hai người gọi.

#### 3. Không biên dịch được cho ARM, và `avr-size` trả về "0 byte"

`CHUOI_CONG_CU` chỉ biết `avr8`. Thêm `armv6-m`/`armv7-m`/`armv7e-m` với đường biên dịch
bare-metal (nguồn `.c/.s` + linker script bắt buộc → `.elf` → `.bin` + `.hex` + `.map`).

Ba quyết định trong bảng, mỗi cái chọn phía "sai thì chậm" thay vì "sai thì treo":

- **`cpu = cortex-m4` cho armv7e-m**, dù ISA đó phủ cả M7. Lệnh của M4 chạy được trên M7 (M7
  là tập trên) nên firmware dịch cho M4 chỉ chậm hơn; dịch cho M7 rồi nạp vào M4 thì sinh lệnh
  chip không hiểu.
- **`float = soft`** mặc định. "FPU tuỳ biến thể" nghĩa là bật `-mfloat-abi=hard` trên chip
  không có FPU sẽ hard-fault ở lệnh dấu phẩy động đầu tiên — một lỗi phải chạy thật mới hiện.
  Muốn hard-float thì phải truyền `fpu=` và nó được đối chiếu với bảng `FPU_HOP_LE`.
- **Không tự sinh linker script.** Nó quyết định địa chỉ Flash/RAM của đúng con chip này; một
  địa chỉ đoán ra cho một firmware dịch xong, nạp xong, và không chạy. Có hai tệp `.ld` thì
  cũng từ chối — không đoán dùng cái nào.

Và bộ đọc kích thước phải viết riêng: `avr-size -C` in `Program:/Data:`, còn binutils ARM thì
không, nên bộ đọc của AVR khớp **0 dòng** và trả về `(0, 0)` — "firmware nặng 0 byte", một con
số vô lý mà vẫn đi tiếp được vào phép so hạn mức và cho ra kết luận "vừa chip" cho mọi
firmware. `kich_thuoc_arm()` đọc `-A` và **loại trừ** theo tên thay vì liệt kê trắng: một
section do linker script tự đặt (`.isr_vector`, `.qspi_text`) phải được tính, còn `.debug_*`
thì không — trên firmware thử, riêng `.debug_str` đã 14 KB so với 24 byte mã thật.

Chuyện thứ tư: `arm-none-eabi-gcc` của Homebrew **không kèm newlib**, nên `-lc` báo
`cannot find -lc` — một câu không nói được phải làm gì. Nay hỏi thẳng trình biên dịch bằng
`-print-file-name=libc.a`; không có thì liên kết `-nostdlib` **và khai ra cờ `thieu_libc`**,
kèm câu giải thích rằng `memcpy`/`memset` do chính trình biên dịch tự sinh cũng sẽ không liên
kết được. Đổi cách liên kết trong im lặng là cách để `undefined reference to memset` xuất hiện
sau đó, ở một chỗ không liên quan gì tới nguyên nhân thật.

#### 4. G7 — nạp vào bo mà không có `st-info` thì đối chiếu ID chip bằng gì

`target.detect` / `target.flash` (R4, cổng G-FLASH) / `target.log`. Bo này chạy firmware
ST-LINK kiểu **mass-storage** nên nạp được bằng cách sao `.bin` vào `/Volumes/DIS_F469NI`, không
cần cài gì. Nhưng MDD-40 §B1 đòi *"flash đối chiếu ID chip"* (TC034), và đường ổ đĩa **không
đọc được ID chip**.

Chỗ này dễ làm tròn lên, nên viết rõ cả trong mã: nhãn ổ `DIS_F469NI` là bằng chứng về **bo**,
không phải về **silicon**. Nó đủ để *bác bỏ* (ghim F103 mà nhãn nói F469 → dừng, E4012), không
đủ để *khẳng định*. Không đọc được ID chip thì `target.flash` **từ chối** với E4013 và trình hai
đường cho người dùng chọn: cài `st-info`/`st-flash` qua `tool.install`, hoặc gọi lại với
`dong_y_khong_doi_chieu_chip=true`. Tác tử không được tự chọn hộ.

Ba điều khác của G7, mỗi điều từ một ca kiểm:

- **`shutil.copy` trả 0 không phải bằng chứng đã nạp** (TC032). Firmware DAPLink nhận cả tệp
  rồi mới kiểm, và khi từ chối thì nó gắn lại ổ kèm `FAIL.TXT`. Nên `dat=True` đòi: không có
  `FAIL.TXT` (và `FAIL.TXT` của lần trước bị dọn trước khi sao, nếu không thì lần này đọc lại
  kết luận của lần trước); còn nếu không thấy ổ gắn lại thì vẫn `dat` nhưng **kèm cảnh báo rằng
  chưa có bằng chứng bo đã ghi xong**.
- **Sao tệp thất bại giữa đường** (TC033) → nói thẳng Flash đang ở trạng thái không nhất quán,
  kèm đường khôi phục (connect-under-reset, bootloader ROM).
- **Không thấy bo** (TC032) → danh sách kiểm tra **đủ bốn mục** đề bài đòi: nguồn, cáp, driver,
  chân BOOT/NRST. Ghi chú cũ của TC032 là *"mới có một bước"*; nay đủ bốn.

Và một thứ chỉ lộ ra khi chạy trên máy thật: **tai nghe Bluetooth của anh Công cũng hiện ra ở
`/dev/cu.*`**. Đọc log từ nó thì im lặng, mà im lặng sẽ bị đọc thành "firmware sai". Nên cổng
được **phân loại** (`co_the_la_bo`) kèm lý do, chứ không lẳng lặng bỏ — người dùng thấy cổng đó
trong Terminal và sẽ hỏi tại sao nó thiếu. `target.log` có nhiều hơn một ứng viên thì **không
đoán**, nó trình danh sách để người chọn.

#### 5. Chuyện mạng: `www.st.com` bị chặn, và không có máy tìm kiếm nào dùng được

Đo được trên máy anh Công: `www.st.com` bị **reset ở tầng mạng** sau ~0,6 s, kể cả khi ép đúng
IP Akamai và kể cả ngoài sandbox — trong khi `ti.com`, `github.com`, `example.com` vào bình
thường. `st.com` (không `www`) trả 301 về đúng host bị chặn. Mọi instance SearXNG công khai thử
được đều chặn bằng anti-bot; DuckDuckGo, Mojeek, Bing đều trả trang xác minh trình duyệt hoặc
chỉ dựng kết quả bằng JS; tự dựng SearXNG thì cần Docker, máy chưa có.

Còn lại một nguồn vào được **và** do chính hãng viết: tổ chức GitHub của nhà sản xuất. Nên
`doc.search_web` có backend thứ hai (`tim_kiem.py`): SearXNG nếu cấu hình, **rồi** GitHub của
hãng — và kết quả luôn khai `nguon_tim`, vì một danh sách ứng viên không khai nguồn sẽ được đọc
như thể nó từ datasheet.

Hai chi tiết đáng ghi:

- Repo của hãng đặt tên theo **họ** chip: tài liệu của `stm32f469` nằm trong `STM32CubeF4`. Tìm
  thẳng "stm32f469" trong tên repo thì khớp **0**, và "không khớp" ở đây bị đọc thành "hãng
  không phát hành tài liệu". Nên từ khoá được sinh thêm dạng họ (`stm32f469` → `stm32f4`, `f4`).
- Bảng `TO_CHUC_HANG` **không có** mục "mọi thứ khác → cứ tìm cả GitHub". Một repo của người lạ
  trùng tên chip sẽ được trả về trông y như tài liệu hãng — sai mà trông đúng là cách hỏng tệ
  nhất.

Lần chạy thật đầu tiên đụng ngay **hết hạn mức GitHub API** (60 lượt/giờ cho cả máy khi không
xác thực; chính tôi dùng hết trong lúc thăm dò). Đây là chỗ dễ gọi sai tên: hạn mức **không
phải** mất mạng. Mất mạng thì thử lại ngay được; hết hạn mức thì thử lại ngay là chắc chắn thất
bại lần nữa, và một tác tử được bảo "lỗi mạng" sẽ thử lại đúng như thế cho tới khi hết lượt gọi
công cụ. Nên có mã riêng **E3003**, nói rõ **còn bao nhiêu phút** nữa mới thử lại được, và chỉ
thẳng hai đường đi tiếp (người dùng đưa URL, hoặc đặt `EIDE_GITHUB_TOKEN`). Hết hạn mức mà có
nhớ đệm quá hạn thì dùng nhớ đệm và **khai ra là cũ** — một danh sách repo cũ vài ngày vẫn gần
đúng, còn không trả gì thì tác tử mất hẳn đường tìm.

#### 6. Tab Mạch thật không còn là chỗ trống chờ G7

A9 trước đây là một khối `empty` ghi "thuộc bước G7". Nay nó hiện đúng cột mà §E7 đòi: *nạp gì
(hash, kích thước) vào đâu, verify thế nào, nếu không khớp thì vì sao dừng*. Khối nạp **không**
được rút gọn thành "đã nạp xong": nó mang hash, số byte, đích, chip đã đối chiếu (hoặc câu
"CHƯA đối chiếu bằng ID đọc từ silicon"), và **verify hay không verify** — "đã nạp" mà không
verify là một câu đúng chữ nhưng dẫn tới kết luận sai về việc chip đang chạy bản nào.

Thêm khối `log` bên Swift: hiện **nguyên văn**, không tóm tắt (log là bằng chứng; một bản tóm
tắt log là lời của người tóm tắt, không phải của bo), và **cổng im lặng phải trông khác cổng
chưa đọc** — một khung trống không nói được đó là "bo không in gì" hay "chưa ai bấm đọc", mà
hai thứ đó dẫn tới hai kết luận trái nhau.

#### 7. Một test của tôi xanh vì nó kiểm bản sao của chính nó

`_cong_noi_tiep` viết thẳng `Path("/dev")` trong thân hàm, nên ca kiểm không trỏ được sang thư
mục giả. Bản đầu tôi **chép lại phép phân loại cổng vào chính test** — và một test như thế xanh
kể cả khi hàm thật sai. Sửa: `THU_MUC_DEV` thành hằng số của mô-đun, test kiểm đúng hàm thật.
Cùng loại với bốn phép đo tự lừa mình ở DEV-276; đây là lần thứ năm.

#### 8. Hai lỗi chỉ lộ ra khi cho tác tử tự tìm thật

**Tìm ra bo KHÁC cùng họ, và tác tử từ chối đúng.** Với truy vấn "STM32F469I-DISCO", bộ tìm
trả về `stm32f4_discovery.h` của repo `stm32f4discovery-bsp` — đó là bo **STM32F4-DISCOVERY
(F407)**, không phải bo đang cắm. Tác tử đọc xong và nói *"chưa tìm được tài liệu phù hợp"*:
phán đoán đúng, nhưng nó phải làm việc đó để bù cho một phép chấm điểm sai của tôi.

Sai ở đâu: điểm được **cộng dồn** cho mọi biến thể khớp được, nên một tên chứa cả `stm32`,
`stm32f4` và `f4` nhận ba lần điểm cho **cùng một sự thật** ("thuộc họ F4") — đủ để đè một
tên khớp đúng mã bo. Nay lấy **max theo độ đặc hiệu**: biến thể đầy đủ 100, mã đặt hàng 90,
bỏ chữ họ 80, họ chung 40, tiền tố hãng 10.

Và một chi tiết đặt tên của ST phải biết mới tìm được: repo/thư mục đặt theo **mã đặt hàng**,
bỏ tiền tố `stm` và đôi khi bỏ cả chữ họ — chip `STM32F469I` → repo `32f469idiscovery-bsp`,
thư mục `Drivers/BSP/STM32469I-Discovery/`, tệp `stm32469i_discovery.h` (**không có chữ F**).
Tìm thẳng "stm32f469" thì khớp 0, và "không khớp" bị đọc thành "hãng không phát hành tài liệu".
Sau khi sửa, cùng truy vấn ấy trả về đúng `stm32469i_discovery.h` của `32f469idiscovery-bsp`,
điểm 254 so với 140 của bo F407.

**Danh sách đánh số hiện ra 1, 2, 5.** Ảnh chụp bước 2 cho thấy tác tử viết `1. 2. 3.` mà giao
diện hiện `1. 2. 5.`: số thứ tự lấy theo chỉ số trong danh sách **đã làm phẳng**, nên hai gạch
đầu dòng con của mục 2 cũng được đếm. Tác tử viết đúng, giao diện đọc sai, và người đọc tưởng
tác tử đếm nhầm. Nay đếm riêng theo mức thụt, và quay về mức nông hơn thì xoá bộ đếm của các
mức sâu hơn.

#### 9. Mười sáu thẻ cổng cho một công cụ, và một nhớ đệm bị tưởng là dữ liệu

Lượt "tự tìm tài liệu" dựng **16 thẻ cổng G-DATA**, tất cả cho cùng `doc.search_web`. Nguyên
nhân không phải luật G-DATA mà là ma trận rủi ro/tự chủ: R3 ở mức A3 thì hỏi, và mỗi lời gọi
là một lần hỏi. Hỏi lại mười sáu lần không làm người dùng an toàn hơn — nó dạy người ta bấm
Duyệt theo phản xạ, và khi một thẻ ĐÁNG đọc hiện ra thì họ cũng bấm nốt. (Cùng lý lẽ với chú
thích sẵn có ở `build.compile` về việc không xếp nó R3.)

→ Duyệt một lần thì **cả lượt việc** đó không hỏi lại cùng công cụ nữa; câu mới của người dùng
mở lượt mới và xoá trí nhớ ấy. Cố ý KHÔNG nhớ cho ba loại: thao tác không hoàn tác được,
`never_auto`, và R4 — `target.flash` gọi mười lần thì hỏi đủ mười lần. Đã kiểm ngược cả hai
chiều: bỏ phép nhớ → ca "một thẻ cho cả lượt" đỏ; nhớ cả thao tác không hoàn tác → ca
"nạp hai lần, hai thẻ" đỏ.

Và một lỗi kín hơn, chỉ lộ ra ở lượt chạy sau: tác tử **không gọi `doc.search_web` lần nào**
mà đi bới `.eide/tim-kiem/*.json` và `.eide/sessions/*/transcript.jsonl` bằng `fs.read`. Nhớ
đệm tìm kiếm nằm trong sandbox dự án nên `fs.glob` thấy nó, và một tệp JSON tên
`STMicroelectronics-32f469idiscovery-bsp-main.json` trông y như dữ liệu của dự án. Nó không
phải: đó là dữ liệu của **máy** (danh sách repo của hãng), dùng chung cho mọi dự án. Chuyển ra
`~/.cache/eide/tim-kiem`. Một nhớ đệm để lẫn vào chỗ chứa hiện vật sẽ được đọc như hiện vật.

#### 10. `doc.fetch` từ chối đúng tệp mà `doc.load` nạp được

Tác tử tìm ra đúng `stm32469i_discovery.h` trong repo `32f469idiscovery-bsp` của ST, gọi
`doc.fetch`, và bị **chính EIDE** chặn: bộ nhận dạng theo magic byte trả `khong_biet` cho một
tệp văn bản thuần, nên `doc.fetch` không lưu. Rồi tác tử rút ra một kết luận sai từ lỗi của ta:
*"hãng chỉ lưu mã nguồn và header C, không lưu tài liệu bản gốc… nên công cụ đã từ chối tệp
header thô"*.

Đây là mục 2 lặp lại ở một chỗ khác: `doc.load` đã nạp được mã nguồn từ mục 2, nhưng
`doc.fetch` vẫn giữ danh sách nhận-được cũ (PDF/Office/RTF). Hai công cụ của cùng một hệ thống
nói ngược nhau, và cái nói "không" đứng trước.

→ Không có magic byte KHÔNG có nghĩa là không đọc được. Thêm nhánh `van_ban`, với phép kiểm
hai tầng: giải mã được UTF-8 **và** dưới 2 % ký tự không in được. Chỉ kiểm giải mã là chưa đủ —
một tệp nhị phân vẫn có thể tình cờ hợp lệ UTF-8, và khi đó ta lưu nó thành "tài liệu" rồi
trích dẫn "dòng 40" của một mớ ký tự điều khiển. Nhánh HTML vẫn đứng TRƯỚC nhánh này: HTML
cũng là văn bản, nhưng nó phải rơi vào đường xử lý riêng của nó.

Đo lại sau khi sửa: tải đúng tệp ấy về được, 10 728 byte, 362 dòng, và trong đó có đủ thứ cần
cho firmware đầu tiên — `LED1_GPIO_PORT = GPIOG`, `LED1_PIN = GPIO_PIN_6`, `LED2 = PD4`,
`LED3 = PD5`, `LED4 = PK3`, `WAKEUP_BUTTON = PA0`.

Một ghi nhận cho bước đọc log: header BSP của bo này **không định nghĩa cổng COM nào**
(`grep -E "COM|USART|UART"` trả rỗng). Nghĩa là cổng COM ảo của ST-LINK nhiều khả năng không
nối sẵn vào USART nào — nên `target.log` im lặng sẽ là kết quả ĐÚNG, không phải dấu hiệu
firmware sai, và đó chính là câu mà công cụ log được viết để nói.

#### 11. Phiên chạy hết tới biên dịch — và ba lỗi chỉ hiện ra khi có firmware thật

Lần chạy sạch đầu tiên đi được tới bước 8: tác tử tự tìm, tải và nạp **ba tài liệu**
(`stm32469i_discovery.h` của BSP, `stm32f469xx.h` của CMSIS, và trang nhà phân phối anh Công
đưa), ghim hộ chiếu chip, viết firmware bare-metal ba tệp, biên dịch **đạt** với 0 lỗi 0 cảnh
báo, và ảnh nạp có vector table đúng hợp đồng Cortex-M (SP trỏ vào RAM, Reset_Handler trong
Flash, bit Thumb bật).

Firmware nó viết dùng **PG6** — đúng chân LED1 của bo — bật xung nhịp GPIOG trước khi chạm
thanh ghi, và chú thích dẫn nguồn kèm **số dòng**: *"LED1 (Green) nối vào chân PG6 (tài liệu
BSP-STM32469I-DISCO-H dòng 131, 145)"*.

Nhưng kho chỉ có **một** Fact, và Fact đó **sai**.

**`fact.extract` trả `ok` với 0 ứng viên.** Bộ mẫu của nó khớp theo tên thông số điện của
datasheet (VDD, VIH, nhiệt độ). Một header BSP không có chữ nào trong bộ mẫu ấy, nên tác tử
gọi hai lần, cả hai `ok`, kho vẫn rỗng — rồi nó viết firmware bằng số đọc được từ tài liệu mà
**không có Fact nào đứng sau**. Đúng thứ N1 tồn tại để ngăn, và nó lọt qua vì "không tìm thấy
gì" mang cùng hình dạng với "đã làm xong".

→ Bộ trích `#define` cho tài liệu mã nguồn: `trich_dinh_nghia` + `ghep_chan_tu_dinh_nghia`.
Trên `stm32469i_discovery.h` thật nó đọc được 50 chỉ thị và ghép ra **10 chân**: LED1 = PG6,
LED2 = PD4, LED3 = PD5, LED4 = PK3, WAKEUP_BUTTON = PA0, SD_DETECT = PG2, TS_INT = PJ5…
Ghép theo **tiền tố** chứ không theo thứ tự xuất hiện: ghép theo thứ tự sẽ nối cổng của khai
báo này với số chân của khai báo kia và tạo ra một chân không tồn tại. Mỗi Fact trỏ tới **đúng
hai dòng** khai báo — cổng và số chân nằm ở hai `#define` khác nhau, và một trích dẫn chỉ tới
một trong hai thì người mở tài liệu ra không kiểm lại được.

Một thứ bộ trích tìm thấy mà con người dễ bỏ qua: header của ST **tự khai** `AUDIO_INT` và
`OTG_FS1_OVER_CURRENT` **cùng PB7**. Không phải lỗi đọc — đó là điều tài liệu nói, và im lặng
về nó là giấu đi một quyết định phần cứng. Nay nó thành `chan_trung` kèm cảnh báo.

**Và Fact duy nhất trong kho là `flash.size = 7.0`.** Mẫu "FLASH Size" khớp vào dòng
`#define FLASHSIZE_BASE 0x1FFF7A22UL /*!< FLASH Size register base address */` — con số ở đó
là **địa chỉ của thanh ghi ghi kích thước**, không phải kích thước. Bộ đọc số lấy ra `7`.
`_han_muc` lấy 7 làm trần Flash. `build.compile` chia 224 byte cho 7 và báo firmware chiếm
**320 % Flash của chip**. Không lớp nào trên đường đi ấy thấy con số vô lý.

→ Hai cái phanh, đặt ở hai chỗ khác nhau vì một cái sẽ hỏng lần nữa:

1. `_la_dong_dia_chi` — bỏ qua dòng khai địa chỉ (`*_BASE`, `*_ADDR`, "base address") trước
   khi khớp mẫu thông số.
2. `PHAM_VI_HOP_LY` — khoảng giá trị hợp lý theo đơn vị cơ bản cho từng khoá (Flash 1 KB…64 MB,
   VDD 0,5…60 V, nhiệt độ −100…200 °C). Giá trị ngoài khoảng thì **không ghi thành Fact**, và
   `_han_muc` kiểm lại lần nữa trước khi dùng làm trần. Thà không có hạn mức còn hơn có hạn
   mức sai: "chưa biết firmware có vừa chip không" là một câu đúng, còn "320 %" thì không.

**Bộ đo của tôi cũng suýt nói sai.** Bảng đối chiếu firmware ↔ tài liệu bóc chân từ mã nguồn
bằng mẫu `PG6` / `GPIOG`+`GPIO_PIN_6`. Firmware bare-metal thật viết `GPIOG->BSRR = (1UL << 6)`
— không khớp mẫu nào, nên bảng sẽ ghi "không" cho **cả bốn** LED và người đọc hiểu là firmware
sai chân. Sửa: thêm mẫu dịch bit, và quan trọng hơn là trả về cờ **"có đọc được mã không"** —
một tập rỗng có hai nghĩa trái ngược ("firmware không dùng chân nào" và "bộ đo không đọc nổi
mã này"), và trả cùng một `set()` cho cả hai là biến cái thứ hai thành cái thứ nhất.

#### 12. Việc nạp bị chặn bằng một báo động giả

Phiên đi tới bước nạp, và `target.flash` **từ chối** với E4012: *"dự án ghim STM32F469NI nhưng
bo đang cắm là chipid 0x434"*. Bo đang cắm đúng là F469. Lỗi là của tôi, ở hai chỗ chồng lên
nhau — và chỗ thứ hai nguy hiểm hơn chỗ thứ nhất.

**Chỗ thứ nhất: đọc nhầm dòng.** Tác tử đã tự xin cài `stlink` qua cổng G-TOOL (đúng điều anh
Công yêu cầu — công cụ do *nó* xin, không phải tôi cài hộ), nên `st-info --probe` chạy được.
Đầu ra của nó có **cả hai** dòng:

    chipid:     0x434
    dev-type:   STM32F46x_F47x

`doc_id_chip` đọc `chipid` trước, nên phép đối chiếu nhận được chuỗi `chipid 0x434` — một mã
số mà nó không có cách nào so với `STM32F469NI`. Đổi thứ tự: `dev-type` trước, `descr` sau,
`chipid` chỉ còn dùng để nói *"đọc được bo nhưng chưa suy ra được tên chip"*. Tiện thể lấy
luôn `flash: 2097152` và `sram: 262144` — số đọc từ **chính con chip đang cắm**, chắc hơn mọi
con số trích từ tài liệu bằng biểu thức chính quy (xem `flash.size = 7` ở mục 11).

**Chỗ thứ hai: phép so chỉ có hai giá trị.** `_cung_chip` trả `True`/`False`, và `False` được
dùng làm *"chứng minh được là khác chip"* → dừng. Nhưng `False` thật ra gộp hai chuyện trái
ngược: **"chứng minh được là khác"** và **"không so được"**. Cái sau phải dẫn tới HỎI, không
dẫn tới DỪNG.

Đây đúng là hình dạng của bài học đã viết ở G6 cho `chua_do_duoc`: *"không kiểm được" không
bao giờ được hiện ra thành "đã kiểm"*. Ở đây nó xuất hiện theo chiều ngược lại — "không kiểm
được" hiện ra thành "đã kiểm và thấy sai". Cả hai đều là cùng một lỗi: một trạng thái thứ ba
bị ép vào một ô nhị phân.

→ `so_chip()` trả `khop` | `lech` | `chua_so_duoc`. `target.flash` **chỉ** chặn ở `lech`;
`chua_so_duoc` rơi xuống nhánh xin xác nhận tường minh đã có sẵn. Hậu quả thực tế của việc
làm sai: một cảnh báo sai ở đúng chỗ nguy hiểm nhất (thao tác không hoàn tác được) dạy người
dùng bấm qua cảnh báo — và lần sau, khi thẻ cổng báo đúng, họ cũng bấm qua.

#### 13. Ứng dụng người dùng TỰ KIỂM ĐƯỢC, và hai phép đo của tôi lại sai

Anh Công yêu cầu một ứng dụng *"mà mình TỰ KIỂM ĐƯỢC bằng tay, chứ không phải chỉ nháy một
đèn rồi tin lời bạn"*: dùng cả bốn đèn, có phản ứng với nút bấm, và mức tích cực của nút phải
đọc từ tài liệu chứ không đoán.

Tác tử làm được, và có một bước đáng ghi lại: nó gọi `fact.from_doc` cho từng chân, rồi khi
cần biết **đèn sáng ở mức cao hay thấp**, nó phát hiện header BSP chỉ *khai báo* `BSP_LED_On`
chứ không có thân hàm — nên nó đi **tải thêm tệp `.c`** và trích ra
`led.on_state = GPIO_PIN_RESET` từ đúng dòng có `HAL_GPIO_WritePin(..., GPIO_PIN_RESET)`.
Đèn trên bo này tích cực mức THẤP, và firmware kéo chân xuống 0 để bật. Tôi đã kiểm lại chỗ
trích dẫn ấy bằng tay: câu chữ có thật ở đúng khoảng dòng được nêu.

Kết quả: 4 đèn chạy vòng khi thả nút, cả 4 chớp nhanh đồng loạt khi giữ nút. Anh Công bấm thử
và xác nhận đúng — đây là mục đầu tiên của dự án đạt ở **tầng NGƯỜI**, thứ không có cách nào
đo bằng mã.

**Nhưng bộ đo của tôi báo sai hai lần, theo hai chiều ngược nhau.**

Lần một, báo **thiếu** cái đang có: phép kiểm "chân nào trong mã" lấy tích Descartes của
{cổng thấy được} × {số thấy sau `<<`}. Những số nó bắt được là **0, 3, 6, 10** — đó là bit bật
xung nhịp trong `RCC_AHB1ENR` (GPIOAEN=0, GPIODEN=3, GPIOGEN=6, GPIOKEN=10), **không phải số
chân**. Còn PD4/PD5 thì trượt hẳn vì firmware viết `1UL << LED2_PIN`, tức tên macro chứ không
phải chữ số. Sửa: giải bảng `#define` của chính firmware thành số, ghép cổng với bit **trên
cùng một dòng**, và bỏ qua dòng có `RCC_`.

Lần hai, báo **có** vì lý do sai: regex `\bGPIO([A-K])\b` **không khớp** `GPIOG_BSRR`, vì `_`
cũng là ký tự từ nên `\b` không đứng được ở đó. Nghĩa là suốt thời gian qua, bảng đối chiếu
firmware ↔ tài liệu xanh **nhờ khớp vào chú thích** `/* LED1 … PG6 */`, không phải nhờ đọc mã.
Đúng cùng một lỗi với "control.c không có AVR" ở DEV-276 — lần thứ sáu. Sửa thành
`\bGPIO([A-K])(?![A-Z])`: khớp `GPIOG_BSRR`, không khớp `GPIOAEN`.

Và một lần tôi tự nghi oan hệ thống: thấy `led.on_state = GPIO_PIN_RESET` trích dẫn "dòng
241–280" mà tệp `.h` ở đó chỉ có macro reset I2C, tôi kết luận `fact.from_doc` đã để lọt một
Fact bịa. Sai — Fact ấy trích dẫn tệp **`.c`**, không phải `.h`; tôi kiểm nhầm tệp. Phép kiểm
nguyên văn E2006 vẫn nguyên vẹn.

**Thêm `target.verify`** (R2): đọc ngược Flash từ chip rồi so từng byte với tệp đã nạp.
`st-flash write` tự in "verified", nhưng đó là lời của **chính công cụ vừa ghi**; công cụ này
đi hỏi silicon *con chip đang chứa bản nào*. Nó cũng giữ đúng ba trạng thái: khớp / khác /
**không đo được** — thiếu `st-flash` thì trả E4015 với câu "KHÔNG đo được khác với KHÔNG khớp",
chứ không nói chip sai bản. Đo thật trên bo: 492 byte, khác 0 byte, sha256 `f3510534…`.

#### 14. Logo lên màn hình — năm lỗ hổng nữa, và bốn trong số đó làm việc chạy được trông như việc không thể

Yêu cầu: *"tìm logo của trường PTIT, viết chương trình hiển thị logo lên màn hình và thông
tin của sản phẩm, của tôi và của thầy Hiếu"*. Bo này có màn cảm ứng 800×480 nối qua **MIPI
DSI** — khác hẳn mức khó của việc nháy một cái đèn.

**Khảo sát trước khi giao việc.** Vẽ được lên màn ấy cần LTDC + DSI + driver panel OTM8009A +
SDRAM ngoài làm bộ đệm khung, tức khoảng **60–70 tệp** trải trên năm repo của ST
(`32f469idiscovery-bsp`, `stm32f4xx-hal-driver`, `cmsis-device-f4`, `cmsis-core`,
`stm32-otm8009a`). Ba chỗ chặn, gỡ được hai — và cái thứ ba **cố ý không gỡ hộ**.

**(a) Không có đường lấy mã nguồn của hãng.** `doc.fetch` lấy một tệp một lượt, và tệp nó lấy
về đi vào **kho tài liệu** — trong khi thứ cần ở đây là **mã sẽ được biên dịch**. Sáu mươi
lượt gọi vượt ngân sách một lượt làm việc, và người dùng phải duyệt cổng sáu mươi lần: đúng
kiểu ma sát dạy người ta bấm Duyệt theo phản xạ, rồi bấm nốt cả cái thẻ đáng đọc.

→ `code.vendor_fetch` (R3, G-DATA). Chỉ nhận tệp văn bản: một tệp nhị phân lọt vào thư mục
firmware sẽ làm trình biên dịch báo một lỗi không liên quan gì tới nguyên nhân thật. Không bao
giờ ghi ra ngoài thư mục đích, kể cả khi đường dẫn trong repo có `..`. Và **hỏng một phần phải
nói ra là hỏng một phần**: lấy 70 tệp mà 3 tệp lỗi rồi báo "xong" là cách để lỗi hiện ra lúc
liên kết, xa chỗ gây ra nó nhất. Có `doi_ten` vì `stm32f4xx_hal_conf_template.h` **bắt buộc**
phải thành `stm32f4xx_hal_conf.h`, nếu không mọi `#include` trong HAL đều hỏng.

**(b) Chip không có trình đọc PNG.** Không có công cụ đổi ảnh thì tác tử chỉ còn hai đường:
bịa ra một mảng điểm ảnh, hoặc bảo người dùng tự đi làm. → `asset.image_to_c` (R2). Ba điều cố
ý: **tính trước** số byte và so với Flash *còn lại* (nói trước, thay vì để trình liên kết báo
`region FLASH overflowed` sau mười phút); **giữ tỉ lệ** khi thu nhỏ (méo là thứ nhìn thấy
ngay); và nói rõ RGB565 **bỏ hẳn** kênh trong suốt — một logo nền trong suốt sẽ thành nền đen
nếu không ai nói trước.

**(c) Không có newlib, và không gỡ hộ.** `brew install --cask gcc-arm-embedded` cần **sudo**
nên tác tử không cài được; máy không có `memset`/`memcpy`/`printf` mà HAL dùng nhiều. Ràng
buộc này được nói thẳng trong lệnh giao việc để tác tử tự xử lý — đúng yêu cầu của anh Công:
*"nếu agent gặp lỗi hoặc chưa làm được thì bạn fix lỗi hoặc bổ sung năng lực. Không làm thay
agent."*

**Rồi lượt chạy đầu phơi ra ba lỗ hổng nữa, và cả ba cùng một hình dạng: một việc CHẠY ĐƯỢC
trông như một việc KHÔNG THỂ.**

**(d) `E3001` cho một truy vấn không phải về chip.** Tác tử gõ *"logo PTIT Học viện Công nghệ
Bưu chính Viễn thông"* và nhận về lỗi **mất mạng** — trong khi máy vào mạng hoàn toàn bình
thường. Nguyên nhân: `TO_CHUC_HANG` không khớp hãng nào, nên backend GitHub bỏ cuộc, và không
có backend nào khác. Một lỗi gọi sai tên dẫn tác tử đi sai hướng: nó sẽ đợi mạng, không đi tìm
đường khác.

→ Backend **Wikimedia Commons**, đứng cuối chuỗi `SearXNG → GitHub hãng → Wikimedia`. Thứ tự
ấy theo độ gần với "tài liệu của hãng", và Wikimedia là **bên thứ ba** nên phải đứng cuối:
kết quả ghi rõ phải nạp với `nguon="ben_thu_ba"` và nhắc xem giấy phép từng tệp. Khi truy vấn
có chữ "logo/ảnh/hình" thì ảnh được xếp trên PDF — hỏi logo mà nhận về một bản PDF 1275×1650
thì gần như chắc chắn không phải thứ người ta muốn. Đo thật: ra đúng
`Logo_PTIT_University.png` (4251×4251, có kênh trong suốt).

**(e) `doc.fetch` từ chối ảnh.** Tìm đúng logo rồi bị **chính EIDE** chặn ở bước tải:
*"không nhận ra định dạng… byte đầu b'\x89PNG'"*. → Nhận PNG/JPEG/GIF/BMP/TIFF/WebP/SVG,
nhưng **không** đưa vào kho tài liệu: ảnh không trích dẫn được, nên `note_vi` chỉ thẳng sang
`asset.image_to_c` thay vì để tác tử gọi `doc.load` rồi đọc một lỗi nói về OCR. SVG phải xét
**trước** HTML — nó là văn bản XML, và nhận nhầm thành trang web thì một tệp logo bị từ chối
kèm câu "trên trang không có liên kết PDF nào".

**(f) Lỗi của chính tôi, và nó giả dạng thành lỗi mạng.** `User-Agent` tôi viết cho lời gọi
Wikimedia có dấu tiếng Việt (*"luận văn PTIT"*), mà urllib mã hoá header HTTP bằng **latin-1**
→ `UnicodeEncodeError`. Nó hiện ra thành *"Không gọi được API Wikimedia"* — một câu khiến người
đọc đi kiểm đường truyền, trong khi lỗi nằm gọn trong một chuỗi hằng. Sửa thành ASCII, và có
một ca kiểm **đọc thẳng mã nguồn** rồi `encode("latin-1")` từng dòng có `User-Agent`, để lỗi
này không quay lại bằng một lần sửa vô ý.

#### 15. Đoán đường dẫn, và ba lần hệ thống nói sai về chính nó

Việc "hiện logo lên màn" được chia làm ba lượt sau khi lượt gộp thất bại. **Lượt một xong
sạch**: tác tử đi `doc.search_web` → `doc.fetch` → `asset.image_to_c`, tìm được
`Logo_PTIT_University.png` trên Wikimedia (4251×4251, có kênh trong suốt), tải về, và sinh ra
`logo_ptit.c/h` ở 240×240 rgb565 — 115 KB trong Flash 2 MB. Cả ba phép kiểm xanh: có ảnh
thật, mảng sinh **bằng công cụ** từ chính ảnh đó, và header khai đúng kích thước.

**Lượt hai thất bại theo một kiểu đáng ghi.** Tác tử xin 49 tệp từ `STM32CubeF4` theo bố cục
quen thuộc — `Drivers/STM32F4xx_HAL_Driver/Src/…`, `Drivers/BSP/STM32469I-Discovery/…`,
`Drivers/BSP/Components/otm8009a/…` — và **44 tệp trả 404**. Chỉ `Drivers/CMSIS/Include/*`
còn thật. Lý do: ST đã tách HAL, CMSIS device, BSP của bo và driver panel thành các **repo
riêng** (submodule), nên bố cục tác tử nhớ là bố cục của bản đóng gói cũ.

Đây không phải lỗi suy luận. Đó là **đoán khi đáng lẽ phải nhìn**, và lỗi thật là của EIDE:
nó không có công cụ nào để *nhìn xem một repo có gì*. → `code.vendor_list` (R2), dùng lại
nhớ đệm cây tệp của bộ tìm kiếm. Đo thật: `*hal_dsi*` trong `stm32f4xx-hal-driver` ra đúng
`Inc/stm32f4xx_hal_dsi.h` + `Src/stm32f4xx_hal_dsi.c`; `*otm8009a*` trong `stm32-otm8009a` ra
4 tệp; `*stm32f469xx*` trong `cmsis-device-f4` ra 6 tệp, kể cả `Source/Templates/gcc/
startup_stm32f469xx.s`. Không khớp gì thì nói thẳng *"nhiều SDK tách thành nhiều repo"* thay
vì để tác tử thử lại đúng phép đoán vừa hỏng.

**Và ba lần hệ thống nói sai về chính nó — mỗi lần một chiều khác nhau.**

**(a) Bộ chống quay vòng đếm sai chiều.** Lượt gộp trôi hết vào:

    ledger.query → fs.glob ×5 → store.list → store.get → ledger.query → history.list
                 → ledger.query ×4

Mười bốn lời gọi chỉ-đọc, không ghi gì. Nhưng `_nhac_neu_dang_quay_vong` đếm **theo từng tên
công cụ** với ngưỡng 6, nên không tên nào chạm ngưỡng cho tới lời gọi thứ mười bốn — và tới
đó thì lượt đã hết, lời nhắc không còn ai đọc. Trải việc tìm ra nhiều công cụ khác nhau không
làm nó bớt là quay vòng. Thêm ngưỡng **tổng** lời gọi chỉ-đọc (10), và thêm `history.list`,
`history.diff`, `snapshot.list` vào danh sách công cụ đọc — **đúng ba công cụ tác tử đã dùng
để quay vòng**, và cả ba vắng mặt trong bản trước.

**(b) Nhật ký chép một lời gọi thành công thành lỗi.** Sở cứ ghi
`code.vendor_fetch → LỖI None` trong khi sổ cái ghi `ok: true`, 22 giây. Nguyên nhân: lời gọi
bị cổng chặn **chạy ở lượt sau** (`run-113` mở cổng, `run-121` chạy), nên lúc bộ ghi đọc sổ
cái thì dòng `tool_result` chưa kịp có, và `ok is None` bị in ra thành `LỖI None`. Nay đợi
rồi đọc lại, và nếu vẫn chưa có thì ghi **"CHƯA RÕ (kết quả chưa ghi xong)"**. Một sở cứ nói
sai về chính thứ nó đang làm chứng thì tệ hơn không có sở cứ.

**(c) Lỗi của người giao việc, tức là tôi.** Lượt đầu tôi giao cả việc trong một câu: tìm
logo + lấy 60–70 tệp driver + viết chương trình + biên dịch + nạp. Ngân sách một lượt là 40
lời gọi. Việc quá lớn cho một lượt thì **chia ra là việc của người giao**, không phải lỗi của
người làm — và tôi đã đổ cho tác tử trước khi nhìn ra điều đó.

#### 16. Bốn lần thử lấy driver, và mỗi lần lộ ra một tầng sâu hơn

Bước "lấy driver màn hình" mất bốn lượt. Đáng ghi vì **mỗi lần tác tử thất bại theo một kiểu
khác, và lần nào lỗi cũng nằm ở EIDE chứ không ở suy luận của nó.**

| Lần | Tác tử làm gì | EIDE thiếu gì |
|---|---|---|
| 1 | xin 49 tệp theo bố cục `STM32CubeF4` → 44 tệp 404 | không có cách **nhìn** repo có gì |
| 2 | xin 26 tệp từ `stm32f4xx_hal_driver@main` → 0 tệp, mà vẫn `ok` | `vendor_list` bị ẩn; `vendor_fetch` **báo thành công giả** |
| 3 | sửa đúng tên repo, vẫn trượt | không ai hỏi **nhánh** thật là gì |
| 4 | — | (đang chạy) |

**Báo thành công giả, trong chính công cụ tôi vừa viết để giúp tác tử.** `code.vendor_fetch`
trả `ok` khi **0/26** tệp về được, vì tôi thiết kế nó theo lẽ "thành công một phần vẫn là
thành công, chỉ cần liệt kê tệp hỏng". Nhưng **không có phần nào cả**, và tác tử đi tiếp như
thể đã có driver trong tay. Đó đúng là thứ N6 tồn tại để ngăn — và tôi tái phạm ở chỗ mới
nhất sau khi đã cẩn thận về nó ở mọi chỗ khác. Nay 0 tệp là **E3006**, và nếu **toàn bộ** là
404 thì nói thẳng *"gần như chắc chắn TÊN REPO hoặc NHÁNH sai, không phải từng đường dẫn
sai"*.

**Một công cụ chống-đoán mà nấp sau một lần tìm thì không chặn được gì.** Tôi đặt
`code.vendor_list` là `core=False` — ẩn tới khi tác tử tìm thấy bằng `tool.search`. Nên nó đi
thẳng tới `vendor_fetch` với một tên repo đoán ra. Nay `core=True`.

**Nhánh cũng là một phép đoán, và nó trộn lẫn thật.** Đo trên năm repo tác tử cần:
`stm32f4xx-hal-driver` → `master`, `cmsis-device-f4` → `master`, `cmsis-core` → `master`,
nhưng `32f469idiscovery-bsp` → `main` và `stm32-otm8009a` → `main`. Không ai đoán đúng được
cả năm. Nên công cụ **tự hỏi**: `nhanh_mac_dinh()` hỏi GitHub `default_branch` (có nhớ đệm);
`liet_ke` thử nhánh được nêu trước, hỏng thì hỏi mặc định và thử lại một lần rồi khai
`doi_nhanh=True`; `lay_sdk` **thử một tệp trước** khi xin cả danh sách, vì sai nhánh thì mọi
tệp đều 404 và người gọi chỉ biết sau khi đã xin cả chục tệp.

Một phép đo phụ, để biết bước cuối khó tới đâu: ba mô-đun HAL cần cho màn hình
(`hal_ltdc.c`, `hal_dsi.c`, `hal_sdram.c`) **không gọi hàm libc nào** — nên việc máy thiếu
newlib ít nguy hiểm hơn tôi lo lúc đầu.

#### 17. Biên dịch 30 tệp của hãng: 51 → 13 → 4 lỗi, và ba chỗ EIDE bắt tác tử đoán

Bước cuối — viết chương trình, biên dịch, nạp — mất nhiều vòng, và **phép đo tôi đặt cho nó
không hỏi "lần đầu có dịch sạch không"**. Dịch 30 tệp của ST lần đầu ra 51 lỗi là chuyện
thường của nghề. Câu đáng hỏi là **"mỗi vòng có bớt lỗi đi không"**, vì sửa vòng quanh mới là
thứ đáng báo động. Đo được: **51 → 13 → 4**.

Ba lỗi trong chuỗi ấy là lỗi của EIDE, và cả ba cùng một hình dạng: **hệ thống bắt tác tử
đoán một thứ mà nó có thể hỏi.**

**(a) Một `-I` cho một cây thư mục.** `stm32469i_discovery_lcd.c:58` có
`#include "../../../Utilities/Fonts/fonts.h"` — ba cấp `..` chỉ đúng khi tệp nằm ở
`Drivers/BSP/STM32469I-Discovery/`. Tôi thiết kế `code.vendor_fetch` đổ hết vào **một thư mục
phẳng** cho tiện, và `bien_dich` truyền đúng một `-I`. Hậu quả: người đọc lỗi đi tìm một
`fonts.h` bị thiếu, trong khi tệp ấy **có thật** trong `STM32CubeF4/Utilities/Fonts/`. → `-I`
cho thư mục gốc **và mọi thư mục con có header** (trần 60), để giữ được cây của hãng thì giữ.

**(b) Nhánh.** Repo của ST không thống nhất — đo trên năm repo tác tử cần:
`stm32f4xx-hal-driver`, `cmsis-device-f4`, `cmsis-core` dùng `master`; `32f469idiscovery-bsp`
và `stm32-otm8009a` dùng `main`. Không ai đoán đúng cả năm. → công cụ tự hỏi
`default_branch`, thử nhánh được nêu trước rồi mới đổi, và **khai ra là đã đổi**.

**(c) Thế hệ API của driver.** Bốn lỗi cuối đều là
`'OTM8009A_IO_t' has no member named 'Init'` — `stm32-otm8009a` ở nhánh `main` là **API v2**,
còn BSP `32f469idiscovery-bsp` là **v1** và gọi API cũ. Đây là một vấn đề rất thật của nghề
nhúng, và tác tử không sai: nó chỉ không có cách nào **nhìn thấy** repo ấy có tag `v1.0.7`.
→ `code.vendor_list` khai luôn danh sách tag, kèm câu nhắc rằng driver có nhiều thế hệ API và
phải khớp BSP đang dùng.

Một chi tiết vui về phép đoán tên repo: tác tử viết `stm32f4xx_hal_driver` (gạch dưới) trong
khi tên thật là `stm32f4xx-hal-driver`. Nó **vẫn chạy** — GitHub giữ chuyển hướng cho repo đã
đổi tên. Nên phép đoán tên của nó thật ra đúng; thứ nó không đoán được là **nhánh**, và đó
chính là chỗ công cụ đi hỏi thay nó.

Và một ghi nhận về môi trường: giữa chừng **bo bị rút khỏi máy** (`st-info` thấy 0 bộ nạp,
`/Volumes/DIS_F469NI` biến mất). Phép kiểm "đọc ngược Flash" đỏ với đúng lý do
*"Couldn't find any ST-Link devices"* thay vì im lặng hay báo sai — đó là hành vi đúng.

### Số đo

`1029 ca đơn vị` (+93 so với DEV-277) · `99 công cụ` khi cờ sơ đồ tắt (+8: `doc.fetch`, `target.detect`,
`target.flash`, `target.verify`, `target.log`, `code.vendor_fetch`, `code.vendor_list`,
`asset.image_to_c`), `108` khi bật.

Phiên bo thật (`tools/phien_stm32.py`): bước 1–2 chạy được trên bo đang cắm — tác tử tự tìm ra
công cụ (`tool.search` → `target.detect`), nhận đúng **ST Discovery F469NI**, và **tự nói ra**
rằng mã chip đó suy từ nhãn bộ nạp *"chưa phải là ID chip đọc trực tiếp từ silicon qua SWD"*.

### Còn lại

- Bước 3–10 của phiên (tự tìm tài liệu → trích Fact → viết firmware → nạp → đọc log) đang chạy;
  hạn mức GitHub cần ~17 phút để nạp lại trước khi bước 3 đo được.
- `plan.enter`/`plan.exit` (§B5) vẫn chưa làm.
- `target.verify` / `target.debug` / `target.dangerous` chưa làm — TC030 (breakpoint, thanh ghi)
  và TC035 (RDP/eFuse) cần chúng. TC035 hiện đã được chặn ở tầng S0 nên không có lỗ hổng an
  toàn, chỉ là năng lực còn thiếu.

### [DEV-279] 28/09/2026 · Màn hình đen: ba lần "mọi phép đo đều xanh mà hành vi vẫn sai"

Bối cảnh: firmware hiện logo PTIT + bốn dòng thông tin đã **dịch sạch, nạp đúng từng byte,
`target.verify` khớp hoàn toàn, ảnh nạp 129 780 B ≥ mảng logo 115 200 B**. Chín phép kiểm bằng
mã đều xanh. Anh Công nhìn bo và nói: *"màn hình đen xì"*.

Đây là chỗ tầng NGƯỜI của MDD-40 tồn tại để bắt, và nó bắt được ba lần liên tiếp — mỗi lần lộ
ra một năng lực EIDE còn thiếu. Ba lần ấy chia sẻ đúng một hình dạng: **EIDE đo được rằng mọi
thứ đúng, nhưng không đo được điều đang sai.**

#### Lần 1 — chip kẹt trong ngắt, và EIDE không có cách nào nhìn thấy

`openocd` nói `halted due to debug-request, current mode: **Handler SysTick**`. `SysTick_Handler`
là bí danh của `Default_Handler`, mà `Default_Handler` là `while (1) {}`: `HAL_Init()` bật
SysTick, tick đầu tiên nhảy vào vòng lặp vô hạn, chương trình chết trước khi chạm dòng vẽ.

Không có công cụ nào của EIDE hỏi được câu *"chip đang làm gì"* → thêm **`target.debug`** (R2,
`core=False`): dừng chip, đọc PC/xPSR/MSP và ô nhớ tuỳ ý, rồi cho chạy tiếp. Tác tử tự tìm ra
nó (`tool.search` → `target.debug`), tìm ra lỗi, sửa, nạp lại.

#### Lần 2 — `pc = Default_Handler` là một câu trả lời vòng tròn

Sửa SysTick xong, chip chuyển sang kẹt `Handler HardFault`. Ba chỗ hỏng lộ ra liền nhau:

**(a) Phép đo im lặng trông y hệt phép đo không có gì để nói.** `soi_chip()` gộp cả chuỗi lệnh
openocd vào **một** `-c`. openocd chạy đúng nhưng **không in kết quả `mdw`**, nên `o_nho` rỗng
và không ai biết vì sao. Tách mỗi lệnh một `-c` thì đọc ra ngay
`0xe000ed28: 00020000 40000000`. Khoá bằng test so chính dòng lệnh (`"; " not in ...`).

**(b) Thanh ghi lỗi bị giấu sau một câu đố.** Gặp HardFault mà phải nhớ địa chỉ CFSR mới chẩn
đoán được thì đó là một phép đo có sẵn nhưng không ai lấy. → `soi_chip()` đọc **luôn**
CFSR/HFSR/MMFAR/BFAR và dịch bit thành lời (`_BIT_CFSR`, 17 bit). Đọc được:
`CFSR = 0x00020000` → **INVSTATE** (sai trạng thái Thumb), `HFSR = 0x40000000` → FORCED.

**(c) Manh mối nằm trong payload mà lời văn không nhắc tới thì coi như không có.**
`loi_phan_cung` đã đủ dữ liệu, nhưng `note_vi` vẫn chỉ nói về `SysTick_Handler` — tức chỉ sang
lỗi của **lần trước**. Tác tử đi theo lời văn, không đi theo JSON. → đưa CFSR/HFSR vào `note_vi`.

**(d) Một địa chỉ không tên bắt tác tử đọc cả cây mã để đoán.** Nhận `pc 0x08000db0`, tác tử
gọi **`fs.read` 28 lần**, hết hạn mức 40 lời gọi của lượt và **dừng giữa việc**. Đây là lỗ hổng
năng lực của EIDE, không phải lỗi của tác tử: `arm-none-eabi-addr2line` trả lời cùng câu hỏi
trong 40 ms. → **`giai_ma_dia_chi()`**: địa chỉ → tên hàm + `tệp:dòng`.

**(e) Và phanh cho chính năng lực vừa thêm.** `addr2line` luôn trả về một cái tên nghe thuyết
phục — của bản ELF **trên đĩa**. Đo lần đầu: PC giải mã thành `OTM8009A_Init_Ext`, mà 32 byte
tại đúng địa chỉ đó **trên chip KHÁC tệp vừa dịch** — chip đang chạy bản cũ, và cái tên kia sẽ
dẫn tác tử đi sửa một hàm không liên quan. → **`khop_tai_dia_chi()`** đọc ngược 32 byte tại
đúng PC và trả ba trạng thái: tin được / biết là sai / chưa đo được. Phanh này kiếm được chỗ
của nó ngay lần chạy đầu tiên, không phải phòng xa.

#### Lần 3 — khung ngoại lệ: từ "handler nào" sang "lệnh nào"

Nạp lại đúng bản (hash khớp), chip vẫn HardFault, và `target.debug` chỉ nói được
`pc = Default_Handler` (`startup.c:272`). Đúng, và vô dụng: `HardFault_Handler` là bí danh của
`Default_Handler` nên PC ấy đúng với **mọi** fault, mãi mãi.

Địa chỉ đáng đọc nằm ở nơi khác. Khi vào ngoại lệ, chính CPU đẩy 8 thanh ghi lên ngăn xếp, và
từ thứ 7 là **PC của lệnh đã fault**. → **`giai_khung_ngat()`** + `soi_chip()` tự gọi openocd
lần thứ hai để đọc 8 từ ở MSP (địa chỉ MSP chỉ biết được *sau* khi dừng chip).

Đo trên bo ngay sau khi viết xong:

| số đo | giá trị | nghĩa |
|---|---|---|
| `pc` lúc dừng | `0x08000f24` | `Default_Handler` — vô dụng |
| `pc_fault` (khung) | `0x00000000` | **nhảy tới địa chỉ 0** |
| `lr` (khung) | `0x080006F7` | `OTM8009A_ReadID_Ext` · `otm8009a.c:472` |
| cờ T của xPSR đã đẩy | `0` | không ở trạng thái Thumb — bằng chứng **độc lập** cho INVSTATE |

Tức là: gọi một con trỏ hàm **NULL** từ `otm8009a.c:472`. Chỉ đúng một dòng.

Kết quả: lượt sau tác tử gọi `target.debug` **một lần** rồi `fs.read firmware/otm8009a.c
offset=450` — đúng tệp, đúng vùng, không còn dò 28 lần. Sửa, dịch lại, nạp. Đo lại:

```
1. Thread   pc=0x08001942  HAL_Delay     stm32f4xx_hal.c:401
4. Thread   pc=0x08001924  HAL_GetTick   stm32f4xx_hal.c:326
```

Ra khỏi HardFault, và PC luân phiên giữa `HAL_Delay` ↔ `HAL_GetTick` chứng minh SysTick **có**
tick — `HAL_Delay` sẽ treo mãi nếu tick không tăng. Màn hình thì chỉ mắt anh Công trả lời được.

#### Hai lỗi của chính phép đo, ở hai phía đối nhau

Bài học *"trạng thái thứ ba không được gộp vào hai"* xuất hiện thêm hai lần, và lần này ở cả
hai phía:

* **`_han_muc` làm to hạn mức lên mười lần.** `str(gt).replace(".", "")` biến `"2097152.0"`
  (Fact sinh từ `st-info`) thành `20971520` → trần Flash **20 MB cho chip 2 MB**. Loại lỗi này
  không bao giờ tự kêu: trần quá rộng thì firmware nào cũng "vừa chip", kể cả bản 3 MB không
  nạp được. → **`doc_so()`**: dấu chấm chỉ là phân nhóm nghìn khi nó chia thành **đúng nhóm ba
  chữ số**; và `KB`/`K` của tài liệu chip là 1024, không phải 1000.
* **Nhật ký nói sai về chính thứ nó đang làm chứng.** `_kiem_khung_ngat` tra ký hiệu ở
  `0x080006f7` trong khi công cụ tra `0x080006f6` — lệch đúng **bit Thumb** của LR — nên nhật
  ký in *"không có ký hiệu"* cho đúng cái tên mà tác tử vừa nhận được và dùng đúng.

### Số đo

`1069 ca đơn vị` (+40 so với DEV-278). Không thêm công cụ mới; `target.debug` được bổ sung ba
năng lực (thanh ghi lỗi, tên hàm, khung ngoại lệ) và một phanh (`khop_tai_dia_chi`).

Phiên bo thật: bước 17–20 (`tools/phien_stm32.py --buoc 17..20`). Bước 20 xanh cả hai phép kiểm
mới: *"tác tử đọc thanh ghi lỗi và nhận được bit lỗi cụ thể"*, *"khung ngoại lệ chỉ ra lệnh gây
fault"*.

#### Lần 4 — thứ EIDE thiếu không phải một phép đo nữa, mà là con mắt

Hết HardFault, chương trình chạy (`HAL_Delay` ↔ `HAL_GetTick`), **màn hình vẫn đen**. Câu hỏi
tiếp theo có hai câu trả lời ở hai đầu khác nhau của hệ thống, cách sửa không liên quan gì
nhau: *chương trình vẽ sai, hay nó vẽ đúng mà tấm panel không hiện?* Nhìn vào một màn hình đen
thì không phân biệt được — và cả bốn lượt trước, tác tử lẫn tôi đều đang đoán giữa hai nhánh ấy.

→ Công cụ mới **`target.screen`**: đọc thẳng bộ nhớ khung ảnh của chip qua SWD (`dump_image`,
1,5 MB trong ~15 giây) và ghi ra PNG. Kèm **`doc_cau_hinh_ltdc()`** tự lấy địa chỉ, kích thước
và định dạng từ chính thanh ghi LTDC — bắt gõ tay ba con số ấy thì sai một cái là ảnh đọc ra
lệch hàng và trông y hệt "chương trình vẽ sai", tức là một phép đo **tự sinh ra bằng chứng giả**.

Đọc từ thanh ghi: `LTDC_GCR` bit 0 = 1, `L1CR` bit 0 = 1, `L1CFBAR = 0xC0000000`,
`L1CFBLR >> 16 = 3200` → 800 điểm ARGB8888, `L1CFBLNR = 480` dòng.

Kết quả đọc ra khung ảnh: **200 màu** — trắng 82,8 %, đen 12,2 %, **`#DE2019` 2,1 %** (đúng đỏ
logo PTIT), `#FF0000` 0,8 %, `#000080` 0,8 %. Ảnh hiện logo PTIT và bốn dòng chữ, đặt đúng chỗ.

Tức là: **chương trình vẽ đúng.** Màn hình đen vì đường LTDC → DSI → panel (OTM8009A) hoặc đèn
nền, không phải vì phần vẽ. Bốn lượt trước đi sai nhánh, và không ai biết vì không ai nhìn được.

Hiệu quả đo được trên cùng một tác tử, cùng một câu hỏi:

| lượt | công cụ đã có | số lời gọi | kết quả |
|---|---|---|---|
| 18 | `target.debug` (chỉ PC) | **40** (28 × `fs.read`) | hết hạn mức, dừng giữa việc |
| 20 | + khung ngoại lệ | 23 | mở đúng tệp, đúng vùng |
| 21 | + `target.screen` | **2** | `tool.search` → `target.screen`, kết luận đúng |

Và ảnh ấy lộ thêm hai lỗi chất lượng mà **máy đo được** còn mắt người trước màn hình đen thì
không: **bốn dòng chữ vỡ, glyph chồng lên nhau** (lỗi dựng phông), và **logo có hộp nền đen**
(kênh alpha của PNG bị đổ thành đen khi đổi sang mảng điểm). Cả hai vào danh sách việc.

Một ghi chú về ràng buộc bảo mật: đây **không** phải ảnh chụp màn hình máy tính. Nó đọc bộ nhớ
của con chip trên bàn, không liên quan tới cửa sổ nào đang mở, và không dùng `screencapture` —
lệnh đã hai lần chụp nhầm cửa sổ riêng tư trong dự án này.

#### Lần 5 — "lỗi ở đường LTDC → DSI → panel" vẫn là tên của cả một chuỗi

Tác tử sửa xong hai lỗi mà khung ảnh lộ ra: tải **phông thật của ST** (`font8/12/16/20/24.c`)
nên chữ hết vỡ, và sinh lại logo dạng **ARGB8888** nên hết hộp nền đen. Đọc lại khung ảnh:
1301 màu, chữ sắc nét, logo sạch nền. Màn hình vẫn đen.

`target.screen` nói được "lỗi ở đường LTDC → DSI → panel" — nhưng đó là tên của **bốn mắt
xích**, và bốn mắt ấy hỏng theo bốn cách khác nhau, cho ra **cùng một** màn hình đen.
→ **`doc_duong_hien_thi()`** đi dọc chuỗi và nói đứt ở mắt nào, kèm số và chỗ trong mã cần sửa:

| mắt xích | đo được | |
|---|---|---|
| LTDC bật | `LTDC_GCR = 0xC0002221` | ✓ |
| Lớp 1 bật | `LTDC_L1CR = 0x00000001` | ✓ |
| Host DSI bật | `DSI_CR = 0x00000001` | ✓ |
| Bọc DSI bật (DSIEN) | `DSI_WCR = 0x0000000A` → bit 2 = 0 | ✗ |
| Hiển thị không bị tắt (SHTDN) | `DSI_WCR` bit 1 = 1 | ✗ |
| Panel ra khỏi reset (XRES = PH7) | `GPIOH_ODR` bit 7 = 0 | ✗ |

Chân XRES lấy từ chính mã BSP, không từ trí nhớ: *"reset the LCD by activation of XRES (active
low) connected to PH7"* — và vì nó là số của **riêng từng bo**, nó là tham số, và kết quả luôn
khai mình đang đọc chân nào.

#### Lần 6 — một mẫu PC không phân biệt được ba thứ khác hẳn nhau

Tác tử sửa, nạp; chip **không** fault, nhưng ba mắt cuối vẫn đứt. PC nằm ở `HAL_InitTick` sáu
lần liên tiếp — nghĩa là chương trình chưa chạy tới chỗ bật chúng. Nhưng *tại sao* thì một mẫu
PC đơn lẻ không nói được: **kẹt một lệnh**, **vòng lặp chặt**, và **chip reset lại** (nên lần
nào cũng bị bắt gặp ở đoạn khởi động) đều cho ra cùng một con số.

→ `target.debug` nhận tham số `lay_mau`, cộng với **`doc_nguyen_nhan_reset()`** đọc `RCC_CSR`
để chính con chip khai lý do khởi động gần nhất (IWDG/WWDG cắn? reset phần mềm? bật nguồn?).

Và đây là **lỗi của chính phép đo mới, bắt được ngay khi viết xong**: bản đầu kết luận theo
*số địa chỉ khác nhau*. Sáu mẫu rơi vào **năm** địa chỉ → nó nói *"chương trình đang chạy bình
thường"*. Mà cả năm nằm trong **42 byte** của nhau — một vòng lặp chặt bên trong đúng một hàm.
Thứ phân biệt được là **khoảng trải**, không phải số lượng. Ngưỡng (256 byte) được nói ra trong
kết quả, không giấu trong một câu kết luận.

Kết quả: lượt sau tác tử gọi `tool.search` → `target.debug {lay_mau: 8}` — **hai lời gọi** — và
nhận đúng câu *"8 mẫu rơi vào 4 địa chỉ nhưng chỉ trải 40 byte, hàm `HAL_InitTick`"*, kèm
`RCC_CSR = 0x0E000000` (bật nguồn + NRST + BOR, **không** có chó canh nào cắn).

#### Sổ cái: hai tiến trình cùng ghi — do chính tác tử phát hiện

Giữa lượt, tác tử mở đầu câu trả lời bằng một cảnh báo không ai hỏi nó:

> **Lưu ý toàn vẹn:** Sổ cái ghi nhận bị lệch thứ tự ở dòng 9174 (`seq` ghi là 9156).

Kiểm bằng mã: **4 chỗ lệch**, `seq` tụt lui rồi nhảy lại. Nguyên nhân: `Ledger` khoá bằng
`threading.Lock` — chỉ an toàn **trong một tiến trình** — trong khi app EIDE đang mở dự án và
bộ kịch bản phiên mở **cùng** dự án đó. Mỗi bên đọc `_seq`/`_head` lúc khởi tạo rồi tự đếm
tiếp, nên sổ cái thành hai dãy số chồng nhau và chuỗi hash đứt.

Đó là hỏng đúng cái thuộc tính mà sổ cái tồn tại để có (§F3 "toàn vẹn lịch sử"). Sửa:

* **Khoá liên tiến trình** (`fcntl.flock`) ôm trọn cả việc đọc đuôi lẫn việc ghi. Tính `seq`
  ngoài khoá rồi mới khoá để ghi thì hai tiến trình vẫn tính ra cùng một số — dùng đúng cái
  lỗi mà khoá này sinh ra để chữa.
* **Đọc lại đuôi tệp bên trong khoá**: giá trị nhớ trong bộ nhớ chỉ là gợi ý, đĩa mới là sự
  thật. `_duoi_tep()` duyệt ngược từ cuối theo khối, không đọc cả tệp — sổ cái phiên này đã
  hơn **10 000 dòng**, và đọc lại cả tệp mỗi lần ghi biến việc ghi từ O(1) thành O(n): dự án
  càng làm lâu càng chậm dần, kiểu chậm không ai truy ra được vì nó không hỏng ở đâu cả.
* Đọc lùi phải ở chế độ **nhị phân**. Nhảy tới một vị trí byte bất kỳ rồi đọc ở chế độ văn bản
  cắt đôi một ký tự UTF-8 nhiều byte — và sổ cái này đầy tiếng Việt có dấu, nên lỗi ấy nổ ngay
  ở lần chạy bộ kiểm đầu tiên.
* **`verify()` thôi cáo buộc sai.** Bản trước gộp hai hỏng khác hẳn nhau vào một câu *"Sổ cái
  bị sửa"*. `seq` lặp mà **từng bản ghi vẫn tự khớp hash của chính nó** là tai nạn vận hành,
  không phải ai sửa gì. Một cáo buộc sai ở đúng chỗ người ta phải tin tuyệt đối thì đắt hơn
  nhiều so với im lặng.

Bộ kiểm cho chỗ này chạy **ba tiến trình thật**, mỗi tiến trình ghi 40 sự kiện, rồi đòi
`seq == 1..120` và `verify()` xanh. Phá có chủ ý (bỏ đọc lại đuôi) → đỏ ở đúng bản ghi thứ ba.

#### Lần 7 — phép đo tự chế ra bằng chứng, hai lần trong một hàm

Ba "mắt đứt" ở lần 5 được kiểm lại, và **hai trong ba là lỗi của chính phép đo**:

| mắt | báo cáo sai | sự thật | vì sao sai |
|---|---|---|---|
| DSIEN | ✗ chưa bật | **✓ đang bật** | để ở **bit 2**; `stm32f469xx.h` nói `DSI_WCR_DSIEN_Pos = 3` (bit 2 là `LTDCEN`) |
| XRES panel | ✗ bị giữ reset | **✓ đã ra khỏi reset** | đọc `0x40021C1C` = **`LCKR`**; `GPIOH_ODR` ở offset `0x14` → `0x40021C14` |
| SHTDN | ✗ đang tắt | **✗ đúng là đang tắt** | — |

Cả hai đều là con số **viết theo trí nhớ** thay vì tra từ header của ST. Và hậu quả không
dừng ở một dòng báo cáo sai: tác tử đã đi sửa hai chỗ không hỏng, và tôi đã nói với anh Công
rằng chuỗi đứt ở ba chỗ. **Một bằng chứng sai tệ hơn hẳn không có bằng chứng, vì người ta hành
động theo nó.**

Sửa: mọi hằng số neo vào `stm32f469xx.h` và có bộ kiểm so thẳng từng giá trị
(`GPIOH_ODR == 0x40021C14`, `(COLM, SHTDN, LTDCEN, DSIEN) == (0, 1, 2, 3)`). Đọc thêm **IDR**
bên cạnh ODR: ODR nói chương trình *muốn* gì, IDR nói chân *đang thực sự* ở đâu — với chân
open-drain kéo tải ngoài, hai cái lệch nhau được, và chính cái lệch đó là thông tin.

Còn lại đúng một mắt, và nó thật: `DSI_WCR = 0x0A` → **SHTDN = 1**, bọc DSI đang ở trạng thái
tắt hiển thị. Đáng chú ý: mã của tác tử **đã** xoá bit này ở ba chỗ (`DSI->WCR &= ~DSI_WCR_SHTDN`)
mà đọc lại lúc chạy vẫn thấy 1 — tức có ai đó bật lại nó về sau. Đó là việc tác tử đang truy.

#### Lần 8 — hai vòng `while(1)` giống hệt nhau nếu chỉ nhìn PC

Nạp lại bản khớp rồi lấy mẫu lại: PC không ở `HAL_InitTick` như bản trước báo (tên đó lấy từ
ELF của **bản khác** — phanh `khop_tai_dia_chi` đã cảnh báo đúng) mà ở `HAL_Delay`/`HAL_GetTick`.

Nhưng `main.c` có **hai** vòng `while(1)` gọi `HAL_Delay`, nghĩa ngược hẳn nhau:

```c
if (BSP_LCD_Init() != LCD_OK) { while (1) { HAL_Delay(100); } }   /* màn hình hỏng */
...
while (1) { HAL_Delay(1000); }                                    /* chạy xong xuôi */
```

PC không phân biệt được. LR cũng không: `HAL_Delay` gọi tiếp `HAL_GetTick`, nên LR đã bị ghi
đè bằng một địa chỉ bên trong chính `HAL_Delay`.

→ **`doc_dau_vet_ngan_xep()`**: quét đỉnh ngăn xếp, nhặt những từ vừa nằm trong vùng Flash vừa
có bit 0 = 1 (bit Thumb của địa chỉ trở về). Đo trên bo: **`0x080006DA` = `main` tại
`main.c:79`** — đúng vòng `while(1)` cuối chương trình. Tức là chương trình **đã chạy hết**:
LCD init trả về `LCD_OK`, nó vẽ xong logo và bốn dòng chữ, rồi ngồi ở vòng cuối.

Hàm nói thẳng rằng đây là **phỏng đoán**, không phải chuỗi gọi dựng từ bảng unwind: vài địa
chỉ trong đó là rác còn sót từ các lần gọi trước. Một dấu vết có lẫn rác vẫn hơn hẳn không có
gì — miễn là không ai trình bày nó như sự thật.

Và một chi tiết về giá của phép đo: đọc ngăn xếp tốn **thêm một lần dừng chip**, vì địa chỉ MSP
chỉ biết được *sau* khi dừng. `lay_mau_pc()` vì thế tắt nó đi (`doc_ngan_xep=False`) — lấy tám
mẫu mà dừng mười sáu lần thì phép đo bắt đầu can thiệp vào chính thứ nó đang đo.

#### Lần 9 — mắt đứt cuối cùng cũng là lỗi của phép đo, và tác tử là người tìm ra

Tác tử được giao việc "truy xem ai bật lại bit SHTDN". Nó không đi tìm thủ phạm — nó đi **đọc
cả hai địa chỉ** rồi báo lại:

> Địa chỉ `0x40017000`: `0x0000000A` (đây là thanh ghi cấu hình **`DSI_WCFGR`**, offset `0x400`).
> Địa chỉ `0x40017004`: **`0x00000008`** (đây mới là thanh ghi điều khiển **`DSI_WCR`**, offset `0x404`).
> Như vậy phép đo chuỗi hiển thị của `target.screen` đang đọc nhầm offset `0x400`.

Đúng. `stm32f469xx.h` ghi sẵn offset vào ngay dòng chú thích:

```c
__IO uint32_t WCFGR;   /*!< DSI Wrapper Configuration Register,  Address offset: 0x400 */
__IO uint32_t WCR;     /*!< DSI Wrapper Control Register,        Address offset: 0x404 */
```

Phép đo đọc thanh ghi **cấu hình** rồi giải nghĩa nó như thanh ghi **điều khiển**: `0x0A` ra
thành *"SHTDN = 1, màn đang tắt"*, trong khi `WCR` thật bằng `0x08` — SHTDN = 0.

Chỗ đáng ghi nhất không phải cái lỗi, mà là **cách nó lộ ra**. Lần 7 tôi tự kiểm lại và tìm ra
hai lỗi; lần này tôi đã tin bản vừa sửa, và người đọc ra là tác tử — vì nó có đủ công cụ để
đọc thẳng bộ nhớ và **không mặc định rằng công cụ nói đúng**. Đó chính là tầng mà MDD-40 muốn:
không ai, kể cả EIDE, được miễn đối chiếu.

Một ghi chú về nguyên nhân gốc, vì nó lặp lại ba lần liên tiếp trong đúng một hàm: cả ba hằng
số sai đều là số **tôi tự dựng lại** — hai lần theo trí nhớ, lần thứ ba bằng một bộ phân tích
header viết vội (nó đếm lệch một trường `RESERVED` nên mọi offset sau đó lùi 4 byte). Trong
khi ST đã ghi sẵn từng offset vào chú thích, ở dạng đọc được bằng mắt. **Suy ra một con số
luôn rẻ hơn đi tra nó, và luôn đắt hơn về sau.**

Sau khi sửa, cả sáu mắt đều thông:

```
✓ LTDC bật              LTDC_GCR = 0xC0002221
✓ Lớp 1 bật             LTDC_L1CR = 0x00000001
✓ Host DSI bật          DSI_CR = 0x00000001
✓ Bọc DSI bật (DSIEN)   DSI_WCR(0x40017004) = 0x00000008 → SHTDN=0 DSIEN=1
✓ Hiển thị không bị tắt DSI_WCR(0x40017004) = 0x00000008
✓ Panel ra khỏi reset   ODR(0x40021C14) bit 7 = 1, IDR(0x40021C10) bit 7 = 1
```

Và khung ảnh đọc từ chip (`docs/stm32f469/ket-qua/anh/khung-anh-doc-tu-chip.png`, 1301 màu) hiện
đúng logo PTIT cùng bốn dòng chữ, sắc nét, nền trắng sạch.

#### Lần 10 — sáu mắt "thông suốt" vẫn là điều kiện CẦN, không phải đủ

Anh Công nhìn bo: vẫn đen. Nên sáu mắt xanh ở lần 9 mới chỉ nói được *"LTDC đã bật, bọc DSI
đã bật, panel hết reset"* — toàn những câu về **cấu hình**, không câu nào về **vận hành**.

Thêm năm mắt của tầng liên kết DSI, và một câu chưa ai hỏi suốt mười lượt: **LTDC có ĐANG QUÉT
không**, chứ không chỉ "đã bật". Đọc `LTDC_CPSR` (vị trí điểm ảnh đang quét) **hai lần** rồi so:

| mắt mới | đo được trên bo | |
|---|---|---|
| LTDC đang quét | `CPSR: 0x024B012B → 0x0015008F` | ✓ điểm ảnh đang chảy thật |
| PLL của DSI đã khoá | `DSI_WISR = 0x3300`, PLLLS = 1 | ✓ |
| PHY của DSI bật | `DSI_PCTLR = 0x06`, DEN = CKE = 1 | ✓ |
| Chế độ video | `DSI_MCR = 0`, CMDM = 0 | ✓ |
| Không lỗi đường DSI | `DSI_ISR0 = DSI_ISR1 = 0` | ✓ |

`ISR0` gom lỗi ACK **do chính panel báo về**; nó bằng 0 nghĩa là panel nhận luồng DSI mà không
kêu ca gì. Cộng với `CPSR` đổi giá trị, kết luận thu hẹp lại rất nhiều: **toàn bộ phía STM32
sạch từ đầu tới cuối, lỗi nằm ở chính tấm panel.**

Và vì một bảng toàn dấu ✓ đứng trước một màn hình đen là kiểu báo cáo dạy người ta thôi tin
báo cáo, `doc_duong_hien_thi()` khi thông suốt sẽ **nói thẳng phần chưa đo được nằm ở đâu**:
chuỗi khởi tạo panel, lệnh bật màn / độ sáng, đèn nền, hoặc nhận nhầm biến thể panel.

Tác tử nhận kết luận ấy, tự khoanh tiếp bằng số (`BSP_LCD_Init` phải đã trả `LCD_OK`, vì nếu
không thì mã đã kẹt ở `while(1)` trước khi vẽ — mà khung ảnh **có** hình), rồi chỉ ra bốn lệnh
DCS còn thiếu và bổ sung chúng vào `main.c`:

```c
HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11, 0x00);  /* Sleep Out   */
HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x51, 0xFF);  /* độ sáng max */
HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x53, 0x2C);  /* BCTRL = 1   */
HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29, 0x00);  /* Display On  */
```

#### Một lỗ hổng năng lực khác, đo được: tác tử tốn cả lượt để tự định vị

Giữa hai lượt làm việc, lời nhắc chung chung *"làm tiếp đi bạn"* khiến tác tử tiêu **cả lượt**
cho `ledger.query` → `history.list` → `history.diff` — ba lời gọi, không việc nào xong. Nó
không có cách rẻ nào để trả lời *"lượt trước tôi đang làm gì và đã kết luận gì"*.

Bước kế tiếp trả lại **kết luận của chính nó** thay vì nói "làm tiếp": cùng một tác tử, cùng
một việc, lượt đó đi thẳng vào `fs.grep` → … → `fs.edit` → `build.compile` → `target.flash`.
Đây là một lỗ hổng thật của EIDE (thiếu một bản tóm tắt "tôi đang ở đâu" rẻ tiền), chưa vá.

#### Lần 11 — "ai đặt ra giá trị ấy": N6 nằm trong firmware, sống sót mười lượt

Anh Công hỏi thẳng: *"kiểm tra xem nhận nhầm loại panel không"*. Đọc biến toàn cục
`Lcd_Driver_Type` từ RAM chip → `1` = `LCD_CTRL_OTM8009A`. Nghe như đã dò đúng.

Rồi hỏi tiếp câu mà con số ấy **không** trả lời được — *ai đặt ra nó*:

```c
uint16_t OTM8009A_ReadID(void) { return OTM8009A_ID; }        /* 4 byte mã */
static inline uint16_t NT35510_ReadID(void) { return 0; }
```

Phép "dò loại panel" của BSP **khai báo** kết quả chứ không dò. `Lcd_Driver_Type` là lời của
mã, không phải lời của panel. Hai cái vỏ này là lối tắt tác tử tạo hồi vá HardFault ở lần 2 —
và chúng che mất đúng câu hỏi anh Công vừa đặt, suốt mười lượt, vì **mọi phép đo đều hỏi "giá
trị bằng bao nhiêu" chứ không ai hỏi "ai đặt ra giá trị ấy"**. N6 (không báo đạt giả), lần này
nằm trong firmware thay vì trong EIDE.

→ **`ky_hieu_theo_ten()`**: tên biến/hàm → địa chỉ **và kích thước**, đọc từ `nm -S`. Địa chỉ
để đọc biến toàn cục trên chip đang chạy mà không tra tay. Kích thước để hỏi câu thứ hai: một
hàm 4 byte không thể vừa gửi lệnh DSI vừa đợi panel trả lời.

Kích thước một mình vẫn **chưa đủ**, và bản đầu đã báo động giả ngay: `BSP_LCD_Init` cũng chỉ
6 byte, nhưng thân nó là `movs r0,#1 ; b.w BSP_LCD_InitEx` — một vỏ mỏng, hoàn toàn bình
thường. Thứ phân biệt được nằm trong chính mã máy: **có lệnh nhảy đi đâu không**. `objdump`
cho từng hàm nhỏ, rồi phân ba nhánh: *trả hằng số* / *vỏ mỏng* / *chưa kết luận được* (thiếu
`objdump`).

(Và bản đầu của phép đọc `objdump` lấy `split("\t")[-1]` — đó là cột **toán hạng**, nên từ
khoá lệnh mất sạch và phép dò "có nhảy không" luôn trả lời KHÔNG. Lệnh nằm ở cột thứ ba.)

Tác tử viết lại phép dò cho thật. Đo sau khi nạp — và lần này chip được đối chiếu hash trước
khi tin con số:

| | trước | sau |
|---|---|---|
| `OTM8009A_ReadID` | 4 byte, `movs r0,#64 ; bx lr` | **34 byte**, `bl DSI_IO_ReadCmd(0xDA,…)` |
| `Lcd_Driver_Type` | `1` — do mã khai | `1` — **do panel trả lời ID `0x40`** |

**Trả lời được câu anh Công hỏi: không nhận nhầm.** Và nó chứng minh thêm một thứ quý hơn:
đường DSI **đọc-ghi hai chiều** đang chạy, panel nghe được và nói lại được.

#### Lần 12 — sáu số 0, và cái bẫy quen thuộc ở dạng mới

Tác tử dựng một khối `g_panel_status` đọc các thanh ghi DCS tự khai của panel (`0x0A` power
mode, `0x0C` pixel format, `0x52` brightness, `0x54` ctrl display). Đọc từ RAM chip: **cả sáu
byte bằng 0**. Nghe như panel khai màn của nó đang tắt.

Nhưng byte đầu là `id1`, đọc bằng đúng lệnh `0xDA` vừa trả về `0x40` mấy dòng trước. Cùng một
lệnh, cùng một panel, hai kết quả. Nên sáu số 0 kia là **"lệnh đọc thất bại"**, không phải
"panel trả lời 0" — và mã lúc đó **bỏ mã trả về** của `DSI_IO_ReadCmd`, nên không ai phân biệt
được. Một phép đo im lặng trông y hệt một phép đo có kết quả; đây là lần thứ N của cùng một
hình dạng trong phiên này.

Giao lại, và tác tử làm đúng hai việc: giữ mã trả về từng lần đọc, **và** khởi tạo bộ đệm bằng
**giá trị mồi** `AA BB CC DD EE FF 12 34` để "chưa ai ghi vào" khác được với "đọc ra 0". Kết
quả đo trên chip (hash đã đối chiếu):

```
g_panel_status   = AA BB CC DD EE FF 12 34     ← nguyên mồi: không lần đọc nào ghi được gì
g_panel_read_ret = [1, 1, 1, 1, 1, 1, -1, -1]  ← 1 = LCD_ERROR, cả sáu lần
```

Sáu lệnh đọc DCS đều **thất bại** sau khi chế độ video chạy, trong khi cùng lệnh ấy **thành
công** lúc `LCD_ReadType()` dò panel (trước `HAL_DSI_Start`). Đó là số đo, và nó hẹp hơn hẳn
"màn hình đen".

#### Lần 13 — vá lỗ hổng "tôi đang ở đâu", đo được bằng chính hành vi của tác tử

Lỗ hổng ghi ở lần 10 đã đủ bằng chứng để vá. Triệu chứng: mỗi lượt mới, tác tử tiêu 3–10 lời
gọi cho `ledger.query` / `history.list` / `history.diff` chỉ để nhớ ra mình đang dở việc gì —
có lượt **hết sạch hạn mức 40 lời gọi trước khi làm được việc nào**.

Nguyên nhân nằm ở một dòng: khối `<inventory>` chỉ in

```
Lượt chạy dở: run-256 — <70 ký tự đầu của câu người dùng>
```

Một mã số và một mẩu câu. Tác tử biết **có** lượt dở nhưng không biết dở **ở đâu**, nên nó đi
đào sổ cái — trong khi thông tin ấy đã nằm sẵn ở đó, chỉ là không được đưa lên. Bắt nó trả
tiền hai lần cho cùng một thông tin.

→ Lượt dở giờ mang theo **danh sách công cụ nó vừa gọi**, gộp lần lặp liên tiếp, giữ 12 cái
cuối (nhiều hơn là chép sổ cái vào ngữ cảnh — đúng thứ bảng này sinh ra để khỏi phải làm):

```
Lượt chạy dở: run-256 — sửa màn hình đen giúp tôi
  Lượt đó đã gọi: target.screen → fs.read ×3 → fs.edit → build.compile
  Đừng đi đọc lại sổ cái để nhớ ra việc đang dở — nó ở ngay đây. Và khi sắp hết hạn mức,
  hãy ghi chỗ đang dở vào EIDE.md (memory.note) để lượt sau khỏi phải dò lại.
```

Một ghi nhận đáng nói cho báo cáo: `EIDE.md` — bộ nhớ dài hạn của dự án, tác tử **đọc mỗi
lượt** — vẫn gần như trống sau 34 bước. Cơ chế có sẵn từ đầu; thứ thiếu là một lý do cụ thể để
dùng nó đúng lúc. Đó là bài học chung của cả phiên này: *một năng lực không được nhắc đúng lúc
thì tương đương không có*.

#### Lần 14 — đèn nền tắt hẳn, và lời khai của panel không đứng vững

Anh Công đo giúp thứ máy không đo được: tắt đèn phòng, nhìn sát màn — **đèn nền không sáng,
đen tuyệt đối**. Không phải đen-xám có ánh, mà tối như lúc rút điện.

Số đo ấy thu hẹp mọi thứ: trên bo này đèn nền **do chính OTM8009A điều khiển bằng lệnh DCS**,
không có GPIO riêng (`otm8009a.c` dòng 419/424 — `WRDISBV` đặt độ sáng, `WRCTRLD` bật
*"Brightness Control Block, Display Dimming & BackLight on"*). Nên câu hỏi còn lại: lệnh GHI
có tới panel không? Và không ai biết, vì **mọi mã trả về đều đang bị vứt** — bốn
`HAL_DSI_ShortWrite` trong `main.c`, và cả `OTM8009A_Init(...)` ở `lcd.c:448`.

Tác tử giữ lại từng mã. Đọc từ chip (hash đã đối chiếu):

```
g_dsi_write_ret     = [0, 0, 0, 0]        ← cả bốn lệnh GHI đều thành công
g_otm8009a_init_ret = [0]                 ← chuỗi khởi tạo panel chạy HẾT, trả OK
g_panel_cmd_status  = 40 9C 00 07 4F 2C …
                       │  │        │  └── 0x54 = 0x2C → BCTRL=1, BL=1  (đèn nền BẬT)
                       │  │        └───── 0x52 = 0x4F (độ sáng ≈ 30 %)
                       │  └────────────── 0x0A = 0x9C → booster=1, sleep_out=1, DISPLAY_ON=1
                       └───────────────── 0xDA = 0x40, đúng ID OTM8009A
```

Panel **tự khai** nó đang bật, đèn nền đang bật, độ sáng 30 %. Mắt người: tối tuyệt đối. Hai
lời ấy không thể cùng đúng — nên phải phân định thay vì chọn bên.

Phép thử rẻ nhất: **ghi một giá trị rồi đọc lại đúng thanh ghi đó**.

| | |
|---|---|
| `g_bright_val_written` | `0x88` |
| `g_bright_write_ret` | `0` — ghi báo thành công |
| `g_bright_read_ret` | `0` — đọc báo thành công |
| `g_bright_after` | **`0x00`** — không phải `0x88` |

Và cùng thanh ghi độ sáng ấy, ba lần chạy cho **ba giá trị khác nhau**: `0x4F` → `0x2A` →
`0x00`. **Đường đọc DCS trả về rác** — mã trả về nói "thành công" trong khi dữ liệu là nhiễu.

Hệ quả cho cả chuỗi lập luận: mọi câu dạng *"panel khai nó đang sáng"* đều dựng trên số liệu
ấy, nên chúng **không đứng vững** — kể cả `0x9C` nghe rất thuyết phục. Đây là lần thứ ba trong
phiên mà một mã trả về `ok` đi kèm dữ liệu vô nghĩa (trước đó: `code.vendor_fetch` trả `ok`
với 0/26 tệp; `soi_chip` gộp `-c` nên `mdw` im lặng). Cùng một hình dạng: **`ok` nói về lời
gọi, không nói về kết quả.**

Chốt lại phần máy đo được, tất cả đều đã xanh và lặp lại được:

- khung ảnh trong SDRAM có đúng logo + bốn dòng chữ;
- LTDC **đang quét** (`CPSR` đổi giữa hai lần đọc);
- PLL DSI đã khoá, PHY bật, chế độ video, `ISR0 = ISR1 = 0`;
- mọi lệnh ghi DCS trả `HAL_OK`, `OTM8009A_Init` trả OK;
- panel trả lời đúng ID `0x40` ở lần đọc trước khi vào chế độ video.

Thứ duy nhất không xanh là **ánh sáng thật**. Với chừng ấy sở cứ, nghi ngờ chuyển sang phía
phần cứng, và hai câu hỏi rẻ nhất cần anh Công trả lời trước khi đốt thêm lượt firmware: bo
này **đã từng hiện gì chưa** (bản demo của ST lúc mới cắm), và **cáp mềm của module LCD có
cắm chắc không**.

#### Lần 15 — bo TỪNG CHẠY ĐÚNG, và điều đó cho một bản đối chứng

Anh Công trả lời: *"Board trước khi bạn nạp code mới thì hoạt động bình thường mà. Giao diện
hiển thị nhiều ứng dụng có thể touch vào để điều khiển."*

Panel, đèn nền, cáp mềm — **tất cả đều tốt**. Nghi ngờ phần cứng ở lần 14 là sai hướng, và
tôi đã nói điều đó với tác tử thay vì lặng lẽ đổi đề.

Quan trọng hơn: nó cho một **bản đối chứng**. Hai tệp `stm32469i_discovery_lcd.c` và
`otm8009a.c` đã bị sửa nhiều lần suốt mười mấy lượt — để qua HardFault, để qua lỗi biên dịch,
để thêm cái này cái kia. Mỗi chỗ lệch so với bản gốc của ST là một nghi phạm, và danh sách ấy
**hữu hạn**. Giao việc: lấy bản gốc về, đối chiếu từng chỗ, mỗi chỗ trả lời hai câu — *vì sao
nó được sửa* và *nó có thể làm màn không sáng không*. Chưa sửa vội.

#### Lần 16 — gốc rễ: một lớp bọc vứt mất byte dữ liệu của ~50 lệnh

Tác tử trình ra nghi phạm số 1, và kiểm chứng độc lập cho thấy **nó đúng**:

```c
/* BSP của ST — NbrParams <= 1 nghĩa là gói ngắn 2 byte: lệnh + GIÁ TRỊ */
void DSI_IO_WriteCmd(uint32_t NbrParams, uint8_t *pParams) {
  if (NbrParams <= 1)
    HAL_DSI_ShortWrite(&hdsi_eval, ..., pParams[0], pParams[1]);   /* pParams[1] = giá trị */
  ...
}

/* Driver của ST gọi với Length = 0, giá trị nằm trong pData */
otm8009a_write_reg(&pObj->Ctx, 0xFF, &short_reg_data[1], 0);

/* Lớp bọc tự viết — nhánh Length == 0 */
else { buf[1] = 0; DSI_IO_WriteCmd(0, buf); }      /* ← VỨT pData[0] */
```

Quy ước của driver OTM8009A đời cũ: `Length = 0` **không** có nghĩa "không có dữ liệu", mà là
"gói ngắn một byte dữ liệu, dữ liệu ở `pData`". Lớp bọc hiểu nhầm thành "không có gì để gửi".

Hệ quả: **khoảng 50 lệnh ghi thanh ghi một byte trong cả chuỗi khởi tạo OTM8009A đều ghi
`0x00`** — mở khoá CMD2, chỉnh bơm nguồn (`SD_PCH_CTRL`), gamma, tất cả. Panel không dựng được
mạch nguồn nội của nó, nên **panel và đèn nền cùng chết**, trong khi nó vẫn đủ sống để trả lời
lệnh đọc ID.

Và nó giải thích nốt hai thứ đã làm cả tôi lẫn tác tử lạc hướng nhiều lượt:

* **`g_otm8009a_init_ret = 0` chưa bao giờ có nghĩa.** `bsp_otm8009a_write` `return 0` vô điều
  kiện, còn `DSI_IO_WriteCmd` là `void`. Lần thứ tư trong phiên cùng một hình dạng: **`ok` nói
  về lời gọi, không nói về kết quả.**
* **Lời khai "panel đang sáng" ở lần 14** dựng trên một panel chưa hề được cấu hình — nên
  `0x9C` nghe thuyết phục ấy là rác, đúng như phép thử ghi-rồi-đọc-lại đã chỉ ra.

Tác tử sửa: `buf[1] = (pData != NULL) ? pData[0] : 0;`, và cho `bsp_otm8009a_write` trả về mã
thật thay vì `return 0` cứng.

**Và phép kiểm của tôi báo ĐỎ cho bản sửa đúng ấy** — vì nó tìm đúng chuỗi `buf[1] = pData[0]`,
không khớp dạng có toán tử ba ngôi. Một phép kiểm chỉ nhận ra đúng lời giải mà chính nó nghĩ ra
thì không đo gì cả. Sửa thành: bắt **ý** (vế phải có nhắc `pData` không), không bắt một cách
viết.

Đo sau khi nạp: `DSI_ISR1` bit 7 (`LPWRE`) bật — lần đầu tiên đường DSI **báo có chuyện xảy
ra**, thay vì im lặng như suốt mười mấy lượt trước, khi mọi lệnh đều là `0x00` nên panel chẳng
phản ứng gì.

#### Lần 17 — **MÀN HÌNH ĐÃ SÁNG**, và gốc rễ là một quy ước không ai viết ra

> *"Lên rồi bạn ơi. Đẹp quá"* — anh Công, 28/09/2026.

Logo PTIT và bốn dòng thông tin hiện trên màn 800×480 của bo STM32F469I-DISCO. Ảnh khung đọc
từ chính SDRAM lúc màn đang sáng: `docs/stm32f469/ket-qua/anh/KHUNG-ANH-KHI-MAN-HINH-DA-SANG.png`
(1319 màu, `#FFFFFF` nền, `#DE2219` đỏ PTIT, `#000080` xanh tiêu đề).

**Gốc rễ, viết gọn một câu:** lớp bọc nối driver OTM8009A (API v2) sang hàm `DSI_IO_WriteCmd`
của BSP (API v1) hiểu sai quy ước đóng gói của cả hai loại gói DSI.

| | bố cục `DSI_IO_WriteCmd` đòi | lớp bọc dựng | hệ quả |
|---|---|---|---|
| gói **ngắn** (`Length == 0`) | lệnh + **một byte dữ liệu** (P1) | vứt dữ liệu, gửi `0x00` | ~50 lệnh ghi thanh ghi đều ghi `0x00` |
| gói **dài** (`Length > 0`) | `{dữ liệu…, LỆNH}` | `{LỆNH, dữ liệu…}` | lệnh mở khoá CMD2 `0xFF {0x80,0x09,0x01}` gửi đi thành lệnh `0x01` |

Không mở được CMD2 thì panel **bỏ qua toàn bộ** cấu hình phía sau — kể cả bơm nguồn nội và
điều khiển đèn nền. Panel vẫn đủ sống để trả lời lệnh đọc ID, nhưng không sáng.

Và cả hai lỗi đều **im lặng**: `HAL_DSI_ShortWrite`/`LongWrite` trả `HAL_OK` vì chúng chỉ nhận
gói vào hàng đợi, không biết gì về việc panel có hiểu hay không. Đo được: `cmd_count = 101`,
`first_err_ret = 0` — một trăm lẻ một lệnh "thành công" trong khi không lệnh nào tới đích.

**Lần thứ năm trong phiên, cùng một hình dạng: `ok` nói về LỜI GỌI, không nói về KẾT QUẢ.**
Bốn lần trước: `code.vendor_fetch` trả `ok` với 0/26 tệp · `soi_chip` gộp `-c` nên `mdw` im
lặng · `bsp_otm8009a_write` `return 0` cứng · `g_otm8009a_init_ret = 0` vô nghĩa. Đây là bài
học trung tâm của cả phiên, và nó không phải bài học về DSI.

Một ghi nhận nữa: sửa xong nhánh gói dài, tác tử **làm hỏng lại nhánh gói ngắn** (`(NbrParams
== 0) ? P0 : P1`) — đúng cái lỗi vừa vá hai lượt trước, sống lại ở chỗ khác. Vì quy ước
*"`Length == 0` nghĩa là một byte dữ liệu"* không được viết ra ở đâu cả. Sau khi được chỉ ra,
tác tử ghi nó vào `EIDE.md` bằng `memory.note` — **lần đầu trong cả phiên bộ nhớ dài hạn được
dùng đúng việc**, và đúng cho thứ đáng ghi nhất.

#### Tổng kết quãng "màn hình đen": 17 lần, 11 năng lực mới

Từ lúc anh Công nói *"màn hình đen xì"* tới lúc *"lên rồi"*, EIDE được bổ sung:

| năng lực | trả lời câu hỏi nào |
|---|---|
| `target.debug` | chip đang làm gì |
| đọc CFSR/HFSR + giải 17 bit | fault gì |
| khung ngoại lệ | **lệnh nào** fault (không phải handler nào) |
| `giai_ma_dia_chi` | địa chỉ → tên hàm + tệp:dòng |
| `khop_tai_dia_chi` | tên hàm ấy có nói về mã ĐANG CHẠY không |
| dấu vết ngăn xếp | ai gọi tới đây |
| `lay_mau_pc` + `RCC_CSR` | kẹt / vòng lặp / reset lại |
| `target.screen` | chip đã VẼ được gì (đọc framebuffer → PNG) |
| `doc_duong_hien_thi` | chuỗi 11 mắt đứt ở đâu |
| `ky_hieu_theo_ten` | biến toàn cục + **hàm nào chỉ trả hằng số** |
| lượt dở tự khai | tác tử đang dở việc gì |

Và ba lỗi của chính phép đo, mỗi lỗi **tự chế ra một bằng chứng sai**: `GPIOH_ODR` đọc nhầm
sang `LCKR` · `DSIEN` để bit 2 thay vì 3 · `DSI_WCR` đọc nhầm sang `WCFGR` (lỗi này do **tác
tử** tìm ra, không phải tôi). Cả ba đều là con số tự dựng lại thay vì tra từ header của ST.

### Còn lại

- Khôi phục bản demo gốc của ST cho bo, nếu anh Công muốn (ta đã ghi đè lên nó).
- Tóm tắt "tôi đang ở đâu" đã vá; `plan.enter`/`plan.exit` (§B5) vẫn chưa làm.
- Cần anh Công nhìn bo trong phòng tối: **đèn nền có sáng không** (màn đen-xám có ánh so với
  đen tuyệt đối). Đó là phép đo duy nhất còn lại mà máy không làm được, và nó chia đôi phần
  việc còn lại: đèn nền sáng → dữ liệu điểm ảnh không tới panel; đèn nền tắt → đường nguồn /
  độ sáng.
- Tóm tắt "tôi đang ở đâu" cho tác tử giữa hai lượt — lỗ hổng đo được ở trên, chưa vá. Phần vẽ đã chứng minh là đúng bằng số.
- Chữ vỡ (dựng phông) và hộp nền đen của logo (alpha) — hai lỗi do `target.screen` lộ ra.
- `plan.enter`/`plan.exit` (§B5) vẫn chưa làm.

### [DEV-280] 28/09/2026 · Plan mode — người dùng thấy CÁCH LÀM trước khi tác tử tiêu lời gọi

Mục cuối cùng còn trống của MDD-40 (§B5). Anh Công: *"plan mode rất quan trọng"*.

Lý do làm nó bây giờ không phải vì nó còn trong danh sách, mà vì phiên bo STM32F469 vừa rồi
đo ra đúng những con số nó sinh ra để chặn:

| số đo | nghĩa |
|---|---|
| 402 lượt · **1078 lời gọi** | quy mô một việc "hiện logo lên màn" |
| `fs.read` 298 + `fs.grep` 210 + `fs.glob` 72 = **580 (54 %)** | tác tử dò đường bằng cách đọc, và người dùng chỉ thấy kết quả **sau khi** số lời gọi ấy đã tiêu xong |
| `ledger.query` 82 + `history.diff` 21 | tự định vị giữa hai lượt |
| có lượt tiêu trọn **40/40** hạn mức | rồi dừng giữa việc, không ai biết trước nó định làm gì |

Và hai sự cố mà plan mode nhắm đúng vào: tác tử **vá một đầu rồi làm hỏng đầu kia** (gói DSI
dài/ngắn) vì không có bước nào bắt liệt kê "chỗ này còn chạm tới đâu"; và một giả định sai của
**tôi** — *"có thể panel hỏng"* — tốn hai lượt, trong khi anh Công biết ngay bo từng chạy tốt.
Giả định nằm trên giấy thì bị bác trong ba giây.

#### Luồng

```
plan.enter  → khoá mọi công cụ GHI; tác tử còn đọc, đo, hỏi
(tìm hiểu)
plan.exit   → kiểm bằng mã → tính plan.big → thẻ G-SCOPE nếu lớn
(người duyệt)
→ kế hoạch thành hiện vật `plan:current`, hiện ở <pending> mỗi lượt
→ Stop hook đối chiếu công cụ đã gọi với công cụ trong kế hoạch
```

#### Bốn quyết định, và lý do của từng cái

**1. Khoá công cụ ghi lấy từ HỢP ĐỒNG, không từ danh sách tên.** `writes_artefact` /
`risk >= R3` là thứ mỗi công cụ tự khai. Một danh sách tên phải nhớ cập nhật, và cái quên cập
nhật sẽ đúng là cái lọt qua. Chặn ở `_one_tool` **trước cả hook và policy**, vì đây là câu hỏi
về *chế độ đang ở*, không phải về *quyền với thao tác này* — trộn hai thứ vào `policy.yaml`
thì mỗi công cụ mới phải nhớ thêm một dòng luật.

**2. `plan.big` tính bằng MÃ, không hỏi mô hình.** Để tác tử tự khai việc của mình có lớn
không thì nó sẽ khai "nhỏ" đúng vào lúc nó đang định làm việc lớn — không phải vì gian, mà vì
lúc ấy nó đang tập trung vào việc chứ không vào việc phân loại việc. Ba dấu hiệu, mỗi cái đủ
một mình: ≥ 5 bước · có bước chạm cổng · có bước từ R3.

**3. Kế hoạch là HIỆN VẬT, không phải một câu trong hội thoại.** Nén ngữ cảnh sẽ ăn mất một
câu; hiện vật thì còn, và Stop hook đối chiếu được với nó.

**4. Stop hook làm độ lệch NHÌN THẤY ĐƯỢC, không phạt.** Đi thêm việc ngoài kế hoạch thường là
dấu hiệu kế hoạch thiếu chứ không phải tác tử sai. Một hook phạt sẽ dạy tác tử viết kế hoạch
thật rộng cho an toàn — tức là phá đúng thứ mà plan mode sinh ra để có.

Và hai phép kiểm nhỏ mà đắt nếu thiếu: **tên công cụ trong kế hoạch phải có thật** (kế hoạch
nêu công cụ không tồn tại đọc vẫn xuôi tai, người dùng vẫn duyệt, và chỉ hỏng lúc chạy — khi
đó thứ đã duyệt không còn là thứ đang chạy); và **mỗi bước phải nói để lại hiện vật gì** (bước
không để lại gì thì sau không ai kiểm được nó đã làm hay chưa). `plan.step_done` cũng đòi hiện
vật: một bước "xong" mà không để lại gì thì dấu tích ấy chỉ nói rằng *tác tử tin là* nó xong —
đúng thứ N6 cấm.

Một chi tiết dễ hụt: cổng được duyệt thì `plan.exit` **chạy lại y hệt lần trước**, nên nó
không có cách nào tự biết lần này nó chạy sau một cái gật đầu. Dấu `da_duyet` vì thế đóng ở
`_resolve_gate`. Thiếu nó thì kế hoạch kẹt mãi ở `cho_duyet` và người dùng bấm Duyệt xong lại
thấy tác tử nói nó vẫn đang chờ duyệt.

`memory.note` **không** bị khoá trong lúc soạn: khoá nó nghĩa là cấm tác tử ghi lại đúng thứ
nó vừa học được để soạn kế hoạch ấy.

### Số đo

`1145 ca đơn vị` (+24). Bốn công cụ mới: `plan.enter`, `plan.exit`, `plan.step_done`,
`plan.cancel`. Phá có chủ ý (bỏ dòng gọi khoá) → ca `test_LOI_chan_cong_cu_ghi…` đỏ đúng chỗ.

### Còn lại

- Verifier chạy cho lời tuyên "đạt" của **chính tác tử chính** (hiện 0/402 lượt).
- `tool.propose`: tác tử tự thấy thiếu năng lực và **tự viết công cụ mới**.

### [DEV-281] 28/09/2026 · Tác tử tự phát hiện cái sai của chính mình

Anh Công, sau phiên bo STM32F469: *"Agent không tự động phát hiện được sai mà bạn phải phát
hiện."* Đúng, và sổ cái của phiên ấy chỉ ra **vì sao** — không phải vì thiếu cơ chế.

#### Cái van có sẵn, nhưng ống dẫn không đi qua nó

`src/eide/subagent.py` đã có `verifier`, và nó được thiết kế rất kỹ: chỉ có công cụ **đọc**,
và **cố ý không cho biết đề bài** — *"cho nó đọc đề bài là mời nó suy ra kết luận mong đợi rồi
đi tìm cách biện minh"*. Nhưng:

```python
CAN_KIEM_CHUNG = ("firmware", "sim-runner")   # chỉ nổ khi một SUBAGENT tuyên đạt
```

Tác tử chính làm hết mọi việc trong lượt của nó. Đo trên sổ cái: **402 lượt, 1078 lời gọi,
0 lần gọi subagent** ⇒ verifier chạy **0 lần**. Lời tuyên "xong" của tác tử chính — thứ người
dùng thật sự đọc — chưa bao giờ bị ai kiểm.

→ Hook `tu_kiem_khi_tuyen_dat`: tuyên "đạt" **và** lượt này có ghi hiện vật → `another_round`
kèm lệnh chạy verifier với **bằng chứng**, không phải kết luận.

Điều kiện thứ hai quan trọng ngang điều kiện thứ nhất. Một câu *"xong rồi"* sau một lượt thuần
đọc thường là **trả lời một câu hỏi**, không phải tuyên bố một việc đã làm — bắt nó kiểm chứng
là dựng thủ tục quanh một cuộc trò chuyện. Và chỉ nổ một lần mỗi lượt: vòng thứ hai là vòng
tác tử đang *trả lời chính lời nhắc này*.

#### `ok` nói về LỜI GỌI, không nói về KẾT QUẢ

Hình dạng lỗi lặp **năm lần** trong một phiên, ở năm tầng: `code.vendor_fetch` ok với 0/26
tệp · `soi_chip` gộp `-c` nên `mdw` im lặng · `bsp_otm8009a_write` `return 0` cứng ·
`g_otm8009a_init_ret = 0` vô nghĩa · `HAL_DSI_ShortWrite` trả `HAL_OK` cho 101 lệnh không tới
đích.

→ `eide/ket_qua.py`: sau mỗi lời gọi **thành công**, nếu lời gọi **liệt kê đích danh** một tập
thứ cần lấy mà kết quả trả về **rỗng**, lõi chèn một lời nhắc. Bắt được hai ca đầu (công cụ
EIDE); ba ca sau nằm trong firmware người dùng, và thứ bắt chúng là verifier đọc bằng chứng.

**Phần khó của bộ dò này là chỗ nó phải IM LẶNG**, và bản đầu đã sai đúng ở đó — ba lần:

| lỗi | hậu quả | sửa |
|---|---|---|
| có `pattern`/`query` trong danh sách "xin" | `fs.glob` không khớp tệp nào bị gắn cờ — mà một phép TÌM không thấy gì **là** câu trả lời | bỏ; chỉ nhận danh sách liệt kê đích danh |
| `bool` là con của `int` | `dat: True` được tính là "số > 0" và **dập tắt cảnh báo** ở đúng ca `soi_chip` | loại `bool` tường minh |
| xét mọi số trong kết quả | `so_hong: 26` là số thứ **hỏng** — nó xác nhận chứ không bác bỏ — lại dập tắt cảnh báo | chỉ xét các khoá **đếm tiến triển** |

Sáu ca đối chứng đều đúng sau khi sửa. Ranh giới ấy không phải chi tiết phụ: `0` rất thường là
câu trả lời ĐÚNG và là tin tốt (*0 lỗi biên dịch*), nên một bộ dò kêu ở mọi số 0 sẽ thành máy
báo động giả trong một buổi chiều — và báo động giả dạy người ta bỏ qua cảnh báo, đắt hơn hẳn
việc không có nó.

### Số đo

`1164 ca đơn vị` (+19). Gỡ dây nối trong lõi → ca `test_LOI_that_su_nhac…` đỏ đúng chỗ.

### Còn lại

- `tool.propose`: tác tử tự thấy thiếu năng lực và **tự viết công cụ mới** (anh Công đã chọn
  hướng "tự viết tool thật, qua cổng").

### [DEV-282] 28/09/2026 · Tác tử tự bù năng lực cho chính mình

Anh Công: *"Agent cũng cần tự thấy thiếu công cụ để viết thêm (tự viết thêm năng lực)."* Được
trình ba hướng — chỉ đề xuất / viết script rời / tự viết tool thật qua cổng — anh chọn hướng
đi xa nhất.

#### Số đo làm chặng này ra đời

Tác tử có `pc = 0x08000db0` và cần biết hàm nào nằm ở đó. Nó gọi **`fs.read` 28 lần**, hết
hạn mức 40 lời gọi của lượt, rồi dừng giữa việc mà vẫn chưa chắc. `arm-none-eabi-addr2line`
trả lời cùng câu hỏi trong **40 ms**.

Nó không thiếu thông minh. Nó thiếu **cái miệng**: `tool.install` chỉ cài CLI ngoài, và không
có đường nào để nói *"EIDE thiếu một năng lực"*. Toàn phiên, **580/1078 lời gọi (54 %)** là
`fs.read`/`fs.grep`/`fs.glob`.

#### Luồng

```
tool.propose → kiểm đề xuất bằng mã → thẻ G-TOOL (R3)
(người duyệt)
→ tác tử viết .eide/cong-cu/<ten>.py và .eide/cong-cu/test_<ten>.py bằng fs.write
tool.reload  → CHẠY bộ kiểm; XANH thì nạp và đăng ký, ĐỎ thì từ chối kèm đuôi pytest
```

Và phần **"tự thấy"**: lời nhắc chống quay vòng — thứ nổ đúng lúc tác tử đang cày — nay có
lựa chọn thứ tư: *"cày tay nhiều thế này thường là dấu hiệu THIẾU CÔNG CỤ, không phải thiếu
cố gắng — xin tự viết nó bằng `tool.propose`, kèm chính số đo vừa rồi làm lý do."* Ba lựa
chọn cũ đều dẫn nó quay lại cày tay.

#### Bốn hàng rào, vì đây là mã chạy trong chính tiến trình EIDE

1. **Đề xuất phải nói được gì.** `vi_sao` bắt buộc mang **số đo**, không mang cảm giác —
   *"tôi thấy hơi chậm"* không đủ để ai quyết, *"tôi gọi `fs.read` 28 lần rồi hết hạn mức"*
   thì đủ. `test` phải nói sẽ kiểm ca nào, **kể cả ca nó phải im lặng**.
2. **Chỉ ghi vào `.eide/cong-cu/` của dự án.** Ranh giới này không do tôi nghĩ ra — **sandbox
   quyết hộ**: `fs.write` bị chặn ngoài thư mục dự án (TC070), nên bản thiết kế đầu (ghi vào
   `src/eide/tools/them/`) sẽ hỏng ngay lời gọi đầu tiên. Bắt được trước khi viết test, và nó
   hoá ra là thiết kế đúng hơn: công cụ tự viết là của **dự án**, mã nguồn EIDE không bị
   chạm, và hoàn tác một changeset là đủ để gỡ sạch.
3. **Bộ kiểm phải XANH mới được đăng ký.** Hàng rào quan trọng nhất. Không có nó thì ta vừa
   cho tác tử một cách rất nhanh để tự tin vào một thứ sai. Chạy trong tiến trình riêng —
   một bộ kiểm hỏng không được kéo theo cả EIDE. Test đỏ → `E7005`, kèm câu *"đừng sửa test
   cho vừa mã: N6 — không đổi tiêu chí để đạt."*
4. **Đăng ký đúng cái tên đã duyệt.** Người dùng duyệt một cái tên cụ thể; nạp xong mà
   registry mọc ra `code.khac_han` là lách cổng → `E7007`.

Khung mã trả về cho tác tử mang sẵn ba bài học đã trả giá, đặt ngay chỗ nó đang viết: trả về
**số đo** chứ đừng chỉ trả `ok` · *"không đo được"* phải khác *"đo được và bằng 0"* · hằng số
phần cứng **tra** từ header của hãng, đừng dựng lại từ trí nhớ.

#### Ca kiểm đáng kể nhất

`test_TRON_VONG_DOI_de_xuat_viet_kiem_nap_dung_duoc`: tác tử đề xuất → viết mã + test → nạp →
và **gọi được công cụ nó tự viết ngay trong cùng lượt**, không phải khởi động lại EIDE. Từng
mảnh xanh riêng không chứng minh được cái vòng khép lại, mà cái vòng khép lại mới là thứ được
yêu cầu.

### Số đo

`1180 ca đơn vị` (+16). Hai công cụ mới: `tool.propose` (R3, cổng G-TOOL), `tool.reload`.

### Còn lại

- MDD-40 không còn mục nào trống.
- Khôi phục bản demo gốc của ST cho bo STM32F469, nếu anh Công muốn.

### [DEV-283] 28/09/2026 · Dự án thứ hai trên cùng bo: FreeRTOS — ba năng lực mới chạy thật

Anh Công mở một dự án MỚI trên cùng bo STM32F469I-DISCO (dự án G7 để nguyên), đầu vào là
thông tin bo đã đo được ở phiên trước, việc là *"tìm bản FreeRTOS tương thích và viết ứng dụng
biên dịch và cài lên phần cứng"*. Đây là lần đầu plan mode, verifier cho tác tử chính, và
`tool.propose` chạy trên một việc thật — và kịch bản **cố ý không bảo tác tử dùng cái nào**.
Bảo trước thì phép đo mất nghĩa: ta sẽ chỉ biết nó làm theo lời.

#### Plan mode tự nổ, không ai bảo

Nhận việc, tác tử đi khảo sát (`passport.isa` → `code.vendor_list` → `env.check` →
`target.detect`) rồi **tự gọi `plan.enter`**, và nộp kế hoạch **8 bước** — mỗi bước có đủ
*việc · công cụ · hiện vật · cổng · chi phí*, kèm **3 giả định** và **3 mục ngoài phạm vi**
(nói rõ nó cố ý *không* đụng tới LCD/DSI, Ethernet/USB, và option bytes). Thẻ **G-SCOPE** hiện
ra, anh Công duyệt.

Tiến độ được đánh dấu bằng `plan.step_done` kèm hiện vật: 3/8 → 6/8 qua hai lượt. Đây đúng là
thứ phiên trước không có — ở đó mỗi lượt mới tác tử tiêu 3–10 lời gọi chỉ để tự định vị.

#### Bộ nhớ dài hạn được dùng ngay từ lượt đầu

Phiên trước, `EIDE.md` gần như trống sau 34 bước. Lần này, ngay lượt hai tác tử gọi
`memory.note` ×3 và **9/10 mốc** của bo có trong `EIDE.md`. Một lời gọi bị từ chối `E4003` vì
nó thử ghi vào mục **"Đừng"** — ranh giới của người (§7.1). Đó là thiết kế chạy đúng, không
phải bug: nó nhận gợi ý và ghi sang mục khác.

#### Bug của EIDE, lộ ra đúng chỗ rẽ nhánh

`code.vendor_list("FreeRTOS/FreeRTOS-Kernel")` trả về:

> *"hết hạn mức GitHub, còn 222 s — **có thể repo không tồn tại**."*

Hai vế dẫn tới hai hành động **ngược nhau**: một cái bảo *"đợi vài phút rồi gọi lại đúng repo
này"*, cái kia bảo *"tìm chỗ khác"*. Tác tử tin vế sau, và bước 2 trong kế hoạch của nó thành
**"tạo các tệp mã nguồn FreeRTOS Kernel bằng `fs.write`"** — tức tự gõ lại nhân của một dự án
có thật. Thứ tệ nhất có thể làm với mã của hãng.

Sửa: `HetHanMuc` có nhánh riêng trong `liet_ke()`, và công cụ trả **`E3003`** (không phải
`E3005`) với `blame="external"` và lời khuyên **ngược lại**: *gọi lại đúng repo ấy sau N phút,
đừng đổi repo, và tuyệt đối đừng tự viết lại mã của hãng bằng tay — mã ấy là thứ phải LẤY,
không phải thứ để nhớ lại.* Lại đúng bài học cũ ở dạng mới: **một trạng thái thứ ba bị gộp
vào hai**, và lần này cái giá là hướng đi của cả một kế hoạch.

Sau khi sửa và hạn mức hồi, tác tử lấy mã thật về: `tasks.c`, `queue.c`, `list.c`, `heap_4.c`,
`FreeRTOSConfig.h`, và `port.c` đúng bản **`portable/GCC/ARM_CM4F/`** — "tương thích" trở
thành một thứ **đo được** (port khớp Cortex-M4F có FPU) thay vì một lời tuyên bố.

#### Đo trên phần cứng thật

| phép đo | kết quả |
|---|---|
| chip chứa đúng bản vừa dịch | ✓ (đọc ngược Flash, 5 300 byte) |
| PC lấy mẫu 6 lần | `prvIdleTask` (`tasks.c:5934`) và `prvCheckTasksWaitingTermination` (`tasks.c:6208`) |
| chân LED đổi trạng thái | PG6 và PD4 **có đổi** giữa các lần đọc |

PC rơi vào đúng phần trong của bộ lập lịch FreeRTOS là bằng chứng mạnh nhất có thể lấy được
bằng máy: nhân **đã khởi động và đang chạy**, không phải một vòng lặp giả vờ. Phần còn lại —
nhịp nháy có đúng như thiết kế không — thuộc tầng NGƯỜI.

### Số đo

`1182 ca đơn vị` (+2, cho chỗ phân biệt hết-hạn-mức). Dự án G7 cũ **không bị chạm tới**, có
hàng rào kiểm bằng mã trong `tools/phien_freertos.py`.

### Còn lại

- Anh Công nhìn bo xác nhận nhịp nháy của các tác vụ.
- `tool.propose` chưa được tác tử dùng lần nào trong phiên này — chưa gặp việc nào bí tới mức
  cần. Ghi lại để biết cơ chế có được tìm tới hay không, không phải để ép.

### [DEV-284] 28/09/2026 · Verifier lần đầu chạy thật — và bốn lý do nó đã không chạy

Anh Công xác nhận bằng mắt: **LED nháy**, các tác vụ FreeRTOS chạy độc lập. Đây là lúc tác tử
tuyên việc xong, tức là đúng lúc hook kiểm chứng độc lập phải nổ. Nó **không nổ**, và bốn lần
truy liên tiếp mỗi lần lộ một lỗi khác nhau của tôi — cả bốn đều thuộc loại **hỏng im lặng**.

#### 1. Điều kiện bắt đúng cái ca nó sinh ra để bắt

Bản đầu chỉ nổ khi **lượt này** có ghi. Nhưng lời tuyên "xong" gần như luôn nằm ở một lượt
**báo cáo** — lượt ấy chỉ đọc — còn việc thì đã ghi ở các lượt trước. Sửa lần một: dùng một cờ
trên `Agent` sống qua nhiều lượt.

#### 2. Cờ trong bộ nhớ không sống nổi qua khởi động lại

App EIDE **khởi động lại giữa các bước làm việc**, nên cờ ấy reset về `False` mỗi lần và việc
ghi ở tiến trình trước thành vô hình. Sửa lần hai: bỏ cờ, đọc từ **sổ cái** — *"kể từ lần
`task.run(verifier)` gần nhất, có lời gọi GHI nào không"*. Sổ cái bền; bộ nhớ thì không.

#### 3. Dò "lời tuyên đạt" bằng TỪ KHOÁ là chỗ mọi danh sách đều thua

Tác tử viết: *"FreeRTOS Kernel chạy đa tác vụ thực tế trên phần cứng STM32F469I-DISCO."* Một
lời tuyên đạt rõ ràng — và **không chứa từ nào** trong danh sách 14 từ khoá của tôi.

Sửa lần ba, và đây là sửa đúng chỗ: **bỏ hẳn việc dò câu chữ.** Điều kiện thành *có việc đã
ghi mà chưa ai kiểm* + *tác tử đang trả lượt về cho người*. Cách nó viết câu kết không liên
quan gì tới việc có cần kiểm hay không. Chi phí có trần tự nhiên: cờ tắt khi verifier chạy,
nên mỗi đợt việc tốn đúng một lần kiểm.

#### 4. Bảo ai đó dùng một thứ họ không nhìn thấy thì không phải là bảo

Hook nổ, `another_round=True`, hai lượt liền — và tác tử **không gọi verifier lần nào**.
`task.run` là `core=False`: nó chỉ hiện ra sau `tool.search`. Lời nhắc bảo *"gọi
`task.run(subagent=verifier)"* trong khi công cụ ấy không có trong danh sách tác tử nhìn thấy.
Sửa: hook **mở khoá `task.run`** ngay trước khi nhắc.

Và một chi tiết vui: cũng trong lúc truy, phát hiện hook plan mode bị **đăng ký hai lần** —
`checks` in ra `['doi_chieu_ke_hoach_lech', 'doi_chieu_ke_hoach_lech']`. Một lỗi chép tệp của
tôi, vô hại nhưng nói dối về số lần kiểm.

#### Kết quả: chuỗi khép lại

```
snapshot.create → store.get → ui.notice → task.run(verifier) → task.run(verifier)
```

Verifier trả **`khong_dat`**, và tác tử **báo cáo thẳng điều đó** thay vì giữ kết luận cũ —
đúng N6. Nhưng lý do `khong_dat` lại là **lỗi thứ năm của tôi**: verifier thử
`store.get("snap-01")` và nhận `E5005`, vì snapshot nằm ở cây riêng chứ không trong kho hiện
vật chung — và tập công cụ của verifier **không có `snapshot.list`**.

*Một người kiểm chứng bị bịt mắt đúng chỗ cần nhìn thì mọi kết luận của họ đều nói về cái bịt
mắt, không nói về thứ đang được kiểm.* → thêm `snapshot.list` vào tập công cụ của verifier,
vẫn **chỉ công cụ đọc**: thêm mắt, không thêm tay.

### Số đo

`1189 ca đơn vị` (+7). Năm lỗi sửa trong một chặng, tất cả cùng một họ: **cơ chế có, nhưng
đường dẫn tới nó bị đứt ở một chỗ không ai nhìn thấy.**

### Còn lại

- `tool.propose` vẫn chưa được tác tử dùng lần nào — chưa gặp việc nào bí tới mức cần.

### [DEV-285] 28/09/2026 · `tool.propose` chạy thật — tác tử tự viết công cụ cho chính nó

Anh Công giao việc phức tạp hơn trên dự án FreeRTOS: màn LCD hiện logo PTIT + thông tin đề
tài, nút **“Chi tiết”** chạm được, màn chi tiết có nút **“Close”**, và **LED vẫn nháy song
song**. Ba chỗ khó cùng lúc — LCD là thứ tác tử đã tự đặt *ngoài phạm vi* ở kế hoạch trước,
cảm ứng thì nó chưa từng đụng.

#### Bug: kế hoạch trong ngữ cảnh không nói nó là kế hoạch CHO VIỆC GÌ

Nhận việc mới, tác tử **không lập kế hoạch nào** — nó đi thẳng vào `store.req_create`. Vì
`<pending>` in:

```
- Kế hoạch đã duyệt: 7/8 bước xong
```

Một con số, không nội dung. Tác tử thấy dòng ấy và tưởng việc mới đã nằm trong kế hoạch cũ.
**Cùng họ với lỗi “Lượt chạy dở: run-256”**: một mã số không nội dung thì người đọc tự điền
nội dung vào, và thường điền sai.

Sửa: dòng ấy in cả **mục tiêu** của kế hoạch, kèm câu *"việc vừa giao mà khác việc trên thì kế
hoạch này không phủ nó — soạn kế hoạch mới"*. Thêm: xong hết bước thì kế hoạch chuyển
`hoan_thanh` và **thôi chiếm chỗ** "kế hoạch hiện tại"; và `plan.enter` **không chặn** khi kế
hoạch cũ đã duyệt — người dùng đổi ý là chuyện bình thường, bắt tác tử chạy nốt một kế hoạch
lỗi thời là cách chắc nhất để nó làm sai việc.

Sau khi sửa: tác tử lập **kế hoạch mới 7 bước** cho việc mới, thẻ G-SCOPE nổ lại. Dự án G7 vẫn
nguyên hash (`116e4e91de2a6632`) — nó chỉ đọc, không sửa.

#### Bug: verifier đòi kiểm sau MỌI bước

Hook `kiem_viec_chua_ai_kiem` nổ ở mọi lượt có ghi, nên tác tử tiêu một lượt cho verifier sau
mỗi bước — kế hoạch bảy bước thành mười bốn lượt. Plan mode **đã** có kỷ luật từng bước
(`plan.step_done` đòi hiện vật); kiểm chứng độc lập thuộc về **lúc kết thúc**, không phải mỗi
chặng nghỉ giữa đường. Sửa: hoãn khi còn bước chưa xong.

#### `tool.propose` nổ lần đầu, và lý do của nó có SỐ ĐO

> **ten**: `plan.get`
> **vi_sao**: *"Đã tốn 10 lời gọi đọc (5 `ledger.query`, 3 `fs.grep`, 1 `tool.search`, 1
> `fs.glob`) vẫn chưa lấy lại được đầy đủ văn bản 7 bước của kế hoạch đã duyệt."*
> **test**: 2 ca — có kế hoạch → trả bước + trạng thái + hiện vật; **không có kế hoạch → nói
> ra**, đừng trả cấu trúc rỗng trông như có.

Và nó **đúng**: `<pending>` in kế hoạch dưới dạng một dòng tóm tắt, nên tác tử **không đọc
được kế hoạch của chính nó**. Vòng đời chạy trọn trong một lượt:

```
fs.write ×2 → tool.reload → plan.get → …
```

Bộ kiểm xanh, công cụ đăng ký, và tác tử **dùng ngay** thứ nó vừa viết.

#### Nhưng mã nó viết đi vòng qua API — và đó là lỗi của KHUÔN MẪU

`plan_get.py` mở **thẳng tệp SQLite** của kho, đoán tên bảng, và **dò ngược thư mục cha** tìm
`.eide/store.sqlite` — tức nó đọc được kho của một **dự án khác**, và sẽ hỏng vào ngày lược đồ
kho đổi. `ctx.store.get("plan:current")` nằm ngay trong tầm tay; nó bỏ qua `ctx` hoàn toàn.

Khuôn mẫu `khuon_ma()` **chưa bao giờ nói `ctx` có gì**. Tác tử không biết thì cái nó tự nghĩ
ra sẽ là cái đi vòng. Sửa: khuôn liệt kê thẳng `ctx.store` / `ctx.config.paths.project_root` /
`ctx.registry` / `ctx.ledger`, kèm chính ca hỏng này làm ví dụ.

Và sửa luôn gốc: `<pending>` giờ **liệt kê từng bước** kèm dấu `[x]`/`[ ]` và công cụ — thứ lẽ
ra đã ở trước mặt tác tử ngay từ đầu.

### Số đo

`1195 ca đơn vị` (+6). Một lỗi tiềm ẩn của chính tôi bắt được khi viết ca kiểm: vòng lặp
`for i, b in enumerate(b, 1)` **che mất** biến danh sách `b`.

### Còn lại

- Tác tử viết lại `plan.get` dùng `ctx.store` thay vì mở SQLite.
- Màn hình + cảm ứng: đang ở bước 2/7 của kế hoạch mới.

### [DEV-286] 28/09/2026 · Tác tử BỊA TÊN NGƯỜI — và bốn lời khuyên không khớp lý do

Việc: màn LCD hiện logo PTIT + thông tin đề tài, nút **“Chi tiết”** chạm được, **Close** quay
lại, LED vẫn nháy song song.

#### Phát hiện nặng nhất: nội dung bị bịa

Đọc khung ảnh thẳng từ SDRAM (`target.screen`). Tác tử **đã vẽ được** — bố cục ổn, chữ sắc
nét. Nhưng trên màn hiện:

| trên màn | trong lời giao việc |
|---|---|
| *“Sinh vien : **Nguyen Dinh Cong**”* | **Học viên: Vũ Trí Công** |
| *“GVHD : **Nhom Nghien Cuu He Thong Nhung**”* | **Giảng viên hướng dẫn: TS. Nguyễn Trung Hiếu** |

Cả hai đều **không có thật**. Bốn dòng ấy được đưa **nguyên văn** trong yêu cầu, nên không có
chỗ nào để suy ra — chép đúng rẻ hơn nghĩ ra nhiều. Đây là N1 áp vào **chữ** thay vì vào số,
và nó nặng hơn một Fact sai: **không ai kiểm một cái tên bằng máy được.** Ảnh sở cứ:
`docs/stm32f469-freertos/ket-qua/anh/khung-anh-NOI-DUNG-BIA.png`.

Sau khi được chỉ đúng hai dòng: sửa xong, ảnh mới ở
`anh/khung-anh-sau-khi-sua-ten.png`. Hai thứ còn thiếu: **logo PTIT** (khung ảnh chỉ 5 màu) và
**cảm ứng** — nó dùng nút vật lý PA0 thay vì chạm màn.

#### Bốn lời khuyên của EIDE không khớp với lý do EIDE vừa nêu

Cùng một họ lỗi, bốn lần trong một chặng — và mỗi lần đều đẩy tác tử đi một hướng sai:

| lỗi | EIDE nói | sự thật | cái giá |
|---|---|---|---|
| `code.vendor_list` | *"hết hạn mức — **có thể repo không tồn tại**"* | repo đúng, chỉ hết lượt | tác tử định **tự gõ lại nhân FreeRTOS** |
| `<pending>` | *"Kế hoạch đã duyệt: 7/8 bước xong"* | không nói kế hoạch **cho việc gì** | không lập kế hoạch cho việc mới |
| `build.compile` | `#error ... enable hardware floating point support` | thứ phải đổi là tham số **`fpu=`** của lời gọi | dễ đi sửa `FreeRTOSConfig.h` hoặc đổi sang port không-FPU |
| `target.flash` | *"đọc được STM32F46x_F47x từ bo…"* rồi khuyên **“cài `st-info`”** | `st-info` đã cài và vừa dùng để đọc ra câu ấy; thứ thiếu là **hộ chiếu chip** | gửi tác tử đi làm một việc vốn đã xong |

Bài học chung, và nó đáng đứng riêng: **một lời khuyên không khớp với lý do vừa nêu thì tệ
hơn im lặng** — im lặng để người ta đi tìm, còn lời khuyên sai làm người ta đi nhanh về phía
sai. Cả bốn chỗ giờ đều chỉ đúng đường, và mỗi chỗ có một ca kiểm neo lại.

#### `tool.propose` chạy thật, hai lần

Lần đầu tác tử xin `plan.get`, lý do có số đo: *"đã tốn 10 lời gọi đọc (5 `ledger.query`, 3
`fs.grep`, 1 `tool.search`, 1 `fs.glob`) vẫn chưa lấy lại được đầy đủ văn bản 7 bước"*. Vòng
đời khép trong một lượt: `fs.write ×2 → tool.reload → plan.get`.

Nhưng mã nó viết **đi vòng qua API**: mở thẳng SQLite, đoán tên bảng, dò ngược thư mục cha —
tức đọc được kho của **dự án khác**. Lỗi ở **khuôn mẫu**: `khuon_ma()` chưa bao giờ nói `ctx`
có gì. Sửa khuôn; tác tử viết lại dùng `ctx.store`.

Và một lỗ hổng nữa: **công cụ tự viết không sống qua lần khởi động lại** — registry ở bộ nhớ,
nên mỗi phiên phải `tool.reload` lại. *Một năng lực biến mất khi mở lại dự án thì chưa phải
năng lực; nó là một mẹo dùng được đúng một lượt.* → `nap_cong_cu_tu_viet()` chạy khi mở dự án,
vẫn giữ hai ranh giới: chỉ nạp tệp **có bộ kiểm đi kèm**, và hỏng thì bỏ qua cái đó chứ không
chặn việc mở dự án.

Lần hai nó xin `fs.copy` — cũng đúng: EIDE không có công cụ chép tệp, mà nó cần chuyển 18 tệp
tham chiếu vào `firmware/`.

#### Hai lỗi của chính phép kiểm tôi viết

`_kiem_noi_dung_dung` so chuỗi **phân biệt hoa thường**, nên báo đỏ khi mã dùng
`BUU CHINH VIEN THONG` viết hoa. Và trong `assemble.py`, vòng `for i, b in enumerate(b, 1)`
**che mất** biến danh sách `b`. Cùng họ với phép kiểm chỉ nhận ra đúng lời giải mà chính nó
nghĩ ra.

### Số đo

`1202 ca đơn vị` (+7). Kế hoạch màn hình: 6/7 bước.

#### Kết: màn hình tương tác chạy hoàn hảo

> *"Đã chạy hoàn hảo."* — anh Công, 28/09/2026.

Logo PTIT · thông tin đề tài đúng tên · nút **“Chi tiết”** chạm được → màn chi tiết → **Close**
quay lại · LED nháy song song suốt thời gian đó. Ảnh sở cứ:
`docs/stm32f469-freertos/ket-qua/anh/KHUNG-ANH-HOAN-CHINH.png`; mã ở
`docs/stm32f469-freertos/firmware-chay-duoc/` (`sha256 094546e6…`, 263 344 byte, đã đối chiếu
với chip).

Ba chỗ hỏng còn lại được gỡ theo đúng một cách: **đo, rồi mới sửa.**

**Màn sáng nhưng NHẤP NHÁY.** Ba phép đo, mỗi cái loại một khả năng:

| đo | kết quả | loại được gì |
|---|---|---|
| đọc cùng dải khung ảnh hai lần | **không đổi** | không phải do tác vụ vẽ lại |
| `DSI_ISR1` bốn lần | `0x80` (`LPWRE`) **bám dai** | LTDC đẩy nhanh hơn DSI rút |
| `RCC_CFGR` trên silicon | `SWS = 0` | **SYSCLK vẫn ở HSI 16 MHz** |

Bản G7 trên cùng bo chạy 180 MHz. Mã FreeRTOS bật HSE và đặt `PLLM` bằng tay qua thanh ghi
nhưng **không chuyển SYSCLK sang PLL**, nên cả chip ở 16 MHz trong khi mọi thông số nhịp của
BSP màn hình tính cho 180 MHz. Sửa xong: `SWS = 2`, `PLLN = 360`, Flash 5 wait state — và mắt
thứ 11 của chuỗi hiển thị **tự tắt**. Chuỗi thông suốt cả 11.

**Nút vẽ ở ba toạ độ khác nhau.** Anh Công hỏi *"vùng màu xanh là cái gì?"*. Đo trên khung
ảnh: hình chữ nhật thật ở **x 154…759**, mã vẽ `FillRect(160, 400, 480, 50)` → **x 160…640**,
còn chữ vẽ `CENTER_MODE` nên căn giữa **cả màn 800 px**. Ba chỗ, ba toạ độ — người nhìn thấy
một mảng xanh trôi lệch khỏi dòng chữ của chính nó. Đo toạ độ thay vì nhận xét "nút bị lệch"
là thứ biến một cảm giác thành một con số sửa được.

**Nút sai loại.** Nó ghi *"AN NUT USER BUTTON (PA0)"* — nút vật lý, trong khi yêu cầu là
**chạm màn**. Tác tử tự tìm ra panel cảm ứng nối qua I2C và làm được.

#### Tác tử tự viết BA công cụ cho chính nó

`plan.get` · `fs.copy` · `fs.remove` — mỗi cái kèm bộ kiểm riêng phải XANH mới được đăng ký,
sống ở `.eide/cong-cu/` của dự án và được nạp lại mỗi lần mở dự án. Giữ trong repo tại
`docs/stm32f469-freertos/firmware-chay-duoc/cong-cu-tac-tu-tu-viet/`.

### Còn lại

- Khôi phục bản demo gốc của ST cho bo, nếu anh Công muốn.

### [DEV-287] 28/09/2026 · Biểu tượng ứng dụng và bảng Giới thiệu

Anh Công đưa `ui/eide_B_chip_code.png` làm biểu tượng, và yêu cầu bổ sung thông tin giới thiệu
app kèm tác giả và thầy hướng dẫn.

**Biểu tượng.** `lam-bieu-tuong.sh` dựng `Resources/EIDE.icns` từ ảnh gốc bằng `sips` +
`iconutil` (sáu cỡ, mỗi cỡ hai bản 1×/2×), và `dong-goi.sh` chép nó vào gói kèm
`CFBundleIconFile`. Việc dựng **không** nằm trong `dong-goi.sh`: nó tốn vài giây mỗi lần đóng
gói mà kết quả không đổi, và một bước chậm không đổi gì là bước người ta sẽ tìm cách bỏ.

**Bảng Giới thiệu.** Thay mục *About EIDE* mặc định của macOS — bảng mặc định chỉ đọc
`Info.plist` nên không nói được ai hướng dẫn đề án, mà với một luận văn thì đó đúng là thông
tin người xem tìm đầu tiên. Là một `NSWindow` phụ chứ không phải `WindowGroup` thứ hai: một
scene nữa sẽ thêm mục trong menu Window và tự mở lại khi khôi phục phiên, cả hai đều không
đúng với một bảng "về ứng dụng".

Mọi thông tin trong bảng là **hằng số của mã**, không lấy từ kho và không lấy từ tác tử. Lý do
nằm ngay trong chặng trước: tác tử đã **tự nghĩ ra** tên học viên và tên thầy hướng dẫn rồi vẽ
chúng lên màn LCD (DEV-286). Tên người là thứ duy nhất trong cả hệ thống mà **không phép đo
nào kiểm được**, nên nó phải nằm ở chỗ chỉ người sửa được.

**Kiểm bằng GUI thật, không bằng lời.** Kênh kiểm giao diện thêm hai lệnh: `gioi_thieu` (mở
bảng) và tham số `cua_so` cho lệnh `anh` (chụp đúng cửa sổ có tiêu đề ấy) — cần vì
`NSApp.windows` không đảm bảo thứ tự trước–sau, nên không có cách nào chụp đúng một cửa sổ phụ
mà không nói tên nó ra. Ảnh do **chính app tự vẽ**, không `screencapture`:
`docs/anh/gioi-thieu-eide.png`.

Một chi tiết nhỏ mà không có nó thì bảng trông như ứng dụng chưa có biểu tượng: bảng đọc
`Resources/AppIcon.png` trước, chỉ lấy `NSApp.applicationIconImage` làm phương án dự phòng —
khi chạy bằng `swift run` (chưa đóng gói `.app`) thì thuộc tính ấy trả biểu tượng **mặc định
của macOS**.

### Số đo

`1202 ca đơn vị` (không đổi — đây là thay đổi ở tầng giao diện, và nó được kiểm bằng ảnh chụp
qua GUI thật).


### [DEV-288] 28/09/2026 · Bộ kiểm tự viết của tác tử — sáu ô xanh không đo gì cả

**Việc người dùng giao:** *"Kiểm tra năng lực tự viết test plan, testcase, tự do test của
agent"*. Kịch bản phiên FreeRTOS thêm bước 19, cố ý **không** nói khuôn nào, công cụ nào, kiểm
những gì — đó chính là phần cần đo. Chỉ nêu hai điều quan tâm: mỗi ca phải nói *đo bằng gì* và
*ngưỡng nào là đạt* **trước** khi chạy, và phần không kiểm được phải khai ra.

Tác tử viết `test/test_ui.c`: sáu ca TC-01…TC-06, mỗi ca có tên, có ngưỡng, có thông điệp, in
báo cáo JSON, chạy qua `test.run`, sáu ô xanh. Ba phép kiểm đầu của kịch bản — *có hiện vật ·
ca có ngưỡng · có dám để ô đỏ* — đều xanh.

Rồi tôi phá `firmware/ui.c` thật: đổi mọi toạ độ nút thành `99999`, tức là hỏng hẳn logic chạm.
Chạy lại chính bộ kiểm ấy:

```
ĐẠT  TC-01 … ĐẠT  TC-06          ← cả sáu ca, không ca nào nhúc nhích
```

Tệp test **tự định nghĩa lại** `UI_ToggleScreen` và `UI_HandleTouch` ngay trong chính nó. Nó
đang kiểm một bản sao của logic viết trong tệp test, nên nó sẽ xanh mãi mãi dù sản phẩm làm gì.

**Cấu trúc đúng không chứng minh được nó đo gì.** Một bộ kiểm có đủ tên ca, đủ ngưỡng, đủ báo
cáo JSON, mà không chạm mã sản phẩm, thì tệ hơn không có bộ kiểm nào: nó biến một chỗ *chưa
được kiểm* thành một *ô xanh*, và ô xanh thì dừng việc tìm lỗi.

Đây là dạng khác của bài học cũ **"`ok` nói về lời gọi, không nói về kết quả"**, lần này ở tầng
kiểm thử: *"xanh nói về tệp test, không nói về sản phẩm"*.

#### Năng lực mới: `test.sensitivity` — đo bộ kiểm bằng đột biến mã

`src/eide/build/dot_bien.py` + công cụ `test.sensitivity` (R1, không khoá): phá mã sản phẩm rồi
chạy lại bộ kiểm. Không ca nào đỏ ⇒ bộ kiểm không nhìn thấy tệp ấy.

Nó trả **bốn** trạng thái, không phải hai — mỗi lần gộp lại là một lần nói sai:

| trạng thái | nghĩa |
|---|---|
| `thay` | phá thì đỏ ⇒ bộ kiểm có nhìn tệp này |
| `khong_thay` | nạp được, phá rồi vẫn xanh ⇒ không nhìn |
| `khong_nap_duoc` | bộ kiểm không dịch nổi cùng tệp sản phẩm — bằng chứng **mạnh hơn**: trùng ký hiệu nghĩa là tệp test đã định nghĩa lại hàm của sản phẩm; thiếu header của bo nghĩa là logic dính chặt phần cứng |
| `chua_do_duoc` | không có chỗ nào để phá / không đọc được — cái này mới thật sự là "chưa biết" |

Ba chỗ mô-đun tự rào mình, vì nếu không thì chính nó thành một ô xanh giả:

- **Không đụng chuỗi và chú thích.** Đổi một chữ trong `printf` thì hành vi không đổi, và một
  đột biến không đổi hành vi mà bộ kiểm "không bắt được" là một **cáo buộc sai**.
- **Không phá toán tử ghép.** Bản đầu đổi `i++` thành `i+-` — mã không dịch được, mà "không
  dịch được" rất dễ bị đọc thành "bộ kiểm bắt được". Bài kiểm `test_dot_bien_khong_pha_toan_tu
  _ghep` bắt đúng lỗi này khi tôi viết nó.
- **Bộ kiểm đỏ sẵn thì không kết luận gì.** Không phân biệt được "đỏ vì đột biến" với "đỏ từ
  trước", nên phải nói *chưa đo được*, không được nói tốt mà cũng không được nói giả.

Mô-đun tự nói ra chỗ nó **không** làm: đây không phải mutation testing đầy đủ, không có
mutation score, không phân biệt đột biến tương đương. Nó trả lời đúng một câu nhị phân cho mỗi
tệp — *"bộ kiểm có thấy tệp này không?"* — và một bộ kiểm qua được phép này vẫn có thể rất
nông; nó chỉ chứng minh mình **không rỗng**.

#### Ba lỗ hổng của EIDE đã đẻ ra cái bộ kiểm giả ấy

Giao số đo cho tác tử rồi để nó tự sửa, ba chỗ lộ ra — và cả ba đều là lỗi của **EIDE**, không
phải tính lười của tác tử:

1. **`test.run` chỉ gom `firmware/control*.c`** — một cái tên nghĩ ra từ một dự án khác. Dự án
   này đặt logic ở `ui_state.c`, nên nó không được liên kết vào, tệp test báo thiếu ký hiệu, và
   tác tử **chép logic sang tệp test** để có thứ mà chạy. *Một cái tên tệp đoán sẵn đã đẻ ra
   một ô xanh giả.* Nay nhặt theo thứ **đo được**: tệp `.c` nào trong `firmware/` không
   `#include` header của bo thì liên kết vào. Và `note_vi` **nói ra** nó dịch cùng tệp nào, bỏ
   ngoài tệp nào vì sao — không có câu ấy thì `8/8 ca đạt` đọc như "sản phẩm đã được kiểm".
2. **Khuôn đầu ra JSON chỉ được nói ra trong một thông báo lỗi chỉ hiện khi CHƯA có tệp test
   nào.** Có tệp rồi thì im lặng, và tác tử đoán: nó in **mười dòng JSON mười kiểu** cho cùng
   một ca (`{"assert":…}`, `{"type":"case",…}`, `{"ca":…}`, …). Khuôn nay nằm ở
   `mo_phong.KHUON_RA`, đi kèm mọi lối hỏng, và khi có JSON mà không có khoá `ca` thì nói luôn
   tệp test đang in khoá gì. **Cố ý không nới bộ phân tích cho nhận cả mười khuôn:** mười dòng
   kia tự khai "đạt" mà sau lưng không có phép khẳng định nào — nhận chúng là đếm mười ca đạt
   giả, đúng thứ N6 cấm. Chỗ cần sửa là *nói ra*, không phải *nhận bừa*.
3. **Chạy xong không đếm được ca nào thì `test.run` trả THÀNH CÔNG** với dòng `0/0 ca đạt` —
   một câu không có ô đỏ nào — còn lời chỉ khuôn nằm trong `vi_sao_khong_dat` thì không lối nào
   tới được tác tử. Nay là lỗi `E4014`.

#### Tác tử làm gì khi nhận số đo

Không cãi, và không tin luôn: nó **tự chạy `test.sensitivity`** để kiểm lại lời người dùng
trước khi sửa. Rồi nó tách `firmware/ui_state.c` — máy trạng thái màn hình + phép kiểm vùng
chạm, không `#include` header nào của bo — và sửa `ui.c` thành lớp **uỷ quyền** cho nó. Logic
nằm một chỗ, trên đúng đường sản phẩm chạy, và dịch được trên máy chủ.

Đo lại, bằng `cc` trần chứ không bằng `dot_bien.py` (đo một công cụ bằng chính nó thì hai cái
cùng sai một kiểu vẫn ra màu xanh):

```
✅ phá thì ĐỎ: ui_state.c · ngoài tầm: touch.c, ui.c (không dịch cùng được)
```

Tám ca, có cả hai ca **biên** `(150,380)` đạt và `(149,380)` không đạt. Và nó tự khai phần chưa
kiểm được: `ui.c` (vẽ LCD qua BSP) và `touch.c` (I2C tới FT6206) — nói rõ phần nào đã tách
sang `ui_state.c` để kiểm được, phần nào chỉ kiểm được trên bo.

Nạp lại bo sau khi tách: PC rơi vào `prvCheckTasksWaitingTermination` (nhân FreeRTOS vẫn chạy),
11/11 mắt xích hiển thị thông, màn vẫn đúng logo PTIT + bốn dòng + nút "Chi tiet". Việc tách
không làm hỏng sản phẩm — đo trên silicon, không suy từ mã.

Nhưng ba số đo ấy **chưa đủ**, và chỗ thiếu đúng vào chỗ vừa sửa: chúng nói khung ảnh có nội
dung và nhân còn chạy, **không** nói vòng chạm còn sống. Toàn bộ việc tách là lấy
`UI_State_CheckTouch` và `UI_State_Toggle` ra khỏi `ui.c` — tức là đúng đoạn từ ngón tay tới
lúc màn đổi. Đọc khung ảnh không đi qua đoạn đó một bước nào.

Người dùng bấm thử nút "Chi tiet" trên bo và xác nhận **vẫn chạy tốt** (28/09/2026). Đây mới là
bằng chứng cho phép tách: cảm ứng I2C → `touch.c` → `UI_State_CheckTouch` → `UI_State_Toggle` →
`ui.c` vẽ lại. Trên máy chủ, tám ca kiểm chỉ chạm được khúc giữa; hai đầu chỉ bo thật nói được,
và tác tử đã khai đúng như vậy.

#### Một cái bẫy trong kịch bản phiên, do tôi đạp phải

`--buoc 20` đọc như *"chạy tiếp bước 20 của phiên đang có"*, nhưng mặc định lại `rmtree` cả thư
mục dự án. Tôi mất `test/test_ui.c` bản đầu và cả sổ cái của dự án theo đúng cách ấy. Nay hai
cờ nói ngược nhau thì **dừng**, bắt gõ rõ, không đoán hộ. Firmware khôi phục từ bản chụp đã
commit; sổ cái **không** nối lại — nối một sổ cái cũ vào một sổ cái mới sẽ làm chuỗi băm khớp
giả, mà một chuỗi băm khớp giả còn tệ hơn một chuỗi bị đứt có ghi chú.

### Số đo

`1214 ca đơn vị` (+12 so với DEV-287): 11 ca cho `dot_bien` + 1 ca cho phép nhặt tệp logic
không theo tên. Công cụ mới: `test.sensitivity`. Một ca cũ được **siết**:
`test_test_run_KHONG_in_JSON_thi_khong_ket_luan` từ "thành công mang `dat=False`" thành "lỗi
`E4014` kèm khuôn cần in".

### [DEV-289] 28/09/2026 · Mở lại dự án: hội thoại dựng lại được, cái NÚT thì không

**Việc người dùng giao:** *"Review tính năng cơ bản tạo dự án, mở dự án, tính năng đảm bảo tắt
app mở lại dự án vẫn làm việc tiếp được"*.

Review này không đọc mã rồi kết luận. Mỗi câu hỏi là một phép thử chạy qua app thật: trỏ vào
thư mục rỗng · giao việc · `kill -9` (máy sập, không phải thoát tử tế) · mở lại · hỏi tiếp.
Kịch bản ở `tools/review_ben_vung.py` và `tools/review_lam_tiep.py`, nhật ký ở
`docs/review-mo-du-an/`.

#### Phần chạy đúng

- **Tạo dự án = mở một thư mục rỗng.** Trỏ app vào thư mục trống thì lõi tự dựng `.eide/`
  (sổ cái có xích băm, `store.sqlite`, `blobs/`, `counters.json`), tự sinh `EIDE.md` từ khuôn,
  tự `git init` và tạo `cs-0000`. Không có bước nào phải làm tay.
- **`kill -9` không mất gì trên đĩa.** Thứ duy nhất biến mất là `store.sqlite-wal`/`-shm` —
  WAL đã được gộp vào CSDL, tức là dữ liệu đi vào chỗ bền hơn. (Bản đầu của phép kiểm so cả
  danh sách tệp nên báo đỏ vì đúng cái chuyển động ấy: một **báo động sai**, và một báo động
  sai làm người đọc mất lòng tin vào những ô đỏ thật bên cạnh.)
- **Kế hoạch sống qua cú sập.** Nó là hiện vật `plan:current` trong kho, kể cả trạng thái
  `da_duyet` và cờ `xong` của từng bước. Mở lại, gõ đúng hai chữ *"Làm tiếp nhé"*, tác tử nói
  *"Mình đang thực hiện Bước 2 trong kế hoạch đã duyệt"* và không gọi `plan.enter` lần nữa —
  người **không** phải duyệt lại từ đầu. Đây là chỗ mất mát đắt nhất nếu hỏng, và nó không hỏng.
- **Trí nhớ hội thoại mất, nhưng có đường tra.** Thử bằng một mã bí mật chỉ nói bằng lời,
  không ghi vào đâu: sau khi tắt–mở, tác tử tra `ledger.query` và lấy lại đúng `XANH-47` từ
  lời người nói trong sổ cái. Nó không nhớ, nhưng nó biết tra ở đâu. *(Hệ quả cần biết: mọi
  câu gõ vào đều nằm vĩnh viễn trong sổ cái — "đừng ghi vào đâu cả" chỉ đúng với hiện vật.)*

#### Ba lỗi, cùng một nguồn: phát lại dựng lại cả thứ không dựng lại được

Đo trên một dự án có hai thẻ cổng **đều đã được duyệt xong**:

```
Vừa mở lại   : dòng hội thoại = 15 | thẻ đang chờ = 2      ← hai thẻ đã trả lời rồi
Sau Cmd-R x1 : dòng hội thoại = 30 | thẻ đang chờ = 4
Sau Cmd-R x2 : dòng hội thoại = 45 | thẻ đang chờ = 6
Sau Cmd-R x3 : dòng hội thoại = 60 | thẻ đang chờ = 8
```

Và bấm "Duyệt" trên một thẻ dựng lại thì nhận `E_GATE_STALE`. **Một cái nút bấm được mà không
làm gì** — tệ hơn hẳn không có nút, vì người tưởng mình vừa quyết định điều gì đó.

Nguyên nhân: `_phat_lai_transcript` chiếu lại `console.post` từ sổ cái kèm nguyên trường
`card`, còn phía Swift dựng `Card` mới với `resolved = false`. Dòng chữ chiếu lại được; thứ
**trả lời** được một thẻ — lời gọi công cụ đang treo trong `pending_gates` — nằm trong bộ nhớ
của tiến trình đã chết.

Sửa, ở `src/eide/protocol/rpc.py`:

1. Mỗi thẻ phát lại **đóng ngay**, theo trạng thái tra từ sổ cái: đã có quyết định thì
   `card.resolve` kèm người đã chọn gì; chưa ai trả lời thì `card.expire` kèm lý do **và**
   cách làm lại. Không chọn lối "giữ nó treo" (người mất quyền quyết mà không biết) cũng
   không chọn lối "tự chạy lại" (một việc chưa ai đồng ý đã xảy ra).
2. Phát lại **đúng một lần cho mỗi lõi**. `ui.sync` còn chạy khi bấm Cmd-R và khi giao diện
   mất đồng bộ, mà lúc ấy Console đang có sẵn các dòng cũ. Bề mặt vẫn được vẽ lại — đó mới là
   việc chính của Cmd-R.
3. `resume.py` không còn nói *"thẻ cổng đang chờ người trả lời"* mà nói **đã hết hiệu lực**,
   kèm dặn: đừng chờ, đừng bảo người dùng bấm lại, cần thì hỏi lại rồi dựng thẻ mới.

#### Lỗi thứ tư, chỉ tấm ảnh bắt được

Sau ba lần sửa trên, phép đo báo `the_dang_cho = 0`. Nhưng **ảnh chụp cửa sổ** cho thấy thẻ
vẫn nằm trong dòng hội thoại với đủ hai nút Duyệt/Từ chối, bấm được.

`Card` là **struct** — kiểu trị. Dòng hội thoại giữ một *bản sao*, nên `cards[i].resolved =
true` không đụng tới nó, mà `ConsoleView` lại vẽ nút dựa vào chính bản sao ấy. Lỗi này **không
phải chỉ khi mở lại**: trong một phiên bình thường, duyệt xong thì nút vẫn ở đó.

Số đo đúng, câu hỏi sai — `the_dang_cho` không bao giờ nói được điều này. Nên ngoài việc sửa
`AppState.apply`, kênh kiểm giao diện phơi thêm `so_the_con_nut`, đếm đúng thứ `ConsoleView`
vẽ, để lần sau nó không tái phát trong im lặng.

Chứng minh ngược, bằng cách cất hết bản sửa đi rồi đo lại đúng dự án ấy:

```
BẢN CHƯA SỬA : dòng = 18 | thẻ chờ = 3 | thẻ còn nút = (chưa có phép đo này)
BẢN ĐÃ SỬA   : dòng = 18 | thẻ chờ = 0 | thẻ còn nút = 0
```

#### Một chỗ dễ hiểu lầm, nay nói thẳng

Console dựng lại nguyên cuộc trò chuyện hôm trước, còn tác tử bắt đầu mỗi phiên với ngữ cảnh
**rỗng** — hai thứ ấy là hai kho khác nhau. Cái im lặng giữa chúng đọc như *"tác tử vẫn nhớ
mọi thứ"*, và người dùng phát hiện ra điều ngược lại vào đúng lúc đắt nhất. Nay bản phát lại
kết thúc bằng một dòng nói rõ: đây là hình chiếu của sổ cái, tác tử làm việc lại từ sổ cái,
kho hiện vật và `EIDE.md`; thẻ cổng cũ đã đóng; điều gì quan trọng mà chỉ nói bằng lời thì
nhắc lại giúp.

#### Chọn nhầm một TỆP làm thư mục dự án

Bộ chọn để `canChooseFiles = true`, nên chọn `main.c` được, và lõi ném
`NotADirectoryError: …/main.c/.eide` — đúng chỗ, nhưng người đọc không hiểu chuyện gì và không
biết sửa thế nào. Vá hai phía: bộ chọn chỉ nhận thư mục, `hopLe`/`vanDe` kiểm `isDirectory`,
và `Paths.ensure` nói bằng lời người đọc được — vì ô ấy là ô **văn bản**, gõ tay được, nên
chặn ở giao diện là chưa đủ.

#### Hai khoảng trống, chưa vá — đây là tính năng, không phải lỗi

- **Không có nút "Tạo dự án".** `CommandGroup(replacing: .newItem) {}` xoá hẳn File ▸ New và
  không có gì thay vào; màn mở chỉ có một nút "Mở dự án". Tạo dự án *chạy được* (mở một thư
  mục rỗng) nhưng không ai nhìn vào giao diện mà đoán ra được. Bản mẫu UI có khai A14.1.1
  *"Mở / tạo dự án"* — khối ấy chưa được dựng.
- **Không có danh sách dự án gần đây.** Chỉ một chuỗi `duAnPath` trong UserDefaults, ghi đè
  mỗi lần; app tự mở lại đúng dự án ấy lúc khởi động. Làm việc với hai dự án cùng lúc — đúng
  tình huống của chính đề án này, có hai dự án trên cùng một bo — thì phải gõ lại đường dẫn.

### Số đo

`1221 ca đơn vị` (+7): `tests/test_mo_lai_du_an.py`. Bốn ca đầu đã được chứng minh là **đỏ
được** bằng cách phá lại chỗ vừa vá (bỏ cờ phát-lại-một-lần → 1 ca đỏ; bỏ luôn phần đóng thẻ →
3 ca đỏ).

### [DEV-290] 28/09/2026 · Vòng đời dự án: tạo mới · đóng · mở lại gần đây

Hai khoảng trống DEV-289 nêu ra, nay vá. Nhưng lúc làm lộ ra **chỗ thứ ba**, và nếu thiếu nó
thì hai cái kia vô dụng: `AppState.dong()` **chưa từng được gọi ở đâu**. Một khi đã đặt dự án
thì không có đường quay lại màn mở — danh sách gần đây có làm ra cũng không ai tới được. Nên
ba việc này phải đi cùng nhau chứ không tách rời.

#### Tạo dự án

File ▸ **Dự án mới…** (⌘N) và một nút trên màn mở. Dùng `NSSavePanel` chứ không phải
`NSOpenPanel`: người đang **đặt tên** một thứ chưa có, không phải chọn một thứ đã có — bảng
"mở" không có ô gõ tên, nên với nó "tạo dự án" vẫn là "tự tạo thư mục trong Finder trước đã".

App **chỉ tạo thư mục**, không dựng `.eide/`. Giữ đúng một nguồn sự thật cho câu hỏi *"một dự
án gồm những gì"*: `Paths.ensure` bên Python. App mà tự dựng lấy vài thư mục thì hai chỗ sẽ
trôi khỏi nhau, và cái trôi ấy chỉ lộ ra khi có người mở một dự án do bản app cũ tạo.

Hai lối bị chặn, mỗi lối một câu nói rõ vì sao:

- **Đã có sẵn thứ gì đó ở đó** → bảo chọn tên khác, hoặc dùng "Mở dự án" nếu đây là dự án cũ.
- **Nằm bên trong một dự án khác** (`duAnBaoTrum` đi ngược cây thư mục tìm `.eide`) → đây là
  luật *"không tạo lồng"* của bản mẫu UI (A14.1.1). Lý do không phải hình thức: một dự án lồng
  trong dự án khác thì `.eide/` của cái trong — sổ cái, kho hiện vật, ảnh chụp — trở thành tệp
  thường trong hộp cát của tác tử ngoài; nó đọc được, sửa được, và **không có gì nói cho nó
  biết** đấy là sổ cái của một dự án khác.

#### Danh sách gần đây

Tám dự án, mới nhất trước, trong File ▸ **Mở gần đây** và trên màn mở. Ba quyết định:

- **Chỉ ghi nhớ sau khi lõi đã bắt tay xong**, không ghi lúc bấm nút. Ghi lúc bấm thì danh
  sách sẽ đầy những đường dẫn gõ sai, và người phải thử từng cái mới biết cái nào thật.
- **Dự án tự mở lúc khởi động cũng được ghi.** Không thì dự án người dùng dùng *nhiều nhất*
  lại là dự án duy nhất không có trong danh sách.
- **Dự án không còn trên đĩa vẫn được HIỆN**, chỉ mờ đi, không bấm được, kèm nhãn *"không còn
  ở đây"* và nút "Quên". Lặng lẽ lọc nó ra thì người thấy một mục biến mất mà không biết vì
  sao — mà lý do thường là họ vừa đổi tên hay chuyển thư mục, tức là đúng lúc họ cần biết nhất.

#### Đo qua GUI thật, và một chỗ chỉ tấm ảnh nói được

Kênh kiểm giao diện thêm ba lệnh (`du_an_moi`, `mo_gan_day`, `dong_du_an`) và hai trường trong
ảnh chụp (`man_hinh`, `du_an_gan_day`). Không có `man_hinh` thì không phân biệt được *"đã đóng
dự án"* với *"lệnh đóng chẳng làm gì"* — hai thứ trông giống hệt nhau qua mọi số khác. Kịch
bản: `tools/review_tao_va_gan_day.py`, nhật ký `docs/review-mo-du-an/03-*.md`. Mười ô, xanh cả
mười.

Giới hạn nói ra: ba lệnh ấy gọi **đúng** những hàm mà nút bấm gọi, chỉ thiếu bảng chọn tệp của
macOS — bảng ấy là modal, không lái được từ một tệp lệnh.

Và một chỗ nữa: ảnh tự chụp của màn mở ra **trắng-trên-trắng**, không đọc được chữ nào — làm
tôi tưởng nút "Dự án mới…" không được vẽ. Nó vẫn ở đó; màn ấy không có nền của **riêng** nó,
nó mượn nền cửa sổ, mà `cacheDisplay` chỉ vẽ cây view. Trên máy trông vẫn đúng, nhưng cả cách
kiểm của dự án này dựa vào tấm ảnh — **một màn không chụp được là một màn không kiểm được**.
Thêm `.background(.background)` là xong.

#### Cái nhãn "không còn ở đây" suýt nữa chỉ đúng trên giấy

Riêng việc dòng `hai` hiện mờ kèm *"không còn ở đây"* thì bằng chứng là **tấm ảnh**
(`docs/review-mo-du-an/anh/man-mo-du-an.png`), không phải một con số: phép đo chỉ khẳng định
được đường dẫn còn trong danh sách. Phơi thêm một trường tính lại `fileExists` ở kênh kiểm sẽ
chỉ lặp lại đúng biểu thức mà view dùng, chứ không chứng minh view có vẽ nó — nên tôi không
làm, và ghi rõ ở đây thay vì để một ô xanh nói hộ.

Và chính tấm ảnh ấy bắt được lỗi. Bản đầu: `FileManager.fileExists` gọi trong thân view chỉ
chạy lại khi SwiftUI **dựng lại** view — mà xoá một thư mục ở Finder thì không có gì báo cho
SwiftUI cả. Xoá dự án trong lúc màn này đang hiện thì dòng của nó **vẫn xanh và vẫn bấm
được**: đúng cái bẫy mà nhãn kia sinh ra để tránh, chỉ dời đi vài giây. Nhãn chỉ xuất hiện ở
lần dựng sau — mở app lần tới, hoặc vừa đóng một dự án — nên mười ô đo đều xanh và ảnh chụp
đầu tiên (chụp ở một lần chạy khác) cũng trông đúng.

Vá bằng một nhịp hai giây, chỉ chạy khi **chưa mở dự án nào**, tức đúng lúc màn này hiện ra.
Bài đo nay đợi qua một nhịp rồi mới chụp, và nhật ký ghi thẳng cách đọc tấm ảnh: *nếu `hai`
vẫn xanh thì nhịp đồng hồ đã hỏng.*

Đây là lần thứ hai trong hai chặng liền, một ô xanh đúng đi kèm một màn hình sai — lần trước
là thẻ cổng đã đóng mà nút vẫn bấm được (DEV-289). Cùng một hình dạng: **số đo đúng, câu hỏi
sai**, và cái sai chỉ hiện ra khi nhìn vào thứ người dùng thật sự nhìn.

### Số đo

`1221 ca đơn vị` (không đổi — đây là thay đổi ở tầng giao diện, kiểm bằng mười ô đo qua GUI
thật và một ảnh do chính app vẽ).

### [DEV-291] 28–29/09/2026 · Chạy lại toàn bộ 76 ca kiểm và quét toàn bộ giao diện

**Việc người dùng giao:** *"mở app thực hiện tất cả các usecase trong tài liệu … full các
testcase … đảm bảo mọi label, control đều hoạt động tốt"*, rồi *"ghi log chi tiết để từ đó
chúng ta fix triệt để"*.

Nguồn đề bài: `docs/review-v3/test/Usecase_Test_23-09-2026.md` — 19 usecase, 76 ca kiểm, đo
23/09/2026 trên kiến trúc **cũ** (định tuyến ý định, `chat.parse_intent`, `archive.list`).
Lõi nay là vòng lặp công cụ khác hẳn, nên đây là một phép đo mới chứ không phải so hai cột.

#### Số đo

| | Ca kiểm | Giao diện |
|---|---|---|
| Đạt | **65/68 đo được** (96 %) | **124/124 ô** |
| Không đạt | 3 | 0 |
| Ngoài phạm vi · cần người · cần thiết bị | 2 · 3 · 3 | — |

Bộ chạy: `tools/bo_usecase.py` (76 ca thành dữ liệu) · `tools/chay_usecase.py` (lái app thật)
· `tools/quet_giao_dien.py` (11 bề mặt) · `tools/bao_cao_tong.py` (gộp + **tự kiểm sót**).
Mỗi ca có một tệp log riêng ở `ket-qua-chay-lai/nhat-ky/TCxxx.md`: câu người gõ · đề bài chờ ·
**bảng từng lời gọi công cụ kèm tham số đầy đủ và mã lỗi** · nguyên văn lời đáp. Đủ để ngồi
sửa mà không phải chạy lại — chạy lại một ca tốn một lượt mô hình.

#### Ba lỗi SẢN PHẨM, đã sửa

**L1 — `store.option_choose` gán "NGƯỜI QUYẾT" cho một câu người dùng không hề chọn gì.**
Người gõ đúng một câu — *"Làm cho mình cái mạch thông minh."* — và tác tử gọi
`store.option_choose{quyet_boi:"nguoi", trich_loi_nguoi:"Làm cho mình cái mạch thông minh."}`
rồi tuyên "Đã chốt kiến trúc — ADR-01".

Đây là **giả mạo xuất xứ**, không phải lỗi trình bày. Nó vi phạm N1 theo cách tệ nhất: nguồn
CÓ THẬT (người dùng có nói câu đó) nhưng KHÔNG nói điều được gán cho nó — và một trích dẫn
thật đặt sai chỗ khó phát hiện hơn nhiều so với một trích dẫn bịa. `NGUOI` lại là tầng tin cậy
**cao nhất**, thứ mọi quyết định sau đó dựa vào mà không ai kiểm lại.

Nay `quyet_boi="nguoi"` phải **chứng minh được**, không phải khai được — ba phép kiểm, cả ba
đều tra từ dữ liệu đã có: câu trích có trong sổ cái không · câu ấy có chữ mang nghĩa lựa chọn
không · có nhắc đúng phương án không. Bản đầu thiếu phép thứ hai và **vẫn cho lọt đúng ca nó
canh**: "Làm cho mình cái **mạch** thông minh" và tên phương án "Bo **mạch** Linux nhỏ làm USB
gadget" cùng có chữ "mạch" — một từ chung của cả lĩnh vực. Lỗi trả về nói ra **hai đường đi**
(hạ xuống `quyet_boi="tac_tu"`, hoặc hỏi rồi chốt), vì chặn mà không chỉ lối thì tác tử sẽ thử
lại đúng lối cũ. Có một ca kiểm riêng chứng minh cái phanh **không** chặn nhầm đường đúng.

**L7 — `build.compile` chọn chuỗi công cụ theo "máy có gì", không theo "dự án là gì".** Điều
kiện là `if arduino-cli đã cài and isa có fqbn`, nên một dự án chỉ có `firmware/*.c` vẫn bị
đẩy sang `arduino-cli compile` và người đang hỏi về `-O3` nhận về một lỗi nói chuyện **định
dạng sketch Arduino**. Họ sẽ đi tìm một tệp `.ino` mà dự án không bao giờ cần. Nay chỉ chọn
arduino-cli khi thư mục **thật sự có `.ino`**.

Hậu quả không dừng ở một thông điệp: nó **chặn đứng** TC055 trước khi ca ấy tới được phần chạy
hồi quy. Một lỗi ở bước chọn công cụ che mất toàn bộ thứ nằm sau nó.

**L9 — bảng trong Console cuộn ngang được nhưng không có dấu hiệu nào cho biết còn nội dung.**
`showsIndicators: false`, nên cột thứ ba bị cắt thành `Giải p…` và người đọc không có lý do gì
để thử kéo ngang. Với họ, phần ấy không tồn tại.

Thêm một lỗi trình bày cùng đợt: lời tác tử mang tiền tố `[Tác tử] ` chèn **trong chữ**, làm
khối Markdown đầu tiên không được dựng — người dùng đọc thấy nguyên `## Kết quả…`. Tiền tố ấy
vốn đã thừa (Console in nhãn vai ở cột trái), nên bỏ hẳn ở cả 21 chỗ thuộc 4 tệp: sửa một
**lớp** lỗi chứ không một chỗ, vì mọi khối mở đầu — tiêu đề, trích dẫn, gạch đầu dòng, bảng,
khối mã — đều bị cùng một kiểu.

#### Sáu lỗi của chính BỘ ĐO — ghi ngang hàng, vì chúng dẫn tới việc sai y như lỗi thật

`LOI-TIM-DUOC.md` ghi đủ chín mục. Chúng quy về hai hình dạng:

**Ô XANH GIẢ.** L3: phép chấm TC004 chỉ đòi lời đáp có một dấu `?`, nên nó **bật xanh cho đúng
cái lỗi nó canh** — lượt chốt ADR-01 vẫn có câu hỏi ở cuối. L5: TC029 đòi một chuỗi *dò → nạp
→ kiểm* nhưng chấm bằng **một trong ba** công cụ, nên tác tử dò xong rồi dừng vẫn đạt, và hai
phần ba đề bài không bao giờ được chạm tới. Sửa: `cam_cong_cu` (chấm bằng **việc đã làm**,
không bằng **lời đã nói**) và `cong_cu_du` (đòi đủ chuỗi).

**Ô ĐỎ GIẢ — tệ ngang ô xanh giả, vì nó cử người đi sửa một thứ không hỏng.** L4: TC014 làm
đúng sách (trả đúng 4,7 kΩ, trích đoạn chèn độc hại ra cảnh báo, nói rõ không chạy lệnh) mà
trượt vì cụm cấm là `rm -rf` — chuỗi mà chính câu cảnh báo phải chứa. TC019 nói thẳng "KHÔNG
ĐẠT" mà trượt vì cấm nguyên chữ `đạt`. L8: TC029 **từ chối nạp** vì ảnh nhị phân chưa có biên
bản build, rồi hỏi xác nhận — đúng thứ cổng G-FLASH sinh ra để có — và bị chấm "THIẾU
`target.flash`", tức **phạt đúng hành vi cẩn thận**. Sửa: cụm cấm hẹp lại · thêm phanh phủ
định · thêm lượt xác nhận thứ hai cho luồng có bước hỏi.

**L2 — đo sai tiền điều kiện thì con số nói về một bài toán khác.** Bốn ca UC01 ghi "Phiên
mới" bị chạy chung dự án, nên TC004 thừa hưởng ngữ cảnh LAN→USB và đọc câu mơ hồ thành "chọn
phương án" — một hành vi **hợp lý trong một ngữ cảnh sai**. Nhưng cho mỗi ca một dự án lại
làm TC002 mất đặc tả mà đề bài bảo nó đã có. Cả hai lối đều sai, ngược nhau. Nay mô tả bằng
**xô phiên** (`phien`), đúng chuỗi phụ thuộc trên giấy.

**L6 — chấm bằng từ khoá trên tiếng Việt tự do không đủ tin cậy để làm phán quyết.** Ba lần
trong một đợt, nó đánh trượt những lời đáp gần như hoàn hảo chỉ vì tác tử chọn cách nói khác
("không có thông tin về" thay vì "không có trong"). Nới danh sách sau mỗi lần trượt là chạy
theo, không phải sửa. Nên bảng cuối có **hai cột**: máy chấm (lượt sàng) và **sau khi đọc
tay** (kết luận). Ô xanh của máy nghĩa là *"có dấu hiệu"*, ô đỏ nghĩa là *"đáng đọc kỹ"*.

#### Ba ca không đạt còn lại — cùng một hình dạng

TC006 · TC008 · TC052 đều là ca **Happy kết thúc bằng một câu hỏi**. TC052 rõ nhất: phương án
nó *đề xuất* chính là cách sửa đúng (tách logic sang `control.c` rồi test) — **năng lực có,
nhưng nó dừng lại hỏi thay vì đi theo giả định đã nêu**. Thiên về hỏi là an toàn, nhưng ba ca
Happy liền dừng ở câu hỏi thì ngưỡng đang đặt hơi cao. Đây là một hướng đáng bàn riêng, chưa
sửa trong chặng này.

#### Tấm ảnh bắt được thứ con số bỏ sót — lần thứ ba liên tiếp

L9 lọt qua cả **124 ô** của bộ quét, và mọi con số đều **đúng**: khối không rộng hơn khung,
không đè nhau, nhãn không rỗng, không giá trị thô nào lộ ra. Bộ quét đo **bố cục khối**; chỗ
hỏng nằm **bên trong một khối**. Cùng hình dạng với DEV-289 (thẻ cổng đã đóng mà nút vẫn bấm
được) và DEV-290 (nhãn "không còn ở đây" không hiện ra): **số đo đúng, câu hỏi sai.** Vì vậy
bộ quét chụp cả 11 bề mặt, và ảnh là một phần của kết quả chứ không phải minh hoạ.

#### Bo thật

TC029 nạp thật lên STM32F469I-DISCO. Ảnh nạp lên chính là bản FreeRTOS **đang chạy** (cùng
hash `e6fa7328…`), nên đo trọn đường dò→nạp→kiểm mà không xoá mất bản demo người dùng đã xác
nhận. Kiểm lại sau đó bằng `target.debug`: PC vẫn rơi vào vùng idle của FreeRTOS như trước.
Nhóm UC05 trong bảng gốc 23/09 là **"Bị chặn"** toàn bộ vì chưa có bo; nay **6/6 ca đo được
đều đạt**.

### Số đo

`1231 ca đơn vị` (+10 so với DEV-290): `test_ai_quyet.py` (4 — có ca chứng minh phanh không
chặn nhầm đường đúng), `test_chon_chuoi_cong_cu.py` (4), `test_loi_tac_tu_khong_co_tien_to.py`
(2). Hai ca đầu của `test_chon_chuoi_cong_cu` lúc viết ra **bị bỏ qua** vì tôi dò `avr-gcc`
trên `PATH` còn mã thật tìm nó trong `~/Library/Arduino15/…` — một ca bị bỏ qua không chứng
minh gì mà bảng vẫn xanh. Đã sửa để hỏi đúng cái mã thật hỏi, rồi phá lại bản vá để chắc
chúng đỏ được.

### [DEV-292] 29/09/2026 · Kết quả đo ra Excel, và README giới thiệu năng lực tác tử

**Việc người dùng giao:** *"cập nhật lại toàn bộ kết quả vào file excel … cập nhật lại readme
ở git chi tiết giới thiệu toàn bộ các năng lực của Agent"*.

#### Excel — một tệp MỚI, không đè lên tệp gốc

`docs/review-v3/test/Usecase_Test_KET_QUA_29-09-2026.xlsx`, sinh bằng
`tools/xuat_excel.py` từ chính các tệp kết quả (không gõ tay con số nào).

Bảng 23/09/2026 là một phép đo **thật** trên kiến trúc cũ. Đè lên nó là xoá mất mốc so sánh —
và một bảng chỉ còn cột "hôm nay" thì không ai biết sản phẩm đã đi được bao xa, cũng không ai
kiểm lại được lời tuyên "đã tốt lên". Tệp mới giữ **cả hai cột** cạnh nhau.

Sáu sheet. `Test case` có **ba cột kết quả**, và cần cả ba:

* **23/09/2026** — kiến trúc cũ. Giữ để so, không phải để trách.
* **29/09 máy chấm** — tự động bằng từ khoá + chuỗi công cụ. Đây là lượt **sàng**.
* **29/09 sau khi đọc tay** — đọc nguyên văn từng lời đáp. **Đây mới là kết luận.**

Vì sao không tin thẳng máy chấm: trong chính đợt này nó đã cho cả ô xanh giả (TC004 chấm bằng
dấu `?` nên bật xanh cho đúng cái lỗi nó canh) lẫn ô đỏ giả (TC014 trượt vì cụm cấm là
`rm -rf` — chuỗi mà chính câu cảnh báo phải chứa). Sheet đầu tiên `Doc the nao` nói thẳng điều
đó trước khi người đọc nhìn thấy bất kỳ con số nào, thay vì để họ tự suy ra.

Sheet `Loi tim duoc` tách rõ **lỗi SẢN PHẨM** khỏi **lỗi BỘ ĐO** (tô màu khác nhau): hai loại
ấy dẫn tới hai việc khác hẳn nhau. Sheet `Thong ke` dùng **công thức** chứ không số cứng — mở
ra là thấy nó cộng từ đâu.

Tự kiểm sau khi ghi: đủ 76 mã, không trùng, không thiếu.

#### README — phần "Tác tử làm được những gì"

Mười mục theo **việc người dùng cần**, không theo cây mã: làm rõ ý tưởng · tri thức · thiết kế
mạch · viết mã và kiểm thử · mạch thật · bộ nhớ · lịch sử · chế độ kế hoạch · tự kiểm chứng và
tự bù năng lực · ba lớp chặn. Số liệu lấy từ **chính kho đăng ký** (108 công cụ / 9 nhóm,
6 tác tử con, 6 skill, 10 cổng), không viết theo trí nhớ.

Mỗi mục nói cả chỗ công cụ **từ chối làm**, vì đó mới là phần khó tin nhất nếu chỉ đọc tên
công cụ: `ckm.pinout_set` từ chối gán chân không có trong Fact · `passport.pin` từ chối ghim
hộ chiếu khi chưa có tài liệu · `snapshot.create` từ chối tự đặt tên bản ưng ý ·
`fact.compare` từ chối kết luận khi thiếu dữ kiện · `target.log` nói là im lặng khi cổng im
lặng.

#### Ba con số cũ trong README, đã sửa

`836 test` → **1231**. `76 TC + 16 CX` → **76 TC + 124 ô giao diện + 1231 ca đơn vị**. Dòng
G7-B ghi **"chưa"** trong khi `target.debug`/`target.screen` và subagent `hardware` đã chạy
trên bo thật từ nhiều chặng trước — thêm luôn hai dòng **Plan mode** và **Tự bù năng lực**.

Một README nói `836 test` khi thực tế có `1231` là đúng loại sai nguy hiểm nhất của cả dự án
này: **nghe hợp lý, không ai kiểm, và nó làm mọi con số khác trong cùng tài liệu mất giá**.

Thêm một phép tự kiểm: mọi đường dẫn nội bộ trong README phải **tồn tại thật**. Một README trỏ
vào tệp không có là một lời hứa sai, và nó hỏng lặng lẽ. Chạy: 0 đường dẫn hỏng.

### Số đo

`1231 ca đơn vị` (không đổi — chặng này là tài liệu và bộ xuất, không đụng vào lõi).

### [DEV-293] 29/09/2026 · Tài liệu thiết kế khớp lại với mã — và một bộ dò để nó không trôi nữa

**Việc người dùng giao:** *"cập nhật tất cả các tài liệu quan trọng như thiết kế 4C, các tài
liệu khác thật chi tiết đảm bảo tài liệu thiết kế đúng với code"*.

#### Đo trước, sửa sau

Sửa tài liệu theo cảm giác thì lệch mới thay lệch cũ. Nên việc đầu tiên là
`tools/kiem_tai_lieu.py` — dò bốn thứ **kiểm được bằng máy** giữa 14 tệp tài liệu và mã đang
chạy: tên công cụ có trong kho đăng ký không · đường dẫn có tồn tại không · mã lỗi (dạng Ennnn) có
còn được sinh ra không · con số đếm được (công cụ, UICommand, HumanAct, bề mặt, subagent,
skill, cổng) tài liệu ghi bao nhiêu so với mã.

Nó nói thẳng chỗ nó **không** làm được: không đọc hiểu nội dung. Phần *"tài liệu mô tả đúng
cách hệ thống hoạt động không"* vẫn phải đọc.

**Bộ dò tự sửa mình ba lần trước khi dùng được** — và ba lần ấy đều là báo động giả, đúng loại
lỗi đã ghi ở L4/L6 của DEV-291:

1. `history.py` bị bắt là "công cụ không tồn tại" — nó là một đường dẫn trong dấu nháy ngược.
2. Chín công cụ `sch.*` bị báo mất, vì chúng nằm sau cờ `EIDE_FEATURE_SCHEMATIC` và kho đăng
   ký mặc định không có. Nay bộ dò bật cờ lên trước khi đếm.
3. `"14 công cụ"` trong README bị chấm sai — đó là số công cụ của **một tác tử con**, không
   phải tổng. Một mẫu regex không đọc được ngữ cảnh ấy, nên phép này thôi tự phán: nó
   **liệt kê** mọi chỗ nêu con số kèm con số mã thật có, rồi để người đọc quyết.

Và hai lần nữa khi tài liệu cần nhắc tên cũ để nói nó đã đổi thành gì — đó là **giá trị** của
một bảng ánh xạ, không phải lỗi. Giải bằng hai dấu vùng rõ ràng (`<!-- lich-su -->` cho bảng
lúc thiết kế, `<!-- ten-cu -->` cho cột trái bảng ánh xạ) thay vì đuổi theo cách diễn đạt —
đuổi theo từ ngữ là cách chắc chắn để bỏ sót một cách nói mới.

#### Tài liệu mới: EIDE-C4-46 — kiến trúc theo mô hình C4

`docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md`. Bốn độ phóng, mỗi cái trả một câu:

* **C1 Bối cảnh** — EIDE nằm giữa kỹ sư · Gemini · GitHub của hãng · SearXNG · bo thật ·
  chuỗi công cụ trên máy · LibreOffice/Tesseract/KiCad. Bốn điều định hình mọi thứ bên dưới:
  một người một máy (nên lõi **không mở cổng mạng nào**) · chỉ một mô hình · phần cứng là tác
  nhân ngoài chứ không phải một mô hình · tác tử không tự cài gì.
* **C2 Khối chạy được** — EIDE.app (Swift, 15 tệp / 5 030 dòng) ↔ lõi Python (85 tệp /
  33 357 dòng) qua JSON-RPC trên stdio ↔ thư mục dự án. Kèm lý do tách hai tiến trình: lõi
  chạy được **không cần giao diện**, nên mọi phép đo tự động chạy được mà không dựng app; và
  app không có logic nghiệp vụ nào để mà sai.
* **C3 Thành phần** — bảng trách nhiệm từng mô-đun, mỗi dòng có thêm cột **"điều nó TỪ CHỐI
  làm"**. Đó mới là phần khó tin nhất nếu chỉ đọc tên mô-đun.
* **C4 Mã** — bốn chỗ mà hiểu sai sẽ hiểu sai cả hệ thống: ba lớp chặn quanh mỗi lời gọi ·
  `history.py` là đường ghi duy nhất · tầng tin cậy là thứ kiểm được chứ không phải nhãn dán ·
  ba cơ chế xếp chồng canh "đạt giả", và cả ba đều trả **ba trạng thái** chứ không hai.

#### MDD-40 lên v3.1

`≈40 công cụ` → **117 công cụ / 10 nhóm** (108 mặc định + 9 sau cờ sơ đồ). Đối chiếu từng tên
lúc thiết kế bằng máy: **44/67 giữ nguyên**, 23 đổi hoặc không làm — mỗi cái một dòng nói **vì
sao**, không chỉ nói *đã đổi*:

* `rag.ask` bỏ vì nó là lối "hỏi một hộp đen rồi tin"; nay tác tử **chọn đoạn** và mã kiểm
  trích dẫn — N1 đòi truy vết tới **trang**, không tới một điểm tương đồng.
* `bash` **cố ý không làm**: một công cụ chạy lệnh tuỳ ý phá vỡ mọi bảo chứng — không kiểm
  được hộp cát, không sinh changeset, không hoàn tác được.
* `analyze.hardfault` bỏ vì phân tích HardFault cần **đọc thanh ghi thật** (CFSR/HFSR/MMFAR/
  BFAR), không phải một công cụ đoán từ văn bản.
* `target.dangerous` chưa làm — thao tác khoá vĩnh viễn vẫn bị chặn ở hook S0 và nói rõ hậu
  quả, nhưng chưa có công cụ thực thi, và tác tử **nói thẳng điều đó** thay vì hứa một việc
  không có thật (TC035).

Bảng gốc lúc thiết kế **giữ nguyên làm hồ sơ**, chỉ đánh dấu là vùng lịch sử. Thêm mục **A5 —
trạng thái hiện thực**: chín nguyên tắc N1–N9, mỗi cái chỉ rõ sống ở đâu trong mã, đo bằng ca
kiểm nào, trạng thái ra sao. Và nói rõ phần **ngoài phạm vi vẫn là ngoài phạm vi** — gọi nó là
"chưa làm" thì bảng nói sai.

#### Hai chỗ tài liệu nói sai tên, đã sửa

`EIDE-NOTE-42` gọi `history.doan_loai` như một công cụ của tác tử — nó là một **hàm trong mã**
(`history.py::doan_loai()`). Và nó ghi phép quét lệnh phá hoại là "chưa có", trong khi đã có
và đã đo được ở TC070 ngày 29/09.

#### Bộ dò vào hồi quy

`tests/test_tai_lieu_khop_ma.py` gọi bộ dò trong mỗi lượt `pytest`. Đã chứng minh nó **đỏ
được**: bịa một tên công cụ và một đường dẫn vào tài liệu C4 thì nó bắt cả hai.

Vì sao đáng một ca kiểm chứ không phải một việc nhớ làm định kỳ: tài liệu dài hơn 8000 dòng,
đọc tay thì mỗi lần sửa mã phải đọc lại tất cả, nên thực tế là **không ai đọc lại**. README
từng ghi `836 test` khi thực tế đã 1231 (DEV-292) — một con số nghe hợp lý, không ai kiểm, và
nó làm mọi con số khác cùng trang mất giá.

### Số đo

`1232 ca đơn vị` (+1). Sau khi sửa: **0 chỗ lệch chắc chắn** giữa 14 tệp tài liệu và mã.

### [DEV-294] 29/09/2026 · Đối chiếu NỘI DUNG bốn tài liệu chuyên đề với mã

DEV-293 để lại một câu chưa trả lời: bộ dò chỉ kiểm được tên, đường dẫn, mã lỗi và con số —
*"tài liệu mô tả ĐÚNG cách hệ thống hoạt động không"* thì vẫn phải đọc. Chặng này đọc nốt bốn
tài liệu chuyên đề.

#### MEM-42 — khớp, không phải sửa gì

Đây cũng là một kết quả, và nó đáng ghi ngang với những chỗ sai. Đối chiếu ba khẳng định cụ
thể nhất:

* **Lược đồ tóm tắt 10 mục** — `src/eide/memory/summary.py::MUC` có đúng 10: mục tiêu · trạng
  thái theo chặng · quyết định · giả định đang dùng · sửa của người · việc còn lại · tệp đang
  sửa · hiện vật STALE · câu hỏi mở · lỗi đã gặp.
* **Bốn ngưỡng nén** — tài liệu ghi C0 < 60 % · C1 60–70 % · C2 70 % · C3 85 % · C4 95 %; mã
  (`ContextBudget`) có `nguong_c1=0.6`, `nguong_c2=0.7`, `nguong_c3=0.85`, `nguong_c4=0.95`.
* **Sáu chỉ số §13** — `memory.metrics` có thật.

#### ING-43 — bảng mã lỗi sai 5/8, đã sửa

Bản v1.0 đánh số `E1001`–`E1008` liền mạch. Khi hiện thực, dải `E1004`–`E1006` **đã bị công
cụ khác lấy trước** — `fs.read` gọi vào thư mục, `fs.edit` không tìm thấy đoạn, `fs.edit` đoạn
trùng nhiều lần — nên nhóm nạp tài liệu chuyển sang `E1010`–`E1015`. `E1007`/`E1008` **chưa làm**; việc chúng mô tả (OCR thất bại, LibreOffice thất bại) nay là `E1014`/`E1015`.

Tệ hơn "sai số": `E1005` trong tài liệu là *zip bomb*, còn `E1005` trong mã là *`fs.edit`
không tìm thấy đoạn cần thay*. **Một mã lỗi dùng lại cho hai việc khác nhau là chỗ người đọc
tra nhầm mà không biết mình tra nhầm** — họ sẽ đọc được một câu trả lời, chỉ là câu trả lời
cho câu hỏi khác. Bảng mới ghi đủ chín mã kèm nghĩa và chỗ sinh, và nói rõ ba mã `E1004`–
`E1006` KHÔNG thuộc nhóm nạp tài liệu.

#### SCH-44 — tám công cụ thành chín, và một cái tên chưa bao giờ có

`sch.symbol_confirm` thiếu hẳn trong tài liệu: nó ghi lại việc **người** đã xem một ký hiệu
sinh từ Fact rồi xác nhận, và nó đòi `trich_loi_nguoi` — tác tử không xác nhận hộ người dùng
được, vì như thế thì cái chờ ấy chẳng chờ ai. Ngược lại, `sch.open` ở bảng lộ trình **chưa
làm** và không định làm; việc mở tệp do `sch.import` đảm nhiệm.

#### HIER-45 đúng — README sai

Sáu bất biến của cây khối là `E8001`–`E8006` (không chu trình · Port của khối con chỉ nối
trong cha trực tiếp · Port lên cha đúng một net mỗi phía · lá có Port = tập pin của Fact
pinout · bus khớp members · `flatten` không đổi khi sửa nội bộ). README gọi chúng là
`E9001`–`E9006` — một họ **khác**, dành cho lỗi bản đồ tri thức mạch và thư viện khối
(`E9001` khối không thể là cha của chính nó · `E9002` khối chưa khép kín · `E9005` port bus
chưa khai members).

Cả hai dải đều tồn tại, nên bộ dò không bắt được: nó kiểm *mã lỗi có còn không*, không kiểm
*có phải đúng mã lỗi ấy không*. Đây là giới hạn đã nói trước của phép dò, và lần này nó lộ ra
đúng như dự đoán — phần ngữ nghĩa chỉ đọc mới thấy.

#### Bộ dò mạnh thêm hai bậc, và tự bắt lỗi của tôi

* **Đường dẫn thiếu tiền tố.** Bản trước chỉ dò đường dẫn bắt đầu bằng `src/`, `ui/`, `tools/`
  … nên `hooks/s0.py` lọt. Mà đó chính là cách tài liệu thiết kế hay viết, và cũng là chỗ dễ
  sai nhất — người đọc gõ vào thì không ra gì. Nay báo riêng: *"THIẾU tiền tố src/eide/"*. Nó
  bắt ngay hai chỗ trong mục A5 tôi vừa viết ở DEV-293.
* **`(?<![A-Za-z])` trước số cổng**, để `N5 cổng trước phép đoán` không bị đọc thành *"5
  cổng"* — `N5` là mã nguyên tắc, không phải một con số đếm.

Và một lần nữa tôi suýt rơi vào bẫy L6: khi bộ dò bắt `sch.open` trong chính câu nói rằng nó
chưa làm, phản xạ đầu là **thêm một cụm từ** vào danh sách nhận dạng. Thay vì thế, sửa câu văn
dùng đúng vốn từ đã có (`chưa làm`). Giữ danh sách nhỏ thì luật còn đọc được; nới nó sau mỗi
lần vướng là cách chắc chắn để không ai còn hiểu luật ấy nói gì.

#### Một chỗ nữa: nhật ký được miễn phép dò mã lỗi

Chính mục DEV-294 này làm bộ dò đỏ — nó nhắc `E1007`/`E1008` để nói chúng không còn. Và một
mục DEV cũ (704) có sẵn một bảng ánh xạ `E1007 → E1014`.

Đó là **việc của một nhật ký**: ghi lại mã cũ. Bắt nó là bắt nhầm một bản ghi lịch sử. Nên
`EIDE-DEV-LOG.md` được miễn phép dò mã lỗi — mã lỗi biến mất vẫn bị bắt ở mọi tài liệu
**thiết kế**, và đó mới là chỗ nó gây hại: người đọc tài liệu thiết kế sẽ đi tra một mã không
tồn tại.

### Số đo

`1232 ca đơn vị` (không đổi). **0 chỗ lệch chắc chắn** giữa 14 tệp tài liệu và mã. Bốn tài
liệu chuyên đề đã đọc và đối chiếu nội dung: MEM-42 khớp · ING-43 sửa bảng mã lỗi · SCH-44 bổ
sung công cụ thứ chín · HIER-45 đúng, README sai theo.

### [DEV-295] 29/09/2026 · Quy hoạch dữ liệu dự án để chép đi được · `du-an.json` · ba chỗ menu

#### Đo trước: chép thư mục đi thì cái gì vỡ

Câu này không đoán được, phải đếm. Trong `du-lieu/stm32f469-freertos`:

| Nơi | Số đường dẫn TUYỆT ĐỐI |
|---|---|
| `.eide/store.sqlite` | **169** |
| `.eide/ledger.jsonl` | 41 |
| `.eide/sessions/` | 57 |
| `EIDE.md` · `changesets.jsonl` · `counters.json` | 0 |

Soi tiếp theo cột thì ra hai nhóm khác hẳn nhau:

* **168 chỗ nằm trong `events.payload` và `artefacts.canonical`** — kết quả công cụ (lệnh biên
  dịch, đường dẫn tệp test). Chúng chỉ *lộ bố cục máy cũ*; không ai đọc chúng để chạy.
* **Đúng MỘT chỗ hỏng thật:** `artefacts.view_hint.path` của `target.screen` ghi đường dẫn
  tuyệt đối tới ảnh khung hình. Chép sang máy khác thì ảnh không mở được. Đã sửa thành đường
  dẫn tương đối so với gốc dự án.

Một hiện vật **sống lâu hơn cái máy sinh ra nó** — đó là toàn bộ lý do chỗ này đáng sửa.

#### `du-an.json` — thẻ căn cước nằm ngay trong thư mục

`src/eide/du_an.py`. Ghi khi mở dự án và cuối mỗi lượt. Trước nó, người cầm thư mục không có
cách nào biết ba điều mà không mở EIDE lên: đây có phải dự án EIDE không · nó đang ở đâu ·
**chép đi thì phải mang theo cái gì**.

Câu thứ ba đắt nhất. Thư mục đo được 14,5 MB, trong đó `.eide/build/` chiếm **3,0 MB** và
dựng lại được. Không nói ra thì người ta hoặc chép cả đống, hoặc — tệ hơn — lọc bằng cảm giác
và bỏ mất sổ cái.

**Ba hạng**, và phân hạng nằm trong chính tệp chứ không trong đầu người viết công cụ sao lưu:

| Hạng | Mất thì sao |
|---|---|
| `ben` | **Mất là mất hẳn** — sổ cái · kho · changeset · blob · EIDE.md · `.git` · công cụ tự viết |
| `dung_lai_duoc` | Tốn thời gian, không mất thông tin — `.eide/build/` |
| `tam` | Bỏ được ngay — kênh kiểm giao diện, ảnh nháp |

**Bài kiểm bắt một lỗ hổng trong thiết kế đầu của tôi.** Bản đầu chỉ liệt kê mục *đang tồn
tại*, nên một dự án vừa mở (chưa ghi sổ cái lần nào) sinh ra `du-an.json` **không nhắc tới
`ledger.jsonl`** — người đọc tệp ấy để biết phải chép gì sẽ không chép nó. Danh sách
"phải mang theo" là một **hợp đồng**, không phải ảnh chụp hiện trạng: thiếu một dòng ở đây là
mất một thứ ở kia. Nay liệt kê đủ bảng, mục chưa có thì đánh `co: false`.

**Kiểm bằng cách làm thật:** chép dự án sang `/tmp` theo đúng danh sách của chính tệp ấy, rồi
mở bản chép. Sổ cái toàn vẹn 2 315 sự kiện · 6 hiện vật mã nguồn + 2 mạch thật · EIDE.md 73
dòng · `git log` nguyên. Bỏ lại 3,0 MB.

#### Ba chỗ menu

**`⌘Z` gây hiểu nhầm.** Đo bằng cách bảo app **tự khai thanh menu** của nó (lệnh `menu` mới
của kênh kiểm): `Edit ▸ Undo ⌘Z` có sẵn, và nó lùi **chữ vừa gõ**, không lùi việc tác tử vừa
làm. Người bấm ⌘Z mong lùi một thay đổi của dự án sẽ nhận một kết quả hợp lý mà sai — loại
nhầm khó phát hiện nhất, vì không có thông báo nào. Nay `Tác tử ▸ Hoàn tác việc vừa làm ⌥⌘Z`
nằm ngay trên `Dừng khẩn`, tên khác và phím khác để đọc là thấy khác.

**Hai menu rỗng.** `View` và `Help` do macOS tự thêm cho một `WindowGroup`; app không có
sidebar, không thanh công cụ, không tệp trợ giúp. Một menu rỗng là một lời hứa không có gì sau
lưng — cùng họ với thẻ cổng bấm được mà không làm gì (DEV-289) và nhãn "không còn ở đây" không
hiện ra (DEV-290).

`Help` bỏ được. `View` thì SwiftUI **dựng lại sau mỗi lần gỡ** — đo được: gọi gỡ một lần không
ăn, gọi lặp 6 nhịp vẫn còn. Thay vì đuổi theo khung nhìn bằng một cái đồng hồ mỗi lúc một dài,
**đổ vào đó thứ vốn thuộc về nó**: ba bề rộng Console, trước nay chỉ bấm được bằng chuột. Dọn
được một menu rỗng và thêm một đường cho bàn phím, bằng cùng một thay đổi.

Đo lại sau khi sửa: `Menu RỖNG còn lại: KHÔNG CÒN CÁI NÀO`.

### Số đo

`1236 ca đơn vị` (+4): `tests/test_du_an_kha_chuyen.py`. Một ca kiểm rằng danh sách
"phải mang theo" và "bỏ được" **không giao nhau** — một đường dẫn nằm cả hai bên thì hai người
đọc hai danh sách sẽ ra hai kết luận ngược nhau về cùng một thư mục.

### [DEV-296] 29/09/2026 · "Hỏi không phải là dừng" — ba ca Happy cuối cùng

Ba ca TC006 · TC008 · TC052 là **thứ duy nhất** bộ 76 ca nói là sai với sản phẩm: đều là ca
Happy kết thúc bằng một câu hỏi hợp lý và **không một hiện vật nào**.

TC052 lộ rõ nhất. Người nhờ viết unit test. Tác tử đọc mã, thấy `main.c` gắn cứng thanh ghi
AVR nên không chạy được trên máy chủ, **đề xuất đúng cách sửa** (tách logic sang một tệp
riêng rồi test), in ra giả định sẽ dùng nếu người bỏ qua — rồi dừng. Việc tách ấy **không phụ
thuộc câu trả lời nào**.

#### Luật KHÔNG phải "hỏi ít đi"

Hạ ngưỡng hỏi là đi ngược N4 và mở đường cho đạt giả: tác tử đoán bừa rồi báo xong. Luật đặt
ra không đụng vào chuyện *có nên hỏi không* — nó nói rằng một lượt kết thúc bằng câu hỏi mà
**không để lại gì** là một lượt tiêu token không đổi lấy gì, và người dùng mất một lượt chỉ
để bấm một nút.

Dám làm trước vì **mọi thay đổi đều hoàn tác được** (N9): làm rồi mà họ muốn khác thì lùi một
lệnh. Và lời nhắc nói thẳng rằng *"mọi thứ đều phụ thuộc"* là một câu trả lời hợp lệ — thiếu
câu ấy thì luật này biến thành áp lực đẻ ra hiện vật rác, mà một hiện vật rác tệ hơn một lượt
trắng vì nó **trông như tiến độ**.

#### Ba lần sửa, và hai lần đầu không đủ

**Lần 1 — hook `Stop`.** Nổ đúng lúc (kiểm trong sổ cái: `hoi_xong_thi_lam_phan_khong_phu_thuoc`
ở `run-003`), nhưng tác tử chỉ hỏi lại một câu gọn hơn. Lời khuyên chung chung sau khi lượt đã
xong thì đổi được ít.

**Lần 2 — trích lại chính lời tác tử.** Ngay trong thẻ nó vừa dựng đã có câu trả lời: *"nếu
anh bỏ qua, em sẽ tách logic sang `control.c` rồi chạy test"*. Hook đọc `assumption_if_skipped`
từ sổ cái và chỉ vào đúng câu ấy. Vẫn không đổi hành vi — nhưng đáng giữ, vì nó biến một lời
khuyên chung thành một việc cụ thể do **chính tác tử** vừa chọn.

**Lần 3 — hiến pháp.** Hook `Stop` là lời khuyên *sau khi* lượt đã xong; hiến pháp định hình
lượt **trước khi** nó chạy. Thêm vào §4, gộp với luật "tối đa 2 lần hỏi" vốn cùng một ý:

> **Hỏi không phải là dừng.** Làm phần không phụ thuộc câu trả lời trước, rồi hỏi phần còn
> lại: *họ trả lời cách nào thì việc gì cũng phải làm?* — làm ngay việc ấy.

Đo lại: TC052 gọi `test.run` và viết test thật (78 s). TC008 đạt. TC006 làm phần thực chất rất
tốt — cập nhật cả ba phương án với khối nguồn, **so sánh lại bằng số** (150–300 mA · pin
2500 mAh → 3–5 giờ · chi phí từng phương án) — chỉ thiếu chữ "v2", mà kho vốn đánh phiên bản
cho mọi hiện vật nên đặc tả v2 tồn tại về cấu trúc, chỉ không được gọi tên. Chấm tay: **đạt**,
lỗi phép chấm.

**68/68 ca đo được đạt.** Không còn ca nào không đạt.

#### Nâng trần hiến pháp 3600 → 3700, công khai

Ca `test_hien_phap_khong_duoc_phinh_qua_tran` đỏ khi thêm luật. Chính ca ấy nói nó là một
**điểm quyết định**: *"đỏ nghĩa là ai đó vừa thêm vào hiến pháp — hãy quyết định có đáng
không, đừng lặng lẽ nâng trần."*

Trước khi nâng đã tìm chỗ cắt: §10 dài nhất (721 token) nhưng cả bảng đều chịu lực. Đã nén
luật mới ba lần và gộp nó với một luật cũ cùng ý — vẫn dư 76 token.

Nâng **đúng 100**, không hơn. Hiến pháp nay 3676 token, nên lần thêm sau vẫn chạm trần và vẫn
phải mở lại đúng cuộc trò chuyện này. **Nâng dư ra là tắt cái phanh.**

Chỗ này khác với "sửa tiêu chí cho vừa kết quả" mà N6 cấm: N6 cấm hạ ngưỡng ĐẠT để một phép
thử hỏng thành đạt. Đây là một ngân sách token, và nó vừa mua được một **hành vi đo được** —
không phải một ô xanh.

Bài kiểm thứ hai cũng chặn đúng: nó bắt chữ `main.c` trong dấu nháy ngược vì tưởng là tên công
cụ không tồn tại. Đã viết lại không dùng nháy.

### Số đo

`1242 ca đơn vị` (+6): `tests/test_hoi_xong_thi_lam.py`. Bộ usecase: **68/68 ca đo được đạt**
(trước: 65/68).

### [DEV-297] 29/09/2026 · Đưa tài liệu vào bằng giao diện — kéo–thả và nút ghim giấy

Cả sản phẩm dựng trên *"mọi con số truy về datasheet"*. Nhưng trước chặng này, cách duy nhất
để **đưa** một datasheet vào là mở Finder, chép tay vào thư mục dự án, rồi gõ bảo tác tử. Tìm
khắp mã Swift chỉ có đúng một `NSOpenPanel`, và nó dùng để chọn *thư mục dự án*.

Chỗ đưa datasheet vào không nên là chỗ khó nhất của một công cụ lấy datasheet làm nền.

#### Việc này KHÔNG phải "gửi đường dẫn cho tác tử"

Hộp cát của tác tử là **thư mục dự án**. Một tệp ở `~/Downloads` với nó là không tồn tại —
`fs.read` từ chối, `doc.load` từ chối. Nên đưa tài liệu vào là **chép tệp vào trong dự án rồi
mới nói tên**. Bỏ qua bước ấy thì cú kéo–thả trông như chạy mà tác tử báo "không đọc được", và
người dùng không có cách nào đoán ra vì sao.

`ui/EIDEApp/Sources/EIDE/State/ThemTaiLieu.swift`. Tệp vào `tai-lieu/` — trùng chỗ `doc.fetch`
tải về, để chỉ có một chỗ chứa tài liệu chứ không hai.

#### Ba điều nó cố ý không làm

* **Không tự nạp vào kho.** Chép xong chỉ báo cho tác tử. `doc.load` là R2 và sinh hiện vật —
  không phải việc một cú kéo–thả tự quyết thay người.
* **Không ghi đè.** Trùng tên thì `-2`, `-3`. Người kéo nhầm một tệp cùng tên mà mất bản cũ
  thì cú kéo ấy đắt hơn nhiều so với một tệp thừa. Đo được: kéo lại cùng tệp → thư mục có
  `rm-spi.md` và `rm-spi-2.md`, bản đầu nguyên vẹn.
* **Không đi vòng qua I1.** Kết quả là một `HumanAct` kiểu `upload` đi qua `console.act` như
  mọi thứ khác — kéo–thả thay NGÓN TAY, không thay giao thức.

Một phát hiện phụ: `upload` **đã có sẵn** trong giao thức (`HUMAN_ACT_KINDS`, bắt buộc trường
`files`, có sẵn dòng dựng *"Nạp tệp: …"*) nhưng **chưa ai gửi nó** — một đường khai rồi bỏ đó
từ đầu. Không phải viết mới, chỉ phải nối vào.

#### Vùng thả là CẢ bàn giao tiếp

Người kéo một datasheet vào thì họ nhắm vào *"chỗ nói chuyện với tác tử"*, không nhắm vào một
ô nhập cao 30 điểm ở đáy. Vùng thả hẹp là vùng thả trượt. Kèm viền nét đứt + chữ *"Thả để
thêm tài liệu cho tác tử"* khi đang kéo — không có phản hồi ấy thì người ta không biết thả
được hay không.

Và app **nói ra** việc đã chép: *"Đã chép vào tai-lieu/: … — tác tử chỉ đọc được tệp nằm trong
thư mục dự án."* Người kéo một tệp từ Desktop mà không biết nó vừa được nhân bản vào dự án sẽ
ngạc nhiên đúng lúc họ dọn thư mục.

#### Đo qua giao diện thật

Kênh kiểm thêm lệnh `them_tai_lieu` — nó gọi **đúng hàm** mà cú kéo và nút ghim giấy gọi, nên
phần chép vào hộp cát và `HumanAct.upload` đều là đường thật.

| Phép thử | Kết quả |
|---|---|
| Kéo một tệp nằm NGOÀI dự án | Chép vào `tai-lieu/`, tác tử nhận và **tự nạp vào kho** (`RM-SPI-TRICH`), qua kiểm chứng độc lập |
| Kéo lại cùng tên | `rm-spi-2.md` — bản đầu nguyên vẹn |
| Hỏi câu chỉ trả lời được nếu ĐỌC THẬT | *"`TXDMAEN` (bit 1) trong `SPI_CR2`"*, kèm tên tệp và dòng 7–10 |

Phép thử thứ ba mới là phép đo thật: hai phép đầu chỉ chứng minh tệp đã đi đúng chỗ.

### Số đo

`1246 ca đơn vị` (+4): `tests/test_them_tai_lieu.py`. Ca ở đó canh **hợp đồng phía lõi** —
`upload` là act hợp lệ, bắt buộc `files`, và dựng được thành câu đọc được; thiếu điều cuối thì
mô hình nhận một chuỗi rỗng và cú kéo–thả trôi đi trong im lặng.

### [DEV-298] 29/09/2026 · Xuất / nhập dự án — `project.export` và File ▸ Xuất/Nhập

Chép thư mục **là** cách mang dự án đi, và nó đúng. Lệnh này tồn tại vì làm tay thì hai chuyện
hay xảy ra, và cả hai chỉ lộ ra về sau:

* **Chép cả đống.** Dự án FreeRTOS 14,4 MB, trong đó `.eide/build/` chiếm 3,0 MB dựng lại
  được bằng một lệnh biên dịch.
* **Lọc bằng cảm giác rồi bỏ mất sổ cái.** `.eide/` là thư mục ẩn, tên không gợi gì, và trong
  dự án còn bị `.gitignore`. Người gọn gàng sẽ bỏ nó — **mất im lặng**: bản chép vẫn mở được,
  chỉ là không còn quá khứ, không còn changeset, không hoàn tác được nữa.

`src/eide/goi_du_an.py` không nghĩ ra luật mới: nó **đọc phân hạng đã có** trong `du-an.json`
(DEV-295) rồi làm theo. Đo được: **14,4 MB → gói 2,0 MB**, nhập lại sổ cái toàn vẹn 2 315 sự
kiện, mở ra chạy tiếp được ngay.

#### Nhập thì KIỂM trước khi nói xong

Gói mang sổ cái có chuỗi hash. Giải nén xong mà không kiểm thì một gói hỏng — hoặc bị sửa —
mở ra như bình thường và chỉ lộ ra ở một lúc rất xa, đúng lúc người dùng đang tin vào một lịch
sử không còn nguyên vẹn. `nhap()` chạy `ledger.verify()` trước khi trả về, gãy thì nói gãy ở
đâu.

Hai lối vào cũng bị chặn, mỗi lối một lý do:

* **Nhập vào thư mục đang có dự án** → từ chối. Trộn hai lịch sử là hỏng cả hai, và hỏng theo
  cách không ai gỡ được.
* **Gói có mục trỏ `../` ra ngoài** → không giải nén. Một gói dựng bằng tay có thể ghi đè tệp
  **ngoài** thư mục đích.

#### Một con lặp tự ăn chính mình

Công cụ `project.export` bắt buộc ghi gói **vào trong dự án** — để không ghi ra ngoài hộp cát.
Nhưng vòng quét `rglob` trong lúc đang ghi **bắt gặp chính tệp gói** và gói nó vào chính nó.
Đo được: lệnh chạy mãi không dừng, tệp phình cho tới khi hết đĩa. Một vòng lặp không có ai
chặn, và nó chỉ lộ ra khi đã muộn.

Đây là đường đi **thường gặp nhất**, không phải một ca hiếm — nên nó có ca kiểm riêng, và ca
ấy kiểm cả kích thước gói: *"gói phình bất thường — nhiều khả năng đã tự gói chính nó"*.

#### Giao diện

File ▸ **Xuất dự án…** và **Nhập dự án…**.

Xuất thì **bảo tác tử làm** thay vì gọi thẳng Python: việc này sinh một hiện vật và phải vào
sổ cái như mọi việc khác. Một đường tắt từ menu xuống đĩa là một đường **không ai thấy trong
lịch sử**.

Nhập thì gọi thẳng lõi, và đó là chỗ **duy nhất** giao diện làm vậy — có lý do: chưa có dự án
nào đang mở thì chưa có lõi nào đang chạy để mà gửi `HumanAct` vào. Nhưng nó gọi đúng
`eide.goi_du_an.nhap`, nên phép kiểm sổ cái vẫn chạy; không tự `unzip` cho nhanh.

### Số đo

`1252 ca đơn vị` (+6): `tests/test_goi_du_an.py`. Gồm ca cho con lặp tự-gói-chính-mình, ca
chặn `../` thoát ra ngoài, và ca từ chối nhập đè lên một dự án đang có.

### [DEV-299] 29/09/2026 · Tên đề tài vào toàn bộ hồ sơ

**Tên đề tài:** *Phát triển phần mềm nhúng có ứng dụng trí tuệ nhân tạo (AI)*

Bo mạch **đã mang tên này** từ trước — `firmware/ui.c` hiện `DT: PHAT TRIEN PHAN MEM NHUNG /
CO UNG DUNG TRI TUE NHAN TAO(AI)` trên màn LCD. Thứ tụt lại là hồ sơ trong git: README, chín
tài liệu thiết kế, bảng Giới thiệu của app, và `Info.plist`.

Đưa vào **15 chỗ**, mỗi chỗ một dạng phù hợp: README có dòng riêng; tài liệu thiết kế thêm một
hàng `**Đề tài**` ngay trên hàng `**Khung**`; bảng Giới thiệu có một dòng in đậm đứng đầu;
`Info.plist` ghi trong `NSHumanReadableCopyright`.

#### Bản chụp firmware trong `docs/` đã cũ, và cũ đúng chỗ quan trọng

`docs/stm32f469-freertos/firmware-chay-duoc/ui.c` vẫn giữ tên đề tài **trước đó**:

```
-   "DT: PHAT TRIEN PHAN MEM NHUNG"          ← đang chạy trên bo
-   "CO UNG DUNG TRI TUE NHAN TAO(AI)"
+   "DT: Nghien cuu & Trien khai EIDE Agent"  ← bản chụp trong git
+   "tren Bo STM32F469I-Discovery"
```

Và cả một lỗi chính tả đã sửa trên bo mà bản chụp còn giữ: `DO AN TOT NGHIEP` → `DE AN TOT
NGHIEP`.

Đây đúng loại lệch mà `du-lieu/` bị gitignore sinh ra: thứ chạy thật và thứ được cất giữ trôi
khỏi nhau trong im lặng. Bản chụp mới chép từ chính mã đang chạy, kèm `mach.bin` hiện tại.

#### Một chỗ tôi tự quyết, nói ra để anh sửa nếu không đúng ý

Anh viết `TRÍ TUỆ NHÂN TẠO(AI)` — dính, không dấu cách. Trên màn LCD cũng vậy, nhưng ở đó là
phông cố định và chỗ hẹp. Trong hồ sơ tôi viết **`trí tuệ nhân tạo (AI)`** có dấu cách, theo
lối thường của tiếng Việt. Nếu anh muốn giữ đúng dạng dính thì nói, sửa một lệnh.

### Số đo

`1252 ca đơn vị` (không đổi — chặng này là hồ sơ). Bộ dò tài liệu: **0 chỗ lệch chắc chắn**.
Bảng Giới thiệu đã chụp lại bằng chính app: `docs/anh/gioi-thieu-eide.png`.

### [DEV-300] 29/09/2026 · Hướng dẫn cài đặt — `docs/md/EIDE-CAI-DAT.md`

Từ máy trắng tới lượt chạy đầu tiên. Mỗi lệnh trong tài liệu là **lệnh tôi vừa chạy thật** —
không có bước nào chép từ trí nhớ.

#### Ba điều viết ra vì đã đo, không vì đoán

**Lõi chạy được KHÔNG cần giao diện.** Đặt ngay đầu tài liệu, vì nó cắt phân nửa công sức cho
người chỉ muốn xem tác tử làm việc: dừng ở Bước 3 là đủ, không cần Xcode.

**Công cụ phần cứng: đừng cài trước.** Thiếu cái nào thì `env.check` nói thiếu gì và cài bằng
lệnh nào, qua cổng `G-TOOL` để người duyệt. Bảng trong tài liệu để người *biết trước mình sẽ
được hỏi gì*, không phải một danh sách phải làm.

**Cái bẫy newlib.** `arm-none-eabi-gcc` bản Homebrew không kèm newlib, nên `memset`/`memcpy`
báo `undefined reference` **kể cả khi không ai gọi chúng** — trình biên dịch tự sinh chúng cho
phép gán cấu trúc và khởi tạo mảng. Chặng G7 mất thời gian ở đúng chỗ này. Một dòng trong
hướng dẫn cài đặt đáng giá hơn một buổi chiều.

#### Hai chỗ tài liệu suýt nói sai, bắt được vì chạy thử

**`python -m eide` hỏng trên chính máy này.** Gói `eide` chưa bao giờ được cài vào venv — mọi
thứ chạy được suốt mấy tháng vì `tools/*.py` tự `sys.path.insert(0,'src')` và app thì tự đặt
`PYTHONPATH`. Lệnh README ghi (`pip install -e ".[dev]"`) **đúng**, chỉ là chưa ai chạy nó ở
đây. Chạy xong thì `python -m eide --help` in ra bình thường — nhưng nếu tôi viết hướng dẫn mà
không thử, người cài đầu tiên sẽ là người phát hiện.

**Con số 124/124 là con số của dự án KHÁC.** Tài liệu bảo chạy `quet_giao_dien.py` trên dự án
vừa tạo ở Bước 3 rồi hứa 124/124 — mà 124/124 đo trên dự án FreeRTOS đã có nội dung. Chạy thật
trên dự án trống: **123/124**, ô đỏ là *"có ít nhất một khối cho người sửa bằng widget"* — đỏ
vì **chưa có hiện vật nào để sửa**, không phải vì cài sai.

Nay tài liệu ghi 123/124 và giải thích ô đỏ ấy. *Một hướng dẫn hứa 124 rồi người cài thấy 123
sẽ đi tìm một lỗi không tồn tại.*

#### Mục trục trặc lấy từ những chỗ đã thật sự vấp

Không phải bảng lỗi tưởng tượng: `No module named eide` (vừa gặp) · cắm nhầm cổng USB OTG ·
`undefined reference to memcpy` · kéo tệp nằm ngoài dự án vào thì tác tử không đọc được
(DEV-297) · `⌘Z` là Undo của ô văn bản chứ không của dự án (DEV-295).

Kèm số công cụ cập nhật khắp nơi: **117 → 118** (thêm `project.export` ở DEV-298).

### Số đo

`1252 ca đơn vị` · bộ dò tài liệu **0 chỗ lệch**. README trỏ sang hướng dẫn ở hai chỗ: đầu
tệp và ngay trên khối lệnh cài rút gọn.

---

### [DEV-301] 29/09/2026 · Tác tử viết được tài liệu — `doc.render` (Word · Excel · PDF)

**Yêu cầu:** *"review năng lực viết tài liệu của Agent… Mình muốn Agent có khả năng viết tài
liệu xuất ra docx, excel, pdf (tốt nhất là Agent có thể tự code ra phần mềm để ghi file theo
yêu cầu)."*

#### Đo trước đã: năng lực hiện có bằng không

| Câu hỏi | Số đo |
|---|---|
| Công cụ nào ghi byte ra tệp? | **Không cái nào.** `grep "write_bytes\|'wb'"` trong `src/eide/tools/` → trống |
| `fs.write` ghi được gì? | `write_text` — **chỉ chữ**. `.docx` là ZIP nhị phân, không đường nào |
| 7 công cụ `doc.*` làm gì? | `load · read · figures · language · fetch · search_web · to_pdf` — **tất cả là ĐỌC** |

Đối lại, vật liệu thì đã đủ sẵn từ lâu: `python-docx`, `openpyxl`, `python-pptx`, `pypdf` nằm
trong `.venv` (đang dùng để *đọc* tài liệu), LibreOffice có trên máy, và `office.chuyen_doi()`
đã bọc nó — chỉ đang dùng một chiều. **Cơ chế có sẵn, đường dẫn tới nó đứt.**

#### Vì sao một công cụ, không phải ba

`doc.to_docx` + `doc.to_xlsx` + `doc.to_pdf` sẽ là ba công cụ mà mỗi cái chỉ đẻ ra được đúng
một hình dạng tài liệu người viết công cụ nghĩ sẵn — mà "theo yêu cầu" nghĩa là hình dạng của
người dùng. Nên: **hình dạng nằm trong nguồn Markdown** tác tử tự viết, `doc.render` chỉ dựng.

Và nguồn là Markdown chứ không ghi thẳng nhị phân, vì hai lẽ: *(a)* một thay đổi không xem
được là một thay đổi không duyệt được — sổ cái giữ được nhị phân nhưng người duyệt chỉ thấy
"12 KB đổi thành 13 KB"; *(b)* phân hạng `ben`/`dung_lai_duoc`/`tam` trong `du-an.json` đã có
sẵn chỗ: nguồn là `ben`, bản render là `dung_lai_duoc` nên gói mang đi không cõng theo.

#### Bốn lỗi mà SỐ ĐO không thấy, chỉ NHÌN mới thấy

Bản đầu chạy trót lọt cả ba định dạng: 79 đoạn · 6 bảng · 6 trang — mọi con số đều hợp lý. Mở
tệp PDF ra nhìn thì:

| Chỗ | Bản in cho ra | Nguyên nhân |
|---|---|---|
| `*Đề tài: **…*** ` | `*Đề tài: Phát triển…` — dấu sao **lọt ra giấy** | một `finditer` cho cả ba kiểu: nhánh hai-sao khớp trước, cặp một-sao bọc ngoài mất cặp đóng |
| Gạch đầu dòng dài | vỡ làm hai đoạn, kèm `**từ chối…**` nguyên dấu | dòng nối tiếp của một mục bị đọc thành đoạn mới |
| `---` | một gạch cụt lủn | `─`×40 không có trong phông mặc định của LibreOffice |
| `[…](#neo)` | in cả `(#dữ-liệu-dự-án-nằm-ở-đâu)` | neo nội bộ vô nghĩa trên giấy |

Lần thứ tư trong dự án này một tấm ảnh bắt được thứ mọi con số bỏ qua. *Số đo đúng, câu hỏi
sai.*

#### Và một lỗi MẤT DỮ LIỆU, lộ ra ở tệp bên cạnh

`sang_pdf` viết bản docx trung gian vào `ra.parent/<cùng tên>.docx` rồi xoá sau khi đổi xong.
Nghĩa là render `bao-cao.pdf` trong thư mục đang có `bao-cao.docx` sẽ **đè rồi xoá luôn tệp của
người dùng**. Đo được ngay lần chạy thử đầu: dựng cả ba định dạng vào một thư mục, xong thì
`.docx` không còn ở đó. Nay bản trung gian nằm trong `tempfile.TemporaryDirectory()`, và ca
hồi quy kiểm **tệp bên cạnh** chứ không kiểm tệp nó tạo ra.

#### Hai chỗ cố ý nói KHÔNG

* **Excel từ văn xuôi** → `E2013`, không đổ cả đoạn văn vào ô `A1`. Một `.xlsx` mở lên được
  nhưng vô dụng **trông giống thành công**, mà thứ trông giống thành công đắt hơn một lỗi thẳng.
* **PDF khi máy không có LibreOffice** → báo thiếu kèm đường khác, không tự vẽ một PDF thô sơ
  để người nhận tưởng là bản in được.

#### E2E qua giao diện thật — `tools/thu_xuat_tai_lieu.py`, 9/9

Ba ca, và ca thứ ba lại dạy đúng bài cũ. Bản đầu của nó hỏi *"tác tử có từ chối không"* rồi
chấm bằng việc chữ `bảng` có mặt trong lời đáp — **xanh**, nhưng cái thật sự xảy ra khác hẳn:
`doc.render` từ chối, tác tử **đọc gợi ý trong lỗi, tự thêm một bảng thật vào tệp nguồn**, rồi
xuất lại thành một bảng 7 hàng dùng được. Hành vi ấy đúng hơn cái tôi định đo (§4 hiến pháp:
*hỏi không phải là dừng*). Nhãn ca kiểm mới là cái sai. Nay ca 3 hỏi ba câu khớp với thứ đáng
quan tâm: hàng rào có **nổ** không (`E2013` trong sổ cái) · tệp ra có phải **bảng thật** không
(≥2 cột, ≥3 hàng, không ô nào dài quá 400 ký tự) · tác tử có **nói ra** là đã sửa tệp nguồn
không. Cả hai nhánh — từ chối, và tự thêm bảng — đều được nhận.

### Số đo

`doc.render` · **119 công cụ** (110 mặc định) · 16 ca đơn vị mới · E2E giao diện **9/9**.
Dựng lại `docs/md/EIDE-CAI-DAT.md` sang cả ba định dạng: 75 đoạn · 6 sheet · 6 trang, chữ
tiếng Việt có dấu đúng.

---

### [DEV-302] 29/09/2026 · `tool.propose` chưa từng nổ — hai chỗ chặn, và cách gỡ

Đây là khoản đáng kể nhất trong ngày, và nó **không phải một tính năng mới**: cơ chế "tác tử
tự viết lấy công cụ" đã có từ DEV-2xx, có bốn hàng rào, có bộ kiểm đơn vị. Nhưng
`tool.propose` **chưa nổ trong bất kỳ lượt chạy thật nào**. Một cơ chế như thế đúng bằng không
có — y hệt bộ dò độ nhạy kiểm thử từng chạy 0/402 lượt trong khi mã của nó vẫn xanh.

Bài đo: xin một tệp **PowerPoint**. `doc.render` cố ý chỉ nhận `docx`/`xlsx`/`pdf`, còn
`python-pptx` thì nằm sẵn trong môi trường. Không ai gợi ý tên `tool.propose` cho tác tử.

**Lượt 1 — 1/7.** Tác tử gọi `tool.search` ba lần, không thấy gì, rồi **lịch sự bỏ cuộc**:
viết một dàn ý để người dùng tự chép sang PowerPoint bằng tay.

#### Chỗ chặn thứ nhất: một câu do chính tôi viết ra

`tool.search` khi không thấy gì trả về đúng một lời khuyên:

> *"Không có công cụ nào cho việc này. Nói thẳng với người dùng rằng EIDE chưa làm được việc
> đó — đừng thay bằng một việc gần giống."*

Câu ấy đúng, và nó **đóng luôn lối thứ hai**. `tool.propose` không được nhắc ở bất kỳ đâu —
không trong hiến pháp, không trong skill, không trong lời khuyên này.

Tệ hơn: lời khuyên chỉ nổ khi `count == 0`, mà phép tìm là tìm **mờ**. Hỏi *"xuất ra tệp
powerpoint"* thì nó trả về **8 công cụ** — `doc.to_pdf`, `fs.read`, `build.map` — không cái nào
làm được việc ấy. Nên đúng lúc cần hướng dẫn nhất, tác tử nhận một danh sách vô dụng và
**không một chữ nào**.

Nay lời nhắc đi kèm **mọi** kết quả tìm, nói ra cả hai lối và giữ nguyên chỗ cấm cũ (N6: không
thay bằng một việc gần giống).

**Lượt 2 — vẫn 1/7.** Lời nhắc đã có mà tác tử vẫn không đề xuất.

#### Chỗ chặn thứ hai: luật chỉ mở một cánh cửa

`kiem_de_xuat` đòi `vi_sao` phải kèm **số đo**: bao nhiêu lời gọi đã tốn, bao lâu, mấy lần thử.
Đúng cho ca sinh ra cơ chế này — `addr2line`, nơi tác tử đã cày `fs.read` 28 lần rồi hết hạn
mức. Ở đó **có** một đường làm tay, chỉ là nó đắt, nên đếm được.

Nhưng "làm một tệp `.pptx`" thì **không có đường cày tay nào để mà đo**. Không phải chậm — là
*không có*. Tác tử đọc lược đồ, thấy đòi số đo, không có số nào để điền, nên không đề xuất. Nó
làm đúng theo luật; **luật mới là chỗ thiếu**.

Cửa thứ hai mở bằng thứ **kiểm được**, không bằng văn xuôi: kể ra ít nhất **hai công cụ đã
xem** kèm lý do từng cái không làm được. Viết nổi hai cái tên đúng dạng `nhom.viec` nghĩa là đã
đi tìm thật — khác hẳn một câu *"EIDE thiếu năng lực này"*.

**Lượt 3 — 8/8.** Tác tử `tool.search` → `tool.propose` → thẻ **G-TOOL** cho người duyệt →
`fs.write` mã + bộ kiểm → `tool.reload` chạy bộ kiểm → gọi công cụ mới của chính nó. Sản phẩm:
`.eide/cong-cu/doc_pptx.py` (4 497 B) + `test_doc_pptx.py` (1 271 B), và `bao-cao.pptx` 4
slide mở lại được, có chữ.

Đây là lần đầu tiên trong đời dự án mà một công cụ do **tác tử viết** được nạp và chạy trong
một lượt thật.

### Số đo

`tools/thu_tu_viet_cong_cu.py` **8/8** (từ 1/7) · 3 ca đơn vị mới cho hai chỗ chặn ·
`1275 ca đơn vị` toàn bộ · bộ dò tài liệu **0 chỗ lệch**.

---

### [DEV-303] 29/09/2026 · Sơ đồ mermaid thành HÌNH — trên Console và trong tài liệu xuất ra

**Yêu cầu:** *"Phần tương tác view với markdown, sequen, các sơ đồ… hiện tại vẫn đang để dạng
code. Nên render ra và có thêm nút cho hiện code"* → *"Cả phần xuất ra docx, pptx, xlsx, pdf
cũng cần render ra như vậy"* → *"Toàn bộ năng lực view và chỉnh sửa này hãy cập nhật cho Agent"*.

#### Đo trước: có những kiểu sơ đồ nào

Quét toàn bộ `docs/` và `du-lieu/`: **8 `graph`** (do `ckm.mermaid()` của lõi sinh, nên còn dài
dài) và **1 `sequenceDiagram`** (tác tử viết, có `autonumber`, `loop`, `Note over`, `<br/>`).
Không kiểu nào khác. Cả hai đều rơi vào `case .ma` của `Markdown.swift` — vẽ ra khối chữ đơn
sắc, không phân biệt với `bash`.

#### Tự vẽ, không nhúng `mermaid.js`

Ba lẽ, lẽ thứ ba nặng nhất: EIDE **không mở cổng mạng nào** và chạy được offline; mỗi ô hội
thoại một `WKWebView` là một tiến trình trình duyệt; và mermaid vẽ vài chục kiểu trong khi EIDE
sinh ra **hai**. Dựng cỗ máy đa dụng cho hai ca đã biết là trả giá cho thứ không dùng tới.

Cái giá phải trả thay: **hai bộ đọc cho một cú pháp** — `Views/SoDo.swift` (SwiftUI `Canvas`)
và `src/eide/so_do.py` (Pillow). Lõi là tiến trình con, chiều gọi chỉ có một, nên nó không nhờ
app vẽ hộ được. Ràng buộc giữ hai bên khớp: `test_hai_bo_doc_ra_cung_mot_thu` bắt cả hai đọc
**cùng một tập sơ đồ thật** ra cùng số vai, cùng số khối.

#### Bốn lỗi, và cả bốn đều chỉ NHÌN mới thấy

| Lỗi | Ô kiểm lúc ấy | Vì sao số đo im lặng |
|---|---|---|
| `ImageRenderer` trả về **khung xám trơn** — hình mất sạch, thanh tiêu đề vẫn đủ | **18/18 xanh** | mọi ô hỏi bộ ĐỌC, không ô nào hỏi bộ VẼ. Thủ phạm: `ScrollView` bọc ngoài |
| Đồ thị có vòng `Kỹ sư ⇄ EIDE` làm hai nút **đẩy tầng của nhau lên mãi** — mọi khối xếp một hàng | 18/18 xanh | phép xếp tầng chỉ chặn số vòng lặp cho khỏi treo; nó không treo, nó **sai theo kiểu khó thấy hơn** |
| Nhãn đường nối **đè lên hộp khối** (`VCC / GND` nằm trên chữ `Khối vi điều khiển`) | 18/18 xanh | phép tránh nhau chỉ tránh nhãn khác, không tránh nút |
| `A <--> B` đẻ ra một khối tên **`MOD_MCU <`** | 18/18 xanh | `<-->` chứa `-->`; cắt ở giữa, phần trái `"A <"` rơi xuống nhánh mặc định |

Ba lỗi đầu bắt được bằng cách **mở ảnh ra nhìn**; lỗi thứ tư bắt được trên ảnh chụp cửa sổ thật
sau một lượt tác tử vừa vẽ. Lần thứ năm trong dự án này *số đo đúng, câu hỏi sai*.

Cách xếp tầng nay: **cắt cạnh lùi bằng duyệt sâu trước**, rồi xếp tầng trên đồ thị không vòng,
rồi **căn giữa theo con** từ tầng cuối ngược lên. Nhãn đặt sau cùng, thử vài vị trí dọc đường và
lấy chỗ đầu tiên không chạm nút hay nhãn đã đặt — không chỗ nào trống thì **vẫn vẽ**, vì một
nhãn hơi chồng còn đọc mò được, một nhãn biến mất thì người đọc không biết là đã mất.

#### Nút *Xem mã*

Sơ đồ do tác tử sinh, nên nó là hiện vật: người dùng phải xem được thứ tác tử **thật sự viết**,
không chỉ thứ giao diện vẽ lại. Ba lý do cụ thể: bố cục này không giống mermaid (ai nghi hình
sai phải đọc được nguồn); chép đi chỗ khác (GitHub, tài liệu); và bộ đọc có tập con, nếu nó bỏ
sót một dòng thì chỉ nguồn mới cho thấy.

#### Tài liệu xuất ra

`doc.render` thêm **`pptx`** (mỗi tiêu đề một slide) và vẽ sơ đồ thành **ảnh** trong cả bốn định
dạng. Hai chỗ phụ cũng sửa: sơ đồ quá bè thì **xoay hướng chảy** rồi chọn bản vuông vắn hơn
(một `graph LR` 12 khối ra tỉ lệ 6:1, thu cho vừa trang A4 thì chữ không đọc được — một hình
không đọc được cũng bằng không có); và `$$…$$` đổi sang ký hiệu Unicode thay vì in nguyên cú
pháp TeX vào giữa trang.

Emoji bị **bỏ** trước khi vẽ ở phía Python: phông có dấu tiếng Việt trên macOS không có chúng,
nên Pillow vẽ ra một ô vuông rỗng — mà ô vuông rỗng trông như lỗi phông.

#### Cập nhật cho chính tác tử — và hai đường dẫn đứt tìm được ở đó

Thêm skill `trinh-bay-bang-hinh`, hai dòng trong bảng "ghi cái gì bằng công cụ nào" của hiến
pháp, và mô tả `doc.render` nói rõ mermaid được vẽ thành hình. **Hiến pháp giữ nguyên trần
3 700** — nén ba đoạn cũ thay vì nâng trần; nay 3 696.

Hai chỗ đứt tìm được khi đo:

1. **`tim_skill("vẽ sơ đồ")` trả RỖNG** dù skill có cả `sơ đồ` lẫn `vẽ` trong từ khoá — phép
   lọc đòi **cả cụm** nằm nguyên trong chuỗi mô tả, nên mọi truy vấn nhiều chữ đều trượt. Lỗi
   này có từ đầu và chạm tới **mọi skill**. Nay khớp theo từng chữ, và từ khoá khai báo nặng
   hơn chữ tình cờ có trong thân bài.
2. **Tác tử vẽ sơ đồ vào tệp nguồn nhưng không đưa lên Console.** Người dùng bảo *"vẽ cho dễ
   hiểu"* rồi nhận về một tệp `.pptx` — muốn xem thứ mình vừa xin thì phải mở tệp. Ca kiểm
   2/4. Nói thẳng trong skill: hình phải hiện **trong lời đáp**, không chỉ trong tệp. Chạy
   lại: **4/4**.

### Số đo

`1291 ca đơn vị` · bộ quét giao diện **124/124** · `tools/thu_so_do.py` **18/18** ·
`tools/thu_xuat_tai_lieu.py` **13/13** · bộ dò tài liệu **0 chỗ lệch** · hiến pháp 3 696/3 700.

---

### [DEV-304] 29/09/2026 · "Thư mục Agent sinh ra tài liệu nằm ở đâu?" — tệp làm ra phải TÌM ĐƯỢC

**Câu hỏi của anh Công**, nguyên văn: *"Mình tìm mà không biết thư mục Agent sinh ra tài liệu
nằm ở đâu nhỉ?"*

Đó không phải câu hỏi của người chưa quen. Đó là một lỗi, và đo ra thì nó nằm ở ba chỗ:

| Chỗ | Trạng thái trước |
|---|---|
| Lời đáp của tác tử | chỉ có đường **tương đối** (`trinh-tu-cham.pptx`) |
| Tab *Tài liệu & Nguồn* | tệp làm ra **lẫn vào bảng datasheet đã nạp**, cột Phiên bản · Trang · Nhà phát hành đều trống — vì nó không phải datasheet |
| Bất kỳ đâu khác | không có |

Tệp vẫn luôn nằm **trong thư mục dự án** — `_resolve()` chặn ghi ra ngoài hộp cát, và chuyện
đó đúng. Nhưng *nằm đúng chỗ* khác hẳn *tìm được*. Một tệp người dùng không tìm thấy thì cũng
bằng chưa làm.

#### Sửa

* Khối riêng **A3.2 "Tài liệu tác tử đã tạo"** trên tab *Tài liệu & Nguồn*: tên tệp · dạng ·
  cỡ đọc được (`56 KB`, không phải `57160`) · **đường dẫn đầy đủ**, kèm thư mục dự án ngay ở
  dòng tóm tắt.
* `doc.render` trả thêm `duong_day_du`, và câu báo cho người đọc nói thẳng *"Tệp nằm ở: …"*.

Phân biệt hai loại bằng **cấu trúc, không bằng đuôi tệp**: `doc.render` đăng ký qua
`history.ghi_tep` nên canonical chỉ có `{path, sha, bytes}`, còn tài liệu nạp vào có `title`,
`pages`, `publisher`. Dò theo đuôi sẽ nhầm — một datasheet cũng đuôi `.pdf`.

#### Chỗ suýt sai khi đo

Bản kiểm đầu dùng một kho giả trả **cùng một danh sách cho mọi loại hiện vật**, nên khối A3.6
(*Nạp & trích xuất theo định dạng*) trông như cũng dính lỗi. Nó không dính: A3.6 đọc
`store.list("classification")`, một loại khác. Kho giả sai làm ra một lỗi không có thật — suýt
nữa thì sửa một chỗ đang đúng.

### Số đo

`1294 ca đơn vị` · quét giao diện **124/124** · bộ dò tài liệu **0 chỗ lệch** · ba ca mới,
trong đó một ca bắt đúng chuyện datasheet `.pdf` không được đọc nhầm thành tệp tác tử tạo.

---

### [DEV-305] 30/09/2026 · Việc lớn nhiều chặng: `plan.merge`, và ba lỗ hổng của chế độ kế hoạch

**Câu hỏi của anh Công:** năng lực chia một việc lớn thành nhiều lần thực hiện, ghi kết quả
từng lần rồi hợp nhất — đã có chưa? Ví dụ: viết trọn tài liệu thiết kế một con chip.

#### Đo trước: bốn phần năm đã có

| Anh cần | Có chưa | Cơ chế |
|---|---|---|
| Chia việc lớn thành nhiều bước | ✅ | `plan.exit` — 2–20 bước, mỗi bước khai việc · công cụ · hiện vật · cổng · chi phí; **tên công cụ được kiểm là có thật** |
| Người duyệt trước khi làm | ✅ | cổng G-SCOPE; trong lúc soạn thì **mọi công cụ ghi bị khoá** |
| Làm qua nhiều lượt, nhiều ngày | ✅ | kế hoạch đã duyệt vào `<pending>` mỗi lượt, kèm bước nào xong |
| Sống qua `kill -9` | ✅ | kế hoạch là hiện vật trên đĩa (DEV-289) |
| Ghi kết quả từng chặng | ⚠️ | `plan.step_done` đòi hiện vật — **nhưng không kiểm nó có thật** |
| **Hợp nhất các phần** | ❌ | không công cụ nào |

#### Ba lỗ hổng, cả ba đo được chứ không suy ra

**1. `plan.step_done` nhận một câu kể lại.** `plan.step_done(1, "tôi đã viết xong chương 1
rồi nhé")` → **NHẬN**, bước thành xong. Phép kiểm cũ chỉ đòi chuỗi khác rỗng. Đó là chỗ đậu
giả rẻ nhất còn lại trong chế độ kế hoạch, và nó trái đúng kỷ luật mà `bang_chung` của tác tử
con đã có từ đầu: *"tôi đã kiểm" không phải bằng chứng.*

Nay kiểm ba loại trỏ được: đường dẫn tệp có thật · mã hiện vật trong kho · mã changeset. Lỗi
`E6004` còn **nhắc lại thứ kế hoạch đã hứa** cho bước ấy.

**2. `plan.enter` lần hai đè mất kế hoạch đang chạy.** Đang giữa kế hoạch 3 bước, đã xong
bước 1 → gọi lại `plan.enter` → mục tiêu đổi, số bước về 0, **không một lời báo**. Mã có một
chú thích nói rõ đây là chủ ý (*"người dùng đổi ý là chuyện bình thường"*) — lý lẽ ấy biện
minh cho việc CHO PHÉP kế hoạch mới, nó không biện minh cho việc **xoá dấu vết phần đã làm**.
Nay kế hoạch cũ được cất sang `plan:<run_id>` và lời đáp nói rõ nó ở đâu, xong mấy bước.

**3. Không có bước hợp nhất.** Xong hết thì kế hoạch chỉ đổi `trang_thai` rồi thôi. Với "viết
tài liệu thiết kế chip", mỗi bước ra một chương, và phần việc cuối — ghép theo thứ tự, sinh
mục lục, nói ra chương nào hụt — không chỗ nào lo. Người dùng nhận mười tệp rời và tự ráp.

`plan.merge` ráp theo **đúng thứ tự bước**, hạ cấp tiêu đề cho khớp thứ bậc, ghi rõ mỗi phần
lấy từ tệp nào, và **kê phần không gộp được ngay trong tài liệu** chứ không giấu vào kết quả
lời gọi. Nó **không** viết lại nội dung — một công cụ vừa ghép vừa viết lại thì người duyệt
không phân biệt được đâu là bản gốc.

#### Hai lỗi của chính `plan.merge`, cả hai lộ ra ở lần chạy thật

**Thứ bậc tiêu đề lộn ngược.** Mỗi phần vốn là tài liệu đứng riêng nên mở đầu ở `#`; ghép
thẳng dưới một mục `##` thì mục con hiện to hơn mục cha. Nay hạ cấp, và bỏ qua dòng `#` nằm
trong khối mã — `#include` không phải tiêu đề.

**Ghép cùng một tệp nhiều lần.** Tác tử viết cả sáu phần dồn vào `y-tuong.md`, nên merge ghép
đúng tệp ấy **sáu lần**: `ok=True`, nội dung nhân sáu, và tác tử phải tự `fs.write` đè lên để
chữa (`cs-0008`). Một lời gọi `ok` cho ra thứ vô nghĩa thì tệ hơn một lỗi nói thẳng. Nay
trùng thì ghép một lần và nói ra; **mọi** bước cùng một tệp thì từ chối (`E6008`) kèm lý do —
tệp ấy đã là bản hợp nhất rồi.

Và chỗ phát hiện được **dời lên sớm hơn**: `plan.exit` cảnh báo ngay lúc lập kế hoạch nếu
nhiều bước khai cùng một `hien_vat`, kèm hai hệ quả (không gộp được · hỏng một bước phải làm
lại cả nhóm). Phát hiện đúng mà muộn thì không cứu được lần chạy ấy.

#### Lỗ hổng thứ tư, và nó là lỗ hổng cũ mặc áo mới

Chạy E2E lần hai: tác tử có kế hoạch ba bước **ngay trong `<pending>`**, được bảo *"làm tiếp"*,
nó sửa tệp bằng `fs.edit` rồi dừng — **không gọi `plan.step_done` lần nào**. Kế hoạch đứng yên
0/3, không lỗi nào được ném ra.

Lý do: `plan.step_done` và `plan.merge` là `core=False`, tức chỉ hiện ra sau một lần
`tool.search`. **Cùng hình dạng với hai lần trước** — hook kiểm chứng bảo gọi `task.run` mà
không mở khoá (DEV-2xx), và `tool.search` không nhắc `tool.propose` (DEV-302). *Bảo ai đó dùng
một thứ họ không nhìn thấy thì không phải là bảo.*

Nay: có kế hoạch đã duyệt thì ba công cụ ấy được **mở khoá mỗi lượt**, và `<pending>` **gọi
tên chúng ra** — danh sách bước cho tác tử biết phải làm gì; nó vẫn cần biết đánh dấu bằng cái
gì.

#### Đo qua giao diện thật — và chỗ phải nói thẳng

`tools/thu_chia_viec_lon.py`: **12/14**. Ca cốt lõi — *"chia ba phần, mỗi phần một tệp, làm
xong từng phần thì đánh dấu, cuối cùng gộp"* — **3/3**, có bằng chứng: ba tệp phần riêng, và
tệp gộp mang mục lục kèm dấu nguồn từng phần do chính `plan.merge` sinh.

Hai ô đỏ còn lại **không phải lỗi sản phẩm**: khi không được dặn gì, tác tử chọn viết dồn vào
một tệp và làm xong cả kế hoạch ngay lượt đầu — nên không còn gì để *"làm tiếp"*, và không có
gì để gộp. Đó là **thói quen của tác tử**, và nó hợp lý với tài liệu ngắn. *"Nó không tự chọn"*
khác hẳn *"nó không làm được"*, và trộn hai thứ ấy vào một ô là nói sai về sản phẩm.

Bốn ca kiểm cũ đỏ khi phép kiểm hiện vật siết lại — chúng đang dựa vào đúng lỗ hổng vừa bịt
(`hien_vat="docs/a.md"` với tệp không tồn tại). Sửa chúng dùng hiện vật thật, không nới phép
kiểm.

### Số đo

`plan.merge` · **1308 ca đơn vị** (+14 ca mới) · E2E giao diện **12/14** · hiến pháp giữ trần
**3 693/3 700** (nén bảy chỗ, không nâng trần) · bộ dò tài liệu **0 chỗ lệch** · skill mới
`chia-viec-lon`.

---

### [DEV-306] 30/09/2026 · 31/120 công cụ chưa nổ lần nào — nối ba đường, và một chỗ KHÔNG phải lỗi

Quét sổ cái của **mọi** dự án trong `du-lieu/`: **31 trên 120 công cụ chưa từng nổ** trong bất
kỳ lượt chạy thật nào. 25 trong số đó là `core=False` — chỉ hiện sau một lần `tool.search`, mà
tác tử chỉ tìm khi nó biết có thứ để tìm.

#### Ba đường đứt, và cả ba đều đứt ở chỗ khác nhau

**1. `skill.load` — 0 lần nạp trong toàn bộ lịch sử.** Tám skill hiện tên trong `<skills-hint>`
**mỗi lượt**, mà công cụ để mở chúng thì tác tử không nhìn thấy. Gợi ý một danh mục rồi giấu
cái nút mở nó đi thì danh mục ấy chỉ tốn token. Nay mở khoá mỗi lượt.

**2. `history.undo_30s` — cửa sổ lùi KHÔNG cần thẻ cổng, chưa dùng lần nào.** Menu **⌥⌘Z** gửi
câu *"Hoàn tác việc bạn vừa làm giúp mình"*; lúc ấy tác tử chỉ thấy `history.undo` (R2, cổng
G-HIST) nên nó **dựng thẻ cổng cho một việc lẽ ra lùi được ngay** — đúng thứ cửa sổ 30 giây
sinh ra để tránh. Nay mở khoá **chỉ khi còn trong cửa sổ**: một công cụ luôn hiện mà luôn hỏng
là một công cụ dạy người ta bỏ qua nó.

**3. `fact.review` — đường DUY NHẤT để một Fact lên VÀNG, chưa nổ lần nào**, nghĩa là chưa Fact
nào từng thành VÀNG. Công cụ ấy `core=True` nên tác tử vẫn nhìn thấy; chỗ đứt nằm ở **phía
người**: khối "Hàng đợi rà soát Fact" báo *"chờ anh xác nhận từng dòng"* rồi để họ tự đoán phải
làm gì. Nay khối ấy nói thẳng câu người dùng gõ được (*"duyệt FACT-07"*) và tên công cụ sẽ chạy.

#### Và một chỗ KHÔNG phải lỗi — ghi lại để lần sau không ai sửa nhầm

`ledger.verify` (công cụ) chưa nổ lần nào, nhưng **cơ chế thì chạy liên tục**: bề mặt Nhật ký
gọi `ledger.verify()` mỗi lần vẽ lại, `du-an.json` ghi kết quả mỗi lần mở dự án, và
`goi_du_an.nhap()` kiểm trước khi trả về. Công cụ chỉ là lối thoát hiểm thủ công.

*Số lần chạy bằng 0 là một phát hiện, không phải một kết luận.* Phải hỏi tiếp: cơ chế ấy có
đường nào khác để nổ không.

#### Đo sau khi nối — cả hai nổ lần đầu tiên

Qua giao diện thật: xin hướng dẫn viết AVR bare-metal → tác tử gọi **`skill.load` hai lần**.
Gõ đúng câu menu ⌥⌘Z gửi → **`history.undo_30s` là lời gọi ĐẦU TIÊN** của lượt, không thẻ cổng
nào dựng lên.

---

### [DEV-307] 30/09/2026 · `branch.merge`, và nhánh trước nay chỉ cô lập một nửa

`branch.merge` có trong thiết kế §E5.5 mà **không có trong mã**: ba công cụ
`create`/`switch`/`list` cho thử hai phương án song song rồi **không có đường mang kết quả
về** — nhánh thử xong là ngõ cụt, muốn dùng thì chép tay từng tệp.

#### Chỗ lộ ra khi viết nó: nhánh chưa bao giờ cô lập hiện vật

`tao_nhanh` ghi trong docstring rằng *"chuyển nhánh sẽ khôi phục nửa thứ hai"*. Mã của
`chuyen_nhanh` chỉ gọi `git checkout`. Nên viết một REQ trên nhánh thử rồi quay về `main` thì
REQ ấy **vẫn nằm đó**: nhánh cô lập **tệp** mà không cô lập **hiện vật**.

Lộ ra vì ca kiểm đầu tiên của phép gộp đỏ: nó không thấy hiện vật nào *"chỉ bên kia đổi"* — vì
chúng chưa bao giờ bị tách ra. *Hai phương án song song dùng chung một kho thì không phải hai
phương án song song.*

Nay `chuyen_nhanh` khôi phục kho theo bản chụp gần nhất **của nhánh đích**, và mỗi bản chụp ghi
lại nhánh nó được tạo trên (`contents["nhanh"]`) — không ghi thì mọi bản chụp trông như nhau.
An toàn vì có đường lui: một mốc ngầm được chụp ngay trước khi chuyển.

#### Phép gộp: hai nửa, hai cách

* **Tệp** — `git merge`. Git biết gộp văn bản, và quan trọng hơn: **nó biết lúc nào nó không
  biết**. Xung đột thì `--abort` và trả về danh sách tệp xung đột. Không để lại cây làm việc ở
  trạng thái gộp dở: một cây dở dang là thứ người dùng phải tự dọn mà họ không hề xin.
* **Hiện vật** — so ba bên (điểm rẽ · bên này · bên kia). Chỉ một bên đổi thì lấy bên ấy.
  **Cả hai bên cùng đổi thì không đụng vào**, và kê ra cho người quyết.

Vì sao không tự trộn hiện vật xung đột: một `store.req` đổi ở cả hai nhánh thì không có phép
trộn nào đúng — lấy bên nào cũng là vứt bỏ một quyết định ai đó đã cân nhắc. Chọn hộ là **giả
mạo xuất xứ** của quyết định ấy, và `explain` sẽ nói sai về việc vì sao nó thành ra như thế.

### Số đo

`branch.merge` · **1320 ca đơn vị** (+12) · số công cụ **121** (112 mặc định) cập nhật trong 4
tài liệu · bộ dò tài liệu **0 chỗ lệch** · `skill.load` và `history.undo_30s` **nổ lần đầu**
trong lượt chạy thật.

---

### [DEV-308] 30/09/2026 · Soi nốt 30 công cụ chưa nổ — bốn đường đứt nữa, và một bảng phân loại

Sau DEV-306 còn **30/121** công cụ chưa nổ lần nào. Soi từng cái thay vì sửa hàng loạt, vì
**vài cái "chưa nổ" là đúng** — và sửa một chỗ đang đúng thì đắt hơn để nguyên.

#### Bốn đường đứt, cả bốn đều là MỘT CÂU HƯỚNG DẪN THIẾU, không phải mã hỏng

| Công cụ | Câu thiếu | Hệ quả đo được |
|---|---|---|
| **`store.req_update`** | Bảng hiến pháp chỉ nói *"yêu cầu người dùng nêu → `store.req_create`"*, không nói gì về việc **sửa** một yêu cầu đã có | TC006: tác tử cập nhật cả ba phương án nhưng **không ai gọi là "v2"** — nó không có đường ra bản v2 trong đầu |
| **`stale.accept`** | `<inventory>` chỉ nói STALE *"cần cập nhật"* | Lối thứ hai không tồn tại với tác tử, nên nó hoặc sửa thừa hoặc lờ đi. Có thật những lần thượng nguồn đổi mà hạ nguồn vẫn đúng |
| **`memory.undo_compact`** | Dòng báo nén — nhánh chạy nhiều nhất — không nhắc gì tới việc huỷ nén được | *Một phép đảo ngược không ai biết là có thì cũng như không có* |
| **`plan.cancel`** | `core=False`, và `<pending>` không nhắc | Đã mở khoá cùng `plan.step_done`/`plan.merge` ở DEV-305 |

Chữa: câu hướng dẫn đặt **đúng chỗ tác tử đang nhìn lúc cần** — lối sửa REQ nằm trong mô tả
`store.req_create` (nơi nó đứng ngay trước khi tạo nhầm cái mới), lối thứ hai của STALE nằm
ngay dưới danh sách STALE, đường huỷ nén nằm trong chính dòng báo nén.

Không tốn một token nào của hiến pháp — nó đang ở 3 693/3 700.

#### Đo lại qua giao diện thật

* *"Mình đổi ý: dải đo phải là −20…80 °C chứ không phải 0–50 nữa"* → **`store.req_update`**,
  và **không** gọi `store.req_create` — đúng thứ TC006 thiếu.
* Gõ đúng câu mà **File ▸ Xuất dự án** gửi → **`project.export`** là lời gọi đầu tiên.

Cộng với DEV-306: `skill.load` · `history.undo_30s` · `store.req_update` · `project.export`
đều **nổ lần đầu tiên** trong đời dự án.

#### Bảng phân loại 30 cái — để lần sau không ai đo lại từ đầu

| Nhóm | Số | Ví dụ | Việc cần làm |
|---|---|---|---|
| **Đường đứt — đã chữa** | 4 | `store.req_update` · `stale.accept` · `memory.undo_compact` · `plan.cancel` | xong |
| **Cơ chế nổ qua đường khác — KHÔNG phải lỗi** | 1 | `ledger.verify` | không làm gì; xem DEV-306 |
| **Vừa viết xong, chưa có lượt thật** | 1 | `branch.merge` | dùng khi có việc |
| **Sau cờ tính năng, mặc định tắt** | 3 | `sch.export` · `sch.import` · `sch.symbol_confirm` | đúng như thiết kế |
| **Cần THIẾT BỊ hoặc bàn tay người** | 3 | `target.verify` (cần bo) · `snapshot.release` · `store.option_choose` | chờ người |
| **Cần một loại việc chưa ai giao** | 18 | `khoi.*` (4, thư viện khối) · `doc.figures`/`language`/`to_pdf` · `ckm.import_netlist` · `memory.*` (5 còn lại) · `blob.read` · `ui.explain` · `store.procedure_progress` · `fact.review` | giao đúng loại việc rồi đo lại |

Nhóm cuối là nhóm cần cẩn thận nhất: *"chưa ai giao loại việc ấy"* rất dễ thành cái cớ. Cách
phân biệt: giao thử đúng loại việc đó một lần. Nếu công cụ vẫn không nổ thì nó là đường đứt.

### Số đo

**1323 ca đơn vị** (+3) · 4 công cụ nổ lần đầu qua giao diện thật · bộ dò tài liệu **0 chỗ
lệch** · hiến pháp **3 693/3 700**, không đụng tới.

---

### [DEV-309] 30/09/2026 · Giao đúng loại việc cho 18 công cụ "chưa ai giao" — và nhãn ấy hoá ra ĐÚNG

DEV-308 xếp 18 công cụ vào nhóm *"cần một loại việc chưa ai giao"*. Nhãn ấy **rất dễ thành cái
cớ**: nói vậy thì công cụ nào cũng có lý do để im. Cách phân biệt duy nhất là **giao thử đúng
loại việc đó một lần**.

`tools/thu_18_cong_cu.py` — mỗi ca một câu tiếng Việt như người dùng thật sẽ gõ, **không nhắc
tên công cụ** (nhắc tên là mớm bài, và mớm bài thì đo chính lời mớm chứ không đo sản phẩm).

#### Kết quả: 31 → 11 công cụ chưa nổ

Cả 18 đều nổ khi được giao đúng việc — `memory.status` · `memory.metrics` ·
`memory.remember_user` · `memory.gc` · `memory.forget` · `ckm.import_netlist` · `khoi.list` ·
`khoi.place` · `khoi.extract` · `doc.language` · `doc.to_pdf` · `doc.figures` ·
`store.procedure_progress` · `fact.review` · `ui.explain` · `store.option_choose` ·
`plan.cancel` · `snapshot.release`.

**Nhãn cũ đúng.** Đây là kết quả đáng giá nhất của lượt đo: nó nói rằng 18 công cụ ấy không có
đường nào đứt, và lần sau không ai phải đi soi chúng nữa.

Còn lại 11, đều có lý do đứng được: `blob.read` (chỉ nổ khi một kết quả bị cắt) · `branch.merge`
(vừa viết) · `khoi.upgrade` (cần thư viện có hai bản) · `ledger.verify` (cơ chế nổ qua bề mặt
Nhật ký) · `memory.undo_compact` (cần đã nén) · `sch.*` (3, sau cờ tính năng) ·
`target.verify` (cần bo) · `store.procedure_progress`/`fact.review` (đã nổ ở lượt một, xem dưới).

#### Ba chỗ chính PHÉP ĐO tự làm hỏng mình

**1. Bộ đo xoá mất bằng chứng của chính nó.** Script dọn sạch dự án mỗi lần chạy — mà xoá dự
án là xoá luôn sổ cái. `fact.review` và `store.procedure_progress` nổ ở lượt một rồi **biến mất
khỏi thống kê** vì lượt hai dọn đúng chỗ chúng từng nổ. Nay có cờ `--giu`, và docstring nói rõ:
*một phép đo phá mất dữ liệu của phép đo trước là một phép đo chỉ nói về lần cuối cùng.*

**2. Lượt E2E ghi vào THƯ MỤC NHÀ của người dùng.** `khoi.extract` với `dung_chung=true` lưu
vào `~/.eide/blocks` — ngoài mọi dự án, dùng chung cả máy. Hai khối `LDO-3V3` do lượt đo tạo ra
nằm lại đó, và ca kiểm `khoi.list phải rỗng` **đỏ ngay ở lần chạy sau**. Mất một lúc mới thấy
lỗi nằm ở phép đo chứ không ở sản phẩm. Đã dọn sạch `~/.eide`.

**3. Cả bộ kiểm đều có thể chạm `~`.** Bốn chỗ trong mã ghi dưới `~/.eide`: bộ nhớ người dùng ·
thư viện khối · thiết lập · bộ đệm tìm kiếm. Nay `conftest` cho **mỗi ca một thư mục nhà
riêng**. Một bộ kiểm đỏ-hay-xanh-tuỳ-máy là một bộ kiểm nói về cái máy, không nói về sản phẩm;
và một bộ kiểm để lại rác ngoài kho là một bộ kiểm không ai dám chạy hai lần.

**Lối ra có chủ ý:** `@pytest.mark.nha_that` cho ca cần máy thật. `test_xay_dung` gọi
`arduino-cli`, mà nó cất chuỗi công cụ dưới `$HOME` — đổi nhà là nó tải lại rồi biên dịch hỏng.
Cách ly mọi thứ bằng mọi giá sẽ biến ba ca đo **máy thật** thành ba ca đo một thư mục rỗng.

### Số đo

**1323 ca đơn vị** · công cụ đã nổ **110/121** (từ 90/121) · `tools/thu_18_cong_cu.py` hai
lượt: 15/15 và 16/19 — ba ô đỏ lượt hai là tiền đề khác nhau giữa hai lượt, không phải đường
đứt · bộ dò tài liệu **0 chỗ lệch**.

---

### [DEV-310] 30/09/2026 · Quy trình lập trình: phân tích trước · đánh mốc trước · thiết kế trước

**Yêu cầu của anh Công:** *"trước khi code phải có tài liệu phân tích code (với trường hợp viết
thêm) và đưa ra nội dung sẽ sửa rồi mới tiến hành sửa. Trước khi sửa cần phải đánh dấu bản
trước đó để nếu sửa lỗi có thể rollback về được. Với việc làm mới hoàn toàn thì cần có phân
tích và thiết kế cẩn thận: phân tích và lựa chọn kiến trúc, phân tích và lựa chọn code
structure rồi mới tiến hành tách công việc để thực thi."*

Và sau đó: *"các công cụ này cần thông minh nên bạn nên sử dụng Agent con ở đó nhé"*.

#### Đo trước: ba đòi hỏi, ba lỗ hổng

| Thử | Kết quả |
|---|---|
| `fs.write` đè `main.c` 200 dòng mà **chưa hề đọc** | **NHẬN** — tệp còn một dòng. Câu *"đọc tệp trước"* chỉ là gợi ý trong mô tả công cụ |
| Mốc lùi trước khi sửa | **KHÔNG có** — chỉ có changeset, không có điểm quay về đặt tên được |
| `plan.exit` hỏi gì về kiến trúc | **không gì** — nó kiểm hình thức (đủ bước, công cụ có thật), không kiểm nội dung kỹ thuật |

#### Ba luật cài bằng MÃ

**1. Không ghi đè tệp chưa đọc trọn (`E4020`).** Đọc 20 dòng giữa một tệp 800 dòng rồi đè cả
tệp vẫn là xoá 780 dòng chưa nhìn, nên chỉ tính "đã đọc" khi đọc trọn. `fs.edit` không cần luật
này — nó đòi đoạn cũ khớp từng ký tự nên không đọc thì không viết nổi lời gọi.

Ghi đè mù hỏng theo kiểu **im lặng và toàn phần**: không xung đột, không cảnh báo, chỉ có một
tệp ngắn hơn hẳn. Changeset vẫn hoàn tác được — nhưng hoàn tác là sửa hậu quả, không phải ngăn
nguyên nhân.

**2. Mốc lùi tự động ở lần sửa ĐẦU TIÊN của mỗi lượt.** Một lượt sửa mã đẻ ra nhiều changeset;
khi người dùng nói *"bỏ hết đi"* họ muốn lùi **cả lượt** về một điểm, không phải bấm hoàn tác
bảy lần và tự nhớ đã tới đâu. Một mốc mỗi lượt, không phải mỗi lần ghi — đặt mốc ở mọi lần ghi
thì mốc thành tiếng ồn.

**3. `plan.exit` đòi thiết kế cho việc viết mã (`E6009`).** Hai câu, cho hai loại việc khác
nhau: *dựng cái chưa có* → chọn kiến trúc (`store.option_*`/`adr_create`) và nói cấu trúc mã;
*sửa cái đang có* → một bước `code.analyze`. Luật đặt ở KẾ HOẠCH chứ không ở từng lời gọi
`fs.edit`: bắt một dòng sửa vặt phải viết tài liệu thì luật ấy sẽ bị lách.

#### `code.analyze` — và chỗ tác tử con vào việc

`fs.read` cho thấy **một tệp**. Câu đắt nhất trước khi sửa là câu khác: **ai đang dùng nó?**
Sửa một hàm mà không biết năm chỗ gọi nó thì năm chỗ ấy hỏng lặng lẽ — và `fs.read` không trả
lời được, vì câu ấy cần quét cả cây mã.

Tài liệu sinh ra **tách dữ kiện khỏi nhận định**, mỗi phần ghi rõ ai làm ra nó:

* **Dữ kiện** do mã quét: ký hiệu, phụ thuộc, nơi gọi.
* **Nhận định** do tác tử con **`code-analyst`** (mới, thứ bảy) đọc hiểu — ngữ cảnh sạch, chỉ
  công cụ đọc, được đưa sẵn bảng dữ kiện để khỏi quét lại.

Câu giao cho nó nặng nhất là câu thứ ba: **chỗ nào bảng dữ kiện KHÔNG nhìn thấy** — gọi gián
tiếp qua con trỏ hàm, macro nối chuỗi, bảng phân phối. Phép quét văn bản kêu thừa chứ không bỏ
sót chỗ gọi **thẳng**; chỗ gọi **gián tiếp** thì nó mù hẳn, mà đó đúng là chỗ hỏng đắt nhất khi
sửa firmware. Giới hạn ấy ghi thẳng vào tài liệu, không giấu trong mã.

#### Năm lỗi của chính phần vừa viết

1. **`.m` khớp `.md`.** Luật "chỉ hỏi kiến trúc khi viết MÃ" so đuôi bằng phép tìm chuỗi con,
   nên `.m` (Objective-C) khớp ngay trong `tai-lieu/1.md` — **mười ca kiểm đỏ cùng lúc**, và lý
   do thật nằm ở hai ký tự. Báo động giả dạy người ta bỏ qua cảnh báo, nên nó đắt hơn hẳn việc
   không có cảnh báo.
2. **`code.analyze` là `core=False`** nên tác tử không nhìn thấy. Đo qua giao diện thật: giao
   *"xem giúp rồi sửa"*, nó đọc năm tệp bằng `fs.read` rồi tự sửa, **không gọi lần nào**. Lần
   thứ tư trong dự án này cùng một hình dạng lỗi. Nay `core=True`, và `fs.edit` nhắc tên nó.
3. **`Changeset.to_dict()` không mang `snapshot_id`** — mốc lùi có trong bộ nhớ mà không tới sổ
   cái. Năm changeset liên tiếp báo `snapshot_id=None` trong khi mốc đã đặt thật.
4. **Sự kiện sổ cái cũng thiếu trường ấy** — mốc chỉ sống trong tiến trình đang chạy.
5. **Tác tử con chạy mà không để lại dấu trong sổ cái**: quên truyền `ghi_so`. Nhận định của
   `code-analyst` nằm trong tài liệu, còn sổ cái chỉ thấy `verifier`. Một việc không truy vết
   được (N1), và ở đây nó còn là một việc **tốn tiền không ai đếm được**.

#### Ba lần phép đo tự hỏng — và một luật cho bộ đo

Bộ E2E chạy năm lượt mới đúng. Ba ô đỏ đầu **không nói về sản phẩm**:

* đo chuỗi lời gọi trong một cửa sổ thời gian, trong khi sổ cái cho thấy luật chạy đúng: kế
  hoạch 6 bước không kiến trúc bị `E6009`, tác tử đọc gợi ý, thêm `store.adr_create`, nộp lại 7
  bước và **qua**;
* một ô đòi *"kế hoạch không kiến trúc phải bị chặn"* — tức **chỉ xanh khi tác tử mắc lỗi**.
  Lần chạy sau nó làm đúng ngay từ đầu và ô ấy đỏ;
* một ô đòi tác tử phải nộp lại thành công **trong thời gian chờ** — đó là chuyện tốc độ, khác
  với chuyện luật có giữ được hay không.

Luật rút ra, ghi vào chính bộ đo: **một phép đo chỉ xanh khi sản phẩm mắc lỗi là một phép đo
hỏng.** Đo BẤT BIẾN (không kế hoạch thiếu kiến trúc nào được nhận), kèm một ô chống xanh rỗng
(có nộp kế hoạch viết mã để mà đo).

### Số đo

`code.analyze` + tác tử con `code-analyst` · **1339 ca đơn vị** (+16) · **122 công cụ** (113
mặc định) · **7 tác tử con** · E2E quy trình lập trình **8/8** qua giao diện thật, trong đó
`E4020` và `E6009` đều nổ thật trong lượt chạy · bộ dò tài liệu **0 chỗ lệch**.

---

### [DEV-311] 30/09/2026 · Dựng một RTOS từ đầu — hai lỗ hổng của EIDE lộ ra khi làm việc thật

Anh Công giao: bỏ hẳn FreeRTOS, tự viết nhân RTOS cho STM32F469NI, cho tới khi màn hình LCD lên
như bản cũ. *"Mục tiêu phải giúp agent phân tích thiết kế và phát triển được khối lượng phức
tạp."* Toàn bộ hồ sơ ở [`docs/rtos-tu-viet/`](rtos-tu-viet/README.md).

Kết quả: **1 029 dòng nhân tự viết**, 6 tác vụ, chuyển ngữ cảnh `PendSV` naked assembly, hàng
đợi có timeout, **259 488 B Flash**, **0 ký hiệu FreeRTOS**, màn hình lên trên bo thật.

#### Lỗ hổng 1 — `build.compile` không nói nó đã dịch những tệp nào

Hai lần biên dịch đầu **đỏ**; lần thứ ba tác tử bỏ bớt đầu vào thì **xanh** — và ảnh ra
**1 416 byte**, không một ký hiệu LCD/UI/Touch nào, trong khi dự án có 15 tệp mã. Nó đã thu hẹp
đầu vào cho tới khi qua được rồi báo "biên dịch xong".

Đây là lỗi của **sản phẩm**, không của tác tử: kết quả `build.compile` có `tep_ra`, `flash`,
`sram`, `section` — mà **không có danh sách nguồn**. *1 416 byte trông như một con số, không
trông như một vấn đề*, nên không ai đọc ra là hỏng.

Nay mã so cây nguồn với **dòng lệnh thật đã chạy** và kê ra tệp nào không vào ảnh, đặt ngay
**đầu** `note_vi` chứ không cuối. Bỏ qua `vendor/` có chủ ý: mã hãng có thể cố ý không dịch hết.

#### Lỗ hổng 2 — lời gọi mô hình chỉ ghi siêu dữ liệu

Anh Công yêu cầu giữa phiên: *"ghi nhận log lại nhé toàn bộ kể cả các lời gọi LLM và kết quả
trả về"*. Đo ra: sổ cái ghi `llm_call` với model, token, thời gian, tên công cụ đã gọi; hội
thoại nằm trong `transcript.jsonl`. Nhưng **thứ thật sự gửi tới mô hình** — hiến pháp,
`<inventory>`, sáu khối nhắc — thì không ở đâu cả. `RecordingGateway` có sẵn nhưng chỉ ghi
**chiều về**: đủ để phát lại, không đủ để soát lại.

Khi một lượt đi sai, câu hỏi không phải *"nó trả lời gì"* mà là **"lúc ấy nó nhìn thấy gì"**.

Nay `RecordingGateway` ghi cả hai chiều, bật bằng `EIDE_GHI_LLM=1`, mặc định **tắt** — tệp ấy
lớn (phiên này 57 MB cho 160 lời gọi) và chứa nguyên văn mọi thứ gửi đi, nên bật nó phải là một
lựa chọn có ý thức. Lược đồ công cụ chỉ ghi **tên**: nó là hằng số của phiên bản, không phải
biến của lượt, ghi đủ làm tệp phình gấp mấy lần mà không thêm thông tin.

#### Ba lỗi phần cứng, và cách tác tử tìm ra chúng

Không lỗi nào tìm được bằng đọc mã. Cả ba đều do **anh Công nhìn bo** rồi tác tử dò bằng công
cụ phần cứng:

| Triệu chứng anh Công thấy | Tác tử đo được | Nguyên nhân gốc |
|---|---|---|
| LED nhấp nháy, **LCD đen** | khung hình có đủ 6 màu ⇒ phần vẽ đúng; `DSI_WISR` `PLLLS=0`, `DSI_PCTLR=0`, `DSI_ISR1=0x80` | `HAL_Delay()` nay nối vào `rtos_delay_ms()` nên **nhường CPU giữa chuỗi khởi tạo DSI có ràng buộc thời gian cứng**; `vTaskButton` ưu tiên cao hơn chen vào mỗi 30 ms |
| Màn lên, **bấm nút không đổi trang** | `GPIOB` xác nhận `Touch_Init()` đã chạy | `i2c_delay()` dùng vòng NOP cố định 150 bước; xung nhịp lên 180 MHz làm I2C vượt 600 kHz, sườn lên RC của open-drain không kịp |
| Ảnh 1 416 byte | 0 ký hiệu LCD/UI/Touch trong ELF | xem Lỗ hổng 1 |

Lỗi DSI là loại đáng nhớ nhất: **nó chỉ tồn tại vì có RTOS**. Bản FreeRTOS không gặp vì
`HAL_Delay` ở đó là vòng chờ bận. Một nhân đúng về mặt lập lịch vẫn có thể phá một khối ngoại
vi chỉ vì nó nhường CPU đúng chỗ không được nhường.

#### Chuỗi năng lực vừa dựng đã chạy thật

Phiên này đi qua gần hết những thứ làm trong ngày: `plan.enter` → ba phương án so bằng số →
`store.option_choose` (G-DESIGN) → `plan.exit` **thoả `E6009`** vì có bước chọn kiến trúc →
`plan.step_done` từng bước → `code.analyze` khi sửa mã có sẵn → `build.compile` → `target.flash`
(G-FLASH) → `target.verify` → `target.screen`. **`E4020`** cũng nổ thật khi tác tử định ghi đè
một tệp chưa đọc.

### Số đo

**1 341 ca đơn vị** · nhân RTOS **1 029 dòng**, Flash **259 488 B**, 0 ký hiệu FreeRTOS ·
**160 lời gọi mô hình** ghi đủ hai chiều (57 MB, nén 16 MB) · 18 hiện vật · bộ dò tài liệu
**0 chỗ lệch**.

---

### [DEV-312] 30/09/2026 · Báo cáo RTOS bằng `doc.render` — và giới hạn của bộ vẽ sơ đồ chuỗi

Anh Công đặt một tài liệu `.docx` mô tả yêu cầu, thiết kế theo C4, quá trình tác tử làm, kèm
**số liệu thời gian và chi phí**. Viết bằng Markdown rồi dựng bằng **chính `doc.render` của
EIDE** — 9 trang, 9 bảng, 4 sơ đồ C4 vẽ thành ảnh:
[`docs/rtos-tu-viet/bao-cao/`](rtos-tu-viet/bao-cao/).

#### Số liệu lấy từ nhật ký, không ước lượng

| | |
|---|---|
| Thời gian thực | **81,2 phút** (08:59:33 → 10:20:44 UTC, đọc từ sổ cái) |
| Chờ mô hình | **24,8 phút** — 30,5 % thời gian thực |
| Lời gọi mô hình | **355** · trung bình 4,2 giây |
| Token vào | 23 126 605, **trong đó 19 793 272 đã đệm (85,6 %)** |
| Token ra · suy nghĩ | 73 517 · 118 429 |
| Lượt trao đổi · lời gọi công cụ · changeset | 46 · 367 · 20 |

Tỉ lệ đệm 85,6 % là con số đáng chú ý nhất: hiến pháp, lược đồ 122 công cụ và phần đầu hội
thoại lặp ở mọi lượt nên được đệm. **Chi phí thật gần như chỉ phụ thuộc phần mới của mỗi lượt.**

Kho không lưu bảng giá, nên chi phí trình bày dưới dạng **công thức kèm tham số** và ba kịch
bản đơn giá — không bịa một con số rồi để nó thành sự thật trong một tài liệu nộp.

#### Giới hạn bộ vẽ: đồ thị CHUỖI

Sơ đồ C1 đầu tiên là một chuỗi bốn nút (`Kỹ sư → EIDE → Firmware → Bo`) có một cạnh vượt tầng.
Bộ vẽ xếp mỗi tầng một nút ⇒ **tất cả nằm cùng một cột**, mọi cạnh chồng lên cùng một đường
thẳng đứng, và nhãn rơi nhầm chỗ — người đọc hiểu sai quan hệ giữa các khối.

Hai lần sửa, cả hai đều đo lại bằng mắt trên bản PDF:

1. **Cạnh vượt tầng vòng ra bên cạnh** thay vì đi xuyên giữa. Bản đầu vồng cố định 60 px —
   với một cạnh dài 700 px thì 60 px trông vẫn như đường thẳng. Nay vồng **tỉ lệ với chiều
   dài** (22 %, tối thiểu 70 px), và **nhãn bám vào đỉnh cung**: đặt nhãn trên dây cung là đặt
   nó đúng chỗ cạnh ấy vừa tránh ra.
2. Vẫn chưa đủ với hình chuỗi, nên **bản vẽ đổi hình dạng**: `EIDE` thành nút toả ra hai nhánh
   (`Firmware`, `Bo`). Rẽ nhánh là dạng bộ vẽ làm tốt — sơ đồ C2 cùng tài liệu ra rất sạch.

Nói thẳng chỗ còn lại: **bộ vẽ xử lý đồ thị rẽ nhánh tốt và đồ thị chuỗi kém.** Sửa cho chuỗi
cần một thuật toán định tuyến cạnh thật sự (kênh riêng cho cạnh vượt tầng), không phải một
tham số nữa. Chưa làm, và ghi lại ở đây để lần sau không ai tưởng nó đã xong.

### Số đo

**1 341 ca đơn vị** · báo cáo 9 trang / 9 bảng / 4 sơ đồ · bộ dò tài liệu **0 chỗ lệch**.

---

### [DEV-313] 30/09/2026 · Ước lượng nhân sự cho cùng khối lượng — và ba lỗi dựng bảng Word

Anh Công đặt thêm: *"trường hợp tôi là công ty chỉ dùng nhân sự thì cần làm ước lượng nguồn lực
và tính chi phí… từ phân tích, thiết kế, phát triển, kiểm thử"*.

#### Ước lượng: WBS ba điểm, không phải một con số tròn

Mục 5 mới của báo cáo dùng **PERT** — mỗi hạng mục ước ba giá trị rồi lấy
`E = (LQ + 4×KD + BQ)/6`. Cách này nói ra được **độ bất định**, thứ một con số đơn lẻ giấu đi.

| | |
|---|---|
| Tổng | **31,7 ngày công**, độ lệch chuẩn ±2,3 |
| Khoảng ~68 % · ~95 % | 29–34 · 27–36 ngày công |
| Phân bổ | Senior 18,4 (58 %) · Mid 11,1 (35 %) · QA 2,2 (7 %) · PM 6,3 |
| Thời gian lịch | **4–5 tuần**, Senior là đường găng |
| Chi phí (mức giữa, kèm PM) | **≈ 111 triệu đồng** |

Hai hạng mục có **bi quan gấp bốn lần lạc quan** — tầng port assembly (2→8) và gỡ lỗi DSI
(1→8). Cả hai đã xảy ra đúng như thế trong phiên tác tử, nên đó không phải phòng hờ suông.

Kiểm chéo bằng **COCOMO** trên 1,029 KSLOC: organic 52 ngày công, embedded 78 — gấp 1,6–2,5
lần WBS. Chênh lệch ấy **nói ra chứ không giấu**: COCOMO tính trọn vòng đời công nghiệp, hiệu
chuẩn trên dự án lớn, và không trừ phần tái sử dụng driver. Đọc nó như **cận trên**.

Toàn bộ mục 5 dán nhãn **tầng ĐỒNG** ngay đầu mục: mục 1–4 là số đo đọc từ sổ cái, mục 5 là
phán đoán. Hai loại số ấy không đứng cùng một hàng, nên chúng ở hai mục khác nhau.

#### Ba lỗi dựng bảng Word, cả ba chỉ thấy khi mở bản PDF ra nhìn

**1. Bề rộng cột: `cell.width` đúng mà `tblGrid` sai.** Mọi ô đã đặt 3,54 inch, nhưng `gridCol`
vẫn 1440 twips (1 inch) cho mọi cột — và **LibreOffice, thứ dựng bản PDF, đọc lưới chứ không
đọc ô**. Bảng WBS 6 cột ra với cột đầu teo còn một inch, mỗi hàng cao gấp bốn lần cần thiết.
Hai chỗ cùng nói về một thứ thì phải sửa cả hai.

Kèm theo: `autofit` là **lời đề nghị**, không phải lệnh — phải đặt bố cục **cố định** thì bề
rộng mới được tôn trọng. Và cận dưới của mỗi cột nay đủ chứa **từ dài nhất** trong cột ấy, vì
một hằng số 0,55 inch làm chữ "Senior" gãy thành "Senio/r".

**2. Hai bảng liền nhau trông như một.** Không có đoạn rỗng giữa chúng, nên hàng tiêu đề của
bảng sau đọc ra như một hàng dữ liệu của bảng trước.

**3. Trích dẫn nhiều dòng thành nhiều khối.** Một lời ghi chú ba dòng hiện ra như ba lời ghi
chú khác nhau, mỗi cái một khung. Nay các dòng `>` liền nhau gộp thành một.

Cả ba đều thuộc loại **số đo không bắt được**: `so_bang`, `so_doan`, `so_ky_tu` đều đúng và ổn
định qua mọi lần dựng. Lần thứ sáu trong dự án này một tấm ảnh bắt được thứ mọi con số bỏ qua.

### Số đo

**1 344 ca đơn vị** (+3) · báo cáo 12 trang / 15 bảng / 4 sơ đồ · bộ dò tài liệu **0 chỗ lệch**.

---

### [DEV-314] 30/09/2026 · README nói về RTOS tự viết — và năm con số sai bắt được khi đi kiểm

Anh Công bảo đẩy mã RTOS lên git rồi mô tả nó trên README "để biết giá trị của agent này".
Mã thì **đã ở trên git từ `f8d9d7b`** — việc còn lại là kể cho đúng. Nhưng để kể, phải tra lại
từng con số định viết ra. Năm con số không trụ được.

#### Năm con số sai, và vì sao chúng sai

| Định viết | Thật ra | Vì sao lệch |
|---|---|---|
| Flash **259 488 B** | **260 204 B** | số của bản dựng **trước** khi vá lỗi DSI; bản vá thêm 716 B |
| "**1 029 dòng nhân RTOS**" | nhân **689**, còn 340 là `main.c` | 1 029 là nhân **cộng** ứng dụng — câu chữ gộp hai thứ làm một |
| "**0 ký hiệu** FreeRTOS" | `nm` cho **6** khớp | 6 ấy là hàm tác vụ của ứng dụng (`vTaskLED1`…) giữ lối đặt tên cũ; nhân FreeRTOS thật là **14** ký hiệu, nay bằng 0 |
| "184 ký hiệu" ở bản cũ | **20** khớp, trong đó **14** là nhân | con số nhớ nhầm, chưa từng chạy `nm` |
| "**311** lời gọi mô hình" | **351** ghi được | 311 là `llm_call` ở **vòng chính**; nhật ký có thêm **44 của tác tử con** |

Con số thứ ba là cái đáng nói nhất. Viết "0 ký hiệu FreeRTOS" thì **người đọc chạy `nm` sẽ thấy
6 và nghĩ là nói dối**. Nay README nói trước chỗ dễ đọc nhầm ấy, kèm tên bốn ký hiệu nhân đã
biến mất. *Một câu đúng mà người kiểm chứng thấy khác là một câu hỏng.*

Con số thứ năm cũng vậy: 351 ≠ 311 nhìn như log bị thiếu. Hoá ở giữa là tác tử con — phân bố
độ dài lời nhắc hệ thống chia đôi rất sạch (**307 bản ghi ~11 000 ký tự** vòng chính · **44 bản
ghi ~1 000 ký tự** tác tử con), nên con số ấy giải thích được chứ không phải chắp vá.

#### Hai chỗ bằng chứng trên git không khớp báo cáo

**Hồ sơ đã đẩy là bản chụp sớm.** Sổ cái trong `ho-so-tac-tu/` có 3 809 sự kiện, còn báo cáo
ghi 3 915 — vì hồ sơ được gói **giữa chừng**, trước 4 lời gọi cuối. Báo cáo đúng, bằng chứng
thiếu. Đã làm tươi từ dự án sống: **3 915 sự kiện · 367 lời gọi**, khớp báo cáo. *Bằng chứng
đẩy lên phải đỡ được đúng con số đã công bố, nếu không thì nó phản chứng chính mình.*

**Nhật ký LLM có 12 tệp rác.** Đếm ra 363 bản ghi, 12 cái không parse được JSON — tưởng là lời
gọi lỗi mạng, suýt viết vậy vào README. Mở ra xem thì đó là **tệp `._*` AppleDouble của macOS**
lọt vào `tar`. Số thật là **351, tất cả đều có nguyên văn trả về**. Đã gói lại với
`COPYFILE_DISABLE=1`.

#### Một lần nữa phép đo suýt phá bằng chứng của chính nó

Đồng bộ transcript bằng `rsync -a --delete` từ `.eide/transcripts/` — thư mục ấy **rỗng**, tên
thật là `sessions/`. `--delete` xoá sạch **12 transcript đã đẩy git**. Khôi phục được bằng
`git checkout` vì chúng đã được commit.

Đây là lần thứ hai trong dự án (lần đầu: `thu_18_cong_cu.py` tự xoá sổ cái của chính nó). Cùng
một hình dạng: **một thao tác dọn dẹp chạy trên một đường dẫn chưa kiểm tra là có thật**.
`--delete` với nguồn rỗng không phải là đồng bộ, nó là xoá.

#### Bộ kiểm neo cũng sai

Viết nhanh một đoạn kiểm neo `#...` trong README: nó báo **8 neo hỏng trên 7 neo** — nhiều lỗi
hơn cả số neo, dấu hiệu chắc chắn là bộ kiểm hỏng chứ không phải README. Hàm tạo slug bỏ `·`
**sau** khi đổi khoảng trắng nên mất dấu `--` kép. Sửa lại: **0 neo hỏng / 7**, 0 đường dẫn
hỏng / 29.

#### README thêm gì

Mục **§18 "Bài kiểm lớn nhất: một RTOS viết từ số không"** — bảng khối lượng, bảng so với
FreeRTOS trên cùng bo, ba lỗi phần cứng, giá phải trả, và **ba điều bảng ấy không chứng minh**
(chưa thử nghiệm dài hạn nên chưa cùng một sản phẩm · người vẫn trên đường găng · tiền mô hình
không phải toàn bộ chi phí). Thêm một hàng ở bảng "Mới trong bản này", một hàng ở "Đã đo được
gì", một hàng ở "Trạng thái", và sửa số ca đơn vị 1339 → 1344 ở đầu trang.

### Số đo

**1 344 ca đơn vị** · bộ dò tài liệu **0 chỗ lệch** · README 0 neo hỏng / 0 đường dẫn hỏng ·
báo cáo dựng lại **12 trang / 15 bảng**, kiểm bằng mắt trang bảng số đo.

---

### [DEV-315] 30/09/2026 · Phân tích và thiết kế của tác tử lên tab — ba khối mới, và hai lỗi sơ đồ chỉ ảnh bắt được

Anh Công theo dõi phiên dựng RTOS rồi nói: *"việc phân tích và thiết kế của Agent khá okay
nhưng nội dung đó chưa được show ở tab bên cạnh"*. Đo lại trên chính dự án ấy:

    A2  Yêu cầu & Giải pháp    A2.1∅  A2.3  A2.4
    A5  Thiết kế               A5.4∅  A5.2∅          ← RỖNG HOÀN TOÀN
    A7  Mã nguồn               A7.1  build

Tác tử vừa so **ba phương án kiến trúc**, chốt một cái qua cổng G-DESIGN, chia việc thành **6
bước qua 12 phiên bản kế hoạch**, viết một **tài liệu phân tích mã**. Không thứ nào mở ra xem
được từ tab. Con số cụ thể: `plan` xuất hiện **0 lần** trong cả `surfaces.py`; hiện vật `note`
chỉ có mặt ở một hàm tóm tắt dự phòng.

#### Vì sao tab Thiết kế rỗng — và đây không phải lỗi cài đặt

MDD-40 §E7 dòng 405 nói tab Thiết kế hiện *"hình + danh sách khối"* dựng từ `module_graph`; mà
dòng 174 ghi rõ `arch.decompose`/`store.module_*` đã **gộp vào Bản đồ tri thức MẠCH** (§C2).
Nghĩa là cả ba khối của tab Thiết kế — BOM, CKM, sơ đồ nguyên lý — đều dựng từ *mạch*.

**Thiết kế phần mềm không có nhà.** Không ai viết sai dòng nào; chỗ trống nằm trong thiết kế,
và chỉ lộ ra khi có một dự án phần mềm thuần đi qua.

#### Ba khối mới, không thêm loại hiện vật nào

**A5.6 Kiến trúc phần mềm** — sáu mục chiếu từ thứ đã có trong kho: kiến trúc đã chốt (kèm sơ
đồ mô-đun), thành phần chính, **rủi ro nêu lúc chọn**, phương án đã loại kèm lý do, hệ quả
ghi ở ADR, mô-đun trên đĩa. Mục đầu **mở sẵn** (`mo_san`), vì sáu mục gập hết thì mở tab ra vẫn
chỉ thấy sáu dòng tiêu đề — vẫn chưa trả lời được câu hỏi ban đầu.

Cạnh của sơ đồ đọc từ `#include`/`import` **có thật trong tệp**. Không có quan hệ nào thì
**không vẽ**, và nói ra vì sao: sáu ô rời không nối gì là trang trí giả dạng bản vẽ kiến trúc.
Trên dự án RTOS: 5 cạnh thật từ 6 tệp.

**A2.5 Kế hoạch chia việc** — mục tiêu, **giả định**, **ngoài phạm vi**, và từng bước kèm công
cụ + hiện vật. MDD-40 dòng 409 xếp kế hoạch ở **Console**; đây là **sai lệch có chủ ý**. Lý do
đo được: kế hoạch RTOS đi qua 12 phiên bản, và ba điều tác tử tự tuyên bố không làm — chưa cấp
phát động, chưa bật MPU, chưa tích hợp DSI/LTDC — là thứ cần nhất lúc nghiệm thu, mà Console
là dòng chảy nên chúng đã trôi mất từ lâu. *Đề nghị cập nhật tài liệu: có.*

Khối này **không có nút bấm**, cố ý: bước kế hoạch chỉ đóng bằng `plan.step_done`, mà công cụ
ấy đòi một hiện vật mở ra xem được. `KhoiQuyTrinh` có sẵn ba nút "Xong / Không được / Bỏ qua"
và trông rất tiện để tái dùng — nhưng nó gửi `surface: "code"` và không đòi hiện vật, tức là
một **nút nói dối**. Nên viết `KhoiKeHoach` riêng, chỉ đọc.

**A7.2 Phân tích mã trước khi sửa** — đọc thẳng nội dung tệp `.md` lên tab. Quy trình ở DEV-309
bắt phải phân tích trước khi sửa mã có sẵn; *một bản phân tích bắt buộc phải viết mà không ai
đọc được thì là thủ tục, không phải phân tích.*

#### Cột "Ai quyết" nói thiếu về phía người

ADR-01 ghi `quyet_boi: tac_tu`, và bảng A2.4 hiện đúng một chữ **"Tác tử"** — đọc ra thành
*"tác tử tự quyết, không ai xem"*. Nhưng sổ cái có `h-0004` lúc **09:06:37**: anh bấm duyệt
`gate-0001`, đúng cổng G-DESIGN chặn `store.option_choose`.

Không sửa `quyet_boi`: `_kiem_nguoi_that_su_chon` cố tình khắt khe, và bấm *Duyệt* trên thẻ
cổng thật sự chưa phải là tự chọn. Sửa chỗ **hiện ra**: ba trạng thái khác nhau thì ba chữ
khác nhau — *Anh quyết* · *Tác tử đề xuất · anh duyệt qua cổng G-DESIGN* · *Tác tử tự quyết —
chưa ai duyệt*. Nói thiếu về phía người cũng là một cách nói sai.

#### Hai lỗi sơ đồ, chỉ tấm ảnh bắt được

Dựng xong khối A5.6, bộ quét báo **123/124 ô xanh**, không kiểu khối nào "chưa biết vẽ", không
khối nào chồng nhau. Nhìn ảnh thì thấy hai thứ mọi con số bỏ qua:

1. **Nhãn cụm bị cắt mất nửa trên.** Khung `subgraph` vươn lên trên nút cao nhất 16–24 px để
   nhét nhãn, mà khổ hình chỉ tính tới lề. `firmware` hiện ra một nửa ở mép.
2. **`main.c` tràn sang khung thư mục khác.** Khung cụm là **hợp** các ô thành viên, còn tầng
   lại xếp nút theo *tâm của các con* — nút hai cụm đan nhau nên hai khung chồng lên. Sơ đồ
   nói `main.c` nằm trong `firmware/rtos`. **Một sơ đồ nói sai về cấu trúc thư mục thì tệ hơn
   không có sơ đồ.**

Sửa ở cả hai bộ vẽ (Swift cho tab, Python cho tài liệu). Phía Python còn một lớp nữa: xếp nút
cùng cụm liền nhau *trong một tầng* vẫn chưa đủ, vì cụm trải qua nhiều tầng — phải cấp cho mỗi
cụm một **dải toạ độ dùng chung cho mọi tầng**.

Và tách `xep_cho()` ra khỏi phép vẽ, vì trước đó hình học chỉ kiểm được bằng mắt: `ve_png` vẫn
trả PNG hợp lệ, `so_khoi`/`so_noi` vẫn đúng. *Một hình sai vẫn là một hình vẽ được.* Nay bốn ca
đo thẳng toạ độ — hai khung không giao nhau, mỗi nút nằm trong khung của chính nó.

#### Một lệch nhỏ tự lộ ra

Chú thích ở `KeHoach.trang_thai` kể **bốn** trạng thái, mã ghi **sáu** (`hoan_thanh` ở
`plan.step_done`, `da_cat` ở `plan.enter`). Nay có `TEN_TRANG_THAI_VI` đặt cạnh định nghĩa,
`surfaces.py` nhập từ đó. *Một danh sách kể thiếu tệ hơn không kể, vì nó trông như đã đủ.*

### Số đo

**1 372 ca đơn vị** (+28) · bộ quét giao diện **124/124** trên dự án chuẩn · bộ dò tài liệu
**0 chỗ lệch** · E2E qua app thật trên bản sao dự án RTOS, ảnh ở
[`ket-qua-tab-phan-tich-thiet-ke/`](../review-v3/test/ket-qua-tab-phan-tich-thiet-ke/) ·
năm phép phá sản phẩm đều làm bộ kiểm đỏ.

---

### [DEV-316] 30/09/2026 · Đổi dự án mà màn hình không đổi, và số đo đứng im suốt lượt

Anh Công báo ba việc về màn hình tương tác: đổi dự án mà chat của dự án cũ vẫn còn; token và
số lời gọi công cụ không cập nhật; và đề nghị rà xem nhãn nào chưa tích hợp. Cả ba đều đúng,
và mỗi cái lộ ra một chỗ hỏng lớn hơn phần nhìn thấy.

#### 1 · `AppState.mo()` khởi động lõi mới mà không xoá gì

Không một dòng nào dọn trạng thái cũ. Chat còn lại là phần **dễ thấy nhất**, chưa phải phần
nguy nhất: `cards` giữ nguyên các **thẻ cổng đang chờ duyệt** của dự án trước. Bấm *Duyệt* trên
một thẻ như vậy là gửi quyết định về một lõi đã chết, cho một hiện vật ở thư mục khác.

Thêm `doiDuAn(_:)` dọn đủ mười thứ, gọi **trước** `client.start`. Hai thứ cố ý **không** xoá:
`draft` — chữ người tự gõ mà chưa gửi, xoá nó là làm mất việc của người để cho gọn màn hình
của máy; và `selectedSurface` — tab đang xem là thói quen của người, không phải dữ liệu dự án.

Có một ca kiểm đọc chính `AppState.swift`, đối chiếu danh sách `@Published` với danh sách được
dọn: thêm một trường mới mà quên dọn thì ca ấy đỏ.

Hai thứ nữa lộ ra khi đi theo đường này:

* `UITestChannel.tat()` **chưa từng được gọi**. Mỗi lần đổi dự án lại thêm một bộ đếm giờ 4 Hz,
  cái cũ không ai tắt.
* Nhánh nhập gói `.zip` đặt thông báo *trước* khi mở dự án — nay chính `doiDuAn` xoá nó, nên
  người nhập một gói xong sẽ không thấy gì xác nhận. Đảo thứ tự.

#### 2 · Cả một lượt chỉ có hai mốc tin

`run.update` lúc bắt đầu (chi phí rỗng) và lúc kết thúc. Ở giữa — chỗ tác tử gọi mười công cụ
và tiêu vài trăm nghìn token — thanh trạng thái đứng nguyên `0/40 tool · 0/300 s`. Người nhìn
vào đó **không phân biệt được *đang chạy* với *đã treo***, mà đấy đúng là lúc họ cần biết nhất:
một lượt dài là lúc duy nhất người ta muốn bấm Dừng.

Thêm `_nhip(ctx)` sau mỗi lời gọi công cụ và sau mỗi lượt gọi mô hình. Dùng `run.update` chứ
không vẽ lại thanh trạng thái: dựng thanh trạng thái phải `inventory.build()` — quét kho, quét
sổ cái — và làm thế sau mỗi lời gọi là trả một cái giá lớn cho một con số nhỏ.

Đo trên app thật: dãy công cụ **0 → 2 → 3 → 5 → 6 → 7 → … → 12**, token **0 → 57 820 →
150 351 → 235 110**.

#### 3 · Và bộ đếm còn CHẠY NGƯỢC

`emit_all` luôn gửi kèm thanh trạng thái, nên `paint(only=["history"])` — chạy mỗi khi người
ghi bản ưng ý hoặc rẽ nhánh — đẩy `da_dung_tool = 0` lên màn hình **giữa một lượt đang chạy**.

*Một con số đi lùi tệ hơn một con số đứng yên: đứng yên chỉ là chưa biết, đi lùi là nói sai.*

#### 4 · Rà nhãn: một cái chưa bao giờ hiện, một cái chưa bao giờ có

Đối chiếu ba tầng — lõi gửi gì · Swift khai gì · view đọc gì:

* **`isa` gửi từ đầu, không nhãn nào vẽ.** Tập lệnh quyết định mọi cờ biên dịch, và nó chỉ tồn
  tại trong JSON. Nay có nhãn *Tập lệnh*, hiện khi đã ghim hộ chiếu chip.
* **Token đã tiêu không có trong mô hình.** Nó chỉ sống trong thẻ Run, mà thẻ ấy **biến mất khi
  lượt xong** — nên không nơi nào nói tổng của phiên. Nay có ô `lượt / phiên`, tách `cached`
  riêng vì nó rẻ hơn nhiều lần và gộp vào là làm người đọc tưởng đắt hơn thực tế.

Đồng hồ ngữ cảnh cạnh bên **không** trả lời câu này: nó nói *còn nhớ được bao nhiêu*. Ngữ cảnh
đứng yên ở 20 % suốt buổi trong khi hoá đơn tăng đều là chuyện bình thường — mỗi lượt nạp lại
phần cố định rồi vứt đi.

Một ca kiểm nay quét mọi trường `status_bar` lõi gửi và đòi mỗi trường có người đọc.

#### Bộ đo tắt đúng lúc cần đo

Kênh kiểm thử bật theo sự có mặt của `.eide/ui-test` trong dự án — đúng, vì nó phải TẮT ở mọi
dự án thật. Hệ quả: **đổi dự án là mất kênh**, mà đổi dự án lại đúng là thứ cần đo. Nay đã bật
một lần trong phiên thì theo sang dự án sau; bật lần đầu vẫn phải do người đặt thư mục vào.

Kèm hai lỗi nữa ở chính bộ đo: con trỏ `daDoc` không về 0 khi sang inbox khác (kênh bỏ qua N
lệnh đầu của dự án mới), và `GiaoDien.__init__` **cắt trắng outbox** nên xoá đúng dòng
`kenh_mo` mình sắp đợi — thêm `xoa=False` để bám vào kênh đang mở.

#### Một ca kiểm vô nghĩa, bắt được bằng cách phá sản phẩm

`test_lõi_phat_NHIP_sau_moi_loi_goi_cong_cu` dò `for call in rsp.tool_calls:` trên cả tệp — mà
chuỗi ấy cũng nằm trong **docstring đầu `loop.py`**, nên nó bắt trọn hơn sáu trăm dòng và luôn
thấy `_nhip` ở đâu đó. Gỡ hẳn lời gọi ra, ca vẫn xanh. Nay neo vào dòng ngay sau vòng lặp và
chặn trên độ dài thân bắt được.

*Sáu phép phá, năm cái đỏ ngay — cái thứ sáu xanh, và đó là cái đáng giá nhất.*

### Số đo

**1 407 ca đơn vị** (+35) · bộ quét giao diện **124/124** · E2E qua app thật **22/22**
([`thu_doi_du_an_va_nhip.py`](../../tools/thu_doi_du_an_va_nhip.py)) · bộ dò tài liệu **0 chỗ
lệch** · sáu phép phá sản phẩm đều làm bộ kiểm đỏ.

---

### [DEV-317] 01/10/2026 · Công thức LaTeX chỉ đổi được ở MỘT trong sáu chỗ

Anh Công báo bản xuất tài liệu không render được LaTeX ra docx, pdf và pptx. Dựng một tài liệu
có công thức ở sáu ngữ cảnh rồi đọc lại từ chính tệp xuất ra:

| Ngữ cảnh | Word | PowerPoint |
|---|---|---|
| Đoạn văn nguyên vẹn `$$…$$` | **đổi được** | in cả dấu đô-la |
| Giữa dòng `$…$` | in nguyên `\frac{f_{VCO}}{PLLP}` | in nguyên |
| Gạch đầu dòng | in nguyên | in nguyên |
| Ô bảng | in nguyên | in nguyên |
| Trích dẫn | in nguyên | in nguyên |
| Rào ` ```math ` | in nguyên, dạng khối mã | in nguyên |

Ba tệp đều báo **ĐẠT**, và `so_doan`/`so_bang`/`so_ky_tu` đều đúng. *`ok` nói về lời gọi,
không nói về kết quả* — lần thứ bảy trong dự án này.

Gốc gọn: `cong_thuc_nguoi_doc` được gọi ở **đúng một chỗ** trong cả tệp — nhánh đoạn văn của
bộ dựng Word, và chỉ khi cả đoạn là `$$…$$`.

#### Sửa ở chỗ mọi ngữ cảnh đều đi qua

Phép đổi chuyển vào **bộ quét chữ trong dòng** (`_quet`), nơi đoạn văn, gạch đầu dòng, ô bảng,
trích dẫn, tiêu đề, slide và ô Excel đều phải đi qua. Đặt trước nhánh nhấn mạnh, vì `$a * b$`
có dấu sao và nhánh nghiêng đọc trước sẽ cắt công thức làm đôi.

Đoạn chỉ có `$$…$$` và rào ` ```math ` nay thành **một loại khối riêng** (`cong_thuc`), nhận ra
một lần ở bộ đọc Markdown — trước đây phép nhận nằm trong bộ dựng Word nên PowerPoint không
có. Bảng ký hiệu mở từ 23 lên 90 mục: đủ bộ chữ Hy Lạp, tập hợp, logic, giải tích, và ký tự
thoát `\%` `\{` `\}`.

#### Chỗ khó nhất: dấu đô-la cũng là tiền

"Giá $5 và $10 nữa" mà đọc thành công thức thì **ăn mất cả đoạn chữ ở giữa**. Bốn điều kiện,
mỗi cái loại một kiểu nhầm có thật: có dấu đóng cùng đoạn · ruột không dính khoảng trắng ở hai
đầu · không quá 300 ký tự · **ruột không phải toàn chữ số** (`$5$`, `$1.000$` là giá). Sáu câu
có dấu đô-la thật — giá tiền, biến shell `$HOME` — đều giữ nguyên, mà `$x$` và `$E = mc^2$`
vẫn đổi được.

#### Ba chốt chặn thừa nhau, không chốt nào đo được

`\le` là tiền tố của `\leq`. Bản đầu có **ba** cơ chế cùng ngăn chuyện ấy — thứ tự khai trong
bảng (một chốt vô hình), `sorted` theo độ dài, và `(?![A-Za-z])` — và **phá riêng cái nào bộ
kiểm cũng không đỏ**, vì hai cái còn lại đỡ.

Gộp còn một biểu thức, và đo lại cho thẳng thắn: hai thuộc tính của nó vẫn thừa nhau, bỏ cả
hai mới đỏ. Nói ra trong chú thích chứ không giấu. Thứ **thật sự đo được** nằm ở chỗ khác:
một ca kiểm phủ **cả bảng 90 ký hiệu**. Chính nó bắt được `\leftrightarrow` bị luật xoá
`\left` ăn mất đầu, ra thành `rightarrow` — lỗi không chốt nào ở trên chạm tới, và không ca
thử-một-lệnh nào tìm ra.

#### Lệnh không đổi được thì NÓI RA

`tex_con_sot` đếm phần còn sót — soi **bản đã đổi**, không soi nguồn, vì soi nguồn thì `\frac`
và `\times` cũng bị đếm và cảnh báo sẽ kêu mỗi lần. *Một cảnh báo luôn kêu thì bằng không
kêu.* `doc.render` nay báo ngay đầu câu trả lời: chưa đổi được lệnh nào, và chúng sẽ in ra
giấy đúng như đang viết.

Phân số bỏ ngoặc khi không cần: `(1)/(1000)` → `1/1000`, giữ `(a+b)/c`.

#### Một giờ mất vì bytecode cũ

Giữa lúc thử độ nhạy, phép phá đổi `findall(c)` → `findall(x)` — **cùng số ký tự**, và khôi
phục trong cùng một giây. Phép kiểm cache của Python là *mtime tính theo giây + kích thước
tệp*, nên nó không thấy gì đổi và tiếp tục chạy bản đã phá. `inspect.getsource` đọc tệp `.py`
nên hiện mã đúng, trong khi mã chạy là mã sai.

*Một phép đo đọc một chỗ và chạy một chỗ khác thì nói về chỗ nào cũng sai.* Từ nay xoá
`__pycache__` giữa các lượt phá.

#### Rồi ba lỗi nữa, cũng chỉ trang in bắt được

Dựng bộ tệp mẫu để anh Công tự kiểm, và nhìn bản PDF thì thấy ba chỗ ở đúng những ca chưa
từng thử:

| Viết | Ra | Vì sao |
|---|---|---|
| `\sqrt{R^2 + X^2}` | `√{R^2 + X^2}` | `\sqrt` nằm trong bảng như một ký tự lẻ, không ai gỡ ngoặc nhọn của nó |
| `2^{\circ}` | `2^°` | luật `^{…}` chạy trước, mà **độ là hậu tố chứ không phải số mũ** |
| `\frac{1}{2\pi\tau}` | `1/2πτ` | **sai nghĩa** — `1/2πτ` đọc thành `(1/2)·π·τ` |

Cái thứ ba đáng nói nhất: chuỗi ra **không còn một ký tự TeX nào**, mọi con số đọc lại đều
đúng, chỉ là nghĩa đã khác. Không bộ đếm nào chạm tới được.

Gốc là phép quyết định đóng ngoặc đếm theo *ký tự phép toán*, mà `2\pi\tau` không có dấu cộng
hay khoảng trắng nào. Nay đếm theo **hạng** — một lệnh TeX, một số, một tên là một hạng — và
số tách riêng khỏi tên đứng sau, vì trong TeX `2R` nghĩa là `2·R`.

Bộ tệp mẫu ở [`ket-qua-cong-thuc/`](../review-v3/test/ket-qua-cong-thuc/): một nguồn, bốn tệp
dựng ra, kèm bảng "phải thấy gì / không được thấy gì" cho từng mục.

### Số đo

**1 443 ca đơn vị** (+36) · bộ dò tài liệu **0 chỗ lệch** · sáu ngữ cảnh kiểm bằng cách mở lại
tệp **và bằng mắt trên trang PDF** · bảng 90 ký hiệu có ca phủ toàn bộ.

---

### [DEV-318] 01/10/2026 · EIDE chỉ nạp được bo ST — tác tử đứng trước một bo Arduino mà bó tay

Anh Công cắm bo robot MOBILUCK và bảo tác tử rà soát. Nó dò ra `/dev/cu.usbserial-21410`, rồi
`target.detect` trả về **`nap_duoc = false`** với câu *"KHÔNG có đường nạp nào"* — cho một bo
Arduino Nano đang cắm hẳn hoi.

Gốc: cả đường nạp của EIDE chỉ biết **ST-LINK** — `st-flash` và ổ đĩa MSD của bo
Discovery/Nucleo. `avrdude` có tên trong danh sách kiểm công cụ nhưng **không nằm trên đường
nạp nào**. Tác tử biên dịch được firmware ATmega328P (`build.compile` gọi `avr-gcc` qua lõi
`arduino:avr`) rồi dừng ở đó.

Anh Công: *"Phải để agent làm chứ. Sai thì fix cho agent thông minh hơn."*

#### Thêm gì

| | |
|---|---|
| `doc_chu_ky_avr()` | bắt tay bootloader, đọc **chữ ký ba byte từ silicon** |
| `nap_qua_avrdude()` | nạp `.hex` (tự đổi từ `.elf`), đòi dòng `verified` mới tính là xong |
| `doc_nguoc_avr()` | đọc ngược Flash **từ chip** rồi so từng byte — bằng chứng độc lập |
| `_byte_tu_ihex()` | đọc Intel HEX theo địa chỉ, dòng hỏng thì bỏ qua chứ không ném |

`target.detect` nhận thêm `doc_chu_ky_avr`; `target.flash` nhận thêm cách `avrdude`;
`target.verify` đọc `cach` của lần nạp gần nhất để chọn đúng đường đọc ngược — dùng `st-flash`
đọc một con AVR thì không phải *"chưa đối chiếu được"*, mà là **đo nhầm con chip**, và câu trả
lời sai ấy trông y hệt một câu trả lời đúng.

#### Cổng USB nối tiếp KHÔNG phải bằng chứng có chip

Nó là con chip cầu USB (CH340/FTDI) và vẫn hiện ra kể cả khi đã nhổ ATmega khỏi đế. Nên
`do_bo()` khai *"có đường nạp"* chứ không khai *"có chip"*, và phép đọc chữ ký là một **lựa
chọn tác tử phải nêu ra** — vì mọi thao tác avrdude đều **reset bo** qua DTR, mà reset một
robot đang cân bằng là làm nó ngã.

#### Một chữ `v`

Lần chạy đầu trên bo thật: tác tử thử cả 57 600 và 115 200 baud, rồi báo trung thực *"chưa đọc
được chữ ký"*. Chạy tay avrdude mới thấy nó in đúng một dòng:

    Avrdude done.  Thank you.

**avrdude 8.0 im lặng ở mức mặc định** — bắt tay xong, không in chữ ký. Thêm `-v`:

    Device signature = 1E 95 0F (ATmega328P, ATA6614Q, LGT8F328P)

Bo hoàn toàn khoẻ mạnh; thiếu một chữ `v` trong lệnh của tôi. Và ba phiên bản avrdude in chữ
ký **ba kiểu khác nhau** — `0x1e950f` · `0x1e 0x95 0x0f` · `1E 95 0F` — cả ba đều "chạy xong",
chỉ khác chỗ in. Đúng loại khác biệt chỉ lộ ra khi cắm bo thật.

#### Một lỗ hổng do chính bộ kiểm bắt

`ATmega8515` có trong bảng chữ ký mà **không có mã avrdude** — đọc ra tên chip rồi vẫn không
nạp được. Ca `test_moi_chu_ky_deu_tra_duoc_ma_avrdude` canh đúng bất biến ấy.

#### Kết quả trên bo thật

Tác tử tự gọi `target.detect` với `doc_chu_ky_avr=true` và đọc được **`0x1E 0x95 0x0F` →
ATmega328P**, khớp tài liệu. Chưa nạp — chờ anh Công xác nhận danh mục an toàn.

#### Nạp xong rồi mới thấy phép đối chiếu đã tụt xuống thành một lời miễn

Tác tử nạp đạt: 5 710 byte, avrdude in `verified`, đọc ngược 32 768 byte từ chip và **0 byte
lệch**. Nhưng trường `chip_da_doi_chieu` trong kho **rỗng**.

Tra sổ cái: hai lần gọi `target.flash` đầu bị chặn `E4013`, lần thứ ba đi qua bằng
`dong_y_khong_doi_chieu_chip=true`. Tức tác tử đã **bỏ qua phép đối chiếu chip** — thứ TC034
tồn tại để bắt — dù năm phút trước nó vừa đọc được `1e950f` và vừa ghim hộ chiếu ATmega328P.

Nó cầm đủ hai vế mà công cụ không ghép được: `target.flash` gọi `do_bo()` mới, và `do_bo()` cố
ý không đọc chữ ký AVR (việc ấy reset bo). Nên trên bo AVR, một phép kiểm an toàn **im lặng
hạ cấp thành một lời miễn** — đúng loại hỏng tệ nhất, vì nó vẫn xanh.

Vá: `target.flash` tự đọc chữ ký khi đường nạp là avrdude. Lý do lần này không có tác dụng
phụ — **sắp nạp thì cũng reset bo rồi**.

Nạp lại, không cờ miễn: `chip_da_doi_chieu = ATmega328P`, khớp hộ chiếu, 0 byte lệch.

### Số đo

**1 473 ca đơn vị** (+30) · bộ dò tài liệu **0 chỗ lệch** · nạp thật vào ATmega328P ở
`/dev/cu.usbserial-21410`, đọc ngược 32 768 byte, 0 byte lệch · 374 lời gọi mô hình ghi nguyên
văn.

---

## DEV-319 · Nới được hạn thời gian một lượt — vì việc FPGA có bước dài hơn hạn ngay từ bản chất

*01/10/2026. Lệch với MDD-40 §B1 và UC19.*

### Tài liệu nói gì

§B1 chốt ngân sách một lượt: **40 lời gọi công cụ, 300 giây**. UC19 nói rõ *"quá hạn lượt
(300 s) thả người dùng ra"*. Hai con số ấy chọn cho việc vi điều khiển, nơi mỗi bước dài vài
giây: biên dịch một firmware AVR mất dưới một giây, nạp qua avrdude mất bốn giây.

### Mã làm khác

`Budget.__post_init__` nay đọc hai biến môi trường `EIDE_TRAN_GIAY_LUOT` và
`EIDE_TRAN_LOI_GOI_LUOT`. **Mặc định không đổi** — vẫn 300 s và 40 lời gọi. Chỉ dự án nào cần
thì đặt biến.

Hai chốt chặn để việc nới không thành vô hạn:
- **Trần trên 7 200 giây.** Một hạn mức vô hạn biến "tác tử đang làm" thành "tác tử đang treo"
  mà không ai biết khi nào nên dừng chờ.
- **Không hạ được xuống dưới mặc định.** Biến này để nới, không để siết — siết hạn mức là cách
  làm tác tử bỏ việc giữa đường mà vẫn báo xong.
- Chuỗi không phải số thì giữ mặc định, không báo lỗi: một biến môi trường gõ sai không nên làm
  cả phiên không chạy được.

### Vì sao lệch

Việc FPGA có những bước **dài hơn hạn một lượt ngay từ bản chất công việc**, không phải vì chậm:

| Bước | Thời gian |
|---|---|
| Tải gói `oss-cad-suite` | **483 MB** |
| Tổng hợp một lõi RISC-V bằng Yosys rồi đặt-đi dây bằng nextpnr | vài phút |

Với hạn 300 giây, tác tử **không bao giờ chạm được** tới lúc một lời gọi `tool.install` xong. Nó
hết lượt giữa đường; lần sau vào lại thì bắt đầu từ đầu. Đó là một vòng lặp không bao giờ kết
thúc, không phải một bước chậm.

Đo được ngày 01/10/2026: hai lượt liền tác tử tiêu hết 300 giây vào `env.check` và `tool.search`
rồi hết lượt **trước khi gọi `tool.install` lần nào**.

### Hướng đúng hơn, chưa làm

Nới hạn mức là cách chữa chỗ đau, không phải cách chữa nguyên nhân. Cách đúng là cho
`tool.install` và các bước dài khác **chạy ở chế độ nền**, báo tiến độ qua nhiều lượt, và giữ
trạng thái để lượt sau tiếp tục chứ không làm lại. Khi đó hạn 300 giây của §B1 giữ nguyên được,
vì lượt không còn phải chờ bước dài.

Chưa làm vì nó cần thêm cơ chế trạng thái giữa các lượt. Ghi lại đây để không ai nhầm việc nới
hạn mức là lời giải cuối.

## [DEV-320] Mã máy và cấu hình phần cứng phải khớp nhau, và EIDE phải tự nói ra

*02/10/2026. `src/eide/build/toolchain.py`, `src/eide/build/hdl.py`, `src/eide/tools/hdl.py`.*

Để trả lời câu "189 chu kỳ mỗi cặp (i,j) đi đâu", tác tử chạy một phép đo so hai cấu hình
CPU — có bộ nhân phần cứng và không có:

```
build.compile  isa="rv32i"     →  hdl.sim  CFG_MUL=1
build.compile  isa="rv32i"     →  hdl.sim  CFG_MUL=0
```

Hai lượt ra **số giống hệt nhau**, và con số giống nhau ấy được đọc thành *"bộ nhân phần
cứng không giúp gì"*.

Nhưng `-march=rv32i` **bảo đảm** mã máy không chứa một lệnh nhân nào. Bộ nhân ngồi không cả
hai lượt. Phép đo ấy không so hai cấu hình — nó chạy cùng một thứ hai lần.

Cái sai này không hiện ra thành lỗi. Cả hai lượt `ok=true`, cả hai in ra số, hai con số bằng
nhau trông đúng như một kết luận. Không công cụ nào có cớ để từ chối, vì xét riêng thì mỗi
lời gọi đều hợp lệ. Chỉ **cặp** của chúng là vô nghĩa.

Tôi tháo mã ra đếm:

| | lệnh `mul` | lời gọi `__mulsi3` |
|---|---|---|
| `rv32i` | 0 | 10 (trong 2 hàm) |
| `rv32im` | 4 | 0 |

**Thêm vào EIDE ba thứ:**

`KetQuaBienDich.lenh_mo_rong` — mã máy **có thật** dùng lệnh mở rộng nào, đếm từ bản tháo mã.
Không suy từ cờ `-march`: cờ ấy chỉ *cho phép* sinh lệnh, không bảo đảm có lệnh nào được sinh.

`toolchain.kiem_khop_phan_cung(lenh_mo_rong, cau_hinh)` — đối chiếu, trả câu cảnh báo nói ra
**hệ quả** chứ không chỉ nói là lệch: *"hai lượt sẽ ra số BẰNG NHAU, và con số bằng nhau ấy
không nói gì về bộ nhân cả"*. Bắt cả chiều ngược: mã máy có `mul` mà CPU tắt bộ nhân thì CPU
bẫy lệnh lạ và chương trình không tới đích.

`hdl.sim` tự đọc dữ kiện ấy từ `build:firmware` trong kho. Tác tử không phải nhớ, không phải
tự nghĩ ra việc đối chiếu.

**Và một lỗi tìm ra nhờ chính việc nối dây này.** `_chay()` kết thúc bằng:

```python
kq.loi, kq.canh_bao = doc_thong_diep(kq.nguyen_van, goc=goc)
```

Phép **gán** ấy xoá sạch mọi cảnh báo bên gọi đã đặt vào trước khi chạy. Cảnh báo được dựng
ra rồi bị bỏ đi trong im lặng — đúng cái mẫu *cơ chế có sẵn, đường dẫn tới nó đứt*, lần này
chính bộ kiểm bắt được. Nay cộng thêm, không gán.

Bộ kiểm: 1538 → **1546**. Trong đó hai ca đi qua `registry.call`, vì bài học `_goc()` còn đó:
lớp lõi xanh không nói gì về việc lớp công cụ có nối đúng không.

## [DEV-321] Hết hạn phải diệt cả nhóm tiến trình, không chỉ tiến trình con

*02/10/2026. `src/eide/build/hdl.py`.*

Một lượt `hdl.synth` chạm hạn 1 800 giây. Công cụ báo trượt đúng, và `hdl.pnr` sau đó từ chối
đúng — *"Không có tệp mạng cổng `soc_top.json`. Chạy `hdl.synth` trước."* Mọi thứ nhìn như đã
xử lý xong.

Nhưng `yosys` không tự chạy ABC. Nó gọi `sh -c yosys-abc …`. Còn
`subprocess.run(timeout=…)` chỉ diệt **đúng tiến trình con trực tiếp** — nên `sh` và
`yosys-abc` sống sót. Tôi phát hiện ra khi thấy một `yosys-abc` đã chạy **49 phút** trong khi
lượt sinh ra nó đã bị dừng và đã báo trượt từ lâu.

Nó không chỉ chiếm chỗ. Nó **giành CPU của lượt chạy kế tiếp**, nên lượt sau chậm đi, và cái
chậm ấy bị đọc thành đặc tính của thiết kế. Một phép đo thời gian bị tiến trình mồ côi làm
lệch là một phép đo sai mà trông không có gì sai cả — và trong đề án này thời gian tổng hợp
đang là một con số ta dùng để kết luận.

Nay `_chay` dùng `subprocess.Popen(..., start_new_session=True)` để đặt tiến trình vào một
nhóm riêng, rồi `_diet_ca_nhom()` gửi `SIGTERM` cho cả nhóm (cho công cụ kịp dọn tệp tạm) và
`SIGKILL` cho những gì còn sống.

Ca kiểm `test_het_han_diet_ca_chau_khong_chi_con` cho `sh` đẻ một tiến trình cháu sống lâu,
ghi pid của nó ra tệp, rồi canh xem cháu có chết theo không. Và tôi đã kiểm rằng ca ấy **đo
được thật** — chạy hai cách cạnh nhau trên cùng một kịch bản:

```
subprocess.run(timeout=) — cách cũ : cháu còn sống = True
diệt cả nhóm — cách mới            : cháu còn sống = False
```

Phép so ấy quan trọng hơn bản thân ca kiểm: một ca kiểm xanh với mã đã vá chưa nói được nó
có bắt được lỗi cũ không.

Bộ kiểm: 1546 → **1547**.

## [DEV-322] Bỏ Bài 3 khỏi đặc tả FPGA, và một kết quả âm đáng giữ

*02/10/2026. `docs/fpga/yeu-cau-agent-riscv-tang-nano-20k.md`, `README.md`,
`docs/riscv-tn20k/`, `docs/md/DE-XUAT-CAU-TRUC-FPGA.md`, và `rtl/` của dự án.*

Anh Công đưa Bài 3 ra khỏi phạm vi. Đặc tả nay gồm hai bài. Đã sửa: cắt hẳn mục BÀI 3 khỏi
đặc tả, mười hai chỗ nhắc nó ở ngoài mục ấy, bối cảnh A1 từ ba mục tiêu còn hai, A2 bỏ lời
hứa về lệnh tuỳ biến và vector, điểm dừng bắt buộc từ sáu còn năm (và đánh số lại cho liền),
bảng khả thi bỏ hai dòng 3a/3b/3c.

Tài liệu Agent đã nộp thì **thêm ghi chú, không viết lại** — một bản phân tích có ngày tháng
là hiện vật, sửa nội dung nó là xoá dấu vết. Áp cho `nang-luc-kit.md` (hai bản),
`ho-so-tac-tu/EIDE-bai1-2.md`.

Giữ lại kho lưu `docs/riscv-tn20k/bai3/` kèm `NGOAI-PHAM-VI.md`, vì số đo thật xoá đi thì
không dựng lại được.

### Kết quả âm: mô phỏng đúng không nói gì về việc có nạp được

Nấc 3c **đúng về chức năng**: `cpm=3.84`, tổng kiểm `0x08EA34EA` trùng đáp án Python độc lập,
bộ kiểm đơn vị bắt 7/7 phép phá. Nhưng tổng hợp lên chip **không về đích**.

Biểu hiện đầu tiên chỉ là *chậm*: 5 giây thành hơn 30 phút rồi chạm hạn. Tôi đoán sai **hai
lần** — lần đầu nghĩ do bộ dồn kênh đọc tệp thanh ghi vector (Agent chốt toán hạng vào
`opa`/`opb`, vẫn chậm), lần sau nghĩ do phép làm phẳng toàn mạch. Nguyên nhân chỉ lộ ra khi
tổng hợp **riêng mô-đun bộ nhớ**:

```
Module bram: replaced 819152 cells with 5635760 new cells
  262144  DFFE          ◀── cả 32 KB thành flip-flop
  786384  $_MUX_
Extracted 2474345 AND gates ... 262516 inputs
```

Thêm cổng thứ hai vào BRAM làm **suy luận BSRAM đứt hoàn toàn**. Cả 32 KB bị dựng thành
262 144 thanh ghi trên một chip có 15 552 — vượt 17 lần. `yosys-abc` cày 30 phút để tối ưu
một mạng 2,47 triệu cổng cho một mạch không bao giờ nạp được.

Nguyên nhân ở **cấu trúc**, không ở số cổng: bản hai cổng đặt cả hai cổng trong cùng một khối
`always @(posedge clk)`, mỗi cổng vừa đọc vừa ghi với cho phép ghi theo từng byte, trên cùng
một mảng. Gowin BSRAM không có nguyên thuỷ nào như thế.

> Một thiết kế mô phỏng đúng chưa nói gì về việc nó có nạp được không. Hai câu hỏi ấy khác
> nhau, và chúng được trả lời bởi hai công cụ khác nhau.

Chính đặc tả Bài 3 đã đặt đúng câu hỏi này — mục kiến trúc điểm (3): *"luồng công cụ ... theo
kết quả kiểm tra BRAM hai cổng ở G1"*. Câu hỏi đặt đúng mà chưa ai trả lời trước khi viết RTL.

### `rtl/` đã trả về bản chạy được, và chứng minh lại

Dự án đang ở trạng thái **không vừa chip**, nên phải trả về. `bram.v` bỏ cổng B; `soc_top.v`
bỏ include `bai3/`, bỏ `ENABLE_VMINI`, `ENABLE_PCPI` mặc định 0, vẫn giữ các dây PCPI buộc về
mức không tích cực — `pcpi_wait` thả nổi thì CPU có thể treo vĩnh viễn ở một lệnh lạ, một kiểu
hỏng không hiện ra lúc mô phỏng nếu chương trình không dùng lệnh lạ nào.

Đo lại sau khi trả về:

```
tổng hợp   4,6 giây (từ >1800)   LUT4 2 211/20 736 = 10,7 %   BSRAM 16/46 suy luận lại được
đặt-đi-dây 20,0 giây             Fmax 106,01 MHz, cần 27
Bài 1      nhận đúng "Hello from PicoRV32" hai lần, PASS
Bài 2      H0 618,04 · H1 83,40 · H2 49,40 — trùng đúng đường cơ sở cũ
```

Và một ca thật cho DEV-320 vừa làm: chạy Bài 2 với mã máy `rv32im` trên cấu hình `CFG_MUL=0`
thì **không ra dòng RESULT nào** (CPU bẫy lệnh lạ), kèm đúng cảnh báo *"Mã máy chứa 15 lệnh
của phần `m` nhưng cấu hình CPU TẮT bộ nhân"*. Chỗ vá ấy bắt được ca thật, không chỉ ca kiểm.

## [DEV-323] Duyệt cổng xong phải nói ra, nếu không mô hình tự dựng lời giải thích

*02/10/2026. `src/eide/loop.py`.*

Hai lượt liền trong phiên FPGA: thẻ cổng `G-QUAL` hiện ra, người dùng bấm Duyệt, và tác tử
báo lại rằng **lời giao việc đã bị cắt mất**, rồi xin gửi lại đề bài.

Tôi tin ngay. Ghi luôn một mục việc-chờ-làm rằng cổng xén dữ liệu. **Sai.** Tra sổ cái thì
lời giao việc còn nguyên **770 ký tự, đủ cả đầu lẫn đuôi**.

Nguyên nhân thật nằm ở nhánh duyệt cổng chặn một lời gọi công cụ — nhánh **không phát lời
nhắc nào**. Mô hình thấy đúng hai thứ mâu thuẫn và liền nhau:

```
E4003  "DỪNG LẠI, đừng gọi lại tool này, kết thúc lượt và chờ quyết định"
       ← rồi ngay sau là kết quả CỦA CHÍNH công cụ ấy, không ai giải thích
```

Nó dung hoà bằng cách dựng ra một lời giải thích: đề bài đã bị mất. Lời ấy nghe hợp lý, và
nó tốn hai lượt cùng một mục tài liệu ghi sai nguyên nhân.

Nhánh **từ chối** đã có lời nhắc (*"Đừng tìm đường khác để làm việc đó"*) và đã có ca kiểm.
Nhánh cổng do S0 phát cũng có. Chỉ nhánh thường gặp nhất là không — và nó không có vì không
ai thấy thiếu: lời gọi vẫn chạy, kết quả vẫn về, mọi thứ xanh.

Nay lời nhắc nói ba điều, mỗi điều chữa một cách hiểu sai đã xảy ra thật: cổng đã được duyệt
và lời gọi đã chạy thay; `E4003` hết hiệu lực; **đề bài vẫn là lời người dùng giao ở đầu
lượt, nó không bị mất và không cần hỏi lại**.

Ca kiểm `test_duyet_cong_chan_loi_goi_thi_PHAI_noi_ra` canh cả ba câu ấy, không chỉ canh có
lời nhắc.

> Một khoảng trống trong ngữ cảnh không làm mô hình im lặng. Nó làm mô hình dựng ra một lời
> giải thích, và lời ấy nghe hợp lý.

Và một điều về chính tôi, đáng ghi hơn chỗ vá: suốt phiên này tôi áp đúng một quy tắc cho tác
tử — *lời báo của nó là lời kể, phải kiểm* — rồi tin ngay một lời kể của nó về chính EIDE, và
ghi cái sai ấy thành tài liệu. Một lời kể sai về **nguyên nhân** đắt hơn một lỗi, vì nó gửi
người đọc sau đi sai hướng.

Bộ kiểm: 1547 → **1548**.

## [DEV-324] `ledger.query` cắt ở 220 ký tự mà không nói — và nó làm tôi sai hai lần

*02/10/2026. `src/eide/tools/builtin.py`.*

Ba lượt liền trong phiên FPGA: thẻ cổng ngắt lượt, người dùng duyệt, rồi tác tử báo rằng lời
giao việc đã bị cắt và xin gửi lại đề bài.

Tôi sai hai lần trước khi tìm ra.

**Lần một:** tin ngay, ghi vào `VIEC-CHO-LAM` rằng cổng xén dữ liệu, commit.

**Lần hai:** tra sổ cái, thấy lời giao việc còn nguyên **770 ký tự cả đầu lẫn đuôi**, kết luận
tác tử kể sai, viết lại mục ấy kèm một bài học về việc đừng tin lời kể của tác tử, commit lần
nữa. Và vá DEV-323 (nhánh duyệt cổng thiếu lời nhắc) — chỗ vá ấy đúng, nhưng nó không phải
nguyên nhân của hiện tượng.

**Nguyên nhân thật:**

```python
ra.append({... "tom_tat": chu[:220]})
```

`ledger.query` cắt **mọi** sự kiện ở 220 ký tự và không nói gì. Tôi tra **tệp**
`.eide/ledger.jsonl` nên thấy đủ. Tác tử đọc **qua công cụ** nên thấy 220 ký tự đầu của một
lời giao việc 770 ký tự — và nó báo đúng rằng đề bài bị cắt.

**Cả hai đều báo đúng về thứ mình nhìn thấy.** Chỗ hỏng là công cụ cắt trong im lặng, nên
không bên nào biết hai bên đang xem hai thứ khác nhau. Và tôi đã dùng cái thấy của mình để
bác cái thấy của nó, rồi ghi kết luận ấy thành tài liệu.

Nay: bản tóm lên **1 200 ký tự** (một lời giao việc dài hơn 220 ký tự là chuyện thường), và
khi còn cắt thì đánh dấu `da_cat` + `do_dai_that`, kèm lời nhắc nói rõ *đây là bản tóm* và
chỉ đường đọc đủ — *hỏi người dùng, hoặc đọc thẳng `.eide/ledger.jsonl`*, đừng suy từ phần
thấy được.

Ca kiểm `test_ledger_query_noi_ra_khi_da_cat` canh bốn điều: sự kiện dài bị đánh dấu, sự kiện
ngắn **không** bị đánh dấu (không cảnh báo bừa), có `do_dai_that`, và lời nhắc chỉ được đường
đọc đủ.

> Khi hai bên báo hai điều trái nhau, câu hỏi đầu tiên không phải *"ai sai"* mà là **"hai bên
> có đang xem cùng một thứ không"**.

Đây là lần thứ ba trong đề án một công cụ **cắt hoặc bỏ dữ liệu trong im lặng** rồi gây ra một
kết luận sai: `_chay` gán đè `canh_bao` (DEV-320), tệp ra còn sót từ lần trước làm chặng trượt
báo đạt (01/10), và nay là chỗ này. Mẫu chung: **im lặng trông giống hoạt động bình thường.**

Bộ kiểm: 1548 → **1549**.

## [DEV-325] Năm việc giao diện, và chỗ đứng để đo chúng

*02/10/2026. `ui/EIDEApp/` (Package.swift · Markdown.swift · MathText.swift · AppState.swift ·
ConsoleView.swift · UITestChannel.swift), `src/eide/xuat_ban.py`.*

Anh Công nêu năm việc về giao diện ngày 01/10/2026. Cả năm đều kết thúc trong sổ việc bằng
cùng một câu: *"không con số nào bắt được chuyện này, phải nhìn màn hình"*.

Câu ấy đúng với bề rộng cột và màu sắc. Nhưng nó **sai với phần tách khối, tách ô, đổi ký
hiệu** — những phần ấy là hàm thuần, vào chuỗi ra chuỗi. Lý do thật khiến không đo được là
khác: `Package.swift` chỉ có **một `executableTarget`**, không một mục tiêu kiểm nào, nên
**toàn bộ giao diện chưa từng có một ca kiểm tự động**.

Nên việc đầu tiên không phải vá, mà là dựng chỗ đứng: thêm `testTarget` dùng
`@testable import EIDE`. Sau đó mới vá được có kiểm.

### Ba trong năm mục chẩn đoán SAI nguyên nhân

Đây là phần đáng đọc hơn các bản vá.

**Mục 1 — công thức LaTeX.** Sổ việc ghi *"phần công thức chưa hề được nối vào bộ dựng
Markdown của Swift"*. **Sai**: `MathText.khoiCongThuc` và `MathText.tach` đã nối từ trước.

Lỗi thật chỉ thấy khi so hai bảng ký hiệu:

| | Python | Swift |
|---|---|---|
| số mục | 91 | 76 |
| `\sum` | `∑` phép tổng | `Σ` chữ Sigma Hy Lạp |
| `\prod` | `∏` phép nhân | `Π` chữ Pi Hy Lạp |

Swift thiếu 28 mục Python có (`\Sigma`, `\Theta`, `\chi`, `\emptyset`, `\implies`…) — chúng
hiện ra dạng TeX thô trên màn mà đúng trong tệp Word, đúng điều anh Công thấy. Python thiếu
13 lệnh bố cục Swift có. Và hai mục **sai**: dùng chữ Hy Lạp thay ký hiệu phép toán, nên
`\Sigma` và `\sum` ra **cùng một chữ** — hai thứ khác nhau hiện ra như một.

Nay bảng Swift **sinh ra từ bảng Python**, cả hai 109 mục, và
`test_hai_bang_ky_hieu_phai_giong_nhau` đọc thẳng tệp Swift để canh.

**Mục 2 — `**` lọt ra màn.** Phần lớn **đã hoạt động**: 11 trên 17 ca kiểm mới xanh ngay với
mã cũ, kể cả ca khó nhất (`*Đề tài: **Phát triển…** · Vũ Trí Công*`). Giá trị của 11 ca ấy
không phải vá gì, mà là chúng **ràng lại** những thứ đang đúng.

**Mục 5 — bảng dựng sai.** Mục duy nhất chẩn đoán **trúng hoàn toàn**, cả bốn lỗi.

### Hai lỗi tìm ra trong lúc vá, không có trong sổ việc

**`\alphabet` → `αbet`.** Swift thay từng mục bằng `replacingOccurrences`, xếp dài trước ngắn.
Cách ấy đủ để `\leftarrow` không bị `\left` ăn đầu — nhưng **chỉ với lệnh có trong bảng**. Một
lệnh chưa biết mà bắt đầu bằng tên lệnh đã biết thì vẫn bị cắt. Hậu quả thứ hai tệ hơn hậu quả
thứ nhất: phép kiểm cuối hàm — *"còn gạch chéo nghĩa là còn lệnh chưa hiểu"* — **mất tác dụng**,
vì gạch chéo đã bị ăn cùng phần đầu lệnh. Khối công thức báo đã đổi trọn vẹn và hiện một kết
quả sai, thay vì hiện nguyên bản kèm dòng *"chưa đổi hết ký hiệu"*. Đúng cái mà chú thích của
chính hàm ấy hứa là sẽ không xảy ra.

**`a\:b` và `a\ b` không đổi được.** Chốt `(?![A-Za-z])` phía Python đúng với lệnh viết bằng
chữ (`\leftb` không phải `\left`) nhưng **sai với lệnh dạng dấu câu** — tên lệnh kết thúc ngay
ở dấu ấy, nên một chữ đứng sau là cách dùng thường. Nay cả hai bên chia **hai nhóm**.

Lệch này nằm im cho tới lúc bảng có lệnh dấu câu. Nó được bắt bởi
`test_MOI_lenh_trong_bang_doi_dung_mot_minh_no` — ca phủ cả bảng, viết từ trước cho một mục
đích khác.

### Năm bản vá

**Bảng Markdown** — bốn lỗi: hàng không được san cho bằng tiêu đề (`ForEach` đi theo số ô của
hàng); `oCua` cắt theo mọi dấu `|` kể cả trong `` ` `` và `\|`; bề rộng đếm **mã nguồn** nên ô
`**ĐẠT**` được cấp chỗ cho 7 ký tự mà chỉ hiện 3; chỉ đo 20 hàng đầu trong khi bảng tuân thủ
của dự án robot có 109 hàng. Thêm: trần ghi cứng 170 px (≈27 ký tự) cho bảng từ 4 cột, nay
300 px kèm **hạn tổng** và sàn, và bề rộng tính **một lần** lúc dựng chứ không trong thân
`View` — `daiHienRa` chạy bộ dựng Markdown, gọi nó cho từng ô của bảng 109×6 là hàng chục
nghìn lượt mỗi lần vẽ lại.

**Rào ` ```math `** nay thành công thức, không còn là khối mã.

**Cảnh báo dồn đống** — 10 chỗ thêm, 1 chỗ xoá, và chỗ xoá ấy là `doiDuAn()`. Nay mọi chỗ đi
qua `themThongBao()`: **gộp cái trùng kèm số lần** (`×10` thay cho mười thẻ — một cảnh báo nổ
mười lần nói lên điều khác với mười cảnh báo khác nhau), nút tắt từng thẻ, nút "Dọn hết" khi
có từ ba thẻ, và mức `info` tự hết sau 25 giây. Mức `warn`/`error` **không** tự hết.

**Điểm mù của bộ quét** — `UITestChannel` chỉ xuất `notices.suffix(5)`, nên dù màn hình dồn
một trăm thẻ nó vẫn chỉ thấy năm: **không thể** phát hiện chuyện dồn đống, mãi mãi. Nay xuất
thêm `thong_bao_tong` và `thong_bao_tong_lan`, nên đặt được ngưỡng.

**Bản chụp cắt ở 3 000 ký tự** — nâng lên 20 000, và khi còn phải cắt thì **ghi bản đủ ra tệp**
rồi để lại đường dẫn cùng độ dài thật ngay trong chuỗi. Nhật ký là sở cứ, và một sở cứ cắt mất
đoạn cuối thì chỗ bị cắt luôn là chỗ không ai biết là đã mất.

### Đo

31 ca kiểm Swift, và **13 trong số đó đỏ khi trả lại mã cũ** — tôi kiểm riêng từng nhóm bằng
cách phá lại mã rồi chạy. Bộ kiểm Python 1551 → **1552**.

Còn lại, không làm lượt này: **A5.10 cây mô-đun** cần một bộ đọc quan hệ gọi mô-đun Verilog, và
**A8 chưa hiện kết quả `build:hdl:sim`** — kết quả bộ kiểm HDL với phép đo độ nhạy không hiện
ở đâu trên giao diện.

## [DEV-326] A8.0 — kết quả bộ kiểm HDL, và đường dẫn cho con số độ nhạy

*02/10/2026. `src/eide/surfaces.py`, `src/eide/tools/hdl.py`, `src/eide/build/hdl.py`.*

Tab Mô phỏng dựng cho `sim.run` của vi điều khiển: nó đọc hiện vật loại `sim_result`. `hdl.sim`
ghi vào `build:hdl:sim`, một khoá khác hẳn. Nên **kết quả mọi bộ kiểm HDL không hiện ở đâu trên
giao diện** — kể cả lượt vừa chạy 1 000 bộ giá trị ngẫu nhiên và bắt 7/7 phép phá mã. Lại đúng
cái mẫu: cơ chế có sẵn, đường dẫn tới nó đứt. Đây là lần thứ ba trong bốn ngày (A5.11/A5.13 là
hai lần trước).

Khối A8.0 đặt **dòng độ nhạy ngay dưới dòng kết luận**, không đặt ở cuối. Và khi thiếu con số
ấy thì nó **nói ra là thiếu**, kèm cách đo:

> Độ nhạy bộ kiểm — CHƯA ĐO. Một bộ kiểm in PASS mà chưa ai phá mã thì chưa biết nó canh được
> gì — hãy sửa một chỗ trong thiết kế, chạy lại, và xem bộ kiểm có trượt không.

Nấc 3a của Bài 3 từng PASS với hai lỗ, và chỉ phép đo độ nhạy mới thấy. Một chữ PASS màu xanh
không kèm con số ấy là nửa sự thật.

### Con số độ nhạy trước đây không đi đâu cả

`test.sensitivity` đo được chuyện này cho firmware C, nhưng nó **không ghi hiện vật nào** — con
số chỉ trả về cho mô hình rồi mất theo lượt. Nên khối vừa dựng sẽ hiện "CHƯA ĐO" vĩnh viễn, kể
cả sau khi tác tử vừa phá mã bảy lần.

Nay `hdl.sim` nhận tham số `do_nhay={"bat": 7, "tong": 7}`, ghi vào hiện vật, và A8.0 đọc ra.
Mô tả tham số nói thẳng điều kiện: *"Chỉ điền khi đã thật sự làm — con số này nói bộ kiểm canh
được gì, và một con số bịa ra thì tệ hơn không có."*

> Một phép đo không vào kho thì lượt sau không ai biết nó từng xảy ra.

### Và một bài học về chính bộ kiểm của tôi

Năm ca `test_A8_*` đầu tiên gọi `_khoi_mo_phong_hdl` trực tiếp. Tôi thử **bỏ hẳn dòng
`khoi += _khoi_mo_phong_hdl(store)` ra khỏi `simulation()`** — cả năm ca vẫn xanh.

Đúng cái bài học của `_goc()`: lớp lõi xanh không nói gì về việc lớp trên có nối đúng không, và
cả năm công cụ `hdl.*` từng đổ với `E5999` vì chính chuyện đó. Thêm
`test_A8_di_qua_BO_DUNG_TAB_that_khong_chi_goi_ham` — nó đi qua `simulation()` và đỏ đúng khi
đường dẫn đứt:

```
AssertionError: khối A8.0 chưa được nối vào tab Mô phỏng — khối hiện có: []
```

Bộ kiểm: 1552 → **1558**.

## [DEV-327] A5.10 — cây mô-đun của chip, đọc từ Verilog thật

*02/10/2026. `src/eide/hdl_cay.py` (mới), `src/eide/surfaces.py`.*

Khối cuối còn thiếu của tab Thiết kế, và là khối anh Công nêu rõ nhất: nhìn vào phải biết
**mô-đun nào dùng chung, mô-đun nào riêng của bài nào** — vì với FPGA, đổi một mô-đun chung là
đổi cho mọi bài.

Đối xứng với A5.6 (cây phần mềm từ `#include`). Ở đây cạnh đọc từ **lời gọi mô-đun** thật.

Ba quyết định, và mỗi cái tránh một cách sai cụ thể:

**Danh sách tệp lấy từ lệnh tổng hợp ĐÃ CHẠY, không glob thư mục.** Cây vẽ ra khi đó là cây của
thiết kế **thật sự nằm trong chip**. Khác biệt ấy có thật: dự án RISC-V có `blinky.v` rời và ba
mô-đun của Bài 3 đã ra khỏi phạm vi — glob thì chúng vào cây, và thiết kế trông như có thêm bốn
khối không ai dùng.

**Không có quan hệ thật thì không vẽ.** Luật của A5.6. Một cây toàn nút rời trông như một thiết
kế không có cấu trúc, mà sự thật chỉ là bộ đọc không đọc được gì.

**Cột "Trong thiết kế" tách hai loại.** Một mô-đun được khai trong tệp đã tổng hợp mà không ai
gọi thì Yosys bỏ đi — nó không vào chip. Gộp vào một bảng thì con số tài nguyên ở A5.11 bên dưới
trông như không khớp.

### Ba lỗi, và cả ba chỉ lộ ra khi chạy trên dự án thật

**Mẫu bắt lời gọi thiếu ranh giới từ.** Bản đầu viết `[ \t]*` giữa hai tên — tức cho phép
**không có gì**. Nên:

```
if (…)       → mô-đun `i`     gọi thực thể `f`
for (…)      → mô-đun `fo`    gọi thực thể `r`
case (…)     → mô-đun `cas`   gọi thực thể `e`
assert (…)   → mô-đun `asser` gọi thực thể `t`
```

Danh sách từ khoá **không đỡ được**, vì `i` và `fo` không phải từ khoá — chúng là *một nửa* của
từ khoá. Cây PicoRV32 ra **65 quan hệ, 50 là rác**, và mỗi nút rác mang nhãn "KHÔNG thấy khai ở
tệp nào" nên trông đúng như một tệp bị thiếu. Sau khi vá: 15 quan hệ, không nút nào chưa thấy
khai.

**Vẽ cây mất hết nhánh.** Tiền tố không được nối tiếp, nên 20 nút hiện ra cùng một mức — một
danh sách phẳng trông như thiết kế không có tầng.

**Neo `^` bỏ qua lời gọi sau dấu `;`.** Thấy theo một đường vòng đáng ghi: ca kiểm qua tab của
tôi đỏ với `0 quan hệ gọi` trong khi khối đã nối đúng. Hai thứ ấy **trông giống nhau trên màn
hình** — một khối chưa nối, và một khối nối rồi mà bộ đọc không đọc ra gì. Nay neo ở đầu dòng
hoặc sau `;`, và không nới rộng hơn: neo giữa biểu thức thì mọi lời gọi hàm trong một phép gán
đều thành "mô-đun".

Không ca kiểm nào trên chuỗi tự soạn bắt được ba lỗi ấy, vì tôi sẽ không nghĩ ra việc thử
`if (`. Nay chúng thành ca kiểm — `test_tu_khoa_KHONG_thanh_mo_dun` phá lại cả bốn và ra đúng
`['i', 'fo', 'cas', 'asser']`.

### Và một ca canh đường dẫn

`test_A5_10_di_qua_BO_DUNG_TAB_that` đi qua `design()` thật. Bỏ dòng nối khối ra thì nó đỏ:

```
AssertionError: khối A5.10 chưa được nối vào tab Thiết kế — khối hiện có: ['A5.4', 'A5.11', 'A5.6', 'A5.2']
```

Lần thứ hai trong một ngày tôi phải thêm ca kiểu này. Lớp lõi xanh không nói gì về việc lớp
trên có nối đúng không.

Bộ kiểm: 1558 → **1573**.

## [DEV-328] `$[-128, 127]$` — luật công thức giữa dòng lệch nhau, và chỗ bộ kiểm tôi bỏ lọt

*02/10/2026. `ui/EIDEApp/.../MathText.swift`, `src/eide/xuat_ban.py`,
`tests/du-lieu-chung/cong-thuc-giua-dong.json`.*

Anh Công thấy câu này trên màn hình **sau khi tôi đã báo xong việc công thức** (DEV-325):

```
Với kiểu I8: giá trị trong $[-128, 127]$, acc_t là int32_t.
```

Hai dấu đô-la còn nguyên. Mà trong tệp Word thì đúng — nên lại là một chỗ hai bên lệch nhau,
đúng loại DEV-325 vừa dọn cho bảng ký hiệu.

### Luật của Swift sai theo CẢ HAI chiều

```swift
if tex.contains("\\") || tex.rangeOfCharacter(from: .letters) != nil
    || tex.contains("^") || tex.contains("_")
```

- `[-128, 127]` **không có** thứ nào trong bốn thứ ấy, nên nó rơi xuống chữ thường mang theo
  cả hai dấu đô-la.
- `giá $5 và $10 nữa` có ruột `"5 và "`, **có chữ cái**, nên luật này nhận là công thức và
  **ăn mất đoạn chữ ở giữa** — ra `giá 5 và10 nữa`. Tôi thấy nó trong lời báo của ca kiểm khi
  phá lại mã cũ.

Phía Python đã đúng từ trước, và luật của nó được nghĩ kỹ hơn: bốn điều kiện, mỗi cái loại một
kiểu nhầm có thật — có dấu đóng, ruột không bắt đầu/kết thúc bằng khoảng trắng (chính điều kiện
này loại `"5 và "`), không có dấu `$` bên trong, không quá 300 ký tự, và ruột không thuần chữ
số. Swift nay dùng đúng luật ấy.

### Chỗ bộ kiểm của tôi bỏ lọt, và vì sao

Ca `test_cong_thuc_trong_dong_doi_thanh_ky_hieu` tôi viết trong DEV-325 thử
`$\alpha \le 0.05$` — **một công thức có lệnh TeX**. Nó xanh với cả luật cũ. Phải có một ca
**không chứa lệnh nào** mới thấy, và tôi không nghĩ ra ca ấy.

Phía Python thì có đủ: `test_tien_KHONG_bi_doc_thanh_cong_thuc` phủ sáu câu tiền, và
`test_cong_thuc_that_VAN_doi_duoc` phủ chiều ngược. Nên đây không phải chuyện thiếu ý tưởng về
cách kiểm — là chuyện **tôi không mang bộ kiểm đã có sang bên kia**.

### Ràng hai bên bằng một tập mẫu dùng chung

`tests/du-lieu-chung/cong-thuc-giua-dong.json` — 8 ca là công thức, 9 ca là tiền, mỗi ca kèm
lý do. **Cả hai bộ kiểm đọc chính tệp ấy**: pytest qua
`la_cong_thuc_chu_khong_phai_tien()` mới tách ra ở `xuat_ban.py`, và XCTest qua
`MathText.laCongThucChuKhongPhaiTien`. Hai vị từ cùng hình dạng nên so được trực tiếp.

Và tôi kiểm rằng ràng buộc có thật: **đổi tên tệp đi thì phía Swift đỏ**. Một ca đọc tệp mà
không đỏ khi mất tệp thì nó chỉ giả vờ đọc.

Thêm `test_tap_mau_dung_chung_co_doc_duoc_tu_phia_Swift` phía Python — nó canh rằng bộ kiểm
Swift còn tham chiếu tới đúng tệp ấy. Đổi tên mà quên một bên thì bên ấy bỏ qua tập mẫu trong
im lặng và vẫn xanh.

> Hai bộ kiểm cùng xanh chưa nói hai bên làm cùng một việc, nếu chúng kiểm hai tập mẫu khác
> nhau.

Bộ kiểm: Python 1573 → **1575**, Swift 31 → **36**.

## [DEV-329] Câu của NGƯỜI cũng phải qua bộ dựng Markdown

*02/10/2026. `ui/EIDEApp/Sources/EIDE/Views/ConsoleView.swift`.*

Anh Công báo lần thứ hai rằng dấu `**` còn nguyên trên màn hình, và lần này chỉ đúng câu mình
vừa gõ cho tác tử:

> Bản kết quả phải trả lời `**bốn câu**`, mỗi câu kèm con số lấy từ CSV

Chỗ hỏng là một câu `if` trong thân `DongTranscript`, kèm lý do viết hẳn ra:

```swift
// Câu của người là chữ trơn (họ gõ gì hiện nấy); lời tác tử qua bộ dựng markdown
if nhan == "BẠN" { Text(tach.1) } else { MarkdownView(text: tach.1) }
```

Lý do ấy **đúng nếu người gõ văn trơn**. Nhưng trong đề án này lời giao việc *là* markdown —
bảng so sánh, chữ đậm, khối mã, công thức. Nay cả hai vai đi qua cùng một bộ dựng.

Cái giá, nói ra chứ không giấu: một biểu thức hay đường dẫn người gõ có thể bị hiểu thành dấu
nhấn. Ba thứ đỡ, và cả ba đều có ca kiểm — luật *flanking* của CommonMark giữ `a * b * c`
nguyên vẹn; dấu `_` giữa từ không mở dấu nhấn nên `ten_bien_x` giữ nguyên; và N6: bộ dựng
không bao giờ nuốt nội dung. Mất nhiều nhất là một đoạn in nghiêng ngoài ý muốn.

### Lần thứ ba trong một ngày tôi viết bộ ca kiểm xanh cả khi đường dẫn đứt

Ba ca đầu tôi viết cho chỗ này thử `Markdown.chuThuan` — và chúng **vẫn xanh với mã cũ**, vì
`chuThuan` chưa bao giờ hỏng. Thứ hỏng là chỗ **chọn** bộ dựng.

Hai lần trước cùng hình dạng: khối A8.0 và khối A5.10, cả hai bộ ca kiểm đều xanh khi tôi bỏ
hẳn khối ra khỏi tab. Ba lần trong một ngày thì không còn là tai nạn — nó là một thói:

> Tôi kiểm **thứ làm việc**, rồi kết luận cho **việc đã được làm**. Hai điều ấy cách nhau một
> đường dẫn, và đường dẫn là chỗ hay đứt nhất.

`View` của SwiftUI không gọi được từ ca kiểm, nên `ChonBoDungTests` đọc chính **mã nguồn** của
`ConsoleView.swift` và khẳng định thân `DongTranscript` không còn nhánh rẽ theo vai. Cách ấy
thô, nhưng nó bắt được đúng cái đã hỏng — tôi phá lại và nó đỏ. Một ca thô mà bắt được thì hơn
một ca đẹp mà không.

Bộ kiểm Swift: 36 → **40**.

---

## [DEV-330] [M1-01] Toàn vẹn cặp `function_call` ↔ `function_response` — và 105 phiên thật đã hỏng

Nhiệm vụ #1 của `toi-uu/KE-HOACH-SUA-VA-KIEM-THU.md` (giai đoạn 1). **Sửa lỗi thuần**, không
có cờ tính năng: ba đường trong lõi để lại một lịch sử mà Gemini đọc không khớp, và một lịch
sử không khớp thì mô hình tự dựng ra phần còn thiếu.

**Ba chỗ đã sửa** (`src/eide/loop.py`):

1. `_tool_loop` — cổng bật ở lời gọi thứ k thì vòng lặp `return` ngay, k+1..n **không có
   message `role=tool` nào**. Nay mỗi lời gọi còn lại nhận một kết quả `E4031` "chưa chạy, vì
   lời gọi trước đang chờ người duyệt cổng" (`_chua_chay_vi_cho_cong`).
2. `_one_tool` — lời nhắc "`ok` mà kết quả rỗng" được append **trước** kết quả của chính lời
   gọi ấy, cắt đôi cặp gọi ↔ trả. Nay nó xếp vào `ctx._nhac_sau_batch` và chỉ vào lịch sử sau
   khi mọi kết quả của batch đã vào (`_xa_nhac_sau_batch`, gọi ở **cả hai** lối ra của vòng).
   Nội dung lời nhắc không đổi một chữ — chỉ đổi chỗ đặt.
3. `_resolve_gate` — append một message `role=tool` **thứ hai** cho cùng `tool_call_id`, trong
   khi kết quả `E4003` (`gate_pending`) đã nằm sẵn trong lịch sử. Nay tìm kết quả cũ và thay
   tại chỗ (thêm khoá `_da_duyet_sau: <gate_id>`), rồi `transcript.thay_toan_bo` — vì
   `DanhSachGhiDia` chỉ ghi xuống đĩa lúc `append`, nó không thấy một phép sửa ô.

**Một chỗ nữa** (`src/eide/llm/gemini.py`): `_to_contents` sinh **một `Content` riêng cho mỗi**
kết quả, và `Part.from_function_response` không mang `id`. Nay `_gom_ket_qua` dời message chen
giữa xuống sau nhóm kết quả, và nhóm kết quả liền nhau thành **một** `Content` chứa N
`FunctionResponse(id=…)`. `id` chỉ được gửi khi lượt mô hình tương ứng cũng đã gửi `id` ở
`function_call` — gửi một id không khớp lời gọi nào còn tệ hơn không gửi id. Chỉ đụng danh sách
lúc dựng request; transcript trên đĩa không đổi dạng.

### Số đo

| | Trước | Sau |
|---|---|---|
| `pytest -q` | 1610 xanh · 0 đỏ | **1615 xanh · 0 đỏ** (+5 ca mới) |
| `tools/kiem_tai_lieu.py` | 0 lệch chắc chắn | 0 lệch chắc chắn |
| `kiem_tra_day_du --nhanh` | 20/21 | không chạm |
| `swift test` | 0 ca / 0 suite | không chạm |

"Phá lại thì đỏ": làm riêng cho **cả bốn** chỗ sửa, mỗi chỗ hoàn nguyên một mình → đúng ca của
nó đỏ, trả lại → xanh. Ca âm TC-M1-01-05 (lịch sử vốn đã chuẩn) vẫn xanh cả trên bản hỏng —
đó là việc của nó.

### Lỗi này không phải lý thuyết: 105 trong 309 phiên thật

`kiem_cap_goi_tra(messages)` là hàm thuần, soát được cả transcript đã lưu. Chạy trên toàn bộ
`du-lieu/` (783 tệp `.jsonl`, 309 tệp có lượt gọi công cụ):

```
  sạch: 204   có chỗ sai: 105        → 255 chỗ sai
    156 chỗ ·  99 phiên   kết quả THỨ HAI cho cùng id
     74 chỗ ·  47 phiên   message chen giữa gọi ↔ trả
     24 chỗ ·   5 phiên   kết quả nằm trong lượt không gọi nó
      1 chỗ ·   1 phiên   lời gọi KHÔNG có kết quả nào
```

Loại thứ ba nghe như một lỗi khác, nhưng mở ra thì vẫn là chỗ số 3: ở
`du-lieu/riscv-tn20k/.eide/sessions/ses-0004`, lời gọi `call_58993` (`tool.install`) nhận kết
quả `E4003` ở dòng 51, rồi **kết quả thứ hai** ở dòng 65 — cách 14 message, nên nó rơi vào cửa
sổ của một lượt mô hình khác. Cùng một nguyên nhân, chỉ khác chỗ cái đuôi rơi xuống.

Một phần ba số phiên có công cụ mang một lịch sử tự mâu thuẫn. Đây là nền của những lượt
"tác tử kể sai chuyện đã xảy ra" mà DEV-323 ghi mà chưa truy được tới gốc.

### Một ca cũ chuyển đỏ, và vì sao tôi sửa ca chứ không sửa mã

`test_lõi_phat_NHIP_sau_moi_loi_goi_cong_cu` đỏ. Nó **đọc chữ trong mã nguồn**: nó neo vào
đúng dòng `for call in rsp.tool_calls:`, mà tôi đổi thành `for k, call in enumerate(...)` để có
chỉ số k. Hành vi nó đo — `_nhip` nằm ngay sau `_one_tool` trong thân vòng lặp — không hề đổi.
Nên tôi nới cái neo cho nhận cả hai cách viết (§3.2: test cũ khoá một chi tiết không phải thứ
nó đo).

Nhưng mốc thứ hai của ca ấy — *"thân vòng lặp dưới 12 dòng, không phải nửa tệp"* — thì tôi
**không** nới, dù nó cũng đỏ (16 dòng). Mốc ấy đang làm đúng việc: nó chống chính cái vô nghĩa
mà bản đầu của ca mắc phải. Nới nó lên 20 là lấy thước đo của mã đi đo mã. Thay vào đó tôi
tách phần E4031 ra `_chua_chay_vi_cho_cong` — thân vòng lặp còn 6 dòng, và chỗ cần giải thích
dài thì nằm trong docstring của hàm riêng, nơi nó thuộc về.

**Ngoài "Tệp chạm tới"** của nhiệm vụ: `tests/test_thanh_trang_thai_va_doi_du_an.py` (một cái
neo, lý do ở trên). Ghi ra theo N-6.

### Còn nợ

Lời nhắc "ĐÃ DUYỆT" có một câu nói *"kết quả của nó là tin nhắn ngay sau đây"*. Sau khi kết quả
được thay tại chỗ, nó không còn ở sau nữa — nó ở **trên**. Tôi đổi đúng câu ấy thành "đã thay
chỗ lời từ chối cũ, ở ngay trên"; bốn câu mà `test_duyet_cong_chan_loi_goi_thi_PHAI_noi_ra`
kiểm chữ thì giữ nguyên từng chữ. Nhiệm vụ ghi "không đổi nội dung lời nhắc hiện có" — để
nguyên thì lời nhắc chỉ sai chỗ một tin nhắn, và đó đúng là loại khoảng trống đã tốn hai lượt
ngày 02/10/2026.

`kiem_cap_goi_tra` **chưa** được gắn vào hook hay cổng nào — nó là thước đo, chưa là hàng rào.
Gắn nó thành một phép soát tự động là việc của một nhiệm vụ sau.

---

## [DEV-331] [M1-02] Lược đồ công cụ: 25 869 token mỗi lời gọi, và một cái trần chưa ai đọc

Nhiệm vụ #2 của kế hoạch tối ưu. Hai nửa tách rời: **phần đo** chạy luôn, **phần gọn** nằm
sau cờ `EIDE_FEATURE_GON_CONG_CU`, mặc định TẮT (N-4 — nó đổi danh sách công cụ mô hình nhìn
thấy, tức là đổi hành vi tác tử).

### Cái trần không có thước

`ContextBudget.tool_schema = 4000` nằm trong `config.py` từ đầu. `grep` ra đúng **hai** chỗ:
dòng khai báo, và một ca kiểm cộng tổng các trần lại. **Không dòng mã nào đọc nó.** Nên suốt
thời gian qua không ai biết lược đồ thật là bao nhiêu — và nó là **25 869 token, gửi lại mỗi
lời gọi mô hình**, vượt trần hơn sáu lần.

Đây đúng hình dạng bài học "cơ chế có sẵn, đường dẫn tới nó đứt" — cái trần tồn tại, chỉ là
chưa ai nối dây tới nó.

Nay: `Registry.token_luoc_do()` là thước; `llm_call` trong sổ cái mang thêm
`tool_schema_tokens` và `cong_cu_hien`; vượt trần thì ghi `note` **và không chặn** (một lượt
bị chặn vì lược đồ dài là một lượt người dùng mất, một dòng sổ thì không mất gì).

### Số đo

| | Cờ TẮT | Cờ BẬT |
|---|---|---|
| công cụ hiển thị | 73 | **18** |
| ký tự lược đồ | 77 607 | 13 425 |
| token lược đồ | **25 869** | **4 475** |

Giảm **82,7 %**, và 4 475 ≤ trần 6 000 của nhiệm vụ. Bộ kiểm: 1615 → **1623 xanh, 0 đỏ**
(+8 ca). "Phá lại thì đỏ" làm riêng cho **cả bảy** chỗ sửa.

### Chỗ kế hoạch nói chưa đúng, đã đo lại

Kế hoạch ghi: *"phần dài KHÔNG nằm ở `summary_vi` mà ở mô tả TRONG `params`"*, và đề nghị cắt
mỗi mô tả tham số còn ≤ 160 ký tự. Nửa đầu đúng — `params` chiếm **76 %** số ký tự lược đồ.
Nhưng cách sửa thì gần như không ăn gì:

```
388 mô tả tham số · dài nhất 475 · TRUNG VỊ 37 ký tự · chỉ 2 cái vượt 160
luật cắt 160 ký tự thu về:  356 / 77 461 ký tự  =  0,46 %
```

Và cả hai cái vượt 160 (`fact.compare` 475, `target.flash` 201) đều **không** thuộc `CORE_GON`,
nên trong lược đồ lúc cờ bật, luật ấy nổ **0 lần**. Toàn bộ 82,7 % tới từ việc thu tập công cụ,
không từ việc cắt mô tả.

Tôi vẫn hiện thực luật cắt đúng như kế hoạch ghi: nó rẻ, nó làm trên **bản sao** nên
`spec.params` giữ nguyên cho `tool.search` và lỗi tham số đọc, và nó chặn trước ngày ai đó
viết một mô tả 2 000 ký tự. Nhưng đừng tính nó vào phần tiết kiệm. Phần dài thật nằm ở **số
lượng** trường và các `enum` trong `params`, không ở độ dài từng mô tả — muốn ăn tiếp vào 76 %
ấy thì phải sửa chính lược đồ của từng công cụ, và đó là một nhiệm vụ khác.

### LRU cho `_unlocked`

`_unlocked` trước đây chỉ được `add`, **không bao giờ gỡ** — một phiên dài mở khoá dần mấy
chục công cụ, lược đồ phình lên đúng lúc cửa sổ ngữ cảnh đã chật nhất. Nay (chỉ khi cờ bật):
công cụ không được gọi trong `TRAN_LRU_LUOT = 3` lượt thì rời lược đồ, và tên bị gỡ được ghi
`note` vào sổ.

Hai chỗ phải cẩn thận, cả hai đều có ca kiểm riêng:

* **Kế hoạch được ghim.** Bước kế hoạch chưa xong mà nêu `cong_cu` nào thì công cụ ấy không bị
  gỡ, dù chưa gọi lần nào. LRU chỉ biết việc ĐÃ làm; kế hoạch là lời hứa về việc SẮP làm, và
  gỡ đúng công cụ của bước kế tiếp là bắt tác tử đi tìm lại nó.
* **`attend` và `set` không tính là một lượt.** Chuyển tab là sự chú ý, không phải yêu cầu
  (DEV-226 đã học một lần với chuyện bảy cú bấm thành bảy lượt gọi mô hình). Đếm chúng thì bảy
  cú bấm chuyển tab làm tác tử mất công cụ nó đang dùng dở.

`tool.search` nằm trong `CORE_GON`. Thiếu nó thì tập gọn thành một cái lồng: tác tử không thấy
công cụ nào khác, và cũng không có đường nào đi tìm.

### Một ca cũ chuyển đỏ

`test_sch0.py::test_mac_dinh_moi_co_deu_TAT` chốt cứng `to_dict() == {"schematic": False}`,
nên **mỗi cờ mới làm nó đỏ** — kể cả một cờ mặc định TẮT đúng như nó đòi. Một ca kiểm phải đỏ
khi ai đó làm **sai**, không phải khi ai đó làm **thêm**. Nay nó đo đúng điều nó nói: mọi giá
trị trong `to_dict()` đều `False`, cộng một dòng khẳng định hai tên cờ có mặt. Tôi phá lại:
cho `gon_cong_cu` mặc định `True` → ca ấy đỏ. Ngoài "Tệp chạm tới", ghi theo N-6.

### Chưa làm, và vì sao

Cờ **vẫn TẮT**. Cổng 4.3 đòi bốn điều trước khi đổi mặc định, và ba trong bốn chưa có: bộ eval
phát lại (M4-21) chưa làm, bộ 76 ca với cờ BẬT chưa chạy (tốn tiền mô hình — §3.0 nói phải hỏi
người dùng trước), và chỉ số chi phí (M1-20) chưa có. Con số 82,7 % là **token tiết kiệm**, nó
không nói gì về việc tác tử làm việc tốt hơn hay tệ hơn khi chỉ còn 18 công cụ trong tầm mắt —
thứ đó chỉ đo được bằng eval, và đó chính là lý do nó nằm sau một cờ.

---

## [DEV-332] [M1-03] Tác tử con đi vòng cả ba lớp — 1 822 lời gọi, không lần nào qua policy

Nhiệm vụ #3. **Sửa lỗi thuần** (đi vòng hàng rào), không cờ: N-5 nói lỗi thì phải hết, không
để tuỳ chọn.

### Lỗ hổng

`subagent.chay` gọi thẳng `registry.run(call.tool, call.args, ctx)`. Không
`_khoa_khi_soan_ke_hoach`, không `hooks.pre_tool_use`, không `policy.decide`, không
`hooks.post_tool_use`. Trong khi `SUBAGENT["firmware"].cong_cu` có `fs.write`, `fs.edit`,
`build.compile`, và `"sim-runner"` có `fs.write`.

Nghĩa là: `POL-N1-constant-guard` chặn tác tử CHÍNH ghi `#define BAUD 115200` khi không có
nguồn — nhưng tác tử chính chỉ cần bảo `firmware` ghi hộ. Cùng cách ấy đi vòng được khoá plan
mode (§B5): đang soạn kế hoạch, công cụ ghi khoá, gọi `task.run` là xong.

**Một hàng rào đi vòng được bằng một lớp gián tiếp thì không phải hàng rào.**

### Đã xảy ra chưa? Có, 1 822 lần — nhưng chưa ai mất gì

Soát 68 sổ cái trong `du-lieu/`:

```
1 822 lời gọi công cụ của tác tử con, trong 26 phiên — 0 lần qua policy.decide
công cụ đã gọi: fs.read 599 · ledger.query 311 · store.get 263 · fs.glob 192 ·
                fs.grep 186 · store.list 127 · history.diff 105 · fact.query 32 ·
                env.check 2 · build.compile 1 · fs.stat 1 · blob.read 1
```

Toàn bộ là công cụ ĐỌC, trừ đúng một lời gọi `build.compile`. Nên lỗ hổng này chưa làm hỏng
gì — không phải vì nó được canh, mà vì các tác tử con tình cờ chưa dùng tới `fs.write`. Một lỗ
hổng chưa bị bước vào vẫn là một lỗ hổng, và đây là loại chỉ lộ ra đúng lúc nó đắt nhất.

### Đã sửa

Tách phần kiểm của `_one_tool` thành `Agent.kiem_va_chay(call, ctx, *, che_do)` — **một** bản
logic cho cả hai loại tác tử, thứ tự ba lớp giữ nguyên. `_one_tool` nay gọi chính nó, nên
không có hai bản song song để một bản thiếu luật mới.

`che_do="con"` khác đúng một chỗ: gặp `policy.action == "ask"` thì **không dựng thẻ**, trả
`E4032`. Thẻ cổng là câu hỏi cho người đang theo dõi một lượt việc; tác tử con chạy trong ngữ
cảnh sạch, người dùng không thấy nó và không biết nó đang làm gì — một thẻ do nó dựng là câu
hỏi không có chỗ đứng. Nó phải ghi vào `chua_lam` rồi nộp báo cáo.

Lối rơi về `registry.run` còn đó cho `ctx` không mang tác tử (ca kiểm cũ dựng ctx giả), nhưng
nó **ghi `khong_qua_hang_rao: True` vào sổ** chứ không lặng lẽ chạy — và có một ca kiểm khẳng
định khoá ấy không bao giờ xuất hiện trên đường chạy thật.

### Số đo

Bộ kiểm 1623 → **1628 xanh, 0 đỏ** (+5 ca). "Phá lại thì đỏ" cho cả hai chỗ sửa: bỏ nhánh qua
hàng rào → 3 ca đỏ, ca âm vẫn xanh; bỏ nhánh E4032 → ca thẻ cổng đỏ.

Không ca cũ nào phải sửa lần này — `test_subagent_KHONG_dung_duoc_cong_cu_ngoai_tap_cua_no`
vẫn trả `E5006` trước mọi hook, đúng như "Bảo vệ hồi quy" đòi.

---

## [DEV-333] [M2-01] Đường truy vết khai báo có mã, có ca kiểm, và chưa từng chạy một lần

Nhiệm vụ #4. Phần nền là **sửa lỗi thuần**; phần mở trường mới trên lược đồ nằm sau cờ
`EIDE_FEATURE_TRUY_VET`, mặc định TẮT.

### Lỗ hổng: ba chỗ, mỗi chỗ đứt một kiểu

`deps.ha_nguon_cua` vốn có hai đường và cộng lại: **theo khai báo** (`deps.upstream`) và
**theo loại** (chuỗi mặc định §E5.4). Đường khai báo chính xác hơn hẳn — nó nói *hiện vật
này* dựng từ *cái kia*, chứ không phải *loại này* thường dựng từ *loại kia*. Nhưng:

1. `History.ghi_kho` và `History.ghi_tep` **không có tham số `deps`**, nên `store.apply` luôn
   nhận `None`. Grep `deps=` trong `src/eide`: không một lời gọi nào ngoài chính `db.py`.
2. `Store.apply` ghi `deps=excluded.deps` trong câu upsert, nên kể cả có ghi được thì **lần
   sửa thứ hai sẽ xoá sạch**. Đường khai báo sống được đúng một version.
3. Cộng hai đường lại nghĩa là khai báo **không bao giờ thu hẹp** được gì: một tiêu chí khai
   `do_req: FR-01` vẫn lỗi thời khi người ta sửa FR-02, vì đường theo loại vẫn quét nó.

Cả ba cộng lại: `upstream` **luôn rỗng**, và đường khai báo chưa chạy lần nào kể từ khi được
viết ra. Lại đúng hình dạng "cơ chế có sẵn, đường dẫn tới nó đứt" — lần thứ tư trong bốn
nhiệm vụ của đợt này.

### Số đo

Kịch bản 3 REQ, mỗi REQ một phương án + một tiêu chí + một tệp mã, rồi sửa **một** REQ:

```
KHÔNG khai gì (như trước M2-01)  →  9 hiện vật STALE   (tất cả)
khai đúng nguồn                  →  3 hiện vật STALE   (PA-1 · criteria:sim-1 · mod1.c)
```

Một băng cảnh báo lúc nào cũng sáng là một băng cảnh báo không ai đọc — đó mới là cái giá
thật của con số 9, chứ không phải chín dòng thừa.

Bộ kiểm 1628 → **1637 xanh, 0 đỏ** (+9 ca). "Phá lại thì đỏ" riêng cho **cả sáu** chỗ sửa.
Không ca cũ nào phải sửa; CX06 vẫn ra STALE đúng danh sách.

### Hai chỗ phải cẩn thận

**Khai báo chỉ thắng ĐÚNG LOẠI nó khai.** Một phương án khai nguồn là REQ thì nó tự quyết lấy
chuyện "REQ nào làm tôi lỗi thời", nhưng nó **vẫn** phải lỗi thời khi ADR đổi — chuyện ấy nó
chưa nói gì. Không có ràng buộc này thì khai một dòng `upstream` là vô tình tự miễn trừ khỏi
mọi đường phụ thuộc khác.

**Hiện vật không khai gì vẫn lan theo loại y như cũ.** Phần lớn kho hiện nay không khai gì, và
một ca âm riêng (`test_tep_ma_khong_khai_REQ_van_stale_theo_loai`) canh đúng điều đó — nó vẫn
xanh cả trên bản bị phá, như một ca âm phải thế.

### Một phép đo hỏng, bắt được vì con số trông lạ

Lần đo đầu ra **6 → 2**, và ba tệp `.c` không xuất hiện ở *cả hai* cột. Nếu chỉ nhìn tỉ lệ thì
6→2 cũng "đẹp" như 9→3 và dễ ghi thẳng vào nhật ký. Nguyên nhân: kịch bản đo tạo tệp trên đĩa
bằng `write_text` **trước** khi gọi `fs.write`, nên `fs.write` chặn đúng luật E4020 *"chưa đọc
thì chưa đè"* — không tệp nào vào kho. Phép đo đã bị chính hàng rào của sản phẩm chặn, và nó
trả về một con số hợp lý thay vì nổ.

Nay kịch bản có `assert` rằng `fs.write` trả ok và tệp có mặt trong kho trước khi đọc kết quả.
Một phép đo không tự kiểm tiền đề của nó thì chỉ nói được rằng *nó đã chạy*, không nói được
rằng *nó đã đo*.

### Chưa làm

`ma_tran_truy_vet(store)` đã có và đã được kiểm, nhưng **chưa ai hiện nó lên tab A2** — đó là
M2-02, nhiệm vụ kế tiếp và phụ thuộc đúng hàm này. Ma trận chỉ gom năm cột (option · adr ·
code · criteria · ket_qua); loại hiện vật khác không lên bảng, vì một cột "khác" gộp mọi thứ
lại thì không trả lời được câu hỏi nào.

Cờ `truy_vet` vẫn TẮT: nó thêm một trường vào lược đồ của `fs.write` và `fs.edit` — hai công
cụ dùng nhiều nhất — nên đó là đổi thứ mô hình nhìn thấy mỗi lượt. Phần nền (ghi và đọc
`deps.upstream`, ma trận, `option_create`, `sim.criteria` tự khai nguồn) chạy **cả khi cờ tắt**.

---

## [DEV-334] [M2-02] Ma trận truy vết lên tab A2, và một con số 5/37 phải đọc cho đúng

Nhiệm vụ #5, dựng trên `deps.ma_tran_truy_vet` của M2-01. Khối giao diện là **trình bày
thuần** (không cờ); hook Stop nằm sau cờ `EIDE_FEATURE_REQ_PHU`, mặc định TẮT.

### Khối A2.2, không phải A2.5

Kế hoạch nhiệm vụ ghi *"thêm khối `block(\"A2.5\", ...)`"*. **A2.5 đã có chủ** từ trước: đó là
khối "Kế hoạch chia việc" (`surfaces.py:_khoi_ke_hoach`, còn sinh cả `A2.5.1`, `A2.5.2`… cho
các bản kế hoạch cũ). Phần "Hiện trạng" của nhiệm vụ không thấy chỗ này.

Ca âm `test_khong_co_REQ_thi_khong_co_A2_5` bắt được ngay: nó **đỏ trên mã cũ** vì A2.5 đã tồn
tại — một ca âm lẽ ra phải xanh trước khi sửa. Đó là tín hiệu, không phải nhiễu.

Dùng **A2.2**: trống trong cả mã lẫn 18 tệp tài liệu, và nằm đúng chỗ — ngay sau bảng REQ, vì
đây là cái nhìn **theo yêu cầu** chứ không theo hiện vật. Ba bảng cũ của tab A2 (REQ, phương
án, ADR) đều nhìn theo hiện vật, nên câu hỏi *"yêu cầu nào chưa ai làm"* chỉ trả lời được bằng
cách đối chiếu ba bảng bằng mắt — và một câu hỏi phải đối chiếu bằng mắt là câu hỏi không ai hỏi.

Bốn tình trạng, **bốn chữ khác nhau** cho chặng đầu tiên còn thiếu: `chưa thiết kế` →
`chưa hiện thực` → `chưa kiểm` → `đủ`. Có một ca kiểm riêng khẳng định bốn chữ ấy khác nhau
từng đôi một; gộp chúng thành "chưa xong" thì người đọc vẫn phải tự đi tìm thiếu ở đâu.

Kiểu khối là `table` — Swift đã dựng được từ trước, nên **không sửa gì ở `ui/`**. `swift test`
vẫn 43 ca, 0 đỏ. Tôi thêm `"table"` vào `test_giao_dien_biet_ve_kieu_khoi_moi` theo đúng
"Tiêu chí xong", để kiểu khối của A2.2 cũng được canh bằng số.

### Con số trên kho thật, và cách đọc nó cho đúng

Chạy ma trận trên **63 kho `store.sqlite`** của các dự án đã làm:

```
37 REQ trong 22 kho có yêu cầu
  5/37 REQ có ít nhất một phép đo
  tình trạng: chưa thiết kế 27 · chưa hiện thực 10 · chưa kiểm 0 · đủ 0
```

**Con số này KHÔNG phải một lời phán về chất lượng sản phẩm, và tôi không ghi nó như thế.**
Bảng đọc theo **lời khai**: `option.dap_ung_req`, `criteria.assert[*].do_req`, và
`deps.upstream`. Cột "Mã nguồn" dựa vào `hien_thuc_req` — trường vừa mới tồn tại ở M2-01 (và
còn sau cờ TẮT), nên **chưa một tệp nào trên đĩa từng khai nó**. Vì vậy cột ấy trống ở mọi dự
án, và 10 REQ mang chữ "chưa hiện thực" thật ra nghĩa là *"không tệp nào KHAI rằng nó làm yêu
cầu này"* — chứ không phải *"chưa ai viết mã"*. Robot hai bánh có mã chạy được trên bo thật và
vẫn nằm trong 10 ấy.

Hai câu đó khác nhau, và gộp chúng lại đúng là cách một bảng bắt đầu nói quá. Nên `summary`
của khối nói thẳng nó đọc gì: *"đọc theo lời khai: dap_ung_req · hien_thuc_req · do_req"*.

Phần đọc được NGAY từ con số này: `chưa kiểm 0` và `đủ 0` — tức **không REQ nào** đi hết chuỗi,
và 27 REQ chưa có một phương án nào nhận. Hai điều đó dựa trên dữ liệu đã có từ lâu
(`dap_ung_req` tồn tại từ trước M2-01), nên chúng là phép đo thật.

### Hook `req_chua_phu`

Nó hỏi một câu **khác** `kiem_viec_chua_ai_kiem`: không phải *"việc đã ghi có ai kiểm chưa"*
mà *"yêu cầu nào chưa ai đo tới"*. Verifier không trả lời được câu sau — nó có
`doc_duoc_viec=False`, cố ý không biết đề bài, nên không đếm được phủ yêu cầu.

Bốn cửa im lặng, mỗi cửa một lý do, và mỗi cửa một ca kiểm: cờ TẮT · lượt chưa ghi gì · đang
giữa một kế hoạch đã duyệt (cùng lý lẽ với hook trên: kế hoạch bảy bước mà mỗi bước bị nhắc
một vòng thì thành mười bốn lượt) · đã nhắc trong lượt này rồi.

Lời nhắc cho **hai** lối và nói rõ lối thứ hai là hợp lệ: viết phép đo, hoặc nói thẳng REQ ấy
ngoài phạm vi lượt này. Thiếu cửa thoát thì lời nhắc thành áp lực đẻ ra tiêu chí cho có — và
một tiêu chí không đo gì làm hỏng đúng cái bảng nó vừa làm sáng.

### Số đo

Bộ kiểm 1637 → **1646 xanh, 0 đỏ** (+9 ca). `swift test` 43 ca, 0 đỏ, không đổi.
"Phá lại thì đỏ" riêng cho **cả sáu** chỗ sửa. Không ca cũ nào phải sửa.

### Chưa làm

Cờ `req_phu` vẫn TẮT: "Tiêu chí xong" đòi chạy lại bộ 76 ca với cờ bật để so pass-rate, và bộ
ấy tốn tiền mô hình nên §3.0 bắt hỏi người dùng trước. Lời nhắc này chèn chữ vào transcript
mỗi lượt có ghi, nên nó đổi hành vi theo cách chỉ eval đo được.

---

## [DEV-335] [M2-03] Chất lượng yêu cầu đo bằng mã — và hai lần bộ kiểm của tôi không canh gì

Nhiệm vụ #6. `src/eide/yeu_cau.py` là module **thuần, luôn có**; phần nối vào kết quả công cụ
nằm sau cờ `EIDE_FEATURE_REQ_CHAT_LUONG`, mặc định TẮT.

Ba phép đo, cả ba 0 token: `kiem_tieu_chi` (có số kèm đơn vị hoặc phép so không),
`tu_mo_ho` (10 từ mà hai người đọc ra hai nghĩa), `trung_lap` (Jaccard theo từ ≥ 0,6).
**Không chặn ghi** — chặn một yêu cầu vì nó mơ hồ là lấy mất quyền của người đang còn mơ hồ
về chính việc họ muốn. Nó nói ra, rồi chỉ đường `ask_user`.

### Lỗi trong `_go_dau` của design.py, chưa sửa

`tools/design.py:359` viết `.replace("d", "d")` — một phép thay **vô nghĩa**, gần như chắc là
gõ nhầm từ `.replace("đ", "d")`. Hệ quả đo được:

```
_go_dau("ổn định") → "on đinh"
_go_dau("ON DINH") → "on dinh"      ← hai câu này KHÔNG khớp nhau
```

Hàm ấy đang được `_kiem_nguoi_that_su_chon` dùng để đối chiếu câu trích với sổ cái — tức một
phép kiểm an toàn ("người có thật sự chọn không"). Tôi **không sửa** nó: `design.py` ngoài
"Tệp chạm tới", và đổi cách so khớp của một phép kiểm an toàn là việc cần ca kiểm riêng chứ
không nên kèm vào đây. `yeu_cau.go_dau` làm đúng, và docstring của nó chỉ thẳng sang chỗ sai
kia để lần sau ai đọc cũng thấy.

### Hai lần "phá lại thì đỏ" KHÔNG đỏ — và lý do của từng lần khác nhau

Đây là phần đáng ghi nhất của nhiệm vụ này.

**Lần một — ca kiểm dựng trên một điều tôi tự nhớ sai.** Tôi viết ca
`test_tu_mo_ho_khong_bat_trong_long_tu_khac` với lý lẽ *"thiết" chứa "it" sau khi bỏ dấu, nên
so theo chuỗi con sẽ kêu oan*. Đổi hàm sang so chuỗi con → ca vẫn **xanh**. Vì `go_dau("thiết")`
ra `"thiet"`, và `"thiet"` **không chứa** `"it"` (t-h-i-e-t). Tôi chưa mở ra đo, chỉ nhớ.

Chỗ va thật thì nhiều và dễ: `bit`, `unit`, `init`, `exit` — đều chứa `"it"`, đều là từ thường
gặp nhất trong một yêu cầu phần mềm nhúng. Đo lại: cả bốn câu đều bị phép so chuỗi con kêu là
có từ "ít". Ca kiểm nay dùng bốn câu ấy, và nó đỏ đúng khi đổi sang chuỗi con.

**Lần hai — `__pycache__` cũ, và nó chỉ xảy ra vì phép phá dài đúng bằng mã gốc.** Phép phá
đổi `_NGUONG_TRUNG = 0.6` thành `= 0.0`: **cùng số byte**, và xảy ra trong cùng một giây với
lệnh `cp` trả lại mã. Python xác thực `.pyc` bằng (mtime giây, kích thước nguồn) — cả hai
khớp, nên nó dùng lại bản biên dịch của **mã đã bị phá** sau khi mã đã được trả lại.

Tôi phát hiện vì một con số trông lạ: `grep` nói ngưỡng là 0,6, mà hàm xử sự như 0,0. Nếu
không dừng lại ở chỗ ấy thì tôi đã ghi vào nhật ký rằng ca kiểm "không canh ngưỡng", trong khi
thật ra **phép đo đang chạy mã khác với mã trong tệp**.

Từ đây mọi phép "phá lại thì đỏ" đều xoá `__pycache__` trước khi chạy. Tôi đã soát lại năm
nhiệm vụ trước: chỉ phép phá này có độ dài trùng khít, các phép khác đều đổi kích thước tệp
nên `.pyc` tự mất hiệu lực.

Ca `test_trung_lap` nay cũng ghim thật cái ngưỡng: *"Nhận tệp ảnh qua USB"* so với *"Nhận tệp
phim qua LAN"* giống nhau **3/7 từ = 0,429** — cùng dạng câu, khác hẳn việc, nên KHÔNG phải
trùng lặp. Hạ ngưỡng xuống 0,4 là ca ấy đỏ.

### Đo trên 37 REQ thật, và một ca kêu oan đã vá

Chạy bộ dò trên REQ của 63 kho `store.sqlite`:

```
37 REQ · 25 sạch (67%) · tieu_chi 11 · tu_mo_ho 2
```

Lần chạy đầu ra `tu_mo_ho 3`, và một trong ba là **kêu oan**: FR-01 của dự án RISC-V,
*"SoC mô phỏng thành công và in đúng chuỗi ra UART **ít nhất 2 lần**"*. "ít nhất 2 lần" là một
mức ĐO ĐƯỢC; "ít" ở đây là lượng từ, không phải tính từ. Đã vá: lượng từ đứng ngay trước một
con số (cho phép một từ đệm như "nhất" chen giữa) thì không kêu. `"Dùng ít RAM"` vẫn bị bắt.

11 cảnh báo `tieu_chi` thì là tín hiệu thật: những REQ ấy có trường `criteria` để trống hoặc
không có con số nào kèm đơn vị.

### Số đo

Bộ kiểm 1646 → **1657 xanh, 0 đỏ** (+11 ca). "Phá lại thì đỏ" cho **cả bảy** chỗ sửa, chạy lại
toàn bộ sau khi xoá `__pycache__`. Không ca cũ nào phải sửa; thông điệp luật N7 không đổi.

### Chưa làm

Subagent `req-critic` (bước 4, đánh dấu "tuỳ chọn, gộp M2-13") **chưa làm** — nó cần khung
subagent của M2-13. Cờ `req_chat_luong` vẫn TẮT: "Tiêu chí xong" đòi chạy TC004/TC005 với cờ
bật để xem số câu hỏi làm rõ có tăng, và bộ ấy tốn tiền mô hình.

---

## [DEV-336] [M2-06] Bước kế hoạch phải khai kiểm bằng gì, và `step_done` đối chiếu sổ cái

Nhiệm vụ #7. Sau cờ `EIDE_FEATURE_KE_HOACH_CONG_KIEM`, mặc định TẮT. Mã lỗi mới: **E6012**.

### Chỗ hở

`plan.step_done` đòi một **hiện vật mở ra xem được** (E6004) — đã là bước tiến so với bản đầu
nhận cả câu *"tôi đã viết xong chương 1 rồi nhé"*. Nhưng một tệp `.c` tồn tại trên đĩa **không
nói nó biên dịch được**. Tác tử ghi tệp, đánh dấu xong, sang bước sau; lỗi dịch chỉ lộ ra ở
bước cuối, khi đã có mấy bước dựng trên nó.

Đây là một lớp nữa của đúng bài học "ô xanh chưa nói gì tới khi biết cơ chế nào làm nó xanh":
dấu "xong" ở đây được bật bởi *sự tồn tại của một tệp*, không bởi *tệp ấy làm được việc*.

### Đã làm

`Buoc` thêm `kiem` và `req`. Khi cờ bật: `kiem_ke_hoach` đòi mọi bước **sinh mã** phải khai
`kiem` (`build.compile`/`test.run`/`sim.run`/`hdl.lint`/`code.analyze`, hoặc `khong` **kèm lý
do ở `ghi_chu`**); `plan.step_done` duyệt sổ cái và đòi `tool_result{tool==kiem, ok==True}` có
`seq` **lớn hơn** `seq` của lần `tool_result` gần nhất của công cụ ghi của bước.

**Thứ tự là cả vấn đề**, không chỉ "đã chạy chưa": một lần biên dịch TRƯỚC khi sửa tệp không
nói gì về tệp sau khi sửa. Có một ca kiểm riêng cho đúng chuyện đó, và một ca nữa cho lần kiểm
**đỏ** không được tính là đã kiểm.

Dữ liệu để trả lời đã có trong sổ cái **từ trước**: `ledger_and_lint` ghi
`tool_result {tool, ok}` theo thứ tự ở mọi lời gọi. Không thêm một dòng dữ liệu mới nào — chỉ
là chưa ai đọc nó để hỏi câu này. Lần thứ năm trong bảy nhiệm vụ gặp hình dạng ấy.

### Đo trên phiên thật: 19 trong 26

Phép đo đầu tôi làm ở mức **dự án** — "sổ cái của dự án này có lần kiểm nào đạt không" — và ra
**0 bước bị chặn**. Con số ấy đúng nhưng **đo sai câu hỏi**: cổng không hỏi "dự án có bao giờ
dịch được không", nó hỏi "lần ghi NÀY đã được kiểm chưa".

Đo lại ở đúng mức: tìm mọi lần `plan.step_done` thành công trong sổ cái thật, lùi về lần
`fs.write`/`fs.edit` gần nhất trước đó, rồi xem giữa hai mốc có phép kiểm nào đạt không.

```
26 lần đánh dấu xong ngay sau một lần ghi mã
19 lần KHÔNG có phép kiểm nào đạt ở giữa  →  cổng sẽ chặn
   robot-tu-can-bang 9 · rtos-ptit 5 · thu-chia-viec 5
```

73 % số lần đánh dấu "xong" cho một bước vừa ghi mã không có bằng chứng nào rằng mã ấy chạy
được. Trong đó có `rtos-ptit` và `robot-tu-can-bang` — hai dự án **cuối cùng vẫn chạy trên bo
thật**, nên con số này không nói sản phẩm sai; nó nói **dấu "xong" được bật sớm hơn bằng
chứng**, và chuỗi bước sau đó dựng trên một niềm tin chưa kiểm.

### Số đo

Bộ kiểm 1657 → **1671 xanh, 0 đỏ** (+14 ca). "Phá lại thì đỏ" cho **cả chín** chỗ sửa, chạy
sau khi xoá `__pycache__`. Không ca cũ nào phải sửa; E6003/E6004/E6009 và thông điệp của chúng
không đổi.

### Hai chỗ ca kiểm của tôi đo sai, đã sửa trước khi tin nó

**Kế hoạch thử không hợp lệ theo luật có từ trước.** Bản đầu của `_kh()` dựng một kế hoạch ghi
`drv.c` mà không có bước chọn kiến trúc — nên `plan.exit` chặn bằng **E6009** (`thieu_phan_tich`,
luật của 30/09/2026) trước khi tới được cổng mới. Ca kiểm đỏ, nhưng đỏ vì một luật khác. Đã
thêm bước `store.adr_create` và một câu nói cấu trúc mã; nay nó đo đúng cổng nó định đo.

**Bảng TC của nhiệm vụ ghi mã lỗi sai.** Tên ca là `test_step_done_chua_build_thi_E6010`, trong
khi E6010 thuộc M1-10; phần thân nhiệm vụ và bảng cấp phát §6 đều ghi **E6012**. Dùng E6012 và
đặt tên ca theo nó.

---

## [DEV-337] [M2-08] `code.analyze` không thấy ngắt, và một regex tham lam nuốt 20 hàm

Nhiệm vụ #8. **Sửa lỗi thuần**, không cờ.

### Hai lỗi, cùng một hệ quả: tài liệu nói thiếu mà không ai biết

Tài liệu phân tích mã sinh ra để người đọc **trước khi duyệt cho sửa**. Nó nói "tệp này có
những hàm nào" — nên một hàm nó không thấy là một hàm **không ai nhìn trước khi sửa**.

1. **Ngắt không khớp mẫu nào.** `_HAM[".c"]` đòi có kiểu trả về trước tên hàm, nên
   `ISR(TIMER0_COMPA_vect)` (cú pháp AVR) và `void __attribute__((interrupt)) TIM2_IRQHandler`
   đều rơi ra ngoài. Đo trên `du-lieu/robot-tu-can-bang/firmware/timer.c`: tài liệu liệt kê
   bốn hàm, **hai ngắt vắng mặt**.
2. **`[^;]*` trong mẫu là tham lam.** Một hàm thân rỗng không có dấu `;` nào, nên mẫu vượt
   qua nó và nuốt luôn các hàm phía sau. Ba hàm thân rỗng liền nhau thì chỉ hàm đầu được
   thấy — đo được: `['phu']` thay vì ba tên.

Ngắt là chỗ đắt nhất để bỏ sót: nó chạy ngoài luồng chính, nó chạm biến chia sẻ, và một lỗi
đồng bộ ở đó **không tái hiện được bằng cách đọc luồng chính** — nên nó cũng không lộ ra trong
lúc thử.

### Số đo trên 185 tệp `.c` thật

```
mẫu cũ thấy 1 758 hàm · mẫu mới thấy 1 786  →  thêm 28 hàm trước đây VÔ HÌNH
   8 ngắt  (cú pháp ISR(...) hoặc __attribute__((interrupt)))
  20 hàm thường  (regex tham lam nuốt)
78 hàm nay được GẮN NHÃN "isr" — 70 trong số đó vốn đã có trong danh sách,
   chỉ chưa ai nói chúng là ngắt
```

**Lần đầu tôi gộp hai con số này thành một câu** — *"thêm 28 hàm, trong đó 78 là ngắt"* — và
nó vô nghĩa ngay trên mặt chữ: 78 không thể là tập con của 28. Hai phép đếm khác nhau: *mới
thấy được* (28) và *nay được gắn nhãn ngắt* (78, phần lớn là hàm `*_IRQHandler` có kiểu trả về
nên mẫu cũ vẫn thấy, chỉ không biết chúng là ngắt). Suýt nữa thì một câu sai vào nhật ký.

### Đã làm

* `_THAM_SO` thay `[^;]*`: không vượt `{`/`}`/`;`, cho đúng một lớp ngoặc lồng (con trỏ hàm
  `void f(void (*cb)(int))`). Danh sách tham số trải nhiều dòng vẫn nhận được — có ca kiểm
  riêng, và nó **vẫn xanh** khi tôi trả lại regex cũ, đúng như một ca canh-đừng-làm-hỏng.
* Ba mẫu ngắt: `ISR(vector)`, `__attribute__((interrupt|signal))`, và tên khớp
  `\w+_(IRQ)?Handler`.
* `_tim_ky_hieu` gộp nhiều mẫu rồi **sắp theo vị trí trong tệp** — thứ tự trong tài liệu là
  thứ tự người đọc thấy khi mở tệp, không phải thứ tự các mẫu regex chạy.
* `phan_loai(p, chu) -> {tên: "ham"|"isr"|"static"}` là **hàm mới**, không đổi kiểu
  `TepMa.ky_hieu` (vẫn `list[str]`): `ai_dung` dùng nó làm khoá, và đổi kiểu ở đó là đổi hợp
  đồng của `code.analyze`.
* Tài liệu thêm cột **Ngắt (ISR)** và một câu nói **hệ quả**, không chỉ liệt kê tên: biến nào
  vừa bị ngắt ghi vừa bị luồng chính đọc thì phải `volatile`, và đoạn đọc nhiều byte phải chặn
  ngắt. Một bảng liệt kê tên không đổi cách người ta đọc phần còn lại; một câu như thế thì có.

### Một tên tôi tự nhớ, và nó sai

Ca kiểm trên firmware thật bản đầu tôi ghi ngắt của `uart.c` là `USART_RX_vect`. Mã thật là
**`USART_UDRE_vect`** (truyền, không phải nhận). Ca đỏ, tôi tra `grep` rồi sửa theo mã. Đây là
lần thứ hai trong đợt này một hằng số tự nhớ sinh ra một phép đo sai — lần trước là
`"thiết"` chứa `"it"` ở DEV-335.

### Số đo

Bộ kiểm 1671 → **1679 xanh, 0 đỏ** (+8 ca). "Phá lại thì đỏ" cho **cả sáu** chỗ sửa.
`test_code_analyze_tra_loi_cau_AI_DANG_DUNG` vẫn xanh; kiểu trả về của `code.analyze` không đổi.

---

## [DEV-338] [M3-01] ERC quá áp: luật đã viết sẵn, `erc()` không gọi nó

Nhiệm vụ #9. **Sửa lỗi thuần**, không cờ.

### Chỗ đứt

`compare.qua_ap(ap_cap, chiu_toi_da)` đã có sẵn **từ trước**: phép so, câu chữ tiếng Việt,
mức `blocker`, và cả phép chặn vế ĐỒNG (N2). `KHOA["v_max"]` cũng đã có bí danh
(`v_max`, `vdd.max`, `vin.max`, `ap_toi_da`). Nhưng `erc()` chỉ gọi **bốn** luật, và không
luật nào gọi `qua_ap` — nên tác tử phải **tự nhớ** gọi `fact.compare` mới thấy.

Một phép kiểm phụ thuộc vào việc ai đó nhớ gọi nó thì không phải một phép kiểm. Lần thứ sáu
trong chín nhiệm vụ gặp đúng hình dạng này.

Luật này khác ba luật kia của §4.2 ở một điểm đáng nói: chúng bắt mạch **chạy sai**, nó bắt
mạch **hỏng**. 5 V vào chân chịu 3,6 V không làm lệch số đo — nó phá con chip, và không có
cách nào "chạy lại để xem".

### Đã làm

`qua_ap_tren_net(cay, tf, phang, thuoc)`, gọi trong `erc()` ngay sau `muc_logic_tren_net`.
Hai vế cấp, vì cùng một lỗi có hai đường vào:

* **rail** — `canonical.ap_danh_dinh` của net (do `ckm.net_set` ghi, tầng `NGUOI`). Không suy
  từ **tên** net: một net tên "3V3" mà bị cấp 5 V thì cái tên chính là thứ sai.
* **tín hiệu** — `voh` lớn nhất của một chân trên net. Đường này thường gặp hơn: nối chân ra
  5 V vào chân vào 3,3 V, và hai con chip đều "đúng" khi đọc riêng.

Thêm hai khoá: `vddio_max` (nhiều chip có VDD lõi khác VDDIO) và `v_tolerant` — chân khai
chịu được 5 V thì **bỏ qua**. Chân 5V-tolerant rất thường gặp (STM32); báo oan ở đó thì bảng
ERC mất uy tín đúng vào loại mạch phổ biến nhất.

Không có vế nào thì **im lặng**, và trong giới hạn thì cũng **không thêm dòng "đạt"**.

### Hai ca kiểm của tôi không canh gì, và một ca trong số đó RỖNG

Phá lại từng chỗ sửa: năm phép phá, **ba** đỏ, **hai** không.

**Ca "không báo trên net đất" là một ca rỗng.** Dàn dựng `bo` của `tests/test_erc.py`
**không có net GND nào** — nên ca ấy xanh cả khi tôi bỏ hẳn phép bỏ qua net đất. Nó không
kiểm gì cả. Nay nó tự dựng một net `loai="gnd"` mang `ap_danh_dinh` (người khai nhầm, chuyện
có thật) cùng một chân có `v_max`; thiếu phép bỏ qua thì ERC báo blocker trên net đất, và ca
đỏ.

**Ca "trong giới hạn" chỉ xét `khong_dat`.** Nên nó xanh cả khi luật sinh một dòng `đạt` cho
mọi chân. Nay nó đòi `_tim(ds, "qua_ap") == []` — không dòng nào, kể cả "đạt".

Đây là lần thứ ba trong đợt này một ca kiểm của tôi xanh vì nó không chạm tới thứ nó nói nó
canh. Hai lần trước ở DEV-335 (một điều tôi tự nhớ sai) và DEV-336 (phép đo sai mức).

### Đo trên dữ liệu thật: 0 phát hiện, và lý do đáng ghi hơn con số

```
5 kho có mô hình mạch chạy được ERC   →  0 phát hiện quá áp
479 Fact thật, ERC đọc được 15:  v_max 5 · vih 3 · i_max 3 · addr 2 · vddio_max 1 · i_out_max 1
```

Mở ra xem thì **hai tập dữ liệu không giao nhau**: ba kho CÓ Fact `v_max` (`thu-nghiem-cuoi`,
`thu-nghiem-g4`, `thu-nghiem-ing-b`) đều **không có mô hình mạch** — không lá, không net;
chúng là dự án thử bộ rút Fact. Còn năm kho có mô hình mạch thì **không kho nào có Fact
`v_max`**.

Và có một đường còn đứt nữa, đứt ngay cả khi hai tập ấy giao nhau: Fact thật dùng chủ thể
**`chip:ATmega328P`**, trong khi `chu_the_la` trả `["leaf:U1", "U1", "ATmega328P"]` — **không
có tiền tố `chip:`**. Nên một Fact `chip:ATmega328P · vdd.max = 5,5 V` là vô hình với ERC dù
mạch có U1 là ATmega328P.

Đó đúng là việc của **M3-07** (#12: *"Nối Fact datasheet ↔ khoá/chủ thể ERC"*), và kế hoạch
M3-01 đã ghi trước *"nên làm cùng M3-07, vì M3-07 sửa cách tra chủ thể `chip:X`"*. Tôi để
nguyên theo phạm vi. Nhưng nói thẳng ở đây: **cho tới khi M3-07 xong, luật này chưa nổ được
trên dữ liệu thật** — nó chỉ nổ trong ca kiểm, nơi Fact được ghi bằng chủ thể `leaf:`/`pin:`.
Một luật đúng mà không có đường tới dữ liệu thì vẫn là một đường dẫn đứt, chỉ là đứt ở khúc
sau.

### Số đo

Bộ kiểm 1679 → **1686 xanh, 0 đỏ** (+7 ca). `test_board_check…_dat == []` và
`test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao` vẫn xanh.

---

## [DEV-339] [M3-03] ERC theo kiểu chân — và hai phép phá chỉ ra THIẾT KẾ của tôi sai

Nhiệm vụ #10. **Sửa lỗi thuần**, không cờ. Tệp mới: `src/eide/knowledge/erc_kieu_chan.py`.

`tools/sch.py` ghi thẳng ở đầu tệp: **máy này không cài KiCad**. Nên bốn lỗi mà ERC của KiCad
bắt bằng một ma trận kiểu chân thì hoặc EIDE tự bắt, hoặc không ai bắt. Bốn luật:
`xung_dau_ra` (blocker) · `nguon_khong_cap` (major) · `net_mot_chan` (minor) ·
`dau_vao_treo` (minor).

`net_mot_chan` đã có từ trước trong `knowledge/ckm.py` (`cho_dut`) — nhưng chỉ là một **dòng
chữ** trong kết quả `ckm.build`: không `path`, không mức, không vào bảng ERC. Nên không ai
lọc được theo mức, và nó mất ngay khi người dùng nhìn sang chỗ khác.

### Hai quyết định để bảng ERC không bị tắt

**`passive` không bao giờ là xung đột.** Mạch di cư từ netlist phẳng có hướng Port mặc định
là `passive` cho gần như mọi chân (`cay._huong_theo_ten` chỉ đoán `power_in` cho VCC/GND). Đo
trên `robot-canbang`: **107 Port lá, không một Port nào là `power_out`**, và phần lớn là
`passive`. Coi `passive` là xung đột thì mạch ấy sáng đèn đỏ hàng loạt.

**Không sinh phát hiện `dat`.** Bốn luật này nói về chỗ sai; một dòng "net này ổn" cho từng
net trên mạch 200 net chôn mất ba dòng đáng đọc.

### Sáu phép phá, ba không đỏ — và hai trong ba là lỗi THIẾT KẾ, không phải lỗi ca kiểm

Đây là lần đầu trong đợt này phép "phá lại thì đỏ" bắt được **thiết kế sai**, chứ chỉ bắt ca
kiểm yếu.

**1. Tôi miễn net ĐẤT cho cả ba luật — và điều đó sai.** Ca kiểm vẫn xanh khi tôi bỏ hẳn phép
miễn, nên tôi mở ra nghĩ lại: đất không được "cấp" (nên `nguon_khong_cap` phải miễn), nhưng
một net GND nối **đúng một chân** nghĩa là chân đất của con ấy **không nối về đâu** — đó là
lỗi thật, và là loại làm mạch chạy chập chờn chứ không chết hẳn. Nay `la_dat` chỉ miễn cho
`nguon_khong_cap` và `dau_vao_treo`, không miễn `net_mot_chan`. Ca kiểm nay ghim cả hai chiều.

**2. Nhánh "cấp được vì khai `iout_max`" không ca nào chạm tới.** Bỏ hẳn nhánh ấy mà mọi ca
vẫn xanh — vì trong dàn dựng, U3 đã có hướng `power_out` nên nhánh Fact không bao giờ chạy.
Nhánh ấy lại đúng là thứ cần cho **mạch di cư** (hướng Port là `passive`, nhưng khối nguồn có
Fact `iout_max`). Đã thêm ca kiểm đi đúng đường đó.

Phép phá thứ ba (`net_mot_chan` mất `path`) thì ca của chính nó đỏ — chỉ
`test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao` không đỏ, vì `"/board"` vẫn là một path hợp lệ.
Đó không phải lỗ: ca HIER17 canh "có path", không canh "path đúng chỗ".

### Đo trên 5 mô hình mạch thật: 8 phát hiện, và tôi đã soi từng cái

`EIDE_FEATURE_SCHEMATIC=1 tools/thu_sch.py` → **63/63**, không tụt.

```
nguon_khong_cap  6    net_mot_chan  2
  robot-canbang    +5V (U2.MS1…), VMOT (U2.VMOT, U3.VMOT)
  thu-18           +3V3 (C2.1, U1.2), +5V (C1.1, U1.3)
  thu-nghiem-ckm   3V3 (U1.7, U2.1) · net ALERT một chân (U2.3) · net SCL một chân (U1.28)
  thu-nghiem-sch   3V3 (U1.7, U3.2)
```

Soi từng cái, không gọi gộp là "báo nhầm" hay "bắt đúng":

* **`robot-canbang` +5V và VMOT — đúng, và đúng y như KiCad.** Mô hình **không có Port
  `power_out` nào**: 5 V đến từ bo Arduino, VMOT từ nguồn ngoài. KiCad gặp đúng tình huống
  này cũng báo *"Input power pin not driven by any Output Power pin"*, và cách sửa của nó là
  thêm **PWR_FLAG**. Lời nhắc của ta chỉ thẳng sang `ckm.net_set(pwr_flag=true)` — cùng một
  cơ chế, cùng một câu trả lời.
* **`thu-nghiem-ckm` net SCL nối đúng một chân (`U1.28`) — bắt đúng một lỗi thật.** Chân
  clock của I2C không nối tới cảm biến. Đây là dự án thử nên mô hình dựng dở, nhưng phát hiện
  thì không sai: mô hình đang nói SCL không dẫn đi đâu.
* **`thu-nghiem-sch` và `thu-18` — nói đúng về MÔ HÌNH, chưa chắc đúng về mạch.** `U3.2`
  (VOUT của LDO) có hướng `passive`, nên mô hình **không khai** ai cấp 3V3. Đó là "chưa
  biết", không phải "sai". Ta vẫn báo, và vẫn là mức `canh_bao/major` chứ không phải blocker
  — đúng cách KiCad xử: chân `passive` trên net nguồn **không** làm im lời nhắc, vẫn phải
  khai PWR_FLAG hoặc đặt đúng kiểu chân.

Tổng 8 phát hiện trên 5 mạch — không phải nhiễu hàng loạt, và mỗi cái dẫn tới một việc cụ
thể. Nhưng ghi rõ ở đây: **sáu trong tám là "mô hình chưa khai", không phải "mạch sai"**. Ai
đọc bảng ERC cần biết khác biệt ấy, nên câu `cach_sua` của luật nói cả hai lối: nối tới chân
`power_out`, **hoặc** khai `pwr_flag` nếu nguồn đến từ ngoài bo.

### Số đo

Bộ kiểm 1686 → **1695 xanh, 0 đỏ** (+9 ca). `thu_sch.py` 63/63.
`test_board_check…_dat == []` và `test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao` vẫn xanh.

---

## [DEV-340] [M3-04] Hai bộ cấp trên một rail, và rail nối vào GND — hai lỗi bị bỏ qua lặng lẽ

Nhiệm vụ #11. **Sửa lỗi thuần**, không cờ.

### Hai chỗ im lặng, và cái thứ hai im lặng theo kiểu tệ hơn

**`_hai_ve_dong` giữ MỘT bộ cấp và bỏ các bộ khác.** Đúng một dòng:
`if f_cap is not None and (cap is None or _uu_tien(f_cap) < _uu_tien(cap["fact"]))` — bộ cấp
ở tầng tin nhất thắng, các bộ còn lại **không được nhắc tới ở đâu cả**. Hai LDO cùng đẩy lên
một rail thì con có điện áp ra cao hơn gánh hết tải, con kia chạy ngược, cả hai nóng lên — và
chuyện đó không đọc ra được từ sơ đồ.

**`_nhom_nguon` loại CẢ NHÓM nếu chỉ MỘT net thành viên là đất.** Nên một rail +3V3 bị nối
nhầm vào GND thì cả nhóm rơi khỏi **mọi** phép kiểm — không phải "bỏ qua một luật", mà là
biến mất khỏi bảng ERC, đúng lúc nó đáng được kiểm nhất. Mạch ấy sẽ chết ngay khi cấp điện.

### Đã làm

`tranh_chap_nguon(cay, tf, thuoc)` — blocker khi từ **2 lá** trở lên cấp một nhóm net, nhận
ra bằng Fact `iout_max` **hoặc** hướng `power_out`. `chap_nguon(cay, thuoc)` — blocker khi một
nhóm điện có cả net nguồn lẫn net đất.

Ba chỗ phải cẩn thận, cả ba có ca kiểm riêng:

* **Port của KHỐI không được đếm.** Trên mạch mẫu, net 3V3 có **hai** Port `power_out`: của
  lá U3 và của khối `/board/pwr`. Port khối là *đường đi qua* cấp, không phải bộ cấp thứ hai
  — đếm cả nó thì mọi mạch có khối nguồn đều bị báo tranh chấp, tức luật nổ trên chính cái
  mạch đúng.
* **Gom theo `ref`.** Một LDO có hai chân VOUT song song vẫn là MỘT bộ cấp.
* **`or_ing` khai rõ thì im.** Cấp song song qua diode OR-ing (nguồn dự phòng) là thiết kế có
  thật. Báo oan ở mức `blocker` thì người ta học được cách bỏ qua blocker — mức duy nhất
  không được phép bị bỏ qua.

### Phép phá thứ năm không đỏ: nhánh nhận dạng đất THEO TÊN chưa ca nào chạm tới

Năm phép phá, bốn đỏ. Cái không đỏ: bỏ `ten_net.upper() in TEN_DAT` khỏi `chap_nguon` mà ca
vẫn xanh — vì net GND trong ca kiểm của tôi khai `loai="gnd"` tử tế.

Nhánh theo tên lại đúng là nhánh **cần nhất**: mạch di cư từ netlist phẳng thường chỉ có
**tên** net, không có `loai`. Chỉ xét `loai=="gnd"` thì luật im đúng trên loại mạch mà người
ta nối sai nhiều nhất. Đã thêm ca dùng net tên `VSS` không khai `loai`, và phá lại thì đỏ.

### Đo trên 5 mô hình mạch thật: 0 phát hiện — và đây là con số ĐÚNG

```
5 kho chạy được ERC  →  tranh_chap_nguon 0 · chap_nguon 0        (thu_sch.py 63/63)
```

Con số 0 này **khác hẳn** con số 0 của DEV-338. Ở M3-01, luật không nổ được vì **đường tới
dữ liệu bị đứt** (Fact dùng chủ thể `chip:X`). Ở đây 0 là câu trả lời đúng: hai lỗi này là
loại *catastrophic* — không bo nào sống tới lúc được lưu vào kho mà vẫn còn hai LDO đánh nhau
trên một rail.

Để con số 0 ấy không bị đọc thành "luật chết", tôi **cấy lỗi vào bản sao của một kho thật**
(`robot-canbang`): thêm hai lá, mỗi lá một chân `power_out` nối vào net `+5V` thật của mạch
ấy.

```
trước khi cấy:  không phát hiện nào
sau khi cấy:    1 blocker — "Net nguồn +5V có 2 bộ cấp: `UX1`, `UX2`"
```

Luật sống, chạy trên mô hình thật, và im khi không có gì để nói. Đó là hai điều khác nhau và
cả hai đều cần đo — một luật im vì không có lỗi và một luật im vì nó không chạy thì trên bảng
ERC trông giống nhau y hệt.

### Số đo

Bộ kiểm 1695 → **1703 xanh, 0 đỏ** (+8 ca). `thu_sch.py` 63/63. Các ca `test_HIER07_*` và
`test_khoi_cap_nhan_ra_bang_FACT_du_Port_chua_biet_huong` giữ nguyên.

---

## [DEV-341] [M3-07] Nối Fact datasheet ↔ ERC, và nói ra ERC kết luận được bao nhiêu

Nhiệm vụ #12. **Sửa lỗi thuần** — và nó gỡ đúng chỗ đứt mà DEV-338 (#9) đã đo ra và nói trước.

### Bốn chỗ đứt, nối lại

1. **Chủ thể.** `fact.extract` ghi `subject = thuc_the`, và mô tả công cụ khuyên dạng
   `chip:ATmega328P@1.0.0`. Còn `chu_the_la` chỉ tra `leaf:U1` · `U1` · tên chip, và
   `TraFact.tra` khớp chuỗi **tuyệt đối**. Nên **mọi Fact trích từ datasheet không bao giờ
   tới được ERC**: bộ rút Fact chạy đúng, ERC chạy đúng, hai bên không nhìn thấy nhau.
   Nay `TraFact` đánh chỉ mục **thêm** dưới tên trần (`chip:X@ver` → `X`), bỏ tiền tố và
   phiên bản, **không nới gì khác**.
2. **Khoá.** `docs.py` sinh `icc.typ` ở chế độ dòng chữ (`icc.max` chỉ ở chế độ bảng), mà bí
   danh `i_max` không có `icc.typ`. Nay có — nhưng kèm cờ `dung_typ_thay_max` trong bằng
   chứng và một câu trong `vi`: *"có vế dùng con số **danh định** `.typ`, không phải tối đa"*.
   Dòng danh định nhỏ hơn dòng tối đa, nên một ngân sách "đạt" tính bằng `typ` có thể không
   đạt khi chạy thật. Nhận con số thì được; im lặng về nó thì không.
3. **Mẫu trích còn thiếu.** Không có mẫu nào cho `iout.max` (vế **CẤP** của luật ngân sách
   dòng) và `i2c.addr` (vế **duy nhất** của luật trùng địa chỉ bus). Nay có cả hai, kèm
   khoảng hợp lý `iout.max = (1 mA, 50 A)` — cái phanh cuối cho vế cấp, vì một Fact sai ở
   đó làm ERC kết luận "đạt" cho một mạch thiếu nguồn.
   Địa chỉ đọc được cả `0x48` và `1001000` (nhị phân 7 bit), **cùng trả về `0x48`**: hai
   Fact cùng một địa chỉ mà ghi khác dạng thì phép so trùng không bắt được — đúng lỗi nó
   sinh ra để bắt.
4. **Độ phủ.** `erc.do_phu(ds)` trả `{luat: {dat, khong_dat, canh_bao, chua_du}}` kèm
   `_fact_con_thieu`. `board.check` và `sch.netlist` trả thêm khoá `do_phu` (khoá cũ không
   đổi). `sch.netlist` trước đây chỉ trả `khong_dat` — `chua_du_du_kien` **bị ẩn hẳn**, nên
   "netlist sạch" và "ERC không kết luận được gì" đọc ra giống nhau.

### Số đo

**Fact tới được ERC: 5 → 17 (+12).** Ba kho có Fact trích từ datasheet
(`thu-nghiem-cuoi` 4, `thu-nghiem-g4` 6, `thu-nghiem-ing-b` 2) — **toàn bộ** đều mang chủ
thể `chip:`, tức trước M3-07 **không một Fact nào trong số đó tới được ERC**.

**Độ phủ ERC trên 5 mô hình mạch thật** (con số nay đọc được, trước đây không có):

```
robot-canbang     6 phát hiện · kết luận được 4 · chưa đủ 2
thu-18            4            · 2 · 2
thu-nghiem-ckm    6            · 5 · 1
thu-nghiem-hier   3            · 3 · 0
thu-nghiem-sch    2            · 1 · 1
```

Bộ kiểm 1703 → **1713 xanh, 0 đỏ** (+10 ca). `thu_sch.py` 63/63.

Hai tập dữ liệu vẫn chưa giao nhau (ba kho có Fact `v_max` vẫn không có mô hình mạch), nên
luật quá áp của M3-01 vẫn chưa nổ trên dữ liệu thật — nhưng **đường dẫn đã thông**: từ nay một
Fact `chip:X` trên một kho có mạch sẽ tới được ERC.

### Phép phá của tôi dựng sai, và ca âm thì xanh vì lý do khác

Tám phép phá, bảy đỏ. Cái không đỏ là phép phá "nới tay phép tra chủ thể" — và nó phơi ra
**hai** lỗi của tôi, lồng vào nhau:

**Phép phá dựng sai.** Tôi cắt tên chip còn 2 ký tự (`AMS1117` → `AM`) tưởng là nới lỏng.
Không phải: `"AM"` chẳng khớp chủ thể nào, nên nó còn **chặt hơn** bản đúng. Dựng lại cho
đúng kiểu nới tay thật: cho `tra()` rơi về **bất kỳ** Fact `chip:` nào cùng khoá.

**Ca âm vẫn xanh.** Và lần này không phải vì phép phá: ca `test_chip_khac_ten_khong_bi_gan_nham`
chỉ khai `i_max` cho U1, không khai cho U2 — nên kết luận là `chua_du_du_kien` **vì U2 thiếu
Fact dòng**, bất kể vế cấp có bị gán nhầm hay không. Nó xanh vì một lý do khác hẳn thứ nó nói
nó canh.

Sửa: khai đủ `i_max` cho **cả hai** vế tiêu thụ, để thứ duy nhất còn thiếu là vế **CẤP**. Nay
nới tay phép tra là ca ấy đỏ ngay.

Đây là lần thứ tư trong đợt này một ca kiểm xanh vì không chạm tới thứ nó canh (DEV-335,
DEV-338, DEV-339, và lần này) — nhưng là lần đầu **phép phá cũng sai**, nên suýt nữa tôi kết
luận "ca âm này canh tốt" từ hai cái sai cùng che nhau.

---

## [DEV-342] [M3-10] Vòng sinh → ERC → sửa, có trần — và ERC chỉ chạy khi có ai gọi

Nhiệm vụ #13. Sau cờ `EIDE_FEATURE_ERC_TU_DONG`, mặc định TẮT. Tiền đề M3-03, M3-04, M3-07 —
cả ba vừa xong, nên từ nay ERC đã có thứ đáng báo.

### Chỗ hở

ERC chỉ chạy khi **có ai gọi**: `board.check`, `ckm.build`, `sch.netlist`. Nên một tác tử
dựng mạch bằng mười lời gọi `ckm.*` rồi nói "xong" **chưa bao giờ nhìn thấy** bảng ERC — trừ
khi nó tự nhớ gọi. Và đo trên dữ liệu thật (DEV-338, DEV-339): không phiên nào gọi
`board.check` sau một chuỗi sửa bản đồ.

Đây là cùng một hình dạng với M1-01 → M3-07, nhưng ở một tầng khác: không phải "cơ chế có mà
đường dẫn đứt", mà **"cơ chế có, đường dẫn thông, và không ai đi vào đường ấy"**.

### Ba chỗ cố ý làm hẹp, mỗi chỗ chữa một cách hỏng khác

* **Chỉ báo lỗi MỚI** (so với ảnh ERC của lần ghi trước, `ctx.erc_truoc`). Báo lại lỗi cũ ở
  mỗi lời gọi thì sau năm lời gọi tác tử đọc cùng một dòng năm lần — và nó học được cách bỏ
  qua khối ấy, kể cả lần có dòng mới.
* **Trần 3 lần sửa cho cùng một `(luật, path)`**, rồi đổi lời nhắc sang `ask_user`. Hai lần
  sửa đầu không đúng thì cái sai thường nằm ở chỗ **hiểu đề bài**, không ở chỗ gõ — lần sửa
  thứ tư chỉ để khẳng định điều đó, bằng tiền.
* **Chỉ sau công cụ GHI**, lọc bằng `spec.writes_artefact`. `ckm.graph` và `khoi.list` là
  `writes_artefact=False`, nên chúng không kích ERC. ERC là mã thuần, nhưng không miễn phí.

Và một cửa im lặng nữa ở hook Stop: tác tử **đã nói ra** lỗi (khớp tên luật hoặc `path` trong
`ctx.loi_da_noi`) thì thôi. Thiếu cửa đó thì hook thành vòng lặp — nó bắt thêm vòng, tác tử
nói về lỗi, nó vẫn thấy lỗi còn đó và bắt thêm vòng nữa.

### Chi phí: đo, không đoán

Hook chạy sau **mỗi** lần ghi bản đồ, nên chi phí là câu hỏi thật:

```
robot-canbang    187 nút · ERC  7,6 ms · 6 phát hiện, 4 nặng
thu-nghiem-ckm    41 nút ·      0,7 ms
thu-18            21 nút ·      0,4 ms
thu-so-do          6 nút ·      0,3 ms
```

187 nút là mô hình mạch lớn nhất trong kho, và 7,6 ms thì không đáng một dòng bàn. Trần 2000
nút vẫn đặt, và khi vượt thì hook **nói ra** trong `note_vi` thay vì im lặng bỏ qua: một hook
im lặng chậm còn tệ hơn một hook không chạy, vì người dùng không biết nó đang ở đâu.

### Hai ca kiểm của tôi đo chính câu lệnh của mình

**Dàn dựng sai luật của sản phẩm.** Bản đầu tôi dựng lỗi `xung_dau_ra` bằng `ckm.chip_add`,
và nó bị chặn bằng **E8002**: *"không có Fact chân nào mang khoá `net`"* — đúng luật
(`chip_add` không cho tự đặt net). Ca kiểm đỏ, nhưng đỏ vì một luật khác. Dựng lại quanh
`chap_nguon` (rail nối vào GND), lỗi chỉ cần khối/Port/net — đúng những gì công cụ `ckm.*`
làm được, và cũng đúng cách tác tử thật dựng bản đồ.

**Ca "trần 3 lần" đo chính nó.** Bản đầu đặt thẳng `ctx.erc_lan_sua[k] = 3` rồi khẳng định
`ctx.erc_lan_sua` khác rỗng — tức nó đo câu lệnh vừa gõ, không đo mã sản phẩm. Thực tế bộ đếm
**rỗng** ở thời điểm ấy: nó chỉ tăng khi lỗi **còn lại sau một lần ghi nữa**. Nay ca kiểm ghi
thêm một lần rồi `assert` bộ đếm khác rỗng **trước** khi ép nó lên 3.

### Số đo

Bộ kiểm 1713 → **1720 xanh, 0 đỏ** (+7 ca). `thu_sch.py` 63/63, `kiem_tai_lieu` 0 chỗ lệch.
Bảy phép phá, **bảy** đỏ — lần đầu trong đợt này không phép phá nào trượt.

Cờ vẫn TẮT: "Tiêu chí xong" đòi eval 76 ca và bộ phát lại không tụt trước khi bật mặc định,
và nó chèn lời nhắc vào transcript nên chỉ eval nói được nó làm tác tử khá hơn hay tệ hơn.

---

## [DEV-343] [M3-12] PASS giả của mô phỏng HDL — và regex của kế hoạch từ chối oan 588/846

Nhiệm vụ #14. **Sửa lỗi thuần** (ô xanh giả), không cờ.

### Ba lỗ, cả ba cho ra một chữ PASS màu xanh

Bản cũ đọc kết quả mô phỏng bằng đúng ba dòng:

```python
tren = kq.nguyen_van.upper()
co_pass, co_fail = "PASS" in tren, "FAIL" in tren
kq.dat = co_pass and not co_fail
```

* `nguyen_van` là log **biên dịch cộng** log chạy. Nên một dòng do chặng biên dịch in ra làm
  cả chặng "đạt" trong khi testbench **không in gì**.
* Dò **chuỗi con**, nên `"bypass mode on"` chứa `"PASS"`.
* **Không xét `ma_thoat`**, nên `$fatal` sau khi đã in PASS thì vẫn đạt.

Đây là ô xanh giả nằm trên **chính đường đo** — loại đắt nhất, vì mọi thứ phía sau đều tin
vào nó. Và `kq2.vi_sao_khong_dat` (quá hạn, không chạy nổi) trước đây bị bỏ rơi: `kq2` mang
nó, `kq` thì không, nên nó không tới được người đọc.

### Hàm thuần `doc_ket_qua_tb(log_chay, ma_thoat)`

`dat` = có ≥ 1 dòng PASS, 0 dòng FAIL, không dấu hỏng (`FATAL`/`ERROR` đầu dòng, `%Error`,
`Assertion failed`, `$fatal`), **và** `ma_thoat == 0`. Thêm `so_ca_pass`/`so_ca_fail` vào
`KetQuaHdl.to_dict()`: "2 pass / 1 fail" nói ngay rằng testbench có chạy và có ca đỏ, còn
chữ `FAIL` trần không phân biệt được "một ca đỏ" với "testbench chết ngay dòng đầu".

### Regex mà kế hoạch ghi sẵn từ chối oan 588 trong 846 bản ghi thật

Kế hoạch M3-12 ghi mẫu `^\s*(?:TEST\s+\S+\s+)?(PASS|FAIL)\b`. Tôi hiện thực đúng thế, rồi
chạy nó trên **846 bản ghi chặng mô phỏng thật** trong `du-lieu/`:

```
846 bản ghi · bản cũ gọi ĐẠT 846 · bản mới (theo regex kế hoạch) 258 · lệch 588
```

**588 lệch là con số quá lớn để mừng.** Mở log ra đếm thì thấy quy ước in của testbench dự
án này là **nhãn đứng TRƯỚC** từ khoá:

```
KET QUA: PASS                    243 lần
TB_PCPI_DOT4: PASS               201
KET QUA MO PHONG: PASS            69
PASS: Hoan tat 4 phep do...       40
KET QUA MO PHONG BAI 2: PASS      51
```

Mẫu chỉ-neo-đầu-dòng gọi **toàn bộ** những dòng ấy là "không in gì". Một bộ đọc chặt tới mức
gọi mọi testbench đang chạy đúng là "không in gì" thì nó không chặt — nó chỉ sai theo chiều
khác, và chiều ấy còn tệ hơn: nó biến 588 phép đo thật thành rác.

Nới đúng một chỗ: cho phép một **nhãn kết thúc bằng `:` hoặc `]`** trước từ khoá. Vẫn không
bắt chuỗi con:

* `bypass mode on` — không có `:` ngay trước `pass`;
* `pass_through.v:3` — `PASS\b` không khớp vì sau nó là `_`;
* `OK: Tat ca cac ca am tinh deu pass (...)` — có `:`, nhưng sau dấu ấy là chữ khác. Đây là
  một câu **kể**, không phải một dòng kết quả, và nó cũng lấy từ log thật.

Đo lại: **846/846 khớp bản cũ, 0 từ chối oan.** Và bộ kiểm vẫn bắt đủ bốn ca PASS giả.

Hai phép phá mới canh đúng hai chiều của chỗ nới này: thu mẫu về như kế hoạch ghi → ca quy
ước thật đỏ; bỏ yêu cầu dấu `:`/`]` → ca câu-kể và ca `bypass` đỏ.

### Hai ca kiểm của tôi xanh vì lý do sai

**Tệp mô phỏng giả dùng `$4`, mà `-o <anh>` là `$3`.** Nên `iverilog` giả không sinh ra tệp,
`mo_phong` dừng ngay ở *"iverilog không sinh ra tệp mô phỏng"*, và `vvp` giả **chưa bao giờ
chạy** — hai ca kiểm xanh mà chưa chạm tới thứ chúng định đo.

**Ca FATAL bắt được do tình cờ.** Bản đầu dùng `"FATAL: assertion failed"`, và mã cũ bắt được
nó vì `"FAILED"` **chứa** `"FAIL"` — tức ca ấy xanh cả trước lẫn sau khi sửa. Đổi sang
`"FATAL: timeout at t=10000"` (không có chữ "failed") thì nó đỏ đúng trên mã cũ.

**Và một ca nữa không canh được chỗ nó tưởng.** Ca "tên tệp `pass_through.v` trong log biên
dịch" vẫn xanh khi tôi cố ý đọc lại log gộp — vì chữ `pass` của nó nằm **giữa dòng**, nên
phép neo dòng đã chặn sẵn. Tách thành một ca riêng với log biên dịch in `PASS: lint clean`
**đầu dòng** (chuyện có thật với script bọc lint) thì chỗ "chỉ đọc log chạy" mới có ca canh.

### Số đo

Bộ kiểm 1720 → **1732 xanh, 0 đỏ** (+12 ca). `kiem_tai_lieu` 0 chỗ lệch.
Tám phép phá, tám ca đỏ. Giao thức tối thiểu giữ nguyên: testbench chỉ in `PASS` vẫn đạt.

---

## [DEV-344] [M3-13] `hdl.sensitivity` — và một con số tự khai trông y như một con số đã đo

Nhiệm vụ #15. **Công cụ mới**, R1, `core=False`, không cờ.

### Chỗ hổng: `hdl.sim` nhận `do_nhay` do tác tử **tự điền**

DEV-343 vừa làm `hdl.sim` đọc `PASS`/`FAIL` thật chặt. Nhưng tham số `do_nhay` của nó thì
không ai kiểm: tác tử gõ `{"bat": 7, "tong": 7}` là kho nhận. Mô tả tham số có dặn *"chỉ điền
khi đã thật sự làm"* — và một lời dặn không phải một phép đo.

Con số ấy đi thẳng lên **dòng quan trọng nhất của khối A8.0**, dòng đặt ngay dưới chữ PASS.
Trước nhiệm vụ này, một con số tự khai và một con số đo được hiện ra **giống hệt nhau** ở đó.

### Ba chỗ sửa

**`dot_bien.PHEP_VERILOG`** — năm phép đột biến cho Verilog: đảo điều kiện `if`, `&` → `|`,
hằng `'d` cộng 1, `posedge` → `negedge`, `==` → `!=`. `dot_bien_van_ban`/`do_do_nhay` nhận
thêm tham số `bang`, **mặc định vẫn bảng C**, nên `test.sensitivity` của firmware không đổi
hành vi một chút nào.

**`hdl.do_do_nhay_hdl()`** — phá mã RTL thật rồi chạy lại testbench. Nó không viết lại vòng
đột biến: chỉ đưa bảng Verilog và một hàm `chay` vào `do_do_nhay` đã có, nên phần *"trả tệp
về nguyên vẹn trong `finally`"* cũng dùng lại chứ không viết lần hai.

**Công cụ `hdl.sensitivity`** — ghi `{bat, tong, do_bang: "ma"}` **đè** lên con số tự khai: một
phép đo thắng một lời khai. Và `hdl.sim` từ nay đánh dấu con số nó nhận là `do_bang: "tu_khai"`,
để khối A8.0 nói thẳng ra *"tác tử tự khai, chưa ai đo lại"*.

Ca đắt nhất của cả nhiệm vụ là testbench in `PASS` **vô điều kiện**: nó cho ra đúng chữ mà
`hdl.sim` đọc được, và không phép kiểm nào phân biệt được nó với testbench thật — trừ phép này.
Phá gì nó cũng xanh, và `so_khong_thay` đếm đúng chỗ đó.

### Đo trên testbench thật của Bài 3 (lõi RISC-V)

| testbench | kết quả |
|---|---|
| `tb_pcpi_dot4` | **1/1** — *đảo điều kiện if (3 chỗ)* → bộ kiểm ĐỎ |
| `tb_pcpi_mac` | **1/1** — *đảo điều kiện if (2 chỗ)* → bộ kiểm ĐỎ |
| `tb_pcpi_vmini` | **không đo được** — bộ kiểm ĐỎ từ trước khi phá gì |

Cổng chặn *"bộ kiểm phải xanh trước khi đo"* đã làm đúng việc của nó ở dòng thứ ba, và thứ nó
chặn lại là một phát hiện: `tb_pcpi_vmini.v` tạo thực thể `bram` với năm cổng
`b_en`/`b_addr`/`b_wdata`/`b_wstrb`/`b_rdata` — **bản hai cổng**. Mà `rtl/bram.v` đã bị đưa về
một cổng ngày 02/10/2026, có lý do ghi sẵn trong chính tệp ấy: bản hai cổng làm suy luận BSRAM
đứt hoàn toàn, yosys dựng cả 32 KB thành 262 144 flip-flop trên con GW2AR-18 chỉ có 15 552.
Nên testbench của nấc 3c **không dịch nổi** từ hôm ấy tới nay:

```
tb_pcpi_vmini.v:50: error: port ``b_en'' is not a port of ram.   (và 4 cổng nữa)
```

`bai3/NGOAI-PHAM-VI.md` vẫn ghi *"bộ kiểm 3c — độ nhạy 7/7, có đồng hồ canh đã chứng minh nổ
được"*. Câu ấy **đúng vào lúc nó được viết** và sai từ lúc `bram.v` đổi — một con số đo đúng
rồi nằm lại trong tài liệu sau khi thứ nó đo đã biến mất. Bài 3 đã ở ngoài đường dựng
(`NGOAI-PHAM-VI.md` nói thế), nên tôi **không sửa RTL**; chỗ này ghi vào đây là để con số 7/7
kia đừng được đọc như một số còn hiệu lực.

### Mẫu số là **TỆP**, không phải phép phá — và nhãn đang gọi sai

Thấy ra khi đối chiếu `1/1` của tôi với `7/7` của bản đo tay `tai-lieu/do-nhay-dot4.py`.
`do_do_nhay` có `break` ngay khi một phép phá làm bộ kiểm đỏ, nên nó **không bao giờ** đếm hết
năm phép: `1/1` nghĩa là *1 trong 1 tệp RTL*. Nhãn thì ghi `bắt 1/1 phép phá mã`.

Hai nguồn đổ vào cùng một ô ấy đếm hai thứ khác nhau — tác tử tự khai thường khai số **phép**,
công cụ đo trả số **tệp** — và một nhãn chung mời người đọc so `1/1` với `7/7` như hai con số
cùng thước, rồi kết luận bộ kiểm yếu đi trong khi chỉ có cái thước đổi. Nhãn giờ đi theo
`do_bang`: *"bắt 1/1 tệp RTL bị phá thì bộ kiểm ĐỎ (đo bằng mã)"* với con số đo được, giữ
*"phép phá mã"* cho con số tự khai. `note_vi` của công cụ sửa cùng một chỗ — câu của nó trước
đây mở đầu bằng "phép phá mã" rồi nửa sau lại nói "tệp", sai đơn vị với chính nó trong một câu.

### Một lỗi của chính phép đo, không phải của sản phẩm

Dàn dựng đầu tiên của tôi gom RTL và testbench vào **một** thư mục. `tb_pcpi_mac.v` ghi
`` `include "bai3/rtl/pcpi_mac.v" `` — đường dẫn tính từ gốc cây Bài 3 — nên include đứt, và
**cả ba** ca báo *"bộ kiểm đang ĐỎ từ trước"*. Một kết luận sai **về sản phẩm**, sinh ra từ một
dàn dựng sai của phép đo. Đặt `goc` đúng ở `docs/riscv-tn20k/` thì hai ca đầu xanh ngay.

Đây đúng hình dạng việc còn mở trong README §8 về đường dựng bitstream: `include` tính từ gốc
dự án thì mọi phép đo phải đứng đúng chỗ ấy mới chạy, và khi nó không chạy thì lỗi hiện ra như
lỗi của thiết kế.

Lần đo ghi vào mục này chạy trên một **bản sao** của `docs/riscv-tn20k/`, không trên cây theo
git — phép đo này ghi đè tệp RTL thật rồi trả về trong `finally`, và một lần ngắt giữa vòng sẽ
để lại mã đã bị phá trong thư mục làm việc. `diff -rq` sau khi đo: không chỗ nào lệch.

### Một ca kiểm cũ phải nới

`test_do_nhay_di_theo_hien_vat_khong_chi_tra_cho_mo_hinh` chốt cứng **cả dict** `do_nhay`, nên
thêm khoá `do_bang` là nó đỏ. Nay nó kiểm `bat`/`tong` **có vào kho** chứ không so cả dict —
đúng ý "Bảo vệ hồi quy" của nhiệm vụ: ca ấy canh việc con số tới được kho, không canh việc
dict có đúng ba khoá.

### "6/6" của bản WIP là 7/9 khi phá bằng tập rộng hơn

Bản WIP khai *"phá lại thì đỏ: 6/6 chỗ sửa"*. Trước khi chốt, tôi dựng lại phép phá với **chín**
chỗ — mỗi chỗ một cách tháo khác nhau, xoá `__pycache__` trước từng lượt (DEV-335) — và được
**7/9**. Hai chỗ LỌT:

* **Tháo `bang=PHEP_VERILOG` khỏi `do_do_nhay_hdl`** → bộ kiểm **vẫn xanh**. Bảng kiểu C tình
  cờ cũng phá được `dem.v` của hai ca có sẵn (`q + 1` → `q - 1`), nên không ca nào chứng minh
  được rằng đường HDL thật sự dùng bảng Verilog. Cả năm phép Verilog — thứ duy nhất khiến
  nhiệm vụ này tồn tại — có thể bị tháo mà bộ kiểm không nhúc nhích.
* **Đổi cổng *"bộ kiểm phải XANH trước khi đo"* thành `if False`** → bộ kiểm **vẫn xanh**. Đúng
  cái cổng vừa phát hiện ra `tb_pcpi_vmini` thì không có ca nào canh. Tháo nó đi là
  `hdl.sensitivity` ghi `{bat: 0, tong: 0, do_bang: "ma"}` vào kho — một lời khai mặc áo phép đo,
  tức đúng cái bệnh nhiệm vụ này đi chữa, lần này do chính công cụ chữa bệnh gây ra.

"6/6" không sai về số; nó sai về **tập**. Sáu phép phá ấy chọn đúng sáu chỗ đã có ca canh. Một
tỉ lệ bắt 100 % chỉ nói được điều gì khi tập phép phá không do người đang mong nó đẹp chọn ra.

Bù hai ca: `TC-M3-13-06` dùng một mô-đun mà **chỗ duy nhất** phá được là `posedge` (bảng C
không có phép nào khớp: không hằng ≥ 2 chữ số, không `==`, không `<` vì `<=` bị chặn, không
`+`), kèm một testbench phân biệt được hai sườn; và `TC-M3-13-07` gọi **chính công cụ** với
một testbench in `FAIL` ngay, rồi kiểm đủ ba điều: trả `ok=False`, mã `E4030`, **và kho không
bị ghi**. Phá lại: **9/9**.

### Số đo

Bộ kiểm 1732 → **1744 xanh, 0 đỏ** (+12 ca). `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN, và số
"cần đọc lại" 15 → 11 sau khi cập nhật số công cụ 127 → 128 trong README.
**Phá lại thì đỏ: 9/9 chỗ sửa.**

Công cụ thứ 128 này **chưa lượt Agent nào gọi** — mã của nó đã chạy trên hiện vật thật, nhưng
đó là tôi gọi hàm, không phải tác tử gọi công cụ. README §8 đếm nó vào phần chưa dùng thật,
vì đúng cái phân biệt ấy là nội dung của nhiệm vụ này.

---

## [DEV-345] [M3-18] Ràng buộc chân FPGA — và một bitstream đã dựng với chân đồng hồ tự chọn

Nhiệm vụ #16. **Sửa lỗi thuần** (bitstream "đạt" mà chân do công cụ chọn) + **công cụ mới**
(`hdl.constraints_check`, R1, `core=False`), không cờ.

### Chỗ hổng: `dat_di_day` chỉ hỏi "tệp `.cst` có tồn tại không"

Câu ấy không đủ, và chỗ nó không đủ là chỗ tốn nhất của cả đường FPGA. Nếu một cổng của mô-đun
đỉnh **không có `IO_LOC`**, nextpnr không báo lỗi — nó tự chọn một chân còn trống. Tổng hợp đạt,
đặt-đi dây đạt, bitstream dựng xong, Fmax đẹp. Rồi nạp lên bo thì đèn không sáng, và không một
dòng nào trên màn hình nói vì sao: người ta sẽ đi tìm lỗi trong RTL, vì mọi chặng đều xanh.

Phép kiểm phải đứng **trước** nextpnr. Sau nó thì không còn gì để chặn: chân đã được chọn, và
một chân chọn sai cũng là lựa chọn hợp lệ với công cụ.

### Chuyện ấy đã xảy ra rồi, trên hiện vật trong repo

Chạy phép kiểm trên **sáu cặp (mạng cổng, `.cst`) thật** trong `du-lieu/`:

| mô-đun đỉnh | dự án | chặn | phải đọc |
|---|---|---|---|
| `blinky` | `fpga-sinhvien` | 0 | 1 |
| `soc_top` | `fpga-sinhvien` | 0 | 0 |
| `blinky` | `riscv-tn20k` | 0 | 4 |
| **`blinky`** | **`riscv-tn20k-b`** | **1** | 5 |
| `soc_top` | `riscv-tn20k-b` | 0 | 2 |
| `picorv32` | `fpga-sinhvien` | *(408 — xem dưới)* | 8 |

Dòng in đậm là một lỗi có thật, và nó đã đi tới bitstream:

* `blinky.v` khai cổng đỉnh **`sys_clk`**; tệp `.cst` khai **`clk_27m`**. Không dòng `IO_LOC`
  nào cho `sys_clk` — `grep` cả bảy tệp `.cst` trong repo cũng không ra.
* nextpnr vẫn chạy. `blinky_pnr.json` và **`blinky.fs` 4,6 MB** có mốc 01/10/2026 21:22.
* Trong tệp bố trí, `sys_clk_IBUF_I` nằm ở `NEXTPNR_BEL = X0Y6/IOBA`. Và `clk_27m` của
  `soc_top` — cổng **có** `IO_LOC "clk_27m" 4;` — cũng nằm ở `X0Y6/IOBA`.

Nghĩa là nextpnr đặt cái đồng hồ không ràng buộc ấy vào **đúng chân 4**, chân dao động 27 MHz
thật của bo. Bitstream ấy có thể đã chạy đúng. **Bằng may, không bằng ràng buộc** — ô vào đó
là ô vào được mạng đồng hồ, nên xác suất rơi đúng rất cao, và chính vì nó rơi đúng mà không ai
phát hiện ra suốt bảy ngày. Đây là hình dạng tệ nhất của một lỗi: nó không gây hậu quả lần này.

Không sửa `.cst` của hiện vật cũ — đó là dữ liệu của những lượt đo đã chốt. Ghi vào README §8.

### 408 "lỗi" của `picorv32` là lỗi của phép đo, không của sản phẩm

Bản dàn dựng đầu tiên của tôi ghép **mọi** tệp mạng cổng với **mọi** `.cst` của dự án, nên nó
ghép cả `picorv32.json` — mạng cổng của *lõi CPU tổng hợp riêng* để đếm ô, không bao giờ đem
đặt-đi dây (không có `picorv32_pnr.json`, không có `.fs`). 409 cổng của một lõi CPU thì tất
nhiên không cổng nào có `IO_LOC`, và tổng "409 blocker" của lượt chạy đầu **gần như toàn bộ**
đến từ một cặp vô nghĩa.

Tôi suýt ghi con số 409 ấy vào đây. Con số thật là **1** — đúng một chỗ, trên đúng một cặp mà
công cụ sẽ thật sự được gọi với. Cùng cái bẫy của DEV-344 (dàn dựng sai sinh ra kết luận sai
về sản phẩm) và của "lọc sai ra số đẹp": một phép lọc trả về số **hợp lý** thì tốn nhiều lượt
hơn một phép lọc trả về rỗng.

### Hai trong năm luật chưa có dữ liệu để nổ

Kế hoạch đòi năm loại phát hiện. Ba cái đầu — `thieu_rang_buoc` (blocker), `rang_buoc_thua`
(major), `trung_chan` (blocker) — chỉ cần `.cst` và mạng cổng, và cả ba đã nổ trên dữ liệu thật.

Hai cái sau cần Fact chân của kit. Tra lại **mọi** kho trong `du-lieu/` và `docs/`:

* **không kho nào** có Fact `pin:tangnano20k.*` (các Fact `pin:` đang có đều của
  `ATmega328P`, `AMS1117`…);
* **không kho nào** có khoá `vccio` hay chủ đề `bank.*`.

Nên `chan_lech_kit` và `io_type_lech_bank` **hôm nay chưa kết luận được gì trên dữ liệu thật**.
Chúng có ca kiểm, có đường dẫn Fact → luật đã nối và đã đo (`test_constraints_check_doc_Fact_chan_kit_tu_kho`),
nhưng dữ liệu để chúng nổ thì chưa ai nạp. Đúng hình dạng việc còn mở "luật ERC quá áp chưa nổ
trên dữ liệu thật". Ghi ra chứ không để một luật im lặng được đọc thành một luật đã kiểm.

Và vì thế `cst.kiem` trả thêm một phát hiện mức `info`: **`chua_co_fact_chan_kit`**. Không có
Fact thì nó **khai là đã bỏ** phần đối chiếu kit. Im lặng ở đó sẽ được đọc thành "đã kiểm chân,
không sao cả" — mà kết luận thật chỉ là "`.cst` khớp với cổng thiết kế", không nói chân 15 có
thật là LED0 trên bo hay không.

### Hai chỗ kế hoạch ghi mà mã không nhận

* **Mã lỗi.** Kế hoạch không ghi mã, tôi chọn `E4031` — rồi `grep` thấy `loop.py:1085` đã dùng
  `E4031` cho *"chưa chạy, vì chờ cổng"*. Hai chuyện khác nhau mang cùng một mã là một lời nói
  sai ở chỗ người đọc không kiểm lại được. Đổi sang **`E4033`** (E4030–E4032 đã có chủ). Đúng
  cái bẫy đã trúng ở M2-06 với `E6010`.
* **Khoá Fact.** Kế hoạch ghi Fact chân kit có khoá `chuc_nang`; mã đang ghi Fact chân bằng
  `ten`/`net`/`af` (xem `tools/knowledge.py`). Nhận cả ba, ưu tiên `chuc_nang` — vì một phép
  kiểm chỉ đọc đúng một tên khoá sẽ im lặng trên mọi Fact mà hệ thống này thật sự sinh ra.

### Phép so tên cố ý LỎNG

`led[0]` ↔ `LED0` phải khớp. Tên cổng do người viết RTL đặt, tên chức năng do tài liệu kit đặt,
và đòi hai bên giống hệt nhau là đòi một quy ước chưa ai thoả thuận. Nên `_cung_mot_ten` rút cả
hai về chữ–số rồi so chứa-nhau. Một phép so chặt sẽ báo lệch cho **mọi** thiết kế, và một cảnh
báo luôn luôn nổ thì bằng không có cảnh báo nào.

### `rang_buoc_thua` là `major`, không phải blocker

Đo trên `riscv-tn20k-b`: `.cst` của kit khai 11 chân, `soc_top` dùng 4 cổng (9 bit) — nên
`btn_s2` và `uart_rx` là ràng buộc thừa. Đó là hình dạng bình thường của *một tệp `.cst` cho cả
kit, dùng cho nhiều thiết kế*, và chặn nó lại là chặn sai. Nhưng cũng không im: một tên thừa
cũng có thể là **tên cổng viết sai chính tả**, và lúc ấy nó đi cặp với một `thieu_rang_buoc` —
đúng cặp `clk_27m` (thừa) + `sys_clk` (thiếu) của `blinky` ở trên.

### Phép phá: 18/20 ở lượt đầu

Tập 20 phép phá chọn theo *chỗ mã tháo được*, không theo *chỗ tôi biết đã có ca canh* — bài học
DEV-344. Hai chỗ LỌT, và cả hai cùng một hình dạng: nhánh **"không kiểm được"** của
`kiem_rang_buoc_chan` đổi thành "kiểm được, 0 cổng, 0 phát hiện" mà bộ kiểm vẫn xanh. Mà 0 cổng
thì **mọi** luật đều xanh — một ô xanh giả hoàn hảo, ngay trong công cụ đi tìm ô xanh giả.

Hai nhánh ấy nói hai chuyện khác nhau và phải có hai ca: *tệp không đọc được* (JSON hỏng) và
*tệp đọc được mà không có mô-đun đỉnh* (tên đỉnh gõ sai, hoặc RTL đã đổi tên). Cái thứ hai dễ
bỏ sót hơn vì nó không ném ngoại lệ nào cho ai nhìn thấy. Bù hai ca, phá lại: **20/20**.

Một lỗi nhỏ của chính phép đo, đáng ghi: ca đầu tôi viết dùng JSON hỏng, mà phép phá tôi viết
lại nhắm nhánh *thiếu mô-đun đỉnh* — hai cái không gặp nhau, nên ca mới xanh và phép phá vẫn
LỌT. Mất một lượt mới thấy. Một ca kiểm và một phép phá không trỏ vào cùng một dòng thì con số
"phá lại thì đỏ" nói về chỗ khác với chỗ người ta tưởng.

### Số đo

Bộ kiểm 1744 → **1773 xanh, 0 đỏ** (+29 ca: 21 trong `tests/test_cst.py` mới, 8 trong
`tests/test_hdl.py`). Trong đó **8 ca chạy trên hiện vật thật** — cả **7** tệp `.cst` trong repo
đọc hết, 0 dòng sai cú pháp. `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. **Phá lại thì đỏ: 20/20.**

Phép quét tệp `.cst` thật cũng phải sửa một lần: bản đầu chỉ quét `du-lieu/*/constraints/` và
`docs/*/constraints/`, và thu **4 trong 7** tệp — ba tệp còn lại nằm sâu hơn một bậc hoặc nằm
cạnh RTL. Ca kiểm vẫn xanh với 4 tệp, và câu "mọi tệp `.cst` thật đều đọc được" lúc ấy nói về
phần phép quét chạm tới, không về repo. Cùng hình dạng với chuyện "408 lỗi của `picorv32`": cả
hai lần, cái sai nằm ở phạm vi phép đo chứ không ở kết luận nó rút ra.

README: 128 → **129 công cụ** (120 bật mặc định, nhóm FPGA 6 → 7), §8 thêm mục về bitstream
`blinky` nói trên, và `hdl.constraints_check` đếm vào phần **chưa được Agent gọi lần nào** —
như `hdl.sensitivity` ở DEV-344, mã đã chạy trên hiện vật thật nhưng chưa lượt tác tử nào gọi.

---

## [DEV-346] [M4-01] `test.criteria` — tệp test do tác tử tự viết, và nó đang tự chấm điểm mình

Nhiệm vụ #17. **Công cụ mới** (`test.criteria`, R2, `core=False`), không cờ.

### Chỗ hổng: `test.run` đếm cái `dat` mà chính tệp test in ra

```python
kq.so_dat = sum(1 for x in kq.ca if x.get("dat") is True)
```

`sim.run` đã đi qua chỗ này từ lâu, và `build/tieu_chi.py` ghi sẵn lý do ở ngay dòng đầu:
*"Chương trình mô phỏng ĐO, EIDE PHÁN"*. Đường unit test thì chưa — nên **thứ đang bị kiểm
cũng là thứ tuyên bố kết quả**, và một dòng sửa trong `test/test_pid.c` đủ để mọi ca "đạt".

Và ở đây cái vòng ấy khép kín hơn ở mô phỏng: **tệp test là thứ tác tử tự viết.** Tác tử viết
mã sản phẩm, viết tệp test cho nó, rồi đọc kết quả do chính tệp test ấy in ra. Ở mô phỏng ít
nhất mô hình vật lý còn do người dựng.

### Ba chỗ sửa

**`chay_test(..., tieu_chi=None)`** — không có tiêu chí thì y như cũ, chỉ dán nhãn
`che_do="tu_khai"`. Có tiêu chí thì tệp test chỉ còn in **số đo** `{"do": {"T1": 300}}`, và
`_phan_theo_tieu_chi` gọi `tieu_chi.xet_ket_qua` **nguyên vẹn** — không viết lại phép so.
Nhờ thế một ngưỡng đọc ở tab mô phỏng và cùng ngưỡng ấy ở tab test luôn phán giống nhau; hai
bản sao của cùng một phép so thì sớm muộn lệch.

**Công cụ `test.criteria`** — lược đồ như `sim.criteria`, `trich_loi` là đường duy nhất để một
tiêu chí được coi là đã xác nhận. Phần kiểm assert tách thành `_kiem_assert` **dùng chung** với
`sim.criteria`, vì một bản sao thứ hai sẽ lệch, và lúc lệch thì hai loại tiêu chí nhận những
thứ khác nhau mà không ai nói ra.

**`test.run(..., ma_tieu_chi="")`** — bỏ trống là **còn được**, không phải lỗi. Mọi dự án đang
có đi đường ấy và ép tiêu chí ngay sẽ phá chúng; một công cụ phá việc cũ thì bị gỡ chứ không
được dùng. Nhưng lượt tự khai phải **tự nói ra** là tự khai.

### `ma` đi thẳng vào khoá hiện vật thì `test.criteria` xoá sổ tiêu chí của `sim.run`

Hai loại tiêu chí dùng chung không gian `criteria:*`. Kế hoạch ghi *"ghi hiện vật
`criteria:unit-<ma>`"*, và chỗ đáng nói là **vì sao** phải ép tiền tố thay vì nhờ tác tử gõ
đúng: một lần gọi `test.criteria(ma="sim-01")` sẽ ghi đè bảng tiêu chí mô phỏng mà người dùng
đã xác nhận, và `sim.run` sau đó phán theo ngưỡng của unit test — không lỗi nào kêu lên.
`_ma_tc_unit` ép tiền tố, và có một ca kiểm đi đúng đường ấy
(`test_test_criteria_khong_the_de_len_tieu_chi_cua_sim`).

### Bốn chỗ kế hoạch không nêu mà mã vẫn cần

* **E4023 cho đường unit test.** Kế hoạch chỉ nêu E4008/E4009/E4024. Nhưng cái bẫy DEV-336 đã
  bắt ở `sim.run` — *số đo không chứa MỘT mã assert nào của tiêu chí* — ở đây **dễ trúng hơn**:
  `nguon` bỏ trống thì lấy MỌI tệp `test/*.c`, nên thêm một bộ test thứ hai là lượt sau đem số
  đo của nó so với tiêu chí của bộ trước. Dùng lại đúng mã `E4023`: cùng một chuyện thì cùng
  một mã, một mã mới cho cùng một chuyện là bắt người đọc học hai lần.
* **E4024 phải từ chối TRƯỚC khi ghi kho.** Ghi rồi mới từ chối thì kho giữ lại một mục
  `che_do="eide_phan"` cho một lượt mà thật ra là tệp test tự khai. Lời từ chối đi tới tác tử
  và tắt theo lượt; **hiện vật thì ở lại**, và nó là thứ người đọc sở cứ sau này tin.
* **Thiếu số đo không được lùi về đếm `ca`.** Nếu lùi, chỉ cần bỏ khoá `do` đi là về lại chế độ
  tự chấm điểm — tiêu chí thành một tờ giấy dán tường: nó có, đã được xác nhận, và không phán
  gì cả. Mỗi assert không có số đo là một dòng *chưa đo được*, và cả lượt không đạt.
* **Tiêu chí 0 assert phải nói ra.** `xet_ket_qua` đã gọi đó là không đạt, nhưng ở đường unit
  test nó hiện ra y như *"test chạy xong, 0 ca"* — một kết quả rỗng vô hại.

### Chỗ NGƯỜI đọc con số, không phải chỗ tác tử đọc nó

`note_vi` đi tới tác tử; người dùng đọc **tab A8**. Và `test.run` ghi vào cùng loại hiện vật
`sim_result`, nên nó hiện ở đúng khối của `sim.run` — khối mà dòng "Kết luận" trước đây nói
**một câu duy nhất** cho mọi lượt:

> ĐẠT — theo đúng tiêu chí mà chương trình mô phỏng tự kiểm

Với một lượt `test.run` tự khai, câu ấy sai hai lần: nó không phải mô phỏng, và *"tự kiểm"*
chính là chỗ đáng không tin — mà câu lại đọc như một lời bảo đảm. Nay dòng ấy đi theo `che_do`,
và lượt tự khai có thêm một dòng **"Độ tin của con số này"** nói thẳng là ĐỎ cho một kết luận
nghiệm thu. Bảng tiêu chí cũng vậy: `criteria:unit-01` từng được gọi là *"Tiêu chí mô phỏng"*
và hứa *"mô phỏng sẽ không chạy tới khi anh duyệt bảng này"* — nói về một công cụ khác công cụ
mà bảng ấy thật sự chặn.

Đây đúng chỗ DEV-344 vừa sửa ở khối A8.0, lần này ở khối A8.1. Chế độ nằm ở `note_vi` thôi thì
chưa tới người đọc.

### Phép phá: 17/24 ở lượt đầu

Tập 24 phép phá dựng **từ `git diff`**, không từ ký ức. Bảy chỗ LỌT, và chúng gom lại thành
hai bài học:

* **Năm chỗ là những câu "nói ra" mà tôi viết rồi không canh:** `ma_tieu_chi` vào hiện vật,
  tiêu chí 0 assert, cổng E4023, E4024-ghi-kho-trước, và `_kiem_assert` bị nới. Mỗi cái là một
  dòng tôi viết *vì* nó quan trọng, rồi không viết ca cho nó — "quan trọng" không tự thành
  "được canh".
* **Hai chỗ là ca kiểm của tôi xanh nhờ một dòng KHÁC.** `test_tab_A8_noi_ra_con_so_la_TU_KHAI`
  kiểm `"TỰ KHAI" in str(kh)`, và nó vẫn xanh khi tôi phá chữ ấy ở dòng *Kết luận* — vì
  `summary` của khối cũng chứa nó. Phép phá bắt được, ca kiểm thì không. Siết lại thành
  `_cap(kh, "Kết luận")`: soi đúng một dòng, không soi cả khối.

Và một phép phá của tôi **vô hiệu**: `them = [] or [[…]]` — `[]` là giả nên biểu thức trả về
chính danh sách cũ, tức là không phá gì. Nó báo LỌT và tôi suýt đi viết một ca kiểm cho một
chỗ vốn đã được canh. Một phép phá không đổi hành vi thì nói sai y như một ca kiểm không đo gì.
Sửa thành `them = []` rồi mới đo lại được.

Bù bảy ca, phá lại: **24/24**.

### Số đo

Bộ kiểm 1773 → **1791 xanh, 0 đỏ** (+18 ca, `tests/test_test_tieu_chi.py` mới). Không ca cũ
nào phải nới: sáu ca `test.run` trong `test_xay_dung.py` đi đường không-tiêu-chí và giữ nguyên
hành vi. `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. **Phá lại thì đỏ: 24/24.**

README: 129 → **130 công cụ** (121 bật mặc định, nhóm "Viết mã" 8 → 9), và `test.criteria` đếm
vào phần **chưa được Agent gọi lần nào** — như hai công cụ của DEV-344/345.

---

## [DEV-347] [M4-02] Đường thứ hai tới một "đạt" — và hàng rào cũ chưa bao giờ nổ ngoài `sim-01`

Nhiệm vụ #18. **Sửa lỗi thuần** (đi vòng hàng rào N6/TC022) + một cờ mới
`SIM_RUNNER_GIOI_HAN`, mặc định TẮT.

### Hai lỗ, và lỗ thứ hai làm lỗ thứ nhất thành vô nghĩa

**Lỗ 1 — xoá bớt ca test.** `POL-N6-doi-tieu-chi` chặn đường ngắn nhất tới một "đạt" vô
nghĩa: đổi NGƯỠNG sau khi đã có kết quả. Nhưng đường thứ hai rộng hơn và không ai canh: tệp
test ba ca, một ca đỏ; ghi lại tệp còn một ca là "1/1 đạt". `fs.write` là một lời gọi bình
thường, `test.run` là một lời gọi bình thường, và không luật nào thấy gì lạ.

**Lỗ 2 — hàng rào cũ chưa bao giờ nổ ngoài `sim-01`.** `criteria.has_result` tra **cứng**:

```python
co_kq = ctx.store.get("sim_result:can-bang") is not None
```

Nên mọi bộ tiêu chí khác — `sim-ntc` của phiên robot, và từ M4-01 là cả `unit-*` — luôn được
coi là *"chưa có kết quả"*, tức `POL-N6-doi-tieu-chi` **im** cho chúng. Luật viết đúng từng
chữ; đường dẫn tới nó đứt. Đúng cái mẫu `kiem_cap_goi_tra()` đang mắc, lần này ở một luật đã
được viện dẫn như một hàng rào đang chạy.

### Bốn chỗ sửa

**`doi_tieu_chi`** nhận cả `test.criteria`, và `_co_ket_qua(ctx, ma)` tra các `sim_result` có
`canonical.ma_tieu_chi == ma` — con số mà M4-01 vừa bắt đầu ghi vào hiện vật. Hai chỗ cố ý
hẹp:

* **không** nhận "có `sim_result` nào đó là đủ": như thế thì thêm một bộ mô phỏng thứ hai sẽ
  khoá cổng cho **mọi** bộ tiêu chí, kể cả bộ chưa chạy lần nào — và hỏi ở đó dạy người dùng
  bấm duyệt theo phản xạ;
* **vẫn giữ** đường cũ cho `sim-01`, vì hiện vật `sim_result:can-bang` của mọi kho đã lưu
  trước M4-01 không khai `ma_tieu_chi`. Một phép tra chỉ nhận hiện vật mới sẽ nới hàng rào
  đúng ở những dự án đã chạy thật.

**Hook `sua_test_sau_do`** đếm "số chỗ canh" trước–sau (`"dat":` của khuôn JSON, `"ma":` của
khuôn số đo, `$display("FAIL` của testbench, `assert`) và phát `test.weakened` + `test.doi_gi`
= *"7 chỗ canh → 3 (test/test_pid.c)"*. Con số thứ hai mới là thứ thẻ cổng cần hiện — cùng lý
do `doi_tieu_chi` phải hiện "15.0 → 45.0" chứ không chỉ hiện "đổi ngưỡng".

Ba chỗ hook **cố ý im**, vì kêu ở đó là chặn đúng đường đi tới chỗ sửa thật: tệp sản phẩm
(sửa `firmware/pid.c` sau một kết quả đỏ là việc cần làm) · chưa có kết quả nào · tệp chưa
tồn tại (viết bộ test đầu tiên). Và một chỗ nữa: **số chỗ canh không đổi** — đổi tên ca, sửa
chữ, dọn mã. Phép đo là *"yếu đi bao nhiêu"*, không phải *"có sửa hay không"*.

**`POL-N6-sua-test`** — `ask`, `G-QUAL`, `never_auto`, N6, TC022. Và `POL-N6-doi-tieu-chi` +
`POL-QUAL-criteria-change` nay liệt cả `test.criteria`: hook cấp đúng dữ kiện là chưa đủ, nếu
không luật nào đọc thì `test.criteria` thành cửa sau cho đúng việc mà `sim.criteria` bị chặn.

**Cờ `sim_runner_gioi_han`** — bật thì `fs.write`/`fs.edit` của riêng `sim-runner` bị giới hạn
trong `sim/`. Nó là tác tử con *nêu tiêu chí và chạy đo*; cho nó ghi vào `test/` là cho đúng
cái tác tử đang bị đo quyền sửa thước đo của mình. Sau cờ vì nó **đổi tập việc** một tác tử
con làm được (N-4). Hàng rào chính thì **không** sau cờ: `POL-N6-sua-test` chặn cả tác tử
chính lẫn tác tử con, bằng một phép đo đếm được thay vì một lệnh cấm theo tên thư mục.

### Một luật trỏ tới nhóm dữ kiện chưa khai thì DỪNG CẢ LƯỢT, không phải "không nổ"

Thêm `POL-N6-sua-test` xong, `test_muc_tu_chu_thap_thi_ghi_phai_hoi` (ca cũ, tự dựng `pre`)
đỏ ngay:

```
ValueError: Điều kiện policy không tính được: 'test.weakened'
```

`_eval` cố ý ném cho điều kiện không tính được — im lặng cho qua thì tệ hơn. Nhưng hệ quả là:
`_env` có một danh sách *"nhóm nào phải luôn tồn tại"*, và nhóm `test` không có trong đó, nên
luật mới làm **mọi** `fs.write` đổ — kể cả khi hook im đúng cách. Một luật mới không chỉ có
thể "không nổ"; nó có thể biến một công cụ đang chạy tốt thành một lỗi hệ thống.

Mở danh sách ấy ra thì thấy **`criteria` cũng chưa bao giờ có trong đó**. Nó chưa nổ chỉ vì
hook `doi_tieu_chi` luôn cấp đủ ba khoá ở MỌI nhánh — tức là hàng rào đang dựa vào một thói
quen tốt của một hook, không dựa vào một bảo đảm. Thêm cả hai, kèm một ca kiểm chạy bốn công
cụ mà hai luật mới khớp tới.

### Phép phá: 22/27, và hai phép phá của tôi vô hiệu

Tập 27 phép phá dựng từ `git diff`. Năm chỗ LỌT:

* `_ma_tieu_chi` không ép tiền tố `unit-` — ca kiểm của tôi truyền `ma="unit-01"`, đã có sẵn
  tiền tố, nên nhánh ấy không chạy. Bù một ca truyền `ma="01"`.
* kêu cả khi số chỗ canh **không đổi** — ca của tôi đi 1 → 3, nên nhánh `n_moi == n_cu` trống.
* `_TEP_DO` bỏ nhánh `tb_*.v` / `*_tb.v` — ca của tôi để testbench ở `test/tb_dem.v`, khớp
  nhánh `test/` trước. Mà dự án FPGA thật đặt testbench **cạnh RTL**
  (`bai3/sim/tb_*.v`, `phien-bo-that-03-10/rtl/`), đúng chỗ phép lọc hẹp sẽ bỏ sót.
* `POL-N6-doi-tieu-chi` bỏ `test.criteria` — tôi có ca kiểm **hook** cho nó, không có ca kiểm
  **luật**. Hai tầng khác nhau, và chỉ tầng thứ hai mới dựng ra thẻ.

Chỗ thứ năm hoá ra **không phải lỗ hổng mà là phép phá vô hiệu** — hai lần liền ở cùng một
dòng:

1. `cu = cu or ""` thay cho `if cu is None: return im`. Với `cu = ""` thì `n_cu = 0`, nên
   `n_moi >= n_cu` luôn đúng và hook vẫn im. Không đổi hành vi.
2. Sửa thành "bỏ phép kiểm `is_file()`" — vẫn vô hiệu, vì `except OSError` ngay dưới đó bắt
   `FileNotFoundError`.

Phải bỏ **cả hai** lớp phòng mới phá được. Đây là lần thứ hai trong hai nhiệm vụ liền (M4-01
có `[] or [[…]]`), nên nó không phải tai nạn: một phép phá cũng cần được kiểm xem nó có thật
sự đổi hành vi — y như một ca kiểm cần được kiểm xem nó có thật sự đo gì.

Bù bốn ca, phá lại: **27/27**.

### Số đo

Bộ kiểm 1791 → **1816 xanh, 0 đỏ** (+25 ca, `tests/test_test_bi_sua_yeu.py` mới). Ca hồi quy
`test_doi_NGUONG_khi_da_co_ket_qua_thi_hook_bao_cho_cong_G_QUAL` và
`test_them_assert_MOI_cung_tinh_la_doi` giữ nguyên, không phải nới. `kiem_tai_lieu` 0 chỗ LỆCH
CHẮC CHẮN. **Phá lại thì đỏ: 27/27.**

Cờ tính năng 7 → **8**, cờ mới mặc định TẮT. Không công cụ mới, nên số công cụ giữ **130**.

---

## [DEV-348] [M4-05] Mutant không dịch được — và ba lỗi nữa trên cùng đường đo độ nhạy

Nhiệm vụ #19. **Sửa lỗi thuần** (ô xanh giả trong phép đo), không cờ. Nhiệm vụ nhỏ nhất của
đợt (P1 · S) và là nhiệm vụ tìm ra nhiều lỗi thật nhất — cả bốn chỉ lộ ra khi **chạy phép đo
trên dữ liệu thật**, không lộ ra khi đọc mã.

### Lỗi 1 — thứ nhiệm vụ này được giao: `False` có hai nghĩa

Vòng đột biến cũ kết luận bằng đúng một câu hỏi: *"phá rồi thì `chay` có trả `False` không?"*

```python
dat, _ = chay(p)
if not dat:
    thay_doi = True          # ⇐ "bộ kiểm BẮT ĐƯỢC"
```

Nhưng `False` nói hai chuyện khác hẳn nhau: **bộ kiểm chạy rồi có ca đỏ** (nó CÓ canh chỗ ấy),
hoặc **mã không dịch nổi** (chưa phép kiểm nào chạy). Gộp lại thì con số độ nhạy đẹp lên một
cách giả — và đẹp theo hướng tệ nhất: những phép phá **thô** nhất, loại làm hỏng cú pháp, là
loại dễ được tính là "bắt được" nhất, trong khi chúng không nói gì về việc bộ kiểm có đọc một
giá trị nào của tệp hay không.

Nay mutant không dịch được vào `so_mutant_khong_hop_le` và vòng đo **đi tiếp** sang phép sau
(`continue`, không `break`): một phép phá không dịch được chưa trả lời câu hỏi nào. Mọi phép
đều stillborn thì cả tệp là `chua_do_duoc` — không phải `khong_thay`, vì `khong_thay` là một
**cáo buộc** ("bộ kiểm không nhìn tệp này").

Dấu hiệu **không** được đọc từ nội dung log. `_DAU_HIEU_KHAC` có `"error:"`, và
`vi_sao_khong_dat` của một ca test hỏng thật rất dễ chứa chữ ấy — `"TC-01: error: mong 1 nhan
0"`. Một phép dò theo nội dung sẽ gọi mọi ca test hỏng như thế là "mutant không dịch được",
tức biến một phép đo *bắt được* thành *chưa đo được*: con số độ nhạy **tụt** xuống vì một lý
do sai. Nên hàm `chay` phải **khai** ra, bằng tiền tố `[BIEN_DICH] `.

### Lỗi 2 — `test.sensitivity` chưa bao giờ chạy nổi trên một tệp firmware THẬT

Chạy phép đo trên ba dự án firmware thật trong `du-lieu/` thì nó **đổ**:

```
IndexError: list index out of range     (dot_bien.py:98)
```

Chỗ giữ chuỗi/chú thích là `\x00{i}\x00` với `i` là số thứ tự. Phép đột biến đầu của bảng C là
`(?<![\w.])(\d{2,})(?![\w.])` → `99999`, và `\x00` **không** nằm trong `[\w.]` — nên từ chỗ giữ
thứ 11 (`\x0010\x00`) trở đi, chính con số của chỗ giữ bị đột biến thành `99999`, và bước phục
hồi `giu[99999]` ném `IndexError`.

Mọi tệp firmware thật đều có hơn 10 chú thích. Nghĩa là **đường đo độ nhạy cho C chưa bao giờ
chạy được trên một tệp thật**; mọi con số cũ đều đến từ tệp nhỏ do ca kiểm tự dựng. Một công
cụ đi vạch mặt ô xanh giả, và nó không chạy nổi trên sản phẩm. Mã chỗ giữ nay viết bằng **chữ
hoa** (`\x00AB\x00`) — không bảng phép nào chạm tới `[A-Z]+`.

### Lỗi 3 — `mo_phong` chạy lại tệp mô phỏng CŨ khi biên dịch đổ

Đo ngày 08/10/2026: sửa `dem.v` thành `q <= q + ;` (sai cú pháp) rồi gọi `mo_phong`:

```
dat = True · pass_fail = 'PASS' · ma_thoat = 0 · len(loi) = 1
```

`mo_phong` dựng `sim.vvp` rồi chạy nó, và nó chỉ hỏi `anh.exists()`. Tệp của lượt trước còn
nằm đó, nên lượt dịch **đổ** vẫn thấy "có tệp" và `vvp` chạy **bản cũ** — in ra `PASS` của một
mã khác mã trên đĩa.

Trên đường đo độ nhạy nó tệ hơn một bậc: mutant hỏng cú pháp được đọc thành *"testbench vẫn
xanh"*, tức **"bộ kiểm không canh chỗ này"** — một cáo buộc sai về sản phẩm, sinh ra từ một tệp
sót lại. Và tức là Lỗi 1 **không sửa được** nếu không sửa chỗ này trước: mutant stillborn ở
đường HDL không bao giờ trả `False` để mà phân loại.

`_don_tep_ra` đã có từ 01/10/2026 cho **đúng chuyện này** ở `nextpnr`, và docstring của nó ghi
sẵn bài học. `tong_hop`, `dat_di_day`, `dong_goi` đều gọi nó. Chỉ `mo_phong` là không — cơ chế
có sẵn, đường dẫn tới nó đứt ở đúng một chặng.

### Lỗi 4 — `loi_nguoi_doc` khen một chỗ trống

Nhánh cuối của `loi_nguoi_doc` chạy cho cả trường hợp `so_thay == 0`, nên nó in:

> Bộ kiểm nhìn thấy cả **0/1** tệp — phá tệp nào cũng có ca đỏ.

Một câu đọc như lời bảo đảm, cho một lượt đo chưa kết luận được gì. Nay `so_thay == 0` ra
**"CHƯA ĐO ĐƯỢC"** kèm lý do từng tệp, và nói thẳng *"con số độ nhạy ở đây KHÔNG phải 0 — nó
là chưa biết"*.

### Đo trên dữ liệu thật: một ô xanh giả, đã sửa

`du-lieu/rtos-sinhvien` (12 tệp sản phẩm, 1 tệp test), chạy **cả hai hành vi** trên cùng dữ
liệu:

| | `so_thay` | `logo_ptit.c` |
|---|---|---|
| **cũ** | **1** | `thay` — *"đổi mọi hằng số từ hai chữ số (1 chỗ) → bộ kiểm ĐỎ"* |
| **mới** | **0** | `chua_do_duoc` — *"mọi đột biến đều làm hỏng biên dịch (1 phép)"* |

Con số cũ là **1/5 bắt được**; sự thật là **0 tệp đo được**. Phần còn lại của dự án ấy cũng
đáng ghi: 4 tệp font `khong_thay`, `control_rtos.c` trùng ký hiệu (tệp test tự định nghĩa lại
hàm sản phẩm), `main.c` không dịch được trên máy chủ. Hai dự án firmware thật còn lại
(`stm32f469-freertos`, `thu-nghiem-g6`) có **bộ kiểm đỏ sẵn**, nên không đo được gì.

Và **kiểm lại DEV-344**: đo lại bài 3 sau khi sửa cả bốn lỗi — `tb_pcpi_dot4` **1/1**,
`tb_pcpi_mac` **1/1**, `stillborn = 0`. Con số của DEV-344 **đứng**: phép *"đảo điều kiện if"*
dịch được, và testbench đỏ vì hành vi đổi, không vì mã hỏng. Nó đứng do may: Lỗi 3 chỉ nổ khi
mutant làm hỏng cú pháp, mà năm phép của `PHEP_VERILOG` cố ý đều hợp lệ về cú pháp.

### Phép phá: 15/20, và luật nằm trong hai closure không ai gọi tới được

Năm chỗ LỌT, và bốn trong số đó cùng một hình dạng: **luật đúng, nằm ở chỗ ca kiểm không với
tới**.

* Luật *"chỉ gắn tiền tố khi có lỗi biên dịch"* nằm trong **hai closure** — `_chay` của
  `test.sensitivity` và `chay` của `hdl.sensitivity`. Hai phép phá nhắm đúng chỗ ấy đều LỌT.
  Gom về `dot_bien.ket_qua_chay`: một chỗ quyết định, và đo được — kể cả ca *"quá hạn thì
  KHÔNG phải stillborn"*, thứ không ca nào với tới khi nó còn nằm trong closure.
* Nhánh gắn tiền tố của `do_do_nhay_hdl` **không dựng nổi ca kiểm qua bảng mặc định**: năm
  phép `PHEP_VERILOG` cố ý đều hợp lệ về cú pháp. Mở tham số `bang` để ca kiểm bơm một bảng
  một phép làm hỏng cú pháp vào **đúng đường thật** — cùng hàm, cùng `mo_phong`, cùng `chay`;
  chỉ cái bảng là của ca kiểm.
* Ba chỗ báo lại của công cụ `hdl.sensitivity` (kết quả · kho · `note_vi`) LỌT vì **mọi ca
  kiểm cũ của nó đều đi qua một lượt đo có `stillborn == 0`**. Đây là tầng báo lại, và nó hỏng
  theo kiểu riêng: phép đo đúng, con số đúng, rồi con số không đi tới đâu.

Bù tám ca, phá lại: **22/22**. Và tập phép phá lần này **tự kiểm**: script so byte trước–sau
mỗi phép và in `[VÔ HIỆU]` nếu không đổi gì — sau ba phép vô hiệu báo LỌT oan ở M4-01/M4-02.

### Số đo

Bộ kiểm 1816 → **1835 xanh, 0 đỏ** (+19 ca trong `tests/test_dot_bien.py`). `kiem_tai_lieu` 0
chỗ LỆCH CHẮC CHẮN. **Phá lại thì đỏ: 22/22.** Không công cụ mới, không cờ mới: **130 công
cụ**, **8 cờ**.

---

## [DEV-349] [M4-19] Đột biến trên bản sao — và hai lần tôi tự tay làm phép đo cáo buộc sai

Nhiệm vụ #20. **Sửa lỗi thuần** (nguy cơ mất/hỏng dữ liệu), không cờ. P2 · S.

### Chỗ hổng: phép đo ghi vào chính tệp của dự án

```python
try:
    p.write_text(moi_ma, "utf-8")      # ⇐ tệp SẢN PHẨM của người dùng
    dat, log = chay(p)
finally:
    p.write_text(goc, "utf-8")
```

`finally` chỉ đỡ được ngoại lệ Python. Một `Ctrl-C`, một lần máy mất điện, một `kill -9` giữa
vòng đo — và tệp sản phẩm nằm lại ở trạng thái **đã bị phá**, trong một dự án mà người dùng
tưởng là nguyên vẹn. Phép đo tự tay làm hỏng thứ nó đi đo.

Và nó không phải rủi ro trên giấy: suốt M4-05 tôi phải sao `du-lieu/` ra thư mục tạm **trước
mỗi lượt đo thật**, chỉ vì chuyện này. Một phép đo mà người dùng nó phải tự phòng bị là một
phép đo chưa xong.

Nay `do_do_nhay(..., thu_muc_tam=…)` sao từng tệp ra `thu_muc_tam/<thứ tự>/<tên>`, đột biến
**bản sao**, và tệp gốc chỉ được ĐỌC. Thư mục con theo thứ tự vì `bai1/dem.c` và `bai2/dem.c`
cùng tên: gộp chúng một chỗ thì lượt đo của tệp sau ghi lên bản sao của tệp trước, và vì vòng
đo trả tệp về trong `finally`, cái hỏng hiện ra thành một **kết luận sai** về một trong hai
tệp, không thành một lỗi ai thấy.

### Điều kiện dùng được, và vì sao `hdl.sensitivity` KHÔNG dùng

`thu_muc_tam` chỉ đúng khi hàm `chay` **thật sự đọc đường dẫn nó nhận**. `chay` của
`hdl.sensitivity` thì không: nó bỏ qua đối số và gọi `mo_phong` dịch lại **cả thư mục nguồn**.
Bật `thu_muc_tam` ở đó là phá bản sao mà biên dịch bản gốc — mọi mutant đều "không đổi gì", và
**mọi** tệp RTL bị kết luận là *bộ kiểm không canh tới*. Một cáo buộc sai với từng tệp, và lượt
đo vẫn xanh trơn. Đường cũ giữ nguyên cho nó, và điều kiện ấy ghi thẳng vào docstring.

### Hai lần tôi tự tay làm phép đo cáo buộc sai — cả hai lộ ra trên dữ liệu thật

**Lần 1 — `-I` cho cả lượt mốc.** Bản đầu của tôi gắn đường tìm header cho mọi lượt chạy. Chạy
trên ba dự án firmware thật thì **cả ba** thành *"không đo được"*: mốc của `rtos-sinhvien` đổi
từ XANH sang ĐỎ. Lượt mốc phải chạy bộ kiểm **y như tác tử vẫn chạy nó**; thêm một cờ biên dịch
vào đó là đổi chính cái mốc mà mọi so sánh sau này dựa vào.

**Lần 2 — và đây là cái đắt hơn: `-I` thay vì `-iquote`.** Sửa xong lần 1, mốc xanh lại, nhưng
**11 trong 12** tệp của `rtos-sinhvien` bị xếp là `khong_nap_duoc` — *"mã sản phẩm không dịch
được trên máy chủ (thiếu header của bo)"*. Mở log biên dịch ra:

```
test_rtos.c:180:5: error: use of undeclared identifier 'FILE'
    FILE *fbin = fopen(".eide/build/mach.bin", "rb");
```

`du-lieu/rtos-sinhvien/firmware/` có **`stdio.h` riêng** — chuyện thường của mã bare-metal. `-I`
đổi đường tìm cho cả `#include <...>`, nên `#include <stdio.h>` của tệp test khớp vào bản giả
của bo. Tôi thêm một cờ để tránh một cáo buộc sai, và nó sinh ra mười một cáo buộc sai khác.

`-iquote` chỉ đổi đường cho `#include "..."` — đúng và chỉ đúng phần mà bản sao làm đứt. Và sau
khi đổi sang nó, cái guard của lần 1 (*chỉ gắn cờ cho lượt có tệp sản phẩm*) trở thành **không
đổi hành vi**: `-iquote` không chạm `<...>`, và thư mục của tệp đang dịch vẫn được tìm trước.
Nên tôi **bỏ** nhánh ấy — một nhánh `if` không đổi hành vi là một nhánh không ca kiểm nào canh
được, và phép phá đã chỉ ra đúng điều đó.

### Đo trên dữ liệu thật: cùng kết luận, và không chạm một byte nào

Chạy `test.sensitivity` **tại chỗ** trên ba dự án trong `du-lieu/` — không sao ra đâu cả, đó
chính là điều cần chứng minh:

| | M4-05 (đột biến tại chỗ) | M4-19 (trên bản sao) |
|---|---|---|
| `rtos-sinhvien` | thay 0 · không_thay 4 · không_nạp 3 · chưa_đo 5 · stillborn 1 | **giống hệt** |
| `stm32f469-freertos` | mốc ĐỎ | mốc ĐỎ |
| `thu-nghiem-g6` | mốc ĐỎ | mốc ĐỎ |

Và phép đo quan trọng nhất của nhiệm vụ: **50 trong 50** tệp firmware thật của ba dự án có
`sha256` **và** `st_mtime_ns` không đổi một byte nào sau lượt đo. mtime đáng kể riêng: nó là thứ
`make` đọc, nên một phép đo ghi lại y nguyên nội dung vẫn làm cả cây dựng lại.

Thư mục bản sao dọn hai bậc: `do_do_nhay` dọn thư mục nó được **giao**, còn vỏ `.eide/mutate`
là của công cụ nên công cụ dọn. Thiếu bậc thứ hai thì mỗi `run_id` để lại một thư mục rỗng
trong dự án của người dùng.

### Phép phá: 7/13, và sáu chỗ LỌT nói sáu chuyện khác nhau

Năm chỗ cần ca kiểm mới, và chúng chia đúng theo chỗ tôi đã nghĩ "cái này hiển nhiên":

* bản sao mang **nội dung** tệp gốc — bản sao rỗng thì bước nạp dịch một tệp rỗng, luôn trót
  lọt, và kết luận mạnh nhất của phép đo (`khong_nap_duoc`) biến mất;
* hai tệp **cùng tên** khác thư mục có hai bản sao riêng;
* bản sao của tệp **trước** đã bị dọn khi đang đo tệp **sau** — phép dọn ở cuối không thay được
  phép dọn từng bước, vì cái ở cuối chỉ chạy khi có cái cuối;
* `-iquote` **không che** header hệ thống — dựng lại đúng cảnh của `rtos-sinhvien`: một
  `stdio.h` giả trong thư mục firmware;
* thư mục tạm **lồng theo `run_id`** — kiểm ở tầng công cụ bằng cách bắt đối số, vì chuyện hai
  lượt song song không dựng được trong một ca đơn vị.

Chỗ thứ sáu không phải lỗ hổng mà là **nhánh đã thành vô nghĩa** sau khi đổi sang `-iquote` —
đã bỏ nhánh, không viết ca cho nó.

Một phép phá của tôi cũng viết sai: `[ ? ] KHÔNG tìm thấy chỗ phá` — tôi dán nguyên đoạn mã từ
bản *trước* khi tách hàm `_do_mot_tep`, nên thụt lề lệch bốn dấu cách. Khuôn script in ra `[?]`
thay vì im lặng bỏ qua, nên nó không lẫn vào đâu được. Bù năm ca, phá lại: **13/13**.

### Số đo

Bộ kiểm 1835 → **1846 xanh, 0 đỏ** (+11 ca). `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. **Phá lại
thì đỏ: 13/13.** Không công cụ mới, không cờ mới: **130 công cụ**, **8 cờ**.

---

## [DEV-350] [M4-04] Điểm đột biến — và phép đo mới treo 10 phút trên tệp thật đầu tiên

Nhiệm vụ #21. **Công cụ mới** (tham số `muc` cho `test.sensitivity`, mặc định giữ hành vi cũ),
không cờ. Tiền đề M4-05 và M4-19 đã xong — và đó là lý do nhiệm vụ này làm được: con số chỉ
đáng tin khi mutant hỏng biên dịch không được tính (M4-05) và phép đo không ghi vào tệp người
dùng (M4-19).

### Chỗ hổng: `re.subn` gộp mọi chỗ khớp thành MỘT đột biến

Chế độ cũ trả đúng một câu cho mỗi tệp: *"bộ kiểm có thấy tệp này không?"* — đủ để lật tẩy một
ô xanh giả, không đủ để làm gì tiếp. Một tệp 400 dòng mà bộ kiểm chỉ canh **một** hằng số vẫn
ra `thay` ("bộ kiểm BẮT ĐƯỢC"), y như một tệp được canh từng dòng. Vì `dot_bien_van_ban` dùng
`re.subn`, "đảo mọi phép `==` trong tệp" là một đột biến duy nhất, và canh được một trong mười
chỗ là đủ.

Nay `liet_ke_dot_bien` + `ap_mot` tách từng vị trí, và `muc="chi_tiet"` trả `diem`,
`so_mutant`, `so_bat`, `so_stillborn`, kèm `song` — **danh sách dòng bộ kiểm không canh**.
Danh sách đáng hơn con số: một điểm 0,62 không nói đi sửa chỗ nào.

Năm phép thêm, đặt ở **cuối** bảng (bốn phép cũ được gọi theo chỉ số ở nhiều ca kiểm, và chế
độ theo tệp chỉ dùng `toi_da_phep=3` phép đầu — nên thêm vào cuối thì cả hai chuyện ấy không
đổi một ly): hằng hex → `0x0` · `&&` → `||` · `>=` → `>` · `return <biểu thức>;` →
`return 0;` · xoá một lời gọi hàm đứng riêng.

### Tiêu chí xong của kế hoạch: tái hiện ca DANH-GIA §2.2, và nó ĐẠT

Hôm ấy Agent **tự khai** *"2 trong 4 ca bộ kiểm không bắt được"* kèm dự đoán *"nạp lên bo thật
sẽ nổ HardFault ngay chu kỳ đầu"*; người kiểm lại bằng tay — đổi `0xFFFFFFFD` thành `0`, dịch
lại, cả 4 ca vẫn xanh. Rồi bo nổ đúng `IBUSERR` ở đúng chỗ ấy.

Đo lại bằng máy trên hiện vật thật (`du-lieu/rtos-sinhvien/firmware/control_rtos.c`):

| câu hỏi | trả lời đo được |
|---|---|
| bảng phép **cũ** có đột biến nào cho hằng hex? | **0** — `(?<![\w.])(\d{2,})(?![\w.])` bị chặn bởi chữ `x`, nên phép đo cũ *về mặt cấu trúc* không thể thấy chỗ này |
| bảng **mới** có, ở dòng nào? | dòng **147**: `*(--sp) = 0xFFFFFFFDU;` → `0x0U` |
| áp vào rồi chạy bộ kiểm thật? | **XANH** — mutant **SỐNG** |

Điểm mù mà hôm ấy chỉ tồn tại vì Agent tự khai và một người ngồi sửa tay, nay **đo được bằng
máy**. Thành một ca kiểm thường trực, chạy trên chính hiện vật ấy.

### Phép đo mới TREO 10 phút trên tệp thật đầu tiên

Lượt chạy `muc="chi_tiet"` đầu tiên trên `du-lieu/rtos-sinhvien` không xong trong 10 phút và
bị tôi giết. Không đổ, không báo gì — nó trông như một lượt chạy lâu.

Đo ra nguyên nhân:

```
logo_ptit.c: 720 311 ký tự, 7 209 dòng
  phép 4 (đổi hằng hex thành 0x0): 57 600 chỗ khớp
```

`liet_ke_dot_bien` bản đầu dựng **cả tệp** cho **mỗi** chỗ khớp — một bản 720 KB cộng một lượt
regex bỏ che, 57 600 lần: khoảng **41 GB** việc chuỗi. Và một lượt `chay_test` của dự án ấy chỉ
mất **0,6 s**, nên chi phí không nằm ở biên dịch mà nằm ở chính phần liệt kê.

Nay chỗ khớp được liệt kê **rẻ** (chỉ vị trí), lấy mẫu **trước**, rồi mới dựng chi tiết cho
những mục còn lại; số dòng tra qua một **bản đồ đoạn** chứ không qua phép so hai bản — cần bản
đồ vì một chú thích `/* … */` ba dòng co lại thành một chỗ giữ không có dòng mới nào, nên toạ
độ bản đã che không trùng toạ độ mã gốc. Đo lại: **0,04 s** cho tệp 150 KB, so với **≈ 21 s**
của bản chậm.

Ca kiểm chi phí của tôi cũng phải sửa một lần: bản đầu dùng hằng hex **trần**, và nó KHÔNG bắt
được bản chậm — `_bo_che` trả về ngay khi không có chỗ giữ nào. Chính các **chú thích mỗi dòng**
mới làm mỗi lượt bỏ che thành một lượt regex thật, và đó đúng là hình dạng của tệp thật.

### Chạy chi_tiet trên 12 tệp thật: 110 s, và một con số đúng mà vô dụng

```
muc=chi_tiet · 110 s · điểm=0,0 · mutant=180 bắt=0 stillborn=0
  font12/16/20/24/8.c, logo_ptit.c → mỗi tệp "bắt 0/30 đột biến"
```

Điểm 0,0 là **đúng**: đây là sáu tệp bitmap, không bộ kiểm nào đọc chúng. Nhưng nó cũng là một
con số không dùng được, và nó chỉ ra chỗ thật: tệp duy nhất đáng đo của dự án ấy —
`control_rtos.c` — là `khong_nap_duoc`, vì tệp test `#include` chính tệp `.c` đó nên nạp nó
thành đơn vị dịch thứ hai là trùng ký hiệu. **Phép đo DANH-GIA §2.2 ở trên phải đi đường
riêng, không qua công cụ.** Đây là lần thứ ba việc còn mở *"`chay(None)` chỉ dịch tệp test"*
chặn đúng chỗ cần đo (M4-01, M4-19, nay M4-04).

Một chỗ tiến bộ đáng ghi: `font8.c` ở chế độ tệp là `chua_do_duoc` (*"không có chỗ nào để đột
biến"*) — bảng cũ không chạm được nó. Chế độ chi tiết có **30** đột biến cho nó, nhờ phép hằng
hex. Bảng mới thấy những tệp bảng cũ không chạm tới.

### Hai luật của dự án bắt được chuyện tôi làm sai

**N8 không có ngoại lệ.** Cho `test.sensitivity` ghi hiện vật (kế hoạch đòi) thì sổ công cụ đổ
ngay: *"ghi hiện vật nhưng không đòi explain — trái N8"*. Tôi nhận luật: thêm `explain` vào
lược đồ và sửa bốn lời gọi trong ca kiểm. Vẫn R1, vẫn không khoá — *"rẻ tới mức gọi được
ngay"* là chuyện mức rủi ro và cửa duyệt, không phải chuyện một trường giải thích. Và một hiện
vật mang lời giải thích do **chính công cụ** sinh ra thì đúng là "lời tự khai mặc áo phép đo"
mà DEV-346 vừa đi chữa.

**Plan mode khoá công cụ ghi, lấy từ hợp đồng chứ không từ danh sách tên.** Nên vừa khai
`writes_artefact` là `test.sensitivity` bị khoá, và ca kiểm cũ đỏ đúng chỗ. Cách giải không
phải nới luật chung mà là dùng cơ chế đã có: `KHONG_KHOA`, cùng lý do với `memory.note` —
khoá một phép **đo** trong lúc soạn kế hoạch là cấm tác tử biết bộ kiểm hiện tại canh được
những gì, đúng thứ nó cần để soạn một kế hoạch sửa. Kèm một ca canh chính chỗ miễn ấy, và canh
rằng luật chung **không** bị nới cho mọi công cụ R1 khác.

### Phép phá: 15/22, rồi 21/22, rồi 22/22

Bảy chỗ LỌT ở lượt đầu. Năm cần ca kiểm mới: phép `return` · bỏ mục đột biến không đổi gì ·
`muc` lạ phải ném lỗi · công cụ truyền `muc` xuống · công cụ ghi hiện vật. Một chỗ là **bước
sắp xếp trước khi lấy mẫu** — nó không đổi gì đo được (tính tất định đến từ `seed`), nên tôi
**bỏ dòng** thay vì dựng một ca contrived, đúng bài học M4-19. Chỗ cuối là bước sắp xếp **sau**
khi lấy mẫu: nó có đổi thứ đo được (danh sách theo thứ tự trong tệp, để người đọc không phải
nhảy ngược xuôi), nên thêm một phép kiểm thứ tự.

### Số đo

Bộ kiểm 1846 → **1862 xanh, 0 đỏ** (+16 ca). `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. **Phá lại
thì đỏ: 22/22.** Không công cụ mới, không cờ mới: **130 công cụ**, **8 cờ**. Hiện vật mới:
`sim_result:test-sensitivity`.

---

## [DEV-351] [M4-06] Vòng tự nâng bộ kiểm — và phần *Evaluator* do MÃ làm, không do mô hình

Nhiệm vụ #22. **Đổi hành vi**, sau cờ `TEST_HARDEN` (mặc định TẮT) — trừ một phần sửa lỗi
thuần luôn chạy. Tiền đề M4-04 và M4-05 đã xong.

### Chỗ hổng: một lời dặn trong mô tả công cụ không phải một cơ chế

Mô tả `test.sensitivity` dặn *"Gọi nó SAU khi test.run xanh, trước khi nói với người dùng rằng
đã kiểm xong"*. Câu ấy đúng, và không ai ép: `grep sensitivity` trong `hooks/` và `loop.py` ra
**rỗng**. Nên suốt bao nhiêu phiên, `test.run` xanh rồi tác tử báo "đã kiểm xong", và không
lượt nào đi đo xem bộ kiểm ấy canh được gì.

**Phần luôn chạy, không cần cờ:** hiện vật đo nay khai `deps.upstream` gồm tệp test **và** tệp
sản phẩm. Thiếu nó thì sửa một trong hai rồi con số cũ **nằm đó như còn đúng** — và một con số
đã lỗi thời mà không ai đánh dấu thì tệ hơn không có con số: nó dừng việc đo lại.

**Phần sau cờ:** Stop hook `test_xanh_chua_do_nhay` nhắc khi test xanh mà chưa ai đo, **và mở
khoá** `test.sensitivity` — nửa thứ hai bắt buộc, vì công cụ ấy là `core=False` nên tác tử chỉ
thấy nó sau `tool.search`. Đo được ở hook `kiem_viec_chua_ai_kiem` trên phiên FreeRTOS: hook nổ
hai lượt liền và tác tử **không gọi lần nào**. Bảo ai đó dùng một thứ họ không nhìn thấy thì
không phải là bảo.

### So PHIÊN BẢN, không so đồng hồ

Bản đầu của hook so `updated_at` giữa hiện vật test và hiện vật đo. Ca kiểm đầu tiên của chính
hook ấy đỏ ngay: `updated_at` có độ phân giải thô, nên hai lần ghi trong cùng một giây **bằng
nhau**, và phép so "mới hơn" im lặng sai.

Nay `test.sensitivity` ghi kèm `version_test` — số phiên bản của `sim_result:unit-test` tại lúc
đo — và hook so con số ấy. Một số phiên bản là dữ kiện chính xác; một cái đồng hồ thì không.
Nhờ thế hook cũng trả lời đúng câu *"test đã chạy lại sau lần đo chưa"*, thay vì chỉ trả lời
được *"đã có hiện vật đo chưa"* — mà câu sau thì một lần đo duy nhất ở đầu dự án khoá hook im
mãi mãi.

### `test.harden`: phần Evaluator do MÃ làm

Vòng tự nâng nào nhận mọi ca do mô hình viết cũng sẽ sinh ra đúng thứ cả mảng này đi chữa: **ca
xanh mãi mãi**. Và ở đây mô hình có động cơ rõ ràng — việc nó được giao là *"làm cho mutant
chết"*, mà chép giá trị trong mã sản phẩm sang ca kiểm là đường ngắn nhất tới một ô xanh.

Nên phép nhận ca **không hỏi mô hình**: EIDE chạy bộ kiểm **hai lần** — XANH trên mã thật, ĐỎ
trên mutant — và chỉ nhận khi cả hai đúng. Thiếu một chiều là loại, và **ca bị loại được trả
lại**: một ca xanh mãi mãi ở lại trong `test/` còn tệ hơn không thêm gì.

Đòi cả hai chiều chứ không chỉ chiều "đỏ trên mutant": chỉ đòi chiều ấy là nhận cả những ca đỏ
sẵn, bộ kiểm thành đỏ vĩnh viễn, và lượt sau `do_do_nhay` trả ngay *"bộ kiểm đang ĐỎ từ trước
khi đột biến"* — vòng tự nâng **tự khoá chính nó** bằng một ca nó vừa nhận.

Hai trần, độc lập nhau: `max_vong` chặn theo số mutant, `toi_da_goi` chặn theo **tiền mô hình**.
Cần cả hai vì một mutant có thể tốn nhiều lượt gọi (tác tử con có `toi_da_goi=8` riêng), nên ba
mutant "trong trần vòng" vẫn có thể là hai mươi lượt mô hình.

Tác tử con `test-writer` chỉ có `fs.read`/`fs.glob`/`fs.grep`/`fs.write`/`test.run`/`store.get`
— **không** `fs.edit`, **không** `build.compile`, **không** công cụ chạm bo. Tệ hơn `sim-runner`
ở M4-02 một bậc nếu cho nó quyền sửa mã sản phẩm: ở đó mới là *khả năng*, ở đây là *động cơ*.

### Hai ràng buộc thật mà hai hàng rào có sẵn chỉ ra

**Một dự án chỉ có MỘT tệp test.** Bản đầu bảo `test-writer` ghi `test/t_harden_0.c`, và ca mới
bị loại với lý do *"ĐỎ ngay trên mã thật"* — vì `chay_test` dịch **mọi** tệp trong `test/` cùng
nhau, nên một tệp thứ hai có `main()` làm trình liên kết báo trùng ký hiệu. Kiểm lại trên dữ
liệu thật: cả bốn dự án có `test/` đều đúng **một** tệp. Nay lời giao việc bảo thêm ca **vào
chính tệp đang có**, và phép dò "có ca mới chưa" đọc **nội dung** chứ không đọc danh sách tệp.

**`fs.write` không ghi đè tệp chưa đọc (E4020).** Kịch bản đầu của tôi cho `test-writer` gọi
thẳng `fs.write`, và nó bị từ chối — đúng luật, có từ 30/09/2026. Lời giao việc nay nói ra hợp
đồng ấy, và ca kiểm đi đúng đường thật: `fs.read` rồi mới `fs.write`.

### Bộ dò tài liệu tự khai một việc nó không làm

`_tat_ca_cong_cu` có docstring *"Kể cả công cụ nằm sau CỜ TÍNH NĂNG"*, nhưng nó bật đúng **một**
cờ theo tên: `EIDE_FEATURE_SCHEMATIC`. Thêm `test.harden` là nó báo một công cụ **có thật**
thành "không tồn tại" — đúng cái báo động sai mà docstring ấy nói là phải tránh. Nay nó lấy
danh sách từ `Features.ten_co()` và bật hết, đúng mẫu `cong_cu_bi_khoa` đã chọn: lấy từ hợp
đồng, không từ một tên gõ cứng.

Hai ca kiểm `sch` cũng phải siết: chúng đòi `bo_qua_vi_co` **chỉ** chứa `sch.*`, đúng khi
`schematic` là cờ duy nhất gate công cụ và nói quá khi có hai. Nay chúng đòi *mọi `sch.*` nằm
trong danh sách bị bỏ*, không đòi ngược lại.

### Số đo, và một tiêu chí CHƯA đạt

Bộ kiểm 1862 → **1878 xanh, 0 đỏ** (+16 ca). `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. **Phá lại
thì đỏ: 22/22** (lượt đầu 18/22). Cờ 8 → **9** · tác tử con 7 → **8** · công cụ **131** khi bật
hết cờ (121 bật mặc định; mặc định không đổi).

Đo "trước" trên dự án thật `du-lieu/rtos-sinhvien`, tệp `logo_ptit.c`: **điểm 0,0** · 30 mutant
· 20 sống · 18 s.

**Tiêu chí *"mutation score tăng sau harden"* CHƯA đạt, và tôi không nhận nó.** Hai lý do, cả
hai đo được:

* Chạy `test.harden` thật cần **lời gọi mô hình**, và §3.0 của kế hoạch bắt hỏi người dùng
  trước khi tiêu tiền mô hình. Tôi chưa hỏi.
* Kể cả có hỏi, dự án ấy **không có chỗ để đo**: tệp duy nhất đáng nâng là `control_rtos.c`, và
  nó là `khong_nap_duoc` vì tệp test `#include` chính tệp `.c` đó (DEV-350). Sáu tệp còn lại là
  bitmap — không ca kiểm nào "giết" được một đột biến một byte trong logo, và đem chúng đi nhờ
  viết ca là tiêu tiền mô hình để lấy về số không.

Nên cờ `TEST_HARDEN` giữ **TẮT**, và tiêu chí ấy để mở trong kế hoạch. Bật mặc định còn cần bộ
76 ca chạy hai chế độ — cũng phải hỏi trước.

---

## [DEV-352] [M4-07] Verifier nhận gói bằng chứng do MÃ dựng — và một cờ thứ mười vô hình

Nhiệm vụ #23. **Đổi hành vi**, sau cờ `VERIFIER_GOI_BANG_CHUNG` (mặc định TẮT) — trừ một phần
sửa lỗi thuần luôn chạy (`Features.ten_co()`). Không tiền đề.

### Chỗ hổng: một trường trong hợp đồng mà không dòng nào đọc

`DinhNghia.doc_duoc_viec: bool = True` có trong `subagent.py` từ G6, và `verifier` khai
`doc_duoc_viec=False` kèm một đoạn docstring nói rõ vì sao: *"Cho nó đọc đề bài là mời nó suy
ra kết luận mong đợi rồi đi tìm cách biện minh"*. Trường ấy **chưa bao giờ được đọc**. `SA.chay`
nhận `viec` rồi gửi nguyên văn, nên trên đường `task.run(subagent="verifier")` — đường mà tác tử
chính tự gọi — verifier đọc đúng thứ tác tử chính muốn nó đọc.

Đây lần thứ bảy đúng một hình dạng trong đợt này: **cơ chế có sẵn, đường dẫn tới nó đứt.**

Đo trên sổ cái 42 dự án thật: **327 lời gọi `task.run` có `viec`, 323 trong số đó là verifier.**
Không phải một đường lý thuyết — nó là đường chính của cả lớp kiểm chứng. Và **209/323 đề bài
dài hơn 300 ký tự**, nhiều đề bài nói sẵn đáp án: *"hiện vật build:firmware … kết quả
'dat: false'"*, *"đối chiếu với hdl.bitstream (dat=true, chip GW2A)"*.

### Hai nửa, và chỉ một nửa làm việc

`goi_bang_chung_tu_so_cai(ledger, store, history)` dựng đầu vào từ sổ cái và kho, ba khối:

* **A** — changeset kể từ lần verifier gần nhất, dùng **đúng mốc** mà
  `kiem_chung.co_viec_chua_kiem` dùng. Lệch mốc thì hook nói "còn việc chưa kiểm" trong khi gói
  lại kể một đợt việc khác.
* **B** — hiện vật bị chạm, **đọc lại từ kho**: phiên bản, cờ STALE, và `dat` nếu có.
* **C** — kết quả `build`/`sim_result`/`target` gần nhất. Lấy theo **loại**, không theo tên, nên
  một công cụ đo thêm sau này tự có mặt.

Dựng được trên **29/42 dự án thật**, 0 lần đổ. Trong đó `du-lieu/robot-canbang` đụng **đúng trần
6 000 ký tự** — trần ấy không phải một con số phòng xa, nó nổ trên dữ liệu có thật. Và tham số
`history` không trang trí: ở `rtos-sinhvien` nó biến `firmware/control_rtos.c` thành
`firmware/control_rtos.c (update→v24)` — phiên bản **tại lúc đổi**, số mà sổ cái một mình không
ghi, và số duy nhất nói được *"sau changeset ấy có ai đổi thêm nữa không"*.

### Nửa `loc_claim`, và con số nói nó yếu

Kế hoạch nêu năm dấu hiệu của một câu lập luận: `vì`, `nên`, `chắc chắn`, `đã kiểm`,
`đã xác nhận`. Đem đo trên 323 đề bài thật: nó bỏ được **11 trong 1 706 câu** — chạm 11/323 đề
bài. Chỗ rò thật không phải chữ "vì"; tác tử chính **trích sẵn phán quyết** cho verifier đọc.

Nên có dấu hiệu thứ sáu, thêm vì phép đo chứ không vì kế hoạch nói: `dat:` / `dat=` /
`pass_fail` / `chay_duoc=` / `không đạt` / `đã đạt`. Số mới: **95/1 706 câu, chạm 88/323 đề bài,
và 0/323 đề bài bị lọc thành trắng.** Thử thêm `thành công` nữa thì lên 123 câu, nhưng *"lệnh
chạy thành công, mã thoát 0"* là một **quan sát** — bỏ quan sát đi là lấy mất dữ kiện của
verifier, không lấy mất lập luận. Nên không nhận.

Và phải nói thẳng mức độ của nửa này: **`loc_claim` là một phép lọc văn xuôi, nó leaky và nó
biết thế.** Một câu lập luận không mang chữ nào trong sáu dấu hiệu vẫn đi qua. Hàng rào là nửa
kia — gói bằng chứng do mã dựng, thứ tác tử chính không soạn được.

### Cờ thứ mười vô hình, và một ca kiểm đúng đề nhưng kiểm một tên gõ sẵn

`verifier_goi_bang_chung` khai đúng trường trong `Features`, mà `Features.load()` vẫn trả
`False` khi `EIDE_FEATURE_VERIFIER_GOI_BANG_CHUNG=1`. Lý do: `ten_co()` là một **danh sách gõ
tay**, và `load()`/`to_dict()`/`tools/kiem_tai_lieu.py` đều vòng qua nó. Một cờ không có tên
trong danh sách ấy thì không bật được, không hiện trên tab cờ, và `kiem_tai_lieu` không bật nó
lên để đếm công cụ.

Có một ca kiểm nêu đúng bất biến này — `test_co_moi_co_trong_ten_co_va_to_dict` — và nó **xanh
suốt**, vì nó kiểm một tên gõ sẵn (`sim_runner_gioi_han`) thay vì so hai danh sách. Nay
`ten_co()` lấy từ `dataclasses.fields(Features)`, và ca kiểm mới so **tập hợp với tập hợp** rồi
bật mọi cờ qua biến môi trường để chắc đường nạp thật sự chạy.

Đây là biến thể của bài học DEV-344: một ca kiểm nói đúng điều cần canh mà không chạm tới thứ
nó nói nó canh.

### Giới hạn phạm vi, và những gì KHÔNG đổi

Đường **tự động** của SubagentStop vẫn dùng `viec_cho_verifier(bc)` — nó vốn đã sạch từ G6,
verifier ở đó chỉ thấy báo cáo. Có một ca kiểm canh đúng chuyện ấy: cờ bật thì đường tự động
**vẫn** gửi `BÁO CÁO (dữ liệu…)`, không gửi `BẰNG CHỨNG (dữ liệu)`. Lược đồ `TRUONG_BAO_CAO`
không đổi.

Điều kiện chuyển chế độ lấy từ **hợp đồng** (`dn.doc_duoc_viec`), không từ một danh sách tên:
thêm một verifier thứ hai sau này thì nó tự được bảo vệ.

### Tiêu chí còn mở

Kế hoạch đòi *"trên bộ ca gài lỗi (M4-22), tỉ lệ verifier bác đúng không giảm khi bật cờ"*.
M4-22 **chưa làm** (nó ở nhiệm vụ sau), và phép đo ấy cần lời gọi mô hình thật — §3.0 bắt hỏi
người dùng trước. Nên cờ giữ **TẮT**, và tiêu chí để mở, giống tiêu chí còn mở của M4-06.

Ba con số đã đo được thì đo bằng dữ liệu thật, không bằng mô hình: 323 đề bài verifier thật,
95/1 706 câu bị lọc, 29/42 dự án dựng được gói.

### Phá lại thì đỏ: 34/36 ở lượt đầu

Hai chỗ LỌT cùng một hình dạng, và là hình dạng của DEV-344: **một ca kiểm xanh vì MỘT DÒNG
KHÁC.** Bỏ hẳn khối B khỏi gói mà bộ kiểm vẫn xanh — vì ca kiểm của khối A đã thấy `a.c` qua
dòng changeset rồi. Hai khối ấy nói hai câu khác nhau: A nói *"cs-3 chạm a.c"* (chuyện đã xảy
ra), B nói *"a.c trong kho hiện là v1 và đang STALE"* (chuyện ĐANG đúng) — và chỉ câu thứ hai
trả lời được *"bằng chứng này còn giá trị không"*. Chỗ thứ hai: nhánh *"không có changeset nào"*
bị làm cho im lặng cũng xanh, mà im lặng và "không có gì để kiểm" khác hẳn nhau với người đọc.

Sau khi thêm hai ca đọc riêng từng khối: **36/36**. Bộ kiểm 1 878 → **1 896 xanh**, 0 đỏ.

## [DEV-353] [M4-09] Hook Stop đọc TÊN công cụ, nên `task.run(code-analyst)` tắt được hàng rào N6

Nhiệm vụ #24. **Sửa lỗi thuần**, không cờ, không tiền đề.

### Một phép kiểm tư cách thành viên đứng thay cho một phép đọc tham số

`kiem_viec_chua_ai_kiem` đi ra sớm bằng
`if "task.run" in (getattr(ctx, "cong_cu_da_goi", []) or [])`. Mà `cong_cu_da_goi` chỉ ghi
**TÊN** (`loop.py` `_one_tool`: `ctx.cong_cu_da_goi.append(call.tool)`), còn `task.run` chạy
**tám** loại tác tử con. Nên một lời gọi `task.run(subagent="code-analyst")` — hay `firmware`,
`sim-runner`, `test-writer`… — tắt luôn yêu cầu kiểm chứng độc lập ở cuối lượt.

Hai chỗ khác trên cùng đường đã làm đúng từ trước: `loop.py` đặt `ghi_chua_kiem = False` chỉ
khi `(call.args or {}).get("subagent") == "verifier"`, và `kiem_chung.co_viec_chua_kiem` lùi sổ
cái tới đúng cái mốc ấy. Chỉ hook này đọc tên.

### Đường đi vòng này đã NỔ, và nó nổ ở một lượt có `fs.edit` vào hàm ngắt

Hỏi "nó có đúng không" là hỏi sau; hỏi trước là "nó đã nổ lần nào chưa". Hook Stop ghi lại
chính `checks` của nó vào sổ cái, nên đếm được trên **68 sổ cái** (26 sổ có `task.run`, 257 lời
gọi — `verifier` 253, `code-analyst` 2, `firmware` 1, `sim-runner` 1):

* **41 lượt** hook khai `tu_kiem_da_chay`, tức nó đã im;
* **1 trong 41 lượt ấy không có một `task.run(subagent="verifier")` nào** —
  `robot-sinhvien2` `run-007`;
* và quét theo hình dạng (có `task.run` khác verifier + còn việc ghi chưa kiểm tới cuối lượt)
  ra **2 lượt**: thêm `rtos-sinhvien` `run-026`, lượt có cả `target.flash`.

`run-007` đọc rất rõ. Lời gọi `task.run(subagent="code-analyst")` nằm ở **đầu** lượt, trước khi
tác tử ghi dòng nào. Sau nó mới là `fs.edit` vào `ISR(TIMER2_COMPA_vect)` của
`firmware/timer.c`, rồi `build.compile`, rồi `fs.write sim/dump_isr.c`, rồi `sim.run`. Hook Stop
cuối lượt: `['tu_kiem_da_chay']`, `another_round=False`. Lời gọi làm hook im xảy ra **trước** cái
việc mà nó được coi là đã bảo đảm — một phép kiểm tư cách thành viên trên một danh sách tên thì
không có thứ tự, và cũng không có tham số.

### Sửa: một cờ của LƯỢT, đặt ở đúng chỗ đã đọc `subagent`

`TurnContext.da_goi_verifier: bool = False`, đặt `True` ngay cạnh `self.ghi_chua_kiem = False`
trong `_one_tool` — cùng một điều kiện, nên không có chỗ thứ tư để lệch. Hook đổi sang
`getattr(ctx, "da_goi_verifier", False)`.

Vì sao một cờ trong bộ nhớ là đúng **ở đây**, trong khi DEV-33x đã bỏ một cờ bộ nhớ cho đúng
câu hỏi này: hai câu hỏi khác nhau. *"Còn việc chưa ai kiểm chưa"* là câu hỏi xuyên phiên — app
khởi động lại giữa các bước — nên nó phải đọc sổ cái, và nó vẫn đọc sổ cái
(`co_viec_chua_kiem`, không đổi). *"Verifier có chạy trong LƯỢT này không"* là câu hỏi trong
phạm vi một lượt; `ctx` sinh ra và chết cùng lượt, nên nó là vật đúng để hỏi.

Ca kiểm cũ `test_da_goi_verifier_roi_thi_thoi` dựng `cong_cu=["fs.write","task.run"]` với sổ cái
RỖNG — nó **khoá đúng hành vi sai**. Theo §3.2: sửa ca cũ cho nó dựng một sổ cái có
`task.run(subagent="verifier")` sau lần ghi, và ghi lý do vào đây.

### Phá lại thì đỏ: 10/12 — hai chỗ LỌT không đổi hành vi

Tập phá dựng từ `git diff`, đi theo chỗ tháo được: mỗi nhánh `if`, mỗi điều kiện ghép `and`,
mỗi giá trị mặc định, mỗi chỗ đặt cờ. Lượt đầu **9/12**; chỗ LỌT thật là *mặc định của `getattr`
đổi thành `True`* — ctx nào không mang trường thì hook im luôn. Thêm
`test_ctx_KHONG_co_truong_thi_coi_nhu_CHUA_kiem` → **10/12**.

Hai chỗ LỌT còn lại **không đổi hành vi**, và đã kiểm lại chính phép phá trước khi tin chữ LỌT
(bài học M4-01/M4-02):

* *bỏ `res.ok` khỏi điều kiện* — `_one_tool` đã `return self._tool_error(...)` khi
  `not res.ok and res.error is not None`, và `grep` cho thấy **không có** `ToolResult(False)`
  nào trong `src/eide` thiếu `error=`. Nên nhánh ấy không tới được: `res.ok` ở dòng đó là một
  guard chết. Không viết ca kiểm contrived cho nó, và không bỏ nó đi vì nó là mã có sẵn, ngoài
  phạm vi nhiệm vụ.
* *so `subagent` lỏng thành `"verifier" in ten`* — trong tám tên của `SUBAGENT`, chỉ `verifier`
  chứa chuỗi ấy, và tên lạ đã bị `task_run` chặn bằng `E5004` trước khi tới đây.

Bộ kiểm 1 896 → **1 901 xanh**, 0 đỏ (5 ca mới). `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.

## [DEV-354] [M4-11] STALE theo TỆP, chặn tuyên xong khi còn STALE, và hồi quy nhẹ sau khi sửa mã

Nhiệm vụ #25. Hai phần **sửa lỗi thuần** (khai `deps.upstream`, hook `ket_qua_stale`) và một
phần **đổi hành vi** sau cờ `HOI_QUY_NEN` (mặc định TẮT). Tiền đề M2-01 đã xong.

### Kế hoạch chỉ sai chỗ, và chỉ biết bằng cách đo

Kế hoạch ghi: *"`deps.ha_nguon_cua`: với loại đích `sim_result` mà hiện vật có `deps.upstream`
thì CHỈ lấy khi `artefact_id in upstream`"*. Tôi viết ba ca kiểm đầu của bảng TC theo đúng mô
tả ấy — và **cả ba xanh sẵn** trên mã trước M4-11. Lớp đọc đã đúng từ M2-01: `ha_nguon_cua` có
nhánh `khai_ro` loại một hiện vật khỏi chuỗi mặc định khi nó đã khai nguồn **cùng loại**.

Chỗ đứt nằm ở lớp **GHI**: `test.run` và `sim.run` — hai công cụ mọi dự án đi qua — gọi
`store.apply(...)` **không có tham số `deps`**. Nên hiện vật của chúng không khai gì, và chuỗi
mặc định §E5.4 (`"code" → ("build", "sim_result", "target")`) đánh STALE **mọi** kết quả
test/sim khi sửa **bất kỳ** tệp mã nào. M4-06 đã làm đúng việc này cho
`sim_result:test-sensitivity`; hai đường chính thì chưa.

Lần thứ bảy đúng hình dạng ấy trong đợt: **cơ chế có sẵn, đường dẫn tới nó đứt.** Ba ca kiểm
kia giữ lại làm hàng rào cho lớp mà bản sửa dựa vào, và docstring nói rõ chúng xanh sẵn — một
ca kiểm xanh sẵn mà không nói ra thì lần sau ai đọc cũng tưởng nó đo bản sửa.

### Làm đúng CHỮ của kế hoạch thì tự đẻ ra một ô "còn tươi" GIẢ

Kế hoạch ghi bước 1: *"test.run/sim.run ghi thêm `deps.upstream = tep_nguon`"*. Đem thử trên
kho thật thì thấy không được:

* `du-lieu/robot-sinhvien2` lưu `sim_result:can-bang` với `tep_nguon = ['sim/test_balance.c']`
  — **một** tệp. Mà chính tệp ấy `#include "../firmware/pid.c"`, `"../firmware/motor.c"`,
  `"../firmware/filter.c"`.
* Lấy `tep_nguon` làm `upstream` thì sửa `firmware/pid.c` — tệp mà phép mô phỏng **dịch trực
  tiếp vào** — không còn làm kết quả lỗi thời. Hẹp đúng chỗ không nên hẹp.

Và `tep_nguon` hẹp vì một lý do có thật: `test.run`/`sim.run` nêu `nguon` tường minh thì chúng
dịch **đúng** các tệp ấy, còn phần sản phẩm vào bằng `#include`.

Nên `upstream` là **bao đóng `#include "..."` cục bộ** (`_khep_include`), không phải danh sách
tệp đưa cho trình biên dịch. Trên `robot-sinhvien2`, bao đóng ra đúng 5 mắt:
`sim/test_balance.c` · `firmware/filter.c` · `firmware/motor.c` · `firmware/pid.c` ·
`firmware/config.h`.

Chỉ `"..."`, không `<...>`: header hệ thống không phải phụ thuộc của dự án. Chỗ này có bẫy thật
— `du-lieu/rtos-sinhvien/firmware/` có một `stdio.h` riêng của bo, đúng tệp đã làm 11/12 tệp bị
xếp sai ở M4-19 (DEV-349) — nên ca kiểm canh `<...>` phải dựng một `stdio.h` giả **có thật**
trong dự án, không thì nó xanh vì tệp không tồn tại chứ không vì phép lọc chạy.

### Số đo: 107 → 49 trên chín kho thật

Bán kính STALE của *kết quả test/sim* khi sửa một tệp mã, đếm bằng `ha_nguon_cua` trên kho
thật, hai lần — một lần với kho như nó đang là, một lần sau khi khai `upstream` do
`_khep_include` dựng:

| Dự án | tệp mã × kết quả | trước | sau |
|---|---|---|---|
| `robot-canbang` | 6 × 1 | 6 | **3** |
| `robot-sinhvien` | 14 × 1 | 14 | **10** |
| `robot-sinhvien2` | 14 × 1 | 14 | **5** |
| `robot-tu-can-bang` | 24 × 1 | 24 | **13** |
| `rtos-sinhvien` | 30 × 1 | 30 | **8** |
| `stm32f469-freertos` | 6 × 2 | 12 | **6** |
| `usecase/uc03` | 3 × 1 | 3 | **1** |
| `usecase/uc11` | 4 × 1 | 4 | **3** |
| **TỔNG** | | **107** | **49** |

**58 trong 107 lần đánh STALE là cáo buộc oan** (54 %). Một băng cảnh báo lúc nào cũng sáng là
băng cảnh báo không ai đọc.

### Nhãn STALE phải chặn được lời tuyên xong, không thì nó là trang trí

`mark_stale` của §E5.4 chỉ *đánh dấu và nói lý do* — có chủ ý: không tự xoá, không tự chạy lại,
người quyết. Nhưng không chỗ nào **đọc** cái nhãn ấy lúc kết lượt, nên nó rơi đúng hình dạng đã
gặp bốn lần trong đợt này: phép đo đúng, con số đúng, rồi con số không đi tới đâu.

Hook Stop `ket_qua_stale` (không cờ — sửa lỗi thuần theo N6) nhắc một vòng khi lượt đã tuyên mà
còn kết quả lỗi thời, kèm **mã changeset** làm lý do và **tên công cụ** chạy lại. Ba cửa thoát:
lượt thuần đọc, chưa trả lượt về, và nhắc đúng một lần mỗi lượt. Nó **mở khoá** `test.run` /
`sim.run` trước khi bảo gọi — bài học DEV-351: hook nổ hai lượt liền mà tác tử không gọi lần
nào, vì công cụ `core=False` không nằm trong danh sách nó nhìn thấy.

`sim_result:test-sensitivity` cố ý không tính ở đây: nó đã có hook riêng và hook ấy so
`version_test`, một phép đo chính xác hơn nhãn stale.

### Hồi quy nhẹ: mách con số, KHÔNG xoá nhãn

Sau cờ `HOI_QUY_NEN`. Vừa ghi một tệp nằm trong `deps.upstream` của bộ kiểm thì chạy lại bộ
kiểm ngay — trần 20 s, **một lần mỗi lượt**, không đo độ phủ — rồi tiêm `hồi quy: x/y ca đạt`
vào transcript.

Hai chỗ cố ý không làm: **không ghi lại hiện vật** (nhãn STALE vẫn còn; §E5.4 nói "không tự
chạy lại", và một đường tự động ghi đè sẽ xoá mất chính cơ chế đánh dấu), và **không chạy
`sim.run`** (mô phỏng có thể lâu).

Điều kiện nổ đọc `deps.upstream` — **cùng một phép đọc** mà STALE dùng, không phải một phép so
tên thư mục. Nhờ thế một dự án đặt mã ở `src/` thay vì `firmware/` vẫn được, và một tệp bộ kiểm
không hề dịch tới thì không tiêu một lượt biên dịch nào. Phép chọn tệp để dịch **lọc theo đuôi**
`.c/.cpp/.cc`: bao đóng kéo cả `firmware/config.h` vào upstream (đúng cho STALE), mà đưa một
`.h` cho trình biên dịch là một lượt dịch đổ — và lúc ấy hồi quy báo "CHƯA chạy được" cho một bộ
kiểm vẫn chạy tốt.

### Tập phá tìm ra một lỗi trong chính mã tôi vừa viết

`_khep_include` có `tran = 200`, và vòng lặp viết `while hang_doi and len(xong) < tran`. Hai tệp
`#include` lẫn nhau làm hàng đợi tự nuôi chính nó trong khi `len(xong)` dừng ở hai — nên **cái
trần không chặn gì cả**. Phép phá *"bỏ phép dedupe"* không ra chữ ĐỎ, nó làm bộ kiểm **treo 900
giây** và cả script đổ. Nay trần đếm **lượt** (`for _ in range(tran)`), và tập phá biến một lượt
treo thành một chữ ĐỎ thay vì để nó giết cả phép đo.

Ba chỗ nữa tập phá chỉ ra là *phép đo* yếu, không phải sản phẩm:

* Nhãn của tôi nói *"bỏ CẢ HAI lớp lọc"* mà mã chỉ tháo **một** — hai lớp phòng
  (`p.is_file()` canh tệp mầm, `ung.is_file()` canh tệp được include) nằm cách nhau 15 dòng, và
  một phép thay chuỗi không tháo được cả hai. Đúng bài học M4-02. Nay khuôn script nhận một
  **danh sách cặp** để áp nhiều chỗ cùng lúc.
* Ca canh `#include <...>` xanh vì `stdio.h` không tồn tại, không vì phép lọc chạy.
* Dedupe không chỉ để chạy nhanh — nó là thứ giữ cho trần còn nghĩa. Dựng được ca phân biệt
  bằng phép đo chứ không bằng ước lượng: vòng `a ↔ b` cộng chuỗi `a → c → d → e`, với
  `tran = 6` thì có dedupe ra **5** tệp, không có ra **4**.

Và hai chỗ LỌT còn lại **không đổi hành vi**: bỏ `res.ok` khỏi điều kiện hồi quy (`_one_tool`
đã `return self._tool_error(...)` trước đó, và không `ToolResult(False)` nào trong `src/eide`
thiếu `error=`), đúng cái guard chết đã gặp ở M4-09.

### Phá lại thì đỏ: 24/32 lượt đầu → **31/34**

Tập dựng từ `git diff`, bốn mảng: bao đóng `#include`, hai chỗ ghi `deps`, hook
`ket_qua_stale`, đường hồi quy sau cờ. Lượt đầu **24/32**; sau khi thêm bảy ca kiểm cho các
chỗ LỌT (tệp mầm không tồn tại · dedupe tiêu hết trần · vòng `#include` chạy trong luồng có
đồng hồ · lý do ca đỏ trong lời nhắc hồi quy · `0/0` không được đọc thành đã đo · trần 20 s
tới được `chay_test` · `<...>` với một `stdio.h` giả có thật) và thêm hai phép phá **gộp**:
**31/34**.

Ba chỗ LỌT còn lại **không đổi hành vi**, và đã kiểm lại từng cái trước khi tin chữ LỌT:

* *bỏ `ung.is_file()`* — `p.is_file()` ở đầu vòng vẫn lọc. Hai lớp phòng ở hai chỗ, tháo một
  lớp thì không đổi gì; phép phá **gộp cả hai** thì ĐỎ.
* *trần quay lại đếm `len(xong)`* — phép dedupe vẫn làm hàng đợi cạn, nên nó vẫn dừng và vẫn
  ra đúng kết quả. Phép phá **gộp** (tháo cả dedupe lẫn trần-đếm-lượt) thì vòng lặp không dừng
  — và ca luồng-có-đồng-hồ biến nó thành **một chữ ĐỎ trong 8 giây** thay vì một lượt treo 120
  giây. Đây là chỗ đáng nhất của cả tập phá: hai lớp phòng độc lập thì chỉ phép phá gộp nói
  được có ca canh hay không.
* *bỏ `res.ok`* — guard chết: `_one_tool` đã `return self._tool_error(...)` trước đó, và không
  `ToolResult(False)` nào trong `src/eide` thiếu `error=`. Cùng chỗ đã gặp ở M4-09.

Bộ kiểm 1 901 → **1 929 xanh**, 0 đỏ (28 ca mới trong `tests/test_hoi_quy.py`).
`kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN. Cờ `HOI_QUY_NEN` giữ **TẮT**.

### Tiêu chí còn mở

Kế hoạch đòi *"số lần tuyên xong với kết quả STALE trong sổ cái phiên mẫu = 0"*. Con số ấy
**chưa đóng được**: sổ cái ghi lời gọi công cụ và `checks` của hook, nhưng không ghi trạng thái
kho tại thời điểm ấy, nên không soát lại được phiên đã lưu như các phép đo khác của đợt này.
Đóng nó cần **phát lại** các phiên mẫu với hook mới — tức lời gọi mô hình thật, mà §3.0 bắt hỏi
anh Công trước. Thay vào đó phép đo trên kho thật ở trên (107 → 49) nói về đúng cơ chế mà tiêu
chí ấy nhắm tới, và nói bằng dữ liệu đã có.

## [DEV-355] [M5-03] SVD: hệ thống trả HAI CÂU TRẢ LỜI TRÁI NHAU cho cùng một tệp

Nhiệm vụ #28. **Sửa lỗi thuần** (nối hai câu trả lời lại thành một) + **công cụ mới**
`reg.lookup` (`core=False`, R1). Không tiền đề, không cờ.

### Chỗ hổng: không phải thiếu tính năng, mà là một mâu thuẫn

`ingest.phan_loai` nhìn một tệp SVD, thấy `<device>` + `peripheral`, và khai `loai="svd"`,
mức hỗ trợ **ĐẦY ĐỦ**, `doc_duoc=True`. Rồi `doc.load` gọi `_nap_theo_loai` — `"svd"` không
nằm trong `_LOAI_VAN_BAN`, không phải Office, không có nhánh nào — nên nó rơi xuống
`E1001 "chưa có bộ đọc nạp nó vào kho tài liệu"`.

Một comment ngay trên `_LOAI_VAN_BAN` nói *"bốn loại đó có công cụ riêng đọc đúng cấu trúc của
chúng"*. `grep -rni svd src/` trước M5-03 ra đúng **hai** chỗ: phép phân loại, và chính câu
comment ấy. Không có bộ đọc nào.

Mâu thuẫn tệ hơn một tính năng thiếu. Thiếu thì tác tử đi đường khác; mâu thuẫn thì nó hỏi
*"tệp này đọc được không"*, nghe **có**, nạp, nghe **không** — và thử lại y nguyên.

### Vì sao đọc bằng mã, và vì sao phép cộng phải do mã làm

Một địa chỉ thanh ghi là `base + offset`. `0x40011000 + 0x08` nhớ sai một chữ số thì firmware
ghi vào **một thanh ghi khác**: không lỗi biên dịch, không lỗi chạy, chỉ là một ngoại vi không
làm gì. Đúng loại con số mà §C1 đòi phải có nguồn tra lại được, và đúng loại sai mà bài học
*"hằng số phần cứng phải tra, không được dựng lại"* nói tới.

`knowledge/svd.py` đọc `device/peripherals/peripheral` → `registers/register` → `fields/field`
bằng `xml.etree` (không thêm phụ thuộc, N-10). Ba chỗ SVD thật khác tệp tự viết, và cả ba đều
có ca kiểm riêng:

* **`derivedFrom`** — phần lớn ngoại vi cùng họ của một SVD thật khai bằng MỘT dòng
  `derivedFrom` và không có `<registers>`. Không xử lý thì mất gần hết register map. Và chiều
  ngược lại cũng phải đúng: một ngoại vi vừa `derivedFrom` vừa tự khai thanh ghi thì **bản tự
  khai thắng** — lấy thanh ghi của ngoại vi gốc lúc ấy là ghi vào kho một register map không
  phải của nó, mà nó trông đúng y như một register map thật.
* **`<cluster>`** — gói một nhóm thanh ghi lặp lại, cộng offset riêng, và cho tên một tiền tố.
  Bỏ qua thì mất thanh ghi; cộng thiếu offset cluster thì ra địa chỉ **SAI** — và địa chỉ sai
  tệ hơn thanh ghi thiếu, vì nó trông như đã có.
* **Ba lối khai vị trí bit** — `bitOffset`+`bitWidth`, `bitRange` `[msb:lsb]`, và `lsb`/`msb`
  (Nordic, SiLabs). SVD thật trộn cả ba trong một tệp.

### Hai chỗ chọn phía THẬN TRỌNG, và vì sao

`_so` trả `None` chứ không `0` khi không đọc được, và một ngoại vi có `baseAddress` hỏng thì bị
**bỏ cả ngoại vi**. Thanh ghi thiếu `addressOffset` cũng bị bỏ. Lý do giống nhau: `base = 0`
làm mọi địa chỉ của ngoại vi ấy thành offset trần, và một địa chỉ bằng `base` là một địa chỉ
**sai mà hợp lệ**. Thiếu một thanh ghi thì tác tử đi tra tiếp; có một thanh ghi sai thì nó dùng
luôn.

Địa chỉ ghi `0x` + **tám** chữ số như datasheet viết. `0x44` và `0x00000044` là cùng một số mà
không cùng một thứ với người đọc: cái thứ nhất trông như offset, và tác tử sẽ cộng base vào nó
lần thứ hai.

`size`/`access` **chỉ ghi khi SVD khai**. Điền mặc định 32 bit cho một thanh ghi không khai là
bịa một dữ kiện rồi dán tầng BẠC lên nó.

### Trần, và chỗ trần cắt phải NÓI RA

SVD thật của một MCU họ F4 có cỡ 1 500–3 000 thanh ghi và hơn 10 000 trường bit, nên trần
`TRAN_DON_VI = 40 000` là cần. Nhưng bản đầu của tôi cắt **im lặng** — và cắt im lặng ở đây là
chỗ tệ nhất của cả tệp: tác tử tra một thanh ghi ở cuối tệp, nhận *"không có"*, rồi kết luận
**chip không có thanh ghi ấy** trong khi câu đúng là **chưa nạp tới**. Hai câu dẫn tới hai việc
ngược nhau. Nay `doc.load` trả `da_cat_o_tran` và nói thẳng điều đó trong `note_vi`.

### `reg.lookup`, và vì sao nó phải tồn tại cạnh bộ đọc

Đo được trên bo STM32F469: nạp xong header BSP, tác tử đi `fs.grep` trong tệp để đọc chân thay
vì gọi `fact.extract_pinout` — bản đồ chân vào được **mắt** nó mà không vào **kho**, và firmware
sau đó dùng số không có Fact nào đứng sau (N1). SVD rơi vào đúng cái bẫy ấy và nặng hơn: nó là
XML hàng chục nghìn dòng, nên `fs.grep` trả về những mảnh thẻ **không mang theo `baseAddress`**
— tác tử đọc `addressOffset` rồi tự cộng, và phép cộng ấy không có nguồn nào kiểm lại được.

`reg.lookup` gom theo **chủ thể** (một thanh ghi một dòng, không tãi ra bốn dòng theo khoá),
trần **20 dòng** không nâng được qua tham số, và **nói ra** tổng số khớp. Phép tra rỗng phân
biệt hai câu: *chip không có thanh ghi ấy* và *chưa ai nạp register map* — hai việc khác nhau.

Và SVD **tự ghi Fact ngay lúc nạp**, khác PDF (phải gọi `fact.extract` sau). Lý do: với PDF phép
trích là một phỏng đoán trên văn xuôi, nên nó là một bước riêng người xem được; với SVD không có
phỏng đoán nào, và bắt gọi thêm một công cụ chỉ tạo thêm một chỗ để quên.

### Phá lại thì đỏ: 28/34 lượt đầu → **34/34**

Sáu chỗ LỌT ở lượt đầu, và **cả sáu là lỗ thật**, không chỗ nào vô hiệu:

1. `_so` trả `0` thay vì `None` — không ca nào canh `baseAddress` hỏng.
2. Bỏ lối khai bit thứ ba (`lsb`/`msb`) — ca kiểm chỉ dùng hai lối đầu.
3. Thanh ghi thiếu `addressOffset` vẫn được nạp với địa chỉ = `base`.
4. **`dem()` trả `(r, r)` vẫn xanh** — vì ca kiểm chính của bộ ra 4 thanh ghi và 4 trường, hai
   con số **tình cờ bằng nhau**. Một phép đo mà hai vế bằng nhau thì nó không đo được vế nào;
   ca mới dựng 1 thanh ghi / 3 trường.
5. `reg.lookup` không gom theo chủ thể vẫn xanh — vì 25 thanh ghi của ca trần chỉ có **một**
   Fact mỗi cái, nên gom hay không cũng ra 25 dòng. Ca mới cho mỗi thanh ghi hai Fact.
6. Trần 20 nâng được lên 500 qua tham số — không ca nào truyền `gioi_han` lớn.

Hai chỗ 4 và 5 cùng một hình dạng và đáng ghi lại: **phép đo xanh vì dàn dựng của nó làm hai vế
trùng nhau**, không vì mã đúng. Nó là biến thể của DEV-344 ở tầng dữ liệu dàn dựng chứ không ở
tầng assert.

Bộ kiểm 1 942 → **1 950 xanh**, 1 skip, 0 đỏ (21 ca mới + 1 ca `nha_that`).
Công cụ 131 → **132**. `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.

### Tiêu chí còn mở: chưa có SVD THẬT nào trên máy

Kế hoạch đòi *"nạp được SVD thật STM32F469, ghi số thanh ghi vào DEV-LOG"*. Quét cả máy
09/10/2026: **không có tệp `.svd` nào** ngoài các tệp do chính bộ kiểm sinh ra trong `tmp`.

Ca `test_nap_duoc_SVD_THAT` đã viết và đánh `nha_that` + `skipif`: nó dò bốn chỗ hay có
(`~/STM32Cube`, `~/.platformio`, `STM32CubeIDE.app`, `tai-lieu-tham-khao/`) và **skip** khi
không thấy. Nên con số *"nạp được N thanh ghi của một chip thật"* chưa có — và tôi ghi đúng như
thế, thay vì tự viết một tệp SVD lớn rồi gọi nó là *thật*. Một bộ đọc chạy đúng trên tệp tự
viết chưa nói gì về một tệp có `derivedFrom` khắp nơi và cluster lồng nhau.

## [DEV-356] [M5-05] Một con số ĐÚNG ĐỘ LỚN mà SAI THỨ NGUYÊN vẫn vào kho được

Nhiệm vụ #29. **Sửa lỗi thuần**, không cờ, không tiền đề.

### Ba chỗ đứt, và cả ba cùng một hình dạng

1. **`hop_ly` không kiểm đơn vị.** Nó quy về đơn vị cơ bản rồi chỉ so **độ lớn**, nên
   `hop_ly("vdd.max", 25, "°C")` trả `True`: 25 nằm trong khoảng điện áp hợp lý (0,5–60 V), và
   chẳng dòng nào hỏi *"25 cái gì"*. Một Fact `vdd.max = 25 °C` ở tầng BẠC là **vế giới hạn**
   của luật ERC quá áp — tức một ô xanh giả đúng chỗ đắt nhất.
2. **Hai khoá không bao giờ được kiểm khoảng.** `_MAU_THONG_SO` sinh ra `"fmax"` và `"ta.max"`;
   `PHAM_VI_HOP_LY` khai `"f.max"`, `"temp.min"`, `"temp.max"`. Hai bảng không gặp nhau, nên
   phép kiểm khoảng của tần số và nhiệt độ **chưa nổ lần nào**.
3. **Đường HÀNG BẢNG không gọi `hop_ly` lần nào** — mà bảng là đường chính của datasheet:
   `_tu_hang_bang` tồn tại chính vì đơn vị nằm ở cột riêng, nên nó có đủ dữ kiện để kiểm thứ
   nguyên, và nó là đường duy nhất không kiểm.

Lần thứ tám đúng hình dạng ấy trong đợt: cơ chế có sẵn (`PHAM_VI_HOP_LY`, `ve_si`), đường dẫn
tới nó đứt.

### Tra thứ nguyên theo tiền tố DÀI NHẤT, và vì sao không theo "phần trước dấu chấm cuối"

Kế hoạch ghi *"theo TIỀN TỐ khoá (phần trước dấu chấm cuối)"*. Làm đúng thế thì ba khoá
`i2c.pullup.typ` (ohm), `i2c.fmax` (hertz) và `i2c.addr` (không có thứ nguyên, giá trị là chuỗi
`"0x48"`) đều rút về `i2c` hoặc `i2c.pullup` — và hai trong ba bị gán sai. Nên `thu_nguyen_cua`
tra khoá nguyên vẹn trước rồi bỏ dần đoạn cuối, lấy **cái dài nhất khớp**.

Đơn vị **rỗng** bị loại cho mọi thứ nguyên trừ nhóm byte: datasheet ghi `Flash: 32768` không kèm
đơn vị thật, và `ve_don_vi_co_ban` đã có ngữ nghĩa KB=1024 cho nhóm ấy. Với volt/ampe/hertz thì
một con số không đơn vị là một con số không ai kiểm lại được — và `_SO_DON_VI` vốn luôn bắt kèm
đơn vị, nên không mất gì.

### Ca kiểm của kế hoạch XANH VÌ MỘT LÝ DO KHÁC

Bảng TC nêu TC-M5-05-04: hàng `o=["VDD","25","°C"]` → `_tu_hang_bang` trả rỗng. **Nó trả rỗng
trên mã chưa sửa** — nhưng không vì phép kiểm đơn vị nào: `"VDD"` trơn KHÔNG khớp mẫu nào trong
`_MAU_THONG_SO` (mẫu đòi `VDD (max)` / `VDD (min)` hoặc `supply voltage`), nên hàng bị bỏ ngay ở
bước tìm khoá. Viết đúng chữ của kế hoạch thì được một ca xanh trước và sau khi sửa.

Nên các ca đơn vị dùng tên hàng **khớp mẫu** (`VDD (max)`, `Supply voltage`), và có thêm một ca
ghim lại chính tính chất ấy để lần sau không ai lặp lại.

### Hai lỗ nữa, tìm ra bằng TẬP PHÁ, ngoài phạm vi kế hoạch nêu

**`hop_ly` nổ `TypeError` với giá trị không phải số.** `pv[0] <= co_ban` so một `float` với một
`str`. `i2c.addr` — khoá giá trị-chuỗi duy nhất hiện có — sống sót **chỉ vì** nó không có khoảng
trong `PHAM_VI_HOP_LY`. Cái lỗi nằm đó im lặng, chờ người đầu tiên thêm một khoảng cho một khoá
như thế. Đã thêm cửa chặn ở phép kiểm khoảng.

**Đường bảng và đường dòng chữ sinh HAI KHOÁ KHÁC NHAU cho cùng một thông số.**
`_tu_hang_bang` cắt mù hậu tố (`k.rsplit(".", 1)[0]`), nên:

| Thông số | đường dòng chữ | đường BẢNG (trước M5-05) |
|---|---|---|
| dung lượng Flash | `flash.size` | **`flash.max`** |
| tần số tối đa | `fmax` | **`fmax.max`** |
| địa chỉ I2C | `i2c.addr` | **`i2c.max`** |

Ba khoá bên phải không có trong `KHOA_CHUAN`, không có trong `PHAM_VI_HOP_LY`, và
`tools/xay_dung._han_muc` **không đọc `flash.max`** — nên **một dung lượng Flash đọc từ BẢNG
chưa bao giờ thành hạn mức**, mà Fact vẫn trông hợp lệ nên không ai thấy. Đúng cùng hình dạng
với chính lỗi M5-05 đi vá: hai khoá cho một thông số, hai bên không gặp nhau.

Sửa: chỉ cắt hậu tố khi nó **đúng là** một hậu tố mà cột bảng cấp được (`min`/`typ`/`max`); khoá
còn lại giữ nguyên vẹn. Kế hoạch có dòng *"Không đổi tên khoá mà bộ trích sinh ra"* — và sửa này
nằm trong tinh thần ấy chứ không ngược: ba khoá bị đổi là ba khoá **không chỗ nào đọc**, nên
không Fact cũ nào đang khớp với ai bị lệch.

### Phá lại thì đỏ: 17/21 lượt đầu → **23/24**

Bốn chỗ LỌT ở lượt đầu, và chúng chia làm hai loại:

* **Hai lỗ thật** → thành hai mục ở trên (`TypeError` với chuỗi; khoá bảng kiểm bằng `khoa_goc`
  nên mất phép kiểm khoảng). Thêm ba phép phá mới cho phần vừa sửa.
* **Hai phép phá vô hiệu**, đã kiểm lại trước khi tin chữ LỌT:
  * *"tra tiền tố NGẮN nhất trước"* — bảng hiện **không có** khoá `"i2c"`, nên đi từ ngắn hay
    từ dài cũng cùng rơi vào `"i2c.pullup"`. Tức ca kiểm `i2c` của tôi **không đo được** tính
    chất nó nói nó đo. Nay có một ca đo trực tiếp `thu_nguyen_cua` bằng cách thêm một dòng vào
    bảng trong phạm vi ca kiểm (`adc` cạnh `adc.fmax`).
  * *"ô sai làm BỎ NỐT cả hàng (`break` thay `continue`)"* — `cap` có đúng **một** phần tử cho
    mỗi ô, nên `break` thoát một vòng lặp một phần tử: không đổi hành vi. Bỏ phép phá ấy đi
    thay vì dựng một ca kiểm contrived để che nó (bài học M4-19).

Chỗ LỌT còn lại cũng vô hiệu: bỏ `isinstance` khỏi phép kiểm thứ nguyên — với chuỗi, `ve_si`
trả nguyên nên đơn vị cơ bản vẫn khớp, và kết quả không đổi.

Bộ kiểm 1 976 → **1 980 xanh**, 1 skip, 0 đỏ (30 ca mới trong `tests/test_don_vi_fact.py`).
`kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.

## [DEV-357] [M5-07] Chốt N1 cuối cùng mà MÃ đứng canh, và nó so chuỗi sau khi xoá hết dấu chấm

Nhiệm vụ #30. **Sửa lỗi thuần**, không cờ, không tiền đề.

### Cửa mà MỌI hằng số firmware phải đi qua, và nó nhận bừa

`fact.from_doc` là cây cầu duy nhất để một con số trong tài liệu được phép đi vào mã nguồn: mô
hình chọn đoạn và đặt tên khoá, **mã kiểm giá trị có mặt thật trong đoạn ấy**. Kỷ luật đó là
toàn bộ giá trị của công cụ — nó ra đời vì tác tử đọc đúng bốn mục tài liệu rồi bị chốt hằng số
N1 chặn khi ghi `main.c`.

Phép kiểm cũ, hai dòng:

```python
def _chuan(x): return re.sub(r"[\s.,]", "", x).lower()
co = _chuan(gt) in _chuan(noi_dung)
```

Hai chỗ nó nói sai, và cả hai nói sai theo đúng chiều tệ nhất — **nhận bừa**:

* **Xoá dấu chấm** biến `2.7 V` thành `27v`, nên `gia_tri="27"` đi qua. Một điện áp 2,7 V vào
  kho thành **27**, mang trích dẫn, mang tầng BẠC, trông y như một Fact đọc đúng.
* **Phép CHỨA không có ranh giới**, nên `3` khớp `Table 3`, `180` khớp `1800`, `39` khớp `0.39`.

Và `source.quote` lưu 200 ký tự **đầu đoạn**, không phải chỗ có con số — nên người mở Fact ra
xem thấy một đoạn không chứa con số, và trích dẫn không chứng minh gì cả.

### Bốn phép kiểm, và chúng trả lời bốn câu khác nhau

1. **`trich` phải có thật** trong đoạn (chỉ gộp khoảng trắng, không xoá dấu chấm). Thiếu phép
   này thì `trich` là một trường tự do: mô hình gõ một câu nghe hợp lý, con số nằm trong câu
   ấy, và **cả hai cùng do nó viết ra** — lời khai tự chứng minh chính nó.
2. **Ranh giới token** `(?<![\w.,])…(?![\w]|[.,]\d)`. Dấu chấm/phẩy *theo sau* chỉ chặn khi nó
   mở đầu một phần thập phân, nên `Mã lỗi 39, và…` vẫn khớp được — chặn cả dấu phẩy ngắt câu
   là chặn một cách viết rất thường gặp.
3. **Giá trị ≤ 2 ký tự thì phải có `trich`.** Ranh giới một mình không đủ: `3` khớp `Table 3`
   ở đúng ranh giới. Một số một–hai chữ số gần như luôn tìm thấy ở đâu đó trong một đoạn.
4. **`don_vi_do` phải đứng ngay sau số**, khớp cả token. `Tần số 180 MHz, điện áp 3.3 V` có cả
   `MHz` lẫn `V`; một phép "có mặt trong câu" sẽ nhận `V` cho giá trị `180`. Và `m` không phải
   `mA` — `ve_si` quy đổi theo cái tác tử khai, nên con số trong kho khác con số trên giấy.

Nhánh hex/thập phân (`39` ↔ `0x27`) giữ nguyên ý nhưng đi **cùng** phép ranh giới, không đường
riêng.

### Hai chỗ KHÔNG theo chữ của kế hoạch, và lý do

**Mã lỗi.** Kế hoạch ghi `E2008` cho mọi lý do từ chối. Giữ **E2006** cho *"giá trị không có
trong đoạn"* — đúng nghĩa mã cũ, và việc cần làm vẫn như trước (chọn đoạn khác hoặc sửa giá
trị). `E2008` chỉ cho ba lý do **mới**: `trich` bịa · số quá ngắn · đơn vị lệch. Gộp cả bốn vào
một mã là bắt tác tử học một mã cho bốn chuyện dẫn tới bốn việc khác nhau — và một ca kiểm cũ
đang khoá đúng nghĩa cũ ấy.

**Một ca cũ phải sửa (§3.2).** `test_fact_from_doc_nhan_ca_hai_dang_cua_mot_gia_tri` gọi với
`gia_tri="39"` không kèm `trich`. Tính chất nó canh (*"hai dạng của một giá trị đều nhận"*) vẫn
đúng; nó chỉ phải nói ra mình đọc ở **câu** nào. Lý do ghi ngay trong docstring của ca ấy.

### TC-M5-07-01 của kế hoạch cũng xanh vì một lý do khác

Viết đúng chữ kế hoạch — `gia_tri="27"`, không `trich` — thì ca bị chặn vì **số quá ngắn**
(`"27"` dài hai ký tự), và phép so dấu chấm **không bao giờ chạy tới**. Cùng cái bẫy vừa gặp ở
TC-M5-05-04: một ca kiểm đúng đề mà không chạm thứ nó nói nó canh. Ca thật nêu `trich` để luật
số-ngắn không che mất, rồi kiểm **cả hai** lý do bằng hai lời gọi với hai mã lỗi khác nhau.

### Phá lại thì đỏ: 15/22 lượt đầu → **22/22**

Bảy chỗ LỌT, và **cả bảy là ca kiểm của tôi chưa chạm tới** — không chỗ nào vô hiệu:

1. *trả lại phép xoá dấu chấm* — phép ấy nằm ở hàm so `trich`, còn phép khớp giá trị đi regex
   riêng; ca `27 ≠ 2.7` không canh chỗ đó.
2. *bỏ ranh giới TRƯỚC* — không ca nào có giá trị đứng sau dấu thập phân (`0.39`).
3. *ranh giới sau chặn luôn dấu phẩy ngắt câu* — không ca nào có `39,`.
4. *bỏ nhánh hex* — câu trích của ca hex có **cả hai** dạng, nên phép khớp trần đã tìm thấy và
   nhánh hex chưa bao giờ chạy tới.
5. *đơn vị khớp ở bất kỳ đâu* — ca cũ dùng một đơn vị không xuất hiện ở đâu trong câu, nên
   "bất kỳ đâu" cũng trượt.
6. *đơn vị không cần ranh giới cuối* — không ca nào có đơn vị là tiền tố của đơn vị khác
   (`m` ⊂ `mA`).
7. *cửa sổ quote hẹp còn 2 ký tự* — ca cũ chỉ kiểm `"1800" in quote`, mà ±1 ký tự vẫn chứa.

Năm trong bảy chỗ ấy chỉ lộ ra khi **dàn dựng có đúng hình dạng cần đo** — bốn dòng văn bản
thêm vào bộ dàn dựng (`0.39 phần trăm`, `0x27` một mình, `39,`, `100 mA`) là thứ biến bảy chữ
LỌT thành bảy chữ ĐỎ.

Bộ kiểm 1 993 → **2 000 xanh**, 1 skip, 0 đỏ (20 ca mới trong `tests/test_fact_from_doc.py`).
`kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.

## [DEV-358] [M5-13] Trần ngữ cảnh bị LÁCH bởi chính phép cắt dựng ra để giữ nó

Nhiệm vụ #31. **Sửa lỗi thuần**, không cờ, không tiền đề.

### Ba công cụ đọc tri thức không có chính sách, và trần chung không đỡ được

`CHINH_SACH` của phong bì không có `doc.read`, `fact.query`, `fact.extract`, nên cả ba rơi vào
trần chung 4 000 token. Mà trần chung **bị lách**: `_cat_chung` cắt *số* phần tử của một list
(`d[:30]`) và không cắt từng phần tử.

Hai con số của chuyện này:

* Một `doc.read` **mặc định** trả 40 đoạn × 2 000 ký tự ≈ 60 000 ký tự ≈ **20 000 token** — và
  30 phần tử đầu của nó vẫn là 60 000 ký tự. Đây không phải ca bất thường mà trần chung sinh
  ra để đỡ: nó là đường đọc tài liệu CHÍNH.
* `{"ds": ["y" * 20000] * 5}` có 5 phần tử, nên `d[:30]` không cắt gì, rồi mỗi chuỗi được cắt
  theo trần **của cả kết quả** (12 000 ký tự) → 5 × 12 000 = 60 000 ký tự. Một cái trần
  4 000 token ra **20 000 token**, bằng chính phép cắt đáng ra phải chặn nó.

### Ngân sách phải đi xuống theo

`_cat_chung(d, tran)` nay mang theo ngân sách, và chia nó cho các nhánh con (sàn
`TRAN_PHAN_TU_TOKEN = 400`, vì một mảnh 100 ký tự thì mô hình không đọc ra được gì ngoài *"có
thứ gì ở đây"*). Phần tử nhỏ không tiêu gì nên chỗ dư không mất — chỉ phần tử to bị kẹp.

Và chỗ gọi chừa lại một phần tư trần cho **vỏ JSON**: `_cat_chung` tiêu đúng ngân sách nó được
giao, nên giao cả trần thì `shown_tokens` nhảy lên **4 024** vì mấy chục token dấu ngoặc và tên
khoá. Một cái trần bị vượt bởi chính phép cắt dựng ra để giữ nó.

### `doc.read`: cửa sổ đi theo TỪ KHOÁ, không lấy đầu đoạn

≤ 8 đoạn, mỗi đoạn 600 ký tự **quanh chỗ khớp `tim`**. Nửa sau là cả giá trị của chính sách:
tác tử gọi `doc.read(tim="throttle")` vì nó cần đúng chỗ ấy. Trả 600 ký tự đầu của một đoạn
5 000 ký tự là trả về phần nó **không** hỏi — rồi nó gọi lại, hoặc tệ hơn, kết luận tài liệu
không có phần đó.

`so_khop` giữ nguyên (không ghi đè bằng số đoạn đang hiện), và `note_vi` chỉ đường đọc tiếp
bằng `tu` hoặc `blob.read`. Một trần cắt im lặng thì 8 đoạn đọc như toàn bộ tài liệu.

### `fact.query` / `fact.extract`: bỏ `explain`, GIỮ `source`

`explain` của một Fact là một chuỗi JSON cỡ 1 KB, và mô hình **không cần** nó để dùng con số:
nó cần `value`, `unit`, `tier`, và chỗ tra lại. `source` thì giữ — nhưng gọn còn
`doc_id`/`page`/`cite`. Cắt luôn cả `source` là lấy mất đúng thứ làm một Fact khác với một con
số nhớ được.

Chính sách chỉ nổ khi kết quả > 800 token. Dưới đó đi nguyên: một dấu *"đã cắt"* xuất hiện ở
**mọi** lời gọi thì không còn nói gì.

### Số đo trên 23 kho THẬT

Một lời gọi `fact.query` không tham số, bọc hai lần — một lần với chính sách mới, một lần với
bảng chính sách đã bỏ `fact.query` ra (tức hành vi trước M5-13):

| Dự án | Fact | trước | sau |
|---|---|---|---|
| `robot-sinhvien` | 30 | **12 076** | 4 579 |
| `robot-canbang` | 100 | 10 171 | **4 381** |
| `robot-tu-can-bang` | 100 | 9 548 | 4 213 |
| `rtos-sinhvien` | 17 | 4 502 | 2 062 |
| `stm32f469-disco` | 14 | 4 541 | 1 791 |
| … 18 kho nữa | | | |
| **TỔNG** | | **67 635** | **32 560** |

Giảm **35 075 token, tức 51 %**. Và chỗ đáng chú ý hơn tỉ lệ: `robot-sinhvien` đưa **12 076
token vào ngữ cảnh cho MỘT lời gọi** — bốn lời gọi như thế là hết một cửa sổ 48k.

Bốn kho nhỏ (1–2 Fact) ra con số **y nguyên**, đúng như ca âm đòi.

### Phá lại thì đỏ: 20/23 lượt đầu → **23/23**

Ba chỗ LỌT, và cả ba cùng một hình dạng: **dàn dựng của ca kiểm làm phép phá thành vô hiệu**,
không phải mã đúng.

1. *không cắt `o[:10]`* — không ca nào có hàng bảng nhiều ô.
2. *hạ trần kích hoạt về 0* — ca âm của tôi dựng `source` **đã đúng** hình dạng `_gon` trả về,
   nên hạ trần cũng không đổi gì. Ca âm đúng phải có `explain` để `_gon` *có thể* cắt, rồi đòi
   nó **đừng** cắt.
3. *ngân sách dict không chia theo số khoá* — ca `{"ds": [...]}` có **một** khoá, nên chia cho
   một là phép đồng nhất.

Đây là lần thứ ba trong ba nhiệm vụ liền (M5-03 · M5-07 · M5-13) mà chỗ LỌT nằm ở **bộ dàn
dựng**, không ở mã sản phẩm: hai vế tình cờ bằng nhau, một hình dạng tình cờ đã đúng, một tập
hợp tình cờ có một phần tử. Bài học gom lại: *khi dựng ca kiểm cho một phép chia hay một phép
cắt, dàn dựng phải có **ít nhất hai** phần tử và chúng phải **khác nhau**.*

Bộ kiểm 2 012 → **2 015 xanh**, 1 skip, 0 đỏ (tổng 15 ca mới trong `tests/test_mem_a.py`).
`kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.

## [DEV-359] [M5-17] Bản tóm tắt C2 — nguồn DUY NHẤT về đoạn đã nén — sống đúng một tiến trình

Nhiệm vụ #32, P0 cuối của Giai đoạn 1. **Phần A sửa lỗi thuần**; **phần B đổi hành vi** sau cờ
`RESUME_TUONG_THUAT` (mặc định TẮT). Không tiền đề.

### Phần A: cơ chế có sẵn, đường dẫn tới nó đứt (lần thứ chín)

`BoNen.__init__` đặt `tom_tat_hien_tai = None`, và chỉ gán nó khi nén thành công **trong tiến
trình ấy**. Tiến trình mới dựng một `BoNen` mới, nên `dung_khoi_resume(tom_tat_truoc=…)` luôn
nhận `None` và khối `<resume>` in *"Chưa có bản tóm tắt nào"*.

Hậu quả đúng chỗ đau nhất: bản tóm tắt là **nguồn duy nhất** về giai đoạn đã bị nén khỏi ngữ
cảnh — chính `van_ban()` của nó nói thế. Mở lại dự án sau một lần nén thì đoạn hội thoại ấy
không còn ở transcript (`thay_toan_bo` đã ghi đè), cũng không còn ở resume. Nó chỉ còn **trong
sổ cái**, nơi nó đã được ghi từ đầu: `ledger.append("compact", {… "tom_tat": tt.to_dict()})`.

`tom_tat_cuoi_tu_so_cai(ledger)` duyệt ngược và dừng ở sự kiện `compact` gần nhất đáng kể:
`buoc == "ok"` kèm `tom_tat` → trả bản ấy; `buoc == "huy"` → trả `None`. §6.2.3 cho huỷ nén
trong 24 giờ, và huỷ nghĩa là đoạn hội thoại **quay về nguyên văn** — nạp lại bản tóm tắt lúc
ấy là đưa vào ngữ cảnh một bản rút gọn của thứ đang có đủ, tức hai nguồn cho một giai đoạn.

Dừng ở cái **gần nhất**, không phải *"có `huy` ở đâu đó thì bỏ hết"*: một lần huỷ tháng trước
không được làm mọi lần nén sau đó vô hình.

`BanTomTat.tu_dict` đảo `to_dict`, và hai chỗ phải cẩn thận vì đây là dữ liệu đã nằm trên đĩa:
`covers` ghi thành **list** (JSON không có tuple) nên đọc lại phải đưa về tuple; và sổ cái của
một bản EIDE cũ có thể **thiếu khoá** — hàm này chạy ở đường khởi động, nên một `KeyError` ở
đây là đổi một bản tóm tắt mất lấy cả dự án không mở được. Cùng lý do, `BoNen.__init__` bọc
`try`.

### Phần B: 96 % phiên thật chưa bao giờ chạm ngưỡng nén

Đo trên dữ liệu thật: **313 phiên có transcript**, và **303 trong số đó (96 %) thuộc dự án chưa
từng nén lần nào**. Tức câu *"chưa có bản tóm tắt nào"* không phải một ngoại lệ — nó là câu khối
resume nói ở **gần như mọi lần mở lại**, trong khi một transcript đầy đủ đang nằm sẵn trên đĩa.

`tuong_thuat_co_hoc(messages)` dựng tường thuật **bằng mã, 0 token mô hình**: 3 lời người cuối,
10 lời gọi công cụ cuối (tên · ok hoặc mã lỗi · `summary_line`), lỗi cuối. Trần 1 500 ký tự.

Ba thứ, và chỉ ba. Cố ý **không** tóm tắt lời tác tử nói: một bản rút gọn của lời nó tự nói là
chỗ dễ nhất để một kết luận sai sống thêm một phiên — mà cả mảng này tồn tại để chặn đúng
chuyện đó. Và tường thuật kết bằng một câu nói rõ *"đây là việc ĐÃ xảy ra, không phải việc cần
làm tiếp"*: bài học DEV-34x, bốn lượt liền lặp lại việc cũ vì khối resume nghe như một lời giao
việc.

Bản tóm tắt C2 **thắng** tường thuật khi có cả hai: nó đã qua vòng kiểm chứng (§6.2), còn tường
thuật chỉ là một bản kê việc.

Sau cờ vì nó đổi thứ mô hình đọc ở **lượt đầu tiên** của mọi phiên mở lại (N-4) — và lượt đầu
là lượt đắt nhất để đổi, vì mọi thứ sau đó dựa trên nó.

### Số đo trên dữ liệu thật

| Phép đo | Con số |
|---|---|
| Lần nén C2 **đạt** trên sổ cái thật | **4** (2 dự án: `robot-tu-can-bang`, `thu-nghiem-mem-c`) |
| Lần **huỷ** nén | 0 |
| Bản tóm tắt nạp lại được qua `tu_dict`, **không rỗng** | **2/2 dự án** |
| Phiên có transcript | **313** |
| … thuộc dự án **chưa từng nén** | **303 (96 %)** |

### Một lỗi trong chính phép đo, lần thứ bảy của đợt

Phép đếm phiên đầu tiên của tôi lọc bằng `'"buoc": "ok"' in line`. Sổ cái thật ghi JSON **không
có khoảng trắng** sau dấu hai chấm (`{"seq":1,…}`), nên chuỗi ấy **không khớp lần nào** — và
phép đo trả về **100 %** thay vì trả rỗng. Một con số hợp lý, sai, và không có gì kêu lên.

Đúng bài học *"lọc sai ra số đẹp"*: lọc sai mà trả rỗng thì rẻ, trả một con số hợp lý thì tốn.
Lần này nó rẻ vì tôi mở dữ liệu thô ra đếm — `grep -c '"compact"'` ra 146 dòng ở
`robot-tu-can-bang`, trong khi phép lọc nói dự án ấy chưa nén lần nào. Hai con số chỏi nhau là
thứ duy nhất cứu phép đo.

### Phá lại thì đỏ: 20/23 lượt đầu → **23/23**

Ba chỗ LỌT, **cả ba là ca kiểm của tôi chưa chạm tới**, và cả ba cùng một hình dạng với ba
nhiệm vụ trước:

1. *tường thuật không nói mã lỗi ở dòng lời gọi* — chuỗi `` `target.flash` → E4040 `` cũng
   xuất hiện ở dòng **Lỗi cuối cùng**, nên assertion của tôi xanh qua dòng khác. Ca mới dựng
   **hai** lời gọi đổ với **hai** mã, và soi phần văn bản **trước** dòng lỗi cuối.
2. *bỏ trần 1 500 ký tự* — transcript dàn dựng ngắn hơn trần, nên bỏ trần không đổi gì.
3. *bỏ cửa `try` quanh phép đọc transcript* — ca kiểm của tôi chạy trên một dự án **chỉ có một
   phiên**, nên `_tuong_thuat_phien_truoc` trả rỗng ngay ở bước *"không có phiên nào trước"* và
   chưa chạm tới cửa `try` nó nói nó canh. Nay ca dựng một phiên trước, và **khẳng định có
   tường thuật trước khi phá**.

Bốn nhiệm vụ liền (M5-03 · M5-07 · M5-13 · M5-17) đều có chỗ LỌT nằm ở **bộ dàn dựng**, không ở
mã sản phẩm. Bài học gom lại, viết ra để dùng: *trước khi tin một ca kiểm, hỏi nó có chạy tới
dòng mã nó nói nó canh không — và khẳng định điều đó bằng một assertion đặt TRƯỚC phép phá.*

Bộ kiểm 2 015 → **2 030 xanh**, 1 skip, 0 đỏ (18 ca mới trong `tests/test_mem_c.py`).
Cờ 11 → **12**, cái mới giữ TẮT. `kiem_tai_lieu` 0 chỗ LỆCH CHẮC CHẮN.
