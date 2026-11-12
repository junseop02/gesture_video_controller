
import math
import time


def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


def angle(a, b, c):
    ab = (
        a.x - b.x,
        a.y - b.y,
        a.z - b.z
    )

    cb = (
        c.x - b.x,
        c.y - b.y,
        c.z - b.z
    )

    dot = sum(
        x * y for x, y in zip(ab, cb)
    )

    na = math.sqrt(
        sum(x * x for x in ab)
    )

    nc = math.sqrt(
        sum(x * x for x in cb)
    )

    if na * nc < 1e-8:
        return 0.0

    cosine = max(
        -1.0,
        min(1.0, dot / (na * nc))
    )

    return math.degrees(
        math.acos(cosine)
    )


def finger_extended(lm, mcp, pip, tip):
    return angle(
        lm[mcp], lm[pip], lm[tip]
    ) > 155


def finger_folded(lm, mcp, pip, tip):
    return angle(
        lm[mcp], lm[pip], lm[tip]
    ) < 125


def is_v_sign(lm):
    index_open = finger_extended(
        lm, 5, 6, 8
    )

    middle_open = finger_extended(
        lm, 9, 10, 12
    )

    ring_folded = finger_folded(
        lm, 13, 14, 16
    )

    pinky_folded = finger_folded(
        lm, 17, 18, 20
    )

    spread = angle(
        lm[8], lm[5], lm[12]
    ) > 15

    return (
        index_open
        and middle_open
        and ring_folded
        and pinky_folded
        and spread
    )


def is_ok(lm):
    palm = max(
        distance(lm[0], lm[9]),
        1e-6
    )

    touching = (
        distance(lm[4], lm[8]) / palm
    ) < 0.35

    others_open = all([
        finger_extended(lm, 9, 10, 12),
        finger_extended(lm, 13, 14, 16),
        finger_extended(lm, 17, 18, 20)
    ])

    return touching and others_open


def is_fist(lm):
    return all([
        finger_folded(lm, 5, 6, 8),
        finger_folded(lm, 9, 10, 12),
        finger_folded(lm, 13, 14, 16),
        finger_folded(lm, 17, 18, 20)
    ])


def is_relaxed_open(lm):
    fingers = [
        (5, 6, 8),
        (9, 10, 12),
        (13, 14, 16),
        (17, 18, 20)
    ]

    open_count = sum(
        angle(lm[a], lm[b], lm[c]) >= 135
        for a, b, c in fingers
    )

    return open_count >= 3


def recognize_gesture(lm, handedness=None):
    if is_v_sign(lm):
        return "V_SIGN"

    if is_ok(lm):
        return "PLAY_PAUSE"

    return "UNKNOWN"


PRIORITY = {
    "V_SIGN": 1,
    "PLAY_PAUSE": 2,
    "SEEK_FORWARD": 3,
    "SEEK_BACKWARD": 3,
    "VOLUME_UP": 3,
    "VOLUME_DOWN": 3
}


def select_gesture(candidates):
    valid = [
        gesture
        for gesture in candidates
        if gesture in PRIORITY
    ]

    if not valid:
        return "UNKNOWN"

    best_priority = min(
        PRIORITY[g] for g in valid
    )

    selected = {
        g for g in valid
        if PRIORITY[g] == best_priority
    }

    if len(selected) != 1:
        return "UNKNOWN"

    return selected.pop()


class GestureController:
    def __init__(
        self,
        hold_time=1.0,
        cooldown=0.8,
        stable_time=0.15
    ):
        self.hold_time = hold_time
        self.cooldown = cooldown
        self.stable_time = stable_time

        self.enabled = False

        self.current_gesture = "UNKNOWN"
        self.gesture_start = time.monotonic()

        self.v_latched = False
        self.command_latched = False
        self.last_command_time = -float("inf")

    def reset_tracking(self):
        self.current_gesture = "UNKNOWN"
        self.gesture_start = time.monotonic()

        self.v_latched = False
        self.command_latched = False

    def update(self, gesture):
        now = time.monotonic()

        if gesture != self.current_gesture:
            self.current_gesture = gesture
            self.gesture_start = now
            self.command_latched = False

            if gesture != "V_SIGN":
                self.v_latched = False

        elapsed = now - self.gesture_start

        if gesture == "V_SIGN":
            if (
                elapsed >= self.hold_time
                and not self.v_latched
            ):
                self.enabled = not self.enabled
                self.v_latched = True
                self.last_command_time = now

                if self.enabled:
                    return "CONTROL_ON"

                return "CONTROL_OFF"

            return None

        if not self.enabled:
            return None

        if gesture == "UNKNOWN":
            return None

        if self.command_latched:
            return None

        motion_commands = (
            "SEEK_FORWARD",
            "SEEK_BACKWARD",
            "VOLUME_UP",
            "VOLUME_DOWN"
        )

        is_motion = gesture in motion_commands

        # 이동 명령은 한 프레임만 감지되어도 처리
        if (
            not is_motion
            and elapsed < self.stable_time
        ):
            return None

        if (
            now - self.last_command_time
            < self.cooldown
        ):
            return None

        self.command_latched = True
        self.last_command_time = now

        return gesture
