import React, { useEffect, useState } from "react";
import { useStore } from "@/store";
import { listProfiles, createProfile, deleteProfile, getProfile } from "@/utils/api";
import type { ProfileSummary } from "@/types";
import { 
  Plus, 
  Trash2, 
  PenTool, 
  ChevronRight, 
  Sparkles,
  Search,
  MoreVertical,
  Activity
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

export default function LandingScreen() {
  const { setScreen, setActiveProfile, setTrainerProfileId, profiles, setProfiles } = useStore();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try { setProfiles(await listProfiles()); }
    catch { toast.error("Profiles could not be loaded"); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const p = await createProfile(name.trim());
      toast.success(`"${p.name}" created`);
      setName(""); setCreating(false);
      await load();
      setTrainerProfileId(p.id); setScreen("trainer");
    } catch(e: any) { toast.error(e.message); }
  };

  const handleDelete = async (id: string, n: string) => {
    if (!confirm(`Delete "${n}"?`)) return;
    try { await deleteProfile(id); await load(); }
    catch(e: any) { toast.error(e.message); }
  };

  const openEditor = async (s: ProfileSummary) => {
    try { setActiveProfile(await getProfile(s.id)); setScreen("editor"); }
    catch(e: any) { toast.error(e.message); }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10">
      {/* Header Section */}
      <header className="flex items-end justify-between">
        <div className="space-y-1">
          <h2 className="title-large flex items-center gap-3">
            Your Handwriting <Sparkles className="text-apple-blue" size={28} />
          </h2>
          <p className="text-apple-gray-300 text-lg">Manage your digital ink profiles and handwriting models.</p>
        </div>
        <button 
          onClick={() => setCreating(true)} 
          className="btn-apple-primary"
        >
          <Plus size={18} /> New Profile
        </button>
      </header>

      {/* Profile Creation Modal (Inline for Apple feel) */}
      {creating && (
        <div className="apple-card bg-apple-blue/5 border-apple-blue/20 flex gap-4 items-center animate-scale-in">
          <div className="flex-1">
            <input 
              autoFocus 
              className="apple-input text-lg font-medium" 
              placeholder="Give your profile a name (e.g. My Cursive)..."
              value={name} 
              onChange={e => setName(e.target.value)}
              onKeyDown={e => { 
                if(e.key === "Enter") handleCreate(); 
                if(e.key === "Escape") setCreating(false); 
              }}
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="btn-apple-primary">Create</button>
            <button onClick={() => setCreating(false)} className="btn-apple-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-apple-gray-300 group-focus-within:text-apple-blue transition-colors" size={18} />
          <input 
            className="apple-input pl-12 bg-white/5 border-white/5 hover:bg-white/10" 
            placeholder="Search profiles..." 
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="title-section">Active Profiles</h3>
        
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="apple-glass rounded-apple h-40 animate-pulse" />
            ))}
          </div>
        ) : profiles.length === 0 ? (
          <div className="apple-card py-20 text-center border-dashed border-white/10">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
              <PenTool size={32} className="text-apple-gray-300" />
            </div>
            <p className="text-apple-gray-300 font-medium">No profiles yet. Create your first one to start writing.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {profiles.map((p, i) => (
              <div 
                key={p.id} 
                className="apple-card-hover flex flex-col justify-between group"
                style={{ animationDelay: `${i * 0.05}s` }}
                onClick={() => openEditor(p)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex gap-4">
                    <div className="w-12 h-12 rounded-apple-sm bg-apple-gray-500 flex items-center justify-center text-apple-blue">
                      <Activity size={24} />
                    </div>
                    <div>
                      <h4 className="font-bold text-white text-lg leading-tight">{p.name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[11px] font-bold text-apple-gray-300 uppercase tracking-tighter">
                          {p.characters_trained} Characters
                        </span>
                        <span className="w-1 h-1 rounded-full bg-apple-gray-400" />
                        <span className="text-[11px] font-bold text-apple-gray-300 uppercase tracking-tighter">
                          {p.variants_total} Variations
                        </span>
                      </div>
                    </div>
                  </div>
                  <button 
                    onClick={e => { e.stopPropagation(); handleDelete(p.id, p.name); }}
                    className="p-2 rounded-full hover:bg-apple-system-red/10 text-apple-gray-300 hover:text-apple-system-red transition-all"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <div className="mt-8 space-y-3">
                  <div className="flex justify-between items-end text-[11px] font-bold text-apple-gray-300 uppercase">
                    <span>Model Density</span>
                    <span className="text-white">{Math.min(100, Math.floor(p.variants_total / 2.5))}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-apple-blue rounded-full transition-all duration-1000" 
                      style={{ width: `${Math.min(100, p.variants_total / 2.5)}%` }}
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button 
                    onClick={e => { e.stopPropagation(); setTrainerProfileId(p.id); setScreen("trainer"); }} 
                    className="btn-apple-secondary flex-1 text-xs py-2"
                  >
                    <PenTool size={14} /> Train Character
                  </button>
                  <button 
                    onClick={e => { e.stopPropagation(); openEditor(p); }} 
                    disabled={p.variants_total === 0} 
                    className="btn-apple-primary flex-1 text-xs py-2"
                  >
                    Open Editor <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Guide Section */}
      <footer className="pt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { id: "1", title: "Collect Data", desc: "Draw characters to build your custom handwriting dataset." },
          { id: "2", title: "Compose Text", desc: "Type your notes and preview the handwriting simulation." },
          { id: "3", title: "Inject to OneNote", desc: "Run the auto-writer to inject your ink into OneNote pages." },
        ].map(step => (
          <div key={step.id} className="p-6 apple-glass border-white/5 rounded-apple space-y-2">
            <span className="text-[10px] font-bold text-apple-blue uppercase tracking-[0.2em]">Step {step.id}</span>
            <h5 className="font-bold text-white">{step.title}</h5>
            <p className="text-xs text-apple-gray-300 leading-relaxed">{step.desc}</p>
          </div>
        ))}
      </footer>
    </div>
  );
}
