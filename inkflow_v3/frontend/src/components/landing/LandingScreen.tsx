import React, { useEffect, useState } from "react";
import { useStore } from "@/store";
import { listProfiles, createProfile, deleteProfile, getProfile } from "@/utils/api";
import type { ProfileSummary } from "@/types";
import { Plus, Trash2, PenLine, ChevronRight, Feather } from "lucide-react";
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
    catch { toast.error("Profile konnten nicht geladen werden"); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const p = await createProfile(name.trim());
      toast.success(`"${p.name}" erstellt`);
      setName(""); setCreating(false);
      await load();
      setTrainerProfileId(p.id); setScreen("trainer");
    } catch(e:any) { toast.error(e.message); }
  };

  const handleDelete = async (id:string, n:string) => {
    if (!confirm(`"${n}" löschen?`)) return;
    try { await deleteProfile(id); await load(); }
    catch(e:any) { toast.error(e.message); }
  };

  const openEditor = async (s:ProfileSummary) => {
    try { setActiveProfile(await getProfile(s.id)); setScreen("editor"); }
    catch(e:any) { toast.error(e.message); }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-8 py-10">
        <div className="mb-8 animate-slide-up">
          <div className="flex items-center gap-3 mb-2">
            <Feather size={28} className="text-accent-gold"/>
            <h1 className="font-display text-3xl font-bold text-white">InkFlow</h1>
          </div>
          <p className="text-ink-300 italic text-sm">Dein Text — deine Handschrift — in OneNote.</p>
        </div>

        <div className="flex items-center justify-between mb-4">
          <p className="label">Handschriftprofile</p>
          <button onClick={()=>setCreating(true)} className="btn-primary text-xs px-3 py-1.5">
            <Plus size={13}/>Neu
          </button>
        </div>

        {creating && (
          <div className="glass-warm rounded-2xl p-4 mb-4 animate-slide-up">
            <div className="flex gap-2">
              <input autoFocus className="input flex-1" placeholder="Profilname…"
                value={name} onChange={e=>setName(e.target.value)}
                onKeyDown={e=>{ if(e.key==="Enter") handleCreate(); if(e.key==="Escape") setCreating(false); }}/>
              <button onClick={handleCreate} className="btn-primary">Erstellen</button>
              <button onClick={()=>setCreating(false)} className="btn-ghost">Abbrechen</button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1,2].map(i=><div key={i} className="glass rounded-2xl h-32 animate-pulse-soft"/>)}
          </div>
        ) : profiles.length === 0 ? (
          <div className="glass rounded-2xl p-10 text-center">
            <PenLine size={32} className="mx-auto mb-3 text-ink-500"/>
            <p className="text-ink-300 mb-4 text-sm">Noch kein Profil — starte mit deiner eigenen Handschrift.</p>
            <button onClick={()=>setCreating(true)} className="btn-primary mx-auto"><Plus size={14}/>Profil erstellen</button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {profiles.map((p,i) => (
              <div key={p.id} className="glass rounded-2xl p-5 group hover:border-accent-gold/20 transition-all cursor-pointer animate-slide-up" style={{animationDelay:`${i*0.04}s`}}>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-medium text-white text-sm">{p.name}</h3>
                    <p className="text-xs text-ink-500 mt-0.5">{p.characters_trained} Zeichen · {p.variants_total} Varianten</p>
                  </div>
                  <button onClick={e=>{e.stopPropagation();handleDelete(p.id,p.name);}}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded text-red-400/60 hover:text-red-400">
                    <Trash2 size={13}/>
                  </button>
                </div>
                <div className="h-1 bg-white/6 rounded-full overflow-hidden mb-3">
                  <div className="h-full bg-accent-gold rounded-full transition-all" style={{width:`${Math.min(100,p.variants_total/2)}%`}}/>
                </div>
                <div className="flex gap-2">
                  <button onClick={()=>{setTrainerProfileId(p.id);setScreen("trainer");}} className="btn-ghost text-xs px-3 py-1.5 flex-1">
                    <PenLine size={12}/>Training
                  </button>
                  <button onClick={()=>openEditor(p)} disabled={p.variants_total===0} className="btn-primary text-xs px-3 py-1.5 flex-1">
                    Editor<ChevronRight size={12}/>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-10 grid grid-cols-3 gap-3 animate-slide-up" style={{animationDelay:"0.15s"}}>
          {[
            {n:"1",t:"Profil trainieren",d:"Buchstaben zeichnen → Varianten speichern"},
            {n:"2",t:"Text eingeben",d:"Editor öffnen, Text eingeben, Vorschau sehen"},
            {n:"3",t:"In OneNote schreiben",d:"Kalibrieren → Start → InkFlow schreibt automatisch"},
          ].map(s=>(
            <div key={s.n} className="glass rounded-2xl p-4">
              <div className="w-6 h-6 rounded-lg bg-accent-gold/20 border border-accent-gold/30 flex items-center justify-center mb-2">
                <span className="text-xs font-bold text-accent-gold">{s.n}</span>
              </div>
              <p className="text-xs font-medium text-white mb-1">{s.t}</p>
              <p className="text-xs text-ink-400 leading-relaxed">{s.d}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
