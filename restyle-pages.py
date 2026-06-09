#!/usr/bin/env python3
"""
restyle_pages.py
════════════════════════════════════════════════════════════════════
The definitive fix. Instead of injecting CSS on top of conflicting
styles, this script:

  1. Reads each page's HTML
  2. REPLACES the entire <style> block with a clean Nutanix-matched
     design system — same tokens, same fonts, same component styles
  3. Keeps ALL HTML content and JavaScript untouched
  4. Removes any previous theme/mobile injections from <style> tags
     (but keeps the functional mobile nav scripts)

Pages targeted (dark-themed, broken by theme injector):
  - Linux Admin Interview StudyGuide.html
  - OS Admin L3 Interview Prep.html
  - Master Interview Hub.html
  - ITIL Unix Interview Prep.html  (already has good dark theme, just needs chrome fix)
  - rhel study guide.html

These pages share the same HTML structure:
  - .header (fixed top bar) → replaced by #shub-topbar
  - .layout with .sidebar + .content/.main
  - .topic-card / .qa-item collapsible cards
  - .toc-btn / .sidebar-item nav items
  - .cmd-block / .code-block
  - .info-box / .warn-box

Usage:
  cd ~/Studyhtml
  python3 restyle_pages.py            # apply
  python3 restyle_pages.py --undo     # restore .bak3 backups
  python3 restyle_pages.py --dry-run  # preview only
"""
import os, sys, re, shutil

BACKUP_EXT = ".bak3"
MARKER     = "<!-- RESTYLE-v1 -->"
SKIP       = {"index.html", "Nutanix Foundations Guide.html",
              "Network Study Reference.html"}  # these have different structures

def c(t,code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t,"0;32");  Y = lambda t: c(t,"0;33")
R = lambda t: c(t,"0;31");  C = lambda t: c(t,"0;36")
B = lambda t: c(t,"1;37");  D = lambda t: c(t,"0;90")

# ════════════════════════════════════════════════════════════════════
#  THE UNIFIED DARK DESIGN SYSTEM
#  Nutanix quality, dark variant — matches its navy/blue/gold palette
#  but inverted for dark bg. Same fonts, same component shapes.
# ════════════════════════════════════════════════════════════════════
UNIFIED_CSS = """\
<!-- RESTYLE-v1 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<style id="studyhub-unified">
/* ═══════════════════════════════════════════════════════════════
   StudyHub Unified Dark Theme — all pages
   Navy/Blue/Gold palette from Nutanix, dark variant
   ═══════════════════════════════════════════════════════════════ */
:root {
  /* Core palette — dark version of Nutanix design system */
  --bg:        #0B1220;
  --surface:   #111827;
  --surface2:  #1A2236;
  --surface3:  #1F2D45;
  --border:    #1E3A5F;
  --border2:   #2A4A72;

  /* Brand colours — same as Nutanix */
  --navy:      #0B1E3D;
  --blue:      #1B4F8A;
  --mid:       #2E6CC7;
  --sky:       #4A9FD5;
  --teal:      #00929F;
  --accent:    #F0A500;  /* Nutanix gold */

  /* Semantic colours */
  --green:     #10B981;
  --red:       #EF4444;
  --purple:    #8B5CF6;

  /* Text */
  --text:      #E2ECF8;
  --text2:     #94A8C4;
  --text3:     #5A6E8A;

  /* Code */
  --code-bg:   #070D1A;
  --code-fg:   #79C0FF;

  /* Font stack — same as Nutanix */
  --font-head: 'Syne', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

/* ── Reset ──────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; -webkit-tap-highlight-color: transparent; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.75;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── Page header (fixed, original — hidden on mobile by nav fix) */
.header {
  position: fixed; top: 58px; left: 0; right: 0; z-index: 90;
  background: rgba(11,18,32,0.97);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0 1.5rem;
  display: flex; align-items: center;
  justify-content: space-between;
  height: 58px;
  gap: 1rem;
}
.header-brand { display: flex; align-items: center; gap: 12px; }
.header-logo {
  width: 34px; height: 34px; border-radius: 8px;
  background: linear-gradient(135deg, var(--sky), var(--mid));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-head); font-weight: 800; font-size: 13px;
  color: #fff; flex-shrink: 0;
}
.header-title {
  font-family: var(--font-head); font-weight: 700; font-size: 0.95rem;
  color: var(--text);
}
.header-sub { font-size: 0.68rem; color: var(--text3); font-family: var(--font-mono); }
.header-stats { display: flex; gap: 1.5rem; }
.hstat { text-align: center; }
.hstat-n {
  font-family: var(--font-head); font-weight: 800;
  font-size: 1.1rem; color: var(--accent);
}
.hstat-l {
  font-size: 0.62rem; color: var(--text3);
  text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Layout ─────────────────────────────────────────────────── */
.layout {
  display: flex;
  padding-top: 116px;  /* 58px shub-topbar + 58px .header */
  min-height: 100vh;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
.sidebar {
  width: 260px; min-width: 260px;
  background: var(--navy);
  border-right: 1px solid var(--border);
  height: calc(100vh - 116px);
  position: sticky; top: 116px;
  overflow-y: auto;
  padding: 0.75rem 0;
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.sidebar-section { margin-bottom: 0.25rem; }
.sidebar-section-header {
  padding: 0.6rem 1rem 0.25rem;
  font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--text3); font-family: var(--font-mono);
  margin-top: 0.5rem;
}

/* Sidebar items — works for .sidebar-item AND .nav-btn */
.sidebar-item, .nav-btn {
  display: flex; align-items: center; gap: 10px;
  padding: 0.55rem 1rem;
  cursor: pointer;
  border: none; width: 100%; text-align: left;
  border-left: 3px solid transparent;
  background: transparent;
  font-family: var(--font-body);
  font-size: 0.82rem;
  color: var(--text2);
  transition: all 0.15s;
}
.sidebar-item:hover, .nav-btn:hover {
  background: rgba(255,255,255,0.04);
  color: var(--text); border-left-color: var(--border2);
}
.sidebar-item.active, .nav-btn.active {
  background: rgba(240,165,0,0.08);
  color: var(--accent); border-left-color: var(--accent);
}
.sidebar-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.sidebar-count, .num {
  margin-left: auto;
  background: var(--surface2); border-radius: 10px;
  padding: 1px 7px; font-size: 0.62rem;
  color: var(--text3); font-family: var(--font-mono);
  display: inline-flex; align-items: center;
}
.sidebar-item.active .sidebar-count,
.nav-btn.active .num { background: rgba(240,165,0,0.15); color: var(--accent); }

.nav-group-label {
  font-family: var(--font-mono); font-size: 0.6rem;
  color: var(--text3); text-transform: uppercase;
  letter-spacing: 0.12em; padding: 0.75rem 1rem 0.25rem;
}

/* ── Main content ────────────────────────────────────────────── */
.main, .content {
  flex: 1; overflow-y: auto;
  padding: 2rem 2.5rem 4rem;
  max-width: calc(100vw - 260px);
}
.content-inner { max-width: 920px; margin: 0 auto; }

/* ── Tab panels ──────────────────────────────────────────────── */
.tab-panel, .section { display: none; }
.tab-panel.active, .section.active { display: block; }
@keyframes fadeIn {
  from { opacity:0; transform:translateY(6px); }
  to   { opacity:1; transform:translateY(0);   }
}
.tab-panel.active, .section.active {
  animation: fadeIn 0.28s ease;
}

/* ── Page / section header ───────────────────────────────────── */
.page-header, .section-header {
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}
.page-header-row { display: flex; align-items: flex-start; gap: 1rem; }
.page-icon, .section-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; flex-shrink: 0; background: var(--surface2);
}
.page-title, .section-title {
  font-family: var(--font-head); font-weight: 800;
  font-size: 1.6rem; color: var(--text); line-height: 1.2;
}
.page-desc, .section-desc {
  font-size: 0.85rem; color: var(--text2);
  margin-top: 0.3rem; line-height: 1.6;
  font-style: italic;
}
.page-tags, .cover-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.tag, .cover-tag {
  padding: 3px 10px; border-radius: 20px;
  font-size: 0.7rem; font-family: var(--font-mono);
  background: var(--surface2); color: var(--text2);
  border: 1px solid var(--border);
}

/* ── Stat bar (below page header on some pages) ──────────────── */
.stats-row {
  display: flex; gap: 2rem; flex-wrap: wrap;
  padding: 1rem 0; border-top: 1px solid var(--border);
  margin-top: 1rem;
}
.stat-item .val {
  font-family: var(--font-head); font-weight: 800;
  font-size: 1.5rem; color: var(--accent);
}
.stat-item .lbl {
  font-size: 0.68rem; color: var(--text3);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-top: 0.1rem;
}

/* ── Topic / section cards ───────────────────────────────────── */
.topic-card, .card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 1rem;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.topic-card:hover, .card:hover {
  border-color: var(--border2);
  box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}
.topic-header {
  padding: 1.1rem 1.4rem;
  cursor: pointer;
  display: flex; align-items: center;
  justify-content: space-between; gap: 12px;
  user-select: none;
}
.topic-header:hover { background: rgba(255,255,255,0.02); }
.topic-title-row { display: flex; align-items: center; gap: 12px; flex: 1; }
.topic-num {
  font-family: var(--font-mono); font-size: 0.7rem;
  color: var(--accent);
  background: rgba(240,165,0,0.1); border: 1px solid rgba(240,165,0,0.2);
  padding: 2px 8px; border-radius: 4px; flex-shrink: 0;
}
.topic-title {
  font-family: var(--font-head); font-size: 1rem;
  font-weight: 600; color: var(--text);
}
.topic-desc { font-size: 0.8rem; color: var(--text2); margin-top: 3px; }
.topic-meta {
  font-size: 0.72rem; color: var(--text3);
  font-family: var(--font-mono); margin-top: 2px;
}
.chevron {
  color: var(--text3); font-size: 16px;
  transition: transform 0.22s; flex-shrink: 0;
}
.topic-card.open .chevron { transform: rotate(180deg); }
.topic-body {
  display: none;
  padding: 0 1.4rem 1.4rem;
  border-top: 1px solid var(--border);
}
.topic-card.open .topic-body { display: block; }

/* Progress bar on card bottom */
.topic-bar {
  height: 2px; margin: 0.75rem -1.4rem -1.4rem;
  border-radius: 0 0 12px 12px;
  opacity: 0.6;
}

/* ── Q&A ─────────────────────────────────────────────────────── */
.qa-block { margin-top: 1.25rem; }
.qa-item {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 10px; overflow: hidden;
}
.qa-q {
  padding: 0.9rem 1.1rem;
  display: flex; gap: 10px; align-items: flex-start;
  cursor: pointer; user-select: none;
}
.qa-q:hover { background: rgba(255,255,255,0.02); }
.q-badge {
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
  background: rgba(74,159,213,0.12); color: var(--sky);
  border: 1px solid rgba(74,159,213,0.22);
  padding: 2px 6px; border-radius: 3px; flex-shrink: 0; margin-top: 2px;
}
.q-text {
  font-family: var(--font-head); font-weight: 600;
  color: var(--text); font-size: 0.95rem; line-height: 1.45;
}
.qa-a {
  display: none;
  padding: 0.9rem 1.1rem 1rem 2.8rem;
  border-top: 1px solid var(--border);
  background: rgba(0,0,0,0.15);
}
.qa-item.open .qa-a { display: block; }
.a-badge {
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
  color: var(--accent); margin-bottom: 6px; display: block;
}
.qa-a p, .answer p {
  color: var(--text2); font-size: 14.5px;
  margin-bottom: 0.5rem; line-height: 1.75;
}
.qa-a p:last-child { margin-bottom: 0; }

/* ── Step lists ──────────────────────────────────────────────── */
.step-list { list-style: none; margin: 0.75rem 0; }
.step-list li {
  display: flex; gap: 10px; margin-bottom: 8px;
  align-items: flex-start; font-size: 14px; color: var(--text2);
}
.step-n {
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
  color: var(--accent); background: rgba(240,165,0,0.1);
  border: 1px solid rgba(240,165,0,0.2); border-radius: 50%;
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 1px;
}

/* ── Code blocks ─────────────────────────────────────────────── */
pre, .cmd-block, .code-block, [class*="code-block"] {
  background: var(--code-bg) !important;
  border: 1px solid var(--border);
  border-left: 3px solid var(--sky);
  border-radius: 8px;
  padding: 1rem 1.1rem;
  font-family: var(--font-mono) !important;
  font-size: 13px;
  color: var(--code-fg) !important;
  overflow-x: auto;
  line-height: 1.65;
  margin: 0.75rem 0 1.25rem;
}
.cmd-label {
  font-family: var(--font-mono); font-size: 9px;
  text-transform: uppercase; letter-spacing: 1px;
  color: var(--sky); margin-bottom: 6px; margin-top: 1rem;
  display: block;
}
pre .comment, .cmd-block .comment { color: #4A6A5A; font-style: italic; }

/* ── Inline code ─────────────────────────────────────────────── */
:not(pre) > code {
  font-family: var(--font-mono);
  font-size: 0.83em;
  background: rgba(74,159,213,0.1);
  color: var(--sky);
  padding: 1px 5px; border-radius: 4px;
}

/* ── Info / warn boxes ───────────────────────────────────────── */
.info-box {
  background: rgba(74,159,213,0.06);
  border: 1px solid rgba(74,159,213,0.18);
  border-left: 3px solid var(--sky);
  border-radius: 6px; padding: 12px 14px; margin: 10px 0;
  font-size: 14px; color: var(--text2); line-height: 1.6;
}
.warn-box {
  background: rgba(240,165,0,0.06);
  border: 1px solid rgba(240,165,0,0.18);
  border-left: 3px solid var(--accent);
  border-radius: 6px; padding: 12px 14px; margin: 10px 0;
  font-size: 14px; color: var(--text2); line-height: 1.6;
}
.warn-box strong { color: var(--accent); }
.info-box strong { color: var(--sky); }

/* ── Inline text ─────────────────────────────────────────────── */
p.body-text { color: var(--text2); font-size: 14.5px; margin: 8px 0; line-height: 1.75; }
li { color: var(--text2); font-size: 14px; line-height: 1.65; }
h2 { font-family: var(--font-head); color: var(--sky); font-weight: 700; margin: 1.5rem 0 0.75rem; font-size: 1.15rem; }
h3 { font-family: var(--font-head); color: var(--teal); font-weight: 600; margin: 1.25rem 0 0.5rem; font-size: 0.98rem; }
a  { color: var(--sky); }

/* ── Tables ──────────────────────────────────────────────────── */
table { width: 100%; border-collapse: collapse; margin: 0.75rem 0 1.5rem;
  border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 8px rgba(0,0,0,0.25); font-size: 0.84rem; }
thead tr { background: var(--blue); }
thead th { padding: 0.65rem 0.9rem; color: #fff;
  font-family: var(--font-head); font-weight: 600;
  text-align: left; font-size: 0.76rem; letter-spacing: 0.03em; }
tbody tr:nth-child(odd)  { background: var(--surface); }
tbody tr:nth-child(even) { background: var(--surface2); }
tbody td { padding: 0.55rem 0.9rem; color: var(--text2);
  vertical-align: top; line-height: 1.5;
  border-top: 1px solid var(--border); }
tbody td:first-child { font-family: var(--font-head); font-weight: 600; color: var(--sky); }

/* ── Section-level nav tabs (TocBtns) ───────────────────────── */
.toc, .toc-inner, .nav-tabs, .topics-nav {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.toc-btn, .tab-btn {
  background: none; border: none;
  color: var(--text3);
  font-family: var(--font-mono); font-size: 11px;
  letter-spacing: 0.04em; text-transform: uppercase;
  padding: 14px 18px; cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid transparent; transition: all 0.18s;
}
.toc-btn:hover { color: var(--accent); }
.toc-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Category pills ──────────────────────────────────────────── */
.cat-nav { display: flex; overflow-x: auto; gap: 2px; scrollbar-width: none; }
.cat-nav::-webkit-scrollbar { display: none; }
.cat-btn {
  background: none; border: none;
  color: var(--text3); font-family: var(--font-mono);
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em;
  padding: 10px 14px; cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid transparent; transition: all 0.15s;
}
.cat-btn:hover { color: var(--text); }
.cat-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Divider ─────────────────────────────────────────────────── */
.divider { height: 1px; background: var(--border); margin: 1.5rem 0; }

/* ── Footer ──────────────────────────────────────────────────── */
.footer {
  text-align: center; padding: 2rem 1rem;
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text3); letter-spacing: 0.08em;
  border-top: 1px solid var(--border); margin-top: 2rem;
}

/* ── Badges ──────────────────────────────────────────────────── */
.badge {
  display: inline-block;
  background: rgba(240,165,0,0.1); border: 1px solid rgba(240,165,0,0.25);
  color: var(--accent); font-family: var(--font-mono);
  font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  padding: 3px 10px; border-radius: 3px; margin-bottom: 1rem;
}

/* ── Scrollbars ──────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--border2); }
::selection { background: var(--blue); color: #fff; }

/* ── Mobile (≤768px) — sidebar off, content full width ──────── */
@media (max-width: 768px) {
  .header { display: none; }
  .layout { display: block; padding-top: 58px; }
  .sidebar { display: none; }
  .main, .content {
    max-width: 100%; padding: 16px 14px 110px;
  }
  .toc-inner, .cat-nav {
    overflow-x: auto; flex-wrap: nowrap;
    scrollbar-width: none;
  }
  .toc-btn, .cat-btn { font-size: 10px; padding: 12px 10px; }
  pre, .cmd-block { font-size: 12px; }
  .page-title, .section-title { font-size: 1.3rem; }
  table { display: block; overflow-x: auto; font-size: 0.78rem; }
}
</style>"""

# ════════════════════════════════════════════════════════════════════
#  PAGE TITLES
# ════════════════════════════════════════════════════════════════════
PAGE_TITLES = {
    "ccna study notes.html":                 "CCNA Study Notes",
    "linux admin interview studyguide.html": "Linux Admin Interview Guide",
    "os admin l3 interview prep.html":       "OS Admin L3 — Interview Prep",
    "master interview hub.html":             "Master Interview Hub",
    "itil-unix-interview-prep.html":         "ITIL & Unix Interview Prep",
    "rhel study guide.html":                 "RHEL Study Guide",
}

# ════════════════════════════════════════════════════════════════════
#  STUDYHUB TOPBAR + CHROME (injected after <body>)
# ════════════════════════════════════════════════════════════════════
def topbar(title):
    return f"""
<div id="shub-topbar" style="position:fixed;top:0;left:0;right:0;z-index:9999;height:58px;background:#0B1E3D;display:flex;align-items:center;padding:0 20px;gap:12px;border-bottom:2px solid #1B4F8A;box-shadow:0 2px 20px rgba(0,0,0,.5);">
  <a href="index.html" style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.05rem;color:#fff;text-decoration:none;letter-spacing:.04em;white-space:nowrap;">Study<span style="color:#F0A500;">Hub</span></a>
  <span style="font-family:'DM Sans',sans-serif;font-size:.72rem;color:#6B8AB0;font-weight:300;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:240px;">{title}</span>
  <div style="flex:1;"></div>
  <a href="index.html" style="display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:7px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);color:#8AAED6;font-size:.74rem;font-family:'DM Sans',sans-serif;text-decoration:none;">
    <svg width="11" height="11" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 9l7-7 7 7M4 8v9a1 1 0 001 1h4v-5h2v5h4a1 1 0 001-1V8"/></svg>
    All Guides
  </a>
</div>
<div id="shub-prog" style="position:fixed;top:58px;left:0;height:3px;width:0%;background:linear-gradient(90deg,#F0A500,#4A9FD5);z-index:9998;transition:width .08s linear;pointer-events:none;"></div>
<button id="shub-btt" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" style="position:fixed;bottom:24px;right:20px;width:42px;height:42px;background:#1B4F8A;color:#fff;border:none;border-radius:50%;font-size:1.1rem;cursor:pointer;z-index:9997;opacity:0;pointer-events:none;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(27,79,138,.45);transition:opacity .2s,transform .2s;">↑</button>
<script id="shub-chrome">
(function(){{
  var p=document.getElementById('shub-prog'),b=document.getElementById('shub-btt');
  window.addEventListener('scroll',function(){{
    var h=document.documentElement,st=h.scrollTop||document.body.scrollTop,sh=(h.scrollHeight||document.body.scrollHeight)-h.clientHeight;
    if(p) p.style.width=(sh>0?Math.min(st/sh*100,100):0)+'%';
    if(b){{b.style.opacity=st>280?'1':'0';b.style.pointerEvents=st>280?'auto':'none';}}
  }},{{passive:true}});
}})();
</script>"""

# ════════════════════════════════════════════════════════════════════
#  STRIP ALL PREVIOUS INJECTIONS
# ════════════════════════════════════════════════════════════════════
OLD_STYLE_IDS  = ["shub-theme","shub-theme-v2","shub-unified","studyhub-unified",
                   "shub-light-extras","shub-dark-extras","shn-styles","shn-page-mobile",
                   "shm-v4","mob-fix-css"]
OLD_SCRIPT_IDS = ["shub-chrome","shub-chrome-js","shub-theme-js","shn-js","shm-js"]
OLD_EL_IDS     = ["shub-topbar","shub-prog","shub-btt","shub-progress","shub-back"]
OLD_COMMENTS   = ["<!-- SHUB-THEME-v1 -->","<!-- SHUB-THEME-v2 -->","<!-- RESTYLE-v1 -->"]

def strip(html):
    for sid in OLD_STYLE_IDS:
        html = re.sub(
            r"<style[^>]+id=['\"]"+re.escape(sid)+r"['\"][^>]*>.*?</style>",
            "", html, flags=re.DOTALL|re.I)
    for sid in OLD_SCRIPT_IDS:
        html = re.sub(
            r"<script[^>]+id=['\"]"+re.escape(sid)+r"['\"][^>]*>.*?</script>",
            "", html, flags=re.DOTALL|re.I)
    for eid in OLD_EL_IDS:
        html = re.sub(
            r"<(?:div|nav|button|a)\b[^>]*\bid=['\"]"+re.escape(eid)+r"['\"][^>]*>.*?</(?:div|nav|button|a)>",
            "", html, flags=re.DOTALL|re.I)
        html = re.sub(r"<[^>]+\bid=['\"]"+re.escape(eid)+r"['\"][^>]*>","",html,flags=re.I)
    for m in OLD_COMMENTS:
        html = html.replace(m, "")
    # Remove all old font links
    html = re.sub(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*/?>','',html,flags=re.I)
    html = re.sub(r"@import url\(['\"][^)]+googleapis[^)]+\)['\"];?","",html,flags=re.I)
    html = re.sub(r'\n{4,}','\n\n',html)
    return html

# ════════════════════════════════════════════════════════════════════
#  REPLACE THE PAGE'S OWN <style> BLOCK
# ════════════════════════════════════════════════════════════════════
def replace_styles(html, fname):
    """Replace the page's primary <style> block with UNIFIED_CSS."""
    # Find the main style block (the first/largest one)
    style_matches = list(re.finditer(r'<style[^>]*>(.*?)</style>', html, re.DOTALL|re.I))
    if not style_matches:
        return html

    # Find the largest style block (main page CSS)
    main_match = max(style_matches, key=lambda m: len(m.group(0)))

    # Replace it with our unified CSS
    html = html[:main_match.start()] + UNIFIED_CSS + html[main_match.end():]
    return html

# ════════════════════════════════════════════════════════════════════
#  APPLY TO ONE FILE
# ════════════════════════════════════════════════════════════════════
def apply(path, dry=False):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        orig = f.read()

    if MARKER in orig:
        print(f"  {D('⟳  already done')}  {D(fname)}")
        return 'skip'

    # 1. Strip all previous injections
    html = strip(orig)

    # 2. Replace main <style> block with unified CSS
    html = replace_styles(html, fname)

    # 3. Inject topbar after <body>
    title  = PAGE_TITLES.get(fname.lower(), fname.replace(".html",""))
    tb     = topbar(title)
    html   = re.sub(r'(<body[^>]*>)', r'\1' + tb, html, count=1, flags=re.I)

    if dry:
        n_styles = len(list(re.finditer(r'<style', orig, re.I)))
        print(f"  {C('○')}  {fname}  [{n_styles} style blocks found]")
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

# ════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════
def main():
    args = sys.argv[1:]
    dry  = '--dry-run' in args
    rev  = '--undo'    in args
    wd   = os.path.dirname(os.path.abspath(__file__))

    print()
    print(B("  ╔══════════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub Page Restyler — replaces CSS wholesale ║"))
    print(B("  ╚══════════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('APPLY'))}\n")

    files = sorted(
        os.path.join(wd, f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not f.lower().endswith('.bak')
        and not f.lower().endswith('.bak2')
        and not f.lower().endswith('.bak3')
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
        print(f"  {C('Would restyle')}: {counts.get('dry',0)}  {D('Skip')}: {counts.get('skip',0)}")
    else:
        print(f"  {G('Restyled')}: {counts.get('patched',0)}  {D('Skip')}: {counts.get('skip',0)}")

    if not rev and not dry and counts.get('patched', 0):
        git_msg = 'git commit -m "Restyle all pages with unified dark design system"'
        print(f"\n  {B('Push to GitHub:')}")
        print(f"    {C('git add .')}")
        print(f"    {C(git_msg)}")
        print(f"    {C('git push')}")
    print()

if __name__ == '__main__':
    main()
