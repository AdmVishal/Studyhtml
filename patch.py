#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║        StudyHub — Mobile Patch Injector  (patch.py v2)      ║
║                                                              ║
║  For each HTML page:                                         ║
║    1. Ensures correct viewport meta tag                      ║
║    2. Injects <link> to mobile.css                          ║
║    3. If the page has NO existing mobile sidebar/menu,       ║
║       builds a TOC drawer from the page's h1/h2 headings    ║
║       and injects the hamburger button + JS                  ║
║    4. If the page already has a working sidebar toggle       ║
║       (e.g. Nutanix guide), leaves it completely alone      ║
║                                                              ║
║  Usage:                                                      ║
║    python3 patch.py            # patch all pages            ║
║    python3 patch.py --dry-run  # preview, no file changes   ║
║    python3 patch.py --undo     # restore from .bak files    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, re, shutil
from html.parser import HTMLParser

CSS_FILE      = "mobile.css"
BACKUP_EXT    = ".bak"
PATCH_MARKER  = "<!-- SHN-PATCH -->"

# Files to skip entirely (already fully mobile-friendly)
SKIP_FILES = {"index.html"}

# If a page contains any of these strings it already has
# its own working mobile sidebar — skip injecting the TOC drawer
EXISTING_NAV_SIGNALS = [
    "toggleSidebar",
    "shn-toggle",        # our own marker from a previous patch run
    "menu-toggle",
]

# ── Terminal colours ─────────────────────────────────────────
def _c(t, code): return f"\033[{code}m{t}\033[0m"
green  = lambda t: _c(t, "0;32")
yellow = lambda t: _c(t, "0;33")
red    = lambda t: _c(t, "0;31")
cyan   = lambda t: _c(t, "0;36")
bold   = lambda t: _c(t, "1;37")
dim    = lambda t: _c(t, "0;90")

# ── Extract headings from HTML ───────────────────────────────
class HeadingExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []        # list of (tag, id, text)
        self._current_tag = None
        self._current_id  = None
        self._current_text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3"):
            self._current_tag  = tag
            self._current_id   = dict(attrs).get("id", "")
            self._current_text = []

    def handle_endtag(self, tag):
        if tag == self._current_tag and tag in ("h1", "h2", "h3"):
            text = re.sub(r'\s+', ' ', "".join(self._current_text)).strip()
            if text and len(text) > 2:
                self.headings.append((self._current_tag,
                                      self._current_id, text))
            self._current_tag = None

    def handle_data(self, data):
        if self._current_tag:
            self._current_text.append(data)

def extract_headings(html):
    parser = HeadingExtractor()
    parser.feed(html)
    return parser.headings   # [(tag, id, text), ...]

# ── Auto-add id attrs to headings that lack them ─────────────
def ensure_heading_ids(html):
    seen = {}
    def make_id(text):
        slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
        slug = slug[:40]
        seen[slug] = seen.get(slug, 0) + 1
        return slug if seen[slug] == 1 else f"{slug}-{seen[slug]}"

    def replacer(m):
        tag   = m.group(1)          # e.g. h2
        attrs = m.group(2)          # everything inside the tag
        rest  = m.group(3)          # closing >
        if 'id=' in attrs.lower():
            return m.group(0)       # already has id
        # grab text from the next close tag
        return m.group(0)           # we'll do a second pass below

    # Simpler: just add id="" to any h1/h2/h3 that lacks one,
    # derived from their text content
    def add_id(m):
        full    = m.group(0)
        open_t  = m.group(1)   # e.g. <h2 class="h2">
        tag     = m.group(2)   # e.g. h2
        inner   = m.group(3)   # content between open and close
        close_t = m.group(4)   # e.g. </h2>
        if 'id=' in open_t.lower():
            return full
        text = re.sub(r'<[^>]+>', '', inner).strip()
        if not text:
            return full
        hid = make_id(text)
        new_open = open_t.rstrip('>') + f' id="{hid}">'
        return new_open + inner + close_t

    html = re.sub(
        r'(<(h[123])\b[^>]*>)(.*?)(</\2>)',
        add_id, html, flags=re.DOTALL | re.IGNORECASE
    )
    return html

# ── Build the TOC drawer HTML ─────────────────────────────────
def build_drawer(headings, page_title):
    items = []
    num   = 0
    for tag, hid, text in headings:
        # Only h1 and h2 in the TOC (h3 is too granular)
        if tag not in ("h1", "h2"):
            continue
        # Skip very short or noisy headings
        if len(text) < 3:
            continue
        num += 1
        anchor = f"#{hid}" if hid else "#"
        num_label = f"{num:02d}" if tag == "h2" else "★"
        items.append(
            f'    <a class="shn-link" href="{anchor}" onclick="shnClose()">'
            f'<span class="shn-link-num">{num_label}</span>{text}</a>'
        )
    if not items:
        return ""

    items_html = "\n".join(items)
    safe_title = page_title[:30] + ("…" if len(page_title) > 30 else "")

    return f"""
  {PATCH_MARKER}
  <!-- SHN: Mobile Nav Drawer -->
  <div id="shn-overlay" onclick="shnClose()"></div>
  <button id="shn-toggle" onclick="shnOpen()" aria-label="Open navigation">&#9776;</button>
  <nav id="shn-drawer" aria-label="Page navigation">
    <div class="shn-header">
      <span class="shn-title">Contents</span>
      <button class="shn-close" onclick="shnClose()" aria-label="Close">&#10005;</button>
    </div>
    <a class="shn-back" href="index.html">&#8592; Study Hub Index</a>
    <div class="shn-group">{safe_title}</div>
{items_html}
  </nav>
  <script>
  (function() {{
    var drawer  = document.getElementById('shn-drawer');
    var overlay = document.getElementById('shn-overlay');
    var toggle  = document.getElementById('shn-toggle');
    if (!drawer) return;

    window.shnOpen = function() {{
      drawer.classList.add('shn-open');
      overlay.classList.add('shn-open');
      toggle.innerHTML = '&#10005;';
      toggle.setAttribute('aria-expanded', 'true');
    }};

    window.shnClose = function() {{
      drawer.classList.remove('shn-open');
      overlay.classList.remove('shn-open');
      toggle.innerHTML = '&#9776;';
      toggle.setAttribute('aria-expanded', 'false');
    }};

    /* Highlight active section while scrolling */
    var links = drawer.querySelectorAll('.shn-link[href^="#"]');
    if (links.length > 0) {{
      window.addEventListener('scroll', function() {{
        var scrollY = window.scrollY + 80;
        var active  = null;
        links.forEach(function(l) {{
          var id  = l.getAttribute('href').slice(1);
          var el  = id ? document.getElementById(id) : null;
          if (el && el.offsetTop <= scrollY) {{ active = l; }}
        }});
        links.forEach(function(l) {{ l.classList.remove('shn-active'); }});
        if (active) {{ active.classList.add('shn-active'); }}
      }}, {{ passive: true }});
    }}

    /* Close on Escape key */
    document.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') shnClose();
    }});
  }})();
  </script>"""

# ── Patch a single file ───────────────────────────────────────
def patch_file(filepath, dry_run=False):
    fname = os.path.basename(filepath)

    with open(filepath, encoding="utf-8", errors="replace") as f:
        original = f.read()

    # Already patched?
    if PATCH_MARKER in original:
        print(f"  {dim('⟳  already patched')}       {dim(fname)}")
        return "already"

    html = original

    # ── Step 1: Fix / add viewport meta ────────────────────
    vp_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    has_vp = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I))
    if has_vp:
        html = re.sub(
            r'<meta[^>]+name=["\']viewport["\'][^>]*>',
            vp_tag, html, flags=re.I
        )
    else:
        html = re.sub(r'(<head[^>]*>)',
                      r'\1\n  ' + vp_tag,
                      html, count=1, flags=re.I)

    # ── Step 2: Inject mobile.css link before </head> ───────
    css_link = f'  <link rel="stylesheet" href="{CSS_FILE}">'
    if CSS_FILE not in html:
        html = re.sub(r'(</head>)',
                      css_link + r'\n\1',
                      html, count=1, flags=re.I)

    # ── Step 3: Decide whether to inject the TOC drawer ─────
    has_existing_nav = any(sig in html for sig in EXISTING_NAV_SIGNALS)

    if not has_existing_nav:
        # Ensure headings have id attributes
        html = ensure_heading_ids(html)

        # Extract headings and page title
        headings = extract_headings(html)
        title_m  = re.search(r'<title[^>]*>(.*?)</title>', html, re.I|re.S)
        page_title = title_m.group(1).strip() if title_m else fname

        # Build drawer (only if we found headings)
        drawer_html = build_drawer(headings, page_title)
        if drawer_html:
            # Inject right after <body> opening tag
            html = re.sub(r'(<body[^>]*>)',
                          r'\1' + drawer_html,
                          html, count=1, flags=re.I)
            nav_note = f"{cyan('+ TOC drawer')} ({len(headings)} headings)"
        else:
            nav_note = yellow("no headings found — skipped TOC")
    else:
        nav_note = dim("existing nav detected — skipped TOC")

    # Sanity: did anything change?
    if html == original:
        print(f"  {yellow('⚠  nothing changed')}       {fname}")
        return "skip"

    if dry_run:
        print(f"  {cyan('○  would patch')}            {fname}  [{nav_note}]")
        return "dry"

    # Backup & write
    shutil.copy2(filepath, filepath + BACKUP_EXT)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  {green('✔  patched')}                {fname}  [{nav_note}]")
    return "patched"

# ── Undo a single file ─────────────────────────────────────────
def undo_file(filepath):
    fname   = os.path.basename(filepath)
    backup  = filepath + BACKUP_EXT
    if os.path.exists(backup):
        shutil.copy2(backup, filepath)
        os.remove(backup)
        print(f"  {green('✔  restored')}               {fname}")
        return "restored"
    print(f"  {yellow('⚠  no backup')}              {fname}")
    return "skip"

# ── Main ───────────────────────────────────────────────────────
def main():
    args    = sys.argv[1:]
    dry_run = "--dry-run" in args
    undo    = "--undo"    in args

    work_dir = os.path.dirname(os.path.abspath(__file__))

    print()
    print(bold("  ╔══════════════════════════════════════════╗"))
    print(bold("  ║   StudyHub Mobile Patch  v2             ║"))
    print(bold("  ╚══════════════════════════════════════════╝"))
    print()
    print(f"  Dir  : {cyan(work_dir)}")
    print(f"  Mode : {yellow('DRY RUN') if dry_run else (red('UNDO') if undo else green('PATCH'))}")
    print()

    # Check mobile.css present
    if not undo and not os.path.exists(os.path.join(work_dir, CSS_FILE)):
        print(red(f"  ✗  {CSS_FILE} not found. Copy it into Studyhtml/ first.\n"))
        sys.exit(1)

    # Gather HTML files
    files = sorted([
        os.path.join(work_dir, f)
        for f in os.listdir(work_dir)
        if f.lower().endswith(".html") and f not in SKIP_FILES
    ])

    if not files:
        print(yellow("  ⚠  No HTML files found.\n"))
        sys.exit(0)

    print(f"  Found {bold(str(len(files)))} HTML file(s):\n")

    counts = {}
    for fp in files:
        result = undo_file(fp) if undo else patch_file(fp, dry_run)
        counts[result] = counts.get(result, 0) + 1

    print()
    print(f"  {'─'*46}")
    if undo:
        print(f"  {green('Restored')}: {counts.get('restored',0)}   "
              f"{yellow('No backup')}: {counts.get('skip',0)}")
    elif dry_run:
        print(f"  {cyan('Would patch')}: {counts.get('dry',0)}   "
              f"{dim('Already OK')}: {counts.get('already',0)}")
    else:
        print(f"  {green('Patched')} : {counts.get('patched',0)}   "
              f"{dim('Already OK')}: {counts.get('already',0)}   "
              f"{yellow('Skipped')}: {counts.get('skip',0)}")
    print()

    if not undo and not dry_run and counts.get("patched", 0) > 0:
        git_msg = 'git commit -m "Add mobile responsiveness v2"'
        print(f"  {green('✔  Done!')} Push to GitHub:")
        print(f"    {cyan('git add .')}")
        print(f"    {cyan(git_msg)}")
        print(f"    {cyan('git push')}")
    elif not undo and not dry_run:
        print(f"  {green('✔  All files already up to date.')}")

    print()

if __name__ == "__main__":
    main()
