"""Basic tests for the face tracking module."""

from src.tracker import track_face_crop


class TestTrackFaceCropBasics:
    """Basic sanity tests for track_face_crop."""

    def test_empty_input(self):
        """Empty bbox list returns empty output."""
        compressed, scene_cuts = track_face_crop([])
        assert compressed == []
        assert scene_cuts == []

    def test_single_frame_with_face(self):
        """One frame with a face returns one crop position."""
        # Face centered at (320, 180) in a 640x360 frame
        bboxes = [(300, 160, 340, 200)]
        compressed, scene_cuts = track_face_crop(bboxes, video_width=640, video_height=360)

        assert len(compressed) == 1
        assert compressed[0][2] == 1  # frame count
        assert compressed[0][0] > 0   # valid x coordinate
        assert compressed[0][1] > 0   # valid y coordinate
        assert scene_cuts == []

    def test_no_face_before_first_detection(self):
        """Frames with None bbox before first face return (-1, -1) sentinel."""
        bboxes = [None, None, None, (300, 160, 340, 200), (300, 160, 340, 200)]
        compressed, scene_cuts = track_face_crop(bboxes, video_width=640, video_height=360)

        # First segment should be the no-face sentinel
        assert compressed[0][0] == -1
        assert compressed[0][1] == -1
        assert compressed[0][2] == 3  # 3 no-face frames


class TestDeadZoneBugRegression:
    """
    Regression tests for Bug 1: dead zone never activated.

    Original code compared abs(dx) > 0 instead of abs(dx) > dz_half_w,
    causing the crop to chase every frame of face movement.
    """

    def test_face_within_dead_zone_holds_crop(self):
        """Crop must not move when face stays inside the dead zone.

        For 640x360 video: crop_w=202.5, dz_half_w=10.125, dz_half_h=18.0.
        A face that moves less than 10px in x and 18px in y from the initial
        position should never trigger crop movement.
        """
        # Initialize at (320, 180) then make small movements within dead zone
        init_bbox = (300, 160, 340, 200)      # center (320, 180)
        small_move = (305, 165, 345, 205)     # center (325, 185) — delta (5, 5), within dead zone
        bboxes = [init_bbox] + [small_move] * 30

        compressed, _ = track_face_crop(bboxes, video_width=640, video_height=360)

        # All 31 frames should compress to a single segment (crop never moved)
        assert len(compressed) == 1
        assert compressed[0][2] == 31

    def test_face_outside_dead_zone_moves_crop(self):
        """Crop must move when face exits the dead zone."""
        init_bbox = (300, 160, 340, 200)      # center (320, 180)
        large_move = (360, 160, 400, 200)     # center (380, 180) — delta 60px, outside dead zone
        bboxes = [init_bbox] + [large_move] * 10

        compressed, _ = track_face_crop(bboxes, video_width=640, video_height=360)

        # Crop should have moved — more than one segment
        assert len(compressed) > 1


class TestSnapBugRegression:
    """
    Regression tests for Bug 2: scene cuts and speaker switches didn't snap.

    Original code recorded the snap event but fell through to the smooth-pan
    logic, producing a gradual pan instead of an instant jump.
    """

    def test_speaker_switch_snaps_to_new_face_position(self):
        """Crop must jump instantly to the new speaker's face on a switch."""
        # Speaker 0 on the left (face center x=150), speaker 1 on the right (x=500)
        spk0_bbox = (130, 150, 170, 210)   # center (150, 180)
        spk1_bbox = (480, 150, 520, 210)   # center (500, 180)

        bboxes = [spk0_bbox] * 20 + [spk1_bbox] * 20
        speaker_ids = [0] * 20 + [1] * 20

        compressed, scene_cuts = track_face_crop(
            bboxes,
            video_width=640,
            video_height=360,
            speaker_track_ids=speaker_ids,
            min_speaker_hold_frames=0,
        )

        assert 20 in scene_cuts

        # Find the crop position at frame 20 (the snap frame)
        frame_offset = 0
        snap_cx = None
        for seg in compressed:
            if frame_offset == 20:
                snap_cx = seg[0]
                break
            frame_offset += seg[2]

        # Snap should land at the new face x (500), not mid-pan (~237 if smoothed)
        assert snap_cx is not None
        assert abs(snap_cx - 500) <= 3

    def test_scene_boundary_snaps_to_new_face_position(self):
        """Crop must jump instantly at a scene boundary."""
        spk_bbox_a = (130, 150, 170, 210)   # center (150, 180)
        spk_bbox_b = (480, 150, 520, 210)   # center (500, 180)

        bboxes = [spk_bbox_a] * 20 + [spk_bbox_b] * 20
        face_scenes = [(0, 19), (20, 39)]

        compressed, scene_cuts = track_face_crop(
            bboxes,
            video_width=640,
            video_height=360,
            face_scenes=face_scenes,
        )

        assert 20 in scene_cuts

        frame_offset = 0
        snap_cx = None
        for seg in compressed:
            if frame_offset == 20:
                snap_cx = seg[0]
                break
            frame_offset += seg[2]

        assert snap_cx is not None
        assert abs(snap_cx - 500) <= 3
