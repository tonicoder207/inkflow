import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { Lock, Mail, Loader2, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      toast.error(error.message, {
        style: { background: '#1e1b4b', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }
      });
    } else {
      toast.success('Welcome back!', {
        style: { background: '#064e3b', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }
      });
    }
    setLoading(false);
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen p-4 overflow-hidden">
      {/* Background ambient elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md relative z-10"
      >
        <div className="glass-card p-10 rounded-3xl space-y-8">
          <div className="text-center space-y-2">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="mx-auto w-16 h-16 bg-white/[0.05] rounded-2xl border border-white/10 flex items-center justify-center mb-6 shadow-xl"
            >
              <Sparkles className="text-blue-400" size={32} />
            </motion.div>
            <h1 className="text-3xl font-bold tracking-tight text-white font-['Outfit']">InkFlow Admin</h1>
            <p className="text-slate-400 text-sm">Secure access to license management</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" size={20} />
                <input 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  className="glass-input w-full pl-12" 
                  placeholder="Email address" 
                  required 
                />
              </div>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" size={20} />
                <input 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  className="glass-input w-full pl-12" 
                  placeholder="Password" 
                  required 
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading} 
              className="primary-button w-full py-3.5 flex items-center justify-center gap-2 text-sm uppercase tracking-wider mt-4"
            >
              {loading ? (
                <><Loader2 className="animate-spin" size={18} /> Authenticating...</>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
