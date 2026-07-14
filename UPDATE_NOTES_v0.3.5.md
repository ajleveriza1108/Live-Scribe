# Live Scribe v0.3.5

## Reliability update

This release consolidates the fixes found during Windows source testing.

### Fixed

- Restored all UI button handlers to the `TaglishTranscriberApp` class.
- Fixed the `_start_requested` startup crash.
- Added an automated test that checks required UI handlers.
- Updated the Windows launcher to support both `.venv + app.py` and portable builds.
- Updated Linux and macOS launchers with the same source/portable behavior.
- Improved Windows development setup when Python 3.11 is missing.
- Fixed the GitHub push helper when the `origin` remote does not yet exist.
- Retained the temporary live model-download progress panel.
- Retained the separate `Stop & Save WAV` and `Verify from WAV` workflow.

The app still requires real microphone and model-inference testing before a buyer release.
