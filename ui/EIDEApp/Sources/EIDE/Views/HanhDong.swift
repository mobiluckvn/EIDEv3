import SwiftUI

/// Một cái NÚT do LÕI khai — EIDE-EDIT-47 §DEV-373.
///
/// Cùng tinh thần với `SuaDuoc` (I8) nhưng cho **việc làm** thay vì cho ô sửa: lõi nói rõ
/// bấm vào thì gửi HumanAct nào, kèm `target`/`data`/`text`. Giao diện chỉ thay chỗ
/// `{ma}`/`{loai}` theo dòng rồi gửi.
///
/// Vì sao không để giao diện tự soạn: nó đã tự soạn ở hai chỗ khác (nút "Giải thích thêm",
/// bộ lọc tác giả) và cả hai lần đều ổn vì thông điệp đơn giản. Với "cập nhật hạ nguồn"
/// thì không: lõi biết danh sách hiện vật lỗi thời, lý do lỗi thời, và công cụ dựng lại
/// từng loại — còn giao diện thì không biết gì trong ba thứ ấy.
struct HanhDong {
    let raw: JSONValue
    init(_ raw: JSONValue) { self.raw = raw }

    var ma: String { raw["ma"]?.stringValue ?? "" }
    var nhan: String { raw["nhan"]?.stringValue ?? "" }
    var kind: String { raw["kind"]?.stringValue ?? "say" }
    /// `"dong"` — một nút mỗi dòng; `"khoi"` — một nút cho cả khối.
    var muc: String { raw["muc"]?.stringValue ?? "dong" }
    var giaiThich: String { raw["giai_thich"]?.stringValue ?? "" }
    /// Bấm vào là một lượt mô hình. Lõi nói trước; đừng để người phát hiện qua hoá đơn.
    var tonToken: Bool { raw["ton_token"]?.boolValue ?? false }
    /// Giao diện phải hỏi lý do và đặt vào `note` TRƯỚC khi gửi.
    var canLyDo: Bool { raw["can_ly_do"]?.boolValue ?? false }

    /// HumanAct để gửi, với `{ma}`/`{loai}` đã thay theo dòng.
    ///
    /// `nil` khi lõi khai một `kind` cần `target` mà dòng không có mã — thà không gửi gì
    /// còn hơn gửi một thông điệp trỏ vào hiện vật rỗng.
    func act(ma rowMa: String, loai: String, khoi: String, surface: String,
             lyDo: String) -> HumanAct? {
        func thay(_ s: String) -> String {
            s.replacingOccurrences(of: "{ma}", with: rowMa)
                .replacingOccurrences(of: "{loai}", with: loai)
        }
        var target: HumanAct.Target?
        if let t = raw["target"]?.objectValue {
            let id = thay(t["id"]?.stringValue ?? "")
            if id.isEmpty { return nil }
            target = .init(type: thay(t["type"]?.stringValue ?? ""), id: id)
        }
        var data: [String: JSONValue] = [:]
        for (k, v) in raw["data"]?.objectValue ?? [:] {
            data[k] = Self.thayTrong(v, thay: thay)
        }
        guard let kindEnum = HumanAct.Kind(rawValue: kind) else { return nil }
        return HumanAct(kind: kindEnum,
                        text: thay(raw["text"]?.stringValue ?? ""),
                        target: target, data: data,
                        origin: .init(surface: surface, block: khoi,
                                      row: rowMa.isEmpty ? nil : rowMa),
                        note: lyDo.isEmpty ? nil : lyDo)
    }

    /// Thay chỗ trong giá trị JSON lồng — `{"hien_vat": ["{ma}"]}` phải ra mã thật.
    static func thayTrong(_ v: JSONValue, thay: (String) -> String) -> JSONValue {
        switch v {
        case .string(let s): return .string(thay(s))
        case .array(let a): return .array(a.map { thayTrong($0, thay: thay) })
        case .object(let o): return .object(o.mapValues { thayTrong($0, thay: thay) })
        default: return v
        }
    }
}

/// Nút vẽ từ một `HanhDong`. Hỏi lý do trước khi gửi, nếu lõi đòi.
struct NutHanhDong: View {
    @EnvironmentObject var state: AppState
    let hd: HanhDong
    let ma: String
    let loai: String
    let khoi: String

    @State private var hoiLyDo = false
    @State private var lyDo = ""

    var body: some View {
        Button {
            if hd.canLyDo {
                lyDo = ""
                hoiLyDo = true
            } else {
                gui(lyDo: "")
            }
        } label: {
            HStack(spacing: 3) {
                Text(hd.nhan).font(.system(size: 10))
                if hd.tonToken {
                    Image(systemName: "bolt.fill").font(.system(size: 7))
                        .foregroundStyle(Color.staleAmber)
                }
            }
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.accentColor)
        .help(hd.giaiThich.isEmpty
              ? (hd.tonToken ? "Bấm vào là một lượt mô hình — có tốn token"
                             : "Lõi làm bằng mã, không tốn token")
              : hd.giaiThich + (hd.tonToken ? " · Có tốn token." : " · 0 token."))
        .popover(isPresented: $hoiLyDo, arrowEdge: .bottom) {
            VStack(alignment: .leading, spacing: 8) {
                Text(ma.isEmpty ? hd.nhan : "\(hd.nhan) — \(ma)")
                    .font(.system(size: 12, weight: .semibold))
                if !hd.giaiThich.isEmpty {
                    Text(hd.giaiThich).font(.system(size: 10))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                TextField("vì sao? (bắt buộc — đây là câu anh đọc lại sáu tháng sau)",
                          text: $lyDo)
                    .textFieldStyle(.roundedBorder).font(.system(size: 11))
                    .frame(width: 330)
                HStack {
                    Spacer()
                    Button("Bỏ") { hoiLyDo = false }.buttonStyle(.plain)
                        .font(.system(size: 11)).foregroundStyle(.secondary)
                    Button("Gửi") {
                        gui(lyDo: lyDo)
                        hoiLyDo = false
                    }
                    .keyboardShortcut(.defaultAction)
                    .disabled(lyDo.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
            .padding(14)
        }
    }

    private func gui(lyDo: String) {
        if let act = hd.act(ma: ma, loai: loai, khoi: khoi,
                            surface: state.selectedSurface, lyDo: lyDo) {
            state.gui(act)
        }
    }
}
