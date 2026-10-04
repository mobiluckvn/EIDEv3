# EIDE v3 — môi trường làm phần mềm nhúng có Agent cùng làm

EIDE là một môi trường để viết phần mềm cho vi điều khiển, trong đó có một Agent làm việc
**cùng** người kỹ sư chứ không làm thay. Hai bên cùng ghi vào một kho chung, và mọi thứ Agent
làm đều để lại dấu đủ để người kiểm lại được.

Ba luật nền, mọi thứ khác dựng trên chúng:

1. **Mỗi con số dùng để quyết định phải lần về được chỗ nó lấy ra** — trang tài liệu của hãng,
   dòng trong tệp cài đặt, hay câu nói nguyên văn của người dùng. Không có chỗ lấy thì Agent
   không có đường đặt con số đó vào kho.
2. **Không có kết quả "đạt" nào mà thiếu bằng chứng.** Mức đo phải nêu **trước** khi chạy. Đổi
   mức đo sau khi đã thấy kết quả thì phải qua một cửa duyệt của người.
3. **Mọi thay đổi gỡ lại được**, kể cả thay đổi do người tự gõ. Việc không gỡ lại được — như
   nạp chip — vẫn được ghi, và ghi kèm lý do vì sao không gỡ lại được.

| | |
|---|---|
| **Đề tài** | Phát triển phần mềm nhúng có ứng dụng trí tuệ nhân tạo |
| | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — Học viện Công nghệ Bưu chính Viễn thông |
| **Học viên** | Vũ Trí Công · **Hướng dẫn:** TS. Nguyễn Trung Hiếu |
| **Chạy trên** | macOS · lõi Python + giao diện Swift · mô hình `gemini-3.8-flash` |

---

## Mục lục

1. [Nhìn một lượt: EIDE làm được gì](#1--nhìn-một-lượt-eide-làm-được-gì)
2. [Người và Agent làm việc với nhau thế nào](#2--người-và-agent-làm-việc-với-nhau-thế-nào)
3. [Những thứ giữ cho Agent không nói sai](#3--những-thứ-giữ-cho-agent-không-nói-sai)
4. [Từng nhóm việc, chi tiết](#4--từng-nhóm-việc-chi-tiết)
5. [Cách thử: bốn mức](#5--cách-thử-bốn-mức)
6. [Kết quả thử đến nay](#6--kết-quả-thử-đến-nay)
7. [Ba việc thật đã làm xong](#7--ba-việc-thật)
8. [Những chỗ chưa làm được](#8--những-chỗ-chưa-làm-được)
9. [Cài và chạy](#9--cài-và-chạy)
10. [Mã nguồn bày thế nào](#10--mã-nguồn-bày-thế-nào)

---

## 1 · Nhìn một lượt: EIDE làm được gì

Agent có **127 công cụ** (118 bật mặc định, thêm 9 công cụ vẽ sơ đồ mạch bật bằng cờ), **7
Agent con**, **8 bộ hướng dẫn nạp theo việc**, **11 cửa duyệt**, và **11 tab** để người xem
việc đang tới đâu.

Bảng dưới xếp theo *việc người cần làm*, không theo cách chia mã:

| Việc | Số công cụ | Agent làm được gì |
|---|---|---|
| **Làm rõ đề bài** | 11 | hỏi gộp một cụm câu · ghi yêu cầu kèm câu nói nguyên văn · nêu 2–4 cách làm rồi để người chốt |
| **Đọc tài liệu** | 20 | nạp PDF, Word, Excel, slide, mã nguồn · đọc theo trang hoặc theo mục · rút hình kèm chữ trong hình · lấy con số **bằng mã**, không để mô hình đọc hộ |
| **Viết tài liệu** | 1 | dựng ra Word · PowerPoint · Excel · PDF từ nguồn Markdown nằm trong kho |
| **Thiết kế mạch** | 27 | bản đồ mạch · cây khối nhiều cấp · thư viện khối · sinh sơ đồ nguyên lý mở được bằng KiCad |
| **Viết mã** | 8 | đọc hiểu mã cũ trước khi sửa · dịch mã · bản đồ bộ nhớ · chạy bộ kiểm · đo xem bộ kiểm có đo gì không |
| **Chạy thử trên máy** | 2 | nêu mức đo trước, chạy, rồi đối chiếu |
| **Làm việc với bo thật** | 6 | dò bo · nạp · đọc ngược để so từng byte · đọc log · tìm chỗ treo · đọc khung ảnh từ chip |
| **Làm chip trên FPGA** | 5 | soát cú pháp Verilog · mô phỏng testbench · tổng hợp · đặt-đi dây và **đo Fmax thật** · đóng gói bitstream |
| **Nhớ và quản việc** | 28 | kho dữ liệu · sổ ghi việc · gỡ lại · bản chốt · nhánh · chia việc nhiều chặng |
| **Tự lo cho mình** | 4 | tìm công cụ · **tự viết công cụ mới** rồi tự kiểm trước khi dùng |

### Hai thứ Agent này làm mà phần lớn Agent khác không làm

**Nó mở lại tệp nó vừa tạo rồi đếm.** Không báo "đã ghi 12 KB". Dựng xong một tệp Word thì nó
mở tệp đó ra, đếm số đoạn, số bảng, số hình, rồi mới báo. Vì câu "ghi thành công" chỉ nói về
lời gọi, không nói về tệp nằm trên đĩa.

**Nó tự viết được công cụ mới cho chính nó.** Khi cần một tệp PowerPoint mà trong kho chưa có
công cụ nào làm được, nó tự viết một công cụ mới kèm bộ kiểm, chạy bộ kiểm, và chỉ nạp công cụ
đó khi bộ kiểm chạy đúng. Công cụ tự viết **không** nằm trong 122 công cụ kể ở trên — nó sinh
ra lúc chạy, trong đúng dự án đang làm. Việc này đã chạy thật, không phải tính năng trên giấy.

---

## 2 · Người và Agent làm việc với nhau thế nào

### 2.1 · Một phiên làm việc đi như sau

```
Người gõ một câu
   ↓
Agent đọc kho (yêu cầu cũ, tài liệu đã nạp, lịch sử sửa) rồi làm
   ↓
Mỗi việc Agent làm sinh một bản ghi có số bản — xem được, so được, gỡ lại được
   ↓
Việc nào có hậu quả thì dừng lại, hiện một thẻ cho người bấm Duyệt hoặc Không
   ↓
Người nhìn 11 tab bên phải để biết việc đang tới đâu
```

### 2.2 · Mười một cửa duyệt — chỗ Agent phải dừng và hỏi

Agent không được tự ý làm những việc có hậu quả. Mỗi loại việc có một cửa riêng, và thẻ hiện
lên nói rõ **sẽ làm gì, lên cái gì, hậu quả là gì**:

| Cửa | Dừng lại khi Agent muốn |
|---|---|
| `G-DATA` | ghi một con số vào kho, hoặc nâng mức tin được của nó |
| `G-DESIGN` | chốt một cách làm trong nhiều cách |
| `G-FILE` | ghi hoặc xoá tệp |
| `G-FLASH` | nạp vào chip — nói rõ nạp gì, vào đâu, đã có bản lùi chưa |
| `G-HIST` | gỡ lại, đổi nhánh, khôi phục bản cũ |
| `G-OPS` | chạy lệnh hệ thống |
| `G-QUAL` | đổi mức đo sau khi đã có kết quả |
| `G-SAFE` | việc có thể làm hỏng thiết bị |
| `G-SCOPE` | bắt đầu một việc lớn nhiều chặng |
| `G-SNAP` | ghi đè một bản chốt |
| `G-TOOL` | cài thêm công cụ vào máy |

### 2.3 · Mười một tab: người xem được việc, không chỉ xem chữ

Màn hình chat chỉ là một nửa. Nửa còn lại là 11 tab, mỗi tab là hình chiếu của kho:

| Tab | Nội dung |
|---|---|
| **A2** Yêu cầu & Giải pháp | yêu cầu kèm câu nói gốc · các cách làm · cách đã chốt · kế hoạch chia việc |
| **A3** Tài liệu & Nguồn | tài liệu đã nạp · cây tệp · tài liệu Agent đã viết ra |
| **A4** Tri thức mạch | bản đồ mạch: khối, chân, đường tín hiệu |
| **A5** Thiết kế | cây khối · sơ đồ nguyên lý · **cấu trúc phần mềm** · sơ đồ các mô-đun |
| **A6** Công cụ | công cụ nào có, công cụ nào Agent tự viết |
| **A7** Mã nguồn | tệp mã · kết quả dịch · **bản đọc hiểu mã trước khi sửa** |
| **A8** Mô phỏng | mức đo nêu trước · kết quả chạy · đối chiếu |
| **A9** Mạch thật | bo đang cắm · lần nạp gần nhất kèm mã băm, đích, kết quả đọc ngược |
| **A10** Nhật ký | sổ ghi việc — kiểm được là chưa ai sửa dòng nào |
| **A11** Lịch sử | từng lần sửa, ai sửa, vì sao, gỡ lại được không |
| **A14** Dự án & Bộ nhớ | thư mục dự án · bộ nhớ dài hạn · đồng hồ đo chỗ nhớ Agent đang dùng |

Giao diện **không tự nghĩ ra gì**. Mọi thứ hiện trên màn hình đều do lõi gửi sang qua đúng 16
loại lệnh. Lõi thêm loại khối mới thì giao diện vẽ được ngay, không phải sửa mã Swift. Lõi gửi
loại khối giao diện chưa biết thì giao diện **nói ra**, không bỏ qua im lặng.

Mọi cái chạm của người — gõ câu, bấm nút trong thẻ, đổi tab — đều đi qua **một cửa duy nhất**
vào lõi. Không có đường tắt nào.

---

## 3 · Những thứ giữ cho Agent không nói sai

Phần này là lý do EIDE khác một khung chat gắn thêm công cụ.

### 3.1 · Năm bậc tin được — không phải con số nào cũng bằng nhau

| Bậc | Lấy từ đâu | Dùng để làm gì |
|---|---|---|
| **VÀNG** | tài liệu của hãng, đã có người xác nhận | quyết định gì cũng được |
| **BẠC** | mã đọc thẳng từ trang PDF, chưa ai xem lại | dùng được, nhưng hiện nhãn đang chờ xem |
| **NGƯỜI** | người dùng nói, có trích nguyên văn | cao nhất khi tài liệu không nói gì |
| **CÀI ĐẶT** | đọc từ `.ioc`, `sdkconfig`, `.dts`, `.ld`, `.map` — máy đang cài thế nào | đem so với tài liệu để tìm chỗ lệch |
| **ĐỒNG** | đoán từ hình, từ chữ trong hình, từ tên gọi | **chỉ để gợi ý**, không để quyết |

Đường nâng từ BẠC lên VÀNG chỉ người đi được, Agent không đi được.

Và khi người dùng nói một con số, Agent phải trích **đúng câu họ nói**. Gán "người đã chọn"
cho một câu mà họ không hề chọn là nói sai về nguồn, mà NGƯỜI là bậc cao nhất — nên EIDE kiểm
lại: câu trích phải có thật trong sổ ghi việc, phải mang nghĩa lựa chọn, và phải nhắc đúng cách
làm được chọn.

### 3.2 · Ba lớp chặn quanh mỗi lời gọi công cụ

```
Agent muốn gọi một công cụ
   ↓
Lớp 1 — Luật:  công cụ này có được gọi lúc này không? trong chế độ này không?
   ↓
Lớp 2 — Cửa:   việc này có hậu quả không? có thì hiện thẻ, chờ người bấm
   ↓
Lớp 3 — Hộp cát: tệp này có nằm trong thư mục dự án không? vượt ra là chặn
   ↓
Chạy, rồi ghi vào sổ cả tham số lẫn kết quả lẫn mã lỗi
```

### 3.3 · Ba cách gỡ lại, dùng cho ba tình huống khác nhau

| Cách | Gỡ được gì | Dùng khi |
|---|---|---|
| Gỡ 30 giây | lần sửa vừa rồi | gõ sai, muốn lùi ngay |
| Gỡ theo lần sửa | một lần sửa cụ thể trong lịch sử | phát hiện sai sau vài bước |
| Về bản chốt | cả kho về đúng một mốc đã chốt | đi sai hướng, muốn về chỗ cũ |

Bản chốt **không bị xoá** khi khôi phục — lịch sử giữ nguyên, chỉ thêm một bước "đã về bản X".

### 3.4 · Giữ kín, bằng cấu trúc chứ không bằng lời dặn

- **Không mở cổng mạng nào.** Giao diện chạy lõi Python làm tiến trình con, nói với nhau qua
  đầu vào–đầu ra chuẩn. Không có cổng để ai gọi vào.
- **Agent bị khoá trong thư mục dự án.** Đường dẫn ra ngoài bị chặn ở lớp thứ ba.
- **Khoá mô hình chỉ nằm trong tệp `.env`**, tệp này không vào git, và không công cụ nào in nó
  ra.
- **Chỉ một mô hình được gọi.** Danh sách mô hình cho phép chỉ có `gemini-3.8-flash`. Trong
  phiên làm robot, cả **1 415 lời gọi** đều là mô hình đó, không một lời gọi nào khác.
- **Tài liệu có thể chứa câu ra lệnh cho Agent.** Đoạn nào trong PDF trông như đang chỉ dẫn
  Agent thì được đánh dấu và đọc như **dữ liệu**, không như lệnh, và hiện cảnh báo đỏ trên tab
  Tài liệu.

---

## 4 · Từng nhóm việc, chi tiết

### 4.1 · Làm rõ đề bài trước khi làm

Agent hỏi **một cụm câu** thay vì hỏi lắt nhắt từng câu, mỗi câu kèm *vì sao hỏi* và *nếu bỏ
qua thì sẽ dùng giả định nào*. Tối đa hai lần hỏi mỗi lượt.

Và **hỏi không có nghĩa là dừng**: Agent làm hết phần không phụ thuộc câu trả lời trước, rồi
mới hỏi phần còn lại. Hết hai lần hỏi thì nó đi tiếp với giả định, và **nói rõ giả định đó**.
Nó dám đi tiếp vì mọi thay đổi đều gỡ lại được.

### 4.2 · Đọc tài liệu

Nhận dạng loại tệp theo **mấy byte đầu tệp**, không theo đuôi tệp — tệp `.pdf` mà bên trong là
ảnh thì nó biết.

Cách trích dẫn đổi theo loại tài liệu, vì không phải loại nào cũng có số trang:

| Loại | Trích theo |
|---|---|
| PDF | số trang |
| Word | đường tiêu đề (Word không có số trang cố định) |
| Excel | `Tên sheet!ô` |
| Slide | số slide |
| Mã nguồn | số dòng |

Con số thì lấy **bằng mã** từ trang PDF, không để mô hình đọc hộ. Ký hiệu kỹ thuật được đổi về
dạng chuẩn ngay lúc đọc: `4R7` thành 4,7 Ω · `3V3` thành 3,3 V · dải `2.7–3.6 V` giữ cả hai
đầu · **`TBD` thành "chưa có", không thành 0**. Một giá trị chưa có mà hoá thành 0 thì mọi
phép tính sau đó đều sai mà không ai biết.

### 4.3 · Viết tài liệu ra Word · PowerPoint · Excel · PDF

Agent viết nguồn Markdown, rồi dựng ra tệp gửi đi được.

| Định dạng | Dùng khi | Agent từ chối khi |
|---|---|---|
| **Word** `.docx` | tài liệu để đọc và sửa tiếp | — |
| **PowerPoint** `.pptx` | trình bày — mỗi tiêu đề một slide | — |
| **Excel** `.xlsx` | số liệu để lọc, sắp, tính | nguồn **không có bảng nào** |
| **PDF** | bản gửi đi, bản in | máy chưa có LibreOffice |

Vì sao nguồn là Markdown chứ không ghi thẳng tệp nhị phân: **một thay đổi không xem được là
một thay đổi không duyệt được**. Nguồn nằm trong kho nên so được bằng mắt và gỡ lại được.

Hai lời từ chối trên là **cố ý**. Một tệp Excel chứa cả đoạn văn trong ô A1 thì mở lên được mà
dùng không được — và một thứ dùng không được mà trông như đã xong thì tai hơn một lỗi báo
thẳng.

Công thức toán viết kiểu LaTeX (`$…$`, `$$…$$`, khối ```math) được đổi sang ký hiệu đọc được ở
**mọi chỗ**: trong đoạn văn, trong gạch đầu dòng, trong ô bảng, trong trích dẫn, trên slide,
trong ô Excel. Bảng đổi có **90 ký hiệu**, có bộ kiểm phủ hết. Dấu đô-la dùng để chỉ **tiền**
thì giữ nguyên. Lệnh nào chưa đổi được thì **kê ra**, không im lặng in cú pháp thô.

### 4.4 · Sơ đồ thành hình, ở cả hai nơi

Khối ```mermaid được **vẽ ra hình** — trên màn hình chat (kèm nút *Xem mã*) và thành ảnh trong
cả bốn định dạng tệp. Bộ vẽ **tự viết**, không nhúng thư viện ngoài, vì EIDE không mở cổng mạng
nào. Kiểu sơ đồ nào chưa vẽ được thì hiện mã **kèm câu nói rõ là chưa vẽ được**.

### 4.5 · Viết mã: đọc trước, đánh mốc trước, chọn cấu trúc trước

Ba luật chặn, mỗi luật có mã lỗi riêng:

- **Không ghi đè tệp chưa đọc hết** (`E4020`). Muốn sửa một tệp thì phải đọc nó trước.
- **Tự đánh một mốc lùi** ở lần sửa đầu mỗi lượt, không cần ai nhắc.
- **Kế hoạch viết mã mới phải chọn cấu trúc trước** (`E6009`), và kế hoạch sửa mã cũ phải có
  bước đọc hiểu mã cũ.

Bước đọc hiểu mã tách rõ hai thứ: **dữ kiện** (mã quét ra: hàm này đang có ai gọi) và **nhận
định** (Agent con đọc rồi đánh giá). Trộn hai thứ này vào một chỗ thì người đọc không biết đâu
là đo, đâu là đoán.

### 4.6 · Chạy thử trên máy: nêu mức đo trước

Thứ tự bắt buộc: **nêu mức đo → chạy → đối chiếu**. Và thứ chấm kết quả là **bộ mức đo**,
không phải chương trình mô phỏng — chương trình chỉ in số ra. Nếu để chương trình tự in
"đạt" thì nó có thể in "đạt" bất kể số đo là bao nhiêu, và chuyện này **đã xảy ra thật** trong
phiên làm robot.

Muốn đổi mức đo sau khi đã thấy kết quả thì phải qua cửa `G-QUAL`. Đổi thước sau khi đã đo là
việc người phải duyệt.

### 4.7 · Làm việc với bo thật

| Công cụ | Làm gì |
|---|---|
| `target.detect` | dò bo đang cắm, đọc mã chip từ silicon rồi so với chip đã ghim trong dự án |
| `target.flash` | nạp — qua ST-Link cho ARM, qua avrdude cho AVR |
| `target.verify` | **đọc ngược từ chip** rồi so từng byte với tệp đã nạp |
| `target.log` | đọc cổng nối tiếp |
| `target.debug` | giải mã thanh ghi lỗi, dấu vết ngăn xếp, nguyên nhân khởi động lại |
| `target.screen` | đọc khung ảnh từ chip ra tệp PNG |

Một luật thêm vào sau khi bị trúng lỗi thật: **sau mỗi lần nạp phải đọc cổng nối tiếp để xem
chương trình nào đang chạy.** Lý do là `avrdude` so với **đúng cái tệp nó được đưa**, nên đưa
sai tệp thì nó vẫn báo "verified, 0 byte lệch". Trong phiên robot, Agent đã báo nạp xong một
bản trong khi trên chip là bản khác, và cả ba dấu hiệu (`ok`, `verified`, `0 byte lệch`) đều
xanh.

### 4.8 · Việc lớn: chia chặng, mỗi chặng để lại thứ mở ra xem được

Mỗi bước xong phải có **thứ mở ra xem được** — một tệp, một mục trong kho, một lần sửa. Một
câu kể lại thì không nhận. Xong cả kế hoạch thì ráp các phần theo đúng thứ tự bước, sinh mục
lục, hạ cấp tiêu đề, và **kê rõ phần nào không ráp được ngay trong tài liệu**.

### 4.9 · Nhớ lâu, và nhớ có kiểm lại

Ngữ cảnh chia 10 khối, mỗi khối có trần riêng, và có đồng hồ cho người xem khối nào đang gần
trần. Khi phải thu gọn, EIDE hỏi lại 3 câu kiểm xem bản thu gọn có mất gì không — thu gọn mà
mất mất một quyết định thì các bước sau sẽ đi sai mà không ai biết.

Bộ nhớ dài hạn nằm trong tệp `EIDE.md` của dự án. Agent **không** được ghi đè tệp này bằng
công cụ ghi tệp thường; phải đi qua công cụ bộ nhớ, để mỗi lần thêm luật đều có dấu.

---

## 5 · Cách thử: bốn mức

Bốn mức này đo bốn thứ khác nhau, và không mức nào thay được mức khác.

### Mức 1 — Ca đơn vị: **1 575 ca Python + 40 ca giao diện**

```bash
.venv/bin/python -m pytest -q
```

Đo từng hàm, từng luật chặn, từng mã lỗi. Chạy nhanh, không tốn tiền mô hình. Mức này **không**
nói được sản phẩm có dùng được không — nó chỉ nói mã làm đúng cái nó định làm.

Phần giao diện mới có bộ kiểm từ 02/10/2026:

```bash
cd ui/EIDEApp && swift test        # 40 ca
```

Trước đó **cả giao diện chưa từng có một ca kiểm nào** — `Package.swift` chỉ khai một mục tiêu
chạy được, không có mục tiêu kiểm. Đó là lý do thật khiến năm việc anh Công nêu về màn hình đều
kết thúc bằng câu *"không con số nào bắt được, phải nhìn màn hình"*. Câu ấy đúng với bề rộng cột
và màu sắc, nhưng **sai với phần tách khối, tách ô, đổi ký hiệu** — những phần ấy là hàm thuần,
vào chuỗi ra chuỗi.

Và một phép đo về chính bộ kiểm: **13 trong 40 ca đỏ khi trả lại mã cũ**. Con số ấy quan trọng
hơn con số 40, vì nó nói bộ kiểm có canh được gì không.

### Mức 2 — Ca đi qua giao thức thật, không tốn tiền mô hình

```bash
.venv/bin/python tools/kiem_tra_day_du.py --nhanh
.venv/bin/python tools/kiem_tai_lieu.py        # mã có nói khác tài liệu thiết kế không
```

Mỗi nhóm tính năng có một bộ riêng, và mỗi bộ đều có **ca đường hỏng cố ý** — không chỉ thử
đường chạy đúng:

```bash
.venv/bin/python tools/thu_g3.py     # 31 ca + 8 đường hỏng cố ý
.venv/bin/python tools/thu_g4.py     # 23 ca + 8 đường hỏng
.venv/bin/python tools/thu_g5.py     # 35 ca + 8 đường hỏng
.venv/bin/python tools/thu_ckm.py    # 35 ca bản đồ mạch + 8 đường hỏng
.venv/bin/python tools/thu_hier.py   # 46 ca cây khối
.venv/bin/python tools/thu_g6.py     # 34 ca dịch mã, mức đo, Agent con
EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/thu_sch.py   # 63 ca sinh sơ đồ + 10 đường hỏng
```

### Mức 3 — Ca đi qua **giao diện thật**

```bash
.venv/bin/python tools/thu_giao_dien.py    # 24 ca qua app thật
```

Cách này **không** gõ phím qua hệ điều hành. Gõ phím kiểu đó gửi phím tới cửa sổ đang được
chọn, nên khi người dùng đang làm việc khác thì phím rơi nhầm cửa sổ — đã xảy ra, và đó là lý
do cách ấy bị bỏ.

Thay vào đó app mở một kênh tệp tại `<dự án>/.eide/ui-test/`, chỉ bật khi thư mục đó có, và
khi bật thì hiện dải báo rõ cho người biết. Mọi thứ đọc từ kênh vẫn đi qua đúng một cửa vào
lõi như ngón tay người — kênh thay ngón tay, không thay giao thức.

Được thêm một thứ quan trọng: kênh **đọc ngược** trạng thái giao diện, nên kiểm được những
thứ chỉ nhìn mới thấy — chữ có bị cắt không, khối có đè nhau không, câu trả lời của Agent có
được dựng thành chữ hay còn dấu Markdown thô.

### Mức 4 — Một việc thật, từ đầu tới cuối, trên bo thật

```bash
.venv/bin/python tools/phien_robot_phan_mem.py   # robot hai bánh tự đứng
```

Mức này là mức duy nhất trả lời được câu *Agent có gánh nổi một việc phức tạp thật hay không*.
Ba mức trên không trả lời được câu đó.

### Một phép đo nữa: bộ kiểm có đo gì không

Công cụ `test.sensitivity` **sửa hỏng mã sản phẩm có chủ đích** rồi xem bộ kiểm có chuyển sang
đỏ không, sau đó trả mã về nguyên trạng. Một bộ kiểm vẫn xanh khi sản phẩm đã hỏng thì nó không
đo sản phẩm.

Phép đo này cần, vì trong phiên robot **ba lần liên tiếp** Agent viết bộ kiểm cho đúng chỗ nó
vừa sửa, và cả ba lần bộ kiểm chỉ chép lại logic sang tệp kiểm rồi so logic với chính nó —
xanh bất kể mã sản phẩm đúng hay sai. Lần cuối, sau khi bị bắt viết lại cho bộ kiểm **dùng
thẳng mã sản phẩm**, sáu phép phá đều chuyển đỏ đúng lúc phải đỏ.

---

## 6 · Kết quả thử đến nay

| Phép đo | Kết quả | Xem ở |
|---|---|---|
| 76 ca kiểm theo 19 nhóm việc, chạy qua app thật | **68/68 ca đo được đạt** · 8 ca còn lại mang nhãn riêng | [`BAO-CAO-TONG.md`](docs/review-v3/test/BAO-CAO-TONG.md) · [bảng Excel](docs/review-v3/test/Usecase_Test_KET_QUA_29-09-2026.xlsx) |
| Quét 11 tab giao diện | **124/124 ô** | [`ket-qua-giao-dien/`](docs/review-v3/test/ket-qua-giao-dien/) |
| Ca đơn vị Python | **1 575** | `pytest -q` |
| Ca đơn vị giao diện | **40** · 13 ca đỏ khi trả lại mã cũ | `cd ui/EIDEApp && swift test` |
| Agent tự viết công cụ cho chính nó | **8/8** | [`thu_tu_viet_cong_cu.py`](tools/thu_tu_viet_cong_cu.py) |
| Viết tài liệu Word · PowerPoint · Excel · PDF | **13/13** | [`thu_xuat_tai_lieu.py`](tools/thu_xuat_tai_lieu.py) |
| Vẽ sơ đồ (trên màn hình và trong tệp) | **18/18** | [`thu_so_do.py`](tools/thu_so_do.py) |
| Cách làm mã: đọc trước, đánh mốc, chọn cấu trúc | **8/8** | [`thu_quy_trinh_code.py`](tools/thu_quy_trinh_code.py) |
| Chia việc lớn rồi ráp lại | **12/14** | [`thu_chia_viec_lon.py`](tools/thu_chia_viec_lon.py) |
| Mã có nói khác tài liệu thiết kế không | **0 chỗ lệch** trên 15 tệp | `tools/kiem_tai_lieu.py` |
| Luồng công cụ FPGA bốn chặng | **chạy thông tới silicon** — Verilog → bitstream → nạp → **96/96 ô đo trên bo** | [`docs/fpga/phien-sinhvien-04-10/bai2/ket-qua/`](docs/fpga/phien-sinhvien-04-10/bai2/ket-qua/) |
| Công cụ đã được dùng thật | **115/127** | rà toàn bộ sổ ghi việc |

Mỗi ca kiểm có một tệp log riêng, trong đó có **bảng từng lời gọi công cụ kèm tham số đầy đủ
và mã lỗi**: [`ket-qua-chay-lai/nhat-ky/`](docs/review-v3/test/ket-qua-chay-lai/nhat-ky/).

Chín lỗi tìm được trong đợt đo ghi ở [`LOI-TIM-DUOC.md`](docs/review-v3/test/LOI-TIM-DUOC.md),
và **tách rõ lỗi của sản phẩm với lỗi của chính bộ đo**. Hai loại ấy dẫn tới hai việc khác
nhau, nên gộp vào một cột là nói sai về sản phẩm.

### Một việc không thêm tính năng nào nhưng đáng kể

Rà toàn bộ sổ ghi việc phát hiện **31 trong 122 công cụ chưa bao giờ được dùng lần nào**. Bảy
công cụ có đường dẫn tới chúng bị đứt — đã nối lại. Phần còn lại được giao đúng loại việc để
kiểm. Nay **110/122 đã được dùng thật**.

Một công cụ không bao giờ được dùng thì bằng không có nó.

---

## 7 · Ba việc thật

### 7.1 · Viết một hệ điều hành thời gian thực, thay hẳn FreeRTOS

Đề bài: bỏ FreeRTOS, viết lấy nhân thời gian thực cho bo STM32F469I-DISCO, chạy tới khi màn
hình LCD và cảm ứng lên đúng như bản cũ. Cùng một bo, cùng tệp driver của hãng, và cùng cái
màn hình phải sáng.

Ngày 04/10/2026 việc này được **làm lại từ dự án trống**, với đầu vào viết lại cho tường minh
([`docs/rtos-tu-viet/DAU-VAO-AGENT-RTOS-v2.md`](docs/rtos-tu-viet/DAU-VAO-AGENT-RTOS-v2.md)).
Số dưới đây là của lần làm lại ấy, đo trên kit thật.

| | |
|---|---|
| Nhân và ứng dụng Agent **tự viết** | **1 211 dòng** — lập lịch, chuyển ngữ cảnh `PendSV` bằng hợp ngữ, hàng đợi tĩnh, 6 tác vụ, giao diện 3 trang |
| Mã **lấy của hãng**, không sửa | 110 676 dòng — HAL, CMSIS, BSP, driver OTM8009A/NT35510/FT6206, bộ phông, ảnh logo |
| Ký hiệu FreeRTOS còn trong ảnh | **0** |
| Nhịp hệ thống **đo thật** | **~1 003 Hz** (đọc `uwTick` cách nhau 10 giây) |
| Xung nhịp | `SWS = PLL`, HSE + PLL đã khoá, 180 MHz |
| Mức nước ngăn xếp **đo trên chip** | LED 19/128 · Button 25/128 · Monitor 29/128 · **Display 64/512** word |
| Lỗi phần cứng | `CFSR = 0`, `HFSR = 0` |
| Giao diện | 3 trang, **6 lần đổi trang / 7 lần chạm** — đọc từ ô nhớ trên chip |

Về kích thước ảnh thì **điều kiện mình tự đặt lại không đạt theo cách đọc chặt**, và nói ra
thì đúng hơn là làm tròn cho đẹp:

| | byte |
|---|---|
| bản FreeRTOS cũ (`mach.bin` đo được) | 260 204 |
| bản tự viết | **265 152** — lớn hơn **1,9 %** |
| trong đó ảnh logo, có ở cả hai bản | 230 400 |
| phần mã không kể logo | cũ 29 804 · mới 34 752 |

Tài liệu đầu vào mình viết *"không lớn hơn bản cũ (khoảng 263 KB)"*. Đọc theo con số làm tròn
263 KB thì đạt; đọc theo bản nhị phân đo được thì không. Chỗ mơ hồ là lỗi câu chữ của mình, và
nó là ví dụ nhỏ cho một điều lớn hơn ở mục dưới: **tiêu chí viết lỏng thì không đo được gì.**

#### Bảy lỗi cùng một họ: cơ chế có sẵn, đường dẫn tới nó đứt

Đây là phát hiện chính của cả hai việc làm lại, lớn hơn bất cứ con số hiệu năng nào. Trong hai
ngày, **bảy lần** gặp đúng một hình dạng — một thứ **viết đúng** mà **không ai gọi tới** — và
**không lần nào có lỗi báo ra**:

| lần | cơ chế viết đúng | đường dẫn tới nó |
|---|---|---|
| 1 | nhánh nạp FPGA trong thực đơn công cụ | chưa chạy lần nào, nổ `NameError` |
| 2 | `PULL_MODE=UP` trong tệp ràng buộc chân | chân vẫn thả nổi |
| 3 | bảng tổng kiểm chuẩn sinh ra | `main.c` không `#include` |
| 4 | `bat_log_giay` bắt bản ghi quanh lúc nạp | chưa lượt nào dùng |
| 5 | `rtos_tick()` | ô vector SysTick trỏ `Default_Handler` |
| 6 | `PendSV_Handler` nối đúng ô vector, ưu tiên đúng | không ai đặt `PENDSVSET` |
| 7 | `RTOS_IDLE_PRIORITY` | không ai tạo tác vụ rỗi |

Ba lỗi 5–6–7 nối thành một chuỗi mà **mỗi khâu chỉ lộ ra sau khi vá khâu trước**, và cả ba cho
cùng một triệu chứng — bo tối thui:

1. không nhịp → không tác vụ nào thức;
2. có nhịp nhưng không ai xin chuyển ngữ cảnh → không tác vụ nào chạy;
3. có chuyển ngữ cảnh nhưng không có tác vụ rỗi → `ready_map` về 0 → `PendSV` đọc địa chỉ `0`
   → `IBUSERR` → HardFault.

Và một lỗi thứ tám cùng họ nhưng ngược chiều: `current_ui_page` mang giá trị `0` trong khi mọi
nhánh xử lý chạm so với `1`, `2`, `3` — **đường dẫn có, mà giá trị đi trên nó không ai nhận**.
Màn hình vẫn đẹp, không cảnh báo dịch, không fault, và nút bấm chết hoàn toàn.

> Trước khi hỏi *"mã này có đúng không"*, hỏi *"có đường nào thật sự gọi tới nó không"*.

#### Hai điểm mù Agent tự khai trước, rồi nổ đúng chỗ ấy

Ở bước 7, sau khi bộ kiểm của nó xanh 4/4, Agent **tự phá mã mình bốn lần** rồi báo **2 trong 4
ca bộ kiểm không bắt được** — kèm dự đoán hậu quả:

> *Lần 1 — thứ tự `xPSR` và `PC` trên ngăn xếp: VẪN XANH. Lỗi này nạp lên bo thật sẽ nổ
> HardFault ngay chu kỳ đầu tiên.*
> *Lần 2 — `EXC_RETURN`: VẪN XANH. Bộ kiểm host không có khối NVIC để thẩm tra mã thoát ngắt.*

Người kiểm lại claim ấy bằng tay: đổi `0xFFFFFFFD` thành `0x00000000` rồi dịch lại — **cả 4 ca
vẫn xanh**. Claim đúng. Và khi chuyển ngữ cảnh bắt đầu chạy thật, bo nổ đúng `IBUSERR` ở đúng
chỗ ấy.

> Một điểm mù **được khai báo trước** thì khi nó nổ, ta biết ngay chỗ để tìm. Nếu Agent im ở
> bước 7, chỗ đó là một con bo tối thui với hàng chục nguyên nhân khả dĩ.

#### Ba lỗi của người, giữ trong nhật ký làm sở cứ

Chúng đo được điều mà lỗi của Agent không đo: **chất lượng của đề bài**.

- **Tiêu chí số 3 tự khuyến khích làm sai.** Mình viết *"mọi tệp mã nguồn đều vào được ảnh"* —
  mà một tệp rỗng thì không vào được ảnh, nên cách dễ nhất để đạt là **viết thêm mã cho tệp
  rỗng**. Agent làm đúng theo cái tiêu chí sai ấy: 36 dòng không ai gọi, và **ghi cả động cơ
  vào chú thích** (*"để đảm bảo mọi tệp đều được biên dịch vào ảnh — Điều kiện số 3"*). Nhờ nó
  ghi ra, 36 dòng ấy không lọt vào con số *Agent tự viết*.
- **Thiếu tiêu chí về xung nhịp.** Mình đưa hằng số PLL vào tài liệu rồi **tưởng thế là xong**.
  Bản nạp đầu chạy HSI 16 MHz, mọi mốc thời gian chậm đúng 11,25 lần — không fault, không treo,
  thanh ghi nào cũng hợp lý. **Một hệ chậm 11 lần nhìn giống một hệ không chạy.** Bài học viết
  vào tài liệu: *giá trị cấu hình không phải phép đo* — SysTick nạp 179 999 là đúng, nhưng nó
  chỉ nói *nhịp sẽ là 1 000 Hz NẾU xung nhịp là 180 MHz*.
- **Xoá mất ba tệp driver của Agent** vì nhìn **hình dạng cái tên** (tệp kèm mã băm) mà không
  mở ra đọc — chúng là bản V1 thật, ba tệp cùng gốc tên chỉ là dòng trỏ. Lần thứ hai trong
  ngày mắc đúng lỗi *hành động theo thứ mình tưởng thay vì thứ đo được*.

#### Chỗ đáng kể nhất về cách làm: đo được trước, sửa sau

Khi hai nút bấm không ăn, có ba nguyên nhân khả dĩ cần ba bản vá khác nhau — cảm ứng chết, toạ
độ lệch hệ trục, hay tầng trên không đổi trang. Thay vì đoán, yêu cầu Agent **thêm bốn ô nhớ
đọc được qua cổng gỡ lỗi**. Một lượt đọc là xong:

| ô nhớ | giá trị | loại trừ được |
|---|---|---|
| `debug_ts_init_status` | 0 | không phải cảm ứng chết |
| `debug_ts_touch_count` | 11 | **không phải I2C sai tần số** |
| `debug_ui_page_change_count` | 0 | chỗ đứt ở tầng trên |

Chuyện I2C ở 180 MHz — thứ **đã từng sập ở phiên cũ của chính việc này** — bị loại bằng **một
con số**, không bằng suy luận. Không có bốn ô nhớ ấy thì việc sửa sẽ bắt đầu ở đúng chỗ không
hỏng.

#### Phiên này để lại gì

| | |
|---|---|
| bước có thật qua giao diện | **25**, mỗi bước một ảnh cửa sổ EIDE |
| lời gọi mô hình | 837 |
| changeset | 103 |
| sở cứ đầy đủ | [`docs/rtos-tu-viet/phien-sinhvien-04-10/`](docs/rtos-tu-viet/phien-sinhvien-04-10/) |

Phiên cũ của việc này giữ lại trong [`docs/rtos-tu-viet/`](docs/rtos-tu-viet/) để so hai lần
làm — gồm mã nguồn bản cũ, 3 915 dòng sổ ghi việc và
[báo cáo 12 trang](docs/rtos-tu-viet/bao-cao/BAO-CAO-RTOS.docx) do chính EIDE dựng.

**Đánh giá so với người làm cho cả hai việc làm lại** — chỗ Agent mạnh, chỗ Agent yếu, và ba
tiêu chí người viết lỏng đã sinh ra hậu quả gì:
[`docs/md/DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md`](docs/md/DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md).

### 7.2 · Robot hai bánh tự đứng — và báo cáo nói cả phần Agent sai

Đề bài: đọc tập tài liệu phần cứng rồi viết phần mềm giúp robot đứng được. Khó ở chỗ hồ sơ
**đã bỏ hẳn phần thuật toán** — không còn vòng điều khiển, không còn bộ lọc, không còn PID.
Chỉ còn điều kiện bắt buộc về phần cứng. Không có lời giải để chép.

| | |
|---|---|
| Phần mềm | **1 820 dòng C**, 10 mô-đun, cho ATmega328P |
| Tệp ảnh | 13 056 B Flash / 32 KB · 634 B RAM / 2 KB |
| Hàm ngắt 50 kHz | **35 lệnh · 0 lời gọi hàm · 0 số thực · 0 phép chia** — đúng thứ tài liệu cấm |
| Bảng điều kiện bắt buộc | **109 mục** dựng từ tài liệu, đối chiếu lại sau mỗi lần sửa |
| Sổ ghi việc | **16 666 dòng**, kiểm được là chưa ai sửa dòng nào |
| Lời gọi mô hình | **1 415**, tất cả cùng một mô hình |
| **Kết quả** | **robot đứng được** |

**Báo cáo của việc này nói thẳng tám chỗ Agent báo xong trong khi đang sai**, vì đó là phần có
ích nhất:

- tắt động cơ bằng một chân mạch đã nối cứng xuống đất — chính Agent đọc ra điều đó ở lượt
  trước
- chạy thử trên máy báo **6/6 đạt** trong khi đã đảo dấu khâu P, tức robot chắc chắn không
  đứng được
- câu `"dat": true` **viết cứng** trong lệnh in, nên chương trình in "đạt" bất kể số đo
- bỏ một yêu cầu trong bản ghi yêu cầu mà không báo ai
- báo nạp xong một bản trong khi trên chip là bản khác
- ba bộ kiểm liên tiếp chỉ chép logic sang tệp kiểm

**Không chỗ nào trong tám chỗ đó do Agent tự tìm ra.** Tất cả đều do một phép đo người thiết
kế, hoặc do người đọc mã rồi hỏi lại.

Và chỗ quyết định: robot chỉ đứng được **sau khi có một bản chạy được để so sánh**. Năm vòng
cắm bo trước đó thu hẹp được một phần, nhưng chỗ bị nghi là hệ số PID.
Khi nạp bản của nhà cung cấp — phần mềm người viết, đã đứng được trên chính bo này — robot
đứng ngay. Một lần nạp đó chia đôi chỗ cần tìm lỗi: phần cứng, jack động cơ, cảm biến, nguồn
đều tốt, nên lỗi còn lại nằm trong phần mềm.

Đối chiếu từng con số tìm ra **bảy** chỗ lệch, trong đó chỗ nặng nhất là hằng số chỉnh chuẩn
gia tốc: **535 thay vì 92**, tức **3,1 độ** điểm cân bằng sai. Robot đuổi một thế đứng mà nó
không giữ được, nên nó vọt qua rồi ngã. Còn hệ số PID thì bản chạy được dùng **đúng** con số
EIDE vẫn để — nó chưa bao giờ là nguyên nhân.

#### Mất bao lâu, tốn bao nhiêu

| | Nếu một đội người làm tay (ước lượng) | Phiên Agent (đo được) |
|---|---|---|
| Thời gian | **31,0 ngày công ±2,6** · khoảng **4 tuần** lịch | **7,4 giờ**, một buổi |
| Nhân lực | 1 Senior + 1 Mid + QA + quản lý | **1 người** + Agent |
| Tiền | **≈ 105 triệu đồng** (mức giữa) | **≈ 340 nghìn đồng** tiền mô hình |
| Phần mềm có đứng được không | có | **có** |

Chênh khoảng **300 lần về tiền** và **30 lần về giờ công** (31 ngày công của một đội so với 7,4
giờ của một người).

Con số 31 ngày công tính đủ bốn khâu, chia theo 13 việc nhỏ, mỗi việc ước ba mức rồi lấy theo
PERT. Hai việc có mức chậm nhất gấp bốn đến sáu lần mức nhanh nhất, và đó là hai chỗ rủi ro
thật:

| Việc | Vai | Nhanh | Thường | Chậm | Ngày công |
|---|---|---|---|---|---|
| Hàm ngắt 50 kHz: 0 số thực, 0 phép chia | Senior | 1 | 3 | **8** | 3,50 |
| **Gỡ lỗi trên bo: ba dấu cộng trừ và ba con số theo từng bo** | Senior | 2 | 5 | **12** | 5,67 |

Dòng thứ hai trong phiên thật **đã rơi về phía mức chậm**: mười lần cắm bo, và vẫn chưa xong
tới khi có bản chạy được để so.

Kiểm chéo bằng COCOMO trên 1,820 KSLOC cho **95 – 155 ngày công**, tức gấp 3 đến 5 lần. Chênh
lệch đó có lý do — COCOMO tính trọn vòng đời công nghiệp và được biết là ước lượng thừa cho dự
án dưới 2 KSLOC — nên lấy PERT làm số chính và đọc COCOMO như mức trần.

**Bốn điều bảng trên không chứng minh**, nói trước để không bị đọc quá tay:

1. **Người vẫn nằm trên đường quyết định.** Cả mười lần cắm bo đều cần người dựng robot lên rồi
   nói nó ngã về phía nào. Agent không chạm được vào robot, nên 7,4 giờ ấy phần lớn là chờ
   người thử.
2. **Bước cuối dùng một bản đã chạy được để so.** Không có nó thì phiên này còn kéo dài.
3. **340 nghìn đồng không phải toàn bộ chi phí** — chưa tính giờ của người, phần cứng, và thời
   gian dựng EIDE.
4. **Tám chỗ Agent báo xong trong khi đang sai đều cần một phép đo do người thiết kế.** Thời
   gian rà soát đó nằm **trong** 7,4 giờ, nhưng nó cần một người biết phải đo cái gì. Giao cho
   người không biết nghi chỗ nào thì tám chỗ ấy lọt hết, và robot sẽ không đứng.

Xem cách tính đầy đủ — token, đơn giá ba mức, bảng 13 việc, COCOMO:
[**báo cáo so sánh với người làm tay**](docs/robot-tu-can-bang/BAO-CAO-SO-SANH.md) ·
[`docs/robot-tu-can-bang/`](docs/robot-tu-can-bang/).

### 7.3 · Lõi RISC-V trên FPGA — đã chạy trên bo thật, 96 trên 96 ô

Việc này nằm đây vì đó là chỗ đo được nhiều nhất: nó cố ý nằm **ngoài hẳn** vùng EIDE từng làm.
Trước việc này EIDE không có một dòng nào về HDL — không tổng hợp Verilog được, không mô phỏng
Verilog được, không đóng gói bitstream được, không nạp FPGA được, và không biên dịch cho RISC-V
được.

Đề bài: dựng một CPU RISC-V trên kit Sipeed Tang Nano 20K, chạy chương trình C trên CPU đó, rồi
đo chi phí nhân ma trận ở ba cấu hình phần cứng khác nhau.

Ngày 03–04/10/2026 việc này được **làm lại từ bước 1 trong một dự án trống**, với đầu vào viết
lại cho tường minh ([`docs/fpga/DAU-VAO-AGENT-FPGA-v2.md`](docs/fpga/DAU-VAO-AGENT-FPGA-v2.md)),
và lần này **chạy trên bo thật**. Số dưới đây là số đo từ silicon, không phải số mô phỏng.

#### Bài 1 — CPU sống trên chip

| điều kiện nghiệm thu | số đo trên bo |
|---|---|
| CPU chạy, in được qua cổng nối tiếp | `Hello from PicoRV32 on Tang Nano 20K, cycle=1485001241` |
| xung nhịp đúng 27 MHz | Δcycle giữa các dòng: **27 000 001 · 27 000 031 · 27 000 024** |
| đèn nháy theo CPU | LED0 nháy, người quan sát xác nhận |
| chạy liên tục sau khi rút điện cắm lại | `cycle` đọc được 1 404 001 194 > 837 000 733 lần trước |

Nguyên nhân gốc mất gần một ngày để tìm: **chân 88 đọc mức 0 khi không ai bấm**, nên tín hiệu
reset bị giữ mãi và CPU không bao giờ chạy. Agent tự khoanh được bằng bộ phát chẩn đoán do nó
viết — in `S:0` (chân 88 mức 0) và `C:40` (bộ đếm khởi động chạy đủ) — rồi ghi `ADR-01`: bỏ nút
khỏi mạch reset, nêu rõ cả mặt dở *không reset tay được*, và tự khai tầng VÀNG chứ không khai
NGƯỜI.

#### Bài 2 — 96 ô đo, trên bo và trong mô phỏng

4 kích thước ma trận × 2 kiểu dữ liệu × 4 cách cài đặt × 3 cấu hình CPU = **96 ô**.

Bốn phép kiểm dưới đây **do người tự làm**, đọc bản ghi gốc và mã máy, không nhận qua lời Agent:

| phép kiểm | kết quả |
|---|---|
| ô bắt được từ cổng nối tiếp của bo | **96 / 96** |
| ô có `ok=1` | **96 / 96** |
| ô có tổng kiểm lệch bảng tính tay ở tầng NGƯỜI | **0** |
| ô lệch số chu kỳ giữa bo thật và mô phỏng Verilator | **0** |

Bảng tính tay ấy là bốn con số người tự tính độc lập với mã của Agent, chốt vào tài liệu đầu vào
ở tầng NGƯỜI trước khi đo: `0xfeaabd40` · `0x2110c56a` · `0xc7ce1f03` · `0x36395f4b`. Agent lệch
với chúng thì Agent sai, không phải bảng sai.

Lệch 0 % giữa bo và mô phỏng không phải trùng hợp, và Agent giải thích được vì sao: lõi này tuần
tự, không đường ống sâu, không dự đoán rẽ nhánh, bộ nhớ chỉ có BRAM nội trễ cố định, và Verilator
mô phỏng chính mã RTL ấy từng sườn xung nhịp.

**Đưa phép nhân xuống phần cứng được gì** — số đo trên bo:

| | ít nhất | nhiều nhất |
|---|---|---|
| bộ nhân tuần tự so với nhân bằng phần mềm | 1,57× | 6,8× |
| bộ nhân nhanh dùng DSP so với nhân bằng phần mềm | 2,45× | **12,5×** |

Chu kỳ mỗi phép nhân-cộng ở ma trận 32×32, cách viết cơ bản: **502 → 74 → 40**.

Và chỗ đáng kể hơn con số lớn nhất là **chỗ con số nhỏ nhất**. Cả hai ô tăng ít nhất đều là
*số 8 bit, cách viết hoán vị vòng lặp* — chỗ mà cấu hình không có bộ nhân **đã nhanh sẵn** (131
thay vì 502). Agent giải thích bằng định luật Amdahl: khi tỷ trọng thời gian dành cho phép nhân
đã nhỏ, thêm bộ nhân phần cứng nhanh đến đâu cũng chỉ cải thiện được chút ít. Đó là câu trả lời
cho *lúc nào thêm phần cứng không giúp gì*, và nó chỉ hiện ra khi đo đủ 96 ô.

Biến độc lập của cả thí nghiệm kiểm được **trong mã máy**, không phải trong lời ai nói: cấu hình
không có bộ nhân còn **24** lời gọi `__mulsi3` / `__udivdi3`, hai cấu hình kia còn **0**.

**Agent tự viết 2 020 dòng** — Verilog, C, hợp ngữ, linker script, Python, ràng buộc chân.

#### Sáu lỗi của Agent, và ba lỗi của người

Lỗi nào của Agent cũng bị bắt bằng cách **mở mã hoặc mở sổ cái ra đối chiếu**, không bằng đọc
báo cáo của nó:

| lỗi | phép đo bắt được |
|---|---|
| cờ `ok` của cách viết cơ bản tự so với chính nó → 24 trong 96 ô **không thể báo sai** | đọc ba dòng mã quanh `baseline_chk` |
| tổng kiểm chuẩn được sinh ra nhưng `main.c` không `#include` → mốc chuẩn không tới chip | `grep` cả thư mục, không có chỗ dùng nào |
| cách viết V3 đổi từ chia khối sang chuyển vị mà không báo, và vòng chuyển vị nằm **trong** khoảng bấm giờ | so kế hoạch đã duyệt với mã thật |
| chú thích nói vùng đệm 12 KB, mã khai bốn mảng = 16 KB | đếm khai báo |
| Makefile thiếu `-lgcc` nên `make` đổ ở link cả ba cấu hình | tự chạy `make` |
| mô phỏng nạp một tệp `-Os`, bitstream nạp một tệp `-O2` — **hai chương trình khác nhau** | lần theo tham số `HEX_FILE` |

Chỗ cuối là chỗ nguy hiểm nhất: tiêu chí nghiệm thu là *bo lệch mô phỏng ≤ 1 %*, mà hai bên đang
chạy hai bản mã chênh gần 3 KB. Lệch thì sẽ đi tìm nguyên nhân ở phần cứng; khớp thì còn tệ hơn.

Và ba lỗi của người, ghi vào nhật ký làm sở cứ vì chúng đo được điều mà lỗi của Agent không đo:

- **Tiêu chí nghiệm thu tự nó vô hiệu.** Tài liệu đầu vào do người viết đòi *mọi ô `ok=1`* — mà
  một bo tính sai toàn bộ vẫn đạt được, vì cờ ấy chỉ so bốn cách viết với nhau. Đã vá bằng mục
  5.3b: chốt luật sinh dữ liệu và bốn tổng kiểm ở tầng NGƯỜI.
- **Đặt tên tệp theo cấu hình mình *tưởng* đang đo**, không theo nhãn đo được — đè mất 22 ô dữ
  liệu của Agent. Nay tên tệp lấy từ nhãn `hw=` trong chính bản ghi.
- **Vòng đọc cổng thoát khi đếm được 32 chuỗi `RESULT`**, nên nó cắt giữa dòng thứ 32. Đếm một
  chuỗi xuất hiện không giống đọc xong một dòng. Nay đòi có cả dấu kết thúc.

Hai lỗi Agent **tự tìm và tự báo đúng loại**, không phải người chỉ ra: lệnh chia bẫy CPU ở hai
cấu hình có bộ nhân vì phần cứng để `ENABLE_DIV=0` (`ADR-03`: chia bằng dịch bit), và hàm
`memset` tự viết bị trình biên dịch đổi thành lời gọi chính nó gây tràn ngăn xếp (`ADR-02`: thêm
`-fno-tree-loop-distribute-patterns`). Cả hai đều có lý do và chỗ trích.

Một chỗ nữa đáng ghi vì nó nói về **loại sai sót còn lại sau khi mọi thứ đã đạt**: tài liệu
tổng kết Agent tự xuất ra có ba con số thô mà kiểm lại khớp **đúng từng chữ số**, nhưng một con
số **suy ra** thì hụt — nó ghi bộ nhân DSP nhanh hơn bộ nhân tuần tự *1,54×–1,85×*, tính lại từ
hai bản ghi thì đỉnh là **2,03×** ở ô `N=32, I8, V2`. Số thô thì nó chép đúng; số phải tính qua
96 ô thì nó lấy thiếu. Đã sửa và ghi rõ chỗ sửa trong chính tài liệu ấy
([`docs/fpga/phien-sinhvien-04-10/KET-QUA.md`](docs/fpga/phien-sinhvien-04-10/KET-QUA.md)).

#### Dòng tài liệu để trống, và câu trả lời đo được

Tài liệu đầu vào cố ý để trống một dòng: *"mình chưa rõ cổng nào làm gì — bạn tự xác định rồi
ghi lại"*. Câu trả lời tìm ra bằng cách để nó tự lộ: mở cổng thứ nhất làm cổng nối tiếp rồi gọi
lệnh nạp, lệnh nạp báo *unable to claim usb device*. Hai kênh của cùng một chip FTDI — cổng thứ
nhất là **JTAG**, cổng thứ hai là **UART**. Giữ cổng nạp mở thì không nạp được.

#### Ba thói quen đo rút ra từ việc này

Mỗi thói quen dưới đây đổi bằng một lần đo sai, và cả ba đều cùng một họ: **thứ nhìn thấy không
phải thứ đang chạy.**

> **Mốc đọc phải sau mốc nạp.** Một lượt báo *"bắt 32 dòng từ bo, lệch 0 %"* hoá ra đọc cổng
> **92 giây trước khi bitstream tồn tại** — tức đọc bo đang chạy bài trước, rồi so bản ghi mô
> phỏng với chính nó. Mốc thời gian trong sổ cái nói ra điều đó, lời tường thuật thì không.

> **Một lần đọc rác không phải bằng chứng.** Lần bắt đầu tiên nhận 173 byte mà **có cả dấu kết
> thúc** — đó là đuôi của lượt trước còn trong bộ đệm. Phải xả cổng tới khi im rồi mới cho bo
> chạy lại.

> **Một phép kiểm xanh trên mã nguồn không nói gì về bản nhị phân đang đo.** Giao diện dùng để
> ghi nhật ký là gói dựng từ ba ngày trước; nó cắt lời Agent ở 3 000 ký tự không để lại dấu, nên
> 16 trong 30 câu mất đuôi và người đọc nhật ký — là tôi — kết luận sai rằng Agent không trả lời
> một câu hỏi. Nay có chốt chặn phiên nếu gói cũ hơn mã nguồn (`DEV-333`).

#### Phiên làm việc này để lại gì

| | |
|---|---|
| bước có thật qua giao diện | **54**, mỗi bước một ảnh cửa sổ EIDE |
| lời gọi mô hình | 1 307 |
| changeset | 161 |
| dòng sổ cái | 16 789 |
| bản ghi thô từ bo | [`docs/fpga/phien-sinhvien-04-10/bai2/ket-qua/`](docs/fpga/phien-sinhvien-04-10/bai2/ket-qua/) — ba tệp, mỗi tệp 32 dòng |
| bảng 96 ô | `bang-doi-chieu-96-o.md` — 96 dòng, đã đối chiếu máy với bản ghi gốc, 0 lệch |

Bốn lỗi của EIDE vá trong hai ngày này đều thuộc **một họ: cơ chế có sẵn, đường tới nó đứt** —
nhánh nạp FPGA chưa chạy lần nào nên nổ `NameError` (`DEV-330`), không có cách bắt bản ghi quanh
lúc nạp (`DEV-331`), không đọc được mã nhận dạng chip FPGA (`DEV-332`), và gói giao diện cũ hơn
mã nguồn (`DEV-333`). Chi tiết:
[`docs/fpga/DEV-333-GOI-APP-CU-HON-MA-NGUON.md`](docs/fpga/DEV-333-GOI-APP-CU-HON-MA-NGUON.md).

Toàn bộ sở cứ của phiên này — mã Agent viết, ba bản ghi thô từ bo, bảng 96 ô, nhật ký 54
bước kèm 54 ảnh cửa sổ EIDE, và sổ cái lời gọi công cụ kèm mốc thời gian — nằm trong
[`docs/fpga/phien-sinhvien-04-10/`](docs/fpga/phien-sinhvien-04-10/).

Phiên cũ của việc này — làm trước khi có bo, mọi con số là số mô phỏng — giữ lại trong
[`docs/riscv-tn20k/`](docs/riscv-tn20k/) để so hai lần làm.

### 7.4 · Đặt ba việc đã xong cạnh nhau: thời gian và tiền

| | Hệ điều hành tự viết | Robot hai bánh tự đứng | Lõi RISC-V trên FPGA |
|---|---|---|---|
| Phần mềm giao ra | 689 dòng lõi + 340 dòng ứng dụng | 1 820 dòng, 10 mô-đun | 2 020 dòng Verilog + C + hợp ngữ |
| **Phiên Agent — thời gian** | **81,2 phút** | **7,4 giờ** | **khoảng 14 giờ, hai ngày** |
| **Phiên Agent — lời gọi mô hình** | 351 | 1 415 | **1 307** |
| **Nếu người làm tay — ngày công** | **31,7 ±2,3** | **31,0 ±2,6** | chưa dựng ước lượng |
| **Nếu người làm tay — tiền** | **≈ 111 triệu đồng** | **≈ 105 triệu đồng** | — |
| Chênh về tiền | **khoảng 3 300 lần** | **khoảng 300 lần** | — |
| Chạy thật trên bo | LCD 800×480 + cảm ứng + 6 việc | robot đứng được | **96/96 ô đo trên silicon** |

Cột FPGA chưa có ước lượng ngày công vì nó là việc **đầu tiên nằm ngoài hẳn vùng EIDE từng
làm** — trước nó EIDE không có một dòng nào về HDL — nên phần lớn thời gian hai ngày ấy là
**vá chính EIDE** (bốn lỗi, `DEV-330` đến `DEV-333`), không phải làm bài. Đem con số ấy so với
một người đã có sẵn công cụ thì so sai.

Hai cột đầu không chênh giống nhau, và chỗ khác nhau đó nói lên điều chính:

Bài hệ điều hành chênh **gấp hơn mười lần** so với bài robot. Lý do là bài hệ điều hành gần như
toàn bộ nằm trong phần **đọc tài liệu, tra thanh ghi, viết mã** — đúng phần Agent nhanh. Bài
robot thì phần lớn thời gian nằm ở **gỡ lỗi trên bo thật**, mà phần đó Agent không rút ngắn được
bao nhiêu: nó không chạm được vào robot, mỗi lần đều phải chờ người dựng lên rồi nói nó ngã về
phía nào.

Nói cách khác: **mức lợi của Agent tỉ lệ với phần việc nằm trong máy tính.** Việc nào càng dính
vào vật thật thì khoảng chênh càng hẹp.

### 7.5 · Rút ra được gì từ ba việc này

Chỗ Agent thật sự giúp được nhiều nhất **không phải là tốc độ gõ mã**. Là chỗ này: nó làm những
phép đo mà người sẽ bỏ. Đọc ngược chip đủ 32 lần trong một phiên. Dựng bảng 109 điều kiện rồi
đối chiếu lại sau mỗi lần sửa. Ghi 249 lần sửa đều gỡ lại được. Giữ nguyên văn 1 415 lời gọi
mô hình. Không phải vì nó cẩn thận hơn người, mà vì **nó không mỏi**, và mỏi là lý do người bỏ
bước.

Chỗ Agent không làm được, và hai việc này cho thấy khá rõ:

1. **Nó không tự biết nó sai.** Mọi câu "đã xong, đã kiểm, 0 byte lệch" đều có thể đúng về lời
   gọi và sai về kết quả.
2. **Bộ kiểm nó tự viết thì báo đạt sẵn.** Phải có người sửa hỏng mã sản phẩm rồi đòi bộ kiểm
   phải báo lỗi.
3. **Nó không chạm được vào thế giới.** Có những con số chỉ đo được khi người dựng robot lên
   và nói nó ngã về phía nào.

Nên hình dung đúng không phải "Agent thay người", mà là: **Agent gánh phần ghi chép và phần
làm đủ bước, người giữ phần phán đoán và phần chạm vào vật thật.** Và có một vai thứ ba hoá ra
cũng quan trọng: **một bản đã chạy được**, dùng để so sánh.

Có một điều kiện đi kèm những con số tiền ở trên, phải nói rõ: **340 nghìn đồng chỉ đúng khi có
người biết phải nghi chỗ nào.** Giao cùng việc đó cho người không biết đặt phép đo thì tám chỗ
sai sẽ lọt hết, và robot sẽ không đứng — lúc ấy số tiền đó mua được một phần mềm trông như đã
xong.

---

## 8 · Những chỗ chưa làm được

Bảy việc về màn hình anh Công nêu đã làm xong ngày 02/10/2026 — và ba trong bảy việc **chẩn
đoán sai nguyên nhân**, chỉ biết khi có chỗ đứng để đo:

| Việc anh Công nêu | Nguyên nhân thật |
|---|---|
| công thức toán chưa dựng ở chat | *"chưa hề nối vào"* là **sai** — đã nối từ trước. Lỗi thật: hai bảng ký hiệu lệch **41 mục**, và phía chat đổi `\sum` thành chữ Sigma Hy Lạp thay vì ký hiệu phép tổng |
| dấu `**` lọt ra màn hình | phần lời Agent **đã đúng**; lỗi ở **lời người gõ** — nó đi một đường khác, cố ý để chữ trơn |
| bảng Markdown dựng sai | bốn lỗi, và là việc duy nhất chẩn đoán trúng hoàn toàn |
| cảnh báo dồn đống | 10 chỗ thêm, 1 chỗ xoá — và chỗ xoá ấy chỉ chạy khi đổi dự án |
| bản chụp cắt lời Agent | cắt ở 3 000 ký tự, nay 20 000 và ghi bản đủ ra tệp |
| màn hình Thiết kế trắng | dữ liệu có sẵn trong kho, thiếu khối đọc nó ra |
| kết quả bộ kiểm chip không hiện ở đâu | tab Mô phỏng đọc một khoá khác với khoá công cụ HDL ghi vào |

Bốn việc cuối cùng một hình dạng, và nó là mẫu lặp đi lặp lại trong dự án này: **cơ chế có sẵn,
đường dẫn tới nó đứt.** Không phải thiếu tính năng — là thiếu một dòng nối.

Ba lần trong cùng ngày tôi viết bộ ca kiểm **xanh cả khi đường dẫn đứt**: tôi kiểm *thứ làm
việc*, rồi kết luận cho *việc đã được làm*. Hai điều ấy cách nhau một đường dẫn, và đường dẫn
là chỗ hay đứt nhất. Nay mỗi khối có một ca đi qua đúng đường người dùng đi.

Nói ra để người đọc không phải tự tìm:

- **12 trong 127 công cụ vẫn chưa được dùng thật.** Trong đó có công cụ dò việc nguy hiểm trên
  bo, chưa viết xong.
- **Bộ vẽ sơ đồ còn yếu với sơ đồ dạng chuỗi dài.**
- **Sáu ca kiểm cần người trực tiếp làm**, chưa tự động hoá được.
- **Robot còn 23 trong 109 điều kiện chưa làm**, phần lớn là các điểm đo để cắm máy hiện sóng.
- **Đường dựng bitstream chỉ chạy được qua EIDE, không chạy được bằng `make`.** `soc_top.v`
  ghi đường dẫn `include` tính từ gốc dự án, nên `make bitstream-h1` đứng trong `bai2/` thì đổ.
  Nghĩa là tài liệu đang mô tả một đường dựng mà người khác gõ lại sẽ không ra — 96 ô đo được
  là thật, nhưng chưa dựng lại được bằng lệnh tay.
- **Agent không có công cụ chạy `make`.** Nó sửa được Makefile và mã C, nhưng phải nhờ người gõ
  `make` rồi báo lại. Trong việc FPGA chỗ này chặn hai lần, và cả hai lần Agent **hỏi** chứ
  không giả định là đã chạy — đúng việc, nhưng vẫn là một chặng phải có người.
- **Cách bắt bản ghi quanh lúc nạp mất mười ô đầu ở cấu hình nhanh.** `bat_log_giay` mở cổng
  trước khi nạp, mà kênh JTAG của chip FTDI chiếm cổng nối tiếp trong lúc ghi flash, nên chương
  trình chạy nhanh đã in xong mấy ô đầu trước khi đọc được. Cách chạy được là nạp xong rồi xả
  cổng cho im, sau đó cho bo chạy lại — chưa gói thành công cụ.
- **`tool.install` mở một thẻ duyệt mới mỗi lần gọi lại**, nên một việc cài có thể để lại hàng
  chục thẻ treo — thẻ được duyệt sang lượt sau, mà Agent thử lại trong cùng lượt.
- **Agent không có công cụ chạy một tệp Python.** Nó viết được `gen_data.py`, `plot.py`,
  `parse_log.py`, nhưng không tự chạy được chúng — nên nó không kiểm được chính công cụ nó vừa
  sửa, và một lần đã báo "đã xác minh thành công" cho một tệp đang vỡ. Lời báo ấy đúng về mô
  phỏng mà sai về công cụ: nó xác minh qua **sản phẩm** đã sinh ra trước đó.
- **Tác tử xác minh con có hạn 10 lời gọi, quá chặt.** Nó cày hết hạn vào `ledger.query` rồi
  trả về `chua_du_du_kien` mà chưa kịp nộp báo cáo — nên lời xác minh biến mất đúng lúc cần
  nó nhất.

Danh sách đầy đủ, kèm chỗ cần sửa trong mã:
[`docs/md/VIEC-CHO-LAM.md`](docs/md/VIEC-CHO-LAM.md).

---

## 9 · Cài và chạy

> **Cài lần đầu?** Đọc [**Hướng dẫn cài đặt đầy đủ**](docs/md/EIDE-CAI-DAT.md) — từ máy trắng
> tới lượt chạy đầu tiên, kèm bảng công cụ phần cứng (chỉ cài khi cần) và phần xử lý trục trặc.
> Dưới đây là bản ngắn cho người đã quen.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env          # rồi điền GEMINI_API_KEY
```

Chạy lõi:

```bash
# Một lượt, in ra cửa sổ dòng lệnh
.venv/bin/python -m eide --du-an du-lieu/du-an-cua-toi --go "Làm bộ chuyển LAN sang USB cho TV"

# Lõi phục vụ giao diện (app Swift chạy lõi làm tiến trình con)
.venv/bin/python -m eide --du-an du-lieu/du-an-cua-toi --stdio
```

Chạy giao diện (macOS):

```bash
cd ui/EIDEApp && ./dong-goi.sh      # dịch và đóng gói EIDE.app
open EIDE.app
```

Lần đầu mở: chọn **thư mục dự án** (đây cũng là vùng Agent bị khoá trong), gốc mã nguồn EIDE,
và Python. App tự nhớ cho lần sau.

---

## 10 · Mã nguồn bày thế nào

### 10.1 · Hai phần, nói với nhau qua đầu vào–đầu ra chuẩn

```
┌─────────────────────────────┐
│  EIDE.app  (Swift, macOS)   │   không tự quyết gì — chỉ vẽ lại thứ lõi gửi
│  Console · 11 tab · thẻ cửa │
└──────────────┬──────────────┘
               │ JSON-RPC 2.0 trên stdio — không mở cổng mạng nào
┌──────────────┴──────────────┐
│  Lõi EIDE  (Python)         │
│  vòng lặp Agent · 122 công  │
│  cụ · luật · cửa duyệt · kho│
└──────────────┬──────────────┘
               │
       <thư mục dự án>/.eide/   ← mọi thứ của dự án nằm trong đây
```

### 10.2 · Tất cả dữ liệu dự án nằm trong một thư mục

```
<dự án>/
├── .eide/
│   ├── ledger.jsonl       sổ ghi việc — mỗi dòng móc vào dòng trước bằng mã băm
│   ├── changesets.jsonl   từng lần sửa, ai sửa, vì sao
│   ├── snapshots.jsonl    các bản chốt
│   ├── blobs/             nội dung tệp theo mã băm
│   ├── llm/               nguyên văn từng lời gọi mô hình (khi bật EIDE_GHI_LLM=1)
│   ├── build/             kết quả dịch mã
│   └── ui-test/           kênh kiểm thử giao diện (chỉ có khi đang kiểm)
├── EIDE.md                bộ nhớ dài hạn và luật riêng của dự án
└── … tệp của bạn
```

Đem cả thư mục này sang máy khác là dựng lại được toàn bộ phiên làm việc, không cần tin vào
bản kể lại nào.

### 10.3 · Cây mã

```
src/eide/
├── loop.py            vòng lặp Agent
├── tools/             122 công cụ, chia theo nhóm
├── policy/            luật chặn và cửa duyệt
├── knowledge/         đọc tài liệu, rút con số, chữ trong hình
├── store/             kho dữ liệu dựa trên sổ ghi việc + git
├── build/             dịch mã, bo thật, nạp chip
├── sch/               sinh sơ đồ nguyên lý (bật bằng cờ)
├── surfaces.py        11 tab — hình chiếu của kho
└── xuat_ban.py        dựng Word · PowerPoint · Excel · PDF

ui/EIDEApp/Sources/EIDE/
├── Protocol/          13 loại việc người làm · 16 loại lệnh lõi gửi
├── State/             hình chiếu của thứ lõi đã gửi — không tự nghĩ ra gì
└── Views/             Console · thẻ cửa duyệt · 11 tab · thanh trạng thái
```

---

## Tài liệu

| | |
|---|---|
| **Cài đặt** | [`docs/md/EIDE-CAI-DAT.md`](docs/md/EIDE-CAI-DAT.md) |
| **Thiết kế tổng thể** (bản gốc để đối chiếu) | [`EIDE-MDD-40_v3.0`](docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md) |
| **Cấu trúc mã hiện tại** | [`EIDE-C4-46`](docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md) |
| **Chỗ mã khác tài liệu, và vì sao** | [`EIDE-DEV-LOG.md`](docs/md/EIDE-DEV-LOG.md) |
| **Việc đã nêu, chưa làm** | [`VIEC-CHO-LAM.md`](docs/md/VIEC-CHO-LAM.md) |
| **Kết quả đo mới nhất** | [`BAO-CAO-TONG.md`](docs/review-v3/test/BAO-CAO-TONG.md) |
| **Việc thật 1 — hệ điều hành tự viết** | [`docs/rtos-tu-viet/`](docs/rtos-tu-viet/) |
| **Việc thật 2 — robot hai bánh tự đứng** | [`docs/robot-tu-can-bang/`](docs/robot-tu-can-bang/) |
