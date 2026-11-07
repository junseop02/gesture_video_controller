import math
import time
from collections import deque


class MotionTracker:
    def __init__(
        self,
        threshold=0.18,
        window=0.6,
        cooldown=1.0
    ):
        self.threshold = threshold
        self.window = window
        self.cooldown = cooldown

        self.history = deque()
        self.last_detection = -float("inf")
        self.last_seen = None

    def reset(self):
        self.history.clear()
        self.last_seen = None

    def update(self, landmarks):
        now = time.monotonic()

        # 손목(0), 검지 시작점(5), 소지 시작점(17)
        # 세 랜드마크의 평균으로 손 중심 계산
        indices = [0, 5, 17]

        x = sum(landmarks[i].x for i in indices) / 3
        y = sum(landmarks[i].y for i in indices) / 3

        # 손이 사라졌다가 다시 나타난 경우
        # 이전 위치와 연결하지 않음
        if self.last_seen is not None:
            if now - self.last_seen > 0.2:
                self.history.clear()

        self.last_seen = now
        self.history.append((now, x, y))

        # 설정한 시간 범위를 벗어난 좌표 제거
        while self.history and now - self.history[0][0] > self.window:
            self.history.popleft()

        # 쿨다운 중에는 새로운 제스처 감지하지 않음
        if now - self.last_detection < self.cooldown:
            return None

        if len(self.history) < 3:
            return None

        start_time, start_x, start_y = self.history[0]

        dx = x - start_x
        dy = y - start_y

        # 대각선 이동의 오인식 방지
        horizontal = abs(dx) > abs(dy) * 1.5
        vertical = abs(dy) > abs(dx) * 1.5

        direction = None

        if horizontal and abs(dx) >= self.threshold:
            direction = "RIGHT" if dx > 0 else "LEFT"

        elif vertical and abs(dy) >= self.threshold:
            # 이미지 좌표는 아래로 갈수록 y 증가
            direction = "DOWN" if dy > 0 else "UP"

        if direction is not None:
            self.last_detection = now
            self.history.clear()

        return direction