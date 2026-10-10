# -*- coding: utf-8 -*-
"""Thiết kế GIAO DIỆN cho màn hình của bo — mô hình, render HTML, sinh code C.

Hiện vật gốc là `mo_hinh.ManHinh` (JSON trong kho, hoàn tác được, có STALE như mọi hiện vật
khác). HTML và code C đều là bản **dựng ra** từ nó.

Vì sao không lấy HTML làm bản gốc: bước "chuyển thành code" sẽ phải đọc lại HTML để suy ra ý
định, và đó là việc mất thông tin — `<div>` không nói nó là nhãn hay nút, `left: 37%` không nói
toạ độ pixel nào trên panel 800×480. Một nguồn, hai bản dựng, nên chúng không lệch nhau được.
"""
