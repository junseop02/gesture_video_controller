import math
import time


GUN_TOLERANCE = 35
VOLUME_UP_TOLERANCE = 30
VOLUME_DOWN_TOLERANCE = 35

PALM_SIGN = 1
PALM_MIN_FACING = 0.25

# 진단 단계에서는 손바닥 방향을 SEEK 필수 조건에서 제외
REQUIRE_PALM_FOR_GUN = False


def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


def angle(a, b, c):
    ab = (a.x - b.x, a.y - b.y, a.z - b.z)
    cb = (c.x - b.x, c.y - b.y, c.z - b.z)

    dot = sum(x * y for x, y in zip(ab, cb))
    na = math.sqrt(sum(x * x for x in ab))
    nc = math.sqrt(sum(x * x for x in cb))

    if na * nc < 1e-8:
        return 0.0

    cosine = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(cosine))


def finger_extended(lm, mcp, pip, tip):
    return angle(lm[mcp], lm[pip], lm[tip]) > 155


def finger_folded(lm, mcp, pip, tip):
    return angle(lm[mcp], lm[pip], lm[tip]) < 125


def finger_direction(lm, start, end):
    dx = lm[end].x - lm[start].x
    dy = lm[end].y - lm[start].y

    if math.hypot(dx, dy) < 1e-6:
        return None

    return math.degrees(math.atan2(dx, -dy))


def angle_difference(a, b):
    return abs((a - b + 180) % 360 - 180)


def points_direction(lm, start, end, target, tolerance):
    direction = finger_direction(lm, start, end)

    if direction is None:
        return False

    return angle_difference(direction, target) <= tolerance


def thumb_extended(lm):
    palm = max(distance(lm[0], lm[9]), 1e-6)

    thumb_tip_to_index = distance(lm[4], lm[5]) / palm
    thumb_tip_to_pinky = distance(lm[4], lm[17]) / palm

    return (
        thumb_tip_to_index > 0.55
        and thumb_tip_to_pinky > 0.65
    )


def palm_facing_score(lm, handedness):
    if handedness not in ("Left", "Right"):
        return 0.0

    wrist = lm[0]
    index = lm[5]
    pinky = lm[17]

    ax = index.x - wrist.x
    ay = index.y - wrist.y
    az = index.z - wrist.z

    bx = pinky.x - wrist.x
    by = pinky.y - wrist.y
    bz = pinky.z - wrist.z

    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx

    magnitude = math.sqrt(nx * nx + ny * ny + nz * nz)

    if magnitude < 1e-8:
        return 0.0

    hand_sign = 1 if handedness == "Left" else -1

    return (nz / magnitude) * hand_sign * PALM_SIGN


def is_palm_facing(lm, handedness):
    return (
        palm_facing_score(lm, handedness)
        >= PALM_MIN_FACING
    )


def is_v_sign(lm):
    index_open = finger_extended(lm, 5, 6, 8)
    middle_open = finger_extended(lm, 9, 10, 12)

    ring_folded = finger_folded(lm, 13, 14, 16)
    pinky_folded = finger_folded(lm, 17, 18, 20)

    spread = angle(lm[8], lm[5], lm[12]) > 15

    return (
        index_open
        and middle_open
        and ring_folded
        and pinky_folded
        and spread
    )


def is_ok(lm):
    palm = max(distance(lm[0], lm[9]), 1e-6)

    touching = distance(lm[4], lm[8]) / palm < 0.35

    others_open = all([
        finger_extended(lm, 9, 10, 12),
        finger_extended(lm, 13, 14, 16),
        finger_extended(lm, 17, 18, 20),
    ])

    return touching and others_open


def gun_diagnostics(lm, handedness):
    index_open = finger_extended(lm, 5, 6, 8)

    middle_folded = finger_folded(lm, 9, 10, 12)
    ring_folded = finger_folded(lm, 13, 14, 16)
    pinky_folded = finger_folded(lm, 17, 18, 20)

    thumb_open = thumb_extended(lm)

    shape_ok = (
        index_open
        and thumb_open
        and middle_folded
        and ring_folded
        and pinky_folded
    )

    index_angle = finger_direction(lm, 5, 8)

    # 좌우 어느 쪽이든 수평으로 겨누면 허용
    direction_ok = False

    if index_angle is not None:
        direction_ok = (
            angle_difference(
                index_angle,
                90
            ) <= GUN_TOLERANCE
            or angle_difference(
                index_angle,
                -90
            ) <= GUN_TOLERANCE
        )

    palm_score = palm_facing_score(
        lm,
        handedness
    )

    palm_ok = (
        palm_score >= PALM_MIN_FACING
    )

    return {
        "shape_ok": shape_ok,
        "thumb_ok": thumb_open,
        "index_ok": index_open,
        "middle_ok": middle_folded,
        "ring_ok": ring_folded,
        "pinky_ok": pinky_folded,
        "direction_ok": direction_ok,
        "palm_ok": palm_ok,
        "palm_score": palm_score,
        "index_angle": index_angle,
    }


def is_gun(lm, handedness):
    info = gun_diagnostics(
        lm,
        handedness
    )

    if not info["shape_ok"]:
        return False

    if not info["direction_ok"]:
        return False

    if (
        REQUIRE_PALM_FOR_GUN
        and not info["palm_ok"]
    ):
        return False

    return True


def is_index_up(lm):
    index_open = finger_extended(lm, 5, 6, 8)

    others_folded = all([
        finger_folded(lm, 9, 10, 12),
        finger_folded(lm, 13, 14, 16),
        finger_folded(lm, 17, 18, 20),
    ])

    pointing_up = points_direction(
        lm,
        5,
        8,
        0,
        VOLUME_UP_TOLERANCE
    )

    # 총 모양과 구분하기 위해 엄지 펼침을 제외
    return (
        index_open
        and others_folded
        and pointing_up
        and not thumb_extended(lm)
    )


def is_thumb_down(lm):
    palm = max(distance(lm[0], lm[9]), 1e-6)

    thumb_open = (
        distance(lm[4], lm[2]) / palm > 0.55
    )

    others_folded = all([
        finger_folded(lm, 5, 6, 8),
        finger_folded(lm, 9, 10, 12),
        finger_folded(lm, 13, 14, 16),
        finger_folded(lm, 17, 18, 20),
    ])

    pointing_down = points_direction(
        lm,
        2,
        4,
        180,
        VOLUME_DOWN_TOLERANCE
    )

    return (
        thumb_open
        and others_folded
        and pointing_down
    )


def recognize_gesture(lm, handedness):
    if is_v_sign(lm):
        return "V_SIGN"

    if is_ok(lm):
        return "PLAY_PAUSE"

    if is_gun(lm, handedness):
        if handedness == "Left":
            return "SEEK_BACKWARD"

        if handedness == "Right":
            return "SEEK_FORWARD"

    if is_index_up(lm):
        return "VOLUME_UP"

    if is_thumb_down(lm):
        return "VOLUME_DOWN"

    return "UNKNOWN"


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

                return (
                    "CONTROL_ON"
                    if self.enabled
                    else "CONTROL_OFF"
                )

            return None

        if not self.enabled:
            return None

        if gesture == "UNKNOWN":
            return None

        if self.command_latched:
            return None

        if elapsed < self.stable_time:
            return None

        if (
            now - self.last_command_time
            < self.cooldown
        ):
            return None

        self.command_latched = True
        self.last_command_time = now

        return gesture