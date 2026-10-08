# ĐANG LÀM — chỗ dừng khuya 08/10/2026

> Tệp này trả lời đúng một câu cho phiên sau: **mở ra là làm tiếp được từ đâu.**
> Trạng thái đầy đủ của 106 việc nằm ở `EIDE_Toi_uu_Agent_2026-10-06.xlsx`,
> sheet **“Tiến độ 08-10-2026 (khuya)”** (cột Q, T–Y của sheet “Danh mục tối ưu” là bằng
> chứng từng việc). Ba sheet “Tiến độ 08-10-2026”, “… (chiều)”, “… (toi)” là ảnh chụp sáng,
> chiều và tối, giữ lại để so.

## Đang ở đâu

| | |
|---|---|
| **Xong** | **19/106** — việc #1 → #19 của Giai đoạn 1, theo đúng thứ tự `#` của kế hoạch |
| **Đang dở** | **không có.** `main` = `a3228c5`, đã đẩy. Mọi nhánh `toi-uu/*` đã gộp. |
| Ca kiểm | 1 610 → **1 835** xanh, 0 đỏ · `swift test` 43 · `kiem_tai_lieu` 0 chỗ LỆCH |
| Nhật ký | DEV-330 → **DEV-348** trong `docs/md/EIDE-DEV-LOG.md` |
| Công cụ | 127 → **130** (`hdl.sensitivity`, `hdl.constraints_check`, `test.criteria`) |
| Cờ | 7 → **8** (thêm `SIM_RUNNER_GIOI_HAN`, mặc định TẮT như sáu cờ kia) |

## Việc đầu tiên của phiên sau: #20 M4-19

Đột biến trên **bản sao**, không ghi đè tệp sản phẩm của người dùng — P2 · S, không cờ, không
tiền đề (M4-04, M4-12, M4-16 dựa trên nó). Mở `KE-HOACH-SUA-VA-KIEM-THU.md`, mục `[M4-19]`,
làm đúng quy trình §3.1:

```bash
git switch -c toi-uu/M4-19
# viết TC TRƯỚC, xem chúng ĐỎ trên mã hiện tại
find src tests -name __pycache__ -type d -exec rm -rf {} +      # bắt buộc, xem DEV-335
.venv/bin/python -m pytest -q -rf            # mốc: 1835, không ca cũ nào đỏ
.venv/bin/python tools/kiem_tai_lieu.py      # phải 0 chỗ LỆCH CHẮC CHẮN
```

M4-19 vá cái rủi ro mà M4-05 vừa phải lách quanh suốt: phép đo độ nhạy **ghi đè tệp sản phẩm
thật** rồi trả lại trong `finally`, nên mọi lượt đo của tôi hôm nay đều phải chạy trên một bản
sao trong scratchpad. `finally` chỉ đỡ được ngoại lệ Python — một lần `Ctrl-C` hay một lần máy
chết giữa vòng đo sẽ để lại mã đã bị phá trong dự án. Kế hoạch có nêu cái bẫy ở bước 3: sao
tệp ra thư mục tạm thì `#include "x.h"` tương đối đứt, nên `chay_test` cần thêm `them_co`
(`-I`).

Hết Giai đoạn 1 mới chạy **cổng cuối giai đoạn (§4.2)**, không phải sau mỗi việc.
Nhớ: công cụ mới nào cũng làm README lệch số công cụ — sửa 4 chỗ (dòng ~43 tổng + số bật
mặc định, dòng bảng nhóm việc, dòng ~1041 phần chưa dùng thật, dòng ~1180 cây mã). Cờ mới
thì README không đếm, nhưng Excel có ô "Cờ tính năng mới" phải sửa.

## Chín thứ phải đọc trước khi gõ dòng đầu tiên

1. **Xoá `__pycache__` trước mỗi phép “phá lại thì đỏ”.** Một phép phá dài **đúng bằng** mã
   gốc (`0.6` → `0.0`) làm Python coi `.pyc` cũ là còn hợp lệ, và phép đo chạy **mã khác với
   mã trong tệp** — DEV-335.
2. **“Phá lại thì đỏ N/N” nói được điều gì chỉ khi tập phép phá không do người đang mong nó
   đẹp chọn ra.** M3-13 khai 6/6; phá bằng tập rộng hơn ra **7/9**. M3-18 ra **18/20** và
   M4-01 ra **17/24**, M4-02 ra **22/27** ở lượt đầu. Cách dựng tập: đọc `git diff`, không
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
   là **tiền đề** của chính nhiệm vụ. Những chỗ ấy chỉ hiện ra khi đọc mã quanh nó, hoặc khi
   chạy phép đo thật.
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

## Việc còn MỞ, không thuộc nhiệm vụ nào trong 106

* **Bảy cờ mới đều còn TẮT** — `GON_CONG_CU` · `TRUY_VET` · `REQ_PHU` · `REQ_CHAT_LUONG` ·
  `KE_HOACH_CONG_KIEM` · `ERC_TU_DONG` · `SIM_RUNNER_GIOI_HAN`. Cả bảy đổi thứ Agent **nhìn
  thấy, đọc, hoặc LÀM ĐƯỢC mỗi lượt**, nên chỉ bộ 76 ca chạy **hai chế độ** mới nói được chúng
  làm Agent khá hơn hay tệ hơn. Bộ ấy tốn tiền mô hình nên §3.0 bắt **hỏi người dùng trước**.
* **Ba công cụ mới nhất chưa lượt Agent nào GỌI** — `hdl.sensitivity` ·
  `hdl.constraints_check` · `test.criteria`. Mã của cả ba đã chạy trên hiện vật thật, nhưng đó
  là tôi gọi hàm, không phải tác tử gọi công cụ. README §8 đếm cả ba vào phần chưa dùng thật.
* **Chưa dự án firmware nào trong repo có một con số độ nhạy đáng tin** — đo 08/10/2026 trên
  cả ba dự án có cả `test/` lẫn `firmware/`: `rtos-sinhvien` **0/12 tệp** đo được (4 tệp font
  `khong_thay`, `control_rtos.c` trùng ký hiệu, `main.c` không dịch trên máy chủ,
  `logo_ptit.c` mọi mutant hỏng biên dịch); `stm32f469-freertos` và `thu-nghiem-g6` có bộ
  kiểm **ĐỎ SẴN**. Đây là trạng thái của dữ liệu đo, không phải lỗi sản phẩm. DEV-348.
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
