import AppKit
import Foundation
import SwiftUI

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

    /// Đã từng bật trong phiên chạy này chưa.
    ///
    /// Kênh bật theo sự có mặt của `.eide/ui-test` trong dự án — cách ấy giữ cho kênh TẮT ở
    /// mọi dự án thật, và đó là điều đúng. Nhưng nó có một hệ quả: **đổi dự án là mất kênh**,
    /// vì dự án mới chưa có thư mục ấy. Mà "đổi dự án" lại đúng là thứ cần đo — anh Công báo
    /// màn hình giữ nguyên chat của dự án cũ, và không bài đo nào chạm tới được.
    ///
    /// *Một bộ đo tắt đúng lúc xảy ra việc cần đo thì không đo được gì.*
    ///
    /// Nên: đã bật một lần trong phiên thì theo sang dự án sau, tự tạo thư mục. Bật lần đầu
    /// vẫn phải do người đặt thư mục vào — app không bao giờ tự mở kênh.
    private var daTungBat = false

    /// Bật kênh: thư mục `ui-test/` có sẵn trong dự án, hoặc kênh đã bật ở dự án trước.
    func batNeuCo(duAn: URL, state: AppState) {
        let d = duAn.appendingPathComponent(".eide/ui-test")
        if !FileManager.default.fileExists(atPath: d.path) {
            guard daTungBat else { return }
            try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        }
        daTungBat = true
        // Con trỏ đọc thuộc về MỘT tệp inbox. Sang dự án khác là sang một tệp khác, mà con
        // trỏ vẫn đứng ở dòng thứ N của tệp cũ — kênh sẽ bỏ qua N lệnh đầu của dự án mới.
        daDoc = 0
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
            case "so_do_thu":
                // Hỏi thẳng BỘ DỰNG: một đoạn markdown ra những khối gì, sơ đồ có vẽ được
                // không, và vẽ ra những nhãn nào.
                //
                // Cố ý KHÔNG bơm một dòng giả vào hội thoại. I2 nói hội thoại là hình chiếu
                // của sổ cái; một móc thử phá bất biến ấy sẽ che lỗi chứ không tìm ra lỗi.
                // Ở đây chỉ hỏi hàm thuần, và nó đúng là thứ đang cần đo.
                ghi(soDoThu(v["md"]?.stringValue ?? ""))
            case "anh_so_do":
                // App tự vẽ CHÍNH KHỐI SƠ ĐỒ ra PNG, để người đọc báo cáo nhìn được hình chứ
                // không chỉ đọc con số. Cùng lý do với `anh`: không dùng `screencapture`.
                if let tep = v["tep"]?.stringValue {
                    ghi(anhSoDo(md: v["md"]?.stringValue ?? "", tep: tep))
                }
            case "quyet":
                // Bấm nút trên thẻ cổng.
                if let gid = v["gate_id"]?.stringValue {
                    let duyet = v["approved"]?.boolValue ?? false
                    s.gui(.decide(gateID: gid, approved: duyet,
                                  choice: v["choice"]?.stringValue,
                                  note: v["note"]?.stringValue))
                    ghi(["su_kien": "quyet_cong", "gate_id": gid, "duyet": duyet ? "có" : "không"])
                }
            case "anh":
                // App TỰ VẼ cửa sổ của mình ra PNG. Không dùng `screencapture`.
                //
                // Chụp theo vùng màn hình đã hai lần lọt cửa sổ của ứng dụng khác vào ảnh —
                // một lần có cả tệp `.env` kèm khoá API của người dùng. Ảnh đã chụp thì
                // không rút lại được, nên cách chụp phải KHÔNG THỂ lấy nhầm, chứ không phải
                // cẩn thận để đừng lấy nhầm.
                Task { @MainActor in
                    let tep = v["tep"]?.stringValue ?? ""
                    // `cua_so`: chụp đúng cửa sổ có tiêu đề chứa chuỗi này. Không truyền thì
                    // lấy cửa sổ chính như cũ.
                    //
                    // Cần vì bảng "Giới thiệu EIDE" là một `NSWindow` phụ: `NSApp.windows`
                    // không đảm bảo thứ tự trước–sau, nên không có cách nào chụp đúng nó mà
                    // không nói tên ra.
                    let ten = v["cua_so"]?.stringValue ?? ""
                    let chon: (NSWindow) -> Bool = ten.isEmpty
                        ? { $0.isVisible && $0.canBecomeMain }
                        : { $0.isVisible && $0.title.localizedCaseInsensitiveContains(ten) }
                    guard let w = NSApp.windows.first(where: chon),
                          let view = w.contentView, !tep.isEmpty else {
                        self.ghi(["su_kien": "anh_loi", "ghi_chu": "không có cửa sổ"])
                        return
                    }
                    guard let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) else {
                        self.ghi(["su_kien": "anh_loi", "ghi_chu": "không tạo được bitmap"])
                        return
                    }
                    view.cacheDisplay(in: view.bounds, to: rep)
                    guard let png = rep.representation(using: .png, properties: [:]) else {
                        self.ghi(["su_kien": "anh_loi", "ghi_chu": "không mã hoá được PNG"])
                        return
                    }
                    do {
                        let u = URL(fileURLWithPath: tep)
                        try FileManager.default.createDirectory(
                            at: u.deletingLastPathComponent(), withIntermediateDirectories: true)
                        try png.write(to: u)
                        self.ghi(["su_kien": "da_chup", "tep": tep,
                                  "rong": Int(rep.pixelsWide), "cao": Int(rep.pixelsHigh)])
                    } catch {
                        self.ghi(["su_kien": "anh_loi", "ghi_chu": "\(error)"])
                    }
                }
            // Ba lệnh cho vòng đời dự án. Chúng gọi ĐÚNG những hàm mà nút bấm gọi, chỉ
            // thiếu cái bảng chọn tệp của macOS — bảng ấy là modal, không lái được từ tệp,
            // và đó là giới hạn được nói ra chứ không giấu đi.
            case "du_an_moi":
                if let d = v["tep"]?.stringValue {
                    do {
                        try s.taoDuAnTai?(d)
                        Task { await s.moDuAnKhac?(d) }
                        ghi(["su_kien": "du_an_moi", "tep": d])
                    } catch {
                        ghi(["su_kien": "du_an_moi_loi", "loi": error.localizedDescription])
                    }
                }
            case "mo_gan_day":
                if let d = v["tep"]?.stringValue {
                    Task { await s.moDuAnKhac?(d); self.ghi(["su_kien": "da_mo", "tep": d]) }
                }
            case "dong_du_an":
                s.dong()
                ghi(["su_kien": "da_dong_du_an"])
            case "gioi_thieu":
                // Mở bảng Giới thiệu. Có mặt ở đây để phép kiểm giao diện chạm được vào nó
                // qua đúng một cửa như mọi thao tác khác, thay vì phải lái menu ở mức OS.
                Task { @MainActor in
                    GioiThieuCuaSo.hien()
                    self.ghi(["su_kien": "da_mo_gioi_thieu"])
                }
            case "be_rong":
                // Ba nút Hẹp/Vừa/Rộng trên đầu Console. Đo được bề rộng THẬT sau khi bấm,
                // vì `RootView` còn kẹp nó theo 38 % chiều ngang cửa sổ — một nút đổi biến
                // mà khung không nhúc nhích thì vẫn là một nút không làm gì.
                if let x = v["muc"]?.stringValue,
                   let w = AppState.ConsoleWidth.allCases.first(where: { $0.nhan.lowercased()
                       == x.lowercased() || "\($0)" == x }) {
                    s.consoleWidth = w
                    ghi(["su_kien": "da_doi_be_rong", "muc": w.nhan,
                         "rong_dat": Int(w.rawValue)])
                } else {
                    ghi(["su_kien": "loi", "ghi_chu": "bề rộng lạ: \(v["muc"] ?? .null)"])
                }
            case "them_tai_lieu":
                // Thay CÚ KÉO của người, không thay giao thức: nó gọi đúng hàm mà cú kéo và
                // nút ghim giấy gọi, nên phần chép vào hộp cát và `HumanAct.upload` đều là
                // đường thật.
                if let ds = v["tep"]?.arrayValue {
                    let u = ds.compactMap { $0.stringValue }.map { URL(fileURLWithPath: $0) }
                    s.themTaiLieu(u)
                    ghi(["su_kien": "da_them_tai_lieu", "so_tep": u.count])
                }
            case "menu":
                // App tự khai thanh menu của nó: có những mục nào, phím tắt nào.
                //
                // Câu "Cmd+C/Cmd+V trong ô nhập có chạy không" trả lời được bằng ĐO chứ
                // không cần suy: nếu menu Edit chuẩn của macOS còn nguyên thì các lệnh sửa
                // văn bản còn nguyên. Suy từ mã thì chỉ biết mình KHÔNG xoá nó — không biết
                // nó có thật sự ở đó không.
                Task { @MainActor in
                    var ra: [[String: Any]] = []
                    for m in NSApp.mainMenu?.items ?? [] {
                        let muc = (m.submenu?.items ?? []).compactMap { x -> [String: Any]? in
                            if x.isSeparatorItem { return nil }
                            return ["ten": x.title,
                                    "phim": x.keyEquivalent.isEmpty ? "" :
                                        self.moTaPhim(x)]
                        }
                        ra.append(["ten": m.title, "muc": muc])
                    }
                    self.ghi(["su_kien": "menu", "thanh_menu": ra])
                }
            case "co_cua_so":
                // Đổi khổ cửa sổ để đo giao diện ở nhiều kích thước màn hình.
                Task { @MainActor in
                    if let w = NSApp.windows.first(where: { $0.isVisible && $0.canBecomeMain }),
                       let r = v["rong"]?.intValue, let c = v["cao"]?.intValue {
                        var f = w.frame
                        f.size = NSSize(width: CGFloat(r), height: CGFloat(c))
                        w.setFrame(f, display: true)
                    }
                    self.ghi(["su_kien": "da_doi_co"])
                }
            case "len_truoc":
                // App tự đưa cửa sổ của MÌNH lên trước, để ảnh chụp vùng màn hình không lọt
                // cửa sổ của ứng dụng khác. Đây là app tự làm với chính nó — không phải ai
                // đó bơm cú bấm vào hệ thống.
                Task { @MainActor in
                    NSApp.activate(ignoringOtherApps: true)
                    NSApp.windows.first(where: { $0.isVisible && $0.canBecomeMain })?
                        .makeKeyAndOrderFront(nil)
                    try? await Task.sleep(nanoseconds: 400_000_000)
                    self.ghi(["su_kien": "da_len_truoc"])
                }
            case "sync":
                Task { @MainActor in
                    await s.veLai()
                    self.ghi(["su_kien": "da_sync"])
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
    /// Khung cửa sổ app trên màn hình, gốc TRÊN–TRÁI (đúng hệ trục `screencapture -R`).
    ///
    /// Có nó để bộ đo chụp được **đúng cửa sổ EIDE** thay vì cả màn hình. Lần đầu chụp toàn
    /// màn hình đã lọt vào ảnh: cửa sổ trò chuyện riêng của người dùng và tệp `.env` đang mở
    /// kèm khoá API. Một ảnh làm sở cứ không được mang theo thứ nó không cần.
    private func khungCuaSo() -> [String: Any] {
        guard let w = NSApp.windows.first(where: { $0.isVisible && $0.canBecomeMain }),
              let man = w.screen ?? NSScreen.main else { return [:] }
        let f = w.frame
        // AppKit đếm y từ ĐÁY màn hình; `screencapture -R` đếm từ ĐỈNH.
        let y = man.frame.maxY - f.maxY
        // `so` là CGWindowID: cho phép chụp ĐÚNG cửa sổ này (`screencapture -l`) kể cả khi
        // nó đang nằm dưới cửa sổ khác. Chụp theo VÙNG màn hình thì thứ nằm trên lọt vào
        // ảnh — đã xảy ra hai lần, và một lần trong đó là tệp `.env` của người dùng.
        return ["x": Int(f.origin.x.rounded()), "y": Int(y.rounded()),
                "rong": Int(f.width.rounded()), "cao": Int(f.height.rounded()),
                "so": Int(w.windowNumber)]
    }

    /// Bề rộng thật của từng khối sau khi vẽ, theo mã khối.
    private func rongKhoi() -> [String: Int] {
        guard let s = state else { return [:] }
        return s.khungKhoi.mapValues { Int($0.width.rounded()) }
    }

    /// Chiều cao thật của từng khối sau khi vẽ, theo mã khối.
    private func caoKhoi() -> [String: Int] {
        guard let s = state else { return [:] }
        return s.khungKhoi.mapValues { Int($0.height.rounded()) }
    }

    /// Cặp khối có khung giao nhau. Chỉ tính phần chồng ĐÁNG KỂ (> 4 pt mỗi chiều) để một
    /// pixel làm tròn không bị báo thành lỗi.
    ///
    /// **Giới hạn đã đo được, đừng tin quá vào con số này.** Nó so KHUNG KHAI BÁO của các
    /// khối. Lỗi tràn nội dung thật (bảng 256 dòng trong một `ScrollView` ngang vẽ ra ngoài
    /// khung của chính nó và phủ lên khối dưới) KHÔNG làm khung giao nhau — kiểm lại bằng
    /// cách cố tình bỏ giới hạn dòng: danh sách này vẫn rỗng. Thứ bắt được lỗi đó là
    /// `caoKhoi()` cộng với một ngưỡng, hoặc mắt người nhìn ảnh chụp.
    private func khoiDeNhau() -> [String] {
        guard let s = state else { return [] }
        let ds = s.khungKhoi.sorted { $0.key < $1.key }
        var ra: [String] = []
        for i in 0..<ds.count {
            for j in (i + 1)..<ds.count {
                let a = ds[i].value, b = ds[j].value
                let giao = a.intersection(b)
                if giao.width > 4 && giao.height > 4 {
                    ra.append("\(ds[i].key)↔\(ds[j].key)")
                }
            }
        }
        return ra
    }

    /// Trần của một trường chữ trong bản chụp. Nâng từ 3 000 lên 20 000.
    ///
    /// Lời tác tử dài hơn 3 000 ký tự là chuyện thường trong đề án này — một bản thiết kế
    /// kiến trúc hay một danh mục an toàn thì dài hơn thế nhiều.
    static let tranChu = 20_000

    /// Cắt một trường chữ, và khi phải cắt thì **GHI PHẦN ĐỦ RA TỆP** rồi để lại đường dẫn.
    ///
    /// Bản trước dùng thẳng `String(cuoi.prefix(3000))`. Câu trả lời dài hơn bị cắt giữa
    /// chừng, nên **nhật ký phiên chép thiếu** — hai lần trong phiên robot: danh mục an toàn
    /// và phần thiết kế phép đo dấu đều mất phần đuôi.
    ///
    /// Nhật ký là sở cứ. Một sở cứ cắt mất đoạn cuối thì **chỗ bị cắt luôn là chỗ không ai
    /// biết là đã mất** — không có dấu hiệu nào, câu cuối trông như một câu kết thúc bình
    /// thường. Nay ba thứ cùng lúc: trần cao hơn, dấu cắt hiện ra trong chính chuỗi, và tệp
    /// chứa bản đủ.
    func catVaGhiRa(_ s: String, ten: String) -> String {
        guard s.count > Self.tranChu else { return s }
        var duong = "(không ghi được ra tệp)"
        if let d = thuMuc {
            let u = d.appendingPathComponent("\(ten)-\(soLenh).txt")
            if (try? s.write(to: u, atomically: true, encoding: .utf8)) != nil {
                duong = u.lastPathComponent
            }
        }
        return String(s.prefix(Self.tranChu))
            + "\n\n⟨CẮT Ở \(Self.tranChu) KÝ TỰ — bản đủ \(s.count) ký tự ở \(duong)⟩"
    }

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
                // A5.8 — khối sơ đồ: phơi ra thứ người NHÌN THẤY (mấy trang, mấy ký hiệu bấm
                // được), để ca đo hỏi được "ảnh có rỗng không" thay vì chỉ đếm khối.
                "so_trang_svg": b.arr("tep").count,
                "so_ref_bam_duoc": b.arr("ref").count,
                "cot_sua_loai": b.str("loai_sua") ?? "",
                "ve_duoc": !(s.khoiChuaBietVe.contains(b.type)),
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

        var ra: [String: Any] = [
            "su_kien": "anh_chup",
            "khung_cua_so": khungCuaSo(),
            // Cặp khối có KHUNG giao nhau. Giữ lại vì rẻ, nhưng đọc kỹ giới hạn của nó ở
            // `khoiDeNhau()`: nó KHÔNG bắt được lỗi tràn nội dung.
            "khoi_de_nhau": khoiDeNhau(),
            // Chiều cao thật của từng khối. Đây mới là con số bắt được lỗi bảng dài: một
            // khối cao gấp nhiều lần cửa sổ là một khối không ai đọc hết được.
            "cao_khoi": caoKhoi(),
            // Bề RỘNG từng khối. Khối rộng hơn khung là khối đẩy các thứ bên phải ra ngoài
            // màn hình — người dùng mất luôn nút "Vì sao?" và không có cách nào cuộn tới.
            "rong_khoi": rongKhoi(), "nhan": nhan,
            // Đang ở màn NÀO. Không có trường này thì không phân biệt được "đã đóng dự án"
            // với "lệnh đóng chẳng làm gì" — hai thứ trông giống hệt nhau qua các số khác.
            "man_hinh": s.connection.ok ? "lam-viec" : "mo-du-an",
            "tab_dang_xem": s.selectedSurface,
            "tab_co_the_chon": s.surfaceOrder.map { $0.key },
            "be_rong_console": s.consoleWidth.nhan,
            "be_rong_console_px": Int(s.consoleWidth.rawValue),
            // Kiểu khối mà giao diện KHÔNG biết vẽ. Lõi sinh ra chúng thì người dùng nhận
            // một ô trống không lời giải thích, nên đây phải là một con số đọc được.
            "khoi_chua_biet_ve": Array(s.khoiChuaBietVe),
            "du_an_gan_day": s.duAnGanDay?() ?? [],
            "so_dong_hoi_thoai": s.transcript.count,
            // Số thẻ CÒN NÚT bấm được trong dòng hội thoại — đúng thứ `ConsoleView` vẽ
            // (`line.card != nil && !card.resolved`).
            //
            // Phải đếm riêng, vì `the_dang_cho` KHÔNG nói được điều này: `Card` là struct,
            // nên dòng hội thoại giữ một bản sao riêng và `cards[i].resolved = true` không
            // đụng tới nó. Đo được 28/09/2026: `the_dang_cho` báo 0 trong khi ảnh chụp cho
            // thấy thẻ vẫn còn hai nút Duyệt/Từ chối. Số đo đúng, câu hỏi sai — và chỉ tấm
            // ảnh mới bắt được.
            "so_the_con_nut": s.transcript.filter { ($0.card.map { !$0.resolved }) == true }.count,
            // Đếm riêng dòng của TÁC TỬ: bộ đo cần biết lượt vừa rồi nó có nói gì không.
            // Thiếu con số này, một lượt mà tác tử chỉ gọi công cụ rồi im lặng sẽ bị chép
            // lại bằng lời của lượt TRƯỚC — nhật ký thành sai mà trông vẫn hợp lý.
            "so_loi_tac_tu": loiTacTu.count,
            "loi_tac_tu_cuoi": catVaGhiRa(cuoi, ten: "loi-tac-tu"),
            "loi_tac_tu_do_dai": String(cuoi.count),
            // Chữ SAU KHI DỰNG — để hỏi được "trên màn hình còn dấu sao không".
            "loi_tac_tu_render": catVaGhiRa(Markdown.chuThuan(cuoi), ten: "loi-tac-tu-render"),
            "khoi_markdown": khoiMd,
            "the_dang_cho": theHien,
            "tab_dang_mo": s.selectedSurface,
            "tab_tieu_de": bm?.title ?? "",
            "khoi_tren_tab": khoi,
            // Xuất CẢ TỔNG SỐ, không chỉ năm thẻ cuối.
            //
            // Bản trước chỉ xuất `suffix(5)`. Nên dù màn hình có dồn một trăm thẻ, bộ quét
            // giao diện vẫn chỉ thấy năm — nó **không thể** phát hiện chuyện dồn đống, mãi
            // mãi. Đúng loại lỗi dự án này gặp đi gặp lại: cơ chế đo có sẵn, nhưng bị bịt
            // đúng chỗ cần thấy. Anh Công phải tự nhìn màn hình mới thấy, và phải nêu ra
            // bằng lời.
            //
            // `tong` cho đặt được ngưỡng. `tong_lan` đếm cả số lần của các thẻ đã gộp, nên
            // phân biệt được "năm cảnh báo khác nhau" với "một cảnh báo nổ năm mươi lần".
            "thong_bao": s.notices.suffix(5).map {
                ["muc": $0.level, "chu": $0.text, "so_lan": String($0.soLan)]
            },
            "thong_bao_tong": String(s.notices.count),
            "thong_bao_tong_lan": String(s.notices.reduce(0) { $0 + $1.soLan }),
            "trang_thai": [
                "du_an": s.status.du_an, "chip": s.status.chip,
                "chang": s.status.chang, "stale": s.status.stale,
                "fact": s.status.fact, "mo_hinh": s.status.mo_hinh,
                // Ngân sách và token: bộ đo phải hỏi được "con số có SỐNG giữa lượt không".
                // Lấy đúng thứ tự mà `NganSachView`/`TokenView` lấy — nếu không, bộ đo đo
                // một con đường khác với con đường người nhìn.
                "ngan_sach": [
                    "tool": s.status.ngan_sach.tool,
                    "giay": s.status.ngan_sach.giay,
                    "da_dung_tool": s.run?.status == "running"
                        ? (s.run?.tools ?? 0) : s.status.ngan_sach.da_dung_tool,
                    "da_dung_giay": s.run?.status == "running"
                        ? (s.run?.seconds ?? 0) : s.status.ngan_sach.da_dung_giay,
                ] as [String: Any],
                "token": [
                    "luot": s.run?.status == "running"
                        ? (s.run?.tokensIn ?? 0) + (s.run?.tokensOut ?? 0)
                        : s.status.token.luot,
                    "phien": s.status.token.phien,
                    "phien_vao": s.status.token.phien_vao,
                    "phien_ra": s.status.token.phien_ra,
                ] as [String: Any],
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
            ] as [String: Any],
            // KHÔNG nằm trong `trang_thai`: đây là dữ liệu cho bộ đo chứ không phải một ô
            // trên thanh. Để lẫn vào đó thì phép kiểm "ô nào bỏ trống câm" đọc nó như một ô
            // và báo lỗi mỗi khi không có lượt nào chạy — tức là lúc bình thường nhất.
            "run_trang_thai": s.run?.status ?? "",
            "dang_chay": s.busy,
        ]
        // `isa` chỉ vào bản chụp khi THẬT SỰ hiện trên thanh: `StatusBarView` giấu nhãn này
        // khi chưa ghim hộ chiếu chip. Một chuỗi rỗng ở đây đọc ra thành "một ô đang bỏ
        // trống câm", tức bộ quét báo một lỗi không có thật.
        if var tt = ra["trang_thai"] as? [String: Any],
           let isa = s.status.isa, !isa.isEmpty {
            tt["isa"] = isa
            ra["trang_thai"] = tt
        }
        return ra
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
        // Phân biệt "sơ-đồ" với "khối-mã" là điều kiện để BỘ QUÉT đo được việc mermaid đã
        // thành hình hay còn nằm dạng mã. Không có tên riêng thì không có phép đo.
        case .soDo: return "sơ-đồ"
        }
    }

    // MARK: - Ghi ra

    /// Đo bộ dựng trên một đoạn markdown bất kỳ. Xem lệnh `so_do_thu`.
    private func soDoThu(_ md: String) -> [String: Any] {
        let khoi = Markdown.tach(md)
        var soDo: [[String: Any]] = []
        for k in khoi {
            guard case .soDo(let nguon) = k else { continue }
            let d = DocSoDo.doc(nguon)
            soDo.append([
                "kieu": DocSoDo.kieu(nguon),
                "ve_duoc": d != nil,
                "tom_tat": d?.tomTat ?? "",
                "nhan": DocSoDo.nhanNguoiThay(nguon)
                    .components(separatedBy: .newlines).filter { !$0.isEmpty },
            ])
        }
        return ["su_kien": "so_do_thu", "khoi": khoi.map(tenKhoi), "so_do": soDo,
                "chu_thuan": Markdown.chuThuan(md)]
    }

    /// Vẽ khối sơ đồ ra tệp PNG.
    @MainActor
    private func anhSoDo(md: String, tep: String) -> [String: Any] {
        let nguon = Markdown.tach(md).compactMap { k -> String? in
            if case .soDo(let n) = k { return n }
            return nil
        }
        guard let dau = nguon.first else {
            return ["su_kien": "anh_so_do", "tep": "", "vi_sao": "không có khối mermaid nào"]
        }
        let r = ImageRenderer(content: SoDoHinh(nguon: dau).padding(12))
        r.scale = 2
        guard let anh = r.nsImage,
              let tiff = anh.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff),
              let png = rep.representation(using: .png, properties: [:]) else {
            return ["su_kien": "anh_so_do", "tep": "", "vi_sao": "không dựng được ảnh"]
        }
        let u = URL(fileURLWithPath: tep)
        try? FileManager.default.createDirectory(at: u.deletingLastPathComponent(),
                                                 withIntermediateDirectories: true)
        try? png.write(to: u)
        return ["su_kien": "anh_so_do", "tep": tep]
    }

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

    /// Phím tắt dạng người đọc: ⌘⇧W thay vì "w" + một bitmask.
    private func moTaPhim(_ x: NSMenuItem) -> String {
        var t = ""
        if x.keyEquivalentModifierMask.contains(.control) { t += "⌃" }
        if x.keyEquivalentModifierMask.contains(.option) { t += "⌥" }
        if x.keyEquivalentModifierMask.contains(.shift) { t += "⇧" }
        if x.keyEquivalentModifierMask.contains(.command) { t += "⌘" }
        return t + x.keyEquivalent.uppercased()
    }

}
