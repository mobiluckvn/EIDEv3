# -*- coding: utf-8 -*-
"""Giao thuc dieu khien giao dien UAP v1.1 — EIDE-MDD-40 Phan D.

Sau bat bien (§D1):
  I1  Mot cua vao: loi chi nhan thao tac nguoi qua console.act/HumanAct.
  I2  Mot dong hoi thoai: moi HumanAct -> dung mot dong "[Ban] ...".
  I3  Giao dien khong quyet: chi render SurfaceModel/Card do loi gui.
  I4  Loi khong biet giao dien: chi thay HumanAct (y chi + xuat xu).
  I5  Co thu tu (seq), khong trung (id), khoi phuc duoc (resume seq).
  I6  Cong la the rieng: chi HumanAct kind=decide voi gate_id dang cho moi mo cong.
"""

from .humanact import HumanAct, Origin, Target, HUMAN_ACT_KINDS
from .uicommand import UICommand, UI_COMMANDS

__all__ = ["HumanAct", "Origin", "Target", "HUMAN_ACT_KINDS", "UICommand", "UI_COMMANDS"]
