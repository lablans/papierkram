#!/usr/bin/env python3
"""Toolkit for tracked, XML-level cleanup of .docx files (see SKILL.md).

Commands: `python3 -I wordtool.py --help` (each command is a function below; its signature is the command line).
Library (import from a per-document transform; run that with `python3 -I` and add this directory to sys.path
explicitly): Redline, chars, whitespace_dels, field_runs, span, text, style_ids, pstyle, load, save.
"""
import argparse, copy, datetime, difflib, inspect, itertools, os, re, sys, zipfile
from collections import Counter
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
XML = 'http://www.w3.org/XML/1998/namespace'
q = lambda t: '{%s}%s' % (W, t)
PARTS = ('document.xml', 'footnotes.xml', 'endnotes.xml', 'header1.xml', 'header2.xml', 'header3.xml',
         'footer1.xml', 'footer2.xml', 'footer3.xml')

PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl', 'numPr',
  'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens', 'kinsoku', 'wordWrap', 'overflowPunct',
  'topLinePunct', 'autoSpaceDE', 'autoSpaceDN', 'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind',
  'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc', 'textDirection', 'textAlignment',
  'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr', 'sectPr', 'pPrChange']
RPR_ORDER = ['ins', 'del', 'moveFrom', 'moveTo', 'rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps',
  'strike', 'dstrike', 'outline', 'shadow', 'emboss', 'imprint', 'noProof', 'snapToGrid', 'vanish', 'webHidden',
  'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs', 'highlight', 'u', 'effect', 'bdr', 'shd', 'fitText',
  'vertAlign', 'rtl', 'cs', 'em', 'lang', 'eastAsianLayout', 'specVanish', 'oMath', '~ext', 'rPrChange']
PPR_META = {'rPr', 'sectPr', 'pPrChange'}
RPR_META = {'ins', 'del', 'moveFrom', 'moveTo', 'rPrChange'}


def ln(e):
  if not isinstance(e.tag, str):
    return '~other'
  qn = etree.QName(e)
  return qn.localname if qn.namespace == W else '~ext'


def under(e, name):
  return any(ln(a) == name for a in e.iterancestors())


def own(e, p):
  """True if e belongs to paragraph p itself (not to a nested text-box paragraph)."""
  return next(e.iterancestors(q('p')), None) is p


def insert_ordered(parent, child, order):
  k = order.index(ln(child))
  for i, c in enumerate(parent):
    if isinstance(c.tag, str) and order.index(ln(c) if ln(c) in order else '~ext') > k:
      parent.insert(i, child)
      return child
  parent.append(child)
  return child


def canon(els):
  # copy both sides: a detached copy serializes its namespace declarations, a node in the tree does not
  return [etree.tostring(copy.deepcopy(e), method='c14n') for e in els]


def load(path):
  return etree.parse(path)


def save(tree, path):
  tree.write(path, xml_declaration=True, encoding='UTF-8', standalone=True)


def style_ids(styles_tree):
  """{lower-cased w:name: styleId}. Built-in names are English ("heading 1", "list paragraph"), while IDs
  are localized and change between saves (Heading1 vs berschrift1) - never hard-code an ID."""
  return {s.find(q('name')).get(q('val')).lower(): s.get(q('styleId'))
          for s in styles_tree.getroot().iter(q('style')) if s.find(q('name')) is not None}


def pstyle(p):
  s = p.find(q('pPr') + '/' + q('pStyle'))
  return None if s is None else s.get(q('val'))


def text(p, view='accept'):
  """Paragraph text; tab='⇥', soft break='↵'. view: 'accept' skips deletions, 'reject' skips insertions."""
  out = ''
  for e in p.iter(q('t'), q('delText'), q('tab'), q('br'), q('cr')):
    if not own(e, p) or ln(e.getparent()) != 'r':
      continue
    if view == 'accept' and (under(e, 'del') or ln(e) == 'delText'):
      continue
    if view == 'reject' and under(e, 'ins'):
      continue
    out += {'tab': '⇥', 'br': '↵', 'cr': '↵'}.get(ln(e), e.text or '')
  return out


def chars(p):
  """[(element, index, protected, char)] for the visible text of p. Field instructions and results are
  protected (Word regenerates them); tabs and soft breaks appear as '⇥'/'↵' and are protected too
  (remove a soft break with Redline.delete_runs on its run)."""
  out, stack = [], []
  for e in p.iter():
    if not isinstance(e.tag, str) or not own(e, p) or under(e, 'del'):
      continue
    n = ln(e)
    if n == 'fldChar':
      t = e.get(q('fldCharType'))
      if t == 'begin':
        stack.append('instr')
      elif t == 'separate' and stack:
        stack[-1] = 'result'
      elif t == 'end' and stack:
        stack.pop()
    elif ln(e.getparent()) != 'r':
      continue
    elif n == 't':
      prot = bool(stack) or under(e, 'fldSimple')
      out += [(e, i, prot, c) for i, c in enumerate(e.text or '')]
    elif n in ('tab', 'br', 'cr'):
      out.append((e, 0, True, '⇥' if n == 'tab' else '↵'))
  return out


def whitespace_dels(p, preset=(), keep_leading=False):
  """Indices (into chars(p)) to delete: leading/trailing spaces and all but one space of each run of spaces.
  keep_leading for footnotes (the space after the footnote mark is conventional)."""
  cs = chars(p)
  dels = set(preset)
  ok = lambda k: not cs[k][2]
  vis = [k for k in range(len(cs)) if k not in dels]
  for seq in ([] if keep_leading else vis, reversed(vis)):
    for k in seq:
      if cs[k][3] != ' ':
        break
      if ok(k):
        dels.add(k)
  group = []
  for k in [k for k in range(len(cs)) if k not in dels] + [None]:
    if k is not None and cs[k][3] == ' ':
      group.append(k)
      continue
    if len(group) > 1:
      keep = next((g for g in group if not ok(g)), group[0])
      dels.update(g for g in group if g != keep and ok(g))
    group = []
  return dels


def field_runs(instr_run):
  """(begin, separate, end) sibling runs of the field whose instrText run is given."""
  def find(start, step, kind):
    e = step(start)
    while e is not None:
      f = e.find(q('fldChar')) if ln(e) == 'r' else None
      if f is not None and f.get(q('fldCharType')) == kind:
        return e
      e = step(e)
    raise ValueError('field ' + kind + ' not found')
  b = find(instr_run, lambda e: e.getprevious(), 'begin')
  s = find(instr_run, lambda e: e.getnext(), 'separate')
  return b, s, find(s, lambda e: e.getnext(), 'end')


def span(start, end):
  """Sibling runs from start to end inclusive; spell-check markers in between are dropped."""
  out, e = [], start
  while True:
    nxt = e.getnext()
    if ln(e) == 'proofErr':
      e.getparent().remove(e)
    else:
      assert ln(e) == 'r', ln(e)
      out.append(e)
    if e is end:
      return out
    e = nxt


class Redline:
  """Writes Word tracked changes under one author with fresh revision ids."""

  def __init__(self, author, trees=()):
    self.author = author
    self.date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:00Z')
    used = [int(v) for t in trees for e in t.getroot().iter() if isinstance(e.tag, str)
            for v in [e.get(q('id'))] if v and v.lstrip('-').isdigit()]
    self.ids = itertools.count(max(used + [0]) + 1000)

  def stamp(self, e):
    e.set(q('id'), str(next(self.ids)))
    e.set(q('author'), self.author)
    e.set(q('date'), self.date)
    return e

  def ppr(self, p, mutate):
    """Change paragraph properties via mutate(pPr); records pPrChange only if something really changed."""
    ppr = p.find(q('pPr'))
    if ppr is None:
      ppr = etree.Element(q('pPr'))
      p.insert(0, ppr)
    base = lambda: [c for c in ppr if isinstance(c.tag, str) and ln(c) not in PPR_META]
    old = [copy.deepcopy(c) for c in base()]
    mutate(ppr)
    if canon(base()) != canon(old) and ppr.find(q('pPrChange')) is None:
      ch = self.stamp(etree.Element(q('pPrChange')))
      etree.SubElement(ch, q('pPr')).extend(old)
      insert_ordered(ppr, ch, PPR_ORDER)
    if len(ppr) == 0:
      p.remove(ppr)

  def rpr(self, holder, mutate, mark=False):
    """Change run properties of a w:r (or of the paragraph mark when holder is a w:pPr and mark=True)."""
    rpr = holder.find(q('rPr'))
    if rpr is None:
      rpr = etree.Element(q('rPr'))
      insert_ordered(holder, rpr, PPR_ORDER) if mark else holder.insert(0, rpr)
    base = lambda: [c for c in rpr if isinstance(c.tag, str) and ln(c) not in RPR_META]
    old = [copy.deepcopy(c) for c in base()]
    mutate(rpr)
    if canon(base()) != canon(old) and rpr.find(q('rPrChange')) is None:
      ch = self.stamp(etree.Element(q('rPrChange')))
      etree.SubElement(ch, q('rPr')).extend(old)
      insert_ordered(rpr, ch, RPR_ORDER)
    if len(rpr) == 0:
      holder.remove(rpr)

  def run(self, text_, rpr=None, tag='t'):
    r = etree.Element(q('r'))
    if rpr is not None:
      r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, q(tag))
    t.text = text_
    t.set('{%s}space' % XML, 'preserve')
    return r

  def insert_text(self, anchor, text_, rpr=None, before=False):
    """Tracked insertion of text_ next to anchor (a run or revision element)."""
    w = self.stamp(etree.Element(q('ins')))
    w.append(self.run(text_, rpr))
    anchor.addprevious(w) if before else anchor.addnext(w)
    return w

  def delete_runs(self, runs):
    """Wrap consecutive sibling runs (incl. whole fields) in one tracked deletion."""
    wrap = self.stamp(etree.Element(q('del')))
    runs[0].addprevious(wrap)
    for r in runs:
      for t in r.findall(q('t')):
        t.tag = q('delText')
        t.set('{%s}space' % XML, 'preserve')
      for t in r.findall(q('instrText')):
        t.tag = q('delInstrText')
      wrap.append(r)
    return wrap

  @staticmethod
  def atomize(run):
    """Split a run so each content child sits in its own run (same properties); returns the new runs."""
    rpr = run.find(q('rPr'))
    content = [c for c in run if c is not rpr]
    if len(content) <= 1:
      return [run]
    out = []
    for c in content:
      r = etree.Element(q('r'), attrib=dict(run.attrib))
      if rpr is not None:
        r.append(copy.deepcopy(rpr))
      r.append(c)
      run.addprevious(r)
      out.append(r)
    run.getparent().remove(run)
    return out

  def delete_chars(self, p, dels):
    """Tracked deletion of the characters at indices dels (into chars(p)); protected ones are refused."""
    cs = chars(p)
    per_t = {}
    for k in sorted(dels):
      e, i, prot, _ = cs[k]
      assert not prot and ln(e) == 't', ('protected character', k)
      per_t.setdefault(e, set()).add(i)
    for t, idx in per_t.items():
      run = next(r for r in self.atomize(t.getparent()) if t in r)
      rpr = run.find(q('rPr'))
      segs = []
      for i, c in enumerate(t.text):
        kind = i in idx
        if segs and segs[-1][0] == kind:
          segs[-1][1] += c
        else:
          segs.append([kind, c])
      for kind, s in segs:
        r = self.run(s, rpr, 'delText' if kind else 't')
        r.attrib.update(run.attrib)
        if kind:
          w = self.stamp(etree.Element(q('del')))
          w.append(r)
          r = w
        run.addprevious(r)
      run.getparent().remove(run)

  def _mark(self, p, kind):
    ppr = p.find(q('pPr'))
    if ppr is None:
      ppr = etree.Element(q('pPr'))
      p.insert(0, ppr)
    rpr = ppr.find(q('rPr'))
    if rpr is None:
      rpr = insert_ordered(ppr, etree.Element(q('rPr')), PPR_ORDER)
    if rpr.find(q(kind)) is None:  # a second marker is a schema error
      insert_ordered(rpr, self.stamp(etree.Element(q(kind))), RPR_ORDER)

  def delete_mark(self, p):
    """Tracked deletion of p's paragraph mark: on Accept, p merges into the NEXT paragraph. Choose the
    direction so a heading is never merged away; for an empty paragraph usually delete the mark of the
    body paragraph in front of it instead."""
    self._mark(p, 'del')

  def split_after(self, p, e):
    """Tracked paragraph break after child e of p: p keeps the content up to e and gets an inserted mark,
    a new paragraph (no w14:paraId) takes the rest and p's properties."""
    p2 = etree.Element(q('p'))
    ppr = p.find(q('pPr'))
    if ppr is not None:
      c = copy.deepcopy(ppr)
      for x in c.iter(q('pPrChange'), q('rPrChange'), q('ins'), q('del')):
        x.getparent().remove(x)
      p2.append(c)
    for sib in list(e.itersiblings()):
      p2.append(sib)
    p.addnext(p2)
    self._mark(p, 'ins')
    return p2


def views(path, mode):
  """Paragraph texts of a part in 'orig' | 'reject' | 'accept' view, merging paragraphs whose mark is
  absent in that view."""
  out, buf = [], ''
  for p in load(path).getroot().iter(q('p')):
    buf += text(p, 'reject' if mode in ('orig', 'reject') else 'accept')
    mark = p.find(q('pPr') + '/' + q('rPr'))
    gone = mark is not None and mark.find(q('ins' if mode == 'reject' else 'del')) is not None
    if gone and mode != 'orig':
      continue
    out.append(buf)
    buf = ''
  return out + ([buf] if buf else [])


def verify(orig_dir, new_dir):
  """Check that every edit is tracked (Reject All gives back the original text) and show the accept-view diff."""
  ok = True
  for part in PARTS:
    o, n = (os.path.join(d, 'word', part) for d in (orig_dir, new_dir))
    if not os.path.exists(o):
      continue
    orig, rej, acc = views(o, 'orig'), views(n, 'reject'), views(n, 'accept')
    same = orig == rej
    ok &= same
    print(f'== {part}: reject view == original: {same}')
    if not same:
      for line in difflib.unified_diff(orig, rej, lineterm='', n=0):
        print('  REJECT', line[:200])
    for line in difflib.unified_diff(orig, acc, lineterm='', n=0):
      if not line.startswith(('---', '+++', '@@')):
        print('  ', line.replace(' ', '·')[:200])
  return ok


def audit(unpacked):
  """List formatting findings in an unpacked document, to review before writing a transform."""
  wd = os.path.join(unpacked, 'word')
  doc, sty = load(os.path.join(wd, 'document.xml')), load(os.path.join(wd, 'styles.xml'))
  names = {v: k for k, v in style_ids(sty).items()}
  name = lambda p: names.get(pstyle(p) or '', 'normal')
  root = doc.getroot()
  print('== pending revisions:', Counter(e.get(q('author')) for e in root.iter(
    q('ins'), q('del'), q('rPrChange'), q('pPrChange'))) or 'none')
  sets = load(os.path.join(wd, 'settings.xml')).getroot()
  print('== track changes on:', sets.find(q('trackRevisions')) is not None,
        '| updateFields:', sets.find(q('updateFields')) is not None)

  used = Counter()
  for part in PARTS + ('numbering.xml',):
    path = os.path.join(wd, part)
    if os.path.exists(path):
      used.update(re.findall(r'w:(?:pStyle|rStyle|tblStyle|styleLink|numStyleLink) w:val="([^"]*)"',
                             open(path, encoding='utf8').read()))
  print('== paragraph styles in use:', dict(Counter(name(p) for p in root.iter(q('p')))))
  keep = set(used) | {s.get(q('styleId')) for s in sty.getroot().iter(q('style')) if s.get(q('default')) == '1'}
  byid = {s.get(q('styleId')): s for s in sty.getroot().iter(q('style'))}
  todo = list(keep)
  while todo:
    s = byid.get(todo.pop())
    for tag in ('basedOn', 'link', 'next'):
      v = None if s is None or s.find(q(tag)) is None else s.find(q(tag)).get(q('val'))
      if v and v not in keep:
        keep.add(v)
        todo.append(v)
  print('== unused styles:', sorted(names.get(i, i) for i in byid if i not in keep))

  bms = {e.get(q('name')) for e in root.iter(q('bookmarkStart'))}
  issues = []
  ps = list(root.iter(q('p')))
  for i, p in enumerate(ps):
    nm, t = name(p), text(p)
    if nm.startswith('toc '):
      continue
    tbl = under(p, 'tc')
    tag = lambda kind, extra='': issues.append(f'{i:4} {kind:15} [{nm}] {extra}{t[:70]!r}')
    if '  ' in t or (t and t != t.strip(' ')):
      tag('spaces')
    if '↵' in t and not tbl:
      tag('soft-break')
    if not t.strip() and not tbl and p.find('.//' + q('drawing')) is None and p.find('.//' + q('fldChar')) is None:
      tag('empty', '(childless <w:p/>) ' if len(p) == 0 else '')
    ppr = p.find(q('pPr'))
    direct = [] if ppr is None else [ln(c) for c in ppr if ln(c) not in ('pStyle', 'numPr', 'rPr', 'cnfStyle',
                                                                            'sectPr', 'pPrChange')]
    if direct:
      tag('direct-pPr', ','.join(direct) + ' ')
    num = None if ppr is None else ppr.find(q('numPr') + '/' + q('numId'))
    if nm.startswith('heading') and num is not None and num.get(q('val')) == '0':
      tag('numbering-off')
    runs = [r for r in p.iter(q('r')) if own(r, p) and r.find(q('t')) is not None and not under(r, 'del')]
    bold = lambda r: r.find(q('rPr') + '/' + q('b')) is not None
    if nm == 'normal' and not tbl and runs and t.strip() and len(t) < 120 and all(bold(r) for r in runs if (r.findtext(q('t')) or '').strip()):
      tag('label' if t.strip().endswith(':') else 'pseudo-heading')
    if not tbl and re.match(r'\s*(\(?[ivx]+\)|\(?[a-z]\)|\d+\)|[-•–]\s)', t):
      tag('typed-list')
    nxt = p.getnext()
    if nm == 'normal' and t.strip() and nxt is not None and ln(nxt) == 'p' and (
        names.get(pstyle(nxt) or '') == 'list paragraph' or nxt.find(q('pPr') + '/' + q('numPr')) is not None):
      tag('list-lead-in')
    if re.search(r'Fehler!|Error!', t):
      tag('error-text')
  for p in ps:
    for h in p.iter(q('hyperlink')):
      a = h.get(q('anchor'))
      if h.get('{%s}id' % R) is None and (a is None or a not in bms):
        issues.append(f'     broken-link     {"".join(h.itertext())[:70]!r}')
  for it in root.iter(q('instrText')):
    s = (it.text or '').strip()
    m = re.match(r'(REF|PAGEREF)\s+(\S+)', s)
    if m and m.group(2) not in bms:
      issues.append(f'     missing-bookmark {s!r}')
    if s == 'HYPERLINK' or re.match(r'HYPERLINK\s*$', s):
      issues.append(f'     broken-link     HYPERLINK field without target')
    for st in re.findall(r'\\t\s+"([^"]*)"', s):
      for nm_ in st.split(',')[0::2]:
        if nm_.strip().lower() not in names.values():
          issues.append(f'     toc-style       TOC \\t names missing style {nm_!r}')
  print('== issues (paragraph index, kind, [style], text):')
  print('\n'.join(issues) or '   none')

  colours, other = Counter(), Counter()
  for r in root.iter(q('r')):
    rpr = r.find(q('rPr'))
    if rpr is None or under(r, 'del'):
      continue
    for c in rpr:
      v = c.get(q('val'))
      if ln(c) in ('color', 'highlight'):
        colours[f'{ln(c)}={v}'] += 1
      elif ln(c) not in RPR_META:
        other[ln(c) + (f'={v}' if v and ln(c) in ('sz', 'lang', 'rStyle') else '')] += 1
  print('== colours/highlights on runs:', dict(colours))
  print('== other direct run formatting:', dict(other.most_common(25)))


def unpack(docx, target):
  """Extract a .docx into a new directory (zipfile writes no symlinks and strips unsafe paths)."""
  os.mkdir(target)
  with zipfile.ZipFile(docx) as z:
    z.extractall(target)


def pack(orig_docx, unpacked, out_docx):
  """Zip an unpacked directory in the original archive's entry order ([Content_Types].xml first)."""
  names = zipfile.ZipFile(orig_docx).namelist()
  disk = sorted(os.path.relpath(os.path.join(a, f), unpacked).replace(os.sep, '/')
                for a, _, fs in os.walk(unpacked) for f in fs)
  with zipfile.ZipFile(out_docx, 'w', zipfile.ZIP_DEFLATED) as z:
    for n in [n for n in names if n in disk] + [n for n in disk if n not in names]:
      z.write(os.path.join(unpacked, n), n)


def render(docx, outdir):
  """Render through real Word (WSL, Word must be closed) to PDF and page PNGs, as after Accept All."""
  import subprocess
  os.makedirs(outdir, exist_ok=True)
  win = lambda p: subprocess.check_output(['wslpath', '-w', os.path.abspath(p)], text=True).strip()
  name = os.path.splitext(os.path.basename(docx))[0]
  ps1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'word2pdf.ps1')
  subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', win(ps1),
                  '-In', win(docx), '-Out', win(outdir) + '\\' + name + '.pdf'], check=True, timeout=300)
  subprocess.run(['pdftoppm', '-r', '80', '-png', os.path.join(outdir, name + '.pdf'), os.path.join(outdir, name)],
                 check=True)
  print(os.path.join(outdir, name + '.pdf'))


DUMP_SKIP = {'rPrChange', 'pPrChange', 'tcPrChange', 'trPrChange', 'ins', 'del', 'rPr', 'pStyle', 'rStyle'}
NOISE_ATTR = re.compile(r'^(rsid\w*|paraId|textId|durableId)$')


def _one(c, skip=DUMP_SKIP, names=None):
  attrs = ','.join(f'{etree.QName(k).localname}={v}' for k, v in c.attrib.items()
                   if not NOISE_ATTR.match(etree.QName(k).localname))
  if names and ln(c) in ('basedOn', 'next', 'link'):
    attrs = names.get(c.get(q('val')), c.get(q('val')))  # IDs are localized; names are not
  sub = _props(c, skip)
  return ln(c) + (f'({attrs})' if attrs else '') + (f'{{{sub}}}' if sub else '')


def _props(el, skip=DUMP_SKIP, names=None):
  return ' '.join(_one(c, skip, names) for c in ([] if el is None else el) if isinstance(c.tag, str) and ln(c) not in skip)


def records(d):
  """The document as it reads after Accept All: paragraphs (style, direct props, text, formatted runs),
  style definitions by name, numbering levels and settings."""
  wd = os.path.join(d, 'word')
  sty = load(os.path.join(wd, 'styles.xml'))
  names = {v: k for k, v in style_ids(sty).items()}
  paras = []
  for p in load(os.path.join(wd, 'document.xml')).getroot().iter(q('p')):
    where, cell = '', next(p.iterancestors(q('tc')), None)
    if cell is not None:
      tr = cell.getparent()
      where = f'cell r{list(tr.getparent().iterchildren(q("tr"))).index(tr) + 1}c{list(tr.iterchildren(q("tc"))).index(cell) + 1}'
      if p is cell.find(q('p')):
        where += f' <{_props(cell.find(q("tcPr")))}>'
    runs = []
    for r in p.iter(q('r')):
      if under(r, 'del') or not own(r, p):
        continue
      rp = r.find(q('rPr'))
      st = None if rp is None or rp.find(q('rStyle')) is None else rp.find(q('rStyle')).get(q('val'))
      f = ' '.join(x for x in (f'style={names.get(st, st)}' if st else '', _props(rp)) if x)
      t = ''.join(e.text or '' for e in r.findall(q('t')))
      if f and t.strip():
        runs.append((f, t))
    ppr = p.find(q('pPr'))
    paras.append({'where': where, 'style': names.get(pstyle(p) or '', 'normal'), 'text': text(p), 'runs': runs,
                  'ppr': [] if ppr is None else [_one(c) for c in ppr if isinstance(c.tag, str) and ln(c) not in DUMP_SKIP]})
  # 'link' names the paired character style, whose name Word localizes ("Überschrift 1 Zchn" / "Heading 1 Char")
  skip = DUMP_SKIP | {'name', 'rsid', 'uiPriority', 'qFormat', 'unhideWhenUsed', 'semiHidden', 'link'}
  styles = {names.get(s.get(q('styleId'))): _props(s, skip, names) for s in sty.getroot().iter(q('style'))}
  other = []
  num = os.path.join(wd, 'numbering.xml')
  if os.path.exists(num):
    other += [f'NUMBERING abstract {l.getparent().get(q("abstractNumId"))} level {l.get(q("ilvl"))} :: {_props(l)}'
              for l in load(num).getroot().iter(q('lvl'))]
  other += [f'SETTING {_one(c)}' for c in load(os.path.join(wd, 'settings.xml')).getroot()
            if isinstance(c.tag, str) and ln(c) not in ('rsids', 'docVars')]
  return paras, styles, other


def dump_lines(d):
  paras, styles, other = records(d)
  out = []
  for p in paras:
    out.append(' '.join(x for x in (p['where'], f"[{p['style']}]", ' '.join(p['ppr'])) if x) + ' | ' + p['text'])
    out += [f'      {f}: {t!r}' for f, t in p['runs']]
  return out + [f'STYLE {k} :: {v}' for k, v in styles.items()] + other


def dump(unpacked):
  """Print the document as text, as it reads after Accept All: content, formatting, styles, numbering, settings."""
  print('\n'.join(dump_lines(unpacked)))


def diff_lines(dir_a, dir_b):
  return list(difflib.unified_diff(dump_lines(dir_a), dump_lines(dir_b), dir_a, dir_b, lineterm='', n=1))


def diff(dir_a, dir_b):
  """ASCII diff of two unpacked documents (content, formatting, styles, numbering, settings); fails if they differ."""
  lines = diff_lines(dir_a, dir_b)
  print('\n'.join(lines) or 'no differences')
  return not lines


def stylecompare(dir_a, dir_b):
  """Compare the formatting of two versions with the same content.

  Shows how paragraph styles, direct and character formatting and style definitions map from A to B;
  paragraphs are paired by identical text."""
  (pa, sa, _), (pb, sb, _) = records(dir_a), records(dir_b)
  sm = difflib.SequenceMatcher(None, [p['text'] for p in pa], [p['text'] for p in pb], autojunk=False)
  pairs = [(pa[i + k], pb[j + k]) for i, j, n in sm.get_matching_blocks() for k in range(n)]
  print(f'== {len(pairs)} paragraphs paired by text; unpaired: {len(pa) - len(pairs)} in A, {len(pb) - len(pairs)} in B')
  ex = lambda t: repr(t[:50])
  smap = Counter((x['style'], y['style']) for x, y in pairs if x['style'] != y['style'])
  print('== paragraph style A -> B (count, example):')
  for (s1, s2), c in smap.most_common():
    print(f'  {c:4}  {s1} -> {s2}  e.g. {ex(next(x["text"] for x, y in pairs if (x["style"], y["style"]) == (s1, s2)))}')
  removed, added = Counter(), Counter()
  for x, y in pairs:
    removed.update(set(x['ppr']) - set(y['ppr']))
    added.update(set(y['ppr']) - set(x['ppr']))
  print('== direct paragraph formatting only in A:', dict(removed.most_common(15)))
  print('== direct paragraph formatting only in B:', dict(added.most_common(15)))
  ra = Counter(f for x, _ in pairs for f, _ in x['runs'])
  rb = Counter(f for _, y in pairs for f, _ in y['runs'])
  print('== character formatting (runs in A / in B), where the counts differ:')
  for f in sorted(set(ra) | set(rb), key=lambda f: -abs(ra[f] - rb[f]))[:20]:
    if ra[f] != rb[f]:
      print(f'  {ra[f]:4} / {rb[f]:<4} {f}')
  used = {x['style'] for x, _ in pairs} | {y['style'] for _, y in pairs}
  print('== definitions of styles in use that differ:')
  for s in sorted(used):
    if sa.get(s) != sb.get(s):
      print(f'  {s}\n    A: {sa.get(s)}\n    B: {sb.get(s)}')


def bbox_pages(pdf):
  """Per page: lines as lists of words (x0, y0, x1, y1, text), from pdftotext -bbox-layout."""
  import html, subprocess
  out = subprocess.run(['pdftotext', '-bbox-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout
  pages = []
  for pg in re.split(r'<page ', out)[1:]:
    pages.append([[(float(a), float(b), float(c), float(e), html.unescape(t)) for a, b, c, e, t in
                   re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', ln_)]
                  for ln_ in re.findall(r'<line[^>]*>(.*?)</line>', pg, re.S)])
  return pages


def wide_gaps(words, limit=20):
  """Inter-word gaps wider than limit pt on one line (a justified line ended by a manual break, or tabs)."""
  return [(round(b[0] - a[2], 1), a[4], b[4]) for a, b in zip(words, words[1:]) if b[0] - a[2] > limit]


def number_gap(page_words, line, ink_right=None):
  """Gap in pt between a heading/list number and its text. Uses the extracted label word if there is one,
  otherwise ink_right (rightmost dark pixel column left of the first word, in pt), because Word exports some
  numbering without extractable text."""
  first = line[0]
  if re.fullmatch(r'\d+(\.\d+)*\.?', first[4]) and len(line) > 1:
    return round(line[1][0] - first[2], 1)
  if ink_right is not None:
    return round(first[0] - ink_right, 1)
  return None


def lint(docx, outdir):
  """Layout checks on the real Word render (renders first unless <outdir>/<name>.pdf exists)."""
  import glob, io, subprocess
  from PIL import Image
  name = os.path.splitext(os.path.basename(docx))[0]
  pdf = os.path.join(outdir, name + '.pdf')
  if not os.path.exists(pdf):
    render(docx, outdir)
  pages = bbox_pages(pdf)
  subprocess.run(['pdftoppm', '-r', '100', '-gray', '-png', pdf, os.path.join(outdir, 'lint')], check=True)
  imgs = sorted(glob.glob(os.path.join(outdir, 'lint-*.png')))
  s = 100 / 72
  heights = sorted(l[0][3] - l[0][1] for pg in pages for l in pg if l)
  body_h = heights[len(heights) // 2]
  margin = sorted(min(l[0][0] for l in pg if len(l) > 2) for pg in pages if any(len(l) > 2 for l in pg))
  margin = margin[len(margin) // 2]
  issues, gaps = [], []
  for pi, (pg, img_path) in enumerate(zip(pages, imgs), 1):
    img = Image.open(img_path).convert('L')
    for line in pg:
      if not line or line[0][1] < 60 or line[0][3] > 790:
        continue
      t = ' '.join(w[4] for w in line)
      if re.search(r'Fehler!|Error!|Verweisquelle|Reference source', t):
        issues.append(f'p{pi}: field error text: {t[:70]!r}')
      if '.....' not in t:
        for g, a, b in wide_gaps(line):
          issues.append(f'p{pi}: {g}pt gap between {a!r} and {b!r} (stretched line or tabs?)')
      x0, y0, x1, y1, _ = line[0]
      ink = None
      if x0 - margin > 6 and not any(abs(w[3] - y1) < 2 and w[2] <= x0 for l in pg for w in l):
        box = img.crop((int((margin - 3) * s), int(y0 * s), int((x0 - 0.6) * s), int(y1 * s)))
        cols = [x for x in range(box.width) if min(box.getpixel((x, y)) for y in range(box.height)) < 100]
        ink = (int((margin - 3) * s) + max(cols) + 1) / s if cols else None
      g = number_gap(pg, line, ink)
      if g is not None and '.....' not in t:
        gaps.append((round(y1 - y0, 1), g, pi, t))
    tall = [l for l in pg if l and l[0][3] - l[0][1] > body_h * 1.12 and 650 < l[0][3] < 775]
    for l in tall:
      below = [m for m in pg if m and m[0][1] > l[0][3] and m[0][3] < 775 and m[0][3] - m[0][1] >= body_h * 0.95]
      if not below:
        issues.append(f'p{pi}: heading is the last text on the page: {" ".join(w[4] for w in l)[:60]!r}')
  for h, g, pi, t in gaps:
    if g < 0.2 * h:  # narrower than about half a space
      issues.append(f'p{pi}: number (nearly) touches its text (gap {g}pt at {h}pt): {t[:60]!r}')
  print('== issues:')
  print('\n'.join(issues) or '   none')
  print('== number-to-text gaps by text height (pt): consistent within a height, or a style indent is off')
  by_h = {}
  for h, g, pi, t in gaps:
    by_h.setdefault(round(h * 2) / 2, []).append((g, pi, t))
  for h, v in sorted(by_h.items()):
    lo, hi = min(v), max(v)
    print(f'  {h:5}: n={len(v):3}  min {lo[0]}pt (p{lo[1]} {lo[2][:30]!r})  max {hi[0]}pt (p{hi[1]} {hi[2][:30]!r})')
  fonts = subprocess.run(['pdffonts', pdf], capture_output=True, text=True).stdout.splitlines()[2:]
  print('== fonts in the PDF:', sorted({f.split()[0].split('+')[-1] for f in fonts if f.strip()}))
  with zipfile.ZipFile(docx) as z:
    rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', z.read('word/_rels/document.xml.rels').decode()))
    doc = etree.fromstring(z.read('word/document.xml'))
    print('== images:')
    for dr in doc.iter('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline',
                       '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor'):
      ext = dr.find('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent')
      blip = dr.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
      if blip is None or ext is None:
        continue
      svg = blip.find('.//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip')
      target = rels.get(blip.get('{%s}embed' % R), '?')
      width_in = int(ext.get('cx')) / 914400
      if svg is not None:
        print(f'  vector  {rels.get(svg.get("{%s}embed" % R), "?")} (fallback {target}, {width_in * 2.54:.1f} cm wide)')
      elif target.lower().endswith(('.svg', '.emf', '.wmf')):
        print(f'  vector  {target}  ({width_in * 2.54:.1f} cm wide)')
      else:
        px = Image.open(io.BytesIO(z.read('word/' + target))).size
        print(f'  RASTER  {target}  {px[0]}x{px[1]} px, {width_in * 2.54:.1f} cm wide = {px[0] / width_in:.0f} dpi'
              ' - ask for a vector source (SVG/EMF)')


def crop(before_pdf, after_pdf, spec, outdir, dpi=130):
  """Cut before/after crops from two Word renders for a review page.

  spec: JSON list of {id, anchor | before_anchor/after_anchor | page, above, height, min_page?, page_top?};
  anchors are text found in each PDF separately, because pages shift."""
  import json, subprocess
  os.makedirs(outdir, exist_ok=True)
  docs = {'before': (before_pdf, bbox_pages(before_pdf)), 'after': (after_pdf, bbox_pages(after_pdf))}
  index = []
  for ex in json.load(open(spec)):
    row = dict(ex)
    for side, (pdf, pages) in docs.items():
      anchor = ex.get(side + '_anchor', ex.get('anchor'))
      page, y = ex.get('page'), 0
      if anchor:
        page, y = next(((i, l[0][1]) for i, pg in enumerate(pages, 1) if i >= ex.get('min_page', 1) for l in pg
                        if l and anchor in ' '.join(w[4] for w in l)), (None, 0))
        assert page, f'anchor not found in {side}: {anchor!r}'
        y = 0 if ex.get('page_top') else y
      top, sc = max(0, y - ex.get('above', 14)), dpi / 72
      subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', str(dpi), '-singlefile', '-png',
                      '-x', str(int(52 * sc)), '-y', str(int(top * sc)), '-W', str(int(492 * sc)),
                      '-H', str(int(ex['height'] * sc)), pdf, os.path.join(outdir, f"{ex['id']}-{side}")], check=True)
      row[side + '_page'] = page
    index.append(row)
  json.dump(index, open(os.path.join(outdir, 'index.json'), 'w'), indent=1)
  print('\n'.join(f"{r['id']}: before p{r['before_page']}, after p{r['after_page']}" for r in index))


def check(orig_docx, new_docx, outdir, validator, author):
  """Verification gate for a finished transform: tracked edits, schema, ASCII diff, layout lint.

  validator: the docx skill's scripts/office/validate.py; author: the redline author. The diff goes to
  <outdir>/diff.txt, the Word render to <outdir>/render (Word must be closed)."""
  import subprocess
  os.makedirs(outdir, exist_ok=True)
  orig, new = os.path.join(outdir, 'orig'), os.path.join(outdir, 'new')
  unpack(orig_docx, orig)
  unpack(new_docx, new)
  ok = verify(orig, new)
  ok &= subprocess.run([sys.executable, validator, new_docx, '--original', orig_docx, '--author', author]).returncode == 0
  lines = diff_lines(orig, new)
  with open(os.path.join(outdir, 'diff.txt'), 'w', encoding='utf8') as f:
    f.write('\n'.join(lines) + '\n')
  print(f"== ASCII diff: {os.path.join(outdir, 'diff.txt')} "
        f"({sum(1 for l in lines if l[:1] in '+-' and l[:3] not in ('+++', '---'))} changed lines)")
  lint(new_docx, os.path.join(outdir, 'render'))
  return ok


def selftest():
  """Run the toolkit's self-test."""
  import tempfile
  body = (
    '<w:p/>'
    '<w:p><w:pPr><w:pStyle w:val="X"/></w:pPr><w:r><w:t xml:space="preserve"> Lorem  ipsum </w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> REF _Ref1 </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t xml:space="preserve">a  b</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r><w:r><w:t xml:space="preserve">  dolor</w:t></w:r>'
    '<w:r><w:br/></w:r><w:r><w:t>sit </w:t></w:r></w:p>'
    '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>amet</w:t></w:r></w:p>')
  xml = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
  with tempfile.TemporaryDirectory() as tmp:
    for d in ('a', 'b'):
      os.makedirs(os.path.join(tmp, d, 'word'))
      open(os.path.join(tmp, d, 'word', 'document.xml'), 'w').write(xml)
    path = os.path.join(tmp, 'b', 'word', 'document.xml')
    tree = load(path)
    ps = list(tree.getroot().iter(q('p')))
    assert len(ps) == 3, 'a childless <w:p/> must count as a paragraph'
    rl = Redline('Test Author', [tree])
    p = ps[1]
    dels = whitespace_dels(p)
    assert all(not chars(p)[k][2] for k in dels), 'field results must stay untouched'
    assert ''.join(c[3] for k, c in enumerate(chars(p)) if k not in dels) == 'Lorem ipsum a  b dolor↵sit', 'whitespace'
    rl.delete_chars(p, dels)
    rl.ppr(p, lambda ppr: None)
    assert p.find('.//' + q('pPrChange')) is None, 'no-op must not create a revision'
    rl.ppr(p, lambda ppr: ppr.find(q('pStyle')).set(q('val'), 'Y'))
    assert p.find('.//' + q('pPrChange')) is not None
    br_run = next(r for r in p.iter(q('r')) if r.find(q('br')) is not None)
    p3 = rl.split_after(p, br_run)
    rl.delete_runs([br_run])
    assert text(p3) == 'sit' and 'paraId' not in str(p3.attrib)
    rl.delete_mark(ps[2])
    rl.delete_mark(ps[2])
    assert len(ps[2].findall('.//' + q('del'))) == 1, 'a paragraph mark must not be deleted twice'
    rl.rpr(ps[2].find(q('r')), lambda rpr: rpr.remove(rpr.find(q('b'))))
    assert ps[2].find('.//' + q('rPrChange')) is not None
    save(tree, path)
    a, b = (os.path.join(tmp, d, 'word', 'document.xml') for d in ('a', 'b'))
    assert views(a, 'orig') == views(b, 'reject'), (views(a, 'orig'), views(b, 'reject'))
    assert views(b, 'accept')[1:3] == ['Lorem ipsum a  b dolor', 'sit'], views(b, 'accept')
    for d in ('a', 'b'):
      open(os.path.join(tmp, d, 'word', 'styles.xml'), 'w').write(
        f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="X"><w:name w:val="heading 1"/></w:style>'
        f'<w:style w:type="paragraph" w:styleId="Y"><w:name w:val="heading 2"/></w:style></w:styles>')
      open(os.path.join(tmp, d, 'word', 'settings.xml'), 'w').write(f'<w:settings xmlns:w="{W}"/>')
    da, db = dump_lines(os.path.join(tmp, 'a')), dump_lines(os.path.join(tmp, 'b'))
    assert '[heading 1] |  Lorem  ipsum a  b  dolor↵sit ' in da, da
    assert db[1:4] == ['[heading 2] | Lorem ipsum a  b dolor', '[heading 2] | sit', '[normal] | amet'], db
  words = [(70, 0, 100, 12, 'completely'), (400, 0, 440, 12, 'excluded.')]
  assert wide_gaps(words) == [(300, 'completely', 'excluded.')]
  assert number_gap([], [(70, 0, 85, 14, '6.3'), (85.2, 0, 120, 14, 'Right')]) == 0.2
  assert number_gap([], [(90, 0, 120, 14, 'Right')], ink_right=89.5) == 0.5
  print('selftest ok')


COMMANDS = (unpack, audit, lint, render, verify, check, dump, diff, stylecompare, crop, pack, selftest)


def main(argv=None):
  parser = argparse.ArgumentParser(prog='wordtool.py', description=__doc__.split('\n')[0])
  commands = parser.add_subparsers(required=True, metavar='command')
  for fn in COMMANDS:
    sub = commands.add_parser(fn.__name__, help=fn.__doc__.split('\n')[0], description=fn.__doc__)
    for name, param in inspect.signature(fn).parameters.items():
      if param.default is param.empty:
        sub.add_argument(name)
      else:
        sub.add_argument('--' + name, type=type(param.default), default=param.default)
    sub.set_defaults(command=fn)
  args = vars(parser.parse_args(argv))
  return 1 if args.pop('command')(**args) is False else 0


if __name__ == '__main__':
  sys.exit(main())
