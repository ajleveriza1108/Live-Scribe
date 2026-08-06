from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=(Path('data/hardware_profile.json'),Path('data/.first-run-complete'),Path('data/unfinished_session.json'),Path('data/sessions.sqlite3'),Path('data/sessions.sqlite3-shm'),Path('data/sessions.sqlite3-wal'))
ALLOWED_MODELS={Path('models/.gitkeep')}; ALLOWED_EXPORTS={Path('exports/.gitkeep')}; ALLOWED_RECORDINGS={Path('recordings/.gitkeep')}
def tracked_paths():
    if not (ROOT/'.git').is_dir(): return None
    try: r=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=False)
    except OSError: return None
    if r.returncode!=0: return None
    return {Path(x.decode('utf-8',errors='replace')) for x in r.stdout.split(b'\0') if x}
def publishable(folder:Path):
    tracked=tracked_paths(); prefix=folder.relative_to(ROOT)
    if tracked is not None: return {p for p in tracked if p==prefix or prefix in p.parents}
    if not folder.is_dir(): return set()
    return {p.relative_to(ROOT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
def versions():
    out={}
    s=(ROOT/'src/taglish_transcriber/__init__.py').read_text(encoding='utf-8'); m=re.search(r'__version__\s*=\s*"([^"]+)"',s); out['package']=m.group(1) if m else ''
    s=(ROOT/'src/taglish_transcriber/ui.py').read_text(encoding='utf-8'); m=re.search(r'text="Version\s+([^"]+)"',s); out['ui']=m.group(1) if m else ''
    s=(ROOT/'scripts/build_portable.py').read_text(encoding='utf-8'); m=re.search(r'VERSION\s*=\s*"([^"]+)"',s); out['builder']=m.group(1) if m else ''
    s=(ROOT/'portable_app.spec').read_text(encoding='utf-8'); m=re.search(r'"CFBundleShortVersionString":\s*"([^"]+)"',s); out['spec']=m.group(1) if m else ''
    return out
def run_preflight():
    errors=[]; tracked=tracked_paths()
    for rel in FORBIDDEN:
        if (rel in tracked if tracked is not None else (ROOT/rel).exists()): errors.append(f'Runtime file must not be published: {rel}')
    for rel in sorted(publishable(ROOT/'models')-ALLOWED_MODELS): errors.append(f'Downloaded model must not be published: {rel}')
    for rel in sorted(publishable(ROOT/'exports')-ALLOWED_EXPORTS): errors.append(f'Generated export must not be published: {rel}')
    for rel in sorted(publishable(ROOT/'recordings')-ALLOWED_RECORDINGS): errors.append(f'Runtime recording must not be published: {rel}')
    v=versions(); nonempty={x for x in v.values() if x}
    if len(nonempty)!=1 or any(not x for x in v.values()): errors.append('Version metadata is inconsistent: '+', '.join(f'{k}={x or "missing"}' for k,x in v.items()))
    return errors,{'status':'failed' if errors else 'ok','root':str(ROOT),'using_git_index':tracked is not None,'versions':v,'error_count':len(errors),'errors':errors}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); e,r=run_preflight()
    if a.json: print(json.dumps(r,indent=2))
    elif e:
        print('Live Scribe repository preflight failed:'); [print('  - '+x) for x in e]
    else: print('Live Scribe repository preflight passed for version '+next(iter(set(r['versions'].values())))+'.')
    return 1 if e else 0
if __name__=='__main__': raise SystemExit(main())
