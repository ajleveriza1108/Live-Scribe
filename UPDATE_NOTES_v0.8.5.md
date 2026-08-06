# Live Scribe v0.8.5

## Windows source first-start repair

- Windows source folders now prepare their local `.venv` automatically.
- Added a dedicated Python 3.11 source setup script.
- Added a root-level `Start Live Scribe.bat`.
- Added a manual source setup launcher.
- Added clear handling for missing Python 3.11 and failed dependency
  installation.
- Packaged EXE and existing `.venv` startup remain first priority.
- Added regression tests for the launcher bootstrap path.
