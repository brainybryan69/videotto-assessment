"""
Speaker ID debouncing for stable camera tracking.

Removes rapid speaker-ID bounces that cause jarring crop window snaps.
"""


def debounce_speaker_ids(speaker_track_ids, min_hold_frames=15):
    """
    Remove rapid speaker-ID bounces shorter than min_hold_frames.

    Speaker detection sometimes flickers the active-speaker label during
    crosstalk or brief classification uncertainty, producing 1-10 frame
    segments that cause jarring rapid-fire crop snaps. This pre-filter
    replaces those short segments with the surrounding stable speaker ID
    so the downstream dead-zone tracker never sees them.

    Algorithm:
      1. Run-length encode the raw IDs into (track_id, start, length) runs.
      2. For any run shorter than min_hold_frames, replace it with the
         previous stable run's ID (or the next stable run if it's the first).
      3. Expand back to a per-frame list.

    Args:
        speaker_track_ids: Per-frame list of speaker IDs (int or None).
            None means no speaker detected at that frame.
        min_hold_frames: Minimum frames a speaker must hold to be "stable".

    Returns:
        Same-length list with short flicker runs replaced by nearest stable ID.
        None segments are never modified.

    Examples:
        >>> debounce_speaker_ids([0]*50 + [1]*3 + [0]*50, min_hold_frames=10)
        [0]*103  # The 3-frame speaker-1 segment is replaced by speaker 0

        >>> debounce_speaker_ids([None]*10 + [0]*50, min_hold_frames=15)
        [None]*10 + [0]*50  # None segments are untouched
    """
    if not speaker_track_ids:
        return []

    # Step 1: RLE encode into [track_id, start, length] runs
    runs = []
    i = 0
    while i < len(speaker_track_ids):
        current = speaker_track_ids[i]
        j = i
        while j < len(speaker_track_ids) and speaker_track_ids[j] == current:
            j += 1
        runs.append([current, i, j - i])
        i = j

    # Step 2: Replace short non-None runs with nearest stable neighbour
    for idx in range(len(runs)):
        track_id, _start, length = runs[idx]

        if track_id is None or length >= min_hold_frames:
            continue

        # Prefer previous stable non-None run
        replacement = None
        for prev in range(idx - 1, -1, -1):
            if runs[prev][0] is not None and runs[prev][2] >= min_hold_frames:
                replacement = runs[prev][0]
                break

        # Fall back to next stable non-None run
        if replacement is None:
            for nxt in range(idx + 1, len(runs)):
                if runs[nxt][0] is not None and runs[nxt][2] >= min_hold_frames:
                    replacement = runs[nxt][0]
                    break

        if replacement is not None:
            runs[idx][0] = replacement

    # Step 3: Expand back to per-frame list
    result = []
    for track_id, _start, length in runs:
        result.extend([track_id] * length)

    return result
