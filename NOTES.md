# Notes

## Bug Findings and Fixes

### Bug 1: Dead zone never activates

The problem description states: *"the crop window only moves when the face exits an inner region (the dead zone). This prevents the crop from chasing every small face movement and produces inherently stable output."*

After running `python visualize.py sample_data/clip_a.mp4 sample_data/clip_a.json` and watching `output.mp4`, the video continuously jitters, indicating a flaw in the dead zone logic.

The bug lies on lines 149–150 in `tracker.py`:
```python
need_move_x = abs(dx) > 0
need_move_y = abs(dy) > 0
```

`dx` and `dy` are the distances between the face center and the crop center. The condition should check whether the face has moved *outside* the dead zone, but `> 0` is true for any non-zero movement, which is effectively always the case with floating-point face coordinates. The dead zone region becomes zero pixels wide and the crop chases every frame.

**Fix:** Compare against the actual dead zone half-dimensions instead:
```python
need_move_x = abs(dx) > dz_half_w
need_move_y = abs(dy) > dz_half_h
```

After fixing and re-watching the output, the camera is now much smoother and no longer jitters continuously.

---

### Bug 2: Scene cuts and speaker switches don't snap

The problem description states: *"Scene cuts and speaker switches trigger an instant snap rather than a smooth pan."*

After running `python visualize.py sample_data/clip_b.mp4 sample_data/clip_b.json -o output_b.mp4` and watching the output, speaker switches produce a slow pan instead of an instant jump.

The following code is incomplete:
```python
if should_snap:
    scene_cut_frames.append(frame_idx)
```

When a speaker switch or scene boundary is detected, `should_snap` is set to `True` and the frame is recorded in `scene_cut_frames`. However, the code then falls through into the normal dead zone and smoothing logic. There is no early exit to actually perform the snap.

**Fix:** After recording the snap, immediately set `crop_cx, crop_cy` to the new face position and `continue` to skip smoothing entirely:
```python
face_x, face_y = face

if should_snap:
    scene_cut_frames.append(frame_idx)
    crop_cx, crop_cy = clamp_crop(face_x, face_y)
    per_frame.append((crop_cx, crop_cy))
    continue
```

After fixing and re-watching the output, the camera now instantly snaps when a scene cut or speaker switch occurs.

---

## Design Decisions

### Debouncer implementation

For each short run (length < `min_hold_frames`), the replacement ID is taken from the nearest preceding stable run. If no preceding stable run exists (e.g. a flicker at the very start of the clip), it falls back to the nearest following stable run. `None` segments are never modified — they represent frames with no detected speaker and should pass through as-is.

---

## Other Observations

The dead zone boundary can cause mild oscillation when a face hovers right at the edge. Some frames the face is just inside (crop holds), the next it's just outside (crop moves), producing a subtle stutter. A hysteresis approach — using a larger threshold to start moving and a smaller one to stop — would eliminate this without widening the dead zone overall.