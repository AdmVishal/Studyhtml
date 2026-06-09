#!/usr/bin/env python3
"""
fix_network_mobile.py  v2
─────────────────────────────────────────────────────────────────
Fixes: Network Study Reference.html

ROOT CAUSE (confirmed from source):
  - <nav class="sidebar" id="sidebar"></nav>  ← EMPTY in HTML
  - Sidebar is built 100% by JS from a `sections` array at runtime
  - Previous fix tried to read .nav-item from DOM before JS ran → empty drawer
  - Also: existing CSS hides .sidebar AND .proto-tabs on mobile → no nav at all

CORRECT FIX:
  - After the page's own <script> runs and builds the sidebar,
    our script runs (deferred) and builds the mobile drawer from
    the ALREADY-RENDERED .nav-item buttons in the live DOM.
  - Use DOMContentLoaded + small setTimeout to ensure page JS ran first.
  - Inject a sticky top nav bar on mobile with protocol pills +
    a Topics drawer button — much simpler and more reliable than
    trying to sync with the hidden sidebar.

Usage:
  python3 fix_network_mobile.py        # apply
  python3 fix_network_mobile.py --undo # restore backup
"""

import os, sys, re, shutil

TARGET = "Network Study Reference.html"
MARKER = "<!-- NET-MOB-v2 -->"
BACKUP = TARGET + ".bak"

def c(t,code): return f"\033[{code}m{t}\033[0m"
green  = lambda t: c(t,"0;32")
yellow = lambda t: c(t,"0;33")
red    = lambda t: c(t,"0;31")
cyan   = lambda t: c(t,"0;36")
bold   = lambda t: c(t,"1;37")
dim    = lambda t: c(t,"0;90")

# ── The complete injection ────────────────────────────────────────
# Goes just before </body> so it runs AFTER the page's own script
# that populates the sidebar.
INJECTION = """<!-- NET-MOB-v2 -->
<style>
/* ════ Network Study Reference — Mobile Fix v2 ══════════════════ */

/* Override existing mobile rules that kill all navigation */
@media (max-width: 768px) {

  /* Keep sidebar hidden (we build our own drawer below) */
  .sidebar { display: none !important; }

  /* Proto-tabs in header hidden — replaced by our bottom bar */
  .proto-tabs { display: none !important; }

  /* Content full width with space for bottom bar */
  .content {
    margin-left: 0 !important;
    padding: 16px 14px 120px !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
  }

  .layout { display: block !important; }

  /* Header compact */
  header {
    padding: 0 10px !important;
    gap: 8px !important;
  }
  .brand-text { font-size: 12px !important; }
  .brand-icon { width: 26px !important; height: 26px !important; font-size: 13px !important; }
  .search-box { flex: 1 !important; max-width: 100% !important; min-width: 0 !important; }
  .search-box input { font-size: 14px !important; padding: 6px 28px 6px 28px !important; }

  /* ── Sticky bottom navigation bar ───────────────────────────── */
  #nm-bar {
    position: fixed !important;
    bottom: 0 !important; left: 0 !important; right: 0 !important;
    z-index: 9000 !important;
    background: #161b22 !important;
    border-top: 1px solid #30363d !important;
    display: flex !important;
    align-items: center !important;
    padding: 8px 12px !important;
    gap: 8px !important;
    box-shadow: 0 -4px 20px rgba(0,0,0,.4) !important;
  }

  /* Protocol pills in bottom bar */
  #nm-pills {
    display: flex !important;
    gap: 5px !important;
    overflow-x: auto !important;
    flex: 1 !important;
    scrollbar-width: none !important;
    -webkit-overflow-scrolling: touch !important;
  }
  #nm-pills::-webkit-scrollbar { display: none !important; }

  .nm-pill {
    flex-shrink: 0 !important;
    padding: 6px 12px !important;
    border-radius: 20px !important;
    border: 1px solid #30363d !important;
    background: none !important;
    color: #8b949e !important;
    font-family: var(--font, system-ui) !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: .04em !important;
    text-transform: uppercase !important;
    cursor: pointer !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: all .15s !important;
    white-space: nowrap !important;
  }
  .nm-pill.nm-all  { border-color: #8b949e !important; color: #8b949e !important; }
  .nm-pill.nm-bgp  { border-color: #58a6ff !important; color: #58a6ff !important; background: rgba(88,166,255,.1) !important; }
  .nm-pill.nm-ospf { border-color: #3fb950 !important; color: #3fb950 !important; background: rgba(63,185,80,.1) !important; }
  .nm-pill.nm-eigrp{ border-color: #d29922 !important; color: #d29922 !important; background: rgba(210,153,34,.1) !important; }
  .nm-pill.nm-vpn  { border-color: #bc8cff !important; color: #bc8cff !important; background: rgba(188,140,255,.1) !important; }

  /* Topics button in bottom bar */
  #nm-topics-btn {
    flex-shrink: 0 !important;
    background: #58a6ff !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 14px !important;
    font-family: var(--font, system-ui) !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    gap: 5px !important;
    -webkit-tap-highlight-color: transparent !important;
    white-space: nowrap !important;
  }

  /* ── Topics drawer ──────────────────────────────────────────── */
  #nm-overlay {
    display: none;
    position: fixed !important;
    inset: 0 !important;
    background: rgba(0,0,0,.75) !important;
    z-index: 9100 !important;
  }
  #nm-overlay.open { display: block !important; }

  #nm-drawer {
    position: fixed !important;
    top: 0 !important; left: 0 !important; bottom: 0 !important;
    width: min(290px, 85vw) !important;
    background: #161b22 !important;
    border-right: 1px solid #30363d !important;
    z-index: 9200 !important;
    display: flex !important;
    flex-direction: column !important;
    transform: translateX(-100%) !important;
    transition: transform .28s cubic-bezier(.4,0,.2,1) !important;
  }
  #nm-drawer.open { transform: translateX(0) !important; }

  #nm-drawer-head {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 14px 16px !important;
    border-bottom: 1px solid #30363d !important;
    background: #21262d !important;
    flex-shrink: 0 !important;
  }
  #nm-drawer-title {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
    color: #8b949e !important;
    font-family: var(--font, system-ui) !important;
  }
  #nm-close-btn {
    background: rgba(255,255,255,.06) !important;
    border: 1px solid #30363d !important;
    border-radius: 7px !important;
    color: #8b949e !important;
    width: 30px !important;
    height: 30px !important;
    font-size: 15px !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* Back to hub */
  #nm-back {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 11px 16px !important;
    color: #e3b341 !important;
    text-decoration: none !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid #30363d !important;
    background: rgba(227,179,65,.04) !important;
    font-family: var(--font, system-ui) !important;
    flex-shrink: 0 !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* Scrollable item list */
  #nm-item-list {
    overflow-y: auto !important;
    flex: 1 !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 4px 0 60px !important;
  }
  #nm-item-list::-webkit-scrollbar { width: 3px !important; }
  #nm-item-list::-webkit-scrollbar-thumb { background: #30363d !important; }

  /* Section headers inside drawer */
  .nm-sec {
    padding: 12px 16px 3px !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: .14em !important;
    text-transform: uppercase !important;
    color: #484f58 !important;
    font-family: var(--font, system-ui) !important;
  }

  /* Topic buttons inside drawer */
  .nm-item {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    width: 100% !important;
    padding: 10px 16px !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    background: none !important;
    text-align: left !important;
    font-family: var(--font, system-ui) !important;
    font-size: 13px !important;
    color: #8b949e !important;
    cursor: pointer !important;
    line-height: 1.35 !important;
    box-sizing: border-box !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: background .12s !important;
  }
  .nm-item:active { background: #21262d !important; }
  .nm-item.nm-cur {
    background: #21262d !important;
    color: #e6edf3 !important;
    border-left-color: #58a6ff !important;
  }
  .nm-dot {
    width: 6px !important; height: 6px !important;
    border-radius: 50% !important;
    background: currentColor !important;
    opacity: .45 !important;
    flex-shrink: 0 !important;
  }
  .nm-item.nm-cur .nm-dot { opacity: 1 !important; }

  /* Responsive misc */
  pre { font-size: 11px !important; overflow-x: auto !important; }
  code { font-size: 10.5px !important; }
  .tbl { overflow-x: auto !important; }
  .cards { grid-template-columns: 1fr !important; }
  .step { padding: 10px 12px !important; }
  .panel h1 { font-size: 20px !important; }
  .panel h2 { font-size: 15px !important; }
}

@media (min-width: 769px) {
  #nm-bar     { display: none !important; }
  #nm-overlay { display: none !important; }
  #nm-drawer  { display: none !important; }
}
</style>

<!-- Mobile nav HTML (hidden on desktop via CSS above) -->
<div id="nm-overlay"></div>
<nav id="nm-drawer">
  <div id="nm-drawer-head">
    <span id="nm-drawer-title">Topics</span>
    <button id="nm-close-btn">&#10005;</button>
  </div>
  <a id="nm-back" href="index.html">&#8592; Study Hub</a>
  <div id="nm-item-list"></div>
</nav>
<div id="nm-bar">
  <div id="nm-pills"><!-- pills built by JS --></div>
  <button id="nm-topics-btn">&#9776; Topics</button>
</div>

<script>
/* Network Study Reference — Mobile Nav v2
   Runs AFTER page's own script has populated #sidebar */
(function () {
  if (window.innerWidth > 768) return;

  var overlay   = document.getElementById('nm-overlay');
  var drawer    = document.getElementById('nm-drawer');
  var closeBtn  = document.getElementById('nm-close-btn');
  var topicsBtn = document.getElementById('nm-topics-btn');
  var itemList  = document.getElementById('nm-item-list');
  var pillsBar  = document.getElementById('nm-pills');

  /* ── Open / Close ────────────────────────────────────── */
  function openDrawer() {
    drawer.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    topicsBtn.innerHTML = '&#10005; Close';
    refreshItems();
  }
  function closeDrawer() {
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
    topicsBtn.innerHTML = '&#9776; Topics';
  }

  topicsBtn.addEventListener('click', function () {
    drawer.classList.contains('open') ? closeDrawer() : openDrawer();
  });
  closeBtn.addEventListener('click', closeDrawer);
  overlay.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeDrawer();
  });

  /* ── Build drawer items from live .nav-item DOM elements ─
     These are created by the page's own JS from the sections array.
     We poll until they exist (page JS may run asynchronously).    */
  var built = false;

  function buildItems() {
    if (built) return;

    var pageSidebar = document.getElementById('sidebar');
    if (!pageSidebar) return;

    var navItems = pageSidebar.querySelectorAll('button.nav-item');
    if (navItems.length === 0) return; // page JS hasn't run yet, retry

    built = true;
    itemList.innerHTML = '';

    navItems.forEach(function (orig) {
      var item = document.createElement('button');
      item.className = 'nm-item';
      var dot = document.createElement('span');
      dot.className = 'nm-dot';
      item.appendChild(dot);
      item.appendChild(document.createTextNode(orig.textContent.trim()));

      item.addEventListener('click', function () {
        orig.click();
        setTimeout(closeDrawer, 160);
      });

      itemList.appendChild(item);
    });

    /* Mark the current active item */
    syncActive();
  }

  function refreshItems() {
    if (!built) buildItems();
    else syncActive();
  }

  function syncActive() {
    var pageSidebar = document.getElementById('sidebar');
    if (!pageSidebar) return;
    var active = pageSidebar.querySelector('button.nav-item.active');
    var activeText = active ? active.textContent.trim() : '';
    itemList.querySelectorAll('.nm-item').forEach(function (item) {
      var isActive = item.textContent.trim() === activeText;
      item.classList.toggle('nm-cur', isActive);
    });
  }

  /* ── Build protocol pills from page's .proto-tab buttons ─ */
  function buildPills() {
    var pageTabs = document.querySelectorAll('.proto-tab');
    if (pageTabs.length === 0) return;

    pillsBar.innerHTML = '';
    pageTabs.forEach(function (tab) {
      var p = tab.getAttribute('data-p') || 'all';
      var pill = document.createElement('button');
      pill.className = 'nm-pill';
      pill.textContent = tab.textContent.trim();
      pill.setAttribute('data-p', p);
      if (tab.classList.contains('active')) pill.classList.add('nm-' + p);

      pill.addEventListener('click', function () {
        tab.click();           /* fire page's own tab handler */
        updatePills();
        syncActive();
        setTimeout(buildItems, 50); /* items may change after filter */
      });

      pillsBar.appendChild(pill);
    });
  }

  function updatePills() {
    var pageTabs = document.querySelectorAll('.proto-tab');
    pillsBar.querySelectorAll('.nm-pill').forEach(function (pill, i) {
      var p = pill.getAttribute('data-p');
      pill.className = 'nm-pill';
      if (pageTabs[i] && pageTabs[i].classList.contains('active')) {
        pill.classList.add('nm-' + p);
      }
    });
  }

  /* ── Observe sidebar for changes (when proto filter is applied) */
  var observer = new MutationObserver(function () {
    built = false;          /* force rebuild */
    syncActive();
    updatePills();
  });

  /* ── Initialise: wait for page JS to finish building sidebar ── */
  function init() {
    var sidebar = document.getElementById('sidebar');
    if (!sidebar) { setTimeout(init, 50); return; }

    /* Try to build immediately */
    buildItems();
    buildPills();

    /* If sidebar still empty, poll every 100ms for up to 3s */
    if (!built) {
      var attempts = 0;
      var poll = setInterval(function () {
        attempts++;
        buildItems();
        buildPills();
        if (built || attempts > 30) clearInterval(poll);
      }, 100);
    }

    /* Watch sidebar for future DOM changes */
    observer.observe(sidebar, {
      childList: true, subtree: true, attributes: true,
      attributeFilter: ['class']
    });
  }

  /* Run after DOM is fully ready AND page scripts have executed */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(init, 100);
    });
  } else {
    setTimeout(init, 100);
  }

})();
</script>"""

# ── Helpers ───────────────────────────────────────────────────
def banner():
    print()
    print(bold("  ╔════════════════════════════════════════════╗"))
    print(bold("  ║  Network Study Reference — Mobile Fix v2   ║"))
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
        print(dim(f"     Run from your Studyhtml/ directory."))
        sys.exit(1)

    # ── UNDO ──────────────────────────────────────────────────
    if undo:
        if os.path.exists(bak):
            shutil.copy2(bak, fp)
            os.remove(bak)
            print(green(f"  ✔  Restored from backup."))
        else:
            print(yellow(f"  ⚠  No backup found: {BACKUP}"))
        print()
        return

    # ── READ ──────────────────────────────────────────────────
    with open(fp, encoding='utf-8', errors='replace') as f:
        html = f.read()

    if MARKER in html:
        print(yellow("  ⚠  Already patched (marker found)."))
        print(dim("     Run --undo first, then re-apply."))
        print(); return

    # ── REMOVE any old patch attempts ─────────────────────────
    old_markers = ['<!-- NET-MOBILE-FIX-v1 -->', '<!-- NET-MOBILE-FIX -->',
                   '<!-- STUDYHUB-MOBILE-v4 -->', "<!-- SHN-v3 -->"]
    for m in old_markers:
        if m in html:
            print(dim(f"  ✓  Removing old marker: {m}"))

    # Strip shm-v4 style block injected by previous patch.py
    html = re.sub(r"\n<style id='shm-v4'>.*?</style>", '', html, flags=re.DOTALL)
    html = html.replace("<!-- STUDYHUB-MOBILE-v4 -->", "")

    # ── INJECT before </body> ─────────────────────────────────
    if re.search(r'</body>', html, re.I):
        html = re.sub(r'(</body>)', INJECTION + r'\n\1', html, count=1, flags=re.I)
    else:
        html += '\n' + INJECTION

    # ── BACKUP + WRITE ────────────────────────────────────────
    shutil.copy2(fp, bak)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(html)

    print(green(f"  ✔  Patched: {TARGET}"))
    print(dim(f"  ✓  Backup:  {BACKUP}"))
    print()
    print(bold("  What's fixed:"))
    print(dim("  • Sticky bottom bar: protocol pills + ≡ Topics button"))
    print(dim("  • Topics drawer: reads LIVE nav-items after page JS builds them"))
    print(dim("  • Polls DOM until sidebar is populated (handles async JS)"))
    print(dim("  • Tapping any topic → content switches, drawer closes"))
    print(dim("  • Protocol pills (BGP/OSPF/EIGRP/VPN) fire page's own filter"))
    print(dim("  • MutationObserver keeps drawer in sync with page state"))
    print(dim("  • Desktop: zero change"))
    print()
    git_msg = 'git commit -m "Fix Network Study Reference mobile nav v2"'
    print(bold("  Push to GitHub:"))
    print(f"    {cyan('git add .')}")
    print(f"    {cyan(git_msg)}")
    print(f"    {cyan('git push')}")
    print()

if __name__ == '__main__':
    main()
