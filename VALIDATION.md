# 0.1.0 alpha 검증 기록

검증 환경: Linux, Python 3.12, PySide6 6.8.3, PyMuPDF 1.26.6,
Qt Quick offscreen software rendering, Tesseract English language data.

## PDF 통합 시험

15개 시험 통과. 화면 상태만 확인하지 않고, 수정한 PDF를 저장·다시 열어 실제 내용을 검사했습니다.

- 영문 본문 교체: 이전 문장 제거, 새 문장 추출, 실행 취소/다시 실행.
- 한글 본문 교체: 저장 후 한글 추출 확인.
- 텍스트 영역 초과: 변경 전체 롤백, 원문 유지.
- 페이지 이동·삭제·삽입·회전과 실행 취소, 저장된 순서 확인.
- 마지막 페이지 삭제 방지.
- 이미지 삽입, 형광펜, 한글 메모 저장.
- 회전된 페이지의 본문 교체·추가 좌표 확인.
- 원본 경로 저장과 저장 상태 표시.
- 저장 실패 시 원본 파일과 미저장 편집 상태 보존.
- 암호 입력, 편집 제한, 소유자 암호, 저장 후 암호 유지.
- 텍스트 영역 복사와 검색, 페이지 렌더링.
- 변경 전 문서를 기준으로 한 오래된 편집/OCR 결과 거부.
- 영어 OCR 후 문자 추출·검색. OCR 전후 원본 페이지 렌더 픽셀 일치.

## 실제 UI 시험

QML 창을 실행한 뒤 포인터 이벤트와 실제 PDF 엔진으로 확인했습니다.

- 문서 열기, 본문·썸네일 렌더링.
- Ctrl+클릭으로 다중 선택.
- 썸네일을 마우스로 끌어 순서 변경, 문서 내용으로 변경 결과 확인.
- 본문 수정 버튼과 편집 대화상자에서 텍스트 교체, 적용 버튼 클릭.
- 저장 후 별도로 PDF를 열어 이전 텍스트가 제거되었는지 확인.
- 검색, 페이지 이동, 실행 취소·다시 실행.
- 별도 프로세스에서 영어 OCR 실행 후 저장된 PDF의 문자층 확인.
- OCR 준비 중 취소.

## 아직 확인하지 않은 항목

- Windows 실기기에서 설치·실행·제거.
- Windows GPU 가속, 고해상도 화면과 드라이버별 동작.
- 실제 사용자 대용량 문서와 Sumatra의 속도 비교.
- 한국어 OCR 인식 정확도.
- 고급 양식·전자서명·PDF/A·복잡한 내부 링크/목차 보존.

이 패키지는 실행 파일을 포함한 알파 버전이며, 위 미검증 항목까지 완료한 배포용 완제품은 아닙니다.

## Windows 설치 패키지 구성 검증 (2026-09-24)

- 공식 CPython embeddable 3.12.10과 Windows x64 바이너리 wheel을 묶었습니다.
- Windows GUI용 PE 실행 파일을 교차 컴파일하고 NSIS 오프라인 설치 파일을 생성했습니다.
- Qt/Python/PDF 런타임의 DLL 의존성을 정적으로 검사했습니다.
- 내장 OCR 경로로 15개 문서 시험과 UI 통합 시험을 다시 통과했습니다.
- 한국어 샘플에서 문자 추출과 투명 문자층 생성 확인. 인식 정확도를 보증하는 시험은 아닙니다.
- Windows 실기기에서 설치·실행·GPU·제거 시험은 하지 않았습니다.

# 0.2.0 검증 기록 · 2026-09-25

기존 문서 시험 15개와 읽기·인쇄 권한/좌표 시험 4개, Qt 실제 포인터 UI 시험 두 묶음 통과.

- 읽기: 수평으로만 드래그, 역방향, 여러 줄, 90도 회전 글자 선택과 Ctrl+C.
- 링크: 기본 브라우저 호출의 URL 확인(실제 브라우저 실행은 mock), 문서 내 이동,
  링크 드래그 시 실행 방지, 페이지 재배열 후 링크 대상 유지, 회전 좌표.
- 휠: -120과 -1200 입력에서 1:10 이동량, -6 입력 20회의 누적, pixelDelta 우선,
  Ctrl+휠 확대. Qt 6.8은 ScrollUpdate의 각도 0 이벤트를 호환 이벤트로 버리므로
  실제 터치패드 형태의 각도+pixelDelta 이벤트로 검증했습니다.
- 인쇄: 같은 QPrinter/QPainter 파이프라인을 PDF 출력으로 실행. 2–3쪽 범위 출력이
  두 장인지, 회전·일반 페이지 모두 빈 출력이 아닌지 확인. 취소 시 진행 중단,
  원본 미변경. 문서의 인쇄 금지와 150dpi 제한 확인.
- 현재 보는 스캔 페이지 자동 OCR(한국어+영어 엔진) 후 문자층 갱신 확인.
- 기존 썸네일 드래그·다중 선택, 본문 교체·저장·다시 열기, 검색,
  실행 취소·다시 실행, OCR와 준비 중 취소 회귀 시험 통과.
- 읽기·편집 화면 캡처를 직접 확인.
- Windows Qt6PrintSupport.dll에 WINSPOOL/COMDLG32 프린터 API 의존성과
  네이티브 Windows 인쇄 구현이 포함됨을 정적으로 확인.
- x64 GUI 실행기 버전 0.2.0 재컴파일. NSIS 현재 사용자 설치와 바탕화면·시작 메뉴의
  '비책 PDF' 바로가기 생성 스크립트 업데이트.

실물 프린터, Logitech 무한 휠, Windows 설치·바로가기 실행 및 GPU는 이 Linux 환경에서
실기기 시험하지 않았습니다. 현재 선택은 한 페이지 안이며, 인쇄는 최대 300dpi 래스터입니다.

# 0.3.0 검증 기록 · 2026-09-25

## 미리보기·성능

- 캐시 적중 시 현재 페이지 이미지 URI를 다시 연결. 예전 해상도의 이미지가 제거된 상태에서
  이미 캐시된 다른 해상도로 돌아왔을 때 빈 화면이 남는 경로를 재현한 회귀 시험 통과.
- 썸네일의 실제 가로·세로 페이지 비율과 화면 배율에 맞는 해상도 확인.
- PNG 압축/해제 대신 GUI 소유 공유 메모리 슬롯 2개를 사용. 창 종료 시 worker를 종료한 후 해제.
- MuPDF 디스플레이 리스트 8쪽 재사용, 본문 512MiB 기본 / 최대 1GiB 선택,
  썸네일 64MiB 별도 캐시. 이미지 완료 신호는 해당 페이지에만 전달.
- 샘플 일반/스캔 페이지의 1600/3000픽셀 렌더·IPC·QImage 변환 구간 비교:
  `benchmarks/transport-results.json` 및 `benchmarks/README.md` 참조.
- 현재 화면을 먼저 그리고 근처 페이지를 미리 준비. 지나간 페이지의 대기 요청을 취소하며
  진행 중 작업은 2개 이내로 제한.
- 기존 휠 입력 파일(`ui/ScrollInput.qml`)은 0.2.0과 동일.

## PDF 결합

- 2개 이상의 PDF 추가, 순서 변경, 미리보기·페이지 수 표시, 새 PDF 출력.
- 실제 출력의 페이지 순서, 내부 링크 대상, 웹 링크, 메모, 같은 이름의 양식 필드,
  책갈피 위치와 원본 바이트 유지 확인.
- 독립 도구로 만든 AES-256 시험 PDF에서 암호 요청·권한 제한·소유자 암호 결합 확인.
- 원본 덮어쓰기 거부, 취소·잘못된 입력 시 기존 출력 보존.
- QML 결합 창에서 파일 검사→재정렬→8페이지 PDF 저장 과정 검증.
- 현재 열린 문서의 저장하지 않은 편집을 스냅샷으로 결합. 원본과 미저장 상태 유지 확인.
- 파일 드롭에 사용하는 QUrl과 일반 문자열 경로 모두 확인.

문서 시험 총 23개 및 UI 시험 3개 묶음. Windows 실기기/GPU/실물 프린터/특정 사용자 PDF는 미검증.
암호화·결합은 PDF를 새로 구성하므로 출력의 전자서명 검증 상태를 보존하지 않습니다.


# 0.4.0 검증 기록 · 2026-09-25

## 검색 위치 이동

- 실제 QML 창에서 Enter / Shift+Enter / F3, 검색 결과 클릭 및 끝에서 처음으로 이동 확인.
- 120쪽, 서로 다른 페이지 크기의 PDF에서 38·81·120쪽 검색어를 화면 안의 정확한 위치까지 이동.
- 한 페이지 안의 서로 다른 일치 항목을 차례대로 이동. 활성 결과와 다른 결과를 구분해 표시.
- 검색 도중 탭 변경 시 결과·이동 요청이 다른 문서로 넘어가지 않음.
- 편집으로 검색 결과를 갱신할 때 이전 결과에 가까운 강조 위치를 복원.

## 여러 문서·수명 관리

- 실제 QML에서 20개 파일, 총 2,284쪽을 동시에 열고 빠르게 탭 전환.
- 전체 탭이 PDF worker 1개 / GUI 소유 공유 프레임 2개를 사용하는지 객체와 PID 확인.
- 이미지 캐시가 모든 탭의 512MiB + 64MiB 예산 안에 있는지 확인. 이 수치는 전체 프로세스 메모리의 상한이나 모든 PDF에 대한 성능 보장은 아님.
- 비활성 탭은 페이지 렌더 대기 요청과 문자 좌표 캐시를 해제. 종료 탭의 진행 중 프레임 응답은 슬롯 해제까지 처리한 뒤 QObject 폐기.
- 탭별 확대율·스크롤 위치·검색어, 편집 내용, 실행 취소·다시 실행 유지.
- 편집 요청 직후 다른 탭으로 전환하고 각 문서를 실제 PDF로 저장·재개방해 내용 격리 확인.
- 이미 열린 경로는 기존 탭 활성화. Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+W와 20개 항목의 열린 문서 목록 확인.
- 저장하지 않은 탭의 취소, 저장 실패 후 편집 유지, 저장 성공 후 닫기 확인.
- 렌더·검색 도중 탭 닫기, 최초 컨트롤러 탭과 마지막 탭 닫기, 빈 탭에서 재개방 확인.
- 앱 종료 시 숨겨진 탭의 편집을 확인하고 저장. 취소 시 모든 탭 유지.
- QML ReferenceError / TypeError / 파일 위치가 포함된 경고 없음. 실제 탭·검색 화면 캡처 확인.

## 회귀 시험·패키징

- 문서/결합/권한 단위·통합 시험 23개 통과.
- 기존 UI 시험: 본문 교체·저장, 썸네일 드래그·다중 선택, 실행 취소·OCR 취소.
- 읽기 시험: 문자 선택·복사, 회전 좌표, 외부·내부 링크, 인쇄 범위·취소, 한국어/영어 자동 OCR.
- 휠 시험: 1:10 입력량, 작은 각도 누적, pixelDelta 우선, Ctrl+휠 확대. 계산식은 그대로 유지하고 활성 문서 컨트롤러 전달만 추가.
- 결합 시험: 혼합 페이지 비율, 공유 프레임·캐시 재연결, 파일 검사·순서 변경, 미저장 편집을 포함한 결합.
- Windows x64 GUI 실행기 및 NSIS 설치 파일 0.4.0. 소스와 런타임/OCR/라이선스 포함.

Windows 설치·실행, Windows GPU, 실물 프린터와 사용자의 실제 PDF에 대한 기기 검증은 아직 하지 않았습니다.
테스트 스크립트: `scripts/qa_tabs.py`, `scripts/qa_ui.py`, `scripts/qa_reader.py`, `scripts/qa_upgrade.py`.


# 0.5.0 검증 기록 · 2026-09-25

- 주석 단위·통합 시험 4개 추가: 표준 객체/한글/답글/비평면화, 독립 writer 주석 유지,
  주석 전용 권한/잠금/검토 상태 보호, 오래된 수정 대상 차단/색 변경/저장 후 핸들 무효화.
- 본문 수정·OCR·결합·권한 회귀를 포함한 전체 시험 27개.
- 실제 QML에서 여러 줄 드래그 형광펜, 선택 후 밑줄·취소선, 위치 클릭 메모, 작성자·댓글 수정,
  답글 추가, PDF 저장, 다른 탭의 외부 주석 편집, 삭제/실행 취소, 본문 주석 클릭 확인.
- 텍스트 본문 content stream은 주석 전후 동일. annotation /AP, /NM, /IRT 및 /RT /R 등은 pypdf로 독립 확인.
- 외부 형식 fixture는 pypdf로 직접 제작한 합성 PDF이며 Acrobat에서 생성했다는 의미가 아님.
- 별도 엔진 Poppler에서 렌더링. 샘플 PDF의 글꼴을 임베드하여 시스템 대체 글꼴 차이를 제거.
- 읽기/선택/링크/휠/인쇄/자동 OCR, 결합, 20개 탭/검색/저장·닫기 기존 시험 수행.
- 잘못된 색상으로 적용 실패를 발생시켜 입력한 주석 초안이 유지되는지 확인. 주석 편집 창이 열리면 자동 OCR 시작을 억제.
- Windows x64 GUI 실행기와 설치 프로그램 0.5.0. 실제 앱 캡처와 주석 샘플 PDF 포함.

Windows와 Adobe Acrobat/Reader 실기기 실행은 미검증. 지원 범위와 왕복 확인 절차는
`docs/ANNOTATION_COMPATIBILITY.md` 참조. 지원하지 않는 주석은 읽기 전용으로 유지.

# 0.5.1 설치 오류 수정 · 2026-09-25

- 사용자 오류 화면: 기존 `runtime/_bz2.pyd`를 설치 중 열 수 없음.
  실행 중인 런타임에 대한 덮어쓰기가 가능한 기존 설치 구조를 확인했다.
  해당 사용자 PC의 실제 파일 잠금 주체나 접근 권한을 원격으로 확인한 것은 아니다.
- NSIS는 매번 별도 버전 폴더에 전체 파일을 설치하고 마지막에 실행 경로를 교체한다.
  같은 버전의 재설치도 새 폴더를 예약한다. 이전 앱·런타임 폴더는 설치 중 변경하지 않는다.
- 필수 파일 건너뛰기를 금지하고 활성화 전 실패 시 새 폴더만 정리한다.
  설치 작업의 중복 실행을 막고 바로가기는 고정된 루트 실행기를 사용한다.
- 기존 PDF 엔진/읽기/결합/주석 테스트 27개 통과. 새 실제 C 실행기 제어 흐름 테스트 1개 통과.
  새 테스트는 Win32 API를 대역으로 제공하며 한글·공백 경로, 인수 보존, 버전/기존 설치 선택,
  잘못된 선택 파일과 실행 실패를 다룬다. Windows 실행 테스트라고 주장하지 않는다.
- Windows x64 GUI 실행기 0.5.1과 NSIS 설치 프로그램을 빌드하고 압축 해제해
  앱·OCR·런타임 파일과 소스 ZIP을 비교하며 NSIS CRC 및 PE 버전·아키텍처를 확인한다.
- Windows 실기기 설치/실행, DLL 잠금, 취소·롤백, 제거는 미검증이다.
  확인 절차는 `packaging/CROSS_BUILD.md`에 명시했다.
- 앱의 PDF 기능과 휠 처리 코드는 버전 표시를 제외하고 0.5.0과 같다.

# 윤DF 0.6.0 · 슬라이드 쇼와 키보드 페이지 이동 · 2026-09-25

- 제품 이름을 윤DF / YoonDF로 변경했다. 창 제목·기본 문서명·상단 브랜드·인쇄 창·정보 창·
  PDF 결합 메타데이터·PE 제품 정보·설치 이름·바탕 화면/시작 메뉴 바로가기를 변경했다.
  기존 설정 및 설치 탐색 식별자는 유지하고 이전 실행 파일 경로의 호환 실행기를 제공한다.
- F5/F11/Ctrl+L로 현재 페이지부터 전체 화면 슬라이드 쇼 시작, Esc 또는 같은 키로 종료.
  페이지 전체 맞춤, 좌/우 마우스 클릭, 한 장 단위 휠, 자동으로 숨는 이동 도구와 커서,
  문서 내/외부 링크를 지원한다. 인접 두 페이지를 기존 전역 캐시 안에서 미리 그린다.
- 일반 읽기와 슬라이드 쇼에서 방향키·Page Up/Down·Space/Shift+Space로 한 장씩 이동,
  Home/End 및 Ctrl+Home/End로 처음/끝 이동. 범위 밖으로 넘어가거나 순환하지 않는다.
- 입력 필드와 대화상자는 글 편집 키를 유지한다. 슬라이드 쇼 중 탭/편집 단축키는 멈추고
  자동 OCR 시작 및 진행 중 검색의 자동 페이지 이동을 막는다.
- 종료 후 원래 창 상태·확대율·사이드바·편집 모드를 복원한다. 넘기지 않았으면 기존 페이지
  내 위치, 넘겼으면 마지막 표시 페이지 상단을 복원한다.

검증:

- `python -m unittest discover -s tests -v`: 28개 통과.
- `scripts/qa_presentation.py`: 실제 QTest 키/클릭/휠 이벤트. 일반 페이지 이동, 연속 입력,
  경계, 검색/페이지 번호/주석 입력 보호, 모달 상태에서 F5 차단, 세로/가로/회전 페이지 맞춤,
  전체 화면의 UI 숨김, 일반/최대화 창 복원, 위치/확대/패널/편집 블록 복원, 링크,
  분할/다중 휠 입력, 검색/자동 OCR 간섭 방지, 빈 문서 방어. QML 경고 없음.
- `scripts/qa_reader.py`: 문자 선택/복사·문서 링크·무한 휠·인쇄·한국어/영어 자동 OCR 통과.
- `scripts/qa_annotations.py`: 표준 주석 생성/수정/답글/저장, 외부 주석 유지, 탭 격리,
  실패 시 초안 유지·독립 파서/Poppler 검사 통과. QML 경고 없음.
- `scripts/qa_tabs.py`: 개발 중 새 페이지 이동 경로의 검색 위치·탭별 상태 및 편집 격리,
  20개 문서 / 2,284페이지, 하나의 엔진·두 공유 프레임, 저장 실패와 종료 처리 통과.
- 실제 UI를 `docs/reader.png`, `docs/presentation.png`로 캡처했다.
- Windows x64 GUI 실행기·NSIS 설치기를 교차 빌드하고 CRC, PE 아키텍처/버전,
  추출한 전체 페이로드와 소스 ZIP의 일치를 확인한다.

UI 검증은 Linux Qt offscreen 소프트웨어 렌더링 환경이다. Windows 실기기의 설치,
전체 화면 전환, 다중 모니터/DPI, D3D11 및 실제 프린터는 아직 검증하지 않았다.


# 0.6.1 PDF 연결 프로그램 등록 수정 · 2026-09-25

- 배포용 NSIS 설치 파일에 빠져 있던 현재 사용자 PDF 앱 등록을 추가했다.
  Applications/YoonDF.exe, SupportedTypes, YoonDF.PDF, OpenWithProgids,
  Capabilities/FileAssociations, RegisteredApplications 및 App Paths를 사용한다.
- 실행 명령은 버전 폴더가 아닌 루트 YoonDF.exe를 사용하며 실행 파일과 %1을 각각 인용한다.
  제거 시 윤DF 소유 등록만 제거한다. .pdf 기본값이나 UserChoice는 쓰지 않는다.
- 설치 완료 화면에 선택형 Windows 기본 앱 설정 열기를 추가했다.
  앱의 설정 버튼도 Windows 10/11 공통 ms-settings:defaultapps를 사용한다.
- scripts/qa_settings.py: 실제 QML에서 1000×640/1320×900 설정 창 크기,
  Windows용 버튼 클릭 → 대화상자 닫힘 → 설정 URI 전달, 실패 시 수동 안내,
  비 Windows 호출 차단과 QML 경고 없음 확인. OS 호출은 mock이며 Windows 실행 검증이 아니다.
- 네이티브 실행기 회귀 시험: 한글·공백·여러 파일 인수, 버전별 실행 경로,
  기존 설치 경로, 손상된 버전 정보와 런타임 오류 처리를 확인했다.
- Windows x64 GUI 실행기 0.6.1 및 NSIS 컴파일, 설치 파일 CRC와 추출 파일/소스 일치 확인.
  읽기 모드 ScrollInput.qml은 0.5.0과 바이트 동일하다.

Windows 실제 ‘연결 프로그램’/기본 앱 목록, PDF 더블클릭 및 설치/제거 동작은
이 Linux 환경에서 실행하지 못했다. 대체 Inno Setup 스크립트는 같은 등록 구조로
갱신했지만 이번 배포는 NSIS이며 Inno 빌드는 실행하지 않았다.


# 0.6.2 외부 PDF를 기존 창의 탭으로 열기 · 2026-09-25

- 새 실행은 Qt/화면/PDF 엔진을 만들기 전에 현재 사용자의 실행 중인 리더에 파일을 전달한다.
  Windows는 로그인 세션별 named mutex, Linux 검증은 flock으로 리더 하나를 선출한다.
  완성된 JSON 요청만 atomic rename으로 공개하고, 접수 확인 후 전달 프로세스가 종료한다.
  파일 경로는 절대 경로·한글·공백을 보존한다. 네트워크 포트를 열지 않는다.
- tests/test_instance.py: 8개 프로세스 동시 시작에서 리더 하나와 모든 파일 전달,
  강제 종료 후 남은 owner 정보가 있어도 재시작, 종료 중 대기 요청의 새 리더 인계,
  잘못된 요청과 상대 경로 차단. 실제 별도 프로세스로 Linux 잠금/파일 전달 검증.
- scripts/qa_startup.py: 실제 app.run의 최초 실행 → 두 파일을 두 탭으로 열기 → 종료 후
  소유권 정보 해제. PDF 작업 프로세스는 하나.
- scripts/qa_external_open.py: 실제 main.py를 별도 프로세스로 실행해 기존 QML 창에 전달.
  새 탭, 같은 파일의 기존 탭 활성화, 미저장 편집 유지, 최소화 전 일반/최대화 상태 복원,
  파일 없는 바로가기 재실행, QML 주석 초안·네이티브 대화상자 중 열기 지연,
  대기 요청이 있을 때 창 닫기 방지, 슬라이드 쇼 종료 후 새 탭, 동시 5개 실행,
  종료 확인 취소 후 다중 파일 전달 확인. 12개 탭에서도 리더 창/PDF 엔진 각 하나.
- 전체 단위·통합 시험 32개 통과. 기존 qa_tabs.py도 통과:
  20개 파일/2,284페이지, 두 공유 프레임, 독립 검색/편집/저장/실행 취소,
  숨은 탭의 저장 확인, 실패한 저장과 닫기 취소, QML 객체 정리.
- Windows x64 GUI 실행기·NSIS 0.6.2, 설치 파일 CRC와 추출 payload/소스 ZIP 일치 확인.
  ScrollInput.qml은 기존 정상 작동 버전과 바이트 동일하다.

Windows 실제 named mutex, 탐색기 더블클릭, 전경 활성화와 설치/업데이트 실행은 미검증이다.
최소화/최대화와 탭 동작은 Linux Qt offscreen으로 확인했으며 Windows 하드웨어 검증을
대신하지 않는다. 0.6.1 이하에는 전달 수신부가 없으므로 업데이트 후 기존 창을 닫고 다시 실행해야 한다.

## 0.7.0 editing, tabs and facing pages (2026-09-26)

- Reproduced the reported 0.6.2 tab mismatch with the original release: visible
  ListView currentIndex 0 while Documents.activeIndex was 1. The new incremental
  QAbstractListModel preserves a real mouse press through 12 state updates; mouse
  release, rapid tab switching, and selected-tab styling agree with the document.
- 37 unit/integration tests pass. New tests save/reopen replacement text with the
  original embedded font and an explicitly selected font, reject missing glyphs
  without changing the PDF, extract inline/duplicate/rotated raster images at native
  resolution including alpha, enforce copy restrictions and stale-document guards,
  and verify image insertion/undo/redo/save.
- `qa_editor_release.py` runs the real QML UI with QtTest pointer/key events. It
  verifies two-page layout (including mixed page sizes and an odd last page),
  spread keys, right-page search coordinates, per-tab view settings, slideshow
  return, independent highlight and memo context actions, clipboard image pixels,
  atomic PNG export and immediate picker-driven insertion. It also verifies original
  font retention, draft preservation after a missing-glyph error, and successful
  Korean replacement after explicit font selection. Saved PDF annotations are
  three Highlight objects and one separate Text object.
- The native-window close event closes only the active tab while another remains.
  Cancel preserves the tab; Save writes before closing it. Ctrl+Shift+Q checks
  hidden dirty tabs and cancels or completes whole-application exit correctly.
- Existing `qa_tabs.py`, `qa_reader.py`, `qa_annotations.py`, `qa_presentation.py`
  and `qa_external_open.py` pass with no QML errors. These cover 20 files/2,284
  pages in one PDF worker, actual PDF edits, selection, printing, OCR, annotation
  round trips, presentation keys/links/position restoration, and subprocess file
  handoff into a single reader. The presentation geometry assertion now uses
  actual viewport coordinates, independent of the new spread container hierarchy.
- `ui/ScrollInput.qml` is byte-identical to the verified 0.5.0 release. Infinite
  wheel, fractional inputs, pixel scroll and Ctrl zoom retain their passing checks.
- Linux QA uses Qt 6.8.3 offscreen/software rendering and PyMuPDF 1.26.6. Windows
  native execution, actual Adobe Reader interaction and hardware GPU behavior
  remain untested here. Original-font reuse requires a matching usable font program
  with the required glyphs; complex mixed-font layout remains an explicit choice.


# 윤DF 0.8.0 · 페이지 위 직접 편집과 객체 이동 · 2026-09-26

- 메모 편집기를 중앙 모달에서 PDF 옆의 고정 폭 패널로 이동했다. 페이지 영역은 패널 옆으로 줄어들며 두 페이지 보기와 스크롤을 유지한다. 작성 중 파일 드롭·탭 전환·OCR·다른 편집을 막아 초안을 보호한다.
- 본문에서 주석을 우클릭하면 해당 주석을 지운다. 기존 표준 PDF 주석/답글 삭제 및 권한·잠금 보호를 사용한다.
- 본문 편집은 페이지 좌표의 TextArea와 위쪽 서식 도구줄로 바꾸었다. 원본·선택 글꼴을 Qt에도 등록하며 페이지가 화면 밖으로 사라져도 초안은 별도 세션에 유지한다. 적용 실패 시 초안 보존.
- 삽입 이미지의 네이티브 Form XObject를 이동·배율 변경한다. 복제 페이지의 리소스는 분리하여 다른 페이지를 바꾸지 않는다. 이전 버전의 독립 이미지 스트림은 첫 이동 시 전환한다. 이미지 객체 식별용 문자열이 xref_copy에서 소실되는 PyMuPDF 1.26.6 동작을 회피한다.
- Text 메모 아이콘은 글자와 별개로 드래그한다. /Rect만 좌표 변환해 옮겨 NoRotate 아이콘의 회전 페이지 오차를 방지하고 /Contents, /NM, /IRT와 답글을 유지한다. 새 메모를 적용하면 바로 아이콘을 옮길 수 있는 읽기 도구로 돌아간다.
- Ctrl/Shift 선택 썸네일을 한 그룹으로 이동하며 한 번의 실행 취소로 복원한다. PDF의 page xref를 유지해 링크와 책갈피의 대상이 이동한 페이지를 따라간다. 두 페이지 보기의 썸네일 수 오류를 수정했다.

검증 환경: Linux, Python 3.12, PySide6 Essentials 6.8.3, PyMuPDF 1.26.6,
Qt Quick offscreen/software. Windows 실기기 시험을 대체하지 않는다.

- 전체 단위·통합 시험 42개 통과. 새 5개 시험은 이미지 이동/크기/저장 재개방/본문 수정 뒤 재이동/실행 취소, 0·90·180·270도 회전, CropBox, 이전 버전 이미지, 복제 페이지 리소스 격리, 메모/답글/회전/실행 취소, 다중 페이지 순서와 링크·목차 보존을 검사한다.
- `scripts/qa_direct_editing.py`: 실제 포인터와 키 이벤트로 두 페이지 옆 메모 패널, 메모 초안 중 스크롤, 오른쪽 페이지의 마커 이동과 실행 취소/다시 실행, 본문 우클릭 형광펜 삭제, 오른쪽 페이지 직접 입력, 페이지 이동 중 초안 보존과 원본 글꼴, 삽입 이미지 이동/모서리 크기 조절, Ctrl/Shift 썸네일 선택과 여러 장 드래그를 검증했다. 저장한 PDF의 본문·이미지 좌표·메모·페이지 순서를 다시 검사했다. QML 경고 없음.
- `scripts/qa_editor_release.py`: 실제 탭 클릭, 두 페이지 배치/검색/키 이동, 각주와 형광펜 분리, 원본 화소 복사/저장/삽입, 원본 글꼴·부족한 글리프 초안 보존·선택 한글 글꼴, 저장/취소/현재 탭 닫기 통과.
- `scripts/qa_annotations.py`: 주석·답글·외부 PDF·탭 격리·삭제/복원과 독립 파서/Poppler 렌더 검사 통과.
- `scripts/qa_external_open.py`: 실제 두 번째 실행의 탭 전달, 중복 문서 미저장 내용 유지, 최소화 복원, 주석 초안 중 열기 요청 대기 통과.
- `scripts/qa_presentation.py`: 슬라이드 쇼와 입력 중 키 보호, 문서 복귀 통과.
- 실제 UI 캡처 `docs/note-sidebar-080.png`, `docs/inline-text-080.png`, `docs/image-move-080.png`를 확인했다.

Windows 설치·실행·GPU, 실제 Acrobat 왕복 편집과 사용자 원본 PDF는 이 환경에서 시험하지 않았다.

- `scripts/qa_tabs.py`: 20개 파일/2,284쪽, 검색 위치, 빠른 탭 전환, 편집 격리와 저장/닫기 통과.
- `scripts/qa_reader.py`: 읽기 선택·링크, 10배/분할/pixel 휠, 인쇄 범위·취소, 한국어/영어 자동 OCR 통과.


# 윤DF 0.9.0 · 원본 글꼴과 실시간 조판 · 2026-09-26

- 원본 부분 글꼴의 Unicode cmap이 없는 한글 PDF를 만들어 재현했다. PDF의 ToUnicode/CIDToGIDMap 또는 안전하게 식별한 trace 정보로 문자표만 복구하며, glyf 윤곽 바이트가 동일함을 확인했다. 포함되지 않은 새 글자는 복구한 것으로 간주하지 않는다.
- 원본 글꼴 프로그램을 우선 사용하고 정확히 같은 이름의 설치 글꼴로만 자동 재시도한다. 한글 이름을 Unicode로 정규화하고 TTC/OTC 개별 face와 localized alias를 검색한다. PDF CFF는 원래 CharStrings를 포함하는 OpenType으로 감싸 화면과 PDF에 사용한다.
- 원본 span의 서체·크기·색·굵게·기울임 정보를 유지한 QTextDocument를 화면에 연결하고 그 문서 자체를 QPdfWriter로 출력한다. 줄을 늘리거나 폭을 바꿨을 때 화면 레이아웃과 저장 PDF의 각 줄 baseline이 0.01pt 이내로 일치한다. 원본 이미지/선은 유지하고 대상 텍스트만 교체하며 실행 취소할 수 있다.
- 입력 중 자동 높이, 폭 손잡이, 페이지 넘침/본문 겹침 안내, 글꼴 오류 시 초안 보존을 확인했다. 실패한 글꼴 선택으로 이전 서체가 조용히 저장되지 않도록 적용을 막는다. 페이지 밖으로 나가는 입력도 적용하지 않는다.
- 같은 본문을 적용한 뒤 다시 여는 과정에서 Qt가 이전 외부 QTextDocument를 참조하는 문제를 재현했다. 살아 있는 QML 뷰를 먼저 분리한 뒤 문서를 교체하도록 수정했고 반복 편집을 통과했다.

검증: Linux, Python 3.12, Qt/PySide6 6.8.3 offscreen/software, PyMuPDF 1.26.6, fontTools 4.61.1.

- `pytest -q`: 전체 46개 단위/통합 시험 통과. 부분 글꼴 복구, 혼합 bold/italic, 실시간 줄 위치와 저장 PDF 일치, 글리프 부족과 복구, 무변경 적용, 한글 이름과 TTC face를 포함한다.
- `scripts/qa_font_editing.py`: 실제 본문 클릭, IME commit으로 한글 입력, 부족한 글자 안내와 초안 유지, 전체 한글 글꼴 선택, 검색 목록에서 한글 파일명 검색/선택, Escape로 검색만 닫기, 입력 시 높이 확장과 폭 변경 줄바꿈, 저장 후 내용 재추출 통과.
- `scripts/qa_editor_release.py`: 실제 탭 클릭, 두 페이지 보기/검색/슬라이드 쇼, 형광펜과 메모 분리, 이미지 복사/저장/삽입, 원본 서체 적용 후 같은 본문 재편집, 글리프 오류 후 한글 글꼴 선택, 저장/취소/탭 닫기 통과.
- `scripts/qa_direct_editing.py`: 두 페이지 옆 메모와 드래그 마커/답글, 우클릭 삭제, 페이지를 벗어난 본문 초안, 삽입 이미지 이동/크기, Ctrl/Shift 다중 페이지 드래그와 저장 순서 통과. 위 세 UI 시험에 QML 오류 없음. 일부 Qt 생성 글꼴의 과거 생성일에 대한 fontTools 로그는 편집/저장 결과에 영향을 주지 않는다.
- 실제 UI 캡처: `docs/font-search-090.png`, `docs/live-text-090.png`.

현재는 선택한 블록 안의 줄바꿈이며 다른 문단/페이지를 자동으로 밀어내지 않는다.
복잡한 원본 자간과 조판, 세로쓰기, 없는 글리프의 재생성은 보장하지 않는다.
Windows 설치/실행, 네이티브 IME·DPI·GPU, 실제 Acrobat 왕복, 사용자 스크린샷의 원본 PDF는 미검증이다.


# 윤DF 0.9.1 · 원본과 편집 시작 배치 비교 · 2026-09-26

이번 검증은 편집 화면과 출력 조각만 비교하던 0.9.0의 부족한 기준을 보완한다.

- rawdict의 각 글자 origin과 줄 기준선을 보존하여 Qt의 글자 간격, 줄별 들여쓰기, 고정 줄 간격에 적용한다. 복구한 서체에서 새로 계산한 기본 간격으로 원본을 대체하지 않는다.
- 시험 PDF의 서로 다른 들여쓰기와 1.8pt 자간을 그대로 가져왔다. 원본과 편집 시작 시 모든 글자 origin을 0.08pt 이내로 비교하고, 실제 한 글자 수정 후 저장한 PDF를 다시 열어 나머지 좌표와 주변 문장 보존을 검사한다.
- QPdfWriter의 정수 MediaBox와 소수점 편집 영역 사이 배율 차이를 재현했다. MediaBox를 바깥쪽으로 반올림하고 실제 크기의 clip을 사용해 삽입하며, 저장 후 가로 글자 위치가 늘어나는 문제를 없앴다.
- Qt가 줄 끝의 자간까지 줄바꿈 폭에 포함하는 차이를 처리했다. 마지막 글자 교체 시 같은 폭의 단어가 불필요하게 다음 줄로 밀리는 사례를 시험한다. 글자 크기 변경 시 줄 간격과 자간도 비례 변경한다.
- `scripts/qa_font_editing.py`는 실제 QML에 연결된 두 줄 한글 부분 글꼴 문서에서 입력 전 각 글자의 위치를 원본과 0.08pt 이내로 비교한다. 이후 실제 IME 입력, 없는 글자의 안내와 초안 보존, 전체 글꼴 선택, 한글 서체 검색, 폭/높이 변경, 저장 재개방을 확인한다.
- `scripts/qa_editor_release.py`, `scripts/qa_direct_editing.py`로 반복 본문 편집, 원본 서체, 두 페이지 보기, 탭, 주석/메모 이동, 이미지 이동, 다중 페이지 순서와 저장/닫기 동작을 확인한다.

검증 환경은 Linux, Qt 6.8.3 offscreen/software, PyMuPDF 1.26.6이다.
단위·통합 시험 47개 및 위 세 UI 회귀 스크립트가 통과했다.
화면 증거: `docs/original-layout-091.png`, `docs/live-text-091.png`, `docs/font-search-091.png`.

이 비교 결과는 구성한 시험 문서에 대한 것이며 사용자 스크린샷의 실제 PDF는 받지 못했다.
Windows 실행/설치, 실제 Acrobat 왕복, 세로쓰기·가로 배율·복합 기준선 조판을 확인한 것으로 해석하지 않는다.
소스/설치 파일은 0.9.1로 함께 배포하며 기존 휠 입력 코드는 0.9.0과 바이트 동일하다.


# 윤DF 0.9.2 · 글꼴 대기 복구와 편집 중 닫기 · 2026-09-26

- 0.9.1의 글꼴 완료 콜백에서 편집 문서 구성 예외를 주입하자 로딩 안내가 남는 경로를 재현했다. 예외·오래된 응답·시간 초과에 종료 상태를 설정하고 재시도를 제공한다. 사용자 PDF가 없어 실제 사용자 멈춤의 원인이 같다고 확정하지 않는다.
- 글꼴 해석·부분 글꼴 복구·설치 글꼴 탐색은 별도 제한 시간 프로세스로 분리했다. 실제 자식 프로세스를 오래 대기시켜 제한 시간에 종료·회수되고 다음 작업이 가능한지 시험했다. GUI의 Qt 네이티브 글꼴 등록이나 원본 PDF 해석 중 가능한 모든 멈춤을 검증한 것은 아니다.
- 새 한글 ‘마지막’과 IME 미완성 ‘막’을 입력한다. 원본 부분 글꼴에 없는 문자의 미리보기에서 글리프 0이 없는지 확인하고, 사용자 선택으로 없는 문자만 내장 글꼴을 적용한 뒤 저장 PDF에서 글자를 추출한다. 기존 문자의 원본 글꼴은 유지한다.
- 실제 QML 창 닫기에서 계속 편집, 적용 후 저장·현재 탭 닫기, 글꼴 응답 지연 중 입력 버리고 마지막 창 닫기를 시험했다. 닫기 시 원문과 이전에 적용한 편집의 저장 확인을 유지한다.
- 앱 종료 신호가 진행 중인 글꼴 작업에 전달되며, 제한 시간을 기다리지 않고 해당 자식 프로세스를 종료·회수한다. 실제 대기 중인 자식 프로세스로 취소와 회수를 시험했다.
- 실제 실행기는 runtime/YoonDF.exe를 호출한다. 새 C 호스트의 Unicode DLL 경로, Python -c/multiprocessing 인수, 종료 코드·실패 안내를 Win32 대역 시험으로 검증했다. Windows 작업 관리자 자체를 실행한 검증은 아니다.

Linux, Qt 6.8.3 offscreen/software, PyMuPDF 1.26.6에서 단위·통합 시험 **52개** 통과.
실제 UI 스크립트 `qa_font_editing.py`, `qa_recovery.py`, `qa_editor_release.py`,
`qa_direct_editing.py`, `qa_external_open.py` 통과. 외부 파일 열기 시험은 새 닫기 확인
화면에서 계속 편집을 선택하고 주석 초안을 유지하는 절차로 갱신했다. QML 오류 없음.
증거 화면: `docs/missing-glyph-092.png`, `docs/close-draft-092.png`.

Windows 설치·실행·작업 관리자 표시·네이티브 IME·GPU 및 사용자 원본 PDF는 미검증이다.
패키지 검사에서는 x64 GUI 실행기/호스트와 윤DF 파일 설명, DLL 진입점, NSIS CRC,
추출 파일 전체 및 소스 ZIP의 바이트 일치를 검사한다. 기존 휠 파일은 0.9.0과 동일하다.


# 윤DF 0.9.4 · 긴 문단 편집 안정화 · 2026-09-26

사용자 제공 0.9.3 소스와 응답 없음 화면을 검토했다. 실제 PDF와 Windows 덤프는 받지 않았다.
4px 입력 폭 충돌로 40줄 문단이 두 배 높이로 바뀌는 사례, 한글 없는 대체 글꼴 선택,
반복 글꼴 검사/서식 갱신과 엔진 종료 뒤 남는 요청을 수정했다. 조합 중 서식 변경을 보류한다.
단위·통합 68개, 실제 QML/IME 이벤트 8회 반복 편집·저장·재개방과 여섯 기존 UI 회귀 스크립트 통과.
원래 글자 좌표 비교와 저장 후 추출 검사를 유지했다. 조건·수치·미검증 범위는
`docs/EDITING_FIXES_094.md`와 `benchmarks/editing-094.json`에 기록했다.
Windows x64 실행기/호스트 및 NSIS 패키지 정적 검증과 실기기 실행 검증을 구분한다.


# 윤DF 0.9.15 · 손상된 개체가 있는 PDF의 주석 · 2026-09-27

사용자 화면: 보고서 PDF(『문화예술활동현황조사』 통계정보보고서, 91쪽)에서 제목을 드래그한 뒤
메모를 적용하자 "code=8: invalid key in dict" 오류가 나고 주석이 달리지 않았다. 원본 PDF는 받지 못했다.
어느 페이지도 쓰지 않는 깨진 개체 하나를 넣은 PDF로 같은 오류를 재현했다. 원인은 편집 직전에
만드는 실행 취소용 사본 저장(garbage=0)이 그 개체를 다시 읽다가 멈추는 것이었다.

- 저장이 실패하면 읽을 수 없는 개체를 null로(스트림은 빈 스트림으로) 바꾸고 다시 저장한다.
  MuPDF가 읽을 때 이미 그렇게 취급하므로 페이지 모양은 같다(주석을 뺀 렌더 픽셀 비교).
- 주석 키(NM, RT, RC, Rect)는 사전을 문자열로 바꿨다 되읽는 xref_set_key 대신 직접 쓴다.
- 망가진 주석 하나가 같은 페이지의 다른 주석과 글자 선택을 막지 않는다.
- 복사는 막혀 있고 주석은 허용된 PDF에서 글자 위치만 넘겨 형광펜·밑줄·메모를 남긴다(복사는 계속 차단).
- 글자를 선택하고 메모 버튼(또는 오른쪽 클릭)을 누르면 그 글자에 형광펜과 메모가 함께 달린다.

엔진 수준 시험 38가지 PDF(한글, 회전·자르기·원점 이동, 사용하지 않는/참조된/개체 스트림 안의 깨진 개체,
깨진 Info, 깨진 주석 참조, 스트림 길이 오류, 손상 이미지, 객체 스트림+xref 스트림, 증분 저장,
xref 손상·앞뒤 쓰레기 바이트, AES/RC4 암호와 권한 조합, 링크·양식·공유 주석·간접 Annots 배열,
이상한 기존 주석(NM 중복·없음, CMYK/회색 색, 홀수 QuadPoints, 없는 IRT, IRT 순환, Rect 없음),
상속된 회전, 태그 PDF, 300쪽, 아주 크거나 작은 페이지)에서 메모·표시 4종·수정·답글·이동·삭제·
실행 취소/다시 실행·저장·다시 열기를 모두 통과했다. `tests/test_annotation_robustness.py`에 대표 사례를 남겼다.
실제 QML 창에서 사용자의 순서(드래그 → 메모 버튼 → 입력 → 적용), 메모 버튼 후 클릭, 형광펜,
오른쪽 클릭 메모, 수정·답글·삭제·되돌리기, 저장을 손상 보고서·복사 금지 PDF·가로 페이지에서
확인했다(`scripts/qa_comment_flows.py`).


# 윤DF 0.9.16 · 흑백 미니멀 디자인과 새 로고 · 2026-09-27

- 화면 토큰(Theme.qml)을 검정·흰색·회색만으로 바꾸고, 그림자·둥근 모서리·원색 장식을 없앴다.
  주석 색 견본만 PDF에 들어가는 실제 색이라 남겼다.
- 글꼴: 나눔명조(원본 그대로), YoonDF Display·YoonDF Text(Playfair Display·Source Serif 4의
  정적 굵기, OFL 예약 이름 때문에 이름 변경), JetBrains Mono. 영문 글꼴의 한글은 나눔명조로 이어진다.
  중간 굵기(600)를 요청하면 한글이 보통 굵기로 대체되어 굵게는 700으로 통일했다.
- 로고와 아이콘은 `scripts/make_logo.py`로 글꼴 윤곽에서 그린다(SVG, PNG 7종, ICO).
- `scripts/qa_design.py`로 시작·읽기·주석·작성·편집 화면(밝게/어둡게)과 설정·오류·결합 창을 찍어
  확인했고 QML 경고가 없다. Windows 실기기의 글꼴 표시(ClearType)는 확인하지 못했다.
  증거 화면: `docs/monochrome-start-0916.png`, `docs/monochrome-comments-0916.png`, `docs/monochrome-dark-0916.png`.


# 윤DF 0.9.17 · 미리보기 앱 같은 디자인, 아메카지 색, 캐릭터 로고 · 2026-09-27

- 화면 토큰(Theme.qml)을 아메카지 색(인디고 데님, 가죽 브라운, 황동, 올리브, 에크루)으로 바꾸고,
  둥근 모서리와 부드러운 그림자, 짧은 이징 움직임을 넣었다. 그림자는 셰이더 없이 9분할 이미지
  (`scripts/make_shadows.py`)라 소프트웨어 렌더러에서도 그려진다.
- 새 부품: Segmented(흰 알약이 미끄러지는 분할 버튼), Shadow, 둥근 카드 Block.
- 글꼴은 Pretendard 1.3.9 원본(Regular·SemiBold·Bold). Linux Qt는 세 굵기를 한 가족으로 묶는다.
  Windows에서 SemiBold가 별도 가족으로 잡히면 600 요청은 가까운 굵기로 대체된다(미확인).
- 캐릭터: `art/character`의 원본에서 `scripts/make_character.py`로 배경을 걷어 내고(바닥 그림자,
  다리 사이 빈틈 포함) 털 가장자리의 흰 테두리를 지웠다. `scripts/make_logo.py`로 아이콘 8종과 ICO를 만든다.
- `scripts/qa_design.py`로 시작·읽기·주석·작성·편집(밝게/어둡게), 설정·오류·결합·정보 창을 찍어 확인했다.
  증거 화면: `docs/preview-start-0917.png`, `docs/preview-comments-0917.png`, `docs/preview-dark-0917.png`.


# 윤DF 0.9.18 · 손 흔드는 캐릭터와 흰 바탕 · 2026-09-27

- 캐릭터 그림을 `scripts/make_character.py`에서 팔꿈치 기준으로 몸통(`wave-body.png`)과
  아래팔(`wave-forearm.png`) 두 겹으로 나눴다. 두 겹이 팔꿈치의 둥근 관절을 함께 가지고 있어서
  아래팔을 돌려도 이음매가 벌어지지 않는다. 팔꿈치 위치는 스크립트가 출력한 비율(0.7569, 0.6167)을 쓴다.
- `ui/WavingCharacter.qml`: 폴짝 뛰며 아래팔을 들고(OutBack), 세 번 흔들며 몸을 ±1.5도 기울이고,
  제자리로 돌아온다(약 3초). 화면에 나타날 때와 누를 때 재생한다. 셰이더·동영상 없이 이미지 회전만 쓴다.
- `scripts/qa_design.py`에서 시작 캐릭터가 저절로 인사를 마치고 팔 각도·높이가 0으로 돌아오는지,
  누르면 다시 인사하는지 확인했다. 증거 화면: `test-output/design-start.png`, `design-start-wave.png`.
- `docs/wave.gif`는 같은 QML 애니메이션을 흰 바탕에서 40ms마다 찍어 공통 96색 팔레트로 저장했다.
- 밝은 화면 토큰: window·chrome·surface·raised·field를 `#ffffff`로, sidebar `#fafaf9`, canvas `#f1f1f0`.
  어두운 화면은 그대로다. Windows 실기기에서의 애니메이션 부드러움(GPU·고해상도 화면)은 확인하지 못했다.
- 실행 취소 사본 정리: `_purge_snapshots`가 사본 경로를 resolve()한 경로와만 비교해서, Windows 임시 폴더가
  8.3 짧은 이름(`RUNNER~1`)으로 잡히면 모든 사본을 지웠다. GitHub Actions Windows 빌드의
  `tests.test_document` 5건이 이 때문에 실패하고 있었다(run 36303058284 등). Linux에서 임시 폴더를
  심볼릭 링크로 두면 같은 5건이 똑같이 실패하는 것을 확인했고, 양쪽을 같은 방식으로 정규화한 뒤 통과한다.
  회귀 시험 `test_undo_when_the_temp_folder_has_two_names`는 수정 전 실패, 수정 후 통과.
- 단위 시험 90개, `scripts/qa_*.py` 21개 모두 통과(Linux, offscreen).


# 윤DF 0.9.19 · Y 로고 기준 화면 전면 개편과 절제된 움직임 · 2026-09-27

기준: `docs/design/YoonDF-UI-Redesign-Prompt.md`, `art/logo/YoonDF-Refined-Logo.png`.
PDF 엔진·편집·저장 로직, 작업 프로세스, 공개 API와 데이터 모델은 바꾸지 않았다(bridge에는
`reduceMotion` 설정 하나만 추가).

- 로고: 받은 PNG에서 타일(모서리 반경 폭의 22%)과 Y(팔 기울기 0.713/0.743, 줄기 폭, 홈 높이)를 재서
  `scripts/make_logo.py`가 벡터로 다시 그린다. `assets/logo/mark.svg`, 아이콘 10종, ICO(16–256).
  24px 이하는 타일을 꽉 채우고 Y를 키운다. 캐릭터 이미지는 앱에서 뺐다(원본은 `art/character`에 남김).
- 토큰(Theme.qml): 명세 색(흰색, 작업 영역 #F5F5F7, 잉크 #29313A, 보조 #62666C, 선 #E3E5E8,
  강조 #466985, 선택 바탕 #E3EAF0)과 어두운 테마 대응 색, 간격 4·8·12·16·24, 반경 6/10/12,
  글자 14/12–13/16, 움직임 시간. 그림자 이미지는 중성 잉크색으로 옅게 다시 만들었다.
- 새 부품: AppMenu·AppMenuItem·AppMenuSeparator(모든 메뉴), SidePanel(양쪽 패널), AppCheckBox.
- 화면 확인(`scripts/qa_design.py`, QML 경고 없음): 1320×900과 1000×640에서 시작·읽기·주석·
  메모 작성·편집·본문 수정 중(떠 있는 도구)·설정·오류·결합·정보, 밝게/어둡게. 1000×640에서
  도구줄 잘림 없음(집중 읽기·슬라이드 쇼·인쇄·페이지 보기가 ⋯로 이동). 떠 있는 본문 수정 도구가
  고치는 문단과 겹치지 않는지 좌표로 확인. 전후 비교: `docs/redesign-0919-compare.jpg`.
- 움직임 확인(`scripts/qa_motion.py`, 실제 창·실제 PDF):
  버튼을 누르면 내용 배율이 1보다 작아지고 클릭 영역 폭(32px)은 그대로, 명령은 클릭 즉시 실행.
  메뉴는 열리는 중 불투명도 0과 1 사이를 지나고, 닫히는 순간부터 입력을 받지 않으며 그 사이
  메뉴 밖 클릭(사이드바 버튼)은 정상 처리. 주석 패널은 여는 순간 폭을 차지하고 내용만 페이드,
  열고 닫을 때 페이지 영역 폭 변경은 각 1회. 같은 개폐에서 페이지 렌더 결과 수는 움직임을 켰을 때가
  동작 줄이기보다 많지 않았다(두 번 실행: 4 대 4, 4 대 6). 17ms 간격 12회 연속 개폐, 전환 중 Ctrl+S·탭 전환·동작 줄이기 전환 뒤 최종 상태 일치.
  본문 수정 중 사이드바·테마·동작 줄이기를 바꿔도 입력 글과 커서 위치 그대로.
- 실행 영상: `docs/motion.gif`(`scripts/record_motion.py`가 실제 창을 실시간으로 찍음, 8.8초).
- 단위 시험 90개, 기존 `scripts/qa_*.py` 20개와 새 `qa_motion.py` 모두 통과(Linux, offscreen,
  소프트웨어 렌더러).
- 확인하지 못한 것: Windows 실기기의 100%·125%·150% 배율에서 글자 잘림·클릭 위치, GPU 렌더러에서의
  움직임 부드러움, Segoe UI Variable·맑은 고딕으로 대체될 때의 모양(번들 Pretendard가 우선이라
  보통은 쓰이지 않음), 실제 IME(한글 입력기) 조합 중 패널 개폐.


# 윤DF 0.9.20 · 문서 아이콘, 파란 강조색, 메모와 형광펜 분리 · 2026-09-27

- 아이콘: `art/logo/YoonDF-Document-Logo.png`에서 타일 색(#017ADA), 타일 모서리(폭의 19%), 문서 크기
  (타일 폭의 50.6%, 높이의 67.6%), 문서 모서리(문서 폭의 12.7%), 접힌 모서리(문서 폭의 32%, #A0CFFA),
  글자 폭(문서 폭의 50.3%)과 기준선을 재서 `scripts/make_logo.py`가 벡터로 그린다. 글자는
  Pretendard Bold 윤곽을 획으로 두껍게 해서 원본 굵기에 맞췄다. 48px 이하는 글자 없이 문서를 키운다.
  원본과 나란히 놓고 비교했다.
- 강조색: accent #017ADA, 선택 바탕 #E5F1FC, 선택 글자 #0160AD, 페이지 위 표시 #017ADA.
  어두운 화면 #4DA3F0. 흰 바탕·잉크 글자·선 색은 그대로.
- 메모/형광펜 분리: 엔진이 읽은 주석 목록을 `bichaek/annotation_views.py`가 두 보기로 나눈다(PDF는
  그대로). 단위 시험 12개(`tests/test_annotation_views.py`): 글 없는 표시는 형광펜에만, 메모가 있는
  표시는 양쪽, 공백만 있는 메모는 메모 아님, 메모·텍스트 상자·펜·스탬프는 메모에만, 답글 묶음 유지
  (깊이 보존), 부모 없는 답글, 답글인 표시, 검토 상태, 입력 불변, 빈 목록, 요약 텍스트 형식, 실제 PDF
  저장 후 다시 읽은 주석.
- 실제 창 시험(`scripts/qa_comment_views.py`, 손상 객체 보고서·복사 금지 PDF·회전 페이지 각각):
  형광펜은 형광펜 탭에만 생기고 패널이 따라감, 드래그 메모·위치 메모는 메모 탭, 메모 수정 창에
  표시한 글과 색 고르기가 없음, 수정 전후 표시의 색·글·영역·종류 동일, 형광펜 탭에서 메모 달기와
  색 바꾸기(메모·작성자 유지), 답글 수 표시, 페이지의 표시를 누르면 그 탭이 열림(이미 고른 표시를
  다시 눌러도), 모두 복사(복사 금지 PDF는 본문 글이 나가지 않음), 삭제·실행 취소, 저장 후 별도로 열어
  메모·색 확인. 이어서 6쪽 60개 표시: 쪽 순서, 형광펜 탭에만, 탭 40번 빠르게 전환, 60개 모두 복사,
  문서 탭 전환 후에도 문서별 목록 유지. QML 경고 없음.
  시험 중 실제 결함 1건을 고쳤다: 이미 고른 표시를 메모 탭에서 페이지로 다시 누르면 형광펜 탭으로
  넘어가지 않았다(선택이 그대로라 신호가 없음). 이제 누를 때마다 보여 준다.
- 회전 페이지에서 포인터로 세로 글자를 끌면 한 글자 덜 선택될 수 있다(기존 시험도 같은 허용치).
  표시 글 추출 자체는 회전 페이지에서도 완전함을 따로 확인했다.
- 단위 시험 102개, `scripts/qa_*.py` 23개 모두 통과(Linux, offscreen, 소프트웨어 렌더러). 화면: `docs/comments-0920.png`.
- 확인하지 못한 것: Windows 실기기에서 새 아이콘이 작업표시줄·탐색기에서 보이는 모습(아이콘 캐시
  때문에 설치 후 바로 안 바뀔 수 있음), 실제 한글 입력기로 메모 수정.

