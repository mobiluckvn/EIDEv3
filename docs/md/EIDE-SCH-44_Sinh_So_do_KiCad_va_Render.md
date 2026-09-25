**EIDE — SINH SƠ ĐỒ NGUYÊN LÝ KICAD VÀ RENDER**

Tích hợp cộng thêm vào v3: CKM → SKiDL → netlist/ERC → bố cục → .kicad_sch → SVG → người sửa trong KiCad → nạp lại. Cách ly bằng namespace, cờ tính năng, suy giảm nhẹ nhàng, hồi quy bắt buộc

*Mã tài liệu EIDE-SCH-44 · v1.0 · 25/09/2026 · bổ sung MDD-40 v3.0 (C2, B3, E2) và ING-43 (§4.4)*

|                         |                                                                                                                                                                                                                                                                                                                                                                                                   |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**         | EIDE-SCH-44 (Schematic Generation & Rendering) v1.0                                                                                                                                                                                                                                                                                                                                               |
| **Quan hệ**             | Cộng thêm vào MDD-40 v3.0: hiện vật AR09 (schematic/netlist) có thêm dạng người là .kicad_sch/SVG; công cụ mới namespace sch.\*; khối UI A5.8; yêu cầu SCH-01…SCH-22. Dùng bộ đọc .kicad_sch của ING-43 §4.4 cho round-trip. Gộp engine với dự án "KiCad SKiDL MCP Agent"                                                                                                                         |
| **Nguyên tắc tích hợp** | KHÔNG sửa hợp đồng tool hiện có · KHÔNG đổi lược đồ Store/CKM (chỉ thêm bảng/cột nullable) · cờ features.schematic mặc định TẮT · KHÔNG cài KiCad trên máy (quyết định 25/09/2026): render, ERC, đọc/ghi .kicad_sch đều bằng thư viện Python thuần trong sandbox; thư viện ký hiệu KiCad chỉ tải về như dữ liệu · bộ hồi quy 76 TC + CX + MEM + ING phải giữ nguyên kết quả khi cờ tắt VÀ khi bật |
| **Ngày**                | 25/09/2026                                                                                                                                                                                                                                                                                                                                                                                        |
| **Khung**               | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu                                                                                                                                                                                                                                                                                                   |
| **Tác giả**             | Vũ Trí Công                                                                                                                                                                                                                                                                                                                                                                                       |
| **Ngoài phạm vi**       | PCB layout, Gerber, DRC, pick-and-place (UC15) — sinh .kicad_sch không kéo theo .kicad_pcb                                                                                                                                                                                                                                                                                                        |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                                                                                                                                                      | **Người sửa** |
|---------------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 25/09/2026 | Bản đầu: ba bài toán và mục tiêu "đúng trước, đẹp sau"; kiến trúc tích hợp cách ly; đường ống 7 bước; hợp đồng 8 tool sch.\*; bố cục theo module có tiêu chí số; symbol từ Fact; render 3 mức; round-trip; an toàn tích hợp (cờ, hồi quy, kiểm lược đồ, rollback); UI A5.8; ca kiểm SCH01–SCH18; SCH-01…SCH-22; lộ trình SCH-A…D. | VTC           |

**1. Mục tiêu và ba bài toán**

Tính năng: từ Bản đồ tri thức mạch (CKM) đã có, tác tử sinh sơ đồ nguyên lý dạng tệp KiCad (.kicad_sch), render thành hình để người đọc trên tab Thiết kế, và nhận lại sơ đồ sau khi người sửa trong KiCad. Ba bài toán bên trong có độ khó khác nhau và được xếp mục tiêu riêng:

| **\#** | **Bài toán**                                                 | **Mục tiêu v3.1**                                                                                    | **Không phải mục tiêu**                                        |
|--------|--------------------------------------------------------------|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| 1      | Sinh mạch ĐÚNG: linh kiện, chân, net khớp CKM và Fact pinout | Netlist sinh ra = netlist CKM (đẳng cấu); ERC nội bộ + KiCad ERC 0 lỗi                               | —                                                              |
| 2      | RENDER để người đọc                                          | SVG/PDF tương tác trên tab Thiết kế bằng renderer nội bộ (không cần KiCad); bấm ký hiệu → Fact/nguồn | Trình soạn thảo sch trong EIDE; giống KiCad 100 % về hình thức |
| 3      | BỐ CỤC đọc được                                              | Không chồng, không cắt, mỗi net ≤ N đoạn gấp, module thành vùng, dây dài → nhãn net                  | "Đẹp như người vẽ" — người tinh chỉnh trong KiCad              |

**Nguyên tắc:** CKM vẫn là nguồn sự thật (N1, N3). Tệp .kicad_sch là DẠNG NGƯỜI của hiện vật AR09 theo E1 của MDD-40 — sinh ra từ dạng máy, có lớp giải thích, và khi người sửa thì đi ngược về dạng máy qua changeset. Không có "nguồn sự thật thứ hai" nằm trong tệp KiCad.

**2. Kiến trúc tích hợp cách ly**

![](../img/s1_sch_pipeline.png)

*Hình 1. Đường ống sinh – render – round-trip, đặt cạnh hệ thống hiện có mà không sửa nó*

**2.1. Bảy lớp bảo vệ hệ thống hiện tại**

| **\#** | **Biện pháp**               | **Cụ thể**                                                                                                                                                                                                                                                                                                                    |
|--------|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1      | Namespace riêng             | Mọi tool mới ở sch.\*; module Python eide/sch/ độc lập; không import ngược từ module cũ vào sch (chỉ sch gọi API công khai của CKM/Store/policy)                                                                                                                                                                              |
| 2      | Cờ tính năng                | features.schematic = false mặc định (settings.json + EIDE.md không ảnh hưởng). Tắt → tool sch.\* không được đăng ký (mô hình không thấy), UI A5.8 ẩn, không có nhánh mã nào của sch chạy                                                                                                                                      |
| 3      | Không đổi hợp đồng cũ       | board.schematic/board.pinout/board.check/bom.build/diagram.render giữ nguyên chữ ký và hành vi; sch.\* là tool mới gọi chúng, không thay thế                                                                                                                                                                                  |
| 4      | Lược đồ chỉ cộng thêm       | Store: bảng mới sch_sheets (id, version, path, lib_versions, layout_hash, explain) + cột nullable artefact.kicad_ref; không đổi cột hiện có; migration có kiểm tra ngược (down)                                                                                                                                               |
| 5      | Không phụ thuộc KiCad       | Máy KHÔNG cài KiCad. SKiDL + kiutils (pip trong sandbox dự án) đảm nhiệm netlist/ERC/đọc-ghi .kicad_sch; renderer nội bộ S-expr → SVG là đường chính; thư viện ký hiệu kicad-symbols tải về như dữ liệu (git/zip, có phiên bản, hash) qua G-DATA. Thiếu SKiDL/kiutils → sơ đồ khối/đồ thị net hiện có; không bao giờ lỗi cứng |
| 6      | Hồi quy bắt buộc hai chế độ | Chạy 76 TC + CX01–16 + MEM01–14 + ING01–16 với cờ TẮT (phải giống hệt trước) và với cờ BẬT (phải giống hệt, vì sch chỉ chạy khi được gọi); sai lệch bất kỳ → không merge                                                                                                                                                      |
| 7      | Rollback theo changeset     | Mọi tệp .kicad_sch/.kicad_sym/.net do sch.\* ghi đều là changeset (E5), hoàn tác được; xoá tính năng = tắt cờ, dữ liệu cũ không bị động                                                                                                                                                                                       |

**2.2. Điểm chạm duy nhất với hệ thống cũ**

| **Điểm chạm**                | **Loại thay đổi**                                            | **Rủi ro**                                                                                                | **Kiểm**                                |
|------------------------------|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------|
| Đăng ký tool (tool registry) | Cộng thêm 8 tool khi cờ bật                                  | Prompt tool tăng ~1,2 k token → nạp trễ (chỉ sch.compose và sch.render hiển thị, còn lại qua tool.search) | Đo token khối 2 (MEM-42 §4.1) trước/sau |
| Hợp đồng AR09 (E2)           | Thêm view_hint kicad (SVG) bên cạnh code view netlist        | Không                                                                                                     | CX01–04 giữ nguyên                      |
| PostToolUse hook             | Thêm ánh xạ tool_result sch.\* → Surface design.sch          | Hook cũ không đổi; nhánh mới chỉ chạy với tool sch.\*                                                     | Unit test hook với tool giả             |
| ING-43 classify              | Đã có KICAD → dùng lại; thêm .kicad_sym                      | Không                                                                                                     | ING06–07                                |
| Policy                       | Thêm luật cho sch.\* (ghi tệp = R1, cài KiCad = G-TOOL)      | Không đổi luật cũ                                                                                         | Policy unit test                        |
| Skill                        | Thêm skill kicad-schematic (cách viết SKiDL, quy ước bố cục) | Không                                                                                                     | —                                       |

**3. Đường ống bảy bước**

| **Bước**       | **Tool**                       | **Vào**                                                       | **Ra**                                                                            | **Kiểm bằng mã**                                                                                          |
|----------------|--------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| 1 Soạn         | sch.compose                    | CKM: module_graph, netlist nội bộ, Fact pinout (≥ NGƯỜI), BOM | Tệp SKiDL (.py) mô tả mạch: Part theo lib/ref, Net theo tên CKM, kết nối theo pin | Cú pháp; mọi ref/net có trong CKM; chân dùng có trong Fact pinout (không bịa chân)                        |
| 2 Sinh netlist | sch.netlist                    | Tệp SKiDL                                                     | KiCad .net + ERC SKiDL + board.check (ERC nội bộ) — không dùng kicad-cli          | Đẳng cấu với netlist CKM (so tập (ref.pin, net)); lệch → lỗi E7001 kèm diff, không đi tiếp                |
| 3 Ký hiệu      | sch.symbols                    | BOM + Fact pinout                                             | Ánh xạ ref → symbol (lib chính thức) hoặc .kicad_sym sinh từ Fact                 | Tên/số chân symbol ↔ Fact pinout; lệch → dùng symbol sinh, ghi cảnh báo                                   |
| 4 Bố cục       | sch.place                      | Netlist + module_graph + symbol                               | Toạ độ/xoay từng ký hiệu, nhãn net, dây                                           | Tiêu chí §4: 0 chồng, 0 cắt ký hiệu, ≤ N gấp, đúng lưới 1,27 mm                                           |
| 5 Ghi          | sch.write                      | Bố cục                                                        | .kicad_sch (+ .kicad_sym, .kicad_pro tối thiểu), uuid ổn định theo ref            | kiutils parse lại được (round-trip ổn định); lược đồ S-expr KiCad 8/9 kiểm bằng bộ kiểm nội bộ; changeset |
| 6 Render       | sch.render                     | .kicad_sch + .kicad_sym                                       | SVG (chính) / PDF / PNG bằng renderer nội bộ + bản đồ id ký hiệu → ref            | Ảnh không rỗng; số ký hiệu trong SVG = số ref; text không đè (kiểm bbox)                                  |
| 7 Round-trip   | sch.import (dùng ING-43 KICAD) | .kicad_sch người đã sửa                                       | Diff netlist ↔ CKM → changeset human; STALE; đề nghị cập nhật module              | Không ghi đè CKM im lặng; net/linh kiện mới → hỏi                                                         |

**3.1. Hợp đồng tool (trích CDS-12 cho sch.\*)**

> sch.compose { module_ids?: \[\], style: "flat"\|"hierarchical" } requires: module_graph ≥ 1, netlist_ckm, passport → artefact skidl_src risk R0
>
> sch.netlist { skidl_ref } requires: skidl_src → artefact netlist_kicad risk R0
>
> sch.symbols { prefer_lib: "official"\|"generated" } requires: bom, facts pinout → artefact symbol_map risk R0
>
> sch.place { strategy: "module-grid", max_bends: 3 } requires: netlist_kicad, symbol_map → artefact layout risk R0
>
> sch.write { sheet_name, kicad_version: "8"\|"9" } requires: layout → files \*.kicad_sch/\*.kicad_sym (changeset) risk R1 (ghi tệp; G-FILE nếu người đã sửa)
>
> sch.render { format: "svg"\|"pdf"\|"png" } requires: file .kicad_sch → blob + surface design.sch risk R0
>
> sch.import { path } requires: — → diff + changeset human (qua ING KICAD) risk R1
>
> sch.export { } xuất gói .kicad_sch/.kicad_sym/.net/SVG để người mở ở máy khác có KiCad (máy này KHÔNG cài) risk R0
>
> Mọi tool: trả lỗi {code E7xxx, message_vi, hint_for_agent, alternatives}; explain bắt buộc (N8) cho hiện vật sinh ra.

**4. Bố cục theo module — tiêu chí bằng số**

- Mỗi module của module_graph là một vùng chữ nhật trên lưới 1,27 mm; vùng xếp theo luồng tín hiệu trái → phải (nguồn vào, MCU giữa, ngoại vi/kết nối phải), nguồn trên, GND dưới.

- Trong vùng: IC/MCU ở giữa; linh kiện thụ động gắn với chân nào thì đặt sát chân đó (pull-up cạnh SDA/SCL, tụ lọc cạnh VDD); connector ở biên vùng.

- Dây: chỉ đi dây trực giao trong vùng khi ≤ 3 đoạn gấp và không cắt ký hiệu; ngoài ra dùng nhãn net (local trong vùng, global giữa vùng, hierarchical khi style=hierarchical). Nguồn/GND luôn dùng ký hiệu power.

- Tiêu chí nghiệm thu (đo bằng mã, không chấm cảm tính): 0 ký hiệu chồng nhau; 0 dây cắt qua thân ký hiệu; 0 dây chéo; tỉ lệ net dùng nhãn ≤ 70 % (nếu cao hơn → cảnh báo "mạch khó đọc", đề nghị style=hierarchical); trang ≤ A3; mọi ký hiệu có ref/value hiển thị không đè.

- Thuật toán: (1) gán vùng cho module bằng xếp cột theo luồng; (2) trong vùng, đặt IC trước, rồi thụ động theo chân bằng tham lam có kiểm chồng; (3) đi dây bằng A\* trên lưới với phạt gấp; (4) net không đi được → nhãn; (5) chạy tiêu chí, nếu vi phạm → nới vùng 20 % và lặp (≤ 5 lần).

- Mô hình không tự "vẽ" toạ độ; nó chỉ chọn style, nhóm module, và gợi ý luồng — toạ độ do mã tính (xác định, lặp lại được với cùng đầu vào).

**5. Ký hiệu (symbol) từ thư viện và từ Fact**

- Thư viện ký hiệu KiCad chính thức (kicad-symbols) được tải về như DỮ LIỆU (.kicad_sym, git tag/zip có hash, qua G-DATA, cache ở M4) — không cần cài KiCad; phiên bản ghi vào hộ chiếu. Tìm theo MPN/bí danh; đối chiếu số chân và tên chân với Fact pinout; khớp ≥ 95 % → dùng, ghi lib_ref@version; lệch → không dùng im lặng.

- Sinh symbol từ Fact (.kicad_sym): số chân, tên, kiểu (power_in/input/output/bidirectional/passive) suy từ Fact pin.type; xếp chân theo nhóm (nguồn trên, GND dưới, bus trái/phải); ghi rõ "sinh từ DS rev X p.Y" vào mô tả symbol — đây là N1 áp vào ký hiệu.

- Chip không có Fact pinout ≥ NGƯỜI → sch.compose từ chối bước đó với E7002 "chưa có pinout đã duyệt cho U3 — nạp datasheet (G-DATA) hoặc xác nhận pinout" — không bịa chân.

**6. Render ba mức và giao diện**

| **Mức**                  | **Điều kiện**                                                       | **Cách**                                                                                                                                                  | **Chất lượng**                                                                   |
|--------------------------|---------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| R1 (chính)               | Luôn — máy không cài KiCad                                          | Renderer nội bộ: kiutils đọc .kicad_sch + .kicad_sym → SVG (đường, chân, text, nhãn, ký hiệu power); PDF/PNG bằng cairosvg/resvg; kiểm bbox text không đè | Đọc được, cùng quy ước KiCad (lưới, hướng chân); không cam kết giống KiCad 100 % |
| R2 (tuỳ chọn, ngoài máy) | Người có KiCad ở máy khác                                           | sch.export gói tệp; người mở/kiểm/in ở máy đó; nạp lại qua sch.import                                                                                     | Chuẩn KiCad                                                                      |
| R3 (suy giảm)            | Không sinh được .kicad_sch (thiếu SKiDL/kiutils, hoặc bước 1–5 lỗi) | Sơ đồ khối + đồ thị net hiện có của CKM (không đổi)                                                                                                       | Như hiện nay — hệ thống cũ không bị ảnh hưởng                                    |

SVG được gắn id theo ref/net để tab Thiết kế (khối A5.8) làm tương tác: bấm ký hiệu → panel Fact + nguồn + BOM; bấm net → tô sáng toàn net + kết quả ERC liên quan; hover chân → AF và net. Diff giữa hai phiên bản sch: so netlist (thêm/bớt linh kiện/net) + so vị trí (chỉ báo "đã bố cục lại"), trình bày bằng lời theo E3.

**7. Round-trip với KiCad**

1.  Máy này không cài KiCad: người bấm "Xuất gói" (sch.export) → mở/sửa ở máy có KiCad (hoặc trong tương lai trình sửa nhẹ của EIDE) → chép tệp về thư mục dự án. EIDE theo dõi mtime tệp trong dự án.

2.  Người bấm "Nạp lại" (hoặc tác tử đề nghị khi thấy tệp đổi) → sch.import → ING-43 KICAD đọc → netlist mới.

3.  So với CKM: (a) chỉ đổi vị trí/nhãn → changeset human "bố cục", không STALE; (b) đổi giá trị linh kiện → cập nhật BOM/Fact NGƯỜI, STALE ERC; (c) thêm/bớt linh kiện hoặc net → thẻ hỏi "cập nhật module_graph theo sơ đồ, hay giữ CKM và đánh dấu sơ đồ lệch?" — không tự chọn.

4.  Mọi lần sinh lại (sch.write) giữ uuid theo ref để KiCad không mất vị trí người đã kéo: bố cục cũ là đầu vào ưu tiên của sch.place (chỉ đặt phần mới), trừ khi người chọn "bố cục lại toàn bộ".

5.  Tệp do người sửa mà tác tử muốn ghi đè → G-FILE (như mã nguồn).

**8. An toàn tích hợp — quy trình đưa vào**

| **Bước**                 | **Yêu cầu bắt buộc**                                                                                                                          | **Bằng chứng**                                                                                               |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| A. Nhánh riêng           | feature/sch-44; không chạm tệp ngoài eide/sch/, registry (thêm), hook (nhánh mới), policy (luật mới), migration (cộng thêm), UI A5.8          | Diff review: danh sách tệp thay đổi                                                                          |
| B. Cờ tắt                | Toàn bộ bộ hồi quy (76 TC ×5, CX, MEM, ING) giống 100 % kết quả trước khi merge; token khối tool không đổi                                    | Báo cáo so sánh tự động                                                                                      |
| C. Cờ bật, không gọi sch | Bộ hồi quy vẫn giống; chỉ khối tool tăng ≤ 1,2 k token                                                                                        | Như trên                                                                                                     |
| D. Cờ bật, gọi sch       | SCH01–18 đạt; ERC (SKiDL + nội bộ) 0 lỗi trên 3 mạch mẫu (STM32 Blue Pill, ESP32 devkit, ATmega328P + TMP102)                                 | Tệp .kicad_sch qua bộ kiểm lược đồ nội bộ; kiểm mở bằng KiCad 8/9 làm ở máy CI/máy khác (không phải máy này) |
| E. Suy giảm              | Gỡ kiutils → không render, báo đúng; gỡ SKiDL → R3; không có lỗi cứng, không bao giờ đề nghị cài KiCad                                        | SCH15–17                                                                                                     |
| F. Rollback              | Hoàn tác changeset sch.write khôi phục đúng; tắt cờ sau khi đã dùng → dự án mở bình thường, tệp sch còn nguyên nhưng không được tool nào chạm | SCH18                                                                                                        |
| G. Migration             | down() xoá bảng sch_sheets và cột nullable không ảnh hưởng dữ liệu cũ; kiểm trên bản sao dự án thật                                           | Script kiểm                                                                                                  |

**9. Giao diện — khối A5.8 (bổ sung mô hình UI)**

| **Widget**                                                                            | **Loại** | **Yêu cầu**            |
|---------------------------------------------------------------------------------------|----------|------------------------|
| Nút "Sinh sơ đồ KiCad" (chọn flat/hierarchical, module nào)                           | action   | SCH-01, SCH-04         |
| SVG tương tác: bấm ký hiệu → Fact/nguồn/BOM; bấm net → tô sáng + ERC; hover chân → AF | display  | SCH-06, SCH-07         |
| Băng chất lượng bố cục (0 chồng / 0 cắt / % nhãn) + nút "Bố cục lại"                  | display  | SCH-05                 |
| Mức render đang dùng (nội bộ / sơ đồ khối); không bao giờ đề nghị cài KiCad           | display  | SCH-08, SCH-09         |
| Diff sơ đồ v(n-1)→v(n) bằng lời + tô                                                  | display  | SCH-10                 |
| Xuất gói (mở ở máy có KiCad) · Nạp lại · thẻ hỏi khi CKM ≠ sơ đồ                      | action   | SCH-11, SCH-12, SCH-13 |
| Symbol sinh từ Fact: xem, xác nhận, sửa kiểu chân                                     | edit     | SCH-14, SCH-15         |
| Cảnh báo pinout chưa duyệt (E7002) với nút nạp datasheet                              | display  | SCH-03                 |
| Xuất gói sch (.kicad_sch + .kicad_sym + .net + SVG) vào snapshot                      | action   | SCH-16                 |
| Cờ tính năng schematic (Thiết lập) — bật/tắt, mặc định tắt                            | edit     | SCH-17                 |

**10. Ca kiểm SCH01–SCH18**

| **Mã** | **Ca**                                           | **Mong đợi**                                                                          |
|--------|--------------------------------------------------|---------------------------------------------------------------------------------------|
| SCH01  | Cờ tắt, chạy toàn bộ hồi quy                     | Giống 100 % kết quả trước; tool sch.\* không xuất hiện                                |
| SCH02  | Cờ bật, không gọi sch, chạy hồi quy              | Giống 100 %; token khối tool tăng ≤ 1,2 k                                             |
| SCH03  | Sinh sơ đồ cho ATmega328P + TMP102 (CKM đủ Fact) | Netlist đẳng cấu; ERC 0; .kicad_sch mở trong KiCad 8/9                                |
| SCH04  | Chip U3 chưa có pinout ≥ NGƯỜI                   | E7002, đề nghị nạp datasheet; không bịa chân                                          |
| SCH05  | Symbol lib lệch tên chân với Fact                | Không dùng lib; sinh symbol từ Fact; cảnh báo                                         |
| SCH06  | Mạch 40 linh kiện, 3 module                      | Tiêu chí bố cục đạt (0 chồng/0 cắt/≤ 3 gấp); % nhãn ≤ 70                              |
| SCH07  | Mạch 120 linh kiện                               | Đề nghị hierarchical; mỗi sheet đạt tiêu chí                                          |
| SCH08  | Render nội bộ (không có KiCad trên máy)          | SVG có id theo ref; số ký hiệu = số ref; text không đè                                |
| SCH09  | Bấm ký hiệu trên SVG                             | Panel Fact + nguồn; bấm net → tô sáng + ERC                                           |
| SCH10  | Sinh lại sau khi thêm 1 linh kiện                | uuid cũ giữ; chỉ phần mới được đặt; diff bằng lời đúng                                |
| SCH11  | Người kéo ký hiệu trong KiCad rồi nạp lại        | Changeset human "bố cục"; không STALE                                                 |
| SCH12  | Người thêm net mới trong KiCad rồi nạp lại       | Thẻ hỏi cập nhật CKM hay đánh dấu lệch; không ghi đè im lặng                          |
| SCH13  | Tác tử sinh lại khi người đã sửa tệp             | G-FILE                                                                                |
| SCH14  | SKiDL sinh net không có trong CKM (mô hình bịa)  | E7001 với diff; dừng                                                                  |
| SCH15  | Máy không có KiCad (mặc định)                    | Toàn bộ đường ống chạy bằng Python thuần; không có lời đề nghị cài KiCad ở bất kỳ đâu |
| SCH16  | Không có SKiDL/kiutils                           | R3: sơ đồ khối như cũ; thông điệp đề nghị cài                                         |
| SCH17  | Cùng CKM chạy 5 lần                              | Toạ độ giống hệt (bố cục xác định)                                                    |
| SCH18  | Hoàn tác changeset sch.write; tắt cờ             | Tệp về trước; dự án mở bình thường                                                    |

**11. Yêu cầu SCH-01…SCH-22 và lộ trình**

| **Mã** | **Yêu cầu**                                                                                        |
|--------|----------------------------------------------------------------------------------------------------|
| SCH-01 | Sinh sơ đồ từ CKM qua SKiDL; mô hình viết SKiDL, mã kiểm                                           |
| SCH-02 | Netlist sinh ra đẳng cấu với CKM; lệch → E7001, dừng                                               |
| SCH-03 | Không bịa chân: pinout phải ≥ NGƯỜI; thiếu → E7002                                                 |
| SCH-04 | Style flat/hierarchical; chọn module                                                               |
| SCH-05 | Bố cục theo module với tiêu chí số; xác định, lặp lại được                                         |
| SCH-06 | Render SVG có id theo ref/net                                                                      |
| SCH-07 | Tương tác: ký hiệu → Fact/nguồn; net → tô sáng + ERC                                               |
| SCH-08 | Renderer nội bộ là đường chính; suy giảm về sơ đồ khối                                             |
| SCH-09 | Không cài, không gọi, không đề nghị cài KiCad trên máy; thư viện ký hiệu chỉ là dữ liệu qua G-DATA |
| SCH-10 | Diff sơ đồ bằng lời (E3)                                                                           |
| SCH-11 | Xuất gói để mở ở máy khác; theo dõi mtime; Nạp lại                                                 |
| SCH-12 | Round-trip phân loại thay đổi: bố cục / giá trị / cấu trúc                                         |
| SCH-13 | Thay đổi cấu trúc từ KiCad → thẻ hỏi, không ghi đè CKM im lặng                                     |
| SCH-14 | Symbol lib chính thức đối chiếu Fact ≥ 95 %                                                        |
| SCH-15 | Symbol sinh từ Fact có ghi nguồn                                                                   |
| SCH-16 | Gói sch vào snapshot/release                                                                       |
| SCH-17 | Cờ features.schematic mặc định tắt; tắt = không có nhánh mã sch nào chạy                           |
| SCH-18 | Không đổi hợp đồng tool cũ; lược đồ chỉ cộng thêm; migration có down()                             |
| SCH-19 | Hồi quy hai chế độ giống 100 % trước khi merge                                                     |
| SCH-20 | uuid ổn định theo ref; giữ bố cục người đã sửa khi sinh lại                                        |
| SCH-21 | Mọi tệp sch là changeset hoàn tác được; G-FILE khi ghi đè tệp người sửa                            |
| SCH-22 | PCB/Gerber vẫn ngoài phạm vi                                                                       |

| **Bước** | **Nội dung**                                                                                | **Ca kiểm**                   | **Điều kiện**                |
|----------|---------------------------------------------------------------------------------------------|-------------------------------|------------------------------|
| SCH-A    | Cờ + module sch/ + sch.compose/netlist/symbols (lib) + E7001/E7002 + R3; hồi quy hai chế độ | SCH01, 02, 03, 04, 14, 16, 18 | Sau G4 (CKM/Fact) của MDD-40 |
| SCH-B    | sch.place + sch.write + sch.render (R1/R2) + A5.8 SVG tương tác                             | SCH05–09, 15, 17              | SCH-A                        |
| SCH-C    | Round-trip: sch.open/import, phân loại thay đổi, uuid ổn định, G-FILE                       | SCH10–13                      | ING-D                        |
| SCH-D    | Hierarchical sheets; symbol sinh từ Fact có giao diện xác nhận; gói vào snapshot            | SCH07, SCH-16                 | SCH-C                        |

Thư viện (Python thuần, pip trong sandbox dự án): skidl, kiutils (đọc/ghi S-expression KiCad 8/9), networkx (bố cục), cairosvg hoặc resvg (PDF/PNG), sexpdata. Dữ liệu: kicad-symbols (.kicad_sym) tải theo git tag có hash, cache ở M4. KHÔNG cài KiCad, KHÔNG dùng kicad-cli.
