import SwiftUI

struct TheView: View {
    let card: Card

    var body: some View {
        switch card.kind {
        case .gate:    TheCongView(card: card)
        case .clarify: TheLamRoView(card: card)
        default:       TheLaView(card: card)
        }
    }
}

// MARK: - Thẻ cổng (§B4, §E7, I6)

/// Thẻ cổng. Ba quy tắc cứng, và cả ba đều có lý do đo được:
///
/// 1. **Hậu quả đứng trước lựa chọn.** Người phải đọc "mất gì" trước khi thấy nút bấm.
/// 2. **Không có mặc định.** Không nút nào là `defaultAction` — Enter không duyệt hộ ai.
/// 3. **Chỉ thẻ này mở được cổng** (I6). Gõ "có" trong ô nhập không mở. Lý do nằm ở
///    UC18: nếu câu xác nhận nạp firmware trộn chung với câu làm rõ yêu cầu, thì một
///    chữ "Có" trả lời cả hai thứ — và một trong hai là nạp vào chip thật.
struct TheCongView: View {
    @EnvironmentObject var state: AppState
    let card: Card
    @State private var lyDo: String = ""
    /// Bản người sửa trong cột phải của khối diff — DEV-370.
    @State private var banDaSua: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 6) {
                Image(systemName: card.neverAuto ? "lock.shield.fill" : "shield.lefthalf.filled")
                Text(card.gate ?? "CỔNG")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                if !card.risk.isEmpty {
                    Text(card.risk)
                        .font(.system(size: 9, weight: .semibold, design: .monospaced))
                        .padding(.horizontal, 4).padding(.vertical, 1)
                        .background(Color.gateRed.opacity(0.15), in: RoundedRectangle(cornerRadius: 3))
                }
                Spacer()
                if card.neverAuto {
                    Text("không bao giờ tự động")
                        .font(.system(size: 9)).foregroundStyle(.secondary)
                        .help("Không mức tự chủ nào bỏ qua được cổng này.")
                }
            }
            .foregroundStyle(Color.gateRed)

            TextMd(card.title).font(.system(size: 13, weight: .semibold))

            // Hậu quả TRƯỚC lựa chọn.
            if !card.consequences.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(card.consequences, id: \.self) { c in
                        HStack(alignment: .top, spacing: 5) {
                            Text("•").foregroundStyle(Color.gateRed)
                            TextMd(c).font(.system(size: 12)).textSelection(.enabled)
                        }
                    }
                }
            }
            if card.irreversible {
                Label("Thao tác này KHÔNG hoàn tác được.", systemImage: "exclamationmark.octagon.fill")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color.gateRed)
            }
            // Cổng G-FILE kèm diff (DEV-366, sau cờ `EIDE_FEATURE_CONG_CO_DIFF`): **ghi đè
            // cái gì lên cái gì**. Đứng SAU phần hậu quả và TRƯỚC hai cái nút — đúng quy
            // tắc 1 của thẻ cổng.
            if let d = state.diffGanVoi(gateID: card.gateID ?? "") {
                // Cột phải SỬA ĐƯỢC khi lõi cho phép (DEV-370). Thấy một cờ dịch sai thì
                // người sửa ngay tại đây rồi duyệt — thay cho vòng "Không → gõ một câu mô
                // tả chỗ cần sửa → đợi một lượt mô hình → hy vọng nó sửa đúng chỗ".
                DiffView(d: d, banDaSua: $banDaSua)
            }

            if let r = card.requireText {
                TextMd(r).font(.system(size: 11)).foregroundStyle(.secondary)
            }
            if !card.requireFields.isEmpty {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Phải nêu: \(card.requireFields.joined(separator: ", "))")
                        .font(.system(size: 11)).foregroundStyle(.secondary)
                    TextField("vì sao…", text: $lyDo).textFieldStyle(.roundedBorder)
                }
            }

            Divider()

            HStack(spacing: 8) {
                ForEach(Array(luaChon.enumerated()), id: \.offset) { i, nhan in
                    Button(nhan) { quyet(approved: i == 0, choice: nhan) }
                        .disabled(thieuLyDo)
                        // Không .keyboardShortcut(.defaultAction) — xem quy tắc 2.
                }
                // Nút thứ ba, CHỈ hiện khi người đã thật sự sửa cột phải. Hiện sẵn một nút
                // "duyệt với bản đã sửa" khi chưa ai sửa gì là mời người bấm một thứ không
                // khác gì nút bên cạnh.
                if daSua {
                    Button("Duyệt với bản đã sửa") { duyetKemBanSua() }
                        .disabled(thieuLyDo)
                        .help("Ghi bản của tác tử trước, rồi ghi bản anh sửa đè lên — hai "
                              + "thay đổi riêng, hoàn tác cái của anh thì về bản của nó")
                }
                Spacer()
                Text(card.gateID ?? card.id)
                    .font(.system(size: 9, design: .monospaced)).foregroundStyle(.tertiary)
            }
        }
        .padding(11)
        .background(Color.gateRed.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Color.gateRed.opacity(0.35)))
    }

    private var luaChon: [String] { card.options.isEmpty ? ["Duyệt", "Từ chối"] : card.options }
    private var thieuLyDo: Bool {
        !card.requireFields.isEmpty && lyDo.trimmingCharacters(in: .whitespaces).isEmpty
    }

    /// Người đã sửa cột phải THÀNH MỘT BẢN KHÁC bản tác tử định ghi.
    private var daSua: Bool {
        guard let b = banDaSua,
              let d = state.diffGanVoi(gateID: card.gateID ?? "") else { return false }
        return b != (d["phai"]?["noi_dung"]?.stringValue ?? "")
    }

    private func quyet(approved: Bool, choice: String) {
        guard let gid = card.gateID else { return }
        state.gui(.decide(gateID: gid, approved: approved, choice: choice,
                          note: lyDo.isEmpty ? nil : lyDo))
    }

    private func duyetKemBanSua() {
        guard let gid = card.gateID, let act = Self.actDuyetKemSua(
            gateID: gid, banDaSua: banDaSua,
            goc: state.diffGanVoi(gateID: gid)?["phai"]?["noi_dung"]?.stringValue,
            lyDo: lyDo) else { return }
        state.gui(act)
    }

    /// `decide` kèm bản người sửa. `nil` khi không có gì để kèm.
    ///
    /// Tách ra để đo được, và vì đây là chỗ một lỗi im lặng tốn nhất: gửi `amended` mà
    /// nội dung y hệt bản của tác tử sẽ đẻ ra một changeset "của người" không chứa thay
    /// đổi nào — làm hỏng đúng cái câu *"ai viết dòng này"* mà cả gói sinh ra để giữ.
    static func actDuyetKemSua(gateID: String, banDaSua: String?, goc: String?,
                               lyDo: String) -> HumanAct? {
        guard let b = banDaSua, b != (goc ?? "") else { return nil }
        return HumanAct(
            kind: .decide,
            data: ["gate_id": .string(gateID), "approved": .bool(true),
                   "choice": .string("Duyệt với bản đã sửa"),
                   "amended": .object(["content": .string(b)])],
            origin: .init(surface: "console"),
            note: lyDo.isEmpty ? nil : lyDo)
    }
}

// MARK: - Thẻ làm rõ (N4)

/// Thẻ hỏi một cụm. Mỗi câu hỏi nói luôn **vì sao hỏi** — người có quyền biết câu trả
/// lời của mình sẽ quyết định điều gì. Và nếu bỏ qua, giả định được nói thẳng ra.
struct TheLamRoView: View {
    @EnvironmentObject var state: AppState
    let card: Card
    @State private var traLoi: [String: String] = [:]
    /// Bản người sửa trong cột phải của khối diff — chỉ thẻ xung đột mới có.
    @State private var banDaSua: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "questionmark.bubble")
                Text("Cần anh làm rõ").font(.system(size: 11, weight: .bold))
                Spacer()
                Text("\(card.questions.count) câu, hỏi một lần")
                    .font(.system(size: 9)).foregroundStyle(.tertiary)
            }
            .foregroundStyle(Color.accentColor)

            if let i = card.intro, !i.isEmpty {
                MarkdownView(text: i).textSelection(.enabled)
            }

            ForEach(Array(card.questions.enumerated()), id: \.offset) { i, q in
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .firstTextBaseline, spacing: 5) {
                        Text("\(i + 1).").font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.secondary)
                        TextMd(q.text).font(.system(size: 12, weight: .medium))
                    }
                    if let w = q.why {
                        TextMd(w).font(.system(size: 10)).italic().foregroundStyle(.secondary)
                            .padding(.leading, 16)
                    }
                    if !q.choices.isEmpty {
                        FlowChoices(choices: q.choices,
                                    chon: traLoi[q.id],
                                    onChon: { traLoi[q.id] = $0 })
                            .padding(.leading, 16)
                    }
                    TextField(q.prefill.map { "\($0) — anh vừa nói trong câu" } ?? "trả lời…",
                              text: Binding(get: { traLoi[q.id] ?? "" },
                                            set: { traLoi[q.id] = $0 }))
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 12))
                        .padding(.leading, 16)
                }
            }

            // Thẻ xung đột: hai bản nằm NGAY TRONG thẻ, không phải sau một cái nút.
            //
            // Người đang phải chọn giữ bản nào — bắt họ mở thêm một tấm nữa để xem thứ họ
            // đang quyết là đặt một bước thừa vào đúng chỗ dễ bấm bừa nhất.
            if let d = state.diffGanVoi(cardID: card.id) {
                DiffView(d: d, banDaSua: $banDaSua)
            }

            if let gd = card.assumptionIfSkipped, !gd.isEmpty {
                Label("Bỏ qua thì tôi đi tiếp với giả định: \(gd)",
                      systemImage: "questionmark.circle")
                    .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
            }

            HStack {
                Button("Gửi trả lời") { guiTraLoi() }
                .disabled(traLoi.values.allSatisfy(\.isEmpty))
                Button("Bỏ qua, dùng giả định") {
                    state.gui(.choose(cardID: card.id, answers: [:]))
                }
                .buttonStyle(.plain).font(.system(size: 11)).foregroundStyle(.secondary)
                Spacer()
            }
        }
        .padding(11)
        .background(Color.accentColor.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Color.accentColor.opacity(0.3)))
    }

    private func guiTraLoi() {
        Self.guiTraLoi(state: state, card: card,
                       traLoi: traLoi.filter { !$0.value.isEmpty }, banDaSua: banDaSua)
    }

    /// Gửi câu trả lời. Với thẻ xung đột, **nội dung đi TRƯỚC, lựa chọn đi SAU**.
    ///
    /// Thứ tự ấy không phải tiểu tiết: lõi đóng sổ xung đột khi nhận `choose`, và lúc ấy nó
    /// đi tìm changeset của người để báo lại. Gửi ngược thì nó đóng sổ một việc chưa xảy ra.
    ///
    /// `base_version` lấy **hash của cột PHẢI** — bản đang nằm trên đĩa lúc này. Lấy hash
    /// bản của người (cột trái) là cố ghi đè bằng đúng cái phiên bản vừa gây ra xung đột;
    /// lần lưu này sẽ xung đột lần nữa, và đoạn người vừa gõ trong cột phải mất theo.
    ///
    /// `static` để **đo được**: đây là chỗ dễ mất việc của người nhất trong cả gói, và một
    /// closure trong thân view thì chỉ kiểm được bằng cách mở app ra bấm.
    static func guiTraLoi(state: AppState, card: Card, traLoi: [String: String],
                          banDaSua: String?) {
        if let d = state.diffGanVoi(cardID: card.id),
           let noiDung = banGuiDi(d, chon: traLoi["chon"] ?? "", banDaSua: banDaSua),
           let tg = card.raw["du_lieu"]?["target"]?.stringValue, !tg.isEmpty {
            let phan = tg.split(separator: ":", maxSplits: 1).map(String.init)
            state.gui(HumanAct(
                kind: .edit,
                target: .init(type: phan.first ?? "file", id: phan.count > 1 ? phan[1] : tg),
                data: ["base_version": .string(d["phai"]?["hash"]?.stringValue ?? ""),
                       "content": .string(noiDung),
                       "summary": .string("giải xung đột: \(traLoi["chon"] ?? "")"),
                       "session_id": .string(state.moPhienSua())],
                origin: .init(surface: "history", block: "the-xung-dot"),
                note: "anh chọn giữ bản này khi hai bản đụng nhau"))
        }
        state.gui(.choose(cardID: card.id, answers: traLoi))
    }

    /// Nội dung sẽ ghi, theo lựa chọn. `nil` = không ghi gì (giữ bản đang có trên đĩa).
    private static func banGuiDi(_ d: JSONValue, chon: String,
                                 banDaSua: String?) -> String? {
        if chon.hasPrefix("Dùng bản tôi vừa sửa") {
            // Chưa đụng vào cột phải mà chọn "bản tôi vừa sửa" thì bản ấy CHÍNH LÀ bản
            // hiện tại — không ghi gì, để khỏi đẻ ra một changeset rỗng.
            return banDaSua
        }
        if chon.hasPrefix("Giữ bản của tôi") {
            return d["trai"]?["noi_dung"]?.stringValue
        }
        return nil          // "Giữ bản của tác tử" — nó đang nằm trên đĩa rồi.
    }
}

/// Các lựa chọn xuống dòng theo bề ngang — câu hỏi kỹ thuật hay có lựa chọn dài.
struct FlowChoices: View {
    let choices: [String]
    let chon: String?
    let onChon: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(choices, id: \.self) { c in
                Button { onChon(c) } label: {
                    HStack(spacing: 5) {
                        Image(systemName: chon == c ? "largecircle.fill.circle" : "circle")
                            .font(.system(size: 10))
                        TextMd(c).font(.system(size: 11)).multilineTextAlignment(.leading)
                    }
                    .foregroundStyle(chon == c ? Color.accentColor : .primary)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

// MARK: - Thẻ lạ

/// Lõi gửi một loại thẻ giao diện chưa biết. **Không bỏ qua im lặng** (E3.2 §5):
/// hiện nội dung thô để người vẫn thấy được lõi đang hỏi gì.
struct TheLaView: View {
    let card: Card

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Label("Thẻ loại “\(card.raw["type"]?.stringValue ?? "?")” — bản giao diện này chưa biết vẽ",
                  systemImage: "questionmark.square.dashed")
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(Color.staleAmber)
            Text(JSONValue.object(card.raw).display)
                .font(.system(size: 10, design: .monospaced))
                .textSelection(.enabled)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.staleAmber.opacity(0.07), in: RoundedRectangle(cornerRadius: 7))
    }
}
