# Seller Release Guide — v0.7.0

## Repository

Repository: `ajleveriza1108/Live-Scribe`

## Before building

1. Review `LICENSE.txt` and all third-party license obligations.
2. Confirm no customer recordings, exports, settings, models, or custom dictionary data are committed.
3. Run `python -m pytest`.
4. Run `python -m compileall -q src app.py`.
5. Build each platform on its matching operating system or use GitHub Actions.
6. Test microphone permission, WAV creation, Stop/final-pass behavior, and DOCX export on real hardware.

## GitHub release workflow

The workflow builds:

- Windows x64
- Linux x64
- macOS Apple Silicon
- macOS Intel

Manual workflow runs create temporary artifacts. A version tag creates a GitHub Release.

```bash
git add .
git commit -m "Add live productivity and recorded-media transcription"
git push origin main
git tag v0.7.0
git push origin v0.7.0
```

## Buyer archive requirements

Each archive must contain:

- packaged executable/runtime folder
- correct platform launcher
- empty writable `models`, `recordings`, `exports`, and `data` folders
- `Skills`, `Knowledge`, `dictionary`, and `engines`
- `BUYER_GUIDE.txt`
- `LICENSE.txt`
- `THIRD_PARTY_NOTICES.md`

Do not include downloaded model weights in the normal base edition.

## Release validation

- Launch without system Python.
- Confirm no model download starts during installation or launch.
- Confirm Start Listening stays disabled until a selected model is downloaded.
- Run packaged `--self-test` during the build.
- Confirm the default microphone is detected.
- Record at least five minutes to WAV.
- Confirm the WAV remains playable after Stop.
- Test quiet room and steady fan noise.
- Confirm final pass uses the full recording.
- Confirm the review tab flags a deliberately different live/final sample.
- Confirm DOCX opens in Microsoft Word or LibreOffice.
- Move the complete package to another writable folder and launch again.

## Etsy delivery

Use a short Etsy download file containing buyer instructions and a private release link when the platform file-size limit is too small. Tell buyers to keep their original ZIP and a second backup. Do not promise perfect transcription or complete noise cancellation.

## v0.7.0 release checks

Before selling a build, test:

- Start, pause, resume, stop, and full WAV verification
- No-audio and clipping notices
- Floating captions
- Transcript edit, speaker label, marker, checked state, and timestamp playback
- Session library search and reopen
- Interruption recovery from a forced application close
- Five-minute recording rollover and final WAV combination
- Model removal and partial-download cleanup
- MP4, MKV, MP3, WAV, M4A, FLAC, and WebM transcription
- VTT, CSV, Markdown, DOCX, TXT, and SRT exports
- Flash-drive use on a different drive letter

Do not advertise every codec as guaranteed on every operating system. State that
support depends on the codec being readable by the included PyAV build.

## v0.7.1 buyer-release checks

- Confirm the automatic PC report appears once on a fresh data/settings.json and
  does not return on the next launch.
- Confirm Models > Check This PC Again still produces a visible requested report.
- Confirm the Live Session page clearly shows Choose Video or Audio File.
- Confirm Vocabulary Manager displays its offline/local-data notice.
- Confirm active recording parts appear in recordings/In Progress.
- Confirm Stop & Save WAV creates the merged file in recordings/Final Output.
- Confirm Delete Completed Parts preserves the Final Output WAV.
- Confirm Delete All In-Progress requires a strong warning.
- Explain that keeping both parts and the merged WAV increases buyer storage.

## v0.7.2 download-progress test

Before publishing:

- Start a fresh model download and confirm normal percentage movement.
- Stop after partial progress, reopen the app, and resume.
- Confirm resumed bytes do not produce an impossible TB/s speed.
- Confirm an incomplete download never displays a full 100% bar.
- Confirm the card changes to Finalizing with an animated bar.
- Confirm 100% appears only immediately before the verified ready state.

## v0.7.3 release checks

- Launch a fresh copy and confirm the PC report appears once.
- Close and relaunch; confirm it does not return.
- Confirm `data/.first-run-complete` exists.
- Confirm an older copy with `hardware_profile.json` but settings set to false
  does not replay the popup.
- Start a model download, press Stop Download, and confirm no traceback appears
  in the launcher.
- Relaunch and confirm the same model resumes from partial files.

## v0.7.4 recorded-file button check

- Start a fresh copy with no downloaded model.
- Confirm Choose Video or Audio File is clickable.
- Click it and confirm the message offers to open Models.
- Download/select a model and confirm the file chooser opens.
- Confirm both recorded-file buttons are disabled only during an active
  download, model load, live session, or transcription.

## v0.7.5 noise-reduction checks

- Confirm live reduction defaults off.
- Confirm the original WAV remains unchanged.
- Compare fan/hum audio with the switch on and off.
- Test quiet/distant speech and advise disabling it when clarity drops.
- Do not market it as perfect, neural, or complete noise cancellation.

## v0.8.0 Interview Mode checks

- Create a profile from a resume and job description.
- Confirm at least 30 questions are generated.
- Confirm alternative wording and keywords are saved.
- Test "What makes you the strongest candidate?" against "Why should we hire you?"
- Confirm prepared suggestions never enter the official transcript.
- Test Prepared Answers Only without a local LLM.
- Test the local endpoint using a llama.cpp-compatible server.
- Confirm the role selector labels incoming segments correctly.
- Do not advertise simultaneous microphone-plus-system capture until that
  platform-specific feature is implemented and tested.
- Position real-time assistance only for permitted or disclosed use.

## v0.8.1 validation

- Confirm the entire microphone dropdown opens the list.
- Confirm unavailable microphones are visible but cannot be selected.
- Test Test Input before downloading or loading a speech model.
- Confirm Test Input saves no recording.
- Run Summarize & Format on a speaker-labeled transcript.
- Confirm raw entries remain unchanged.
- On Windows build 20348+, run the helper workflow, pull the committed EXE, and
  test Chrome/Zoom/Teams process-tree capture.
- While selected-app transcription is active, play sound from another app and
  confirm it is excluded.
- Toggle Listen to this app off and on without stopping the session.

