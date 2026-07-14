# Engine Packs

The base Etsy package contains one transcription runtime, not several large AI stacks. This keeps the portable download smaller and reduces installation problems.

## Active core engines
- Faster-Whisper: live transcription and full-WAV final transcription.
- Built-in NumPy noise reducer: optional conservative removal of steady background noise.
- Rule-based grammar/diction review: comments only, with no second language-model download.

## Optional researched packs
The registry lists DeepFilterNet, Qwen3-ASR, and whisper.cpp as possible future packs. They are intentionally not bundled in v0.3.2. An optional pack should be downloaded only when the buyer chooses it and should live in this folder without replacing the core app.
