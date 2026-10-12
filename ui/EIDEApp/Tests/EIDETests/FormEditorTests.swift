import XCTest
@testable import EIDE

/// Trình soạn biểu mẫu và đặc tả `sua_duoc` — EIDE-EDIT-47 DEV-368.
///
/// Câu phải đo: **một dòng bốn trường thì gửi đi cái gì**. Sai ở đây hỏng theo kiểu khó
/// thấy nhất — đúng đường dẫn nhưng sai chỉ số thì ghi vào dòng của dòng khác, và không
/// có lỗi nào kêu lên; người chỉ phát hiện khi đọc lại bảng vài ngày sau.
@MainActor
final class FormEditorTests: XCTestCase {

    private func state() -> AppState {
        let s = AppState()
        s.connection = .dangChay("thử")
        return s
    }

    /// Đúng hình dạng `surfaces.sua_duoc` trả về.
    private func sd(idTu: String = "block", bacBo: Bool = false,
                    xacNhan: Bool = false) -> SuaDuoc {
        SuaDuoc(.object([
            "loai": .string("criteria"),
            "id_tu": .string(idTu),
            "truong": .array([
                .object(["path": .string("assert/{row}/nguong"), "cot": .string("Ngưỡng"),
                         "kieu": .string("so"), "bat_buoc": .bool(true),
                         "can_nguon": .bool(true), "gay_stale": .bool(true)]),
                .object(["path": .string("assert/{row}/phep_so"),
                         "cot": .string("Phép so"), "kieu": .string("chon"),
                         "lua_chon": .array([.string(">="), .string("<=")]),
                         "gay_stale": .bool(true)]),
                .object(["path": .string("assert/{ma}/ghi_chu"), "cot": .string("Ghi chú"),
                         "kieu": .string("chu"), "gay_stale": .bool(false)]),
            ]),
            "bac_bo_duoc": .bool(bacBo),
            "xac_nhan_duoc": .bool(xacNhan),
        ]))!
    }

    // ===================================================== gom nhiều ô thành MỘT patch
    func test_sua_ba_o_ra_DUNG_MOT_patch_ba_phep() {
        let act = FormEditor.actLuu(
            sd: sd(), idHienVat: "criteria:sim-01", phienBan: 3, row: 1, ma: "A2",
            dangCo: ["Ngưỡng": "3.3", "Phép so": ">=", "Ghi chú": "cũ"],
            moi: ["Ngưỡng": "5", "Phép so": "<=", "Ghi chú": "mới"],
            nguon: [:], viSao: "đo lại rồi", khoi: "A8.1", surface: "simulation",
            session: "es-1")

        XCTAssertNotNil(act)
        XCTAssertEqual(act?.kind, .edit)
        let patch = act?.data["patch"]?.arrayValue ?? []
        XCTAssertEqual(patch.count, 3, "ba ô đổi phải ra MỘT patch ba phép, không ba lần lưu")
        XCTAssertEqual(act?.data["base_version"]?.stringValue, "v3")
        XCTAssertEqual(act?.data["session_id"]?.stringValue, "es-1")
        XCTAssertEqual(act?.note, "đo lại rồi")
    }

    func test_thay_dung_chi_so_dong_va_ma_dong() {
        // `{row}` là CHỈ SỐ, `{ma}` là cột đầu. Thay nhầm thì một bảng ghi vào đúng dòng
        // của dòng khác — và không lỗi nào kêu.
        let act = FormEditor.actLuu(
            sd: sd(), idHienVat: "criteria:sim-01", phienBan: 1, row: 4, ma: "A9",
            dangCo: ["Ngưỡng": "1", "Ghi chú": "x"],
            moi: ["Ngưỡng": "2", "Ghi chú": "y"], nguon: [:], viSao: "",
            khoi: "A8.1", surface: "simulation", session: "es-1")
        let duong = (act?.data["patch"]?.arrayValue ?? []).compactMap { $0["path"]?.stringValue }
        XCTAssertTrue(duong.contains("assert/4/nguong"), "\(duong)")
        XCTAssertTrue(duong.contains("assert/A9/ghi_chu"), "\(duong)")
    }

    func test_O_KHONG_DOI_thi_khong_nam_trong_patch() {
        let act = FormEditor.actLuu(
            sd: sd(), idHienVat: "criteria:sim-01", phienBan: 1, row: 0, ma: "A1",
            dangCo: ["Ngưỡng": "3.3", "Phép so": ">="],
            moi: ["Ngưỡng": "3.3", "Phép so": "<="], nguon: [:], viSao: "",
            khoi: "", surface: "simulation", session: "es-1")
        let patch = act?.data["patch"]?.arrayValue ?? []
        XCTAssertEqual(patch.count, 1)
        XCTAssertEqual(patch.first?["path"]?.stringValue, "assert/0/phep_so")
    }

    func test_KHONG_DOI_GI_thi_khong_gui_gi() {
        let act = FormEditor.actLuu(
            sd: sd(), idHienVat: "criteria:sim-01", phienBan: 1, row: 0, ma: "A1",
            dangCo: ["Ngưỡng": "3.3"], moi: ["Ngưỡng": "3.3"], nguon: [:], viSao: "x",
            khoi: "", surface: "simulation", session: "es-1")
        XCTAssertNil(act, "một changeset rỗng vẫn là một dòng trong lịch sử và một lần "
                          + "đánh STALE — cho việc không có gì xảy ra")
    }

    // ===================================================== kiểu dữ liệu
    func test_truong_SO_gui_di_mot_SO_chu_khong_phai_chuoi() {
        // Gửi "5" vào trường số thì kho ghi một chuỗi, và phép so ngưỡng sau đó so chuỗi
        // với số — một phép so luôn sai mà không kêu.
        XCTAssertEqual(FormEditor.giaTri("5", kieu: "so"), .number(5))
        XCTAssertEqual(FormEditor.giaTri("3,3", kieu: "so"), .number(3.3), "dấu phẩy Việt")
        XCTAssertEqual(FormEditor.giaTri("12", kieu: "so_nguyen"), .number(12))
        XCTAssertEqual(FormEditor.giaTri("true", kieu: "bool"), .bool(true))
        XCTAssertEqual(FormEditor.giaTri("có", kieu: "bool"), .bool(true))
        XCTAssertEqual(FormEditor.giaTri("x", kieu: "chu"), .string("x"))
        XCTAssertEqual(FormEditor.giaTri("không-phải-số", kieu: "so"),
                       .string("không-phải-số"),
                       "không ép được thì gửi nguyên văn để LÕI từ chối và nói lý do")
    }

    // ===================================================== nguồn đi kèm
    func test_nguon_nguoi_cho_di_theo_LOI_GHI_CHU_chu_khong_mat() {
        let act = FormEditor.actLuu(
            sd: sd(), idHienVat: "criteria:sim-01", phienBan: 1, row: 0, ma: "A1",
            dangCo: ["Ngưỡng": "3.3"], moi: ["Ngưỡng": "5"],
            nguon: ["Ngưỡng": "datasheet tr.12"], viSao: "đo lại",
            khoi: "", surface: "simulation", session: "es-1")
        XCTAssertEqual(act?.note, "đo lại · nguồn — Ngưỡng: datasheet tr.12")
    }

    // ===================================================== đọc đặc tả
    func test_doc_dung_dac_ta_sua_duoc() {
        let s = sd(idTu: "row", bacBo: true, xacNhan: true)
        XCTAssertEqual(s.loai, "criteria")
        XCTAssertEqual(s.idTu, "row")
        XCTAssertTrue(s.bacBoDuoc && s.xacNhanDuoc)
        XCTAssertEqual(s.truong.count, 3)
        XCTAssertTrue(s.truong[0].batBuoc && s.truong[0].canNguon)
        XCTAssertEqual(s.truong[1].luaChon, [">=", "<="])
        XCTAssertNil(SuaDuoc(nil), "khối không khai gì thì là khối CHỈ ĐỌC")
        XCTAssertNil(SuaDuoc(.object([:])))
    }

    // ===================================================== bác bỏ
    func test_bac_bo_KHONG_GUI_khi_thieu_ly_do() {
        let s = state()
        XCTAssertFalse(BacBoView.gui(state: s, loai: "report", idHienVat: "ERC-1",
                                     ma: "ERC-1", lyDo: "   ", khoi: "A5.9c",
                                     surface: "design"))
        XCTAssertTrue(s.daGui.isEmpty,
                      "một dòng “đừng” không nói vì sao thì lượt sau tác tử chỉ biết là "
                      + "bị cấm, và nó sẽ đề xuất lại bằng một cách gọi khác")
    }

    func test_bac_bo_gui_edit_co_co_bac_bo_va_ly_do() {
        let s = state()
        XCTAssertTrue(BacBoView.gui(state: s, loai: "report", idHienVat: "ERC-1",
                                    ma: "ERC-1", lyDo: "net này là test point",
                                    khoi: "A5.9c", surface: "design"))
        let a = s.daGui[0]
        XCTAssertEqual(a.kind, .edit)
        XCTAssertEqual(a.target?.type, "report")
        XCTAssertEqual(a.data["bac_bo"]?.boolValue, true)
        XCTAssertEqual(a.note, "net này là test point")
    }
}
