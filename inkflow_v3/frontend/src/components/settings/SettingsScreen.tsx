import React from "react";
import { Server, Info, Lightbulb } from "lucide-react";

export default function SettingsScreen() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-xl mx-auto px-8 py-10 flex flex-col gap-4 animate-slide-up">
        <h1 className="font-display text-2xl font-bold text-white mb-2">Einstellungen</h1>

        <div className="panel">
          <div className="flex items-center gap-2 mb-3"><Server size={15} className="text-accent-gold"/><h2 className="text-sm font-medium text-white">Backend</h2></div>
          <p className="text-xs text-ink-400 mb-3 leading-relaxed">
            InkFlow benötigt das Python-Backend auf <code className="text-accent-gold">localhost:8000</code>.
            Im installierten Desktop-Modus startet es automatisch.
          </p>
          <div className="bg-black/30 rounded-xl p-3 font-mono text-xs text-emerald-400 border border-white/8">
            <div>cd backend</div>
            <div>pip install -r requirements.txt</div>
            <div>python main.py</div>
          </div>
        </div>

        <div className="panel">
          <div className="flex items-center gap-2 mb-3"><Lightbulb size={15} className="text-accent-gold"/><h2 className="text-sm font-medium text-white">OneNote Tipps</h2></div>
          <ul className="text-xs text-ink-400 space-y-2">
            {[
              "OneNote vor dem Schreiben öffnen und auf die erste Zeile klicken.",
              "Zoom in OneNote auf 100% stellen für beste Ergebnisse.",
              "Kalibrierung einmal pro OneNote-Fenster-Größe durchführen.",
              "Maus in die obere linke Bildschirmecke = sofortiger Stopp.",
              "Für beste Ergebnisse: Alphabet komplett trainieren (3+ Varianten).",
            ].map((t,i) => (
              <li key={i} className="flex gap-2"><span className="text-accent-gold/60 shrink-0">›</span>{t}</li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="flex items-center gap-2 mb-3"><Info size={15} className="text-accent-gold"/><h2 className="text-sm font-medium text-white">Über InkFlow v3</h2></div>
          <p className="text-xs text-ink-400 leading-relaxed">
            InkFlow 3.0 — Handschrift-Generator mit OneNote-Integration.<br/>
            Vollständig lokal. Keine Cloud, kein Login, kein Tracking.<br/>
            Profile und Exports werden im App-Datenordner gespeichert.
          </p>
        </div>
      </div>
    </div>
  );
}
