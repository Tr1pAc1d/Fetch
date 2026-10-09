; =====================================================================
;       TAB INC. - DUMMY / INSPECTION SETUP SCRIPT FOR FETCH
; =====================================================================

#define MyAppName "Fetch (Inspection Edition)"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TAB inc."
#define MyAppURL "https://tabinc.io"
#define MyAppExeName "Fetch-Server.exe"

[Setup]
AppId={{C7892D14-99D2-4A22-BF1C-9E21E74D089A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userdesktop}\Fetch-Inspection-Test
DefaultGroupName=TAB inc\Fetch (Inspection)
AllowNoIcons=yes
LicenseFile=F:\King\Fetch\installer\TERMS.txt
OutputDir=F:\King\Fetch-Release
OutputBaseFilename=FetchSetup-Inspection
SetupIconFile=F:\King\Fetch\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Non-admin privileges required for safe, easy inspection without UAC
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "firewall"; Description: "Add Windows Defender / Firewall exception for Fetch (Recommended - Simulated Dry-Run)"; GroupDescription: "Network Configuration:"; Flags: checkedonce
Name: "startup"; Description: "Start Fetch automatically when Windows starts (Simulated)"; GroupDescription: "Startup Options:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional Shortcuts:"

[Files]
Source: "F:\King\Fetch\server\dist\Fetch-Server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\assets\icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch\installer\TERMS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "F:\King\Fetch-Release\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Fetch"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall Fetch Inspection"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Fetch (Inspection)"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Dry-run inspection action (logs the simulated firewall rule to inspect what production installer executes)
Filename: "cmd.exe"; Parameters: "/c echo [INSPECTION LOG] Production FetchSetup executes: netsh advfirewall firewall add rule name=""Fetch Host (TAB inc.)"" dir=in action=allow program=""{app}\{#MyAppExeName}"" enable=yes > ""{app}\FIREWALL_INSPECTION_LOG.txt"""; Flags: runhidden; Tasks: firewall
; Finish page option to launch host
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
