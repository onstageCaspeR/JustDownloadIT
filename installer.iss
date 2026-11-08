; Inno Setup script for JustDownloadIT.
;
; Packaging config only - the application code is not modified by this file.
; JustDownloadIT is now built by PyInstaller as an onedir bundle, so this script
; packages the whole output folder recursively. Compression stays lzma2 with
; solid compression (no UPX anywhere in the pipeline).

#define MyAppName "JustDownloadIT"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "JustDownloadIT"
#define MyAppURL "https://github.com/onstageCaspeR/JustDownloadIT"
#define MyAppExeName "JustDownloadIT.exe"
#define MyAppIcon "app_icon.ico"

[Setup]
AppId={{8B3F9E1A-2C5D-4A7B-9C1D-3E5F7A9B2C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (c) 2026 onstageCaspeR
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=JustDownloadIT-Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyMemo=no
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Whole onedir bundle (JustDownloadIT.exe + _internal\...) installed as-is.
Source: "release_build\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icon kept alongside the exe so shortcuts and the title bar use it.
Source: "{#MyAppIcon}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
