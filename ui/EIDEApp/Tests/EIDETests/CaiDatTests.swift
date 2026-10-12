import XCTest
@testable import EIDE

/// Khối cài đặt dự án ở A14 — EIDE-EDIT-47 DEV-371.
///
/// Câu phải đo: **một cái công tắc gửi đi cái gì**. Một cờ tính năng không phải hiện vật
/// trong kho — không phiên bản, không changeset, không hạ nguồn STALE — nên gửi nó bằng
/// `edit` thì lõi đi tìm một hiện vật không tồn tại và `base_version` là số bịa ra.
@MainActor
final class CaiDatTests: XCTestCase {

    /// Đúng hình dạng `surfaces.cai_dat_du_an` trả về.
    private func sd() -> SuaDuoc {
        SuaDuoc(.object([
            "loai": .string("cai_dat"),
            "id_tu": .string("row"),
            "phien_ban_tu": .string(""),
            "gui_bang": .string("set"),
            "truong": .array([
                .object(["path": .string("feature.{ma}"), "cot": .string("Bật"),
                         "kieu": .string("bool"), "gay_stale": .bool(false)]),
            ]),
        ]))!
    }

    func testKhaiGuiBangSet() {
        XCTAssertEqual(sd().guiBang, "set")
        // Khối không khai thì vẫn là `edit` — mười mấy bảng cũ không phải sửa gì.
        let cu = SuaDuoc(.object(["loai": .string("req"), "truong": .array([])]))!
        XCTAssertEqual(cu.guiBang, "edit")
    }

    func testGuiDungKeyVaGiaTriBool() {
        let t = sd().truong[0]
        let act = FormEditor.actDat(key: t.duong(row: 0, ma: "watcher"), bat: true,
                                    surface: "project", khoi: "A14.7", ma: "watcher")
        XCTAssertEqual(act.kind, .set)
        XCTAssertEqual(act.data["key"]?.stringValue, "feature.watcher")
        XCTAssertEqual(act.data["value"]?.boolValue, true)
        // Không có `target`: không có hiện vật nào ở đây để trỏ tới.
        XCTAssertNil(act.target)
        XCTAssertEqual(act.origin.block, "A14.7")
        XCTAssertEqual(act.origin.row, "watcher")
    }

    func testTatThiGuiFalseChuKhongBoTrong() {
        let act = FormEditor.actDat(key: "feature.pdf_bang", bat: false,
                                    surface: "project", khoi: "A14.7", ma: "pdf_bang")
        XCTAssertEqual(act.data["value"]?.boolValue, false,
                       "bỏ trống thì lõi không biết là tắt hay là chưa nói gì")
    }

    /// Lõi gửi `"có"`/`"không"` bằng tiếng Việt, không gửi `true`/`false`: bảng này người
    /// đọc trước, máy đọc sau. Nên chỗ dịch ngược nằm ở đây và phải đo được.
    func testDocDungTrangThaiBatTat() {
        for s in ["có", "CÓ", " true ", "bật", "1"] {
            XCTAssertTrue(KhoiKV.laBat(s), s)
        }
        for s in ["không", "false", "", "—"] {
            XCTAssertFalse(KhoiKV.laBat(s), s)
        }
    }
}
