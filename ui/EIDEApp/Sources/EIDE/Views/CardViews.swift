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

            Text(card.title).font(.system(size: 13, weight: .semibold))

            // Hậu quả TRƯỚC lựa chọn.
            if !card.consequences.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(card.consequences, id: \.self) { c in
                        HStack(alignment: .top, spacing: 5) {
                            Text("•").foregroundStyle(Color.gateRed)
                            Text(c).font(.system(size: 12)).textSelection(.enabled)
                        }
                    }
                }
            }
            if card.irreversible {
                Label("Thao tác này KHÔNG hoàn tác được.", systemImage: "exclamationmark.octagon.fill")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color.gateRed)
            }
            if let r = card.requireText {
                Text(r).font(.system(size: 11)).foregroundStyle(.secondary)
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

    private func quyet(approved: Bool, choice: String) {
        guard let gid = card.gateID else { return }
        state.gui(.decide(gateID: gid, approved: approved, choice: choice,
                          note: lyDo.isEmpty ? nil : lyDo))
    }
}

// MARK: - Thẻ làm rõ (N4)

/// Thẻ hỏi một cụm. Mỗi câu hỏi nói luôn **vì sao hỏi** — người có quyền biết câu trả
/// lời của mình sẽ quyết định điều gì. Và nếu bỏ qua, giả định được nói thẳng ra.
struct TheLamRoView: View {
    @EnvironmentObject var state: AppState
    let card: Card
    @State private var traLoi: [String: String] = [:]

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
                Text(i).font(.system(size: 12)).textSelection(.enabled)
            }

            ForEach(Array(card.questions.enumerated()), id: \.offset) { i, q in
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .firstTextBaseline, spacing: 5) {
                        Text("\(i + 1).").font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.secondary)
                        Text(q.text).font(.system(size: 12, weight: .medium))
                    }
                    if let w = q.why {
                        Text(w).font(.system(size: 10)).italic().foregroundStyle(.secondary)
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

            if let gd = card.assumptionIfSkipped, !gd.isEmpty {
                Label("Bỏ qua thì tôi đi tiếp với giả định: \(gd)",
                      systemImage: "questionmark.circle")
                    .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
            }

            HStack {
                Button("Gửi trả lời") {
                    state.gui(.choose(cardID: card.id, answers: traLoi.filter { !$0.value.isEmpty }))
                }
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
                        Text(c).font(.system(size: 11)).multilineTextAlignment(.leading)
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
