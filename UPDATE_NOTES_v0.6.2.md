# Live Scribe v0.6.2

## Portable flash-drive hardening

- Confirmed the buyer release as a PyInstaller one-folder portable build.
- Redirected Hugging Face Hub, Xet, XDG, Python cache, and temporary files into
  `.cache` beside the application.
- Added a first-run 32 MB portable-storage quick-write test.
- Added removable/external/network drive identification where the operating
  system exposes enough information.
- Added portable-drive speed notes to the PC capability report.
- Slow drives warn and prefer Compact but do not automatically block models.
- Added Check This PC Again support for rerunning the storage test.
- Added atomic settings and vocabulary writes.
- Prevented application closure during downloads, recordings, model loading,
  and WAV verification.
- Added PORTABLE_USE.txt and a portable-folder marker to buyer builds.
- Updated Windows, Linux, and macOS launchers to keep writable state local.
