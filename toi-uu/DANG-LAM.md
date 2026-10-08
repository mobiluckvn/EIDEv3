# ĐANG LÀM — chỗ dừng tối 09/10/2026

> Tệp này trả lời đúng một câu cho phiên sau: **mở ra là làm tiếp được từ đâu.**
> Trạng thái đầy đủ của 106 việc nằm ở `EIDE_Toi_uu_Agent_2026-10-06.xlsx`,
> sheet **“Tiến độ 09-10-2026 (toi)”** (cột Q, T–Y của sheet “Danh mục tối ưu” là bằng
> chứng từng việc). Các sheet “Tiến độ 08-10-2026” + ba biến thể, và “Tiến độ 09-10-2026”,
> là ảnh chụp các mốc trước, giữ lại để so.

## Đang ở đâu

| | |
|---|---|
| **Xong** | **22/106** — việc #1 → #22 của Giai đoạn 1. Việc #22 còn **một tiêu chí chưa đạt** (xem dưới) |
| **Đang dở** | **không có.** `main` = `f829ddb`, đã đẩy. Mọi nhánh `toi-uu/*` đã gộp. |
| Ca kiểm | 1 610 → **1 878** xanh, 0 đỏ · `swift test` 43 · `kiem_tai_lieu` 0 chỗ LỆCH |
| Nhật ký | DEV-330 → **DEV-351** trong `docs/md/EIDE-DEV-LOG.md` |
| Công cụ | 127 → **130** (`hdl.sensitivity`, `hdl.constraints_check`, `test.criteria`) |
| Cờ | 7 → **9** (thêm `SIM_RUNNER_GIOI_HAN`, `TEST_HARDEN` — mặc định TẮT như các cờ kia) |

## Việc đầu tiên của phiên sau: #23 M4-07

Verifier nhận **gói bằng chứng do EIDE dựng từ sổ cái**, không nhận đề bài tác tử chính tự
viết — P0 · M, **có cờ** `VERIFIER_GOI_BANG_CHUNG`, không tiền đề. Mở
`KE-HOACH-SUA-VA-KIEM-THU.md`, mục `[M4-07]`, làm đúng quy trình §3.1:

```bash
git switch -c toi-uu/M4-07        # ĐỪNG quên bước này — xem ghi chú dưới
# viết TC TRƯỚC, xem chúng ĐỎ trên mã hiện tại
find src tests -name __pycache__ -type d -exec rm -rf {} +      # bắt buộc, xem DEV-335
.venv/bin/python -m pytest -q -rf            # mốc: 1878, không ca cũ nào đỏ
.venv/bin/python tools/kiem_tai_lieu.py      # phải 0 chỗ LỆCH CHẮC CHẮN
```

> **Tôi quên `git switch -c` ở M4-06** và commit thẳng lên `main`; nội dung đúng, quy trình thì
> không. Đã dựng lại con trỏ `toi-uu/M4-06` tại đúng commit `f829ddb`. Gõ lệnh mở nhánh **trước
> khi** viết dòng mã đầu tiên, đừng để nó là bước nhớ sau.

## Việc còn NỢ của #22 M4-06 — một tiêu chí chưa đạt

`[M4-06]` đã ☑ nhưng **một tiêu chí xong còn để mở**, và nó cần anh Công quyết:

* Tiêu chí: *"mutation score trên dự án mẫu **tăng** sau harden"*.
* Đã có phần **trước**: `du-lieu/rtos-sinhvien`, `logo_ptit.c` → điểm **0,0** · 30 mutant ·
  20 sống · 18 s.
* Phần **sau** chưa đo, hai lý do: chạy `test.harden` thật cần **lời gọi mô hình** và §3.0 bắt
  hỏi người dùng trước; và dự án ấy **không có chỗ để đo** — tệp duy nhất đáng nâng
  (`control_rtos.c`) là `khong_nap_duoc` vì tệp test `#include` chính tệp `.c` đó, còn sáu tệp
  kia là bitmap (không ca kiểm nào giết được một đột biến một byte trong logo).
* Nên cờ `TEST_HARDEN` giữ **TẮT**. Muốn đóng tiêu chí này thì cần một dự án mẫu có bộ kiểm
  **đo được** — hoặc sửa chỗ hẹp `chay(None)` nói ở phần việc còn mở.

## Mười hai thứ phải đọc trước khi gõ dòng đầu tiên

1. **Xoá `__pycache__` trước mỗi phép “phá lại thì đỏ”.** Một phép phá dài **đúng bằng** mã
   gốc (`0.6` → `0.0`) làm Python coi `.pyc` cũ là còn hợp lệ, và phép đo chạy **mã khác với
   mã trong tệp** — DEV-335.
2. **“Phá lại thì đỏ N/N” nói được điều gì chỉ khi tập phép phá không do người đang mong nó
   đẹp chọn ra.** M3-13 khai 6/6; phá bằng tập rộng hơn ra **7/9**. M3-18 ra **18/20** và
   M4-01 ra **17/24**, M4-02 ra **22/27**, M4-05 ra **15/20**, M4-19 ra **7/13**, M4-04 ra
   **15/22**, M4-06 ra **18/22** ở lượt đầu. Cách dựng tập: đọc `git diff`, không
   đọc ký ức — đi theo
   *chỗ mã tháo được*, không theo *chỗ mình biết đã có ca canh*. Và mỗi nhánh `if` của một hàm
   là **một** chỗ, không phải cả hàm là một chỗ.
3. **Kế hoạch có chỗ sai, hoặc thiếu chỗ; đo trước khi tin.** Sáu lần sai trong 18 việc:
   A2.5 đã có chủ (M2-02) ·
   mã lỗi ghi nhầm E6010 (M2-06) · regex PASS/FAIL từ chối oan 588/846 (M3-12) · “phần dài
   nằm ở mô tả tham số” chỉ đúng một nửa (M1-02) · mã lỗi E4031 đã có chủ ở `loop.py`
   (M3-18) · khoá Fact chân kit kế hoạch ghi `chuc_nang`, mã ghi `ten`/`net`/`af` (M3-18).
   Và ba nhiệm vụ gần nhất không sai mà **thiếu**: M4-01 không nêu cổng E4023 cho đường unit
   test, không nêu `surfaces.py`; M4-02 không nêu `policy/engine.py`, không nêu
   `POL-QUAL-criteria-change`, không nêu nhánh *số chỗ canh không đổi thì im*; M4-05 ghi "tệp
   chạm tới" là `dot_bien.py` + tests, mà thật ra phải sửa cả `build/hdl.py`,
   `tools/xay_dung.py`, `tools/hdl.py` — và một trong ba lỗi phụ (`mo_phong` chạy lại tệp cũ)
   là **tiền đề** của chính nhiệm vụ; M4-19 ghi cờ dịch là `-I`, mà `-I` che header hệ thống
   nên phải là `-iquote`. Những chỗ ấy chỉ hiện ra khi đọc mã quanh nó, hoặc khi chạy phép đo
   thật.
4. **Phạm vi phép đo sai thì ra một con số *hợp lý* chứ không ra rỗng** — và lúc ấy nó tốn
   nhiều lượt hơn. Hai lần trong M3-18: ghép mọi mạng cổng với mọi `.cst` ra “409 lỗi” trong
   khi số thật là **1**; và phép quét tệp `.cst` thật thu 4 trong 7 tệp mà ca kiểm vẫn xanh.
5. **Soi đúng một dòng, đừng soi cả khối.** `assert "TỰ KHAI" in str(khoi)` của tôi vẫn xanh
   khi tôi phá chữ ấy ở dòng *Kết luận* — vì `summary` của khối cũng chứa nó. Phép phá bắt
   được, ca kiểm thì không (M4-01).
6. **Kiểm lại chính PHÉP PHÁ của mình.** Ba lần trong hai nhiệm vụ: `them = [] or [[…]]`
   (M4-01), rồi `cu = cu or ""` và bỏ `is_file()` ở cùng một dòng (M4-02) — cả ba **không đổi
   hành vi**, nên chúng báo LỌT oan và suýt làm tôi viết ca kiểm cho những chỗ vốn đã được
   canh. Trước khi tin một chữ LỌT: phép phá ấy có thật sự đổi hành vi không? Chỗ có **hai**
   lớp phòng (`is_file()` **và** `except OSError`) thì phải tháo cả hai mới phá được. Từ M4-05
   script phá **tự kiểm**: so byte trước–sau và in `[VÔ HIỆU]` thay vì chạy bộ kiểm — nên dùng
   lại script ấy (`scratchpad/pha_lai_m4_05.py`) làm khuôn.
7. **Một luật `policy.yaml` mới trỏ tới nhóm dữ kiện chưa khai thì DỪNG CẢ LƯỢT**, không phải
   "không nổ": `_eval` ném `ValueError`, và `_env` có một danh sách *"nhóm phải luôn tồn tại"*.
   Thêm luật thì thêm nhóm vào danh sách ấy — không thì công cụ mà luật khớp tới đổ hết
   (M4-02).
8. **CHẠY phép đo trên dữ liệu thật, đừng chỉ đọc mã.** M4-05 là nhiệm vụ nhỏ nhất của đợt
   (P1 · S) và tìm ra **bốn** lỗi — ba trong số đó ngoài việc được giao, và cả ba chỉ lộ ra ở
   lượt chạy đầu trên firmware thật: phép đo **đổ** `IndexError`, `mo_phong` chạy lại
   `sim.vvp` **cũ** khi biên dịch đổ, và `loi_nguoi_doc` khen một chỗ trống. Đọc mã không bắt
   được cái nào.
9. **Luật đúng mà nằm trong một closure thì không ca kiểm nào với tới.** Bốn chỗ LỌT của M4-05
   cùng hình dạng ấy: luật gắn tiền tố nằm trong hai closure (gom về `ket_qua_chay` thì đo
   được ngay), nhánh stillborn của đường HDL không dựng nổi ca qua bảng phép mặc định (mở
   tham số `bang`), và ba chỗ **báo lại** của một công cụ mà mọi ca cũ đều đi qua với
   `stillborn == 0`. Tầng báo lại hỏng theo kiểu riêng: phép đo đúng, con số đúng, rồi con số
   không đi tới đâu.
10. **Một cờ biên dịch thêm vào là một phép đo khác.** `-I` thay vì `-iquote` làm `stdio.h`
   giả của bo che bản hệ thống, và **11 trong 12** tệp bị xếp là *"không dịch được trên máy
   chủ"* — tôi thêm một cờ để tránh một cáo buộc sai và sinh ra mười một cáo buộc sai khác.
   Gắn cờ cho **lượt mốc** thì tệ hơn nữa: nó đổi chính cái mốc mà mọi so sánh dựa vào, và cả
   ba dự án thật thành "không đo được" (M4-19). Trước khi thêm một cờ: nó đổi đường tìm của
   `"..."` hay của cả `<...>`, và nó có vào lượt mốc không.
11. **Một nhánh `if` không đổi hành vi thì bỏ đi, đừng viết ca cho nó.** Sau khi đổi sang
   `-iquote`, cái guard *"chỉ gắn cờ cho lượt có tệp sản phẩm"* thành vô nghĩa — phép phá chỉ
   ra đúng điều đó bằng một chữ LỌT, và câu trả lời là bỏ nhánh, không phải dựng một ca kiểm
   contrived để che nó. Trúng lần nữa ở M4-04 với bước sắp xếp trước khi lấy mẫu.
12. **So PHIÊN BẢN, đừng so đồng hồ.** `updated_at` của kho có độ phân giải thô, nên hai lần
   ghi trong cùng một giây **bằng nhau** và phép so "mới hơn" im lặng sai — ca kiểm đầu tiên
   của hook M4-06 đỏ ngay vì chuyện ấy. Hiện vật nào cần biết "thứ kia đã đổi chưa" thì ghi
   kèm **số phiên bản** của thứ kia (`version_test`), rồi so con số. Một số phiên bản là dữ
   kiện chính xác; một cái đồng hồ thì không.

## Việc còn MỞ, không thuộc nhiệm vụ nào trong 106

* **Bảy cờ mới đều còn TẮT** — `GON_CONG_CU` · `TRUY_VET` · `REQ_PHU` · `REQ_CHAT_LUONG` ·
  `KE_HOACH_CONG_KIEM` · `ERC_TU_DONG` · `SIM_RUNNER_GIOI_HAN`. Cả bảy đổi thứ Agent **nhìn
  thấy, đọc, hoặc LÀM ĐƯỢC mỗi lượt**, nên chỉ bộ 76 ca chạy **hai chế độ** mới nói được chúng
  làm Agent khá hơn hay tệ hơn. Bộ ấy tốn tiền mô hình nên §3.0 bắt **hỏi người dùng trước**.
* **Ba công cụ mới nhất chưa lượt Agent nào GỌI** — `hdl.sensitivity` ·
  `hdl.constraints_check` · `test.criteria`. Mã của cả ba đã chạy trên hiện vật thật, nhưng đó
  là tôi gọi hàm, không phải tác tử gọi công cụ. README §8 đếm cả ba vào phần chưa dùng thật.
* **Chưa dự án firmware nào trong repo có một con số độ nhạy đáng tin** — đo lại 09/10/2026
  bằng đường bản sao, và đo thêm bằng chế độ chi tiết (điểm **0,0** trên 180 mutant, 110 s): `rtos-sinhvien` **0/12 tệp** đo được (4 tệp
  font `khong_thay`, `control_rtos.c` trùng ký hiệu, `main.c` không dịch trên máy chủ,
  `logo_ptit.c` mọi mutant hỏng biên dịch); `stm32f469-freertos` và `thu-nghiem-g6` có bộ kiểm
  **ĐỎ SẴN**. Đây là trạng thái của dữ liệu đo, không phải lỗi sản phẩm. DEV-348 · DEV-349.
* **`chay(None)` của `test.sensitivity` chỉ dịch tệp TEST, nên một tệp test gọi hàm sản phẩm
  làm mốc ĐỎ** và cả phép đo dừng trước khi vào vòng đột biến. Tức phép đo chỉ chạy được khi
  tệp test **tự dịch được một mình** — mà một tệp test tự định nghĩa lại hàm sản phẩm thì đúng
  là cái ô xanh giả phép đo này đi tìm. Trúng **ba** lần (M4-01, M4-19, M4-04) khi dựng ca
  kiểm, và lần thứ ba nặng hơn: tệp duy nhất đáng đo của `rtos-sinhvien` —
  `control_rtos.c` — là `khong_nap_duoc` vì tệp test `#include` chính tệp `.c` đó, nên phép đo
  tái hiện DANH-GIA §2.2 phải đi **đường riêng**, không qua công cụ. Chưa sửa: nó là một
  quyết định thiết kế của `test.sensitivity`, không phải một lỗi — nhưng nó là chỗ hẹp nhất
  của cả mảng, và M4-06 sẽ đụng ngay vào nó.
* **`POL-N6-sua-test` chưa nổ trên một phiên thật nào** — hook `sua_test_sau_do` cấp dữ kiện
  cho lời gọi **sắp** xảy ra, nên không soát lại được phiên đã lưu như mọi phép đo trước của
  đợt này. Nó có 25 ca kiểm và phá lại 27/27, nhưng chưa lượt tác tử thật nào chạm vào.
* **Chưa kho nào có tiêu chí unit test** — loại hiện vật `criteria:unit-*` vừa mới tồn tại
  (DEV-346), nên `test.run` ở mọi dự án đang có vẫn đi đường **tự khai**: tệp test tự in `dat`.
  Đường EIDE-phán đã thông và đã đo, chỉ chưa dự án nào dùng. Cùng hình dạng với hai luật kiểm
  chân FPGA bên dưới.
* **`kiem_cap_goi_tra()` chưa thành hàng rào** — soát được mọi phiên đã lưu, nhưng chưa hook
  nào gọi tự động: bắt được chuyện cũ, chưa chặn được chuyện mới.
* **Ba luật kiểm chưa nổ được trên dữ liệu thật vì thiếu dữ liệu, không vì sai:**
  luật ERC quá áp (ba kho có Fact điện áp thì không có mô hình mạch, và ngược lại), rồi
  `chan_lech_kit` và `io_type_lech_bank` của M3-18 — **không kho nào** trong repo có Fact
  `pin:tangnano20k.*` hay khoá `vccio`. Cả ba đã có đường dẫn đo được, chỉ chưa ai nạp dữ liệu.
* **Một bitstream cũ đã dựng với chân đồng hồ do nextpnr tự chọn** — `blinky` của
  `du-lieu/riscv-tn20k-b`: cổng `sys_clk` không có `IO_LOC` ở bất kỳ tệp `.cst` nào, mà
  `blinky.fs` 4,6 MB vẫn dựng ra 01/10/2026. Nó rơi đúng chân 4 nên có thể đã chạy đúng —
  bằng may. Không sửa hiện vật cũ; từ nay `dat_di_day` chặn trước nextpnr. DEV-345 · README §8.
* **Testbench nấc 3c của Bài 3 không dịch nổi từ 02/10/2026** — `tb_pcpi_vmini.v` tạo thực thể
  `bram` với năm cổng `b_*` của **bản hai cổng**, mà `rtl/bram.v` đã đưa về một cổng (có lý do
  ghi sẵn trong tệp: bản hai cổng làm suy luận BSRAM đứt). `bai3/NGOAI-PHAM-VI.md` vẫn ghi
  “độ nhạy 7/7” — con số ấy đúng lúc được viết và hết hiệu lực từ hôm `bram.v` đổi. Bài 3 đã
  ở ngoài đường dựng nên **chưa sửa**. DEV-344.
* **Lỗi `_go_dau` trong `src/eide/tools/design.py`** — viết `.replace("d", "d")` nên
  `"ổn định"` và `"ON DINH"` không khớp nhau; hàm ấy đang dùng cho một phép kiểm an toàn
  (*người có thật sự chọn không*). Tìm thấy ở M2-03, **chưa sửa** vì ngoài phạm vi.
* **Cột “Mã nguồn” của ma trận truy vết trống ở mọi dự án** — nó đọc `hien_thuc_req`, trường
  vừa mới tồn tại nên chưa dự án nào có.
* **`req-critic`** (bước 4 của M2-03) — kế hoạch ghi “tuỳ chọn, gộp M2-13”. Chưa làm, đúng
  theo kế hoạch.
