import SwiftUI

/// Vẽ sơ đồ mermaid thành hình, kèm nút **xem mã nguồn**.
///
/// ## Vì sao phải có nút mã, không chỉ có hình
///
/// Sơ đồ ở đây do **tác tử sinh ra**, và nó là một hiện vật như mọi hiện vật khác: người dùng
/// phải xem được thứ tác tử thật sự viết, không chỉ thứ giao diện vẽ lại. Ba lý do cụ thể:
///
/// * **Bố cục này không giống mermaid.** Ai nghi hình sai phải đọc được nguồn để tự phán.
/// * **Chép đi chỗ khác.** Dán vào tài liệu, vào GitHub, vào `doc.render` — đều cần nguyên văn.
/// * **Bộ đọc có tập con.** Nếu nó bỏ sót một dòng, chỉ nguồn mới cho thấy chỗ bị bỏ.
///
/// Mặc định hiện HÌNH, vì hình là thứ người đọc cần trước. Nút `{ }` đổi sang mã và ngược lại.
///
/// ## Vẽ bằng `Canvas`, không bằng `Shape` xếp chồng
///
/// Một sơ đồ tuần tự 7 vai × 15 bước là hàng trăm đoạn thẳng, mũi tên và nhãn. Dựng chúng
/// thành từng `View` sẽ tốn hàng trăm nút trong cây bố cục, mỗi lần cuộn tính lại một lần.
/// `Canvas` vẽ thẳng một lượt. Đổi lại: **chữ trong hình không bôi đen chép được** — và đó
/// chính là lý do nút mã ở trên không phải tuỳ chọn cho vui.

// MARK: - Khối sơ đồ trong markdown

struct SoDoView: View {
    let nguon: String
    var co: CGFloat = 12

    @State private var hienMa = false

    private var doc: SoDo? { DocSoDo.doc(nguon) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            thanh
            Divider()
            if doc != nil, !hienMa {
                ScrollView([.horizontal], showsIndicators: true) {
                    SoDoHinh(nguon: nguon).padding(10)
                }
            } else {
                if doc == nil {
                    // Nói thẳng chỗ giao diện chưa làm được. Im lặng hiện mã thô sẽ để người
                    // dùng tự đoán xem app hỏng hay sơ đồ sai — và đoán thì thường đoán nhầm.
                    Text("Giao diện chưa vẽ được kiểu sơ đồ `\(DocSoDo.kieu(nguon))` — dưới đây "
                         + "là nguyên văn mã tác tử viết.")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 8).padding(.top, 6)
                }
                Text(nguon)
                    .font(.system(size: co - 1, design: .monospaced))
                    .textSelection(.enabled)
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .background(Color(nsColor: .underPageBackgroundColor),
                    in: RoundedRectangle(cornerRadius: 5))
    }

    private var thanh: some View {
        HStack(spacing: 6) {
            Image(systemName: doc == nil ? "chevron.left.forwardslash.chevron.right"
                                         : bieuTuong)
                .font(.system(size: 9))
                .foregroundStyle(.tertiary)
            Text(doc?.tomTat ?? "mermaid · \(DocSoDo.kieu(nguon))")
                .font(.system(size: 9))
                .foregroundStyle(.tertiary)
            Spacer(minLength: 8)
            if doc != nil {
                Button(hienMa ? "Xem hình" : "Xem mã") { hienMa.toggle() }
                    .buttonStyle(.plain)
                    .font(.system(size: 9, weight: .medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(Color.secondary.opacity(0.12),
                                in: RoundedRectangle(cornerRadius: 4))
                    .help(hienMa ? "Quay lại hình vẽ"
                                 : "Xem nguyên văn mã mermaid tác tử đã viết — chép đi được")
            }
        }
        .padding(.horizontal, 8).padding(.vertical, 5)
    }

    private var bieuTuong: String {
        if case .tuanTu = doc { return "arrow.left.arrow.right" }
        return "square.grid.3x3.topleft.filled"
    }

}

/// Chỉ HÌNH, không thanh tiêu đề, không khung cuộn.
///
/// Tách ra vì hai nơi cần đúng phần này: khối trong hội thoại (bọc thêm khung cuộn) và bộ đo
/// khi vẽ sơ đồ ra PNG. Bản đầu vẽ thẳng trong `SoDoView` nên bộ đo phải chụp cả `ScrollView`
/// — và `ImageRenderer` trả về một khung **xám trơn**: thanh tiêu đề hiện đủ, hình mất sạch.
/// 18/18 ô xanh mà ảnh trống, vì mọi ô đều hỏi bộ ĐỌC chứ không ô nào hỏi bộ VẼ.
struct SoDoHinh: View {
    let nguon: String

    var body: some View {
        switch DocSoDo.doc(nguon) {
        case .tuanTu(let t): VeTuanTu(so: t)
        case .luong(let l): VeLuong(so: l)
        case nil: EmptyView()
        }
    }
}

// MARK: - Đo chữ

/// Đo bề rộng/cao chữ THẬT, không ước lượng theo số ký tự.
///
/// Nhãn trong sơ đồ EIDE là tiếng Việt có dấu và tên ký hiệu C lẫn lộn (`vTaskLCD (main.c)`).
/// Ước lượng "mỗi ký tự 6 pt" sẽ làm hộp hụt với chữ rộng và thừa với chữ hẹp — mà hộp hụt thì
/// chữ tràn ra ngoài viền, đúng thứ nhìn là thấy sai.
enum DoChu {
    static func co(_ s: String, _ cỡ: CGFloat, dam: Bool = false) -> CGSize {
        let f = NSFont.systemFont(ofSize: cỡ, weight: dam ? .semibold : .regular)
        var rong: CGFloat = 0
        let dong = s.components(separatedBy: .newlines)
        for d in dong {
            rong = max(rong, (d as NSString).size(withAttributes: [.font: f]).width)
        }
        return CGSize(width: ceil(rong), height: ceil(f.ascender - f.descender) * CGFloat(dong.count))
    }
}

// MARK: - Sơ đồ tuần tự

struct VeTuanTu: View {
    let so: SoDoTuanTu

    private let coChu: CGFloat = 10
    private let caoDau: CGFloat = 34          // hộp tên vai
    private let caoBuoc: CGFloat = 30         // một mũi tên
    private let caoMoKhoi: CGFloat = 20       // dòng mở `loop`/`alt`
    private let leTrai: CGFloat = 8
    private let khoangCot: CGFloat = 26       // đệm giữa hai cột

    /// Bề rộng từng cột = bề rộng lớn nhất trong {tên vai, các nhãn tin nhắn chạm vào nó}.
    private var rongCot: [CGFloat] {
        var r = so.vai.map { max(DoChu.co($0.nhan, coChu, dam: true).width + 16, 58) }
        for d in so.dong {
            if case .tin(let tu, let den, let chu, _) = d {
                let w = DoChu.co(chu, coChu - 1).width + 14
                // Nhãn nằm giữa hai cột, nên chia đôi cho hai bên — đủ chỗ mà không phình.
                let phan = w / 2
                r[tu] = max(r[tu], phan)
                r[den] = max(r[den], phan)
            }
        }
        return r
    }

    private var tamCot: [CGFloat] {
        var x = leTrai
        var ra: [CGFloat] = []
        for w in rongCot {
            ra.append(x + w / 2)
            x += w + khoangCot
        }
        return ra
    }

    private var tong: CGSize {
        let w = (tamCot.last ?? 0) + (rongCot.last ?? 0) / 2 + leTrai
        return CGSize(width: max(w, 200), height: caoDau + caoThan + 14)
    }

    /// Cao của phần thân, và vị trí y của từng dòng — tính một lần, dùng cho cả vẽ lẫn khung.
    private var viTriDong: [CGFloat] {
        var y = caoDau + 12
        var ra: [CGFloat] = []
        for d in so.dong {
            switch d {
            case .tin:
                y += caoBuoc
                ra.append(y)
            case .ghiChu(_, _, let chu):
                let h = DoChu.co(chu, coChu - 1).height + 14
                y += h / 2 + 6
                ra.append(y)
                y += h / 2 + 6
            case .moKhoi, .nhanhKhac:
                y += caoMoKhoi
                ra.append(y)
            case .dongKhoi:
                y += 8
                ra.append(y)
            }
        }
        return ra
    }

    private var caoThan: CGFloat { (viTriDong.last ?? caoDau) - caoDau + 18 }

    var body: some View {
        let cot = tamCot
        let rong = rongCot
        let yDong = viTriDong
        Canvas { ctx, _ in
            // 1. Đường đời từng vai — vẽ trước để mọi thứ khác nằm đè lên.
            for x in cot {
                var p = Path()
                p.move(to: CGPoint(x: x, y: caoDau))
                p.addLine(to: CGPoint(x: x, y: tong.height - 6))
                ctx.stroke(p, with: .color(.secondary.opacity(0.35)),
                           style: StrokeStyle(lineWidth: 1, dash: [3, 3]))
            }

            // 2. Khung khối `loop`/`alt` — vẽ trước mũi tên để không che chúng.
            var ngan: [(Int, CGFloat, String, String)] = []       // (chỉ số dòng, y, loại, nhãn)
            for (i, d) in so.dong.enumerated() {
                switch d {
                case .moKhoi(let loai, let nhan):
                    ngan.append((i, yDong[i], loai, nhan))
                case .dongKhoi:
                    guard let (_, yMo, loai, nhan) = ngan.popLast() else { break }
                    let khung = CGRect(x: leTrai / 2, y: yMo - 12,
                                       width: tong.width - leTrai, height: yDong[i] - yMo + 14)
                    ctx.stroke(Path(roundedRect: khung, cornerRadius: 4),
                               with: .color(.accentColor.opacity(0.45)), lineWidth: 1)
                    let nhanKhoi = nhan.isEmpty ? loai : "\(loai) \(nhan)"
                    ve(ctx, nhanKhoi, tai: CGPoint(x: khung.minX + 6, y: khung.minY + 8),
                       cỡ: coChu - 1, mau: .accentColor, canh: .leading, nen: true)
                default: break
                }
            }

            // 3. Tin nhắn, ghi chú, nhánh.
            var soThuTu = 0
            for (i, d) in so.dong.enumerated() {
                let y = yDong[i]
                switch d {
                case .tin(let tu, let den, let chu, let net):
                    soThuTu += 1
                    let nhanChu = so.danhSo ? "\(soThuTu). \(chu)" : chu
                    if tu == den {
                        veTuGoi(ctx, x: cot[tu], y: y, chu: nhanChu, net: net)
                    } else {
                        veMui(ctx, tu: cot[tu], den: cot[den], y: y, net: net)
                        ve(ctx, nhanChu, tai: CGPoint(x: (cot[tu] + cot[den]) / 2, y: y - 9),
                           cỡ: coChu - 1, mau: .primary, canh: .center, nen: true)
                    }
                case .ghiChu(let tu, let den, let chu):
                    let kt = DoChu.co(chu, coChu - 1)
                    let giua = (cot[tu] + cot[den]) / 2
                    let w = max(kt.width + 18, 60)
                    let r = CGRect(x: giua - w / 2, y: y - kt.height / 2 - 6,
                                   width: w, height: kt.height + 12)
                    ctx.fill(Path(roundedRect: r, cornerRadius: 3),
                             with: .color(.yellow.opacity(0.16)))
                    ctx.stroke(Path(roundedRect: r, cornerRadius: 3),
                               with: .color(.yellow.opacity(0.55)), lineWidth: 1)
                    ve(ctx, chu, tai: CGPoint(x: giua, y: y), cỡ: coChu - 1,
                       mau: .primary, canh: .center)
                case .nhanhKhac(let nhan):
                    var p = Path()
                    p.move(to: CGPoint(x: leTrai / 2, y: y - 8))
                    p.addLine(to: CGPoint(x: tong.width - leTrai / 2, y: y - 8))
                    ctx.stroke(p, with: .color(.accentColor.opacity(0.4)),
                               style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                    ve(ctx, nhan.isEmpty ? "khác" : nhan,
                       tai: CGPoint(x: leTrai / 2 + 6, y: y), cỡ: coChu - 1,
                       mau: .accentColor, canh: .leading, nen: true)
                default: break
                }
            }

            // 4. Hộp tên vai — vẽ SAU CÙNG để đường đời không cắt ngang chữ.
            for (i, v) in so.vai.enumerated() {
                let w = rong[i]
                let r = CGRect(x: cot[i] - w / 2, y: 4, width: w, height: caoDau - 8)
                ctx.fill(Path(roundedRect: r, cornerRadius: v.laNguoi ? 12 : 4),
                         with: .color(.accentColor.opacity(v.laNguoi ? 0.22 : 0.13)))
                ctx.stroke(Path(roundedRect: r, cornerRadius: v.laNguoi ? 12 : 4),
                           with: .color(.accentColor.opacity(0.5)), lineWidth: 1)
                ve(ctx, v.nhan, tai: CGPoint(x: cot[i], y: 4 + (caoDau - 8) / 2),
                   cỡ: coChu, mau: .primary, canh: .center, dam: true)
            }
        }
        .frame(width: tong.width, height: tong.height)
    }

    // ------------------------------------------------------------------ nét vẽ
    private func veMui(_ ctx: GraphicsContext, tu: CGFloat, den: CGFloat, y: CGFloat,
                       net: NetVe) {
        var p = Path()
        p.move(to: CGPoint(x: tu, y: y))
        p.addLine(to: CGPoint(x: den, y: y))
        ctx.stroke(p, with: .color(.primary.opacity(net == .dut ? 0.45 : 0.75)),
                   style: StrokeStyle(lineWidth: net == .dam ? 2 : 1.2,
                                      dash: net == .dut ? [4, 3] : []))
        veDauMui(ctx, tai: CGPoint(x: den, y: y), sangPhai: den > tu, net: net)
    }

    private func veTuGoi(_ ctx: GraphicsContext, x: CGFloat, y: CGFloat, chu: String,
                         net: NetVe) {
        // Tự gọi chính mình: một vòng nhỏ sang phải rồi quay lại.
        let w: CGFloat = 18
        var p = Path()
        p.move(to: CGPoint(x: x, y: y - 6))
        p.addLine(to: CGPoint(x: x + w, y: y - 6))
        p.addLine(to: CGPoint(x: x + w, y: y + 4))
        p.addLine(to: CGPoint(x: x, y: y + 4))
        ctx.stroke(p, with: .color(.primary.opacity(0.7)),
                   style: StrokeStyle(lineWidth: 1.2, dash: net == .dut ? [4, 3] : []))
        veDauMui(ctx, tai: CGPoint(x: x, y: y + 4), sangPhai: false, net: net)
        ve(ctx, chu, tai: CGPoint(x: x + w + 6, y: y - 1), cỡ: coChu - 1,
           mau: .primary, canh: .leading, nen: true)
    }

    private func veDauMui(_ ctx: GraphicsContext, tai: CGPoint, sangPhai: Bool, net: NetVe) {
        let d: CGFloat = sangPhai ? -5 : 5
        var p = Path()
        p.move(to: tai)
        p.addLine(to: CGPoint(x: tai.x + d, y: tai.y - 3.5))
        p.addLine(to: CGPoint(x: tai.x + d, y: tai.y + 3.5))
        p.closeSubpath()
        ctx.fill(p, with: .color(.primary.opacity(net == .dut ? 0.45 : 0.8)))
    }

    private func ve(_ ctx: GraphicsContext, _ s: String, tai: CGPoint, cỡ: CGFloat,
                    mau: Color, canh: HorizontalAlignment, dam: Bool = false,
                    nen: Bool = false) {
        guard !s.isEmpty else { return }
        var t = ctx.resolve(Text(s).font(.system(size: cỡ, weight: dam ? .semibold : .regular))
            .foregroundColor(mau))
        t.shading = .color(mau)
        let kt = t.measure(in: CGSize(width: 900, height: 400))
        let x: CGFloat = canh == .leading ? tai.x + kt.width / 2
            : (canh == .trailing ? tai.x - kt.width / 2 : tai.x)
        if nen {
            // Nền mờ dưới nhãn: không có nó, nhãn nằm trên đường đời sẽ bị nét đứt cắt ngang
            // và chữ tiếng Việt có dấu trở nên khó đọc hẳn.
            let r = CGRect(x: x - kt.width / 2 - 3, y: tai.y - kt.height / 2 - 1,
                           width: kt.width + 6, height: kt.height + 2)
            ctx.fill(Path(roundedRect: r, cornerRadius: 2),
                     with: .color(Color(nsColor: .underPageBackgroundColor).opacity(0.92)))
        }
        ctx.draw(t, at: CGPoint(x: x, y: tai.y), anchor: .center)
    }
}

// MARK: - Sơ đồ khối

struct VeLuong: View {
    let so: SoDoLuong

    private let coChu: CGFloat = 10
    private let demX: CGFloat = 34            // khoảng giữa hai tầng
    private let demY: CGFloat = 16            // khoảng giữa hai nút cùng tầng
    private let le: CGFloat = 10

    /// Cạnh LÙI — cạnh khép một vòng. Bỏ chúng ra khỏi phép xếp tầng.
    ///
    /// Sơ đồ thật gần như luôn có vòng: `Kỹ sư --> EIDE` và `EIDE --> Kỹ sư` là một vòng hai
    /// chiều, và trong sơ đồ mạch thì phản hồi với bus hai chiều cũng thế.
    ///
    /// Bản đầu chỉ chặn số vòng lặp cho khỏi treo. Nó không treo, nhưng nó **sai theo một kiểu
    /// khó thấy hơn**: hai nút trong vòng cứ đẩy tầng của nhau lên mỗi vòng lặp, nên khi chạm
    /// trần chúng nằm ở tầng 8–9 còn sáu nút lá dồn chung một tầng. Đo được 29/09/2026 trên sơ
    /// đồ C4 thật: mọi khối xếp thành MỘT HÀNG, nhãn chồng lên nhau. Cả 18 ô kiểm vẫn xanh —
    /// vì ô nào cũng hỏi bộ ĐỌC, không ô nào hỏi bộ VẼ.
    ///
    /// Cách đúng là cắt vòng trước: duyệt sâu, cạnh nào trỏ ngược về một nút **đang nằm trên
    /// ngăn xếp** là cạnh khép vòng.
    private var canhLui: Set<Int> {
        var trang = [Int](repeating: 0, count: so.nut.count)   // 0 chưa thăm · 1 đang · 2 xong
        var lui: Set<Int> = []
        var ke: [[Int]] = Array(repeating: [], count: so.nut.count)
        for (i, c) in so.canh.enumerated() where c.tu < so.nut.count && c.den < so.nut.count {
            ke[c.tu].append(i)
        }
        func sau(_ v: Int) {
            trang[v] = 1
            for i in ke[v] {
                let d = so.canh[i].den
                if trang[d] == 1 { lui.insert(i) }
                else if trang[d] == 0 { sau(d) }
            }
            trang[v] = 2
        }
        for v in 0..<so.nut.count where trang[v] == 0 { sau(v) }
        return lui
    }

    /// Tầng của từng nút: đường dài nhất từ một nút không ai trỏ tới, tính trên đồ thị ĐÃ CẮT
    /// VÒNG nên phép lặp chắc chắn dừng.
    private var tang: [Int] {
        let lui = canhLui
        var t = [Int](repeating: 0, count: so.nut.count)
        for _ in 0..<so.nut.count {
            var doi = false
            for (i, c) in so.canh.enumerated() where !lui.contains(i) {
                guard c.tu < t.count, c.den < t.count else { continue }
                if t[c.den] < t[c.tu] + 1 { t[c.den] = t[c.tu] + 1; doi = true }
            }
            if !doi { break }
        }
        return t
    }

    /// Bề rộng/cao nhãn lớn nhất trên các cạnh chạm vào một nút.
    ///
    /// Không tính chỗ cho nhãn thì chúng vẽ ở giữa hai nút và **đè lên nhau** — sáu cạnh cùng
    /// đi ra từ một nút là sáu nhãn cùng một dải. Nhãn đè nhau thì không nhãn nào đọc được.
    private var choNhan: [CGSize] {
        var ra = [CGSize](repeating: .zero, count: so.nut.count)
        for c in so.canh where !c.nhan.isEmpty {
            let kt = DoChu.co(c.nhan, coChu - 2)
            for i in [c.tu, c.den] where i < ra.count {
                ra[i] = CGSize(width: max(ra[i].width, kt.width),
                               height: max(ra[i].height, kt.height))
            }
        }
        return ra
    }

    private struct O {
        var khung: CGRect
        let nut: SoDoLuong.Nut
    }

    /// Vị trí mọi nút. `ngang == true` thì tầng chạy sang phải, ngược lại chạy xuống.
    private var bo: (o: [O], co: CGSize) {
        let t = tang
        let soTang = (t.max() ?? 0) + 1
        var theoTang: [[Int]] = Array(repeating: [], count: soTang)
        for (i, x) in t.enumerated() { theoTang[x].append(i) }

        var kt: [CGSize] = so.nut.map {
            let c = DoChu.co($0.nhan, coChu, dam: true)
            return CGSize(width: max(c.width + 20, 54), height: max(c.height + 14, 28))
        }
        // Nút tròn phải là hình tròn, nên lấy cạnh lớn hơn cho cả hai chiều.
        for (i, n) in so.nut.enumerated() where n.hinh == .tron {
            let c = max(kt[i].width, kt[i].height)
            kt[i] = CGSize(width: c, height: c)
        }

        let nhan = choNhan
        var o: [O] = so.nut.map { O(khung: .zero, nut: $0) }

        // Kích thước ô của từng nút theo trục NGANG của tầng (trục vuông góc với hướng chảy).
        func oNgang(_ i: Int) -> CGFloat {
            so.ngang ? max(kt[i].height, nhan[i].height) : max(kt[i].width, nhan[i].width)
        }

        // Thứ tự cụm, để nút cùng một `subgraph` nằm LIỀN NHAU trong mỗi tầng.
        //
        // Không có nó thì tầng xếp thuần theo "tâm của các con", nút hai cụm đan xen nhau, và
        // khung cụm — vốn là HỢP của các ô thành viên — chồng lên nhau. Đo được trên sơ đồ
        // mô-đun RTOS: `main.c` thuộc cụm `firmware` nằm lọt vào giữa khung `firmware/rtos`,
        // nhìn ra thành "main.c ở trong thư mục rtos". Một sơ đồ nói sai về cấu trúc thư mục
        // thì tệ hơn không có sơ đồ.
        //
        // Nút không thuộc cụm nào nhận `Int.max` nên xếp cuối, không cắt đôi một cụm. Sơ đồ
        // không có cụm nào thì mọi khoá bằng nhau và phép xếp theo tâm vẫn quyết định như cũ.
        func cum(_ i: Int) -> Int { so.nut[i].cum ?? Int.max }

        // 1. Xếp tầng CUỐI trước, sát nhau.
        var giua = [CGFloat](repeating: 0, count: so.nut.count)
        let demNgang: CGFloat = so.ngang ? demY : demX
        func xep(_ hang: [Int], theoThuTu: [Int]) {
            var x = le
            for i in theoThuTu {
                giua[i] = x + oNgang(i) / 2
                x += oNgang(i) + demNgang
            }
        }
        if let cuoi = theoTang.last {
            xep(cuoi, theoThuTu: cuoi.sorted { cum($0) == cum($1) ? $0 < $1 : cum($0) < cum($1) })
        }

        // 2. Ngược lên: mỗi nút CĂN GIỮA theo các nút nó trỏ tới.
        //
        // Không có bước này thì nút tầng trên dán mép trái, và sáu cạnh cùng xoè ra từ một
        // điểm ở rìa — đo được trên sơ đồ C4 thật: đường nối cắt ngang cả hình, nhãn dồn một
        // chỗ. Ba tầng đúng vẫn có thể là một hình không đọc được.
        let lui = canhLui
        var con: [[Int]] = Array(repeating: [], count: so.nut.count)
        for (k, c) in so.canh.enumerated() where !lui.contains(k) {
            guard c.tu < so.nut.count, c.den < so.nut.count else { continue }
            con[c.tu].append(c.den)
        }
        for li in stride(from: theoTang.count - 2, through: 0, by: -1) {
            let hang = theoTang[li]
            var muon: [(Int, CGFloat)] = hang.map { i in
                let ds = con[i].filter { tang[$0] > li }
                let m = ds.isEmpty ? CGFloat(0) : ds.map { giua[$0] }.reduce(0, +) / CGFloat(ds.count)
                return (i, ds.isEmpty ? .greatestFiniteMagnitude : m)
            }
            // Cụm trước, rồi mới tới tâm mong muốn: giữ nút cùng `subgraph` liền nhau.
            // Nút không có con thì xếp cuối hàng, giữ nguyên thứ tự khai báo.
            muon.sort {
                if cum($0.0) != cum($1.0) { return cum($0.0) < cum($1.0) }
                return $0.1 == $1.1 ? $0.0 < $1.0 : $0.1 < $1.1
            }
            // Đặt theo thứ tự mong muốn nhưng KHÔNG cho chồng lên nhau.
            var x = le
            for (i, m) in muon {
                let nua = oNgang(i) / 2
                let tam = max(x + nua, m == .greatestFiniteMagnitude ? x + nua : m)
                giua[i] = tam
                x = tam + nua + demNgang
            }
        }

        // 3. Dồn về sát lề rồi đổi tâm thành khung thật.
        let doi = (giua.enumerated().map { $1 - oNgang($0) / 2 }.min() ?? le) - le
        var chay = le
        var toiDaNgang: CGFloat = 0
        var toiDaDoc: CGFloat = 0
        for hang in theoTang {
            let dayTang = hang.map { so.ngang ? kt[$0].width : kt[$0].height }.max() ?? 0
            // Nhân 2,4: nhãn xếp so le BA BẬC (xem chỗ vẽ đường nối), nên khoảng giữa hai
            // tầng phải chứa được cả ba bậc chứ không chỉ một nhãn.
            let demTang = (hang.map { so.ngang ? nhan[$0].width : nhan[$0].height }.max() ?? 0)
                * (hang.contains { !con[$0].isEmpty } ? 2.4 : 1)
            for i in hang {
                let t = giua[i] - doi
                if so.ngang {
                    o[i].khung = CGRect(x: chay + (dayTang - kt[i].width) / 2,
                                        y: t - kt[i].height / 2,
                                        width: kt[i].width, height: kt[i].height)
                } else {
                    o[i].khung = CGRect(x: t - kt[i].width / 2,
                                        y: chay + (dayTang - kt[i].height) / 2,
                                        width: kt[i].width, height: kt[i].height)
                }
                toiDaNgang = max(toiDaNgang, t + oNgang(i) / 2 + le)
            }
            chay += dayTang + demNgang + demTang
            toiDaDoc = max(toiDaDoc, chay)
        }

        // Chừa chỗ cho NHÃN cụm. Khung `subgraph` vươn lên trên nút cao nhất 16 px (inset 8 +
        // đẩy 8 để nhét nhãn), mà khổ hình chỉ tính tới lề `le` = 10 — nên nhãn `firmware`
        // bị cắt mất nửa trên ở mép trước khi hình kịp bắt đầu. Thấy trên ảnh chụp tab Thiết
        // kế; không con số nào của bộ quét bắt được, vì hình vẫn "vẽ được".
        let deNhan: CGFloat = so.cum.isEmpty ? 0 : 18
        if deNhan > 0 {
            for i in o.indices { o[i].khung.origin.y += deNhan }
        }
        let w = so.ngang ? toiDaDoc + le : toiDaNgang + le
        let h = (so.ngang ? toiDaNgang + le : toiDaDoc + le) + deNhan
        return (o, CGSize(width: max(w, 180), height: max(h, 70)))
    }

    var body: some View {
        let (o, kt) = bo
        Canvas { ctx, _ in
            // 1. Khung cụm `subgraph`, vẽ dưới cùng.
            for (ci, c) in so.cum.enumerated() {
                let trong = o.filter { $0.nut.cum == ci }.map(\.khung)
                guard !trong.isEmpty else { continue }
                var k = trong.reduce(trong[0]) { $0.union($1) }
                k = k.insetBy(dx: -8, dy: -8)
                k.origin.y -= 8
                k.size.height += 8
                ctx.fill(Path(roundedRect: k, cornerRadius: 6),
                         with: .color(.accentColor.opacity(0.06)))
                ctx.stroke(Path(roundedRect: k, cornerRadius: 6),
                           with: .color(.accentColor.opacity(0.35)),
                           style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                chu(ctx, c.nhan, tai: CGPoint(x: k.minX + 6, y: k.minY + 7), cỡ: coChu - 2,
                    mau: .accentColor, canh: .leading)
            }

            // 2. Đường nối. Nhãn chỉ GOM lại ở đây, đặt ở bước 4.
            var canNhan: [(String, CGPoint, CGPoint)] = []
            for c in so.canh {
                guard c.tu < o.count, c.den < o.count else { continue }
                let a = o[c.tu].khung, b = o[c.den].khung
                let (p1, p2) = diem(a, b)
                var p = Path()
                p.move(to: p1)
                // Cong nhẹ: hai nút không cùng hàng mà nối thẳng sẽ cắt qua nút thứ ba.
                let giua = CGPoint(x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2)
                p.addQuadCurve(to: p2, control: so.ngang
                               ? CGPoint(x: giua.x, y: p1.y)
                               : CGPoint(x: p1.x, y: giua.y))
                ctx.stroke(p, with: .color(.primary.opacity(c.net == .dut ? 0.4 : 0.6)),
                           style: StrokeStyle(lineWidth: c.net == .dam ? 2 : 1.2,
                                              dash: c.net == .dut ? [4, 3] : []))
                mui(ctx, tai: p2, tu: p1)
                if !c.nhan.isEmpty { canNhan.append((c.nhan, p1, p2)) }
            }

            // 3. Nút.
            for x in o {
                let k = x.khung
                let duong: Path
                switch x.nut.hinh {
                case .tron: duong = Path(ellipseIn: k)
                case .bau: duong = Path(roundedRect: k, cornerRadius: k.height / 2)
                case .thoi: duong = thoiPath(k)
                case .hop: duong = Path(roundedRect: k, cornerRadius: 5)
                }
                ctx.fill(duong, with: .color(.accentColor.opacity(0.14)))
                ctx.stroke(duong, with: .color(.accentColor.opacity(0.6)), lineWidth: 1.2)
                chu(ctx, x.nut.nhan, tai: CGPoint(x: k.midX, y: k.midY), cỡ: coChu,
                    mau: .primary, canh: .center, dam: true)
            }

            // 4. Nhãn đường nối — đặt SAU CÙNG, và TRÁNH NHAU thật sự.
            //
            // Hai cách trước đều chưa đủ: đặt ở chính giữa thì sáu cạnh cùng nguồn có sáu
            // điểm giữa trùng nhau; rải so le ba bậc thì đỡ hơn nhưng vẫn còn vài chỗ cắt.
            // Cách này thử vài vị trí dọc đường và lấy chỗ đầu tiên không chạm nhãn đã đặt.
            //
            // Không chỗ nào trống thì vẫn VẼ ở chỗ cuối cùng, không bỏ nhãn: một nhãn hơi
            // chồng còn đọc mò được, một nhãn biến mất thì người đọc không biết là đã mất.
            // Gieo sẵn KHUNG CÁC NÚT vào danh sách "đã chiếm chỗ".
            //
            // Bản trước chỉ tránh nhãn khác, nên nhãn rơi đè lên hộp khối — nhìn trong app
            // thấy `VCC / GND` nằm chồng lên chữ `Khối vi điều khiển`. Nhãn tránh nhãn mà
            // không tránh nút thì mới giải quyết được nửa vấn đề.
            var daDat: [CGRect] = o.map(\.khung)
            for (nhanCanh, p1, p2) in canNhan {
                var t = ctx.resolve(Text(nhanCanh).font(.system(size: coChu - 2))
                    .foregroundColor(.secondary))
                t.shading = .color(.secondary)
                let kt = t.measure(in: CGSize(width: 900, height: 400))
                var dat = CGRect.zero
                for ti in [0.5, 0.66, 0.36, 0.8, 0.22] as [CGFloat] {
                    let c = CGPoint(x: p1.x + (p2.x - p1.x) * ti,
                                    y: p1.y + (p2.y - p1.y) * ti)
                    dat = CGRect(x: c.x - kt.width / 2 - 3, y: c.y - kt.height / 2 - 1,
                                 width: kt.width + 6, height: kt.height + 2)
                    if !daDat.contains(where: { $0.intersects(dat) }) { break }
                }
                daDat.append(dat)
                ctx.fill(Path(roundedRect: dat, cornerRadius: 2),
                         with: .color(Color(nsColor: .underPageBackgroundColor).opacity(0.95)))
                ctx.draw(t, at: CGPoint(x: dat.midX, y: dat.midY), anchor: .center)
            }
        }
        .frame(width: kt.width, height: kt.height)
    }

    /// Hai điểm nối trên biên hai nút, chọn theo hướng chảy của sơ đồ.
    private func diem(_ a: CGRect, _ b: CGRect) -> (CGPoint, CGPoint) {
        if so.ngang {
            return (CGPoint(x: a.maxX, y: a.midY), CGPoint(x: b.minX, y: b.midY))
        }
        return (CGPoint(x: a.midX, y: a.maxY), CGPoint(x: b.midX, y: b.minY))
    }

    private func thoiPath(_ k: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: k.midX, y: k.minY))
        p.addLine(to: CGPoint(x: k.maxX, y: k.midY))
        p.addLine(to: CGPoint(x: k.midX, y: k.maxY))
        p.addLine(to: CGPoint(x: k.minX, y: k.midY))
        p.closeSubpath()
        return p
    }

    private func mui(_ ctx: GraphicsContext, tai: CGPoint, tu: CGPoint) {
        let dx = tai.x - tu.x, dy = tai.y - tu.y
        let d = max(sqrt(dx * dx + dy * dy), 0.001)
        let ux = dx / d, uy = dy / d
        let goc = CGPoint(x: tai.x - ux * 7, y: tai.y - uy * 7)
        var p = Path()
        p.move(to: tai)
        p.addLine(to: CGPoint(x: goc.x - uy * 3.5, y: goc.y + ux * 3.5))
        p.addLine(to: CGPoint(x: goc.x + uy * 3.5, y: goc.y - ux * 3.5))
        p.closeSubpath()
        ctx.fill(p, with: .color(.primary.opacity(0.7)))
    }

    private func chu(_ ctx: GraphicsContext, _ s: String, tai: CGPoint, cỡ: CGFloat,
                     mau: Color, canh: HorizontalAlignment, dam: Bool = false,
                     nen: Bool = false) {
        guard !s.isEmpty else { return }
        var t = ctx.resolve(Text(s).font(.system(size: cỡ, weight: dam ? .semibold : .regular))
            .foregroundColor(mau))
        t.shading = .color(mau)
        let kt = t.measure(in: CGSize(width: 900, height: 400))
        let x = canh == .leading ? tai.x + kt.width / 2 : tai.x
        if nen {
            let r = CGRect(x: x - kt.width / 2 - 3, y: tai.y - kt.height / 2 - 1,
                           width: kt.width + 6, height: kt.height + 2)
            ctx.fill(Path(roundedRect: r, cornerRadius: 2),
                     with: .color(Color(nsColor: .underPageBackgroundColor).opacity(0.92)))
        }
        ctx.draw(t, at: CGPoint(x: x, y: tai.y), anchor: .center)
    }
}
