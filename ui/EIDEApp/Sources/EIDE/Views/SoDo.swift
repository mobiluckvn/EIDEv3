import Foundation

/// Đọc khối ```mermaid thành sơ đồ VẼ ĐƯỢC.
///
/// ## Vì sao tự đọc, không nhúng mermaid.js
///
/// Cách nhanh nhất là nhét một `WKWebView` kèm `mermaid.js` vào mỗi khối. Không chọn, vì ba lẽ,
/// và lẽ thứ ba là lẽ nặng nhất:
///
/// * EIDE **không mở cổng mạng nào** và chạy được khi máy không có Internet. Một thư viện web
///   kéo về lúc chạy phá ràng buộc ấy; đóng gói sẵn ~1 MB JavaScript thì thành một thứ nữa
///   phải theo dõi phiên bản, mà không ai trong dự án này đọc nổi nó.
/// * Mỗi ô hội thoại một `WKWebView` là một tiến trình trình duyệt. Một phiên có hàng chục ô.
/// * Mermaid vẽ được vài chục kiểu sơ đồ; EIDE sinh ra **hai**. Đo ngày 29/09/2026 trên toàn
///   bộ `docs/` và `du-lieu/`: **8 `graph`** (do `ckm.mermaid()` của lõi sinh, nên còn dài dài)
///   và **1 `sequenceDiagram`** (tác tử viết). Không có kiểu nào khác. Dựng một cỗ máy đa dụng
///   cho hai ca đã biết là trả giá cho thứ không dùng tới.
///
/// ## Cái giá, nói ra chứ không giấu
///
/// Bố cục ở đây **không giống hệt mermaid** — nó là cách sắp riêng, đủ đọc. Và tập con thì có
/// biên: gặp kiểu chưa vẽ được (`classDiagram`, `stateDiagram`, `gantt`…) thì trả `nil`, và
/// khối hiện nguyên mã **kèm một câu nói rõ giao diện chưa vẽ kiểu ấy**. Im lặng hiện mã thô
/// là để người dùng tự đoán xem app hỏng hay sơ đồ sai — mà đoán thì thường đoán nhầm.

// MARK: - Mô hình

enum SoDo {
    case tuanTu(SoDoTuanTu)
    case luong(SoDoLuong)

    /// Câu mô tả ngắn cho thanh tiêu đề của khối — người đọc biết ngay đang xem gì.
    var tomTat: String {
        switch self {
        case .tuanTu(let t):
            return "Sơ đồ tuần tự · \(t.vai.count) vai · \(t.soBuoc) bước"
        case .luong(let l):
            return "Sơ đồ khối · \(l.nut.count) khối · \(l.canh.count) nối"
        }
    }
}

/// Nét vẽ của một mũi tên. Ba trạng thái, không hai: mermaid phân biệt nét liền (lời gọi) với
/// nét đứt (lời đáp), và gộp chúng lại là làm mất đúng thứ người đọc sơ đồ tuần tự cần thấy.
enum NetVe {
    case lien
    case dut
    case dam
}

// MARK: - Sơ đồ tuần tự

struct SoDoTuanTu {
    struct Vai: Identifiable {
        let ma: String
        let nhan: String
        /// `actor` vẽ hình người; `participant` vẽ hộp. Mermaid phân biệt, nên ở đây cũng thế.
        let laNguoi: Bool
        var id: String { ma }
    }

    enum Dong {
        case tin(tu: Int, den: Int, chu: String, net: NetVe)
        case ghiChu(tu: Int, den: Int, chu: String)
        case moKhoi(loai: String, nhan: String)
        case nhanhKhac(nhan: String)
        case dongKhoi
    }

    let vai: [Vai]
    let dong: [Dong]
    let danhSo: Bool

    var soBuoc: Int {
        dong.reduce(0) { n, d in if case .tin = d { return n + 1 }; return n }
    }
}

// MARK: - Sơ đồ khối

struct SoDoLuong {
    enum Hinh {
        case hop            // A["..."]
        case bau            // A("...")
        case tron           // A(("..."))
        case thoi           // A{"..."}
    }

    struct Nut: Identifiable {
        let ma: String
        let nhan: String
        let hinh: Hinh
        /// Chỉ số cụm (`subgraph`) chứa nút này, hoặc `nil`.
        let cum: Int?
        var id: String { ma }
    }

    struct Canh {
        let tu: Int
        let den: Int
        let nhan: String
        let net: NetVe
    }

    struct Cum: Identifiable {
        let nhan: String
        var id: String { nhan }
    }

    /// `true` khi sơ đồ chảy từ trái sang phải (`LR`/`RL`); `false` là trên xuống (`TB`/`TD`).
    let ngang: Bool
    let nut: [Nut]
    let canh: [Canh]
    let cum: [Cum]
}

// MARK: - Bộ đọc

enum DocSoDo {

    /// Tên kiểu sơ đồ ở dòng đầu — dùng cả khi KHÔNG vẽ được, để nói đúng tên thứ chưa vẽ.
    static func kieu(_ nguon: String) -> String {
        for d in nguon.components(separatedBy: .newlines) {
            let t = d.trimmingCharacters(in: .whitespaces)
            if t.isEmpty || t.hasPrefix("%%") { continue }
            return String(t.split(separator: " ").first ?? "")
        }
        return ""
    }

    /// `nil` = kiểu này giao diện chưa vẽ được. Gọi nơi gọi phải hiện mã kèm lời giải thích.
    static func doc(_ nguon: String) -> SoDo? {
        switch kieu(nguon) {
        case "sequenceDiagram":
            return tuanTu(nguon).map(SoDo.tuanTu)
        case "graph", "flowchart":
            return luong(nguon).map(SoDo.luong)
        default:
            return nil
        }
    }

    // MARK: Tuần tự

    static func tuanTu(_ nguon: String) -> SoDoTuanTu? {
        var vai: [SoDoTuanTu.Vai] = []
        var chiSo: [String: Int] = [:]
        var dong: [SoDoTuanTu.Dong] = []
        var danhSo = false
        var sauKhoi = 0                      // để bỏ `end` thừa, không cho nó làm vỡ khung

        /// Vai chưa khai vẫn dùng được — mermaid tạo ngầm khi gặp lần đầu, và tác tử có lúc
        /// viết thẳng `A->>B:` mà quên khai. Nuốt mất một vai là mất một cột.
        func viTri(_ ma: String, nguoi: Bool = false, nhan: String? = nil) -> Int {
            let m = ma.trimmingCharacters(in: .whitespaces)
            if let i = chiSo[m] {
                if let n = nhan, vai[i].nhan == vai[i].ma {
                    vai[i] = .init(ma: m, nhan: n, laNguoi: vai[i].laNguoi || nguoi)
                }
                return i
            }
            vai.append(.init(ma: m, nhan: nhan ?? m, laNguoi: nguoi))
            chiSo[m] = vai.count - 1
            return vai.count - 1
        }

        for raw in nguon.components(separatedBy: .newlines) {
            let d = raw.trimmingCharacters(in: .whitespaces)
            if d.isEmpty || d.hasPrefix("%%") || d == "sequenceDiagram" { continue }
            if d == "autonumber" { danhSo = true; continue }
            if d.hasPrefix("activate ") || d.hasPrefix("deactivate ") { continue }

            if d.hasPrefix("participant ") || d.hasPrefix("actor ") {
                let nguoi = d.hasPrefix("actor ")
                let than = String(d.dropFirst(nguoi ? 6 : 12))
                if let r = than.range(of: " as ") {
                    _ = viTri(String(than[..<r.lowerBound]), nguoi: nguoi,
                              nhan: goThe(String(than[r.upperBound...])))
                } else {
                    _ = viTri(than, nguoi: nguoi)
                }
                continue
            }

            if d == "end" {
                if sauKhoi > 0 { sauKhoi -= 1; dong.append(.dongKhoi) }
                continue
            }
            if let (loai, nhan) = moKhoi(d) {
                sauKhoi += 1
                dong.append(.moKhoi(loai: loai, nhan: nhan))
                continue
            }
            if d == "else" || d.hasPrefix("else ") {
                dong.append(.nhanhKhac(nhan: goThe(String(d.dropFirst(4)))))
                continue
            }
            if d == "and" || d.hasPrefix("and ") {
                dong.append(.nhanhKhac(nhan: goThe(String(d.dropFirst(3)))))
                continue
            }

            if d.hasPrefix("Note ") || d.hasPrefix("note ") {
                if let g = ghiChu(String(d.dropFirst(5)), viTri) { dong.append(g) }
                continue
            }

            if let t = tinNhan(d, viTri) { dong.append(t) }
        }

        guard !vai.isEmpty, dong.contains(where: { if case .tin = $0 { return true }
                                                  return false }) else { return nil }
        // Khối chưa đóng thì đóng hộ ở cuối — một nguồn viết dở không nên làm mất cả hình.
        for _ in 0..<sauKhoi { dong.append(.dongKhoi) }
        return SoDoTuanTu(vai: vai, dong: dong, danhSo: danhSo)
    }

    private static let TU_KHOI = ["loop", "alt", "opt", "par", "critical", "break", "rect"]

    private static func moKhoi(_ d: String) -> (String, String)? {
        for k in TU_KHOI where d == k || d.hasPrefix(k + " ") {
            return (k, goThe(String(d.dropFirst(k.count))))
        }
        return nil
    }

    private static func ghiChu(_ than: String,
                               _ viTri: (String, Bool, String?) -> Int) -> SoDoTuanTu.Dong? {
        guard let hai = than.range(of: ":") else { return nil }
        let dau = String(than[..<hai.lowerBound]).trimmingCharacters(in: .whitespaces)
        let chu = goThe(String(than[hai.upperBound...]))
        let ds: String
        if dau.hasPrefix("over ") { ds = String(dau.dropFirst(5)) }
        else if dau.hasPrefix("left of ") { ds = String(dau.dropFirst(8)) }
        else if dau.hasPrefix("right of ") { ds = String(dau.dropFirst(9)) }
        else { ds = dau }
        let cot = ds.split(separator: ",").map {
            viTri($0.trimmingCharacters(in: .whitespaces), false, nil)
        }
        guard let a = cot.first else { return nil }
        return .ghiChu(tu: a, den: cot.last ?? a, chu: chu)
    }

    /// Mũi tên mermaid, xếp DÀI TRƯỚC NGẮN.
    ///
    /// Thứ tự này không phải chuyện thẩm mỹ: `->>` là tiền tố của `-->>` khi dò từ trái, nên
    /// dò `->` trước sẽ cắt `-->>` thành `--` + `>>` và mọi lời đáp thành lời gọi.
    private static let MUI: [(String, NetVe)] = [
        ("-->>", .dut), ("--x", .dut), ("--)", .dut), ("-->", .dut),
        ("->>", .lien), ("-x", .lien), ("-)", .lien), ("->", .lien),
    ]

    private static func tinNhan(_ d: String,
                                _ viTri: (String, Bool, String?) -> Int) -> SoDoTuanTu.Dong? {
        guard let hai = d.range(of: ":") else { return nil }
        let dauCau = String(d[..<hai.lowerBound])
        let chu = goThe(String(d[hai.upperBound...]))
        for (m, net) in MUI {
            guard let r = dauCau.range(of: m) else { continue }
            let tu = String(dauCau[..<r.lowerBound]).trimmingCharacters(in: .whitespaces)
            let den = String(dauCau[r.upperBound...]).trimmingCharacters(in: .whitespaces)
            guard !tu.isEmpty, !den.isEmpty else { return nil }
            return .tin(tu: viTri(tu, false, nil), den: viTri(den, false, nil),
                        chu: chu, net: net)
        }
        return nil
    }

    // MARK: Sơ đồ khối

    static func luong(_ nguon: String) -> SoDoLuong? {
        var nut: [SoDoLuong.Nut] = []
        var chiSo: [String: Int] = [:]
        var canh: [SoDoLuong.Canh] = []
        var cum: [SoDoLuong.Cum] = []
        var cumHienTai: Int?
        var ngang = true

        func ghiNut(_ ma: String, nhan: String?, hinh: SoDoLuong.Hinh?) -> Int {
            let m = ma.trimmingCharacters(in: .whitespaces)
            if let i = chiSo[m] {
                // Nhãn khai sau thì vẫn nhận: `A --> B` rồi mới `B["Tên"]` là cách viết thường.
                if let n = nhan {
                    nut[i] = .init(ma: m, nhan: n, hinh: hinh ?? nut[i].hinh, cum: nut[i].cum)
                }
                return i
            }
            nut.append(.init(ma: m, nhan: nhan ?? m, hinh: hinh ?? .hop, cum: cumHienTai))
            chiSo[m] = nut.count - 1
            return nut.count - 1
        }

        for raw in nguon.components(separatedBy: .newlines) {
            var d = raw.trimmingCharacters(in: .whitespaces)
            if let c = d.range(of: "%%") { d = String(d[..<c.lowerBound])
                                           .trimmingCharacters(in: .whitespaces) }
            if d.isEmpty { continue }

            if d.hasPrefix("graph ") || d.hasPrefix("flowchart ") {
                let h = d.split(separator: " ").last.map(String.init) ?? "LR"
                ngang = h.hasPrefix("L") || h.hasPrefix("R")
                continue
            }
            // Câu trang trí: không đổi cấu trúc, nên bỏ qua chứ không coi là lỗi.
            if d.hasPrefix("classDef ") || d.hasPrefix("class ") || d.hasPrefix("style ")
                || d.hasPrefix("click ") || d.hasPrefix("linkStyle ") { continue }

            if d.hasPrefix("subgraph") {
                let than = String(d.dropFirst(8)).trimmingCharacters(in: .whitespaces)
                cum.append(.init(nhan: goThe(nhanTrongNgoac(than) ?? than)))
                cumHienTai = cum.count - 1
                continue
            }
            if d == "end" { cumHienTai = nil; continue }

            if let c = docCanh(d, ghiNut) { canh.append(contentsOf: c); continue }
            if let (ma, nhan, hinh) = docKhaiNut(d) { _ = ghiNut(ma, nhan: nhan, hinh: hinh) }
        }

        guard !nut.isEmpty else { return nil }
        return SoDoLuong(ngang: ngang, nut: nut, canh: canh, cum: cum)
    }

    /// Mũi tên sơ đồ khối. Lại xếp dài trước ngắn, cùng lý do với mũi tên tuần tự.
    /// Mũi tên sơ đồ khối. Hai chiều đứng trước một chiều, vì `<-->` chứa `-->`.
    ///
    /// Thiếu chúng thì `A <--> B` bị cắt ở `-->`, phần trái còn lại là `"A <"` — có dấu cách
    /// nên không khớp mẫu khai nút, rơi xuống nhánh mặc định và **đẻ ra một khối tên
    /// `MOD_MCU <`**. Nhìn thấy trong app ngày 29/09/2026 trên sơ đồ tác tử vừa vẽ.
    private static let NOI: [(String, NetVe)] = [
        ("<-.->", .dut), ("<-->", .lien), ("<==>", .dam),
        ("-.->", .dut), ("-.-", .dut), ("==>", .dam), ("===", .dam),
        ("-->", .lien), ("---", .lien), ("->", .lien),
    ]

    /// Một dòng có thể chứa chuỗi nhiều nối: `A --> B --> C`. Trả về từng cặp.
    private static func docCanh(_ d: String,
                                _ ghiNut: (String, String?, SoDoLuong.Hinh?) -> Int)
        -> [SoDoLuong.Canh]? {
        var con = d
        var doan: [String] = []
        var net: [NetVe] = []
        while true {
            var som: (Range<String.Index>, NetVe)?
            for (m, n) in NOI {
                if let r = con.range(of: m) {
                    if som == nil || r.lowerBound < som!.0.lowerBound { som = (r, n) }
                }
            }
            guard let (r, n) = som else { break }
            doan.append(String(con[..<r.lowerBound]))
            net.append(n)
            con = String(con[r.upperBound...])
        }
        guard !doan.isEmpty else { return nil }
        doan.append(con)

        var ra: [SoDoLuong.Canh] = []
        var truoc: Int?
        for (i, phanTu) in doan.enumerated() {
            // `|nhãn|` dính ngay sau mũi tên, tức ở ĐẦU đoạn kế.
            var t = phanTu.trimmingCharacters(in: .whitespaces)
            var nhan = ""
            if t.hasPrefix("|"), let dong = t.dropFirst().firstIndex(of: "|") {
                nhan = goThe(String(t[t.index(after: t.startIndex)..<dong]))
                t = String(t[t.index(after: dong)...]).trimmingCharacters(in: .whitespaces)
            }
            guard !t.isEmpty else { truoc = nil; continue }
            let (ma, nh, hinh) = docKhaiNut(t) ?? (t, nil, nil)
            let vt = ghiNut(ma, nh, hinh)
            if let tr = truoc, i > 0 {
                ra.append(.init(tu: tr, den: vt, nhan: nhan, net: net[i - 1]))
            }
            truoc = vt
        }
        return ra.isEmpty ? nil : ra
    }

    /// `A["Nhãn"]` · `A("Nhãn")` · `A(("Nhãn"))` · `A{"Nhãn"}` → (mã, nhãn, hình).
    private static func docKhaiNut(_ d: String) -> (String, String?, SoDoLuong.Hinh?)? {
        let boc: [(String, String, SoDoLuong.Hinh)] = [
            ("((", "))", .tron), ("{{", "}}", .thoi), ("[", "]", .hop),
            ("(", ")", .bau), ("{", "}", .thoi),
        ]
        for (mo, dong, hinh) in boc {
            guard let r = d.range(of: mo), d.hasSuffix(dong) else { continue }
            let ma = String(d[..<r.lowerBound]).trimmingCharacters(in: .whitespaces)
            guard !ma.isEmpty, ma.rangeOfCharacter(from: .whitespaces) == nil else { continue }
            let trong = String(d[r.upperBound...].dropLast(dong.count))
            return (ma, goThe(trong), hinh)
        }
        let ma = d.trimmingCharacters(in: .whitespaces)
        guard !ma.isEmpty, ma.rangeOfCharacter(from: .whitespaces) == nil else { return nil }
        return (ma, nil, nil)
    }

    private static func nhanTrongNgoac(_ s: String) -> String? {
        guard let a = s.firstIndex(of: "["), s.hasSuffix("]") else { return nil }
        return String(s[s.index(after: a)...].dropLast())
    }

    /// Bỏ nháy bọc và đổi `<br/>` thành xuống dòng.
    ///
    /// `<br/>` là cách duy nhất xuống dòng trong nhãn mermaid, và tác tử dùng nó rất nhiều —
    /// để nguyên thì nhãn thành một dòng dài kèm mấy chữ `<br/>` nằm giữa.
    static func goThe(_ s: String) -> String {
        var t = s.trimmingCharacters(in: .whitespaces)
        if t.count >= 2, t.hasPrefix("\""), t.hasSuffix("\"") { t = String(t.dropFirst().dropLast()) }
        for the in ["<br/>", "<br>", "<br />"] {
            t = t.replacingOccurrences(of: the, with: "\n")
        }
        return t.replacingOccurrences(of: "&nbsp;", with: " ")
            .trimmingCharacters(in: .whitespaces)
    }
}

// MARK: - Chữ mà người thật sự nhìn thấy

extension DocSoDo {
    /// Mọi nhãn hiện trên HÌNH, mỗi nhãn một dòng.
    ///
    /// Dùng cho `Markdown.chuThuan` — hàm mà bộ quét giao diện hỏi "trên màn hình còn dấu sao
    /// không". Trả cả mã mermaid ở đó sẽ sai hai đường: mã có `-->` và `["..."]` mà người
    /// không nhìn thấy, còn nhãn tiếng Việt thì lẫn trong cú pháp. Vẽ cái gì thì kể cái đó.
    static func nhanNguoiThay(_ nguon: String) -> String {
        switch doc(nguon) {
        case .tuanTu(let t):
            var ra = t.vai.map(\.nhan)
            for d in t.dong {
                switch d {
                case .tin(_, _, let chu, _): ra.append(chu)
                case .ghiChu(_, _, let chu): ra.append(chu)
                case .moKhoi(let loai, let nhan): ra.append(nhan.isEmpty ? loai : "\(loai) \(nhan)")
                case .nhanhKhac(let nhan): ra.append(nhan)
                case .dongKhoi: break
                }
            }
            return ra.joined(separator: "\n")
        case .luong(let l):
            return (l.cum.map(\.nhan) + l.nut.map(\.nhan)
                    + l.canh.map(\.nhan).filter { !$0.isEmpty }).joined(separator: "\n")
        case nil:
            // Chưa vẽ được thì người ĐANG nhìn thấy mã thật — nên trả mã.
            return nguon
        }
    }
}
