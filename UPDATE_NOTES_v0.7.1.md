# Live Scribe v0.7.1

## First-run PC report

- The automatic compatibility popup now appears only on the true first run.
- Updating the internal hardware-check rules no longer makes the automatic
  popup return.
- Check This PC Again remains available for a user-requested visible report.

## Recorded video and audio visibility

- Live Session now has a dedicated panel:
  "Already have a recorded video or audio file?"
- The primary action is named "Choose Video or Audio File".
- The action-bar shortcut is named "Transcribe Video / Audio".
- The selected source file remains unchanged.

## Vocabulary privacy notice

- Vocabulary Manager explains that entries are stored in the portable folder.
- Live Scribe does not upload vocabulary, topics, sessions, recordings, or
  exports.
- Transcription can run offline after the selected speech model is downloaded.

## Recording folder organization

- Five-minute source parts are stored in `recordings/In Progress`.
- The merged complete WAV is stored in `recordings/Final Output`.
- Safety parts are retained for optional recovery.
- Storage Manager shows both folders separately.
- Delete Completed Parts removes only part folders with a matching merged WAV.
- Delete All In-Progress includes a warning that unfinished recovery audio can
  be permanently lost.
- Keeping both source parts and the merged WAV uses additional storage and may
  roughly double the audio space used by a session.
