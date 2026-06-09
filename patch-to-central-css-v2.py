#!/usr/bin/env python3
"""patch_to_central_css.py  v2 — strips inline CSS, links studyhub.css, injects mobile drawer"""
import os, sys, re, shutil

BACKUP_EXT = ".bak4"
MARKER     = "<!-- SHUB-v4 -->"
CSS_FILE   = "studyhub.css"
SKIP       = {"index.html"}

def c(t, code): return f"\033[{code}m{t}\033[0m"
G = lambda t: c(t,"0;32"); Y = lambda t: c(t,"0;33"); R = lambda t: c(t,"0;31")
C = lambda t: c(t,"0;36"); B = lambda t: c(t,"1;37"); D = lambda t: c(t,"0;90")

TITLES = {
    "ccna study notes.html":                 "CCNA Study Notes",
    "network study reference.html":          "Network Study Reference",
    "linux admin interview studyguide.html": "Linux Admin Interview Guide",
    "os admin l3 interview prep.html":       "OS Admin L3 Interview Prep",
    "master interview hub.html":             "Master Interview Hub",
    "nutanix foundations guide.html":        "Nutanix Foundations Guide",
    "itil-unix-interview-prep.html":         "ITIL & Unix Interview Prep",
    "rhel study guide.html":                 "RHEL Study Guide",
}
def get_title(fname):
    return TITLES.get(fname.lower(), fname.replace(".html","").replace("-"," ").title())

HEAD_INJECT = """\
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="studyhub.css">"""

def make_chrome(title):
    safe = title.replace('"','&quot;')
    return f"""<!-- SHUB-v4 -->
<div id="shub-topbar">
  <a class="shub-logo" href="index.html">Study<span>Hub</span></a>
  <span class="shub-title">{safe}</span>
  <div class="shub-spacer"></div>
  <a class="shub-home" href="index.html">
    <svg width="11" height="11" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 9l7-7 7 7M4 8v9a1 1 0 001 1h4v-5h2v5h4a1 1 0 001-1V8"/></svg>
    <span>All Guides</span>
  </a>
</div>
<div id="shub-prog"></div>
<button id="shub-btt" title="Back to top">&#8593;</button>
<div id="shub-drawer-ov"></div>
<nav id="shub-drawer">
  <div id="shub-drawer-head">
    <span>Contents</span>
    <button id="shub-drawer-close">&#10005;</button>
  </div>
  <a id="shub-drawer-back" href="index.html">&#8592; Study Hub</a>
  <div id="shub-drawer-list"></div>
</nav>
<button id="shub-topics-fab">&#9776; Topics</button>
<script id="shub-chrome-js">
(function(){{
  var prog=document.getElementById('shub-prog'),btt=document.getElementById('shub-btt');
  window.addEventListener('scroll',function(){{
    var h=document.documentElement,st=h.scrollTop||document.body.scrollTop;
    var sh=(h.scrollHeight||document.body.scrollHeight)-h.clientHeight;
    if(prog)prog.style.width=(sh>0?Math.min(st/sh*100,100):0)+'%';
    if(btt)btt.classList.toggle('vis',st>280);
  }},{{passive:true}});
  if(btt)btt.addEventListener('click',function(){{window.scrollTo({{top:0,behavior:'smooth'}});}});
  if(window.innerWidth>767)return;
  var ov=document.getElementById('shub-drawer-ov'),dr=document.getElementById('shub-drawer');
  var dc=document.getElementById('shub-drawer-close'),fab=document.getElementById('shub-topics-fab');
  var list=document.getElementById('shub-drawer-list');
  if(!dr||!fab)return;
  function open(){{dr.classList.add('on');ov.classList.add('on');document.body.style.overflow='hidden';fab.innerHTML='&#10005; Close';}}
  function close(){{dr.classList.remove('on');ov.classList.remove('on');document.body.style.overflow='';fab.innerHTML='&#9776; Topics';}}
  fab.addEventListener('click',function(){{dr.classList.contains('on')?close():open();}});
  dc.addEventListener('click',close);
  ov.addEventListener('click',close);
  document.addEventListener('keydown',function(e){{if(e.key==='Escape')close();}});
  var built=false;
  function build(){{
    if(built)return;
    var sels=['.sidebar .nav-btn','.sidebar .nav-item','.sidebar .sidebar-item','.sidebar .topic-btn','#sidebar button','.nav-panel button'];
    var items=[];
    for(var s=0;s<sels.length;s++){{items=Array.from(document.querySelectorAll(sels[s]));if(items.length)break;}}
    if(!items.length)return;
    built=true;list.innerHTML='';
    var sidebar=document.querySelector('.sidebar,#sidebar,.nav-panel');
    if(sidebar){{
      Array.from(sidebar.children).forEach(function(child){{
        var cls=child.className||'';
        if(cls.includes('section')||cls.includes('group-label')||cls.includes('sidebar-section')){{
          var t=child.textContent.trim();
          if(t.length>1){{var s=document.createElement('div');s.className='shub-dl-sec';s.textContent=t;list.appendChild(s);}}
          return;
        }}
        if(child.tagName==='BUTTON'||cls.includes('nav-btn')||cls.includes('nav-item')||cls.includes('sidebar-item')||cls.includes('topic-btn')){{mkItem(child);return;}}
        child.querySelectorAll('button,[class*="nav-btn"],[class*="nav-item"]').forEach(function(n){{mkItem(n);}});
      }});
    }}else{{items.forEach(function(o){{mkItem(o);}});}}
    sync();
  }}
  function mkItem(orig){{
    var btn=document.createElement('button');btn.className='shub-dl-item';
    var numEl=orig.querySelector('.num,.sidebar-count,[class*="num"]');
    var numTxt=numEl?numEl.textContent.trim():'';
    var label=orig.textContent.replace(numTxt,'').trim();
    if(!label||label.length<2)return;
    if(numTxt){{var ns=document.createElement('span');ns.className='shub-dl-num';ns.textContent=numTxt;btn.appendChild(ns);}}
    btn.appendChild(document.createTextNode(label));
    btn.addEventListener('click',function(){{orig.click();setTimeout(close,180);}});
    list.appendChild(btn);
  }}
  function sync(){{
    var active=document.querySelector('.sidebar .nav-btn.active,.sidebar .nav-item.active,.sidebar .sidebar-item.active,#sidebar button.active');
    var at=active?active.textContent.trim():'';
    list.querySelectorAll('.shub-dl-item').forEach(function(it){{it.classList.toggle('cur',at.length>0&&at.includes(it.textContent.trim()));}});
  }}
  var sb=document.querySelector('.sidebar,#sidebar');
  if(sb)new MutationObserver(function(){{sync();}}).observe(sb,{{attributes:true,subtree:true,attributeFilter:['class']}});
  function init(){{build();if(!built){{var n=0,t=setInterval(function(){{build();if(built||++n>40)clearInterval(t);}},100);}}}}
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',function(){{setTimeout(init,200);}}):setTimeout(init,200);
}})();
</script>"""

OLD_STYLE_IDS=["shub-theme","shub-theme-v2","shub-unified","studyhub-unified","shub-light-extras","shub-dark-extras","shn-styles","shn-page-mobile","shm-v4","mob-fix-css","rhel-mob-css","itil-mob-css","nm3-css","shub-a-css","shub-b-css","shub-c-css","shub-d-css","net-mob-css"]
OLD_SCRIPT_IDS=["shub-chrome","shub-chrome-js","shub-theme-js","shn-js","shm-js","rhel-mob-js","itil-mob-js","nm3-js","shub-master-js","shub-c-js","net-mob-js","ccna-mobile-script"]
OLD_EL_IDS=["shub-topbar","shub-prog","shub-btt","shub-drawer","shub-drawer-ov","shub-drawer-head","shub-drawer-back","shub-drawer-list","shub-drawer-close","shub-topics-fab","shn-overlay","shn-nav","shn-btn","nmf-overlay","nmf-drawer","nmf-btn","nm3-ov","nm3-dr","nm3-bar","nm3-ls","nm3-pl","nm3-tb","rhel-ov","rhel-dr","rhel-bar","rhel-list","rhel-pills","rhel-tbtn","itil-ov","itil-dr","itil-nav-btn","itil-list","shub-c-btn","shub-c-ov","shub-c-dr","shub-c-list","mob-overlay","mob-sidebar-close","mob-topics-btn"]
OLD_COMMENTS=["<!-- SHUB-THEME-v1 -->","<!-- SHUB-THEME-v2 -->","<!-- RESTYLE-v1 -->","<!-- CENTRAL-CSS-v1 -->","<!-- SHUB-v4 -->","<!-- SHN-v3 -->","<!-- NET-MOBILE-FIX-v1 -->","<!-- NET-MOB-v2 -->","<!-- NM-FIX-CLEAN -->","<!-- RHEL-MOB -->","<!-- ITIL-MOB -->","<!-- STUDYHUB-MOBILE-v4 -->","<!-- STUDYHUB-MASTER-v1 -->","<!-- CCNA-MOBILE-FIX -->"]

def clean(html):
    html=re.sub(r'<style[^>]*>.*?</style>','',html,flags=re.DOTALL|re.I)
    html=re.sub(r'<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com|mobile\.css|studyhub\.css|patch\.css|mobile_master)[^>]*/?>','',html,flags=re.I)
    html=re.sub(r"@import url\(['\"][^)]+googleapis[^)]+\)['\"];?\s*",'',html,flags=re.I)
    for eid in OLD_STYLE_IDS:
        html=re.sub(r"<style[^>]+id=['\"]"+re.escape(eid)+r"['\"][^>]*>.*?</style>",'',html,flags=re.DOTALL|re.I)
    for eid in OLD_SCRIPT_IDS:
        html=re.sub(r"<script[^>]+id=['\"]"+re.escape(eid)+r"['\"][^>]*>.*?</script>",'',html,flags=re.DOTALL|re.I)
    for eid in OLD_EL_IDS:
        html=re.sub(r"<(?:div|nav|button|a|script)\b[^>]*\bid=['\"]"+re.escape(eid)+r"['\"][^>]*>.*?</(?:div|nav|button|a|script)>",'',html,flags=re.DOTALL|re.I)
        html=re.sub(r"<[^>]+\bid=['\"]"+re.escape(eid)+r"['\"][^>]*>",'',html,flags=re.I)
    for m in OLD_COMMENTS: html=html.replace(m,'')
    html=re.sub(r'\n{4,}','\n\n',html)
    return html

def patch(path,dry=False):
    fname=os.path.basename(path)
    with open(path,encoding='utf-8',errors='replace') as f: orig=f.read()
    if MARKER in orig:
        print(f"  {D('⟳  already done')}  {D(fname)}"); return 'skip'
    style_count=len(re.findall(r'<style[^>]*>',orig,re.I))
    html=clean(orig)
    vp='<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
    if re.search(r'<meta[^>]+name=["\']viewport["\']',html,re.I):
        html=re.sub(r'<meta[^>]+name=["\']viewport["\'][^>]*/?>',vp,html,flags=re.I)
    else:
        html=re.sub(r'(<head[^>]*>)',r'\1\n  '+vp,html,count=1,flags=re.I)
    html=re.sub(r'(</head>)',HEAD_INJECT+r'\n\1',html,count=1,flags=re.I)
    title=get_title(fname); chrome=make_chrome(title)
    html=re.sub(r'(<body[^>]*>)',r'\1\n'+chrome+'\n',html,count=1,flags=re.I)
    if dry:
        print(f"  {C('○')}  {fname}  {D('['+str(style_count)+' style blocks]')}"); return 'dry'
    shutil.copy2(path,path+BACKUP_EXT)
    with open(path,'w',encoding='utf-8') as f: f.write(html)
    print(f"  {G('✔')}  {fname}  {D('['+str(style_count)+' style blocks removed]')}"); return 'patched'

def undo(path):
    fname=os.path.basename(path); bak=path+BACKUP_EXT
    if os.path.exists(bak):
        shutil.copy2(bak,path); os.remove(bak)
        print(f"  {G('✔  restored')}  {fname}"); return 'ok'
    print(f"  {Y('⚠  no backup')}  {fname}"); return 'skip'

def main():
    args=sys.argv[1:]; dry='--dry-run' in args; rev='--undo' in args
    wd=os.path.dirname(os.path.abspath(__file__))
    print(); print(B("  ╔══════════════════════════════════════════════════╗"))
    print(B("  ║  StudyHub Central CSS Patcher  v2                 ║"))
    print(B("  ╚══════════════════════════════════════════════════╝"))
    print(f"\n  Mode: {Y('DRY RUN') if dry else (R('UNDO') if rev else G('APPLY'))}\n")
    if not rev:
        if not os.path.exists(os.path.join(wd,CSS_FILE)):
            print(R(f"  ✗  {CSS_FILE} not found")); sys.exit(1)
    files=sorted(os.path.join(wd,f) for f in os.listdir(wd)
        if f.lower().endswith('.html')
        and not any(f.lower().endswith(e) for e in ('.bak','.bak2','.bak3','.bak4'))
        and f not in SKIP)
    if not files: print(Y("  No HTML files found.")); sys.exit(0)
    print(f"  {B(str(len(files)))} pages:\n")
    counts={}
    for fp in files:
        r=undo(fp) if rev else patch(fp,dry); counts[r]=counts.get(r,0)+1
    print(f"\n  {'─'*50}")
    if rev:   print(f"  {G('Restored')}: {counts.get('ok',0)}  {Y('No backup')}: {counts.get('skip',0)}")
    elif dry: print(f"  {C('Would patch')}: {counts.get('dry',0)}  {D('Skip')}: {counts.get('skip',0)}")
    else:     print(f"  {G('Patched')}: {counts.get('patched',0)}  {D('Skip')}: {counts.get('skip',0)}")
    if not rev and not dry and counts.get('patched',0):
        git_msg='git commit -m "Central CSS v2: unified style + mobile drawer"'
        print(f"\n  {B('Push:')}"); print(f"    {C('git add .')}"); print(f"    {C(git_msg)}"); print(f"    {C('git push')}")
    print()

if __name__=='__main__': main()
