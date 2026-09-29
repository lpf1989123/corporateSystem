# -*- coding: utf-8 -*-
"""
从《员工手册-2026.9.101.docx》按章导入制度。
- 章节名（去掉「第×章」）作标题
- 「第×条」作 Markdown ### 目录标题
- 正文按原文顺序，不另置目录
- 图片提取到 uploads/ 并以 Markdown 嵌入
"""
import json
import os
import re
import secrets
import sqlite3
import zipfile
from datetime import datetime
from io import BytesIO
from xml.etree import ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(os.path.dirname(BASE), '员工手册-2026.9.101.docx')
DB = os.path.join(BASE, 'data', 'portal.db')
UPLOADS = os.path.join(BASE, 'uploads')

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

CN_DIGITS = '零一二三四五六七八九'


def to_cn(n):
    n = int(n)
    if n <= 0:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n == 10:
        return '十'
    if n < 20:
        return '十' + CN_DIGITS[n - 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return CN_DIGITS[tens] + '十' + (CN_DIGITS[ones] if ones else '')
    return str(n)


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def load_numbering(zf):
    """返回 numId -> {ilvl: (fmt, lvlText, start)} 与计数器。"""
    root = ET.fromstring(zf.read('word/numbering.xml'))
    abs_levels = {}
    for absn in root.findall(W + 'abstractNum'):
        aid = absn.get(W + 'abstractNumId')
        levels = {}
        for lvl in absn.findall(W + 'lvl'):
            ilvl = int(lvl.get(W + 'ilvl') or 0)
            start_el = lvl.find(W + 'start')
            fmt_el = lvl.find(W + 'numFmt')
            text_el = lvl.find(W + 'lvlText')
            levels[ilvl] = {
                'start': int(start_el.get(W + 'val')) if start_el is not None else 1,
                'fmt': fmt_el.get(W + 'val') if fmt_el is not None else 'decimal',
                'text': text_el.get(W + 'val') if text_el is not None else '%1.',
            }
        abs_levels[aid] = levels

    num_map = {}
    for num in root.findall(W + 'num'):
        nid = num.get(W + 'numId')
        abs_el = num.find(W + 'abstractNumId')
        if nid and abs_el is not None:
            num_map[nid] = abs_levels.get(abs_el.get(W + 'val'), {})
    return num_map


def format_num(fmt, n):
    if fmt == 'chineseCounting':
        return to_cn(n)
    if fmt == 'decimalEnclosedCircleChinese':
        # ①②… 简化为带圈数字的近似
        circled = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
        return circled[n - 1] if 1 <= n <= 20 else str(n)
    if fmt == 'lowerLetter':
        return chr(ord('a') + n - 1) if 1 <= n <= 26 else str(n)
    if fmt == 'lowerRoman':
        romans = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
        return romans[n - 1] if 1 <= n <= 10 else str(n)
    return str(n)


class NumberState:
    def __init__(self, num_map):
        self.num_map = num_map
        self.counters = {}  # (numId) -> list by ilvl

    def label(self, num_id, ilvl):
        levels = self.num_map.get(str(num_id)) or {}
        if not levels:
            return ''
        if num_id not in self.counters:
            self.counters[num_id] = {}
        ctr = self.counters[num_id]
        # reset deeper
        for k in list(ctr.keys()):
            if k > ilvl:
                del ctr[k]
        lvl = levels.get(ilvl)
        if not lvl:
            return ''
        ctr[ilvl] = ctr.get(ilvl, lvl['start'] - 1) + 1
        # fill template %1 %2 ...
        text = lvl['text'] or ''
        for i in range(0, ilvl + 1):
            lv = levels.get(i)
            if not lv:
                continue
            val = ctr.get(i, lv['start'])
            token = format_num(lv['fmt'], val)
            text = text.replace(f'%{i + 1}', token)
        return text


def p_text(p):
    parts = []
    for node in p.iter():
        if node.tag == W + 't' and node.text:
            parts.append(node.text)
        elif node.tag == W + 'tab':
            parts.append('\t')
        elif node.tag == W + 'br':
            parts.append('\n')
    return ''.join(parts).strip()


def p_numPr(p):
    pPr = p.find(W + 'pPr')
    if pPr is None:
        return None, None
    numPr = pPr.find(W + 'numPr')
    if numPr is None:
        return None, None
    ilvl_el = numPr.find(W + 'ilvl')
    nid_el = numPr.find(W + 'numId')
    ilvl = int(ilvl_el.get(W + 'val')) if ilvl_el is not None else 0
    nid = nid_el.get(W + 'val') if nid_el is not None else None
    return nid, ilvl


def p_images(p):
    ids = []
    for blip in p.iter(A + 'blip'):
        rid = blip.get(R + 'embed')
        if rid:
            ids.append(rid)
    return ids


def is_chapter_heading(nid, ilvl, label, text):
    if text in CHAPTER_TITLES:
        return True
    if label and re.match(r'^第[一二三四五六七八九十百零\d]+章', label):
        return True
    # numId 1 / abstract 第X章 at ilvl 0
    if nid == '1' and ilvl == 0:
        return True
    return False


def is_article_heading(nid, ilvl, label):
    if label and re.match(r'^第[一二三四五六七八九十百零\d]+条', label.strip()):
        return True
    # multilevel 第X条
    if nid == '7' and ilvl == 2:
        return True
    # standalone 第X条 abstracts mapped via various numIds — check label text pattern from numbering
    if ilvl == 0 and label and label.strip() in (
        # will be caught by regex above when label is「第X条」
    ):
        return True
    # abstract with lvlText 第%1条 at ilvl 0
    if label and re.fullmatch(r'第[一二三四五六七八九十百零\d]+条\s*', label.strip()):
        return True
    return False


CHAPTER_TITLES = [
    '员工请销假管理',
    '劳动合同管理',
    '薪酬管理',
    '绩效管理',
    '生产安全管理',
    '综合管理',
    '财务报销管理',
    '工会福利',
    '员工职业道德规范和行为准则',
]


def extract_rel_images(zf):
    rels = ET.fromstring(zf.read('word/_rels/document.xml.rels'))
    out = {}
    for rel in rels:
        rid = rel.get('Id')
        target = rel.get('Target')
        typ = rel.get('Type') or ''
        if rid and target and ('image' in typ.lower() or target.startswith('media/')):
            path = 'word/' + target.lstrip('/')
            if path in zf.namelist():
                out[rid] = path
    return out


def import_docx(path=DOCX):
    os.makedirs(UPLOADS, exist_ok=True)
    zf = zipfile.ZipFile(path)
    num_map = load_numbering(zf)
    state = NumberState(num_map)
    img_rels = extract_rel_images(zf)

    # 保存图片
    rid_to_url = {}
    for rid, mediapath in img_rels.items():
        data = zf.read(mediapath)
        ext = os.path.splitext(mediapath)[1].lower() or '.png'
        safe = secrets.token_hex(8) + ext
        with open(os.path.join(UPLOADS, safe), 'wb') as f:
            f.write(data)
        rid_to_url[rid] = '/uploads/' + safe
        print('[img]', rid, '->', rid_to_url[rid], len(data), 'bytes')

    root = ET.fromstring(zf.read('word/document.xml'))
    body = root.find(W + 'body')

    # 线性块列表
    blocks = []
    for child in body:
        tag = child.tag.split('}')[-1]
        if tag == 'tbl':
            rows = []
            for tr in child.findall(W + 'tr'):
                cells = []
                for tc in tr.findall(W + 'tc'):
                    cells.append(''.join(t.text or '' for t in tc.iter(W + 't')).strip())
                if any(cells):
                    rows.append(cells)
            if rows:
                blocks.append({'kind': 'table', 'rows': rows})
            continue
        if tag != 'p':
            continue
        text = p_text(child)
        imgs = p_images(child)
        nid, ilvl = p_numPr(child)
        label = ''
        if nid is not None:
            label = state.label(nid, ilvl or 0)
        if not text and not imgs:
            continue
        blocks.append({
            'kind': 'p',
            'text': text,
            'imgs': imgs,
            'nid': nid,
            'ilvl': ilvl,
            'label': label,
        })

    # 按章切分（章标题本身不写入正文，避免与页面标题重复）
    chapters = []
    cur = None
    article_i = 0
    for b in blocks:
        if b['kind'] == 'p' and is_chapter_heading(b['nid'], b['ilvl'] or 0, b['label'], b['text']):
            title = re.sub(r'^第[一二三四五六七八九十百零\d]+章\s*', '', b['text']).strip()
            if not title:
                title = b['text']
            cur = {'title': title, 'lines': []}
            chapters.append(cur)
            article_i = 0
            # 重置条计数：新章内条从 1 起 —— NumberState 对 numId7 会继续，需重置
            if '7' in state.counters:
                state.counters['7'] = {}
            continue
        if cur is None:
            # 章前内容跳过（目录等）；本文件从第一章标题开始
            continue

        if b['kind'] == 'table':
            rows = b['rows']
            if not rows:
                continue
            # markdown table
            head = rows[0]
            cur['lines'].append('| ' + ' | '.join(head) + ' |')
            cur['lines'].append('| ' + ' | '.join(['---'] * len(head)) + ' |')
            for r in rows[1:]:
                # pad
                while len(r) < len(head):
                    r.append('')
                cur['lines'].append('| ' + ' | '.join(r[:len(head)]) + ' |')
            cur['lines'].append('')
            continue

        # images
        for rid in b['imgs']:
            url = rid_to_url.get(rid)
            if url:
                cur['lines'].append(f'![示意图]({url})')
                cur['lines'].append('')

        text = b['text']
        label = (b['label'] or '').strip()
        if not text and not b['imgs']:
            continue

        # 条款标题 → ### 第X条 标题
        if is_article_heading(b['nid'], b['ilvl'] or 0, label):
            # label 可能是「第三条　」
            art_no = re.match(r'^(第[一二三四五六七八九十百零\d]+条)', label)
            if art_no:
                prefix = art_no.group(1)
            else:
                article_i += 1
                prefix = f'第{to_cn(article_i)}条'
            # 若 label 已含条号，用 Word 编号；同步 article_i
            m = re.search(r'第([一二三四五六七八九十百零\d]+)条', label)
            if m:
                # keep as-is from label
                pass
            heading = f'{prefix} {text}'.strip()
            cur['lines'].append(f'### {heading}')
            cur['lines'].append('')
            continue

        # 普通段落：保留编号前缀（文档编号 / （一）（二）等）
        if label and not text.startswith(label.strip()):
            # 避免重复：若正文已自带相同编号则不重复
            line = f'{label}{text}' if text else label
        else:
            line = text
        if line:
            cur['lines'].append(line)
            cur['lines'].append('')

    # 只保留目标章节
    wanted = set(CHAPTER_TITLES)
    chapters = [c for c in chapters if c['title'] in wanted]
    return chapters


def save_to_db(chapters):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ts = now()
    # 确保分类存在
    if not conn.execute("SELECT 1 FROM categories WHERE name=?", ('人力资源',)).fetchone():
        conn.execute("INSERT INTO categories(name,sort,created_at) VALUES(?,?,?)",
                     ('人力资源', 20, ts))

    results = []
    for i, ch in enumerate(chapters):
        title = ch['title']
        content = '\n'.join(ch['lines']).strip() + '\n'
        # 摘要：首条非空非标题行
        summary = ''
        for ln in ch['lines']:
            s = ln.strip()
            if s and not s.startswith('#') and not s.startswith('![') and not s.startswith('|'):
                summary = s[:100] + ('…' if len(s) > 100 else '')
                break
        if not summary:
            summary = f'《员工手册》「{title}」相关规定。'

        row = conn.execute("SELECT id FROM policies WHERE title=?", (title,)).fetchone()
        # 不使用 sections，避免详情页重组内容；目录由 ### 生成
        if row:
            conn.execute("""UPDATE policies SET category=?, version=?, effective_date=?, publisher=?,
                summary=?, content=?, sections=NULL, status='published', sort=?, updated_at=? WHERE id=?""",
                ('人力资源', '2026.9.10', '2026年10月1日', '人力资源部（党建工作部）',
                 summary, content, 20 + i, ts, row['id']))
            results.append(('update', row['id'], title, len(content)))
        else:
            cur = conn.execute("""INSERT INTO policies
                (title,category,version,effective_date,publisher,summary,content,sections,status,views,sort,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (title, '人力资源', '2026.9.10', '2026年10月1日', '人力资源部（党建工作部）',
                 summary, content, None, 'published', 0, 20 + i, ts, ts))
            results.append(('insert', cur.lastrowid, title, len(content)))
    conn.commit()
    conn.close()
    return results


if __name__ == '__main__':
    if not os.path.isfile(DOCX):
        raise SystemExit('找不到文件: ' + DOCX)
    chapters = import_docx(DOCX)
    print(f'解析到 {len(chapters)} 章')
    for c in chapters:
        arts = sum(1 for ln in c['lines'] if ln.startswith('### '))
        imgs = sum(1 for ln in c['lines'] if ln.startswith('!['))
        print(f'  · {c["title"]}  条款={arts}  图片={imgs}  字符≈{sum(len(x) for x in c["lines"])}')
        # preview
        preview = '\n'.join(c['lines'][:8])
        print('    ---')
        for line in c['lines'][:6]:
            print('   ', line[:90])
    results = save_to_db(chapters)
    print('\n入库:')
    for op, pid, title, n in results:
        print(f'  {op} id={pid} 《{title}》 {n} chars')
