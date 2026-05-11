import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { Lock, Mail, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) toast.error(error.message);
    setLoading(false);
  };

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <form onSubmit={handleLogin} className="w-full max-w-md bg-slate-900 p-8 rounded-2xl border border-slate-800 space-y-6">
        <h1 className="text-2xl font-bold text-center">Admin Login</h1>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-slate-800 p-3 rounded-lg" placeholder="Email" required />
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full bg-slate-800 p-3 rounded-lg" placeholder="Passwort" required />
        <button type="submit" disabled={loading} className="w-full bg-blue-600 p-3 rounded-lg font-bold">{loading ? '...' : 'Anmelden'}</button>
      </form>
    </div>
  );
}
