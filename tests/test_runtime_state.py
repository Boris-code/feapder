from feapder.core.runtime_state import RuntimeState


def test_runtime_state_starts_idle_and_running():
    state = RuntimeState()

    assert state.is_idle is True
    assert state.is_stop_requested is False
    assert state.busy_count == 0


def test_runtime_state_tracks_busy_count():
    state = RuntimeState()

    state.mark_busy()
    state.mark_busy()

    assert state.is_idle is False
    assert state.busy_count == 2

    state.mark_idle()
    state.mark_idle()

    assert state.is_idle is True
    assert state.busy_count == 0


def test_runtime_state_does_not_go_negative():
    state = RuntimeState()

    state.mark_idle()

    assert state.busy_count == 0
    assert state.is_idle is True


def test_runtime_state_busy_context_resets_on_exception():
    state = RuntimeState()

    try:
        with state.busy():
            assert state.is_idle is False
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert state.is_idle is True


def test_runtime_state_stop_request_is_sticky():
    state = RuntimeState()

    state.request_stop()
    state.request_stop()

    assert state.is_stop_requested is True
