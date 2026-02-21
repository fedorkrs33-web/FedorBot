; Inno Setup 6 — инсталлятор FedorBot
; Версия подставляется из version.py через version_define.iss
; Перед сборкой: python scripts/get_install_version.py

#include "version_define.iss"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName "FedorBot"
#define MyAppPublisher "FedorBot"
#define MyAppURL "https://github.com/username/fedorbot"
#define MyAppExeName "run_bot.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
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
OutputDir=output
OutputBaseFilename=FedorBot-Setup-{#MyAppVersion}
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\version.py
Uninstallable=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Создать значок в панели быстрого запуска"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
; Исходники
Source: "..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs
Source: "..\version.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\web_app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
; Лаунчеры
Source: "run_bot.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "run_web.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\src"; Permissions: users-modify

[Icons]
Name: "{group}\Запуск бота"; Filename: "{app}\run_bot.bat"; WorkingDir: "{app}"
Name: "{group}\Запуск веб-админки"; Filename: "{app}\run_web.bat"; WorkingDir: "{app}"
Name: "{group}\Удаление {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} — Бот"; Filename: "{app}\run_bot.bat"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\run_bot.bat"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "notepad"; Parameters: "{app}\.env.example"; Description: "Открыть пример .env для настройки"; Flags: postinstall nowait skipifsilent
Filename: "{app}\run_bot.bat"; Description: "Запустить бота сейчас"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Остановка процессов (по желанию): можно добавить taskkill для python, если бот запущен
; Run: "taskkill"; Parameters: "/F /IM python.exe"; Flags: runhidden waituntilterminated; Check: False

[Code]
procedure CurUninstallStepChanged(CurStep: TUninstallStep);
var
  AppDir: String;
begin
  if CurStep = usUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    // Спросить об удалении пользовательских данных (БД, логи) до удаления папки приложения
    if MsgBox('Удалить также пользовательские данные (база fedorbot.db, логи)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      if FileExists(AppDir + '\fedorbot.db') then
        DeleteFile(AppDir + '\fedorbot.db');
      if FileExists(AppDir + '\bot.log') then
        DeleteFile(AppDir + '\bot.log');
    end;
    // Удаление данных в AppData
    if DirExists(ExpandConstant('{localappdata}\FedorBot')) then
      DelTree(ExpandConstant('{localappdata}\FedorBot'), True, True, True);
  end;
end;
