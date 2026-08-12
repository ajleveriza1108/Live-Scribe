# Live Scribe repository audit — v0.9.2

## Repository state reviewed
The public `main` branch was reviewed at v0.8.2.

## Major findings
1. Windows exposed both whole-computer and selected-application capture.
2. Live sessions used large audio/phrase queues and an unbounded event queue.
3. Faster-Whisper had no explicit worker/thread limits or unload lifecycle.
4. Source startup required an existing `.venv` or packaged EXE.
5. Test Input cleanup could block the GUI on slow Windows audio drivers.
6. The public repository tracked a machine-specific hardware report and a first-run completion marker.
7. Ordinary pushes and pull requests had no cross-platform source CI.

## Upgrade implemented
- strict Windows selected-application process-tree capture
- selected microphone listening and output selection
- responsive background audio-device cleanup
- hidden inactive input/output devices and full-surface dropdowns
- automatic Windows source setup
- Smart Silero VAD through Faster-Whisper
- bounded queues and low-RAM resource policy
- one model worker, limited CPU threads, model reuse and RAM release
- repository preflight, privacy checks, and cross-platform source CI

## Remaining hardware validation
Windows process loopback, browser process behavior, USB/Bluetooth monitoring, macOS/Linux routing, long sessions, recovery, and measured RAM use still require physical testing.

## v0.9.2 follow-up

Call / Conversation Mode adds selected-app + microphone dual capture without adding a second Whisper model. Plain English remains region-neutral; optional US, UK, Australian, Canadian, Indian, and Filipino English profiles all reuse the existing English ASR path with light local recognition context.
