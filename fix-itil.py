#!/usr/bin/env python3
"""
fix_rhel_itil.py
────────────────────────────────────────────────────────────────
Targeted mobile fix for exactly two pages, using confirmed
class names from their actual source code:

RHEL Study Guide  (rhel study guide.html)
  Layout: .container{display:flex} .sidebar{width:260px} .content{flex:1}
  Nav:    .nav-btn buttons (JS-driven panel switch)
  Labels: .sidebar-section

ITIL Unix Interview Prep  (itil-unix-interview-prep.html)
  Layout: .main-grid{display:grid; grid-template-columns:280px 1fr}
  Sidebar: .sidebar {position:sticky} .sidebar-link anchors
  Nav bar: .nav-bar .nav-scroll .nav-item (sticky tab bar at top)
  Content: Continuous scroll — sidebar-link = anchor to section id

Usage:
  cd ~/Studyhtml
  python3 fix_rhel_itil.py            # apply both fixes
  python3 fix_rhel_itil.py --undo     # restore backups
  python3 fix_rhel_itil.py --dry-run  # preview only
"""
import os, sys, re, shutil

BACKUP_EXT = ".bak"

def c(t, code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t, "0;32")
Y = lambda t: c(t, "0;33")
R = lambda t: c(t, "0;31")
C = lambda t: c(t, "0;36")
B = lambda t: c(t, "1;37")
D = lambda t: c(t, "0;90")

# ── Strip ALL previous patch IDs/markers ────────────────────────
OLD_STYLE_IDS  = ["shm-v4","shn-styles","shn-page-mobile","ccna-mobile-style",
                   "net-mob-css","nm-fix-css","nm3-css","mob-fix-css",
                   "shub-a-css","shub-b-css","shub-c-css","shub-d-css",
                   "rhel-mob-css","itil-mob-css"]
OLD_SCRIPT_IDS = ["shm-js","shn-js","ccna-mobile-script","net-mob-js",
                   "nm-fix-js","nm3-js","mob-fix-js","shub-master-js",
                   "rhel-mob-js","itil-mob-js","shub-c-js"]
OLD_EL_IDS     = ["shn-overlay","shn-nav","shn-btn",
                   "nmf-overlay","nmf-drawer","nmf-btn",
                   "nm-overlay","nm-drawer","nm-bar","nm-list","nm-pills","nm-topics-btn",
                   "nm3-ov","nm3-dr","nm3-bar","nm3-ls","nm3-pl","nm3-tb",
                   "mob-overlay","mob-sidebar-close","mob-topics-btn",
                   "shub-ov","shub-dr","shub-bar","shub-list","shub-pills","shub-tbtn",
                   "shub-c-btn","shub-c-ov","shub-c-dr","shub-c-list","shub-c-head",
                   "shub-c-close","shub-c-back","shub-c-title",
                   "rhel-ov","rhel-dr","rhel-bar","rhel-list","rhel-pills","rhel-tbtn",
                   "itil-ov","itil-dr","itil-bar","itil-nav-btn"]
OLD_COMMENTS   = ["<!-- SHN-v3 -->","<!-- SHN-PATCH -->","<!-- CCNA-MOBILE-FIX -->",
                   "<!-- NET-MOBILE-FIX-v1 -->","<!-- NET-MOB-v2 -->","<!-- NM-FIX-CLEAN -->",
                   "<!-- STUDYHUB-MOBILE-v4 -->","<!-- STUDYHUB-MOBILE-v3 -->",
                   "<!-- STUDYHUB-MASTER-v1 -->","<!-- RHEL-MOB -->","<!-- ITIL-MOB -->"]

def strip_all(html):
    for sid in OLD_STYLE_IDS:
        html = re.sub(
            r"<style[^>]+id=['\"]" + re.escape(sid) + r"['\"][^>]*>.*?</style>",
            "", html, flags=re.DOTALL | re.I)
    for sid in OLD_SCRIPT_IDS:
        html = re.sub(
            r"<script[^>]+id=['\"]" + re.escape(sid) + r"['\"][^>]*>.*?</script>",
            "", html, flags=re.DOTALL | re.I)
    for eid in OLD_EL_IDS:
        html = re.sub(
            r"<(?:div|nav|button|a|aside)\b[^>]*\bid=['\"]" + re.escape(eid)
            + r"['\"][^>]*>.*?</(?:div|nav|button|a|aside)>",
            "", html, flags=re.DOTALL | re.I)
        html = re.sub(
            r"<[^>]+\bid=['\"]" + re.escape(eid) + r"['\"][^>]*>",
            "", html, flags=re.I)
    for m in OLD_COMMENTS:
        html = html.replace(m, "")
    html = re.sub(r'\n{4,}', '\n\n', html)
    return html


# ════════════════════════════════════════════════════════════════
#  RHEL STUDY GUIDE FIX
#  Exact class names from source:
#    .container { display:flex }
#    .sidebar   { width:260px; min-width:220px }
#    .content   { flex:1 }
#    .nav-btn   { topic switch buttons }
#    .sidebar-section { section label divs }
#    No cat-nav — uses sidebar-section labels only
# ════════════════════════════════════════════════════════════════
RHEL_CSS = """<style id="rhel-mob-css">
@media (max-width: 768px) {
  /* ── Layout: flex → block ─────────────────────────────── */
  .container {
    display: block !important;
    height: auto !important;
    overflow: visible !important;
  }

  /* ── Sidebar: hidden, replaced by drawer ──────────────── */
  .sidebar {
    display: none !important;
  }

  /* ── Content: full width ──────────────────────────────── */
  .content {
    width: 100% !important;
    max-width: 100vw !important;
    padding: 16px 14px 110px !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
    overflow-y: visible !important;
    height: auto !important;
  }

  /* ── Header compact ───────────────────────────────────── */
  .header {
    padding: 14px 14px 10px !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
  }
  .header-text h1 { font-size: 1.1rem !important; }
  .header-text p  { font-size: .75rem !important; }

  /* ── Body overflow guard ──────────────────────────────── */
  body { overflow-x: hidden !important; }

  /* ── Code / pre ───────────────────────────────────────── */
  pre {
    overflow-x: auto !important;
    font-size: .75rem !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 10px 12px !important;
  }
  code { font-size: .72rem !important; }

  /* ── Tables ───────────────────────────────────────────── */
  table {
    display: block !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    font-size: .78rem !important;
  }
  th { white-space: nowrap !important; }

  /* ── Cards ────────────────────────────────────────────── */
  .card { padding: 12px 14px !important; }

  /* ── Headings ─────────────────────────────────────────── */
  h2 { font-size: 1.2rem !important; }
  h3 { font-size: .95rem !important; }

  /* ════ BOTTOM BAR ══════════════════════════════════════ */
  #rhel-bar {
    position: fixed !important;
    bottom: 0 !important; left: 0 !important; right: 0 !important;
    z-index: 8000 !important;
    background: var(--surface, #161b22) !important;
    border-top: 2px solid var(--accent, #e74c3c) !important;
    display: flex !important;
    align-items: center !important;
    padding: 8px 10px !important;
    gap: 8px !important;
    box-shadow: 0 -4px 20px rgba(0,0,0,.6) !important;
  }
  #rhel-pills {
    display: flex !important; gap: 5px !important;
    overflow-x: auto !important; flex: 1 !important;
    scrollbar-width: none !important;
    -webkit-overflow-scrolling: touch !important;
  }
  #rhel-pills::-webkit-scrollbar { display: none !important; }
  .rhel-pill {
    flex-shrink: 0 !important;
    padding: 6px 12px !important;
    border-radius: 20px !important;
    border: 1px solid var(--border, #30363d) !important;
    background: transparent !important;
    color: var(--text-dim, #8b949e) !important;
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: .06em !important; text-transform: uppercase !important;
    cursor: pointer !important; white-space: nowrap !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  .rhel-pill-on {
    background: rgba(231,76,60,.15) !important;
    border-color: var(--accent, #e74c3c) !important;
    color: var(--accent, #e74c3c) !important;
  }
  #rhel-tbtn {
    flex-shrink: 0 !important;
    background: var(--accent, #e74c3c) !important;
    color: #fff !important; border: none !important;
    border-radius: 8px !important; padding: 9px 14px !important;
    font-size: 12px !important; font-weight: 700 !important;
    cursor: pointer !important; white-space: nowrap !important;
    display: flex !important; align-items: center !important; gap: 5px !important;
    -webkit-tap-highlight-color: transparent !important;
  }

  /* ════ DRAWER ══════════════════════════════════════════ */
  #rhel-ov {
    display: none; position: fixed !important; inset: 0 !important;
    background: rgba(0,0,0,.78) !important; z-index: 8100 !important;
  }
  #rhel-ov.on { display: block !important; }

  #rhel-dr {
    position: fixed !important; top: 0 !important; left: 0 !important;
    bottom: 0 !important; width: min(280px, 85vw) !important;
    background: var(--surface, #161b22) !important;
    border-right: 2px solid var(--accent, #e74c3c) !important;
    z-index: 8200 !important; display: flex !important;
    flex-direction: column !important;
    transform: translateX(-100%) !important;
    transition: transform .26s cubic-bezier(.4,0,.2,1) !important;
  }
  #rhel-dr.on { transform: translateX(0) !important; }

  #rhel-dhead {
    display: flex !important; align-items: center !important;
    justify-content: space-between !important;
    padding: 14px 16px !important;
    border-bottom: 1px solid var(--border, #30363d) !important;
    background: var(--surface2, #1c2330) !important;
    flex-shrink: 0 !important;
  }
  #rhel-dtitle {
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: .1em !important; text-transform: uppercase !important;
    color: var(--accent, #e74c3c) !important;
  }
  #rhel-dclose {
    background: rgba(255,255,255,.06) !important;
    border: 1px solid var(--border, #30363d) !important;
    border-radius: 7px !important; color: #aaa !important;
    width: 30px !important; height: 30px !important; font-size: 15px !important;
    cursor: pointer !important; display: flex !important;
    align-items: center !important; justify-content: center !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  #rhel-back {
    display: flex !important; align-items: center !important; gap: 8px !important;
    padding: 11px 16px !important; color: #f39c12 !important;
    text-decoration: none !important; font-size: 12.5px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid var(--border, #30363d) !important;
    background: rgba(243,156,18,.05) !important; flex-shrink: 0 !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  #rhel-list {
    overflow-y: auto !important; flex: 1 !important;
    -webkit-overflow-scrolling: touch !important; padding: 4px 0 60px !important;
  }
  #rhel-list::-webkit-scrollbar { width: 3px !important; }
  #rhel-list::-webkit-scrollbar-thumb { background: var(--border, #30363d) !important; }
  .rhel-sec {
    padding: 10px 16px 3px !important; font-size: 9px !important;
    font-weight: 700 !important; letter-spacing: .14em !important;
    text-transform: uppercase !important;
    color: var(--text-dim, #8b949e) !important;
  }
  .rhel-it {
    display: flex !important; align-items: center !important; gap: 8px !important;
    width: 100% !important; padding: 9px 16px !important;
    border: none !important; border-left: 3px solid transparent !important;
    background: transparent !important; text-align: left !important;
    color: var(--text-dim, #8b949e) !important; font-size: 13px !important;
    cursor: pointer !important; line-height: 1.35 !important;
    box-sizing: border-box !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  .rhel-it:active { background: var(--surface2, #1c2330) !important; }
  .rhel-it.on {
    background: var(--surface2, #1c2330) !important; color: #fff !important;
    border-left-color: var(--accent, #e74c3c) !important; font-weight: 600 !important;
  }
  .rhel-num {
    font-size: .7rem !important; color: var(--accent, #e74c3c) !important;
    font-weight: 700 !important; min-width: 20px !important;
  }
}
@media (min-width: 769px) {
  #rhel-bar, #rhel-ov, #rhel-dr { display: none !important; }
}
</style>"""

RHEL_HTML = """
<!-- RHEL-MOB -->
<div id="rhel-ov"></div>
<nav id="rhel-dr">
  <div id="rhel-dhead">
    <span id="rhel-dtitle">Topics</span>
    <button id="rhel-dclose">&#10005;</button>
  </div>
  <a id="rhel-back" href="index.html">&#8592; Study Hub</a>
  <div id="rhel-list"></div>
</nav>
<div id="rhel-bar">
  <div id="rhel-pills"></div>
  <button id="rhel-tbtn">&#9776; Topics</button>
</div>"""

RHEL_JS = """<script id="rhel-mob-js">
(function(){
  if(window.innerWidth > 768) return;
  var ov=document.getElementById('rhel-ov'),
      dr=document.getElementById('rhel-dr'),
      dc=document.getElementById('rhel-dclose'),
      tb=document.getElementById('rhel-tbtn'),
      ls=document.getElementById('rhel-list'),
      pl=document.getElementById('rhel-pills');
  if(!dr||!tb) return;

  function open(){dr.classList.add('on');ov.classList.add('on');
    document.body.style.overflow='hidden';tb.innerHTML='&#10005; Close';}
  function close(){dr.classList.remove('on');ov.classList.remove('on');
    document.body.style.overflow='';tb.innerHTML='&#9776; Topics';}
  tb.addEventListener('click',function(){dr.classList.contains('on')?close():open();});
  dc.addEventListener('click',close);
  ov.addEventListener('click',close);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});

  var built=false;
  function build(){
    if(built) return;
    /* .nav-btn are the topic buttons — populated by page JS from sections[] */
    var btns=document.querySelectorAll('.nav-btn');
    if(!btns.length) return;
    built=true; ls.innerHTML='';

    /* Group by sidebar-section labels */
    var sidebar=document.querySelector('.sidebar');
    if(!sidebar) return;
    var children=Array.from(sidebar.children);
    children.forEach(function(child){
      if(child.classList.contains('sidebar-section')){
        var sec=document.createElement('div');
        sec.className='rhel-sec';
        sec.textContent=child.textContent.trim();
        ls.appendChild(sec);
      } else if(child.classList.contains('nav-btn')){
        var b=document.createElement('button');
        b.className='rhel-it';
        /* Clone number span if present */
        var numEl=child.querySelector('.num');
        if(numEl){
          var ns=document.createElement('span');
          ns.className='rhel-num';
          ns.textContent=numEl.textContent.trim();
          b.appendChild(ns);
        }
        b.appendChild(document.createTextNode(
          child.textContent.replace(numEl?numEl.textContent:'','').trim()
        ));
        b.addEventListener('click',function(){
          child.click();
          setTimeout(close,180);
        });
        ls.appendChild(b);
      }
    });
    sync();
  }

  function sync(){
    var active=document.querySelector('.nav-btn.active');
    var at=active?active.textContent.trim():'';
    ls.querySelectorAll('.rhel-it').forEach(function(it){
      var txt=it.textContent.trim();
      it.classList.toggle('on', at.includes(txt) || txt.replace(/^[0-9]+ */,'') === at.replace(/^[0-9]+ */,''));
    });
  }

  /* Build section pills from sidebar-section labels */
  function buildPills(){
    if(pl.children.length) return;
    var labels=document.querySelectorAll('.sidebar-section');
    labels.forEach(function(lbl){
      var p=document.createElement('button');
      p.className='rhel-pill';
      p.textContent=lbl.textContent.trim();
      p.addEventListener('click',function(){
        /* Scroll to first nav-btn after this label */
        var next=lbl.nextElementSibling;
        while(next && !next.classList.contains('nav-btn')) next=next.nextElementSibling;
        if(next) next.click();
        setTimeout(close,180);
      });
      pl.appendChild(p);
    });
    /* Add "All" pill at front */
    if(pl.children.length>0){
      var all=document.createElement('button');
      all.className='rhel-pill rhel-pill-on';
      all.textContent='All';
      pl.insertBefore(all,pl.firstChild);
      all.addEventListener('click',function(){open();});
    }
  }

  new MutationObserver(function(){sync();})
    .observe(document.body,{childList:true,subtree:true,
      attributes:true,attributeFilter:['class']});

  function init(){
    build(); buildPills();
    if(!built){
      var n=0,t=setInterval(function(){
        build(); buildPills();
        if(built||++n>40)clearInterval(t);
      },100);
    }
  }
  document.readyState==='loading'
    ?document.addEventListener('DOMContentLoaded',function(){setTimeout(init,200);})
    :setTimeout(init,200);
})();
</script>"""


# ════════════════════════════════════════════════════════════════
#  ITIL UNIX INTERVIEW PREP FIX
#  Exact class names from source:
#    .main-grid { display:grid; grid-template-columns:280px 1fr }
#    .sidebar   { position:sticky; top:49px; height:calc(100vh - 49px) }
#    .sidebar-link  — anchor tags linking to #section-id
#    .nav-bar / .nav-scroll / .nav-item  — top tab bar (sticky)
#    .content-area  — main scroll area
#    Continuous scroll (NOT panel-switch) — sidebar-links are anchors
# ════════════════════════════════════════════════════════════════
ITIL_CSS = """<style id="itil-mob-css">
@media (max-width: 768px) {
  /* ── Grid → single column ─────────────────────────────── */
  .main-grid {
    display: block !important;
    grid-template-columns: 1fr !important;
    min-height: auto !important;
  }

  /* ── Sidebar: hidden, replaced by slide-in drawer ──────── */
  .sidebar {
    display: none !important;
    position: static !important;
    height: auto !important;
  }

  /* ── Content area: full width ─────────────────────────── */
  .content-area {
    width: 100% !important;
    max-width: 100vw !important;
    padding: 20px 14px 110px !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
  }

  /* ── Sticky nav-bar at top: allow horizontal scroll ────── */
  .nav-bar {
    position: sticky !important;
    top: 0 !important; z-index: 500 !important;
  }
  .nav-scroll {
    display: flex !important;
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    gap: 0 !important;
    scrollbar-width: none !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 0 10px !important;
  }
  .nav-scroll::-webkit-scrollbar { display: none !important; }
  .nav-item {
    flex-shrink: 0 !important;
    font-size: 9px !important;
    padding: 12px 10px !important;
    letter-spacing: .08em !important;
  }

  /* ── Header compact ───────────────────────────────────── */
  header { padding: 28px 14px 22px !important; }
  header h1 { font-size: clamp(22px,7vw,36px) !important; }
  .header-stats { gap: 18px !important; padding: 0 14px !important; }

  /* ── Process sections: single column ─────────────────── */
  .process-grid, .cmd-grid, .two-col,
  [class*="grid-"], [class*="two-col"] {
    grid-template-columns: 1fr !important;
    display: block !important;
  }

  /* ── Lifecycle arrows: wrap ───────────────────────────── */
  .lifecycle, [class*="lifecycle"],
  .flow-row, [class*="flow-row"] {
    flex-wrap: wrap !important; gap: 6px !important;
  }

  /* ── Code blocks ──────────────────────────────────────── */
  pre {
    overflow-x: auto !important;
    font-size: 12px !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 12px 14px !important;
    line-height: 1.6 !important;
    border-radius: 6px !important;
  }
  code { font-size: 12px !important; }

  /* ── Tables ───────────────────────────────────────────── */
  table {
    display: block !important; overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important; font-size: 12px !important;
  }
  th { white-space: nowrap !important; }

  /* ── Cards ────────────────────────────────────────────── */
  .card, [class*="process-card"], [class*="cmd-card"] {
    padding: 12px 14px !important; margin-bottom: 10px !important;
  }

  /* ── Body ─────────────────────────────────────────────── */
  body {
    overflow-x: hidden !important;
    font-size: 15px !important;
    line-height: 1.75 !important;
  }

  /* ── Typography boost for readability on mobile ─────────── */
  /* Base paragraph / list text */
  p, li, td, th, .answer, .qa-answer,
  [class*="answer"], [class*="desc"] {
    font-size: 14px !important;
    line-height: 1.75 !important;
  }

  /* Headings */
  h1 { font-size: clamp(20px, 6vw, 28px) !important; line-height: 1.2 !important; }
  h2 { font-size: 20px !important; line-height: 1.3 !important; margin-top: 28px !important; }
  h3 { font-size: 16px !important; line-height: 1.35 !important; margin-top: 18px !important; }
  h4 { font-size: 14px !important; }

  /* Q&A cards */
  .qa-item, [class*="qa-"], [class*="question"],
  .card, [class*="-card"], [class*="process-card"] {
    padding: 14px !important;
    margin-bottom: 14px !important;
  }

  /* Q prefix badge and question text */
  .q-badge, [class*="q-badge"] { font-size: 12px !important; }
  .question-text, [class*="question-text"],
  .qa-q, [class*="qa-q"] { font-size: 14px !important; font-weight: 600 !important; }

  /* Process section headers */
  .section-title, [class*="section-title"],
  .process-title, [class*="process-title"] {
    font-size: 17px !important;
  }

  /* Command descriptions / labels */
  .cmd-label, .cmd-desc, [class*="cmd-"] p,
  .cmd-block + p, .cmd-block p {
    font-size: 13px !important;
  }

  /* Nav-item tabs at top */
  .nav-item {
    font-size: 11px !important;
    padding: 12px 10px !important;
    letter-spacing: .06em !important;
  }

  /* Stat numbers in header */
  .stat-num { font-size: 20px !important; }
  .stat-label { font-size: 10px !important; }
  .header-tag { font-size: 9px !important; }

  /* ════ NAVIGATE BUTTON ══════════════════════════════════ */
  #itil-nav-btn {
    position: fixed !important; bottom: 18px !important; right: 14px !important;
    z-index: 8000 !important;
    background: var(--accent, #00d4ff) !important;
    color: #0a0e14 !important; border: none !important;
    border-radius: 50px !important; padding: 12px 20px !important;
    font-size: 13px !important; font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
    cursor: pointer !important; display: flex !important;
    align-items: center !important; gap: 7px !important;
    box-shadow: 0 4px 24px rgba(0,212,255,.4) !important;
    -webkit-tap-highlight-color: transparent !important;
    letter-spacing: .04em !important;
  }
  #itil-nav-btn:active { transform: scale(.96) !important; }

  /* ════ DRAWER ══════════════════════════════════════════ */
  #itil-ov {
    display: none; position: fixed !important; inset: 0 !important;
    background: rgba(0,0,0,.82) !important; z-index: 8100 !important;
  }
  #itil-ov.on { display: block !important; }

  #itil-dr {
    position: fixed !important; top: 0 !important; left: 0 !important;
    bottom: 0 !important; width: min(290px, 86vw) !important;
    background: var(--surface, #0f1520) !important;
    border-right: 1px solid var(--accent, #00d4ff) !important;
    z-index: 8200 !important; display: flex !important;
    flex-direction: column !important;
    transform: translateX(-100%) !important;
    transition: transform .26s cubic-bezier(.4,0,.2,1) !important;
  }
  #itil-dr.on { transform: translateX(0) !important; }

  #itil-dhead {
    display: flex !important; align-items: center !important;
    justify-content: space-between !important;
    padding: 14px 16px !important;
    border-bottom: 1px solid var(--border, #1e2d45) !important;
    background: var(--panel, #141c2a) !important; flex-shrink: 0 !important;
  }
  #itil-dtitle {
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: .15em !important; text-transform: uppercase !important;
    color: var(--accent, #00d4ff) !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  #itil-dclose {
    background: rgba(0,212,255,.08) !important;
    border: 1px solid var(--border, #1e2d45) !important;
    border-radius: 6px !important; color: var(--accent, #00d4ff) !important;
    width: 30px !important; height: 30px !important; font-size: 14px !important;
    cursor: pointer !important; display: flex !important;
    align-items: center !important; justify-content: center !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  #itil-back {
    display: flex !important; align-items: center !important; gap: 8px !important;
    padding: 11px 16px !important; color: var(--accent4, #ffd700) !important;
    text-decoration: none !important; font-size: 11px !important;
    font-weight: 700 !important; letter-spacing: .06em !important;
    border-bottom: 1px solid var(--border, #1e2d45) !important;
    background: rgba(255,215,0,.04) !important; flex-shrink: 0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    -webkit-tap-highlight-color: transparent !important;
  }
  #itil-list {
    overflow-y: auto !important; flex: 1 !important;
    -webkit-overflow-scrolling: touch !important; padding: 4px 0 60px !important;
  }
  #itil-list::-webkit-scrollbar { width: 3px !important; }
  #itil-list::-webkit-scrollbar-thumb { background: var(--border, #1e2d45) !important; }
  .itil-sec {
    padding: 10px 16px 3px !important; font-size: 10px !important;
    font-weight: 700 !important; letter-spacing: .14em !important;
    text-transform: uppercase !important; color: var(--text-dim, #5a7a9a) !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  .itil-lnk {
    display: flex !important; align-items: center !important; gap: 8px !important;
    padding: 10px 16px !important; color: var(--text-dim, #5a7a9a) !important;
    text-decoration: none !important; font-size: 11.5px !important;
    border-left: 2px solid transparent !important;
    transition: all .14s !important; box-sizing: border-box !important;
    font-family: 'JetBrains Mono', monospace !important;
    -webkit-tap-highlight-color: transparent !important;
    cursor: pointer !important;
  }
  .itil-lnk:active { background: rgba(0,212,255,.05) !important; }
  .itil-lnk.itil-cur {
    color: var(--accent, #00d4ff) !important;
    border-left-color: var(--accent, #00d4ff) !important;
    background: rgba(0,212,255,.04) !important;
  }
  .itil-dot {
    width: 6px !important; height: 6px !important; border-radius: 50% !important;
    flex-shrink: 0 !important; background: currentColor !important; opacity: .5 !important;
  }
}
@media (min-width: 769px) {
  #itil-nav-btn, #itil-ov, #itil-dr { display: none !important; }
}
</style>"""

ITIL_HTML = """
<!-- ITIL-MOB -->
<div id="itil-ov"></div>
<nav id="itil-dr">
  <div id="itil-dhead">
    <span id="itil-dtitle">Navigate</span>
    <button id="itil-dclose">&#10005;</button>
  </div>
  <a id="itil-back" href="index.html">&#8592; Study Hub</a>
  <div id="itil-list"></div>
</nav>
<button id="itil-nav-btn">&#9776; Navigate</button>"""

ITIL_JS = """<script id="itil-mob-js">
(function(){
  if(window.innerWidth > 768) return;
  var ov=document.getElementById('itil-ov'),
      dr=document.getElementById('itil-dr'),
      dc=document.getElementById('itil-dclose'),
      btn=document.getElementById('itil-nav-btn'),
      ls=document.getElementById('itil-list');
  if(!dr||!btn) return;

  function open(){dr.classList.add('on');ov.classList.add('on');
    document.body.style.overflow='hidden';btn.innerHTML='&#10005; Close';}
  function close(){dr.classList.remove('on');ov.classList.remove('on');
    document.body.style.overflow='';btn.innerHTML='&#9776; Navigate';}
  btn.addEventListener('click',function(){dr.classList.contains('on')?close():open();});
  dc.addEventListener('click',close);
  ov.addEventListener('click',close);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});

  /* Build drawer from .sidebar-title (section heads) and .sidebar-link (anchors) */
  var sidebar=document.querySelector('.sidebar');
  if(!sidebar){
    /* Sidebar may be hidden by our CSS — read the original DOM before our CSS hides it */
    /* Use querySelectorAll from document directly */
    sidebar=document.body;
  }
  var sidebarEl=document.querySelector('.sidebar');
  var built=false;

  function build(){
    if(built) return;
    /* Try to find sidebar links */
    var links=document.querySelectorAll('.sidebar-link');
    var titles=document.querySelectorAll('.sidebar-title');
    if(!links.length) return;
    built=true; ls.innerHTML='';

    /* Interleave section titles and links */
    /* Walk sidebar children to preserve order */
    var sEl=document.querySelector('.sidebar');
    if(sEl){
      var ch=Array.from(sEl.querySelectorAll('.sidebar-title, .sidebar-link'));
      ch.forEach(function(el){
        if(el.classList.contains('sidebar-title')){
          var sec=document.createElement('div');
          sec.className='itil-sec';
          sec.textContent=el.textContent.trim();
          ls.appendChild(sec);
        } else {
          /* sidebar-link is an <a> with href="#id" */
          var a=document.createElement('a');
          a.className='itil-lnk';
          a.href=el.getAttribute('href')||'#';
          /* Dot colour indicator */
          var dotEl=el.querySelector('.dot');
          var dot=document.createElement('span');
          dot.className='itil-dot';
          if(dotEl) dot.style.background=window.getComputedStyle(dotEl).background;
          a.appendChild(dot);
          a.appendChild(document.createTextNode(el.textContent.trim()));
          a.addEventListener('click',function(){setTimeout(close,200);});
          ls.appendChild(a);
        }
      });
    }

    /* Highlight on scroll */
    var anchors=Array.from(ls.querySelectorAll('.itil-lnk[href^="#"]'));
    window.addEventListener('scroll',function(){
      var y=window.scrollY+100,cur=null;
      anchors.forEach(function(a){
        var id=a.getAttribute('href').slice(1);
        var el=id?document.getElementById(id):null;
        if(el&&el.offsetTop<=y) cur=a;
      });
      anchors.forEach(function(a){a.classList.remove('itil-cur');});
      if(cur) cur.classList.add('itil-cur');
    },{passive:true});
  }

  function init(){
    build();
    if(!built){
      var n=0,t=setInterval(function(){
        build();
        if(built||++n>30) clearInterval(t);
      },100);
    }
  }
  document.readyState==='loading'
    ?document.addEventListener('DOMContentLoaded',function(){setTimeout(init,150);})
    :setTimeout(init,150);
})();
</script>"""


# ════════════════════════════════════════════════════════════════
#  CORE PATCH LOGIC
# ════════════════════════════════════════════════════════════════
PAGES = {
    "rhel study guide.html": {
        "css": RHEL_CSS, "html": RHEL_HTML, "js": RHEL_JS,
        "desc": "RHEL Study Guide  [Type-A: flex sidebar + .nav-btn]"
    },
    "itil-unix-interview-prep.html": {
        "css": ITIL_CSS, "html": ITIL_HTML, "js": ITIL_JS,
        "desc": "ITIL Unix Prep    [Type-C: grid sidebar + .sidebar-link]"
    },
}

def apply(fp, meta, dry=False):
    fname = os.path.basename(fp)
    with open(fp, encoding='utf-8', errors='replace') as f:
        original = f.read()

    html = strip_all(original)
    stripped = len(original) - len(html)

    injection = f"\n{meta['css']}\n{meta['html']}\n{meta['js']}\n"

    if re.search(r'</body>', html, re.I):
        html = re.sub(r'(</body>)', injection + r'\1', html, count=1, flags=re.I)
    else:
        html += injection

    if dry:
        print(f"  {C('○')}  {meta['desc']}")
        print(f"     {D(f'would strip {stripped:,} chars  |  inject {len(injection):,} chars')}")
        return

    shutil.copy2(fp, fp + BACKUP_EXT)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  {G('✔')}  {meta['desc']}")
    print(f"     {D(f'stripped {stripped:,} chars  |  injected {len(injection):,} chars  |  backup saved')}")

def restore(fp):
    bak = fp + BACKUP_EXT
    fname = os.path.basename(fp)
    if os.path.exists(bak):
        shutil.copy2(bak, fp); os.remove(bak)
        print(f"  {G('✔  restored')}  {fname}")
    else:
        print(f"  {Y('⚠  no backup')}  {fname}")

def main():
    args   = sys.argv[1:]
    dry    = '--dry-run' in args
    undo   = '--undo'    in args
    wd     = os.path.dirname(os.path.abspath(__file__))

    print()
    print(B("  ╔══════════════════════════════════════════════╗"))
    print(B("  ║  RHEL + ITIL Mobile Fix  (exact class names) ║"))
    print(B("  ╚══════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if undo else G('PATCH'))}\n")

    for fname, meta in PAGES.items():
        fp = os.path.join(wd, fname)
        if not os.path.exists(fp):
            print(f"  {Y('⚠  not found')}  {fname}")
            continue
        if undo:
            restore(fp)
        else:
            apply(fp, meta, dry)
        print()

    if not undo and not dry:
        git_msg = 'git commit -m "Fix RHEL and ITIL mobile layout"'
        print(B("  Push to GitHub:"))
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")
    print()

if __name__ == '__main__':
    main()
