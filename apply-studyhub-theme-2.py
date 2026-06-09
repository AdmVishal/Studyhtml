#!/usr/bin/env python3
"""
apply_studyhub_theme.py  v2
═══════════════════════════════════════════════════════════════════════
Applies the StudyHub unified theme to all HTML pages.

v2 fixes: previous version force-applied light colours (#F0F4FA bg)
onto dark-themed pages (Linux, ITIL, RHEL, Master Hub) causing text
to become invisible. 

Correct approach:
  - PRESERVE each page's own colour scheme (dark or light)
  - UNIFY: fonts (Syne/DM Sans/JetBrains Mono), topbar, heading
    typography, code block style, scrollbars, progress bar, back-to-top
  - Override ONLY font-family and heading/code colour rules that are
    safe on any background colour

Dark pages  (bg ~#0d0f14):  Linux, OS Admin, ITIL, Master Hub, RHEL, Network
Light pages (bg ~#F0F4FA):  Nutanix Foundations

Usage:
  cd ~/Studyhtml
  python3 apply_studyhub_theme.py            # apply to all pages
  python3 apply_studyhub_theme.py --dry-run  # preview
  python3 apply_studyhub_theme.py --undo     # restore .bak2 backups
"""

import os, sys, re, shutil

BACKUP_EXT  = ".bak2"
THEME_MARK  = "<!-- SHUB-THEME-v2 -->"
SKIP        = {"index.html"}

def c(t,code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t,"0;32");  Y = lambda t: c(t,"0;33")
R = lambda t: c(t,"0;31");  C = lambda t: c(t,"0;36")
B = lambda t: c(t,"1;37");  D = lambda t: c(t,"0;90")

# ── Detect whether a page is dark-themed ─────────────────────────
def is_dark(html):
    """Return True if the page has a dark background colour scheme."""
    # Look for dark bg values in :root or body CSS
    patterns = [
        r'--bg\s*:\s*#0[0-9a-f]{5}',          # very dark bg e.g. #0d0f14
        r'background\s*:\s*#0[0-9a-f]{5}',
        r'background-color\s*:\s*#0[0-9a-f]{5}',
        r'--bg\s*:\s*#1[0-9a-f]{5}',           # also dark e.g. #161b22
        r'--surface\s*:\s*#1[0-9a-f]{5}',
        r'background\s*:\s*#1[0-3][0-9a-f]{4}', # #10xxxx - #13xxxx
    ]
    for p in patterns:
        if re.search(p, html[:4000], re.I):
            return True
    return False

# ═══════════════════════════════════════════════════════════════════
#  SHARED INFRASTRUCTURE (works on ANY background colour)
#  - Topbar always navy (looks right on dark AND light pages)
#  - Fonts unified to Syne/DM Sans/JetBrains Mono
#  - Progress bar, back-to-top always visible
# ═══════════════════════════════════════════════════════════════════
SHARED_CSS = """<style id="shub-theme-v2">
/* ════════════════════════════════════════════════════════════════
   StudyHub Unified Theme v2 — typography + chrome unification
   Colour scheme of each page is PRESERVED (not overridden)
════════════════════════════════════════════════════════════════ */

/* ── Shared tokens (non-colour) ──────────────────────────────── */
:root {
  --shub-navy:   #0B1E3D;
  --shub-blue:   #1B4F8A;
  --shub-mid:    #2E6CC7;
  --shub-sky:    #4A9FD5;
  --shub-accent: #F0A500;
  --font-head:   'Syne', sans-serif;
  --font-body:   'DM Sans', sans-serif;
  --font-mono:   'JetBrains Mono', monospace;
}

/* ── Topbar ──────────────────────────────────────────────────── */
#shub-topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 9999;
  height: 58px;
  background: var(--shub-navy);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 2px solid var(--shub-blue);
  box-shadow: 0 2px 20px rgba(0,0,0,0.5);
}
.shub-logo {
  font-family: var(--font-head);
  font-weight: 800;
  font-size: 1.05rem;
  color: #fff;
  letter-spacing: 0.04em;
  text-decoration: none;
  white-space: nowrap;
}
.shub-logo-dot { color: var(--shub-accent); }
.shub-page-title {
  font-family: var(--font-body);
  font-size: 0.73rem;
  color: #6B8AB0;
  font-weight: 300;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}
.shub-spacer { flex: 1; }
.shub-home {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 7px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.13);
  color: #8AAED6;
  font-size: 0.74rem;
  font-family: var(--font-body);
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.shub-home:hover { background: rgba(255,255,255,0.14); color: #fff; }

/* ── Progress bar ────────────────────────────────────────────── */
#shub-prog {
  position: fixed;
  top: 58px; left: 0;
  height: 3px;
  width: 0%;
  background: linear-gradient(90deg, var(--shub-accent), var(--shub-sky));
  z-index: 9998;
  transition: width 0.08s linear;
  pointer-events: none;
}

/* ── Back-to-top ─────────────────────────────────────────────── */
#shub-btt {
  position: fixed;
  bottom: 24px; right: 20px;
  width: 42px; height: 42px;
  background: var(--shub-blue);
  color: #fff;
  border: none;
  border-radius: 50%;
  font-size: 1.1rem;
  cursor: pointer;
  z-index: 9997;
  opacity: 0;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(27,79,138,0.45);
  transition: opacity 0.2s, transform 0.2s, background 0.15s;
}
#shub-btt.vis { opacity: 1; pointer-events: auto; }
#shub-btt:hover { background: var(--shub-mid); transform: translateY(-2px); }

/* ── Push all pages' content below our topbar ───────────────── */
/* We target the page's own top-level containers */
body > header:not(#shub-topbar),
body > .header:not(#shub-topbar),
body > .topbar:not(#shub-topbar),
body > .toc,
body > .nav-bar,
body > .app-header {
  margin-top: 58px !important;
}
/* For pages where the sticky/fixed header is not <body>'s child */
.header, .toc, .nav-bar {
  top: 58px !important;
}
/* Nutanix-style topbar (.topbar class used by Nutanix page itself) */
.topbar:not(#shub-topbar) {
  top: 58px !important;
}
/* Main content areas */
.main, .main-content, .content-area, .app-content {
  margin-top: 58px !important;
}

/* ── Font unification ────────────────────────────────────────── */
/* Apply DM Sans to body — safe on all bg colours */
body { font-family: var(--font-body) !important; }

/* Headings — use Syne everywhere */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-head) !important;
}

/* Monospace — unify to JetBrains Mono */
code, pre, kbd, samp,
.cmd-block, [class*="code-block"],
[class*="cmd-block"], [class*="mono"] {
  font-family: var(--font-mono) !important;
}

/* ── Scrollbar style ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.28); }

/* ── Selection ───────────────────────────────────────────────── */
::selection { background: var(--shub-blue); color: #fff; }

/* ── Mobile ──────────────────────────────────────────────────── */
@media (max-width: 768px) {
  #shub-topbar { padding: 0 12px; gap: 8px; height: 50px; }
  #shub-prog   { top: 50px; }
  .shub-page-title { display: none; }
  .shub-home span  { display: none; }
  .shub-home  { padding: 6px 8px; }
  #shub-btt   { bottom: 80px; right: 12px; width: 36px; height: 36px; font-size: 1rem; }

  body > .header, body > header { margin-top: 50px !important; }
  .header, .toc, .nav-bar { top: 50px !important; }
  .topbar:not(#shub-topbar) { top: 50px !important; }
  .main, .main-content, .content-area { margin-top: 50px !important; }
}
@media (min-width: 769px) { }
</style>"""

# ═══════════════════════════════════════════════════════════════════
#  LIGHT PAGE EXTRAS — applied only to light-bg pages (Nutanix-style)
#  Makes tables, callouts, cards look like the Nutanix guide
# ═══════════════════════════════════════════════════════════════════
LIGHT_EXTRA_CSS = """<style id="shub-light-extras">
/* Light page refinements — matches Nutanix Foundations guide quality */
body {
  background: #F0F4FA !important;
  color: #1A2840 !important;
  font-size: 15px !important;
  line-height: 1.7 !important;
}
p { color: #2D3F5C; line-height: 1.75; }
li { color: #2D3F5C; }
li::marker { color: #4A9FD5; }
a { color: #2E6CC7; }
a:hover { color: #4A9FD5; }

h1 { color: #0B1E3D !important; font-weight: 800 !important; line-height: 1.2 !important; }
h2 { color: #1B4F8A !important; font-weight: 700 !important; padding-bottom: 0.3rem; border-bottom: 2px solid #CBD9EE; }
h3 { color: #00929F !important; font-weight: 700 !important; }
h4 { color: #5A6E8A !important; text-transform: uppercase; letter-spacing: 0.07em; font-size: 0.75rem !important; }

thead th { background: #1B4F8A !important; color: #fff !important; font-weight: 600; font-size: 0.78rem; padding: 0.7rem 0.9rem; }
tbody tr:nth-child(odd)  { background: #fff !important; }
tbody tr:nth-child(even) { background: #F5F8FD !important; }
tbody td { color: #2D3F5C; padding: 0.6rem 0.9rem; border-top: 1px solid #CBD9EE; vertical-align: top; }
tbody td:first-child { font-family: var(--font-head); font-weight: 600; color: #1B4F8A; }

pre, code { background: #0F1E35 !important; color: #79C0FF !important; border-radius: 8px; }
:not(pre) > code { background: #E8EFF8 !important; color: #1B4F8A !important; padding: 0.1em 0.4em; border-radius: 4px; }
</style>"""

# ═══════════════════════════════════════════════════════════════════
#  DARK PAGE EXTRAS — applied to dark-bg pages
#  Keeps dark scheme but boosts readability and adds Nutanix quality
# ═══════════════════════════════════════════════════════════════════
DARK_EXTRA_CSS = """<style id="shub-dark-extras">
/* Dark page refinements — improves readability, keeps dark theme */
body {
  font-size: 15px !important;
  line-height: 1.75 !important;
}

/* Headings: brighter so they stand out on dark bg */
h1 { font-weight: 800 !important; line-height: 1.2 !important; }
h2 { font-weight: 700 !important; line-height: 1.25 !important; }
h3 { font-weight: 600 !important; }

/* Paragraph / answer text: ensure it's readable, not faded */
p, .qa-a p, .body-text, .answer, [class*="answer"] {
  color: #c9d5e8 !important;
  line-height: 1.78 !important;
  font-size: 14.5px !important;
}

/* List items */
li { color: #b8c8dd !important; font-size: 14.5px !important; line-height: 1.65 !important; }

/* Q text — question titles should be clearly readable */
.q-text, .qa-q .q-text, [class*="q-text"],
.topic-title, [class*="topic-title"],
.question, [class*="question-text"] {
  color: #e2ecf8 !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

/* Section / topic headers */
.section-title, [class*="section-title"] { color: #fff !important; font-weight: 700 !important; }
.section-desc,  [class*="section-desc"]  { color: #8fa8c8 !important; }

/* Cards: boost border visibility */
.topic-card, .qa-item, .card, [class*="-card"] {
  border-color: rgba(255,255,255,0.1) !important;
}
.topic-card:hover, .qa-item:hover {
  border-color: rgba(255,255,255,0.22) !important;
}

/* Code blocks — ensure visible on dark bg */
pre, .cmd-block, .code-block, [class*="code-block"], [class*="cmd-block"] {
  background: #080c14 !important;
  border-color: rgba(255,255,255,0.08) !important;
  font-size: 13px !important;
  line-height: 1.65 !important;
  padding: 14px 16px !important;
  border-radius: 8px !important;
}

/* Inline code — readable on dark bg */
:not(pre) > code {
  background: rgba(255,255,255,0.08) !important;
  color: #7dd3b8 !important;
  padding: 0.1em 0.4em !important;
  border-radius: 4px !important;
  font-size: 0.85em !important;
}

/* Tables on dark pages */
thead th {
  font-family: var(--font-head) !important;
  font-weight: 600 !important;
  font-size: 0.8rem !important;
  letter-spacing: 0.03em !important;
  color: #e2ecf8 !important;
}
tbody td {
  color: #b8c8dd !important;
  font-size: 0.88rem !important;
  vertical-align: top !important;
  line-height: 1.55 !important;
}
tbody td:first-child {
  font-family: var(--font-head) !important;
  font-weight: 600 !important;
}

/* Muted/dim text: slightly less faded */
.muted, [class*="muted"], [class*="-dim"],
.subtitle, .section-desc { color: #7a90b0 !important; }

/* Nav tab bar text — readable */
.toc-btn, .nav-item, [class*="toc-btn"],
[class*="tab-btn"], [class*="nav-btn"] {
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.04em !important;
}

/* Info/warn boxes */
.info-box, [class*="info-box"] {
  color: #a8c8e8 !important;
  font-size: 14px !important;
}
.warn-box, [class*="warn-box"] {
  color: #d4b880 !important;
  font-size: 14px !important;
}

/* Step list items */
.step-list li, [class*="step-list"] li { color: #b8c8dd !important; font-size: 14.5px !important; }

/* Footer text */
.footer, footer { color: #5a6e8a !important; font-size: 11px !important; }
</style>"""

# ═══════════════════════════════════════════════════════════════════
#  TOPBAR HTML — same on all pages, injected after <body>
# ═══════════════════════════════════════════════════════════════════
def topbar_html(page_title):
    return f"""
<!-- SHUB-THEME-v2 -->
{SHARED_CSS}
<div id="shub-topbar">
  <a class="shub-logo" href="index.html">Study<span class="shub-logo-dot">Hub</span></a>
  <span class="shub-page-title">{page_title}</span>
  <div class="shub-spacer"></div>
  <a class="shub-home" href="index.html">
    <svg width="11" height="11" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2">
      <path d="M3 9l7-7 7 7M4 8v9a1 1 0 001 1h4v-5h2v5h4a1 1 0 001-1V8"/>
    </svg>
    <span>All Guides</span>
  </a>
</div>
<div id="shub-prog"></div>
<button id="shub-btt" title="Back to top">↑</button>
<script id="shub-chrome-js">
(function(){{
  var prog=document.getElementById('shub-prog');
  var btt=document.getElementById('shub-btt');
  window.addEventListener('scroll',function(){{
    var h=document.documentElement,b=document.body;
    var st=h.scrollTop||b.scrollTop;
    var sh=(h.scrollHeight||b.scrollHeight)-h.clientHeight;
    if(prog) prog.style.width=(sh>0?Math.min(st/sh*100,100):0)+'%';
    if(btt) btt.classList.toggle('vis',st>280);
  }},{{passive:true}});
  if(btt) btt.addEventListener('click',function(){{window.scrollTo({{top:0,behavior:'smooth'}});}});
}})();
</script>
"""

# Font link
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&amp;'
    'family=Syne:wght@400;600;700;800&amp;family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300'
    '&display=swap" rel="stylesheet">'
)

PAGE_TITLES = {
    "ccna study notes.html":                  "CCNA Study Notes",
    "network study reference.html":           "Network Study Reference",
    "linux admin interview studyguide.html":  "Linux Admin Interview Guide",
    "os admin l3 interview prep.html":        "OS Admin L3 Interview Prep",
    "master interview hub.html":              "Master Interview Hub",
    "nutanix foundations guide.html":         "Nutanix Foundations Guide",
    "itil-unix-interview-prep.html":          "ITIL & Unix Interview Prep",
    "rhel study guide.html":                  "RHEL Study Guide",
}

def get_title(fname):
    return PAGE_TITLES.get(fname.lower(), fname.replace(".html","").replace("-"," ").title())

# ═══════════════════════════════════════════════════════════════════
#  APPLY TO ONE FILE
# ═══════════════════════════════════════════════════════════════════
def apply(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    # Remove any v1 theme injection first
    if "<!-- SHUB-THEME-v1 -->" in orig:
        orig = re.sub(r'<!-- SHUB-THEME-v1 -->.*?(?=</style>\s*</head>|<div id="shub-topbar)', '',
                      orig, flags=re.DOTALL)
        orig = re.sub(r'<div id="shub-topbar">.*?</script>\s*\n', '', orig, flags=re.DOTALL)
        orig = re.sub(r'<div id="shub-progress"></div>\s*', '', orig)
        orig = re.sub(r'<button id="shub-btt"[^>]*>.*?</button>\s*', '', orig, flags=re.DOTALL)
        orig = re.sub(r'<style id="shub-theme">.*?</style>\s*', '', orig, flags=re.DOTALL)
        print(f"     {D('removed v1 theme')}")

    if THEME_MARK in orig:
        print(f"  {D('⟳  already v2')}  {D(fname)}")
        return 'skip'

    html = orig
    dark  = is_dark(html)
    title = get_title(fname)

    # 1. Fix/add viewport
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        html = re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',
                      vp, html, flags=re.I)
    else:
        html = re.sub(r'(<head[^>]*>)', r'\1\n  ' + vp, html, count=1, flags=re.I)

    # 2. Replace/add Google Fonts
    html = re.sub(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*/?>',
                  '', html, flags=re.I)
    html = re.sub(r"@import url\(['\"]https://fonts\.googleapis[^)]+\)['\"];?",
                  '', html, flags=re.I)
    html = re.sub(r'(<head[^>]*>)', r'\1\n  ' + FONT_LINK, html, count=1, flags=re.I)

    # 3. Inject topbar + shared CSS after <body>
    topbar = topbar_html(title)
    extra  = DARK_EXTRA_CSS if dark else LIGHT_EXTRA_CSS
    inject = topbar + '\n' + extra + '\n'
    html   = re.sub(r'(<body[^>]*>)', r'\1' + inject, html, count=1, flags=re.I)

    if dry:
        scheme = R('dark') if dark else C('light')
        print(f"  {C('○')}  {fname}  [{scheme}]  title: {title}")
        return 'dry'

    shutil.copy2(path, path + BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    scheme = 'dark' if dark else 'light'
    print(f"  {G('✔')}  {fname}  {D('['+scheme+']')}")
    return 'patched'

def undo(path):
    fname = os.path.basename(path)
    bak   = path + BACKUP_EXT
    if os.path.exists(bak):
        shutil.copy2(bak, path); os.remove(bak)
        print(f"  {G('✔  restored')}  {fname}")
        return 'ok'
    print(f"  {Y('⚠  no backup')}  {fname}")
    return 'skip'

def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    rev  = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(B("  ╔══════════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub Theme Injector v2                      ║"))
    print(B("  ║  Unified fonts + chrome, preserves page colours  ║"))
    print(B("  ╚══════════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('APPLY'))}\n")

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not f.lower().endswith('.bak')
        and not f.lower().endswith('.bak2')
        and f not in SKIP
    )
    if not files:
        print(Y("  No HTML files found.")); sys.exit(0)

    print(f"  {B(str(len(files)))} pages:\n")
    counts = {}
    for fp in files:
        r = undo(fp) if rev else apply(fp, dry)
        counts[r] = counts.get(r, 0) + 1

    print(f"\n  {'─'*50}")
    if rev:
        print(f"  {G('Restored')}: {counts.get('ok',0)}   {Y('No backup')}: {counts.get('skip',0)}")
    elif dry:
        print(f"  {C('Would theme')}: {counts.get('dry',0)}   {D('Skip')}: {counts.get('skip',0)}")
    else:
        print(f"  {G('Themed')}: {counts.get('patched',0)}   {D('Skip')}: {counts.get('skip',0)}")

    if not rev and not dry and counts.get('patched', 0):
        git_msg = 'git commit -m "Apply unified StudyHub theme v2 to all pages"'
        print(f"\n  {B('Push to GitHub:')}")
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")
    print()

if __name__ == '__main__':
    main()
