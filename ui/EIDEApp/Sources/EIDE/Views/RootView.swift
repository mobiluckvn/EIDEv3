import SwiftUI

/// Bố cục §E7: Console bên trái (3 cỡ) · 10 tab bên phải · thanh trạng thái dưới cùng.
/// Đồng hồ ngữ cảnh — EIDE-MEM-42 §4, yêu cầu MEM-01/MEM-02.
///
/// Một con số phần trăm trên thanh trạng thái, và cả bảng mười khối khi rê chuột.
/// Lý do nó đáng chỗ: khi tác tử bắt đầu quên, câu hỏi đầu tiên của người là "vì sao".
/// Không có đồng hồ này thì câu trả lời duy nhất là "ngữ cảnh đầy" — một lời giải
/// thích không kiểm được. Có nó thì người thấy **khối nào** đã chạm trần.
/// Ngân sách một lượt — công cụ đã gọi và giây đã trôi.
///
/// Đọc **`state.run` trước** rồi mới tới `state.status`: lõi gửi `run.update` sau mỗi lời gọi
/// công cụ (rẻ), còn thanh trạng thái chỉ dựng lại ở cuối lượt (đắt — phải quét cả kho). Lấy
/// theo thứ tự ngược lại thì trong suốt một lượt dài, con số đứng nguyên ở `0/40`.
struct NganSachView: View {
    @EnvironmentObject var state: AppState

    private var dangChay: Bool { state.run?.status == "running" }

    var body: some View {
        let b = state.status.ngan_sach
        let tool = dangChay ? (state.run?.tools ?? 0) : b.da_dung_tool
        let giay = dangChay ? (state.run?.seconds ?? 0) : b.da_dung_giay
        // Sát trần thì đổi màu: chạm trần là lúc tác tử **bị cắt giữa chừng**, và người đọc
        // cần biết trước khi nó xảy ra chứ không phải sau.
        let cang = b.tool > 0 && Double(tool) >= Double(b.tool) * 0.8
        return HStack(spacing: 4) {
            if dangChay {
                Image(systemName: "circle.fill").font(.system(size: 5))
                    .foregroundStyle(Color.okGreen)
                    .help("Đang chạy — số đo cập nhật sau mỗi lời gọi công cụ")
            }
            Text("\(tool)/\(b.tool) tool · \(Int(giay))/\(Int(b.giay)) s")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(cang ? Color.staleAmber : .secondary)
        }
        .help(cang
              ? "Sắp chạm trần ngân sách lượt — tác tử sẽ phải dừng và báo lại"
              : "Ngân sách một lượt: số lời gọi công cụ và số giây")
    }
}

/// Token đã tiêu. Trả lời câu **đồng hồ ngữ cảnh không trả lời được**.
///
/// Ngữ cảnh có thể đứng yên ở 20 % suốt buổi trong khi số token tiêu ra vẫn tăng đều — mỗi
/// lượt nạp lại phần cố định rồi vứt đi. Trước đây con số này chỉ có trong thẻ Run, mà thẻ ấy
/// biến mất khi lượt xong, nên không nơi nào nói tổng của cả phiên.
struct TokenView: View {
    @EnvironmentObject var state: AppState

    private var dangChay: Bool { state.run?.status == "running" }

    var body: some View {
        let t = state.status.token
        let luot = dangChay
            ? (state.run?.tokensIn ?? 0) + (state.run?.tokensOut ?? 0)
            : t.luot
        // Phiên chỉ cập nhật ở cuối lượt; cộng thêm phần của lượt đang chạy để con số không
        // đứng im giữa chừng. Cộng như thế là ĐÚNG, vì `phien` lúc này chưa tính lượt này.
        let phien = dangChay ? t.phien + luot : t.phien
        return HStack(spacing: 3) {
            Image(systemName: "circle.hexagongrid").font(.system(size: 9))
                .foregroundStyle(.tertiary)
            Text(luot > 0 ? "\(gon(luot)) / \(gon(phien))" : gon(phien))
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.secondary)
        }
        .help(chuGiai(t, luot: luot, phien: phien))
    }

    /// Con số chính xác, tách vào/ra/cache cho cả lượt lẫn phiên.
    ///
    /// Tách `cached` ra riêng vì nó rẻ hơn token thường nhiều lần; gộp vào một con số là làm
    /// người đọc tưởng đắt hơn thực tế.
    private func chuGiai(_ t: StatusBar.Token, luot: Int, phien: Int) -> String {
        func dong(_ nhan: String, _ tong: Int, _ vao: Int, _ ra: Int, _ cache: Int) -> String {
            "\(nhan) \(tong.formatted()) (vào \(vao.formatted()) · ra \(ra.formatted())"
            + (cache > 0 ? " · cache \(cache.formatted())" : "") + ")"
        }
        var d: [String] = ["Token ĐÃ TIÊU:"]
        if luot > 0 {
            d.append("· " + dong("lượt này", luot, t.luot_vao, t.luot_ra, t.luot_cache))
        }
        d.append("· " + dong("cả phiên", phien, t.phien_vao, t.phien_ra, t.phien_cache))
        d.append("")
        d.append("Khác với đồng hồ ngữ cảnh bên phải: đó là chỗ CÒN NHỚ được,")
        d.append("đây là chỗ ĐÃ TIÊU. Ngữ cảnh đứng yên mà số này vẫn tăng là bình thường —")
        d.append("mỗi lượt nạp lại phần cố định rồi vứt đi.")
        return d.joined(separator: "\n")
    }

    /// 1 234 → "1,2k". Thanh trạng thái không đủ chỗ cho bảy chữ số, mà bảy chữ số cũng
    /// không ai đọc lướt được — con số chính xác nằm ở tooltip.
    private func gon(_ n: Int) -> String {
        if n < 1000 { return "\(n)" }
        if n < 1_000_000 { return String(format: "%.1fk", Double(n) / 1000) }
        return String(format: "%.2fM", Double(n) / 1_000_000)
    }
}

struct DongHoNguCanh: View {
    let nc: StatusBar.NguCanh

    private var mau: Color {
        switch nc.muc {
        case "C4": return .gateRed
        case "C3": return .gateRed.opacity(0.8)
        case "C2": return .staleAmber
        case "C1": return .staleAmber.opacity(0.8)
        default:   return .okGreen
        }
    }

    var body: some View {
        if nc.cua_so > 0 {
            HStack(spacing: 4) {
                Circle().fill(mau).frame(width: 6, height: 6)
                Text("ngữ cảnh \(nc.phanTram) %")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
                if nc.muc != "C0" {
                    Text(nc.muc)
                        .font(.system(size: 9, weight: .semibold, design: .monospaced))
                        .foregroundStyle(mau)
                }
            }
            .help(chiTiet)
        }
    }

    private var chiTiet: String {
        var d = ["Cửa sổ \(nc.cua_so) token · dùng \(nc.tong) (\(nc.phanTram) %)",
                 "Dùng được \(nc.kha_dung) — 20 % còn lại để dành cho câu trả lời lượt này",
                 ""]
        for k in nc.khoi where k.token > 0 {
            let tran = k.tran.map { " / \($0)" } ?? ""
            d.append("\(k.vuot ? "⚠︎ " : "")\(k.ten): \(k.token)\(tran)")
        }
        return d.joined(separator: "\n")
    }
}

struct RootView: View {
    @EnvironmentObject var state: AppState
    @EnvironmentObject var setup: Setup

    var body: some View {
        Group {
            if case .dangChay = state.connection {
                noiDung
            } else {
                MoDuAnView()
            }
        }
    }

    private var noiDung: some View {
        VStack(spacing: 0) {
            if state.kenhKiemThu.dangBat {
                // Phiên kiểm thử phải nhìn ra ngay. Một bài test chạy lẫn vào công việc
                // thật là cách nhanh nhất để mất lòng tin vào cả hai.
                HStack(spacing: 6) {
                    Image(systemName: "testtube.2")
                    Text("CHẾ ĐỘ KIỂM THỬ GIAO DIỆN — thao tác đang được điều khiển từ "
                         + "`.eide/ui-test/inbox.jsonl`")
                        .font(.system(size: 11, weight: .medium))
                    Spacer()
                }
                .padding(.horizontal, 12).padding(.vertical, 5)
                .background(Color.staleAmber.opacity(0.18))
                .foregroundStyle(Color.staleAmber)
            }
            // Bề rộng panel hội thoại co theo CỬA SỔ, không cố định.
            //
            // 460 pt là hợp lý trên màn hình 1728 pt, nhưng trên một cửa sổ 1100 pt (khổ tối
            // thiểu) nó chiếm 42 % và phần tab còn lại chật tới mức bảng nào cũng phải co.
            // Trần 38 % giữ cho hai bên đều dùng được ở mọi khổ màn hình.
            GeometryReader { cs in
            HStack(spacing: 0) {
                ConsoleView()
                    .frame(width: min(state.consoleWidth.rawValue, cs.size.width * 0.38))
                Divider()
                VStack(spacing: 0) {
                    TabBar()
                    Divider()
                    SurfaceView(surface: state.surfaces[state.selectedSurface],
                                key: state.selectedSurface)
                }
            }
            }
            Divider()
            StatusBarView()
        }
    }
}

// MARK: - Thanh tab

/// Thanh 11 tab.
///
/// Trên cửa sổ hẹp, thanh này là chỗ đầu tiên "mất control bên phải": 11 tên đầy đủ cần hơn
/// 1.100 pt, còn khổ cửa sổ tối thiểu chỉ có ngần ấy cho CẢ cửa sổ. Nó vẫn cuộn ngang được,
/// nhưng một tab phải cuộn mới thấy là một tab người dùng sẽ không bấm.
///
/// Nên: chật thì rút gọn tên (`Yêu cầu & Giải pháp` → `Yêu cầu`) và thu nhỏ đệm, để cả 11
/// tab cùng nằm trong khung. Vẫn giữ cuộn ngang làm lưới an toàn cho khổ còn hẹp hơn nữa.
struct TabBar: View {
    @EnvironmentObject var state: AppState

    /// Tên ngắn khi chật — vẫn là tên người đọc hiểu, không phải viết tắt bí hiểm.
    private static let TEN_NGAN: [String: String] = [
        "requirements": "Yêu cầu", "documents": "Tài liệu", "knowledge": "Tri thức",
        "design": "Thiết kế", "tools": "Công cụ", "code": "Mã nguồn",
        "simulation": "Mô phỏng", "hardware": "Mạch thật", "journal": "Nhật ký",
        "history": "Lịch sử", "project": "Dự án",
    ]

    var body: some View {
        GeometryReader { g in
            let chat = g.size.width < 1180
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 2) {
                    ForEach(state.surfaceOrder, id: \.key) { t in
                        let chon = state.selectedSurface == t.key
                        Button {
                            state.selectedSurface = t.key
                            // I1 — kể cả việc chuyển tab cũng là một HumanAct có xuất xứ,
                            // để sổ cái phát lại được đúng thứ người đã nhìn (§D2 `attend`).
                            state.gui(.attend(surface: t.key))
                        } label: {
                            HStack(spacing: 5) {
                                Text(chat ? (Self.TEN_NGAN[t.key] ?? t.title) : t.title)
                                    .font(.system(size: chat ? 11 : 12,
                                                  weight: chon ? .semibold : .regular))
                                    .fixedSize()
                                if !chat, let n = soKhoiRong(t.key), n > 0 {
                                    Text("\(n)").font(.system(size: 9, design: .monospaced))
                                        .foregroundStyle(.tertiary)
                                        .help("\(n) khối chưa có dữ liệu")
                                }
                            }
                            .padding(.horizontal, chat ? 6 : 10).padding(.vertical, 6)
                            .background(chon ? Color.accentColor.opacity(0.14) : .clear,
                                        in: RoundedRectangle(cornerRadius: 5))
                        }
                        .buttonStyle(.plain)
                        .help(t.title)
                    }
                }
                .padding(.horizontal, 8).padding(.vertical, 4)
            }
            .background(.background)
        }
        .frame(height: 34)
    }

    private func soKhoiRong(_ key: String) -> Int? {
        state.surfaces[key]?.blocks.filter { $0.type == "empty" }.count
    }
}

// MARK: - Thanh trạng thái (§E7)

struct StatusBarView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        HStack(spacing: 14) {
            muc("Dự án", state.status.du_an, help: "Thư mục dự án đang mở")
            muc("Nhánh", state.status.nhanh, help: "Nhánh git của dự án")
            muc("Chip", state.status.chip,
                help: state.status.chip == "chưa ghim"
                    ? "Chưa ghim hộ chiếu chip nào. Tác tử không ghim tên chip trần khi chưa có tài liệu."
                    : "Hộ chiếu chip đã ghim (ns.part@semver)")

            // Lõi gửi `isa` từ đầu, nhưng không nhãn nào vẽ nó ra — nên tập lệnh mà mọi lựa
            // chọn biên dịch dựa vào chỉ tồn tại trong JSON. Nạp nhầm firmware cho sai kiến
            // trúc là một lỗi tốn cả buổi, và đây là chỗ rẻ nhất để thấy trước.
            if let isa = state.status.isa, !isa.isEmpty {
                muc("Tập lệnh", isa,
                    help: "Kiến trúc tập lệnh suy ra từ hộ chiếu chip — quyết định cờ biên dịch")
            }

            if state.status.fact.isEmpty {
                muc("Fact", "0", help: "Chưa có con số nào truy vết được tới tài liệu")
            } else {
                HStack(spacing: 4) {
                    Text("Fact").font(.system(size: 10)).foregroundStyle(.secondary)
                    ForEach(["VANG", "BAC", "NGUOI", "DONG"], id: \.self) { t in
                        if let n = state.status.fact[t], n > 0, let tier = Tier(rawValue: t) {
                            HStack(spacing: 2) {
                                TierChip(tier: tier)
                                Text("\(n)").font(.system(size: 11, design: .monospaced))
                            }
                        }
                    }
                }
            }

            muc("Chặng", state.status.chang, help: "Chặng làm việc suy ra từ kho, không do mô hình đoán")

            Button {
                state.selectedSurface = "history"
            } label: {
                HStack(spacing: 3) {
                    Image(systemName: state.status.stale > 0
                          ? "exclamationmark.triangle.fill" : "checkmark.circle")
                    Text("STALE \(state.status.stale)")
                }
                .font(.system(size: 11))
                .foregroundStyle(state.status.stale > 0 ? Color.staleAmber : .secondary)
            }
            .buttonStyle(.plain)
            .help(state.status.stale > 0
                  ? "Có hiện vật hạ nguồn cần cập nhật vì thượng nguồn đã đổi"
                  : "Không hiện vật nào cần cập nhật")

            muc("Bản ưng ý", state.status.snapshot ?? "chưa có",
                help: state.status.snapshot == nil
                    ? "Chưa ghi bản ưng ý nào"
                    : "cách đây \(state.status.khoang_cach_snapshot) changeset")

            Spacer()

            muc("Tự chủ", state.status.tu_chu, help: "Mức tự chủ: A3 = ghi tự do, chỉ cổng rủi ro mới hỏi")
            muc("Mô hình", state.status.mo_hinh, help: "Mô hình đang dùng")

            NganSachView()
            TokenView()
            DongHoNguCanh(nc: state.status.ngu_canh)

            Circle()
                .fill(state.connection.ok ? Color.okGreen : Color.gateRed)
                .frame(width: 7, height: 7)
                .help(state.connection.ok ? "Lõi đang chạy" : "Mất kết nối lõi")
        }
        .padding(.horizontal, 12).padding(.vertical, 5)
        .background(.bar)
    }

    private func muc(_ nhan: String, _ gia: String, help: String) -> some View {
        HStack(spacing: 4) {
            Text(nhan).font(.system(size: 10)).foregroundStyle(.secondary)
            Text(gia).font(.system(size: 11, weight: .medium)).lineLimit(1)
        }
        .help(help)
    }
}

// MARK: - Màn mở dự án

struct MoDuAnView: View {
    @EnvironmentObject var state: AppState
    @EnvironmentObject var setup: Setup
    @State private var loiTao: String?
    /// Nhịp kiểm lại xem các dự án trong danh sách có còn trên đĩa không.
    ///
    /// `FileManager.fileExists` gọi trong thân view chỉ chạy lại khi SwiftUI dựng lại view —
    /// mà xoá một thư mục ở Finder thì không có gì báo cho SwiftUI cả. Đo được: xoá dự án
    /// trong lúc màn này đang hiện thì dòng của nó vẫn xanh và vẫn bấm được. Nhịp hai giây
    /// chỉ chạy khi CHƯA mở dự án nào, tức là đúng lúc màn này hiện ra.
    @State private var nhip = 0
    private let dongHo = Timer.publish(every: 2, on: .main, in: .common).autoconnect()

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("EIDE").font(.system(size: 34, weight: .bold))
            Text("Môi trường phát triển nhúng có tác tử làm việc cùng anh.")
                .foregroundStyle(.secondary)

            GroupBox {
                VStack(alignment: .leading, spacing: 10) {
                    hang("Thư mục dự án", $setup.duAnPath, "Nơi tác tử được phép đọc/ghi — đây cũng là sandbox của nó.")
                    hang("Gốc mã nguồn EIDE", $setup.repoPath, "Thư mục chứa src/eide")
                    hang("Python", $setup.pythonPath, "Bỏ trống = dùng .venv/bin/python trong gốc mã nguồn")
                }
                .padding(6)
            }

            if let v = loiTao {
                Label(v, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(Color.gateRed).font(.callout)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let v = setup.vanDe {
                Label(v, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(Color.gateRed).font(.callout)
            }
            if case .hong(let m) = state.connection {
                Label(m, systemImage: "xmark.octagon.fill")
                    .foregroundStyle(Color.gateRed).font(.callout)
                    .textSelection(.enabled)
            }

            if !setup.ganDay.isEmpty { ganDayView }

            HStack {
                Button("Mở dự án") { Task { await moRoiGhiNho() } }
                .keyboardShortcut(.defaultAction)
                .disabled(!setup.hopLe)

                Button("Dự án mới…") { taoDuAnMoi() }

                if !state.coreLog.isEmpty {
                    Spacer()
                    Text(state.coreLog.suffix(3).joined())
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.tertiary).lineLimit(3)
                }
            }
            Spacer()
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .onReceive(dongHo) { _ in nhip &+= 1 }
        // Màn này trước đây không có nền của RIÊNG nó — nó mượn nền cửa sổ. Trên máy thì
        // trông vẫn đúng, nhưng `cacheDisplay` chỉ vẽ cây view, nên ảnh tự chụp ra
        // trắng-trên-trắng và không đọc được chữ nào. Cả cách kiểm của dự án này dựa vào
        // tấm ảnh ấy, nên một màn không chụp được là một màn không kiểm được.
        .background(.background)
    }

    /// Danh sách dự án gần đây.
    ///
    /// Dự án không còn trên đĩa vẫn được HIỆN, chỉ mờ đi và không bấm được, kèm nút "Quên".
    /// Lặng lẽ lọc nó ra thì người dùng thấy một mục biến mất và không biết vì sao — mà lý do
    /// thường là họ vừa đổi tên hay chuyển thư mục, tức là đúng lúc họ cần biết nhất.
    private var ganDayView: some View {
        GroupBox("Mở lại dự án gần đây") {
            VStack(alignment: .leading, spacing: 4) {
                ForEach(setup.ganDay, id: \.self) { d in
                    // `nhip` không được dùng để làm gì ngoài việc buộc dòng này tính lại —
                    // nếu bỏ nó đi, `fileExists` sẽ đóng băng ở lần dựng view đầu tiên.
                    let con = nhip >= 0 && FileManager.default.fileExists(atPath: d)
                    HStack(spacing: 8) {
                        Button {
                            setup.duAnPath = d
                            Task { await moRoiGhiNho() }
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: con ? "folder" : "questionmark.folder")
                                Text(URL(fileURLWithPath: d).lastPathComponent).bold()
                                Text(d).font(.caption).foregroundStyle(.tertiary)
                                    .lineLimit(1).truncationMode(.head)
                            }
                        }
                        .buttonStyle(.link)
                        .disabled(!con)
                        if !con {
                            Text("không còn ở đây").font(.caption)
                                .foregroundStyle(Color.staleAmber)
                        }
                        Spacer(minLength: 0)
                        Button("Quên") { setup.quen(d) }
                            .buttonStyle(.borderless).font(.caption)
                            .foregroundStyle(.tertiary)
                    }
                }
            }
            .padding(6)
        }
    }

    private func taoDuAnMoi() {
        let p = NSSavePanel()
        p.title = "Dự án EIDE mới"
        p.prompt = "Tạo"
        p.nameFieldLabel = "Tên dự án:"
        p.nameFieldStringValue = "du-an-moi"
        p.canCreateDirectories = true
        guard p.runModal() == .OK, let u = p.url else { return }
        do {
            try setup.taoDuAn(tai: u)
            Task { await moRoiGhiNho() }
        } catch {
            loiTao = error.localizedDescription
        }
    }

    /// Mở, rồi CHỈ ghi nhớ khi lõi đã bắt tay xong — xem `Setup.ghiNho`.
    private func moRoiGhiNho() async {
        loiTao = nil
        await state.mo(python: setup.pythonURL, repo: setup.repoURL, duAn: setup.duAnURL)
        if state.connection.ok { setup.ghiNho(setup.duAnPath) }
    }

    private func hang(_ nhan: String, _ gia: Binding<String>, _ goiY: String) -> some View {
        HStack(spacing: 8) {
            Text(nhan).frame(width: 150, alignment: .trailing).foregroundStyle(.secondary)
            TextField(goiY, text: gia).textFieldStyle(.roundedBorder)
            Button("Chọn…") { chonThuMuc(gia) }
        }
    }

    private func chonThuMuc(_ gia: Binding<String>) {
        let p = NSOpenPanel()
        p.canChooseDirectories = true
        // Không cho chọn TỆP. Ô này tên là "Thư mục dự án", và chọn nhầm `main.c` thì lõi
        // ném `NotADirectoryError: …/main.c/.eide` — một dòng người dùng không đọc được và
        // không sửa được. Chặn ngay ở chỗ chọn rẻ hơn nhiều so với giải thích về sau.
        p.canChooseFiles = false
        p.prompt = "Chọn thư mục"
        p.allowsMultipleSelection = false
        if p.runModal() == .OK, let u = p.url { gia.wrappedValue = u.path }
    }
}


/// Kéo cửa sổ về trong màn hình — **đúng một lần cho cả phiên**.
///
/// Cửa sổ thò ra ngoài mép màn hình làm panel hội thoại bị cắt, và người dùng đọc nó thành
/// một lỗi trình bày. Nhưng cách sửa cũng phải không gây hại: bản đầu gọi `setFrame` từ
/// trong `makeNSView` của một `NSViewRepresentable` nằm trong `.background()` của khung gốc —
/// đổi khung sinh ra một vòng bố cục, và **app treo ngay khi mở**, không mở nổi cả kênh kiểm
/// thử. Nên bây giờ: một cờ tĩnh, hoãn nửa giây, và không bao giờ chạy lần thứ hai.
enum DatCuaSo {
    private static var daLam = false

    static func motLan() {
        guard !daLam else { return }
        daLam = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            guard let w = NSApp.windows.first(where: { $0.isVisible && $0.canBecomeMain }),
                  let man = w.screen ?? NSScreen.main else { return }
            let vung = man.visibleFrame
            var f = w.frame
            if vung.contains(f) { return }
            f.size.width = min(f.width, vung.width)
            f.size.height = min(f.height, vung.height)
            f.origin.x = min(max(f.origin.x, vung.minX), vung.maxX - f.width)
            f.origin.y = min(max(f.origin.y, vung.minY), vung.maxY - f.height)
            w.setFrame(f, display: true)
        }
    }
}
