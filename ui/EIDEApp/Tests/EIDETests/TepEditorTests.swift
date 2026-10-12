import XCTest
@testable import EIDE

/// Trình soạn tệp và khoá mềm hai chiều — EIDE-EDIT-47 DEV-367.
@MainActor
final class TepEditorTests: XCTestCase {

    private func state() -> AppState {
        let s = AppState()
        s.connection = .dangChay("thử")
        return s
    }

    private func lenh(_ method: String, _ params: [String: JSONValue]) -> UICommand {
        UICommand(method: method, params: params, seq: 1)
    }

    // ===================================================== lưu
    func test_luu_gui_dung_HASH_LUC_MO_lam_base_version() {
        // `base_version` là hash lúc MỞ, không phải lúc lưu. Đó là thứ duy nhất cho
        // `_sua_tep` phát hiện tác tử đã sửa tệp trong lúc người đang gõ, và gộp ba chiều
        // thay vì ghi đè. Gửi rỗng thì mọi lần như thế thành một lần ghi đè im lặng.
        let a = TepEditorView.actLuu(path: "src/main.c", noiDung: "mới\n",
                                     hash: "hash-luc-mo", viSao: "sửa cờ dịch",
                                     session: "es-3")
        XCTAssertEqual(a.kind, .edit)
        XCTAssertEqual(a.target?.type, "file")
        XCTAssertEqual(a.target?.id, "src/main.c")
        XCTAssertEqual(a.data["base_version"]?.stringValue, "hash-luc-mo")
        XCTAssertEqual(a.data["content"]?.stringValue, "mới\n")
        XCTAssertEqual(a.data["session_id"]?.stringValue, "es-3")
        XCTAssertEqual(a.note, "sửa cờ dịch")
    }

    func test_luu_khai_dung_xuat_xu_la_TRINH_SOAN() {
        // Lõi khoá tệp theo `origin.block == "editor"`. Khai sai thì khoá mềm chiều
        // người → tác tử không bao giờ bật, và tác tử ghi đè mà không hỏi.
        let a = TepEditorView.actLuu(path: "main.c", noiDung: "x", hash: "h",
                                     viSao: "", session: "es-1")
        XCTAssertEqual(a.origin.block, "editor")
        XCTAssertEqual(a.origin.row, "main.c")
        XCTAssertNil(a.note, "“vì sao” bỏ trống thì KHÔNG đặt một chuỗi rỗng đứng tên lý do")
    }

    // ===================================================== khoá của tác tử
    func test_nhan_surface_lock_cua_TAC_TU_va_bo_khi_unlock() {
        let s = state()
        s.apply(lenh("surface.lock", ["surface": .string("code"),
                                      "block": .string("main.c"),
                                      "by": .string("run-7"),
                                      "why": .string("Tác tử đang sửa tệp này")]))
        XCTAssertTrue(s.khoaCuaTacTu.contains("main.c"),
                      "lõi gửi `surface.lock` từ bước G2 và giao diện bỏ qua nó — nên "
                      + "băng “tác tử đang sửa tệp này” chưa bao giờ hiện ra")
        s.apply(lenh("surface.unlock", ["surface": .string("code"),
                                        "block": .string("main.c")]))
        XCTAssertFalse(s.khoaCuaTacTu.contains("main.c"))
    }

    func test_khoa_cua_CHINH_NGUOI_khong_tu_canh_bao_minh() {
        let s = state()
        s.apply(lenh("surface.lock", ["surface": .string("code"),
                                      "block": .string("main.c"),
                                      "by": .string("human"),
                                      "why": .string("anh đang mở tệp này")]))
        XCTAssertTrue(s.khoaCuaTacTu.isEmpty,
                      "vẽ băng “tác tử đang sửa” cho chính khoá của người là nói sai")
    }

    func test_doi_du_an_xoa_khoa() {
        let s = state()
        s.apply(lenh("surface.lock", ["block": .string("main.c"), "by": .string("run-1")]))
        s.doiDuAn(URL(fileURLWithPath: "/tmp/du-an-khac"))
        XCTAssertTrue(s.khoaCuaTacTu.isEmpty)
    }

    // ===================================================== báo đang sửa
    func test_bao_dang_sua_gui_attend_dung_hinh_dang() {
        let s = state()
        s.baoDangSuaTep("main.c", dangSua: true)
        s.baoDangSuaTep("main.c", dangSua: false)
        XCTAssertEqual(s.daGui.count, 2)
        for a in s.daGui {
            XCTAssertEqual(a.kind, .attend, "là SỰ CHÚ Ý — không tốn một lượt mô hình nào")
            XCTAssertEqual(a.origin.block, "editor")
            XCTAssertEqual(a.data["path"]?.stringValue, "main.c")
        }
        XCTAssertEqual(s.daGui[0].data["dang_sua"]?.boolValue, true)
        XCTAssertEqual(s.daGui[1].data["dang_sua"]?.boolValue, false)
    }
}
