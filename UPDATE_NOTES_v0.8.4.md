# Live Scribe v0.8.4

## Input responsiveness and device selection

- Moved Test Input cleanup off the GUI thread.
- Added stale audio-meter callback protection.
- Start Listening waits for input cleanup before opening the device.
- Start Listening now explains missing model and hardware requirements.
- Hidden unavailable microphones and playback devices.
- Retained selected microphone listening and added an explicit Output device
  dropdown label.
- Converted all main modern dropdowns to full-control clicking.
- Added idempotent stream abort and close behavior.
