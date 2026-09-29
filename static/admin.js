/* ==========================================================================
   管理后台  ——  制度维护 / 数据概览 / 系统设置
   ========================================================================== */

/* ---------------- 登录页 ---------------- */
function renderLogin(main) {
  main.innerHTML = `
  <div style="min-height:100vh;display:grid;grid-template-columns:1fr 1fr">
    <div class="login-side" style="position:relative;overflow:hidden;background:linear-gradient(150deg,#06304e,#0b4a72 55%,#0e5a8a);color:#fff;display:flex;flex-direction:column;justify-content:center;padding:70px 72px">
      <div style="position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);background-size:54px 54px;mask-image:radial-gradient(600px 400px at 40% 40%,#000,transparent 85%)"></div>
      <div style="position:absolute;width:560px;height:560px;border-radius:50%;right:-160px;bottom:-200px;border:1px solid rgba(255,255,255,.08);box-shadow:0 0 0 80px rgba(255,255,255,.025),0 0 0 170px rgba(255,255,255,.016)"></div>
      <div style="position:relative;z-index:2;max-width:420px">
        <div style="margin-bottom:44px">
          <img class="logo-img logo-img--login" src="/logo1.png" alt="鲁信环境">
        </div>
        <h2 style="font-size:33px;line-height:1.35;font-weight:700;letter-spacing:.8px;margin-bottom:16px">制度管理后台</h2>
        <p style="font-size:14.5px;line-height:1.95;color:rgba(255,255,255,.72)">
          集中维护公司各类管理制度，支持在线编辑、版本更新与数据统计，让制度管理规范化、可追溯。
        </p>
        <div style="margin-top:40px;display:flex;flex-direction:column;gap:14px">
          ${[['制度集中发布', '一次上传，全员可见'], ['分类灵活维护', '按业务归口清晰管理'], ['数据实时统计', '查阅量一目了然']]
      .map(([t, s]) => `<div style="display:flex;gap:12px;align-items:flex-start">
              <div style="width:22px;height:22px;border-radius:7px;background:rgba(200,168,107,.2);display:grid;place-items:center;flex-shrink:0;margin-top:2px">
                <span style="width:13px;height:13px;display:block">${ICON.check.replace('stroke-width="2.2"', 'stroke-width="3" stroke="#e0c893" style="width:13px;height:13px"')}</span>
              </div>
              <div><b style="font-size:14px;display:block">${t}</b><span style="font-size:12.5px;color:rgba(255,255,255,.55)">${s}</span></div>
            </div>`).join('')}
        </div>
      </div>
    </div>
    <div style="display:grid;place-items:center;padding:40px;background:#fff">
      <div style="width:100%;max-width:372px">
        <h3 style="font-size:23px;font-weight:700;color:var(--brand-deep);margin-bottom:7px">管理员登录</h3>
        <p style="font-size:13.5px;color:var(--ink-4);margin-bottom:32px">请使用管理账号登录后台</p>
        <div class="field">
          <label>账号</label>
          <input class="inp" id="l-user" placeholder="请输入管理员账号" value="admin" autocomplete="username">
        </div>
        <div class="field">
          <label>密码</label>
          <input class="inp" id="l-pass" type="password" placeholder="请输入密码" value="admin888" autocomplete="current-password">
        </div>
        <button class="btn-pri" id="l-btn" style="width:100%;padding:13px;margin-top:8px;font-size:15px">登 录</button>
      </div>
    </div>
  </div>`;

  const go = async () => {
    const username = $('#l-user').value.trim();
    const password = $('#l-pass').value;
    if (!username || !password) return toast('请输入账号和密码', 'warn');
    const btn = $('#l-btn');
    btn.disabled = true; btn.textContent = '登录中…';
    const r = await api('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    btn.disabled = false; btn.textContent = '登 录';
    if (r.code === 0) {
      sessionStorage.setItem('token', r.data.token);
      sessionStorage.setItem('user', JSON.stringify(r.data.user));
      toast('登录成功，欢迎回来');
      renderAdmin($('#app'));
    } else toast(r.msg || '登录失败', 'err');
  };
  $('#l-btn').onclick = go;
  $('#l-pass').addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
}

/* ---------------- 后台主框架 ---------------- */
let ADMIN_PAGE = 'dash';

async function renderAdmin(main) {
  const tk = sessionStorage.getItem('token');
  if (!tk) return renderLogin(main);
  const me = await api('/api/me');
  if (me.code !== 0) { sessionStorage.clear(); return renderLogin(main); }
  const user = me.data;

  main.innerHTML = `
  <div class="adm">
    <aside class="adm-side">
      <div class="adm-logo">
        <img class="logo-img logo-img--adm" src="/logo1.png" alt="鲁信环境">
      </div>
      <nav class="adm-nav">
        ${[['dash', '数据概览', ICON.file], ['policies', '规章制度', ICON.folder],
      ['users', '账号管理', ICON.shield], ['settings', '系统设置', ICON.tag]]
      .map(([k, t, ic]) => `<a class="adm-a ${ADMIN_PAGE === k ? 'on' : ''}" data-p="${k}">${ic}<span>${t}</span><i class="cnt" data-c="${k}"></i></a>`).join('')}
      </nav>
      <div class="adm-user">
        <div class="avatar" style="width:34px;height:34px;border-radius:9px;font-size:13px;background:linear-gradient(135deg,#2ea3d6,#0e5a8a)">${esc(initials(user.realname || user.username))}</div>
        <div style="flex:1;min-width:0"><b>${esc(user.realname || user.username)}</b><span>${esc(user.role)}</span></div>
        <button class="x-btn" onclick="adminLogout()" title="退出登录"><svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round"><path d="M15 17l5-5-5-5"/><path d="M20 12H9"/><path d="M12 20H5a2 2 0 01-2-2V6a2 2 0 012-2h7"/></svg></button>
      </div>
    </aside>
    <section class="adm-main">
      <header class="adm-head">
        <div><h2 id="adm-title">数据概览</h2><p id="adm-sub">门户运行情况一览</p></div>
        <div class="adm-head-r" id="adm-actions"></div>
      </header>
      <div class="adm-body" id="adm-body"><div style="padding:60px;text-align:center;color:var(--ink-4)">载入中…</div></div>
    </section>
  </div>`;

  $$('.adm-a').forEach(a => a.onclick = () => { ADMIN_PAGE = a.dataset.p; renderAdmin(main); });
  const pages = { dash: admDash, policies: admPolicies, users: admUsers, settings: admSettings };
  (pages[ADMIN_PAGE] || admDash)($('#adm-body'), $('#adm-title'), $('#adm-sub'), $('#adm-actions'));
}

function adminLogout() {
  api('/api/logout', { method: 'POST' }).then(() => {
    sessionStorage.clear(); toast('已退出登录'); location.hash = '#/'; location.reload();
  });
}

async function loadCounts() {}

/* ---------------- 概览 ---------------- */
async function admDash(box, title, sub, acts) {
  title.textContent = '数据概览';
  sub.textContent = '门户运行情况一览';
  acts.innerHTML = '';
  const [st, pols] = await Promise.all([
    api('/api/stats').then(r => r.data || {}),
    api('/api/policies?admin=1').then(r => r.data || []),
  ]);
  const maxV = Math.max(1, ...pols.map(p => p.views || 0));
  box.innerHTML = `
    <div class="kpis">
      ${[['现行制度', st.policies, '部', '#0e5a8a'], ['制度条款', st.articles ? Math.round(st.articles) : 0, '条', '#1a9c6b'],
      ['累计查阅', st.views || 0, '次', '#c8a86b'], ['所属分类', st.categories || 0, '个', '#7c62be']]
      .map(([t, v, u, c]) => `
        <div class="kpi">
          <div class="kpi-bar" style="background:${c}"></div>
          <span class="kpi-t">${t}</span>
          <b class="kpi-v">${v ?? 0}<i>${u}</i></b>
        </div>`).join('')}
    </div>
    <div class="panel">
      <div class="panel-h"><h4>制度查阅排行</h4><span class="panel-sub">按累计查阅次数</span></div>
      <div class="bars">
        ${pols.slice().sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 8).map(p => `
          <div class="bar-row">
            <span class="bar-l" title="${esc(p.title)}">${esc(p.title)}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${(p.views || 0) / maxV * 100}%"></div></div>
            <span class="bar-v">${p.views || 0}</span>
          </div>`).join('') || '<div class="empty" style="padding:26px">暂无数据</div>'}
      </div>
    </div>
    <div class="panel">
      <div class="panel-h"><h4>制度清单概览</h4><span class="panel-sub">共 ${pols.length} 部</span></div>
      <div class="tb-wrap"><table class="adm-table">
        <thead><tr><th>制度名称</th><th>分类</th><th>版本</th><th>状态</th><th style="text-align:right">查阅量</th><th>更新时间</th></tr></thead>
        <tbody>${pols.map(p => `<tr>
          <td><b>${esc(p.title)}</b></td>
          <td><span class="pcat ${catClass(p.category)}">${esc(p.category)}</span></td>
          <td class="mono">${esc(p.version)}</td>
          <td><span class="st ${p.status}">${{ published: '已发布', draft: '草稿', archived: '已归档' }[p.status] || p.status}</span></td>
          <td style="text-align:right" class="mono">${p.views || 0}</td>
          <td class="mono" style="color:var(--ink-4)">${esc((p.updated_at || '').slice(0, 10))}</td>
        </tr>`).join('')}</tbody>
      </table></div>
    </div>`;
}

/* ---------------- 制度管理 ---------------- */
let POL_CACHE = [];
async function admPolicies(box, title, sub, acts) {
  title.textContent = '规章制度';
  sub.textContent = '发布、编辑、上下架公司各项制度';
  const r = await api('/api/policies?admin=1');
  POL_CACHE = r.data || [];
  acts.innerHTML = `<input class="inp" id="p-find" placeholder="筛选制度名称…" style="width:220px" oninput="filterPol(this.value)">
    <button class="btn-ghost" onclick="catManage()">分类管理</button>
    <button class="btn-pri" onclick="polEdit(null)">＋ 新增制度</button>`;
  box.innerHTML = `
    <div class="panel" style="padding:0;overflow:hidden">
      <div class="tb-wrap"><table class="adm-table">
        <thead><tr>
          <th style="width:44px">ID</th><th>制度名称</th><th style="width:104px">分类</th><th style="width:90px">版本</th>
          <th style="width:104px">施行日期</th><th style="width:88px">状态</th><th style="width:70px;text-align:right">查阅</th>
          <th style="width:172px;text-align:right">操作</th>
        </tr></thead>
        <tbody id="pol-tbody">${polRows(POL_CACHE)}</tbody>
      </table></div>
    </div>`;
}

function polRows(list) {
  if (!list.length) return `<tr><td colspan="8"><div class="empty" style="padding:50px">${ICON.file}<b>暂无制度</b><span>点击右上角「新增制度」开始录入</span></div></td></tr>`;
  return list.map(p => `<tr id="pr-${p.id}">
    <td class="mono" style="color:var(--ink-4)">${p.id}</td>
    <td><b>${esc(p.title)}</b><div style="font-size:12px;color:var(--ink-4);margin-top:3px;max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc((p.summary || '').slice(0, 46))}</div></td>
    <td><span class="pcat ${catClass(p.category)}">${esc(p.category)}</span></td>
    <td class="mono">${esc(p.version)}</td>
    <td class="mono" style="color:var(--ink-3)">${esc((p.effective_date || '—').slice(0, 12))}</td>
    <td><span class="st ${p.status}">${{ published: '已发布', draft: '草稿', archived: '已归档' }[p.status] || p.status}</span></td>
    <td style="text-align:right" class="mono">${p.views || 0}</td>
    <td style="text-align:right;white-space:nowrap">
      <button class="tbtn" onclick="locateHash(${p.id})">查看</button>
      <button class="tbtn" onclick="polEdit(${p.id})">编辑</button>
      <button class="tbtn danger" onclick="polDel(${p.id},'${esc(p.title).replace(/'/g, "\\'")}')">删除</button>
    </td>
  </tr>`).join('');
}

function locateHash(id) { location.hash = '#/doc/' + id; }
function filterPol(kw) {
  const k = kw.trim().toLowerCase();
  const list = k ? POL_CACHE.filter(p => (p.title + p.category + p.version).toLowerCase().includes(k)) : POL_CACHE;
  $('#pol-tbody').innerHTML = polRows(list);
}

async function polDel(id, name) {
  if (!confirm(`确认删除制度《${name}》？\n操作不可撤销。`)) return;
  const r = await api('/api/policies/' + id, { method: 'DELETE' });
  if (r.code === 0) { toast('已删除'); renderAdmin($('#app')); } else toast(r.msg || '删除失败', 'err');
}

/* ---------------- 所属分类管理 ---------------- */
async function catManage() {
  const r = await api('/api/categories?admin=1');
  if (r.code !== 0) return toast(r.msg || '加载分类失败', 'err');
  const list = r.data || [];
  const mask = document.createElement('div');
  mask.className = 'mask';
  mask.id = 'cat-mask';
  const rows = list.length ? list.map(c => `
    <tr data-id="${c.id}">
      <td class="mono" style="color:var(--ink-4)">${c.id}</td>
      <td><input class="inp cat-name" value="${esc(c.category)}" style="padding:7px 10px"></td>
      <td><input class="inp cat-sort mono" type="number" value="${c.sort ?? 0}" style="width:88px;padding:7px 10px"></td>
      <td class="mono" style="text-align:right">${c.n || 0}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="tbtn" data-act="save">保存</button>
        <button class="tbtn danger" data-act="del">删除</button>
      </td>
    </tr>`).join('') : `<tr><td colspan="5"><div class="empty" style="padding:36px">${ICON.tag}<b>暂无分类</b><span>请在下方添加</span></div></td></tr>`;

  mask.innerHTML = `
  <div class="modal" style="max-width:720px">
    <div class="modal-head">
      <h3>${ICON.tag}所属分类管理</h3>
      <button class="x-btn" onclick="this.closest('.mask').remove()"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
    </div>
    <div class="modal-body">
      <div class="hint" style="margin-bottom:14px">分类供「新增 / 编辑制度」时选用；重命名会同步更新已挂载制度的分类名。有制度占用的分类不可删除。</div>
      <div class="tb-wrap"><table class="adm-table">
        <thead><tr>
          <th style="width:52px">ID</th><th>分类名称</th><th style="width:100px">排序</th>
          <th style="width:80px;text-align:right">制度数</th><th style="width:140px;text-align:right">操作</th>
        </tr></thead>
        <tbody id="cat-tbody">${rows}</tbody>
      </table></div>
      <div style="display:flex;gap:10px;margin-top:16px;align-items:flex-end;flex-wrap:wrap">
        <div class="field" style="flex:1;min-width:180px;margin:0">
          <label>新分类名称</label>
          <input class="inp" id="cat-new-name" placeholder="如：合规风控">
        </div>
        <div class="field" style="width:110px;margin:0">
          <label>排序</label>
          <input class="inp mono" id="cat-new-sort" type="number" value="100">
        </div>
        <button class="btn-pri" id="cat-add" style="height:40px">＋ 添加</button>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn-ghost" onclick="this.closest('.mask').remove()">关闭</button>
    </div>
  </div>`;
  document.body.appendChild(mask);
  mask.addEventListener('click', e => { if (e.target === mask) mask.remove(); });

  const refresh = () => { mask.remove(); catManage(); };

  $('#cat-tbody', mask).onclick = async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const tr = btn.closest('tr');
    const id = tr && tr.dataset.id;
    if (!id) return;
    if (btn.dataset.act === 'save') {
      const name = $('.cat-name', tr).value.trim();
      const sort = parseInt($('.cat-sort', tr).value, 10) || 0;
      if (!name) return toast('请填写分类名称', 'warn');
      const res = await api('/api/categories/' + id, { method: 'PUT', body: JSON.stringify({ name, sort }) });
      if (res.code === 0) { toast('已保存'); refresh(); }
      else toast(res.msg || '保存失败', 'err');
    }
    if (btn.dataset.act === 'del') {
      if (!confirm('确认删除该分类？')) return;
      const res = await api('/api/categories/' + id, { method: 'DELETE' });
      if (res.code === 0) { toast('已删除'); refresh(); }
      else toast(res.msg || '删除失败', 'err');
    }
  };

  $('#cat-add', mask).onclick = async () => {
    const name = $('#cat-new-name', mask).value.trim();
    const sort = parseInt($('#cat-new-sort', mask).value, 10) || 100;
    if (!name) return toast('请填写分类名称', 'warn');
    const res = await api('/api/categories', { method: 'POST', body: JSON.stringify({ name, sort }) });
    if (res.code === 0) { toast('分类已添加'); refresh(); }
    else toast(res.msg || '添加失败', 'err');
  };
}

/* 新增 / 编辑制度 */
async function polEdit(id) {
  let d = { title: '', category: '', version: 'V1.0', effective_date: '', publisher: '人力资源部', summary: '', content: '', status: 'published' };
  if (id) {
    const r = await api('/api/policies/' + id);
    if (r.code !== 0) return toast('读取失败', 'err');
    d = r.data;
  }
  const cr = await api('/api/categories?admin=1');
  const CATS = (cr.data || []).map(c => c.category);
  if (!CATS.length) {
    return toast('请先在「分类管理」中添加所属分类', 'warn');
  }
  if (!d.category || !CATS.includes(d.category)) {
    d.category = CATS[0];
  }
  const mask = document.createElement('div');
  mask.className = 'mask';
  mask.innerHTML = `
  <div class="modal" style="max-width:840px">
    <div class="modal-head">
      <h3>${ICON.file}${id ? '编辑制度' : '新增制度'}</h3>
      <button class="x-btn" onclick="this.closest('.mask').remove()"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
    </div>
    <div class="modal-body">
      <div class="field"><label>制度名称<i>*</i></label><input class="inp" id="f-title" value="${esc(d.title)}" placeholder="如：差旅费报销管理办法"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px">
        <div class="field"><label>所属分类</label>
          <select class="inp" id="f-cat">${CATS.map(c => `<option value="${esc(c)}" ${d.category === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>
        </div>
        <div class="field"><label>版本号</label><input class="inp" id="f-ver" value="${esc(d.version)}" placeholder="V1.0"></div>
        <div class="field"><label>施行日期</label><input class="inp" id="f-date" value="${esc(d.effective_date || '')}" placeholder="2026年10月1日"></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="field"><label>发布部门</label><input class="inp" id="f-pub" value="${esc(d.publisher || '')}" placeholder="人力资源部"></div>
        <div class="field"><label>发布状态</label>
          <select class="inp" id="f-status">
            <option value="published" ${d.status === 'published' ? 'selected' : ''}>已发布（前台可见）</option>
            <option value="draft" ${d.status === 'draft' ? 'selected' : ''}>草稿（前台隐藏）</option>
            <option value="archived" ${d.status === 'archived' ? 'selected' : ''}>已归档（前台隐藏）</option>
          </select>
        </div>
      </div>
      <div class="field"><label>内容摘要</label>
        <textarea class="inp" id="f-sum" rows="2" placeholder="一句话说明本制度的核心内容，将展示在门户卡片上">${esc(d.summary || '')}</textarea>
      </div>
      <div class="field">
        <label>制度正文</label>
        <div class="ed-tabs">
          <button class="ed-tab on" data-m="edit">编辑</button>
          <button class="ed-tab" data-m="preview">预览</button>
          <button class="ed-tab" data-m="upload">上传文件</button>
        </div>
        <textarea class="inp mono" id="f-content" style="min-height:300px;font-size:13.4px;line-height:1.9">${esc(d.content || '')}</textarea>
        <div class="hint">
          Markdown 语法：<code>## 第一章 总则</code> 一级标题 ｜ <code>### 第一条 目的</code> 条款标题 ｜
          <code>| 列1 | 列2 |</code> 表格 ｜ <code>- 项</code> 列表
        </div>
        <div id="f-preview" style="display:none;border:1px solid var(--line);border-radius:10px;padding:20px;max-height:420px;overflow:auto"></div>
        <div id="f-upload" style="display:none">
          <div class="up-zone" id="up-zone">
            ${ICON.filePdf}
            <b>点击选择 或 拖拽文件到此处</b>
            <span>支持 Word（.docx）/ PDF / TXT / Markdown；上传后自动提取正文到编辑区</span>
          </div>
          <div id="up-result"></div>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn-ghost" onclick="this.closest('.mask').remove()">取消</button>
      <button class="btn-pri" id="f-save">${id ? '保存修改' : '确认新增'}</button>
    </div>
  </div>`;
  document.body.appendChild(mask);
  mask.addEventListener('click', e => { if (e.target === mask) mask.remove(); });

  // 编辑器标签 + 上传提取
  const switchTab = (mode) => {
    $$('.ed-tab', mask).forEach(x => x.classList.toggle('on', x.dataset.m === mode));
    $('#f-content', mask).style.display = mode === 'edit' ? '' : 'none';
    $('#f-preview', mask).style.display = mode === 'preview' ? '' : 'none';
    $('#f-upload', mask).style.display = mode === 'upload' ? '' : 'none';
    if (mode === 'preview') $('#f-preview', mask).innerHTML = mdRender($('#f-content', mask).value);
  };
  $$('.ed-tab', mask).forEach(t => t.onclick = () => switchTab(t.dataset.m));

  const zone = $('#up-zone', mask);
  const doUp = async file => {
    zone.classList.add('busy');
    $('#up-result', mask).innerHTML = `<div class="up-ok" style="opacity:.75">${ICON.file}<span>正在上传并提取「${esc(file.name)}」…</span></div>`;
    try {
      const fd = new FormData(); fd.append('file', file);
      const tk = sessionStorage.getItem('token');
      const res = await fetch('/api/upload', { method: 'POST', headers: { 'X-Token': tk }, body: fd });
      const j = await res.json();
      if (j.code !== 0) {
        $('#up-result', mask).innerHTML = '';
        return toast(j.msg || '上传失败', 'err');
      }
      const d = j.data || {};
      let statusHtml = `<div class="up-ok">${ICON.check}<span>已存档：<b>${esc(d.name)}</b>（${(d.size / 1024).toFixed(1)} KB）</span>
        <a href="${d.url}" target="_blank" class="tbtn">下载</a></div>`;
      if (d.extract_ok && d.text) {
        const ta = $('#f-content', mask);
        const existing = (ta.value || '').trim();
        let apply = true;
        if (existing) {
          apply = confirm('编辑区已有内容。确定用提取结果覆盖吗？\n（取消则仅存档附件，不改动正文）');
        }
        if (apply) {
          ta.value = d.text;
          statusHtml += `<div class="up-ok" style="margin-top:8px">${ICON.check}<span>已提取 <b>${d.text.length}</b> 字到编辑区${d.extract_msg ? ' · ' + esc(d.extract_msg) : ''}</span></div>`;
          toast('已自动填入正文');
          switchTab('edit');
        } else {
          statusHtml += `<div class="up-ok" style="margin-top:8px;opacity:.8"><span>已提取 ${d.text.length} 字，但未覆盖编辑区</span>
            <button type="button" class="tbtn" id="up-apply-text">填入编辑区</button></div>`;
        }
      } else {
        statusHtml += `<div class="up-ok" style="margin-top:8px;opacity:.85"><span>${esc(d.extract_msg || '未能自动提取正文，请切换到「编辑」手动粘贴')}</span></div>`;
        toast(d.extract_msg || '上传成功，请手动粘贴正文', 'warn');
      }
      $('#up-result', mask).innerHTML = statusHtml;
      const applyBtn = $('#up-apply-text', mask);
      if (applyBtn && d.text) {
        applyBtn.onclick = () => {
          $('#f-content', mask).value = d.text;
          toast('已填入正文');
          switchTab('edit');
        };
      }
    } catch (e) {
      $('#up-result', mask).innerHTML = '';
      toast('上传失败：' + (e.message || e), 'err');
    } finally {
      zone.classList.remove('busy');
    }
  };
  zone.onclick = () => {
    if (zone.classList.contains('busy')) return;
    const i = document.createElement('input'); i.type = 'file';
    i.accept = '.pdf,.doc,.docx,.txt,.md,.markdown,.png,.jpg,.jpeg';
    i.onchange = () => i.files[0] && doUp(i.files[0]); i.click();
  };
  zone.ondragover = e => { e.preventDefault(); zone.classList.add('over'); };
  zone.ondragleave = () => zone.classList.remove('over');
  zone.ondrop = e => {
    e.preventDefault(); zone.classList.remove('over');
    if (zone.classList.contains('busy')) return;
    e.dataTransfer.files[0] && doUp(e.dataTransfer.files[0]);
  };

  $('#f-save', mask).onclick = async () => {
    const payload = {
      title: $('#f-title', mask).value.trim(),
      category: $('#f-cat', mask).value,
      version: $('#f-ver', mask).value.trim(),
      effective_date: $('#f-date', mask).value.trim(),
      publisher: $('#f-pub', mask).value.trim(),
      summary: $('#f-sum', mask).value.trim(),
      content: $('#f-content', mask).value,
      status: $('#f-status', mask).value,
    };
    if (!payload.title) return toast('请填写制度名称', 'warn');
    if (!payload.content.trim()) return toast('请填写制度正文', 'warn');
    const btn = $('#f-save', mask);
    btn.disabled = true; btn.textContent = '保存中…';
    const r = id ? await api('/api/policies/' + id, { method: 'PUT', body: JSON.stringify(payload) })
      : await api('/api/policies', { method: 'POST', body: JSON.stringify(payload) });
    btn.disabled = false; btn.textContent = id ? '保存修改' : '确认新增';
    if (r.code === 0) { toast(id ? '修改已保存' : '制度已新增'); mask.remove(); renderAdmin($('#app')); }
    else toast(r.msg || '保存失败', 'err');
  };
}

/* ---------------- 账号管理 ---------------- */
async function admUsers(box, title, sub, acts) {
  title.textContent = '账号管理';
  sub.textContent = '管理后台登录账号与权限';
  acts.innerHTML = `<button class="btn-pri" onclick="userAdd()">＋ 新增账号</button>`;
  const r = await api('/api/users');
  const list = r.data || [];
  box.innerHTML = `
    <div class="panel" style="padding:0;overflow:hidden">
      <div class="tb-wrap"><table class="adm-table">
        <thead><tr><th style="width:60px">ID</th><th>登录账号</th><th>姓名</th><th>角色</th><th>创建时间</th><th style="width:170px;text-align:right">操作</th></tr></thead>
        <tbody>${list.map(u => `<tr>
          <td class="mono" style="color:var(--ink-4)">${u.id}</td>
          <td><b class="mono">${esc(u.username)}</b></td>
          <td>${esc(u.realname || '—')}</td>
          <td><span class="st published">${esc(u.role)}</span></td>
          <td class="mono" style="color:var(--ink-4)">${esc((u.created_at || '').slice(0, 16))}</td>
          <td style="text-align:right;white-space:nowrap">
            <button class="tbtn" onclick="userPwd(${u.id},'${esc(u.username)}')">改密码</button>
            ${u.username !== 'admin' ? `<button class="tbtn danger" onclick="userDel(${u.id},'${esc(u.username)}')">删除</button>` : ''}
          </td>
        </tr>`).join('')}</tbody>
      </table></div>
    </div>
    <div class="adm-note" style="margin-top:18px">${ICON.shield}<span>账号管理仅供系统维护使用，请勿将后台账号借予他人。所有登录与操作行为均会记录在系统日志中。</span></div>`;
}

function userAdd() {
  const mask = document.createElement('div');
  mask.className = 'mask';
  mask.innerHTML = `
  <div class="modal" style="max-width:440px">
    <div class="modal-head"><h3>${ICON.shield}新增管理员账号</h3>
      <button class="x-btn" onclick="this.closest('.mask').remove()"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
    <div class="modal-body">
      <div class="field"><label>登录账号<i>*</i></label><input class="inp" id="u-name" placeholder="建议使用姓名拼音"></div>
      <div class="field"><label>姓名</label><input class="inp" id="u-real" placeholder="如：张三"></div>
      <div class="field"><label>初始密码<i>*</i></label><input class="inp" id="u-pass" type="text" placeholder="不少于6位"></div>
      <div class="field"><label>角色</label><select class="inp" id="u-role"><option value="admin">管理员</option><option value="editor">编辑（仅内容）</option></select></div>
    </div>
    <div class="modal-foot">
      <button class="btn-ghost" onclick="this.closest('.mask').remove()">取消</button>
      <button class="btn-pri" id="u-save">确认新增</button>
    </div>
  </div>`;
  document.body.appendChild(mask);
  mask.addEventListener('click', e => { if (e.target === mask) mask.remove(); });
  $('#u-save', mask).onclick = async () => {
    const username = $('#u-name', mask).value.trim();
    const password = $('#u-pass', mask).value;
    if (!username || password.length < 6) return toast('请填写账号，密码不少于6位', 'warn');
    const r = await api('/api/users', {
      method: 'POST', body: JSON.stringify({
        username, password, realname: $('#u-real', mask).value.trim(), role: $('#u-role', mask).value
      })
    });
    if (r.code === 0) { toast('账号已创建'); mask.remove(); renderAdmin($('#app')); } else toast(r.msg || '创建失败', 'err');
  };
}

function userPwd(id, name) {
  const p = prompt(`为账号「${name}」设置新密码（不少于6位）：`);
  if (p === null) return;
  if (p.length < 6) return toast('密码不少于6位', 'warn');
  api('/api/users/' + id, { method: 'PUT', body: JSON.stringify({ password: p }) })
    .then(r => toast(r.code === 0 ? '密码已更新' : (r.msg || '修改失败'), r.code === 0 ? 'ok' : 'err'));
}

async function userDel(id, name) {
  if (!confirm(`确认删除账号「${name}」？`)) return;
  const r = await api('/api/users/' + id, { method: 'DELETE' });
  if (r.code === 0) { toast('已删除'); renderAdmin($('#app')); } else toast(r.msg || '删除失败', 'err');
}

/* ---------------- 系统设置 ---------------- */
async function admSettings(box, title, sub, acts) {
  title.textContent = '系统设置';
  sub.textContent = '门户基础信息与运行参数';
  acts.innerHTML = '';
  const s = (await api('/api/settings')).data || {};
  box.innerHTML = `
    <div class="panel">
      <div class="panel-h"><h4>门户信息</h4></div>
      <div class="set-grid">
        <div class="field"><label>门户名称</label><input class="inp" id="s-name" value="${esc(s.site_name || '')}"></div>
        <div class="field"><label>公司全称</label><input class="inp" id="s-company" value="${esc(s.site_company || '')}"></div>
        <div class="field"><label>门户标语</label><input class="inp" id="s-slogan" value="${esc(s.site_slogan || '')}"></div>
      </div>
    </div>
    <div class="panel" style="margin-top:18px">
      <div class="panel-h"><h4>首页热门搜索</h4><span class="panel-sub">显示在前台 Banner 搜索框下方</span></div>
      <div class="field" style="max-width:640px">
        <label>热词列表</label>
        <textarea class="inp mono" id="s-hots" rows="5" placeholder="每行一个热词，或用逗号分隔">${esc(String(s.hot_keywords || '').split(/[,，]/).join('\n'))}</textarea>
        <div class="hint">每行填写一个关键词；保存后前台首页立即生效。留空则不显示热词区域。</div>
      </div>
    </div>
    <div class="panel" style="margin-top:18px">
      <div class="panel-h"><h4>保存</h4></div>
      <button class="btn-pri" id="s-save">保存设置</button>
    </div>
    <div class="panel" style="margin-top:18px">
      <div class="panel-h"><h4>系统日志</h4><span class="panel-sub">最近 200 条操作记录</span></div>
      <div id="log-box"><div class="empty" style="padding:34px">点击「加载日志」查看</div></div>
      <button class="btn-ghost" style="margin-top:14px" onclick="loadLogs()">加载日志</button>
    </div>
    <div class="panel" style="margin-top:18px">
      <div class="panel-h"><h4>账号安全</h4></div>
      <div class="set-grid">
        <div class="field"><label>新密码</label><input class="inp" id="s-pwd" type="password" placeholder="留空则不修改"></div>
        <div class="field"><label>确认新密码</label><input class="inp" id="s-pwd2" type="password" placeholder="再次输入"></div>
      </div>
      <button class="btn-ghost" id="s-pwd-save">修改当前账号密码</button>
    </div>`;

  $('#s-save').onclick = async () => {
    const hots = $('#s-hots').value
      .split(/[,，\n]/).map(s => s.trim()).filter(Boolean).join(',');
    const r = await api('/api/settings', {
      method: 'POST', body: JSON.stringify({
        site_name: $('#s-name').value, site_company: $('#s-company').value,
        site_slogan: $('#s-slogan').value, hot_keywords: hots,
      })
    });
    toast(r.code === 0 ? '设置已保存' : (r.msg || '保存失败'), r.code === 0 ? 'ok' : 'err');
  };
  $('#s-pwd-save').onclick = async () => {
    const a = $('#s-pwd').value, b = $('#s-pwd2').value;
    if (!a) return toast('请输入新密码', 'warn');
    if (a.length < 6) return toast('密码不少于6位', 'warn');
    if (a !== b) return toast('两次输入的密码不一致', 'warn');
    const me = JSON.parse(sessionStorage.getItem('user') || '{}');
    const r = await api('/api/users/' + me.id, { method: 'PUT', body: JSON.stringify({ password: a }) });
    if (r.code === 0) { toast('密码已修改，请重新登录'); setTimeout(() => adminLogout(), 1200); }
    else toast(r.msg || '修改失败', 'err');
  };
}

async function loadLogs() {
  const box = $('#log-box');
  box.innerHTML = '<div style="padding:26px;text-align:center;color:var(--ink-4)">加载中…</div>';
  const r = await api('/api/logs');
  const list = r.data || [];
  box.innerHTML = list.length ? `
    <div class="tb-wrap" style="max-height:340px;overflow:auto"><table class="adm-table">
      <thead><tr><th style="width:150px">时间</th><th style="width:110px">操作人</th><th style="width:130px">动作</th><th>对象</th><th style="width:120px">IP</th></tr></thead>
      <tbody>${list.map(l => `<tr>
        <td class="mono" style="color:var(--ink-4)">${esc(l.created_at)}</td>
        <td>${esc(l.username || '—')}</td>
        <td><span class="st published">${esc(l.action)}</span></td>
        <td style="color:var(--ink-3)">${esc(l.target || '—')}</td>
        <td class="mono" style="color:var(--ink-4)">${esc(l.ip || '—')}</td>
      </tr>`).join('')}</tbody>
    </table></div>` : '<div class="empty" style="padding:34px">暂无日志记录</div>';
}
