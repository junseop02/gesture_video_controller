# Gesture Video Controller

웹캠으로 손동작을 인식해 영상 제어 명령으로 바꾸는 컴퓨터비전 팀 프로젝트입니다. Python, OpenCV, MediaPipe Hand Landmarker를 사용해 양손의 랜드마크를 검출하고 손 모양과 움직임을 분석합니다.

현재 웹캠 창과 터미널에서 인식된 명령을 확인할 수 있습니다. 실제 YouTube 재생 제어 연동은 추후 작업입니다.

## 설치 및 실행

Windows와 Python 3.12 환경에서 개발했습니다. Git과 웹캠이 필요하며, 손 랜드마크 모델(`models/hand_landmarker.task`)은 저장소에 포함되어 있습니다.

Windows Git Bash에서 실행합니다.

```bash
git clone https://github.com/junseop02/gesture_video_controller.git
cd gesture_video_controller
py -3.12 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python src/hand_tracking.py
```

웹캠 창을 선택한 상태에서 **Esc**를 누르면 종료됩니다. 카메라 연결만 확인하려면 프로젝트 폴더에서 `python tests/camera_test.py`를 실행하세요.

## 제스처

실행 직후에는 제어가 꺼져 있습니다. V 사인을 1초 유지해 `CONTROL_ON`을 확인한 뒤 다른 제스처를 사용하세요.

| 손동작 | 인식 결과 | 영상 제어 용도 |
|---|---|---|
| V 사인을 1초 유지 | `CONTROL_ON` / `CONTROL_OFF` | 제스처 제어 켜기·끄기 |
| OK 사인 | `PLAY_PAUSE` | 재생·일시정지 |
| 편 손을 세운 뒤 사용자 기준 오른쪽으로 젖히기 | `SEEK_FORWARD` | 10초 앞으로 |
| 편 손을 세운 뒤 사용자 기준 왼쪽으로 젖히기 | `SEEK_BACKWARD` | 10초 뒤로 |
| 엄지를 위로 편 자세를 유지하며 손을 위로 이동 | `VOLUME_UP` | 볼륨 증가 |
| 엄지를 아래로 편 자세를 유지하며 손을 아래로 이동 | `VOLUME_DOWN` | 볼륨 감소 |
| 탐색 명령 후 엄지까지 접은 주먹을 0.25초 유지 | `FIST: now only …` | 반대 탐색 방향 허용 |

좌우 탐색은 어느 손으로도 할 수 있습니다. 손목을 거의 제자리에 두고 손을 젖혀 보세요. 탐색 명령이 발생하면 손을 되돌리는 동작에서 반대 명령이 나오는 것을 줄이기 위해 반대 방향을 3초 동안 잠급니다. 같은 방향으로 다시 입력하려면 손을 세운 자세로 되돌린 뒤 다시 젖힙니다.

## 양손 전체화면 제스처 (테스트 중)

이 기능은 `feature/fullscreen-control` 작업 브랜치에서 테스트 중입니다. 현재 GitHub의 `main`에는 좌우 탐색과 볼륨 조절까지 반영되어 있습니다.

| 양손 동작 | 인식 결과 |
|---|---|
| 양손을 가운데에서 양옆으로 벌리기 | `FULLSCREEN_ON` |
| 양손을 양옆에서 가운데로 모으기 | `FULLSCREEN_OFF` |

테스트 버전에서는 웹캠 창의 `FS State`, `FS Distance`, `FS Delta`로 인식 단계, 두 손의 가로 거리, 거리 변화량을 확인할 수 있습니다.

## 테스트 결과 확인

- `Selected`에는 현재 선택된 제스처 후보가 표시됩니다.
- `Last Command`와 화면 오른쪽 아래 로그에는 실제로 출력된 명령이 표시됩니다.
- 실행 중 생성되는 프레임별 진단 CSV는 `traces/`에 저장됩니다.

## 주요 파일

| 경로 | 역할 |
|---|---|
| `src/hand_tracking.py` | 웹캠 입력, 양손 검출, 제스처 처리 및 화면 표시 |
| `src/gesture_recognition.py` | V·OK·주먹·엄지 자세 판정과 명령 처리 |
| `src/swing_tracking.py` | 좌우 스윙, 반대 방향 잠금, 엄지 자세를 결합한 볼륨 판정 |
| `src/motion_tracking.py` | 손의 이동량 및 쿨다운 계산 |
| `tests/camera_test.py` | 웹캠 연결 확인 |
| `requirements.txt` | 실행에 필요한 Python 패키지 목록 |