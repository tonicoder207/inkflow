import React, { useEffect, useState, useRef } from "react";
import { useStore } from "@/store";
import {
  listCalibrations, createCalibration, deleteCalibration,
  computeCalibration, startWrite, getWriteStatus,
  pauseWrite, resumeWrite, cancelWrite, listProfiles, getProfile,
} from "@/utils/api";
import type { CalibrationProfile, CalibrationPoint, ProfileSummary, WriteRequest, WriteSpeed } from "@/types";
import {
  Crosshair, 
  Play, 
  Pause, 
  Square, 
  Trash2, 
  Plus,
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Info, 
  Layers,
  Monitor,
  Zap,
  ChevronRight,
  Settings
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

export default function OneNoteScreen() {
  const { 
    activeProfile, setActiveProfile, onenoteText, setOnenoteText,
    calibrations, setCalibrations, activeCalibration, setActiveCalibration,
    writeStatus, setWriteStatus 
  } = useStore();

  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [calName, setCalName] = useState("Surface Setup");
  const [wordsPerSecond, setWordsPerSecond] = useState(1.5);
  const [scalingFactor, setScalingFactor] = useState(1.0);
  const [jobId, setJobId] = useState<string|null>(null);
  const [calWaiting, setCalWaiting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>|null>(null);

  useEffect(() => {
    listProfiles().then(setProfiles).catch(() => {});
    listCalibrations().then(setCalibrations).catch(() => {});
  }, []);

  useEffect(() => {
    const { inkflow } = window;
    if (!inkflow?.onCalibrationPoints) return;

    inkflow.onCalibrationPoints(async (points: CalibrationPoint[]) => {
      setCalWaiting(false);
      try {
        const cal: CalibrationProfile = {
          id: "", name: calName,
          points,
          write_area_x: 0, write_area_y: 0,
          write_area_width: 1200, write_area_height: 800,
          line_height_px: 26, zoom_level: 1.0, transform_matrix: [], created_at: "",
          first_line_y: 0, second_line_y: 0,
        };
        const saved = await createCalibration(cal);
        await computeCalibration(saved.id);
        const updated = await listCalibrations();
        setCalibrations(updated);
        setActiveCalibration(updated.find(c => c.id === saved.id) ?? null);
        toast.success("Calibration profile saved");
      } catch (e: any) {
        toast.error("Calibration error: " + e.message);
      }
    });

    inkflow.onCalibrationCancelled(() => {
      setCalWaiting(false);
      toast("Calibration cancelled");
    });

    return () => { inkflow.removeCalibrationListeners?.(); };
  }, [calName]);

  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const s = await getWriteStatus(jobId);
        setWriteStatus(s);
        if (["done","error","cancelled"].includes(s.status)) {
          clearInterval(pollRef.current!);
          if (s.status === "done") toast.success("Finished writing to OneNote!");
          if (s.status === "error") toast.error("Write error: " + s.message);
          if (s.status === "cancelled") toast("Writing cancelled");
        }
      } catch {}
    }, 600);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobId]);

  const startCalibration = async () => {
    const { inkflow } = window;
    if (!inkflow?.startCalibration) return toast.error("Overlay only available in Desktop App");
    setCalWaiting(true);
    toast("Click the 4 corners of your OneNote writing area", { icon: "🎯" });
    await inkflow.startCalibration();
  };

  const handleStartWrite = async () => {
    if (!activeProfile) return toast.error("Choose a profile first");
    if (!activeCalibration) return toast.error("Calibrate OneNote first");
    if (!onenoteText.trim()) return toast.error("Enter text to write");

    const req: WriteRequest = {
      profile_id: activeProfile.id,
      calibration_id: activeCalibration.id,
      text: onenoteText,
      speed: "normal",
      words_per_second: wordsPerSecond,
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
    } catch (e: any) { toast.error(e.message); }
  };

  const isRunning = writeStatus?.status === "running";
  const isPaused  = writeStatus?.status === "paused";

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8 animate-fade-in pb-20">
      
      {/* Writing Progress (Dynamic Island Style) */}
      {(isRunning || isPaused) && writeStatus && (
        <div className="dynamic-island w-[400px] gap-4">
          <div className="w-8 h-8 rounded-full bg-apple-blue/20 flex items-center justify-center">
            {isRunning ? <Loader2 size={16} className="animate-spin text-apple-blue" /> : <Pause size={14} className="text-apple-blue" />}
          </div>
          <div className="flex-1">
            <div className="flex justify-between text-[10px] font-bold text-apple-gray-300 uppercase mb-1">
              <span>{writeStatus.status === "paused" ? "Paused" : "Writing to OneNote"}</span>
              <span>{Math.round(writeStatus.progress * 100)}%</span>
            </div>
            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-apple-blue rounded-full transition-all" style={{ width: `${writeStatus.progress * 100}%` }} />
            </div>
          </div>
          <div className="flex gap-2">
            {isPaused ? (
              <button onClick={() => jobId && resumeWrite(jobId)} className="p-1.5 hover:text-apple-system-green transition-colors"><Play size={16} fill="currentColor"/></button>
            ) : (
              <button onClick={() => jobId && pauseWrite(jobId)} className="p-1.5 hover:text-white transition-colors"><Pause size={16}/></button>
            )}
            <button onClick={() => jobId && cancelWrite(jobId)} className="p-1.5 hover:text-apple-system-red transition-colors"><Square size={16} fill="currentColor"/></button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="flex items-end justify-between">
        <div className="space-y-1">
          <h2 className="title-large flex items-center gap-3">
            OneNote Writer <Layers className="text-apple-blue" size={28} />
          </h2>
          <p className="text-apple-gray-300 text-lg">Inject handwriting directly into your digital notebook.</p>
        </div>
        <button 
          onClick={handleStartWrite}
          disabled={!activeProfile || !activeCalibration || !onenoteText.trim() || isRunning}
          className="btn-apple-primary min-w-[180px] py-4"
        >
          {isRunning ? <><Loader2 size={18} className="animate-spin" /> Working...</> : <><Zap size={18} fill="currentColor" /> Start Writing</>}
        </button>
      </header>

      <div className="grid grid-cols-12 gap-8">
        {/* Left: Setup & Calibration */}
        <div className="col-span-4 space-y-6">
          <section className="apple-card space-y-6">
            <div>
              <h4 className="title-section">1. Target Model</h4>
              <select 
                className="apple-input bg-white/5" 
                value={activeProfile?.id ?? ""}
                onChange={async e => {
                  if (!e.target.value) return;
                  try { setActiveProfile(await getProfile(e.target.value)); } catch {}
                }}
              >
                <option value="">— Select Profile —</option>
                {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="title-section mb-0">2. Screen Mapping</h4>
                <button 
                  onClick={startCalibration} 
                  disabled={calWaiting}
                  className="text-xs font-bold text-apple-blue hover:underline flex items-center gap-1"
                >
                  <Plus size={14}/> Add New
                </button>
              </div>

              {calWaiting ? (
                <div className="bg-apple-blue/10 border border-apple-blue/20 rounded-apple-sm p-4 text-center space-y-3 animate-pulse">
                  <Crosshair className="mx-auto text-apple-blue" size={24} />
                  <p className="text-[11px] font-bold text-apple-blue uppercase tracking-widest">Calibration Mode Active</p>
                  <p className="text-[10px] text-apple-gray-200">Click the 4 corners of your OneNote area in order.</p>
                </div>
              ) : calibrations.length === 0 ? (
                <div className="bg-white/5 rounded-apple-sm p-4 text-center border border-dashed border-white/10">
                  <p className="text-[11px] text-apple-gray-400 font-medium">No calibration profiles found.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {calibrations.map(c => (
                    <div 
                      key={c.id}
                      onClick={() => setActiveCalibration(c)}
                      className={clsx(
                        "group flex items-center justify-between p-3 rounded-apple-sm border transition-all cursor-pointer",
                        activeCalibration?.id === c.id 
                          ? "bg-apple-blue/10 border-apple-blue/30 text-white" 
                          : "bg-white/5 border-white/5 text-apple-gray-300 hover:bg-white/10"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <Monitor size={14} className={activeCalibration?.id === c.id ? "text-apple-blue" : "text-apple-gray-400"} />
                        <span className="text-xs font-bold">{c.name}</span>
                      </div>
                      <button 
                        onClick={e => { e.stopPropagation(); deleteCalibration(c.id).then(() => listCalibrations().then(setCalibrations)); }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-apple-system-red transition-all"
                      >
                        <Trash2 size={12}/>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className="apple-card space-y-6">
            <h4 className="title-section">Advanced Controls</h4>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-[11px] font-bold uppercase tracking-tight mb-2">
                  <span className="text-apple-gray-300">Writing Cadence</span>
                  <span className="text-apple-blue">{wordsPerSecond} w/s</span>
                </div>
                <input 
                  type="range" min="0.1" max="5.0" step="0.1"
                  className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-apple-blue"
                  value={wordsPerSecond}
                  onChange={e => setWordsPerSecond(parseFloat(e.target.value))}
                />
              </div>

              <div>
                <div className="flex justify-between text-[11px] font-bold uppercase tracking-tight mb-2">
                  <span className="text-apple-gray-300">Display Scaling</span>
                  <span className="text-apple-blue">{Math.round(scalingFactor * 100)}%</span>
                </div>
                <input 
                  type="range" min="1" max="2.5" step="0.25"
                  className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-apple-blue"
                  value={scalingFactor}
                  onChange={e => setScalingFactor(parseFloat(e.target.value))}
                />
              </div>
            </div>
          </section>

          <div className="p-5 apple-glass border-white/5 rounded-apple flex gap-4 items-start">
            <Info className="text-apple-blue shrink-0" size={18} />
            <div className="space-y-1">
              <p className="text-[11px] font-bold text-white uppercase tracking-tight">Security Fail-Safe</p>
              <p className="text-[10px] text-apple-gray-300 leading-relaxed">
                Move your cursor to any screen corner or press <kbd className="bg-black px-1 border border-white/10">ESC</kbd> to immediately stop the writer.
              </p>
            </div>
          </div>
        </div>

        {/* Right: Text Input */}
        <div className="col-span-8 space-y-6">
          <div className="apple-card p-0 flex flex-col h-[500px] overflow-hidden">
            <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className={clsx("transition-colors", onenoteText.length > 0 ? "text-apple-system-green" : "text-apple-gray-400")} size={16} />
                <span className="text-xs font-bold uppercase tracking-widest text-apple-gray-200">Content Engine</span>
              </div>
              <div className="text-[10px] font-bold text-apple-gray-400 uppercase tracking-widest">
                {onenoteText.length} Characters
              </div>
            </div>
            <textarea 
              className="flex-1 w-full bg-transparent p-8 outline-none text-xl leading-relaxed text-apple-gray-100 placeholder:text-apple-gray-400/20 font-medium resize-none"
              placeholder="Paste or type the text you want InkFlow to write into OneNote..."
              value={onenoteText} 
              onChange={e => setOnenoteText(e.target.value)}
              disabled={isRunning || isPaused}
            />
          </div>

          <div className="grid grid-cols-3 gap-6">
            <div className="apple-card p-5 space-y-2">
              <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
                <CheckCircle size={16} />
              </div>
              <h5 className="text-xs font-bold">Calibration</h5>
              <p className="text-[10px] text-apple-gray-400">{activeCalibration ? "Active: " + activeCalibration.name : "Mapping required"}</p>
            </div>
            <div className="apple-card p-5 space-y-2">
              <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
                <Monitor size={16} />
              </div>
              <h5 className="text-xs font-bold">Scaling</h5>
              <p className="text-[10px] text-apple-gray-400">Fixed at {Math.round(scalingFactor * 100)}% DPI</p>
            </div>
            <div className="apple-card p-5 space-y-2">
              <div className="w-8 h-8 rounded-full bg-apple-blue/10 flex items-center justify-center text-apple-blue">
                <Zap size={16} />
              </div>
              <h5 className="text-xs font-bold">Ready</h5>
              <p className="text-[10px] text-apple-gray-400">Engine in standby mode</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
