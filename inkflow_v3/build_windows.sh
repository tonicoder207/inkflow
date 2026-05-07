#!/bin/bash

echo ""
echo "============================================================"
echo " InkFlow v3 Build System (Git Bash)"
echo "============================================================"
echo ""

# UNIX und Windows Pfade ermitteln
ROOT_UNIX="$(cd "$(dirname "$0")" && pwd)"
if command -v cygpath &> /dev/null; then
    ROOT_WIN="$(cygpath -w "$ROOT_UNIX")"
else
    ROOT_WIN="$ROOT_UNIX"
fi

BACKEND_DIR="$ROOT_UNIX/backend"
FRONTEND_DIR="$ROOT_UNIX/frontend"
PYTHON_DIR="$ROOT_UNIX/python_embedded"
DIST_DIR="$ROOT_UNIX/dist_electron"
ASSETS_DIR="$ROOT_UNIX/assets"

PY=""

echo "[Schritt 0] Suche Python..."

# Prüfe, ob Python im PATH verfügbar ist
if command -v python &> /dev/null; then
    PY="$(command -v python)"
elif command -v python3 &> /dev/null; then
    PY="$(command -v python3)"
else
    # Bekannte Pfade
    USERNAME=$(id -un)
    PATHS=(
        "/c/Users/Toni/AppData/Local/Programs/Python/Python311/python.exe"
        "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python311/python.exe"
        "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python312/python.exe"
        "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python310/python.exe"
        "/c/Python311/python.exe"
        "/c/Python312/python.exe"
        "/c/Python310/python.exe"
    )
    for p in "${PATHS[@]}"; do
        if [ -f "$p" ]; then
            PY="$p"
            break
        fi
    done
fi

if [ -z "$PY" ]; then
    echo ""
    echo "FEHLER: Python nicht gefunden!"
    echo "Installiere Python von: https://www.python.org/downloads/"
    echo "Wichtig: Haken bei 'Add Python to PATH' setzen!"
    echo ""
    read -p "Drücken Sie Enter zum Beenden..."
    exit 1
fi

echo "    Gefunden: $PY"
"$PY" --version || { echo "FEHLER: Python funktioniert nicht"; read -p "Drücken Sie Enter zum Beenden..."; exit 1; }

echo ""
echo "[Schritt 0b] Pruefe Node.js..."
if ! command -v node &> /dev/null; then
    echo "FEHLER: Node.js nicht gefunden!"
    echo "Installiere von: https://nodejs.org"
    read -p "Drücken Sie Enter zum Beenden..."
    exit 1
fi
node --version | sed 's/^/    Node: /'

# Assets
mkdir -p "$ASSETS_DIR"
if [ ! -f "$ASSETS_DIR/LICENSE.txt" ]; then
    echo "InkFlow Desktop" > "$ASSETS_DIR/LICENSE.txt"
fi

if [ ! -f "$ASSETS_DIR/icon.ico" ]; then
    if command -v cygpath &> /dev/null; then
        ASSETS_WIN="$(cygpath -w "$ASSETS_DIR")"
    else
        ASSETS_WIN="$ASSETS_DIR"
    fi
    # Escape für das Python Skript
    ASSETS_WIN_ESC="${ASSETS_WIN//\\/\\\\}"
    "$PY" -c "from PIL import Image,ImageDraw;s=256;img=Image.new('RGBA',(s,s),(12,12,26,255));d=ImageDraw.Draw(img);m=s//8;d.polygon([(s//2,m),(s-m,s//2),(s//2,s-m),(m,s//2)],fill=(201,168,76,255));img.save(r'${ASSETS_WIN_ESC}\\\\icon.ico',format='ICO')" 2>/dev/null
    if [ -f "$ASSETS_DIR/icon.ico" ]; then
        echo "    Icon erstellt"
    else
        echo "    Icon uebersprungen"
    fi
fi

echo ""
echo "[1/5] Embedded Python vorbereiten..."

if [ -f "$PYTHON_DIR/python.exe" ]; then
    echo "    Embedded Python bereits vorhanden - ueberspringe Download"
else
    mkdir -p "$PYTHON_DIR"
    
    echo "    Lade Python 3.11 Embedded herunter..."
    PY_ZIP="/tmp/python_embed.zip"
    curl -sL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -o "$PY_ZIP" || { echo "FEHLER: Download fehlgeschlagen"; exit 1; }
    
    echo "    Entpacke..."
    unzip -q "$PY_ZIP" -d "$PYTHON_DIR" || { echo "FEHLER: Entpacken fehlgeschlagen"; exit 1; }
    
    echo "    Aktiviere site-packages..."
    PTH_FILE="$PYTHON_DIR/python311._pth"
    if [ -f "$PTH_FILE" ]; then
        sed -i 's/#import site/import site/g' "$PTH_FILE"
        echo "    site-packages aktiviert"
    fi
    
    echo "    Installiere pip..."
    curl -sL "https://bootstrap.pypa.io/get-pip.py" -o "/tmp/get-pip.py"
    "$PYTHON_DIR/python.exe" "/tmp/get-pip.py" --quiet || { echo "FEHLER: pip installation fehlgeschlagen"; exit 1; }
    
    echo "    Installiere Backend-Pakete in Embedded Python..."
    echo "    (Das dauert 2-3 Minuten...)"
    "$PYTHON_DIR/python.exe" -m pip install \
        fastapi==0.111.0 \
        "uvicorn[standard]==0.29.0" \
        pillow==10.3.0 \
        numpy==1.26.4 \
        opencv-python-headless==4.9.0.80 \
        reportlab==4.2.0 \
        python-multipart==0.0.9 \
        pydantic==2.7.1 \
        aiofiles==23.2.1 \
        pygetwindow==0.0.9 \
        pywin32==306 \
        pynput==1.7.7 \
        --quiet --no-warn-script-location || { echo "FEHLER: pip install fehlgeschlagen"; exit 1; }
    echo "    Embedded Python OK"
fi

echo ""
echo "[2/5] Teste Backend-Imports..."
if [ ! -f "$BACKEND_DIR/main.py" ]; then
    echo "FEHLER: backend/main.py nicht gefunden in $BACKEND_DIR"
    exit 1
fi
if command -v cygpath &> /dev/null; then
    BACKEND_WIN="$(cygpath -w "$BACKEND_DIR")"
else
    BACKEND_WIN="$BACKEND_DIR"
fi
BACKEND_WIN_ESC="${BACKEND_WIN//\\/\\\\}"

"$PYTHON_DIR/python.exe" -c "import sys; sys.path.insert(0,r'${BACKEND_WIN_ESC}'); import fastapi,uvicorn,PIL,numpy,cv2,reportlab; print('    Imports OK')" || {
    echo "FEHLER: Backend-Imports fehlgeschlagen"
    echo "Versuche: Schritt 1 (Embedded Python) komplett neu durchfuehren"
    echo "Loesche dazu den Ordner: $PYTHON_DIR"
    exit 1
}
echo "    Backend OK"

echo ""
echo "[3/5] Baue Frontend..."
cd "$FRONTEND_DIR"
if [ ! -f "package.json" ]; then
    echo "FEHLER: frontend/package.json fehlt"
    exit 1
fi

echo "    npm install..."
npm install --legacy-peer-deps || { echo "FEHLER: npm install fehlgeschlagen"; exit 1; }

echo "    vite build..."
npm run build || npx vite build || { echo "FEHLER: Frontend-Build fehlgeschlagen"; exit 1; }

if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
    echo "FEHLER: dist/index.html wurde nicht erstellt"
    exit 1
fi
echo "    Frontend OK"

echo ""
echo "[4/5] Electron installieren..."
cd "$ROOT_UNIX"
npm install || { echo "FEHLER: npm install (root) fehlgeschlagen"; exit 1; }
echo "    Electron OK"

echo ""
echo "[5/5] Windows-Installer erstellen..."
echo "    (Das dauert 3-5 Minuten...)"

if [ -d "$DIST_DIR" ]; then
    rm -rf "$DIST_DIR"
fi
mkdir -p "$DIST_DIR"

npx electron-builder --win --x64 --publish never || {
    echo "FEHLER: electron-builder fehlgeschlagen"
    echo "Bitte den Output oben lesen fuer Details"
    exit 1
}

EXE=$(ls "$DIST_DIR"/*.exe 2>/dev/null | head -n 1)
if [ -z "$EXE" ]; then
    echo "WARNUNG: Keine .exe in $DIST_DIR gefunden"
else
    echo ""
    echo "============================================================"
    echo " BUILD ERFOLGREICH!"
    echo ""
    echo " $EXE"
    echo ""
    echo " Diese Datei an Freunde schicken."
    echo " Sie brauchen NICHTS installieren."
    echo "============================================================"
fi

if [ -d "$DIST_DIR" ]; then
    if command -v explorer.exe &> /dev/null; then
        explorer.exe "$(cygpath -w "$DIST_DIR" 2>/dev/null || echo "$DIST_DIR")"
    fi
fi

read -p "Drücken Sie Enter zum Beenden..."
exit 0
