# InkFlow V3 License System - Setup Guide

This system consists of three main parts:
1.  **App (`/inkflow_v3`)**: The main Electron application.
2.  **Admin Panel (`/admin`)**: A web-based dashboard for managing licenses.
3.  **Backend API (`/backend`)**: The central API that connects the App and Admin Panel to Supabase.

---

## 1. Supabase Setup

1.  **Create a New Project** on [Supabase](https://supabase.com).
2.  **Database Schema**: Go to the "SQL Editor" and run the contents of `backend/schema.sql` to create the necessary tables (`licenses`, `devices`, `activations`, `admins`).
3.  **Authentication**: Enable Email/Password auth in the Supabase Dashboard.
4.  **Admin User**: Create an admin user manually in the `auth.users` table or via the Supabase Auth UI, then add their ID and email to the `public.admins` table.

---

## 2. Backend Configuration (`/backend`)

1.  Navigate to `/backend`.
2.  Create a `.env` file based on `.env.example`:
    ```env
    SUPABASE_URL=your_supabase_url
    SUPABASE_SERVICE_KEY=your_supabase_service_role_key
    API_SECRET_KEY=a_secure_random_string
    ```
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Run the backend: `python main.py` (runs on port 8001).

---

## 3. Admin Panel Configuration (`/admin`)

1.  Navigate to `/admin`.
2.  Create a `.env` file based on `.env.example`:
    ```env
    VITE_SUPABASE_URL=your_supabase_url
    VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
    VITE_API_URL=http://localhost:8001
    ```
3.  Install dependencies: `npm install`.
4.  Run in dev mode: `npm run dev`.
5.  Build for production: `npm run build`.

---

## 4. Main App Integration (`/inkflow_v3`)

The app is pre-configured to communicate with the Backend API at `http://localhost:8001` (configurable in `inkflow_v3/frontend/src/utils/license.ts`).

1.  The app generates a unique **Device ID** upon first launch.
2.  Users must enter a **License Key** generated via the Admin Panel.
3.  The app checks the license every 6 hours and allows a **7-day offline grace period**.

---

## Technical Details

-   **Device Binding**: Each license is tied to a specific machine ID. The `max_devices` field in the `licenses` table controls how many machines can use the same key.
-   **Security**: Admin operations require a Bearer Token (`API_SECRET_KEY`).
-   **Frontend**: Built with React, Tailwind CSS, and Lucide icons.
-   **Backend**: Built with FastAPI and Supabase Python SDK.
