# InkFlow v3 — Project Context for AI

## 🚀 Overview
InkFlow v3 is a Windows-based application designed to inject native digital ink (handwriting) directly into Microsoft OneNote. It simulates real stylus input ("Pen Injection") to bypass API limitations and provide a natural writing experience.

## 🏗️ Architecture
The project follows a decoupled architecture:
- **Frontend**: Electron-based UI.
- **Backend**: Python (FastAPI) running as a sidecar process.
- **Communication**: Frontend talks to Backend via REST API (default `localhost:8000`).
- **Pen Injection**: Uses low-level Windows APIs to inject ink strokes into the system.

## 📁 Project Structure
- `/electron`: Main process for Electron, handles window management and backend lifecycle.
- `/frontend`: Web-based UI (Vue/React/HTML).
- `/backend`: Core logic.
    - `/api`: FastAPI routers (Profiles, Rendering, OneNote, Calibration).
    - `/engine`: The "heart" of the app.
        - `onenote_writer.py`: Handles the actual pen injection logic.
        - `handwriting.py`: Logic for stroke generation and processing.
    - `/models.py`: Data structures (Pydantic models).
- `/python_embedded`: A portable Python environment for standalone execution.
- `/data`: User-specific data (profiles, exports, calibration data).

## ✅ What Works
- **FastAPI Backend**: Fully functional routing and health checks.
- **Profile Management**: CRUD operations for user profiles.
- **Calibration Engine**: Supports 4-point perspective transformation to map screen coordinates to OneNote's writing area.
- **Electron Shell**: Handles bundling, installer creation, and admin privilege requests.
- **Static Export**: Rendering and serving ink as static images/files.

## ❌ Current Issues & WIP
- **Coordinate Mapping**: There are still inconsistencies when mapping UI coordinates to the actual OneNote canvas, especially with different **Windows Display Scaling (DPI)** settings.
- **Calibration Stability**: Sometimes the 4-point calibration "drifts" or doesn't align perfectly with OneNote's lines.
- **Admin Privileges**: The app must run as Administrator for Pen Injection to work, which can cause issues with file paths and environment variables.
- **Scaling Settings**: Implementing a user-selectable scaling setting to manually override or fix DPI-related calculation errors.

## 🛠️ Development & Build
- **Run Dev**: 
    1. Start Backend: `cd backend && python main.py`
    2. Start Frontend: `npm start` (starts Electron)
- **Build**: `npm run dist` (uses `electron-builder`).
- **Dependencies**: Listed in `package.json` (JS) and `backend/requirements.txt` (Python).

## 💡 Important Rationale
- **Why Pen Injection?**: Native OneNote API doesn't support "live" ink injection in a way that feels like a real pen.
- **Why Python Sidecar?**: Leverage Python's rich math (NumPy, OpenCV) and low-level Windows libraries (ctypes) for complex ink processing.
- **Why Admin?**: Windows restricts low-level input injection to elevated processes for security.

## 📋 AI Instructions
When working on this project:
1. **Always check DPI/Scaling**: If logic involves screen coordinates, assume Windows scaling (125%, 150%, etc.) might be active.
2. **Path Safety**: Use `os.path.join` and absolute paths where possible, as the current working directory changes between dev and production.
3. **Pydantic Types**: Use the models in `backend/models.py` for API data consistency.
