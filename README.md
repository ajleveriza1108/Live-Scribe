# Live Scribe

**Version 0.9.1**

Live Scribe is a portable, offline transcription application for:

- live microphone transcription
- computer audio, livestreams, Zoom, Google Meet, and other meetings
- recorded video files such as MP4, MKV, MOV, AVI, WebM, M4V, MPEG, MPG, 3GP, TS, and MTS
- recorded audio files such as MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WMA, AIFF, ALAC, and MKA

The app uses one locally downloaded Faster-Whisper speech model. The productivity
features in this release do **not** require another LLM or another large AI
download.


## Recorded-file button availability

**Choose Video or Audio File** is now enabled whenever Live Scribe is idle.

A downloaded speech quality is still required to perform transcription, but the
main file-selection action is no longer silently disabled. When no ready speech
quality is available, clicking the button explains the requirement and offers
to open the Models page.

The button is temporarily disabled only while Live Scribe is:

- listening or recording live audio
- loading a speech model
- downloading a speech model
- transcribing or verifying another recording

## Main workflow

### Live audio

1. Choose **Microphone** or **Computer audio / livestream**.
2. Select the language, topic profile, input, and session title.
3. Click **Start Listening**.
4. Use **Pause** and **Resume** when needed.
5. Click **Stop & Save WAV**.
6. Click **Verify from WAV** for a separate full-recording accuracy pass.

### Recorded video or audio

The feature is on **Live Session**, directly below the session-title field in
the panel labeled **Already have a recorded video or audio file?**

1. Download and select one speech quality.
2. Click **Choose Video or Audio File**.
3. Choose a supported video or audio recording.
4. Live Scribe ignores video images and transcribes the audio track.
5. Correct the result in **Transcript editor**.
6. Export DOCX, TXT, SRT, VTT, CSV, or Markdown.

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

One multilingual model handles every listed language mode. Selecting another
language does not download another model.



## First-run report persistence

The automatic PC compatibility report is now protected by two local signals:

```text
data/.first-run-complete
data/hardware_profile.json
```

The app also retains `hardware_check_completed` in `data/settings.json`.

On a fresh portable copy, the compatibility report is shown once. Live Scribe
writes the completion state immediately after the first hardware assessment and
before the rest of the interface is initialized. Later launches do not replay
the popup, even if settings are partially reset or an older version previously
created only the hardware report.

**Check This PC Again** remains available on the Models page and displays a
report only when the user requests it.

## Clean Stop Download behavior

Live Scribe now disables Hugging Face Xet for model downloads and uses the
standard resumable Hub transfer path. This avoids an hf-xet worker callback
printing a Python traceback when **Stop Download** is pressed.

Stopping a model download now follows this buyer-facing flow:

1. Stop is requested.
2. The standard transfer exits through Live Scribe's handled cancellation.
3. The progress card closes normally.
4. Partial files remain in the portable model folder.
5. Clicking Download Selected Quality later resumes those files.

This change does not add another dependency or model. It may use the standard
HTTP download route instead of Xet's accelerated route so cancellation remains
clean and predictable.

## Accurate model-download progress

Model download progress now separates three stages:

1. **Downloading** — network data is still being transferred.
2. **Finalizing** — expected data has arrived, but Hugging Face is still placing,
   completing, or validating files.
3. **Ready** — all required local model files have been verified.

The progress bar can reach at most **99%** until the model is actually ready.
During finalization it switches to an animated bar with a clear
**Finalizing and verifying** message. A full 100% bar is reserved for the
verified complete state.

Resumed bytes already present on disk are treated as existing progress rather
than newly downloaded data. This prevents false speed readings such as
terabytes per second when Live Scribe starts or resumes a partially downloaded
model.

Download size and speed use decimal KB, MB, and GB so the progress display
matches the buyer-facing approximate model size more closely.

## Buyer-friendly speech quality choices

| Choice | Approximate model download | Typical use |
|---|---:|---|
| Compact | 486 MB | Older PCs, quick tests, smaller flash drives |
| Balanced | 1.53 GB | Good CPU accuracy |
| Best Overall | 1.62 GB | Recommended speed and accuracy balance |
| Maximum Accuracy | 3.09 GB | Strong PCs and difficult recordings |

The internal Whisper model names remain hidden from normal buyers.

## PC and portable-drive check

On the true first run of a portable copy, Live Scribe displays one automatic
PC compatibility report. That automatic popup is not shown again after it has
been acknowledged. Live Scribe may refresh compatibility information silently
on later launches.

The first-run check reads locally detected:

- system RAM
- CPU thread count
- processor architecture
- free model storage
- compatible NVIDIA GPU access and VRAM when available
- portable-drive quick write speed

Each model is marked:

- **Recommended**
- **May run slowly / uncertain**
- **Unavailable**

A model is disabled only for a clear limitation such as insufficient RAM,
unsupported architecture, or insufficient storage. A slow flash drive produces
a warning rather than an automatic block.

Use **Models → Check This PC Again** after moving the portable folder to another
computer or drive. A visible report appears when the user manually requests that
recheck.










## v0.9.1 repository safety and continuous testing

The source repository now has an automated preflight that blocks machine-specific runtime data, downloaded models, recordings, exports, and session databases from publication. Pushes and pull requests run the environment-safe Python 3.11 suite on Windows, Linux, and macOS. See `REPOSITORY_AUDIT.md` and `SECURITY.md`.

## v0.9.0 selected-application and low-RAM core

### Windows computer/livestream audio is application-specific

On Windows, the normal computer/livestream source is now:

```text
Computer / livestream — choose application
```

The user must choose a running window or application. Live Scribe invokes
Windows process-loopback in `includetree` mode, which captures the selected
process and child processes while excluding unrelated applications. There is no
automatic fallback to whole-system capture.

The native helper still requires Windows build 20348 or newer. The repository
workflow uploads the compiled helper as an artifact and can commit it into
`engines/windows`. A local PowerShell builder is also included for computers
with Visual Studio C++ Build Tools and NuGet.

### Smart Silero VAD

Live Scribe reuses Faster-Whisper's bundled offline Silero VAD before Whisper
inference. Clear silence is rejected without loading Torch or downloading a
second VAD model. This reduces unnecessary model calls, phrase-ending delay, and
common silence hallucinations.

### Memory Saver

Memory Saver is enabled by default and provides:

- one CTranslate2 model worker
- limited CPU inference threads
- small bounded audio, phrase, event, recorder, and monitor queues
- lighter live beam search and token limits
- model reuse between consecutive sessions
- a manual Release Model from RAM button
- automatic model release after idle
- original WAV recording and full verification retained

## v0.8.5 Windows source first-start repair

The complete source archive does not include `.venv` or a prebuilt
`LiveScribe.exe`. A Python virtual environment is machine-specific, and the EXE
belongs to a separately built portable release.

The Windows launcher now handles a new source folder automatically:

1. It first checks for the packaged portable executable.
2. It then checks for an existing `.venv`.
3. When only source files are present, it runs
   `scripts/source_setup_windows.ps1`.
4. The setup locates Python 3.11, creates `.venv`, installs
   `requirements-dev.txt`, and runs `app.py --self-test`.
5. After successful setup, the launcher starts the app.
6. Future launches reuse `.venv` and skip setup.

The first source start requires an internet connection. A root-level
`Start Live Scribe.bat` and a manual
`launchers/setup_source_windows.bat` are included.

## v0.8.4 responsive input controls

### Stop Test no longer blocks the window

Audio-device shutdown now runs on a background cleanup worker. The meter and
button reset immediately, late driver callbacks are ignored, and Start
Listening waits for cleanup before opening the same device for transcription.

The monitor also aborts active input/output streams before closing them. This
reduces delays caused by Windows audio drivers that take time to return from
`stop()` or a loopback `record()` call.

### Start Listening requirements are visible

The idle button remains clickable instead of being silently disabled:

- **Choose Speech Quality** — no speech model is selected
- **Download Model to Start** — selected model is not installed
- **Choose a Lighter Model** — hardware assessment clearly blocks the model
- **Start Listening** — model and hardware requirements are ready

Clicking an incomplete state explains the requirement and opens Models when
appropriate.

### Inactive devices are hidden

Microphones and playback devices that fail the local backend availability check
are no longer shown in customer-facing selectors. A clear placeholder is shown
only when no usable device exists.

### Output selector and full-control dropdowns

The microphone-monitor section includes an **Output device** dropdown. The
audio source, microphone, output, topic, model, language, processing device,
sensitivity, and topic-editor selectors now open when any part of the control is
clicked.

## v0.8.3 selected microphone listening

When **Microphone** is selected, the Input page now shows:

```text
Selected microphone monitoring
[Listen to this microphone]
[Playback through ▼]
```

The option is off by default. When enabled, Live Scribe copies the raw selected
microphone signal to the chosen playback device while keeping transcription and
WAV recording active. Playback uses a separate bounded queue and output worker,
so a slow playback device cannot block microphone capture.

Important behavior:

- Use headphones to prevent echo or loud acoustic feedback.
- The microphone sent to Faster-Whisper is unchanged.
- The original WAV is unchanged.
- The monitor can be toggled while transcription is running.
- The playback output can be changed while transcription is running.
- When idle, enabling the switch automatically starts the no-recording input
  test so the user can hear the selected microphone immediately.
- Disabling an automatically started monitor closes that preview without
  stopping or changing a later transcription session.
- Unavailable playback devices remain visible but disabled.

## v0.8.2 dropdown startup hotfix

The v0.8.1 full-surface dropdown overrode `configure()` and then called
`_sync_text()`. `_sync_text()` called the same override again, causing an
unbounded recursion during CustomTkinter button initialization.

The corrected widget:

- disables display synchronization until the base CTkButton is fully built
- calls `ctk.CTkButton.configure()` directly for internal text updates
- preserves disabled values and full-surface click behavior
- keeps `readonly` as a logical dropdown state
- includes a regression test that reproduces CustomTkinter calling
  `self.configure(cursor="hand2")` from its constructor

## v0.8.1 input and transcript tools

### Selected Windows application audio

On supported Windows versions, Live Scribe can isolate one selected application
instead of transcribing every sound played by the computer. The application
list uses visible running Windows apps. The selected app can be changed and the
**Listen to this app** switch can be turned off or on without closing the
transcription session.

This feature uses Windows process-loopback capture and requires:

- Windows build 20348 or newer
- `engines/windows/LiveScribeApplicationLoopback.exe`

The native helper is not faked through ordinary microphone capture. The
repository includes an automated GitHub Actions workflow that builds Microsoft's
official ApplicationLoopback sample, enables read sharing for Live Scribe's
rolling reader, and commits the helper into the repository.

Until the helper exists, the selected-app option is displayed disabled. Whole
computer audio and microphone capture continue to work.

### Summarize & Format

The new button creates an offline extractive summary, key points, decisions,
action items, and a readable speaker-formatted transcript. It does not overwrite
the raw transcript and requires no additional LLM.

### Fully clickable audio dropdowns

The modern microphone and audio-source selectors now open when any part of the
control is clicked, not only the arrow.

### Unavailable microphones

Microphones are checked with the audio backend before selection. Devices that
cannot currently be opened remain visible but are disabled and labeled
Unavailable.

### Live input check

**Test Input** opens only the selected audio input and displays a live sound
level. It does not load a speech model, start transcription, or save a WAV.
The same meter continues to show signal level during an active transcription.

## Interview Mode

Live Scribe now includes a separate Interview Mode foundation.

### Interview Preparation Template

The user can prepare:

- applicant name
- target job and company
- interview type
- preferred answer style and length
- resume and job description
- experience, skills, projects, and achievements
- strengths and weaknesses
- salary preference and availability
- company notes

**Generate Interview Template and Question Bank** creates a broad local bank of
likely interview questions. Each item includes a category, alternative
phrasings, keywords, answer points, and a truthful prepared-answer framework.

The built-in bank covers introductions, resume questions, motivation,
strengths, weaknesses, behavioral STAR questions, teamwork, conflict,
leadership, failures, achievements, problem solving, communication, priorities,
adaptability, ethics, remote work, salary, availability, closing questions, and
role-specific questions.

### Fast prepared-question matching

While Interview Assist is active, completed interviewer phrases are matched
locally against the prepared bank. Matching uses normalized wording, token
overlap, fuzzy similarity, alternative phrasings, and keywords.

- High-confidence prepared matches display immediately.
- Possible matches display with their confidence.
- Unmatched questions can be sent to an optional local AI.
- Prepared Answers Only works without a local LLM.

### Optional local AI answers

Interview Mode includes an OpenAI-compatible local client intended for a local
llama.cpp server. The default endpoint is:

```text
http://127.0.0.1:8080/v1/chat/completions
```

The local model is not bundled into the base app. The prompt requires concise,
truthful answers and prohibits invented work history, qualifications,
certifications, dates, tools, or achievements.

### Transcript separation

Spoken interviewer/interviewee text appears in the Interview Transcript.
Prepared and locally generated suggestions appear only in the Private Interview
Assistant panel. Suggestions are not silently inserted into the official
transcript.

### Audio-source boundary in v0.8.0

This release labels one incoming transcription stream at a time. The user
selects **Interviewer** or **Interviewee** for the next incoming phrase. This
works for a shared microphone, a mixed audio device, or manually switching
roles.

True simultaneous computer-audio-plus-microphone capture is not claimed as
complete in this release. It requires a later dual-capture controller and
platform-specific testing.

## Optional noise reduction

Live Scribe provides two separate, model-free options.

### Light live noise reduction

Enable **Settings → Session settings → Light live noise reduction for transcription (optional)**. It is off by default. It conservatively processes each completed phrase before Faster-Whisper receives it.

- The original WAV remains unchanged.
- No additional AI model, LLM, or dependency is downloaded.
- It targets steady fan, air-conditioner, hum, and room hiss.
- It cannot reliably remove conversations, music, barking, keyboard impacts, or rapidly changing noise.
- Turn it off when quiet or distant speech becomes less clear.

### WAV-verification noise reduction

The existing option is labeled **Reduce steady background noise during WAV verification**. It creates an enhanced copy for the separate accuracy pass while preserving the original WAV.

Neither option is marketed as perfect or complete noise cancellation.

## Productivity features

### Pause and resume

Pause temporarily stops:

- WAV recording
- transcript timestamps
- live transcription

Resume continues the same session without adding the paused time as silence.

### Audio health meter

The Live Session screen reports:

- good signal
- very quiet audio
- no audio detected
- clipping or excessive input level
- paused state

This helps catch a muted microphone, wrong meeting output, or silent system-audio
source before an important session is lost.

### Floating captions

Click **Floating Captions** or press `F11` to open a movable, always-on-top
caption window. Font size can be increased or decreased without changing the
main transcript.

### Transcript editor

The editor supports:

- editing recognized text
- assigning or removing speaker names
- marking a line as checked
- playing eight seconds from a selected timestamp
- Important, Action Item, and Question markers
- keyboard speaker labels with `Ctrl+1`, `Ctrl+2`, and `Ctrl+3`

Playback works from Live Scribe WAV recordings and supported imported
video/audio sources.

### Session library

The local SQLite session library stores reusable transcript records and supports
search across:

- session titles
- transcript text
- speakers
- topic profiles
- language
- markers and notes

Opening a saved session does not require internet access. Removing a library
record does not delete the original media or exported files.

### Automatic recovery

During a live session, Live Scribe saves a throttled local recovery snapshot.
After an interruption, it can restore:

- the session title and settings context
- live transcript entries
- speaker labels and markers
- available recording parts

Recovery writes are limited to reduce unnecessary flash-drive activity.

### Recording folders and long-session protection

Live Scribe creates two clear folders:

```text
recordings/
├── In Progress/
└── Final Output/
```

During recording, five-minute WAV safety parts are saved under
**Recordings/In Progress**. When the user clicks **Stop & Save WAV**, Live Scribe
merges those parts into one complete WAV under **Recordings/Final Output**.

The in-progress parts remain available as an optional safety copy. Keeping both
the individual parts and the merged WAV uses additional storage and can roughly
double the audio space used by that session. After confirming that the merged
WAV plays correctly and recovery is no longer needed, use **Models → Storage
Manager → Delete Completed Parts**.

**Delete All In-Progress** is also available, but it can permanently remove the
only recoverable audio for an unfinished session. Final Output WAV files are not
deleted by either cleanup operation.

### Storage manager

The Models page includes **Storage Manager** for:

- viewing space used by each speech model
- removing an unused model
- cleaning stopped model downloads
- cleaning temporary files
- viewing In Progress and Final Output audio separately
- deleting completed in-progress parts after checking the merged WAV
- deleting all in-progress parts with a strong recovery warning

Final Output WAV files are never deleted automatically.

## Topic Profiles

Topic Profiles improve recognition by passing compact subject context and likely
terms to the existing speech model. They do not use another LLM.

Included profiles:

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

Users can add, edit, and remove profiles locally.

## Vocabulary Manager

Vocabulary Manager can add, edit, and remove:

- personal names
- organizations
- schools, churches, cities, and barangays
- acronyms
- product names
- technical terms
- pronunciation aliases

The original recording remains the final reference for important details.


Everything entered in Vocabulary Manager remains in the local portable app
folder on the PC or USB drive. Live Scribe does not upload vocabulary,
pronunciation entries, topic profiles, saved sessions, recordings, or exports.
After the selected speech model has been downloaded, transcription can operate
offline.


## Export formats

- DOCX formatted report
- TXT
- SRT subtitles
- WebVTT captions
- CSV with timestamps, speaker labels, checked state, and markers
- Markdown
- Copy transcript to clipboard

## Portable flash-drive operation

The packaged buyer release is a PyInstaller **one-folder** application. Keep the
whole folder together; do not copy only the executable.

Writable files remain beside the app:

```text
models/
data/
recordings/
exports/
dictionary/
Skills/
Knowledge/
.cache/
```

Use a fast USB 3.x flash drive or portable SSD for better startup and model-load
performance. Windows-only users should prefer NTFS or exFAT over FAT32 because
FAT32 limits a single file to 4 GB.

Never remove the drive while Live Scribe is:

- recording
- downloading or resuming a model
- transcribing a recorded file
- verifying audio
- exporting
- saving profile or vocabulary changes

Close the app normally, then safely eject the drive.

## Buyer launchers

### Windows

Double-click:

```text
Start Live Scribe.bat
```

### Linux

```bash
chmod +x start_linux.sh LiveScribe/LiveScribe
./start_linux.sh
```

### macOS

Double-click:

```text
Start Live Scribe.command
```

macOS system-audio transcription requires a configured virtual input such as
BlackHole. Each operating system needs its own matching portable build.

## Development setup

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\dev_setup_windows.ps1"
.\launchers\start_windows.bat
```

### Linux or macOS

```bash
chmod +x scripts/dev_setup_unix.sh
./scripts/dev_setup_unix.sh
./launchers/start_linux.sh
```

Use `start_macos.sh` on macOS.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Current source test result:

```text
129 passed
```

A real release still requires physical testing of:

- microphones
- Windows WASAPI loopback
- Linux PulseAudio/PipeWire monitor audio
- macOS virtual audio routing
- NVIDIA GPU execution
- long flash-drive recording
- MP4, MKV, MP3, WAV, and other codecs on each target operating system

## Accuracy notice

AI transcription can make mistakes, especially with names, numbers, dates,
amounts, quotations, accents, uncommon terms, overlapping speakers, and noisy
audio. Always verify important information against the original WAV, video, or
audio source.
