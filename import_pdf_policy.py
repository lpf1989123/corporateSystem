# -*- coding: utf-8 -*-
"""
从「制度源文件」PDF 导入规章制度。

规则（与前台目录 / mdRender 一致）：
1. 标题：文件名去掉序号（如「3. 」）
2. 分类：按关键词自动匹配已有分类
3. 目录层级：
   - 「第x章 …」→ Markdown ##（一级目录 / h2）
   - 「第x条 …」→ Markdown ###（二级目录 / h3）
4. 有序列表：连续的「1．2．3．」项之间不插空行，渲染时合并为一个 <ol>
5. 去掉水印：斜向文字、灰色域名水印、页眉页脚重复公司名等不进入正文
6. 表格：
   - 按表头跨度还原合并单元格，纠正 th（去掉空列/水印）
   - 跨页断开的同一表格自动纵向合并
   - 表格区域内文字不重复进入正文段落
7. 保留段落顺序；有图片则写入 Markdown
"""
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime

try:
    import pymupdf
except ImportError:
    raise SystemExit('请先安装：pip3 install pymupdf')

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'data', 'portal.db')
UPLOADS = os.path.join(BASE, 'uploads')
SRC_DIR = os.path.join(os.path.dirname(BASE), '制度源文件')

# 文件名/正文关键词 → 分类（按现有 categories 表）
CAT_RULES = [
    ('人事管理', ['请销假', '请假', '销假', '劳动合同', '岗位晋升', '外派', '员工手册', '招聘', '考勤']),
    ('薪酬绩效', ['薪酬', '绩效', '考核', '补贴', '激励', '职业资格']),
    ('生产安全', ['安全', '生产', '事故', '消防', '职业健康']),
    ('财务管理', ['财务', '报销', '差旅', '费用', '预算', '会计']),
    ('工会管理', ['工会', '福利', '女工', '团建']),
    ('职业行为', ['职业道德', '行为准则', '廉洁', '保密']),
    ('导读', ['欢迎词', '企业概况', '公司简介']),
]


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def title_from_filename(path):
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r'^\s*\d+\s*[\.．、]\s*', '', name).strip()
    name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
    return name


def guess_category(title, text, available):
    hay = (title + '\n' + (text or '')[:800])
    for cat, kws in CAT_RULES:
        if cat not in available:
            continue
        if any(k in hay for k in kws):
            return cat
    # 回退：优先人事管理，否则第一个非导读分类
    for prefer in ('人事管理', '综合管理'):
        if prefer in available:
            return prefer
    for c in available:
        if c != '导读':
            return c
    return available[0] if available else '人事管理'


def is_heading_chapter(s):
    return bool(re.match(r'^第[一二三四五六七八九十百零\d]+章', s))


def is_heading_article(s):
    return bool(re.match(r'^第[一二三四五六七八九十百零\d]+条', s))


def is_list_start(s):
    return bool(re.match(r'^[（(]\s*[一二三四五六七八九十百零\d]+\s*[)）]', s)
                or re.match(r'^\d+[.、．]\s*', s)
                or re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', s))


def article_rest(s):
    m = re.match(r'^第[一二三四五六七八九十百零\d]+条\s*(.*)$', s)
    return (m.group(1) or '').strip() if m else ''


# 短标题常见收尾（整行即条标题，下一行另起正文）
_SHORT_TITLE_TAIL = re.compile(
    r'(带薪年休假|年休假|婚假|产假|事假|病假|丧假|陪产假|育儿假|产检假|流产假|哺乳假'
    r'|请假程序|销假程序|规定|总则|附则|细则|办法|待遇|监督|纪律)$'
)


def is_short_article_title(s):
    """如「第五条 带薪年休假」「第十一条 请假程序」——整行即标题，无续句。"""
    if not is_heading_article(s):
        return False
    rest = article_rest(s)
    if not rest:
        return True
    # 已是完整句子 → 条号+正文同行
    if re.search(r'[。；]', rest):
        return False
    # 含逗号的长句不是短标题（避免「…落实公司休假」被「假」误匹配）
    if '，' in rest or ',' in rest:
        # 例外：以冒号收尾的引导句，如「第十七条 …处理：」
        if (rest.endswith('：') or rest.endswith(':')) and len(rest) <= 40:
            return True
        return False
    # 典型短标题（含「第七条 产检假、产假、…」）
    if len(rest) <= 36 and _SHORT_TITLE_TAIL.search(rest):
        return True
    return False


# 水印常见文案 / 域名碎片（斜向灰色 www.dtro.com.cn 等）
_WATERMARK_RE = re.compile(
    r'(?i)('
    r'dtro\.com\.cn|'
    r'https?://|'
    r'内部资料|严禁复制|复印件无效|不得外传|'
    r'CONFIDENTIAL|DRAFT|WATERMARK|'
    r'仅供查阅|扫描全能王|勤得利'
    r')'
)
_WATERMARK_DOMAIN_RE = re.compile(
    r'(?i)^[\w.-]*\.(com|cn|net|org)(\.[a-z]{2,})?$'
)
# 页眉重复公司名（各页顶部小字）
_PAGE_HEADER_NAMES = {
    '鲁信天地人环境科技（安徽）集团有限公司',
    '鲁信天地人环境科技集团有限公司',
}

# 表头关键词（用于判断 th / 跨页续表）
_TABLE_HEADER_RE = re.compile(
    r'职级|序列|范围|定位|作用|条件|姓名|名称|部门|备注|序号|项目|类别|内容|说明|时间|日期|岗位|职务'
)


def _color_rgb(color):
    """PyMuPDF span color → (r,g,b) 0–255。"""
    if color is None:
        return (0, 0, 0)
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        vals = color[:3]
        if all(isinstance(x, float) and x <= 1 for x in vals):
            return tuple(int(x * 255) for x in vals)
        return tuple(int(x) for x in vals)
    if isinstance(color, int):
        return ((color >> 16) & 255, (color >> 8) & 255, color & 255)
    return (0, 0, 0)


def is_watermark_span(span, line=None):
    """
    判断 PDF span 是否为水印：
    - 非水平方向（斜向水印）
    - 命中域名 / 机密类水印文案
    - 浅灰且短域名碎片
    """
    text = (span.get('text') or '').strip()
    if not text:
        return True
    direction = (line or {}).get('dir') or (1.0, 0.0)
    # 斜向 / 竖排水印
    if abs(float(direction[0])) < 0.95:
        return True
    if _WATERMARK_RE.search(text):
        return True
    if _WATERMARK_DOMAIN_RE.match(text):
        return True
    if re.fullmatch(r'(?i)w{1,3}\.[\w.-]+', text):
        return True
    # 浅灰短串（常见半透明水印碎片）
    r, g, b = _color_rgb(span.get('color'))
    if max(r, g, b) - min(r, g, b) < 30 and 40 <= r <= 200 and len(text) <= 40:
        if '.' in text or re.search(r'(?i)www|http|\.com|\.cn', text):
            return True
    return False


def is_watermark_text(s):
    """纯文本层水印判断（无坐标时用）。"""
    t = (s or '').strip()
    if not t:
        return True
    if _WATERMARK_RE.search(t):
        return True
    if _WATERMARK_DOMAIN_RE.match(t):
        return True
    if re.fullmatch(r'(?i)w{1,3}\.[\w.-]+', t):
        return True
    return False


def strip_watermarks_in_text(s):
    """从已拼好的段落中剔除残留水印碎片。"""
    if not s:
        return s
    # 去掉夹在正文中的域名水印
    s = re.sub(r'(?i)\bhttps?://\S+', '', s)
    s = re.sub(r'(?i)\b[\w.-]*dtro\.com\.cn\b', '', s)
    s = re.sub(r'(?i)\bwww\.[\w.-]+\b', '', s)
    s = re.sub(r'[ \t]{2,}', ' ', s).strip()
    return s


def extract_page_text_lines(page):
    """抽取页面正文行，自动去掉水印 span。"""
    lines_out = []
    d = page.get_text('dict')
    for b in d.get('blocks', []):
        if b.get('type') == 1:
            continue
        for line in b.get('lines', []):
            parts = []
            for span in line.get('spans', []):
                if is_watermark_span(span, line):
                    continue
                t = span.get('text') or ''
                if t:
                    parts.append(t)
            text = ''.join(parts).strip()
            if not text or is_watermark_text(text):
                continue
            lines_out.append(text)
    return lines_out


def should_skip_line(s):
    if not s:
        return True
    if is_watermark_text(s):
        return True
    if re.fullmatch(r'-?\s*\d+\s*-?', s):
        return True
    # 页眉重复公司名（各页顶部小字）
    if s in _PAGE_HEADER_NAMES:
        return True
    return False


def normalize_para(t):
    """规范空白：章/条后保留一个空格，其余中文间多余空格去掉。"""
    t = re.sub(r'[ \t]+', ' ', t).strip()
    # 占位保护「第X章/条」后的空格，避免被后续规则删掉
    t = re.sub(
        r'(第[一二三四五六七八九十百零\d]+[章节条])\s+',
        lambda m: m.group(1) + '\0',
        t,
        count=1,
    )
    t = re.sub(r'(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])', '', t)
    t = t.replace('\0', ' ')
    return t.strip()


def join_paragraphs(raw_lines):
    """把 PDF 断行拼成段落，保留章/条/列表起点。"""
    paras = []
    buf = ''

    def flush():
        nonlocal buf
        t = normalize_para(buf)
        if t:
            paras.append(t)
        buf = ''

    for s in raw_lines:
        s = s.strip()
        if should_skip_line(s):
            continue
        if is_heading_chapter(s) or is_heading_article(s) or is_list_start(s):
            flush()
            buf = s
            if is_heading_chapter(s) or is_short_article_title(s):
                flush()
            continue
        if not buf:
            buf = s
            continue
        buf = buf + s
    flush()
    return paras


def extract_tables_md(page):
    """兼容旧调用：单页表格 → markdown 行（不含跨页合并）。"""
    items = extract_page_tables(page, page_index=0)
    lines = []
    for it in items:
        lines.extend(table_to_md_lines(it['rows']))
    return lines


def clean_table_cell(c):
    """清洗单元格：换行转空格、去水印碎片。"""
    if c is None:
        return ''
    t = str(c).replace('\n', ' ').strip()
    t = strip_watermarks_in_text(t)
    kept = []
    for tok in t.split():
        if re.fullmatch(r'(?i)[owcnmdtr.]+', tok) and len(tok) <= 6:
            continue
        kept.append(tok)
    t = ' '.join(kept)
    t = re.sub(r'[ \t]+', ' ', t).strip()
    if re.fullmatch(r'[.\sowcnmdtrW]*', t, re.I):
        return ''
    return t


def looks_like_header_cells(cells):
    texts = [clean_table_cell(c) for c in (cells or [])]
    texts = [t for t in texts if t]
    if not texts:
        return False
    hit = sum(1 for t in texts if _TABLE_HEADER_RE.search(t))
    return hit >= max(1, (len(texts) + 2) // 3)


def _header_spans_from_names(names):
    """根据 pymupdf header.names 得到 [(标题, start, end), ...]。"""
    idxs = []
    for i, name in enumerate(names or []):
        t = clean_table_cell(name)
        if t and not re.match(r'^Col\d+$', t):
            idxs.append((i, t))
    if not idxs:
        return []
    n = len(names)
    spans = []
    for j, (i, t) in enumerate(idxs):
        end = idxs[j + 1][0] if j + 1 < len(idxs) else n
        spans.append([t, i, end])
    # 表头前的空列往往属于第一列表头（如「职级范围」前的职级值列）
    if spans and spans[0][1] > 0:
        spans[0][1] = 0
    return [tuple(x) for x in spans]


def _row_by_spans(row, spans):
    n = spans[-1][2]
    row = list(row) + [''] * max(0, n - len(row))
    out = []
    for _title, start, end in spans:
        cells = [clean_table_cell(c) for c in row[start:end]]
        vals, seen = [], set()
        for c in cells:
            if c and c not in seen:
                seen.add(c)
                vals.append(c)
        out.append(' '.join(vals))
    return out


def _densify_row(row):
    return [clean_table_cell(c) for c in row if clean_table_cell(c)]


def normalize_table_rows(tab):
    """
    将 pymupdf Table 规范为逻辑二维表：
    - 按表头跨度折叠合并单元格空列 → 纠正 th
    - 清洗水印；无可靠表头时 densify / 作续表
    """
    raw = tab.extract() or []
    if not raw:
        return []
    names = list(tab.header.names or [])
    ncols = max(len(r) for r in raw)
    while len(names) < ncols:
        names.append('')
    names = names[:ncols]

    cleaned = [[clean_table_cell(c) for c in r] for r in raw]
    cleaned = [r for r in cleaned if any(c.strip() for c in r)]
    if not cleaned:
        return []

    spans = _header_spans_from_names(names)
    use_span = bool(spans) and looks_like_header_cells([s[0] for s in spans])

    if use_span:
        body = cleaned
        if body and looks_like_header_cells(body[0]):
            body = body[1:]
        header_labels = [s[0] for s in spans]
        # 若各行「非空单元格数」与表头列数一致，优先 densify 对齐（避免合并单元格跨度把邻列粘进 th）
        dense_body = [_densify_row(r) for r in body]
        dense_body = [r for r in dense_body if r]
        if dense_body:
            lengths = [len(r) for r in dense_body]
            # 多数行列数 == 表头列数
            if sum(1 for n in lengths if n == len(header_labels)) >= max(1, len(lengths) * 2 // 3):
                rows = [header_labels]
                for r in dense_body:
                    rows.append(_fit_row_cols(r, len(header_labels)))
                return rows
        rows = [header_labels]
        for r in body:
            rows.append(_row_by_spans(r, spans))
        return [r for r in rows if any(c.strip() for c in r)]

    # 续表：names/首行都不像表头
    if not looks_like_header_cells(names) and not looks_like_header_cells(cleaned[0]):
        return [_densify_row(r) for r in cleaned if _densify_row(r)]

    header = _densify_row(cleaned[0])
    if not header:
        return [_densify_row(r) for r in cleaned if _densify_row(r)]
    rows = [header]
    n = len(header)
    for r in cleaned[1:]:
        cells = _densify_row(r)
        if len(cells) < n:
            cells = cells + [''] * (n - len(cells))
        elif len(cells) > n:
            cells = cells[: n - 1] + [' '.join(cells[n - 1:])]
        rows.append(cells)
    return rows


def table_to_md_lines(rows):
    """逻辑二维表 → Markdown 表格。"""
    if not rows:
        return []
    n = max(len(r) for r in rows)
    rows = [r + [''] * (n - len(r)) for r in rows]

    def esc(c):
        return (c or '').replace('|', '\\|')

    lines = []
    head = rows[0]
    lines.append('| ' + ' | '.join(esc(c) for c in head) + ' |')
    lines.append('| ' + ' | '.join(['---'] * n) + ' |')
    for r in rows[1:]:
        lines.append('| ' + ' | '.join(esc(c) for c in r) + ' |')
    lines.append('')
    return lines


def extract_page_tables(page, page_index):
    """抽取单页表格（已规范化），附带 bbox。"""
    out = []
    try:
        finder = page.find_tables()
    except Exception:
        return out
    if not finder:
        return out
    for tab in finder.tables:
        try:
            rows = normalize_table_rows(tab)
        except Exception:
            continue
        if not rows:
            continue
        bbox = tuple(tab.bbox)
        out.append({
            'page': page_index,
            'bbox': bbox,
            'y0': bbox[1],
            'y1': bbox[3],
            'rows': rows,
            'has_header': looks_like_header_cells(rows[0]),
        })
    out.sort(key=lambda t: t['y0'])
    return out


def _fit_row_cols(row, n):
    row = list(row)
    if len(row) < n:
        return row + [''] * (n - len(row))
    if len(row) > n:
        return row[: n - 1] + [' '.join(row[n - 1:])]
    return row


def is_table_continuation(prev, curr):
    """跨页/跨段续表判断。"""
    if not prev or not curr:
        return False
    if curr.get('has_header'):
        return False
    pc = len(prev['rows'][0]) if prev.get('rows') else 0
    cc = len(curr['rows'][0]) if curr.get('rows') else 0
    if pc == 0 or cc == 0:
        return False
    first = (curr['rows'][0][0] or '').strip()
    rank_cont = bool(re.match(r'^P\d+', first))
    if abs(pc - cc) > 2 and not rank_cont:
        return False
    if curr['page'] not in (prev['page'], prev['page'] + 1):
        return False
    if curr['page'] == prev['page']:
        return curr['y0'] >= prev['y1'] - 8
    return prev['y1'] > 520 and curr['y0'] < 220


def merge_cross_page_tables(tables):
    """纵向合并跨页续表。"""
    if not tables:
        return []
    merged = []
    for t in tables:
        if merged and is_table_continuation(merged[-1], t):
            prev = merged[-1]
            n = len(prev['rows'][0])
            body = t['rows']
            if body and looks_like_header_cells(body[0]):
                body = body[1:]
            for r in body:
                prev['rows'].append(_fit_row_cols(r, n))
            prev['y1'] = t['y1']
            prev['bbox'] = (
                min(prev['bbox'][0], t['bbox'][0]),
                prev['bbox'][1],
                max(prev['bbox'][2], t['bbox'][2]),
                t['bbox'][3],
            )
        else:
            merged.append({**t, 'rows': [list(r) for r in t['rows']]})
    return merged


def point_in_bbox(x, y, bbox, pad=2):
    x0, y0, x1, y1 = bbox
    return (x0 - pad) <= x <= (x1 + pad) and (y0 - pad) <= y <= (y1 + pad)


def extract_page_text_lines_outside_tables(page, table_bboxes):
    """抽取不在表格区域内的正文行。"""
    lines_out = []
    d = page.get_text('dict')
    for b in d.get('blocks', []):
        if b.get('type') == 1:
            continue
        for line in b.get('lines', []):
            bbox = line.get('bbox') or (0, 0, 0, 0)
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            if any(point_in_bbox(cx, cy, tb) for tb in table_bboxes):
                continue
            parts = []
            for span in line.get('spans', []):
                if is_watermark_span(span, line):
                    continue
                t = span.get('text') or ''
                if t:
                    parts.append(t)
            text = ''.join(parts).strip()
            if not text or is_watermark_text(text):
                continue
            lines_out.append({'text': text, 'y0': bbox[1]})
    return lines_out


def extract_images(doc, page, page_index):
    """导出有意义的图片（忽略装饰性小图）。"""
    os.makedirs(UPLOADS, exist_ok=True)
    out = []
    seen = set()
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            pix = pymupdf.Pixmap(doc, xref)
            if pix.width < 40 or pix.height < 40:
                continue
            if pix.n >= 5:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            safe = secrets.token_hex(8) + '.png'
            pix.save(os.path.join(UPLOADS, safe))
            out.append(f'![附图](/uploads/{safe})')
            out.append('')
            print(f'  [img] page{page_index + 1} {pix.width}x{pix.height} -> {safe}')
        except Exception as e:
            print('  [img skip]', xref, e)
    return out


def pdf_to_markdown(path):
    doc = pymupdf.open(path)
    meta = {
        'publisher': '人力资源部（党建工作部）',
        'version': 'V1.0',
        'effective_date': '',
        'doc_no': '',
    }
    cover_lines = extract_page_text_lines(doc[0]) if doc.page_count else []
    cover = '\n'.join(cover_lines)
    m = re.search(r'编制单位[：:]\s*(.+)', cover)
    if m:
        meta['publisher'] = strip_watermarks_in_text(m.group(1))
    m = re.search(r'编\s*号[：:]\s*(\S+)', cover)
    if m:
        meta['doc_no'] = strip_watermarks_in_text(m.group(1))
        meta['version'] = meta['doc_no']

    start = 1 if doc.page_count > 1 else 0

    all_tables_flat = []
    for i in range(start, doc.page_count):
        all_tables_flat.extend(extract_page_tables(doc[i], i))
    merged_tables = merge_cross_page_tables(all_tables_flat)
    print(f'  [table] 识别 {len(all_tables_flat)} 个页内表，合并后 {len(merged_tables)} 个')

    tables_by_start_page = {}
    for t in merged_tables:
        tables_by_start_page.setdefault(t['page'], []).append(t)

    raw_items = []
    wm_skipped = 0
    for i in range(start, doc.page_count):
        page = doc[i]
        local = extract_page_tables(page, i)
        bboxes = [t['bbox'] for t in local]
        before = len(page.get_text('text').splitlines())
        text_lines = extract_page_text_lines_outside_tables(page, bboxes)
        wm_skipped += max(0, before - len(text_lines))

        events = []
        for tl in text_lines:
            events.append({'kind': 'text', 'y0': tl['y0'], 'text': tl['text']})
        for t in tables_by_start_page.get(i, []):
            events.append({'kind': 'table', 'y0': t['y0'], 'rows': t['rows']})
        events.sort(key=lambda e: e['y0'])
        raw_items.extend(events)

        imgs = extract_images(doc, page, i)
        if imgs:
            raw_items.append({'kind': 'img', 'y0': 1e9, 'lines': imgs})

    if wm_skipped:
        print(f'  [watermark] 已过滤约 {wm_skipped} 行水印/页眉/表内重复文字')

    text_buf = []
    out = []
    title_like = title_from_filename(path)

    def flush_text():
        nonlocal text_buf
        if not text_buf:
            return
        paras = join_paragraphs(text_buf)
        text_buf = []
        for p in paras:
            p = strip_watermarks_in_text(p)
            if not p or is_watermark_text(p):
                continue
            if p == title_like or p.replace(' ', '') == title_like.replace(' ', ''):
                continue
            out.extend(para_to_md_lines(p))

    for ev in raw_items:
        if ev['kind'] == 'text':
            text_buf.append(ev['text'])
        elif ev['kind'] == 'table':
            flush_text()
            out.extend(table_to_md_lines(ev['rows']))
        elif ev['kind'] == 'img':
            flush_text()
            out.extend(ev['lines'])
    flush_text()

    blob = '\n'.join(out)
    m = re.search(r'自\s*(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)\s*起', blob)
    if m:
        meta['effective_date'] = re.sub(r'\s+', '', m.group(1))

    return finalize_markdown(out), meta



def para_to_md_lines(p):
    """
    单段 → Markdown 行。
    第x章 → ##（一级目录）；第x条 → ###（二级目录）。
    """
    lines = []
    if is_heading_chapter(p):
        # 去掉可能已带的 #，统一为一级标题
        body = re.sub(r'^#{1,6}\s*', '', p).strip()
        lines.append('## ' + body)
        lines.append('')
        return lines

    if is_heading_article(p):
        body = re.sub(r'^#{1,6}\s*', '', p).strip()
        m = re.match(r'^(第[一二三四五六七八九十百零\d]+条)\s*(.*)$', body)
        if not m:
            lines.append('### ' + body)
            lines.append('')
            return lines
        no, rest = m.group(1), (m.group(2) or '').strip()
        if not rest:
            lines.append(f'### {no}')
            lines.append('')
        elif is_short_article_title(body):
            lines.append(f'### {no} {rest}')
            lines.append('')
        else:
            # 条号作二级目录标题，正文紧随
            lines.append(f'### {no}')
            lines.append('')
            lines.append(rest)
            lines.append('')
        return lines

    lines.append(p)
    lines.append('')
    return lines


_OL_ITEM_RE = re.compile(r'^\d+[.、．]')


def merge_consecutive_ol(lines):
    """
    连续有序列表项（1．/2．/3． 或 1./1、）之间去掉空行，
    保证前台 mdRender / 后端 md_to_html 合并为一个 <ol>。
    """
    out = []
    i = 0
    n = len(lines)
    while i < n:
        out.append(lines[i])
        if _OL_ITEM_RE.match((lines[i] or '').strip()):
            j = i + 1
            while j < n and not (lines[j] or '').strip():
                j += 1
            if j < n and _OL_ITEM_RE.match((lines[j] or '').strip()):
                i = j
                continue
        i += 1
    return out


def finalize_markdown(lines):
    """压缩多余空行 + 合并连续 ol + 校正章/条标题层级 + 剔除残留水印行。"""
    # 校正：若章/条误写成错误 # 层级，统一为 ## / ###
    fixed = []
    for ln in lines:
        s = (ln or '').strip()
        if s and is_watermark_text(s):
            continue
        if s:
            s2 = strip_watermarks_in_text(s)
            if not s2 or is_watermark_text(s2):
                continue
            # 保留原标题前缀 #
            if s.startswith('#'):
                hashes = re.match(r'^(#{1,6})\s+', s)
                prefix = hashes.group(0) if hashes else ''
                body = re.sub(r'^#{1,6}\s+', '', s2)
                s = prefix + body if prefix else s2
            else:
                s = s2
        m = re.match(r'^(#{1,6})\s+(第[一二三四五六七八九十百零\d]+章.*)$', s)
        if m:
            fixed.append('## ' + m.group(2))
            continue
        m = re.match(r'^(#{1,6})\s+(第[一二三四五六七八九十百零\d]+条.*)$', s)
        if m:
            fixed.append('### ' + m.group(2))
            continue
        # 无 # 但以章/条开头（兜底）
        if is_heading_chapter(s) and not s.startswith('#'):
            fixed.append('## ' + s)
            continue
        if is_heading_article(s) and not s.startswith('#'):
            fixed.append('### ' + s)
            continue
        fixed.append(s if s or ln == '' else ln)

    # 一般空行压缩（最多连续 1 行）
    cleaned, blank = [], 0
    for ln in fixed:
        if (ln or '') == '':
            blank += 1
            if blank <= 1:
                cleaned.append('')
        else:
            blank = 0
            cleaned.append(ln)

    cleaned = merge_consecutive_ol(cleaned)
    return '\n'.join(cleaned).strip() + '\n'


def save_policy(title, category, content, meta):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ts = now()
    available = [r['name'] for r in conn.execute('SELECT name FROM categories ORDER BY sort')]
    if category not in available:
        category = guess_category(title, content, available)

    summary = ''
    for ln in content.split('\n'):
        s = ln.strip()
        if s and not s.startswith('#') and not s.startswith('![') and not s.startswith('|'):
            summary = s[:120] + ('…' if len(s) > 120 else '')
            break
    if not summary:
        summary = f'《{title}》全文。'

    version = meta.get('version') or 'V1.0'
    effective = meta.get('effective_date') or ''
    publisher = meta.get('publisher') or '人力资源部（党建工作部）'

    row = conn.execute('SELECT id FROM policies WHERE title=?', (title,)).fetchone()
    if row:
        conn.execute("""UPDATE policies SET category=?, version=?, effective_date=?, publisher=?,
            summary=?, content=?, sections=NULL, status='published', updated_at=? WHERE id=?""",
                     (category, version, effective, publisher, summary, content, ts, row['id']))
        pid, op = row['id'], 'update'
    else:
        cur = conn.execute("""INSERT INTO policies
            (title,category,version,effective_date,publisher,summary,content,sections,status,views,sort,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (title, category, version, effective, publisher, summary, content,
                            None, 'published', 0, 30, ts, ts))
        pid, op = cur.lastrowid, 'insert'
    conn.commit()
    conn.close()
    return op, pid, category


def import_one(pdf_path):
    if not os.path.isfile(pdf_path):
        raise SystemExit('找不到文件: ' + pdf_path)
    title = title_from_filename(pdf_path)
    print('标题:', title)
    content, meta = pdf_to_markdown(pdf_path)
    conn = sqlite3.connect(DB)
    available = [r[0] for r in conn.execute('SELECT name FROM categories ORDER BY sort')]
    conn.close()
    category = guess_category(title, content, available)
    print('分类:', category)
    print('版本:', meta.get('version'), '施行:', meta.get('effective_date'), '部门:', meta.get('publisher'))
    arts = len(re.findall(r'^### ', content, re.M))
    chaps = len(re.findall(r'^## ', content, re.M))
    imgs = len(re.findall(r'^!\[', content, re.M))
    tables = len(re.findall(r'^\| ---', content, re.M))
    print(f'结构: 章={chaps} 条={arts} 图={imgs} 表={tables} 字符={len(content)}')
    print('--- 预览 ---')
    for ln in content.split('\n')[:18]:
        print(ln[:100])
    op, pid, category = save_policy(title, category, content, meta)
    print(f'\n入库: {op} id={pid} 《{title}》 [{category}]')
    return pid


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC_DIR, '3. 员工请销假管理办法.pdf')
    if not os.path.isabs(target):
        # 支持相对 制度源文件 或绝对路径
        cand = os.path.join(SRC_DIR, target)
        target = cand if os.path.isfile(cand) else os.path.abspath(target)
    import_one(target)
