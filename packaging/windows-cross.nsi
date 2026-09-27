; SPDX-License-Identifier: AGPL-3.0-or-later
Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!define VERSION "0.9.17"
Name "윤DF"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\YoonDF"
InstallDirRegKey HKCU "Software\BichaekPDF" "InstallDir"
RequestExecutionLevel user
SetCompressor zlib
AllowSkipFiles off
BrandingText "YoonDF ${VERSION} · Open source PDF editor"
Icon "../assets/icon.ico"
UninstallIcon "../assets/icon.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\YoonDF.exe"
!define MUI_FINISHPAGE_RUN_TEXT "윤DF 실행"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_TEXT "기본 PDF 앱 선택 화면 열기"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION OpenDefaultApps
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "../LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "YoonDF"
VIAddVersionKey /LANG=1033 "FileDescription" "YoonDF offline installer (x64)"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "2026 YoonDF contributors"

Var MaintenanceMutex
Var ReleaseName
Var ReleaseDir
Var ReleaseOwned
Var Activated

; Never let concurrent maintenance operations share a staging file/directory.
!macro MaintenanceLock
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\BichaekPDF.Maintenance") p .r0 ?e'
  Pop $1
  StrCpy $MaintenanceMutex $0
  ${If} $0 == 0
  ${OrIf} $1 == 183
    IfSilent +2
    MessageBox MB_ICONSTOP "다른 윤DF 설치 또는 제거가 진행 중입니다. 해당 창을 닫은 뒤 다시 실행해 주세요."
    SetErrorLevel 2
    Abort
  ${EndIf}
!macroend

Function .onInit
  ${IfNot} ${RunningX64}
    IfSilent +2
    MessageBox MB_ICONSTOP "64-bit Windows is required."
    Abort
  ${EndIf}
  !insertmacro MaintenanceLock
FunctionEnd

Function .onGUIEnd
  System::Call 'kernel32::CloseHandle(p $MaintenanceMutex)'
FunctionEnd

Function OpenDefaultApps
  ExecShell "open" "ms-settings:defaultapps"
FunctionEnd

; Register a candidate, leaving the Windows default choice to the user.
; Always point to the stable root launcher, never a versioned runtime.
Function RegisterPdfApplication
  ClearErrors
  WriteRegStr HKCU "Software\Classes\Applications\YoonDF.exe" "FriendlyAppName" "윤DF"
  WriteRegStr HKCU "Software\Classes\Applications\YoonDF.exe\SupportedTypes" ".pdf" ""
  WriteRegStr HKCU "Software\Classes\Applications\YoonDF.exe\DefaultIcon" "" '$\"$INSTDIR\YoonDF.exe$\",0'
  WriteRegStr HKCU "Software\Classes\Applications\YoonDF.exe\shell\open\command" "" '$\"$INSTDIR\YoonDF.exe$\" $\"%1$\"'
  WriteRegStr HKCU "Software\Classes\YoonDF.PDF" "" "윤DF PDF 문서"
  WriteRegStr HKCU "Software\Classes\YoonDF.PDF\Application" "ApplicationName" "윤DF"
  WriteRegStr HKCU "Software\Classes\YoonDF.PDF\Application" "ApplicationIcon" '$\"$INSTDIR\YoonDF.exe$\",0'
  WriteRegStr HKCU "Software\Classes\YoonDF.PDF\DefaultIcon" "" '$\"$INSTDIR\YoonDF.exe$\",0'
  WriteRegStr HKCU "Software\Classes\YoonDF.PDF\shell\open\command" "" '$\"$INSTDIR\YoonDF.exe$\" $\"%1$\"'
  WriteRegStr HKCU "Software\Classes\.pdf\OpenWithProgids" "YoonDF.PDF" ""
  WriteRegStr HKCU "Software\YoonDF\Capabilities" "ApplicationName" "윤DF"
  WriteRegStr HKCU "Software\YoonDF\Capabilities" "ApplicationDescription" "PDF 읽기, 편집, 주석, 결합 및 OCR"
  WriteRegStr HKCU "Software\YoonDF\Capabilities" "ApplicationIcon" '$\"$INSTDIR\YoonDF.exe$\",0'
  WriteRegStr HKCU "Software\YoonDF\Capabilities\FileAssociations" ".pdf" "YoonDF.PDF"
  WriteRegStr HKCU "Software\RegisteredApplications" "YoonDF" "Software\YoonDF\Capabilities"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\YoonDF.exe" "" "$INSTDIR\YoonDF.exe"
  IfErrors registration_failed
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  Return
  registration_failed:
    SetErrors
FunctionEnd

; A failed/cancelled extraction never becomes the current release.
Function .onInstFailed
  SetOutPath "$INSTDIR"
  ${If} $Activated != 1
    ${If} $ReleaseOwned == 1
      RMDir /r "$ReleaseDir"
    ${EndIf}
    Delete "$INSTDIR\BichaekPDF-next.exe"
    Delete "$INSTDIR\YoonDF-next.exe"
    Delete "$INSTDIR\Uninstall-next.exe"
    Delete "$INSTDIR\current-next.ini"
  ${EndIf}
FunctionEnd

; Same-volume replacement. Never delete the live file first, and never ignore
; a failed promotion. For silent installs fail without a blocking dialog.
!macro PromoteFile SOURCE TARGET LABEL
  ${LABEL}_retry:
  System::Call 'kernel32::MoveFileExW(w "${SOURCE}", w "${TARGET}", i 9) i .r1'
  ${If} $1 == 0
    System::Call 'kernel32::GetLastError() i .r2'
    IfSilent ${LABEL}_cancel
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "설치 파일을 전환할 수 없습니다. (오류 $2)$\r$\n${TARGET}$\r$\n$\r$\n다른 설치 창을 닫고 다시 시도해 주세요. 기존 문서와 실행 중인 앱은 유지됩니다." IDRETRY ${LABEL}_retry
    ${LABEL}_cancel:
    SetErrorLevel 2
    Abort
  ${EndIf}
!macroend

Section "윤DF"
  SetShellVarContext current
  StrCpy $ReleaseOwned 0
  StrCpy $Activated 0
  ClearErrors
  CreateDirectory "$INSTDIR\versions"
  IfErrors install_failed

  ; Reserve a *new* directory even when repairing this exact version. Old
  ; pythonw.exe / _bz2.pyd / Qt DLLs may stay loaded without blocking setup.
  StrCpy $0 0
  reserve_release:
    IntOp $0 $0 + 1
    StrCpy $ReleaseName "${VERSION}-$0"
    StrCpy $ReleaseDir "$INSTDIR\versions\$ReleaseName"
    System::Call 'kernel32::CreateDirectoryW(w "$ReleaseDir", p 0) i .r1 ?e'
    Pop $2
    ${If} $1 == 0
      ${If} $2 == 183
        Goto reserve_release
      ${EndIf}
      Goto install_failed
    ${EndIf}
  StrCpy $ReleaseOwned 1
  ClearErrors
  SetOutPath "$ReleaseDir"
  IfErrors install_failed
  SetOverwrite on
  File /r "${PAYLOAD}/*"
  IfErrors install_failed
  IfFileExists "$ReleaseDir\runtime\YoonDF.exe" +2 0
    Goto install_failed
  IfFileExists "$ReleaseDir\runtime\python312.dll" +2 0
    Goto install_failed
  IfFileExists "$ReleaseDir\main.py" +2 0
    Goto install_failed

  ; Prepare everything before switching the entry point. The root launcher
  ; falls back to the legacy layout until current.ini has been committed.
  SetOutPath "$INSTDIR"
  ClearErrors
  System::Call 'kernel32::CopyFileW(w "$ReleaseDir\YoonDF.exe", w "$INSTDIR\BichaekPDF-next.exe", i 0) i .r1'
  ${If} $1 == 0
    Goto install_failed
  ${EndIf}
  System::Call 'kernel32::CopyFileW(w "$ReleaseDir\YoonDF.exe", w "$INSTDIR\YoonDF-next.exe", i 0) i .r1'
  ${If} $1 == 0
    Goto install_failed
  ${EndIf}
  WriteUninstaller "$INSTDIR\Uninstall-next.exe"
  IfErrors install_failed
  FileOpen $0 "$INSTDIR\current-next.ini" w
  IfErrors install_failed
  FileWrite $0 "[Install]$\r$\nRelease=$ReleaseName$\r$\n"
  FileClose $0
  IfErrors install_failed
  !insertmacro PromoteFile "$INSTDIR\YoonDF-next.exe" "$INSTDIR\YoonDF.exe" yoondf_launcher
  ; Preserve old pinned shortcuts and manually configured file associations.
  !insertmacro PromoteFile "$INSTDIR\BichaekPDF-next.exe" "$INSTDIR\BichaekPDF.exe" launcher
  !insertmacro PromoteFile "$INSTDIR\Uninstall-next.exe" "$INSTDIR\Uninstall.exe" uninstaller
  !insertmacro PromoteFile "$INSTDIR\current-next.ini" "$INSTDIR\current.ini" current
  StrCpy $Activated 1

  Delete "$DESKTOP\Bichaek PDF.lnk"
  Delete "$SMPROGRAMS\Bichaek PDF\Bichaek PDF.lnk"
  RMDir "$SMPROGRAMS\Bichaek PDF"
  Delete "$DESKTOP\비책 PDF.lnk"
  Delete "$SMPROGRAMS\비책 PDF\비책 PDF.lnk"
  RMDir "$SMPROGRAMS\비책 PDF"
  CreateDirectory "$SMPROGRAMS\윤DF"
  CreateShortcut "$SMPROGRAMS\윤DF\윤DF.lnk" "$INSTDIR\YoonDF.exe" "" "$INSTDIR\YoonDF.exe" 0 SW_SHOWNORMAL "" "윤DF 열기"
  CreateShortcut "$DESKTOP\윤DF.lnk" "$INSTDIR\YoonDF.exe" "" "$INSTDIR\YoonDF.exe" 0 SW_SHOWNORMAL "" "윤DF 열기"
  WriteRegStr HKCU "Software\BichaekPDF" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "DisplayName" "윤DF"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "DisplayIcon" "$INSTDIR\YoonDF.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF" "NoRepair" 1
  Call RegisterPdfApplication
  IfErrors association_failed
  Goto install_done

  association_failed:
    IfSilent install_abort
    MessageBox MB_ICONSTOP "윤DF는 설치되었지만 PDF 연결 프로그램 등록에 실패했습니다. 설치 프로그램을 다시 실행해 주세요. 앱 안에서 파일 열기(Ctrl+O)는 사용할 수 있습니다."
    Goto install_abort
  install_failed:
    IfSilent install_abort
    MessageBox MB_ICONSTOP "설치를 완료하지 못했습니다. 폴더 쓰기 권한과 남은 디스크 공간을 확인한 뒤 다시 시도해 주세요.$\r$\n기존 실행 경로는 유지됩니다."
  install_abort:
    SetErrorLevel 2
    Abort
  install_done:
SectionEnd

Function un.onInit
  !insertmacro MaintenanceLock
  IfSilent un_ready
  MessageBox MB_OKCANCEL|MB_ICONINFORMATION "열려 있는 윤DF에서 문서를 저장하고 앱을 모두 닫은 뒤 제거해 주세요." IDOK un_ready
  Abort
  un_ready:
FunctionEnd

Function un.onGUIEnd
  System::Call 'kernel32::CloseHandle(p $MaintenanceMutex)'
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  DeleteRegValue HKCU "Software\Classes\.pdf\OpenWithProgids" "YoonDF.PDF"
  DeleteRegKey HKCU "Software\Classes\YoonDF.PDF"
  DeleteRegKey HKCU "Software\Classes\Applications\YoonDF.exe"
  DeleteRegValue HKCU "Software\RegisteredApplications" "YoonDF"
  DeleteRegKey HKCU "Software\YoonDF\Capabilities"
  DeleteRegKey /ifempty HKCU "Software\YoonDF"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\App Paths\YoonDF.exe"
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  Delete "$DESKTOP\윤DF.lnk"
  Delete "$SMPROGRAMS\윤DF\윤DF.lnk"
  RMDir "$SMPROGRAMS\윤DF"
  Delete "$INSTDIR\YoonDF.exe"
  Delete "$INSTDIR\YoonDF-next.exe"
  Delete "$DESKTOP\비책 PDF.lnk"
  Delete "$SMPROGRAMS\비책 PDF\비책 PDF.lnk"
  RMDir "$SMPROGRAMS\비책 PDF"
  Delete "$SMPROGRAMS\Bichaek PDF\Bichaek PDF.lnk"
  RMDir "$SMPROGRAMS\Bichaek PDF"
  Delete "$DESKTOP\Bichaek PDF.lnk"
  ; Only package-owned locations. PDFs outside these paths are untouched.
  RMDir /r "$INSTDIR\versions"
  Delete "$INSTDIR\current.ini"
  Delete "$INSTDIR\current-next.ini"
  Delete "$INSTDIR\BichaekPDF-next.exe"
  Delete "$INSTDIR\Uninstall-next.exe"
  ; Also remove the pre-0.5.1 layout when uninstalling an upgraded copy.
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\bichaek"
  RMDir /r "$INSTDIR\ui"
  RMDir /r "$INSTDIR\assets"
  RMDir /r "$INSTDIR\tessdata"
  RMDir /r "$INSTDIR\licenses"
  RMDir /r "$INSTDIR\source"
  Delete "$INSTDIR\main.py"
  Delete "$INSTDIR\BichaekPDF.exe"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\THIRD_PARTY_NOTICES.md"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\BichaekPDF"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BichaekPDF"
SectionEnd
