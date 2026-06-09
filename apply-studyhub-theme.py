#!/usr/bin/env python3
"""
apply_studyhub_theme.py
═══════════════════════════════════════════════════════════════════════
Applies the Nutanix Foundations design system uniformly across all
StudyHub pages so they look like one coherent website.

Design system extracted from Nutanix Foundations Guide.html:
  Palette  : Navy #0B1E3D / Blue #1B4F8A / Accent #F0A500 / BG #F0F4FA
  Fonts    : Syne (headings) · DM Sans (body) · JetBrains Mono (code)
  Topbar   : Fixed, navy, 60px, accent bottom border
  Sidebar  : Fixed, navy, 280px, scroll
  Content  : Body text 15px/1.7, headings blue, sections with gradient dividers
  Cards    : White surface, blue shadow, 10px radius
  Code     : Dark #0F1E35 background, JetBrains Mono

What this script does PER PAGE:
  1. Replaces the Google Fonts <link> with the exact Nutanix font stack
  2. Injects a <style id="shub-theme"> block with:
       • All CSS variables (colours, fonts, spacing)
       • Topbar, sidebar, content, card, table, code, callout styles
       • Overrides the page's own conflicting styles
  3. Injects a shared <header class="topbar"> to replace each page's own
     header with the unified StudyHub brand bar
  4. Adds back-to-top button, progress bar
  5. Leaves ALL page content, JS, and functionality untouched
  6. Mobile fix (our existing patches) is preserved

Usage:
  cd ~/Studyhtml
  python3 apply_studyhub_theme.py            # apply to all pages
  python3 apply_studyhub_theme.py --dry-run  # preview
  python3 apply_studyhub_theme.py --undo     # restore backups
"""

import os, sys, re, shutil

BACKUP_EXT  = ".bak2"        # separate backup slot from mobile patches
THEME_MARK  = "<!-- SHUB-THEME-v1 -->"
SKIP        = {"index.html"}

def c(t,code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t,"0;32");  Y = lambda t: c(t,"0;33")
R = lambda t: c(t,"0;31");  C = lambda t: c(t,"0;36")
B = lambda t: c(t,"1;37");  D = lambda t: c(t,"0;90")

# ═══════════════════════════════════════════════════════════════════
#  THE SHARED THEME CSS — matches Nutanix guide exactly
# ═══════════════════════════════════════════════════════════════════
THEME_CSS = """<style id="shub-theme">
/* ════════════════════════════════════════════════════════════════
   StudyHub Unified Theme — based on Nutanix Foundations Guide
   Injected by apply_studyhub_theme.py
════════════════════════════════════════════════════════════════ */

/* ── Design Tokens ──────────────────────────────────────────── */
:root {
  --navy:      #0B1E3D;
  --blue:      #1B4F8A;
  --mid:       #2E6CC7;
  --sky:       #4A9FD5;
  --teal:      #00929F;
  --teal-l:    #E0F6F8;
  --accent:    #F0A500;
  --red:       #C0392B;
  --red-l:     #FDECEA;
  --green:     #1A7340;
  --green-l:   #E8F5EE;
  --bg:        #F0F4FA;
  --surface:   #FFFFFF;
  --border:    #CBD9EE;
  --text:      #1A2840;
  --muted:     #5A6E8A;
  --code-bg:   #0F1E35;
  --font-head: 'Syne', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

/* ── Reset & Base ────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html { scroll-behavior: smooth; -webkit-tap-highlight-color: transparent; }

body {
  font-family: var(--font-body) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
  font-size: 15px !important;
  line-height: 1.7 !important;
}

/* ── Unified Topbar ──────────────────────────────────────────── */
#shub-topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 1000;
  height: 60px;
  background: var(--navy);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 1rem;
  border-bottom: 2px solid var(--blue);
  box-shadow: 0 2px 20px rgba(0,0,0,0.4);
}

.shub-logo {
  font-family: var(--font-head);
  font-weight: 800;
  font-size: 1.05rem;
  color: #fff;
  letter-spacing: 0.04em;
  text-decoration: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.shub-logo-dot { color: var(--accent); }

.shub-topbar-title {
  font-size: 0.75rem;
  color: #7B9AC8;
  font-weight: 300;
  margin-left: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.shub-topbar-spacer { flex: 1; }

.shub-home-link {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.9rem;
  border-radius: 7px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  color: #8AAED6;
  font-size: 0.75rem;
  text-decoration: none;
  font-family: var(--font-body);
  white-space: nowrap;
  transition: background 0.15s;
}
.shub-home-link:hover { background: rgba(255,255,255,0.13); color: #fff; }

/* ── Progress Bar ────────────────────────────────────────────── */
#shub-progress {
  position: fixed;
  top: 60px; left: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--sky));
  width: 0%;
  z-index: 1001;
  transition: width 0.1s linear;
}

/* ── Back to Top ─────────────────────────────────────────────── */
#shub-btt {
  position: fixed;
  bottom: 2rem; right: 2rem;
  width: 44px; height: 44px;
  background: var(--blue);
  color: #fff;
  border: none;
  border-radius: 50%;
  font-size: 1.2rem;
  cursor: pointer;
  z-index: 900;
  display: none;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(27,79,138,0.4);
  transition: background 0.15s, transform 0.15s;
}
#shub-btt:hover { background: var(--mid); transform: translateY(-2px); }
#shub-btt.visible { display: flex; }

/* ── Push content below fixed topbar ───────────────────────── */
/* Each page layout gets nudged to account for the 60px topbar */
body > *:not(#shub-topbar):not(#shub-progress):not(#shub-btt):not(script):not(style) {
  /* Individual page layouts override this via their own selectors */
}

/* ── HEADINGS — unified style ───────────────────────────────── */
h1:not(.shub-logo):not([class*="cover"]):not([class*="logo"]) {
  font-family: var(--font-head) !important;
  color: var(--navy) !important;
  font-weight: 800 !important;
  line-height: 1.2 !important;
}
h2 {
  font-family: var(--font-head) !important;
  color: var(--blue) !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
}
h3 {
  font-family: var(--font-head) !important;
  color: var(--teal) !important;
  font-weight: 700 !important;
}
h4 {
  font-family: var(--font-body) !important;
  color: var(--muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
}

/* ── Paragraph text ──────────────────────────────────────────── */
p { color: #2D3F5C; line-height: 1.75; margin-bottom: 0.8rem; }
li { color: #2D3F5C; line-height: 1.65; font-size: 0.9rem; }
li::marker { color: var(--sky); }

/* ── Links ───────────────────────────────────────────────────── */
a { color: var(--mid); }
a:hover { color: var(--sky); }

/* ── Code ────────────────────────────────────────────────────── */
pre, .code-block, [class*="code-block"], [class*="cmd-block"] {
  background: var(--code-bg) !important;
  border-radius: 8px !important;
  padding: 1rem !important;
  overflow-x: auto !important;
  font-family: var(--font-mono) !important;
  font-size: 0.78rem !important;
  color: #79C0FF !important;
  line-height: 1.6 !important;
  margin: 0.75rem 0 1.25rem !important;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2) !important;
}
code, kbd {
  font-family: var(--font-mono) !important;
  font-size: 0.82em !important;
}
:not(pre) > code {
  background: #E8EFF8 !important;
  color: var(--blue) !important;
  padding: 0.1em 0.4em !important;
  border-radius: 4px !important;
  font-size: 0.82em !important;
}

/* ── Tables ──────────────────────────────────────────────────── */
table {
  width: 100%;
  border-collapse: collapse;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 8px rgba(27,79,138,0.08);
  font-size: 0.85rem;
  margin: 0.75rem 0 1.5rem;
}
thead tr { background: var(--blue); }
thead th {
  padding: 0.7rem 0.9rem;
  color: #fff !important;
  font-family: var(--font-head) !important;
  font-weight: 600;
  text-align: left;
  font-size: 0.78rem;
  letter-spacing: 0.03em;
}
tbody tr:nth-child(odd)  { background: var(--surface); }
tbody tr:nth-child(even) { background: #F5F8FD; }
tbody td {
  padding: 0.6rem 0.9rem;
  color: #2D3F5C;
  vertical-align: top;
  line-height: 1.5;
  border-top: 1px solid var(--border);
}
tbody td:first-child {
  font-family: var(--font-head);
  font-weight: 600;
  color: var(--blue);
}

/* ── Cards / panels ──────────────────────────────────────────── */
.card, [class*="-card"]:not([class*="guide-card"]),
.process-card, .topic-card, .qa-item, .step-card {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 1.2rem 1.4rem !important;
  box-shadow: 0 2px 12px rgba(27,79,138,0.07) !important;
  margin-bottom: 1rem !important;
}

/* ── Callout / note blocks ───────────────────────────────────── */
.callout, .note, [class*="callout"], .tip, .warning {
  border-radius: 10px !important;
  padding: 1rem 1.2rem !important;
  margin: 1rem 0 1.5rem !important;
  font-size: 0.88rem !important;
  line-height: 1.6 !important;
}
.callout.info, .note, .tip {
  background: var(--teal-l) !important;
  border-left: 4px solid var(--teal) !important;
  color: #1A4848 !important;
}
.callout.warning, .warning {
  background: var(--red-l) !important;
  border-left: 4px solid var(--red) !important;
  color: #5A1010 !important;
}
.callout.success {
  background: var(--green-l) !important;
  border-left: 4px solid var(--green) !important;
  color: #0D3820 !important;
}

/* ── Section header banners ──────────────────────────────────── */
.section-divider, [class*="section-header"],
[class*="topic-header"], [class*="process-header"] {
  background: linear-gradient(90deg, var(--blue), var(--mid)) !important;
  border-radius: 10px !important;
  padding: 1rem 1.5rem !important;
  margin-bottom: 1.5rem !important;
  color: #fff !important;
}
.section-divider h2, [class*="section-header"] h2 {
  color: #fff !important;
  font-size: 1.05rem !important;
  margin: 0 !important;
  border: none !important;
}

/* ── Badges / tags / pills ───────────────────────────────────── */
.badge, .tag, [class*="-badge"], [class*="-tag"]:not([class*="guide-tag"]) {
  font-family: var(--font-mono) !important;
  font-size: 0.72rem !important;
  padding: 0.2rem 0.6rem !important;
  border-radius: 5px !important;
}

/* ── Scrollbars ──────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ── Selection ───────────────────────────────────────────────── */
::selection { background: var(--blue); color: #fff; }

/* ── Mobile: topbar compact ──────────────────────────────────── */
@media (max-width: 768px) {
  #shub-topbar { padding: 0 12px; gap: 8px; height: 54px; }
  #shub-progress { top: 54px; }
  .shub-topbar-title { display: none; }
  .shub-home-link span { display: none; }
  .shub-home-link { padding: 0.4rem 0.6rem; }
  #shub-btt { bottom: 90px; right: 14px; width: 38px; height: 38px; font-size: 1rem; }
}
</style>"""

# ═══════════════════════════════════════════════════════════════════
#  TOPBAR HTML — injected right after <body>
#  Page title is passed in per-page
# ═══════════════════════════════════════════════════════════════════
def topbar_html(page_title):
    return f"""
<!-- SHUB-THEME-v1 -->
{THEME_CSS}
<div id="shub-topbar">
  <a class="shub-logo" href="index.html">
    Study<span class="shub-logo-dot">Hub</span>
  </a>
  <span class="shub-topbar-title">{page_title}</span>
  <div class="shub-topbar-spacer"></div>
  <a class="shub-home-link" href="index.html">
    <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M3 9l7-7 7 7M4 8v9a1 1 0 001 1h4v-5h2v5h4a1 1 0 001-1V8"/>
    </svg>
    <span>All Guides</span>
  </a>
</div>
<div id="shub-progress"></div>
<button id="shub-btt" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="Back to top">↑</button>
<script id="shub-theme-js">
(function(){{
  /* Progress bar */
  var bar = document.getElementById('shub-progress');
  window.addEventListener('scroll', function(){{
    var h = document.documentElement;
    var pct = (h.scrollTop || document.body.scrollTop) /
              ((h.scrollHeight || document.body.scrollHeight) - h.clientHeight) * 100;
    if(bar) bar.style.width = Math.min(pct,100) + '%';
    var btt = document.getElementById('shub-btt');
    if(btt) btt.classList.toggle('visible', (h.scrollTop||document.body.scrollTop) > 300);
  }}, {{passive:true}});
}})();
</script>
"""

# ═══════════════════════════════════════════════════════════════════
#  FONT LINK — replace any existing Google Fonts with the exact stack
# ═══════════════════════════════════════════════════════════════════
FONT_LINK = '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">'
PRECONNECT = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'

# Page titles for topbar
PAGE_TITLES = {
    "ccna study notes.html":            "CCNA Study Notes",
    "network study reference.html":     "Network Study Reference",
    "linux admin interview studyguide.html": "Linux Admin Interview Guide",
    "os admin l3 interview prep.html":  "OS Admin L3 Interview Prep",
    "master interview hub.html":        "Master Interview Hub",
    "nutanix foundations guide.html":   "Nutanix Foundations Guide",
    "itil-unix-interview-prep.html":    "ITIL & Unix Interview Prep",
    "rhel study guide.html":            "RHEL Study Guide",
}

def get_title(fname):
    return PAGE_TITLES.get(fname.lower(), fname.replace(".html","").replace("-"," ").title())

# ═══════════════════════════════════════════════════════════════════
#  APPLY THEME TO ONE FILE
# ═══════════════════════════════════════════════════════════════════
def apply(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    if THEME_MARK in orig:
        print(f"  {D('⟳  already themed')}  {D(fname)}")
        return 'skip'

    html = orig

    # 1. Fix/add viewport meta
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        html = re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',
                      vp, html, flags=re.I)
    else:
        html = re.sub(r'(<head[^>]*>)', r'\1\n  ' + vp, html, count=1, flags=re.I)

    # 2. Replace Google Fonts link (or add if missing)
    if re.search(r'fonts.googleapis.com', html, re.I):
        # Remove all existing font links
        html = re.sub(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*/?>', '',
                      html, flags=re.I)
    # Inject standardised font links in <head>
    html = re.sub(r'(<head[^>]*>)',
                  r'\1\n  ' + PRECONNECT + '\n  ' + FONT_LINK,
                  html, count=1, flags=re.I)

    # 3. Inject topbar + theme CSS right after <body>
    title   = get_title(fname)
    topbar  = topbar_html(title)
    html    = re.sub(r'(<body[^>]*>)', r'\1' + topbar,
                     html, count=1, flags=re.I)

    if dry:
        stripped = len(orig)
        print(f"  {C('○')}  {fname}")
        print(f"     {D('title: ' + title)}")
        return 'dry'

    shutil.copy2(path, path + BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  {G('✔')}  {fname}")
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

# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    rev  = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(B("  ╔══════════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub Unified Theme Injector                 ║"))
    print(B("  ║  Applies Nutanix design system to all pages      ║"))
    print(B("  ╚══════════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('APPLY'))}\n")

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not f.endswith('.bak')
        and not f.endswith('.bak2')
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
        print(f"  {G('Restored')}: {counts.get('ok',0)}  {Y('No backup')}: {counts.get('skip',0)}")
    elif dry:
        print(f"  {C('Would theme')}: {counts.get('dry',0)}  {D('Already done')}: {counts.get('skip',0)}")
    else:
        print(f"  {G('Themed')}: {counts.get('patched',0)}  {D('Already done')}: {counts.get('skip',0)}")

    if not rev and not dry and counts.get('patched', 0):
        git_msg = 'git commit -m "Apply unified StudyHub theme to all pages"'
        print(f"\n  {B('Push to GitHub:')}")
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")
    print()

if __name__ == '__main__':
    main()
