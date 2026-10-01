# Công thức LaTeX ra tài liệu — tệp để anh mở ra kiểm

Anh Công báo: *"Bản xuất tài liệu của Agent đang lỗi không render latex ra file docx, pdf và
pptx"*. Thư mục này có **nguồn** và **bốn tệp dựng từ chính nguồn ấy** bằng `doc.render` —
đúng công cụ tác tử dùng, không phải một đường riêng cho bài đo.

| Tệp | Mở bằng |
|---|---|
| [`nguon.md`](nguon.md) | bất cứ trình xem văn bản nào — đây là **đầu vào** |
| [`THU-CONG-THUC.pdf`](THU-CONG-THUC.pdf) | Preview · dễ kiểm nhất, xem được ngay |
| [`THU-CONG-THUC.docx`](THU-CONG-THUC.docx) | Word / Pages / LibreOffice |
| [`THU-CONG-THUC.pptx`](THU-CONG-THUC.pptx) | Keynote / PowerPoint — 10 slide |
| [`THU-CONG-THUC.xlsx`](THU-CONG-THUC.xlsx) | Numbers / Excel — chỉ bảng ở mục 4 |

Dựng lại bất cứ lúc nào:

```bash
.venv/bin/python -c "
import sys, pathlib; sys.path.insert(0,'src')
from eide.xuat_ban import render
md = pathlib.Path('docs/review-v3/test/ket-qua-cong-thuc/nguon.md')
for dd, ra in (('docx','THU-CONG-THUC.docx'), ('pdf','THU-CONG-THUC.pdf'),
               ('pptx','THU-CONG-THUC.pptx'), ('xlsx','THU-CONG-THUC.xlsx')):
    print(ra, render(md.read_text('utf-8'), md.parent/ra, dd, goc_anh=md.parent).dat)"
```

## Kiểm cái gì

Nguồn cố ý đặt công thức ở **sáu ngữ cảnh khác nhau**, vì trước bản vá chỉ **một** trong sáu
chỗ chạy được — và đúng cái chỗ ấy lại là chỗ dễ thử nhất, nên lỗi sống lâu.

| Mục | Phải thấy trên giấy | Không được thấy |
|---|---|---|
| 1 · nguyên một đoạn | `f_VCO = f_in × PLLN/PLLM`, căn giữa, nghiêng | `$$`, `\times`, `\frac` |
| 2 · giữa dòng | `f_out ≤ 180 MHz` · `PLLP ∈ {2,4,6,8}` · `Δφ ≈ ± 2°` | `\leq` `\in` `\{` `^{\circ}` |
| 3 · gạch đầu dòng | `T = 1/1000` · `τ = R · C` · `ω_c ≪ ω_s` | `\tau` `\cdot` `\ll` |
| 4 · trong bảng | `Z = √(R^2 + X^2)` | `\sqrt` và **ngoặc nhọn** `{ }` |
| 5 · trích dẫn | `V_drop = I × R_DS(on)` · `η = 0.9` | `\eta` |
| 6 · rào ` ```math ` | `τ = R · C, f_c = 1/(2πτ)` | khối mã đẳng khoảng, `\pi` |
| 7 · **tiền** | `$82 triệu`, `$HOME`, `$4,450` **nguyên vẹn** | chữ bị nuốt mất giữa hai dấu `$` |

Mục 7 là chỗ dễ sai nhất theo chiều ngược lại: đọc dấu đô-la quá hăng thì "giá $5 và $10 nữa"
bị ăn mất cả đoạn chữ ở giữa.

## Ba lỗi chỉ trang in bắt được

Bốn tệp đầu tiên đều báo **ĐẠT**, mọi con số đọc lại (`so_doan`, `so_bang`, `so_ky_tu`) đều
đúng. Nhìn bản PDF mới thấy ba chỗ hỏng, và một trong ba là **sai nghĩa**:

| Viết | Ra | Phải là |
|---|---|---|
| `\sqrt{R^2 + X^2}` | `√{R^2 + X^2}` | ngoặc nhọn TeX lọt ra giấy |
| `2^{\circ}` | `2^°` | độ là hậu tố, không phải số mũ |
| `\frac{1}{2\pi\tau}` | `1/2πτ` | **đọc thành `(1/2)·π·τ`** — phải là `1/(2πτ)` |

Cái thứ ba không bộ đếm nào chạm tới được: chuỗi ra vẫn đúng chính tả, vẫn không còn ký tự
TeX nào, chỉ là **nghĩa đã khác**.

## Lệnh không đổi được thì nó nói ra

Bộ đổi này cố ý **không phải một bộ dựng TeX** — nó có một bảng 90 ký hiệu. Gặp lệnh ngoài
bảng, `doc.render` báo ngay đầu câu trả lời:

> ⚠️ **Chưa đổi được 1 lệnh TeX** — `\varrho`. Chúng in ra giấy đúng như đang viết.

Thử bằng cách thêm một lệnh lạ vào `nguon.md` rồi dựng lại.
