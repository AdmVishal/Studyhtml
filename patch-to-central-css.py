#!/usr/bin/env python3
"""
patch_to_central_css.py
════════════════════════════════════════════════════════════════════
The correct, permanent fix. Moves ALL styling into one file.

For each HTML page:
  1. Removes every <style> block (inline CSS)
  2. Removes all injected theme/mobile CSS blocks from previous scripts
  3. Removes all old <link> stylesheet references
  4. Removes all Google Fonts @import / <link> tags
  5. Adds ONE <link rel="stylesheet" href="studyhub.css"> in <head>
  6. Adds ONE <link> for Google Fonts in <head>
  7. Injects the StudyHub topbar + progress bar + back-to-top
     as clean inline HTML right after <body>
  8. Preserves ALL HTML content and JavaScript completely untouched

After running this:
  - Every page has zero inline CSS
  - All styling comes from studyhub.css
  - Changing one line in studyhub.css updates ALL pages instantly
  - The Nutanix page keeps its own working sidebar toggle JS

Usage:
  cd ~/Studyhtml
  python3 patch_to_central_css.py            # apply to all pages
  python3 patch_to_central_css.py --dry-run  # preview
  python3 patch_to_central_css.py --undo     # restore .bak4 backups
"""

import os, sys, re, shutil

BACKUP_EXT = ".bak4"
MARKER     = "<!-- CENTRAL-CSS-v1 -->"
CSS_FILE   = "studyhub.css"
SKIP       = {"index.html"}   # index has its own standalone style

def c(t,code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t,"0;32");  Y = lambda t: c(t,"0;33")
R = lambda t: c(t,"0;31");  C = lambda t: c(t,"0;36")
B = lambda t: c(t,"1;37");  D = lambda t: c(t,"0;90")

# ── Page titles for topbar ──────────────────────────────────────
TITLES = {
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
    return TITLES.get(fname.lower(),
           fname.replace(".html","").replace("-"," ").title())

# ── StudyHub topbar HTML (goes right after <body>) ──────────────
def make_topbar(title):
    safe = title.replace('"', '&quot;')
    return f"""<!-- CENTRAL-CSS-v1 -->
<div id="shub-topbar">
  <a class="shub-logo" href="index.html">Study<span>Hub</span></a>
  <span class="shub-title">{safe}</span>
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
<script id="shub-chrome">
(function(){{
  var prog = document.getElementById('shub-prog');
  var btt  = document.getElementById('shub-btt');
  window.addEventListener('scroll', function() {{
    var h  = document.documentElement;
    var st = h.scrollTop || document.body.scrollTop;
    var sh = (h.scrollHeight || document.body.scrollHeight) - h.clientHeight;
    if (prog) prog.style.width = (sh > 0 ? Math.min(st / sh * 100, 100) : 0) + '%';
    if (btt)  {{ btt.classList.toggle('vis', st > 280); }}
  }}, {{ passive: true }});
  if (btt) btt.addEventListener('click', function() {{
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }});
}})();
</script>"""

# ── What to put in <head> ───────────────────────────────────────
HEAD_LINKS = """\
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="studyhub.css">"""

# ── Strip all previous styling ──────────────────────────────────
def clean(html):
    """Remove ALL <style> blocks and old injected elements."""

    # 1. Remove every <style>…</style> block (all inline CSS)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html,
                  flags=re.DOTALL | re.I)

    # 2. Remove all Google Fonts links and any old CSS links
    html = re.sub(
        r'<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com|'
        r'mobile\.css|studyhub\.css|patch\.css)[^>]*/?>',
        '', html, flags=re.I)

    # 3. Remove @import font urls that may be inside scripts or leftover
    html = re.sub(
        r"@import url\(['\"]https://fonts\.googleapis[^)]+\)['\"];?\s*",
        '', html, flags=re.I)

    # 4. Remove all previously injected topbar/chrome elements
    OLD_IDS = [
        "shub-topbar", "shub-prog", "shub-btt", "shub-progress",
        "shub-chrome", "shub-chrome-js", "shub-theme-js",
        "shub-back",
    ]
    for eid in OLD_IDS:
        # Remove full elements with children
        html = re.sub(
            r'<(?:div|button|a|script)\b[^>]*\bid=["\']' + re.escape(eid)
            + r'["\'][^>]*>.*?</(?:div|button|a|script)>',
            '', html, flags=re.DOTALL | re.I)
        # Remove self-closing or short open tags
        html = re.sub(
            r'<[^>]+\bid=["\']' + re.escape(eid) + r'["\'][^>]*>',
            '', html, flags=re.I)

    # 5. Remove old comment markers
    for marker in [
        "<!-- CENTRAL-CSS-v1 -->", "<!-- SHUB-THEME-v1 -->",
        "<!-- SHUB-THEME-v2 -->", "<!-- RESTYLE-v1 -->",
        "<!-- SHN-v3 -->", "<!-- CCNA-MOBILE-FIX -->",
        "<!-- STUDYHUB-MOBILE-v4 -->", "<!-- STUDYHUB-MASTER-v1 -->",
        "<!-- NET-MOBILE-FIX-v1 -->", "<!-- NET-MOB-v2 -->",
        "<!-- NM-FIX-CLEAN -->", "<!-- NET-MOB -->",
        "<!-- RHEL-MOB -->", "<!-- ITIL-MOB -->",
    ]:
        html = html.replace(marker, "")

    # 6. Clean up excessive blank lines
    html = re.sub(r'\n{4,}', '\n\n', html)
    return html

# ── Main patch function ─────────────────────────────────────────
def patch(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    if MARKER in orig:
        print(f"  {D('⟳  already done')}  {D(fname)}")
        return 'skip'

    # Count inline styles before cleaning
    style_count = len(re.findall(r'<style[^>]*>', orig, re.I))

    # 1. Strip everything
    html = clean(orig)

    # 2. Fix / add viewport meta
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        html = re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',
                      vp, html, flags=re.I)
    else:
        html = re.sub(r'(<head[^>]*>)', r'\1\n  ' + vp,
                      html, count=1, flags=re.I)

    # 3. Inject font + CSS link into <head>
    html = re.sub(r'(</head>)', HEAD_LINKS + r'\n\1',
                  html, count=1, flags=re.I)

    # 4. Inject topbar after <body>
    title  = get_title(fname)
    topbar = make_topbar(title)
    html   = re.sub(r'(<body[^>]*>)', r'\1\n' + topbar + '\n',
                    html, count=1, flags=re.I)

    if dry:
        removed_kb = (len(orig) - len(html)) // 1024
        print(f"  {C('○')}  {fname}")
        print(f"     {D(str(style_count))} style blocks removed · "
              f"{D('~' + str(removed_kb) + ' KB')} smaller")
        return 'dry'

    shutil.copy2(path, path + BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  {G('✔')}  {fname}  {D('[' + str(style_count) + ' style blocks removed]')}")
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

# ── Main ────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    rev  = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(B("  ╔══════════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub — Patch to Central CSS                 ║"))
    print(B("  ║  Strips all inline CSS → links to studyhub.css   ║"))
    print(B("  ╚══════════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('APPLY'))}\n")

    # Verify studyhub.css exists
    css_path = os.path.join(wd, CSS_FILE)
    if not rev and not os.path.exists(css_path):
        print(R(f"  ✗  {CSS_FILE} not found in {wd}"))
        print(D("     Copy studyhub.css into your Studyhtml/ folder first."))
        sys.exit(1)

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not any(f.lower().endswith(e)
                    for e in ('.bak','.bak2','.bak3','.bak4'))
        and f not in SKIP
    )
    if not files:
        print(Y("  No HTML files found.")); sys.exit(0)

    print(f"  {B(str(len(files)))} pages:\n")
    counts = {}
    for fp in files:
        r = undo(fp) if rev else patch(fp, dry)
        counts[r] = counts.get(r, 0) + 1

    print(f"\n  {'─'*50}")
    if rev:
        print(f"  {G('Restored')}: {counts.get('ok',0)}  "
              f"{Y('No backup')}: {counts.get('skip',0)}")
    elif dry:
        print(f"  {C('Would patch')}: {counts.get('dry',0)}  "
              f"{D('Already done')}: {counts.get('skip',0)}")
    else:
        print(f"  {G('Patched')}: {counts.get('patched',0)}  "
              f"{D('Already done')}: {counts.get('skip',0)}")

    if not rev and not dry and counts.get('patched', 0):
        git_msg = 'git commit -m "Move all pages to central studyhub.css"'
        print(f"\n  {B('Push to GitHub:')}")
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")

    print()

if __name__ == '__main__':
    main()
