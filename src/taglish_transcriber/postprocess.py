from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import GRAMMAR_REVIEW_LANGUAGE_LABELS
from .dictionary_engine import DictionaryCorrection, VocabularyManager
from .models import TranscriptSegment, WhisperEngine, replace_segment_text
from .noise_reduction import reduce_stationary_noise
from .review_engine import (
    GrammarDictionReviewEngine,
    ReviewComment,
    compare_live_and_final,
)
from .skill_library import SkillLibrary


@dataclass(frozen=True, slots=True)
class PostSessionResult:
    segments: tuple[TranscriptSegment, ...]
    comments: tuple[ReviewComment, ...]
    recording_path: Path
    enhanced_recording_path: Path | None
    warnings: tuple[str, ...]
    dictionary_corrections: tuple[DictionaryCorrection, ...]


class PostSessionProcessor:
    def __init__(
        self,
        engine: WhisperEngine,
        *,
        language_code: str | None,
        language_label: str,
        noise_reduction: bool,
        grammar_diction_comments: bool,
        topic_context: str | None = None,
        topic_terms: list[str] | tuple[str, ...] = (),
    ) -> None:
        self.engine = engine
        self.language_code = language_code
        self.language_label = language_label
        self.use_noise_reduction = noise_reduction
        self.use_review = grammar_diction_comments
        self.topic_context = topic_context
        self.topic_terms = tuple(topic_terms)
        self.vocabulary = VocabularyManager()
        self.skills = SkillLibrary()
        self.reviewer = GrammarDictionReviewEngine()

    def process(
        self,
        recording_path: Path,
        *,
        live_entries: tuple[object, ...] | list[object] = (),
    ) -> PostSessionResult:
        warnings: list[str] = []
        enhanced_path: Path | None = None
        transcription_source = recording_path

        if self.use_noise_reduction:
            enhanced_path = recording_path.with_name(recording_path.stem + "_enhanced.wav")
            try:
                result = reduce_stationary_noise(recording_path, enhanced_path)
                transcription_source = result.output_path
                if not result.applied:
                    warnings.append(result.message)
            except Exception as exc:
                enhanced_path = None
                warnings.append(
                    "Noise reduction could not be applied, so the original WAV was used. "
                    f"Details: {str(exc).strip() or 'unknown audio processing error'}"
                )

        hotwords = self.vocabulary.hotwords(
            self.skills.asr_hotwords(),
            priority_terms=self.topic_terms,
        )
        segments = self.engine.transcribe_file(
            transcription_source,
            language_code=self.language_code,
            hotwords=hotwords,
            language_label=self.language_label,
            context_prompt=self.topic_context,
        )

        corrected_segments: list[TranscriptSegment] = []
        dictionary_corrections: list[DictionaryCorrection] = []
        dictionary_comments: list[ReviewComment] = []
        for segment in segments:
            corrected_text, corrections = self.vocabulary.apply_replacements(segment.text)
            corrected_segments.append(replace_segment_text(segment, corrected_text))
            dictionary_corrections.extend(corrections)
            for correction in corrections:
                dictionary_comments.append(
                    ReviewComment(
                        timestamp=segment.start,
                        category=correction.source,
                        original=correction.original,
                        suggestion=correction.corrected,
                        explanation=(
                            "Applied from the local vocabulary files during the final accuracy pass. "
                            "Confirm unusual proper names and important terms against the WAV."
                        ),
                        severity="Applied",
                    )
                )

        comments: list[ReviewComment] = []
        if self.use_review:
            if self.language_label in GRAMMAR_REVIEW_LANGUAGE_LABELS:
                comments.extend(self.reviewer.review(corrected_segments))
            comments.extend(dictionary_comments)
            comments.extend(compare_live_and_final(live_entries, corrected_segments))

        return PostSessionResult(
            segments=tuple(corrected_segments),
            comments=tuple(comments),
            recording_path=recording_path,
            enhanced_recording_path=enhanced_path,
            warnings=tuple(warnings),
            dictionary_corrections=tuple(dictionary_corrections),
        )
