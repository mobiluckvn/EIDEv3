import XCTest
@testable import EIDE

/// Bộ dựng Markdown của Console — phần LOGIC THUẦN.
///
/// Ba việc anh Công nêu về giao diện đều kết thúc bằng cùng một câu trong sổ việc: *"không con
/// số nào bắt được chuyện này, phải nhìn màn hình"*. Câu ấy đúng với bề rộng cột và màu sắc.
/// Nhưng phần **tách khối, tách ô, đổi ký hiệu** là hàm thuần — vào chuỗi, ra chuỗi — và kiểm
/// được bằng số.
///
/// Mọi ca ở đây hỏi đúng câu người dùng hỏi: *"trên màn hình còn dấu Markdown thô không?"*,
/// bằng cách kiểm trên `chuThuan()` — chữ SAU KHI dựng — chứ không kiểm trên chuỗi gốc.
final class MarkdownTests: XCTestCase {

    // =============================================================== rà hết ký hiệu
    //
    // Mục 2 sổ việc: *"Markdown chưa render ** cần phải review đảm bảo render toàn bộ các ký
    // hiệu."* Nên ca ở đây đi theo bảng, từng ký hiệu một, và mỗi ca khẳng định hai điều: chữ
    // còn đủ, và DẤU CÚ PHÁP không còn trên màn.

    private func thay(_ raw: String) -> String { Markdown.chuThuan(raw) }

    func test_dam_nghieng_ma_lien_ket_khong_con_dau() {
        for (vao, chu, dau) in [
            ("**đậm**", "đậm", "*"),
            ("*nghiêng*", "nghiêng", "*"),
            ("_nghiêng_", "nghiêng", "_"),
            ("`mã`", "mã", "`"),
            ("~~gạch~~", "gạch", "~"),
            ("[nhãn](http://a.b)", "nhãn", "]"),
        ] {
            let ra = thay(vao)
            XCTAssertTrue(ra.contains(chu), "mất chữ với “\(vao)” → “\(ra)”")
            XCTAssertFalse(ra.contains(dau), "còn dấu “\(dau)” trên màn với “\(vao)” → “\(ra)”")
        }
    }

    func test_chu_long_kieu_khong_lot_dau_sao() {
        // Đây là ca của bài học `tach_chu()`: một `finditer` phẳng cho cả ba kiểu làm
        // `*Đề tài: **Phát triển…** · Vũ Trí Công*` in ra thành `*Đề tài: Phát triển…`.
        let ra = thay("*Đề tài: **Phát triển EIDE** · Vũ Trí Công*")
        XCTAssertFalse(ra.contains("*"), "còn dấu sao: “\(ra)”")
        XCTAssertTrue(ra.contains("Phát triển EIDE"))
        XCTAssertTrue(ra.contains("Vũ Trí Công"))
    }

    func test_dam_trong_nghieng_va_nguoc_lai() {
        for vao in ["**a *b* c**", "*a **b** c*", "**`mã` trong đậm**"] {
            let ra = thay(vao)
            XCTAssertFalse(ra.contains("*"), "còn dấu sao với “\(vao)” → “\(ra)”")
        }
    }

    func test_tieu_de_sau_muc() {
        for n in 1...6 {
            let dau = String(repeating: "#", count: n)
            let k = Markdown.tach("\(dau) Mục \(n)")
            guard case .tieuDe(let muc, let chu) = k.first else {
                return XCTFail("mức \(n) không thành tiêu đề: \(k)")
            }
            XCTAssertEqual(muc, n)
            XCTAssertEqual(chu, "Mục \(n)")
        }
        // Bảy dấu thăng KHÔNG phải tiêu đề — Markdown chỉ có sáu mức.
        if case .tieuDe = Markdown.tach("####### bảy").first {
            XCTFail("bảy dấu thăng không được thành tiêu đề")
        }
    }

    func test_danh_sach_long_nhau_dem_rieng_tung_muc() {
        let k = Markdown.tach("""
        1. một
          - con a
          - con b
        2. hai
        """)
        guard case .danhSach(let muc) = k.first else { return XCTFail("không thành danh sách") }
        XCTAssertEqual(muc.count, 4)
        XCTAssertEqual(Markdown.soThuTu(muc), [1, 0, 0, 2],
                       "mục 2 phải là 2, không phải 4 — người đọc sẽ tưởng tác tử đếm nhầm")
    }

    func test_trich_dan_nhieu_dong_gop_thanh_mot_khoi() {
        let k = Markdown.tach("> dòng một\n> dòng hai")
        guard case .trichDan(let d) = k.first else { return XCTFail("không thành trích dẫn") }
        XCTAssertEqual(d, ["dòng một", "dòng hai"])
    }

    func test_khoi_ma_giu_nguyen_van_khong_dung_markdown() {
        let k = Markdown.tach("```swift\nlet a = **b**\n```")
        guard case .ma(let than, let nn) = k.first else { return XCTFail("không thành khối mã") }
        XCTAssertEqual(nn, "swift")
        XCTAssertEqual(than, "let a = **b**", "khối mã phải giữ nguyên dấu, không được dựng")
    }

    func test_duong_ke() {
        for vao in ["---", "***", "___", "-----"] {
            guard case .duongKe = Markdown.tach(vao).first else {
                return XCTFail("“\(vao)” không thành đường kẻ")
            }
        }
    }

    func test_khong_hieu_thi_in_nguyen_van_khong_nuot() {
        // N6: không bao giờ nuốt nội dung. Một dấu `**` không đóng thì phải còn chữ.
        let ra = thay("một **câu chưa đóng dấu")
        XCTAssertTrue(ra.contains("câu chưa đóng dấu"), "nuốt mất nội dung: “\(ra)”")
    }

    // =============================================================== bảng
    //
    // Mục 5 sổ việc: bốn lỗi cụ thể trong `BangMd`. Ba trong bốn kiểm được ở đây.

    private func bang(_ raw: String) -> ([String], [[String]])? {
        for k in Markdown.tach(raw) { if case .bang(let c, let h) = k { return (c, h) } }
        return nil
    }

    func test_bang_hang_thieu_o_phai_duoc_san_cho_bang_tieu_de() {
        // Lỗi 5.1: `BangMd` vẽ theo SỐ Ô CỦA HÀNG, không theo số cột của tiêu đề. Hàng thiếu
        // ô thì vẽ thiếu cột, hàng thừa ô thì tràn ra ngoài tiêu đề.
        guard let (cot, hang) = bang("""
        | a | b | c |
        |---|---|---|
        | 1 | 2 |
        | 1 | 2 | 3 | 4 |
        """) else { return XCTFail("không nhận ra bảng") }
        XCTAssertEqual(cot.count, 3)
        for (i, h) in hang.enumerated() {
            XCTAssertEqual(h.count, cot.count,
                           "hàng \(i) có \(h.count) ô, tiêu đề có \(cot.count) — hàng sẽ lệch cột")
        }
        XCTAssertEqual(hang[0], ["1", "2", ""], "ô thiếu phải thành ô rỗng")
        XCTAssertEqual(hang[1], ["1", "2", "3"], "ô thừa phải bị bỏ, không tràn ra ngoài")
    }

    func test_bang_dau_gach_doc_trong_ma_khong_duoc_cat_o() {
        // Lỗi 5.2: `oCua` cắt theo MỌI dấu `|`, kể cả dấu trong dấu nháy ngược.
        guard let (_, hang) = bang("""
        | lệnh | nghĩa |
        |---|---|
        | `a|b` | hoặc |
        """) else { return XCTFail("không nhận ra bảng") }
        XCTAssertEqual(hang[0].count, 2,
                       "ô chứa `a|b` bị cắt thành hai ô → hàng lệch cột. Ra: \(hang[0])")
        XCTAssertEqual(hang[0][0], "`a|b`")
    }

    func test_bang_dau_gach_doc_da_thoat_khong_duoc_cat_o() {
        guard let (_, hang) = bang("""
        | ký hiệu | nghĩa |
        |---|---|
        | a \\| b | hoặc |
        """) else { return XCTFail("không nhận ra bảng") }
        XCTAssertEqual(hang[0].count, 2, "dấu `\\|` đã thoát mà vẫn cắt ô. Ra: \(hang[0])")
        XCTAssertEqual(hang[0][0], "a | b", "dấu thoát phải thành dấu thật khi hiện ra")
    }

    func test_be_rong_cot_dem_chu_HIEN_RA_khong_dem_ma_nguon() {
        // Lỗi 5.3: ô `**ĐẠT**` dài 7 ký tự trong mã mà chỉ hiện 3 chữ. Cột nào nhiều chữ đậm
        // sẽ được cấp bề rộng cho cả dấu Markdown mà người đọc không thấy.
        XCTAssertEqual(Markdown.daiHienRa("**ĐẠT**"), 3,
                       "đếm 7 tức là đếm cả dấu sao người đọc không thấy")
        XCTAssertEqual(Markdown.daiHienRa("`mã`"), 2)
        XCTAssertEqual(Markdown.daiHienRa("[nhãn](http://rất-dài.example.com)"), 4,
                       "đích liên kết không hiện ra thì không được tính vào bề rộng")
        XCTAssertEqual(Markdown.daiHienRa("thường"), 6)
    }

    func test_be_rong_cot_do_HET_hang_khong_chi_20_hang_dau() {
        // Lỗi 5.4: `hang.prefix(20)`. Bảng tuân thủ của dự án robot có 109 hàng.
        var dong = ["| a | b |", "|---|---|"]
        for i in 1...30 { dong.append("| \(i) | x |") }
        dong.append("| \(String(repeating: "D", count: 40)) | x |")
        guard let (cot, hang) = bang(dong.joined(separator: "\n")) else {
            return XCTFail("không nhận ra bảng")
        }
        XCTAssertEqual(hang.count, 31)
        XCTAssertEqual(Markdown.daiOToiDa(cot: cot, hang: hang, j: 0), 40,
                       "ô dài nhất ở hàng 31 — đo 20 hàng đầu thì không thấy")
    }

    // =============================================================== công thức
    //
    // Mục 1 sổ việc nói công thức "chưa hề được nối vào" bộ dựng Swift. Kiểm xem còn đúng không.

    func test_cong_thuc_trong_dong_doi_thanh_ky_hieu() {
        let ra = thay("Ngưỡng là $\\alpha \\le 0.05$ nên đạt.")
        XCTAssertFalse(ra.contains("\\alpha"), "còn lệnh TeX thô trên màn: “\(ra)”")
        XCTAssertFalse(ra.contains("$"), "còn dấu đô la trên màn: “\(ra)”")
        XCTAssertTrue(ra.contains("α"), "không đổi được \\alpha: “\(ra)”")
        XCTAssertTrue(ra.contains("≤"), "không đổi được \\le: “\(ra)”")
    }

    func test_cong_thuc_dung_rieng_thanh_khoi() {
        guard case .congThuc(let s, let tron) = Markdown.tach("$$E = mc^2$$").first else {
            return XCTFail("`$$…$$` không thành khối công thức")
        }
        XCTAssertTrue(tron, "phải đổi trọn vẹn: “\(s)”")
        XCTAssertTrue(s.contains("²"), "không đổi được số mũ: “\(s)”")
    }

    func test_rao_math_cung_thanh_cong_thuc() {
        let k = Markdown.tach("```math\n\\sum_{i=1}^{n} x_i\n```")
        if case .ma = k.first {
            XCTFail("rào ```math phải thành công thức, không phải khối mã")
        }
    }
}

/// Đổi LaTeX sang Unicode — phía Swift.
///
/// Ca quan trọng nhất là ca cuối: một lệnh ta CHƯA BIẾT không được bị cắt đầu. Nếu bị, phép
/// kiểm "còn gạch chéo nghĩa là còn lệnh chưa hiểu" mất tác dụng, và khối công thức hiện một
/// kết quả sai thay vì hiện nguyên bản kèm dòng cảnh báo.
final class MathTextTests: XCTestCase {

    func test_doi_duoc_ky_hieu_thuong_gap() {
        for (tex, chu) in [("\\alpha \\le 0.05", "α ≤ 0.05"),
                           ("\\sum x", "∑ x"),
                           ("\\Sigma \\ne \\sum", "Σ ≠ ∑"),
                           ("\\left( a \\right)", "( a )")] {
            let (ra, tron) = MathText.sangUnicode(tex)
            XCTAssertTrue(tron, "chưa đổi trọn vẹn: “\(ra)”")
            XCTAssertEqual(ra, chu)
        }
    }

    func test_lenh_dau_cau_doi_duoc_khi_co_chu_dung_sau() {
        // `a\,b` là cách dùng thường. Chốt `(?![A-Za-z])` áp cho nhóm này thì nó không đổi.
        for tex in ["a\\,b", "a\\;b", "a\\:b", "a\\!b"] {
            let (ra, tron) = MathText.sangUnicode(tex)
            XCTAssertTrue(tron, "“\(tex)” không đổi được: “\(ra)”")
            XCTAssertFalse(ra.contains("\\"), "“\(tex)” → “\(ra)”")
        }
    }

    func test_lenh_CHUA_BIET_khong_duoc_cat_dau() {
        // `\alphabet` không phải `\alpha` theo sau `bet`. Cắt đầu thì chữ sai, VÀ phép kiểm
        // cuối hàm mất tác dụng vì gạch chéo đã bị ăn mất.
        for tex in ["\\alphabet", "\\leftroot", "\\sumtotal"] {
            let (ra, tron) = MathText.sangUnicode(tex)
            XCTAssertFalse(tron,
                "“\(tex)” là lệnh chưa biết, phải báo CHƯA trọn vẹn để khối hiện nguyên bản "
                + "— nhưng nó báo đã xong với “\(ra)”")
            XCTAssertTrue(ra.contains("\\"), "“\(tex)” → “\(ra)”: mất gạch chéo là mất chốt")
        }
    }

    func test_lenh_dai_khong_bi_lenh_ngan_an_mat_dau() {
        for (tex, co) in [("\\leftarrow", "←"), ("\\leftrightarrow", "↔"),
                          ("\\leq", "≤"), ("\\Leftrightarrow", "⇔")] {
            let (ra, _) = MathText.sangUnicode(tex)
            XCTAssertEqual(ra, co, "“\(tex)” bị cắt thành “\(ra)”")
        }
    }
}

/// Công thức giữa dòng so với dấu TIỀN — và chỗ bộ kiểm của tôi bỏ lọt.
///
/// Anh Công thấy câu này trên màn hình ngày 02/10/2026, sau khi tôi đã báo xong việc công thức:
///
///     Với kiểu I8: giá trị trong $[-128, 127]$, acc_t là int32_t.
///
/// Hai dấu đô-la còn nguyên. Luật cũ của Swift đòi công thức phải có lệnh `\`, hoặc chữ cái,
/// hoặc `^`/`_` — `[-128, 127]` **không có thứ nào**.
///
/// Và ca kiểm tôi viết lượt trước thử `$\alpha \le 0.05$`, một công thức **có lệnh TeX**, nên
/// nó xanh với cả luật cũ. Phải có một ca không chứa lệnh nào mới thấy.
final class CongThucGiuaDongTests: XCTestCase {

    private func thay(_ s: String) -> String { Markdown.chuThuan(s) }

    func test_cau_anh_Cong_thay_tren_man_hinh() {
        let ra = thay("Với kiểu I8: giá trị trong $[-128, 127]$, acc_t là int32_t.")
        XCTAssertFalse(ra.contains("$"), "còn dấu đô-la trên màn: “\(ra)”")
        XCTAssertTrue(ra.contains("[-128, 127]"), "mất nội dung công thức: “\(ra)”")
        XCTAssertTrue(ra.contains("int32_t"), "mất chữ sau công thức: “\(ra)”")
    }

    func test_cong_thuc_KHONG_co_lenh_TeX_van_duoc_nhan() {
        for s in ["$[-128, 127]$", "$N = 16$", "$a + b$", "$x$", "$(n-1)$"] {
            XCTAssertFalse(thay(s).contains("$"), "“\(s)” không được nhận: “\(thay(s))”")
        }
    }

    func test_dau_TIEN_khong_bi_doc_thanh_cong_thuc() {
        // Ruột `"5 và "` kết thúc bằng khoảng trắng → là tiền. Luật cũ nhận nó là công thức
        // (vì có chữ cái) và ăn mất đoạn chữ ở giữa.
        for s in ["giá $5 và $10 nữa", "chi phí $100 so với $200"] {
            XCTAssertTrue(thay(s).contains("$"), "đoạn tiền bị đọc thành công thức: “\(thay(s))”")
        }
        // `$5$` và `$1.000$` là tiền: ruột chỉ có chữ số và dấu phân cách.
        XCTAssertTrue(thay("đúng $5$ đồng").contains("$"))
        XCTAssertTrue(thay("đúng $1.000$ đồng").contains("$"))
    }

    /// Tập mẫu DÙNG CHUNG với phía Python.
    ///
    /// `tests/du-lieu-chung/cong-thuc-giua-dong.json` — cùng tệp mà
    /// `test_cong_thuc_giua_dong_theo_tap_mau_dung_chung` của pytest đọc. Lõi không gọi ngược
    /// lên app được nên cùng một luật phải tồn tại hai bản; tệp ấy là chỗ cái giá đó được trả.
    /// Sửa một bên mà quên bên kia thì bên quên sẽ đỏ.
    func test_tap_mau_dung_chung_voi_phia_Python() throws {
        // Đi lên từ đường dẫn tệp nguồn: Tests/EIDETests → EIDEApp → ui → gốc kho.
        let goc = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent()
        let u = goc.appendingPathComponent("tests/du-lieu-chung/cong-thuc-giua-dong.json")
        let d = try Data(contentsOf: u)
        guard let j = try JSONSerialization.jsonObject(with: d) as? [String: Any] else {
            return XCTFail("không đọc được tập mẫu ở \(u.path)")
        }

        for x in (j["la_cong_thuc"] as? [[String: String]]) ?? [] {
            XCTAssertTrue(MathText.laCongThucChuKhongPhaiTien(x["ruot"] ?? ""),
                "Swift KHÔNG nhận “\(x["ruot"] ?? "")” là công thức — \(x["vi_sao"] ?? "")")
        }
        for x in (j["khong_phai_cong_thuc"] as? [[String: String]]) ?? [] {
            XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien(x["ruot"] ?? ""),
                "Swift nhận “\(x["ruot"] ?? "")” là công thức, mà nó không phải — "
                + "\(x["vi_sao"] ?? "")")
        }
    }

    func test_luat_GIONG_HET_phia_Python() {
        // Bốn điều kiện sao đúng từ `_dong_cong_thuc` của `xuat_ban.py`. Sửa một bên mà quên
        // bên kia thì cùng một câu hiện ra hai kiểu trên màn hình và trên giấy.
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien(""), "ruột rỗng")
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien("5 và "), "kết thúc bằng khoảng trắng")
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien(" x"), "bắt đầu bằng khoảng trắng")
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien("a$b"), "còn dấu đô-la bên trong")
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien("1.000,50"), "thuần chữ số là tiền")
        XCTAssertFalse(MathText.laCongThucChuKhongPhaiTien(String(repeating: "x", count: 301)),
                       "quá 300 ký tự gần như chắc chắn là hai dấu tiền ở hai câu")
        XCTAssertTrue(MathText.laCongThucChuKhongPhaiTien("[-128, 127]"))
        XCTAssertTrue(MathText.laCongThucChuKhongPhaiTien("\\alpha \\le 0.05"))
    }
}

/// Dòng hội thoại — **cả hai vai** đều phải qua bộ dựng markdown.
///
/// Anh Công báo hai lần rằng dấu `**` còn nguyên trên màn hình. Lần thứ hai là đúng câu vừa gõ
/// cho tác tử: *"Bản kết quả phải trả lời **bốn câu**"*. Bốn ca kiểm trước của tôi đều thử trên
/// `chuThuan()` — tức trên đường của **lời tác tử** — nên chúng xanh trong khi đường của **lời
/// người** vẫn là chữ trơn, với lý do viết hẳn trong mã: *"họ gõ gì hiện nấy"*.
///
/// Bài học: *"còn dấu sao trên màn không"* là một câu hỏi về MỘT ĐƯỜNG DẪN cụ thể. Hỏi nó trên
/// một đường rồi kết luận cho cả màn hình là nhảy bước.
final class DongHoiThoaiTests: XCTestCase {

    func test_cau_cua_NGUOI_cung_phai_duoc_dung() {
        // Câu thật anh Công chỉ ra.
        let ra = Markdown.chuThuan("Bản kết quả phải trả lời **bốn câu**, mỗi câu kèm con số")
        XCTAssertFalse(ra.contains("*"), "còn dấu sao: “\(ra)”")
        XCTAssertTrue(ra.contains("bốn câu"))
    }

    func test_bieu_thuc_nguoi_go_KHONG_bi_hieu_thanh_dau_nhan() {
        // Cái giá của việc dựng markdown cho câu người gõ. Ba thứ đỡ, và đây là ca canh chúng.
        for (vao, con) in [("tính a * b * c rồi so", "a * b * c"),
                           ("biến ten_bien_x trong mã", "ten_bien_x"),
                           ("đường C:\\Users\\cong", "C:\\Users\\cong")] {
            let ra = Markdown.chuThuan(vao)
            XCTAssertTrue(ra.contains(con), "“\(vao)” bị hiểu sai → “\(ra)”")
        }
    }

    func test_bang_trong_cau_nguoi_go_cung_thanh_bang() {
        let k = Markdown.tach("| a | b |\n|---|---|\n| 1 | 2 |")
        guard case .bang(let cot, let hang) = k.first else {
            return XCTFail("bảng người gõ không thành bảng: \(k)")
        }
        XCTAssertEqual(cot, ["a", "b"])
        XCTAssertEqual(hang, [["1", "2"]])
    }
}

/// Canh chính CHỖ CHỌN bộ dựng, không chỉ canh bộ dựng.
///
/// Ba ca `DongHoiThoaiTests` phía trên thử `Markdown.chuThuan` — và chúng **vẫn xanh với mã
/// cũ**, vì `chuThuan` chưa bao giờ hỏng. Thứ hỏng là một câu `if` trong thân `View`:
///
///     if nhan == "BẠN" { Text(tach.1) } else { MarkdownView(text: tach.1) }
///
/// Đây là lần thứ ba trong một ngày tôi viết một bộ ca kiểm xanh cả khi đường dẫn đứt — hai
/// lần trước là khối A8.0 và khối A5.10, cả hai đều xanh khi tôi bỏ hẳn khối ra khỏi tab.
/// `View` của SwiftUI không gọi được từ ca kiểm, nên ca này đọc chính MÃ NGUỒN. Cách ấy thô,
/// nhưng nó bắt được đúng cái đã hỏng — và một ca thô mà bắt được thì hơn một ca đẹp mà không.
final class ChonBoDungTests: XCTestCase {

    func test_dong_hoi_thoai_KHONG_con_nhanh_chu_tron_cho_cau_cua_nguoi() throws {
        let u = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Sources/EIDE/Views/ConsoleView.swift")
        let ma = try String(contentsOf: u, encoding: .utf8)

        guard let i = ma.range(of: "struct DongTranscript") else {
            return XCTFail("không tìm thấy DongTranscript — tên đã đổi, ca kiểm này mù")
        }
        guard let j = ma.range(of: "private var tach:", range: i.upperBound..<ma.endIndex) else {
            return XCTFail("không tìm thấy cuối thân DongTranscript")
        }
        let than = String(ma[i.upperBound..<j.lowerBound])

        XCTAssertFalse(than.contains("nhan == \"BẠN\""),
            "còn nhánh rẽ theo vai trong thân dòng hội thoại — câu của người sẽ lại là chữ "
            + "trơn, và dấu `**` lọt ra màn hình đúng như anh Công báo hai lần")
        XCTAssertTrue(than.contains("MarkdownView(text: tach.1)"),
            "dòng hội thoại phải dựng bằng MarkdownView cho CẢ HAI vai")
    }
}
