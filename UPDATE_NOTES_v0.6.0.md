# Live Scribe v0.6.0

## Topic Profiles

This release adds reusable local recording topics without adding an LLM.

### Included starter topics

- General Conversation
- Office & Business Meeting
- School, Class & Lecture
- Zoom, Google Meet & Online Meeting
- Interview & Research
- Church, Sermon & Bible Study
- Livestream, Webinar & Presentation
- Technology & Programming
- E-commerce & Online Selling
- News & Current Events

### Topic management

Users can add, edit, and remove profiles from the new Topics page. Each profile
stores a name, a short recording description, and important terms.

### Accuracy integration

The selected topic's terms are prioritized before general vocabulary in the
Faster-Whisper hotword limit. Its short description is added to the existing
language prompt. The same topic snapshot is used for live transcription and the
separate Verify from WAV pass.

Topic profiles remain local, portable, offline, and very small. They do not
download another AI model and do not guarantee perfect recognition.
