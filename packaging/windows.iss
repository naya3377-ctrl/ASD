; SPDX-License-Identifier: AGPL-3.0-or-later
[Setup]
AppId={{C4F07FAA-CFCF-49C2-AE06-D47E3A65B615}
AppName=윤DF
AppVersion=0.9.3
AppPublisher=YoonDF contributors
DefaultDirName={localappdata}\Programs\YoonDF
DefaultGroupName=윤DF
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=YoonDF-Setup-0.9.3
SetupIconFile=..\assets\icon.ico
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Alternate PyInstaller packaging: use Restart Manager before overwriting.
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
UninstallDisplayIcon={app}\YoonDF.exe
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\dist\YoonDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\윤DF"; Filename: "{app}\YoonDF.exe"
Name: "{autodesktop}\윤DF"; Filename: "{app}\YoonDF.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\BichaekPDF.Document"; ValueType: string; ValueData: "PDF document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\BichaekPDF.Document\DefaultIcon"; ValueType: string; ValueData: """{app}\YoonDF.exe"",0"
Root: HKCU; Subkey: "Software\Classes\BichaekPDF.Document\shell\open\command"; ValueType: string; ValueData: """{app}\YoonDF.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueName: "BichaekPDF.Document"; ValueType: string; ValueData: ""; Flags: uninsdeletevalue

; Per-user candidates only: Windows owns the actual default selection.
Root: HKCU; Subkey: "Software\Classes\Applications\YoonDF.exe"; ValueName: "FriendlyAppName"; ValueType: string; ValueData: "윤DF"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\YoonDF.exe\SupportedTypes"; ValueName: ".pdf"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\YoonDF.exe\DefaultIcon"; ValueType: string; ValueData: """{app}\YoonDF.exe"",0"
Root: HKCU; Subkey: "Software\Classes\Applications\YoonDF.exe\shell\open\command"; ValueType: string; ValueData: """{app}\YoonDF.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\YoonDF.PDF"; ValueType: string; ValueData: "윤DF PDF 문서"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\YoonDF.PDF\Application"; ValueName: "ApplicationName"; ValueType: string; ValueData: "윤DF"
Root: HKCU; Subkey: "Software\Classes\YoonDF.PDF\Application"; ValueName: "ApplicationIcon"; ValueType: string; ValueData: """{app}\YoonDF.exe"",0"
Root: HKCU; Subkey: "Software\Classes\YoonDF.PDF\DefaultIcon"; ValueType: string; ValueData: """{app}\YoonDF.exe"",0"
Root: HKCU; Subkey: "Software\Classes\YoonDF.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\YoonDF.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueName: "YoonDF.PDF"; ValueType: string; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\YoonDF\Capabilities"; ValueName: "ApplicationName"; ValueType: string; ValueData: "윤DF"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\YoonDF\Capabilities"; ValueName: "ApplicationDescription"; ValueType: string; ValueData: "PDF 읽기, 편집, 주석, 결합 및 OCR"
Root: HKCU; Subkey: "Software\YoonDF\Capabilities"; ValueName: "ApplicationIcon"; ValueType: string; ValueData: """{app}\YoonDF.exe"",0"
Root: HKCU; Subkey: "Software\YoonDF\Capabilities\FileAssociations"; ValueName: ".pdf"; ValueType: string; ValueData: "YoonDF.PDF"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueName: "YoonDF"; ValueType: string; ValueData: "Software\YoonDF\Capabilities"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\YoonDF.exe"; ValueType: string; ValueData: "{app}\YoonDF.exe"; Flags: uninsdeletekey

[Run]
Filename: "{app}\YoonDF.exe"; Description: "Launch YoonDF"; Flags: nowait postinstall skipifsilent
Filename: "ms-settings:defaultapps"; Description: "Choose the default PDF app"; Flags: shellexec nowait postinstall skipifsilent unchecked
