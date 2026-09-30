# 윤DF 1.0.6 · UI 글자 렌더링 수정

2026-09-30 · 기준 버전 1.0.5

## 사용자 보고와 수정

Windows 1.0.5의 탭·버튼·메뉴 글자가 자글거리고 흐리다는 보고를 받았다. 제공된 두 캡처에서 작은 글자 가장자리의 색 번짐과 거친 윤곽을 확인했다. 1.0.5에서 UI 전체에 NativeTextRendering과 수직 힌팅을 강제했던 설정을 주요 원인 후보로 판단했다. Windows 현장 재현 없이 단일 원인으로 확정한 것은 아니다.

- 앱의 기본 UI 렌더링을 QtTextRendering으로 변경했다. 플랫폼 비트맵 글리프 대신 배율에 대응하는 거리장 방식으로 UI 글자를 그린다.
- 탭·메뉴·버튼 등 Text에 QtRendering과 HighRenderTypeQuality(104)를 명시했다. 기본 품질 52보다 높은 글리프 해상도를 사용한다.
- 앱 UI 글꼴의 강제 수직 힌팅을 제거하고 NoSubpixelAntialias를 설정했다. 소프트웨어/네이티브 대체 경로에서도 LCD 색 번짐을 피하도록 한다.
- Pretendard 네 가지 정적 글꼴, 크기, 탭 디자인, 승인된 아이콘을 유지했다. PDF 본문·원본 글꼴 편집의 NativeRendering은 그대로다. 사이드바 미리보기에는 애니메이션을 추가하지 않았다.

## 검증

- 단위·통합 94개 통과.
- UI 회귀 22개 묶음 통과. 글꼴·탭·메뉴·본문 편집·주석·OCR·저장·재열기 포함.
- Qt software: 100/125/150/175/200%, 각 1000×640 및 1320×900.
- Qt RHI/OpenGL: 1.0.5와 1.0.6을 각각 125/175/200%에서 실행하고 캡처. Linux Xvfb + Mesa llvmpipe OpenGL 4.5, basic render loop 사용. 그래픽 경로는 OpenGL이며 실제 하드웨어 GPU 벤치마크가 아니다.
- 화면에 보이는 글꼴 객체 97개가 Pretendard를 사용함을 확인. 렌더링 유형을 노출하는 UI 텍스트 객체 44개가 QtRendering을 사용하고 Text 품질이 104임을 검사했다.
- 캡처에서 탭·버튼·설정 글자의 윤곽, 잘림, 밝게·어둡게를 확인했다. 로그와 화면은 1.0.6 폴더에 포함했다.

## 남은 확인

Windows Direct3D/ClearType에서 사용자 화면과 동일한 조건의 실행 검증은 하지 못했다. 실제 Windows에서 흐림이 해소됐다고 단정하지 않는다. 설치 EXE는 오프라인 런타임과 글꼴을 포함한 x64 교차 빌드다.

참고: Qt Text renderType와 renderTypeQuality 공식 문서 https://doc.qt.io/qt-6.8/qml-qtquick-text.html
