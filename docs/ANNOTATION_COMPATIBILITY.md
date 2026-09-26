# PDF 주석 호환 범위 · 0.5.0

주석은 PDF 내부의 네이티브 annotation 객체입니다. 페이지 본문이나 이미지로 합치지 않습니다.

| 종류 | 표시·목록 | 추가 | 내용·작성자·색상 수정 | 답글 |
| --- | --- | --- | --- | --- |
| 메모 (Text) | 지원 | 지원 | 지원 | 지원 |
| 형광펜 (Highlight) | 지원 | 지원 | 지원 | 지원 |
| 밑줄 (Underline) | 지원 | 지원 | 지원 | 지원 |
| 취소선 (StrikeOut) | 지원 | 지원 | 지원 | 지원 |
| 물결 밑줄 (Squiggly) | 지원 | 엔진 API만 | 지원 | 지원 |
| 자유 텍스트·펜·도형·스탬프 등 | 기존 객체 유지 | 미지원 | 미지원 | 미지원 |
| 잠긴 주석·그룹·검토 상태 기록 | 기존 객체 유지 | 미지원 | 미지원 | 미지원 |

각 항목에는 PDF 권한·잠금 조건이 적용됩니다. 삭제는 연결된 답글을 포함하고 실행 취소를 지원합니다.
본문 정보만 수정한 댓글은 이전 rich-text `/RC`를 제거해 Acrobat이 옛 댓글을 우선 표시하지 않게 합니다.
이 경우 댓글 본문의 서식은 일반 텍스트로 바뀌며 주석의 페이지 표시 스트림은 유지됩니다.

## 확인한 것

- PDF Reference 1.7 §8.4, 특히 markup annotation dictionary의 /T, /CreationDate, /IRT, /RT 정의에 맞춰 저장.
- /RT의 답글 값은 /R. /Group과 구별하며 그룹 속성은 읽기 전용으로 취급.
- pypdf로 만든 독립 fixture의 팝업, 답글, Unicode 내용, 사용자 정의 필드, /AP, 검토 상태 보존.
- pypdf로 저장된 PDF의 실제 /Annots, /NM, /QuadPoints, /AP, /IRT, /RT, 작성자·내용·시각 검사.
- 원본 페이지 content stream의 동일성 확인. 주석을 추가해도 본문에 평면화하지 않음.
- 0/90/180/270도 회전 및 CropBox가 있는 페이지의 선택 위치 확인.
- Poppler에서 주석 렌더링과 문법 오류 부재 확인.
- Qt UI에서 드래그→주석 추가→댓글 수정→답글→저장→다른 탭→다시 돌아오기→삭제→실행 취소 확인.

Acrobat 자체를 실행한 테스트 결과가 아닙니다. 독립 writer fixture도 Acrobat이 만든 파일이라고 표기하지 않습니다.

## Windows에서 Acrobat 왕복 확인

1. `samples/annotation-compatibility.pdf`를 Acrobat/Reader에서 연 뒤 주석 패널을 엽니다.
2. 형광펜 1개와 그 답글, 밑줄 1개, 취소선 1개, 메모 1개가 보이는지 확인합니다.
3. 한글 작성자·댓글이 읽히고 원래 문장 위치가 일치하는지 확인합니다.
4. Acrobat에서 메모 내용과 색상을 바꾸고 형광펜에 답글을 추가한 뒤 다른 이름으로 저장합니다.
5. 저장한 파일을 비책 PDF에서 열고 주석 목록에서 수정한 내용·색상·답글을 확인합니다.
6. 비책에서 댓글을 바꾸고 저장한 뒤 Acrobat에서 다시 확인합니다.

이 여섯 단계는 아직 실기기에서 실행하지 않았습니다. Adobe 클라우드 공유 검토·FDF/XFDF·전자서명 보존은 범위 밖입니다.

## 구현 참고

- [Adobe PDF Reference 1.7](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf), §8.4 및 Table 8.21.
- [PyMuPDF Annot](https://pymupdf.readthedocs.io/en/latest/annot.html): metadata, reply reference, flags, appearances.
- [PyMuPDF Page](https://pymupdf.readthedocs.io/en/latest/page.html): standard markup annotations and text geometry.
