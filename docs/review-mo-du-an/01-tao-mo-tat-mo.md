# Phiên làm việc: Review ba tính năng nền: tạo · mở · tắt-mở-làm-tiếp

Ghi tự động. Mỗi mục là một bước có thật trong một phiên EIDE chạy trên máy, với ảnh chụp cửa sổ EIDE làm sở cứ.

- Nguồn: `thư mục rỗng, không chép sẵn gì`
- Thư mục dự án: `du-lieu/thu-ben-vung`
- Bắt đầu: 28/09/2026 20:02:51

---

## Bước 1. Trỏ app vào một thư mục RỖNG — nó tự dựng được dự án không?

**Trước khi mở**

```
{
 "co_eide": false
}
```

**Sau khi app mở**

```
{
 "co_eide": true,
 "tep_trong_eide": [
  "blobs",
  "counters.json",
  "ledger.jsonl",
  "sessions",
  "store.sqlite",
  "store.sqlite-shm",
  "store.sqlite-wal",
  "transcripts",
  "ui-test"
 ],
 "so_dong_so_cai": 13,
 "so_changeset": 0,
 "phien": [
  "ses-0001"
 ],
 "bo_dem": {
  "ses": 1
 },
 "transcript": [],
 "bang_trong_kho": [
  "artefacts",
  "ckm_connection",
  "ckm_edges",
  "ckm_nodes",
  "ckm_port",
  "events",
  "facts",
  "sch_sheets",
  "sqlite_sequence"
 ],
 "so_hien_vat": 0,
 "co_eide_md": true,
 "eide_md_dong": 33
}
```

✅ App tự dựng được dự án từ thư mục rỗng

```
tệp trong .eide: ['blobs', 'counters.json', 'ledger.jsonl', 'sessions', 'store.sqlite', 'store.sqlite-shm', 'store.sqlite-wal', 'transcripts', 'ui-test']
```

✅ Có EIDE.md — bộ nhớ dài hạn của dự án, thứ tác tử đọc mỗi lượt

```
33 dòng
```

![01-mo-thu-muc-rong](anh/01-01-mo-thu-muc-rong.png)


## Bước 2. Giao một việc có DẤU VẾT — tác tử phải ghi một điều vào bộ nhớ dự án

**Anh gõ:**

> Mình bắt đầu một dự án mới trên bo STM32F469I-DISCO.
> 
> Việc đầu tiên rất nhỏ: ghi vào bộ nhớ dài hạn của dự án đúng một điều — **thạch anh của bo này là 8 MHz, và mình đặt tên dự án là DEN-NHAY-8M**.
> 
> Ghi xong thì nói lại cho mình biết bạn ghi vào đâu.

**Tác tử:**

> [Tác tử] Tôi đã ghi nhận thông tin vào bộ nhớ dài hạn của dự án (`EIDE.md`), lưu Fact tương ứng vào kho, và đã được verifier độc lập kiểm chứng đạt (`dat`).
> 
> ### 1. Vị trí đã ghi trong `EIDE.md`
> * **Mục `## Mục tiêu`** (dòng 8, changeset `cs-0001`):
>   > Dự án DEN-NHAY-8M trên bo STM32F469I-DISCO.
> * **Mục `## Chip & phần cứng`** (dòng 12, changeset `cs-0002`):
>   > Bo STM32F469I-DISCO: thạch anh (HSE) 8 MHz (anh cho, chưa có tài liệu).
> 
> ### 2. Fact tầng NGƯỜI đã lưu trong kho
> * **Mã Fact:** `f-nguoi-76230845`
> * **Thực thể:** `bo:STM32F469I-DISCO`
> * **Thuộc tính:** `crystal.freq = 8 MHz`
> * **Tầng tin cậy:** **NGƯỜI** (trích lời: *"thạch anh của bo này là 8 MHz"*, dùng được để cấu hình clock kèm ghi chú nguồn từ anh).
> 
> ### 3. Kết quả kiểm chứng độc lập (Verifier)
> * **Kết luận:** **ĐẠT**
> * **Bằng chứng đối chiếu:** `EIDE.md` (dòng 8 và 12), lịch sử `cs-0001`, `cs-0002`, và Fact `f-nguoi-76230845` khớp chính xác.
> 
> ---
> 
> **Báo cáo:**
> - **Đã làm:** Ghi nhận tên dự án và thông số thạch anh vào `EIDE.md`, lưu Fact tầng NGƯỜI, và cho verifier độc lập kiểm tra toàn vẹn.
> - **Bỏ gì và vì sao:** Chưa nạp tài liệu chính thức (User Manual UM1932 / Datasheet) của STM32F469I-DISCO vì anh chưa yêu cầu.
> - **Giả định đang dùng:** Thạch anh 8 MHz là nguồn tạo xung ngoài HSE cho vi điều khiển trên bo.
> - **Hoàn tác được tới đâu:** Có thể hoàn tác về trạng thái ban đầu bằng cách lùi các changeset `cs-0001` và `cs-0002`.
> - **Bước tiếp theo đề xuất:** Anh muốn nạp tài liệu kỹ thuật của bo để nâng Fact lên tầng VÀNG và xác định chân điều khiển LED, hay đi thẳng vào việc tạo yêu cầu (REQ) cho ứng dụng đèn nháy?

**Công cụ tác tử đã gọi**

```
 1. memory.note          ok  {"line": "Dự án DEN-NHAY-8M trên bo STM32F469I-DISCO.", "explain": {"diff_prev": "bản đầu 
 2. memory.note          ok  {"line": "Bo STM32F469I-DISCO: thạch anh (HSE) 8 MHz (anh cho, chưa có tài liệu).", "secti
 3. fact.assert_human    ok  {"dieu_kien": "Thạch anh ngoài (HSE) gắn trên bo mạch STM32F469I-DISCO", "subject": "bo:ST
 4. task.run             ok  {"subagent": "verifier", "viec": "Kiểm tra tính toàn vẹn của các hiện vật vừa ghi:\n1. Đọc
```

**Chuỗi công cụ**

memory.note → memory.note → fact.assert_human → task.run

**Trạng thái TRƯỚC khi tắt**

```
{
 "co_eide": true,
 "tep_trong_eide": [
  "blobs",
  "changesets.jsonl",
  "counters.json",
  "ledger.jsonl",
  "sessions",
  "store.sqlite",
  "store.sqlite-shm",
  "store.sqlite-wal",
  "transcripts",
  "ui-test"
 ],
 "so_dong_so_cai": 111,
 "so_changeset": 2,
 "phien": [
  "ses-0001"
 ],
 "bo_dem": {
  "ses": 1,
  "h": 1,
  "run": 1,
  "cs": 2
 },
 "transcript": [],
 "bang_trong_kho": [
  "artefacts",
  "ckm_connection",
  "ckm_edges",
  "ckm_nodes",
  "ckm_port",
  "events",
  "facts",
  "sch_sheets",
  "sqlite_sequence"
 ],
 "so_hien_vat": 1,
 "co_eide_md": true,
 "eide_md_dong": 33
}
```

✅ Điều được giao đã nằm trên ĐĨA (EIDE.md), không chỉ trong hội thoại

```
EIDE.md 33 dòng · có 'DEN-NHAY-8M': True · có '8 MHz': True
```

![02-sau-khi-giao-viec](anh/02-02-sau-khi-giao-viec.png)


## Bước 3. GIẾT app bằng kill -9 — như máy sập, không phải thoát tử tế

**Trạng thái NGAY SAU khi bị giết**

```
{
 "co_eide": true,
 "tep_trong_eide": [
  "blobs",
  "changesets.jsonl",
  "counters.json",
  "ledger.jsonl",
  "sessions",
  "store.sqlite",
  "transcripts",
  "ui-test"
 ],
 "so_dong_so_cai": 111,
 "so_changeset": 2,
 "phien": [
  "ses-0001"
 ],
 "bo_dem": {
  "ses": 1,
  "h": 1,
  "run": 1,
  "cs": 2
 },
 "transcript": [],
 "bang_trong_kho": [
  "artefacts",
  "ckm_connection",
  "ckm_edges",
  "ckm_nodes",
  "ckm_port",
  "events",
  "facts",
  "sch_sheets",
  "sqlite_sequence"
 ],
 "so_hien_vat": 1,
 "co_eide_md": true,
 "eide_md_dong": 33
}
```

❌ Không mất gì trên đĩa khi bị giết đột ngột

```
khác biệt: {"tep_trong_eide": [["blobs", "changesets.jsonl", "counters.json", "ledger.jsonl", "sessions", "store.sqlite", "store.sqlite-shm", "store.sqlite-wal", "transcripts", "ui-test"], ["blobs", "changesets.jsonl", "counters.json", "ledger.jsonl", "sessions", "store.sqlite", "transcripts", "ui-test"]]}
```


## Bước 4. Mở lại đúng dự án ấy — tác tử có nhớ việc lượt trước không?

**Trạng thái sau khi mở lại**

```
{
 "co_eide": true,
 "tep_trong_eide": [
  "blobs",
  "changesets.jsonl",
  "counters.json",
  "ledger.jsonl",
  "sessions",
  "store.sqlite",
  "store.sqlite-shm",
  "store.sqlite-wal",
  "transcripts",
  "ui-test"
 ],
 "so_dong_so_cai": 124,
 "so_changeset": 2,
 "phien": [
  "ses-0001",
  "ses-0002"
 ],
 "bo_dem": {
  "ses": 2,
  "h": 1,
  "run": 1,
  "cs": 2
 },
 "transcript": [],
 "bang_trong_kho": [
  "artefacts",
  "ckm_connection",
  "ckm_edges",
  "ckm_nodes",
  "ckm_port",
  "events",
  "facts",
  "sch_sheets",
  "sqlite_sequence"
 ],
 "so_hien_vat": 1,
 "co_eide_md": true,
 "eide_md_dong": 33
}
```

✅ Sổ cái KHÔNG bị ghi đè khi mở lại (mở lại không phải bắt đầu lại)

```
trước tắt 111 dòng · sau mở lại 124 dòng
```

✅ Mở lại tạo PHIÊN MỚI (không ghi chồng lên phiên cũ)

```
trước: ['ses-0001'] · sau: ['ses-0001', 'ses-0002']
```

**Anh gõ:**

> Mình vừa tắt app rồi mở lại.
> 
> Không tra lại tài liệu gì cả, trả lời mình bằng thứ bạn đang có: **tên dự án này là gì, và thạch anh của bo bao nhiêu MHz?** Nếu bạn không biết thì nói thẳng là không biết — đừng đoán.

**Tác tử:**

> [Tác tử] Lượt chạy `run-002` trước đó đã bị dừng giữa chừng khi ứng dụng đóng lại. 
> 
> Từ bộ nhớ dài hạn (`EIDE.md`) và bảng kiểm kê hiện có của dự án, thông tin như sau:
> 
> 1. **Tên dự án:**
>    - **Mục tiêu dự án:** **DEN-NHAY-8M** (phát triển trên bo mạch STM32F469I-DISCO).
>    - *Tên thư mục/không gian dự án trong hệ thống:* `thu-ben-vung`.
> 
> 2. **Thạch anh của bo:**
>    - **8 MHz** (thạch anh ngoài HSE).
>    - *Tầng tin cậy:* **NGƯỜI** (do anh cung cấp ở lượt trước, hiện chưa có datasheet hoặc tài liệu nhà sản xuất đối chiếu).
> 
> ---
> 
> ### Bước tiếp theo
> Anh muốn tiếp tục công việc dở dang của `run-002`, hay bắt đầu nạp datasheet cho STM32F469I-DISCO để đưa thông số 8 MHz lên tầng VÀNG?
> 
> ---
> **Báo cáo tóm tắt:**
> - **Đã làm:** Đọc thông tin dự án và tần số thạch anh từ bộ nhớ dài hạn và bảng kiểm kê.
> - **Bỏ qua:** Không gọi thêm công cụ tra cứu bên ngoài theo đúng yêu cầu.
> - **Giả định đang dùng:** Thông số thạch anh 8 MHz theo lời anh cung cấp (tầng NGƯỜI).
> - **Hoàn tác:** Không có thay đổi nào được tạo ra trên hệ thống.
> - **Chi phí:** 0 lời gọi công cụ.

**Công cụ tác tử đã gọi**

```
— không gọi công cụ nào —
```

**Chuỗi công cụ**

—

✅ Tác tử NHỚ được việc của phiên trước sau khi tắt app

```
lời đáp có 'DEN-NHAY-8M': True · gọi 0 công cụ: 
```

✅ Nếu phải tra thì tra được — có đường tới trí nhớ cũ

```
không cần tra, trả lời thẳng
```

![03-sau-khi-mo-lai](anh/04-03-sau-khi-mo-lai.png)

**Kết thúc**

nhật ký: /Users/congvt/Documents/EIDE_v3/du-lieu/ket-qua/ben-vung/NHAT-KY.md

