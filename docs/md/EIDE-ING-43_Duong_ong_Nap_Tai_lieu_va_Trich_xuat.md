**EIDE — ĐƯỜNG ỐNG NẠP TÀI LIỆU VÀ TRÍCH XUẤT**

Định dạng hỗ trợ (PDF, Office, EDA, cấu hình vendor, log/capture, web) · bộ đọc · gán tầng tin cậy · chuẩn hoá đơn vị · trích dẫn · kiểm thử

*Mã tài liệu EIDE-ING-43 · v1.0 · 25/09/2026 · bổ sung mục C3 của EIDE-MDD-40 v3.0*

|                   |                                                                                                                                                                                                                                                                           |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**   | EIDE-ING-43 (Ingest & Extraction) v1.0                                                                                                                                                                                                                                    |
| **Quan hệ**       | Chi tiết hoá mục C3 "Luồng nạp tài liệu và phê duyệt" và công cụ ingest.file / fact.extract của MDD-40 v3.0; sửa lỗi bỏ sót định dạng Office (docx/xlsx/pptx) và các định dạng EDA/vendor; bổ sung yêu cầu ING-01…ING-20 vào danh mục yêu cầu và khối A3.6 vào mô hình UI |
| **Ngày**          | 25/09/2026                                                                                                                                                                                                                                                                |
| **Đề tài**          | PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI)                                |
| **Khung**         | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu                                                                                                                                                                           |
| **Tác giả**       | Vũ Trí Công                                                                                                                                                                                                                                                               |
| **Bằng chứng đo** | TC010 (không tìm được datasheet), TC011 (hai phiên bản), TC014 (prompt injection trong tài liệu), TC023/025/026 (netlist/Altium/tệp hỏng bị nhận là tệp nén), TC044 (scan mờ), TC062 (BOM ≠ netlist), TC070 (script)                                                      |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                                                                                                                                      | **Người sửa** |
|---------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 25/09/2026 | Bản đầu: rà soát 9 khoảng trống định dạng; bảng định dạng 3 mức hỗ trợ; bộ phân loại theo nội dung (Office trước archive); bộ đọc từng loại; trích Fact từ bảng (PDF/Office) và tệp cấu hình vendor; chuẩn hoá đơn vị; gán tầng theo nguồn; trích dẫn theo loại; phòng thủ; giới hạn; ING01–ING16; ING-01…ING-20. | VTC           |

**1. Rà soát: những gì MDD-40 đã và chưa quy định**

MDD-40 v3.0 (C3, B3) chỉ quy định đường PDF có chữ, PDF scan/ảnh (OCR), zip, netlist KiCad, mã nguồn, script, log/dump, capture .csv, URL, và SVD/ATDF cho registry. Các định dạng sau bị bỏ sót dù đã được yêu cầu từ 05/09/2026 ("trích từ PDF, Word, .zip và mọi loại tệp") hoặc là nguồn Fact quan trọng trong thực tế nhúng:

| **\#** | **Khoảng trống**                                                                              | **Hậu quả hiện tại**                                                                | **Giải quyết ở** |
|--------|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|------------------|
| 1      | Office: .docx/.xlsx/.pptx (và .doc/.xls/.ppt cũ)                                              | .docx là zip chứa XML → bị nhận là archive, bóc thành XML vô nghĩa (cùng lỗi TC023) | §3, §4.2         |
| 2      | Markdown/HTML/TXT (app note web, README SDK)                                                  | Chỉ có URL → PDF                                                                    | §4.3             |
| 3      | Bảng PDF phức tạp (ô gộp, xoay ngang, min/typ/max chung ô)                                    | Fact sai hoặc bỏ sót không có cảnh báo                                              | §5.1             |
| 4      | Hình trong datasheet (sơ đồ khối, timing, mạch tham khảo)                                     | Chỉ OCR chữ; mất tri thức hình                                                      | §4.6             |
| 5      | EDA khác: .kicad_sch/.kicad_pcb, Eagle XML, EasyEDA JSON, Altium ASCII, Gerber/BOM CSV        | Chỉ .net; .kicad_sch nhắc nhưng không có bộ đọc                                     | §4.4             |
| 6      | Cấu hình vendor: CubeMX .ioc, ESP-IDF sdkconfig, Zephyr .dts/.dtsi, linker .ld, SVD của dự án | Nguồn Fact clock/pinmux/bộ nhớ bị bỏ qua                                            | §4.5             |
| 7      | .rar/.7z/.tar.gz                                                                              | Chỉ zip chắc chắn                                                                   | §4.1             |
| 8      | Tài liệu nhiều ngôn ngữ (datasheet tiếng Trung CH32/GD32)                                     | OCR/tokenizer chưa quy định ngôn ngữ                                                | §4.7             |
| 9      | Chuẩn hoá đơn vị & ký hiệu (µ/u, Ω/ohm, 3V3, dải 2.7–5.5 V)                                   | Có ở DX v1 (đã bỏ), chưa chuyển sang fact.extract                                   | §5.2             |

**2. Bảng định dạng hỗ trợ (ba mức)**

Mức ĐẦY ĐỦ: đọc cấu trúc, trích Fact ứng viên, trích dẫn được. Mức MỘT PHẦN: đọc văn bản/bảng vào RAG, không trích Fact tự động. Mức KHÔNG: từ chối với lý do đúng và đề xuất định dạng thay thế. Mọi định dạng đều được phân loại theo NỘI DUNG (magic bytes / cấu trúc), đuôi tệp chỉ là gợi ý.

| **Nhóm**        | **Định dạng**                                         | **Mức**                                                        | **Bộ đọc**                                                                                              | **Trích dẫn (cite)**                      | **Ghi chú**                                                                             |
|-----------------|-------------------------------------------------------|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|-------------------------------------------|-----------------------------------------------------------------------------------------|
| Datasheet/RM/AN | PDF có chữ                                            | ĐẦY ĐỦ                                                         | pymupdf text theo trang; bảng: pdfplumber → camelot (lattice) khi có kẻ ô                               | doc, version, page, bbox, quote           | Đường chính                                                                             |
|                 | PDF scan / PNG / JPG / TIFF                           | MỘT PHẦN → ĐẦY ĐỦ nếu OCR ≥ 0,95                               | tesseract (vie+eng+chi_sim tuỳ chọn) có điểm tin cậy từng ô; bảng OCR bằng layout                       | page, bbox                                | Tầng tối đa BẠC; bắt buộc rà từng dòng (TC044)                                          |
| Office          | .docx                                                 | ĐẦY ĐỦ                                                         | python-docx (đoạn, tiêu đề, bảng, ghi chú) + pandoc → Markdown giữ bảng; ảnh nhúng → OCR                | doc, version, heading path, table#, para# | Không có số trang vật lý; nếu người cần trang → chuyển PDF bằng LibreOffice để lấy page |
|                 | .xlsx / .xlsm / .csv / .tsv                           | ĐẦY ĐỦ                                                         | openpyxl (giá trị + công thức), pandas; mỗi sheet là bảng → Fact ứng viên trực tiếp                     | file, sheet!A1                            | Giữ công thức làm "nguồn của số"; ô hợp nhất lấy anchor                                 |
|                 | .pptx                                                 | MỘT PHẦN                                                       | python-pptx: text + bảng + ghi chú theo slide; ảnh → OCR                                                | slide#, shape                             | Ít khi chứa Fact; vào RAG                                                               |
|                 | .doc / .xls / .ppt / .rtf / .odt / .ods               | ĐẦY ĐỦ qua chuyển đổi                                          | LibreOffice headless → định dạng mới rồi đi đường trên                                                  | như định dạng mới                         | Ghi "đã chuyển đổi" vào metadata                                                        |
| Văn bản         | .md / .txt / .html / .xml                             | MỘT PHẦN                                                       | markdown-it / html2text (giữ bảng) → RAG; bảng Markdown/HTML → Fact ứng viên                            | file, heading, line                       | HTML tải từ web: bọc untrusted                                                          |
| Nén             | .zip / .tar / .tar.gz / .7z / .rar                    | ĐẦY ĐỦ                                                         | zipfile/tarfile/py7zr/rarfile (unrar cần cài — tool manager); bóc đệ quy ≤ 3 cấp, ≤ 500 MB, ≤ 2 000 tệp | archive → path                            | Zip bomb: kiểm tỉ lệ nén \> 100 → dừng                                                  |
| EDA             | KiCad .net (netlist), .kicad_sch, .kicad_pcb (S-expr) | ĐẦY ĐỦ (.net, .kicad_sch) / MỘT PHẦN (.kicad_pcb: chỉ BOM+net) | sexpdata parser; kiutils                                                                                | file, sheet, ref (U1), net                | Nguồn CKM/ERC                                                                           |
|                 | Eagle .sch/.brd (XML), EasyEDA .json                  | MỘT PHẦN                                                       | xml/json → netlist nội bộ                                                                               | file, ref, net                            | Cần bộ ánh xạ; nhãn "chuyển đổi"                                                        |
|                 | Altium .SchDoc/.PcbDoc (nhị phân)                     | KHÔNG                                                          | —                                                                                                       | —                                         | Lỗi đúng lý do: "xuất Netlist (Protel/KiCad) hoặc PDF" (TC025)                          |
|                 | Gerber/drill, BOM .csv/.xlsx, pick-and-place          | MỘT PHẦN (BOM ĐẦY ĐỦ)                                          | BOM → bảng → đối chiếu netlist (TC062)                                                                  | file, row                                 | Gerber ngoài phạm vi (UC15) — chỉ nhận diện, không đọc                                  |
| Cấu hình vendor | STM32CubeMX .ioc                                      | ĐẦY ĐỦ                                                         | INI parser → pin/AF, clock tree, ngoại vi bật                                                           | file, key                                 | Fact origin=config, tầng NGƯỜI-cấu-hình (§6)                                            |
|                 | ESP-IDF sdkconfig, Kconfig                            | ĐẦY ĐỦ                                                         | key=value parser                                                                                        | file, key                                 |                                                                                         |
|                 | Zephyr .dts/.dtsi, .overlay                           | ĐẦY ĐỦ                                                         | dtc/pydevicetree → node, reg, pinctrl                                                                   | file, node path                           |                                                                                         |
|                 | Linker .ld, map file                                  | ĐẦY ĐỦ                                                         | regex MEMORY{} → flash/ram size/origin; map → used                                                      | file, line                                | Đối chiếu với Fact datasheet (mâu thuẫn → cảnh báo)                                     |
|                 | SVD / ATDF / EDC                                      | ĐẦY ĐỦ                                                         | cmsis-svd, xml → thanh ghi/bit                                                                          | file, peripheral.register.bit             | Từ hkw-core; tầng VÀNG nếu từ nhà sản xuất                                              |
| Mã              | C/C++/asm/CMake/Makefile/Kconfig/.py                  | ĐẦY ĐỦ (đọc)                                                   | fs.read theo range; ctags đề mục; hằng số \#define → Fact ứng viên origin=code                          | file:line                                 | Hằng số trong mã KHÔNG phải nguồn sự thật → tầng ĐỒNG-mã (chỉ để so với datasheet)      |
| Script          | .sh/.bat/.ps1/.py người đưa                           | ĐẦY ĐỦ (quét)                                                  | quét tĩnh lệnh nguy hiểm → ASK                                                                          | file:line                                 | TC070                                                                                   |
| Log/dump        | UART/RTT text, core dump, .elf (+ addr2line)          | ĐẦY ĐỦ                                                         | analyze.log / analyze.hardfault                                                                         | file:line, ts                             |                                                                                         |
| Capture         | .csv (Saleae/Sigrok), .sal, .sr, .vcd                 | ĐẦY ĐỦ (.csv/.vcd) / MỘT PHẦN (.sal/.sr: cần sigrok-cli)       | csv → khung; pyvcd; sigrok-cli decode                                                                   | file, t=                                  | UC10                                                                                    |
| Web             | URL (HTML/PDF)                                        | ĐẦY ĐỦ                                                         | tải sau G-DATA → hash → đi đường loại tệp; HTML bọc untrusted                                           | url, fetched_at, hash                     | TC014                                                                                   |

**3. Bộ phân loại theo nội dung (ingest.classify v3)**

Thứ tự kiểm là bắt buộc — Office trước archive, S-expression/XML trước text — vì nhiều định dạng "đội lốt" nhau (docx = zip; .net = text S-expr; .ioc = INI).

> def classify(path) -\> Kind:
>
> head = read(path, 8192); ext = suffix(path).lower()
>
> if head\[:4\] == b"%PDF": return PDF
>
> if is_zip(head):
>
> names = zip_namelist(path)
>
> if "\[Content_Types\].xml" in names:
>
> if any(n.startswith("word/")) : return DOCX
>
> if any(n.startswith("xl/")) : return XLSX
>
> if any(n.startswith("ppt/")) : return PPTX
>
> if "mimetype" in names and read_member(path,"mimetype").startswith(b"application/vnd.oasis"): return ODF
>
> return ARCHIVE_ZIP
>
> if is_ole2(head): return LEGACY_OFFICE \# .doc/.xls/.ppt → LibreOffice convert
>
> if is_7z(head) or is_rar(head) or is_tar(path) or is_gzip(head): return ARCHIVE_OTHER
>
> if is_image(head): return IMAGE
>
> if is_elf(head): return ELF
>
> text = try_decode(head) \# utf-8 / utf-16 / cp1252; None → BINARY_UNKNOWN
>
> if text is None: return BINARY_UNKNOWN \# Altium .SchDoc/.PcbDoc rơi vào đây → lý do đúng
>
> if text.lstrip().startswith("(export") or text.lstrip().startswith("(kicad_sch"): return KICAD
>
> if text.lstrip().startswith("\<?xml"): return EAGLE if "\<eagle" in text else SVD if "\<device" in text else XML
>
> if text.lstrip().startswith("{") and ext == ".json": return EASYEDA if "\\schematic\\" in text else JSON
>
> if ext == ".ioc" and "Mcu.Name" in text: return CUBEMX_IOC
>
> if ext in (".dts", ".dtsi", ".overlay"): return DEVICETREE
>
> if ext == ".ld" or "MEMORY" in text\[:4000\]: return LINKER
>
> if ext in (".c",".h",".cpp",".hpp",".s",".S",".py",".cmake") or ext=="CMakeLists.txt": return SOURCE
>
> if ext in (".sh",".bat",".ps1") or text.startswith("#!"): return SCRIPT
>
> if ext in (".csv",".tsv"): return CAPTURE_CSV if looks_like_capture(text) else TABLE_CSV
>
> if ext == ".vcd" or text.startswith("\$date"): return VCD
>
> if ext in (".md",".txt",".html",".htm"): return TEXT
>
> if looks_like_log(text): return LOG
>
> return TEXT

Mọi kết quả phân loại kèm độ tin cậy và lý do ("zip có word/ → DOCX"); tệp cụt/hỏng → E1002 "tệp cụt/hỏng (kích thước, CRC)"; BINARY_UNKNOWN với đuôi Altium → E1001 "định dạng Altium nhị phân không hỗ trợ — xuất Netlist Protel/KiCad hoặc PDF" (TC025/026). Không bao giờ đưa tệp không phải archive vào archive.list.

**4. Bộ đọc theo loại**

**4.1. Nén**

- Bóc đệ quy tối đa 3 cấp; tổng ≤ 500 MB, ≤ 2 000 tệp; tỉ lệ nén \> 100 hoặc đường dẫn có ".." → dừng, báo. .rar/.7z cần unrar/py7zr — thiếu → tool manager đề nghị cài (G-TOOL).

- Mỗi tệp con phân loại độc lập; kết quả là cây tệp có loại + độ tin cậy; người thấy cây trên tab Tài liệu và chọn "nạp cái nào" nếu \> 20 tệp.

**4.2. Office**

| **Định dạng**                 | **Đơn vị trích**                                                                                       | **Bảng → Fact**                                                                                               | **Ảnh nhúng**                                                              | **Trích dẫn**                                 |
|-------------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|-----------------------------------------------|
| .docx                         | Đoạn theo cây tiêu đề (H1\>H2\>H3); bảng có tiêu đề gần nhất; chú thích (footnote/comment) đi kèm đoạn | Bảng có tiêu đề cột trùng từ điển key (Parameter/Min/Typ/Max/Unit…) → Fact ứng viên như PDF; ô gộp lấy anchor | word/media/\* → OCR nếu là ảnh bảng/sơ đồ; chú thích ảnh (caption) vào RAG | doc@ver · "3.2 Electrical \> Bảng 4" · dòng r |
| .xlsx                         | Sheet → vùng dữ liệu (bỏ hàng trống đầu, phát hiện tiêu đề)                                            | Toàn bộ vùng có tiêu đề → Fact ứng viên; công thức lưu làm provenance                                         | —                                                                          | file@ver · Sheet!B7                           |
| .pptx                         | Slide: tiêu đề + thân + ghi chú                                                                        | Bảng trong slide → Fact ứng viên (ít gặp)                                                                     | OCR                                                                        | file@ver · slide 12                           |
| .doc/.xls/.ppt/.odt/.ods/.rtf | LibreOffice headless → .docx/.xlsx/.pptx (đúng loại) rồi như trên                                      |                                                                                                               |                                                                            | metadata converted_from                       |

**Số trang cho Word:** .docx không có số trang cố định; khi người muốn trích dẫn theo trang (ví dụ để in), tác tử chuyển .docx → PDF (LibreOffice) và lưu cả hai với cùng doc_id: trích dẫn chính theo heading/table, kèm page của bản PDF phái sinh.

**4.3. Văn bản Markdown/HTML/TXT**

- Markdown: cây tiêu đề + bảng GFM → Fact ứng viên; code block giữ nguyên (không trích Fact từ code block).

- HTML: html2text giữ bảng; loại script/style/nav; bảng \<table\> → Fact ứng viên; nguồn web bọc \<document untrusted\> và quét P-INJ.

**4.4. EDA**

- KiCad .net: parser S-expression → components (ref, value, footprint, datasheet URL), nets (name, nodes ref.pin) → CKM; đây là đầu vào ERC (TC038).

- .kicad_sch: đọc symbol instances, labels, wires → dựng netlist nội bộ (không cần KiCad chạy); .kicad_pcb: chỉ lấy BOM + net (bố trí ngoài phạm vi).

- Eagle/EasyEDA: ánh xạ sang netlist nội bộ; gắn nhãn "chuyển đổi, kiểm lại" trên tab Thiết kế.

- BOM .csv/.xlsx: cột ref/value/mpn/qty (dò tiêu đề mềm dẻo) → đối chiếu netlist; lệch → phát hiện (TC062).

**4.5. Cấu hình vendor → Fact "cấu hình"**

Các tệp .ioc/sdkconfig/.dts/.ld/map chứa những gì dự án ĐANG cấu hình, không phải giới hạn của chip. Chúng tạo Fact với origin=config (tầng riêng "CẤU HÌNH", hiển thị xanh lam), dùng để: (a) so với Fact datasheet — mâu thuẫn (ví dụ .ld khai FLASH 64 K nhưng chip 32 K) → phát hiện; (b) sinh mã đúng pinmux/clock đang cấu hình; (c) không bao giờ dùng CẤU HÌNH làm vế "giới hạn vật lý" trong so sánh.

| **Tệp**     | **Key trích**                                                                   | **Ví dụ Fact**                                              |
|-------------|---------------------------------------------------------------------------------|-------------------------------------------------------------|
| CubeMX .ioc | Mcu.Name, PA5.Signal, RCC.SYSCLKFreq_VALUE, \<Periph\>.Mode                     | config:pin.PA5.af = SPI1_SCK · config:clock.sysclk = 72 MHz |
| sdkconfig   | CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ, CONFIG_FREERTOS_HZ, CONFIG_PARTITION_TABLE\_\* | config:cpu.freq = 160 MHz                                   |
| .dts/.dtsi  | node reg, status, pinctrl-0, clock-frequency                                    | config:i2c0.clock-frequency = 400 kHz                       |
| .ld         | MEMORY { FLASH (rx): ORIGIN, LENGTH }                                           | config:flash.size = 65536 B (so với chip flash.size)        |
| map         | .text/.data/.bss size                                                           | config:flash.used = 3 148 B                                 |

**4.6. Hình trong tài liệu**

- Mỗi hình (PDF/Office) → ảnh + chú thích (caption) + số trang/heading + văn bản OCR → một đoạn RAG loại "figure"; mô hình có thể yêu cầu xem ảnh (blob) khi cần đọc sơ đồ (vision) — kết quả đọc hình là ĐỒNG trừ khi người xác nhận.

- Timing diagram / bảng trong ảnh: OCR bảng có layout; giá trị → Fact ứng viên với tin cậy OCR; luôn ≤ BẠC.

**4.7. Ngôn ngữ**

- Nhận diện ngôn ngữ tài liệu (langdetect); OCR nạp gói ngôn ngữ tương ứng (vie, eng, chi_sim, jpn…); từ điển key chuẩn có bí danh đa ngữ (ví dụ "工作电压" → vdd.range); embedding đa ngữ (bge-m3) cho RAG.

**5. Trích Fact từ bảng và chuẩn hoá**

**5.1. Bảng → Fact ứng viên**

1.  Nhận diện bảng thông số: tiêu đề cột khớp từ điển (Symbol/Parameter/Conditions/Min/Typ/Max/Unit và bí danh); không khớp → mô hình chỉ ánh xạ TIÊU ĐỀ cột → key chuẩn (không đọc giá trị).

2.  Ô gộp: lấy giá trị của ô anchor cho mọi ô con; bảng xoay ngang: phát hiện theo tỉ lệ số/chữ và xoay; min/typ/max chung ô ("2.7 / 3.3 / 5.5") → tách theo mẫu.

3.  Mỗi dòng → Fact {subject, key, min/typ/max, unit, condition, source{page,bbox\|heading,table,row}, tier, confidence}; confidence = min(OCR conf, parse conf); \< 0,8 → bắt buộc rà.

4.  Dedup trong cùng tài liệu (bảng tóm tắt và bảng chi tiết trùng key) → giữ bảng chi tiết, tham chiếu bảng kia.

5.  Bảng có chú thích (Note 1, 2) → gắn condition từ chú thích.

**5.2. Chuẩn hoá đơn vị và ký hiệu (bằng mã, 0 token)**

| **Đầu vào**                                          | **Chuẩn hoá**                                                               | **Ghi chú**                     |
|------------------------------------------------------|-----------------------------------------------------------------------------|---------------------------------|
| µ, u, μ (micro); Ω, ohm, R (ở 4R7); k, K; M; m; n; p | Tiền tố SI về số thực + unit chuẩn (V, A, Ω, Hz, s, F, H, W, °C, B)         | Giữ chuỗi gốc trong Fact.raw    |
| 3V3, 5V0, 4R7, 100n                                  | Ký hiệu kỹ thuật → 3,3 V; 5,0 V; 4,7 Ω; 100 nF (nF khi ngữ cảnh là tụ)      | Ngữ cảnh từ tiêu đề cột/đơn vị  |
| 2.7–5.5 V; 2,7 ~ 5,5 V; -40 to +85 °C                | min/max                                                                     | Dấu gạch, ~, to, đến            |
| Dấu thập phân "," và "."                             | Theo ngôn ngữ tài liệu; số hiển thị theo thói quen người dùng (vi: "5,5 V") |                                 |
| Điều kiện "@ 100 kHz, VDD = 3.3 V"                   | condition có cấu trúc {freq, vdd}                                           | Cho phép so sánh đúng điều kiện |
| Ký hiệu "—", "N/A", "TBD"                            | value = null, flag                                                          | Không bịa 0                     |

**5.3. Đối chiếu chéo**

- Cùng key từ nhiều nguồn (datasheet v1 vs v2; datasheet vs .ld; BOM vs netlist) → bảng khác biệt tự động; người chọn hoặc tác tử đề xuất theo quy tắc: errata \> datasheet mới \> datasheet cũ \> cấu hình \> mã.

**6. Gán tầng tin cậy theo nguồn**

| **Nguồn**                                                       | **Tầng mặc định sau người duyệt nguồn**                 | **Lên VÀNG khi**                           | **Ghi chú**                             |
|-----------------------------------------------------------------|---------------------------------------------------------|--------------------------------------------|-----------------------------------------|
| Datasheet/RM/errata PDF từ tên miền nhà sản xuất (trusted)      | BẠC; AUTO VÀNG cho bảng có cấu trúc tin cậy ≥ 0,95      | Người xác nhận dòng                        | Đường chính                             |
| PDF từ bên thứ ba (distributor, forum)                          | BẠC, nhãn "bên thứ ba"                                  | Người xác nhận                             | Không AUTO                              |
| Scan/ảnh/OCR                                                    | BẠC tối đa; \< 0,8 → chỉ ứng viên                       | Người xác nhận từng dòng                   | TC044                                   |
| Office do nhà sản xuất/nhà cung cấp phát hành                   | BẠC                                                     | Người xác nhận                             |                                         |
| Office do người dùng/đồng nghiệp tự viết (spec nội bộ, bảng đo) | NGƯỜI (không có tài liệu chuẩn) — CẦN CHỦ SẢN PHẨM CHỐT | Có tài liệu chuẩn chứng thực               | Đề xuất: NGƯỜI, vì không phải datasheet |
| Cấu hình vendor (.ioc/.dts/.ld)                                 | CẤU HÌNH (tầng riêng)                                   | Không bao giờ — không phải giới hạn vật lý | §4.5                                    |
| Hằng số trong mã                                                | ĐỒNG-mã                                                 | Không                                      | Chỉ để so                               |
| SVD/ATDF nhà sản xuất                                           | VÀNG (máy đọc được, có phiên bản)                       | —                                          | Registry                                |
| Web HTML                                                        | ĐỒNG trừ khi là trang nhà sản xuất (→ BẠC)              | Người xác nhận                             | untrusted                               |

**7. Phòng thủ, giới hạn, lỗi**

- Mọi nội dung tài liệu là DỮ LIỆU: bọc \<document untrusted source=…\>; quét P-INJ (mẫu "ignore previous", lệnh shell, URL lạ) → đánh dấu đoạn, loại khỏi ngữ cảnh mô hình, cảnh báo đỏ (TC014). Macro trong .docm/.xlsm không bao giờ chạy; chỉ đọc dữ liệu.

- Giới hạn: tệp ≤ 200 MB; PDF ≤ 2 000 trang (hơn → hỏi phạm vi trang); OCR ≤ 300 trang/lượt (hơn → nền + báo tiến trình); archive §4.1.

- **Mã lỗi — cập nhật 29/09/2026 theo mã đang chạy.** Bản v1.0 của tài liệu này đánh số
  E1001–E1008 liền mạch (đánh số lúc thiết kế). Khi hiện thực, dải `E1004`–`E1006` đã bị các công cụ khác lấy
  trước (`fs.read` trên thư mục, `fs.edit` không tìm thấy đoạn / đoạn trùng nhiều lần), nên
  nhóm nạp tài liệu chuyển sang dải `E1010`–`E1015`. Bảng đúng:

  | Mã | Nghĩa | Sinh ở |
  |---|---|---|
  | `E1001` | Định dạng chưa đọc được — kèm danh sách định dạng đọc được | `src/eide/errors.py` · `src/eide/tools/knowledge.py` |
  | `E1002` | Tệp hỏng hoặc cụt. *"Nói thật là tệp hỏng. KHÔNG suy đoán phần thiếu chứa gì."* | `src/eide/errors.py` · `src/eide/tools/knowledge.py` |
  | `E1003` | Đường dẫn không tồn tại | `src/eide/errors.py` |
  | `E1010` | Tệp có mật khẩu — *"KHÔNG thử đoán mật khẩu"* | `src/eide/errors.py` |
  | `E1011` | Vượt trần xử lý an toàn (số trang, kích thước…) — dừng để không treo máy giữa chừng | `src/eide/errors.py` |
  | `E1012` | Tỉ lệ giải nén bất thường (zip bomb) | `src/eide/errors.py` |
  | `E1013` | Tệp có macro — EIDE đọc dữ liệu và **không chạy macro** | `src/eide/errors.py` |
  | `E1014` | Không đọc được chữ từ ảnh (OCR) — *"Đừng đoán nội dung ảnh"* | `src/eide/errors.py` · `src/eide/tools/knowledge.py` |
  | `E1015` | Không chuyển đổi được định dạng cũ (cần LibreOffice) | `src/eide/errors.py` |

  Mỗi lỗi có `message_vi` + `hint_for_agent` + `alternatives`.

  *Ba mã `E1004`–`E1006` KHÔNG thuộc nhóm nạp tài liệu:* `E1004` là `fs.read` gọi vào một thư
  mục; `E1005`/`E1006` là `fs.edit` không tìm thấy đoạn cần thay, hoặc đoạn ấy xuất hiện nhiều
  lần. Ghi rõ ở đây vì một mã lỗi dùng lại cho hai việc khác nhau là chỗ người đọc tra nhầm.

- Không tìm thấy tài liệu/không trích được → nói thẳng (TC010), không bịa.

**8. Giao diện (khối A3.6 — bổ sung vào mô hình UI)**

| **Widget**                                                                                 | **Loại** | **Yêu cầu**            |
|--------------------------------------------------------------------------------------------|----------|------------------------|
| Cây tệp sau phân loại: loại, độ tin cậy, lý do, mức hỗ trợ (ĐẦY ĐỦ/MỘT PHẦN/KHÔNG + gợi ý) | display  | ING-01, ING-02, ING-03 |
| Chọn tệp nào nạp khi archive \> 20 tệp                                                     | edit     | ING-04                 |
| Xem tài liệu Office theo cây tiêu đề/sheet/slide; trích dẫn heading/ô/slide                | display  | ING-05, ING-06         |
| Bảng Fact ứng viên từ Office/Markdown với cột nguồn (Sheet!ô, Bảng#)                       | display  | ING-07                 |
| Fact CẤU HÌNH (tầng riêng) và cảnh báo mâu thuẫn với datasheet                             | display  | ING-10, ING-11         |
| Hình trong tài liệu: ảnh + caption + OCR; nút "Nhờ tác tử đọc hình" (ĐỒNG)                 | action   | ING-12                 |
| Bảng khác biệt chéo nguồn (v1/v2, datasheet/.ld, BOM/netlist) + chọn bản                   | edit     | ING-13                 |
| Chuẩn hoá đơn vị: hiện giá trị chuẩn + chuỗi gốc                                           | display  | ING-14                 |
| Ngôn ngữ tài liệu + gói OCR; chọn lại                                                      | edit     | ING-15                 |
| Lỗi `E1001`–`E1003` + `E1010`–`E1015` với gợi ý định dạng thay thế                                               | display  | ING-16                 |
| Tiến trình OCR nền cho tài liệu lớn                                                        | display  | ING-17                 |
| Chuyển .docx → PDF phái sinh để có số trang (cùng doc_id)                                  | action   | ING-06                 |

**9. Ca kiểm ING01–ING16**

| **Mã** | **Ca**                                              | **Mong đợi**                                                                           |
|--------|-----------------------------------------------------|----------------------------------------------------------------------------------------|
| ING01  | Nạp .docx datasheet nội bộ có 3 bảng                | Phân loại DOCX (không phải archive); 3 bảng → Fact ứng viên; trích dẫn heading + Bảng# |
| ING02  | Nạp .xlsx bảng đo 2 sheet                           | Mỗi sheet → Fact ứng viên; nguồn Sheet!ô; công thức lưu provenance                     |
| ING03  | Nạp .doc cũ                                         | Chuyển đổi LibreOffice → DOCX; metadata converted_from; đường như ING01                |
| ING04  | Nạp .PcbDoc                                         | E1001 với gợi ý xuất netlist/PDF (TC025)                                               |
| ING05  | Nạp zip cụt                                         | E1002 "tệp cụt/hỏng", không suy đoán (TC026)                                           |
| ING06  | Nạp .net KiCad                                      | KICAD → CKM; không vào archive.list (TC023)                                            |
| ING07  | Nạp .kicad_sch                                      | Netlist nội bộ dựng từ sơ đồ; ERC chạy được                                            |
| ING08  | Nạp .ioc + .ld                                      | Fact CẤU HÌNH; .ld FLASH 64 K vs chip 32 K → cảnh báo mâu thuẫn                        |
| ING09  | PDF bảng có ô gộp + min/typ/max chung ô             | Fact tách đúng; confidence ghi; \< 0,8 bắt buộc rà                                     |
| ING10  | PDF scan mờ                                         | Tầng ≤ BẠC, cảnh báo OCR, rà từng dòng (TC044)                                         |
| ING11  | Datasheet tiếng Trung                               | Nhận ngôn ngữ; OCR chi_sim; key bí danh ánh xạ đúng                                    |
| ING12  | "4R7", "3V3", "2.7~5.5V", "100n"                    | Chuẩn hoá đúng, giữ raw                                                                |
| ING13  | HTML tải từ web chứa "ignore previous instructions" | Đoạn bị đánh dấu, loại khỏi ngữ cảnh, cảnh báo (TC014)                                 |
| ING14  | .docm có macro                                      | Đọc dữ liệu, không chạy macro, E1006 cảnh báo                                          |
| ING15  | Zip 3 cấp, 600 MB                                   | Dừng ở giới hạn, báo E1004, đề nghị chọn tệp                                           |
| ING16  | Hai phiên bản PDF + một .xlsx cùng key              | Bảng khác biệt chéo nguồn; quy tắc ưu tiên; người chọn (TC011)                         |

**10. Danh mục yêu cầu ING-01…ING-20**

| **Mã** | **Yêu cầu**                                                                                                                    |
|--------|--------------------------------------------------------------------------------------------------------------------------------|
| ING-01 | Phân loại theo nội dung; thứ tự Office → archive → text; lý do + độ tin cậy                                                    |
| ING-02 | Ba mức hỗ trợ ĐẦY ĐỦ/MỘT PHẦN/KHÔNG hiển thị cho người, kèm gợi ý thay thế                                                     |
| ING-03 | Không bao giờ đưa tệp không phải archive vào archive.list                                                                      |
| ING-04 | Archive: bóc đệ quy có giới hạn; chọn tệp khi \> 20; chống zip bomb                                                            |
| ING-05 | Office .docx/.xlsx/.pptx đọc cấu trúc (heading/bảng/sheet/slide); ảnh nhúng OCR; định dạng cũ chuyển đổi                       |
| ING-06 | Trích dẫn theo loại (page/bbox; heading/table/row; sheet!ô; slide); docx → PDF phái sinh cùng doc_id khi cần trang             |
| ING-07 | Bảng (PDF/Office/Markdown/HTML) → Fact ứng viên; giá trị đọc bằng mã; mô hình chỉ ánh xạ tiêu đề cột                           |
| ING-08 | Ô gộp, bảng xoay, min/typ/max chung ô, chú thích Note → condition                                                              |
| ING-09 | EDA: KiCad .net/.kicad_sch đầy đủ; Eagle/EasyEDA chuyển đổi có nhãn; Altium nhị phân từ chối đúng lý do; BOM đối chiếu netlist |
| ING-10 | Cấu hình vendor (.ioc/sdkconfig/.dts/.ld/map) → Fact tầng CẤU HÌNH                                                             |
| ING-11 | CẤU HÌNH không bao giờ là vế giới hạn vật lý; mâu thuẫn với datasheet → phát hiện                                              |
| ING-12 | Hình → đoạn RAG "figure" (ảnh + caption + OCR); đọc hình bằng vision là ĐỒNG                                                   |
| ING-13 | Đối chiếu chéo nguồn cùng key; quy tắc ưu tiên errata \> DS mới \> DS cũ \> cấu hình \> mã                                     |
| ING-14 | Chuẩn hoá đơn vị/ký hiệu bằng mã; giữ raw; condition có cấu trúc                                                               |
| ING-15 | Đa ngôn ngữ: nhận diện, OCR đúng gói, key bí danh đa ngữ, embedding đa ngữ                                                     |
| ING-16 | Mã lỗi `E1001`–`E1003` + `E1010`–`E1015` có message_vi + hint + alternatives                                                                         |
| ING-17 | Giới hạn kích thước/trang; OCR nền có tiến trình                                                                               |
| ING-18 | Nội dung tài liệu là dữ liệu: bọc untrusted, quét P-INJ, không chạy macro                                                      |
| ING-19 | Gán tầng theo nguồn (bảng §6); Office tự viết → NGƯỜI (chờ chốt)                                                               |
| ING-20 | Hằng số trong mã → ĐỒNG-mã, chỉ để so sánh với datasheet                                                                       |

**11. Hiện thực**

| **Bước** | **Nội dung**                                                                                        | **Ca kiểm**          | **Đi cùng**   |
|----------|-----------------------------------------------------------------------------------------------------|----------------------|---------------|
| ING-A    | classify v3 (Office trước archive); mã lỗi `E1001`–`E1003`, `E1010`–`E1015`; cây tệp UI                                  | ING01, 03–06, 14, 15 | G4 của MDD-40 |
| ING-B    | Bộ đọc Office (python-docx, openpyxl, python-pptx, LibreOffice); trích dẫn theo loại; PDF phái sinh | ING01–03             | G4            |
| ING-C    | Bảng → Fact ứng viên thống nhất (PDF/Office/MD/HTML); chuẩn hoá đơn vị; ô gộp/xoay; đối chiếu chéo  | ING09, 12, 16        | G4            |
| ING-D    | EDA (.kicad_sch, Eagle, EasyEDA, BOM) + cấu hình vendor + tầng CẤU HÌNH                             | ING07, 08            | G4/G6         |
| ING-E    | Hình/figure, đa ngôn ngữ, OCR nền                                                                   | ING10, 11            | G4            |

Thư viện Python: pymupdf, pdfplumber, camelot-py, pytesseract (+ gói ngôn ngữ), python-docx, openpyxl, python-pptx, py7zr, rarfile, sexpdata/kiutils, pydevicetree, cmsis-svd, langdetect, markdown-it-py, html2text; LibreOffice headless cho chuyển đổi. Tất cả chạy trong sandbox, không mạng.
