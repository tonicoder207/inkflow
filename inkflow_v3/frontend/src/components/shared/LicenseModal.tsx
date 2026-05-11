import React, { useState } from 'react';
import { useStore } from '@/store';
import { Key, ShieldCheck, Loader2 } from 'lucide-react';
import { activateLicense } from '@/utils/license';
import toast from 'react-hot-toast';

export default function LicenseModal() {
  const { license, setLicense } = useStore();
  const [keyInput, setKeyInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleActivate = async () => {
    setLoading(true);
    const res = await activateLicense(keyInput.trim());
    if (res.status === 'success') {
      setLicense({ key: keyInput.trim(), status: 'valid', licenseType: res.license_type, expiresAt: res.expires_at, lastChecked: new Date().toISOString() });
      toast.success('Aktiviert!');
    } else { toast.error(res.message); }
    setLoading(false);
  };

  if (license.status === 'valid') return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 p-8 rounded-2xl border border-slate-800 w-full max-w-md text-center">
        <Key size={40} className="mx-auto mb-4 text-blue-400" />
        <h2 className="text-2xl font-bold mb-4">Lizenz erforderlich</h2>
        <input value={keyInput} onChange={e => setKeyInput(e.target.value)} placeholder="INK-XXXX" className="w-full bg-slate-800 p-4 rounded-xl text-center font-mono text-xl mb-4" />
        <button onClick={handleActivate} disabled={loading} className="w-full bg-blue-600 p-4 rounded-xl font-bold">{loading ? '...' : 'Aktivieren'}</button>
      </div>
    </div>
  );
}
