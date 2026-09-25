import SwiftUI

/// Bàn giao tiếp — §D: "Người và máy gặp nhau ở MỘT nơi".
///
/// I2: mỗi HumanAct để lại đúng một dòng "[Bạn] …", kể cả khi người thao tác trên tab.
/// Nhờ vậy transcript là hình chiếu của sổ cái và phát lại được.
struct ConsoleView: View {
    @EnvironmentObject var state: AppState
    @FocusState private var focusInput: Bool

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            dongHoiThoai
            if let r = state.run, r.status == "running" { Divider(); RunCard(run: r) }
            Divider()
            oNhap
        }
        .background(Color(nsColor: .textBackgroundColor))
    }

    // MARK: Đầu

    private var header: some View {
        HStack(spacing: 6) {
            Text("Bàn giao tiếp").font(.system(size: 12, weight: .semibold))
            Spacer()
            ForEach(AppState.ConsoleWidth.allCases, id: \.rawValue) { w in
                Button(w.nhan) { state.consoleWidth = w }
                    .buttonStyle(.plain)
                    .font(.system(size: 10))
                    .foregroundStyle(state.consoleWidth == w ? Color.accentColor : .secondary)
            }
        }
        .padding(.horizontal, 10).padding(.vertical, 6)
    }

    // MARK: Transcript

    private var dongHoiThoai: some View {
        ScrollViewReader { sp in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(state.transcript) { line in
                        VStack(alignment: .leading, spacing: 6) {
                            DongTranscript(line: line)
                            if let card = line.card, !card.resolved {
                                TheView(card: card)
                            }
                        }
                        .id(line.id)
                    }
                    ForEach(state.notices) { n in ThongBaoView(notice: n) }
                }
                .padding(10)
            }
            .onChange(of: state.transcript.count) {
                if let last = state.transcript.last {
                    withAnimation { sp.scrollTo(last.id, anchor: .bottom) }
                }
            }
        }
    }

    // MARK: Ô nhập

    private var oNhap: some View {
        VStack(spacing: 6) {
            if !state.theDangCho.isEmpty {
                HStack(spacing: 5) {
                    Image(systemName: "hand.raised.fill").font(.system(size: 10))
                    Text("\(state.theDangCho.count) thẻ đang chờ anh trả lời ở trên")
                        .font(.system(size: 11))
                    Spacer()
                }
                .foregroundStyle(Color.staleAmber)
                .padding(.horizontal, 10).padding(.top, 6)
            }

            HStack(alignment: .bottom, spacing: 6) {
                TextField("Nói với tác tử…", text: $state.draft, axis: .vertical)
                    .textFieldStyle(.plain)
                    .lineLimit(1...6)
                    .focused($focusInput)
                    .onSubmit { state.guiCauDangGo() }
                    .padding(8)
                    .background(Color(nsColor: .controlBackgroundColor),
                                in: RoundedRectangle(cornerRadius: 7))

                Button {
                    state.guiCauDangGo()
                } label: {
                    Image(systemName: "arrow.up.circle.fill").font(.system(size: 20))
                }
                .buttonStyle(.plain)
                .disabled(state.draft.trimmingCharacters(in: .whitespaces).isEmpty || state.busy)
            }
            .padding(.horizontal, 8).padding(.bottom, 8)
        }
        .onAppear { focusInput = true }
    }
}

// MARK: - Một dòng

struct DongTranscript: View {
    let line: TranscriptLine

    var body: some View {
        HStack(alignment: .top, spacing: 7) {
            Text(nhan)
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(mau)
                .frame(width: 46, alignment: .leading)
                .padding(.top, 2)
            // Câu của người là chữ trơn (họ gõ gì hiện nấy); lời tác tử qua bộ dựng
            // markdown + công thức — nó sinh tiêu đề, bảng so sánh, khối mã và ký hiệu
            // toán, và để nguyên thì người đọc phải tự giải mã `|---|---|`.
            if nhan == "BẠN" {
                Text(tach.1)
                    .font(.system(size: 12))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                MarkdownView(text: tach.1)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    /// Lõi đã gắn sẵn tiền tố "[Bạn] "/"[Tác tử] " (I2). Giao diện tách nó ra để
    /// trình bày, nhưng **không** tự đặt nhãn — nhãn là thứ lõi quyết.
    private var tach: (String, String) {
        if line.text.hasPrefix("[Bạn] ") { return ("BẠN", String(line.text.dropFirst(6))) }
        if line.text.hasPrefix("[Tác tử] ") { return ("TÁC TỬ", String(line.text.dropFirst(9))) }
        return (line.role == .human ? "BẠN" : line.role == .agent ? "TÁC TỬ" : "HỆ THỐNG",
                line.text)
    }

    private var nhan: String { tach.0 }

    private var mau: Color {
        switch nhan {
        case "BẠN": return .accentColor
        case "TÁC TỬ": return .primary
        default: return .secondary
        }
    }
}

struct ThongBaoView: View {
    let notice: AppState.Notice

    var body: some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: bieuTuong).font(.system(size: 11)).foregroundStyle(mau)
            VStack(alignment: .leading, spacing: 2) {
                Text(notice.text).font(.system(size: 11)).textSelection(.enabled)
                if let c = notice.code {
                    Text(c).font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .padding(7)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(mau.opacity(0.08), in: RoundedRectangle(cornerRadius: 5))
    }

    private var mau: Color {
        notice.level == "error" ? .gateRed : notice.level == "warn" ? .staleAmber : .secondary
    }
    private var bieuTuong: String {
        notice.level == "error" ? "xmark.octagon.fill"
            : notice.level == "warn" ? "exclamationmark.triangle.fill" : "info.circle"
    }
}

// MARK: - Thẻ Run

struct RunCard: View {
    @EnvironmentObject var state: AppState
    let run: AppState.RunState

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                ProgressView().controlSize(.small)
                Text("Đang chạy \(run.id)").font(.system(size: 11, weight: .medium))
                Spacer()
                Button("Dừng khẩn") { state.gui(.stopNow()) }
                    .buttonStyle(.plain)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(Color.gateRed)
            }
            Text("\(run.tools) công cụ · \(run.tokensIn + run.tokensOut) token · \(String(format: "%.1f", run.seconds)) s")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.secondary)
            if !run.assumptions.isEmpty {
                ForEach(run.assumptions, id: \.self) { a in
                    Label(a, systemImage: "questionmark.circle")
                        .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
                }
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.accentColor.opacity(0.06))
    }
}
