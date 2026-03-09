; ──────────────────────────────────────────────────────────────
; HandNavigator — Inno Setup Installer Script
;
; Installs the HandNavigator desktop app and optionally the
; Cinema 4D plugin into detected C4D installations.
;
; (c) 2026 Flávio Takemoto — MIT License
; ──────────────────────────────────────────────────────────────

#define MyAppName "HandNavigator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Flávio Takemoto"
#define MyAppURL "http://www.takemoto.com.br"
#define MyAppExeName "HandNavigator.exe"

[Setup]
AppId={{8F2E4A1D-3B5C-4D7E-9A1F-6C8D2E4F5A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=HandNavigator_Setup_{#MyAppVersion}
SetupIconFile=assets\handnavigator.ico
UninstallDisplayIcon={app}\HandNavigator.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
PrivilegesRequired=admin
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
; English
english.C4DPluginTitle=Cinema 4D Plugin Installation
english.C4DPluginDesc=Select which Cinema 4D installations should receive the HandNavigator plugin:
english.C4DNotFound=No Cinema 4D installations were detected.
english.C4DPluginsCreated=Created plugins folder for Cinema 4D:
english.C4DPluginInstalled=HandNavigator plugin installed to:
; Portuguese (BR)
brazilianportuguese.C4DPluginTitle=Instalação do Plugin Cinema 4D
brazilianportuguese.C4DPluginDesc=Selecione em quais instalações do Cinema 4D o plugin HandNavigator será instalado:
brazilianportuguese.C4DNotFound=Nenhuma instalação do Cinema 4D foi detectada.
brazilianportuguese.C4DPluginsCreated=Pasta plugins criada para Cinema 4D:
brazilianportuguese.C4DPluginInstalled=Plugin HandNavigator instalado em:
; Spanish
spanish.C4DPluginTitle=Instalación del Plugin Cinema 4D
spanish.C4DPluginDesc=Seleccione en cuáles instalaciones de Cinema 4D se instalará el plugin HandNavigator:
spanish.C4DNotFound=No se detectaron instalaciones de Cinema 4D.
spanish.C4DPluginsCreated=Carpeta plugins creada para Cinema 4D:
spanish.C4DPluginInstalled=Plugin HandNavigator instalado en:

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Desktop App (from PyInstaller dist)
Source: "dist\HandNavigator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; C4D Plugin files (installed via [Code] section based on detection)
Source: "c4d_plugin\HandNavigator\HandNavigator.pyp"; DestDir: "{tmp}\c4d_plugin"; Flags: dontcopy
Source: "c4d_plugin\HandNavigator\LICENSE"; DestDir: "{tmp}\c4d_plugin"; Flags: dontcopy
Source: "c4d_plugin\HandNavigator\README.md"; DestDir: "{tmp}\c4d_plugin"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start with Windows (optional task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "HandNavigator"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  C4DPage: TWizardPage;
  C4DCheckListBox: TNewCheckListBox;
  C4DPaths: array of string;
  C4DNames: array of string;
  C4DCount: Integer;

procedure DetectCinema4D;
var
  BasePath, LocalPath: string;
  I, Year: Integer;
  FullPath: string;
  Found: Boolean;
begin
  C4DCount := 0;
  BasePath := ExpandConstant('{commonpf64}');
  LocalPath := ExpandConstant('{localappdata}');

  { Scan for Cinema 4D versions 2020-2030 in Program Files }
  for Year := 2020 to 2030 do
  begin
    FullPath := BasePath + '\Maxon Cinema 4D ' + IntToStr(Year);
    if DirExists(FullPath) then
    begin
      SetArrayLength(C4DPaths, C4DCount + 1);
      SetArrayLength(C4DNames, C4DCount + 1);
      C4DPaths[C4DCount] := FullPath;
      C4DNames[C4DCount] := 'Cinema 4D ' + IntToStr(Year);
      C4DCount := C4DCount + 1;
    end;
  end;

  { Also check Maxon subfolder: Program Files\Maxon\Cinema 4D YYYY }
  for Year := 2020 to 2030 do
  begin
    FullPath := BasePath + '\Maxon\Cinema 4D ' + IntToStr(Year);
    if DirExists(FullPath) then
    begin
      Found := False;
      for I := 0 to C4DCount - 1 do
      begin
        if C4DPaths[I] = FullPath then
        begin
          Found := True;
          Break;
        end;
      end;
      if not Found then
      begin
        SetArrayLength(C4DPaths, C4DCount + 1);
        SetArrayLength(C4DNames, C4DCount + 1);
        C4DPaths[C4DCount] := FullPath;
        C4DNames[C4DCount] := 'Cinema 4D ' + IntToStr(Year);
        C4DCount := C4DCount + 1;
      end;
    end;
  end;

  { Also check %LOCALAPPDATA%\Maxon\Cinema 4D YYYY (newer versions) }
  for Year := 2020 to 2030 do
  begin
    FullPath := LocalPath + '\Maxon\Cinema 4D ' + IntToStr(Year);
    if DirExists(FullPath) then
    begin
      Found := False;
      for I := 0 to C4DCount - 1 do
      begin
        if C4DPaths[I] = FullPath then
        begin
          Found := True;
          Break;
        end;
      end;
      if not Found then
      begin
        SetArrayLength(C4DPaths, C4DCount + 1);
        SetArrayLength(C4DNames, C4DCount + 1);
        C4DPaths[C4DCount] := FullPath;
        C4DNames[C4DCount] := 'Cinema 4D ' + IntToStr(Year) + ' (user data)';
        C4DCount := C4DCount + 1;
      end;
    end;
  end;
end;

procedure InitializeWizard;
var
  I: Integer;
begin
  DetectCinema4D;

  { Create custom wizard page for C4D selection }
  C4DPage := CreateCustomPage(
    wpSelectTasks,
    ExpandConstant('{cm:C4DPluginTitle}'),
    ExpandConstant('{cm:C4DPluginDesc}')
  );

  C4DCheckListBox := TNewCheckListBox.Create(C4DPage);
  C4DCheckListBox.Parent := C4DPage.Surface;
  C4DCheckListBox.Left := 0;
  C4DCheckListBox.Top := 0;
  C4DCheckListBox.Width := C4DPage.SurfaceWidth;
  C4DCheckListBox.Height := C4DPage.SurfaceHeight;

  if C4DCount > 0 then
  begin
    for I := 0 to C4DCount - 1 do
    begin
      C4DCheckListBox.AddCheckBox(
        C4DNames[I],
        C4DPaths[I],
        0,          { level }
        True,       { checked by default }
        True,       { enabled }
        False,      { not a group }
        True,       { has internals }
        nil         { no data }
      );
    end;
  end else
  begin
    C4DCheckListBox.AddCheckBox(
      ExpandConstant('{cm:C4DNotFound}'),
      '',
      0, False, False, False, True, nil
    );
  end;
end;

procedure InstallC4DPlugin(const C4DPath: string);
var
  PluginsDir: string;
  PluginDest: string;
begin
  PluginsDir := C4DPath + '\plugins';
  PluginDest := PluginsDir + '\HandNavigator';

  { Create plugins and HandNavigator folders if needed }
  if not DirExists(PluginsDir) then
  begin
    ForceDirectories(PluginsDir);
    Log(ExpandConstant('{cm:C4DPluginsCreated}') + ' ' + PluginsDir);
  end;

  ForceDirectories(PluginDest);

  { Extract plugin files from temp }
  ExtractTemporaryFile('HandNavigator.pyp');
  ExtractTemporaryFile('LICENSE');
  ExtractTemporaryFile('README.md');

  { Copy to destination }
  FileCopy(ExpandConstant('{tmp}\c4d_plugin\HandNavigator.pyp'),
           PluginDest + '\HandNavigator.pyp', False);
  FileCopy(ExpandConstant('{tmp}\c4d_plugin\LICENSE'),
           PluginDest + '\LICENSE', False);
  FileCopy(ExpandConstant('{tmp}\c4d_plugin\README.md'),
           PluginDest + '\README.md', False);

  Log(ExpandConstant('{cm:C4DPluginInstalled}') + ' ' + PluginDest);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  I: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    { Install C4D plugin to each selected installation }
    for I := 0 to C4DCount - 1 do
    begin
      if C4DCheckListBox.Checked[I] then
        InstallC4DPlugin(C4DPaths[I]);
    end;
  end;
end;

{ Uninstall: remove plugin from C4D folders }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Year: Integer;
  PluginPath, BasePath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    BasePath := ExpandConstant('{commonpf64}');
    for Year := 2020 to 2030 do
    begin
      PluginPath := BasePath + '\Maxon Cinema 4D ' + IntToStr(Year) + '\plugins\HandNavigator';
      if DirExists(PluginPath) then
        DelTree(PluginPath, True, True, True);

      PluginPath := BasePath + '\Maxon\Cinema 4D ' + IntToStr(Year) + '\plugins\HandNavigator';
      if DirExists(PluginPath) then
        DelTree(PluginPath, True, True, True);

      PluginPath := ExpandConstant('{localappdata}') + '\Maxon\Cinema 4D ' + IntToStr(Year) + '\plugins\HandNavigator';
      if DirExists(PluginPath) then
        DelTree(PluginPath, True, True, True);
    end;
  end;
end;
