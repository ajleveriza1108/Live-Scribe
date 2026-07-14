# Custom Dictionary Guide

The dictionary is a lightweight way to improve names and specialized vocabulary without installing a second language model.

## Files
- `dictionary/custom_terms.txt`: one name or phrase per line. These are sent as ASR hotword hints.
- `dictionary/replacements.json`: explicit final-pass replacements. Use sparingly.
- `dictionary/starter_terms.txt`: general starter vocabulary supplied with the app.

## Best candidates
People, churches, schools, barangays, companies, product names, acronyms, local places, technical terms, and frequently used foreign words.

## Safety
Hotwords are hints, not guarantees. Replacements are applied automatically, so only include pairs that are unambiguous in your own use case.
