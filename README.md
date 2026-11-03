# Gesture Video Controller

Hand gesture-based YouTube video control system using Python, OpenCV, and MediaPipe.

## 1. 프로젝트 소개

웹캠을 통해 사용자의 손동작을 인식하고, 별도의 키보드나 마우스 조작 없이 YouTube 영상을 제어하는 컴퓨터비전 기반 제스처 리모컨 시스템입니다.

## 2. 개발 환경

| 항목 | 환경 |
|---|---|
| OS | Windows 11 |
| Language | Python 3.12.10 |
| IDE | Visual Studio Code |
| Computer Vision | OpenCV |
| Hand Tracking | MediaPipe |
| Numerical Processing | NumPy |
| Version Control | Git / GitHub |

패키지별 정확한 버전과 의존성은 `requirements.txt`에서 관리합니다.

## 3. 개발 환경 설정

### 3.1 GitHub 저장소 복제

```bash
git clone https://github.com/junseop02/gesture_video_controller.git
cd gesture_video_controller
```

### 3.2 Python 가상환경 생성

```bash
python -m venv .venv
```

### 3.3 가상환경 활성화

Windows Git Bash 기준:

```bash
source .venv/Scripts/activate
```

Windows PowerShell 기준:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3.4 필수 패키지 설치

```bash
python -m pip install -r requirements.txt
```

### 3.5 가상환경 종료

```bash
deactivate
```

## 4. 프로젝트 실행

### 웹캠 테스트

```bash
python tests/camera_test.py
```

- 웹캠 영상 실시간 출력
- `ESC` 키를 누르면 프로그램 종료

현재는 웹캠 출력 테스트까지 구현한 상태입니다.

## 5. 주요 기능 (개발 예정)

| 손 제스처 | 제어 기능 |
|---|---|
| 잼잼 동작 | 영상 재생 / 일시정지 |
| 손 아래 → 위 이동 | 볼륨 증가 |
| 손 위 → 아래 이동 | 볼륨 감소 |
| 손 왼쪽 → 오른쪽 이동 | 10초 앞으로 이동 |
| 손 오른쪽 → 왼쪽 이동 | 10초 뒤로 이동 |

제스처 인식 및 YouTube 제어 기능은 추후 구현 예정입니다.

## 6. 개발 진행 현황

- [x] GitHub 저장소 생성 및 연동
- [x] Python 가상환경 설정
- [x] OpenCV, MediaPipe, NumPy 설치
- [x] requirements.txt 생성
- [x] OpenCV 웹캠 출력 테스트
- [ ] MediaPipe 손 랜드마크 검출
- [ ] 손 제스처 인식
- [ ] YouTube 영상 제어
- [ ] 기능 통합 및 테스트

## 7. 팀 구성

컴퓨터비전 팀프로젝트 — 3인 팀

세부 역할은 추후 업데이트 예정입니다.
