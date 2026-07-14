# Live Scribe — Project Context

## Current version

0.6.0

## Repository

`https://github.com/ajleveriza1108/Live-Scribe.git`

## Product definition

A portable, cross-platform, local-first desktop transcription product for English, Tagalog/Filipino, and natural Taglish. The buyer package bundles application dependencies but downloads selected ASR model weights only once.

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
13. The current language selector remains limited to English, Tagalog/Filipino, and Taglish until other languages are tested.
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
11. Export final TXT/SRT/DOCX; optionally include live appendix.

## Future optional packs

- DeepFilterNet neural speech enhancement.
- Qwen3-ASR multilingual final-pass alternative.
- whisper.cpp quantized compact edition.
- Optional small GGUF post-editor for deeper grammar explanations.
- Speaker diarization pack for multi-speaker sessions.

Optional packs must be separately downloadable, license-reviewed, checksum-verified, removable, and disabled by default.

## v0.6.0 interface direction

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

## v0.6.0 topic profile direction

Live Scribe now includes local editable Topic Profiles. The user chooses a
profile before starting a session. Topic terms are prioritized in Faster-Whisper
hotwords, and a short profile description is appended to the language-specific
initial prompt. The selected profile snapshot is reused during Verify from WAV.

Starter profiles cover general conversation, office meetings, classes,
Zoom/Google Meet, interviews, church, livestreams, technology, e-commerce, and
news. Users can add, edit, or remove profiles in the modern Topics page. No LLM
or separate model download is involved.

