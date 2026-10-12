import SwiftUI

/// Trình soạn TỆP trong app — EIDE-EDIT-47 §DEV-367.
///
/// Trước gói này, khối `code` trên tab Mã nguồn là một `Text(...)` chỉ chọn–copy được: lõi
/// có `_sua_tep` (gộp ba chiều, thẻ xung đột, changeset hoàn tác được) từ bước G2, và
/// **không có đường nào cho người gõ một chữ vào đó**. Muốn sửa một dòng thì mở VS Code —
/// và lúc ấy EIDE không biết gì về lần sửa ấy cho tới khi tác tử đọc lại tệp.
///
/// **Không tô màu cú pháp, không gợi ý mã.** EIDE không định thay VS Code; nó cần một
/// đường *lưu có dấu vết*. Ai thích editor riêng thì dùng watcher (DEV-369).
struct TepEditorView: View {
    @EnvironmentObject var state: AppState
    @Environment(\.dismiss) private var dong

    let path: String

    @State private var noiDung = ""
    @State private var banDau = ""
    @State private var hash = ""
    @State private var viSao = ""
    @State private var quaLon = false
    @State private var loi: String?
    @State private var dangNap = true

    private var daSua: Bool { noiDung != banDau }

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 8) {
                Image(systemName: "doc.text")
                Text(path).font(.system(size: 13, weight: .semibold, design: .monospaced))
                if daSua {
                    Text("• chưa lưu").font(.system(size: 10))
                        .foregroundStyle(Color.staleAmber)
                }
                Spacer()
                Text("\(dong(cua: noiDung)) dòng")
                    .font(.system(size: 10, design: .monospaced)).foregroundStyle(.tertiary)
            }

            // Băng vàng khi TÁC TỬ đang giữ tệp này. Nó không chặn — §E4 bước 1 nói soft
            // lock cảnh báo mà vẫn cho người sửa; cái bị chặn là chiều ngược lại.
            if state.khoaCuaTacTu.contains(path) {
                Label("Tác tử đang sửa tệp này — lưu của anh sẽ được gộp ba chiều, và nếu "
                      + "hai bên đụng nhau thì anh sẽ thấy thẻ xung đột.",
                      systemImage: "exclamationmark.triangle.fill")
                    .font(.system(size: 11)).foregroundStyle(Color.staleAmber)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let l = loi {
                Label(l, systemImage: "xmark.octagon.fill")
                    .font(.system(size: 11)).foregroundStyle(Color.gateRed)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if quaLon {
                Label("Tệp quá lớn nên chỉ mở ở chế độ đọc.", systemImage: "lock")
                    .font(.system(size: 11)).foregroundStyle(Color.staleAmber)
            }

            if dangNap {
                ProgressView().controlSize(.small)
            } else {
                TextEditor(text: $noiDung)
                    .font(.system(size: 12, design: .monospaced))
                    .disabled(quaLon)
                    .overlay(RoundedRectangle(cornerRadius: 4)
                        .strokeBorder(Color.secondary.opacity(0.3)))
            }

            TextField("vì sao anh sửa? (tuỳ chọn)", text: $viSao)
                .textFieldStyle(.roundedBorder).font(.system(size: 11))

            HStack {
                Text("Cmd-S để lưu · đóng lại thì EIDE thôi giữ khoá mềm cho tệp này")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
                Spacer()
                Button("Đóng") { dongLai() }
                Button("Lưu") { luu() }
                    .keyboardShortcut("s", modifiers: .command)
                    .disabled(!daSua || quaLon)
            }
        }
        .padding(16).frame(width: 860, height: 620)
        .task { await nap() }
    }

    private func dong(cua s: String) -> Int { max(1, s.components(separatedBy: "\n").count) }

    /// Nội dung tệp tới từ LÕI (`file.open`), không phải từ `FileManager`.
    ///
    /// Giao diện tự đọc tệp thì hộp cát chỉ còn canh một nửa số đường vào — và nửa không
    /// canh là nửa người dùng đang ngồi gõ.
    private func nap() async {
        dangNap = true
        defer { dangNap = false }
        guard let r = await state.moTep(path) else {
            loi = "Không mở được tệp này."
            return
        }
        if r["ok"]?.boolValue != true {
            loi = r["message_vi"]?.stringValue ?? "Không mở được tệp này."
            return
        }
        quaLon = r["qua_lon"]?.boolValue ?? false
        noiDung = r["content"]?.stringValue ?? ""
        banDau = noiDung
        hash = r["hash"]?.stringValue ?? ""
        if quaLon { loi = r["message_vi"]?.stringValue }
        // Khoá mềm chiều NGƯỜI → tác tử: từ giờ tác tử ghi tệp này thì phải hỏi.
        state.baoDangSuaTep(path, dangSua: true)
    }

    private func luu() {
        state.gui(Self.actLuu(path: path, noiDung: noiDung, hash: hash, viSao: viSao,
                              session: state.moPhienSua()))
        banDau = noiDung
        viSao = ""
    }

    private func dongLai() {
        state.baoDangSuaTep(path, dangSua: false)
        state.dongPhienSua()
        dong()
    }

    /// Thông điệp trình soạn gửi khi người bấm Lưu.
    ///
    /// `base_version` là **hash nội dung lúc mở**, không phải lúc lưu: đó là thứ duy nhất
    /// cho `_sua_tep` phát hiện được tác tử đã sửa tệp trong lúc người đang gõ, và gộp ba
    /// chiều thay vì ghi đè.
    static func actLuu(path: String, noiDung: String, hash: String, viSao: String,
                       session: String) -> HumanAct {
        HumanAct(
            kind: .edit,
            target: .init(type: "file", id: path),
            data: ["base_version": .string(hash),
                   "content": .string(noiDung),
                   "summary": .string("anh sửa \(path)"),
                   "session_id": .string(session)],
            origin: .init(surface: "code", block: "editor", row: path),
            note: viSao.trimmingCharacters(in: .whitespaces).isEmpty ? nil : viSao)
    }
}
