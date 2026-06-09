#!/usr/bin/env python3
"""
fix_network_mobile.py
──────────────────────────────────────────────────────────────
Targeted mobile fix for: Network Study Reference.html

ROOT CAUSE: The page's own CSS already does:
  @media(max-width:768px) {
    .sidebar    { display: none; }   ← nav hidden, no way to switch topics
    .proto-tabs { display: none; }   ← protocol tabs also hidden
    .content    { margin-left: 0; }  ← content OK
  }
  Result: only the first-loaded panel is visible. No navigation.

FIX: Inject a full-screen slide-in nav drawer that:
  1. Reads all .nav-item buttons already in the page's .sidebar
  2. Mirrors them into a mobile drawer panel
  3. Adds protocol filter tabs (BGP/OSPF/EIGRP/VPN) to the drawer
  4. Tapping any item fires the page's own click handler (no logic change)
  5. Floating "≡ Topics" button bottom-right to open the drawer
  6. Desktop (>768px): drawer is invisible, zero interference

Usage:
  cd ~/Studyhtml
  python3 fix_network_mobile.py        # apply fix
  python3 fix_network_mobile.py --undo # restore backup
"""

import os, sys, re, shutil

TARGET = "Network Study Reference.html"
MARKER = "<!-- NET-MOBILE-FIX-v1 -->"
BACKUP = TARGET + ".bak"

def col(t, c): return f"\033[{c}m{t}\033[0m"
green  = lambda t: col(t,"0;32")
yellow = lambda t: col(t,"0;33")
red    = lambda t: col(t,"0;31")
cyan   = lambda t: col(t,"0;36")
bold   = lambda t: col(t,"1;37")
dim    = lambda t: col(t,"0;90")

# ─────────────────────────────────────────────────────────────
# The complete mobile fix: CSS + HTML drawer + JS
# ─────────────────────────────────────────────────────────────
MOBILE_FIX = r"""
<!-- NET-MOBILE-FIX-v1 -->

<style id="net-mob-css">
/* ═══ Network Study Reference — Mobile Fix ══════════════════ */

/* ── Override existing mobile rules that hide navigation ──── */
@media (max-width: 768px) {

  /* Keep sidebar hidden (we replace it with our drawer) */
  .sidebar { display: none !important; }

  /* Ensure content is full-width with good padding */
  .content {
    margin-left: 0 !important;
    padding: 16px 14px 100px !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
  }

  /* Layout no longer needs flex */
  .layout {
    display: block !important;
    margin-top: var(--header-h, 56px) !important;
    min-height: auto !important;
  }

  /* Header: compact on mobile */
  header {
    padding: 0 12px !important;
    gap: 10px !important;
    flex-wrap: nowrap !important;
  }
  .brand-text { font-size: 13px !important; }
  .search-box { max-width: none !important; flex: 1 !important; min-width: 0 !important; }
  .search-box input { font-size: 14px !important; padding: 6px 30px 6px 28px !important; }
  /* Hide desktop proto-tabs — replaced by drawer */
  .proto-tabs { display: none !important; }

  /* Tables: horizontal scroll */
  .tbl, table { overflow-x: auto !important; display: block !important; }
  th, td { font-size: 11px !important; padding: 7px 10px !important; white-space: nowrap; }

  /* Code blocks */
  pre { font-size: 11px !important; padding: 12px !important; overflow-x: auto !important; }
  code { font-size: 10.5px !important; }

  /* Cards: single column */
  .cards { grid-template-columns: 1fr !important; }

  /* Steps: compact */
  .step { padding: 10px 12px !important; gap: 10px !important; }

  /* Headings */
  .panel h1 { font-size: 22px !important; }
  .panel h2 { font-size: 16px !important; margin: 24px 0 10px !important; }
  .panel h3 { font-size: 14px !important; }

  /* ── Mobile drawer styles ─────────────────────────────── */

  /* Floating Topics button */
  #nmf-btn {
    display: flex !important;
    position: fixed !important;
    bottom: 20px !important;
    right: 16px !important;
    z-index: 9999 !important;
    align-items: center !important;
    gap: 8px !important;
    background: #58a6ff !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 12px 20px !important;
    font-family: var(--font, system-ui) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: .02em !important;
    cursor: pointer !important;
    box-shadow: 0 4px 24px rgba(88,166,255,.45) !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: transform .15s !important;
  }
  #nmf-btn:active { transform: scale(.96) !important; }

  /* Backdrop overlay */
  #nmf-overlay {
    display: none !important;
    position: fixed !important;
    inset: 0 !important;
    background: rgba(0,0,0,.7) !important;
    z-index: 9997 !important;
    backdrop-filter: blur(3px) !important;
    -webkit-backdrop-filter: blur(3px) !important;
  }
  #nmf-overlay.open { display: block !important; }

  /* Slide-in drawer from left */
  #nmf-drawer {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    bottom: 0 !important;
    width: min(300px, 88vw) !important;
    background: var(--surf, #161b22) !important;
    border-right: 1px solid var(--border, #30363d) !important;
    z-index: 9998 !important;
    display: flex !important;
    flex-direction: column !important;
    transform: translateX(-100%) !important;
    transition: transform .28s cubic-bezier(.4,0,.2,1) !important;
    overflow: hidden !important;
  }
  #nmf-drawer.open { transform: translateX(0) !important; }

  /* Drawer header row */
  #nmf-head {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 14px 16px !important;
    border-bottom: 1px solid var(--border, #30363d) !important;
    background: var(--surf2, #21262d) !important;
    flex-shrink: 0 !important;
  }
  #nmf-head-title {
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
    color: var(--dim, #8b949e) !important;
    font-family: var(--font, system-ui) !important;
  }
  #nmf-close {
    background: rgba(255,255,255,.06) !important;
    border: 1px solid var(--border, #30363d) !important;
    border-radius: 8px !important;
    color: var(--dim, #8b949e) !important;
    width: 32px !important;
    height: 32px !important;
    font-size: 16px !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* Back to hub link */
  #nmf-back {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 11px 16px !important;
    color: #e3b341 !important;
    text-decoration: none !important;
    font-family: var(--font, system-ui) !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid var(--border, #30363d) !important;
    background: rgba(227,179,65,.05) !important;
    flex-shrink: 0 !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* Protocol filter tabs inside drawer */
  #nmf-proto-bar {
    display: flex !important;
    gap: 6px !important;
    padding: 10px 12px !important;
    border-bottom: 1px solid var(--border, #30363d) !important;
    overflow-x: auto !important;
    flex-shrink: 0 !important;
    scrollbar-width: none !important;
  }
  #nmf-proto-bar::-webkit-scrollbar { display: none !important; }
  .nmf-proto-pill {
    flex-shrink: 0 !important;
    padding: 5px 12px !important;
    border-radius: 20px !important;
    border: 1px solid var(--border, #30363d) !important;
    background: none !important;
    color: var(--dim, #8b949e) !important;
    font-family: var(--font, system-ui) !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    cursor: pointer !important;
    letter-spacing: .04em !important;
    text-transform: uppercase !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: all .15s !important;
  }
  .nmf-proto-pill.active-bgp   { border-color: #58a6ff !important; color: #58a6ff !important; background: rgba(88,166,255,.1) !important; }
  .nmf-proto-pill.active-ospf  { border-color: #3fb950 !important; color: #3fb950 !important; background: rgba(63,185,80,.1) !important; }
  .nmf-proto-pill.active-eigrp { border-color: #d29922 !important; color: #d29922 !important; background: rgba(210,153,34,.1) !important; }
  .nmf-proto-pill.active-vpn   { border-color: #bc8cff !important; color: #bc8cff !important; background: rgba(188,140,255,.1) !important; }

  /* Scrollable nav items list */
  #nmf-list {
    overflow-y: auto !important;
    flex: 1 !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 6px 0 !important;
  }
  #nmf-list::-webkit-scrollbar { width: 3px !important; }
  #nmf-list::-webkit-scrollbar-thumb { background: var(--border, #30363d) !important; }

  /* Section labels in drawer */
  .nmf-sec-label {
    padding: 12px 16px 4px !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: .14em !important;
    text-transform: uppercase !important;
    color: var(--muted, #484f58) !important;
    font-family: var(--font, system-ui) !important;
  }

  /* Individual topic items in drawer */
  .nmf-item {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    width: 100% !important;
    padding: 10px 16px !important;
    background: none !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    text-align: left !important;
    color: var(--dim, #8b949e) !important;
    font-family: var(--font, system-ui) !important;
    font-size: 13px !important;
    cursor: pointer !important;
    line-height: 1.35 !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: all .15s !important;
    box-sizing: border-box !important;
  }
  .nmf-item:active { background: var(--surf2, #21262d) !important; }
  .nmf-item.cur { 
    background: var(--surf2, #21262d) !important;
    color: var(--text, #e6edf3) !important;
  }
  .nmf-item.cur-bgp   { border-left-color: #58a6ff !important; color: #58a6ff !important; }
  .nmf-item.cur-ospf  { border-left-color: #3fb950 !important; color: #3fb950 !important; }
  .nmf-item.cur-eigrp { border-left-color: #d29922 !important; color: #d29922 !important; }
  .nmf-item.cur-vpn   { border-left-color: #bc8cff !important; color: #bc8cff !important; }

  .nmf-dot {
    width: 6px !important;
    height: 6px !important;
    border-radius: 50% !important;
    flex-shrink: 0 !important;
    background: currentColor !important;
    opacity: .5 !important;
  }
  .nmf-item.cur .nmf-dot { opacity: 1 !important; }
}

/* Desktop: completely hidden */
@media (min-width: 769px) {
  #nmf-btn     { display: none !important; }
  #nmf-overlay { display: none !important; }
  #nmf-drawer  { display: none !important; }
}
</style>

<!-- Mobile drawer HTML -->
<div id="nmf-overlay"></div>
<nav id="nmf-drawer" role="navigation" aria-label="Topic navigation">
  <div id="nmf-head">
    <span id="nmf-head-title">Topics</span>
    <button id="nmf-close" aria-label="Close navigation">&#10005;</button>
  </div>
  <a id="nmf-back" href="index.html">&#8592; Study Hub Index</a>
  <div id="nmf-proto-bar">
    <!-- Protocol pills injected by JS -->
  </div>
  <div id="nmf-list">
    <!-- Nav items mirrored from page sidebar by JS -->
  </div>
</nav>
<button id="nmf-btn" aria-label="Open topic navigation">&#9776; Topics</button>

<script id="net-mob-js">
(function () {
  'use strict';

  /* Only activate on mobile */
  if (window.innerWidth > 768) return;

  var drawer  = document.getElementById('nmf-drawer');
  var overlay = document.getElementById('nmf-overlay');
  var btn     = document.getElementById('nmf-btn');
  var closeB  = document.getElementById('nmf-close');
  var protoBar= document.getElementById('nmf-proto-bar');
  var list    = document.getElementById('nmf-list');

  if (!drawer || !btn) return;

  /* ── Open / Close ────────────────────────────────────────── */
  function open() {
    drawer.classList.add('open');
    overlay.classList.add('open');
    btn.innerHTML = '&#10005; Close';
    document.body.style.overflow = 'hidden';
    syncActive();
  }

  function close() {
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    btn.innerHTML = '&#9776; Topics';
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', function () {
    drawer.classList.contains('open') ? close() : open();
  });
  closeB.addEventListener('click', close);
  overlay.addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });

  /* ── Mirror sidebar nav items into drawer ────────────────── */
  var pageSidebar = document.querySelector('.sidebar');
  if (!pageSidebar) return;

  /* Clone section labels */
  var secLabels = pageSidebar.querySelectorAll('.sec-label');
  var navItems  = pageSidebar.querySelectorAll('.nav-item');

  /* Build drawer items from the page's own nav-items */
  navItems.forEach(function (orig) {
    var proto = orig.getAttribute('data-p') || '';
    var text  = orig.textContent.trim();

    var item = document.createElement('button');
    item.className = 'nmf-item';
    item.setAttribute('data-p', proto);
    item.innerHTML = '<span class="nmf-dot"></span>' + text;

    /* Tap: fire the original nav-item click then close drawer */
    item.addEventListener('click', function () {
      orig.click();          /* delegate to page's own handler */
      setTimeout(close, 180);
    });

    list.appendChild(item);
  });

  /* ── Build protocol filter pills ────────────────────────── */
  var protos = [
    { key: 'bgp',   label: 'BGP'   },
    { key: 'ospf',  label: 'OSPF'  },
    { key: 'eigrp', label: 'EIGRP' },
    { key: 'vpn',   label: 'VPN'   },
  ];

  var allPill = document.createElement('button');
  allPill.className = 'nmf-proto-pill';
  allPill.textContent = 'All';
  allPill.addEventListener('click', function () {
    filterProto('');
  });
  protoBar.appendChild(allPill);

  protos.forEach(function (p) {
    /* Only add pill if at least one nav item uses this proto */
    var exists = Array.from(list.querySelectorAll('.nmf-item')).some(function (el) {
      return el.getAttribute('data-p') === p.key;
    });
    if (!exists) return;

    var pill = document.createElement('button');
    pill.className = 'nmf-proto-pill';
    pill.textContent = p.label;
    pill.setAttribute('data-p', p.key);
    pill.addEventListener('click', function () { filterProto(p.key); });
    protoBar.appendChild(pill);
  });

  /* Also pull protocol filter from the page's own .proto-tab buttons */
  var pageTabs = document.querySelectorAll('.proto-tab');
  pageTabs.forEach(function (tab) {
    var p = tab.getAttribute('data-p');
    if (!p) return;
    var pill = protoBar.querySelector('.nmf-proto-pill[data-p="' + p + '"]');
    /* Sync active state when page tab is clicked externally */
    tab.addEventListener('click', function () { syncProtoBar(); });
  });

  /* ── Filter nav items by protocol ───────────────────────── */
  function filterProto(proto) {
    list.querySelectorAll('.nmf-item').forEach(function (item) {
      var p = item.getAttribute('data-p') || '';
      item.style.display = (!proto || p === proto) ? '' : 'none';
    });

    /* Update pill active state */
    protoBar.querySelectorAll('.nmf-proto-pill').forEach(function (pill) {
      var pp = pill.getAttribute('data-p') || '';
      pill.className = 'nmf-proto-pill';
      if ((!proto && !pp) || pp === proto) {
        pill.classList.add('active-' + (proto || 'all'));
        if (!proto) pill.style.borderColor = '#8b949e';
      }
    });

    /* Fire matching page proto-tab */
    if (proto) {
      var pageTab = document.querySelector('.proto-tab[data-p="' + proto + '"]');
      if (pageTab) pageTab.click();
    }
  }

  /* ── Sync active item in drawer to page's active nav-item ── */
  function syncActive() {
    var activeOrig = pageSidebar.querySelector('.nav-item.active');
    var activeProto = activeOrig ? (activeOrig.getAttribute('data-p') || '') : '';
    var activeText  = activeOrig ? activeOrig.textContent.trim() : '';

    list.querySelectorAll('.nmf-item').forEach(function (item) {
      item.className = 'nmf-item';
      if (item.textContent.trim() === activeText) {
        item.classList.add('cur');
        if (activeProto) item.classList.add('cur-' + activeProto);
      }
      item.setAttribute('data-p', item.getAttribute('data-p') || '');
    });
  }

  /* ── Sync proto bar to page's active proto-tab ─────────── */
  function syncProtoBar() {
    var activeTab = document.querySelector('.proto-tab.active');
    var ap = activeTab ? activeTab.getAttribute('data-p') : '';
    protoBar.querySelectorAll('.nmf-proto-pill').forEach(function (pill) {
      var pp = pill.getAttribute('data-p') || '';
      pill.className = 'nmf-proto-pill';
      if (pp === ap) pill.classList.add('active-' + ap);
    });
  }

  /* ── Observe page nav-item active changes (MutationObserver) */
  var mo = new MutationObserver(function () {
    syncActive();
    syncProtoBar();
  });
  mo.observe(pageSidebar, { attributes: true, subtree: true, attributeFilter: ['class'] });

  /* Initial sync */
  syncActive();
  syncProtoBar();

  console.log('[NetMob] Mobile nav drawer ready. Items:', list.querySelectorAll('.nmf-item').length);
})();
</script>
"""

# ── Helpers ───────────────────────────────────────────────────
def banner():
    print()
    print(bold("  ╔════════════════════════════════════════════╗"))
    print(bold("  ║  Network Study Reference — Mobile Fix      ║"))
    print(bold("  ╚════════════════════════════════════════════╝"))
    print()

def main():
    args = sys.argv[1:]
    undo = '--undo' in args
    wd   = os.path.dirname(os.path.abspath(__file__))
    fp   = os.path.join(wd, TARGET)
    bak  = os.path.join(wd, BACKUP)

    banner()

    if not os.path.exists(fp):
        print(red(f"  ✗  Not found: {TARGET}"))
        print(dim(f"     Expected at: {fp}"))
        print(dim(f"     Run from inside your Studyhtml/ folder."))
        sys.exit(1)

    # ── UNDO ──────────────────────────────────────────────────
    if undo:
        if os.path.exists(bak):
            shutil.copy2(bak, fp)
            os.remove(bak)
            print(green(f"  ✔  Restored: {TARGET}"))
        else:
            print(yellow(f"  ⚠  No backup found: {BACKUP}"))
        print()
        return

    # ── READ ──────────────────────────────────────────────────
    with open(fp, encoding='utf-8', errors='replace') as f:
        html = f.read()

    if MARKER in html:
        print(yellow("  ⚠  Already patched."))
        print(dim("     Run with --undo to remove, then re-apply."))
        print()
        return

    # ── ANALYSIS ──────────────────────────────────────────────
    has_sidebar = '.sidebar' in html and 'nav-item' in html
    has_proto   = 'proto-tab' in html
    has_layout  = '.layout' in html
    print(dim(f"  ✓  Found .sidebar:   {has_sidebar}"))
    print(dim(f"  ✓  Found proto-tabs: {has_proto}"))
    print(dim(f"  ✓  Found .layout:    {has_layout}"))
    print()

    # ── INJECT before </body> ─────────────────────────────────
    if '</body>' in html.lower():
        html = re.sub(r'(</body>)', MOBILE_FIX + r'\n\1', html, count=1, flags=re.I)
    else:
        html += '\n' + MOBILE_FIX

    # ── BACKUP + WRITE ────────────────────────────────────────
    shutil.copy2(fp, bak)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(html)

    print(green(f"  ✔  Patched: {TARGET}"))
    print(dim(f"  ✓  Backup:  {BACKUP}"))
    print()
    print(bold("  What was fixed:"))
    print(dim("  • Floating '≡ Topics' button (bottom-right, blue)"))
    print(dim("  • Tap Topics → full-screen drawer slides in from left"))
    print(dim("  • Drawer shows ALL topics from the existing sidebar"))
    print(dim("  • Protocol filter pills: BGP / OSPF / EIGRP / VPN"))
    print(dim("  • Tap any topic → content loads, drawer auto-closes"))
    print(dim("  • Active topic highlighted in drawer with protocol color"))
    print(dim("  • MutationObserver keeps drawer in sync with page state"))
    print(dim("  • Desktop (>768px): zero change, drawer fully hidden"))
    print()
    git_msg = 'git commit -m "Fix Network Study Reference mobile navigation"'
    print(bold("  Push to GitHub:"))
    print(f"    {cyan('git add .')}")
    print(f"    {cyan(git_msg)}")
    print(f"    {cyan('git push')}")
    print()

if __name__ == '__main__':
    main()
