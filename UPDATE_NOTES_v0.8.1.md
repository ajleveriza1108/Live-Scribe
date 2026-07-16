# Live Scribe v0.8.1

## Added

- Selected Windows application audio architecture and live on/off toggle.
- Automated Windows helper build workflow.
- Offline Summarize & Format button and tab.
- Full-surface clickable microphone and audio-source dropdowns.
- Disabled labels for microphones that cannot currently be opened.
- Live Test Input sound meter without transcription or recording.
- Existing live-session audio meter remains active.

## Platform boundary

Selected-app capture requires Windows build 20348 or newer and the native
helper produced by the included GitHub Actions workflow. The option remains
disabled until that helper is installed. Normal whole-computer loopback
remains cross-platform according to each operating system's existing setup.
