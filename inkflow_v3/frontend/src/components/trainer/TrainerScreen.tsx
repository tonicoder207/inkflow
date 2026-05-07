import React, { useEffect, useState, useCallback } from "react";
import { useStore } from "@/store";
import { getProfile, uploadCharacter } from "@/utils/api";
import type { HandwritingProfile } from "@/types";
import DrawingPad from "./DrawingPad";
import { ArrowLeft, ChevronLeft, ChevronRight, Check, RefreshCw, Feather } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

const GROUPS = [
  { id:"upper",   label:"ABC",   chars:"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("") },
  { id:"lower",   label:"abc",   chars:"abcdefghijklmnopqrstuvwxyz".split("") },
  { id:"digits",  label:"123",   chars:"0123456789".split("") },
  { id:"special", label:"!?,",   chars:[".",",","!","?",":",";","-","(",")"] },
  { id:"german",  label:"ÄÖÜ",   chars:["Ä","Ö","Ü","ä","ö","ü","ß"] },
];

export default function TrainerScreen() {
  const { trainerProfileId, setScreen } = useStore();
  const [profile, setProfile] = useState<HandwritingProfile|null>(null);
  const [loading, setLoading] = useState(true);
  const [group, setGroup]     = useState(0);
  const [idx, setIdx]         = useState(0);

  const load = useCallback(async () => {
    if(!trainerProfileId) return;
    setLoading(true);
    try { setProfile(await getProfile(trainerProfileId)); }
    catch { toast.error("Profil konnte nicht geladen werden"); }
    finally { setLoading(false); }
  },[trainerProfileId]);

  useEffect(()=>{ load(); },[load]);

  if(!trainerProfileId) return (
    <div className="h-full flex items-center justify-center">
      <div className="panel text-center"><p className="text-ink-300 text-sm mb-4">Kein Profil ausgewählt.</p>
        <button onClick={()=>setScreen("landing")} className="btn-primary"><ArrowLeft size={14}/>Zurück</button></div>
    </div>
  );

  const chars = GROUPS[group].chars;
  const safeIdx = Math.min(idx, chars.length-1);
  const activeChar = chars[safeIdx];
  const variantCount = profile?.characters[activeChar]?.length ?? 0;
  const totalTrained = Object.keys(profile?.characters??{}).length;
  const totalVariants = Object.values(profile?.characters??{}).reduce((a,v)=>a+v.length,0);
  const progress = Math.round((totalTrained / GROUPS.flatMap(g=>g.chars).length) * 100);

  const handleSave = async (blob:Blob) => {
    if(!trainerProfileId) return;
    await uploadCharacter(trainerProfileId, activeChar, blob);
    await load();
    if(safeIdx < chars.length-1) setTimeout(()=>setIdx(i=>i+1), 350);
  };

  return (
    <div className="h-full flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 flex flex-col border-r border-white/5 overflow-hidden">
        <div className="px-4 pt-4 pb-3 border-b border-white/5">
          <button onClick={()=>setScreen("landing")} className="flex items-center gap-1 text-xs text-ink-500 hover:text-ink-300 mb-3 transition-colors">
            <ArrowLeft size={12}/>Projekte
          </button>
          <h2 className="font-display text-sm font-semibold text-white truncate">{profile?.name??"…"}</h2>
          <p className="text-[11px] text-ink-500">{totalTrained} Zeichen · {totalVariants} Varianten</p>
          <div className="mt-2 h-1 bg-white/6 rounded-full overflow-hidden">
            <div className="h-full bg-accent-gold rounded-full transition-all duration-700" style={{width:`${progress}%`}}/>
          </div>
        </div>
        <div className="px-3 pt-3 pb-2 border-b border-white/5">
          {GROUPS.map((g,i)=>{
            const done = g.chars.filter(c=>(profile?.characters[c]?.length??0)>0).length;
            return (
              <button key={g.id} onClick={()=>{setGroup(i);setIdx(0);}}
                className={clsx("flex items-center justify-between w-full px-3 py-2 rounded-xl text-xs mb-1 transition-all",
                  group===i ? "bg-accent-gold/15 text-accent-gold border border-accent-gold/25"
                            : "text-ink-400 hover:bg-white/5 hover:text-ink-200")}>
                <span className="font-mono font-medium">{g.label}</span>
                <span className={clsx("text-[10px] px-1.5 py-0.5 rounded",
                  done===g.chars.length ? "bg-emerald-500/15 text-emerald-400"
                  : done>0 ? "bg-amber-500/15 text-amber-400" : "bg-white/5 text-ink-600")}>
                  {done}/{g.chars.length}
                </span>
              </button>
            );
          })}
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <div className="grid gap-1.5" style={{gridTemplateColumns:"repeat(auto-fill,minmax(36px,1fr))"}}>
            {chars.map((c,i)=>{
              const cnt = profile?.characters[c]?.length??0;
              return (
                <button key={c} onClick={()=>setIdx(i)}
                  className={clsx("h-9 rounded-lg border text-xs font-serif transition-all",
                    i===safeIdx ? "border-accent-gold/60 bg-accent-gold/12 text-accent-gold"
                    : cnt>=3    ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-300"
                    : cnt>0     ? "border-amber-500/20 bg-amber-500/5 text-amber-300"
                                : "border-white/8 text-ink-400 hover:border-white/20")}>
                  {c===" "?"␣":c}
                </button>
              );
            })}
          </div>
        </div>
        {totalTrained>=8 && (
          <div className="px-3 py-3 border-t border-white/5">
            <button onClick={()=>setScreen("editor")} className="btn-primary w-full justify-center text-xs">
              <Feather size={12}/>Editor
            </button>
          </div>
        )}
      </aside>

      {/* Center */}
      <main className="flex-1 flex flex-col items-center justify-center px-8 py-6">
        <div className="flex items-center gap-6 mb-6">
          <button onClick={()=>setIdx(i=>Math.max(0,i-1))} disabled={safeIdx===0}
            className="p-2 rounded-xl border border-white/8 text-ink-400 hover:text-white hover:bg-white/5 disabled:opacity-20 transition-all">
            <ChevronLeft size={18}/>
          </button>
          <div className="text-center">
            <span className="font-display text-6xl text-white/90 leading-none">
              {activeChar===" "?"Leerzeichen":activeChar}
            </span>
            {variantCount>=3 && <span className="ml-2 text-emerald-400"><Check size={16} className="inline"/></span>}
            <p className="text-xs text-ink-500 mt-1">{safeIdx+1} / {chars.length} · {GROUPS[group].label}</p>
          </div>
          <button onClick={()=>setIdx(i=>Math.min(chars.length-1,i+1))} disabled={safeIdx===chars.length-1}
            className="p-2 rounded-xl border border-white/8 text-ink-400 hover:text-white hover:bg-white/5 disabled:opacity-20 transition-all">
            <ChevronRight size={18}/>
          </button>
        </div>
        {!loading && (
          <DrawingPad key={activeChar} char={activeChar} variantCount={variantCount}
            onSave={handleSave} onNext={()=>setIdx(i=>Math.min(chars.length-1,i+1))}
            onPrev={()=>setIdx(i=>Math.max(0,i-1))}/>
        )}
      </main>

      {/* Right */}
      <aside className="w-44 shrink-0 border-l border-white/5 p-4 flex flex-col gap-4 overflow-y-auto">
        <div>
          <p className="label">Dieses Zeichen</p>
          <div className="flex justify-between text-xs mb-1"><span className="text-ink-500">Varianten</span><span className="text-ink-300 font-mono">{variantCount}/5</span></div>
          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-1.5">
            <div className={clsx("h-full rounded-full transition-all",variantCount>=5?"bg-emerald-400":variantCount>=3?"bg-accent-gold":"bg-amber-600")} style={{width:`${Math.min(100,variantCount*20)}%`}}/>
          </div>
          <p className="text-[11px] text-ink-500">
            {["Noch nicht gezeichnet","Gut — noch 2×","Fast — noch 1×","Basis OK ✓","Sehr gut","Optimal ✓"][Math.min(variantCount,5)]}
          </p>
        </div>
        <div className="mt-auto pt-4 border-t border-white/5">
          <p className="label">Gesamt</p>
          <div className="text-[11px] space-y-1">
            <div className="flex justify-between"><span className="text-ink-500">Zeichen</span><span className="text-ink-300 font-mono">{totalTrained}</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Varianten</span><span className="text-ink-300 font-mono">{totalVariants}</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Fortschritt</span><span className={clsx("font-mono",progress>=80?"text-emerald-400":progress>=40?"text-accent-gold":"text-ink-300")}>{progress}%</span></div>
          </div>
        </div>
      </aside>
    </div>
  );
}
