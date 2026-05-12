import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { Monitor, Search, Trash2, Key, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { format } from 'date-fns';

export default function DevicesPage() {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchData = async () => {
    try {
      const res = await api.get('/admin/devices');
      setDevices(res.data);
    } catch (e) { toast.error('Failed to load devices'); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const deleteDevice = async (id: string) => {
    if (!window.confirm('Are you sure you want to remove this device? This will free up a slot for the license.')) return;
    try {
      await api.delete(`/admin/devices/${id}`);
      toast.success('Device removed successfully');
      fetchData();
    } catch (e) { toast.error('Failed to remove device'); }
  };

  const filteredDevices = devices.filter(d => 
    (d.device_name || 'Unknown Device').toLowerCase().includes(search.toLowerCase()) ||
    (d.device_id || '').toLowerCase().includes(search.toLowerCase()) ||
    (d.licenses?.license_key || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold font-['Outfit'] tracking-tight">Devices</h1>
          <p className="text-slate-400 mt-2">Manage connected hardware and activations.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" size={18} />
            <input 
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search devices or keys..."
              className="glass-input pl-10 py-2.5 w-64 text-sm"
            />
          </div>
        </div>
      </header>

      <div className="glass-card rounded-3xl overflow-hidden border-white/10">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.03] border-b border-white/10 text-xs uppercase tracking-wider text-slate-400 font-semibold">
                <th className="p-5 font-medium">Device Name</th>
                <th className="p-5 font-medium">Device ID</th>
                <th className="p-5 font-medium">License Key</th>
                <th className="p-5 font-medium">Last Seen</th>
                <th className="p-5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">Loading devices...</td>
                </tr>
              ) : filteredDevices.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">No devices found.</td>
                </tr>
              ) : (
                filteredDevices.map((d, i) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    key={d.id} 
                    className="hover:bg-white/[0.02] transition-colors group"
                  >
                    <td className="p-5">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                          <Monitor size={16} />
                        </div>
                        <span className="font-medium text-slate-200">{d.device_name || 'Unknown Device'}</span>
                        {d.platform && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-slate-400 border border-white/10">
                            {d.platform}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-5">
                      <span className="font-mono text-sm text-slate-400">{d.device_id}</span>
                    </td>
                    <td className="p-5">
                      <div className="flex items-center gap-2 text-slate-300">
                        <Key size={14} className="text-slate-500" />
                        <span className="font-mono text-sm">{d.licenses?.license_key || 'Unknown'}</span>
                      </div>
                    </td>
                    <td className="p-5 text-sm text-slate-400">
                      <div className="flex items-center gap-2">
                        <Calendar size={14} className="text-slate-500" />
                        {d.last_seen ? format(new Date(d.last_seen), 'MMM d, yyyy HH:mm') : format(new Date(d.created_at), 'MMM d, yyyy HH:mm')}
                      </div>
                    </td>
                    <td className="p-5 text-right">
                      <button 
                        onClick={() => deleteDevice(d.id)}
                        className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Remove Device"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
