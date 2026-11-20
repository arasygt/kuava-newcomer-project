"""US-5: lost tracking is reported and the user can select the target again."""
from app.lock import LOST, TRACKED, UNTRACKED
from tests.conftest import track, upload
from tests.videogen import vanishing_target_video


def test_lost_tracking_is_reported_and_reselection_resumes(client, video_dir):
    path, truth = vanishing_target_video(video_dir / "api_vanish.mp4")
    vid = upload(client, path).json()["id"]
    first = track(client, vid, 0, truth[0]).json()
    lost = first["run"]["lost_frame"]
    assert lost is not None and 30 <= lost <= 40
    assert first["run"]["lost_reason"] in {"tracker_failure", "area_change"}
    assert first["states"][lost] == [LOST]
    assert all(s == [UNTRACKED] for s in first["states"][lost + 1:])

    # User re-selects the target once it is visible again (frame 40)
    second = track(client, vid, 40, truth[40]).json()
    assert second["run"]["start_frame"] == 40 and second["run"]["lost_frame"] is None
    states = second["states"]
    assert states[:lost + 1] == first["states"][:lost + 1]   # earlier results kept
    assert all(s == [UNTRACKED] for s in states[lost + 1:40])
    assert all(s[0] == TRACKED for s in states[40:])


def test_reselecting_earlier_replaces_later_results(client, video_dir):
    path, truth = vanishing_target_video(video_dir / "api_vanish2.mp4")
    vid = upload(client, path).json()["id"]
    track(client, vid, 0, truth[0])                      # lost around frame 30
    res = track(client, vid, 20, truth[20]).json()       # re-select before the loss
    assert res["run"]["start_frame"] == 20
    assert all(s[0] == TRACKED for s in res["states"][:20])
    assert res["states"][res["run"]["lost_frame"]] == [LOST]


def test_no_loss_on_clean_video(client, uploaded, moving_video):
    body = track(client, uploaded["id"], 0, moving_video[1][0]).json()
    assert body["run"]["lost_frame"] is None and body["run"]["lost_reason"] is None
