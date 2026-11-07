import math
import time


def distance(p1, p2):
    """두 랜드마크 사이의 3차원 거리"""
    return math.sqrt(
        (p1.x - p2.x) ** 2
        + (p1.y - p2.y) ** 2
        + (p1.z - p2.z) ** 2
    )


def recognize_hand_shape(landmarks):
    """손 모양을 OPEN, FIST, UNKNOWN으로 분류"""

    palm_size = distance(landmarks[0], landmarks[9])

    if palm_size < 1e-6:
        return "UNKNOWN"

    fingers = [
        (5, 6, 8),
        (9, 10, 12),
        (13, 14, 16),
        (17, 18, 20),
    ]

    extended_count = 0
    folded_count = 0

    for mcp, pip, tip in fingers:
        tip_dist = distance(
            landmarks[tip], landmarks[mcp]
        )
        pip_dist = distance(
            landmarks[pip], landmarks[mcp]
        )

        ratio = tip_dist / max(pip_dist, 1e-6)

        if ratio > 1.6:
            extended_count += 1
        elif ratio < 1.3:
            folded_count += 1

    if extended_count == 4:
        return "OPEN"

    if folded_count >= 3:
        return "FIST"

    return "UNKNOWN"


class JamJamRecognizer:
    """OPEN -> FIST -> OPEN 제스처 인식"""

    def __init__(self, max_duration=1.5, cooldown=1.0):
        self.max_duration = max_duration
        self.cooldown = cooldown

        self.state = "WAIT_OPEN"
        self.start_time = 0.0
        self.last_trigger = -float("inf")
        self.previous_shape = "UNKNOWN"

    def reset(self):
        self.state = "WAIT_OPEN"
        self.previous_shape = "UNKNOWN"

    def update(self, hand_shape):
        now = time.monotonic()

        if now - self.last_trigger < self.cooldown:
            return None

        if self.state != "WAIT_OPEN":
            if now - self.start_time > self.max_duration:
                self.reset()

        if hand_shape == self.previous_shape:
            return None

        self.previous_shape = hand_shape

        if self.state == "WAIT_OPEN":
            if hand_shape == "OPEN":
                self.state = "WAIT_FIST"
                self.start_time = now

        elif self.state == "WAIT_FIST":
            if hand_shape == "FIST":
                self.state = "WAIT_FINAL_OPEN"

        elif self.state == "WAIT_FINAL_OPEN":
            if hand_shape == "OPEN":
                self.last_trigger = now
                self.reset()
                return "PLAY_PAUSE"

        return None