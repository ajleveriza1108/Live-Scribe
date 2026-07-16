# Live Scribe v0.7.5

## Optional live noise reduction

- Added a light live noise-reduction switch, off by default.
- Only transcription audio is processed; the original WAV remains unchanged.
- Targets steady fan, air-conditioner, hum, and room hiss.
- Uses the existing NumPy dependency and no additional AI model.
- Processing failure falls back to original audio.
- The post-session option is clearly labeled as WAV-verification noise reduction.
