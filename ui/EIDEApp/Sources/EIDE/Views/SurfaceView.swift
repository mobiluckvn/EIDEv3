import SwiftUI

/// Bề mặt (tab). Bộ render CHUNG: nó vẽ theo `type` của khối, không theo tên tab.
///
/// I3 — "giao diện không quyết". Hệ quả thực tế của nguyên tắc đó: khi lõi thêm một
/// khối mới vào tab Thiết kế, giao diện này vẽ được ngay mà không phải sửa dòng nào.
/// Và khi lõi gửi một loại khối chưa biết, nó **nói ra** chứ không bỏ qua im lặng.
struct SurfaceView: View {
    let surface: SurfaceModel?
    let key: String

    var body: some View {
        ScrollView {
            if let s = surface {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(spacing: 7) {
                        Text(s.title).font(.system(size: 16, weight: .semibold))
                        MaKhoi(ma: s.code)
                        Spacer()
                    }
                    ForEach(s.blocks) { b in BlockView(block: b) }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                VStack(spacing: 8) {
                    Image(systemName: "rectangle.dashed").font(.largeTitle).foregroundStyle(.tertiary)
                    Text("Lõi chưa gửi nội dung cho bề mặt “\(key)”.")
                        .foregroundStyle(.secondary)
                    Text("Đây là lỗi đồng bộ, không phải tab trống. Thử ⌘R để xin vẽ lại.")
                        .font(.caption).foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, minHeight: 300)
            }
        }
        .background(Color(nsColor: .underPageBackgroundColor))
    }
}

// MARK: - Một khối

struct BlockView: View {
    @EnvironmentObject var state: AppState
    let block: SurfaceBlock
    @State private var hienViSao = false

    private var explain: JSONValue? {
        if case .object(let o)? = block.payload["explain"], !o.isEmpty {
            return block.payload["explain"]
        }
        return nil
    }
    private var tacGia: String? { block.str("tac_gia") }
    private var phienBan: Int? { block.payload["phien_ban"]?.intValue }
    private var diffPrev: String? { block.str("diff_prev") }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // §E3.2 §1 — tóm tắt trước, chi tiết sau.
            HStack(alignment: .firstTextBaseline, spacing: 7) {
                if let t = tacGia { ThanhTacGia(tacGia: t) }
                Text(block.title).font(.system(size: 13, weight: .semibold))
                if let v = phienBan, v > 1 {
                    Text("v\(v)").font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.tertiary)
                }
                MaKhoi(ma: block.code)
                if let st = block.stale, !st.isEmpty {
                    Label("\(st.count) mục cần cập nhật", systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
                }
                Spacer()
                if explain != nil { nutGiaiThich }
            }

            if let s = block.summary, !s.isEmpty {
                TextMd(s).font(.system(size: 11)).foregroundStyle(.secondary)
            }

            // §E3.2 §3 — "luôn nói khác biệt": diff_prev hiện NGAY dưới tóm tắt.
            if let d = diffPrev, !d.isEmpty {
                HStack(alignment: .top, spacing: 5) {
                    Image(systemName: "arrow.triangle.branch")
                        .font(.system(size: 9)).foregroundStyle(Color.accentColor)
                    TextMd("Khác bản trước: \(d)")
                        .font(.system(size: 10)).foregroundStyle(Color.accentColor)
                }
            }

            // Băng STALE nói rõ VÌ SAO cần cập nhật, không chỉ rằng cần.
            if let r = block.str("stale_reason"), !r.isEmpty {
                Label("Cần cập nhật vì \(r)", systemImage: "exclamationmark.triangle.fill")
                    .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
                    .padding(5)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.staleAmber.opacity(0.1),
                                in: RoundedRectangle(cornerRadius: 4))
            }

            noiDung
        }
        .padding(13)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(nsColor: .controlBackgroundColor),
                    in: RoundedRectangle(cornerRadius: 9))
    }

    /// §E3.3 — hai nút khác nhau, và khác nhau ở chỗ tốn tiền hay không.
    ///
    /// **"Vì sao?"** hiện lớp giải thích ĐÃ LƯU: 0 token, tức thì, luôn có.
    /// **"Giải thích thêm"** mới gọi tác tử — người dùng phải chủ động chọn trả giá đó.
    private var nutGiaiThich: some View {
        HStack(spacing: 8) {
            Button("Vì sao?") { hienViSao.toggle() }
                .buttonStyle(.plain)
                .font(.system(size: 11))
                .foregroundStyle(Color.accentColor)
                .help("Hiện lớp giải thích đã lưu — không tốn token")
                .popover(isPresented: $hienViSao, arrowEdge: .bottom) {
                    ViSaoView(explain: explain ?? .null, tieuDe: block.title)
                }
            Button("Giải thích thêm") {
                let ma = block.str("artefact_id") ?? block.code
                state.gui(HumanAct(
                    kind: .say,
                    text: "Giải thích thêm cho tôi về \(ma) — \(block.title). "
                        + "Tôi muốn hiểu kỹ hơn phần vì sao.",
                    origin: .init(surface: state.selectedSurface, block: block.code)))
            }
            .buttonStyle(.plain)
            .font(.system(size: 11))
            .foregroundStyle(.secondary)
            .help("Hỏi tác tử — lần này có tốn token")
        }
    }

    @ViewBuilder private var noiDung: some View {
        switch block.type {
        case "empty":    KhoiRong(block: block)
        case "kv":       KhoiKV(block: block)
        case "table":    KhoiBang(block: block)
        case "timeline": KhoiDongThoiGian(block: block)
        case "changesets": KhoiChangeset(block: block)
        case "procedure": KhoiQuyTrinh(block: block)
        case "snapshots": KhoiSnapshot(block: block)
        case "list":     KhoiDanhSach(block: block)
        case "sections": KhoiMuc(block: block)
        case "text":     MarkdownView(text: block.str("text") ?? "")
        case "code":
            Text(block.str("text") ?? "")
                .font(.system(size: 11, design: .monospaced))
                .textSelection(.enabled)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 5))
        default:
            Label("Giao diện chưa biết vẽ khối loại “\(block.type)”.",
                  systemImage: "questionmark.square.dashed")
                .font(.system(size: 11)).foregroundStyle(Color.staleAmber)
        }
    }
}

// MARK: - Khối rỗng trung thực

/// Ba câu: hiện chưa có gì · vì sao chưa có · cần gì để có.
///
/// Một tab trống trơn khiến người tưởng tính năng hỏng; một tab có nội dung mẫu thì
/// nói dối. Khối này là đường thứ ba, và nó do LÕI viết (§E3.2 §5) — giao diện chỉ vẽ.
struct KhoiRong: View {
    let block: SurfaceBlock

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 6) {
                Image(systemName: "circle.dashed").foregroundStyle(.tertiary)
                TextMd(block.str("chua_co") ?? "Chưa có gì.")
                    .font(.system(size: 12, weight: .medium))
                if let b = block.str("buoc") { BuocChip(buoc: b) }
            }
            if let v = block.str("vi_sao") {
                HStack(alignment: .top, spacing: 6) {
                    Text("Vì sao").font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.tertiary).frame(width: 44, alignment: .trailing)
                    TextMd(v).font(.system(size: 11)).foregroundStyle(.secondary)
                }
            }
            if let c = block.str("can_gi"), c != "—" {
                HStack(alignment: .top, spacing: 6) {
                    Text("Cần gì").font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.tertiary).frame(width: 44, alignment: .trailing)
                    TextMd(c).font(.system(size: 11))
                }
            }
        }
    }
}

// MARK: - Khối khoá–giá trị

struct KhoiKV: View {
    let block: SurfaceBlock

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(Array(block.arr("pairs").enumerated()), id: \.offset) { _, p in
                let cells = p.arrayValue
                HStack(alignment: .top, spacing: 10) {
                    Text(cells.first?.display ?? "")
                        .font(.system(size: 11)).foregroundStyle(.secondary)
                        .frame(width: 210, alignment: .trailing)
                    OCoTang(text: cells.count > 1 ? cells[1].display : "")
                    Spacer()
                }
            }
        }
    }
}

// MARK: - Bảng

struct KhoiBang: View {
    @EnvironmentObject var state: AppState
    let block: SurfaceBlock
    @State private var dangSua: String?          // "hàng|cột"

    private var cols: [String] { block.arr("columns").compactMap(\.stringValue) }
    private var rows: [[JSONValue]] { block.arr("rows").map(\.arrayValue) }
    /// Tên cột → tên trường trong hiện vật. §E2 cột "Người sửa được gì".
    private var cotSua: [String: String] {
        (block.payload["cot_sua"]?.objectValue ?? [:]).compactMapValues(\.stringValue)
    }
    private func meta(_ ma: String) -> JSONValue? {
        block.payload["row_meta"]?[ma]
    }

    var body: some View {
        if rows.isEmpty {
            Text("Bảng rỗng.").font(.system(size: 11)).foregroundStyle(.tertiary)
        } else {
            ScrollView(.horizontal, showsIndicators: true) {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(spacing: 0) {
                        ForEach(Array(cols.enumerated()), id: \.offset) { _, c in
                            HStack(spacing: 3) {
                                Text(c).font(.system(size: 10, weight: .semibold))
                                if cotSua[c] != nil {
                                    Image(systemName: "pencil")
                                        .font(.system(size: 8))
                                        .foregroundStyle(Color.accentColor)
                                        .help("Cột này anh sửa được — bấm vào ô")
                                }
                                Spacer()
                            }
                            .foregroundStyle(.secondary)
                            .frame(width: 170, alignment: .leading)
                            .padding(.vertical, 5).padding(.horizontal, 6)
                        }
                    }
                    .background(Color(nsColor: .underPageBackgroundColor))
                    Divider()
                    ForEach(Array(rows.enumerated()), id: \.offset) { i, r in
                        hang(r, chan: i % 2 == 0)
                        Divider().opacity(0.35)
                    }
                }
            }
            .frame(maxHeight: 460)
        }
    }

    @ViewBuilder
    private func hang(_ r: [JSONValue], chan: Bool) -> some View {
        let ma = r.first?.stringValue ?? ""
        let m = meta(ma)
        HStack(spacing: 0) {
            ForEach(Array(r.enumerated()), id: \.offset) { j, cell in
                let cot = j < cols.count ? cols[j] : ""
                if let truong = cotSua[cot] {
                    OSuaDuoc(ma: ma, truong: truong, gia: cell.display,
                             phienBan: m?["phien_ban"]?.intValue ?? 1,
                             khoi: block.code)
                        .frame(width: 170, alignment: .leading)
                        .padding(.vertical, 4).padding(.horizontal, 6)
                } else {
                    OCoTang(text: cell.display)
                        .frame(width: 170, alignment: .leading)
                        .padding(.vertical, 4).padding(.horizontal, 6)
                }
            }
            // Mỗi dòng có lớp giải thích riêng và thanh tác giả riêng.
            if let m {
                HStack(spacing: 5) {
                    if let tg = m["tac_gia"]?.stringValue { ThanhTacGia(tacGia: tg) }
                    if let v = m["phien_ban"]?.intValue, v > 1 {
                        Text("v\(v)").font(.system(size: 9, design: .monospaced))
                            .foregroundStyle(.tertiary)
                    }
                    if let ex = m["explain"] { NutViSaoDong(explain: ex, tieuDe: ma) }
                    if let r = m["stale_reason"]?.stringValue, !r.isEmpty {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 9)).foregroundStyle(Color.staleAmber)
                            .help("Cần cập nhật vì \(r)")
                    }
                }
                .padding(.horizontal, 6)
            }
            Spacer()
        }
        .background(chan ? Color.clear
                    : Color(nsColor: .underPageBackgroundColor).opacity(0.5))
    }
}

struct NutViSaoDong: View {
    let explain: JSONValue
    let tieuDe: String
    @State private var mo = false

    var body: some View {
        Button { mo.toggle() } label: {
            Image(systemName: "questionmark.circle").font(.system(size: 10))
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.accentColor)
        .help("Vì sao có dòng này — không tốn token")
        .popover(isPresented: $mo, arrowEdge: .bottom) {
            ViSaoView(explain: explain, tieuDe: tieuDe)
        }
    }
}

/// Ô sửa được trong bảng — §E4 bước 1–2.
///
/// Bấm để sửa, gõ giá trị mới, và **ô "vì sao" nằm ngay cạnh**. Tài liệu gọi nó là
/// "tuỳ chọn nhưng được khuyến khích" (§E4 bước 1); đặt nó ngay đây thay vì giấu sau
/// một nút là cách rẻ nhất để lời giải thích thật sự được viết. Sau này khi tác tử
/// hỏi "vì sao anh đổi số này", câu trả lời đã có sẵn.
struct OSuaDuoc: View {
    @EnvironmentObject var state: AppState
    let ma: String
    let truong: String
    let gia: String
    let phienBan: Int
    let khoi: String

    @State private var dangSua = false
    @State private var moi = ""
    @State private var viSao = ""

    var body: some View {
        if dangSua {
            VStack(alignment: .leading, spacing: 4) {
                TextField("giá trị mới", text: $moi)
                    .textFieldStyle(.roundedBorder).font(.system(size: 11))
                TextField("vì sao anh đổi?", text: $viSao)
                    .textFieldStyle(.roundedBorder).font(.system(size: 10))
                HStack(spacing: 6) {
                    Button("Lưu") { luu() }
                        .font(.system(size: 10))
                        .disabled(moi.trimmingCharacters(in: .whitespaces).isEmpty)
                    Button("Bỏ") { dangSua = false }
                        .buttonStyle(.plain).font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
            }
        } else {
            Button {
                moi = gia
                viSao = ""
                dangSua = true
            } label: {
                HStack(spacing: 4) {
                    TextMd(gia).font(.system(size: 11)).lineLimit(3)
                        .multilineTextAlignment(.leading)
                    Spacer(minLength: 0)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .help("Bấm để sửa — thay đổi của anh thành một changeset hoàn tác được")
        }
    }

    private func luu() {
        state.gui(HumanAct(
            kind: .edit,
            target: .init(type: "req", id: ma),
            data: [
                "base_version": .string("v\(phienBan)"),
                "fields": .object([truong: .string(moi)]),
                "summary": .string("sửa \(truong) của \(ma)"),
            ],
            origin: .init(surface: state.selectedSurface, block: khoi, row: ma),
            note: viSao.isEmpty ? nil : viSao))
        dangSua = false
    }
}

/// Ô bảng biết tự nhận ra mình đang chứa một tầng tin cậy và tô đúng màu.
/// §E3.2 §2: "mọi con số là một liên kết… không có số trần".
struct OCoTang: View {
    let text: String

    var body: some View {
        if let t = Tier(loose: text), t.nhan == text || text.uppercased() == t.rawValue {
            TierChip(tier: t)
        } else {
            TextMd(text)
                .font(.system(size: 11))
                .textSelection(.enabled)
                .lineLimit(3)
        }
    }
}

// MARK: - Dòng thời gian (sổ cái)

struct KhoiDongThoiGian: View {
    let block: SurfaceBlock
    @State private var loc: String = ""

    private var items: [JSONValue] { block.arr("items") }
    private var locItems: [JSONValue] {
        loc.isEmpty ? items : items.filter {
            ($0["tom_tat"]?.stringValue ?? "").localizedCaseInsensitiveContains(loc)
            || ($0["kind"]?.stringValue ?? "").localizedCaseInsensitiveContains(loc)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                if let ok = block.payload["integrity_ok"]?.boolValue {
                    Label(ok ? "Chuỗi hash toàn vẹn" : "SỔ CÁI BỊ SỬA",
                          systemImage: ok ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(ok ? Color.okGreen : Color.gateRed)
                }
                Spacer()
                TextField("lọc…", text: $loc)
                    .textFieldStyle(.roundedBorder).frame(width: 170)
                    .font(.system(size: 11))
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 1) {
                    ForEach(Array(locItems.enumerated().reversed()), id: \.offset) { _, it in
                        DongSoCai(item: it)
                    }
                }
            }
            .frame(maxHeight: 460)
        }
    }
}

/// Một sự kiện trong sổ cái.
///
/// Tách thành view riêng không phải vì gọn: trình biên dịch Swift không suy được kiểu
/// của một `HStack` sáu tầng trong thời gian hợp lý. Chia nhỏ là cách duy nhất.
struct DongSoCai: View {
    let item: JSONValue

    private var loai: String { item["kind"]?.stringValue ?? "" }
    private var gio: String {
        let ts = item["ts"]?.stringValue ?? ""
        guard ts.count > 19 else { return "" }
        let i = ts.index(ts.startIndex, offsetBy: 11)
        let j = ts.index(ts.startIndex, offsetBy: 19)
        return String(ts[i..<j])
    }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text("\(item["seq"]?.intValue ?? 0)")
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(.tertiary)
                .frame(width: 34, alignment: .trailing)
            Text(gio)
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(.tertiary)
            Text(loai)
                .font(.system(size: 9, weight: .semibold, design: .monospaced))
                .foregroundStyle(Self.mau(loai))
                .frame(width: 88, alignment: .leading)
            TextMd(item["tom_tat"]?.stringValue ?? "")
                .font(.system(size: 11))
                .textSelection(.enabled)
            Spacer()
        }
        .padding(.vertical, 1)
    }

    static func mau(_ k: String) -> Color {
        switch k {
        case "human_act": return .accentColor
        case "gate", "incident": return .gateRed
        case "llm_call": return .purple
        case "tool_use", "tool_result": return .teal
        case "hook": return .staleAmber
        default: return .secondary
        }
    }
}

// MARK: - Bản ưng ý (§E6)

/// Danh sách bản ưng ý. Dấu ★ cho bản release.
///
/// Cột **khoảng cách** ("cách đây 12 changeset") là thứ §E6.3 đòi hiện khi mở lại dự
/// án. Nó trả lời câu người thật sự hỏi khi nhìn một danh sách mốc: *từ đó tới giờ đã
/// đi xa chưa?* — một cái ngày tháng không trả lời được câu đó.
struct KhoiSnapshot: View {
    @EnvironmentObject var state: AppState
    let block: SurfaceBlock

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if !(block.payload["co_release"]?.boolValue ?? false) {
                Label("Chưa có bản nào đánh dấu release — các thao tác khoá vĩnh viễn "
                      + "trên chip (RDP, eFuse) sẽ bị chặn cho tới khi có.",
                      systemImage: "lock.open")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
            }
            ForEach(Array(block.arr("items").enumerated()), id: \.offset) { _, s in
                DongSnapshot(s: s)
            }
        }
    }
}

private struct DongSnapshot: View {
    @EnvironmentObject var state: AppState
    let s: JSONValue

    private var id: String { s["id"]?.stringValue ?? "" }
    private var laRelease: Bool { s["kind"]?.stringValue == "release" }
    private var cuaNguoi: Bool { s["created_by"]?.stringValue == "human" }

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: laRelease ? "star.fill" : "star")
                .font(.system(size: 12))
                .foregroundStyle(laRelease ? Color.staleAmber : Color.secondary.opacity(0.5))
                .help(laRelease ? "Bản phát hành" : "Bản ưng ý")

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(s["name"]?.stringValue ?? id)
                        .font(.system(size: 12, weight: .semibold))
                        .textSelection(.enabled)
                    Text(id).font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.tertiary)
                    if let k = s["khoang_cach"]?.intValue, k > 0 {
                        Text("cách đây \(k) thay đổi")
                            .font(.system(size: 10)).foregroundStyle(.secondary)
                    }
                    ThanhTacGia(tacGia: cuaNguoi ? "nguoi" : "tac_tu")
                }
                if let n = s["note"]?.stringValue, !n.isEmpty {
                    TextMd(n).font(.system(size: 11)).foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }
                HStack(spacing: 8) {
                    Text(s["tom_tat"]?.stringValue ?? "")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.tertiary)
                    if let c = s["chip"]?.stringValue, !c.isEmpty {
                        Text(c).font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.tertiary)
                    }
                }
                let passed = (s["passed"]?.arrayValue ?? []).compactMap(\.stringValue)
                if !passed.isEmpty {
                    Label("đạt: \(passed.joined(separator: ", "))",
                          systemImage: "checkmark.seal")
                        .font(.system(size: 10)).foregroundStyle(Color.okGreen)
                }
            }

            Spacer()

            HStack(spacing: 10) {
                Button("So sánh") {
                    state.gui(.say("So sánh bản ưng ý \(id) với trạng thái hiện tại "
                                   + "giúp tôi — khác nhau ở đâu?"))
                }
                .buttonStyle(.plain).font(.system(size: 11))
                .foregroundStyle(Color.accentColor)

                // §E6.3 — khôi phục đi qua thẻ G-HIST, và thẻ phải liệt kê sẽ mất gì
                // TRƯỚC. Nên nút này HỎI tác tử chứ không tự khôi phục.
                Button("Khôi phục") {
                    state.gui(.say("Tôi muốn khôi phục về bản ưng ý \(id). "
                                   + "Cho tôi biết sẽ mất gì trước đã."))
                }
                .buttonStyle(.plain).font(.system(size: 11))
                .foregroundStyle(Color.gateRed)
                .help("Tác tử sẽ liệt kê sẽ mất gì rồi mới hỏi")

                if !laRelease {
                    Button("Đánh dấu release") {
                        state.gui(.say("Đánh dấu bản ưng ý \(id) là release."))
                    }
                    .buttonStyle(.plain).font(.system(size: 10))
                    .foregroundStyle(.secondary)
                    .help("Release là điều kiện cho thao tác khoá vĩnh viễn trên chip")
                }
            }
        }
        .padding(.vertical, 6)
        .overlay(alignment: .bottom) { Divider().opacity(0.3) }
    }
}

// MARK: - Quy trình từng bước

/// Quy trình là **hiện vật có cấu trúc**, không phải tệp markdown.
///
/// Khác biệt thấy ngay ở đây: mỗi bước có ô đánh dấu đã làm, có lệnh sao chép được,
/// có cách kiểm để biết mình làm đúng chưa, và bước nguy hiểm được tô đỏ TRƯỚC khi
/// người chạy tới nó. Một tệp `.md` không làm được cái nào trong bốn thứ đó.
struct KhoiQuyTrinh: View {
    @EnvironmentObject var state: AppState
    let block: SurfaceBlock

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            if let m = block.str("muc_dich"), !m.isEmpty {
                TextMd(m).font(.system(size: 11)).foregroundStyle(.secondary)
            }
            let can = block.arr("can_truoc").compactMap(\.stringValue)
            if !can.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Cần có trước").font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.tertiary)
                    ForEach(can, id: \.self) { c in
                        TextMd("• \(c)").font(.system(size: 11))
                    }
                }
                .padding(7)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(nsColor: .underPageBackgroundColor),
                            in: RoundedRectangle(cornerRadius: 5))
            }
            ForEach(Array(block.arr("buoc").enumerated()), id: \.offset) { _, b in
                BuocView(b: b, quyTrinh: block.id)
            }
        }
    }
}

private struct BuocView: View {
    @EnvironmentObject var state: AppState
    let b: JSONValue
    let quyTrinh: String

    private var so: Int { b["so"]?.intValue ?? 0 }
    private var trangThai: String { b["trang_thai"]?.stringValue ?? "" }
    private var nguyHiem: Bool { b["khong_dao_nguoc"]?.boolValue ?? false }

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: bieuTuong)
                .foregroundStyle(mauTrangThai)
                .font(.system(size: 13))
                .frame(width: 18)
                .padding(.top, 1)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text("Bước \(so)").font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.tertiary)
                    if nguyHiem {
                        Label("không hoàn tác được", systemImage: "exclamationmark.octagon.fill")
                            .font(.system(size: 9, weight: .semibold))
                            .foregroundStyle(Color.gateRed)
                    }
                }
                TextMd(b["viec"]?.stringValue ?? "").font(.system(size: 12, weight: .medium))
                    .textSelection(.enabled)

                if let cb = b["canh_bao"]?.stringValue, !cb.isEmpty {
                    Label(cb, systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 11)).foregroundStyle(Color.staleAmber)
                }
                if let lenh = b["lenh"]?.stringValue, !lenh.isEmpty {
                    HStack(spacing: 6) {
                        Text(lenh)
                            .font(.system(size: 11, design: .monospaced))
                            .textSelection(.enabled)
                            .padding(6)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(nsColor: .textBackgroundColor),
                                        in: RoundedRectangle(cornerRadius: 4))
                        Button {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(lenh, forType: .string)
                        } label: { Image(systemName: "doc.on.doc").font(.system(size: 10)) }
                        .buttonStyle(.plain).help("Sao chép lệnh")
                    }
                }
                if let s = b["script"]?.stringValue, !s.isEmpty {
                    Label(s, systemImage: "doc.text")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                if let kq = b["ket_qua_mong_doi"]?.stringValue, !kq.isEmpty {
                    dongPhu("Sẽ thấy", kq)
                }
                if let ck = b["cach_kiem"]?.stringValue, !ck.isEmpty {
                    dongPhu("Kiểm bằng", ck)
                }

                HStack(spacing: 8) {
                    nut("Xong", "xong")
                    nut("Không được", "that_bai")
                    nut("Bỏ qua", "bo_qua")
                }
                .padding(.top, 2)
            }
        }
        .padding(9)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(nen, in: RoundedRectangle(cornerRadius: 6))
    }

    private func dongPhu(_ nhan: String, _ gia: String) -> some View {
        HStack(alignment: .top, spacing: 5) {
            Text(nhan).font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.tertiary).frame(width: 56, alignment: .trailing)
            Text(gia).font(.system(size: 11)).foregroundStyle(.secondary)
                .textSelection(.enabled)
        }
    }

    /// Báo kết quả bước là một HumanAct như mọi thứ khác — nó vào sổ cái và
    /// sinh changeset, nên tiến độ quy trình cũng hoàn tác được (I1, N9).
    private func nut(_ nhan: String, _ tt: String) -> some View {
        Button(nhan) {
            state.gui(HumanAct(kind: .say,
                               text: "Bước \(so) của quy trình: \(nhanTiengViet(tt))",
                               origin: .init(surface: "code", block: quyTrinh,
                                             row: String(so))))
        }
        .buttonStyle(.plain)
        .font(.system(size: 10, weight: trangThai == tt ? .bold : .regular))
        .foregroundStyle(trangThai == tt ? Color.accentColor : .secondary)
    }

    private func nhanTiengViet(_ tt: String) -> String {
        tt == "xong" ? "đã xong" : tt == "that_bai" ? "không được" : "bỏ qua"
    }

    private var bieuTuong: String {
        switch trangThai {
        case "xong": return "checkmark.circle.fill"
        case "that_bai": return "xmark.circle.fill"
        case "bo_qua": return "minus.circle"
        default: return "circle"
        }
    }

    private var mauTrangThai: Color {
        switch trangThai {
        case "xong": return .okGreen
        case "that_bai": return .gateRed
        case "bo_qua": return .secondary
        default: return Color.secondary.opacity(0.45)
        }
    }

    private var nen: Color {
        if nguyHiem { return Color.gateRed.opacity(0.05) }
        return trangThai == "xong" ? Color.okGreen.opacity(0.05)
             : Color(nsColor: .underPageBackgroundColor).opacity(0.5)
    }
}

// MARK: - Dòng thời gian changeset (§E2 dòng "Changeset", §E7 tab 10)

struct KhoiChangeset: View {
    @EnvironmentObject var state: AppState
    let block: SurfaceBlock
    @State private var hienCheckpoint = false
    @State private var locTacGia: String? = nil

    private var items: [JSONValue] {
        let ds = block.arr("items") + (hienCheckpoint ? block.arr("checkpoints") : [])
        guard let loc = locTacGia else { return ds }
        return ds.filter {
            loc == "human" ? ($0["cua_nguoi"]?.boolValue ?? false)
                           : !($0["cua_nguoi"]?.boolValue ?? false)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 10) {
                Picker("", selection: $locTacGia) {
                    Text("Tất cả").tag(String?.none)
                    Text("Của anh").tag(String?.some("human"))
                    Text("Của tác tử").tag(String?.some("agent"))
                }
                .pickerStyle(.segmented).frame(width: 260).labelsHidden()
                Toggle("Hiện checkpoint ngầm", isOn: $hienCheckpoint)
                    .toggleStyle(.checkbox).font(.system(size: 11))
                Spacer()
            }
            ForEach(Array(items.enumerated().reversed()), id: \.offset) { _, cs in
                DongChangeset(cs: cs)
            }
        }
    }
}

struct DongChangeset: View {
    @EnvironmentObject var state: AppState
    let cs: JSONValue

    private var id: String { cs["id"]?.stringValue ?? "" }
    private var cuaNguoi: Bool { cs["cua_nguoi"]?.boolValue ?? false }
    private var luiDuoc: Bool { cs["hoan_tac_duoc"]?.boolValue ?? false }
    private var daLui: String? { cs["da_hoan_tac_boi"]?.stringValue }
    private var stale: [String] { (cs["stale"]?.arrayValue ?? []).compactMap(\.stringValue) }

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            // Thanh tác giả (§E7) — nhìn một cái biết ai làm.
            RoundedRectangle(cornerRadius: 2)
                .fill(cuaNguoi ? Color.accentColor : Color.secondary.opacity(0.5))
                .frame(width: 3)

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(id).font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.tertiary)
                    Text(cs["tom_tat"]?.stringValue ?? "")
                        .font(.system(size: 12, weight: .medium))
                        .textSelection(.enabled)
                }
                HStack(spacing: 8) {
                    if let n = cs["note"]?.stringValue, !n.isEmpty {
                        Text("vì: \(n)").font(.system(size: 10)).italic()
                            .foregroundStyle(.secondary)
                    }
                    if !stale.isEmpty {
                        Label("kéo theo \(stale.count) mục cần cập nhật",
                              systemImage: "arrow.triangle.branch")
                            .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
                            .help(stale.joined(separator: ", "))
                    }
                    if cuaNguoi, !(cs["da_duoc_nhac"]?.boolValue ?? false) {
                        Label("tác tử chưa nhắc tới", systemImage: "bell.badge")
                            .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
                            .help("Hook Stop sẽ buộc tác tử nhắc tới thay đổi này ở lượt sau (N9).")
                    }
                }
            }

            Spacer()

            // §E5.3 — không hoàn tác được thì nói LÝ DO, không chỉ làm mờ cái nút.
            if let ld = cs["ly_do_khong_hoan_tac"]?.stringValue, !ld.isEmpty {
                Label(ld, systemImage: "lock.fill")
                    .font(.system(size: 10)).foregroundStyle(Color.gateRed)
                    .help("Thao tác này đã tác động ra ngoài máy nên không lùi lại được.")
            } else if let d = daLui {
                Text("đã hoàn tác bởi \(d)")
                    .font(.system(size: 10)).foregroundStyle(.tertiary)
            } else if luiDuoc {
                Button("Hoàn tác") {
                    state.gui(HumanAct(kind: .undo,
                                       target: .init(type: "changeset", id: id),
                                       data: ["mode": .string("revert")],
                                       origin: .init(surface: "history")))
                }
                .buttonStyle(.plain)
                .font(.system(size: 11))
                .foregroundStyle(Color.accentColor)
                .help("Tạo một thay đổi mới lùi lại changeset này. Lịch sử không bị xoá.")
            }
        }
        .padding(.vertical, 5)
        .overlay(alignment: .bottom) { Divider().opacity(0.3) }
    }
}

// MARK: - Danh sách & mục

struct KhoiDanhSach: View {
    let block: SurfaceBlock

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            ForEach(Array(block.arr("items").enumerated()), id: \.offset) { _, it in
                HStack(alignment: .top, spacing: 6) {
                    Text("•").foregroundStyle(.tertiary)
                    TextMd(it.display).font(.system(size: 11)).textSelection(.enabled)
                    Spacer()
                }
            }
        }
    }
}

struct KhoiMuc: View {
    let block: SurfaceBlock
    @State private var mo: Set<String> = []

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let p = block.str("path") {
                Text(p).font(.system(size: 9, design: .monospaced)).foregroundStyle(.tertiary)
            }
            ForEach(Array(block.arr("sections").enumerated()), id: \.offset) { _, s in
                let ten = s["ten"]?.stringValue ?? ""
                let than = s["than"]?.stringValue ?? ""
                DisclosureGroup(isExpanded: Binding(
                    get: { mo.contains(ten) },
                    set: { bat in
                        if bat { mo.insert(ten) } else { mo.remove(ten) }
                    })) {
                    MarkdownView(text: than, co: 11)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 3)
                } label: {
                    TextMd(ten).font(.system(size: 12, weight: .medium))
                }
            }
        }
    }
}
