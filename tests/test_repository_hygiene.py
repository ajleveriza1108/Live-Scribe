from pathlib import Path
from scripts.repository_preflight import run_preflight
ROOT=Path(__file__).resolve().parents[1]
def test_repository_preflight_passes_clean_source():
    import shutil
    shutil.rmtree(ROOT/'recordings/In Progress/session', ignore_errors=True)
    shutil.rmtree(ROOT/'recordings/In Progress/recover', ignore_errors=True)
    errors,report=run_preflight()
    assert errors==[]
    assert report['status']=='ok'
    assert report['versions']['package']=='0.9.1'
def test_runtime_files_are_ignored_and_absent():
    lines=set((ROOT/'.gitignore').read_text(encoding='utf-8').splitlines())
    assert {'data/hardware_profile.json','data/.first-run-complete','data/unfinished_session.json','data/interview_profiles.json','data/sessions.sqlite3'}.issubset(lines)
    assert not (ROOT/'data/hardware_profile.json').exists(); assert not (ROOT/'data/.first-run-complete').exists()
def test_source_ci_runs_preflight_and_tests():
    s=(ROOT/'.github/workflows/test-source.yml').read_text(encoding='utf-8'); assert 'python scripts/repository_preflight.py' in s; assert 'python -m pytest -q' in s; assert 'windows-2022' in s and 'ubuntu-22.04' in s and 'macos-15' in s
