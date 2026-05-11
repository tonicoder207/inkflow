import React, { useEffect, useState, useCallback } from "react";
import { useStore } from "@/store";
import { getProfile, uploadCharacter } from "@/utils/api";
import type { HandwritingProfile } from "@/types";
import DrawingPad from "./DrawingPad";
import { 
  AlertCircle,
  ArrowLeft, 
  ChevronLeft, 
  ChevronRight, 
  Check, 
  Sparkles, 
  Feather,
  Info,
  Layers,
  Activity,
  History
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

const GROUPS = [
  { id: "upper",   label: "ABC",   chars: "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("") },
  { id: "lower",   label: "abc",   chars: "abcdefghijklmnopqrstuvwxyz".split("") },
  { id: "digits",  label: "123",   chars: "0123456789".split("") },
  { id: "special", label: "!?,",   chars: [".", ",", "!", "?", ":", ";", "-", "(", ")"] },
  { id: "german",  label: "ÄÖÜ",   chars: ["Ä", "Ö", "Ü", "ä", "ö", "ü", "ß"] },
];

export default function TrainerScreen() {
  const { trainerProfileId, setScreen } = useStore();
  const [profile, setProfile] = useState<HandwritingProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [group, setGroup] = useState(0);
  const [idx, setIdx] = useState(0);

  const load = useCallback(async () => {
    if (!trainerProfileId) return;
    setLoading(true);
    try { setProfile(await getProfile(trainerProfileId)); }
    catch { toast.error("Profile could not be loaded"); }
    finally { setLoading(false); }
  }, [trainerProfileId]);

  useEffect(() => { load(); }, [load]);

  if (!trainerProfileId) return (
    <div className="h-full flex items-center justify-center">
      <div className="apple-card text-center max-w-sm space-y-6">
        <div className="w-16 h-16 rounded-full bg-apple-system-red/10 flex items-center justify-center mx-auto">
          <AlertCircle className="text-apple-system-red" size={32} />
        </div>
        <p className="text-apple-gray-300">No profile selected for training.</p>
        <button onClick={() => setScreen("landing")} className="btn-apple-secondary w-full">
          <ArrowLeft size={16} /> Back to Projects
        </button>
      </div>
    </div>
  );

  const chars = GROUPS[group].chars;
  const safeIdx = Math.min(idx, chars.length - 1);
  const activeChar = chars[safeIdx];
  const variantCount = profile?.characters[activeChar]?.length ?? 0;
  const totalTrained = Object.keys(profile?.characters ?? {}).length;
  const totalVariants = Object.values(profile?.characters ?? {}).reduce((a, v) => a + v.length, 0);
  const progress = Math.round((totalTrained / GROUPS.flatMap(g => g.chars).length) * 100);

  const handleSave = async (blob: Blob) => {
    if (!trainerProfileId) return;
    try {
      await uploadCharacter(trainerProfileId, activeChar, blob);
      await load();
      if (safeIdx < chars.length - 1) {
        setTimeout(() => setIdx(i => i + 1), 350);
      } else {
        toast.success(`Training for "${GROUPS[group].label}" complete!`, { icon: "🎉" });
      }
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="h-full flex gap-8 animate-fade-in">
      {/* Left Sidebar: Character Index */}
      <aside className="w-64 shrink-0 flex flex-col gap-6">
        <header>
          <button 
            onClick={() => setScreen("landing")} 
            className="group flex items-center gap-2 text-[10px] font-bold text-apple-gray-300 uppercase tracking-widest hover:text-white transition-colors mb-4"
          >
            <ArrowLeft size={12} className="group-hover:-translate-x-1 transition-transform" /> Back to Dashboard
          </button>
          <div className="space-y-1">
            <h2 className="font-bold text-lg text-white truncate">{profile?.name || "Loading..."}</h2>
            <div className="flex justify-between text-[10px] font-bold text-apple-gray-300 uppercase">
              <span>Overall Progress</span>
              <span className="text-apple-blue">{progress}%</span>
            </div>
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-apple-blue rounded-full transition-all duration-1000" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </header>

        <nav className="flex-1 apple-glass rounded-apple p-3 flex flex-col gap-1 overflow-hidden">
          <h4 className="title-section px-3 mt-2">Groups</h4>
          <div className="space-y-1">
            {GROUPS.map((g, i) => {
              const done = g.chars.filter(c => (profile?.characters[c]?.length ?? 0) > 0).length;
              const isGroupActive = group === i;
              return (
                <button 
                  key={g.id} 
                  onClick={() => { setGroup(i); setIdx(0); }}
                  className={clsx(
                    "flex items-center justify-between w-full px-4 py-2.5 rounded-apple-sm text-xs font-bold transition-all",
                    isGroupActive 
                      ? "bg-apple-blue text-white shadow-lg shadow-apple-blue/20" 
                      : "text-apple-gray-300 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <span className="font-mono tracking-widest">{g.label}</span>
                  <span className={clsx(
                    "text-[10px] px-1.5 py-0.5 rounded",
                    isGroupActive ? "bg-white/20" : "bg-white/5 text-apple-gray-400"
                  )}>
                    {done}/{g.chars.length}
                  </span>
                </button>
              );
            })}
          </div>
          
          <div className="w-full h-px bg-white/5 my-4" />
          
          <h4 className="title-section px-3">Characters</h4>
          <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
            <div className="grid grid-cols-4 gap-2">
              {chars.map((c, i) => {
                const cnt = profile?.characters[c]?.length ?? 0;
                const isCharActive = i === safeIdx;
                return (
                  <button 
                    key={c} 
                    onClick={() => setIdx(i)}
                    className={clsx(
                      "h-10 rounded-apple-sm flex items-center justify-center text-sm font-medium transition-all",
                      isCharActive 
                        ? "bg-apple-blue text-white ring-2 ring-apple-blue ring-offset-2 ring-offset-black"
                        : cnt >= 3 
                          ? "bg-apple-system-green/10 text-apple-system-green border border-apple-system-green/20"
                          : cnt > 0 
                            ? "bg-apple-blue/10 text-apple-blue border border-apple-blue/10"
                            : "bg-white/5 text-apple-gray-400 hover:bg-white/10"
                    )}
                  >
                    {c === " " ? "␣" : c}
                  </button>
                );
              })}
            </div>
          </div>
        </nav>
      </aside>

      {/* Main Training Area */}
      <main className="flex-1 flex flex-col gap-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button 
              onClick={() => setIdx(i => Math.max(0, i - 1))} 
              disabled={safeIdx === 0}
              className="btn-apple-secondary p-3 rounded-full disabled:opacity-20"
            >
              <ChevronLeft size={20} />
            </button>
            <div className="text-center w-32">
              <span className="text-7xl font-bold text-white tracking-tighter drop-shadow-2xl">
                {activeChar === " " ? "Space" : activeChar}
              </span>
            </div>
            <button 
              onClick={() => setIdx(i => Math.min(chars.length - 1, i + 1))} 
              disabled={safeIdx === chars.length - 1}
              className="btn-apple-secondary p-3 rounded-full disabled:opacity-20"
            >
              <ChevronRight size={20} />
            </button>
          </div>

          <div className="flex gap-3">
            <div className="apple-glass px-4 py-2 rounded-full flex items-center gap-2">
              <Activity size={14} className="text-apple-blue" />
              <span className="text-[10px] font-bold uppercase tracking-widest">{variantCount} Variations Saved</span>
            </div>
            <button onClick={() => setScreen("editor")} disabled={totalTrained < 5} className="btn-apple-primary">
              <Sparkles size={16} fill="currentColor" /> Open Editor
            </button>
          </div>
        </header>

        <div className="flex-1 relative apple-card p-0 overflow-hidden bg-black/40 border-white/5 flex items-center justify-center group">
          {/* Subtle Grid Background */}
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
               style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          
          <div className="relative z-10 w-full h-full flex flex-col items-center justify-center p-12">
            {!loading && (
              <DrawingPad 
                key={activeChar} 
                char={activeChar} 
                variantCount={variantCount}
                onSave={handleSave} 
                onNext={() => setIdx(i => Math.min(chars.length - 1, i + 1))}
                onPrev={() => setIdx(i => Math.max(0, i - 1))}
              />
            )}
          </div>
          
          <div className="absolute bottom-6 flex gap-4 animate-fade-in opacity-40 group-hover:opacity-100 transition-opacity">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase text-apple-gray-300">
              <History size={12} /> Auto-advance after save
            </div>
          </div>
        </div>
      </main>

      {/* Right Stats Sidebar */}
      <aside className="w-56 shrink-0 space-y-6">
        <section className="apple-card space-y-4">
          <h4 className="title-section mb-0">Character Quality</h4>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-[10px] font-bold uppercase tracking-tighter">
                <span className="text-apple-gray-300">Variations</span>
                <span className="text-white">{variantCount} / 5</span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div 
                  className={clsx(
                    "h-full rounded-full transition-all duration-500",
                    variantCount >= 5 ? "bg-apple-system-green" : variantCount >= 3 ? "bg-apple-blue" : "bg-apple-gray-300"
                  )} 
                  style={{ width: `${Math.min(100, variantCount * 20)}%` }} 
                />
              </div>
              <p className="text-[10px] text-apple-gray-400 font-medium leading-tight">
                {[
                  "No data collected yet.",
                  "Good start, 4 more to go.",
                  "Keep going, 3 more.",
                  "Stable base achieved ✓",
                  "Excellent coverage.",
                  "Optimal model quality ✓"
                ][Math.min(variantCount, 5)]}
              </p>
            </div>
          </div>
        </section>

        <section className="apple-card space-y-4">
          <h4 className="title-section mb-0">Model Statistics</h4>
          <div className="space-y-3">
            <StatRow icon={Layers} label="Trained" value={totalTrained} />
            <StatRow icon={Activity} label="Variants" value={totalVariants} />
          </div>
        </section>

        <div className="apple-glass p-4 rounded-apple space-y-3">
          <div className="flex items-center gap-2 text-apple-blue font-bold text-[10px] uppercase tracking-widest">
            <Info size={14} /> Training Tip
          </div>
          <p className="text-[10px] text-apple-gray-300 leading-relaxed">
            For the best realism, draw the same character with slight natural variations in size and slant.
          </p>
        </div>
      </aside>
    </div>
  );
}

function StatRow({ icon: Icon, label, value }: { icon: any, label: string, value: any }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-apple-gray-300">
        <Icon size={12} />
        <span className="text-[10px] font-bold uppercase tracking-tight">{label}</span>
      </div>
      <span className="text-xs font-bold text-white font-mono">{value}</span>
    </div>
  );
}
