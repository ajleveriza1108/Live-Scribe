# Live Scribe

**Current language edition:** English, Tagalog/Filipino, and Taglish. Additional languages are planned for later releases.


**Portable offline live transcription for English, Tagalog/Filipino, and natural Taglish.**

Version **0.6.2** uses two explicit stages: a fast live transcript while the speaker is talking, followed—only when the user clicks **Verify from WAV**—by a careful full-recording review. **Stop & Save WAV** only ends the live session and safely saves the recording.

## Modern interface

Live Scribe now uses a modern, minimal CustomTkinter interface with:

- OLED Black and Dirty White themes
- A transcript-first Live Session workspace
- Compact navigation for Vocabulary, Models, and Settings
- Sticky recording and WAV-verification controls
- A temporary model-download progress card with **Stop Download** and safe resume
- Buyer-friendly speech-quality names and download sizes

## Supported language modes

- English
- Filipino / Tagalog
- English + Filipino / Taglish
- Spanish
- French
- German
- Italian
- Portuguese
- Dutch
- Auto Detect

One downloaded multilingual speech model handles all supported language modes.

## Buyer-friendly speech quality choices

| Choice shown in Live Scribe | Approximate download | Guidance |
|---|---:|---|
| Compact | 486 MB | Fastest and smallest; lower accuracy |
| Balanced | 1.53 GB | Good accuracy for CPU use |
| Best Overall | 1.62 GB | Recommended speed and accuracy balance |
| Maximum Accuracy | 3.09 GB | Highest quality; largest and slowest |

The internal Whisper model names are intentionally hidden from normal buyers.


## Livestream and computer-audio transcription

Live Scribe can now transcribe audio that is playing on the computer:

1. Set **Listen to** to **Computer audio / livestream**.
2. Click **Detect** and choose the output used by the livestream.
3. Start the YouTube, Facebook Live, Zoom, OBS, browser, meeting, or media audio.
4. Click **Start Listening**.
5. Live text appears phrase-by-phrase while the same audio is saved to WAV.
6. Click **Stop & Save WAV**, then **Verify from WAV** for the separate accuracy pass.

Platform behavior:

- **Windows:** Uses WASAPI loopback for the selected speakers or headphones.
- **Linux:** Uses an available PulseAudio/PipeWire monitor source.
- **macOS:** Requires a virtual audio input such as BlackHole because macOS does
  not expose system-output loopback directly. Route the livestream output to
  the virtual device, then select it in Live Scribe.

Live Scribe captures the audio being played by the computer. It does not require
the livestream URL and does not download the video.

## First-run model flow

The portable application and its dependencies are already present after setup or extraction. Launching the app does **not** download a speech model.

1. Open the app.
2. Choose a buyer-friendly speech quality in **Models**.
3. Click **Download Selected Quality**.
4. A progress card shows the downloaded size, total size, percentage, speed, and estimated time remaining.
5. Click **Stop Download** whenever the connection is unstable or the download must be paused.
6. Wait until the progress card disappears before closing Live Scribe.
7. Partial model files are preserved. Click **Download Selected Quality** again later to resume rather than restart.
8. **Start Listening** becomes available only after the chosen model is complete.
9. The same completed model is reused offline in later sessions.

A different model is downloaded only when the buyer explicitly chooses another speech quality and presses the download button.


## Topic Profiles — no additional LLM required

Live Scribe includes editable **Topic Profiles** that help the existing
Faster-Whisper speech model recognize likely names, acronyms, products, platforms,
and specialized terms. Topic Profiles are small local JSON records; selecting one
does not download another model and does not require an LLM.

Starter profiles included:

1. General Conversation
2. Office & Business Meeting
3. School, Class & Lecture
4. Zoom, Google Meet & Online Meeting
5. Interview & Research
6. Church, Sermon & Bible Study
7. Livestream, Webinar & Presentation
8. Technology & Programming
9. E-commerce & Online Selling
10. News & Current Events

### Using a topic during transcription

1. Open **Live Session**.
2. Choose the closest profile under **Topic profile**.
3. Start listening normally.
4. Live Scribe combines the selected topic terms with the local Vocabulary
   Manager and Markdown ASR hints.
5. The same topic context is retained for the separate **Verify from WAV** pass.

### Add, edit, and remove profiles

Open **Topics** from the sidebar.

- **Add New** creates a local reusable profile.
- **Save Changes** edits the selected profile.
- **Remove Selected** deletes it from the current portable copy.
- **Clear Form** prepares the editor for a new profile.

A profile contains:

- a short profile name
- a short description of the recording
- important names and words, entered one per line or separated by commas

Do not paste a complete transcript or manuscript. Topic context is only a
recognition hint. Important information must still be checked against the WAV.


## What v0.6.2 does

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

For difficult words, open the in-app **Vocabulary Manager** or edit `dictionary/pronunciation_guide.json`. The manager now provides explicit controls to:

- **Add New** vocabulary and pronunciation entries
- select an existing entry and **Save Changes**, including renaming its correct spelling
- **Remove Selected** entries that are no longer needed

Enter the correct written spelling and one or more ways the term may sound or be mistakenly transcribed. The app uses them as recognition hints and may apply exact alias corrections during the final WAV pass. Every applied correction is listed in the review comments.

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

Create and push a tag such as `v0.6.2` to generate a GitHub Release automatically.

## Accuracy notice

The same warning is displayed permanently inside the app and included in formatted DOCX reports. AI-assisted transcription can make mistakes. Always replay the saved WAV when exact names, dates, amounts, addresses, quotations, legal wording, medical wording, or safety-critical instructions matter. Several people speaking at once will reduce accuracy.


## Portable flash-drive operation

Live Scribe is packaged as a **one-folder portable application**. Keep the
complete product folder together and launch it through the included Windows,
Linux, or macOS launcher.

The app keeps these writable files beside the program:

- downloaded speech models
- resumable Hugging Face model cache
- settings and hardware report
- topic profiles
- vocabulary and pronunciation entries
- WAV recordings
- DOCX, TXT, and SRT exports
- temporary files and supporting caches

The launcher sets `LIVE_SCRIBE_HOME` and redirects Hugging Face, XDG, Python
cache, and temporary-file locations into `.cache` inside the portable folder.

### Flash-drive speed

A fast USB 3.x flash drive or portable SSD is recommended. A slow drive mainly
affects:

- application startup
- initial model loading
- model downloads and resume operations
- full-WAV verification
- saving large recordings and exports

After the model is loaded, live transcription depends primarily on the host
computer's CPU, RAM, and compatible GPU.

The first-run PC check now includes a small 32 MB sequential-write test. Storage
speed creates a recommendation or warning; it does not hard-disable a model.
Clear RAM, architecture, and free-space failures remain the only reasons for
automatic model blocking.

### Safe removal

Do not unplug or eject the drive during recording, model download, WAV
verification, export, or profile editing. Live Scribe blocks normal application
closure while a download, recording, model load, or verification is active.
Finish or stop the operation, close the app normally, and then safely eject the
drive.

### Packaging choice

The buyer release remains a PyInstaller **one-folder** build instead of a
single self-extracting executable. This avoids unpacking the full application
into a host-computer temporary folder on every launch and keeps the executable
with its supporting runtime files.

Read `PORTABLE_USE.txt` in the release folder for buyer instructions.


## First-run PC capability check

On the first launch, Live Scribe checks the computer before offering speech-model
downloads. The check uses locally detected information only:

- total system RAM
- CPU thread count
- processor architecture
- available storage in the portable model folder
- whether CTranslate2 can access a compatible NVIDIA GPU
- NVIDIA model name and VRAM when `nvidia-smi` is available

No hardware information is uploaded.

Each buyer-facing speech quality receives one of three results:

- **Recommended for this PC** — the detected computer meets Live Scribe's
  conservative comfort guidance.
- **May run slowly — check the note** — the model remains available because
  Live Scribe cannot determine with certainty that it will fail.
- **Unavailable on this PC** — the model is removed from the download selector
  because RAM, storage, or processor architecture is clearly below the app's
  conservative minimum.

The largest **Maximum Accuracy** option stays available with a clear warning when
the result is uncertain. It is disabled only when the app detects a definite
minimum problem such as insufficient RAM or storage.

Open **Models** and choose **Check This PC Again** after:

- moving the portable folder to another computer
- adding RAM
- freeing storage
- configuring an NVIDIA GPU
- changing the drive used by the portable app

Live Scribe saves the last local report in:

```text
data/hardware_profile.json
```

The compatibility result is a conservative estimate, not a performance
guarantee. Actual speed also depends on audio length, background applications,
CPU generation, cooling, and the selected processing mode.


