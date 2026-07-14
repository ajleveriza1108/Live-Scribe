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

