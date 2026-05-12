import React, { useState, useEffect } from 'react';
import { supabase } from './lib/supabase';
import { Toaster } from 'react-hot-toast';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Layout from './components/Layout';
import DashboardHome from './pages/DashboardHome';
import LicensesPage from './pages/LicensesPage';
import DevicesPage from './pages/DevicesPage';

export default function App() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => subscription.unsubscribe();
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen bg-[#0a0a0c]">
      <div className="w-10 h-10 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <BrowserRouter>
      <Toaster 
        position="top-center" 
        toastOptions={{
          className: '!bg-slate-900 !text-white !border !border-white/10 !rounded-xl !shadow-2xl',
          duration: 3000,
        }} 
      />
      
      {!session ? (
        <Login />
      ) : (
        <Layout>
          <Routes>
            <Route path="/" element={<DashboardHome />} />
            <Route path="/licenses" element={<LicensesPage />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      )}
    </BrowserRouter>
  );
}
