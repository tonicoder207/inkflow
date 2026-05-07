import React from "react";
import { useStore } from "@/store";
import { PenLine, BookOpen, Settings, Feather, Wifi, WifiOff } from "lucide-react";
import clsx from "clsx";
import type { AppScreen } from "@/types";

const NAV: {id:AppScreen;label:string;icon:React.ReactNode}[] = [
  { id:"landing",  label:"Projekte",  icon:<BookOpen size={14}/> },
  { id:"editor",   label:"Editor",    icon:<PenLine size={14}/> },
  { id:"onenote",  label:"OneNote",   icon:<Feather size={14}/> },
  { id:"settings", label:"Einstellungen", icon:<Settings size={14}/> },
];

export default function AppShell({ children, online }: { children:React.ReactNode; online:boolean|null }) {
  const { screen, setScreen } = useStore();
  return (
    <div className="flex flex-col h-screen bg-[#0c0c1a] overflow-hidden">
      <header className="flex items-center justify-between px-5 h-11 shrink-0 border-b border-white/5 select-none">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-accent-gold/20 border border-accent-gold/40 flex items-center justify-center">
            <PenLine size={12} className="text-accent-gold"/>
          </div>
          <span className="font-display font-semibold text-sm text-white/90">InkFlow</span>
        </div>
        <nav className="flex gap-1">
          {NAV.map(n => (
            <button key={n.id} onClick={()=>setScreen(n.id)}
              className={clsx("flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all",
                screen===n.id
                  ? "bg-accent-gold/15 text-accent-gold border border-accent-gold/25"
                  : "text-ink-300 hover:text-white hover:bg-white/5")}>
              {n.icon}{n.label}
            </button>
          ))}
        </nav>
        <div className="text-xs">
          {online===null && <span className="text-ink-500 animate-pulse-soft">Verbinde…</span>}
          {online===true  && <span className="flex items-center gap-1 text-emerald-400"><Wifi size={11}/>Online</span>}
          {online===false && <span className="flex items-center gap-1 text-red-400"><WifiOff size={11}/>Offline</span>}
        </div>
      </header>
      <main className="flex-1 overflow-hidden animate-fade-in">{children}</main>
    </div>
  );
}
