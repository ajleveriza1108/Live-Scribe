# Speech Recognition Accuracy Guide

## Two-pass policy
1. The live pass prioritizes responsiveness and creates rough phrase-level text.
2. The original microphone signal is simultaneously saved as WAV.
3. After Stop, the complete WAV receives a slower, higher-quality transcription pass.
4. The app compares live and final text and marks significant disagreements for replay.

## High-risk details
Always review proper names, usernames, addresses, dates, times, currency, quantities, model numbers, abbreviations, quotations, and unfamiliar technical terms.

## Noise policy
Steady background noise may be reduced conservatively before the final pass. The original WAV is never overwritten. Noise reduction cannot reconstruct speech that was never captured clearly.
