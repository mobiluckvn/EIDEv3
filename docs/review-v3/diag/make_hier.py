# -*- coding: utf-8 -*-
from diagram_html import box, render, shoot
b = f"""<div class="rows">
<div class="row center"><div class="note b">Một mô hình duy nhất: Module là nút cây; linh kiện là LÁ. Net sống trong phạm vi một khối; ra ngoài chỉ qua Port. Netlist phẳng (ERC/SKiDL/KiCad .net) = flatten(cây) bằng mã</div></div>
<div class="row">{box('board','Mạch (Module kind=board, gốc)',['Port: VBUS_IN(power) · USB(bus) · ETH(bus)','Net phạm vi board: VBUS_5V, GND, +3V3, I2C0.SDA/SCL …','Fact/REQ gắn cấp mạch: I.total ≤ 500 mA'],'gold')}</div>
<div class="row">{box('pwr','Khối Nguồn (block) — LDO-3V3 @1.2.0 (thư viện)',['Port: VIN(power in) · 3V3(power out) · GND','Net cục bộ: VIN, VOUT, GND','Fact khối: Iout.max = 800 mA (DS AMS1117 p.3, VÀNG)'],'teal')}{box('mcu','Khối MCU (block)',['Port: 3V3 · GND · I2C0 (bus: SDA, SCL) · SPI0 · UART0','Net cục bộ: VDD, NRST, XTAL1/2 …','Khối con: Dao động thạch anh (subblock) · Reset (subblock)'],'teal')}{box('sens','Khối Cảm biến (block)',['Port: 3V3 · GND · I2C (bus)','Net cục bộ: SDA, SCL (có pull-up)','Fact khối: addr = 0x48 (DS TMP102 p.7)'],'teal')}</div>
<div class="row">{box('xtal','Dao động (subblock)',['Port: XI · XO · GND','Lá: Y1 16 MHz · C3 22 pF · C4 22 pF'],'plain')}{box('leaf1','U1 ATmega328P (leaf)',['Port = pin: 1..28 (từ Fact pinout VÀNG)','ref U1 · MPN · datasheet · BOM row'],'grey')}{box('leaf2','R1 4,7 kΩ · R2 4,7 kΩ · U2 TMP102 (leaf)',['Port = pin; giá trị từ Fact/NGƯỜI','BOM row · footprint'],'grey')}</div>
<div class="row center"><div class="note">Nối liên khối chỉ qua Port: board.I2C0 ⟷ mcu.I2C0 ⟷ sens.I2C · Sửa NỘI BỘ một khối (không chạm Port) → không STALE ra ngoài · Sửa Port → mọi khối nối vào Port đó STALE</div></div>
</div>"""
ar = [dict(**{'from': 'board', 'to': 'pwr', 'dir': 'down', 'label': 'chứa'}), dict(**{'from': 'board', 'to': 'mcu', 'dir': 'down'}), dict(**{'from': 'board', 'to': 'sens', 'dir': 'down'}),
      dict(**{'from': 'mcu', 'to': 'xtal', 'dir': 'down', 'label': 'chứa'}), dict(**{'from': 'mcu', 'to': 'leaf1', 'dir': 'down'}), dict(**{'from': 'sens', 'to': 'leaf2', 'dir': 'down'}),
      dict(**{'from': 'mcu', 'to': 'sens', 'dir': 'right', 'color': '#B8121F'}), dict(**{'from': 'pwr', 'to': 'mcu', 'dir': 'right', 'color': '#B8121F'})]
render('h1_hierarchy', b, ar, width=1000, gap=46)
shoot(['h1_hierarchy'])
print('ok')
