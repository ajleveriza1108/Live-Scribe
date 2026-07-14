# Live Scribe v0.7.0

## Lightweight productivity release

This release adds general-purpose transcription tools without adding another
LLM or a second large AI model.

### Live session

- Pause and resume
- Audio input level meter
- No-audio and clipping notices
- Floating always-on-top caption window
- Session title used in recording filenames
- Five-minute crash-contained WAV safety parts

### Recorded media

- Direct transcription of recorded video and audio
- MP4, MKV, MOV, AVI, WebM, M4V, MPEG, MPG, 3GP, TS, MTS
- MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WMA, AIFF, ALAC, MKA
- Video images are ignored; the audio track is transcribed
- Timestamp playback from imported media through PyAV

### Transcript productivity

- Editable transcript text
- Manual speaker names
- Checked/verified line state
- Important, Action Item, and Question markers
- Timestamp audio playback
- VTT, CSV, and Markdown exports
- Copy transcript to clipboard

### Local session management

- Searchable SQLite session library
- Search by title, transcript, speaker, topic, language, and marker
- Rename, open, and remove session records
- Original media remains untouched when a library record is removed

### Recovery and portability

- Throttled local unfinished-session snapshots
- Recovery of transcript and valid WAV parts
- Portable paths stored relative to the app folder when possible
- Storage Manager for models, stopped downloads, temporary files, and usage
- No automatic deletion of recordings

### Size impact

The new functionality is primarily Python code and SQLite, which is included
with Python. PyAV was already required by Faster-Whisper and is now listed
explicitly. No new LLM weights, speaker-recognition model, translation model,
or neural noise-suppression model were added.
