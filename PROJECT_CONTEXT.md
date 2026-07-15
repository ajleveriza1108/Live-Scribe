# Live Scribe — Project Context

## Current version

0.7.0

## Repository

`https://github.com/ajleveriza1108/Live-Scribe.git`

## Product definition

A portable, cross-platform, local-first desktop product for live and recorded-media transcription in eight selected languages, plus dedicated Taglish handling. The buyer package bundles application dependencies but downloads selected ASR model weights only once.

## Non-negotiable product rules

1. Windows, macOS, and Linux must be supported from one codebase.
2. Buyer releases use `.bat`, `.sh`, and macOS `.command` launchers.
3. All mutable files remain in the portable product folder.
4. Original microphone audio is saved continuously as WAV.
5. The original WAV must never be overwritten by enhancement.
6. Live transcription prioritizes responsiveness and remains separate from final formatting.
7. After Stop, a complete-WAV accuracy pass creates the final transcript.
8. Significant live/final disagreements become replay comments, not hidden decisions.
9. Grammar and diction feedback must be comments; do not silently rewrite verbatim speech.
10. Custom vocabulary must be editable without changing Python code.
11. Models are not bundled in the base Etsy package.
12. Launching or starting a session must never silently download a model; model downloads require an explicit in-app button press.
13. The advertised language selector remains limited to the eight tested languages, dedicated Taglish mode, and Auto Detect.
14. Difficult terms use editable pronunciation aliases and controlled review comments.
15. Buyer-facing errors remain calm, nontechnical, and actionable.
16. No accuracy guarantee; preserve evidence and disclose uncertainty.

## Current engines

- Faster-Whisper: live and final ASR.
- SoundDevice/PortAudio: microphone capture.
- PCM WAV recorder: concurrent original-audio archive.
- NumPy stationary-noise reducer: optional post-session cleanup.
- Markdown skill/knowledge loader: bounded ASR hotword extraction.
- Custom vocabulary manager: hotwords and explicit replacements.
- Rule-based review engine: grammar, diction, clarity, confidence, and live/final comparison comments.
- python-docx: final report generation.

## Space-saving strategy

- Bundle one tested ASR runtime, not multiple competing frameworks.
- Download only the user-selected speech model.
- Use compact Markdown and text dictionaries for domain context.
- Keep heavier alternatives as optional engine packs.
- Avoid a second LLM in the core package; deterministic review works without another multi-gigabyte model.

## Data flow

1. Auto-detect or select microphone.
2. Capture raw source-rate mono audio.
3. Queue raw blocks to the WAV writer.
4. Resample a copy to 16 kHz for live phrase recognition.
5. Display rough live text after pauses.
6. On Stop, close and validate the WAV.
7. Optionally create `_enhanced.wav` from the original.
8. Run full-file Faster-Whisper with VAD, word timestamps, hotwords, and stronger decoding settings.
9. Apply pronunciation aliases and explicit dictionary replacements.
10. Generate review comments and compare live versus final text.
11. Export DOCX, TXT, SRT, VTT, CSV, or Markdown; optionally include the live appendix.

## Future optional packs

- DeepFilterNet neural speech enhancement.
- Qwen3-ASR multilingual final-pass alternative.
- whisper.cpp quantized compact edition.
- Optional small GGUF post-editor for deeper grammar explanations.
- Speaker diarization pack for multi-speaker sessions.

Optional packs must be separately downloadable, license-reviewed, checksum-verified, removable, and disabled by default.

## v0.6.2 interface direction

The approved buyer interface is CustomTkinter-based, with OLED Black and Dirty
White themes, compact left navigation, transcript-first Live Session page,
buyer-friendly speech-quality labels, and eight selected transcription languages.
Internal model identifiers remain implementation details and are not shown to buyers.

## Model download control

Active model downloads have a Stop Download button. Cancellation preserves partial
Hugging Face files so choosing the same speech quality later resumes the transfer.
The UI must not describe this as deleting or restarting the model.

## Vocabulary manager behavior

The manager exposes explicit Add New, Save Changes, and Remove Selected operations.
Editing may change both the correct written spelling and its pronunciation aliases.

## v0.6.2 topic profile direction

Live Scribe now includes local editable Topic Profiles. The user chooses a
profile before starting a session. Topic terms are prioritized in Faster-Whisper
hotwords, and a short profile description is appended to the language-specific
initial prompt. The selected profile snapshot is reused during Verify from WAV.

Starter profiles cover general conversation, office meetings, classes,
Zoom/Google Meet, interviews, church, livestreams, technology, e-commerce, and
news. Users can add, edit, or remove profiles in the modern Topics page. No LLM
or separate model download is involved.

## v0.6.2 hardware guidance

Live Scribe performs a local hardware assessment at every startup and displays a
buyer-facing notice on the first run. The assessment checks RAM, CPU threads,
architecture, model-drive free storage, CTranslate2 CUDA availability, and
NVIDIA VRAM when available.

Hard download blocking is intentionally limited to clear conditions:
unsupported architecture, RAM below the conservative model minimum, or
insufficient storage for the unfinished download plus a safety reserve. CPU
speed and uncertain GPU support generate caution notes rather than blocks.

The Models page filters unavailable downloads, shows all four compatibility
results, and includes Check This PC Again for portable copies moved between PCs.
The result is saved to data/hardware_profile.json and is never uploaded.

## v0.6.2 portable flash-drive hardening

The buyer build remains PyInstaller onedir/one-folder. Launchers and the frozen
runtime hook force settings, model cache, Xet cache, XDG caches, Python source
cache, and temporary paths under the portable application root.

The first-run hardware check includes a 32 MB sequential-write advisory test.
Slow storage warns and changes the preferred recommendation toward Compact, but
never creates a hard model block. Clear RAM, architecture, and free-space
failures remain the only automatic blockers.

Settings and vocabulary JSON writes are atomic. The GUI prevents normal closure
during model download, recording, model loading, and WAV verification to reduce
the risk of corruption if a removable drive is unplugged.

## v0.7.0 productivity and recorded-media release

The project now supports direct transcription of common recorded video and audio
through Faster-Whisper/PyAV. The media is not copied or modified; video images
are ignored.

Lightweight features include pause/resume, audio health events, floating
captions, transcript editing, manual speakers, timestamp playback, markers,
SQLite session search, throttled recovery, five-minute WAV safety parts, and a
portable storage manager. No new LLM or large AI model is included.

Portable recordings and enhanced WAV paths are serialized relative to APP_ROOT
when possible so saved sessions survive flash-drive letter or mount changes.

## v0.7.1 first-run, recorded-file visibility, privacy, and recording folders

The automatic PC compatibility popup now depends only on
`hardware_check_completed`. A hardware-check implementation version increase no
longer causes the automatic popup to return. Manual Check This PC Again still
shows a requested report.

Recorded-file transcription is promoted in a dedicated Live Session panel
labeled "Already have a recorded video or audio file?" with a
"Choose Video or Audio File" action.

Vocabulary pages explicitly state that vocabulary, topics, sessions,
recordings, and exports stay in the portable app folder and are not uploaded by
Live Scribe.

Live recordings are split into `recordings/In Progress/<session>/part_*.wav`.
The merged file is saved under `recordings/Final Output/`. Safety parts are
retained until the user removes them through Storage Manager. Keeping both forms
uses extra space; completed parts can be safely cleaned after the final WAV is
confirmed.

## v0.7.2 model-download progress correction

Download progress now reserves 100% for the verified `complete` phase. All
other phases are capped at 99%. The modern and legacy UIs switch to
indeterminate animation during `finalizing`, after model data is received but
before required files are confirmed.

`_ProgressTracker.set_initial_bytes` primes resumed data without calculating it
as newly transferred bytes. Unrealistic filesystem rename/copy spikes above
10 GB/s are ignored by the speed smoother. Download units use decimal KB/MB/GB
to align with buyer-facing model-size labels.

## v0.7.3 first-run persistence and clean download cancellation

First-run completion is redundant across `data/.first-run-complete`,
`data/hardware_profile.json`, and the `hardware_check_completed` settings field.
An existing hardware report migrates automatically to the permanent marker.
The state is committed immediately after the initial assessment, before the
remaining GUI initialization.

Model downloads force `HF_HUB_DISABLE_XET=1` in launchers, runtime hooks,
portable environment setup, and immediately before Hugging Face download
imports. The in-memory huggingface_hub constant is also updated when the package
was imported earlier. Stop Download therefore raises the handled cancellation
through the standard Python transfer path instead of an hf-xet worker callback.

## v0.7.4 recorded-file action availability

The primary Choose Video or Audio File button and the action-bar
Transcribe Video / Audio button remain enabled whenever the app is idle. Model
readiness is validated after the click rather than being represented as a
silent disabled control. When no selected downloaded model is available, the
app explains the requirement and offers to navigate to Models.

Both controls remain disabled during model loading/downloading, live capture,
recorded-file transcription, and verification.

