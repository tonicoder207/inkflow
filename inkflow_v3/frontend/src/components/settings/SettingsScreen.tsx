import React from "react";
import { Server, Info, Lightbulb, ShieldCheck, Cpu, Code2 } from "lucide-react";

export default function SettingsScreen() {
  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fade-in pb-20">
      <header>
        <h2 className="title-large">System Settings</h2>
        <p className="text-apple-gray-300 text-lg">Configure the handwriting engine and system preferences.</p>
      </header>

      <div className="grid grid-cols-1 gap-6">
        {/* Backend Section */}
        <section className="apple-card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
              <Cpu size={18} />
            </div>
            <h3 className="font-bold text-white">Handwriting Engine</h3>
          </div>
          <p className="text-xs text-apple-gray-300 leading-relaxed">
            InkFlow requires the Python backend running on <code className="bg-black px-1.5 py-0.5 rounded text-apple-blue font-bold">localhost:8000</code>. 
            In the desktop app, this starts automatically.
          </p>
          <div className="bg-black/40 rounded-apple-sm p-4 font-mono text-[11px] text-apple-gray-100 border border-white/5 space-y-1">
            <div className="text-apple-gray-400"># Start manually if needed:</div>
            <div className="flex gap-2"><span className="text-apple-blue">$</span> cd backend</div>
            <div className="flex gap-2"><span className="text-apple-blue">$</span> python main.py</div>
          </div>
        </section>

        {/* Tips Section */}
        <section className="apple-card space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
              <Lightbulb size={18} />
            </div>
            <h3 className="font-bold text-white">OneNote Best Practices</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              "Open OneNote and click the first line before starting.",
              "Set OneNote zoom to exactly 100% for best results.",
              "Re-calibrate if you resize the OneNote window.",
              "Safety: Move cursor to screen corner to emergency stop.",
              "Train at least 3 variations per character for realism.",
            ].map((t, i) => (
              <div key={i} className="flex gap-3 items-start p-3 bg-white/5 rounded-apple-sm">
                <span className="text-apple-blue font-bold text-xs shrink-0">0{i+1}</span>
                <p className="text-[11px] text-apple-gray-200 leading-normal">{t}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Security Section */}
        <section className="apple-card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
              <ShieldCheck size={18} />
            </div>
            <h3 className="font-bold text-white">Privacy & Data</h3>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-1 space-y-1">
              <p className="text-xs text-white font-medium">100% Local Processing</p>
              <p className="text-[11px] text-apple-gray-400 leading-relaxed">
                Your handwriting data, profiles, and exports never leave your machine. No cloud, no tracking, no AI training on your personal data.
              </p>
            </div>
          </div>
        </section>

        {/* Version Info */}
        <div className="flex flex-col items-center gap-2 pt-10">
          <div className="w-12 h-12 rounded-apple-sm bg-white/5 flex items-center justify-center text-apple-gray-300">
            <Code2 size={24} />
          </div>
          <p className="text-[10px] font-bold text-apple-gray-400 uppercase tracking-[0.3em]">InkFlow v3.0 Pro</p>
          <p className="text-[10px] text-apple-gray-500">Built for Windows Precision Ink</p>
        </div>
      </div>
    </div>
  );
}
