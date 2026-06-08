#!/usr/bin/env python3
"""
StudyHub — Mobile Patch  v4  (exact class-targeted)
────────────────────────────────────────────────────
Reads the actual CSS from each page and applies a
precision-targeted mobile fix using EXACT class names.

Usage:
  python3 patch.py            # patch all pages
  python3 patch.py --dry-run  # preview, no changes
  python3 patch.py --undo     # restore .bak backups
"""
import os, sys, re, shutil

BACKUP_EXT   = ".bak"
PATCH_MARKER = "<!-- STUDYHUB-MOBILE-v4 -->"
SKIP         = {"index.html"}

def c(t, code): return f"\033[{code}m{t}\033[0m"
green  = lambda t: c(t,"0;32")
yellow = lambda t: c(t,"0;33")
red    = lambda t: c(t,"0;31")
cyan   = lambda t: c(t,"0;36")
bold   = lambda t: c(t,"1;37")
dim    = lambda t: c(t,"0;90")

# ── Detect layout type from actual CSS in the file ───────────────
def detect(html):
    info = {}
    # Extract full style block
    style = re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL|re.I)
    css = style.group(1) if style else ''

    # CCNA / Network / Linux / RHEL / Master pages:
    # .main { display: flex } with .sidebar (240px) + .content (flex:1)
    info['has_flex_main']    = bool(re.search(r'\.main\s*\{[^}]*display\s*:\s*flex', css))
    info['has_sidebar_240']  = bool(re.search(r'\.sidebar\s*\{[^}]*width\s*:\s*240px', css))
    info['has_content_flex'] = bool(re.search(r'\.content\s*\{[^}]*flex\s*:\s*1', css))
    info['has_cat_nav']      = '.cat-nav' in css
    info['has_topic_btn']    = '.topic-btn' in css

    # ITIL page: uses .app-grid or .container with left-nav + content
    info['has_app_grid']     = '.app-grid' in css or 'grid-template-columns' in css
    info['has_left_nav']     = '.left-nav' in css or '.nav-panel' in css
    info['has_process_grid'] = '.process-grid' in css or '.cmd-grid' in css

    # Nutanix guide: has .sidebar + toggleSidebar()
    info['has_toggle']       = 'toggleSidebar' in html

    # Pages with fixed sidebar height = 100vh
    info['has_vh_layout']    = bool(re.search(r'height\s*:\s*calc\(100vh', css))

    # Lifecycle / flow arrows
    info['has_lifecycle']    = '.lifecycle' in css or '.workflow' in css

    # Tab nav
    info['has_tab_nav']      = '.cat-nav' in css or '.tab-nav' in css or '.filter-bar' in css

    return info

# ── Build the exact mobile CSS block for this page ───────────────
def build_css(html, info):
    blocks = []

    # ── A. CCNA / Network / Linux / RHEL style pages ─────────────
    # Layout: header (sticky) → .main (flex) → .sidebar (240px) | .content (flex:1)
    if info['has_flex_main'] and info['has_sidebar_240'] and not info['has_toggle']:
        blocks.append("""
  /* ── Split-panel layout: stack vertically on mobile ── */
  .main {
    display: block !important;
    height: auto !important;
    overflow: visible !important;
  }

  /* Hide sidebar — accessed via ≡ Topics button (added by JS) */
  .sidebar {
    display: none !important;
    position: fixed !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    z-index: 9000 !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 56px 0 40px !important;
    background: var(--surface, #111827) !important;
  }

  /* Sidebar open state */
  body.sidebar-open .sidebar {
    display: block !important;
  }

  /* Content fills full width */
  .content {
    width: 100% !important;
    max-width: 100% !important;
    padding: 20px 14px 40px !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
    height: auto !important;
    overflow-y: visible !important;
  }

  /* Tab/category nav: horizontal scroll */
  .cat-nav {
    display: flex !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    flex-wrap: nowrap !important;
    gap: 2px !important;
    scrollbar-width: none !important;
    padding-bottom: 2px !important;
  }
  .cat-nav::-webkit-scrollbar { display: none !important; }
  .cat-btn {
    flex-shrink: 0 !important;
    font-size: 11px !important;
    padding: 7px 10px !important;
  }

  /* Header: prevent overflow */
  header {
    padding: 16px 14px 0 !important;
    position: sticky !important;
    top: 0 !important;
  }
  .header-top {
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  .subtitle { display: none !important; }

  /* ≡ Topics floating button (injected by JS) */
  #mob-topics-btn {
    display: flex !important;
    position: fixed !important;
    bottom: 18px !important; right: 16px !important;
    z-index: 9500 !important;
    background: var(--accent, #00c9ff) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 11px 18px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    font-family: var(--font, system-ui) !important;
    align-items: center !important;
    gap: 7px !important;
    cursor: pointer !important;
    box-shadow: 0 4px 20px rgba(0,0,0,.5) !important;
    letter-spacing: .02em !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* Close button (inside open sidebar) */
  #mob-sidebar-close {
    display: none;
    position: fixed !important;
    top: 10px !important; right: 12px !important;
    z-index: 9600 !important;
    background: rgba(255,255,255,.12) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    width: 40px !important; height: 40px !important;
    font-size: 18px !important;
    cursor: pointer !important;
    align-items: center !important;
    justify-content: center !important;
  }
  body.sidebar-open #mob-sidebar-close { display: flex !important; }

  /* Overlay when sidebar open */
  #mob-overlay {
    display: none;
    position: fixed !important;
    inset: 0 !important;
    background: rgba(0,0,0,.65) !important;
    z-index: 8999 !important;
  }
  body.sidebar-open #mob-overlay { display: block !important; }
""")

    # ── B. Nutanix guide (already has own sidebar toggle) ────────
    if info['has_toggle']:
        blocks.append("""
  /* Nutanix guide: sidebar already toggleable — just fix layout */
  .main {
    margin-left: 0 !important;
    max-width: 100vw !important;
    padding: 1rem 14px 3rem !important;
  }
  .progress-bar { left: 0 !important; }
  .topbar-search { display: none !important; }
  .cover { padding: 20px 14px !important; }
  .cover h1 { font-size: clamp(1.8rem, 8vw, 2.8rem) !important; }
  .cheatsheet-grid { grid-template-columns: 1fr !important; }
  .card-grid { grid-template-columns: 1fr !important; }
""")

    # ── C. ITIL page specific ─────────────────────────────────────
    if info['has_app_grid']:
        blocks.append("""
  /* ITIL app-grid: stack nav + content vertically */
  .app-grid, [class*="app-grid"] {
    display: block !important;
    grid-template-columns: 1fr !important;
  }
  .left-nav, .nav-panel, [class*="left-nav"] {
    display: none !important;
  }
  .main-content, .content-area, [class*="main-content"] {
    width: 100% !important;
    padding: 16px 14px !important;
    box-sizing: border-box !important;
  }
  .process-grid, [class*="process-grid"],
  .cmd-grid, [class*="cmd-grid"] {
    grid-template-columns: 1fr !important;
    gap: 10px !important;
  }
""")

    # ── D. Lifecycle / flow arrows ────────────────────────────────
    if info['has_lifecycle']:
        blocks.append("""
  /* Lifecycle arrows: wrap on mobile */
  .lifecycle, .workflow, [class*="lifecycle"], [class*="workflow"] {
    flex-wrap: wrap !important;
    gap: 6px !important;
  }
  .lifecycle-step, [class*="lifecycle-step"],
  .flow-step, [class*="flow-step"] {
    flex-shrink: 0 !important;
    font-size: 11px !important;
    padding: 4px 8px !important;
  }
""")

    # ── E. Universal fixes for ALL pages ─────────────────────────
    blocks.append("""
  /* Universal: tables */
  table {
    display: block !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    width: 100% !important;
    max-width: 100% !important;
    font-size: 12px !important;
  }
  th { white-space: nowrap; font-size: 11px !important; }
  td { font-size: 12px !important; }

  /* Universal: code */
  pre, code, [class*="code-block"], [class*="cmd-block"] {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    font-size: 11px !important;
    max-width: 100% !important;
    white-space: pre !important;
  }

  /* Universal: headings */
  h1 { font-size: clamp(1.5rem, 7vw, 2rem) !important; line-height: 1.2 !important; }
  h2 { font-size: clamp(1rem, 5vw, 1.35rem) !important; }
  h3 { font-size: clamp(0.9rem, 4vw, 1.05rem) !important; }

  /* Universal: search input */
  .search-wrap { max-width: 100% !important; }
  .search-wrap input { font-size: 14px !important; }

  /* Universal: body overflow */
  body { overflow-x: hidden !important; }
""")

    if not blocks:
        return ''

    inner = '\n'.join(blocks)
    return f"\n<style id='shm-v4'>\n@media (max-width: 768px) {{{inner}}}\n@media (min-width: 769px) {{\n  #mob-topics-btn {{ display: none !important; }}\n  #mob-sidebar-close {{ display: none !important; }}\n  #mob-overlay {{ display: none !important; }}\n}}\n</style>"

# ── Build JS for pages with the split sidebar layout ─────────────
SPLIT_JS = """
<script id='shm-js'>
(function(){
  if(window.innerWidth > 768) return;
  var sb = document.querySelector('.sidebar');
  if(!sb) return;

  // Overlay
  var ov = document.createElement('div');
  ov.id = 'mob-overlay';
  document.body.appendChild(ov);

  // Close button inside sidebar
  var cb = document.createElement('button');
  cb.id = 'mob-sidebar-close';
  cb.innerHTML = '&#10005;';
  cb.setAttribute('aria-label','Close topics');
  document.body.appendChild(cb);

  // Topics button (bottom-right)
  var btn = document.createElement('button');
  btn.id = 'mob-topics-btn';
  btn.innerHTML = '&#9776; Topics';
  btn.setAttribute('aria-label','Show topics');
  document.body.appendChild(btn);

  function open(){
    document.body.classList.add('sidebar-open');
    document.body.style.overflow = 'hidden';
    btn.innerHTML = '&#10005; Close';
  }
  function close(){
    document.body.classList.remove('sidebar-open');
    document.body.style.overflow = '';
    btn.innerHTML = '&#9776; Topics';
  }

  btn.addEventListener('click', function(){
    document.body.classList.contains('sidebar-open') ? close() : open();
  });
  cb.addEventListener('click', close);
  ov.addEventListener('click', close);

  // Close when topic button is clicked (content loads)
  sb.querySelectorAll('.topic-btn, button, a').forEach(function(el){
    el.addEventListener('click', function(){ setTimeout(close, 200); });
  });

  document.addEventListener('keydown', function(e){
    if(e.key==='Escape') close();
  });
})();
</script>"""

# ── Main patch logic ──────────────────────────────────────────────
def patch(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    if PATCH_MARKER in orig:
        print(f"  {dim('⟳  already patched')}   {dim(fname)}")
        return 'already'

    html = orig
    info = detect(html)

    # 1. Viewport meta
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        html = re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',
                      vp, html, flags=re.I)
    else:
        html = re.sub(r'(<head[^>]*>)', r'\1\n  '+vp, html, count=1, flags=re.I)

    # 2. Patch marker + targeted CSS before </head>
    css_block = build_css(html, info)
    marker_line = f"\n  {PATCH_MARKER}"
    inject_head = css_block + marker_line
    html = re.sub(r'(</head>)', inject_head+r'\n\1', html, count=1, flags=re.I)

    # 3. JS for split-sidebar pages (not Nutanix which has its own)
    if info['has_sidebar_240'] and not info['has_toggle']:
        html = re.sub(r'(</body>)', SPLIT_JS+r'\n\1', html, count=1, flags=re.I)
        nav_note = cyan('+ sidebar JS')
    elif info['has_toggle']:
        nav_note = dim('own nav kept')
    else:
        nav_note = dim('no sidebar')

    if html == orig:
        print(f"  {yellow('⚠  no change')}        {fname}")
        return 'skip'

    if dry:
        has = lambda k: '✓' if info.get(k) else '·'
        flags = f"flex={has('has_flex_main')} sb240={has('has_sidebar_240')} toggle={has('has_toggle')}"
        print(f"  {cyan('○  would patch')}     {fname}")
        print(f"     {dim(flags)}  [{nav_note}]")
        return 'dry'

    shutil.copy2(path, path+BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  {green('✔  patched')}         {fname}  [{nav_note}]")
    return 'patched'

def undo(path):
    fname = os.path.basename(path)
    bak = path+BACKUP_EXT
    if os.path.exists(bak):
        shutil.copy2(bak, path); os.remove(bak)
        print(f"  {green('✔  restored')}        {fname}")
        return 'ok'
    print(f"  {yellow('⚠  no backup')}       {fname}")
    return 'skip'

def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    rev  = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(bold('  ╔════════════════════════════════════════╗'))
    print(bold('  ║  StudyHub Mobile Patch  v4             ║'))
    print(bold('  ╚════════════════════════════════════════╝'))
    print(f'\n  Dir : {cyan(wd)}')
    print(f'  Mode: {yellow("DRY RUN") if dry else (red("UNDO") if rev else green("PATCH"))}\n')

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html') and f not in SKIP
    )
    if not files:
        print(yellow('  ⚠  No HTML files.\n')); sys.exit(0)

    print(f'  {bold(str(len(files)))} file(s):\n')
    counts = {}
    for fp in files:
        r = undo(fp) if rev else patch(fp, dry)
        counts[r] = counts.get(r,0)+1

    print(f'\n  {"─"*44}')
    if rev:
        print(f'  {green("Restored")}: {counts.get("ok",0)}  {yellow("No backup")}: {counts.get("skip",0)}')
    elif dry:
        print(f'  {cyan("Would patch")}: {counts.get("dry",0)}  {dim("Already OK")}: {counts.get("already",0)}')
    else:
        print(f'  {green("Patched")}: {counts.get("patched",0)}  {dim("Already OK")}: {counts.get("already",0)}  {yellow("Skipped")}: {counts.get("skip",0)}')

    if not rev and not dry and counts.get('patched',0) > 0:
        git_msg = 'git commit -m "Mobile patch v4 — exact class targeting"'
        print(f'\n  {green("✔  Done! Push:")}')
        print(f'    {cyan("git add .")}')
        print(f'    {cyan(git_msg)}')
        print(f'    {cyan("git push")}')
    print()

if __name__ == '__main__':
    main()
