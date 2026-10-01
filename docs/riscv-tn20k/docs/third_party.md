# Danh mục thư viện và mã nguồn bên thứ ba (Third-Party Components)

Tài liệu này ghi lại thông tin các thành phần mã nguồn mở bên ngoài được sử dụng trong dự án, tuân thủ yêu cầu lưu giữ giấy phép bản quyền và ghi nhận phiên bản/nguồn gốc (theo Đề bài mục A3.5).

---

## 1. PicoRV32 — Size-Optimized RISC-V CPU Core

- **Tên thành phần:** PicoRV32
- **Tác giả:** Claire Xenia Wolf <claire@yosyshq.com>
- **Kho lưu trữ (Repository):** [https://github.com/YosysHQ/picorv32](https://github.com/YosysHQ/picorv32)
- **Nhánh sử dụng:** `main` (phiên bản ổn định có tag `v1.0`)
- **Tệp mã nguồn chính:** `picorv32.v` (3 049 dòng)
- **Tệp tài liệu kèm theo:** `README.md` (trong `third_party/picorv32/README.md`)
- **Giấy phép (License):** **ISC License** (tương đương MIT / 2-Clause BSD)
- **Hiện trạng vị trí tệp trong dự án:**
  - `third_party/picorv32/README.md`: Lấy trực tiếp từ repo qua `code.vendor_fetch`.
  - `tai-lieu/picorv32.v`: Tải về từ raw github qua `doc.fetch` (SHA256: `0836050971b3c6cdd28ac3b1e5719a67fb645161912bef1e472e63995ceb0622`).

### Toàn văn Giấy phép ISC (ISC License)

```text
ISC License

Copyright (c) 2015  Claire Xenia Wolf <claire@yosyshq.com>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```
