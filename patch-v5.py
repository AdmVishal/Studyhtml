#!/usr/bin/env python3
"""
mobile_master.py  —  StudyHub Universal Mobile Patcher
═══════════════════════════════════════════════════════════════════════
Scans every HTML page in the directory, analyses its exact structure,
strips ALL previous patch attempts, then applies one clean, correct
responsive CSS+JS injection per page.

Page layouts discovered from source (confirmed via GitHub):

  TYPE-A  "flex-sidebar"  ← CCNA, Linux Admin, OS Admin L3,
           .main{display:flex}   Master Interview Hub, RHEL
           .sidebar{width:240px} .content{flex:1}
           .cat-nav tab bar
           JS-driven panels from sections[] array

  TYPE-B  "fixed-sidebar"  ← Network Study Reference (already fixed)
           .layout{display:flex}
           .sidebar{position:fixed; width:260px}
           .content{margin-left:260px}
           .proto-tabs in header
           JS-driven panels from sections[] array

  TYPE-C  "itil-scroll"  ← ITIL Unix Interview Prep
           Continuous-scroll page with left navigation
           .app-container or similar with left-nav + content

  TYPE-D  "nutanix-toggle"  ← Nutanix Foundations Guide
           Already has working mobile toggle (toggleSidebar)
           Just needs table/layout overflows fixed

Strategy per type:
  TYPE-A/B  → Hide sidebar, add sticky bottom bar (protocol/category
              pills + ≡ Topics button), slide-in drawer mirrors
              live .topic-btn/.nav-item buttons (built by page JS)
  TYPE-C    → Left nav made sticky collapsible, content full-width
  TYPE-D    → Leave sidebar toggle alone, fix table overflow only

Usage:
  cd ~/Studyhtml
  python3 mobile_master.py            # patch all pages
  python3 mobile_master.py --dry-run  # preview, no changes
  python3 mobile_master.py --undo     # restore all .bak files
"""

import os, sys, re, shutil

BACKUP_EXT   = ".bak"
MASTER_MARK  = "<!-- STUDYHUB-MASTER-v1 -->"
SKIP_FILES   = {"index.html"}

# ── Colours ───────────────────────────────────────────────────────
def _c(t, c): return f"\033[{c}m{t}\033[0m"
G = lambda t: _c(t, "0;32")
Y = lambda t: _c(t, "0;33")
R = lambda t: _c(t, "0;31")
C = lambda t: _c(t, "0;36")
B = lambda t: _c(t, "1;37")
D = lambda t: _c(t, "0;90")

# ═══════════════════════════════════════════════════════════════════
#  STRIP — remove every previous patch injection
# ═══════════════════════════════════════════════════════════════════
OLD_STYLE_IDS = [
    "shm-v4","shn-styles","shn-page-mobile","ccna-mobile-style",
    "net-mob-css","nm-fix-css","nm3-css","mob-fix-css",
]
OLD_SCRIPT_IDS = [
    "shm-js","shn-js","ccna-mobile-script","net-mob-js",
    "nm-fix-js","nm3-js","mob-fix-js",
]
OLD_DIV_IDS = [
    "shn-overlay","shn-nav","shn-btn",
    "nmf-overlay","nmf-drawer","nmf-btn",
    "nm-overlay","nm-drawer","nm-bar","nm-list","nm-pills","nm-topics-btn",
    "nm3-ov","nm3-dr","nm3-bar","nm3-ls","nm3-pl","nm3-tb",
    "mob-overlay","mob-sidebar-close","mob-topics-btn",
    "ccna-topics-btn","ccna-panel-close","ccna-topics-bar",
    "net-mob-bar","net-mob-drawer",
]
OLD_COMMENTS = [
    "<!-- SHN-v3 -->","<!-- SHN-PATCH -->","<!-- CCNA-MOBILE-FIX -->",
    "<!-- NET-MOBILE-FIX-v1 -->","<!-- NET-MOB-v2 -->","<!-- NM-FIX-CLEAN -->",
    "<!-- STUDYHUB-MOBILE-v4 -->","<!-- STUDYHUB-MOBILE-v3 -->",
    "<!-- STUDYHUB-MASTER-v1 -->",  # strip self too before re-inject
]

def strip_all(html):
    for sid in OLD_STYLE_IDS:
        html = re.sub(
            r"<style[^>]+id=['\"]" + re.escape(sid) + r"['\"][^>]*>.*?</style>",
            "", html, flags=re.DOTALL | re.I)
    for sid in OLD_SCRIPT_IDS:
        html = re.sub(
            r"<script[^>]+id=['\"]" + re.escape(sid) + r"['\"][^>]*>.*?</script>",
            "", html, flags=re.DOTALL | re.I)
    for eid in OLD_DIV_IDS:
        # Remove element and its children
        html = re.sub(
            r"<(?:div|nav|button|a|aside)\b[^>]*\bid=['\"]" + re.escape(eid)
            + r"['\"][^>]*>.*?</(?:div|nav|button|a|aside)>",
            "", html, flags=re.DOTALL | re.I)
        # Lone opening tags / self-closing
        html = re.sub(
            r"<[^>]+\bid=['\"]" + re.escape(eid) + r"['\"][^>]*>",
            "", html, flags=re.I)
    for m in OLD_COMMENTS:
        html = html.replace(m, "")
    html = re.sub(r'\n{4,}', '\n\n', html)
    return html

# ═══════════════════════════════════════════════════════════════════
#  DETECT layout type from CSS inside the page
# ═══════════════════════════════════════════════════════════════════
def detect_type(html):
    css = " ".join(re.findall(r'<style[^>]*>(.*?)</style>', html,
                               re.DOTALL | re.I))
    has_toggle   = "toggleSidebar" in html
    has_flex_sb  = bool(re.search(r'\.sidebar\s*\{[^}]*width\s*:\s*240px', css))
    has_fixed_sb = bool(re.search(r'\.sidebar\s*\{[^}]*position\s*:\s*fixed', css)
                        and re.search(r'--sidebar-w\s*:\s*260px', css))
    has_cat_nav  = ".cat-nav" in css
    has_topic_btn= ".topic-btn" in css
    has_nav_item = ".nav-item" in css
    has_proto_tab= ".proto-tab" in css

    if has_toggle:
        return "D"               # Nutanix — already has mobile toggle
    if has_fixed_sb and has_proto_tab:
        return "B"               # Network Study Reference
    if (has_flex_sb and has_cat_nav) or (has_flex_sb and has_topic_btn):
        return "A"               # CCNA / Linux / OS Admin / Master / RHEL
    # Fallback: ITIL-style continuous scroll
    return "C"

# ═══════════════════════════════════════════════════════════════════
#  BUILD the CSS+HTML+JS injection per type
# ═══════════════════════════════════════════════════════════════════

# ── Common drawer CSS (shared by TYPE-A and TYPE-B) ───────────────
DRAWER_CSS = """
/* ── Sticky bottom bar ──────────────────────────────────── */
#shub-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  z-index: 8000;
  background: var(--surface, #111827);
  border-top: 1px solid var(--border, #1e2d45);
  display: flex; align-items: center;
  padding: 8px 10px; gap: 7px;
  box-shadow: 0 -4px 20px rgba(0,0,0,.5);
}
#shub-pills {
  display: flex; gap: 5px; overflow-x: auto; flex: 1;
  scrollbar-width: none; -webkit-overflow-scrolling: touch;
}
#shub-pills::-webkit-scrollbar { display: none; }
.shub-pill {
  flex-shrink: 0; padding: 6px 12px; border-radius: 20px;
  border: 1px solid var(--border, #1e2d45);
  background: transparent; color: var(--text-dim, #7a8ba8);
  font-family: var(--font, system-ui); font-size: 11px;
  font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
  cursor: pointer; white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}
.shub-pill-active {
  background: rgba(0,201,255,.12) !important;
  border-color: var(--accent, #00c9ff) !important;
  color: var(--accent, #00c9ff) !important;
}
#shub-tbtn {
  flex-shrink: 0; background: var(--accent, #00c9ff);
  color: #0a0e1a; border: none; border-radius: 8px;
  padding: 9px 14px; font-size: 12px; font-weight: 700;
  cursor: pointer; white-space: nowrap; display: flex;
  align-items: center; gap: 5px;
  -webkit-tap-highlight-color: transparent;
}

/* ── Overlay + drawer ───────────────────────────────────── */
#shub-ov {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.75); z-index: 8100;
}
#shub-ov.on { display: block; }
#shub-dr {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: min(290px, 86vw);
  background: var(--surface, #111827);
  border-right: 1px solid var(--border, #1e2d45);
  z-index: 8200; display: flex; flex-direction: column;
  transform: translateX(-100%);
  transition: transform .26s cubic-bezier(.4,0,.2,1);
}
#shub-dr.on { transform: translateX(0); }
#shub-dhead {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 15px; border-bottom: 1px solid var(--border, #1e2d45);
  background: var(--surface2, #1a2236); flex-shrink: 0;
}
#shub-dtitle {
  font-size: 11px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--text-dim, #7a8ba8);
  font-family: var(--font, system-ui);
}
#shub-dclose {
  background: rgba(255,255,255,.07); border: 1px solid var(--border,#1e2d45);
  border-radius: 7px; color: var(--text-dim,#7a8ba8); width: 30px; height: 30px;
  font-size: 15px; cursor: pointer; display: flex; align-items: center;
  justify-content: center; -webkit-tap-highlight-color: transparent;
}
#shub-back {
  display: flex; align-items: center; gap: 8px; padding: 11px 15px;
  color: #e3b341; text-decoration: none; font-size: 12.5px; font-weight: 600;
  border-bottom: 1px solid var(--border,#1e2d45);
  background: rgba(227,179,65,.05); flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
#shub-list {
  overflow-y: auto; flex: 1;
  -webkit-overflow-scrolling: touch; padding: 4px 0 70px;
}
#shub-list::-webkit-scrollbar { width: 3px; }
#shub-list::-webkit-scrollbar-thumb { background: var(--border,#1e2d45); }
.shub-sec {
  padding: 11px 15px 2px; font-size: 9px; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  color: var(--text-muted, #3d5068); font-family: var(--font, system-ui);
}
.shub-it {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 10px 15px; border: none;
  border-left: 3px solid transparent;
  background: transparent; text-align: left;
  color: var(--text-dim, #7a8ba8);
  font-family: var(--font, system-ui); font-size: 13px;
  cursor: pointer; line-height: 1.35; box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}
.shub-it:active { background: var(--surface2, #1a2236); }
.shub-it.shub-cur {
  background: var(--surface2, #1a2236);
  color: var(--text, #e2e8f0);
  border-left-color: var(--accent, #00c9ff);
}
.shub-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; opacity: .4; flex-shrink: 0;
}
.shub-it.shub-cur .shub-dot { opacity: 1; }

/* ── Desktop: hide mobile chrome ────────────────────────── */
@media (min-width: 769px) {
  #shub-bar, #shub-ov, #shub-dr { display: none !important; }
}
"""

# ── Common drawer HTML ────────────────────────────────────────────
DRAWER_HTML = """
<div id="shub-ov"></div>
<nav id="shub-dr">
  <div id="shub-dhead">
    <span id="shub-dtitle">Topics</span>
    <button id="shub-dclose">&#10005;</button>
  </div>
  <a id="shub-back" href="index.html">&#8592; Study Hub</a>
  <div id="shub-list"></div>
</nav>
<div id="shub-bar">
  <div id="shub-pills"></div>
  <button id="shub-tbtn">&#9776; Topics</button>
</div>
"""

# ── Common drawer JS ──────────────────────────────────────────────
def drawer_js(btn_sel, item_sel, section_label_sel=""):
    """
    btn_sel:          CSS selector for page's own category/tab buttons
    item_sel:         CSS selector for page's own topic/nav buttons
    section_label_sel: optional selector for section labels inside sidebar
    """
    return f"""
<script id="shub-master-js">
(function(){{
  if(window.innerWidth > 768) return;
  var ov=document.getElementById('shub-ov'),
      dr=document.getElementById('shub-dr'),
      dc=document.getElementById('shub-dclose'),
      tb=document.getElementById('shub-tbtn'),
      ls=document.getElementById('shub-list'),
      pl=document.getElementById('shub-pills');
  if(!dr||!tb) return;

  function open(){{dr.classList.add('on');ov.classList.add('on');
    document.body.style.overflow='hidden';tb.innerHTML='&#10005; Close';}}
  function close(){{dr.classList.remove('on');ov.classList.remove('on');
    document.body.style.overflow='';tb.innerHTML='&#9776; Topics';}}
  tb.addEventListener('click',function(){{dr.classList.contains('on')?close():open();}});
  dc.addEventListener('click',close);
  ov.addEventListener('click',close);
  document.addEventListener('keydown',function(e){{if(e.key==='Escape')close();}});

  var built=false;
  function build(){{
    if(built)return;
    var items=document.querySelectorAll('{item_sel}');
    if(!items.length)return;
    built=true; ls.innerHTML='';
    items.forEach(function(orig){{
      var b=document.createElement('button');
      b.className='shub-it';
      var d=document.createElement('span');d.className='shub-dot';
      b.appendChild(d);
      b.appendChild(document.createTextNode(orig.textContent.trim()));
      b.addEventListener('click',function(){{orig.click();setTimeout(close,180);}});
      ls.appendChild(b);
    }});
    sync();
  }}

  function sync(){{
    var active=document.querySelector('{item_sel}.active');
    var at=active?active.textContent.trim():'';
    ls.querySelectorAll('.shub-it').forEach(function(it){{
      it.classList.toggle('shub-cur',it.textContent.trim()===at);
    }});
  }}

  function buildPills(){{
    var tabs=document.querySelectorAll('{btn_sel}');
    if(!tabs.length||pl.children.length)return;
    tabs.forEach(function(tab){{
      var p=document.createElement('button');
      p.className='shub-pill';
      p.textContent=tab.textContent.trim();
      if(tab.classList.contains('active'))p.classList.add('shub-pill-active');
      p.addEventListener('click',function(){{
        tab.click();
        setTimeout(function(){{built=false;build();syncPills();}},80);
      }});
      pl.appendChild(p);
    }});
  }}

  function syncPills(){{
    var tabs=document.querySelectorAll('{btn_sel}');
    pl.querySelectorAll('.shub-pill').forEach(function(pill,i){{
      pill.classList.toggle('shub-pill-active',
        !!(tabs[i]&&tabs[i].classList.contains('active')));
    }});
  }}

  new MutationObserver(function(){{sync();syncPills();}})
    .observe(document.body,{{childList:true,subtree:true,
      attributes:true,attributeFilter:['class']}});

  function init(){{
    build();buildPills();
    if(!built){{
      var n=0,t=setInterval(function(){{
        build();buildPills();
        if(built||++n>40)clearInterval(t);
      }},100);
    }}
  }}
  document.readyState==='loading'
    ?document.addEventListener('DOMContentLoaded',function(){{setTimeout(init,200);}})
    :setTimeout(init,200);
}})();
</script>"""

# ── TYPE-A injection: CCNA/Linux/OS/Master/RHEL ──────────────────
def build_type_a(html):
    """
    .main{display:flex} .sidebar{width:240px} .content{flex:1}
    .cat-nav or .section-nav for tabs
    .topic-btn for items
    """
    # Detect tab selector
    tab_sel  = ".cat-btn" if ".cat-btn" in html else ".section-btn"
    item_sel = ".topic-btn" if ".topic-btn" in html else ".nav-item"

    css = f"""<style id="shub-a-css">
@media (max-width: 768px) {{
  /* Layout: stack vertically */
  .main {{ display: block !important; height: auto !important; overflow: visible !important; }}
  /* Sidebar hidden — replaced by drawer */
  .sidebar {{ display: none !important; }}
  /* Content full width */
  .content {{
    width: 100% !important; max-width: 100vw !important;
    padding: 16px 14px 110px !important; overflow-x: hidden !important;
    box-sizing: border-box !important; height: auto !important;
    overflow-y: visible !important;
  }}
  /* Tab bar: horizontal scroll */
  .cat-nav, .section-nav {{
    display: flex !important; overflow-x: auto !important;
    flex-wrap: nowrap !important; gap: 2px !important;
    scrollbar-width: none !important; padding-bottom: 2px !important;
    -webkit-overflow-scrolling: touch !important;
  }}
  .cat-nav::-webkit-scrollbar {{ display: none !important; }}
  .cat-btn, .section-btn {{
    flex-shrink: 0 !important; font-size: 11px !important;
    padding: 7px 10px !important;
  }}
  /* Header compact */
  header {{ padding: 16px 14px 0 !important; }}
  .header-top {{ flex-wrap: wrap !important; gap: 8px !important; }}
  .subtitle {{ display: none !important; }}
  /* Prevent horizontal overflow */
  body {{ overflow-x: hidden !important; }}
  pre, code {{ overflow-x: auto !important; font-size: 11px !important;
    -webkit-overflow-scrolling: touch !important; }}
  table {{ display: block !important; overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important; font-size: 12px !important; }}
  .cards {{ grid-template-columns: 1fr !important; }}
  .tbl {{ overflow-x: auto !important; }}
  h1 {{ font-size: clamp(1.4rem, 7vw, 1.9rem) !important; }}
  h2 {{ font-size: clamp(1rem, 5vw, 1.3rem) !important; }}

{DRAWER_CSS}
}}
</style>"""
    return css + DRAWER_HTML + drawer_js(tab_sel, item_sel)


# ── TYPE-B injection: Network Study Reference ────────────────────
def build_type_b(html):
    css = f"""<style id="shub-b-css">
@media (max-width: 768px) {{
  /* Fixed sidebar hidden */
  .sidebar {{ display: none !important; }}
  /* Content full width */
  .content {{
    margin-left: 0 !important; padding: 16px 14px 110px !important;
    max-width: 100vw !important; box-sizing: border-box !important;
    overflow-x: hidden !important;
  }}
  .layout {{ display: block !important; min-height: auto !important; }}
  /* Header: proto-tabs hidden, replaced by drawer pills */
  .proto-tabs {{ display: none !important; }}
  header {{ padding: 0 10px !important; gap: 8px !important; }}
  .brand-text {{ font-size: 12px !important; }}
  .brand-icon {{ width: 26px !important; height: 26px !important; font-size: 13px !important; }}
  .search-box {{ flex: 1 !important; max-width: 100% !important; min-width: 0 !important; }}
  .search-box input {{ font-size: 14px !important; }}
  pre {{ font-size: 11px !important; overflow-x: auto !important; }}
  code {{ font-size: 10.5px !important; }}
  .tbl {{ overflow-x: auto !important; }}
  table {{ display: block !important; overflow-x: auto !important; }}
  .cards {{ grid-template-columns: 1fr !important; }}
  .panel h1 {{ font-size: 20px !important; }}
  .panel h2 {{ font-size: 15px !important; }}
  body {{ overflow-x: hidden !important; }}

{DRAWER_CSS}
}}
</style>"""
    return css + DRAWER_HTML + drawer_js(".proto-tab", ".nav-item")


# ── TYPE-C injection: ITIL continuous scroll ──────────────────────
def build_type_c(html):
    # ITIL page: no sidebar panel-switch JS, it's a continuous scroll page
    # with a left nav that anchors to sections. Make it a sticky top nav.
    css = """<style id="shub-c-css">
@media (max-width: 768px) {
  /* Any fixed left nav: hidden on mobile */
  .left-nav, .side-nav, .app-sidebar, #sidebar,
  [class*="left-nav"], [class*="side-nav"] {
    display: none !important;
  }
  /* Main content full width */
  .app-container, .main-container, .content-wrap,
  [class*="app-container"], [class*="main-container"] {
    display: block !important; margin-left: 0 !important;
    grid-template-columns: 1fr !important;
  }
  .main-content, .content-area, .app-content,
  [class*="main-content"], [class*="content-area"] {
    width: 100% !important; max-width: 100vw !important;
    padding: 16px 14px 80px !important;
    box-sizing: border-box !important; margin-left: 0 !important;
  }
  body { overflow-x: hidden !important; }

  /* Nav pills in header or tab bars: scroll */
  .nav-pills, .topic-pills, .filter-bar, .process-nav,
  [class*="nav-pills"], [class*="filter-bar"] {
    display: flex !important; overflow-x: auto !important;
    flex-wrap: nowrap !important; gap: 6px !important;
    scrollbar-width: none !important;
    -webkit-overflow-scrolling: touch !important;
    padding-bottom: 4px !important;
  }

  /* Tables */
  table { display: block !important; overflow-x: auto !important;
    font-size: 12px !important; -webkit-overflow-scrolling: touch !important; }
  th { white-space: nowrap !important; }

  /* Code */
  pre, code { overflow-x: auto !important; font-size: 11px !important;
    -webkit-overflow-scrolling: touch !important; }

  /* Lifecycle / flow arrows wrap */
  .lifecycle, [class*="lifecycle"], .workflow, [class*="workflow"] {
    flex-wrap: wrap !important; gap: 6px !important;
  }

  /* Process/command grids: single column */
  .process-grid, .cmd-grid, [class*="process-grid"], [class*="cmd-grid"],
  .grid-2, .two-col, [class*="two-col"] {
    grid-template-columns: 1fr !important; gap: 12px !important;
  }

  /* Cards */
  .cards, .card-grid, [class*="card-grid"] {
    grid-template-columns: 1fr !important; }

  h1 { font-size: clamp(1.4rem, 7vw, 1.9rem) !important; }
  h2 { font-size: clamp(1rem, 5vw, 1.3rem) !important; }
  h3 { font-size: clamp(0.9rem, 4vw, 1.05rem) !important; }

  /* Sticky mini-nav button for ITIL */
  #shub-c-btn {
    position: fixed; bottom: 16px; right: 16px; z-index: 8000;
    background: #B87FFF; color: #0d0d0d; border: none;
    border-radius: 50px; padding: 12px 18px; font-size: 13px;
    font-weight: 700; cursor: pointer; display: flex; align-items: center;
    gap: 6px; box-shadow: 0 4px 20px rgba(184,127,255,.4);
    -webkit-tap-highlight-color: transparent;
  }
  #shub-c-ov {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,.75); z-index: 8100;
  }
  #shub-c-ov.on { display: block; }
  #shub-c-dr {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: min(280px, 85vw);
    background: #0d0d18; border-right: 1px solid #2A2A4A;
    z-index: 8200; display: flex; flex-direction: column;
    transform: translateX(-100%);
    transition: transform .26s cubic-bezier(.4,0,.2,1);
    overflow: hidden;
  }
  #shub-c-dr.on { transform: translateX(0); }
  #shub-c-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 13px 15px; border-bottom: 1px solid #2A2A4A;
    background: rgba(255,255,255,.03); flex-shrink: 0;
  }
  #shub-c-title {
    font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #8B8BAA; font-family: system-ui;
  }
  #shub-c-close {
    background: rgba(255,255,255,.07); border: 1px solid #2A2A4A;
    border-radius: 7px; color: #8B8BAA; width: 30px; height: 30px;
    font-size: 15px; cursor: pointer; display: flex; align-items: center;
    justify-content: center; -webkit-tap-highlight-color: transparent;
  }
  #shub-c-back {
    display: flex; align-items: center; gap: 8px; padding: 11px 15px;
    color: #e3b341; text-decoration: none; font-size: 12.5px; font-weight: 600;
    border-bottom: 1px solid #2A2A4A; background: rgba(227,179,65,.05);
    flex-shrink: 0; -webkit-tap-highlight-color: transparent;
  }
  #shub-c-list {
    overflow-y: auto; flex: 1; -webkit-overflow-scrolling: touch;
    padding: 4px 0 40px;
  }
  #shub-c-list::-webkit-scrollbar { width: 3px; }
  #shub-c-list::-webkit-scrollbar-thumb { background: #2A2A4A; }
  .shub-c-it {
    display: block; width: 100%; padding: 10px 15px; border: none;
    border-left: 3px solid transparent; background: transparent;
    text-align: left; color: #8B8BAA; font-family: system-ui;
    font-size: 13px; cursor: pointer; line-height: 1.35;
    box-sizing: border-box; -webkit-tap-highlight-color: transparent;
    text-decoration: none;
  }
  .shub-c-it:active { background: rgba(255,255,255,.04); }
  .shub-c-it:hover { color: #fff; border-left-color: #B87FFF; }

  @media (min-width: 769px) {
    #shub-c-btn, #shub-c-ov, #shub-c-dr { display: none !important; }
  }
}
</style>"""

    html_inject = """
<div id="shub-c-ov"></div>
<nav id="shub-c-dr">
  <div id="shub-c-head">
    <span id="shub-c-title">Navigate</span>
    <button id="shub-c-close">&#10005;</button>
  </div>
  <a id="shub-c-back" href="index.html">&#8592; Study Hub</a>
  <div id="shub-c-list"></div>
</nav>
<button id="shub-c-btn">&#9776; Navigate</button>
"""
    js = """
<script id="shub-c-js">
(function(){
  if(window.innerWidth > 768) return;
  var ov=document.getElementById('shub-c-ov'),
      dr=document.getElementById('shub-c-dr'),
      dc=document.getElementById('shub-c-close'),
      btn=document.getElementById('shub-c-btn'),
      lst=document.getElementById('shub-c-list');
  if(!dr||!btn) return;

  function open(){dr.classList.add('on');ov.classList.add('on');
    document.body.style.overflow='hidden';btn.innerHTML='&#10005; Close';}
  function close(){dr.classList.remove('on');ov.classList.remove('on');
    document.body.style.overflow='';btn.innerHTML='&#9776; Navigate';}
  btn.addEventListener('click',function(){dr.classList.contains('on')?close():open();});
  dc.addEventListener('click',close);
  ov.addEventListener('click',close);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});

  /* Build nav from page's h2 headings (ITIL-style continuous scroll) */
  var headings = document.querySelectorAll('h2[id], section[id] > h2, .process-section h2');
  if(!headings.length) headings = document.querySelectorAll('h2');
  var n=0;
  headings.forEach(function(h){
    var id = h.id || (h.closest('[id]') ? h.closest('[id]').id : '');
    if(!id){ id='shub-h-'+(++n); h.id=id; }
    var a=document.createElement('a');
    a.className='shub-c-it';
    a.href='#'+id;
    a.textContent=h.textContent.trim().slice(0,60);
    a.addEventListener('click',function(){setTimeout(close,200);});
    lst.appendChild(a);
  });

  /* Also add left-nav links if they exist */
  var navLinks = document.querySelectorAll('.left-nav a, .side-nav a, #left-nav a, [class*="left-nav"] a');
  if(navLinks.length && !headings.length){
    navLinks.forEach(function(a){
      var item=document.createElement('a');
      item.className='shub-c-it';
      item.href=a.href; item.textContent=a.textContent.trim();
      item.addEventListener('click',function(){setTimeout(close,200);});
      lst.appendChild(item);
    });
  }
})();
</script>"""
    return css + html_inject + js


# ── TYPE-D injection: Nutanix — fix tables only ───────────────────
def build_type_d(html):
    return """<style id="shub-d-css">
@media (max-width: 768px) {
  /* Nutanix has its own toggle — just fix overflow issues */
  .main {
    margin-left: 0 !important; max-width: 100vw !important;
    padding: 1rem 14px 3rem !important;
  }
  .progress-bar { left: 0 !important; }
  .topbar-search { display: none !important; }
  .cover { padding: 20px 14px !important; }
  .cover h1 { font-size: clamp(1.8rem,8vw,2.8rem) !important; }
  .cheatsheet-grid { grid-template-columns: 1fr !important; }
  .card-grid { grid-template-columns: 1fr !important; }
  .card-featured { flex-direction: column !important; }
  /* Def-table: stack term above definition */
  .def-table tr { display: flex !important; flex-direction: column !important; }
  .def-table td { display: block !important; width: 100% !important;
    box-sizing: border-box !important; }
  .term-cell {
    width: 100% !important; border-right: none !important;
    border-bottom: 1px solid rgba(100,150,220,.2) !important;
    font-size: .79rem !important; padding: 7px 10px 4px !important;
  }
  .def-cell {
    width: 100% !important; border-top: none !important;
    font-size: .79rem !important; padding: 4px 10px 10px !important;
  }
  /* Data tables: scroll */
  .data-table { display: block !important; overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important; }
  table { max-width: 100% !important; }
  pre, .code-group, .code-block {
    overflow-x: auto !important; font-size: .7rem !important;
    -webkit-overflow-scrolling: touch !important;
  }
  .code-line { font-size: .68rem !important; }
  .section-divider { flex-wrap: wrap !important; padding: 10px 12px !important; }
  .section-divider h2 { font-size: .82rem !important; }
  .quickjump { flex-wrap: wrap !important; gap: 6px !important; }
  .step-text { font-size: .86rem !important; }
  li { font-size: .87rem !important; }
}
</style>"""


# ═══════════════════════════════════════════════════════════════════
#  PATCH a single file
# ═══════════════════════════════════════════════════════════════════
def patch(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        original = f.read()

    # Strip all old patches
    html = strip_all(original)

    # Detect layout
    ptype = detect_type(html)

    # Build the appropriate injection
    if   ptype == "A": injection = build_type_a(html)
    elif ptype == "B": injection = build_type_b(html)
    elif ptype == "C": injection = build_type_c(html)
    else:              injection = build_type_d(html)

    # Wrap with master marker
    full_inject = f"\n{MASTER_MARK}\n{injection}\n"

    # Inject before </body>
    if re.search(r'</body>', html, re.I):
        html = re.sub(r'(</body>)', full_inject + r'\1', html, count=1, flags=re.I)
    else:
        html += full_inject

    if dry:
        removed = len(original) - len(strip_all(original))
        print(f"  {C('○')}  {fname}")
        print(f"     {D(f'Type-{ptype}  |  stripped {removed:,} chars old patches')}")
        return 'dry'

    shutil.copy2(path, path + BACKUP_EXT)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  {G('✔')}  {fname}  {D(f'[Type-{ptype}]')}")
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
    print(B("  ╔══════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub Universal Mobile Patcher           ║"))
    print(B("  ║  Strips all old patches → applies clean fix  ║"))
    print(B("  ╚══════════════════════════════════════════════╝"))
    print(f"\n  Dir : {C(wd)}")
    print(f"  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('PATCH'))}\n")

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not f.endswith('.bak')
        and f not in SKIP_FILES
    )

    if not files:
        print(Y("  ⚠  No HTML files found.\n")); sys.exit(0)

    print(f"  {B(str(len(files)))} file(s) to process:\n")
    counts = {}
    for fp in files:
        r = undo(fp) if rev else patch(fp, dry)
        counts[r] = counts.get(r, 0) + 1

    print(f"\n  {'─'*48}")
    if rev:
        print(f"  {G('Restored')}: {counts.get('ok',0)}   {Y('No backup')}: {counts.get('skip',0)}")
    elif dry:
        print(f"  {C('Would patch')}: {counts.get('dry',0)}")
    else:
        print(f"  {G('Patched')}: {counts.get('patched',0)}   {Y('Skipped')}: {counts.get('skip',0)}")

    if not rev and not dry and counts.get('patched', 0):
        git_msg = 'git commit -m "Universal mobile fix — all pages"'
        print(f"\n  {G('Done! Push to GitHub:')}")
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")
    print()


if __name__ == '__main__':
    main()
