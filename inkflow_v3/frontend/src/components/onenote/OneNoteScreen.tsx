import React, { useEffect, useState, useRef } from "react";
import { useStore } from "@/store";
import {
  listCalibrations, createCalibration, deleteCalibration,
  computeCalibration, startWrite, getWriteStatus,
  pauseWrite, resumeWrite, cancelWrite, listProfiles, getProfile,
} from "@/utils/api";
import type { CalibrationProfile, CalibrationPoint, ProfileSummary, WriteRequest, WriteSpeed } from "@/types";
import {
  Crosshair, Play, Pause, Square, Trash2, Plus,
  CheckCircle, AlertCircle, Loader2, Info, Feather,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Unbekannter Fehler";
}

export default function OneNoteScreen() {
  const { activeProfile, setActiveProfile, onenoteText, setOnenoteText,
          calibrations, setCalibrations, activeCalibration, setActiveCalibration,
          writeStatus, setWriteStatus } = useStore();

  const [profiles,     setProfiles]     = useState<ProfileSummary[]>([]);
  const [calName,      setCalName]      = useState("Standard");
  const [speed,        setSpeed]        = useState<WriteSpeed>("normal");
  const [scalingFactor, setScalingFactor] = useState(1.0);
  const [jobId,        setJobId]        = useState<string|null>(null);
  const [calWaiting,   setCalWaiting]   = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>|null>(null);

  useEffect(() => {
    listProfiles().then(setProfiles).catch(() => {});
    listCalibrations().then(setCalibrations).catch(() => {});
  }, []);

  // Listen for calibration results from the overlay window
  useEffect(() => {
    const { inkflow } = window;
    if (!inkflow?.onCalibrationPoints) return;

    inkflow.onCalibrationPoints(async (points: CalibrationPoint[]) => {
      setCalWaiting(false);
      try {
        // Keep this temporary default in sync with backend compute fallback.
        const cal: CalibrationProfile = {
          id: "", name: calName,
          points,
          write_area_x: 0, write_area_y: 0,
          write_area_width: 1200, write_area_height: 800,
          line_height_px: 26, zoom_level: 1.0, transform_matrix: [], created_at: "",
        };
        const saved = await createCalibration(cal);
        await computeCalibration(saved.id);
        const updated = await listCalibrations();
        setCalibrations(updated);
        setActiveCalibration(updated.find(c => c.id === saved.id) ?? null);
        toast.success("Kalibrierung gespeichert!");
      } catch (e: unknown) {
        toast.error("Fehler: " + getErrorMessage(e));
      }
    });

    inkflow.onCalibrationCancelled(() => {
      setCalWaiting(false);
      toast("Kalibrierung abgebrochen");
    });

    return () => {
      inkflow.removeCalibrationListeners?.();
    };
  }, [calName]);

  // Poll write status
  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const s = await getWriteStatus(jobId);
        setWriteStatus(s);
        if (["done","error","cancelled"].includes(s.status)) {
          clearInterval(pollRef.current!);
          if (s.status === "done")      toast.success("Fertig geschrieben!");
          if (s.status === "error")     toast.error("Fehler: " + s.message);
          if (s.status === "cancelled") toast("Abgebrochen");
        }
      } catch {}
    }, 600);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobId]);

  const startCalibration = async () => {
    const { inkflow } = window;
    if (!inkflow?.startCalibration) {
      toast.error("Kalibrierungs-Overlay nur in der Desktop-App verfügbar");
      return;
    }
    setCalWaiting(true);
    toast("Kalibrierungs-Overlay öffnet sich — klicke 4 Ecken in OneNote", { icon: "🎯", duration: 4000 });
    await inkflow.startCalibration();
  };

  const handleStartWrite = async () => {
    if (!activeProfile) return toast.error("Profil wählen");
    if (!activeCalibration) return toast.error("Kalibrierung wählen");
    if (!onenoteText.trim()) return toast.error("Text eingeben");

    const req: WriteRequest = {
      profile_id: activeProfile.id,
      calibration_id: activeCalibration.id,
      text: onenoteText,
      speed,
      font_size_scale: 1.0,
      size_variation: 0.10,
      rotation_variation: 3.0,
      vertical_jitter: 2.0,
      point_delay_s: 0.005,
      pressure: 0.7,
      scaling_factor: scalingFactor,
    };

    try {
      const status = await startWrite(req);
      setJobId(status.job_id);
      setWriteStatus(status);
      toast("Schreibe... (Esc zum Abbrechen)", { icon: "✍️" });
    } catch (e: unknown) {
      toast.error(getErrorMessage(e));
    }
  };

  const isRunning = writeStatus?.status === "running";
  const isPaused  = writeStatus?.status === "paused";

  // Register Esc cancel shortcut
  useEffect(() => {
    const { inkflow } = window;
    if (isRunning || isPaused) {
      inkflow?.registerEscCancel?.();
      inkflow?.onEscPressed?.(() => {
        if (jobId) {
          cancelWrite(jobId).then(() => {
            toast("Abbruch durch Esc");
            setJobId(null);
            setWriteStatus(null);
          });
        }
      });
    } else {
      inkflow?.unregisterEscCancel?.();
      inkflow?.removeEscListeners?.();
    }
    return () => {
      inkflow?.unregisterEscCancel?.();
      inkflow?.removeEscListeners?.();
    };
  }, [isRunning, isPaused, jobId]);

  return (
    <div className="h-full flex overflow-hidden">

      {/* ── Left: Config ── */}
      <aside className="w-64 shrink-0 border-r border-white/5 overflow-y-auto p-4 flex flex-col gap-5">

        {/* Profile */}
        <div>
          <p className="label">Handschriftprofil</p>
          <select className="input" value={activeProfile?.id ?? ""}
            onChange={async e => {
              if (!e.target.value) return;
              try { setActiveProfile(await getProfile(e.target.value)); }
              catch {}
            }}>
            <option value="">— Profil wählen —</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>

        {/* Calibration */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="label mb-0">Kalibrierung</p>
            <button onClick={startCalibration} disabled={calWaiting}
              className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg
                         bg-accent-gold/15 text-accent-gold border border-accent-gold/25
                         hover:bg-accent-gold/25 disabled:opacity-40 transition-all">
              {calWaiting ? <><Loader2 size={11} className="animate-spin"/>Warte...</>
                          : <><Plus size={11}/>Neu</>}
            </button>
          </div>

          {/* Calibration name input */}
          <div className="mb-2">
            <input
              type="text"
              className="input text-xs"
              placeholder="Name der Kalibrierung"
              value={calName}
              onChange={e => setCalName(e.target.value)}
            />
          </div>

          {calWaiting && (
            <div className="glass rounded-xl p-3 mb-2 text-center animate-fade-in">
              <Crosshair size={20} className="mx-auto mb-2 text-accent-gold animate-pulse-soft"/>
              <p className="text-xs text-ink-300">Transparentes Overlay ist geöffnet</p>
              <p className="text-[11px] text-ink-500 mt-1">Klicke 4 Ecken: oben-links, oben-rechts, unten-rechts, unten-links</p>
            </div>
          )}

          {calibrations.length === 0 && !calWaiting ? (
            <p className="text-xs text-ink-500 leading-relaxed">
              Noch keine Kalibrierung. Klicke „Neu" und folge den Anweisungen.
            </p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {calibrations.map(c => (
                <div key={c.id}
                  onClick={() => setActiveCalibration(c)}
                  className={clsx(
                    "flex items-center justify-between px-3 py-2 rounded-xl border cursor-pointer transition-all text-xs",
                    activeCalibration?.id === c.id
                      ? "border-accent-gold/40 bg-accent-gold/10 text-accent-gold"
                      : "border-white/8 text-ink-300 hover:border-white/20 hover:bg-white/5",
                  )}>
                  <div>
                    <span className="font-medium">{c.name}</span>
                    <span className="text-ink-500 ml-2">Linie: {c.line_height_px}px</span>
                  </div>
                  <button onClick={e => { e.stopPropagation(); deleteCalibration(c.id).then(() => listCalibrations().then(setCalibrations)); }}
                    className="p-1 rounded text-ink-500 hover:text-red-400 transition-colors">
                    <Trash2 size={11}/>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Speed */}
        <div>
          <p className="label">Schreibgeschwindigkeit</p>
          <div className="flex gap-1.5">
            {(["slow","normal","fast"] as const).map((s: WriteSpeed) => (
              <button key={s} onClick={() => setSpeed(s)}
                className={clsx("flex-1 py-1.5 rounded-lg text-xs border transition-all",
                  speed === s
                    ? "bg-accent-gold/15 text-accent-gold border-accent-gold/30"
                    : "bg-white/5 text-ink-400 border-white/8 hover:bg-white/10")}>
                {s === "slow" ? "Langsam" : s === "normal" ? "Normal" : "Schnell"}
              </button>
            ))}
          </div>
        </div>

        {/* Scaling */}
        <div>
          <p className="label">Bildschirm-Skalierung</p>
          <div className="flex items-center gap-2">
            <input 
              type="range" min="1" max="2.5" step="0.25"
              className="flex-1 accent-accent-gold h-1.5 bg-white/5 rounded-lg appearance-none cursor-pointer"
              value={scalingFactor}
              onChange={e => setScalingFactor(parseFloat(e.target.value))}
            />
            <span className="text-[11px] font-mono text-ink-300 w-10 text-right">
              {Math.round(scalingFactor * 100)}%
            </span>
          </div>
          <p className="text-[10px] text-ink-500 mt-1">Standard: 100%. Bei Windows-Skalierung (z.B. 150%) anpassen.</p>
        </div>

        {/* Info */}
        <div className="glass rounded-xl p-3 text-[11px] text-ink-400 leading-relaxed">
          <div className="flex gap-2">
            <Info size={12} className="text-accent-gold shrink-0 mt-0.5"/>
            <span>
              Öffne OneNote, klicke „Neu" für die Kalibrierung.
              Ein transparentes Overlay erscheint — klicke oben-links
              , oben-rechts, unten-rechts und unten-links auf deine Schreibfläche.
            </span>
          </div>
        </div>
      </aside>

      {/* ── Center: Text + Controls ── */}
      <main className="flex-1 flex flex-col">

        {/* Toolbar */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5 shrink-0">
          <div className="flex items-center gap-2 text-sm text-ink-400">
            <Feather size={15} className="text-accent-gold"/>
            <span className="font-medium text-white">OneNote Writer</span>
          </div>
          <div className="flex-1"/>

          {/* Write controls */}
          {!isRunning && !isPaused && (
            <button onClick={handleStartWrite}
              disabled={!activeProfile || !activeCalibration || !onenoteText.trim()}
              className="btn-primary">
              <Play size={14}/>
              Start Writing
            </button>
          )}
          {isRunning && (
            <>
              <button onClick={() => jobId && pauseWrite(jobId)} className="btn-ghost">
                <Pause size={14}/>Pause
              </button>
              <button onClick={() => jobId && cancelWrite(jobId)} className="btn-danger">
                <Square size={14}/>Stop
              </button>
            </>
          )}
          {isPaused && (
            <>
              <button onClick={() => jobId && resumeWrite(jobId)} className="btn-primary">
                <Play size={14}/>Weiter
              </button>
              <button onClick={() => jobId && cancelWrite(jobId)} className="btn-danger">
                <Square size={14}/>Stop
              </button>
            </>
          )}
        </div>

        {/* Status bar */}
        {writeStatus && !["idle"].includes(writeStatus.status) && (
          <div className={clsx(
            "px-5 py-2 border-b border-white/5 flex items-center gap-3 text-xs shrink-0",
            writeStatus.status === "done"   ? "bg-emerald-500/8"  :
            writeStatus.status === "error"  ? "bg-red-500/8"      :
            writeStatus.status === "running"? "bg-accent-gold/5"  : "bg-white/3",
          )}>
            {writeStatus.status === "running"   && <Loader2 size={13} className="animate-spin text-accent-gold"/>}
            {writeStatus.status === "done"       && <CheckCircle size={13} className="text-emerald-400"/>}
            {writeStatus.status === "error"      && <AlertCircle size={13} className="text-red-400"/>}
            {writeStatus.status === "paused"     && <Pause size={13} className="text-amber-400"/>}
            {writeStatus.status === "cancelled"  && <Square size={13} className="text-ink-400"/>}

            <span className="text-ink-200">{writeStatus.message}</span>

            <div className="flex-1 h-1 bg-white/8 rounded-full overflow-hidden">
              <div className="h-full bg-accent-gold rounded-full transition-all duration-300"
                style={{ width: `${writeStatus.progress * 100}%` }}/>
            </div>

            <span className="text-ink-400 font-mono">
              {writeStatus.chars_done}/{writeStatus.chars_total}
            </span>
          </div>
        )}

        {/* Text input */}
        <div className="flex-1 p-5">
          <textarea
            className="input h-full resize-none font-serif text-sm leading-relaxed"
            placeholder={"Text der in OneNote geschrieben werden soll…\n\nInkFlow simuliert echte Schreibbewegungen mit deiner Handschrift.\nJeder Buchstabe wird einzeln mit der Maus gezeichnet."}
            value={onenoteText}
            onChange={e => setOnenoteText(e.target.value)}
            disabled={isRunning || isPaused}
          />
        </div>
      </main>

      {/* ── Right: Status ── */}
      <aside className="w-52 shrink-0 border-l border-white/5 p-4 flex flex-col gap-4 overflow-y-auto">
        <div>
          <p className="label">Status</p>
          <div className="flex flex-col gap-2 text-xs">
            <StatusRow label="Profil"       value={activeProfile?.name ?? "—"} ok={!!activeProfile}/>
            <StatusRow label="Kalibrierung" value={activeCalibration?.name ?? "—"} ok={!!activeCalibration}/>
            <StatusRow label="Text"         value={`${onenoteText.length} Zeichen`} ok={onenoteText.length>0}/>
            <StatusRow label="Geschwindigkeit" value={speed} ok={true}/>
          </div>
        </div>

        {activeCalibration && (
          <div>
            <p className="label">Kalibrierung</p>
            <div className="text-[11px] text-ink-400 space-y-1">
              <div className="flex justify-between"><span>Zeilenhöhe</span><span className="font-mono">{activeCalibration.line_height_px}px</span></div>
              <div className="flex justify-between"><span>Breite</span><span className="font-mono">{activeCalibration.write_area_width}px</span></div>
              <div className="flex justify-between"><span>Zoom</span><span className="font-mono">{activeCalibration.zoom_level}×</span></div>
            </div>
          </div>
        )}

        <div className="mt-auto">
          <p className="label">Hinweise</p>
          <div className="text-[11px] text-ink-500 space-y-1">
            <p>Maus → Ecke = Notbremse</p>
            <p>Schreibt in aktives Fenster</p>
            <p>OneNote vorher öffnen</p>
            <p><kbd className="bg-white/5 px-1 rounded border border-white/10 font-mono">Esc</kbd> = Schreiben abbrechen</p>
          </div>
        </div>
      </aside>
    </div>
  );
}

function StatusRow({ label, value, ok }: { label:string; value:string; ok:boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-ink-500">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className={clsx("truncate max-w-24", ok ? "text-ink-200" : "text-ink-500")}>{value}</span>
        <div className={clsx("w-1.5 h-1.5 rounded-full shrink-0", ok ? "bg-emerald-400" : "bg-ink-600")}/>
      </div>
    </div>
  );
}
