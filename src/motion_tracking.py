
import time
from collections import deque


class MotionTracker:
    def __init__(
        self,
        horizontal_threshold=0.18,
        vertical_threshold=0.15,
        window=0.6,
        cooldown=1.5,
        direction_ratio=1.5
    ):
        self.horizontal_threshold = horizontal_threshold
        self.vertical_threshold = vertical_threshold
        self.window = window
        self.cooldown = cooldown
        self.direction_ratio = direction_ratio

        self.history = deque()
        self.state = "READY"
        self.cooldown_until = 0.0
        self.last_seen = None

    def clear_history(self):
        self.history.clear()
        self.last_seen = None

    def reset(self):
        self.clear_history()
        self.state = "READY"
        self.cooldown_until = 0.0

    def mark_missing(self):
        self.clear_history()

    def lock(self):
        self.clear_history()
        self.state = "COOLDOWN"
        self.cooldown_until = time.monotonic() + self.cooldown

    def update(self, landmarks, allow_motion=True):
        now = time.monotonic()

        # 쿨다운이 끝나면 자동으로 재인식
        if self.state == "COOLDOWN":
            if now < self.cooldown_until:
                self.clear_history()
                return None

            self.state = "READY"
            self.clear_history()

        if landmarks is None or not allow_motion:
            self.clear_history()
            return None

        # 손바닥 중심에 가까운 세 점으로 이동 추적
        indices = (0, 5, 17)

        x = sum(landmarks[i].x for i in indices) / 3
        y = sum(landmarks[i].y for i in indices) / 3

        if (
            self.last_seen is not None
            and now - self.last_seen > 0.2
        ):
            self.clear_history()

        self.last_seen = now
        self.history.append((now, x, y))

        while (
            self.history
            and now - self.history[0][0] > self.window
        ):
            self.history.popleft()

        if len(self.history) < 3:
            return None

        _, start_x, start_y = self.history[0]

        dx = x - start_x
        dy = y - start_y

        horizontal = (
            abs(dx) >= self.horizontal_threshold
            and abs(dx) > abs(dy) * self.direction_ratio
        )

        vertical = (
            abs(dy) >= self.vertical_threshold
            and abs(dy) > abs(dx) * self.direction_ratio
        )

        if horizontal:
            self.clear_history()

            if dx > 0:
                return "SEEK_FORWARD"

            return "SEEK_BACKWARD"

        if vertical:
            self.clear_history()

            # 영상 좌표는 위로 갈수록 y가 작아짐
            if dy < 0:
                return "VOLUME_UP"

            return "VOLUME_DOWN"

        return None
