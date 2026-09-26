# -*- coding: utf-8 -*-
"""Sơ đồ bằng HTML/CSS: khối co giãn theo nội dung (không tràn, không đè); mũi tên SVG tính sau khi bố cục; chụp bằng Chromium."""
import json, html, os, subprocess

CSS = """
*{box-sizing:border-box}body{margin:0;background:#fff;font-family:"DejaVu Sans","Segoe UI",Arial,sans-serif;color:#1d1d1f}
#d{position:relative;padding:14px;width:WIDTHpx}
.rows{display:flex;flex-direction:column;gap:GAPpx}
.row{display:flex;gap:12px;align-items:stretch}
.row.center{justify-content:center}
.box{border:1.5px solid #1F2A44;border-radius:10px;padding:8px 10px;background:#fff;flex:1 1 0;min-width:0}
.box.fixed{flex:0 0 auto}
.box h4{margin:0 0 4px;font-size:12.5px;color:#1F2A44;text-align:center}
.box p{margin:2px 0;font-size:10.8px;line-height:1.35}
.box.red{border-color:#B8121F;background:#FDF3F4}.box.red h4{color:#B8121F}
.box.teal{border-color:#1B7F79;background:#EEF6F6}.box.teal h4{color:#1B7F79}
.box.gold{border-color:#B58900;background:#FFF8E1}.box.gold h4{color:#7a5b00}
.box.grey{border-color:#888;background:#F3F3F3}.box.grey h4{color:#444}
.box.plain{border-color:#1F2A44;background:#fff}
.box.wide{flex-basis:100%}
.note{font-size:10.5px;color:#444;text-align:center;padding:2px 6px}
.note.red{color:#B8121F}.note.b{font-weight:700;color:#1F2A44}
svg.ar{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
svg.ar text{font-size:10px;fill:#333}
.lab{font-size:10px;fill:#1F2A44}
/* sequence */
.seq{display:grid;grid-template-columns:repeat(NLANES,1fr);gap:0;position:relative}
.seq .lane{font-size:11px;font-weight:700;color:#1F2A44;text-align:center;padding:4px;border-bottom:1px solid #ccc}
.seq .msg{grid-column:1 / -1;position:relative;height:34px}
.seq .msg .line{position:absolute;top:22px;height:0;border-top:1.5px solid var(--c)}
.seq .msg .line::after{content:"";position:absolute;right:-1px;top:-5px;border:5px solid transparent;border-left:8px solid var(--c)}
.seq .msg .line.left::after{right:auto;left:-1px;border-left:5px solid transparent;border-right:8px solid var(--c)}
.seq .msg .txt{position:absolute;top:2px;font-size:10px;color:var(--c);white-space:nowrap;background:#fff;padding:0 3px}
.seq .vl{position:absolute;top:28px;bottom:0;border-left:1px dashed #bbb}
/* timeline */
.tl{display:flex;gap:6px}
.tl .cs{flex:1 1 0;min-width:0;border:1.2px solid #1B7F79;background:#EEF6F6;border-radius:8px;padding:5px 4px;text-align:center;font-size:9.8px}
.tl .cs.human{border-color:#B8121F;background:#FDF3F4}.tl .cs.snap{border-color:#B58900;background:#FFF8E1;border-width:2px}
.tl .cs b{display:block;font-size:10.5px;color:#1F2A44}.tl .cs i{display:block;color:#555;font-style:normal;font-size:9px}
.tl .cs .u{color:#1B7F79}.tl .cs .n{color:#B8121F}
/* context window stack */
.stack{display:flex;flex-direction:column;gap:4px}
.stack div{display:flex;justify-content:space-between;border:1px solid #bbb;border-radius:5px;padding:3px 8px;font-size:10.5px;background:#fff}
.stack div.gold{background:#FFF8E1}.stack div.teal{background:#EEF6F6}.stack div.red{background:#FDF3F4}.stack div.grey{background:#F3F3F3}
"""

JS = """
function draw(arrows){
  const d=document.getElementById('d'), r0=d.getBoundingClientRect();
  const svg=document.querySelector('svg.ar'); const NS='http://www.w3.org/2000/svg';
  svg.innerHTML='<defs><marker id="m" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="context-stroke"/></marker></defs>';
  for(const a of arrows){
    const A=document.getElementById(a.from).getBoundingClientRect(), B=document.getElementById(a.to).getBoundingClientRect();
    let x1,y1,x2,y2;
    const cx=r=>r.left-r0.left+r.width/2, cy=r=>r.top-r0.top+r.height/2;
    if(a.dir==='down'){x1=cx(A)+(a.ox||0);y1=A.bottom-r0.top;x2=cx(B)+(a.ox2||a.ox||0);y2=B.top-r0.top;}
    else if(a.dir==='up'){x1=cx(A)+(a.ox||0);y1=A.top-r0.top;x2=cx(B)+(a.ox2||a.ox||0);y2=B.bottom-r0.top;}
    else if(a.dir==='right'){x1=A.right-r0.left;y1=cy(A)+(a.oy||0);x2=B.left-r0.left;y2=cy(B)+(a.oy2||a.oy||0);}
    else {x1=A.left-r0.left;y1=cy(A)+(a.oy||0);x2=B.right-r0.left;y2=cy(B)+(a.oy2||a.oy||0);}
    const col=a.color||'#1F2A44';
    let path;
    if(a.dir==='down'||a.dir==='up'){const my=(y1+y2)/2;path=`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;}
    else {const mx=(x1+x2)/2;path=`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;}
    const p=document.createElementNS(NS,'path');p.setAttribute('d',path);p.setAttribute('fill','none');p.setAttribute('stroke',col);p.setAttribute('stroke-width',a.w||1.4);p.setAttribute('marker-end','url(#m)');
    if(a.dash)p.setAttribute('stroke-dasharray','4 3');svg.appendChild(p);
    if(a.label){const tx=(x1+x2)/2+(a.lx||0), ty=(y1+y2)/2+(a.ly||0);const t=document.createElementNS(NS,'text');t.setAttribute('x',tx);t.setAttribute('y',ty);t.setAttribute('text-anchor','middle');t.setAttribute('fill',col);t.textContent=a.label;
      const bg=document.createElementNS(NS,'rect');svg.appendChild(t);const bb=t.getBBox();bg.setAttribute('x',bb.x-3);bg.setAttribute('y',bb.y-1);bg.setAttribute('width',bb.width+6);bg.setAttribute('height',bb.height+2);bg.setAttribute('fill','#fff');bg.setAttribute('opacity','.9');svg.insertBefore(bg,t);}
  }
}
"""

def box(id_, title, lines=(), cls='plain', extra=''):
    ls = ''.join(f'<p>{html.escape(l)}</p>' for l in lines)
    return f'<div class="box {cls}" id="{id_}" {extra}><h4>{html.escape(title)}</h4>{ls}</div>'

def render(name, body, arrows=(), width=1000, gap=22, nlanes=5):
    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS.replace("WIDTH", str(width)).replace("GAP", str(gap)).replace("NLANES", str(nlanes))}</style></head><body><div id="d">{body}<svg class="ar"></svg></div><script>{JS}draw({json.dumps(list(arrows), ensure_ascii=False)});</script></body></html>'
    os.makedirs('/home/claude/eide-agd/diag/html', exist_ok=True)
    p = f'/home/claude/eide-agd/diag/html/{name}.html'
    open(p, 'w').write(page)
    return p

def shoot(names):
    js = "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});const p=await b.newPage({deviceScaleFactor:2});" + \
         "".join(f"await p.goto('file:///home/claude/eide-agd/diag/html/{n}.html');await p.waitForTimeout(150);await p.locator('#d').screenshot({{path:'/home/claude/eide-agd/{n}.png'}});" for n in names) + "await b.close();})();"
    open('/home/claude/eide-agd/diag/shoot.js', 'w').write(js)
    subprocess.run(['node', '/home/claude/eide-agd/diag/shoot.js'], check=True)
