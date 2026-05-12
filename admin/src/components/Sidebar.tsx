import React from 'react';
import { LayoutDashboard, Key, MonitorSmartphone, Settings, LogOut, Hexagon } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function Sidebar() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Overview', icon: LayoutDashboard },
    { path: '/licenses', label: 'Licenses', icon: Key },
    { path: '/devices', label: 'Devices', icon: MonitorSmartphone },
  ];

  return (
    <aside className="w-64 border-r border-white/5 bg-[#0a0a0c]/80 backdrop-blur-3xl flex flex-col h-screen fixed left-0 top-0 z-40">
      <div className="p-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Hexagon className="text-white" size={24} />
        </div>
        <span className="font-['Outfit'] font-bold text-xl text-white tracking-wide">InkFlow</span>
      </div>

      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link 
              key={item.path} 
              to={item.path}
              className="relative block"
            >
              {isActive && (
                <motion.div 
                  layoutId="sidebar-active" 
                  className="absolute inset-0 bg-white/[0.08] rounded-xl border border-white/10"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <div className={`relative px-4 py-3 flex items-center gap-3 rounded-xl transition-colors ${
                isActive ? 'text-white' : 'text-slate-400 hover:text-white hover:bg-white/[0.02]'
              }`}>
                <item.icon size={20} className={isActive ? 'text-blue-400' : ''} />
                <span className="font-medium">{item.label}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/5">
        <button 
          onClick={() => supabase.auth.signOut()}
          className="w-full px-4 py-3 flex items-center gap-3 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all"
        >
          <LogOut size={20} />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
