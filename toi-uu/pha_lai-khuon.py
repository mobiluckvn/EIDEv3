"""KHUÔN script "phá lại thì đỏ" — giữ lại từ M4-05 (DEV-348) để nhiệm vụ sau sửa `PHEP` rồi
chạy, không phải viết lại từ đầu.

Hai thứ khuôn này làm mà một phép phá bằng tay không làm được:

1. **Xoá `__pycache__` trước MỖI lượt.** Một phép phá dài đúng bằng mã gốc làm Python coi
   `.pyc` cũ là còn hợp lệ, và phép đo chạy mã khác mã trong tệp — DEV-335.
2. **Tự kiểm phép phá.** So byte trước–sau và in `[VÔ HIỆU]` nếu không đổi gì. Ba phép vô hiệu
   trong M4-01/M4-02 đã báo LỌT oan và suýt làm tôi viết ca kiểm cho chỗ vốn đã được canh —
   một phép phá không đổi hành vi thì nói sai y như một ca kiểm không đo gì.

Cách dùng: sửa `TEP_TEST` và `PHEP` (dựng TỪ `git diff`, không từ ký ức — mỗi nhánh `if` là
một chỗ, mỗi mức/nhãn là một chỗ, mỗi tham số mặc định đảo được là một chỗ), rồi:

    .venv/bin/python toi-uu/pha_lai-khuon.py

`PHEP` dưới đây là tập của M4-05, giữ nguyên làm ví dụ."""
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path("/Users/congvt/Documents/EIDE_v3")
TEP_TEST = ["tests/test_dot_bien.py", "tests/test_hdl.py", "tests/test_xay_dung.py"]

DBF = "src/eide/build/dot_bien.py"
HDL = "src/eide/build/hdl.py"
XD = "src/eide/tools/xay_dung.py"
TH = "src/eide/tools/hdl.py"

PHEP = [
    # ------------------------------------------------------------ vòng đột biến
    ("bỏ hẳn nhánh stillborn — mutant không dịch được lại tính là “bắt được”",
     DBF, "            if not dat and _la_loi_bien_dich(log):", "            if False:"),

    ("stillborn thì BREAK thay vì đi tiếp phép sau",
     DBF, '                ghi_chu = f"{mo_ta} ({n} chỗ) → mutant không dịch được (bỏ qua)"\n'
          "                continue",
     '                ghi_chu = f"{mo_ta} ({n} chỗ) → mutant không dịch được (bỏ qua)"\n'
     "                break"),

    ("không đếm so_mutant_khong_hop_le",
     DBF, '                ra["so_mutant_khong_hop_le"] += 1', "                pass"),

    ("khoá so_mutant_khong_hop_le không có trong kết quả khi bằng 0",
     DBF, '                          "so_mutant_khong_hop_le": 0}', "                          }"),

    ("mọi phép stillborn thì xếp khong_thay (một cáo buộc) thay vì chua_do_duoc",
     DBF, '        elif stillborn and "không dịch được" in ghi_chu:', "        elif False:"),

    ("_la_loi_bien_dich đọc NỘI DUNG log thay vì tiền tố — ca test hỏng có “error:” bị nhận nhầm",
     DBF, '    return isinstance(log, str) and log.lstrip().startswith(TIEN_TO_BIEN_DICH)',
     "    return isinstance(log, str) and _khong_dich_duoc(log)"),

    ("_la_loi_bien_dich luôn True — mọi mutant thành stillborn",
     DBF, '    return isinstance(log, str) and log.lstrip().startswith(TIEN_TO_BIEN_DICH)',
     "    return True"),

    ("loi_nguoi_doc không nói ra số mutant bị bỏ",
     DBF, '    them_sb = (f" {sb} phép phá bị BỎ vì mutant không dịch được — chúng không nằm trong con "\n'
          '               "số trên, và cũng không nói gì về bộ kiểm." if sb else "")',
     '    them_sb = ""'),

    ("loi_nguoi_doc khen “phá tệp nào cũng có ca đỏ” khi chưa đo được tệp nào",
     DBF, '    if not d["so_thay"]:', "    if False:"),

    ("mã chỗ giữ về lại chữ SỐ — tệp ≥10 chú thích đổ IndexError",
     DBF, '        return f"\\x00{_ma_cho(len(giu) - 1)}\\x00"',
     '        return f"\\x00{len(giu) - 1}\\x00"'),

    ("_ma_cho lệch một chỗ — trả lại SAI chuỗi đã giữ",
     DBF, "    i += 1\n    while i:", "    while i:"),

    ("regex phục hồi chỗ giữ vẫn bắt chữ số, không bắt chữ hoa",
     DBF, '    moi = re.sub(r"\\x00([A-Z]+)\\x00", lambda m: giu[_so_cho(m.group(1))], moi)',
     '    moi = re.sub(r"\\x00(\\d+)\\x00", lambda m: giu[int(m.group(1))], moi)'),

    # ------------------------------------------------------------ đường HDL
    ("mo_phong KHÔNG xoá tệp sim cũ — biên dịch đổ vẫn báo PASS của lượt trước",
     HDL, "        _don_tep_ra(anh)\n        _chay(kq, lenh + ds,",
     "        _chay(kq, lenh + ds,"),

    ("chay của hdl.sensitivity không khai lỗi biên dịch",
     HDL, '                            loi_bien_dich=kq.nguyen_van if (not kq.dat and kq.loi) else "",',
     '                            loi_bien_dich="",'),

    ("chay của hdl.sensitivity khai lỗi biên dịch cho MỌI lượt không đạt (kể cả tb đỏ thật)",
     HDL, '                            loi_bien_dich=kq.nguyen_van if (not kq.dat and kq.loi) else "",',
     '                            loi_bien_dich=kq.nguyen_van if not kq.dat else "",'),

    ("do_do_nhay_hdl bỏ qua tham số bang, luôn dùng PHEP_VERILOG",
     HDL, "    bang_dung = bang or PHEP_VERILOG", "    bang_dung = PHEP_VERILOG"),

    # ------------------------------------------------------------ đường C
    ("_chay của test.sensitivity không khai lỗi biên dịch",
     XD, '                return DB.ket_qua_chay(dat=False, loi_bien_dich=kq.loi_bien_dich[-800:],',
     '                return DB.ket_qua_chay(dat=False, loi_bien_dich="",'),

    ("ket_qua_chay gắn tiền tố cho MỌI lượt không đạt (kể cả quá hạn)",
     DBF, "    if dat:\n        return True, log\n    if loi_bien_dich:\n"
          "        return False, TIEN_TO_BIEN_DICH + loi_bien_dich\n    return False, log",
     "    if dat:\n        return True, log\n"
     "    return False, TIEN_TO_BIEN_DICH + (loi_bien_dich or log)"),

    ("ket_qua_chay gắn tiền tố cả khi ĐẠT",
     DBF, "    if dat:\n        return True, log",
     "    if dat:\n        return True, TIEN_TO_BIEN_DICH + log"),

    # ------------------------------------------------------------ công cụ hdl.sensitivity
    ("hdl.sensitivity không trả so_mutant_khong_hop_le",
     TH, '            "so_mutant_khong_hop_le": sb,', "            "),

    ("hdl.sensitivity không ghi so_mutant_khong_hop_le vào kho",
     TH, '                          "so_mutant_khong_hop_le": sb, "chi_tiet": r_do["tep"]}',
     '                          "chi_tiet": r_do["tep"]}'),

    ("note_vi của hdl.sensitivity không nói ra mutant bị bỏ",
     TH, '                + (f" {sb} phép phá bị BỎ vì mutant không dịch được — chúng KHÔNG nằm trong "\n'
         '                   "con số trên, và cũng không nói gì về testbench." if sb else ""))}',
     "                )}"),
]


def _xoa_pycache():
    for d in list(GOC.glob("src/**/__pycache__")) + list(GOC.glob("tests/**/__pycache__")):
        shutil.rmtree(d, ignore_errors=True)


def _chay():
    r = subprocess.run([str(GOC / ".venv/bin/python"), "-m", "pytest", "-q", "-x", *TEP_TEST],
                       cwd=GOC, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


_xoa_pycache()
xanh, log = _chay()
if not xanh:
    print("DỪNG: bộ kiểm đang ĐỎ trước khi phá gì.\n", log[-2500:])
    sys.exit(1)
print(f"mốc: XANH — {log.strip().splitlines()[-1]}\n")

bat = lot = 0
for ten, tep, cu, moi in PHEP:
    p = GOC / tep
    van = p.read_text("utf-8")
    if cu not in van:
        print(f"[ ?  ] {ten}\n       KHÔNG tìm thấy chỗ phá trong {tep}")
        continue
    sau = van.replace(cu, moi, 1)
    if sau == van:
        print(f"[VÔ HIỆU] {ten}\n       phép phá KHÔNG đổi một byte nào — nó sẽ báo LỌT oan")
        continue
    try:
        p.write_text(sau, "utf-8")
        _xoa_pycache()
        xanh, log = _chay()
    finally:
        p.write_text(van, "utf-8")
        _xoa_pycache()
    dong = [x for x in log.strip().splitlines()
            if "passed" in x or "failed" in x or "error" in x]
    if not xanh:
        bat += 1
        print(f"[ĐỎ  ] {ten}\n       {dong[-1] if dong else ''}")
    else:
        lot += 1
        print(f"[LỌT ] {ten}\n       bộ kiểm VẪN XANH — không ca nào canh chỗ này")

print(f"\nPhá lại thì đỏ: {bat}/{bat + lot}")
