# Live Scribe v0.3.2 Update

## Model setup is now explicit

- Installing, extracting, or launching the portable app does not download a model.
- A first-time buyer sees `Select a model…` in the model list.
- `Start Listening` stays disabled until a model is downloaded.
- The buyer selects a model and clicks **Download Selected Model**.
- Only that selected model is downloaded.
- Downloaded models remain in the portable `models` folder and are reused offline.
- Starting a session never silently starts a model download.

## Permanent accuracy warning

The main window now states that AI-assisted transcription can make mistakes and instructs the user to review the final transcript and replay the WAV. The same warning is included in formatted DOCX reports and buyer documentation.

## Language scope

The current interface remains limited to English, Tagalog/Filipino, and Taglish. Additional languages are identified as a future expansion rather than being prematurely exposed as supported choices.

## Difficult words and pronunciation

- Added an in-app **Vocabulary & Pronunciation** editor.
- Added `dictionary/pronunciation_guide.json`.
- Buyers can enter the correct spelling and common spoken or mistaken forms.
- Correct spellings and aliases are used as ASR hotword hints.
- Exact alias matches can be corrected during the final WAV pass.
- Every applied pronunciation correction appears in Review Comments.

## Validation

- 13 automated tests pass.
- Python compilation passes.
- Model-state tests confirm that no model is selected on a clean first run.
- Pronunciation guide save, load, hotword, and correction behavior is tested.
- DOCX output is tested for the accuracy warning.
