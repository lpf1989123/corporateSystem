/* ==========================================================================
   鲁信环境 · 企业制度门户  ——  前端核心
   ========================================================================== */
const API = '';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* ---------------- 工具 ---------------- */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nl2br = s => esc(s).replace(/\n/g, '<br>');

function toast(msg, type = 'ok') {
  let box = $('.toast-box');
  if (!box) { box = document.createElement('div'); box.className = 'toast-box'; document.body.appendChild(box); }
  const ic = { ok: '✓', err: '✕', warn: '!' }[type] || '✓';
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.innerHTML = `<span style="font-weight:700">${ic}</span><span>${esc(msg)}</span>`;
  box.appendChild(el);
  setTimeout(() => { el.style.transition = '.3s'; el.style.opacity = '0'; el.style.transform = 'translateY(-10px)'; setTimeout(() => el.remove(), 320); }, 2600);
}

function fmtDate(s) {
  if (!s) return '—';
  return String(s).slice(0, 16);
}

function relTime(s) {
  if (!s) return '';
  const t = new Date(String(s).replace(/-/g, '/'));
  if (isNaN(t)) return s;
  const d = (Date.now() - t.getTime()) / 1000;
  if (d < 60) return '刚刚';
  if (d < 3600) return Math.floor(d / 60) + ' 分钟前';
  if (d < 86400) return Math.floor(d / 3600) + ' 小时前';
  if (d < 604800) return Math.floor(d / 86400) + ' 天前';
  return String(s).slice(0, 10);
}

async function api(path, opt = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opt.headers || {}) };
  const tk = sessionStorage.getItem('token');
  if (tk) headers['X-Token'] = tk;
  const res = await fetch(API + path, { ...opt, headers });
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('json')) return { code: res.ok ? 0 : res.status, msg: '响应异常' };
  return res.json();
}

const PALETTE = ['#0e5a8a', '#1a9c6b', '#c8a86b', '#7c62be', '#c0653f', '#2ea3d6', '#a0459c', '#3f7fc0'];
const avatarColor = name => PALETTE[[...String(name || '?')].reduce((a, c) => a + c.charCodeAt(0), 0) % PALETTE.length];
const initials = name => String(name || '?').trim().slice(0, 1).toUpperCase();
const catClass = cat => ({ '人力资源': 'c1', '财务制度': 'c2', '信息技术': 'c3', '综合管理': 'c4' }[cat] || 'c1');

/* ---------------- 图标 ---------------- */
const ICON = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v5h5"/><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h9l5 5v13z"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7"><path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="2.6"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round"><path d="M21 12a8 8 0 01-8 8H7l-4 3v-7.5A8 8 0 018 4h5a8 8 0 018 8z"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M5 12h13"/><path d="M13 6l6 6-6 6"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round"><path d="M20.6 13.4l-7.2 7.2a2 2 0 01-2.8 0L3 13V3h10l7.6 7.6a2 2 0 010 2.8z"/><circle cx="7.5" cy="7.5" r="1.3"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M12 19V5"/><path d="M6 11l6-6 6 6"/></svg>',
  print: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6"/><path d="M6 18H4v-6h16v6h-2"/><path d="M6 14h12v7H6z"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linejoin="round"><path d="M12 22s8-3.4 8-10V5l-8-3-8 3v7c0 6.6 8 10 8 10z"/></svg>',
  lustre: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" stroke="#fff"><path d="M12 3l2.4 6.2L21 11l-6.6 1.8L12 19l-2.4-6.2L3 11l6.6-1.8z"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linejoin="round"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>',
  building: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linejoin="round"><path d="M4 21V5a2 2 0 012-2h7a2 2 0 012 2v16"/><path d="M15 9h4a2 2 0 012 2v10"/><path d="M2 21h20"/><path d="M8 7h3M8 11h3M8 15h3"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5L20 6.5"/></svg>',
  filePdf: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linejoin="round"><path d="M14 3v5h5"/><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h9l5 5v13z"/><path d="M9 13h1.5a1.5 1.5 0 010 3H9v-3zm0 3v3"/><path d="M14 13v6"/></svg>',
};

/* ---------------- 顶栏 + 页脚 ---------------- */
function topbar(active) {
  return `
  <header class="top">
    <div class="top-in">
      <a class="logo" href="#/">
        <img class="logo-img" src="/logo2.png" alt="鲁信环境">
      </a>
    </div>
  </header>`;
}

function footer() {
  return `
  <footer class="foot">
    <div class="foot-bar">
      <span>© 2026 鲁信天地人环境科技集团有限公司 · 内部资料，请勿外传</span>
      <span class="foot-disc">免责声明：本手册内容如与公司现行有效制度不一致，以公司正式发布并实际执行的制度为准。</span>
    </div>
  </footer>`;
}

function shell(active, inner) {
  return `${topbar(active)}<main id="main">${inner}</main>${footer()}<div class="gotop" id="gotop" onclick="scrollTo({top:0,behavior:'smooth'})">${ICON.up}</div>`;
}

/* ---------------- 首页 ---------------- */
async function renderHome(main, params) {
  const [cats, pols, settings] = await Promise.all([
    api('/api/categories').then(r => r.data || []),
    api('/api/policies').then(r => r.data || []),
    api('/api/settings').then(r => r.data || {}),
  ]);
  const state = { cat: params.get('cat') || '', kw: '' };
  const hots = String(settings.hot_keywords || '')
    .split(/[,，\n]/).map(s => s.trim()).filter(Boolean);
  const hotHint = hots.slice(0, 3).map(k => `「${k}」`).join('') || '「关键词」';

  main.innerHTML = shell('home', `
  <section class="hero">
    <div class="hero-in">
      <div class="hero-tag"><i></i>无纸化学习 · 环保从一本手册开始</div>
      <h1>读懂公司，从这本手册开始</h1>
      <div class="hero-search">
        ${ICON.search.replace('stroke-width="2"', 'stroke-width="2" stroke="#c8d8e6" style="width:19px;height:19px"')}
        <input id="hq" placeholder="试试搜索${hotHint}…" autocomplete="off">
        <button onclick="heroSearch()">立即检索</button>
      </div>
      ${hots.length ? `
      <div class="hero-hots">
        <b>热门搜索</b>
        ${hots.map(k => `<span class="chip-hot" onclick='heroSearch(${JSON.stringify(k)})'>${esc(k)}</span>`).join('')}
      </div>` : ''}
    </div>
  </section>


  <div class="wrap">
    <section class="sect">
      <div class="sect-head">
        <div>
          <h2>规章制度</h2>
          <p>按分类浏览，共 ${pols.length} 部制度</p>
        </div>
      </div>
      <div class="filters" id="filters">
        <button class="fchip on" data-cat="">全部<i>${pols.length}</i></button>
        ${cats.filter(c => c.n > 0).map(c => `<button class="fchip" data-cat="${esc(c.category)}">${esc(c.category)}<i>${c.n}</i></button>`).join('')}
      </div>
      <div class="grid" id="plist">${pols.map(pcard).join('')}</div>
    </section>
  </div>`);

  const doFilter = (cat) => {
    state.cat = cat;
    $$('#filters .fchip').forEach(b => b.classList.toggle('on', b.dataset.cat === cat));
    const list = cat ? pols.filter(p => p.category === cat) : pols;
    const box = $('#plist');
    box.innerHTML = list.length ? list.map(pcard).join('')
      : `<div class="empty" style="grid-column:1/-1">${ICON.file}<b>该分类下暂无制度</b></div>`;
  };
  $$('#filters .fchip').forEach(b => b.onclick = () => doFilter(b.dataset.cat));
  if (state.cat) doFilter(state.cat);
  $('#hq').addEventListener('keydown', e => { if (e.key === 'Enter') heroSearch(); });
}

function heroSearch(k) {
  const v = k || ($('#hq') && $('#hq').value.trim()) || '';
  location.hash = '#/search' + (v ? '?q=' + encodeURIComponent(v) : '');
}

function pcard(p) {
  return `
  <a class="pcard" href="#/doc/${p.id}">
    <div class="pcard-top">
      <span class="pcat ${catClass(p.category)}">${esc(p.category)}</span>
      <span class="pver">${esc(p.version)}</span>
    </div>
    <h3>${esc(p.title)}</h3>
    <div class="sum">${esc(p.summary || '暂无摘要')}</div>
    <div class="pcard-foot">
      <span class="f">${ICON.eye}${p.views || 0}</span>
      <span class="f">${ICON.clock}${esc((p.effective_date || p.updated_at || '').slice(0, 10))}</span>
      <span class="go">查阅${ICON.arrow}</span>
    </div>
  </a>`;
}

/* ---------------- 列表页 ---------------- */
async function renderList(main, params) {
  const cat = params.get('cat') || '';
  const [cats, pols] = await Promise.all([
    api('/api/categories').then(r => r.data || []),
    api('/api/policies' + (cat ? '?category=' + encodeURIComponent(cat) : '')).then(r => r.data || []),
  ]);
  main.innerHTML = shell('list', `
    <section class="doc-hero">
      <div class="doc-hero-in">
        <div class="crumb"><a href="#/">制度门户</a> / <span>全部制度</span></div>
        <h1>全部制度</h1>
        <div class="doc-meta">
          <span class="mitem">${ICON.folder}共 ${pols.length} 部</span>
          <span class="mitem">${ICON.shield}现行有效</span>
        </div>
      </div>
    </section>
    <div class="wrap" style="padding-top:30px;padding-bottom:60px">
      <div class="filters">
        <button class="fchip ${!cat ? 'on' : ''}" data-cat="">全部</button>
        ${cats.filter(c => c.n > 0).map(c => `<button class="fchip ${cat === c.category ? 'on' : ''}" data-cat="${esc(c.category)}">${esc(c.category)}<i>${c.n}</i></button>`).join('')}
      </div>
      <div class="grid">${pols.length ? pols.map(pcard).join('')
      : `<div class="empty" style="grid-column:1/-1">${ICON.file}<b>暂无制度</b><span>请切换分类或联系管理员</span></div>`}</div>
    </div>`);
  $$('.fchip').forEach(b => b.onclick = () => {
    const c = b.dataset.cat;
    location.hash = '#/list' + (c ? '?cat=' + encodeURIComponent(c) : '');
  });
}

/* ---------------- 阅读页 ---------------- */
async function renderDoc(main, id, params) {
  main.innerHTML = `<div style="padding:120px;text-align:center;color:var(--ink-4)">正在载入制度全文…</div>`;
  const r = await api('/api/policies/' + id);
  if (r.code !== 0) { main.innerHTML = shell('', `<div class="empty" style="padding:140px">${ICON.file}<b>制度不存在或已下架</b></div>`); return; }
  const d = r.data;

  // 优先按 Markdown 正文渲染（保留 Word 原文顺序与图片）；无正文时再回退 sections
  // 目录：## 第x章 = 一级，### 第x条 = 二级
  let toc = '', bodyHtml = '';
  if (d.content && String(d.content).trim()) {
    bodyHtml = mdRender(d.content);
    toc = buildMdToc(d.content);
  } else if (d.sections && d.sections.length) {
    bodyHtml = d.sections.map((s, si) => {
      const sid = 'sec-' + si;
      let h = s.no ? `<h2 id="${sid}">${esc(s.no)} ${esc(s.title)}</h2>` : `<h2 id="${sid}">${esc(s.title)}</h2>`;
      let inner = '';
      s.articles.forEach((a, ai) => {
        const aid = `${sid}-${ai}`;
        if (a.no || a.title) {
          const label = (a.no ? a.no + ' ' : '') + (a.title || '');
          h += `<h3 id="${aid}">${esc(label)}</h3>`;
        }
        inner += (a.paras || []).map(p => `<p class="md-p">${esc(p)}</p>`).join('');
      });
      return h + inner;
    }).join('');
    toc = d.sections.map((s, si) => {
      const sid = 'sec-' + si;
      let subs = s.articles.filter(a => a.no || a.title)
        .map(a => `<a class="toc-sub" href="#${sid}-${s.articles.indexOf(a)}" data-t="${sid}-${s.articles.indexOf(a)}">${esc((a.no ? a.no + ' ' : '') + a.title)}</a>`).join('');
      return `<a class="toc-a" href="#${sid}" data-t="${sid}"><span class="n">${s.no ? esc(String(s.no).replace('第', '').replace('章', '')) : '·'}</span>${esc(s.title)}</a>${subs}`;
    }).join('');
  } else {
    bodyHtml = '<p class="md-p">暂无正文</p>';
  }

  main.innerHTML = shell('', `
  <div class="prog" id="prog"></div>
  <section class="doc-hero">
    <div class="doc-hero-in">
      <h1>${esc(d.title)}</h1>
      <div class="doc-meta">
        <span class="mitem">${ICON.tag}${esc(d.category)}</span>
        <span class="mitem">${ICON.shield}${esc(d.version)}</span>
        <span class="mitem">${ICON.clock}${esc(d.effective_date || '—')} 施行</span>
        <span class="mitem">${ICON.building}${esc(d.publisher || '—')}</span>
        <span class="mitem">${ICON.eye}${d.views || 0} 次查阅</span>
      </div>
    </div>
  </section>
  <div class="doc-body">
    <aside class="rail">
      <div class="rail-box">
        <div class="rail-t">目录</div>
        ${toc || '<div style="font-size:13px;color:var(--ink-4)">暂无目录</div>'}
      </div>
      <div class="rail-box">
        <div class="rail-t">制度信息</div>
        <div style="font-size:13px;line-height:2.1;color:var(--ink-3)">
          <div>发布部门：${esc(d.publisher || '—')}</div>
          <div>版本号：${esc(d.version)}</div>
          <div>施行日期：${esc(d.effective_date || '—')}</div>
          <div>最近更新：${esc((d.updated_at || '').slice(0, 10))}</div>
        </div>
      </div>
    </aside>
    <article class="content" id="doc-content">${bodyHtml}</article>
  </div>`);

  // 目录高亮 + 进度条
  const heads = $$('#doc-content h2, #doc-content h3');
  const onScroll = () => {
    const top = $('#doc-content').getBoundingClientRect().top + scrollY;
    const p = Math.min(100, Math.max(0, (scrollY - top + 260) / ($('#doc-content').offsetHeight) * 100));
    $('#prog').style.width = p + '%';
    $('#gotop').classList.toggle('show', scrollY > 620);
    let cur = null;
    heads.forEach(h => { if (h.getBoundingClientRect().top < 140) cur = h.id; });
    $$('.toc-a,.toc-sub').forEach(a => a.classList.toggle('on', a.dataset.t === cur));
  };
  addEventListener('scroll', onScroll, { passive: true });
  requestAnimationFrame(onScroll);

  // 目录点击滚动偏移
  $$('a[href^="#md-"], a[href^="#sec-"]').forEach(a => a.onclick = e => {
    e.preventDefault();
    const el = document.getElementById(a.getAttribute('href').slice(1));
    if (el) { scrollTo({ top: el.getBoundingClientRect().top + scrollY - 92, behavior: 'smooth' }); }
  });
}

function copyLink() {
  navigator.clipboard.writeText(location.href).then(() => toast('链接已复制到剪贴板'), () => toast('复制失败', 'err'));
}

/* 标题枚举（与 mdRender 共用同一套 id 规则） */
function iterMdHeadings(md) {
  const out = [];
  let hid = 0;
  for (const raw of String(md).split('\n')) {
    const m = raw.trim().match(/^(#{1,6})\s+(.*)$/);
    if (!m) continue;
    out.push({ hashes: m[1].length, id: 'md-' + (hid++), text: m[2] });
  }
  return out;
}

/* ## 第x章 → 一级目录；### 第x条 → 二级目录 */
function buildMdToc(md) {
  return iterMdHeadings(md).map(h => {
    if (h.hashes === 2) {
      return `<a class="toc-a" href="#${h.id}" data-t="${h.id}">${esc(h.text)}</a>`;
    }
    if (h.hashes >= 3) {
      return `<a class="toc-sub" href="#${h.id}" data-t="${h.id}">${esc(h.text)}</a>`;
    }
    return '';
  }).join('');
}

/* 收集连续列表项：中间空行不拆开 */
function collectMdList(lines, start, reItem, strip) {
  const it = [];
  let i = start;
  while (i < lines.length) {
    const t = lines[i].trim();
    if (!t) { i++; continue; }
    if (!reItem.test(t)) break;
    it.push(t.replace(strip, ''));
    i++;
  }
  return [it, i];
}

/* 轻量 Markdown 渲染 */
function mdRender(md) {
  const lines = String(md).split('\n');
  let html = '', i = 0, hid = 0;
  while (i < lines.length) {
    const raw = lines[i];
    const s = raw.trim();
    if (!s) { i++; continue; }
    // 图片 ![alt](url)
    let im = s.match(/^!\[([^\]]*)\]\(([^)]+)\)/);
    if (im) {
      html += `<figure class="md-fig"><img src="${esc(im[2])}" alt="${esc(im[1] || '')}" loading="lazy"></figure>`;
      i++; continue;
    }
    if (s.startsWith('|') && /^\|[\s:\-|]+\|$/.test((lines[i + 1] || '').trim())) {
      const head = s.replace(/^\||\|$/g, '').split('|').map(x => x.trim());
      i += 2; const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(lines[i].trim().replace(/^\||\|$/g, '').split('|').map(x => x.trim())); i++; }
      html += '<div class="tb-wrap"><table><thead><tr>' + head.map(h => `<th>${esc(h)}</th>`).join('') + '</tr></thead><tbody>'
        + rows.map(r => '<tr>' + r.map(c => `<td>${esc(c)}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
      continue;
    }
    let m = s.match(/^(#{1,6})\s+(.*)$/);
    if (m) {
      // ## 章 → h2（一级）；### 条 → h3（二级）
      const tag = m[1].length <= 2 ? 2 : 3;
      const id = 'md-' + (hid++);
      html += `<h${tag} id="${id}" data-t="${id}">${esc(m[2])}</h${tag}>`;
      i++; continue;
    }
    if (/^[-*]\s+/.test(s)) {
      const [it, ni] = collectMdList(lines, i, /^[-*]\s+/, /^[-*]\s+/);
      html += '<ul>' + it.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>';
      i = ni; continue;
    }
    if (/^\d+[.、．]\s*/.test(s)) {
      const [it, ni] = collectMdList(lines, i, /^\d+[.、．]\s*/, /^\d+[.、．]\s*/);
      html += '<ol>' + it.map(x => `<li>${esc(x)}</li>`).join('') + '</ol>';
      i = ni; continue;
    }
    const cls = /^[（(]\s*[一二三四五六七八九十\d]+\s*[)）]/.test(s) ? 'md-clause' : 'md-p';
    html += `<p class="${cls}">${esc(s)}</p>`;
    i++;
  }
  return html;
}

/* ---------------- 搜索页 ---------------- */
async function renderSearch(main, params) {
  const q = params.get('q') || '';
  main.innerHTML = shell('search', `
    <section class="search-head">
      <div class="search-head-in">
        <div class="sh-title">${ICON.search}全文检索 · 精确到条款</div>
        <div class="search-box">
          <input id="sq" placeholder="输入关键词，如「年休假」「差旅标准」「保密义务」…" value="${esc(q)}" autocomplete="off">
          <button onclick="doSearch()">搜索</button>
        </div>
      </div>
    </section>
    <div class="wrap" style="padding-top:30px;padding-bottom:60px" id="sresult">
      ${q ? '<div style="text-align:center;padding:60px;color:var(--ink-4)">检索中…</div>' : `
        <div class="empty" style="padding:70px">${ICON.search}<b>输入关键词开始检索</b><span>支持在全部制度的正文与条款中定位</span></div>`}
    </div>`);
  $('#sq').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
  if (q) runSearch(q);
}

async function doSearch() {
  const v = $('#sq').value.trim();
  location.hash = '#/search' + (v ? '?q=' + encodeURIComponent(v) : '');
  if (v) runSearch(v);
}

async function runSearch(q) {
  const box = $('#sresult');
  const r = await api('/api/search?q=' + encodeURIComponent(q));
  const hits = r.data || [];
  if (!hits.length) {
    box.innerHTML = `<div class="empty" style="padding:70px">${ICON.search}<b>未找到与「${esc(q)}」相关的条款</b><span>试试更换关键词，或使用更简短的核心词</span></div>`;
    return;
  }
  const total = hits.reduce((a, h) => a + h.count, 0);
  box.innerHTML = `
    <div style="font-size:14px;color:var(--ink-3);margin-bottom:18px">
      共找到 <b style="color:var(--brand);font-size:16px">${total}</b> 处匹配，涉及
      <b style="color:var(--brand);font-size:16px">${hits.length}</b> 部制度
    </div>
    ${hits.map(h => `
      <div class="hit">
        <div class="hit-top">
          <span class="pcat ${catClass(h.category)}">${esc(h.category)}</span>
          <h3><a href="#/doc/${h.id}?q=${encodeURIComponent(q)}">${esc(h.title)}</a></h3>
          <span class="pver">${esc(h.version)}</span>
          <span class="hit-n">${h.count} 处匹配</span>
        </div>
        ${h.matches.map(m => `
          <div class="match">
            ${(m.chapter || m.article) ? `<div class="loc">${esc(m.article || '')}<span>${esc(m.chapter || '')}</span></div>` : ''}
            <div class="txt">${mark(m.text, q)}</div>
          </div>`).join('')}
      </div>`).join('')}`;
}

function mark(text, kw) {
  const safe = esc(text);
  if (!kw) return safe;
  const k = esc(kw).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return safe.replace(new RegExp(k, 'gi'), m => `<span class="hl">${m}</span>`);
}

/* ---------------- 说明页 ---------------- */
async function renderAbout(main) {
  main.innerHTML = shell('about', `
    <section class="doc-hero">
      <div class="doc-hero-in">
        <div class="crumb"><a href="#/">制度门户</a> / <span>使用说明</span></div>
        <h1>使用说明</h1>
        <p style="color:rgba(255,255,255,.78);margin-top:12px;font-size:14.5px">制度门户的使用方式、管理规范与反馈渠道</p>
      </div>
    </section>
    <div class="wrap" style="padding-top:34px;padding-bottom:70px;max-width:960px">
      <article class="content">
        <h2>一、门户定位</h2>
        <p>企业制度门户是公司各项管理制度的统一查阅入口。所有现行有效的制度文件集中发布于此，员工可随时随地通过电脑或手机查阅、检索与打印。</p>

        <h2>二、如何使用</h2>
        <h3>1. 浏览与查阅</h3>
        <p>在首页「制度全库」中按分类筛选，或点击「全部制度」查看完整清单。点击任意卡片即可进入制度全文页面，左侧目录支持章节与条款的快速跳转。</p>
        <h3>2. 全文检索</h3>
        <p>顶部「全文检索」支持关键词精确匹配，不仅返回所属制度，还直接定位到具体条款段落，命中关键词高亮显示。例如搜索「年休假」，可一次看到所有制度中涉及年休假的条款。</p>
        <h3>3. 打印与导出</h3>
        <p>制度全文页右上角提供「打印 / 导出 PDF」按钮，点击后调用浏览器打印功能，可选择打印纸质件或另存为 PDF 电子件。</p>

        <h2>三、管理制度</h2>
        <h3>1. 发布与更新</h3>
        <p>各部门制度由归口管理部门起草，经审批后由管理员在后台发布。制度修订后，管理员更新版本号与施行日期，历史版本可在后台查询。</p>
        <h3>2. 效力顺序</h3>
        <p>本门户所载制度如与国家和地方法律法规相抵触，以法律法规为准；如与公司正式印发的纸质文件不一致，以加盖公章的正式文件为准。</p>
        <h3>3. 保密要求</h3>
        <p>门户内容属公司内部资料，含敏感信息的制度仅限内部网络访问，请勿截图外传或向外部人员提供。</p>

        <h2>四、意见反馈</h2>
        <p>对门户功能、制度内容或展示方式有任何意见，可通过以下渠道反馈：</p>
        <ul>
          <li>制度内容问题：联系归口管理部门或人力资源部（党建工作部）</li>
          <li>门户功能问题：联系数智化管理部</li>
        </ul>
      </article>
    </div>`);
}

/* ---------------- 路由 ---------------- */
const routes = [
  [/^\/doc\/(\d+)$/, (m, main, p) => renderDoc(main, m[1], p)],
  [/^\/list$/, (m, main, p) => renderList(main, p)],
  [/^\/search$/, (m, main, p) => renderSearch(main, p)],
  [/^\/about$/, (m, main) => renderAbout(main)],
  [/^\/admin$/, (m, main) => renderAdmin(main)],
  [/^\/$/, (m, main, p) => renderHome(main, p)],
];

async function router() {
  const hash = location.hash.replace(/^#/, '') || '/';
  const [path, qs] = hash.split('?');
  const params = new URLSearchParams(qs || '');
  const main = $('#app');
  addEventListener('scroll', () => { }, { once: true });
  for (const [re, fn] of routes) {
    const m = path.match(re);
    if (m) {
      window.scrollTo(0, 0);
      try { await fn(m, main, params); }
      catch (e) { console.error(e); main.innerHTML = `<div class="empty" style="padding:140px">${ICON.file}<b>页面加载失败</b><span>${esc(e.message)}</span></div>`; }
      return;
    }
  }
  main.innerHTML = shell('', `<div class="empty" style="padding:140px">${ICON.search}<b>页面不存在</b><span>请返回首页</span></div>`);
}

addEventListener('hashchange', router);
addEventListener('DOMContentLoaded', router);
if (document.readyState !== 'loading') router();
