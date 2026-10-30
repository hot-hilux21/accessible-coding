; ============================================================
; AccessibleCoding - Windows Setup (Inno Setup)
; Installs the app to a directory of the user's choice,
; installs Python and adds it to PATH, installs the
; Microsoft Visual C++ runtime, and creates shortcuts.
; ============================================================

#define MyAppName "AccessibleCoding"
#define MyAppVersion "1.0.0"
#define MyAppExeName "AccessibleCoding.exe"
#define MyAppPublisher "AccessibleCoding"
#define MyAppURL "https://accessible-coding.duckdns.org"

[Setup]
AppId={{8E5F2C1A-9B3D-4E7A-8C2F-1D4B6A9E3F50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={commonpf}\HotHilux_21\AccessibleCoding
DefaultGroupName=AccessibleCoding
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=AccessibleCoding-Setup
Compression=lzma2
SolidCompression=yes
; The app keeps itself up to date by running this installer, and by then the
; reader has already closed it. Setup closes a running app through the same
; mechanism the Task Manager uses, which is what makes replacing an install
; folder that is in use possible at all. Putting the app back afterwards is
; not wanted: the reader chose to close it, and a window reappearing on its
; own looks like something went wrong.
RestartApplications=no
; A modern, adaptive wizard. In light mode it uses the Windows 11 style, in
; dark mode the built-in dark style, and it decides once, at startup, from the
; reader's own Windows setting rather than from a preference of ours.
; includetitlebar styles the title bar and borders to match the page, which is
; as close as a native setup comes to a borderless window, and hidebevels drops
; the horizontal rules between the header and each page. Inno turns these
; custom styles off by itself under a high-contrast theme, and that fallback is
; right: the reader's contrast setting outranks ours.
WizardStyle=modern dynamic windows11 includetitlebar hidebevels
; The panel beside the Welcome and Finished pages, and the mark in the header.
; Both are drawn by scripts/make_wizard_images.py. PNG rather than BMP because
; Inno keeps the alpha channel, so the header mark sits on whatever background
; the active style gives it instead of on a rectangle of our own colour.
WizardImageFile=installer\assets\wizard-image.png
WizardImageBackColor=$0D0D0D
WizardSmallImageFile=installer\assets\wizard-small.png
; MIT, and short. The reader sees it before choosing where to install.
LicenseFile=LICENSE
ArchitecturesInstallIn64BitMode=x64compatible
; Program Files needs elevation to write to, so the whole setup runs as an
; administrator. {autopf} with PrivilegesRequired=lowest meant the per-user
; copy under AppData instead, which is not where a 64-bit program belongs.
PrivilegesRequired=admin
MinVersion=10.0
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
SetupIconFile=src\accessible_ide\assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to AccessibleCoding Setup
WelcomeLabel2=This will install AccessibleCoding on your computer.%n%nAccessibleCoding is a code editor made for dyslexic and neurodivergent learners. It uses dyslexia-friendly fonts, a focus mode that quiets the rest of the screen, and plain-English error messages.%n%nClick Next to continue, or Cancel to exit.
; One label sits above the license text. Inno calls it LicenseLabel3 when a
; license file is in use. LicenseLabel1 and LicenseLabel2 are not names this
; version knows: using them compiles with a warning and the label shows Inno's
; own wording instead.
LicenseLabel3=Please read the license below, then choose whether to accept it. AccessibleCoding is free and open source. The MIT license lets you use, change, and share it, as long as the license and the copyright notice stay with any copy you pass on.
LicenseAccepted=I &accept the license
LicenseNotAccepted=I &do not accept the license
FinishedLabel=Setup has finished installing AccessibleCoding on your computer.%n%nClick Finish to open AccessibleCoding.
SelectDirLabel3=Setup will install AccessibleCoding into the following folder.%n%nTo use a different folder, type a new one or click Browse.
ReadyLabel1=Setup is now ready to begin installing AccessibleCoding on your computer.
ReadyLabel2a=Click Install to continue with the current settings, or click Back if you need to review or change anything.
BeveledLabel=AccessibleCoding - a code editor built for dyslexic readers

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "installpython"; Description: "Install Python and add it to PATH"; GroupDescription: "Python:"; Flags: checkedonce

[Files]
; restartreplace is why this does not stop with "MoveFile failed; code 183".
; The app is launched by the [Run] entry at the bottom of this file, so the
; ordinary way to meet that error is to run Setup again while AccessibleCoding
; is still open. Windows lets Setup delete a running program, but the name
; stays taken until the last handle on it closes, so the rename that follows
; fails with "Cannot create a file when that file already exists" and the
; install stops partway. With this flag Inno carries on, registers the file
; that is still in use to be replaced at the next restart, and asks for that
; restart when it finishes. It has no effect without administrator rights,
; which PrivilegesRequired=admin above already gives.
Source: "dist\AccessibleCoding\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace
Source: "installer\prereqs\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer\prereqs\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer\prereqs\python-3.13.16-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: ShouldInstallPython

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Microsoft Visual C++ Runtime..."; Flags: waituntilterminated
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing the WebView2 runtime (needed for the app window)..."; Flags: waituntilterminated
Filename: "{tmp}\python-3.13.16-amd64.exe"; Parameters: "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=0 Shortcuts=0"; StatusMsg: "Installing Python and adding it to PATH..."; Flags: waituntilterminated; Check: ShouldInstallPython
; The app asked for this itself, right after the reader pressed "Install
; and restart", so the new build opens as soon as the files are replaced.
; runasoriginaluser because Setup is elevated and the app must not be;
; nowait so Setup does not sit waiting on the program it just started.
Filename: "{app}\{#MyAppExeName}"; Check: ShouldRelaunch; Flags: nowait runasoriginaluser
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AccessibleCoding"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Earlier builds installed the program as AccessibleIDE.exe. Setup upgrades an
; existing install in place, keeping its folder, so without this the old exe
; would sit beside the new one for good after the rename.
Type: files; Name: "{app}\AccessibleIDE.exe"

[Icons]
Name: "{group}\AccessibleCoding"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall AccessibleCoding"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AccessibleCoding"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Code]
{ Returns True if a usable Python (3.10+) is already installed. }
function IsPythonInstalled: Boolean;
var
  Version: String;
begin
  Result := False;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.10\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.11\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.13\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.14\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.10\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.11\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.12\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.13\InstallPath', '', Version) then Result := True;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.14\InstallPath', '', Version) then Result := True;
end;

{ Install Python only if the task is selected AND no Python is present. }
function ShouldInstallPython: Boolean;
begin
  Result := WizardIsTaskSelected('installpython') and not IsPythonInstalled;
end;

{ True only when Setup was started by the app's "Install and restart"
  button, which passes /RELAUNCH on the command line. Every other way of
  arriving at this installer - the reader closing the app, a fresh manual
  run of Setup - passes nothing, and a program the reader closed stays
  closed. The parameter is custom: Inno Setup ignores command line
  parameters it does not know, and CmdLineParamExists is the documented
  way of reading one back. }
function CmdLineParamExists(const Value: string): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Value) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function ShouldRelaunch: Boolean;
begin
  Result := CmdLineParamExists('/RELAUNCH');
end;