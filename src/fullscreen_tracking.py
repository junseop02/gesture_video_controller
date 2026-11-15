"""Two-hand fullscreen detection; update returns (command, motion_active)."""

import time
from collections import deque


class FullscreenTracker:
    def __init__(
        self, min_change=0.14, window=2.0, cooldown=1.2,
        min_hand_motion=0.025, missing_grace=0.25, confirm_frames=2,
        start_change=0.04, start_hand_motion=0.01, motion_timeout=0.35,
    ):
        if not (0 < start_change <= min_change and
                0 < start_hand_motion <= min_hand_motion):
            raise ValueError("Start thresholds must be positive and <= detection thresholds")
        if min(window, cooldown, missing_grace, motion_timeout) <= 0:
            raise ValueError("Time limits must be positive")
        if not isinstance(confirm_frames, int) or confirm_frames < 1:
            raise ValueError("confirm_frames must be a positive integer")
        self.min_change = min_change
        self.window = window
        self.cooldown = cooldown
        self.min_hand_motion = min_hand_motion
        self.missing_grace = missing_grace
        self.confirm_frames = confirm_frames
        self.start_change = start_change
        self.start_hand_motion = start_hand_motion
        self.motion_timeout = motion_timeout
        self.fullscreen = False
        self.last_command_time = -float("inf")
        self.history = deque()
        self.last_seen_time = None
        self.confirm_count = 0
        self.state = "WAIT_HANDS"
        self.distance = 0.0
        self.delta = 0.0
        self.motion_active = False
        self._last_progress_time = None
        self._peak_progress = 0.0

    def center(self, hand):
        indices = (0, 5, 9, 13, 17)
        return tuple(sum(getattr(hand[i], axis) for i in indices) / len(indices)
                     for axis in ("x", "y"))

    def reset_motion(self):
        """Clear a gesture without changing the remembered fullscreen state."""
        self.history.clear()
        self.confirm_count = 0
        self.delta = 0.0
        self.motion_active = False
        self._last_progress_time = None
        self._peak_progress = 0.0
        self.state = "READY"

    def update(self, left, right, enabled=True):
        now = time.monotonic()
        if not enabled:
            self.reset_motion()
            self.last_seen_time = None
            self.distance = 0.0
            self.state = "DISABLED"
            return None, False

        if left is None or right is None:
            # Missing frames cannot count as consecutive confirmation frames.
            self.confirm_count = 0
            self.distance = 0.0
            if (self.last_seen_time is not None and
                    now - self.last_seen_time <= self.missing_grace):
                if (self.motion_active and self._last_progress_time is not None
                        and now - self._last_progress_time > self.motion_timeout):
                    self.reset_motion()
                self.state = "HAND_MISSING"
                return None, self.motion_active
            self.reset_motion()
            self.last_seen_time = None
            self.state = "WAIT_HANDS"
            return None, False

        # A long gap also resets tracking if update was not called during it.
        if (self.last_seen_time is not None and
                now - self.last_seen_time > self.missing_grace):
            self.reset_motion()
        self.last_seen_time = now
        lx, _ = self.center(left)
        rx, _ = self.center(right)
        x1, x2 = sorted((lx, rx))
        self.distance = x2 - x1

        if now - self.last_command_time < self.cooldown:
            self.reset_motion()
            self.state = "COOLDOWN"
            return None, False

        sample = (now, x1, x2, self.distance)
        self.history.append(sample)
        while self.history and now - self.history[0][0] > self.window:
            self.history.popleft()
        if len(self.history) < 3:
            self.state = "READY"
            return None, False

        start = (max if self.fullscreen else min)(self.history, key=lambda p: p[3])
        start_time, start_x1, start_x2, start_distance = start
        self.delta = self.distance - start_distance
        direction = -1 if self.fullscreen else 1
        progress = direction * self.delta
        left_motion = -direction * (x1 - start_x1)
        right_motion = direction * (x2 - start_x2)
        started = (now > start_time and progress >= self.start_change
                   and left_motion >= self.start_hand_motion
                   and right_motion >= self.start_hand_motion)
        detected = (started and progress >= self.min_change
                    and left_motion >= self.min_hand_motion
                    and right_motion >= self.min_hand_motion)

        if started:
            if not self.motion_active or progress > self._peak_progress + 0.002:
                self._last_progress_time = now
                self._peak_progress = progress
            self.motion_active = True
        if self.motion_active and (
                not started or now - self._last_progress_time > self.motion_timeout):
            # Do not repeatedly reacquire a stalled gesture from an old extreme.
            self.reset_motion()
            self.history.append(sample)
            return None, False

        self.state = ("MOVING_CLOSE" if self.fullscreen else "MOVING_OPEN") \
            if self.motion_active else "READY"
        self.confirm_count = self.confirm_count + 1 if detected else 0
        if self.confirm_count >= self.confirm_frames:
            command = "FULLSCREEN_OFF" if self.fullscreen else "FULLSCREEN_ON"
            self.fullscreen = not self.fullscreen
            self.last_command_time = now
            self.reset_motion()
            self.state = command
            return command, True
        return None, self.motion_active
