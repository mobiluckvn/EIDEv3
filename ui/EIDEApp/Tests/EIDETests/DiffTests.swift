import XCTest
@testable import EIDE

/// Khối `diff` phía giao diện — EIDE-EDIT-47 DEV-366.
///
/// Hai câu phải trả lời được bằng số:
///   1. lệnh thứ 17 có tới nơi không, hay nó rơi vào nhánh "chưa biết lệnh này";
///   2. thẻ xung đột gửi đi **cái gì** khi người bấm — và theo thứ tự nào.
///
/// Câu thứ hai đáng một bộ ca riêng vì nó là chỗ dễ mất việc của người nhất trong cả gói:
/// gửi sai `base_version` thì lần lưu này xung đột lần nữa, và người vừa gõ lại cả đoạn mã
/// trong cột phải sẽ mất nó.
@MainActor
final class DiffTests: XCTestCase {

    private func state() -> AppState {
        let s = AppState()
        s.connection = .dangChay("thử")
        return s
    }

    private func lenh(_ method: String, _ params: [String: JSONValue]) -> UICommand {
        UICommand(method: method, params: params, seq: 1)
    }

    /// Đúng hình dạng `diff_khoi.dung_diff` trả về.
    private func khoiDiff(id: String = "d-1", ganVoi: [String: JSONValue],
                          choPhepSua: Bool = true) -> [String: JSONValue] {
        [
            "diff_id": .string(id),
            "tieu_de": .string("main.c — bản của anh ↔ bản hiện tại"),
            "loai": .string("tep"),
            "trai": .object(["nhan": .string("Bản của anh"),
                             "noi_dung": .string("a\nANH\nc\n"),
                             "hash": .string("hash-trai"), "cat": .bool(false),
                             "so_dong": .number(3)]),
            "phai": .object(["nhan": .string("Bản hiện tại"),
                             "noi_dung": .string("a\nTÁC TỬ\nc\n"),
                             "hash": .string("hash-phai"), "cat": .bool(false),
                             "so_dong": .number(3)]),
            "hunks": .array([.object(["loai": .string("xung_dot"),
                                      "dong_trai": .number(2), "so_trai": .number(1),
                                      "dong_phai": .number(2), "so_phai": .number(1)])]),
            "cho_phep_sua": .bool(choPhepSua),
            "gan_voi": .object(ganVoi),
            "tom_tat": .object(["doan": .number(1), "them": .number(0),
                                "bot": .number(0), "doi": .number(0),
                                "xung_dot": .number(1)]),
        ]
    }

    // ===================================================== lệnh thứ 17 tới nơi
    func test_lenh_diff_show_KHONG_roi_vao_nhanh_lenh_la() {
        let s = state()
        s.apply(lenh("diff.show", khoiDiff(ganVoi: ["card_id": .string("card-1")])))
        XCTAssertEqual(s.diffs.count, 1)
        XCTAssertTrue(s.notices.isEmpty,
                      "rơi vào nhánh `default` thì giao diện báo “chưa biết lệnh” — "
                      + "và người thấy một thẻ xung đột trống rỗng")
    }

    func test_tra_duoc_diff_theo_THE_va_theo_CONG() {
        let s = state()
        s.apply(lenh("diff.show", khoiDiff(id: "d-1", ganVoi: ["card_id": .string("card-1")])))
        s.apply(lenh("diff.show", khoiDiff(id: "d-2", ganVoi: ["gate_id": .string("gate-9")])))
        XCTAssertEqual(s.diffGanVoi(cardID: "card-1")?["diff_id"]?.stringValue, "d-1")
        XCTAssertEqual(s.diffGanVoi(gateID: "gate-9")?["diff_id"]?.stringValue, "d-2")
        XCTAssertNil(s.diffGanVoi(cardID: "card-khac"),
                     "giao diện không tự gán diff cho thẻ nào — lõi khai `gan_voi`")
        // Hỏi theo khoá THẺ bằng một mã CỔNG (và ngược lại) phải ra rỗng. Thiếu nửa sau
        // của phép kiểm này thì một phép tra nhận bừa cả hai khoá vẫn xanh.
        XCTAssertNil(s.diffGanVoi(gateID: "card-1"), "không lẫn khoá thẻ với khoá cổng")
        XCTAssertNil(s.diffGanVoi(cardID: "gate-9"), "không lẫn khoá cổng với khoá thẻ")
    }

    func test_doi_du_an_xoa_cac_khoi_diff() {
        let s = state()
        s.apply(lenh("diff.show", khoiDiff(ganVoi: ["card_id": .string("card-1")])))
        s.doiDuAn(URL(fileURLWithPath: "/tmp/du-an-khac"))
        XCTAssertTrue(s.diffs.isEmpty,
                      "một khối diff của dự án cũ nằm lại thì thẻ của dự án mới sẽ vẽ nó")
    }

    // ===================================================== đếm dòng như lõi đếm
    func test_tep_ket_thuc_bang_xuong_dong_KHONG_de_ra_mot_dong_ma() {
        // Thấy trên ảnh chụp thẻ xung đột: một tệp MỘT dòng được đánh số tới 2. Con số
        // lệch mới là phần nguy: `hunks` của lõi đánh theo `splitlines()`, nên giao diện
        // đếm thừa một dòng là phép tô màu trượt ở MỌI tệp kết thúc bằng xuống dòng.
        XCTAssertEqual(DiffView.tachDong("int main(void){return 0;}\n").count, 1)
        XCTAssertEqual(DiffView.tachDong("a\nb\n"), ["a", "b"])
        XCTAssertEqual(DiffView.tachDong("a\nb"), ["a", "b"], "không có \\n cuối thì giữ nguyên")
        XCTAssertEqual(DiffView.tachDong(""), [""], "tệp rỗng vẫn là một dòng rỗng để vẽ")
        XCTAssertEqual(DiffView.tachDong("a\n\n"), ["a", ""],
                       "chỉ bỏ MỘT dòng rỗng cuối — dòng trống thật phải còn")
    }

    // ===================================================== thẻ xung đột gửi gì
    private func theXungDot(_ s: AppState) -> Card {
        let raw: [String: JSONValue] = [
            "type": .string("clarify"), "card_id": .string("card-1"),
            "tra_loi_thanh": .string("xung_dot"),
            "du_lieu": .object(["hien_vat": .string("main.c"),
                                "target": .string("file:main.c")]),
            "questions": .array([.object([
                "key": .string("chon"),
                "question": .string("Giữ bản nào?"),
                "choices": .array([.string("Giữ bản của tôi (anh)"),
                                   .string("Giữ bản của tác tử"),
                                   .string("Dùng bản tôi vừa sửa trong diff")])])]),
        ]
        s.apply(lenh("diff.show", khoiDiff(ganVoi: ["card_id": .string("card-1")])))
        return Card(id: "card-1", raw: raw)
    }

    func test_giu_ban_cua_toi_GUI_noi_dung_cot_trai_truoc_roi_moi_chon() {
        let s = state()
        let c = theXungDot(s)
        TheLamRoView.guiTraLoi(state: s, card: c, traLoi: ["chon": "Giữ bản của tôi (anh)"],
                               banDaSua: nil)

        XCTAssertEqual(s.daGui.count, 2)
        XCTAssertEqual(s.daGui[0].kind, .edit,
                       "nội dung phải đi TRƯỚC: lõi đóng sổ xung đột khi nhận `choose`, "
                       + "và lúc ấy nó đi tìm changeset của người để báo lại")
        XCTAssertEqual(s.daGui[1].kind, .choose)
        XCTAssertEqual(s.daGui[0].data["content"]?.stringValue, "a\nANH\nc\n")
        XCTAssertEqual(s.daGui[0].target?.type, "file")
        XCTAssertEqual(s.daGui[0].target?.id, "main.c")
    }

    func test_base_version_lay_HASH_COT_PHAI_chu_khong_phai_cot_trai() {
        // Lấy hash bản của người là cố ghi đè bằng đúng phiên bản vừa gây ra xung đột —
        // và lần lưu này sẽ xung đột lần nữa, nuốt mất đoạn người vừa gõ trong cột phải.
        let s = state()
        let c = theXungDot(s)
        TheLamRoView.guiTraLoi(state: s, card: c, traLoi: ["chon": "Giữ bản của tôi (anh)"],
                               banDaSua: nil)
        XCTAssertEqual(s.daGui[0].data["base_version"]?.stringValue, "hash-phai")
    }

    func test_giu_ban_cua_TAC_TU_thi_khong_ghi_gi_ca() {
        let s = state()
        let c = theXungDot(s)
        TheLamRoView.guiTraLoi(state: s, card: c, traLoi: ["chon": "Giữ bản của tác tử"],
                               banDaSua: nil)
        XCTAssertEqual(s.daGui.count, 1)
        XCTAssertEqual(s.daGui[0].kind, .choose, "bản ấy đang nằm trên đĩa rồi")
    }

    func test_ban_DA_SUA_gui_dung_chu_nguoi_go_trong_cot_phai() {
        let s = state()
        let c = theXungDot(s)
        TheLamRoView.guiTraLoi(state: s, card: c,
                               traLoi: ["chon": "Dùng bản tôi vừa sửa trong diff"],
                               banDaSua: "a\nCẢ HAI\nc\n")
        XCTAssertEqual(s.daGui.count, 2)
        XCTAssertEqual(s.daGui[0].data["content"]?.stringValue, "a\nCẢ HAI\nc\n")
    }

    func test_chon_ban_da_sua_ma_CHUA_SUA_gi_thi_khong_de_ra_changeset_rong() {
        let s = state()
        let c = theXungDot(s)
        TheLamRoView.guiTraLoi(state: s, card: c,
                               traLoi: ["chon": "Dùng bản tôi vừa sửa trong diff"],
                               banDaSua: nil)
        XCTAssertEqual(s.daGui.count, 1)
        XCTAssertEqual(s.daGui[0].kind, .choose)
    }

    func test_the_lam_ro_THUONG_khong_co_diff_thi_chi_gui_choose() {
        let s = state()
        let c = Card(id: "card-2", raw: ["type": .string("clarify"),
                                         "card_id": .string("card-2")])
        TheLamRoView.guiTraLoi(state: s, card: c, traLoi: ["a": "b"], banDaSua: nil)
        XCTAssertEqual(s.daGui.count, 1)
        XCTAssertEqual(s.daGui[0].kind, .choose)
    }
}
