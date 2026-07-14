# Portable Dictionary and Pronunciation Guide

The app uses three small local vocabulary files. They consume almost no storage and do not require another AI model.

## `custom_terms.txt`

Add one correctly spelled name or phrase per line. These terms are sent to the speech engine as recognition hints.

Good entries include:

- Personal names
- Churches and ministries
- Schools and businesses
- Barangays, cities, and Philippine places
- Acronyms
- Product names
- Medical, legal, or technical terms

## `pronunciation_guide.json`

Use this when a word is difficult to dictate, is commonly misspelled by speech recognition, or sounds different from its written form.

The key is the correct written form. The list contains ways the word may sound or common mistaken transcriptions.

```json
{
  "Cantos": ["kan tos", "cant toes"],
  "Quesada": ["ke sa da", "quesada"],
  "Project Lakbay": ["project lock buy", "project lak bai"]
}
```

The app uses both the correct spelling and the pronunciation forms as recognition hints. During the final WAV review, an exact matched alias may be corrected to the written form and recorded as a review comment.

Use distinctive phrases. Avoid very short aliases such as `a`, `to`, or `in`, because they may occur naturally in unrelated speech.

## `replacements.json`

Use only for explicit corrections that are always safe in your own work. Every applied correction appears in the review comments.

Changes are loaded when a new listening session begins.
