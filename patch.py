#!/usr/bin/env python3
"""
StudyHub — Mobile Patch Injector  v3
─────────────────────────────────────────────────────────────
Strategy:
  1. Fix/add viewport meta
  2. Inject <link> to mobile.css  (generic helpers only)
  3. Detect whether the page has its own sidebar/nav system:
       a. Has .sidebar + toggleSidebar()  → WORKING sidebar,
          just ensure .main margin is zeroed on mobile.
       b. Has its own sidebar but NO mobile toggle  → inject
          a <style> block that hides the sidebar on mobile
          and shows our hamburger + slide-in drawer.
       c. No sidebar at all  → inject a lightweight TOC drawer
          built from the page's h1/h2 headings.
  4. Inject a targeted <style> block inside the page for
     def-table stacking, overflow fixes, and any class names
     specific to that page's structure.

Usage:
  python3 patch.py            # patch all pages
  python3 patch.py --dry-run  # preview only
  python3 patch.py --undo     # restore .bak files
"""

import os, sys, re, shutil
from html.parser import HTMLParser

# ── Config ────────────────────────────────────────────────
CSS_FILE     = "mobile.css"
BACKUP_EXT   = ".bak"
PATCH_MARKER = "<!-- SHN-v3 -->"
SKIP_FILES   = {"index.html"}

# ── Colours ───────────────────────────────────────────────
def _c(t,c): return f"\033[{c}m{t}\033[0m"
green  = lambda t: _c(t,"0;32")
yellow = lambda t: _c(t,"0;33")
red    = lambda t: _c(t,"0;31")
cyan   = lambda t: _c(t,"0;36")
bold   = lambda t: _c(t,"1;37")
dim    = lambda t: _c(t,"0;90")

# ── Heading extractor ─────────────────────────────────────
class HX(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heads=[]; self._t=None; self._id=None; self._buf=[]
    def handle_starttag(self,tag,attrs):
        if tag in('h1','h2','h3'):
            self._t=tag; self._id=dict(attrs).get('id',''); self._buf=[]
    def handle_endtag(self,tag):
        if tag==self._t and tag in('h1','h2','h3'):
            txt=re.sub(r'\s+',' ',' '.join(self._buf)).strip()
            if txt and len(txt)>2:
                self.heads.append((self._t,self._id,txt))
            self._t=None
    def handle_data(self,d):
        if self._t: self._buf.append(d)

def get_headings(html):
    p=HX(); p.feed(html); return p.heads

# ── Auto-add IDs to headings missing them ─────────────────
def add_ids(html):
    seen={}
    def slug(t):
        s=re.sub(r'[^a-z0-9]+','-',t.lower()).strip('-')[:40]
        seen[s]=seen.get(s,0)+1
        return s if seen[s]==1 else f"{s}-{seen[s]}"
    def rep(m):
        otag,tag,inner,ctag=m.group(1),m.group(2),m.group(3),m.group(4)
        if 'id=' in otag.lower(): return m.group(0)
        txt=re.sub(r'<[^>]+>','',inner).strip()
        if not txt: return m.group(0)
        return f'{otag.rstrip(">")} id="{slug(txt)}">{inner}{ctag}'
    return re.sub(r'(<(h[123])\b[^>]*>)(.*?)(</\2>)',
                  rep, html, flags=re.DOTALL|re.I)

# ── Drawer HTML ───────────────────────────────────────────
DRAWER_CSS = """
<style id="shn-styles">
/* SHN drawer */
#shn-btn{display:none}
@media(max-width:768px){
  #shn-btn{
    display:flex!important;position:fixed;top:10px;left:10px;
    z-index:19999;width:46px;height:46px;border-radius:12px;
    background:#1B4F8A;color:#fff;border:none;font-size:1.3rem;
    align-items:center;justify-content:center;cursor:pointer;
    box-shadow:0 4px 20px rgba(0,0,0,.5);
    -webkit-tap-highlight-color:transparent;
  }
  #shn-overlay{
    display:none;position:fixed;inset:0;
    background:rgba(0,0,0,.6);z-index:19998;
  }
  #shn-overlay.on{display:block}
  #shn-nav{
    position:fixed;top:0;left:0;bottom:0;
    width:min(280px,82vw);background:#0B1E3D;
    z-index:19999;overflow-y:auto;
    transform:translateX(-100%);
    transition:transform .28s cubic-bezier(.4,0,.2,1);
    padding-bottom:40px;
    box-shadow:4px 0 30px rgba(0,0,0,.6);
  }
  #shn-nav.on{transform:translateX(0)}
  #shn-nav::-webkit-scrollbar{width:3px}
  #shn-nav::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1)}
  .shn-hdr{
    display:flex;align-items:center;justify-content:space-between;
    padding:14px;border-bottom:1px solid rgba(255,255,255,.08);
    position:sticky;top:0;background:#0B1E3D;z-index:1;
  }
  .shn-hdr span{
    font:700 .72rem/1 system-ui,sans-serif;
    color:#A8C8F0;text-transform:uppercase;letter-spacing:.1em;
  }
  .shn-hdr button{
    background:rgba(255,255,255,.08);border:none;border-radius:6px;
    color:#7B9AC8;width:28px;height:28px;cursor:pointer;font-size:.9rem;
  }
  .shn-back{
    display:flex;align-items:center;gap:6px;
    padding:11px 14px;color:#F0A500;text-decoration:none;
    font:600 .76rem/1 system-ui,sans-serif;
    border-bottom:1px solid rgba(255,255,255,.06);
    background:rgba(240,165,0,.05);
  }
  .shn-grp{
    padding:10px 14px 3px;
    font:700 .58rem/1 system-ui,sans-serif;
    color:#2E4A72;text-transform:uppercase;letter-spacing:.13em;
  }
  .shn-lnk{
    display:flex;align-items:center;gap:8px;
    padding:9px 14px;color:#7BA8D4;text-decoration:none;
    font:.78rem/1.35 system-ui,sans-serif;
    border-left:3px solid transparent;
    -webkit-tap-highlight-color:transparent;
  }
  .shn-lnk:active,.shn-lnk.act{
    color:#fff;background:rgba(255,255,255,.05);
    border-left-color:#F0A500;
  }
  .shn-num{
    font:700 .6rem/1 monospace;
    background:rgba(255,255,255,.07);border-radius:4px;
    padding:1px 5px;color:#4A9FD5;
    flex-shrink:0;min-width:22px;text-align:center;
  }
}
</style>"""

def drawer_html(heads, title):
    items=[]
    n=0
    for tag,hid,txt in heads:
        if tag not in('h1','h2'): continue
        if len(txt)<3: continue
        n+=1
        href=f"#{hid}" if hid else "#"
        lbl=f"{n:02d}" if tag=='h2' else '★'
        items.append(
            f'    <a class="shn-lnk" href="{href}" onclick="shnClose()">'
            f'<span class="shn-num">{lbl}</span>{txt}</a>'
        )
    if not items: return ''
    t=title[:32]+('…' if len(title)>32 else '')
    rows='\n'.join(items)
    return f"""\n{DRAWER_CSS}\n<!-- SHN-v3 -->\n<div id="shn-overlay" onclick="shnClose()"></div>\n<button id="shn-btn" onclick="shnOpen()" aria-label="Open navigation">&#9776;</button>\n<nav id="shn-nav">\n  <div class="shn-hdr"><span>Contents</span><button onclick="shnClose()">&#10005;</button></div>\n  <a class="shn-back" href="index.html">&#8592; Study Hub</a>\n  <div class="shn-grp">{t}</div>\n{rows}\n</nav>\n<script>\n(function(){{\nvar nav=document.getElementById('shn-nav'),\n    ov=document.getElementById('shn-overlay'),\n    btn=document.getElementById('shn-btn');\nwindow.shnOpen=function(){{nav.classList.add('on');ov.classList.add('on');btn.innerHTML='&#10005;';}};\nwindow.shnClose=function(){{nav.classList.remove('on');ov.classList.remove('on');btn.innerHTML='&#9776;';}};\nvar lnks=nav.querySelectorAll('.shn-lnk[href^="#"]');\nwindow.addEventListener('scroll',function(){{\n  var y=window.scrollY+90,act=null;\n  lnks.forEach(function(l){{var el=document.getElementById(l.getAttribute('href').slice(1));if(el&&el.offsetTop<=y)act=l;}});\n  lnks.forEach(function(l){{l.classList.remove('act');}});\n  if(act)act.classList.add('act');\n}},{{passive:true}});\ndocument.addEventListener('keydown',function(e){{if(e.key==='Escape')shnClose();}});\n}})();\n</script>\n"""

# ── Targeted mobile <style> for each page ─────────────────
# Detects which layout/class names the page uses and
# emits precise @media rules for that page only.

def detect_layout(html):
    """Return dict of detected features."""
    f = {}
    f['has_sidebar_class']   = bool(re.search(r'class="[^"]*\bsidebar\b', html, re.I))
    f['has_toggle_sidebar']  = 'toggleSidebar' in html
    f['has_shn_marker']      = 'SHN-v3' in html
    f['has_def_table']       = 'def-table' in html or 'term-cell' in html
    f['has_data_table']      = 'data-table' in html
    f['has_aside']           = bool(re.search(r'<aside\b', html, re.I))
    # Detect sidebar via common patterns
    f['has_nav_sidebar']     = bool(re.search(
        r'position\s*:\s*fixed[^}]*width\s*:\s*(250|260|270|280|300)px', html, re.I))
    # Detect main content margin offset
    f['main_margin']         = re.search(
        r'\.main\s*\{[^}]*margin-left\s*:\s*var\(--sidebar', html, re.I)
    f['has_left_panel']      = bool(re.search(
        r'class="[^"]*\b(left-panel|nav-panel|side-nav|sidenav|left-nav)\b', html, re.I))
    return f

def build_page_style(html, f):
    """Build a targeted <style> block for this page's specific needs."""
    rules = []

    # ── Def-table: stack term above definition on mobile ──
    if f['has_def_table']:
        rules.append("""
  /* Stack def-table columns vertically on mobile */
  .def-table { width:100%!important; }
  .def-table tr { display:flex!important; flex-direction:column!important; }
  .def-table td { display:block!important; width:100%!important; box-sizing:border-box!important; }
  .term-cell {
    width:100%!important; border-right:none!important;
    border-bottom:1px solid rgba(100,150,220,.25)!important;
    font-size:.79rem!important; padding:7px 10px 4px!important;
  }
  .def-cell {
    width:100%!important; border-top:none!important;
    font-size:.79rem!important; padding:4px 10px 10px!important;
  }""")

    # ── Data table: horizontal scroll ─────────────────────
    if f['has_data_table']:
        rules.append("""
  /* Data/comparison tables: scroll horizontally */
  .data-table { display:block!important; overflow-x:auto!important;
    -webkit-overflow-scrolling:touch!important; }
  .data-table thead th { white-space:nowrap; font-size:.72rem!important; padding:7px 8px!important; }
  .data-table tbody td { font-size:.76rem!important; padding:6px 8px!important; }""")

    # ── Pages with existing working sidebar (Nutanix guide) ─
    if f['has_sidebar_class'] and f['has_toggle_sidebar']:
        rules.append("""
  /* Ensure main content fills width when sidebar is hidden */
  .main { margin-left:0!important; max-width:100vw!important;
    padding:1.2rem 14px 3rem!important; }
  .progress-bar { left:0!important; }
  /* Topbar search hidden on mobile */
  .topbar-search { display:none!important; }
  /* Cover responsive */
  .cover { padding:22px 14px!important; }
  .cover h1 { font-size:clamp(1.8rem,8vw,2.8rem)!important; }
  .cheatsheet-grid { grid-template-columns:1fr!important; }
  .card-grid { grid-template-columns:1fr!important; }""")

    # ── Pages with fixed sidebar but NO toggle (CCNA etc) ──
    if f['has_sidebar_class'] and not f['has_toggle_sidebar'] and not f['has_shn_marker']:
        rules.append("""
  /* Hide the built-in sidebar on mobile — replaced by SHN drawer */
  .sidebar, #sidebar, [class*="sidebar"] {
    display:none!important; visibility:hidden!important;
  }
  /* Also hide any fixed aside navigation */
  aside { display:none!important; }
  /* Remove left margin that was reserved for sidebar */
  .main-content, .content, main, .main, body > div:not(#shn-nav):not(#shn-overlay) {
    margin-left:0!important; max-width:100%!important;
    padding-left:14px!important; padding-right:14px!important;
    width:100%!important; box-sizing:border-box!important;
  }""")

    # ── Generic overflow & layout fixes for all pages ──────
    rules.append("""
  /* Prevent horizontal overflow on all elements */
  *, *::before, *::after { max-width:100%; box-sizing:border-box; }
  pre, code, .code-group, .code-block {
    overflow-x:auto!important; -webkit-overflow-scrolling:touch!important;
    white-space:pre!important; font-size:.7rem!important;
  }
  /* Flex rows that need to wrap */
  .lifecycle, .workflow, [class*="lifecycle"], [class*="flow-row"],
  [class*="step-row"], [class*="card-row"] {
    flex-wrap:wrap!important; gap:8px!important;
  }
  /* Tab bars / pill nav */
  [class*="tab-bar"], [class*="topic-nav"], [class*="filter"],
  .topics, .nav-tabs {
    overflow-x:auto!important; -webkit-overflow-scrolling:touch!important;
    flex-wrap:nowrap!important; white-space:nowrap!important;
    padding-bottom:4px!important;
  }
  /* Command/card grids */
  [class*="cmd-grid"], [class*="command-grid"],
  [class*="card-grid"], [class*="section-grid"] {
    grid-template-columns:1fr!important; gap:10px!important;
  }
  /* Wide flex containers inside content */
  [class*="section-content"], [class*="content-area"],
  [class*="two-col"], [class*="split"] {
    flex-direction:column!important; width:100%!important;
  }
  /* Priority/badge chips that wrap */
  [class*="priority"], [class*="badge"], [class*="chip"],
  [class*="tag-row"] { flex-wrap:wrap!important; }
  /* Modal/overlay full width */
  [class*="modal"], [class*="panel"], [class*="drawer"] {
    max-width:100vw!important;
  }
  /* Stat/metric grids */
  [class*="stat-grid"], [class*="metric"], [class*="kpi"] {
    grid-template-columns:1fr 1fr!important;
  }
  /* Large padding containers */
  [class*="hero"], [class*="banner"], [class*="header-wrap"] {
    padding:20px 14px!important;
  }""")

    if not rules:
        return ''

    all_rules = '\n'.join(rules)
    return f"""
<style id="shn-page-mobile">
/* StudyHub mobile patch — auto-generated */
@media (max-width: 768px) {{
{all_rules}
}}
</style>"""

# ── Core patch function ───────────────────────────────────
def patch_file(path, dry_run=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    if PATCH_MARKER in orig:
        print(f"  {dim('⟳  already patched')}    {dim(fname)}")
        return 'already'

    html = orig

    # 1. Viewport meta
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        html = re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',
                      vp, html, flags=re.I)
    else:
        html = re.sub(r'(<head[^>]*>)', r'\1\n  '+vp, html, count=1, flags=re.I)

    # 2. mobile.css link
    if CSS_FILE not in html:
        link = f'  <link rel="stylesheet" href="{CSS_FILE}">'
        html = re.sub(r'(</head>)', link+r'\n\1', html, count=1, flags=re.I)

    # 3. Detect layout features
    f = detect_layout(html)

    # 4. Targeted page <style>
    page_style = build_page_style(html, f)
    if page_style:
        html = re.sub(r'(</head>)', page_style+r'\n\1', html, count=1, flags=re.I)

    # 5. Inject TOC drawer (only if no existing working nav)
    nav_note = ''
    if not f['has_toggle_sidebar']:
        html = add_ids(html)
        heads = get_headings(html)
        dhtml = drawer_html(heads, re.sub(r'<[^>]+>','',
            (re.search(r'<title[^>]*>(.*?)</title>',html,re.I|re.S) or
             type('',(),{'group':lambda s,n:fname})()).group(1)).strip())
        if dhtml:
            html = re.sub(r'(<body[^>]*>)', r'\1'+dhtml,
                          html, count=1, flags=re.I)
            nav_note = f"{cyan('+ TOC')} ({sum(1 for t,_,_ in heads if t in ('h1','h2'))} items)"
        else:
            nav_note = yellow('no headings')
    else:
        nav_note = dim('own nav kept')

    if html == orig:
        print(f"  {yellow('⚠  no change')}         {fname}")
        return 'skip'

    if dry_run:
        print(f"  {cyan('○  would patch')}      {fname}  [{nav_note}]")
        return 'dry'

    shutil.copy2(path, path+BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f2:
        f2.write(html)
    print(f"  {green('✔  patched')}          {fname}  [{nav_note}]")
    return 'patched'

def undo_file(path):
    fname = os.path.basename(path)
    bak = path+BACKUP_EXT
    if os.path.exists(bak):
        shutil.copy2(bak, path); os.remove(bak)
        print(f"  {green('✔  restored')}         {fname}")
        return 'ok'
    print(f"  {yellow('⚠  no backup')}        {fname}")
    return 'skip'

def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    undo = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(bold('  ╔════════════════════════════════════════╗'))
    print(bold('  ║  StudyHub Mobile Patch  v3             ║'))
    print(bold('  ╚════════════════════════════════════════╝'))
    print(f'\n  Dir : {cyan(wd)}')
    print(f'  Mode: {yellow("DRY RUN") if dry else (red("UNDO") if undo else green("PATCH"))}\n')

    if not undo and not os.path.exists(os.path.join(wd, CSS_FILE)):
        print(red(f'  ✗  {CSS_FILE} not found in {wd}\n')); sys.exit(1)

    files = sorted(os.path.join(wd,f) for f in os.listdir(wd)
                   if f.lower().endswith('.html') and f not in SKIP_FILES)
    if not files:
        print(yellow('  ⚠  No HTML files.\n')); sys.exit(0)

    print(f'  {bold(str(len(files)))} file(s) found:\n')
    c={}
    for fp in files:
        r = undo_file(fp) if undo else patch_file(fp, dry)
        c[r]=c.get(r,0)+1

    print(f'\n  {"─"*44}')
    if undo:
        print(f'  {green("Restored")}: {c.get("ok",0)}   {yellow("No backup")}: {c.get("skip",0)}')
    elif dry:
        print(f'  {cyan("Would patch")}: {c.get("dry",0)}   {dim("Already OK")}: {c.get("already",0)}')
    else:
        print(f'  {green("Patched")}: {c.get("patched",0)}   {dim("Already OK")}: {c.get("already",0)}   {yellow("Skipped")}: {c.get("skip",0)}')

    if not undo and not dry and c.get('patched',0)>0:
        git_msg = 'git commit -m "Mobile patch v3 — fix sidebar and layout"'
        print(f'\n  {green("✔  Done! Push to GitHub:")}')
        print(f'    {cyan("git add .")}')
        print(f'    {cyan(git_msg)}')
        print(f'    {cyan("git push")}')
    print()

if __name__=='__main__':
    main()
