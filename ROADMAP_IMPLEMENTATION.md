# Live Scribe implementation roadmap

## v0.9.0 — Selected-app and low-RAM core — implemented

- Windows computer/livestream capture means selecting one window or
  application process tree.
- Ordinary whole-system Windows capture is removed from the normal
  selector.
- Smart Silero VAD is reused from Faster-Whisper.
- Audio, transcript, recorder, monitor, and event queues are bounded.
- Memory Saver uses one model worker, limited CPU threads, lighter live
  decoding, model reuse, manual release, and delayed idle release.
- ApplicationLoopback helper workflow now uploads an artifact and a
  local PowerShell builder is included.

## v0.10.0 — Built-in offline LLM — next

- Platform-specific llama.cpp runtime manager.
- Optional GGUF model download with stop/resume and checksum.
- 2K–4K working context and one request slot for low RAM.
- Interview model preload and token streaming.
- Generative summary, minutes, action items, and transcript Q&A.
- Prepared Answers Only remains available with no LLM.

## v0.11.0 — Speaker intelligence

- Optional sherpa-onnx package.
- Punctuation restoration.
- Speaker diarization and known-speaker enrollment.
- Overlap warnings.
- Optional local TTS.

## v0.12.0 — Audio enhancement

- Optional DeepFilterNet package.
- Enhanced preview and separate enhanced WAV export.
- Original WAV always preserved.
- Automatic gain and clipping guidance.

## v0.13.0 — macOS/Linux completion

- Automatic Unix first-start setup.
- BlackHole/PipeWire setup assistants.
- Signed Apple Silicon and Intel packages.
- Linux self-contained release.
- Platform audio test suite.

## v1.0 — commercial validation

- Long-duration and interruption tests.
- USB/external-drive stress testing.
- Signed packages and checksum manifests.
- Third-party license audit.
- Buyer recovery and migration tools.
