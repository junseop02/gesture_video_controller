import cv2
import mediapipe as mp
from pathlib import Path

from gesture_recognition import (
    recognize_hand_shape,
    JamJamRecognizer
)
from motion_tracking import MotionTracker


# 프로젝트 경로
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "hand_landmarker.task"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"모델 파일이 없습니다: {MODEL_PATH}"
    )


# MediaPipe 설정
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]

options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=str(MODEL_PATH)
    ),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=2
)


# 제스처 인식기
motion_tracker = MotionTracker()
jamjam_recognizer = JamJamRecognizer()


def reset_recognizers():
    motion_tracker.reset()
    jamjam_recognizer.reset()


# 웹캠 연결
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("웹캠을 열 수 없습니다.")


try:
    with HandLandmarker.create_from_options(options) as landmarker:

        timestamp_ms = 0

        # 제스처 명령 활성화 상태
        recognition_enabled = True

        last_motion = "NONE"
        last_gesture = "NONE"
        hand_shape = "NONE"

        while True:
            ret, frame = cap.read()

            if not ret:
                print("프레임을 읽을 수 없습니다.")
                break

            # 좌우 반전
            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]

            # BGR -> RGB
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            # 손 검출
            timestamp_ms += 33

            result = landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )

            if not result.hand_landmarks:
                reset_recognizers()
                hand_shape = "NONE"

            else:
                # 모든 손의 랜드마크 표시
                for hand in result.hand_landmarks:
                    points = []

                    for landmark in hand:
                        x = int(landmark.x * width)
                        y = int(landmark.y * height)

                        points.append((x, y))

                        cv2.circle(
                            frame,
                            (x, y),
                            4,
                            (0, 0, 255),
                            -1
                        )

                    for start, end in HAND_CONNECTIONS:
                        cv2.line(
                            frame,
                            points[start],
                            points[end],
                            (0, 255, 0),
                            2
                        )

                # 첫 번째 손 기준
                hand = result.hand_landmarks[0]

                # 손 모양은 ON/OFF 관계없이 표시
                hand_shape = recognize_hand_shape(hand)

                if recognition_enabled:

                    # 잼잼 제스처
                    gesture = jamjam_recognizer.update(
                        hand_shape
                    )

                    if gesture is not None:
                        last_gesture = gesture

                        print(
                            f"Gesture detected: {gesture}"
                        )

                        motion_tracker.reset()

                    # 상하좌우 이동
                    direction = motion_tracker.update(hand)

                    if direction is not None:
                        last_motion = direction

                        print(
                            f"Motion detected: {direction}"
                        )

            # 인식 ON/OFF 상태
            status = "ON" if recognition_enabled else "OFF"

            status_color = (
                (0, 255, 0)
                if recognition_enabled
                else (0, 0, 255)
            )

            cv2.putText(
                frame,
                f"Recognition: {status}",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                status_color,
                2
            )

            # 손 모양
            cv2.putText(
                frame,
                f"Hand: {hand_shape}",
                (30, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )

            # 이동 방향
            cv2.putText(
                frame,
                f"Motion: {last_motion}",
                (30, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

            # 잼잼 인식
            cv2.putText(
                frame,
                f"Gesture: {last_gesture}",
                (30, 175),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 255),
                2
            )

            # 조작 안내
            cv2.putText(
                frame,
                "S: ON/OFF | ESC: EXIT",
                (30, height - 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.imshow("Hand Tracking", frame)

            key = cv2.waitKey(1) & 0xFF

            # ESC 종료
            if key == 27:
                break

            # S 키로 제스처 명령 ON/OFF
            elif key in (ord("s"), ord("S")):
                recognition_enabled = not recognition_enabled

                reset_recognizers()

                last_motion = "NONE"
                last_gesture = "NONE"

                print(
                    f"Recognition: "
                    f"{'ON' if recognition_enabled else 'OFF'}"
                )

finally:
    cap.release()
    cv2.destroyAllWindows()