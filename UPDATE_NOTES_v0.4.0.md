# Live Scribe v0.4.0

## Livestream and computer-audio transcription

This release adds a second live input mode:

- Microphone
- Computer audio / livestream

When Computer audio / livestream is selected, Live Scribe captures the audio
being played through the selected computer output, creates a live
phrase-by-phrase transcript, and saves the complete captured audio as WAV.

After stopping, Verify from WAV performs the separate full-recording accuracy
pass exactly as it does for microphone sessions.

### Platform support

- Windows: direct WASAPI output loopback
- Linux: PulseAudio/PipeWire monitor sources
- macOS: routed virtual input such as BlackHole is required

The app captures playback audio; it does not need a livestream URL and does not
download or redistribute the video.
