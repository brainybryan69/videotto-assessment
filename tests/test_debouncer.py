"""Tests for the speaker ID debouncer."""

from src.debouncer import debounce_speaker_ids


class TestDebounceBasics:
    """Basic behaviour from the docstring spec."""

    def test_short_flicker_replaced_by_previous_stable(self):
        """A run shorter than min_hold_frames is replaced by the preceding stable ID."""
        ids = [0] * 50 + [1] * 3 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        assert result == [0] * 103

    def test_none_segments_are_never_modified(self):
        """None entries pass through untouched."""
        ids = [None] * 10 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=15)
        assert result == [None] * 10 + [0] * 50

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert debounce_speaker_ids([]) == []

    def test_output_length_matches_input(self):
        """Output must always be the same length as the input."""
        ids = [0] * 50 + [1] * 5 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        assert len(result) == len(ids)


class TestThresholdBoundary:
    """Runs exactly at and just below the threshold."""

    def test_run_exactly_at_threshold_is_kept(self):
        """A run of exactly min_hold_frames should not be replaced."""
        ids = [0] * 50 + [1] * 15 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=15)
        assert result == [0] * 50 + [1] * 15 + [0] * 50

    def test_run_one_below_threshold_is_replaced(self):
        """A run of min_hold_frames - 1 should be replaced."""
        ids = [0] * 50 + [1] * 14 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=15)
        assert result == [0] * 114


class TestFallbackBehaviour:
    """Fallback to next stable run when no previous stable run exists."""

    def test_short_run_at_start_uses_next_stable(self):
        """With no preceding stable run, the next stable run's ID is used."""
        ids = [1] * 3 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        assert result == [0] * 53

    def test_short_run_at_end_uses_previous_stable(self):
        """A short run at the end falls back to the preceding stable run."""
        ids = [0] * 50 + [1] * 3
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        assert result == [0] * 53


class TestMultipleShortRuns:
    """Multiple short runs in sequence."""

    def test_consecutive_short_runs_both_replaced(self):
        """Two back-to-back short runs are both replaced by the nearest stable ID."""
        ids = [0] * 50 + [1] * 3 + [2] * 3 + [0] * 50
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        assert result == [0] * 106

    def test_stable_run_between_short_runs_preserved(self):
        """A long run between two short runs is untouched."""
        ids = [0] * 3 + [1] * 50 + [0] * 3
        result = debounce_speaker_ids(ids, min_hold_frames=10)
        # Both short [0] runs replaced by [1]
        assert result == [1] * 56
