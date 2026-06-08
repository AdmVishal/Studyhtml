#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         StudyHub — Mobile Patch Injector  (patch.py)        ║
║                                                              ║
║  Injects mobile.css + sidebar JS into every .html file      ║
║  in the current directory (or a specified path).            ║
║                                                              ║
║  Usage:                                                      ║
║    python3 patch.py            # patch current directory     ║
║    python3 patch.py --dry-run  # preview only, no changes   ║
║    python3 patch.py --undo     # remove injected patches     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import re
from datetime import datetime

# ── Configuration ──────────────────────────────────────────
CSS_FILE       = "mobile.css"
BACKUP_SUFFIX  = ".bak"
SKIP_FILES     = {"index.html"}          # already mobile-friendly
INJECT_MARKER  = "<!-- MOBILE-PATCH -->" # tag to detect already-patched files

# What we inject just before </head>
CSS_INJECT = f"""  {INJECT_MARKER}
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <link rel="stylesheet" href="{CSS_FILE}">"""

# Sidebar toggle JS — injected just before </body>
# Only activates on pages that have a sidebar element
JS_INJECT = """  <!-- MOBILE-PATCH-JS -->
  <script>
  (function() {
    // Only run on mobile
    if (window.innerWidth > 768) return;

    var sidebar = document.querySelector(
      '.sidebar, [class*="sidebar"], [id*="sidebar"], nav.sidebar'
    );
    if (!sidebar) return;

    // Create overlay
    var overlay = document.createElement('div');
    overlay.id = 'mobile-sidebar-overlay';
    document.body.appendChild(overlay);

    // Create hamburger button
    var btn = document.createElement('button');
    btn.id = 'mobile-menu-btn';
    btn.setAttribute('aria-label', 'Open menu');
    btn.innerHTML = '&#9776;';
    document.body.appendChild(btn);

    // Toggle logic
    function openSidebar() {
      sidebar.classList.add('open');
      overlay.classList.add('show');
      btn.innerHTML = '&#10005;';
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
      btn.innerHTML = '&#9776;';
    }
    btn.addEventListener('click', function() {
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
    overlay.addEventListener('click', closeSidebar);

    // Close on nav link tap
    sidebar.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', closeSidebar);
    });
  })();
  </script>"""

# ── Colours for terminal output ────────────────────────────
def c(text, code): return f"\033[{code}m{text}\033[0m"
def green(t):  return c(t, "0;32")
def yellow(t): return c(t, "0;33")
def red(t):    return c(t, "0;31")
def cyan(t):   return c(t, "0;36")
def bold(t):   return c(t, "1;37")
def dim(t):    return c(t, "0;90")


# ── Core patch function ────────────────────────────────────
def patch_file(filepath, dry_run=False):
    filename = os.path.basename(filepath)

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Already patched?
    if INJECT_MARKER in content:
        print(f"  {dim('⟳  already patched')}  {dim(filename)}")
        return "already"

    modified = content

    # ── Fix viewport meta if missing or wrong ──────────────
    has_viewport = bool(re.search(
        r'<meta[^>]+name=["\']viewport["\']', content, re.IGNORECASE
    ))

    if has_viewport:
        # Update existing viewport to ensure width=device-width
        modified = re.sub(
            r'<meta[^>]+name=["\']viewport["\'][^>]*>',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">',
            modified, flags=re.IGNORECASE
        )
        # Inject only the CSS link (not the meta again)
        css_only = f"  {INJECT_MARKER}\n  <link rel=\"stylesheet\" href=\"{CSS_FILE}\">"
        modified = re.sub(r'(</head>)', css_only + r'\n\1',
                          modified, count=1, flags=re.IGNORECASE)
    else:
        # Inject both meta and CSS link
        modified = re.sub(r'(</head>)', CSS_INJECT + r'\n\1',
                          modified, count=1, flags=re.IGNORECASE)

    # ── Inject sidebar JS before </body> ───────────────────
    modified = re.sub(r'(</body>)', JS_INJECT + r'\n\1',
                      modified, count=1, flags=re.IGNORECASE)

    if modified == content:
        print(f"  {yellow('⚠  no </head> found')}  {filename}")
        return "skip"

    if dry_run:
        print(f"  {cyan('○  would patch')}        {filename}")
        return "dry"

    # Backup original
    backup_path = filepath + BACKUP_SUFFIX
    shutil.copy2(filepath, backup_path)

    # Write patched version
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(modified)

    print(f"  {green('✔  patched')}            {filename}  {dim(f'(backup: {filename}.bak)')}")
    return "patched"


# ── Undo / remove patches ──────────────────────────────────
def undo_file(filepath):
    filename = os.path.basename(filepath)
    backup_path = filepath + BACKUP_SUFFIX

    if os.path.exists(backup_path):
        shutil.copy2(backup_path, filepath)
        os.remove(backup_path)
        print(f"  {green('✔  restored')}           {filename}")
        return "restored"
    else:
        print(f"  {yellow('⚠  no backup found')}    {filename}")
        return "skip"


# ── Main ───────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    undo    = "--undo"    in args

    # Determine working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir   = script_dir

    # Print banner
    print()
    print(bold("  ╔══════════════════════════════════════════╗"))
    print(bold("  ║   StudyHub Mobile Patch Injector        ║"))
    print(bold("  ╚══════════════════════════════════════════╝"))
    print()
    print(f"  Dir      : {cyan(work_dir)}")
    print(f"  CSS file : {cyan(CSS_FILE)}")
    print(f"  Mode     : {yellow('DRY RUN (no files changed)') if dry_run else (red('UNDO patches') if undo else green('PATCH'))}")
    print()

    # Check mobile.css exists (for patching mode)
    if not undo:
        css_path = os.path.join(work_dir, CSS_FILE)
        if not os.path.exists(css_path):
            print(red(f"  ✗  {CSS_FILE} not found in {work_dir}"))
            print(yellow(f"     Copy mobile.css into your Studyhtml folder first.\n"))
            sys.exit(1)

    # Collect HTML files
    html_files = sorted([
        os.path.join(work_dir, f)
        for f in os.listdir(work_dir)
        if f.lower().endswith(".html") and f not in SKIP_FILES
    ])

    if not html_files:
        print(yellow("  ⚠  No HTML files found.\n"))
        sys.exit(0)

    print(f"  Found {bold(str(len(html_files)))} HTML file(s) to process:\n")

    # Process each file
    counts = {"patched": 0, "already": 0, "restored": 0, "skip": 0, "dry": 0}
    for fp in html_files:
        if undo:
            result = undo_file(fp)
        else:
            result = patch_file(fp, dry_run=dry_run)
        counts[result] = counts.get(result, 0) + 1

    # Summary
    print()
    print(f"  {'─'*44}")
    if undo:
        print(f"  {green('Restored')} : {counts['restored']}   "
              f"{yellow('No backup')} : {counts['skip']}")
    elif dry_run:
        print(f"  {cyan('Would patch')} : {counts['dry']}   "
              f"{dim('Already OK')} : {counts['already']}")
    else:
        print(f"  {green('Patched')}   : {counts['patched']}   "
              f"{dim('Already OK')} : {counts['already']}   "
              f"{yellow('Skipped')} : {counts['skip']}")
    print()

    if not undo and not dry_run and counts["patched"] > 0:
        print(f"  {green('✔  Done!')} All pages are now mobile-friendly.")
        print(f"  {dim('Backups saved as .html.bak — run with --undo to revert.')}")
        print()
        git_commit = 'git commit -m "Add mobile responsiveness"'
        print(f"  Commit to GitHub:")
        print(f"    {cyan('git add .')}")
        print(f"    {cyan(git_commit)}")
        print(f"    {cyan('git push')}")
    elif not undo and not dry_run and counts["patched"] == 0:
        print(f"  {green('✔  All files already patched — nothing to do.')}")

    print()


if __name__ == "__main__":
    main()
