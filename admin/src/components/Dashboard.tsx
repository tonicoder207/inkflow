import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { supabase } from '../lib/supabase';
import { Key, Laptop, LogOut, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const [stats, setStats] = useState<any>({});
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [s, l] = await Promise.all([api.get('/admin/stats'), api.get('/admin/licenses')]);
      setStats(s.data); setLicenses(l.data);
    } catch (e) { toast.error('Fehler beim Laden'); }
    setLoading(false);
  };

  const createLicense = async () => {
    try {
      await api.post('/admin/licenses', { max_devices: 1, license_type: 'standard' });
      toast.success('Erstellt'); fetchData();
    } catch (e) { toast.error('Fehler'); }
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">InkFlow Admin</h1>
        <button onClick={() => supabase.auth.signOut()} className="flex items-center gap-2 text-red-400"><LogOut size={20}/> Logout</button>
      </div>
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
           <p className="text-slate-400">Lizenzen</p>
           <p className="text-3xl font-bold">{stats.total_licenses || 0}</p>
        </div>
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
           <p className="text-slate-400">Geräte</p>
           <p className="text-3xl font-bold">{stats.total_devices || 0}</p>
        </div>
      </div>
      <button onClick={createLicense} className="bg-blue-600 px-6 py-3 rounded-lg font-bold flex items-center gap-2"><Plus size={20}/> Neue Lizenz</button>
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-800">
            <tr><th className="p-4">Key</th><th className="p-4">Typ</th><th className="p-4">Geräte</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {licenses.map(l => (
              <tr key={l.id} className="hover:bg-slate-800/50">
                <td className="p-4 font-mono text-blue-400">{l.license_key}</td>
                <td className="p-4">{l.license_type}</td>
                <td className="p-4">{l.devices?.length || 0} / {l.max_devices}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
