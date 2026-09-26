import Foundation

/// Kênh kiểm thử giao diện — gõ vào app và đọc ra app đang hiện gì.
///
/// ## Vì sao không dùng gõ phím của hệ điều hành
///
/// `osascript … keystroke` gửi phím tới **cửa sổ đang có tiêu điểm**, không tới một
/// ứng dụng cụ thể. Khi người dùng đang làm nhiều việc cùng lúc, việc đưa app ra trước
/// có thể thất bại trong tích tắc, và phím rơi vào ứng dụng khác. Chuyện đó đã xảy ra
/// thật trong lúc phát triển: một câu tiếng Việt kèm phím Enter lọt vào cửa sổ khác
/// của người dùng. Một bài kiểm không được phép có rủi ro đó.
///
/// `CGEventPostToPid` nhắm đúng tiến trình được, nhưng vẫn chỉ **gõ vào** — nó không
/// trả lời được câu hỏi quan trọng hơn: *giao diện đang hiện cái gì?*
///
/// ## Cách làm
///
/// Hai tệp trong thư mục dự án:
///
/// ```
/// <dự án>/.eide/ui-test/
///     inbox.jsonl     kiểm thử → app   (HumanAct, hoặc lệnh điều khiển giao diện)
///     outbox.jsonl    app → kiểm thử   (ảnh chụp trạng thái giao diện)
/// ```
///
/// Kênh chỉ bật khi thư mục `ui-test/` **tồn tại** — nó không tự tạo. Người dùng bình
/// thường sẽ không bao giờ có thư mục đó, và khi bật thì giao diện hiện một dải báo
/// rõ để không ai nhầm phiên kiểm thử với phiên làm việc thật.
///
/// ## Điều này KHÔNG phá vỡ bất biến I1
///
/// Mọi thứ đọc từ `inbox` đều đi qua `AppState.gui(_:)` — tức vẫn thành `HumanAct` gửi
/// qua `console.act`, đúng một cửa vào lõi. Kênh này thay **ngón tay người**, không
/// thay giao thức.
@MainActor
final class UITestChannel {

    private weak var state: AppState?
    private var thuMuc: URL?
    private var timer: Timer?
    private var daDoc = 0
    private var soLenh = 0

    var dangBat: Bool { thuMuc != nil }

    /// Bật kênh nếu thư mục `ui-test/` có sẵn trong dự án.
    func batNeuCo(duAn: URL, state: AppState) {
        let d = duAn.appendingPathComponent(".eide/ui-test")
        guard FileManager.default.fileExists(atPath: d.path) else { return }
        self.thuMuc = d
        self.state = state

        let inbox = d.appendingPathComponent("inbox.jsonl")
        if !FileManager.default.fileExists(atPath: inbox.path) {
            FileManager.default.createFile(atPath: inbox.path, contents: nil)
        }
        ghi(["su_kien": "kenh_mo", "ghi_chu": "Giao diện sẵn sàng nhận lệnh kiểm thử"])

        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.doc() }
        }
    }

    func tat() {
        timer?.invalidate()
        timer = nil
        thuMuc = nil
    }

    // MARK: - Đọc lệnh

    private func doc() {
        guard let d = thuMuc,
              let noi = try? String(contentsOf: d.appendingPathComponent("inbox.jsonl"),
                                    encoding: .utf8) else { return }
        let dong = noi.components(separatedBy: .newlines).filter { !$0.isEmpty }
        guard dong.count > daDoc else { return }
        for line in dong[daDoc...] {
            daDoc += 1
            guard let data = line.data(using: .utf8),
                  let v = try? JSONDecoder().decode(JSONValue.self, from: data) else {
                ghi(["su_kien": "loi", "ghi_chu": "dòng không đọc được: \(line.prefix(80))"])
                continue
            }
            thucHien(v)
        }
    }

    private func thucHien(_ v: JSONValue) {
        soLenh += 1
        guard let s = state else { return }

        // Lệnh điều khiển giao diện (thay cho cái bấm chuột).
        if let ui = v["ui"]?.stringValue {
            switch ui {
            case "tab":
                if let t = v["surface"]?.stringValue {
                    s.selectedSurface = t
                    s.gui(.attend(surface: t))
                    ghi(["su_kien": "mo_tab", "surface": t])
                }
            case "dump":
                ghi(anhChup(nhan: v["nhan"]?.stringValue ?? "dump"))
            case "quyet":
                // Bấm nút trên thẻ cổng.
                if let gid = v["gate_id"]?.stringValue {
                    let duyet = v["approved"]?.boolValue ?? false
                    s.gui(.decide(gateID: gid, approved: duyet,
                                  choice: v["choice"]?.stringValue,
                                  note: v["note"]?.stringValue))
                    ghi(["su_kien": "quyet_cong", "gate_id": gid, "duyet": duyet ? "có" : "không"])
                }
            case "cho":
                ghi(["su_kien": "cho", "dang_chay": s.busy ? "có" : "không"])
            default:
                ghi(["su_kien": "loi", "ghi_chu": "lệnh giao diện lạ: \(ui)"])
            }
            return
        }

        // Còn lại là HumanAct — đi qua đúng đường mà nút Gửi đi.
        guard let data = try? JSONEncoder().encode(v),
              let act = try? JSONDecoder().decode(HumanAct.self, from: data) else {
            ghi(["su_kien": "loi", "ghi_chu": "HumanAct không hợp lệ"])
            return
        }
        s.gui(act)
        ghi(["su_kien": "da_gui", "kind": act.kind.rawValue,
             "text": String(act.text.prefix(120))])
    }

    // MARK: - Ảnh chụp giao diện

    /// Chụp lại **thứ giao diện đang hiện** — không phải thứ lõi đã gửi.
    ///
    /// Đây là điểm khác biệt so với kiểm ở tầng giao thức: nó nói được "bộ dựng
    /// markdown đã tách ra một bảng và hai tiêu đề", "thẻ cổng hiện 3 dòng hậu quả",
    /// "tab Mã nguồn có một khối quy trình 5 bước" — những thứ chỉ đúng khi mã Swift
    /// chạy thật.
    private func anhChup(nhan: String) -> [String: Any] {
        guard let s = state else { return [:] }

        let loiTacTu = s.transcript.filter { $0.role == .agent }
        let cuoi = loiTacTu.last?.text ?? ""
        let khoiMd = Markdown.tach(cuoi).map(tenKhoi)

        let theHien: [[String: Any]] = s.theDangCho.map { c in
            [
                "loai": c.kind.rawValue,
                "gate": c.gate ?? "",
                "gate_id": c.gateID ?? "",
                // Thẻ làm rõ không có gate_id; trả lời nó cần card_id.
                "card_id": c.id,
                "tieu_de": c.title,
                "so_hau_qua": c.consequences.count,
                "never_auto": c.neverAuto,
                "so_cau_hoi": c.questions.count,
                "co_gia_dinh": !(c.assumptionIfSkipped ?? "").isEmpty,
                "lua_chon": c.options,
            ]
        }

        let bm = s.surfaces[s.selectedSurface]
        let khoi: [[String: Any]] = (bm?.blocks ?? []).map { b in
            // Lớp giải thích: nút "Vì sao?" chỉ hiện khi khối mang đủ sáu trường (N8).
            let ex = b.payload["explain"]?.objectValue ?? [:]
            let duTruong = ["summary", "why", "sources", "diff_prev", "next", "confidence"]
                .allSatisfy { ex[$0] != nil }
            return [
                "code": b.code, "type": b.type, "title": b.title,
                "summary": b.summary ?? "",
                "summary_render": Markdown.chuThuan(b.summary ?? ""),
                "chu_da_dung": chuDaDung(b),
                "so_buoc": b.arr("buoc").count,
                "so_hang": b.arr("rows").count,
                // Cây khối (A5.9): phơi ra thứ người NHÌN THẤY trên cây, để ca đo hỏi được
                // "nút nào đang cần cập nhật" thay vì chỉ đếm dòng bảng.
                "so_nut_cay": b.arr("cay_nut").count,
                "nut_can_cap_nhat": b.arr("cay_nut")
                    .filter { $0["tinh_trang"]?.stringValue == "stale" }
                    .compactMap { $0["duong"]?.stringValue },
                "nut_con_da_doi": b.arr("cay_nut")
                    .filter { $0["tinh_trang"]?.stringValue == "con_da_doi" }
                    .compactMap { $0["duong"]?.stringValue },
                "sau_nhat": b.arr("cay_nut").map { $0["muc"]?.intValue ?? 0 }.max() ?? 0,
                "so_muc": b.arr("items").count,
                // Ô trống trung thực: ba trường này là thứ người ĐỌC khi chưa có gì.
                // Không phơi ra thì mọi phép kiểm về ô trống đều đậu giả vì chuỗi rỗng.
                "chua_co": b.str("chua_co") ?? "",
                "vi_sao": b.str("vi_sao") ?? "",
                "can_gi": b.str("can_gi") ?? "",
                // G3 — hợp đồng trình bày E2
                "co_explain": !ex.isEmpty,
                "explain_du_6_truong": duTruong,
                "so_nguon": (ex["sources"]?.arrayValue ?? []).count,
                "phien_ban": b.payload["phien_ban"]?.intValue ?? 0,
                "tac_gia": b.str("tac_gia") ?? "",
                "diff_prev": b.str("diff_prev") ?? "",
                "stale_reason": b.str("stale_reason") ?? "",
                // Cột nào người sửa được bằng widget (§E2 "Người sửa được gì")
                "cot_sua": Array((b.payload["cot_sua"]?.objectValue ?? [:]).keys),
                "so_dong_co_explain": (b.payload["row_meta"]?.objectValue ?? [:])
                    .values.filter { !($0["explain"]?.objectValue ?? [:]).isEmpty }.count,
            ]
        }

        return [
            "su_kien": "anh_chup", "nhan": nhan,
            "so_dong_hoi_thoai": s.transcript.count,
            "loi_tac_tu_cuoi": String(cuoi.prefix(3000)),
            // Chữ SAU KHI DỰNG — để hỏi được "trên màn hình còn dấu sao không".
            "loi_tac_tu_render": String(Markdown.chuThuan(cuoi).prefix(3000)),
            "khoi_markdown": khoiMd,
            "the_dang_cho": theHien,
            "tab_dang_mo": s.selectedSurface,
            "tab_tieu_de": bm?.title ?? "",
            "khoi_tren_tab": khoi,
            "thong_bao": s.notices.suffix(5).map { ["muc": $0.level, "chu": $0.text] },
            "trang_thai": [
                "du_an": s.status.du_an, "chip": s.status.chip,
                "chang": s.status.chang, "stale": s.status.stale,
                "fact": s.status.fact, "mo_hinh": s.status.mo_hinh,
                // Đồng hồ ngữ cảnh (MEM-02) — để ca đo hỏi được "khối nào chạm trần".
                "ngu_canh": [
                    "tong": s.status.ngu_canh.tong,
                    "cua_so": s.status.ngu_canh.cua_so,
                    "ty_le": s.status.ngu_canh.ty_le,
                    "muc": s.status.ngu_canh.muc,
                    "kha_dung": s.status.ngu_canh.kha_dung,
                    "khoi": s.status.ngu_canh.khoi.map {
                        ["ten": $0.ten, "token": $0.token,
                         "tran": $0.tran ?? 0, "vuot": $0.vuot] as [String: Any]
                    },
                ] as [String: Any],
            ],
            "dang_chay": s.busy,
        ]
    }

    /// Gom mọi chữ do tác tử viết trong một khối, đã qua bộ dựng. Dùng để soi xem
    /// còn chỗ nào trên tab quên nối vào bộ dựng markdown không (DEV-247).
    private func chuDaDung(_ b: SurfaceBlock) -> String {
        var phan: [String] = [b.summary ?? "", b.str("text") ?? "",
                              b.str("chua_co") ?? "", b.str("vi_sao") ?? "",
                              b.str("can_gi") ?? "", b.str("muc_dich") ?? ""]
        for r in b.arr("rows") {
            phan += r.arrayValue.compactMap(\.stringValue)
        }
        for p in b.arr("pairs") {
            phan += p.arrayValue.compactMap(\.stringValue)
        }
        phan += b.arr("items").compactMap(\.stringValue)
        for x in b.arr("buoc") {
            phan += [x["viec"]?.stringValue ?? "", x["canh_bao"]?.stringValue ?? ""]
        }
        for x in b.arr("sections") {
            phan += [x["ten"]?.stringValue ?? "", x["than"]?.stringValue ?? ""]
        }
        for x in b.arr("cay_nut") {
            phan += [x["ten"]?.stringValue ?? "", x["ly_do"]?.stringValue ?? ""]
        }
        return phan.filter { !$0.isEmpty }
            .map { Markdown.chuThuan($0) }.joined(separator: "\n")
    }

    private func tenKhoi(_ k: MdKhoi) -> String {
        switch k {
        case .doan: return "đoạn"
        case .tieuDe(let n, _): return "tiêu-đề-\(n)"
        case .danhSach: return "danh-sách"
        case .bang: return "bảng"
        case .ma: return "khối-mã"
        case .trichDan: return "trích-dẫn"
        case .duongKe: return "đường-kẻ"
        case .congThuc: return "công-thức"
        }
    }

    // MARK: - Ghi ra

    private func ghi(_ o: [String: Any]) {
        guard let d = thuMuc else { return }
        var obj = o
        obj["ts"] = ISO8601DateFormatter().string(from: Date())
        obj["stt"] = soLenh
        guard let data = try? JSONSerialization.data(withJSONObject: obj,
                                                     options: [.sortedKeys]),
              var s = String(data: data, encoding: .utf8) else { return }
        s += "\n"
        let f = d.appendingPathComponent("outbox.jsonl")
        if let h = try? FileHandle(forWritingTo: f) {
            h.seekToEndOfFile()
            h.write(s.data(using: .utf8)!)
            try? h.close()
        } else {
            try? s.write(to: f, atomically: true, encoding: .utf8)
        }
    }
}
