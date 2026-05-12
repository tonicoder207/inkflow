import React, { useState, useEffect, useRef } from 'react';
import api from '../lib/api';
import { Key, Plus, Copy, MoreHorizontal, CheckCircle2, XCircle, Search, Trash2, PowerOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';

export default function LicensesPage() {
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setActiveDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchData = async () => {
    try {
      const res = await api.get('/admin/licenses');
      setLicenses(res.data);
    } catch (e) { toast.error('Failed to load licenses'); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const createLicense = async () => {
    try {
      await api.post('/admin/licenses', { max_devices: 1, license_type: 'standard' });
      toast.success('License generated successfully');
      fetchData();
    } catch (e) { toast.error('Failed to generate license'); }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const toggleStatus = async (id: string, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
      await api.put(`/admin/licenses/${id}/status`, { status: newStatus });
      toast.success(`License marked as ${newStatus}`);
      fetchData();
      setActiveDropdown(null);
    } catch (e) { toast.error('Failed to update license'); }
  };

  const deleteLicense = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this license?')) return;
    try {
      await api.delete(`/admin/licenses/${id}`);
      toast.success('License deleted');
      fetchData();
      setActiveDropdown(null);
    } catch (e) { toast.error('Failed to delete license'); }
  };

  const filteredLicenses = licenses.filter(l => 
    l.license_key.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold font-['Outfit'] tracking-tight">Licenses</h1>
          <p className="text-slate-400 mt-2">Manage access keys and device limits.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" size={18} />
            <input 
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search keys..."
              className="glass-input pl-10 py-2.5 w-64 text-sm"
            />
          </div>
          <button onClick={createLicense} className="primary-button px-6 py-2.5 flex items-center gap-2">
            <Plus size={18} /> Generate Key
          </button>
        </div>
      </header>

      <div className="glass-card rounded-3xl border-white/10" ref={dropdownRef}>
        <div className="overflow-x-auto overflow-y-visible" style={{ minHeight: "250px" }}>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.03] border-b border-white/10 text-xs uppercase tracking-wider text-slate-400 font-semibold">
                <th className="p-5 font-medium">License Key</th>
                <th className="p-5 font-medium">Status</th>
                <th className="p-5 font-medium">Type</th>
                <th className="p-5 font-medium">Devices</th>
                <th className="p-5 font-medium">Created</th>
                <th className="p-5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 relative">
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">Loading licenses...</td>
                </tr>
              ) : filteredLicenses.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">No licenses found.</td>
                </tr>
              ) : (
                filteredLicenses.map((l, i) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    key={l.id} 
                    className="hover:bg-white/[0.02] transition-colors group relative"
                  >
                    <td className="p-5">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                          <Key size={16} />
                        </div>
                        <span className="font-mono font-medium text-slate-200">{l.license_key}</span>
                        <button 
                          onClick={() => copyToClipboard(l.license_key)}
                          className="text-slate-500 hover:text-white opacity-0 group-hover:opacity-100 transition-all"
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                    </td>
                    <td className="p-5">
                      {l.status === 'active' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">
                          <CheckCircle2 size={14} /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 text-xs font-medium border border-red-500/20">
                          <XCircle size={14} /> {l.status}
                        </span>
                      )}
                    </td>
                    <td className="p-5">
                      <span className="capitalize text-slate-300">{l.license_type}</span>
                    </td>
                    <td className="p-5">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden w-24">
                          <div 
                            className={`h-full rounded-full ${(l.devices?.length || 0) >= l.max_devices ? 'bg-red-500' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min(100, ((l.devices?.length || 0) / l.max_devices) * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400 font-medium">
                          {l.devices?.length || 0}/{l.max_devices}
                        </span>
                      </div>
                    </td>
                    <td className="p-5 text-sm text-slate-400">
                      {format(new Date(l.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="p-5 text-right relative">
                      <button 
                        onClick={() => setActiveDropdown(activeDropdown === l.id ? null : l.id)}
                        className="p-2 text-slate-500 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                      >
                        <MoreHorizontal size={18} />
                      </button>

                      <AnimatePresence>
                        {activeDropdown === l.id && (
                          <motion.div 
                            initial={{ opacity: 0, scale: 0.95, y: -10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -10 }}
                            transition={{ duration: 0.15 }}
                            className="absolute right-8 top-10 w-48 bg-slate-900 border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                          >
                            <button
                              onClick={() => toggleStatus(l.id, l.status)}
                              className="w-full px-4 py-2.5 text-left text-sm text-slate-300 hover:bg-white/5 hover:text-white flex items-center gap-2 transition-colors"
                            >
                              <PowerOff size={16} />
                              {l.status === 'active' ? 'Deactivate' : 'Activate'}
                            </button>
                            <button
                              onClick={() => deleteLicense(l.id)}
                              className="w-full px-4 py-2.5 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors"
                            >
                              <Trash2 size={16} />
                              Delete License
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
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
