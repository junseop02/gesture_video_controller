"""'가운데 -> 좌/우' 손목 스윙으로 SEEK 판정 + 반대 방향 3초/주먹 규칙.

팀원 저장소의 MotionTracker 를 상속한다 (쿨다운·위/아래 볼륨은 원래 코드).

손 방향 = 손목(0) -> 중지 뿌리(9) 벡터의 각도.
  0° = 화면 위, +90° = 화면 오른쪽, -90° = 화면 왼쪽.
화면이 거울 반전(cv2.flip)이라 화면 오른쪽 = 사용자 기준 오른쪽.

판정 순서 (손마다):
  1) WAIT_CENTER : 손이 어디 있든, 먼저 가운데(|각도| <= center_zone)에 dwell 초 머물러야 한다.
  2) ARMED       : 가운데에서 swing_time 초 안에 한쪽으로 trigger_angle 이상 넘어가면 SEEK.
                   오른쪽 = SEEK_FORWARD, 왼쪽 = SEEK_BACKWARD.
  3) 판정 후 다시 WAIT_CENTER. 되돌아오는 동작은 '가운데로 가는 것'일 뿐이라 SEEK 가 아니다.

2026-11-15 실측 반영:
  - 휘두르는 도중 1~3프레임 손을 놓친다(모션 블러) -> gap_max 이하 공백은 이어서 본다.
  - 스윙 중 손목도 손 크기의 0.5~1.4배 움직인다 -> 허용 1.5배.
"""
import csv
import math
import time
from collections import deque
from pathlib import Path

from motion_tracking import MotionTracker


SWING_TO_RIGHT = "SEEK_FORWARD"   # 가운데 -> 사용자 기준 오른쪽
SWING_TO_LEFT = "SEEK_BACKWARD"   # 가운데 -> 사용자 기준 왼쪽
OPPOSITE = {
    "SEEK_FORWARD": "SEEK_BACKWARD",
    "SEEK_BACKWARD": "SEEK_FORWARD",
}


# 진단용 프레임 기록 (값 조정 근거).
# 실행마다 새 파일 traces/swing_trace_YYYYMMDD_HHMMSS.csv — 이전 기록을 절대 덮어쓰지 않는다.
# import 만으로는 파일을 만들지 않는다 (첫 기록 때 연다). TRACE_ENABLED=False 면 기록 안 함.
TRACE_ENABLED = True
TRACE_DIR = Path(__file__).resolve().parent.parent / "traces"
_trace_file = None
_trace = None
_T0 = time.monotonic()


def trace(*row):
    global _trace_file, _trace
    if not TRACE_ENABLED:
        return
    if _trace is None:
        TRACE_DIR.mkdir(exist_ok=True)
        path = TRACE_DIR / time.strftime("swing_trace_%Y%m%d_%H%M%S.csv")
        _trace_file = open(path, "x", newline="", encoding="utf-8")  # 'x' = 이미 있으면 실패
        _trace = csv.writer(_trace_file)
        _trace.writerow(["t", "hand", "event", "state", "allow", "arm", "angle",
                         "wrist_x", "wrist_y", "size", "drift", "since_center", "result"])
    _trace.writerow([f"{time.monotonic() - _T0:.3f}", *row])
    _trace_file.flush()


class SwingTracker(MotionTracker):
    def __init__(
        self,
        center_zone=20,       # |각도| 가 이 이하면 '가운데'
        dwell=0.0,            # 가운데에 이만큼(초) 머물러야 준비 완료. 0 = 가운데 프레임 1장이면 준비
        trigger_angle=40,     # 가운데에서 이 각도 이상 넘어가면 SEEK
        swing_time=0.7,       # 가운데를 떠난 뒤 이 시간(초) 안에 넘어가야 함 (천천히 기울이는 건 무시)
        wrist_drift_max=2.5,  # 손목 이동이 손 크기(0->9 거리)의 이 배수 이하 (잠긴 쪽에서 크게 넘겨 치면 2.0 까지 나옴)
        gap_max=0.4,          # 손을 이만큼(초) 이하로 놓친 건 같은 동작으로 이어 본다
        open_ratio=0.5,       # 판정 직전 open_window 초 동안 '편 손' 프레임이 이 비율 이상이어야 SEEK
        open_window=0.5,
        name="?",             # 진단 기록용 손 이름
        **kwargs
    ):
        kwargs.setdefault("horizontal_threshold", float("inf"))  # 손 전체 좌우 이동 SEEK 끄기
        kwargs.setdefault("gap", gap_max)  # 볼륨 이동 기록도 짧은 공백은 이어서 본다
        super().__init__(**kwargs)

        self.center_zone = center_zone
        self.dwell = dwell
        self.trigger_angle = trigger_angle
        self.swing_time = swing_time
        self.wrist_drift_max = wrist_drift_max
        self.gap_max = gap_max
        self.open_ratio = open_ratio
        self.open_window = open_window
        self.open_log = deque()  # (시각, 편 손 여부)
        self.name = name

        self.debug = ""  # 화면 표시용
        self.pose = None         # 지금 인정하는 엄지 자세 ("UP"/"DOWN"/None)
        self.thumb_seen = None   # (자세, 마지막으로 본 시각)
        self.thumb_grace = 0.5   # 움직이는 중(블러) 자세를 놓쳐도 이만큼(초)은 유지로 본다. 손을 펴면 즉시 해제
        self.clear_swing()

    def clear_swing(self):
        self.arm = "WAIT_CENTER"
        self.center_since = None   # 가운데에 들어온 시각
        self.last_center = None    # 마지막으로 가운데에 있던 시각
        self.center_wrist = None   # 그때 손목 위치 (손목 고정 판단 기준)
        self.armed_side = None     # 잠긴 쪽에서 준비된 경우 그 방향
        self.swing_seen = None     # 마지막으로 손을 본 시각

    def reset(self):
        super().reset()
        self.clear_swing()

    def lock(self):
        super().lock()
        self.clear_swing()

    def mark_missing(self):
        # 이동 기록·스윙 상태 모두 유지한다 (움직이는 중 1~5프레임 놓치는 일이 흔함).
        # 오래 놓친 경우는 update 에서 gap / gap_max 로 걸러진다.
        trace(self.name, "MISSING", self.state, "", self.arm, "", "", "", "", "", "", "")

    def update(self, landmarks, allow_motion=True, blocked=(), thumb=None, fist=False,
               open_hand=False, info=""):
        """blocked: 지금 잠겨 있는 SEEK 명령들. 잠긴 방향은 아예 인식하지 않는다.

        잠긴 쪽으로 손이 가는 것은 '가운데에 있는 것'과 똑같이 취급한다(준비 구역).
        -> 잠긴 쪽으로 팔을 뺐다가 열린 쪽으로 치면 그대로 인식되고,
           잠긴 쪽 동작 자체는 판정·기록·쿨다운 어디에도 영향을 주지 않는다.

        thumb: 이 프레임의 엄지 자세 ("UP"/"DOWN"/None).
          엄지 위 + 손이 위로 이동 = VOLUME_UP, 엄지 아래 + 손이 아래로 이동 = VOLUME_DOWN.
          자세와 이동 방향이 맞을 때만 볼륨이다 (되돌아오는 동작은 방향이 반대라 무시된다).
        fist: 네 손가락이 접혀 있음. 이때는 SEEK 스윙을 판정하지 않는다
          (따봉을 만드는 도중 손이 옆으로 누우면서 SEEK 로 잡히는 것 방지).
        """
        now = time.monotonic()

        # 0) 엄지 자세 (잠깐 놓친 프레임은 thumb_grace 동안 유지로 본다)
        if landmarks is not None:  # 진단: 매 프레임 자세 판정 근거
            trace(self.name, "POSE", self.state, allow_motion, self.arm, "",
                  f"{landmarks[0].x:.3f}", f"{landmarks[0].y:.3f}", "", "", "",
                  f"{thumb}/{'fist' if fist else 'open' if open_hand else '-'} {info}")
        if landmarks is not None:
            self.open_log.append((now, bool(open_hand)))
        while self.open_log and now - self.open_log[0][0] > self.open_window:
            self.open_log.popleft()
        if thumb is not None:
            self.thumb_seen = (thumb, now)
        elif open_hand:
            self.thumb_seen = None  # 손을 폈으면 엄지 자세 끝
        pose = (
            self.thumb_seen[0]
            if self.thumb_seen is not None and now - self.thumb_seen[1] <= self.thumb_grace
            else None
        )
        if pose != self.pose:
            self.clear_history()  # 자세가 바뀌면 이동 기록을 새로 시작 -> '자세를 한 채' 움직인 것만 남는다
            self.pose = pose

        # 1) 원래 코드: 쿨다운 처리 + 위/아래 이동(볼륨)
        vertical = super().update(landmarks, allow_motion=allow_motion)

        if pose is not None and landmarks is not None and allow_motion:
            self.clear_swing()  # 엄지 자세 중에는 SEEK 스윙을 보지 않는다
            self.debug = f"thumb {pose}"
            wanted = "VOLUME_UP" if pose == "UP" else "VOLUME_DOWN"
            if vertical is not None:
                ok = vertical == wanted
                trace(self.name, "VERTICAL" if ok else "VETO", self.state, allow_motion,
                      self.arm, "", "", "", "", "", pose, vertical)
                if ok:
                    return vertical
            return None

        if vertical is not None:
            # 엄지 자세가 아니면 위/아래 이동은 볼륨이 아니다
            trace(self.name, "VETO", self.state, allow_motion, self.arm,
                  "", "", "", "", "", "", vertical)

        if fist and landmarks is not None and allow_motion:
            self.clear_swing()
            self.debug = "fist"
            return None

        if landmarks is None or not allow_motion:
            self.debug = ""
            self.clear_swing()
            trace(self.name, "SKIP", self.state, allow_motion, self.arm,
                  "", "", "", "", "", "", "")
            return None

        # 쿨다운 중에도 '가운데로 돌아옴'은 계속 본다 (판정만 안 함).
        # 그래야 쿨다운이 끝나자마자 다음 스윙이 바로 잡힌다.
        cooling = self.state == "COOLDOWN"

        # 2) 손 방향
        wrist, base = landmarks[0], landmarks[9]
        vx, vy = base.x - wrist.x, base.y - wrist.y
        size = math.hypot(vx, vy)

        if size < 1e-6:
            return None

        # 화면 위 = 0°, 오른쪽 = +90° (y 축은 아래로 증가하므로 -vy)
        hand_angle = math.degrees(math.atan2(vx, -vy))

        # 너무 오래 놓쳤으면 처음부터
        if self.swing_seen is not None and now - self.swing_seen > self.gap_max:
            self.clear_swing()
        self.swing_seen = now

        result = ""
        drift = 0.0
        since_center = ""

        side = SWING_TO_RIGHT if hand_angle > 0 else SWING_TO_LEFT
        in_center = abs(hand_angle) <= self.center_zone
        on_blocked_side = (not in_center) and side in blocked

        if in_center or on_blocked_side:
            # 준비 구역(가운데 또는 잠긴 쪽): dwell 만큼 머물면 준비 완료
            if self.center_since is None:
                self.center_since = now
            if now - self.center_since >= self.dwell:
                self.arm = "ARMED"
            if self.arm == "ARMED":
                self.last_center = now
                self.center_wrist = (wrist.x, wrist.y)
                # 잠긴 쪽에서 준비됐으면 그쪽은 기억해 둔다 (잠금이 풀리는 순간 오발 방지)
                self.armed_side = side if on_blocked_side else None
        else:
            self.center_since = None

            if self.arm == "ARMED":
                elapsed = now - self.last_center
                since_center = f"{elapsed:.2f}"
                drift = math.hypot(
                    wrist.x - self.center_wrist[0],
                    wrist.y - self.center_wrist[1]
                ) / size

                if elapsed > self.swing_time:
                    self.arm = "WAIT_CENTER"  # 너무 천천히 -> 무효, 다시 가운데부터
                elif side == self.armed_side:
                    # 잠긴 쪽에 손을 둔 채 잠금만 풀린 경우: 동작이 아니므로 다시 가운데부터
                    self.arm = "WAIT_CENTER"
                elif abs(hand_angle) >= self.trigger_angle:
                    # SEEK 는 손을 편 채 치는 동작이다. 엄지 자세로 손을 좌우로 기울이면
                    # 손가락 일부가 펴진 것으로 읽혀 스윙처럼 보이므로 '편 손'인지로 거른다.
                    #  - 판정 프레임과 그 직전 프레임이 둘 다 편 손이거나
                    #  - 최근 open_window 초의 편 손 비율이 open_ratio 이상
                    # 비율만 보면 주먹/엄지 자세 직후의 스윙을 놓친다 (실측 11-15 15:24: 14회 놓침).
                    flags = [o for _, o in self.open_log]
                    opened = (
                        (len(flags) >= 2 and flags[-1] and flags[-2])
                        or sum(flags) / max(len(flags), 1) >= self.open_ratio
                    )
                    if drift <= self.wrist_drift_max and not cooling and opened:
                        result = SWING_TO_RIGHT if hand_angle > 0 else SWING_TO_LEFT
                    self.arm = "WAIT_CENTER"  # 판정했든 손목이 움직여 무효든 다시 가운데부터

        self.debug = (
            f"ang {hand_angle:+.0f} "
            + ("cooldown" if cooling else "READY" if self.arm == "ARMED" else "go center")
        )

        trace(self.name, "SWING", self.state, allow_motion, self.arm, f"{hand_angle:.1f}",
              f"{wrist.x:.3f}", f"{wrist.y:.3f}", f"{size:.3f}", f"{drift:.2f}",
              since_center, result)

        if result:
            self.clear_history()  # 볼륨 기록도 비워 스윙 끝의 처짐이 볼륨으로 안 잡히게
            return result

        return None


class SeekGate:
    """반대 방향 3초 규칙 + 주먹으로 방향 전환.

    - SEEK X 가 인식되면: 반대 방향은 block_time(3초) 동안 막는다. X 는 계속 가능.
    - 그 뒤 주먹을 쥐면: 이번엔 X 를 3초 막고, 반대 방향을 바로 푼다 (= 방향 전환 의사 표시).
    두 손 공통으로 하나만 둔다.
    """

    def __init__(self, block_time=3.0, fist_hold=0.25):
        self.block_time = block_time
        self.fist_hold = fist_hold   # 주먹을 이만큼(초) 유지해야 인정 (스윙 중 순간 오인식 방지)
        self.last_seek = None
        self.blocked_until = {}      # {명령: 풀리는 시각}
        self.fist_since = None
        self.fist_used = False       # 주먹 한 번 쥐는 동안 전환은 한 번만

    def allows(self, command, now=None):
        now = time.monotonic() if now is None else now
        return now >= self.blocked_until.get(command, 0.0)

    def remaining(self, command, now=None):
        now = time.monotonic() if now is None else now
        return max(0.0, self.blocked_until.get(command, 0.0) - now)

    def on_seek(self, command, now=None):
        """SEEK 명령이 실제로 나갔을 때 호출."""
        now = time.monotonic() if now is None else now
        self.last_seek = command
        self.blocked_until[OPPOSITE[command]] = now + self.block_time
        self.blocked_until.pop(command, None)

    def update_fist(self, fist_visible, now=None):
        """매 프레임 호출. 주먹으로 방향이 전환된 순간 True."""
        now = time.monotonic() if now is None else now

        if not fist_visible:
            self.fist_since = None
            self.fist_used = False
            return False

        if self.fist_since is None:
            self.fist_since = now

        if (
            self.fist_used
            or self.last_seek is None
            or now - self.fist_since < self.fist_hold
        ):
            return False

        self.fist_used = True
        # 방금 방향을 막고, 반대 방향을 푼다
        self.blocked_until[self.last_seek] = now + self.block_time
        self.blocked_until.pop(OPPOSITE[self.last_seek], None)
        self.last_seek = OPPOSITE[self.last_seek]  # 다시 주먹 쥐면 원래대로 되돌아감
        return True
