import XCTest
@testable import EIDE

/// Nút do LÕI khai — EIDE-EDIT-47 §DEV-373.
///
/// Câu phải đo: **bấm vào thì gửi đi cái gì**. Chỗ dễ sai nhất là phép thay `{ma}`/`{loai}`:
/// thay sót một chỗ thì thông điệp trỏ vào một hiện vật tên `{ma}` — không có lỗi nào kêu
/// lên, lõi chỉ nói "không có hiện vật ấy", và người bấm sẽ tưởng tính năng hỏng.
@MainActor
final class HanhDongTests: XCTestCase {

    /// Đúng hình dạng `surfaces.hanh_dong(...)` trả về cho A11.4.
    private func chapNhan() -> HanhDong {
        HanhDong(.object([
            "ma": .string("chap_nhan"), "nhan": .string("Chấp nhận STALE"),
            "kind": .string("edit"), "muc": .string("dong"),
            "target": .object(["type": .string("{loai}"), "id": .string("{ma}")]),
            "data": .object(["chap_nhan_stale": .bool(true)]),
            "can_ly_do": .bool(true),
            "giai_thich": .string("0 token, và hoàn tác được"),
        ]))
    }

    private func capNhat() -> HanhDong {
        HanhDong(.object([
            "ma": .string("cap_nhat_mot"), "nhan": .string("Cập nhật"),
            "kind": .string("say"), "muc": .string("dong"),
            "text": .string("Cập nhật {ma}."),
            "data": .object(["nut": .string("cap_nhat_ha_nguon"),
                             "hien_vat": .array([.string("{ma}")])]),
            "ton_token": .bool(true),
        ]))
    }

    func testGuiDungTargetVaDataCuaDong() {
        let act = chapNhan().act(ma: "build:firmware", loai: "build", khoi: "A11.4",
                                 surface: "history", lyDo: "chỉ đo kích thước")
        XCTAssertEqual(act?.kind, .edit)
        XCTAssertEqual(act?.target?.id, "build:firmware")
        XCTAssertEqual(act?.target?.type, "build")
        XCTAssertEqual(act?.data["chap_nhan_stale"]?.boolValue, true)
        XCTAssertEqual(act?.note, "chỉ đo kích thước")
        XCTAssertEqual(act?.origin.block, "A11.4")
        XCTAssertEqual(act?.origin.row, "build:firmware")
    }

    /// `{ma}` nằm TRONG một mảng lồng trong `data`. Thay sót ở đó thì lõi nhận
    /// `hien_vat: ["{ma}"]` và lọc ra rỗng — nút chạy, không lỗi, và không làm gì cả.
    func testThayChoTrongMangLong() {
        let act = capNhat().act(ma: "sim_result:x", loai: "sim_result", khoi: "A11.4",
                                surface: "history", lyDo: "")
        XCTAssertEqual(act?.text, "Cập nhật sim_result:x.")
        XCTAssertEqual(act?.data["hien_vat"]?.arrayValue.first?.stringValue,
                       "sim_result:x")
        XCTAssertNil(act?.note, "không có lý do thì KHÔNG gửi note rỗng")
    }

    func testNutCanLyDoThiKhaiRa() {
        XCTAssertTrue(chapNhan().canLyDo)
        XCTAssertFalse(chapNhan().tonToken, "0 token thì đừng gắn dấu tốn tiền")
        XCTAssertTrue(capNhat().tonToken)
    }

    /// Nút của cả KHỐI không có dòng nào, nên `{ma}` thay bằng rỗng. Một descriptor đòi
    /// `target` mà dòng không có mã thì **không gửi gì** — thà không gửi còn hơn gửi một
    /// thông điệp trỏ vào hiện vật rỗng.
    func testKhoiKhongCoMaThiKhongGuiActDoiTarget() {
        XCTAssertNil(chapNhan().act(ma: "", loai: "", khoi: "A11.4",
                                    surface: "history", lyDo: "x"))
        let khoi = HanhDong(.object([
            "ma": .string("cap_nhat_tat_ca"), "nhan": .string("Cập nhật hạ nguồn"),
            "kind": .string("say"), "muc": .string("khoi"),
            "text": .string("Cập nhật những hiện vật đang lỗi thời."),
            "data": .object(["nut": .string("cap_nhat_ha_nguon")]),
        ]))
        let act = khoi.act(ma: "", loai: "", khoi: "A11.4", surface: "history", lyDo: "")
        XCTAssertNotNil(act, "nút của khối không cần target")
        XCTAssertNil(act?.origin.row)
        XCTAssertNil(act?.target)
    }

    func testKindLaKHONG_doc_duoc_thi_khong_gui() {
        let la = HanhDong(.object(["ma": .string("x"), "nhan": .string("Lạ"),
                                   "kind": .string("khong_co_loai_nay")]))
        XCTAssertNil(la.act(ma: "a", loai: "b", khoi: "A11.4",
                            surface: "history", lyDo: ""))
    }
}
