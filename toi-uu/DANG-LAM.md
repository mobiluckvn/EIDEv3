# ĐANG LÀM — chỗ dừng 09/10/2026, sau việc #32

> Tệp này trả lời đúng một câu cho phiên sau: **mở ra là làm tiếp được từ đâu.**
> Bằng chứng từng việc nằm ở `EIDE_Toi_uu_Agent_2026-10-06.xlsx`, sheet **“Danh mục tối ưu”**
> (cột Q, T–Y). Các sheet “Tiến độ …” là ảnh chụp các mốc trước, giữ lại để so.

## Đang ở đâu

| | |
|---|---|
| **Xong** | **30/106** — và **hết P0 không bị chặn của Giai đoạn 1**. GĐ1 có 32 việc, còn #26 (P1) và #27 (P0, bị #26 chặn) |
| **Đang dở** | **không có.** `main` đã đẩy và khớp `origin/main`. Mọi nhánh `toi-uu/*` đã gộp |
| Ca kiểm | 1 896 → **2 030** xanh · 1 skip · 0 đỏ · `kiem_tai_lieu` 0 chỗ LỆCH |
| Nhật ký | DEV-352 → **DEV-359** trong `docs/md/EIDE-DEV-LOG.md` |
| Công cụ | 130 → **132** (`reg.lookup` là cái mới nhất, chưa lượt Agent nào gọi) |
| Cờ | 10 → **12** (thêm `HOI_QUY_NEN`, `RESUME_TUONG_THUAT` — mặc định TẮT như các cờ kia) |

Bảy việc của đợt này, mỗi việc một dòng:

| # | Mã | DEV | Phá lại thì đỏ | Đo trên dữ liệu thật |
|---|---|---|---|---|
| 24 | M4-09 | 353 | 10/12 | 68 sổ cái · hook im 41 lượt, **1 lượt không có verifier nào** |
| 25 | M4-11 | 354 | 24/32 → **31/34** | 9 kho · bán kính STALE **107 → 49** (58 cáo buộc oan) |
| 28 | M5-03 | 355 | 28/34 → **34/34** | `grep -rni svd src/` ra **2 chỗ**, không bộ đọc nào |
| 29 | M5-05 | 356 | 17/21 → **23/24** | `hop_ly("vdd.max", 25, "°C")` trả `True` |
| 30 | M5-07 | 357 | 15/22 → **22/22** | `2.7 V` → `27v`, nên giá trị `27` đi qua |
| 31 | M5-13 | 358 | 20/23 → **23/23** | 23 kho · một `fact.query` **67 635 → 32 560 token** (−51 %) |
| 32 | M5-17 | 359 | 20/23 → **23/23** | 4 lần nén đạt · **303/313 phiên (96 %)** chưa từng nén |

## Việc đầu tiên của phiên sau: #26 M2-09, rồi #27 M4-13

**Thứ tự ấy là bắt buộc**, không phải sở thích: `M4-13` (P0 · M) khai tiền đề cứng là
`M2-09`, và `M2-09` là **P1 · L** — việc lớn nhất còn lại của GĐ1. Tôi đã bỏ qua nó để làm hết
P0 không bị chặn trước; nay nó là đường duy nhất đi tiếp trong GĐ1.

```bash
git switch -c toi-uu/M2-09        # ĐỪNG quên — xem ghi chú ở cuối
# viết TC TRƯỚC, xem chúng ĐỎ trên mã hiện tại
find src tests -name __pycache__ -type d -exec rm -rf {} +      # bắt buộc, xem DEV-335
.venv/bin/python -m pytest -q -rf            # mốc: 2 030 xanh, 1 skip
.venv/bin/python tools/kiem_tai_lieu.py      # phải 0 chỗ LỆCH CHẮC CHẮN
```

Hai chỗ phải đọc trước khi gõ, cả hai nằm ngay trong mô tả M2-09:

* **Nó cần cờ biên dịch mới** (`-fstack-usage`, `-fcallgraph-info`) và *"Không đổi cờ biên dịch
  của `build.compile`"*. Bài học M4-19 nằm đúng ở đây: **một cờ biên dịch thêm vào là một phép
  đo khác** — `-I` thay vì `-iquote` đã làm 11/12 tệp bị xếp sai. Phải dịch ra thư mục riêng
  (`.eide/build/tinh/`), không chạm ảnh nạp chip.
* **`cppcheck`/`lizard` là phụ thuộc tuỳ chọn** (N-10): thiếu thì nói rõ và rơi về đường cũ,
  **hỏi anh Công trước khi cài**.

Sau #27 thì hai P0 còn lại của cả kế hoạch là **#33 M5-01** (chỉ mục BM25/FTS5 + `doc.search`,
P0 · L) và **#34 M5-04** (trích bảng từ PDF datasheet, P0 · L). Cả hai ở Giai đoạn 2, và **cả
hai gần như chắc chắn cần phụ thuộc mới** (`pdfplumber` cho M5-04) — tức §N-10 bắt hỏi trước.

## Bài học của đợt này, viết ra vì nó lặp BỐN lần liền

Bốn nhiệm vụ liền (M5-03 · M5-07 · M5-13 · M5-17) đều có chỗ LỌT nằm ở **bộ dàn dựng của ca
kiểm**, không ở mã sản phẩm. Bốn hình dạng, cùng một gốc:

1. **Hai vế tình cờ bằng nhau.** Ca kiểm chính của M5-03 ra 4 thanh ghi và 4 trường, nên
   `dem()` trả `(r, r)` vẫn xanh. Một phép đo mà hai vế bằng nhau thì nó không đo được vế nào.
2. **Một tập hợp tình cờ có một phần tử.** `{"ds": [...]}` có **một** khoá, nên phép chia ngân
   sách cho số khoá là phép đồng nhất. Dàn dựng cho một phép CHIA hay một phép CẮT phải có **ít
   nhất hai** phần tử, và chúng phải **khác nhau**.
3. **Một hình dạng tình cờ đã đúng.** Ca âm của M5-13 dựng `source` đã đúng y hình dạng hàm
   gọn trả về, nên hạ trần kích hoạt về 0 cũng không đổi gì.
4. **Ca kiểm không chạy tới dòng nó nói nó canh.** Ca *"transcript hỏng"* của M5-17 chạy trên
   một dự án **chỉ có một phiên**, nên hàm trả rỗng ngay ở bước *"không có phiên nào trước"*.

Cách làm từ nay: **đặt một assertion TRƯỚC phép phá** để khẳng định ca kiểm thật sự chạm tới
chỗ cần đo (`assert ag._tuong_thuat_phien_truoc() != ""` rồi mới monkeypatch).

Và ba lần kế hoạch nói khác thực tế, cả ba chỉ biết nhờ đo trước khi tin:

* **M4-11** — kế hoạch bảo sửa lớp ĐỌC đồ thị phụ thuộc; ba ca kiểm đầu **xanh sẵn**, vì lớp ấy
  đã đúng từ M2-01. Chỗ đứt ở lớp GHI.
* **M4-11** — làm đúng chữ kế hoạch (`upstream = tep_nguon`) thì **tự đẻ ra một ô "còn tươi"
  giả**: `robot-sinhvien2` lưu một tệp nguồn, mà tệp ấy `#include` ba tệp firmware.
* **M5-05 và M5-07** — hai ca kiểm của bảng TC **xanh vì một lý do khác**: `"VDD"` trơn không
  khớp mẫu nào, và `"27"` dài hai ký tự nên luật số-ngắn chặn trước phép so dấu chấm.

Và một lỗi trong chính phép đo, lần thứ bảy của đợt: phép đếm phiên của M5-17 lọc bằng
`'"buoc": "ok"' in line`, mà **sổ cái thật ghi JSON không có khoảng trắng** sau dấu hai chấm —
nên nó trả **100 %** thay vì trả rỗng. Cứu được chỉ vì `grep -c '"compact"'` ra 146 dòng, chỏi
với kết luận *"chưa nén lần nào"*. **Mở dữ liệu thô ra đếm trước khi lọc.**

> **Tôi quên `git switch -c` ở M4-06** và commit thẳng lên `main`; nội dung đúng, quy trình thì
> không. Gõ lệnh mở nhánh **trước khi** viết dòng mã đầu tiên.

## Mười ba thứ phải đọc trước khi gõ dòng đầu tiên

1. **Xoá `__pycache__` trước mỗi phép “phá lại thì đỏ”.** Một phép phá dài **đúng bằng** mã
   gốc (`0.6` → `0.0`) làm Python coi `.pyc` cũ là còn hợp lệ, và phép đo chạy **mã khác với
   mã trong tệp** — DEV-335.
2. **“Phá lại thì đỏ N/N” nói được điều gì chỉ khi tập phép phá không do người đang mong nó
   đẹp chọn ra.** M3-13 khai 6/6; phá bằng tập rộng hơn ra **7/9**. Lượt đầu của mười sáu việc
   gần nhất: 7/9 · 18/20 · 17/24 · 22/27 · 15/20 · 7/13 · 15/22 · 18/22 · 34/36 · 10/12 ·
   24/32 · 28/34 · 17/21 · 15/22 · 20/23 · 20/23. Cách dựng tập: đọc `git diff`, không đọc ký
   ức — đi theo *chỗ mã tháo được*, không theo *chỗ mình biết đã có ca canh*. Và mỗi nhánh `if`
   của một hàm là **một** chỗ, không phải cả hàm là một chỗ.
3. **Chỗ có HAI LỚP PHÒNG thì chỉ phép phá GỘP nói được gì.** Tháo riêng từng lớp không đổi
   hành vi, nên nó báo LỌT oan. Trúng ở M4-11 (`dedupe` + trần-đếm-lượt — gộp lại thì vòng lặp
   **treo 900 giây** thay vì đỏ) và M5-03 (`p.is_file()` + `ung.is_file()`). Khuôn script nhận
   một **danh sách cặp** để áp nhiều chỗ cùng lúc.
4. **Phép đo phải biến cái TREO thành chữ ĐỎ.** pytest không có đồng hồ cho từng ca, nên một ca
   treo **không phải** một ca đỏ — và nó giết luôn mọi phép phá còn lại. Ca kiểm vòng `#include`
   nay chạy trong một **luồng có đồng hồ** (`join(timeout=5)`), và khuôn script coi quá hạn
   180 s là một chữ ĐỎ.
5. **Kế hoạch có chỗ sai, hoặc thiếu chỗ; đo trước khi tin.** Chín lần trong 30 việc — xem mục
   *"ba lần kế hoạch nói khác thực tế"* ở trên, cộng sáu lần cũ: A2.5 đã có chủ (M2-02) · mã
   lỗi ghi nhầm E6010 (M2-06) · regex PASS/FAIL từ chối oan 588/846 (M3-12) · “phần dài nằm ở
   mô tả tham số” chỉ đúng một nửa (M1-02) · mã lỗi E4031 đã có chủ (M3-18) · khoá Fact chân
   kit ghi `chuc_nang` mà mã ghi `ten`/`net`/`af` (M3-18).
6. **Phạm vi phép đo sai thì ra một con số *hợp lý* chứ không ra rỗng** — và lúc ấy nó tốn
   nhiều lượt hơn. Ba lần: ghép mọi mạng cổng với mọi `.cst` ra “409 lỗi” trong khi số thật là
   **1**; phép quét tệp `.cst` thu 4 trong 7 tệp mà ca kiểm vẫn xanh (M3-18); và phép đếm phiên
   của M5-17 trả **100 %** vì so chuỗi JSON có khoảng trắng (DEV-359).
7. **Soi đúng một dòng, đừng soi cả khối.** `assert "TỰ KHAI" in str(khoi)` vẫn xanh khi tôi
   phá chữ ấy ở dòng *Kết luận* — vì `summary` của khối cũng chứa nó (M4-01). Cùng hình dạng ở
   M5-17: `` `target.flash` → E4040 `` cũng có ở dòng *Lỗi cuối cùng*.
8. **Kiểm lại chính PHÉP PHÁ của mình.** Năm lần: `them = [] or [[…]]` (M4-01), `cu = cu or ""`
   và bỏ `is_file()` ở cùng một dòng (M4-02), `break` thay `continue` trong một vòng lặp **một
   phần tử** (M5-05), và hai *guard chết* `res.ok` (M4-09, M4-11) — `_one_tool` đã `return`
   trước đó, và không `ToolResult(False)` nào trong `src/eide` thiếu `error=`. Trước khi tin
   một chữ LỌT: phép phá ấy có thật sự đổi hành vi không?
9. **Một luật `policy.yaml` mới trỏ tới nhóm dữ kiện chưa khai thì DỪNG CẢ LƯỢT** (M4-02).
10. **CHẠY phép đo trên dữ liệu thật, đừng chỉ đọc mã.** M4-05 là nhiệm vụ nhỏ nhất của đợt và
   tìm ra **bốn** lỗi, ba trong số đó ngoài việc được giao và cả ba chỉ lộ ra ở lượt chạy đầu
   trên firmware thật.
11. **Luật đúng mà nằm trong một closure thì không ca kiểm nào với tới** (M4-05).
12. **Một cờ biên dịch thêm vào là một phép đo khác.** `-I` thay vì `-iquote` làm **11 trong
   12** tệp bị xếp là *"không dịch được trên máy chủ"* (M4-19). **Đọc lại mục này trước khi làm
   M2-09** — nó thêm `-fstack-usage` và `-fcallgraph-info`.
13. **So PHIÊN BẢN, đừng so đồng hồ.** `updated_at` của kho có độ phân giải thô (M4-06). Và một
   ca kiểm nêu đúng bất biến mà kiểm **một tên gõ sẵn** thì nó xanh suốt — bất biến dạng *"mọi
   X đều phải có trong Y"* phải viết thành **phép so hai tập hợp** (M4-07).

## Việc còn MỞ, không thuộc nhiệm vụ nào trong 106

* **Mười hai cờ đều còn TẮT** — `GON_CONG_CU` · `TRUY_VET` · `REQ_PHU` · `REQ_CHAT_LUONG` ·
  `KE_HOACH_CONG_KIEM` · `ERC_TU_DONG` · `SIM_RUNNER_GIOI_HAN` · `TEST_HARDEN` ·
  `VERIFIER_GOI_BANG_CHUNG` · `HOI_QUY_NEN` · `RESUME_TUONG_THUAT` (và `SCHEMATIC` từ trước).
  Tất cả đổi thứ Agent **nhìn thấy, đọc, hoặc LÀM ĐƯỢC mỗi lượt**, nên chỉ bộ 76 ca chạy **hai
  chế độ** mới nói được chúng làm Agent khá hơn hay tệ hơn. Bộ ấy tốn tiền mô hình nên §3.0 bắt
  **hỏi người dùng trước**.
* **Bốn công cụ mới nhất chưa lượt Agent nào GỌI** — `hdl.sensitivity` ·
  `hdl.constraints_check` · `test.criteria` · `reg.lookup`. Mã của cả bốn đã chạy trên hiện vật
  thật, nhưng đó là tôi gọi hàm, không phải tác tử gọi công cụ. README §8 đếm cả bốn vào phần
  chưa dùng thật.
* **Chưa có tệp `.svd` THẬT nào trên máy** — quét cả máy 09/10/2026 không thấy tệp nào ngoài
  tệp do chính bộ kiểm sinh trong `tmp`. Ca `test_nap_duoc_SVD_THAT` đã viết, đánh `nha_that` +
  `skipif`, dò bốn chỗ hay có và **SKIP**. Nên con số *"nạp được N thanh ghi của một chip
  thật"* chưa có — và tôi không tự viết một SVD lớn rồi gọi nó là *thật*.
* **Chỉ số *"không lượt nào tuyên xong khi còn kết quả lỗi thời"* chưa đóng được** — cửa chặn đã
  có và có 28 ca kiểm, nhưng con số ấy đòi **phát lại** phiên mẫu với cửa mới: sổ cái ghi lời
  gọi và dấu hiệu hook đã nổ, mà **không** ghi trạng thái kho tại thời điểm ấy. Phát lại tốn
  tiền mô hình.
* **Chưa dự án firmware nào trong repo có một con số độ nhạy đáng tin** — `rtos-sinhvien`
  **0/12 tệp** đo được; `stm32f469-freertos` và `thu-nghiem-g6` có bộ kiểm **ĐỎ SẴN**. Đây là
  trạng thái của dữ liệu đo, không phải lỗi sản phẩm. DEV-348 · DEV-349.
* **`chay(None)` của `test.sensitivity` chỉ dịch tệp TEST**, nên một tệp test gọi hàm sản phẩm
  làm mốc ĐỎ và cả phép đo dừng trước khi vào vòng đột biến. Trúng **ba** lần (M4-01, M4-19,
  M4-04). Chưa sửa: nó là một quyết định thiết kế, nhưng là chỗ hẹp nhất của cả mảng.
* **`POL-N6-sua-test` chưa nổ trên một phiên thật nào** — hook `sua_test_sau_do` cấp dữ kiện cho
  lời gọi **sắp** xảy ra, nên không soát lại được phiên đã lưu. Có 25 ca kiểm và phá lại 27/27.
* **Chưa kho nào có tiêu chí unit test** — loại hiện vật `criteria:unit-*` vừa mới tồn tại
  (DEV-346), nên `test.run` ở mọi dự án đang có vẫn đi đường **tự khai**.
* **`kiem_cap_goi_tra()` chưa thành hàng rào** — soát được mọi phiên đã lưu, nhưng chưa hook nào
  gọi tự động: bắt được chuyện cũ, chưa chặn được chuyện mới.
* **Ba luật kiểm chưa nổ được trên dữ liệu thật vì thiếu dữ liệu, không vì sai** — luật ERC quá
  áp, `chan_lech_kit` và `io_type_lech_bank`: **không kho nào** có Fact `pin:tangnano20k.*` hay
  khoá `vccio`.
* **Một bitstream cũ đã dựng với chân đồng hồ do nextpnr tự chọn** — `blinky` của
  `du-lieu/riscv-tn20k-b`. Nó rơi đúng chân 4 nên có thể đã chạy đúng — bằng may. Không sửa
  hiện vật cũ; từ nay `dat_di_day` chặn trước nextpnr. DEV-345 · README §8.
* **Testbench nấc 3c của Bài 3 không dịch nổi từ 02/10/2026** — `tb_pcpi_vmini.v` tạo thực thể
  `bram` với năm cổng của **bản hai cổng**, mà `rtl/bram.v` đã đưa về một cổng. Bài 3 đã ở ngoài
  đường dựng nên **chưa sửa**. DEV-344.
* **Lỗi `_go_dau` trong `src/eide/tools/design.py`** — viết `.replace("d", "d")` nên `"ổn định"`
  và `"ON DINH"` không khớp nhau; hàm ấy đang dùng cho một phép kiểm an toàn. Tìm thấy ở M2-03,
  **chưa sửa** vì ngoài phạm vi.
* **Cột “Mã nguồn” của ma trận truy vết trống ở mọi dự án** — nó đọc `hien_thuc_req`, trường vừa
  mới tồn tại nên chưa dự án nào có.
* **`req-critic`** (bước 4 của M2-03) — kế hoạch ghi “tuỳ chọn, gộp M2-13”. Chưa làm, đúng theo
  kế hoạch.
* **Gói bằng chứng chưa lần nào tới một MÔ HÌNH thật.** Nó dựng được trên 29/42 dự án và đọc rất
  rõ với người, nhưng *"verifier đọc gói này có bác đúng hơn không"* là một câu hỏi về **hành vi
  mô hình**, và nó chưa được đo. Cần M4-22 (bộ ca gài lỗi) rồi hỏi anh Công.
* **`loc_claim` là một phép lọc văn xuôi, và nó leaky có số đo.** 95 trong 1 706 câu của 323 đề
  bài thật. Đừng nhầm nó với hàng rào — hàng rào là gói bằng chứng do mã dựng.
