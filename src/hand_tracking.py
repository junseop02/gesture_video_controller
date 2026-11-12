
import time
from pathlib import Path

import cv2
import mediapipe as mp

from gesture_recognition import (
    GestureController,
    recognize_gesture,
    select_gesture
)
from motion_tracking import MotionTracker


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "hand_landmarker.task"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"모델 파일이 없습니다: {MODEL_PATH}"
    )


BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode


CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]


def draw_landmarks(frame, landmarks):
    height, width = frame.shape[:2]
    points = []

    for lm in landmarks:
        x = int(lm.x * width)
        y = int(lm.y * height)
        points.append((x, y))

        cv2.circle(
            frame, (x, y), 4, (0, 0, 255), -1
        )

    for start, end in CONNECTIONS:
        cv2.line(
            frame,
            points[start],
            points[end],
            (0, 255, 0),
            2
        )


def get_handedness(result, index):
    if (
        index >= len(result.handedness)
        or not result.handedness[index]
    ):
        return "UNKNOWN"

    detected = result.handedness[index][0].category_name

    if detected == "Left":
        return "Right"

    if detected == "Right":
        return "Left"

    return "UNKNOWN"


def draw_text(frame, text, x, y, color=(255, 255, 255)):
    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2
    )


def main():
    options = HandLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=RunningMode.VIDEO,
        num_hands=2
    )

    controller = GestureController()

    trackers = {
        "Left": MotionTracker(),
        "Right": MotionTracker()
    }

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise RuntimeError("웹캠을 열 수 없습니다.")

    start_time = time.monotonic()
    last_timestamp = -1
    last_command = "NONE"

    try:
        with HandLandmarker.create_from_options(options) as detector:
            while True:
                ret, frame = cap.read()

                if not ret:
                    print("프레임을 읽을 수 없습니다.")
                    break

                frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb
                )

                timestamp_ms = int(
                    (time.monotonic() - start_time) * 1000
                )
                timestamp_ms = max(
                    timestamp_ms,
                    last_timestamp + 1
                )
                last_timestamp = timestamp_ms

                result = detector.detect_for_video(
                    mp_image,
                    timestamp_ms
                )

                hand_data = []
                seen_hands = set()

                if result.hand_landmarks:
                    for i, hand in enumerate(result.hand_landmarks):
                        draw_landmarks(frame, hand)

                        name = get_handedness(result, i)
                        static = recognize_gesture(hand, name)

                        hand_data.append({
                            "name": name,
                            "landmarks": hand,
                            "static": static
                        })

                        if name in trackers:
                            seen_hands.add(name)

                static_gestures = [
                    item["static"] for item in hand_data
                ]

                high_priority_active = any(
                    gesture in ("V_SIGN", "PLAY_PAUSE")
                    for gesture in static_gestures
                )

                candidates = list(static_gestures)
                motion_sources = {}

                for item in hand_data:
                    name = item["name"]

                    if name not in trackers:
                        continue

                    tracker = trackers[name]

                    allow_motion = (
                        controller.enabled
                        and not high_priority_active
                    )

                    # 손 모양에 관계없이 이동 방향만 검사
                    motion = tracker.update(
                        item["landmarks"],
                        allow_motion=allow_motion
                    )

                    if motion is not None:
                        candidates.append(motion)
                        motion_sources.setdefault(
                            motion, []
                        ).append(name)

                    height, width = frame.shape[:2]
                    wrist = item["landmarks"][0]

                    x = int(wrist.x * width)
                    y = int(wrist.y * height) + 25

                    x = max(0, min(x, width - 230))
                    y = max(25, min(y, height - 10))

                    label = (
                        motion
                        if motion is not None
                        else item["static"]
                    )

                    draw_text(
                        frame,
                        f"{name}: {label}",
                        x, y,
                        (255, 255, 0)
                    )

                for name, tracker in trackers.items():
                    if name not in seen_hands:
                        tracker.mark_missing()

                selected = select_gesture(candidates)

                if not hand_data:
                    controller.reset_tracking()
                    command = None
                else:
                    command = controller.update(selected)

                if command is not None:
                    last_command = command
                    print(f"Command: {command}")

                    if command in ("CONTROL_ON", "CONTROL_OFF"):
                        for tracker in trackers.values():
                            tracker.reset()

                    elif command in motion_sources:
                        for name in motion_sources[command]:
                            trackers[name].lock()

                status = "ON" if controller.enabled else "OFF"

                status_color = (
                    (0, 255, 0)
                    if controller.enabled
                    else (0, 0, 255)
                )

                draw_text(
                    frame,
                    f"Control: {status}",
                    15, 35,
                    status_color
                )

                draw_text(
                    frame,
                    f"Hands detected: {len(hand_data)}",
                    15, 70,
                    (255, 255, 0)
                )

                draw_text(
                    frame,
                    f"Selected: {selected}",
                    15, 105,
                    (255, 255, 0)
                )

                draw_text(
                    frame,
                    f"Last Command: {last_command}",
                    15, 140,
                    (255, 0, 255)
                )

                draw_text(
                    frame,
                    f"Left: {trackers['Left'].state}",
                    15, 175
                )

                draw_text(
                    frame,
                    f"Right: {trackers['Right'].state}",
                    15, 205
                )

                draw_text(
                    frame,
                    "ESC: EXIT",
                    15,
                    frame.shape[0] - 20
                )

                cv2.imshow("Gesture Controller", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
