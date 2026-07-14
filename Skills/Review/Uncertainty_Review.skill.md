# Uncertainty and Audio Verification Skill

## Purpose
Use model confidence and disagreement between transcription passes to identify portions that need human checking.

## Rules
- Compare the quick live pass with the full-WAV final pass.
- Flag material differences instead of automatically choosing a disputed name or number.
- Ask the user to replay the saved WAV at the relevant timestamp.
- Never state that an automatically generated transcript is guaranteed to be perfect.
