@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
title InkFlow v3 Build

echo.
echo ============================================================
echo  InkFlow v3 Build System
echo ============================================================
echo.

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "PYTHON_DIR=%ROOT%python_embedded"
set "DIST_DIR=%ROOT%dist_electron"
set "ASSETS_DIR=%ROOT%assets"
set "PY="

:: ── Python finden ─────────────────────────────────────────────────────────────
echo [Schritt 0] Suche Python...

:: Bekannte Pfade zuerst
for %%P in (
    "C:\Users\Toni\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Python310\python.exe"
) do (
    if "!PY!"=="" (
        if exist %%P (
            set "PY=%%~P"
            echo     Gefunden: %%~P
        )
    )
)

:: System PATH versuchen
if "!PY!"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%p in ('where python 2^>nul') do (
            if "!PY!"=="" set "PY=%%p"
        )
        if "!PY!"=="" set "PY=python"
        echo     Gefunden in PATH: !PY!
    )
)

if "!PY!"=="" (
    echo.
    echo FEHLER: Python nicht gefunden!
    echo Installiere Python von: https://www.python.org/downloads/
    echo Wichtig: Haken bei "Add Python to PATH" setzen!
    echo.
    pause
    exit /b 1
)

:: Python testen
"!PY!" --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python unter "!PY!" funktioniert nicht
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('"!PY!" --version 2^>^&1') do echo     Build-Python: %%v

:: Node.js pruefen
echo.
echo [Schritt 0b] Pruefe Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Node.js nicht gefunden!
    echo Installiere von: https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo     Node: %%v

:: Assets
if not exist "%ASSETS_DIR%" mkdir "%ASSETS_DIR%"
if not exist "%ASSETS_DIR%\LICENSE.txt" echo InkFlow Desktop > "%ASSETS_DIR%\LICENSE.txt"
if not exist "%ASSETS_DIR%\icon.ico" (
    "!PY!" -c "from PIL import Image,ImageDraw;s=256;img=Image.new('RGBA',(s,s),(12,12,26,255));d=ImageDraw.Draw(img);m=s//8;d.polygon([(s//2,m),(s-m,s//2),(s//2,s-m),(m,s//2)],fill=(201,168,76,255));img.save(r'%ASSETS_DIR:\=/%/icon.ico',format='ICO')" 2>nul
    if exist "%ASSETS_DIR%\icon.ico" (echo     Icon erstellt) else (echo     Icon uebersprungen)
)

:: ── Schritt 1: Embedded Python ───────────────────────────────────────────────
echo.
echo [1/5] Embedded Python vorbereiten...

if exist "%PYTHON_DIR%\python.exe" (
    echo     Embedded Python bereits vorhanden - ueberspringe Download
    goto STEP2
)

mkdir "%PYTHON_DIR%" 2>nul

echo     Lade Python 3.11 Embedded herunter...
set "PY_ZIP=%TEMP%\python_embed.zip"
"!PY!" -c "import urllib.request; urllib.request.urlretrieve('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip', r'%PY_ZIP%'); print('    Download OK')"
if errorlevel 1 (
    echo FEHLER: Download fehlgeschlagen - pruefe Internetverbindung
    pause & exit /b 1
)

echo     Entpacke...
"!PY!" -c "import zipfile; zipfile.ZipFile(r'%PY_ZIP%').extractall(r'%PYTHON_DIR%'); print('    Entpackt')"
if errorlevel 1 (echo FEHLER: Entpacken fehlgeschlagen & pause & exit /b 1)

echo     Aktiviere site-packages...
for %%f in ("%PYTHON_DIR%\python311._pth") do (
    if exist "%%f" (
        "!PY!" -c "
p=r'%%f'
c=open(p).read()
if 'import site' not in c:
    c=c.replace('#import site','import site')
    open(p,'w').write(c)
print('    site-packages aktiviert')
"
    )
)

echo     Installiere pip...
"!PY!" -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', r'%TEMP%\get-pip.py')"
"%PYTHON_DIR%\python.exe" "%TEMP%\get-pip.py" --quiet
if errorlevel 1 (echo FEHLER: pip installation fehlgeschlagen & pause & exit /b 1)

echo     Installiere Backend-Pakete in Embedded Python...
echo     (Das dauert 2-3 Minuten...)
"%PYTHON_DIR%\python.exe" -m pip install ^
    fastapi==0.111.0 ^
    "uvicorn[standard]==0.29.0" ^
    pillow==10.3.0 ^
    numpy==1.26.4 ^
    opencv-python-headless==4.9.0.80 ^
    reportlab==4.2.0 ^
    python-multipart==0.0.9 ^
    pydantic==2.7.1 ^
    aiofiles==23.2.1 ^
    pyautogui==0.9.54 ^
    pygetwindow==0.0.9 ^
    --quiet --no-warn-script-location
if errorlevel 1 (echo FEHLER: pip install fehlgeschlagen & pause & exit /b 1)
echo     Embedded Python OK

:STEP2
:: ── Schritt 2: Backend testen ────────────────────────────────────────────────
echo.
echo [2/5] Teste Backend-Imports...
if not exist "%BACKEND_DIR%\main.py" (
    echo FEHLER: backend\main.py nicht gefunden in %BACKEND_DIR%
    pause & exit /b 1
)
"%PYTHON_DIR%\python.exe" -c "import sys; sys.path.insert(0,r'%BACKEND_DIR%'); import fastapi,uvicorn,PIL,numpy,cv2,reportlab; print('    Imports OK')"
if errorlevel 1 (
    echo FEHLER: Backend-Imports fehlgeschlagen
    echo Versuche: Schritt 1 (Embedded Python) komplett neu durchfuehren
    echo Loesche dazu den Ordner: %PYTHON_DIR%
    pause & exit /b 1
)
echo     Backend OK

:: ── Schritt 3: Frontend bauen ─────────────────────────────────────────────────
echo.
echo [3/5] Baue Frontend...
cd /d "%FRONTEND_DIR%"
if not exist "package.json" (echo FEHLER: frontend\package.json fehlt & pause & exit /b 1)

echo     npm install...
call npm install --legacy-peer-deps
if errorlevel 1 (echo FEHLER: npm install fehlgeschlagen & pause & exit /b 1)

echo     vite build...
call npm run build
if errorlevel 1 (
    echo     Versuche direkten vite build...
    call npx vite build
)
if errorlevel 1 (echo FEHLER: Frontend-Build fehlgeschlagen & pause & exit /b 1)
if not exist "%FRONTEND_DIR%\dist\index.html" (
    echo FEHLER: dist\index.html wurde nicht erstellt
    pause & exit /b 1
)
echo     Frontend OK

:: ── Schritt 4: Electron ──────────────────────────────────────────────────────
echo.
echo [4/5] Electron installieren...
cd /d "%ROOT%"
call npm install
if errorlevel 1 (echo FEHLER: npm install (root) fehlgeschlagen & pause & exit /b 1)
echo     Electron OK

:: ── Schritt 5: Installer bauen ───────────────────────────────────────────────
echo.
echo [5/5] Windows-Installer erstellen...
echo     (Das dauert 3-5 Minuten...)

if exist "%DIST_DIR%" rd /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

call npx electron-builder --win --x64 --publish never
echo     electron-builder Exit-Code: %ERRORLEVEL%
if errorlevel 1 (
    echo FEHLER: electron-builder fehlgeschlagen
    echo Bitte den Output oben lesen fuer Details
    pause & exit /b 1
)

:: Ergebnis
set "EXE="
for %%f in ("%DIST_DIR%\*.exe") do set "EXE=%%f"
if "!EXE!"=="" (
    echo WARNUNG: Keine .exe in %DIST_DIR% gefunden
) else (
    echo.
    echo ============================================================
    echo  BUILD ERFOLGREICH!
    echo.
    echo  !EXE!
    echo.
    echo  Diese Datei an Freunde schicken.
    echo  Sie brauchen NICHTS installieren.
    echo ============================================================
)

if exist "%DIST_DIR%" start "" "%DIST_DIR%"
pause
exit /b 0
