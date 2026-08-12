## R13 — Responsive Session Controls + Interview Floating Captions

- Prevents the expanded meeting/livestream setup panel from pushing the main action buttons below the visible window.
- Converts the workspace setup card into a bounded vertical scroll area and adjusts its height with the Live Scribe window.
- Keeps the transcript/action region usable on shorter displays instead of silently clipping the lower controls.
- Adds a dedicated **Floating Captions (F11)** button to Interview Mode.
- Re-applies the selected Interviewer / Interviewee speaker role to the caption overlay after each interview segment.
- Preserves R11 clean microphone labels and all R12 task-based workspace behavior.

## R12 — Task-Based Workspaces

- Replaced the catch-all Live Session navigation with Online Class & Meetings and Livestreaming workspaces.
- Online Class & Meetings uses selected-app + microphone conversation capture and exposes separate microphone and selected-app audio tests.
- Livestreaming uses selected-app-only capture and hides microphone controls that do not belong to that workflow.
- Interview Mode now includes audio readiness, microphone/app tests, and interview capture controls alongside preparation and private assistance.
- Settings is categorized into General, Transcription, Verification & Export, and Topic Profiles.
- Appearance moved from the sidebar into Settings.
- Topic Profiles moved out of primary navigation and into Settings while preserving full CRUD.
- Sessions now identify livestream source sessions separately from generic live sessions.
- Includes the clean microphone-label behavior that hides internal PortAudio device numbers and migrates old saved labels.
- A later visual-design pass is planned after separate current GUI/UX/UI research; R12 focuses on information architecture and workflow clarity.

# Live Scribe v0.9.2

## Call / Conversation Mode + Global English Profiles

- Added simultaneous selected-application + microphone transcription on Windows.
- Added editable remote/my speaker labels and speaker-aware exports.
- Added separate Caller/Me WAVs plus bounded-memory combined WAV.
- Added source-aware Verify Call Sources.
- Added optional US, UK, Australian, Canadian, Indian, and Filipino English recognition profiles without another model download.
- Plain English remains the region-neutral choice for callers from any country or for mixed/unknown accents.
- Added deterministic offline call notes.
- Kept one Whisper model/transcription worker in Call Mode for lower RAM.
- Preserved Smart Silero VAD, Memory Saver, selected-app isolation, microphone monitoring, recovery, and existing exports.
