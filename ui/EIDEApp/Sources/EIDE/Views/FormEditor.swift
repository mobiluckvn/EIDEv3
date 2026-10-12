import SwiftUI

/// Đặc tả "ô nào sửa được" do LÕI gửi kèm mỗi khối — bất biến I8 (EIDE-EDIT-47 §3.2).
///
/// Giao diện **không suy ra từ tên cột**. Trước gói DEV-368 nó suy: `cot_sua` là một bảng
/// *tên cột → tên trường*, nên chỉ nói được về trường cấp một, và bốn bảng dùng được cách
/// ấy trong khi khoảng ba mươi loại hiện vật thì không.
struct SuaDuoc {
    let raw: JSONValue

    /// `target.type` khi gửi `edit`.
    var loai: String { raw["loai"]?.stringValue ?? "" }
    /// `row` — mỗi dòng một hiện vật; `block` — cả khối là một hiện vật.
    var idTu: String { raw["id_tu"]?.stringValue ?? "row" }
    var themXoa: JSONValue? { raw["them_xoa"] }
    /// `"set"` — ô này không phải hiện vật trong kho, nên gửi `set{key,value}` chứ không
    /// gửi `edit{patch}`; `path` của trường chính là tên `key` (§DEV-371).
    var guiBang: String { raw["gui_bang"]?.stringValue ?? "edit" }
    var bacBoDuoc: Bool { raw["bac_bo_duoc"]?.boolValue ?? false }
    var xacNhanDuoc: Bool { raw["xac_nhan_duoc"]?.boolValue ?? false }
    var truong: [Truong] { (raw["truong"]?.arrayValue ?? []).map(Truong.init) }

    init?(_ v: JSONValue?) {
        guard let v, !v.objectValue.isEmpty else { return nil }
        raw = v
    }

    struct Truong {
        let raw: JSONValue
        init(_ raw: JSONValue) { self.raw = raw }

        var path: String { raw["path"]?.stringValue ?? "" }
        var cot: String { raw["cot"]?.stringValue ?? "" }
        var kieu: String { raw["kieu"]?.stringValue ?? "chu" }
        var donVi: String { raw["don_vi"]?.stringValue ?? "" }
        var batBuoc: Bool { raw["bat_buoc"]?.boolValue ?? false }
        var goiY: String { raw["goi_y"]?.stringValue ?? "" }
        var canNguon: Bool { raw["can_nguon"]?.boolValue ?? false }
        var luaChon: [String] { (raw["lua_chon"]?.arrayValue ?? []).compactMap(\.stringValue) }
        /// Ô này nằm ở DÒNG có cột đầu bằng chuỗi này (bảng mỗi dòng là một trường).
        var dong: String { raw["dong"]?.stringValue ?? "" }

        /// Đường dẫn thật cho một dòng cụ thể. Hai chỗ thay là hợp đồng với lõi
        /// (`surfaces.truong`): `{row}` = chỉ số dòng, `{ma}` = cột đầu của dòng.
        func duong(row: Int, ma: String) -> String {
            path.replacingOccurrences(of: "{row}", with: String(row))
                .replacingOccurrences(of: "{ma}", with: ma)
        }
    }
}

/// Trình soạn biểu mẫu — sửa NHIỀU ô của một dòng rồi lưu MỘT lần.
///
/// Vì sao gom: mỗi ô một `edit` thì một dòng bốn trường thành bốn changeset, bốn dòng
/// trong tab Lịch sử, và bốn lần hạ nguồn bị đánh STALE cho cùng một việc. Gom lại còn
/// đúng một `patch` — và `patch` là thứ lõi áp nguyên tử (I9: không có "lưu một nửa").
struct FormEditor: View {
    @EnvironmentObject var state: AppState
    @Environment(\.dismiss) private var dong

    let sd: SuaDuoc
    /// Hiện vật đích và phiên bản của nó — lõi khai, đây không tự suy.
    ///
    /// `idHienVat` giữ NGUYÊN VĂN mã trong kho (`criteria:sim-01`, `FR-01`). Tách nó ra
    /// khỏi `loai` chứ không ghép thành một chuỗi rồi tách lại: mã trong kho của mấy loại
    /// hiện vật ĐÃ mang sẵn tiền tố, nên tách theo dấu hai chấm sẽ cắt mất một nửa mã và
    /// lõi đi tìm một hiện vật không tồn tại.
    let idHienVat: String
    let phienBan: Int
    /// Chỉ số dòng trong khối, và mã dòng (cột đầu).
    let row: Int
    let ma: String
    /// Giá trị đang có, theo tên cột.
    let dangCo: [String: String]
    var khoi: String = ""
    var surface: String = "project"

    @State private var moi: [String: String] = [:]
    @State private var nguon: [String: String] = [:]
    @State private var viSao = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Sửa \(ma.isEmpty ? idHienVat : ma)")
                .font(.system(size: 15, weight: .semibold))
            Text("Thay đổi của anh thành một changeset hoàn tác được. Lưu một lần cho cả "
                 + "biểu mẫu — không phải mỗi ô một lần.")
                .font(.system(size: 11)).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(sd.truong.enumerated()), id: \.offset) { _, t in
                        oSua(t)
                    }
                }
            }
            .frame(maxHeight: 360)

            TextField("vì sao anh đổi? (tuỳ chọn, nhưng lượt sau anh sẽ cảm ơn chính mình)",
                      text: $viSao)
                .textFieldStyle(.roundedBorder).font(.system(size: 11))

            HStack {
                Spacer()
                Button("Bỏ") { dong() }
                Button("Lưu") {
                    if luu() { dong() }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(!doiGiDo || thieuBatBuoc)
            }
        }
        .padding(18).frame(width: 520)
        .onAppear { moi = dangCo }
    }

    @ViewBuilder private func oSua(_ t: SuaDuoc.Truong) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 4) {
                Text(t.cot).font(.system(size: 11, weight: .medium))
                if t.batBuoc {
                    Text("*").foregroundStyle(Color.gateRed)
                }
                if !t.donVi.isEmpty {
                    Text(t.donVi).font(.system(size: 10)).foregroundStyle(.tertiary)
                }
                Spacer()
            }
            switch t.kieu {
            case "bool":
                Toggle(isOn: Binding(
                    get: { (moi[t.cot] ?? "").lowercased() == "có" || moi[t.cot] == "true" },
                    set: { moi[t.cot] = $0 ? "true" : "false" })) { Text("") }
                    .toggleStyle(.switch).labelsHidden()
            case "chon":
                Picker("", selection: Binding(
                    get: { moi[t.cot] ?? "" },
                    set: { moi[t.cot] = $0 })) {
                        Text("—").tag("")
                        ForEach(t.luaChon, id: \.self) { Text($0).tag($0) }
                    }
                    .labelsHidden().pickerStyle(.menu)
            case "van_ban_dai":
                TextEditor(text: Binding(get: { moi[t.cot] ?? "" },
                                         set: { moi[t.cot] = $0 }))
                    .font(.system(size: 11)).frame(height: 54)
                    .overlay(RoundedRectangle(cornerRadius: 4)
                        .strokeBorder(Color.secondary.opacity(0.3)))
            case "ma":
                TextField("", text: Binding(get: { moi[t.cot] ?? "" },
                                            set: { moi[t.cot] = $0 }))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11, design: .monospaced))
            default:
                TextField("", text: Binding(get: { moi[t.cot] ?? "" },
                                            set: { moi[t.cot] = $0 }))
                    .textFieldStyle(.roundedBorder).font(.system(size: 11))
            }
            if !t.goiY.isEmpty {
                Text(t.goiY).font(.system(size: 10)).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            // §E4 bước 3 / CX05 — số không nguồn thành Fact tầng NGƯỜI. Ô này để người
            // cho nguồn NGAY LÚC gõ, thay vì để tác tử hỏi lại ở lượt sau.
            if t.canNguon, (moi[t.cot] ?? "") != (dangCo[t.cot] ?? "") {
                TextField("nguồn của số này (datasheet tr.12…) — bỏ trống thì nó vào "
                          + "tầng NGƯỜI",
                          text: Binding(get: { nguon[t.cot] ?? "" },
                                        set: { nguon[t.cot] = $0 }))
                    .textFieldStyle(.roundedBorder).font(.system(size: 10))
            }
        }
    }

    private var doiGiDo: Bool { sd.truong.contains { (moi[$0.cot] ?? "") != (dangCo[$0.cot] ?? "") } }
    private var thieuBatBuoc: Bool {
        sd.truong.contains { $0.batBuoc
            && (moi[$0.cot] ?? "").trimmingCharacters(in: .whitespaces).isEmpty }
    }

    @discardableResult
    private func luu() -> Bool {
        let act = Self.actLuu(sd: sd, idHienVat: idHienVat, phienBan: phienBan,
                              row: row, ma: ma,
                              dangCo: dangCo, moi: moi, nguon: nguon, viSao: viSao,
                              khoi: khoi, surface: surface,
                              session: state.moPhienSua())
        guard let act else { return false }
        state.gui(act)
        return true
    }

    /// Thông điệp biểu mẫu gửi đi. `nil` = không có gì đổi, nên **không gửi**.
    ///
    /// Tách ra để đo được: đây là chỗ một dòng bốn trường phải ra ĐÚNG MỘT `patch`, và
    /// chỗ `{row}`/`{ma}` được thay. Thay sai thì một bảng ghi vào đúng dòng của dòng khác.
    static func actLuu(sd: SuaDuoc, idHienVat: String, phienBan: Int,
                       row: Int, ma: String,
                       dangCo: [String: String], moi: [String: String],
                       nguon: [String: String], viSao: String,
                       khoi: String, surface: String, session: String) -> HumanAct? {
        var patch: [JSONValue] = []
        var nguonChu: [String] = []
        for t in sd.truong {
            let cu = dangCo[t.cot] ?? ""
            let m = moi[t.cot] ?? ""
            guard m != cu else { continue }
            patch.append(.object(["path": .string(t.duong(row: row, ma: ma)),
                                  "op": .string("set"),
                                  "value": giaTri(m, kieu: t.kieu)]))
            if let n = nguon[t.cot], !n.trimmingCharacters(in: .whitespaces).isEmpty {
                nguonChu.append("\(t.cot): \(n)")
            }
        }
        guard !patch.isEmpty else { return nil }
        var ghiChu = viSao.trimmingCharacters(in: .whitespacesAndNewlines)
        if !nguonChu.isEmpty {
            ghiChu += (ghiChu.isEmpty ? "" : " · ") + "nguồn — " + nguonChu.joined(separator: "; ")
        }
        return HumanAct(
            kind: .edit,
            target: .init(type: sd.loai, id: idHienVat),
            data: ["base_version": .string("v\(phienBan)"),
                   "patch": .array(patch),
                   "summary": .string("sửa \(patch.count) ô của \(ma.isEmpty ? idHienVat : ma)"),
                   "session_id": .string(session)],
            origin: .init(surface: surface, block: khoi, row: ma),
            note: ghiChu.isEmpty ? nil : ghiChu)
    }

    /// Thông điệp của một ô `gui_bang="set"` — một CÁI CÔNG TẮC, không phải một hiện vật.
    ///
    /// Vì sao không đi qua `edit`: một cờ tính năng không có phiên bản, không có changeset
    /// và không có hạ nguồn STALE. Gửi nó bằng `edit` thì lõi phải đi tìm một hiện vật
    /// không tồn tại, và `base_version` là một con số bịa ra.
    static func actDat(key: String, bat: Bool, surface: String, khoi: String,
                       ma: String) -> HumanAct {
        HumanAct(kind: .set,
                 data: ["key": .string(key), "value": .bool(bat)],
                 origin: .init(surface: surface, block: khoi, row: ma))
    }

    /// Chuỗi người gõ → giá trị đúng KIỂU mà lõi khai.
    ///
    /// Gửi `"5"` vào một trường số thì `ap_patch` ghi một chuỗi, và lần so sánh ngưỡng
    /// sau đó sẽ so chuỗi với số — một phép so luôn sai mà không kêu.
    static func giaTri(_ s: String, kieu: String) -> JSONValue {
        switch kieu {
        case "so":
            if let d = Double(s.replacingOccurrences(of: ",", with: ".")) { return .number(d) }
            return .string(s)
        case "so_nguyen":
            if let i = Int(s) { return .number(Double(i)) }
            return .string(s)
        case "bool":
            return .bool(s == "true" || s.lowercased() == "có")
        default:
            return .string(s)
        }
    }
}
