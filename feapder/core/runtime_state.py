# -*- coding: utf-8 -*-
"""
Small runtime state helper for background runtime threads.
"""
from contextlib import contextmanager
from threading import RLock


class RuntimeState:
    def __init__(self):
        self._stop_requested = False
        self._busy_count = 0
        self._lock = RLock()

    def request_stop(self):
        with self._lock:
            self._stop_requested = True

    @property
    def is_stop_requested(self):
        with self._lock:
            return self._stop_requested

    def mark_busy(self):
        with self._lock:
            self._busy_count += 1

    def mark_idle(self):
        with self._lock:
            if self._busy_count > 0:
                self._busy_count -= 1

    @property
    def busy_count(self):
        with self._lock:
            return self._busy_count

    @property
    def is_idle(self):
        return self.busy_count == 0

    @contextmanager
    def busy(self):
        self.mark_busy()
        try:
            yield
        finally:
            self.mark_idle()
