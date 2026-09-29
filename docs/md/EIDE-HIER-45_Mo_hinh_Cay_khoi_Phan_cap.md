**EIDE — MÔ HÌNH CÂY KHỐI PHÂN CẤP CỦA MẠCH**

Mạch → khối → khối con → linh kiện (lá) · Port ở biên khối · Net theo phạm vi · flatten bằng mã · STALE theo cây · thư viện khối có phiên bản · giao diện cây

*Mã tài liệu EIDE-HIER-45 · v1.0 · 26/09/2026 · sửa đổi MDD-40 v3.0 C2/E2/E5.4 và SCH-44 §4*

|                                          |                                                                                                                                                                                                                                                            |
|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**                          | EIDE-HIER-45 (Hierarchical Circuit Model) v1.0                                                                                                                                                                                                             |
| **Quyết định chủ sản phẩm (26/09/2026)** | \(1\) Linh kiện là LÁ của cây khối — một mô hình duy nhất; (2) độ sâu đệ quy không giới hạn, bố cục/UI khuyến nghị ≤ 4 cấp và cảnh báo khi sâu hơn; (3) khối tái dùng có phiên bản block@semver như hộ chiếu chip                                          |
| **Quan hệ**                              | Thay thế định nghĩa Module/Net trong MDD-40 C2; bổ sung E2 (hiện vật "Cây khối"), E5.4 (STALE theo cây); SCH-44 §4 bố cục và hierarchical sheet dựng từ cây này; ING-43 §4.4 đọc .kicad_sch phân cấp về cây. Yêu cầu HIER-01…HIER-18; khối UI A5.1 mở rộng |
| **Tương thích ngược**                    | Cột parent_id/kind nullable; module cũ = kind=block, parent=board mặc định; net cũ = scope=board; netlist phẳng hiện có = flatten(cây) → mọi tool cũ (board.check, bom.build, diagram.render, sim, target) không đổi                                       |
| **Ngày**                                 | 26/09/2026                                                                                                                                                                                                                                                 |
| **Đề tài**          | PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI)                                |
| **Khung**                                | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu                                                                                                                                                            |
| **Tác giả**                              | Vũ Trí Công                                                                                                                                                                                                                                                |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                                                                                                 | **Người sửa** |
|---------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 26/09/2026 | Bản đầu: rà soát 6 lỗ hổng của mô hình phẳng; mô hình cây (Module/Port/Net/Instance); lược đồ Store; flatten và kiểm bất biến; Fact/REQ theo cấp; STALE theo cây; thư viện khối có phiên bản; ánh xạ SKiDL/KiCad phân cấp; trình bày & UI; migration; HIER01–16; HIER-01…18. | VTC           |

**1. Rà soát mô hình hiện tại**

| **\#** | **Lỗ hổng trong MDD-40 v3.0**                                            | **Hậu quả**                                                                             | **Giải quyết ở** |
|--------|--------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|------------------|
| 1      | Module chỉ có GỒM → linh kiện, THỰC_HIỆN → REQ; không có Module → Module | Không tả được "khối trong khối"; module_graph phẳng                                     | §2, §3           |
| 2      | Net toàn cục, không thuộc khối; không có Port                            | Không có biên khối → không đóng gói, không tái dùng, KiCad hierarchical không dựng được | §2.2–2.3         |
| 3      | Chuỗi STALE cứng REQ→phương án→module→…                                  | Sửa khối con làm STALE cả mạch hoặc không STALE gì                                      | §6               |
| 4      | SCH-44 nói "hierarchical sheets theo module" nhưng không có cây          | Chỉ làm được sheet một tầng                                                             | §7               |
| 5      | Sơ đồ khối/BOM/ERC phẳng                                                 | Mạch lớn không đọc được; ERC không chỉ ra "khối nào"                                    | §8               |
| 6      | Không có thư viện khối tái dùng                                          | Mỗi dự án vẽ lại LDO, pull-up, reset…                                                   | §5               |

**2. Mô hình cây khối**

![](../img/h1_hierarchy.png)

*Hình 1. Cây khối bốn cấp của mạch mẫu; Port ở biên; net cục bộ; lá là linh kiện*

**2.1. Thực thể**

| **Thực thể**                              | **Thuộc tính**                                                                                                                                                                     | **Ghi chú**                                                                                                        |
|-------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| Module (nút cây)                          | id, parent_id (null = gốc), kind ∈ {board, block, subblock, leaf}, name, path ("/mcu/xtal"), order, lib_ref? (block@semver nếu từ thư viện), explain                               | Một cây một gốc (board). Độ sâu không giới hạn; depth \> 4 → cảnh báo bố cục/UI (không cấm)                        |
| Instance của linh kiện = Module kind=leaf | ref (U1), mpn, value, footprint, passport_ref (chip), bom_row, facts\[\]                                                                                                           | Lá không có con; Port của lá = pin theo Fact pinout (VÀNG/NGƯỜI); không có Fact pinout → không tạo được lá (E7002) |
| Port                                      | id, module_id, name, dir ∈ {in, out, bidir, power_in, power_out, passive}, kind ∈ {single, bus}, members\[\] (bus: SDA, SCL), constraints (v_min/max, i_max, level), fact_refs\[\] | Ở lá: một Port cho mỗi pin (sinh tự động từ Fact). Ở khối: do người/tác tử khai; là "hợp đồng" của khối            |
| Net                                       | id, scope_module_id, name, kind ∈ {signal, power, gnd, bus_member}, facts\[\] (áp danh định, pull-up…)                                                                             | Net chỉ nối Port của các con TRỰC TIẾP và Port của chính khối đó; không nối xuyên cấp                              |
| Connection                                | net_id ↔ port_id (port của khối con hoặc port của chính khối = "lên cha")                                                                                                          | Một Port nối ≤ 1 net trong phạm vi khối cha                                                                        |
| Bus                                       | name, members\[\] (tên tín hiệu), protocol (I2C/SPI/UART/CAN/…), facts (tốc độ, pull-up)                                                                                           | Bus là Port kind=bus; khi flatten tách thành từng net thành viên                                                   |
| Fact / REQ theo cấp                       | subject = "module:/mcu" \| "port:/mcu.I2C0" \| "net:/board.+3V3" \| "leaf:U1" \| "pin:U1.28"                                                                                       | Ràng buộc cấp khối kiểm được bằng tổng/so sánh với các con (§4.3)                                                  |

**2.2. Quy tắc phạm vi và đóng gói**

1.  Net thuộc đúng một khối (scope). Nó chỉ chạm Port của các khối con trực tiếp và Port của chính khối (để "lên" cha). Không có dây xuyên hai cấp — muốn ra ngoài phải khai Port.

2.  Port là hợp đồng: sửa nội bộ khối mà không đổi tập Port (tên, hướng, kiểu, ràng buộc) thì bên ngoài không cần biết (không STALE ra ngoài). Đổi Port → §6.

3.  Nguồn/GND: là Port kind=power của từng khối, nối theo cây như tín hiệu khác; không có "net toàn cục ngầm". Khi render/KiCad, power ports được vẽ bằng ký hiệu power theo quy ước, nhưng dữ liệu vẫn qua Port (để kiểm I.total theo cây).

4.  Tên đầy đủ (path) là duy nhất: "/board/mcu/xtal.Y1", net "/board/mcu.VDD"; ref linh kiện (U1, R1) duy nhất toàn mạch để BOM/KiCad không đổi.

**2.3. Lược đồ Store (cộng thêm, có down())**

> ALTER TABLE module ADD COLUMN parent_id TEXT NULL REFERENCES module(id);
>
> ALTER TABLE module ADD COLUMN kind TEXT NOT NULL DEFAULT 'block'; -- board\|block\|subblock\|leaf
>
> ALTER TABLE module ADD COLUMN path TEXT; ALTER TABLE module ADD COLUMN lib_ref TEXT NULL; -- block@semver
>
> CREATE TABLE port (id TEXT PK, module_id TEXT, name, dir, kind, members_json, constraints_json, UNIQUE(module_id,name));
>
> ALTER TABLE net ADD COLUMN scope_module_id TEXT NULL; -- NULL → migrate thành board
>
> CREATE TABLE connection (net_id TEXT, port_id TEXT, PRIMARY KEY(net_id, port_id));
>
> -- migration: mọi module cũ: parent = board (tạo board nếu chưa có), kind = block; linh kiện cũ → leaf con của module chứa nó;
>
> -- net cũ: scope = board; kết nối cũ (ref.pin ↔ net) → connection(net, port(leaf, pin)) qua Port "lên cha" tự sinh ở mỗi khối.
>
> -- down(): xoá bảng port/connection, cột parent_id/kind/path/lib_ref/scope; netlist phẳng vẫn còn nguyên (không mất dữ liệu cũ).

**3. Flatten và bất biến**

Mọi tool hiện có (board.check ERC, bom.build, diagram.render, sim, target) tiếp tục nhận netlist phẳng. Netlist phẳng KHÔNG còn là dữ liệu gốc mà là kết quả xác định của flatten(cây):

> def flatten(root):
>
> uf = UnionFind() \# hợp nhất net theo Port
>
> for m in walk(root): \# mọi khối, mọi cấp
>
> for net in m.nets:
>
> for port in net.connections:
>
> if port.module is m: \# port "lên cha": net này ≡ net ở cha nối vào port đó
>
> uf.union(net, parent_net_of(port))
>
> elif port.module.kind == "leaf": uf.attach(net, (port.module.ref, port.pin))
>
> else: \# port của khối con: net này ≡ net nội bộ của con nối vào port đó
>
> uf.union(net, inner_net_of(port))
>
> return { canonical_name(group): sorted(pins) for group in uf.groups() } \# tên = net ở cấp cao nhất

| **Bất biến (kiểm bằng mã sau mỗi thay đổi)**                                                                     | **Mã lỗi**                                     |
|------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| Cây không có chu trình; mỗi module đúng một cha (trừ gốc)                                                        | E8001                                          |
| Port của khối con chỉ được nối bởi net trong khối cha trực tiếp                                                  | E8002                                          |
| Port "lên cha" của khối X chỉ được nối bởi đúng một net trong X và đúng một net trong cha(X)                     | E8003                                          |
| Lá có Port = tập pin của Fact pinout (không thừa, không thiếu)                                                   | E8004                                          |
| Bus port: members của hai đầu khớp tên/số lượng                                                                  | E8005                                          |
| flatten(cây) trước và sau một thay đổi "nội bộ" (không chạm Port) cho cùng tập (ref.pin) trên các net ngoài khối | E8006 — đây là kiểm chứng của quy tắc đóng gói |
| Ràng buộc Port thoả với net nối vào (mức áp, dòng)                                                               | ERC theo cấp (board.check mở rộng)             |

**4. Fact và REQ theo cấp**

**4.1. Gắn ở đâu**

- REQ chức năng gắn vào khối thực hiện nó (THỰC_HIỆN); REQ phi chức năng (dòng, nhiệt, kích thước) gắn vào khối hoặc mạch. Ma trận truy vết (UC16) đi theo cây: REQ → khối → khối con → lá → mã.

- Fact của lá đến từ datasheet (như hiện nay). Fact của khối là (a) khai báo ở Port/khối (Iout.max của khối nguồn, addr của khối cảm biến) với nguồn là datasheet của lá quyết định, hoặc (b) suy dẫn bằng mã từ các con (tổng dòng tiêu thụ, số chân dùng).

**4.2. Suy dẫn và kiểm ràng buộc theo cây (bằng mã, không LLM)**

| **Ràng buộc**                                                                  | **Cách kiểm**                                                            | **Vế dữ liệu**                                               |
|--------------------------------------------------------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------------|
| Dòng cấp: Iout.max(khối nguồn) ≥ Σ I.max(khối tiêu thụ nối vào Port 3V3)       | Tổng theo cây các Fact I.max của lá/khối con nối vào net ứng với Port đó | Cả hai vế ≥ BẠC/NGƯỜI; thiếu → "chưa đủ dữ kiện", không đoán |
| Mức logic: level(Port A) tương thích level(Port B) trên cùng net               | So Fact VOH/VIH của lá hai đầu (fact.compare, luật mức logic)            | Như TC013                                                    |
| Địa chỉ bus không trùng: các khối trên cùng bus I2C có addr khác nhau          | Tập Fact addr của lá nối vào bus                                         | TMP102 0x48 vs 0x48 → phát hiện                              |
| Pull-up bus: mỗi bus I2C có đúng một cụm pull-up trong phạm vi khối sở hữu bus | Đếm lá R nối SDA/SCL ↔ VDD trên net flatten                              | Như TC038 nhưng chỉ ra "khối nào"                            |
| Ngân sách chân: số Port của khối MCU ≤ số pin khả dụng theo AF                 | Fact pinout + AF                                                         | Gợi ý đổi chân                                               |

**5. Thư viện khối tái dùng (block@semver)**

- Một khối thư viện = gói: manifest (name, version, ports\[\], params: ví dụ Vout, Iout), netlist nội bộ (cây con), Fact kèm nguồn (datasheet của lá), BOM, explain, ca kiểm ERC riêng, và (nếu có) mảnh .kicad_sch bố cục sẵn.

- Lưu: dự án (.eide/blocks/) → người dùng (~/.eide/blocks/) → gói toàn cục M4 (đã phát hành). Nâng cấp phiên bản trong dự án là changeset; hộ chiếu/snapshot ghi block@semver đã dùng (như chip).

- Tác tử: khi arch.decompose gặp nhu cầu quen (nguồn 3V3 từ 5V, reset RC, dao động thạch anh, pull-up I2C, chuyển mức) → đề xuất khối thư viện qua ask_user, nêu tham số và Fact; người duyệt (G-DESIGN) mới đặt vào cây.

- Tham số hoá: khối có params; đặt vào cây là instantiate(block, params) → sinh lá cụ thể (R theo Vout…), mọi số từ công thức có nguồn (calc.eval) — không bịa.

- "Trích khối từ mạch hiện có": người chọn một khối trong cây → "Lưu làm khối thư viện" → tác tử kiểm tính khép kín (chỉ giao tiếp qua Port) rồi đóng gói v1.0.0.

**6. STALE theo cây**

| **Thay đổi**                                       | **STALE lan tới**                                                                                                  | **Không lan tới**                                                         |
|----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Sửa nội bộ khối X (lá, net cục bộ) không đổi Port  | Chính X (ERC, bố cục sheet của X, BOM), các hiện vật hạ nguồn của X (mã dùng pinout của lá trong X, sim liên quan) | Anh em của X; cha của X chỉ nhận cờ "con đã đổi" (thông tin), không STALE |
| Đổi Port của X (thêm/bớt/đổi hướng/kiểu/ràng buộc) | X, cha của X (net nối Port đó), mọi khối anh em nối vào net đó, ERC cấp cha, sheet cha                             | Các nhánh không nối                                                       |
| Đổi Fact của lá (datasheet mới/xác nhận)           | Mọi ràng buộc theo cây dùng Fact đó (từ lá lên tới gốc theo đường Port)                                            | Nhánh khác                                                                |
| Đổi REQ gắn cấp mạch                               | Các khối THỰC_HIỆN REQ đó và hạ nguồn của chúng                                                                    | Khối không liên quan                                                      |
| Nâng phiên bản khối thư viện                       | Như "đổi Port" nếu manifest Port đổi; như "nội bộ" nếu chỉ đổi bên trong                                           | —                                                                         |

Băng STALE trên UI ghi rõ "vì cs-0123 (anh sửa Port I2C0 của khối MCU)" và cây khối tô màu các nút bị ảnh hưởng; "Chấp nhận STALE" áp cho một nút hoặc cả nhánh.

**7. Ánh xạ sang SKiDL và KiCad phân cấp (sửa SCH-44 §4)**

- SKiDL: mỗi khối → một hàm Python có tham số là các Port (Net/Bus objects); lá → Part; net cục bộ tạo trong hàm; gốc gọi các hàm và nối Port. Cây → cấu trúc gọi hàm 1-1; netlist SKiDL = flatten (kiểm E8006 bằng cách so với flatten của mình).

- KiCad: style=hierarchical → mỗi khối (kind=block/subblock) một sheet (.kicad_sch riêng), Port của khối → hierarchical sheet pin, net "lên cha" → hierarchical label trong sheet con; lá vẽ trong sheet của khối chứa nó. Style=flat → toàn bộ trên một sheet, khối thành vùng (như SCH-44 §4), Port thành global label có tiền tố path.

- Bố cục theo cây: đặt vùng cho khối cấp 1 theo luồng; đệ quy đặt con trong vùng cha; depth \> 4 → tự chuyển sang hierarchical và cảnh báo.

- Round-trip: ING-43 đọc .kicad_sch phân cấp → dựng cây (sheet → Module, sheet pin → Port, hierarchical label → net "lên cha"); so cây với CKM theo path; thay đổi cấu trúc → thẻ hỏi như SCH-44 §7.

**8. Trình bày và giao diện (E2 bổ sung: hiện vật "Cây khối")**

| **Mặt**                | **Nội dung**                                                                                                                                                                                                                                                                                                                       |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Dạng máy               | Cây Module/Port/Net/Connection trong Store (§2.3); flatten dẫn xuất                                                                                                                                                                                                                                                                |
| Lớp giải thích         | Mỗi khối: làm gì (REQ nào), giao tiếp gì (Port), gồm gì (con), dựa vào đâu (Fact nguồn), khác bản trước, việc tiếp theo, tin được đến đâu (tầng thấp nhất trong khối)                                                                                                                                                              |
| Dạng người             | Tab Thiết kế A5.1: cây gập/mở (mạch → khối → khối con → linh kiện), breadcrumb path, bấm khối → sơ đồ khối con + bảng Port + net cục bộ + ERC của khối + BOM con; bấm lá → Fact/BOM/pinout; kéo thả lá/khối giữa cha (đổi cây = changeset); thêm khối từ thư viện; "Lưu làm khối thư viện"; tô STALE theo nút; cảnh báo depth \> 4 |
| Người sửa gì → khi lưu | Đổi tên/sắp xếp = trình bày (không STALE); di chuyển lá/khối, thêm/bớt Port, nối Port = cấu trúc (§6); sửa tham số khối thư viện = instantiate lại                                                                                                                                                                                 |

**9. Ca kiểm HIER01–HIER16 và yêu cầu**

| **Mã** | **Ca**                                                   | **Mong đợi**                                                                  |
|--------|----------------------------------------------------------|-------------------------------------------------------------------------------|
| HIER01 | Migration dự án cũ (module phẳng)                        | Cây board→block→leaf sinh đúng; flatten = netlist cũ 100 %; down() phục hồi   |
| HIER02 | Tạo khối con trong khối MCU (dao động)                   | Port XI/XO/GND; net cục bộ; flatten không đổi tập (ref.pin) bên ngoài (E8006) |
| HIER03 | Nối xuyên cấp (net của board chạm pin lá trong khối con) | E8002 từ chối; gợi ý khai Port                                                |
| HIER04 | Lá không có Fact pinout                                  | E7002/E8004; không tạo lá                                                     |
| HIER05 | Sửa giá trị R trong khối cảm biến                        | STALE chỉ trong khối + hạ nguồn; anh em không STALE                           |
| HIER06 | Đổi Port I2C0 của khối MCU                               | STALE cha + khối cảm biến nối vào; cây tô đúng nút                            |
| HIER07 | Kiểm Iout.max(nguồn) ≥ Σ I.max                           | Tính đúng theo cây; thiếu Fact → "chưa đủ dữ kiện"                            |
| HIER08 | Hai khối cùng addr I2C trên một bus                      | Phát hiện, chỉ ra khối                                                        |
| HIER09 | Đặt khối thư viện LDO-3V3@1.2.0 với Vout=3,3             | Instantiate đúng lá; Fact có nguồn; snapshot ghi block@semver                 |
| HIER10 | Trích một khối thành thư viện                            | Kiểm khép kín; đóng gói v1.0.0; dùng lại ở dự án khác                         |
| HIER11 | Cây sâu 6 cấp                                            | Cảnh báo depth; bố cục chuyển hierarchical; vẫn hợp lệ                        |
| HIER12 | Sinh SKiDL từ cây                                        | Hàm theo khối; netlist SKiDL = flatten                                        |
| HIER13 | Sinh .kicad_sch hierarchical                             | Mỗi khối một sheet; sheet pin = Port; nạp lại dựng lại đúng cây               |
| HIER14 | Người kéo lá từ khối A sang B trên UI                    | Changeset human; Port/net cập nhật hoặc thẻ hỏi nếu mất kết nối               |
| HIER15 | ERC báo lỗi trong khối con                               | Vị trí ghi path khối; bấm → tô sáng trong sheet của khối                      |
| HIER16 | Hồi quy toàn bộ (76 TC, CX, MEM, ING, SCH) sau migration | Giống 100 %                                                                   |

| **Mã**  | **Yêu cầu**                                                                                     |
|---------|-------------------------------------------------------------------------------------------------|
| HIER-01 | Module là nút cây có parent/kind/path; linh kiện là lá; độ sâu đệ quy; \> 4 cảnh báo            |
| HIER-02 | Port ở biên khối: tên, hướng, kiểu (single/bus), ràng buộc, fact_refs; lá có Port = pin từ Fact |
| HIER-03 | Net theo phạm vi khối; nối chỉ Port của con trực tiếp hoặc Port "lên cha"                       |
| HIER-04 | flatten(cây) bằng mã là nguồn cho mọi tool phẳng; tool cũ không đổi                             |
| HIER-05 | Bất biến E8001–E8006 kiểm sau mỗi thay đổi                                                      |
| HIER-06 | Fact/REQ gắn được ở mọi cấp; ràng buộc theo cây kiểm bằng mã                                    |
| HIER-07 | STALE theo cây: nội bộ không lan; Port lan tới cha và anh em nối                                |
| HIER-08 | Thư viện khối block@semver: manifest, params, instantiate có nguồn, 3 tầng lưu                  |
| HIER-09 | Trích khối từ mạch thành thư viện có kiểm khép kín                                              |
| HIER-10 | SKiDL 1-1 với cây; netlist SKiDL = flatten                                                      |
| HIER-11 | KiCad hierarchical: sheet = khối, sheet pin = Port; flat = vùng + global label                  |
| HIER-12 | Round-trip .kicad_sch phân cấp → cây                                                            |
| HIER-13 | UI cây gập/mở, breadcrumb, sơ đồ khối con, bảng Port, ERC theo khối, kéo thả = changeset        |
| HIER-14 | Lớp giải thích cho khối (7 câu)                                                                 |
| HIER-15 | Migration cộng thêm có down(); dự án cũ chạy như trước                                          |
| HIER-16 | Snapshot/hộ chiếu ghi block@semver đã dùng                                                      |
| HIER-17 | ERC/BOM/truy vết báo theo path khối                                                             |
| HIER-18 | Hồi quy toàn bộ giống 100 % sau migration                                                       |

**Lộ trình**

| **Bước** | **Nội dung**                                                                 | **Ca kiểm**       | **Đi cùng**                     |
|----------|------------------------------------------------------------------------------|-------------------|---------------------------------|
| HIER-A   | Lược đồ + migration + flatten + bất biến; tool cũ chạy trên flatten          | HIER01–04, 16     | Trước SCH-A (SCH dựng trên cây) |
| HIER-B   | Fact/REQ theo cấp + kiểm ràng buộc theo cây + STALE theo cây + UI cây (A5.1) | HIER05–08, 14, 15 | G3/G4                           |
| HIER-C   | Thư viện khối (dự án/người dùng/M4), instantiate, trích khối                 | HIER09–10         | HIER-B                          |
| HIER-D   | SKiDL/KiCad phân cấp + round-trip (sửa SCH-44 §4, §7)                        | HIER11–13         | SCH-B/C                         |
