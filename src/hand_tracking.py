
import time
from pathlib import Path

import cv2
import mediapipe as mp

from gesture_recognition import (
    GestureController,
    recognize_gesture,
    gun_diagnostics
)


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
            frame,
            (x, y),
            4,
            (0, 0, 255),
            -1
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

    detected_hand = (
        result.handedness[index][0].category_name
    )

    # 기존 카메라 환경에 맞춘 좌우 보정 유지
    if detected_hand == "Left":
        return "Right"

    if detected_hand == "Right":
        return "Left"

    return "UNKNOWN"


def status_text(value):
    return "OK" if value else "NO"


def draw_debug(frame, hand_name, info, row):
    x = 15
    y = 220 + row * 150

    angle_value = info["index_angle"]

    if angle_value is None:
        angle_text = "N/A"
    else:
        angle_text = f"{angle_value:.1f}"

    lines = [
        f"{hand_name} GUN TEST",
        (
            f"Shape: {status_text(info['shape_ok'])}  "
            f"Thumb: {status_text(info['thumb_ok'])}"
        ),
        (
            f"Index: {status_text(info['index_ok'])}  "
            f"Middle: {status_text(info['middle_ok'])}"
        ),
        (
            f"Ring: {status_text(info['ring_ok'])}  "
            f"Pinky: {status_text(info['pinky_ok'])}"
        ),
        (
            f"Direction: {status_text(info['direction_ok'])} "
            f"({angle_text} deg)"
        ),
        (
            f"Palm: {status_text(info['palm_ok'])} "
            f"({info['palm_score']:.2f})"
        ),
    ]

    for j, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (x, y + j * 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
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

                detected_gestures = []

                if result.hand_landmarks:
                    for i, hand in enumerate(
                        result.hand_landmarks
                    ):
                        draw_landmarks(frame, hand)

                        handedness = get_handedness(
                            result,
                            i
                        )

                        gesture = recognize_gesture(
                            hand,
                            handedness
                        )

                        detected_gestures.append(
                            (handedness, gesture)
                        )

                        info = gun_diagnostics(
                            hand,
                            handedness
                        )

                        draw_debug(
                            frame,
                            handedness,
                            info,
                            i
                        )

                        height, width = frame.shape[:2]
                        wrist = hand[0]

                        text_x = int(wrist.x * width)
                        text_y = int(wrist.y * height) + 25

                        text_x = max(
                            0,
                            min(text_x, width - 220)
                        )

                        text_y = max(
                            25,
                            min(text_y, height - 10)
                        )

                        cv2.putText(
                            frame,
                            f"{handedness}: {gesture}",
                            (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (255, 255, 0),
                            2
                        )

                    gestures = [
                        gesture
                        for _, gesture in detected_gestures
                    ]

                    if "V_SIGN" in gestures:
                        selected_gesture = "V_SIGN"

                    else:
                        # 첫 번째 손의 명령을 사용
                        selected_gesture = gestures[0]

                    command = controller.update(
                        selected_gesture
                    )

                    if command is not None:
                        last_command = command
                        print(f"Command: {command}")

                else:
                    controller.reset_tracking()

                status = (
                    "ON" if controller.enabled else "OFF"
                )

                status_color = (
                    (0, 255, 0)
                    if controller.enabled
                    else (0, 0, 255)
                )

                cv2.putText(
                    frame,
                    f"Control: {status}",
                    (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    status_color,
                    2
                )

                cv2.putText(
                    frame,
                    f"Hands detected: {len(detected_gestures)}",
                    (15, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Last Command: {last_command}",
                    (15, 115),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "ESC: EXIT",
                    (15, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                cv2.imshow(
                    "Gesture Controller",
                    frame
                )

                if cv2.waitKey(1) & 0xFF == 27:
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
