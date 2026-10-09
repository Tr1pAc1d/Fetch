; =====================================================================
;              TAB INC. - INNO SETUP COMPILER SCRIPT FOR FETCH
; =====================================================================

#define MyAppName "Fetch"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TAB inc."
#define MyAppURL "https://tabinc.io"
#define MyAppExeName "Fetch-Server.exe"

[Setup]
AppId={{E5894B37-67D4-4B22-8A9C-8E11F64D078B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\TAB inc\Fetch
DefaultGroupName=TAB inc\Fetch
AllowNoIcons=yes
LicenseFile=F:\King\Fetch\installer\TERMS.txt
OutputDir=F:\King\Fetch-Release
OutputBaseFilename=FetchSetup
SetupIconFile=F:\King\Fetch\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "firewall"; Description: "Add Windows Defender / Firewall exception for Fetch (Recommended)"; GroupDescription: "Network Configuration:"; Flags: checkedonce
Name: "startup"; Description: "Start Fetch automatically when Windows starts"; GroupDescription: "Startup Options:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional Shortcuts:"

[Files]
Source: "F:\King\Fetch\server\dist\Fetch-Server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\assets\icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\installer\TERMS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch-Release\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Fetch"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall Fetch"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Fetch"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Fetch"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
; Optional Windows Firewall Rule Injection
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""Fetch Host (TAB inc.)"" dir=in action=allow program=""{app}\{#MyAppExeName}"" enable=yes"; Flags: runhidden; Tasks: firewall
; Launch Fetch at end of setup
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Clean up firewall rule upon uninstall
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Fetch Host (TAB inc.)"""; Flags: runhidden
