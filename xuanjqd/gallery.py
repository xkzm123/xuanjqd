"""生成一个自包含的 HTML 画廊（双击就能看，也能直接打印）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .models import Talk
from .theme import Theme, get_theme

_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --accent:__ACCENT__; --accent2:__ACCENT2__; --ink:__INK__; --sub:__SUB__; --page:__PAGE__;
    --card:#fff; --line:#e6eaf2;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--page);color:var(--ink);
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       -webkit-font-smoothing:antialiased}
  .hero{padding:44px 32px 38px;color:#fff;
        background:linear-gradient(120deg,var(--accent) 0%,var(--accent2) 100%)}
  .hero .wrap{max-width:1180px;margin:0 auto}
  .kicker{font-size:13px;letter-spacing:.18em;text-transform:uppercase;opacity:.75}
  h1{margin:10px 0 6px;font-size:34px;letter-spacing:-.02em}
  .sub{opacity:.85;font-size:15px}
  .stats{display:flex;gap:14px;margin-top:24px;flex-wrap:wrap}
  .stat{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);
        border-radius:14px;padding:10px 16px;backdrop-filter:blur(6px)}
  .stat b{display:block;font-size:20px;line-height:1.2}
  .stat span{font-size:12px;opacity:.8}
  .toolbar{position:sticky;top:0;z-index:9;background:rgba(255,255,255,.86);
           backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .toolbar .wrap{max-width:1180px;margin:0 auto;padding:14px 32px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  input[type=search]{flex:1;min-width:200px;border:1px solid var(--line);border-radius:11px;
        padding:10px 14px;font-size:14px;outline:none;background:#fff}
  input[type=search]:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(31,111,235,.12)}
  .chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 14px;
        font-size:13px;cursor:pointer;color:var(--sub)}
  .chip[aria-pressed=true]{background:var(--accent);color:#fff;border-color:var(--accent)}
  .btn{border:0;border-radius:11px;padding:10px 16px;font-size:14px;cursor:pointer;
       background:var(--accent);color:#fff;font-weight:600}
  .btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--line);font-weight:500}
  main{max-width:1180px;margin:0 auto;padding:28px 32px 80px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:22px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;
        box-shadow:0 1px 2px rgba(15,23,42,.04);transition:.22s ease;cursor:pointer;display:flex;flex-direction:column}
  .card:hover{transform:translateY(-3px);box-shadow:0 14px 30px rgba(15,23,42,.10);border-color:#cfd9ea}
  .card img{width:100%;display:block;background:#fff}
  .card .meta{padding:14px 16px 16px;border-top:1px solid var(--line)}
  .card h3{margin:0 0 6px;font-size:15px;line-height:1.35}
  .card p{margin:0;font-size:12.5px;color:var(--sub);line-height:1.55}
  .tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
  .tag{font-size:11px;padding:3px 8px;border-radius:999px;background:rgba(31,111,235,.09);color:var(--accent)}
  .empty{padding:80px 0;text-align:center;color:var(--sub)}
  .modal{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:center;
         justify-content:center;padding:24px;z-index:50;backdrop-filter:blur(3px)}
  .modal.on{display:flex}
  .modal .box{background:#fff;border-radius:22px;max-width:560px;width:100%;padding:22px;
              max-height:90vh;overflow:auto;position:relative}
  .modal img{width:100%;border-radius:14px;border:1px solid var(--line)}
  .modal .close{position:absolute;right:14px;top:12px;border:0;background:#f1f5f9;border-radius:10px;
                width:32px;height:32px;font-size:17px;cursor:pointer;color:var(--sub)}
  .modal code{display:block;word-break:break-all;font-size:11.5px;background:#f8fafc;border:1px solid var(--line);
              border-radius:10px;padding:10px;margin-top:12px;color:var(--sub)}
  footer{text-align:center;color:var(--sub);font-size:12.5px;padding:0 0 48px}
  @media print{
    .hero{padding:18px 0;color:#000;background:none}
    .hero .stats,.toolbar,footer,.modal{display:none!important}
    .grid{grid-template-columns:repeat(3,1fr);gap:10px}
    .card{break-inside:avoid;box-shadow:none;border:1px dashed #bbb;border-radius:8px}
    .card .meta{padding:6px 8px}
    body{background:#fff}
  }
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <div class="kicker">XUANJQD STUDIO</div>
    <h1>__TITLE__</h1>
    <div class="sub">__SUBTITLE__</div>
    <div class="stats">
      <div class="stat"><b>__COUNT__</b><span>场宣讲会</span></div>
      <div class="stat"><b>__DAYS__</b><span>个日期</span></div>
      <div class="stat"><b>__SPAN__</b><span>时间跨度</span></div>
      <div class="stat"><b>__BUILT__</b><span>生成时间</span></div>
    </div>
  </div>
</header>

<div class="toolbar">
  <div class="wrap">
    <input type="search" id="q" placeholder="搜索公司 / 地点 / 标签 / 编号…">
    <div id="dates" style="display:flex;gap:8px;flex-wrap:wrap"></div>
    <button class="btn ghost" id="print">打印 / 存 PDF</button>
  </div>
</div>

<main>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">没有匹配的宣讲会</div>
</main>

<footer>由 <b>xuanjqd</b> 生成 · 二维码内容为平台签到链接 · 仅用于个人日程管理</footer>

<div class="modal" id="modal">
  <div class="box">
    <button class="close" id="close">×</button>
    <img id="mimg" alt="签到二维码">
    <div id="minfo" style="margin-top:14px;font-size:14px;line-height:1.7"></div>
    <code id="murl"></code>
  </div>
</div>

<script>
const DATA = __DATA__;
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const q = document.getElementById('q');
let activeDate = null;

const dates = [...new Set(DATA.map(d => d.date_label))];
const dbox = document.getElementById('dates');
dbox.innerHTML = '<button class="chip" data-d="" aria-pressed="true">全部</button>' +
  dates.map(d => `<button class="chip" data-d="${d}" aria-pressed="false">${d}</button>`).join('');
dbox.addEventListener('click', e => {
  const b = e.target.closest('.chip'); if(!b) return;
  activeDate = b.dataset.d || null;
  [...dbox.children].forEach(c => c.setAttribute('aria-pressed', String(c === b)));
  render();
});

function card(d){
  return `<article class="card" data-id="${d.id}">
    <img loading="lazy" src="${d.img}" alt="${d.company} 签到二维码">
    <div class="meta">
      <h3>${d.company || ('宣讲会 #' + d.id)}</h3>
      <p>${d.date_label} ${d.time_label || ''}${d.location ? ' · ' + d.location : ''}</p>
      <div class="tags">${(d.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}
        <span class="tag">#${d.id}</span></div>
    </div>
  </article>`;
}

function render(){
  const kw = q.value.trim().toLowerCase();
  const rows = DATA.filter(d => {
    if (activeDate && d.date_label !== activeDate) return false;
    if (!kw) return true;
    return [d.company, d.location, d.title, String(d.id), (d.tags||[]).join(' ')]
      .join(' ').toLowerCase().includes(kw);
  });
  grid.innerHTML = rows.map(card).join('');
  empty.style.display = rows.length ? 'none' : 'block';
}

q.addEventListener('input', render);
document.getElementById('print').addEventListener('click', () => window.print());
grid.addEventListener('click', e => {
  const el = e.target.closest('.card'); if(!el) return;
  const d = DATA.find(x => String(x.id) === el.dataset.id); if(!d) return;
  document.getElementById('mimg').src = d.img;
  document.getElementById('minfo').innerHTML =
    `<b>${d.company || ('宣讲会 #' + d.id)}</b><br>${d.date_label} ${d.time_label||''} · ${d.location||'地点待定'}<br>编号 #${d.id}`;
  document.getElementById('murl').textContent = d.url;
  document.getElementById('modal').classList.add('on');
});
document.getElementById('close').onclick = () => document.getElementById('modal').classList.remove('on');
document.getElementById('modal').onclick = e => { if(e.target.id === 'modal') e.currentTarget.classList.remove('on'); };
document.addEventListener('keydown', e => { if(e.key === 'Escape') document.getElementById('modal').classList.remove('on'); });
render();
</script>
</body>
</html>
"""


def write_gallery(
    out_dir: str | Path,
    talks: Sequence[Talk],
    *,
    title: str = "宣讲会签到码",
    subtitle: str = "扫码即可签到 · 点击卡片查看大图",
    img_dir: str = "qr",
    theme: Theme | str | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    theme = get_theme(theme)

    rows = []
    for t in talks:
        rows.append(
            {
                "id": t.id,
                "company": t.display_name,
                "title": t.title,
                "date_label": t.date_label,
                "time_label": t.time_label,
                "location": t.location,
                "tags": list(t.tags),
                "img": f"{img_dir}/{t.id}.png",
                "url": t.signin_url,
            }
        )

    days = sorted({t.start_at.strftime("%Y-%m-%d") for t in talks if t.start_at})
    span = "—"
    if days:
        span = days[0][5:] if len(days) == 1 else f"{days[0][5:]} ~ {days[-1][5:]}"

    html = (
        _TEMPLATE.replace("__TITLE__", title)
        .replace("__SUBTITLE__", subtitle)
        .replace("__ACCENT__", theme.dark)
        .replace("__ACCENT2__", theme.dark2)
        .replace("__INK__", theme.ink)
        .replace("__SUB__", theme.sub)
        .replace("__PAGE__", theme.page)
        .replace("__COUNT__", str(len(talks)))
        .replace("__DAYS__", str(len(days)))
        .replace("__SPAN__", span)
        .replace("__BUILT__", datetime.now().strftime("%m-%d %H:%M"))
        .replace("__DATA__", json.dumps(rows, ensure_ascii=False))
    )
    path = out_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
