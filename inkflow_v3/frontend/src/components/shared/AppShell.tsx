import React from "react";
import { useStore } from "@/store";
import { 
  LayoutDashboard, 
  PenTool, 
  Settings, 
  Layers, 
  Wifi, 
  WifiOff, 
  AppWindow 
} from "lucide-react";
import clsx from "clsx";
import type { AppScreen } from "@/types";

const NAV: {id: AppScreen; label: string; icon: React.ElementType}[] = [
  { id: "landing",  label: "Dashboard",   icon: LayoutDashboard },
  { id: "editor",   label: "Editor",      icon: PenTool },
  { id: "onenote",  label: "OneNote",     icon: Layers },
  { id: "settings", label: "Settings",    icon: Settings },
];

export default function AppShell({ children, online }: { children: React.ReactNode; online: boolean | null }) {
  const { screen, setScreen } = useStore();
  
  return (
    <div className="flex h-screen bg-black text-apple-gray-50 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 apple-glass border-r border-white/5 flex flex-col shrink-0">
        {/* App Branding */}
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-apple-sm bg-gradient-to-tr from-apple-blue to-indigo-400 flex items-center justify-center shadow-lg shadow-apple-blue/20">
            <AppWindow size={22} className="text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight leading-tight">InkFlow</h1>
            <p className="text-[10px] text-apple-gray-300 font-medium uppercase tracking-widest">v3.0 Pro</p>
          </div>
        </div>

        {/* Main Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const isActive = screen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setScreen(item.id)}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-apple-sm text-sm font-medium transition-all duration-200 group",
                  isActive 
                    ? "bg-white/10 text-white shadow-inner" 
                    : "text-apple-gray-300 hover:bg-white/5 hover:text-white"
                )}
              >
                <Icon 
                  size={18} 
                  className={clsx(
                    "transition-colors",
                    isActive ? "text-apple-blue" : "text-apple-gray-300 group-hover:text-apple-gray-200"
                  )} 
                />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Connection Status Footer */}
        <div className="p-4 border-t border-white/5">
          <div className="flex items-center gap-3 px-4 py-3 rounded-apple-sm bg-white/5 text-[11px] font-medium">
            {online === null && (
              <>
                <div className="w-2 h-2 rounded-full bg-apple-gray-300 animate-pulse" />
                <span className="text-apple-gray-300">Connecting to API...</span>
              </>
            )}
            {online === true && (
              <>
                <div className="w-2 h-2 rounded-full bg-apple-system-green shadow-sm shadow-apple-system-green/50" />
                <span className="text-apple-gray-200">System Ready</span>
              </>
            )}
            {online === false && (
              <>
                <div className="w-2 h-2 rounded-full bg-apple-system-red" />
                <span className="text-apple-system-red">Offline Mode</span>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {/* Subtle Window Gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-apple-blue/5 via-transparent to-transparent pointer-events-none" />
        
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-8 animate-fade-in relative z-10">
          {children}
        </div>
      </main>
    </div>
  );
}
