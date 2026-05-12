import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { Key, MonitorSmartphone, Activity, ArrowUpRight, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function DashboardHome() {
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/stats')
      .then(res => setStats(res.data))
      .catch(() => toast.error('Failed to load stats'))
      .finally(() => setLoading(false));
  }, []);

  const statCards = [
    { title: 'Total Licenses', value: stats.total_licenses || 0, icon: Key, color: 'text-blue-400', bg: 'bg-blue-400/10' },
    { title: 'Active Devices', value: stats.total_devices || 0, icon: MonitorSmartphone, color: 'text-indigo-400', bg: 'bg-indigo-400/10' },
    { title: 'Total Activations', value: stats.total_activations || 0, icon: Activity, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  ];

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold font-['Outfit'] tracking-tight">Overview</h1>
          <p className="text-slate-400 mt-2">Welcome back to the InkFlow control center.</p>
        </div>
        <Link to="/licenses" className="primary-button px-6 py-3 flex items-center gap-2">
          <Plus size={18} /> New License
        </Link>
      </header>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <div key={i} className="glass-card h-40 rounded-3xl animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {statCards.map((stat, i) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="glass-card p-6 rounded-3xl relative overflow-hidden group hover:bg-white/[0.03] transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className={`p-3 rounded-2xl ${stat.bg}`}>
                  <stat.icon className={stat.color} size={24} />
                </div>
                <div className="flex items-center gap-1 text-emerald-400 text-sm font-medium bg-emerald-400/10 px-2.5 py-1 rounded-lg">
                  <ArrowUpRight size={14} /> +12%
                </div>
              </div>
              <div className="mt-6">
                <p className="text-slate-400 text-sm font-medium">{stat.title}</p>
                <h3 className="text-4xl font-bold font-['Outfit'] mt-1">{stat.value}</h3>
              </div>
              {/* Subtle background glow */}
              <div className={`absolute -bottom-10 -right-10 w-32 h-32 ${stat.bg} rounded-full blur-[50px] opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
            </motion.div>
          ))}
        </div>
      )}

      {/* Quick Actions / Getting Started */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        <div className="glass-card p-8 rounded-3xl">
          <h3 className="text-xl font-bold font-['Outfit'] mb-4">System Status</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium text-slate-300">Backend API</span>
              </div>
              <span className="text-emerald-400 text-sm font-medium bg-emerald-400/10 px-3 py-1 rounded-full">Operational</span>
            </div>
            <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                <span className="font-medium text-slate-300">Database</span>
              </div>
              <span className="text-blue-400 text-sm font-medium bg-blue-400/10 px-3 py-1 rounded-full">Connected</span>
            </div>
          </div>
        </div>
        
        <div className="glass-card p-8 rounded-3xl border-blue-500/20 bg-blue-500/[0.02]">
          <h3 className="text-xl font-bold font-['Outfit'] mb-2 text-blue-400">Quick Tip</h3>
          <p className="text-slate-400 leading-relaxed">
            Licenses are bound to a specific hardware ID upon first activation. 
            You can increase the maximum devices limit for a license to allow usage across multiple computers.
          </p>
        </div>
      </div>
    </div>
  );
}
