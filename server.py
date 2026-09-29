# -*- coding: utf-8 -*-
"""
鲁信环境 · 企业制度门户 —— 后端服务
纯标准库实现（SQLite + http.server），零第三方依赖，双击即可运行。

启动：  python server.py
访问：  http://127.0.0.1:8080
后台：  http://127.0.0.1:8080/admin   默认账号 admin / admin888
"""
import json
import os
import re
import socket
import sqlite3
import sys
import hashlib
import secrets
import mimetypes
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 兼容 PyInstaller 打包：exe 模式下，数据库/上传目录放在 exe 旁边（持久保存），
# 静态资源与种子数据打包在程序内部（只读）。
if getattr(sys, 'frozen', False):
    RUN_BASE = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE = getattr(sys, '_MEIPASS', RUN_BASE)
else:
    RUN_BASE = BUNDLE = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(RUN_BASE, 'data', 'portal.db')
UPLOADS = os.path.join(RUN_BASE, 'uploads')
STATIC = os.path.join(BUNDLE, 'static')
DATA = os.path.join(BUNDLE, 'data')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8080'))

SESSIONS = {}          # token -> {user, expire}
SESSION_TTL = timedelta(hours=12)


# --------------------------------------------------------------------------
# 数据库
# --------------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        salt TEXT NOT NULL,
        realname TEXT,
        role TEXT DEFAULT 'admin',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT '综合管理',
        version TEXT DEFAULT 'V1.0',
        effective_date TEXT,
        publisher TEXT DEFAULT '人力资源部',
        summary TEXT,
        content TEXT,           -- 正文 Markdown
        sections TEXT,          -- 结构化章节 JSON（可选）
        status TEXT DEFAULT 'published',   -- published / draft / archived
        views INTEGER DEFAULT 0,
        sort INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        target TEXT,
        ip TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)
    conn.commit()

    # 默认管理员
    if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        salt = secrets.token_hex(8)
        pwd = hashlib.sha256(('admin888' + salt).encode()).hexdigest()
        c.execute("INSERT INTO users(username,password,salt,realname,role,created_at) VALUES(?,?,?,?,?,?)",
                  ('admin', pwd, salt, '系统管理员', 'admin', now()))
        conn.commit()

    # 站点设置
    defaults = {
        'site_name': '鲁信环境 · 企业制度门户',
        'site_company': '鲁信天地人环境科技集团有限公司',
        'site_slogan': '制度上云 · 人人可查 · 共建共治',
        # 首页 Banner 热门搜索词，逗号或换行分隔
        'hot_keywords': '年休假,差旅报销,绩效工资,迟到早退,保密,安全',
    }
    for k, v in defaults.items():
        if not c.execute("SELECT 1 FROM settings WHERE key=?", (k,)).fetchone():
            c.execute("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()

    # 所属分类：预置 + 同步已有制度中的分类
    seed_cats = ['综合管理', '人力资源', '财务制度', '信息技术', '生产安全', '工程技术', '党群工会']
    for i, name in enumerate(seed_cats):
        if not c.execute("SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
            c.execute("INSERT INTO categories(name,sort,created_at) VALUES(?,?,?)",
                      (name, (i + 1) * 10, now()))
    for row in c.execute("SELECT DISTINCT category FROM policies WHERE category IS NOT NULL AND category!=''").fetchall():
        name = row['category'] if isinstance(row, sqlite3.Row) else row[0]
        if name and not c.execute("SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
            c.execute("INSERT INTO categories(name,sort,created_at) VALUES(?,?,?)",
                      (name, 999, now()))
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def log(username, action, target, ip=''):
    conn = db()
    conn.execute("INSERT INTO logs(username,action,target,ip,created_at) VALUES(?,?,?,?,?)",
                 (username, action, target, ip, now()))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# 预置数据：员工手册
# --------------------------------------------------------------------------
def seed_handbook():
    conn = db()
    if conn.execute("SELECT 1 FROM policies WHERE title='员工手册'").fetchone():
        conn.close()
        return
    path = os.path.join(DATA, 'handbook_doc.json')
    if not os.path.exists(path):
        conn.close()
        return
    doc = json.load(open(path, encoding='utf-8'))

    # 同时生成一份 Markdown 正文
    md = []
    for s in doc['sections']:
        if s['no']:
            md.append(f"## {s['no']} {s['title']}\n")
        else:
            md.append(f"## {s['title']}\n")
        for a in s['articles']:
            if a['no'] or a['title']:
                md.append(f"### {a['no']} {a['title']}\n")
            for p in a['paras']:
                md.append(p + '\n')
        md.append('')
    content = '\n'.join(md)

    conn.execute("""INSERT INTO policies
        (title,category,version,effective_date,publisher,summary,content,sections,status,views,sort,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (doc['title'], doc['category'], doc['version'], doc['effectiveDate'],
         '人力资源部（党建工作部）', doc['summary'], content,
         json.dumps(doc['sections'], ensure_ascii=False),
         'published', 0, 1, now(), now()))
    conn.commit()
    conn.close()
    print('[seed] 已导入预置制度：员工手册')


def seed_more():
    """再放两条示例，让门户首页更像真实场景。"""
    conn = db()
    samples = [
        dict(title='差旅费报销管理办法', category='财务制度', version='V2.1',
             effective_date='2026年7月1日', publisher='财务部',
             summary='规范员工因公出差审批、差旅标准、票据要求与报销流程，明确交通、住宿、伙食补助标准及超标处理规则。',
             content="""## 第一章 总则

### 第一条 目的
为规范公司差旅活动管理，控制差旅成本，保障员工因公出差需要，依据国家相关法规及公司财务制度，制定本办法。

### 第二条 适用范围
本办法适用于公司及各子公司全体因公出差人员。

## 第二章 出差审批

### 第三条 审批权限
（一）一般员工出差，由部门负责人审批；
（二）部门负责人出差，由分管领导审批；
（三）分管领导及以上人员出差，由总经理审批。

### 第四条 出差申请
出差前须在公司办公平台提交《出差申请单》，注明出差事由、地点、起止时间、随行人员及预算，审批通过后方可出行。

## 第三章 差旅标准

### 第五条 交通工具
（一）总经理及以上：可乘坐飞机经济舱、高铁一等座；
（二）部门负责人：可乘坐飞机经济舱、高铁二等座；
（三）一般员工：以高铁二等座、普通列车硬卧为主，确需乘坐飞机的须提前审批。

### 第六条 住宿标准
| 职级 | 一线城市 | 二线城市 | 其他地区 |
| --- | --- | --- | --- |
| 总经理及以上 | 600元/天 | 500元/天 | 400元/天 |
| 部门负责人 | 450元/天 | 380元/天 | 300元/天 |
| 一般员工 | 350元/天 | 300元/天 | 250元/天 |

### 第七条 伙食补助
出差期间伙食补助按 100 元/天包干使用，出差当日不足 12 小时按半天计发。

## 第四章 报销流程

### 第八条 报销时限
出差结束后 15 个工作日内提交报销单据，逾期未提交的，需书面说明原因并经部门负责人确认。

### 第九条 票据要求
（一）所有票据须为合法有效发票，抬头必须为"鲁信天地人环境科技集团有限公司"；
（二）住宿费须附住宿清单；
（三）交通费须与出差行程一致。

### 第十条 违规处理
虚报、冒领差旅费用的，除追回全部款项外，视情节给予通报批评及以上处分。
"""),
        dict(title='信息安全管理规定', category='信息技术', version='V1.3',
             effective_date='2026年8月1日', publisher='数智化管理部',
             summary='明确公司信息系统账号、数据、终端、网络及移动办公安全要求，规范数据分级与对外提供流程。',
             content="""## 第一章 总则

### 第一条 目的
为保障公司信息系统与数据资产安全，防范网络与信息安全风险，依据《网络安全法》《数据安全法》等法律法规，制定本规定。

### 第二条 适用范围
本规定适用于公司全体员工、劳务派遣人员及外包服务人员。

## 第二章 账号与权限

### 第三条 账号管理
（一）各业务系统账号实行实名制，一人一号，严禁共用；
（二）密码长度不少于 12 位，须包含大小写字母、数字及符号；
（三）密码每 90 天更换一次，且不得与前 3 次重复。

### 第四条 权限申请
系统权限按最小必要原则授予，员工岗位变动或离职时，所在部门须在 3 个工作日内提出权限变更或回收申请。

## 第三章 数据安全

### 第五条 数据分级
公司数据分为四级：
| 级别 | 名称 | 示例 | 管理要求 |
| --- | --- | --- | --- |
| L1 | 公开数据 | 宣传资料 | 可对外发布 |
| L2 | 内部数据 | 制度文件 | 公司内部流转 |
| L3 | 敏感数据 | 客户信息、报价 | 授权访问、加密存储 |
| L4 | 核心数据 | 核心技术、财务原始数据 | 双人授权、全程审计 |

### 第六条 数据外发
L3 及以上数据对外提供，须填写《数据外发审批单》，经部门负责人及数智化管理部审批；涉及客户信息的还须取得客户书面同意。

### 第七条 数据资产入表
公司数据资产按集团统一要求纳入数据资产台账管理，各部门须配合完成数据资源盘点、确权与质量评估。

## 第四章 终端与网络

### 第八条 终端安全
（一）办公电脑须安装公司统一的终端防护软件，不得私自卸载；
（二）禁止在办公电脑上安装来源不明的软件或使用未授权的外部存储介质。

### 第九条 移动办公
使用手机、平板等移动设备接入公司系统时，须通过企业微信或 VPN 通道，不得使用公共 Wi-Fi 处理敏感数据。

## 第五章 附则

### 第十条 违规处理
违反本规定造成信息安全事件的，视情节轻重给予警告、记过直至解除劳动合同；构成犯罪的，依法追究刑事责任。

### 第十一条 生效日期
本规定自 2026 年 8 月 1 日起施行，由数智化管理部负责解释。
"""),
    ]
    for i, s in enumerate(samples):
        if conn.execute("SELECT 1 FROM policies WHERE title=?", (s['title'],)).fetchone():
            continue
        conn.execute("""INSERT INTO policies
            (title,category,version,effective_date,publisher,summary,content,sections,status,views,sort,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s['title'], s['category'], s['version'], s['effective_date'], s['publisher'],
             s['summary'], s['content'], None, 'published', 0, i + 2, now(), now()))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def md_to_html(md):
    """轻量 Markdown → HTML。支持标题/段落/列表/表格/加粗。"""
    if not md:
        return ''
    lines = md.split('\n')
    html, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1
            continue
        # 表格
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:\-|]+\|$', lines[i+1].strip()):
            head = [c.strip() for c in s.strip('|').split('|')]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            t = '<div class="tb-wrap"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
            for r in rows:
                t += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
            t += '</tbody></table></div>'
            html.append(t)
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            lv = len(m.group(1))
            # ## 章 → h2；### 条 → h3
            tag = 2 if lv <= 2 else 3
            html.append(f'<h{tag} class="md-h md-h{lv}">{inline(m.group(2))}</h{tag}>')
            i += 1
            continue
        m = re.match(r'^[-*]\s+(.*)$', s)
        if m:
            items = []
            while i < len(lines):
                t = lines[i].strip()
                if not t:
                    i += 1
                    continue
                if not re.match(r'^[-*]\s+', t):
                    break
                items.append(re.sub(r'^[-*]\s+', '', t))
                i += 1
            html.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>')
            continue
        m = re.match(r'^\d+[.、．]\s*(.*)$', s)
        if m:
            items = []
            while i < len(lines):
                t = lines[i].strip()
                if not t:
                    i += 1
                    continue
                if not re.match(r'^\d+[.、．]\s*', t):
                    break
                items.append(re.sub(r'^\d+[.、．]\s*', '', t))
                i += 1
            html.append('<ol>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>')
            continue
        # 条款号开头 → 高亮段落
        if re.match(r'^[（(]\s*[一二三四五六七八九十\d]+\s*[)）]', s):
            html.append(f'<p class="md-clause">{inline(s)}</p>')
        else:
            html.append(f'<p>{inline(s)}</p>')
        i += 1
    return '\n'.join(html)


def inline(t):
    t = (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    return t


def ok(data=None, **kw):
    body = {'code': 0, 'msg': 'ok'}
    if data is not None:
        body['data'] = data
    body.update(kw)
    return body


def err(msg, code=1):
    return {'code': code, 'msg': msg}


# --------------------------------------------------------------------------
# 上传文件 → 文本提取（纯标准库：txt/md/docx/pdf）
# --------------------------------------------------------------------------
def _decode_bytes(data):
    for enc in ('utf-8', 'utf-8-sig', 'gb18030', 'gbk', 'latin-1'):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode('utf-8', 'ignore')


def _polish_policy_md(text):
    """把常见制度标题行润成 Markdown，便于编辑区直接用。"""
    if not text:
        return ''
    out = []
    for raw in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        ln = raw.strip()
        if not ln:
            if out and out[-1] != '':
                out.append('')
            continue
        if re.match(r'^第[一二三四五六七八九十百零\d]+章\b', ln) or re.match(r'^第[一二三四五六七八九十百零\d]+章\s', ln):
            out.append('## ' + ln)
        elif re.match(r'^第[一二三四五六七八九十百零\d]+条\b', ln) or re.match(r'^第[一二三四五六七八九十百零\d]+条\s', ln):
            out.append('### ' + ln)
        else:
            out.append(ln)
    # 压缩多余空行
    cleaned, blank = [], 0
    for ln in out:
        if ln == '':
            blank += 1
            if blank <= 1:
                cleaned.append('')
        else:
            blank = 0
            cleaned.append(ln)
    return '\n'.join(cleaned).strip()


def _extract_txt(data):
    return _polish_policy_md(_decode_bytes(data))


def _extract_docx(data):
    import zipfile
    from io import BytesIO
    import xml.etree.ElementTree as ET

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    paras = []
    with zipfile.ZipFile(BytesIO(data)) as zf:
        if 'word/document.xml' not in zf.namelist():
            return '', '不是有效的 Word（.docx）文件'
        root = ET.fromstring(zf.read('word/document.xml'))
    for p in root.iter(W + 'p'):
        parts = []
        for node in p.iter():
            if node.tag == W + 't' and node.text:
                parts.append(node.text)
            elif node.tag == W + 'tab':
                parts.append('\t')
            elif node.tag == W + 'br':
                parts.append('\n')
        line = ''.join(parts).strip()
        if line:
            paras.append(line)
    if not paras:
        return '', '未能从 Word 中提取到文字（可能是纯图片文档）'
    return _polish_policy_md('\n\n'.join(paras)), ''


def _pdf_decode_literal(s):
    """解码 PDF 字面字符串，处理常见转义。"""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            mapping = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f',
                       '(': '(', ')': ')', '\\': '\\'}
            if n in mapping:
                out.append(mapping[n]); i += 2; continue
            if n in '01234567':
                j, val = i + 1, 0
                while j < len(s) and j < i + 4 and s[j] in '01234567':
                    val = val * 8 + int(s[j]); j += 1
                out.append(chr(val & 0xFF)); i = j; continue
            out.append(n); i += 2; continue
        out.append(c); i += 1
    raw = ''.join(out)
    # UTF-16BE（带 BOM）
    try:
        b = raw.encode('latin-1')
        if b.startswith(b'\xfe\xff'):
            return b[2:].decode('utf-16-be', 'ignore')
        if b.startswith(b'\xff\xfe'):
            return b[2:].decode('utf-16-le', 'ignore')
    except Exception:
        pass
    return raw


def _pdf_strings_from_content(content):
    """从 PDF 内容流中抽出 Tj / TJ / ' / \" 字符串。"""
    if isinstance(content, bytes):
        try:
            s = content.decode('latin-1')
        except Exception:
            s = content.decode('utf-8', 'ignore')
    else:
        s = content
    texts = []
    # (literal) Tj  或  (literal) '
    for m in re.finditer(r'\((?:\\.|[^\\)])*\)\s*(?:Tj|\'|")', s):
        lit = m.group(0)
        lit = lit[:lit.rfind(')')]
        lit = lit[1:] if lit.startswith('(') else lit
        t = _pdf_decode_literal(lit).strip()
        if t:
            texts.append(t)
    # [ (a) 120 (b) ] TJ
    for m in re.finditer(r'\[(.*?)\]\s*TJ', s, re.S):
        parts = re.findall(r'\((?:\\.|[^\\)])*\)', m.group(1))
        chunk = ''.join(_pdf_decode_literal(p[1:-1]) for p in parts).strip()
        if chunk:
            texts.append(chunk)
    # <HEX> Tj
    for m in re.finditer(r'<([0-9A-Fa-f\s]+)>\s*(?:Tj|\'|")', s):
        hx = re.sub(r'\s+', '', m.group(1))
        if len(hx) % 2:
            hx = '0' + hx
        try:
            b = bytes.fromhex(hx)
            if b.startswith(b'\xfe\xff'):
                t = b[2:].decode('utf-16-be', 'ignore')
            elif b.startswith(b'\xff\xfe'):
                t = b[2:].decode('utf-16-le', 'ignore')
            else:
                t = _decode_bytes(b)
            t = t.strip()
            if t:
                texts.append(t)
        except Exception:
            pass
    return texts


def _extract_pdf(data):
    import zlib
    chunks = []
    # 优先解压 FlateDecode stream
    for m in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream', data, re.S):
        raw = m.group(1)
        # 去掉可能的结尾多余换行
        for candidate in (raw, raw.rstrip(b'\r\n')):
            try:
                chunks.append(zlib.decompress(candidate))
                break
            except Exception:
                continue
        else:
            chunks.append(raw)
    texts = []
    for c in chunks:
        texts.extend(_pdf_strings_from_content(c))
    # 无压缩内容直接扫一遍全文
    if not texts:
        texts = _pdf_strings_from_content(data)
    # 合并：同一段内 Tj 常被拆成短串，用空串拼接再按换行切
    merged = []
    buf = ''
    for t in texts:
        if t.endswith('\n') or len(t) > 40:
            buf += t
            merged.append(buf.strip())
            buf = ''
        else:
            buf += t
    if buf.strip():
        merged.append(buf.strip())
    text = _polish_policy_md('\n'.join(merged))
    if not text or len(text) < 8:
        return '', '未能从 PDF 提取文字（可能是扫描件/图片型 PDF，请改用 Word 或手动粘贴）'
    return text, ''


def extract_file_text(filename, data):
    """
    根据扩展名提取纯文本。
    返回 (text, msg)：text 为空时 msg 说明原因。
    """
    ext = os.path.splitext(filename or '')[1].lower()
    if not data:
        return '', '文件为空'
    if len(data) > 25 * 1024 * 1024:
        return '', '文件过大（超过 25MB），请缩小后重试'
    try:
        if ext in ('.txt', '.md', '.markdown', '.csv'):
            return _extract_txt(data), ''
        if ext == '.docx':
            return _extract_docx(data)
        if ext == '.pdf':
            return _extract_pdf(data)
        if ext == '.doc':
            return '', '旧版 .doc 暂不支持自动提取，请用 Word 另存为 .docx 后再上传'
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'):
            return '', '图片无法自动提取文字，请手动粘贴到编辑区（原件已存档）'
        return '', f'暂不支持自动提取 {ext or "该类型"} 文件，原件已存档，请手动粘贴正文'
    except Exception as e:
        return '', f'提取失败：{e}'


# --------------------------------------------------------------------------
# 路由
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = 'LuxinPortal/1.0'

    def log_message(self, fmt, *args):
        pass

    # ---------- 基础 ----------
    def _send(self, obj, status=200, ctype='application/json; charset=utf-8'):
        raw = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
        except Exception:
            return {}

    def _query(self):
        p = urllib.parse.urlparse(self.path)
        return p.path, urllib.parse.parse_qs(p.query)

    def _current_user(self):
        tok = self.headers.get('X-Token') or ''
        if not tok:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            tok = (q.get('token') or [''])[0]
        s = SESSIONS.get(tok)
        if not s:
            return None
        if s['expire'] < datetime.now():
            SESSIONS.pop(tok, None)
            return None
        return s['user']

    def _require_admin(self):
        u = self._current_user()
        if not u:
            self._send(err('未登录或登录已过期', 401), 401)
            return None
        return u

    # ---------- 静态文件 ----------
    def _serve_static(self, rel):
        if rel in ('', '/'):
            rel = 'index.html'
        path = os.path.normpath(os.path.join(STATIC, rel))
        if not path.startswith(STATIC) or not os.path.isfile(path):
            self._send({'code': 404, 'msg': 'not found'}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
            ctype += '; charset=utf-8'
        with open(path, 'rb') as f:
            raw = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _serve_upload(self, rel):
        path = os.path.normpath(os.path.join(UPLOADS, rel))
        if not path.startswith(UPLOADS) or not os.path.isfile(path):
            self._send({'code': 404, 'msg': 'not found'}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        with open(path, 'rb') as f:
            raw = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    # ---------- GET ----------
    def do_GET(self):
        path, q = self._query()

        if path.startswith('/uploads/'):
            return self._serve_upload(path[len('/uploads/'):])

        if path.startswith('/api/'):
            return self._api_get(path, q)

        return self._serve_static(path.lstrip('/'))

    def _api_get(self, path, q):
        conn = db()
        if path == '/api/settings':
            rows = conn.execute("SELECT key,value FROM settings").fetchall()
            conn.close()
            return self._send(ok({r['key']: r['value'] for r in rows}))

        if path == '/api/stats':
            s = {
                'policies': conn.execute("SELECT COUNT(*) c FROM policies WHERE status='published'").fetchone()['c'],
                'articles': conn.execute("SELECT COALESCE(SUM(LENGTH(sections)-LENGTH(REPLACE(sections,'\"no\"','')))/5,0) c FROM policies WHERE sections IS NOT NULL").fetchone()['c'],
                'views': conn.execute("SELECT COALESCE(SUM(views),0) c FROM policies").fetchone()['c'],
                'categories': conn.execute("SELECT COUNT(*) c FROM categories").fetchone()['c'],
            }
            conn.close()
            return self._send(ok(s))

        if path == '/api/categories':
            admin = (q.get('admin') or [''])[0] == '1'
            if admin and not self._current_user():
                conn.close()
                return self._send(err('未登录或登录已过期', 401), 401)
            # 以分类表为准；附带制度数量（前台仅统计已发布）
            if admin:
                rows = conn.execute("""
                    SELECT c.id, c.name AS category, c.sort, c.created_at,
                           (SELECT COUNT(*) FROM policies p WHERE p.category=c.name) AS n
                    FROM categories c
                    ORDER BY c.sort ASC, c.id ASC
                """).fetchall()
            else:
                rows = conn.execute("""
                    SELECT c.id, c.name AS category, c.sort,
                           (SELECT COUNT(*) FROM policies p
                            WHERE p.category=c.name AND p.status='published') AS n
                    FROM categories c
                    ORDER BY c.sort ASC, c.id ASC
                """).fetchall()
            conn.close()
            return self._send(ok([dict(r) for r in rows]))

        if path == '/api/policies':
            kw = (q.get('q') or [''])[0].strip()
            cat = (q.get('category') or [''])[0].strip()
            admin = (q.get('admin') or [''])[0] == '1'
            sql = "SELECT id,title,category,version,effective_date,publisher,summary,status,views,created_at,updated_at FROM policies WHERE 1=1"
            args = []
            if not admin:
                sql += " AND status='published'"
            if cat:
                sql += " AND category=?"; args.append(cat)
            if kw:
                sql += " AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)"
                args += [f'%{kw}%'] * 3
            sql += " ORDER BY sort ASC, id DESC"
            rows = conn.execute(sql, args).fetchall()
            conn.close()
            return self._send(ok([dict(r) for r in rows]))

        m = re.match(r'^/api/policies/(\d+)$', path)
        if m:
            pid = int(m.group(1))
            # 浏览量 +1
            conn.execute("UPDATE policies SET views=views+1 WHERE id=?", (pid,))
            conn.commit()
            r = conn.execute("SELECT * FROM policies WHERE id=?", (pid,)).fetchone()
            if not r:
                conn.close()
                return self._send(err('制度不存在'), 404)
            d = dict(r)
            if d.get('sections'):
                try:
                    d['sections'] = json.loads(d['sections'])
                except Exception:
                    d['sections'] = None
            conn.close()
            return self._send(ok(d))

        if path == '/api/search':
            kw = (q.get('q') or [''])[0].strip()
            if not kw:
                conn.close()
                return self._send(ok([]))
            pat = f'%{kw}%'
            rows = conn.execute("""SELECT id,title,category,version,content,sections FROM policies
                                   WHERE status='published' AND (title LIKE ? OR content LIKE ?)""",
                                (pat, pat)).fetchall()
            hits = []
            for r in rows:
                # 结构化逐条检索
                found = []
                secs = None
                if r['sections']:
                    try:
                        secs = json.loads(r['sections'])
                    except Exception:
                        secs = None
                if secs:
                    for s in secs:
                        for a in s['articles']:
                            for p in a['paras']:
                                if kw in p:
                                    found.append({
                                        'chapter': f"{s.get('no','')} {s.get('title','')}".strip(),
                                        'article': f"{a['no']} {a['title']}".strip(),
                                        'text': p,
                                    })
                if not found:
                    for ln in (r['content'] or '').split('\n'):
                        if kw in ln:
                            found.append({'chapter': '', 'article': '', 'text': ln.strip()})
                if found:
                    hits.append({'id': r['id'], 'title': r['title'], 'category': r['category'],
                                 'version': r['version'], 'count': len(found), 'matches': found[:8]})
            hits.sort(key=lambda x: -x['count'])
            conn.close()
            return self._send(ok(hits))

        if path == '/api/logs':
            if not self._require_admin():
                conn.close(); return
            rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 200").fetchall()
            conn.close()
            return self._send(ok([dict(r) for r in rows]))

        if path == '/api/me':
            u = self._current_user()
            conn.close()
            if not u:
                return self._send(err('未登录', 401), 401)
            return self._send(ok(u))

        if path == '/api/users':
            if not self._require_admin():
                conn.close(); return
            rows = conn.execute("SELECT id,username,realname,role,created_at FROM users").fetchall()
            conn.close()
            return self._send(ok([dict(r) for r in rows]))

        conn.close()
        return self._send(err('接口不存在', 404), 404)

    # ---------- POST ----------
    def do_POST(self):
        path, q = self._query()
        # 文件上传（multipart）
        if path == '/api/upload':
            return self._upload()

        body = self._json_body()

        if path == '/api/login':
            u = (body.get('username') or '').strip()
            p = body.get('password') or ''
            conn = db()
            r = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
            conn.close()
            if not r:
                return self._send(err('账号或密码错误'), 401)
            if hashlib.sha256((p + r['salt']).encode()).hexdigest() != r['password']:
                return self._send(err('账号或密码错误'), 401)
            tok = secrets.token_urlsafe(24)
            SESSIONS[tok] = {'user': {'id': r['id'], 'username': r['username'],
                                      'realname': r['realname'], 'role': r['role']},
                             'expire': datetime.now() + SESSION_TTL}
            log(u, '登录', '后台', self.client_address[0])
            return self._send(ok({'token': tok, 'user': SESSIONS[tok]['user']}))

        if path == '/api/logout':
            tok = self.headers.get('X-Token', '')
            SESSIONS.pop(tok, None)
            return self._send(ok())

        # 以下需要管理员
        if path == '/api/categories':
            if not self._require_admin():
                return
            name = (body.get('name') or '').strip()
            if not name:
                return self._send(err('分类名称不能为空'))
            if len(name) > 40:
                return self._send(err('分类名称过长（限40字）'))
            sort = int(body.get('sort') or 100)
            conn = db()
            if conn.execute("SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
                conn.close()
                return self._send(err('分类已存在'))
            conn.execute("INSERT INTO categories(name,sort,created_at) VALUES(?,?,?)",
                         (name, sort, now()))
            conn.commit()
            nid = conn.execute("SELECT last_insert_rowid() i").fetchone()['i']
            conn.close()
            u = self._current_user()
            log(u['username'], '新增分类', name, self.client_address[0])
            return self._send(ok({'id': nid}))

        if path == '/api/policies':
            if not self._require_admin():
                return
            t = (body.get('title') or '').strip()
            if not t:
                return self._send(err('制度名称不能为空'))
            cat = (body.get('category') or '').strip() or '综合管理'
            conn = db()
            if not conn.execute("SELECT 1 FROM categories WHERE name=?", (cat,)).fetchone():
                conn.close()
                return self._send(err('所属分类不存在，请先在分类管理中添加'))
            conn.execute("""INSERT INTO policies
                (title,category,version,effective_date,publisher,summary,content,sections,status,views,sort,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (t, cat, body.get('version') or 'V1.0',
                 body.get('effective_date') or '', body.get('publisher') or '人力资源部',
                 body.get('summary') or '', body.get('content') or '',
                 json.dumps(body.get('sections'), ensure_ascii=False) if body.get('sections') else None,
                 body.get('status') or 'published',
                 body.get('sort') or 99, now(), now()))
            conn.commit()
            nid = conn.execute("SELECT last_insert_rowid() i").fetchone()['i']
            conn.close()
            u = self._current_user()
            log(u['username'], '新增制度', t, self.client_address[0])
            return self._send(ok({'id': nid}))

        if path == '/api/settings':
            if not self._require_admin():
                return
            conn = db()
            for k, v in body.items():
                conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=?",
                             (k, str(v), str(v)))
            conn.commit()
            conn.close()
            return self._send(ok())

        if path == '/api/users':
            if not self._require_admin():
                return
            u = (body.get('username') or '').strip()
            p = body.get('password') or ''
            if not u or not p:
                return self._send(err('账号和密码不能为空'))
            conn = db()
            if conn.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone():
                conn.close()
                return self._send(err('账号已存在'))
            salt = secrets.token_hex(8)
            conn.execute("INSERT INTO users(username,password,salt,realname,role,created_at) VALUES(?,?,?,?,?,?)",
                         (u, hashlib.sha256((p + salt).encode()).hexdigest(), salt,
                          body.get('realname') or u, body.get('role') or 'admin', now()))
            conn.commit()
            conn.close()
            return self._send(ok())

        return self._send(err('接口不存在', 404), 404)

    # ---------- PUT ----------
    def do_PUT(self):
        path, q = self._query()
        body = self._json_body()
        if not self._require_admin():
            return

        m = re.match(r'^/api/categories/(\d+)$', path)
        if m:
            cid = int(m.group(1))
            conn = db()
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
            if not cur:
                conn.close()
                return self._send(err('分类不存在'), 404)
            name = (body.get('name') if body.get('name') is not None else cur['name']).strip()
            if not name:
                conn.close()
                return self._send(err('分类名称不能为空'))
            if len(name) > 40:
                conn.close()
                return self._send(err('分类名称过长（限40字）'))
            sort = int(body['sort']) if body.get('sort') is not None else cur['sort']
            clash = conn.execute("SELECT id FROM categories WHERE name=? AND id!=?", (name, cid)).fetchone()
            if clash:
                conn.close()
                return self._send(err('分类名称已存在'))
            old = cur['name']
            conn.execute("UPDATE categories SET name=?, sort=? WHERE id=?", (name, sort, cid))
            if name != old:
                conn.execute("UPDATE policies SET category=? WHERE category=?", (name, old))
            conn.commit()
            conn.close()
            u = self._current_user()
            log(u['username'], '修改分类', f'{old} → {name}' if name != old else name, self.client_address[0])
            return self._send(ok())

        m = re.match(r'^/api/policies/(\d+)$', path)
        if m:
            pid = int(m.group(1))
            conn = db()
            cur = conn.execute("SELECT * FROM policies WHERE id=?", (pid,)).fetchone()
            if not cur:
                conn.close()
                return self._send(err('制度不存在'), 404)
            f = {k: body.get(k, cur[k]) for k in
                 ('title', 'category', 'version', 'effective_date', 'publisher', 'summary', 'content', 'status')}
            if not conn.execute("SELECT 1 FROM categories WHERE name=?", (f['category'],)).fetchone():
                conn.close()
                return self._send(err('所属分类不存在，请先在分类管理中添加'))
            secs = body.get('sections')
            conn.execute("""UPDATE policies SET title=?,category=?,version=?,effective_date=?,publisher=?,
                            summary=?,content=?,status=?,sections=?,updated_at=? WHERE id=?""",
                         (f['title'], f['category'], f['version'], f['effective_date'], f['publisher'],
                          f['summary'], f['content'], f['status'],
                          json.dumps(secs, ensure_ascii=False) if secs else cur['sections'],
                          now(), pid))
            conn.commit()
            conn.close()
            u = self._current_user()
            log(u['username'], '修改制度', f['title'], self.client_address[0])
            return self._send(ok())

        m = re.match(r'^/api/users/(\d+)$', path)
        if m:
            uid = int(m.group(1))
            conn = db()
            if body.get('password'):
                salt = secrets.token_hex(8)
                conn.execute("UPDATE users SET password=?,salt=? WHERE id=?",
                             (hashlib.sha256((body['password'] + salt).encode()).hexdigest(), salt, uid))
            if body.get('realname') is not None:
                conn.execute("UPDATE users SET realname=? WHERE id=?", (body['realname'], uid))
            conn.commit()
            conn.close()
            return self._send(ok())

        return self._send(err('接口不存在', 404), 404)

    # ---------- DELETE ----------
    def do_DELETE(self):
        path, q = self._query()
        if not self._require_admin():
            return
        m = re.match(r'^/api/categories/(\d+)$', path)
        if m:
            cid = int(m.group(1))
            conn = db()
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
            if not cur:
                conn.close()
                return self._send(err('分类不存在'), 404)
            n = conn.execute("SELECT COUNT(*) c FROM policies WHERE category=?", (cur['name'],)).fetchone()['c']
            if n:
                conn.close()
                return self._send(err(f'该分类下还有 {n} 部制度，请先调整制度分类后再删除'))
            conn.execute("DELETE FROM categories WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            u = self._current_user()
            log(u['username'], '删除分类', cur['name'], self.client_address[0])
            return self._send(ok())

        m = re.match(r'^/api/policies/(\d+)$', path)
        if m:
            pid = int(m.group(1))
            conn = db()
            t = conn.execute("SELECT title FROM policies WHERE id=?", (pid,)).fetchone()
            conn.execute("DELETE FROM policies WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            u = self._current_user()
            log(u['username'], '删除制度', t['title'] if t else str(pid), self.client_address[0])
            return self._send(ok())
        return self._send(err('接口不存在', 404), 404)

    # ---------- 上传 ----------
    def _upload(self):
        if not self._require_admin():
            return
        ctype = self.headers.get('Content-Type', '')
        if 'boundary=' not in ctype:
            return self._send(err('无效的上传请求'))
        boundary = ctype.split('boundary=', 1)[1].strip().encode()
        n = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(n)
        parts = raw.split(b'--' + boundary)
        saved = None
        for p in parts:
            if b'filename="' not in p:
                continue
            head, _, data = p.partition(b'\r\n\r\n')
            fn = re.search(rb'filename="([^"]*)"', head)
            if not fn:
                continue
            name = fn.group(1).decode('utf-8', 'ignore')
            data = data.rstrip(b'\r\n-')
            ext = os.path.splitext(name)[1].lower()
            safe = secrets.token_hex(8) + ext
            with open(os.path.join(UPLOADS, safe), 'wb') as f:
                f.write(data)
            text, extract_msg = extract_file_text(name, data)
            saved = {
                'url': '/uploads/' + safe,
                'name': name,
                'size': len(data),
                'text': text or '',
                'extract_ok': bool(text),
                'extract_msg': extract_msg or ('已提取 %d 字' % len(text) if text else ''),
            }
        if not saved:
            return self._send(err('未找到文件'))
        u = self._current_user()
        log(u['username'], '上传文件', saved['name'], self.client_address[0])
        return self._send(ok(saved))


def lan_ips():
    """枚举本机局域网 IP（不发任何网络包）。"""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            if not info[4][0].startswith('127.'):
                ips.add(info[4][0])
    except Exception:
        pass
    return sorted(ips)


def main():
    init_db()
    # seed_handbook()
    # seed_more()

    # 端口被占用时自动向后顺延，保证"双击就能用"
    srv = None
    port = PORT
    for _ in range(21):
        try:
            srv = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            port += 1
    if srv is None:
        print(f'启动失败：{PORT}-{port} 端口均被占用，请关闭占用程序后重试')
        if getattr(sys, 'frozen', False):
            import time
            time.sleep(4)
        return

    shown_host = '127.0.0.1' if HOST in ('0.0.0.0', '', '*') else HOST
    url = f'http://{shown_host}:{port}'
    print('=' * 60)
    print('  鲁信环境 · 企业制度门户  已启动')
    print(f'  本机访问   : {url}')
    if HOST == '0.0.0.0':
        for ip in lan_ips():
            print(f'  局域网访问 : http://{ip}:{port}   （发给同事，浏览器直接打开）')
    print(f'  管理后台   : {url}/admin')
    print(f'  默认账号   : admin / admin888')
    print('  停止服务   : 关闭本窗口，或按 Ctrl+C')
    print('=' * 60)

    # 双击 exe 启动时自动打开浏览器
    if getattr(sys, 'frozen', False) or os.environ.get('AUTO_OPEN') == '1':
        import threading
        import webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
