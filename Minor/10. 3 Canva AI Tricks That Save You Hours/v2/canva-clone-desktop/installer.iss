; Inno Setup 6 script: wraps dist\CanvasStudio into Output\CanvasStudio-Setup.exe (per-user install, no admin rights).
[Setup]
AppName=Canvas Studio
AppVersion=2.0
DefaultDirName={autopf}\Canvas Studio
DefaultGroupName=Canvas Studio
PrivilegesRequired=lowest
OutputBaseFilename=CanvasStudio-Setup
OutputDir=Output
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\CanvasStudio.exe

[Files]
Source: "dist\CanvasStudio\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Canvas Studio"; Filename: "{app}\CanvasStudio.exe"
Name: "{autodesktop}\Canvas Studio"; Filename: "{app}\CanvasStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\CanvasStudio.exe"; Description: "Start Canvas Studio"; Flags: nowait postinstall skipifsilent
