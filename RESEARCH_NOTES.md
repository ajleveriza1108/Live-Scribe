# Research and Architecture Decisions — v0.5.0

## Selected core
Faster-Whisper remains the default because it already supports multilingual Whisper models, voice activity detection, word timestamps, hotword hints, CPU quantization, and NVIDIA GPU execution.

## Why the app records WAV
The live pass is optimized for responsiveness. The saved original WAV allows a slower complete-recording pass after Stop and gives the user evidence for checking disputed names, numbers, and phrases.

## Noise reduction
The base package includes a lightweight stationary-noise reducer using NumPy. It targets steady fan, air-conditioner, and room noise. It preserves the original WAV. A neural enhancer such as DeepFilterNet is better treated as an optional pack because it adds binaries and model assets.

## Vocabulary and skills
Small Markdown skill and knowledge files take little disk space. Selected `ASR hotwords` sections plus the custom dictionary become bounded Whisper hints. This helps domain vocabulary without loading another large text model.

## Optional future engines
- Qwen3-ASR: promising multilingual final-pass option with Filipino support, but its model/runtime footprint is unsuitable for every buyer by default.
- whisper.cpp: useful candidate for a future quantized compact edition.
- Local text reviewer: optional GGUF language model for deeper grammar explanations. The core product uses deterministic comments so no second model is required.

## Product honesty
No local ASR system can guarantee perfect transcription. Noise reduction cannot recover words that the microphone failed to capture. The app therefore preserves the original audio and flags uncertainty rather than inventing certainty.

## Livestream audio capture

The system-audio input uses SoundCard, which supports Windows/WASAPI,
Linux/PulseAudio, and macOS/CoreAudio. Windows and Linux can expose output
loopback or monitor sources. macOS requires a separately installed virtual
audio routing device such as BlackHole because CoreAudio does not provide a
native speaker-loopback source.
