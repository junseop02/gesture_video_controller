
# Gesture Video Controller

Python, OpenCV, MediaPipe를 활용한 손 제스처 기반 동영상 제어 시스템입니다.

컴퓨터비전 팀프로젝트로, 웹캠에서 손의 랜드마크를 검출하고 손 모양 및 이동 방향을 분석합니다.

현재는 제스처 인식 기능까지 구현했으며, 유튜브 제어 기능은 추후 팀원 작업과 통합할 예정입니다.

## 1. 주요 기술

- Python
- OpenCV
- MediaPipe Hand Landmarker

## 2. 프로젝트 구조

```text
gesture_video_controller/
├── models/
│   └── hand_landmarker.task
├── src/
│   ├── hand_tracking.py
│   ├── gesture_recognition.py
│   └── motion_tracking.py
├── tests/
│   └── camera_test.py
├── .gitignore
├── README.md
└── requirements.txt
```

### 파일 설명

| 파일 | 설명 |
|---|---|
| `hand_tracking.py` | 웹캠 입력, 손 검출, 제스처 인식 통합 및 화면 출력 |
| `gesture_recognition.py` | OPEN/FIST 손 모양 및 잼잼 제스처 인식 |
| `motion_tracking.py` | 상하좌우 손 이동 인식 |
| `camera_test.py` | 웹캠 연결 테스트 |
| `hand_landmarker.task` | MediaPipe 손 랜드마크 검출 모델 |

## 3. 구현 기능

| 손 동작 | 인식 결과 | 향후 영상 제어 기능 |
|---|---|---|
| 손바닥 펼침 | OPEN | 손 모양 판정 |
| 주먹 쥠 | FIST | 손 모양 판정 |
| OPEN → FIST → OPEN | PLAY_PAUSE | 재생/일시정지 |
| 왼쪽 → 오른쪽 | RIGHT | 10초 앞으로 |
| 오른쪽 → 왼쪽 | LEFT | 10초 뒤로 |
| 아래 → 위 | UP | 볼륨 증가 |
| 위 → 아래 | DOWN | 볼륨 감소 |

현재 영상 제어 기능은 연결되지 않았습니다.

인식 결과는 OpenCV 화면과 터미널에서 확인할 수 있습니다.

## 4. 실행 환경

- Windows 환경에서 개발
- Python 및 pip 필요
- 웹캠 필요
- `models/hand_landmarker.task` 모델 파일 필요

Python 및 라이브러리 버전은 `requirements.txt`를 참고하세요.

## 5. 설치 방법

### 5.1 저장소 클론

```bash
git clone https://github.com/junseop02/gesture_video_controller.git
cd gesture_video_controller
```

### 5.2 가상환경 생성

```bash
python -m venv .venv
```

### 5.3 가상환경 활성화

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Git Bash:

```bash
source .venv/Scripts/activate
```

### 5.4 패키지 설치

```bash
python -m pip install -r requirements.txt
```

### 5.5 모델 파일 확인

다음 경로에 모델 파일이 있어야 합니다.

```text
models/hand_landmarker.task
```

모델 파일이 저장소에 포함되지 않은 경우 MediaPipe 공식 모델 배포 경로에서 별도로 준비해야 합니다.

## 6. 실행 방법

프로젝트 최상위 폴더에서 실행합니다.

```bash
python src/hand_tracking.py
```

실행하면 웹캠 화면이 열리고 손의 랜드마크와 인식 결과가 표시됩니다.

## 7. 테스트 방법

### 7.1 손 모양 인식

- 손바닥 펼치기 → `Hand: OPEN`
- 주먹 쥐기 → `Hand: FIST`

### 7.2 잼잼 인식

손바닥 펼침 → 주먹 쥠 → 손바닥 펼침 순서로 동작합니다.

정상 인식 시:

```text
Gesture detected: PLAY_PAUSE
```

### 7.3 이동 방향 인식

- 왼쪽 → 오른쪽: RIGHT
- 오른쪽 → 왼쪽: LEFT
- 아래 → 위: UP
- 위 → 아래: DOWN

정상 인식 시 터미널에 다음과 같이 출력됩니다.

```text
Motion detected: RIGHT
```

### 7.4 제스처 인식 ON/OFF

- `S`: 제스처 명령 인식 ON/OFF
- `ESC`: 프로그램 종료

OFF 상태에서도 손 랜드마크와 손 모양은 표시되지만, 새로운 제스처 명령은 발생하지 않습니다.

키보드 입력은 OpenCV 영상 창이 활성화된 상태에서 사용하세요.

## 8. 유튜브 제어 기능 연동 안내

현재 제스처 명령은 `src/hand_tracking.py`에서 생성됩니다.

잼잼 인식:

```python
gesture = jamjam_recognizer.update(hand_shape)

if gesture is not None:
    print(f"Gesture detected: {gesture}")
```

이동 인식:

```python
direction = motion_tracker.update(hand)

if direction is not None:
    print(f"Motion detected: {direction}")
```

연동할 명령 문자열:

```text
PLAY_PAUSE
LEFT
RIGHT
UP
DOWN
```

유튜브 제어 기능을 연결할 때는 화면에 저장된 마지막 인식 결과가 아니라, `gesture` 또는 `direction`이 새로 발생한 시점에 명령을 처리해야 합니다.

## 9. 현재 제한 사항

- 제스처 판정은 검출된 첫 번째 손을 기준으로 수행합니다.
- 손을 빠르게 움직일 경우 인식이 누락될 수 있습니다.
- 제스처 인식 민감도와 시간 조건은 초기 설정값입니다.
- 유튜브 제어 기능은 아직 연결되지 않았습니다.
- 양손을 독립적으로 추적하는 기능은 아직 구현되지 않았습니다.

## 10. 향후 작업

- [x] 웹캠 연결
- [x] 손 랜드마크 검출
- [x] OPEN/FIST 인식
- [x] 상하좌우 이동 인식
- [x] 잼잼 제스처 인식
- [x] 제스처 명령 ON/OFF
- [ ] 유튜브 제어 기능 통합
- [ ] 제스처 인식 정확도 및 속도 개선
- [ ] 양손 처리 개선
- [ ] 최종 통합 테스트
```
