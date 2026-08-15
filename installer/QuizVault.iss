#define AppName "QuizVault"
#define AppVersion "2.0.0"
#define Root ".."

[Setup]
AppId={{E6B15846-CE13-4D9E-A079-399F93D02D36}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
OutputDir={#Root}\dist
OutputBaseFilename=QuizVault-Setup
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\QuizVault.exe

[Files]
Source: "{#Root}\dist\QuizVault.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\QuizVault"; Filename: "{app}\QuizVault.exe"
Name: "{autodesktop}\QuizVault"; Filename: "{app}\QuizVault.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Parameters: "/silent /install"; StatusMsg: "正在检查 WebView2 Runtime..."; Flags: waituntilterminated
Filename: "{app}\QuizVault.exe"; Description: "启动 QuizVault"; Flags: nowait postinstall skipifsilent
