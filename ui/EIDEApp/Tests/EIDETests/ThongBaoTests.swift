import XCTest
@testable import EIDE

/// Cảnh báo trên màn hình chat.
///
/// Anh Công nêu ngày 01/10/2026: *"Màn hình chat Agent quá nhiều cảnh báo cần ẩn nó đi hoặc
/// xoá đi nếu đã clear nhé."*
///
/// Lỗi rõ ràng chứ không phải cảm giác: **10 chỗ thêm, 1 chỗ xoá**, và chỗ xoá ấy là
/// `doiDuAn()`. Nên suốt một phiên `notices` chỉ tăng, và cách duy nhất để nó rỗng lại là đổi
/// sang dự án khác — điều không ai làm giữa lúc đang chạy việc.
@MainActor
final class ThongBaoTests: XCTestCase {

    func test_canh_bao_trung_duoc_GOP_kem_so_lan() {
        let s = AppState()
        for _ in 0..<10 {
            s.themThongBao(level: "warn", text: "Không vẽ lại được", code: "E_VE")
        }
        XCTAssertEqual(s.notices.count, 1, "mười lần nổ phải thành MỘT thẻ, không phải mười")
        XCTAssertEqual(s.notices[0].soLan, 10, "số lần là thông tin — phải giữ, không bỏ")
    }

    func test_canh_bao_KHAC_nhau_thi_khong_gop() {
        let s = AppState()
        s.themThongBao(level: "warn", text: "a", code: nil)
        s.themThongBao(level: "warn", text: "b", code: nil)
        s.themThongBao(level: "error", text: "a", code: nil)     // khác mức
        s.themThongBao(level: "warn", text: "a", code: "X")      // khác mã
        XCTAssertEqual(s.notices.count, 4,
                       "gộp quá tay thì mất cảnh báo — bốn thứ khác nhau phải còn bốn thẻ")
    }

    func test_bo_duoc_tung_the() {
        let s = AppState()
        s.themThongBao(level: "warn", text: "a")
        s.themThongBao(level: "warn", text: "b")
        s.boThongBao(s.notices[0].id)
        XCTAssertEqual(s.notices.map(\.text), ["b"])
    }

    func test_don_het_duoc() {
        let s = AppState()
        for i in 0..<5 { s.themThongBao(level: "warn", text: "c\(i)") }
        s.xoaHetThongBao()
        XCTAssertTrue(s.notices.isEmpty)
    }

    func test_muc_info_tu_het_con_warn_va_error_thi_KHONG() {
        let s = AppState()
        let cu = Date().addingTimeInterval(-(AppState.giayThongBaoInfo + 10))
        s.notices = [
            .init(level: "info", text: "đã xong", code: nil, soLan: 1, luc: cu),
            .init(level: "warn", text: "coi lại", code: nil, soLan: 1, luc: cu),
            .init(level: "error", text: "hỏng", code: nil, soLan: 1, luc: cu),
        ]
        s.donThongBaoHetHan()
        XCTAssertEqual(s.notices.map(\.level), ["warn", "error"],
                       "`warn` và `error` KHÔNG được tự mất — người dùng phải thấy chúng, "
                       + "và việc bỏ đi là quyết định của họ")
    }

    func test_them_the_moi_thi_don_luon_cai_info_da_het_han() {
        let s = AppState()
        s.notices = [.init(level: "info", text: "cũ", code: nil, soLan: 1,
                           luc: Date().addingTimeInterval(-999))]
        s.themThongBao(level: "warn", text: "mới")
        XCTAssertEqual(s.notices.map(\.text), ["mới"],
                       "dọn ngay lúc thêm thẻ — khỏi cần bộ đếm giờ")
    }
}

/// Bản chụp giao diện cắt lời tác tử.
///
/// Mục 3 sổ việc: `String(cuoi.prefix(3000))` làm **nhật ký phiên chép thiếu** — hai lần trong
/// phiên robot, danh mục an toàn và phần thiết kế phép đo dấu đều mất phần đuôi.
///
/// Nhật ký là sở cứ. Một sở cứ cắt mất đoạn cuối thì chỗ bị cắt luôn là chỗ **không ai biết là
/// đã mất**: câu cuối trông như một câu kết thúc bình thường.
@MainActor
final class BanChupTests: XCTestCase {

    func test_tran_chu_du_cao_cho_loi_tac_tu_that() {
        XCTAssertGreaterThanOrEqual(UITestChannel.tranChu, 20_000,
            "3 000 ký tự là quá thấp: một bản thiết kế kiến trúc dài hơn thế nhiều")
    }

    func test_chu_ngan_thi_khong_cham_vao() {
        let k = UITestChannel()
        let s = "một câu ngắn"
        XCTAssertEqual(k.catVaGhiRa(s, ten: "thu"), s)
    }

    func test_chu_dai_thi_NOI_RA_la_da_cat_va_noi_do_dai_that() {
        let k = UITestChannel()
        let dai = String(repeating: "X", count: UITestChannel.tranChu + 500)
        let ra = k.catVaGhiRa(dai, ten: "thu")
        XCTAssertTrue(ra.contains("CẮT Ở"), "cắt mà không nói thì người đọc không biết đã mất")
        XCTAssertTrue(ra.contains("\(dai.count) ký tự"), "phải nói độ dài THẬT: “\(ra.suffix(90))”")
    }
}
