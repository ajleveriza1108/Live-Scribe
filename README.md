# Live Scribe

**Current language edition:** English, Tagalog/Filipino, and Taglish. Additional languages are planned for later releases.


**Portable offline live transcription for English, Tagalog/Filipino, and natural Taglish.**

Version **0.3.2** uses a two-stage workflow: a fast live transcript while the speaker is talking, followed by a more careful full-recording review after **Stop**. The original microphone audio is saved as WAV throughout the session.

## First-run model flow

The portable application and its dependencies are already present after setup or extraction. Launching the app does **not** download a speech model.

1. Open the app.
2. Select a speech model from the in-app list.
3. Click **Download Selected Model**.
4. Keep the app open until that one-time download finishes.
5. **Start Listening** becomes available only after the chosen model is ready.
6. The same model is reused offline in later sessions.

A different model is downloaded only when the buyer explicitly selects it and presses the download button.

## What v0.3.2 does

- Automatically selects the operating system's default input microphone when available.
- Lets the user choose another detected microphone.
- Writes a rough phrase-level live transcript without slowing the speaker down for formatting.
- Saves the original microphone signal as a 16-bit PCM WAV file during the session.
- Optionally creates a separate noise-reduced WAV after the session; the original is never overwritten.
- Transcribes the complete WAV again using a slower, higher-accuracy Faster-Whisper pass.
- Compares the live pass and final WAV pass and flags significant differences.
- Loads a compact custom dictionary, Markdown `ASR hotwords`, and an editable pronunciation guide to improve names and specialized vocabulary.
- Creates conservative grammar, diction, clarity, and confidence comments after the session.
- Keeps review comments separate from the verbatim transcript.
- Exports final TXT, SRT, and properly formatted DOCX reports.
- Can include the original live transcript as a DOCX appendix.
- Runs locally after the selected speech model has been downloaded once.
- Supports portable releases for Windows, macOS, and Linux.

## Product architecture

```text
Microphone
   ├─ Original WAV recorder ───────────────────────────────┐
   └─ Live phrase detector → fast live transcription      │
                                                          │
Speaker presses Stop                                      │
   ├─ optional steady-noise reduction → enhanced WAV      │
   ├─ complete-WAV final transcription                    │
   ├─ custom dictionary + Markdown hotword hints          │
   ├─ live-versus-final disagreement checks               │
   ├─ grammar/diction/clarity comments                    │
   └─ TXT / SRT / formatted DOCX report ←─────────────────┘
```

The live screen is intentionally simple and may contain rough punctuation. Final formatting and review happen only after the speaker is finished.

## Portable and space-conscious design

The buyer package contains the application runtime and dependencies. It does **not** contain large speech-model weights. On first use, the buyer chooses a Whisper model and downloads it once into the portable `models` folder. The same model is reused offline afterward.

The base package uses one ASR runtime instead of bundling several competing AI stacks. Small skills, knowledge files, dictionary terms, and rule-based review add useful context without requiring a second large language model.

Optional engine ideas are recorded in `engines/engine_registry.json`; they are not silently installed or downloaded.

## Folders buyers should keep together

```text
Live-Scribe/
├── LiveScribe/       packaged application runtime
├── models/                  downloaded speech models
├── recordings/              original and enhanced WAV files
├── exports/                 TXT, SRT, and DOCX files
├── data/                    local settings
├── Skills/                  compact transcription/review instructions
├── Knowledge/               English, Tagalog, Taglish, and ASR notes
├── dictionary/              hotwords and explicit replacements
├── engines/                 optional-engine registry
└── platform launcher
```

Move or copy the **whole folder**. Do not run the app directly inside a ZIP file. A local SSD or portable SSD is recommended for larger models.

## Buyer launchers

### Windows

Double-click:

```text
Start Live Scribe.bat
```

### macOS

Double-click:

```text
Start Live Scribe.command
```

Or run:

```bash
chmod +x "Start Live Scribe.command" start_macos.sh
./start_macos.sh
```

Allow microphone access when macOS asks.

### Linux

```bash
chmod +x start_linux.sh LiveScribe/LiveScribe
./start_linux.sh
```

Allow microphone access through the desktop's privacy or audio settings when required.

## Recommended first settings

- Language: **Auto — English + Tagalog**
- Model: **small**
- Processor: **Auto**
- Microphone: detected system default
- Mic sensitivity: **Normal**
- Final full-WAV accuracy pass: enabled
- Background-noise reduction: enabled for steady fan/air-conditioner noise
- Grammar and diction comments: enabled

Use `medium` or `large-v3-turbo` for a stronger final pass when the computer has enough RAM and processing power.

## Current and future language support

This edition is intentionally limited and optimized for **English**, **Tagalog/Filipino**, and natural **Taglish**. Additional languages are planned for later versions, but they are not exposed in the current interface so buyers do not assume that untested languages are fully supported.

## Dictionary, pronunciation, and wide vocabulary

Before an important session, add names and uncommon terms to:

```text
dictionary/custom_terms.txt
```

Use one entry per line. Good entries include people, churches, schools, barangays, companies, acronyms, product names, technical vocabulary, and frequently used foreign terms.

For difficult words, use the in-app **Vocabulary & Pronunciation** window or edit `dictionary/pronunciation_guide.json`. Enter the correct written spelling and one or more ways the term may sound or be mistakenly transcribed. The app uses them as recognition hints and may apply exact alias corrections during the final WAV pass. Every applied correction is listed in the review comments.

`dictionary/replacements.json` performs explicit automatic replacements during the final pass. Keep it small and include only unambiguous corrections.

Markdown files under `Skills` and `Knowledge` may contain a section named:

```markdown
## ASR hotwords
- Important Name
- Specialized Term
```

The app combines these with the dictionary in a bounded prompt so the list does not grow without limit.

## Noise reduction and diction

The built-in cleanup targets **steady** noise such as fans, air-conditioners, and room hum. It is conservative so it is less likely to damage consonants. It cannot perfectly remove music, overlapping speakers, sudden impacts, echo, or speech that the microphone did not capture clearly.

Diction review concerns wording, repeated fillers, vague words, and readability. It does not medically diagnose pronunciation or speech conditions. The original wording remains in the transcript; suggestions appear in a separate comments area.

## DOCX report

The Word report is generated after the session and can contain:

- title and session metadata
- language mode, model, microphone, and duration
- original and enhanced WAV filenames
- final reviewed transcript with timestamps
- grammar, diction, dictionary, confidence, and WAV-verification comments
- original live transcript appendix
- page numbers and editable Word formatting

## Development setup

Python 3.11 is recommended.

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\dev_setup_windows.ps1"
.\.venv\Scripts\python.exe app.py
```

### macOS or Linux

```bash
chmod +x scripts/dev_setup_unix.sh
./scripts/dev_setup_unix.sh
.venv/bin/python app.py
```

## Tests

```bash
python -m pytest
python -m compileall -q src app.py
```

## Build portable packages

A PyInstaller package must be built on its target operating system. The included GitHub Actions workflow builds Windows x64, Linux x64, macOS Apple Silicon, and macOS Intel archives.

Local build:

```bash
python -m pip install -r requirements-build.txt
python scripts/build_portable.py
```

Create and push a tag such as `v0.3.2` to generate a GitHub Release automatically.

## Accuracy notice

The same warning is displayed permanently inside the app and included in formatted DOCX reports. AI-assisted transcription can make mistakes. Always replay the saved WAV when exact names, dates, amounts, addresses, quotations, legal wording, medical wording, or safety-critical instructions matter. Several people speaking at once will reduce accuracy.
