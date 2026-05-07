import React, { useState, useEffect } from "react";
import { useStore } from "@/store";
import { renderText, exportRender, listProfiles, getProfile } from "@/utils/api";
import type { PaperType, ProfileSummary, RenderSettings } from "@/types";
import { 
  ArrowLeft, 
  Play, 
  Download, 
  Loader2, 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  FileText, 
  Image as Img, 
  FolderOpen, 
  CheckCircle,
  Settings2,
  Maximize2,
  MoreHorizontal
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

const PAPERS = [
  { id: "lined", l: "Lined" },
  { id: "blank", l: "Blank" },
  { id: "grid", l: "Grid" },
  { id: "dot", l: "Dot" }
] as const;

const PAPERS_COLORS = ["#fdf6e3", "#fafaf9", "#f5ead0", "#f0f4ff"];
const INK_COLORS = ["#1D1D1F", "#004080", "#602020", "#104010"];

export default function EditorScreen() {
  const { 
    setScreen, activeProfile, setActiveProfile, editorText, setEditorText,
    paperStyle, setPaperStyle, renderResult, setRenderResult, isRendering, setIsRendering 
  } = useStore();
  
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [page, setPage] = useState(0);
  const [zoom, setZoom] = useState(0.45);
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [inkColor, setInkColor] = useState("#1D1D1F");
  const [sizeVar, setSizeVar] = useState(0.12);
  const [rotVar, setRotVar] = useState(4.0);
  const [vjit, setVjit] = useState(3.0);
  const [fscale, setFscale] = useState(1.0);
  const [showInspector, setShowInspector] = useState(true);

  useEffect(() => { listProfiles().then(setProfiles).catch(() => {}); }, []);

  const build = (): RenderSettings => ({
    profile_id: activeProfile!.id, 
    text: editorText, 
    paper: paperStyle,
    size_variation: sizeVar, 
    rotation_variation: rotVar, 
    vertical_jitter: vjit,
    spacing_variation: 0.15, 
    ink_pressure_variation: 0.1, 
    word_break_probability: 0.02,
    font_size_scale: fscale,
  });

  const handleRender = async () => {
    if (!activeProfile) return toast.error("Please select a profile");
    if (!editorText.trim()) return toast.error("Please enter some text");
    setIsRendering(true); 
    setRenderResult(null); 
    setPage(0);
    try { 
      setRenderResult(await renderText(build())); 
      toast.success("Handwriting generated successfully");
    }
    catch (e: any) { toast.error(e.message); }
    finally { setIsRendering(false); }
  };

  const handleExport = async (fmt: string) => {
    if (!renderResult) return;
    setExporting(true);
    setExportProgress(0);

    const progressInterval = setInterval(() => {
      setExportProgress(p => Math.min(p + 10, 95));
    }, 150);

    try {
      const r = await exportRender(renderResult.render_id, fmt);
      clearInterval(progressInterval);
      setExportProgress(100);

      toast.success(
        (t) => (
          <div className="flex flex-col gap-2">
            <p className="font-bold text-sm">Export Successful</p>
            <p className="text-xs opacity-80">{r.filename}</p>
            <button
              onClick={() => {
                try { window.inkflow?.openExportsFolder?.(); } catch {}
                toast.dismiss(t.id);
              }}
              className="flex items-center gap-1.5 text-xs text-apple-blue font-bold hover:underline mt-1"
            >
              <FolderOpen size={12}/> View in Explorer
            </button>
          </div>
        )
      );

      setTimeout(() => {
        setExporting(false);
        setExportProgress(0);
      }, 3000);
    } catch (e: any) {
      clearInterval(progressInterval);
      toast.error(e.message);
      setExporting(false);
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Top Action Bar */}
      <nav className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setScreen("landing")} 
            className="btn-apple-secondary px-3 py-3"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h3 className="font-bold text-white leading-tight">Composition Studio</h3>
            <p className="text-[10px] text-apple-gray-300 font-bold uppercase tracking-widest">
              {activeProfile?.name || "No Profile Selected"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleRender} 
            disabled={!activeProfile || !editorText.trim() || isRendering} 
            className="btn-apple-primary min-w-[140px]"
          >
            {isRendering ? (
              <><Loader2 size={16} className="animate-spin" /> Rendering...</>
            ) : (
              <><Play size={16} fill="currentColor" /> Generate Ink</>
            )}
          </button>
          <div className="w-px h-8 bg-white/10 mx-2" />
          <button 
            onClick={() => setShowInspector(!showInspector)}
            className={clsx(
              "btn-apple-secondary px-3 py-3",
              showInspector && "bg-white/10 text-apple-blue"
            )}
          >
            <Settings2 size={18} />
          </button>
        </div>
      </nav>

      {/* Main Workspace */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Left: Input Area */}
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex-1 apple-card p-0 overflow-hidden relative group">
            <textarea 
              className="w-full h-full bg-transparent p-10 outline-none text-xl leading-relaxed text-apple-gray-100 placeholder:text-apple-gray-400/30 font-medium resize-none"
              placeholder="Start typing your letter here..."
              value={editorText} 
              onChange={e => setEditorText(e.target.value)}
            />
            <div className="absolute bottom-6 right-8 text-[11px] font-bold text-apple-gray-300 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
              {editorText.length} Characters
            </div>
          </div>
          
          {/* Export Status (Dynamic Island Style) */}
          {exporting && (
            <div className="apple-card py-3 px-5 flex items-center gap-4 animate-scale-in">
              {exportProgress < 100 ? (
                <Loader2 size={18} className="animate-spin text-apple-blue" />
              ) : (
                <CheckCircle size={18} className="text-apple-system-green" />
              )}
              <div className="flex-1 space-y-1">
                <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                  <span className={exportProgress === 100 ? "text-apple-system-green" : "text-apple-gray-300"}>
                    {exportProgress === 100 ? "Export Finished" : "Processing Export..."}
                  </span>
                  <span className="text-white">{exportProgress}%</span>
                </div>
                <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className={clsx(
                      "h-full rounded-full transition-all duration-300",
                      exportProgress === 100 ? "bg-apple-system-green" : "bg-apple-blue"
                    )}
                    style={{ width: `${exportProgress}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Middle/Right: Preview & Controls */}
        <div className={clsx(
          "flex flex-col gap-6 transition-all duration-500 ease-apple",
          showInspector ? "w-[400px]" : "w-0 opacity-0 invisible"
        )}>
          {/* Preview Panel */}
          <div className="h-[350px] apple-card p-0 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <h4 className="title-section mb-0">Live Preview</h4>
              <div className="flex items-center gap-1 bg-black/30 rounded-full px-2 py-1">
                <button onClick={() => setZoom(z => Math.max(0.2, z-0.1))} className="p-1 hover:text-apple-blue transition-colors"><ZoomOut size={12}/></button>
                <span className="text-[10px] font-bold w-10 text-center">{Math.round(zoom*100)}%</span>
                <button onClick={() => setZoom(z => Math.min(1.5, z+0.1))} className="p-1 hover:text-apple-blue transition-colors"><ZoomIn size={12}/></button>
              </div>
            </div>
            
            <div className="flex-1 overflow-auto bg-black/40 flex items-center justify-center p-6 relative">
              {isRendering ? (
                <div className="flex flex-col items-center gap-4 animate-pulse">
                  <Loader2 size={32} className="animate-spin text-apple-blue" />
                  <p className="text-xs font-medium text-apple-gray-300">Rendering Ink...</p>
                </div>
              ) : renderResult ? (
                <div className="space-y-4">
                  <img 
                    src={renderResult.preview_urls[page]} 
                    alt="Preview"
                    className="rounded-lg shadow-2xl border border-white/5 animate-scale-in"
                    style={{ width: `${Math.round(renderResult.width * zoom)}px`, maxWidth: "none" }}
                  />
                  {renderResult.page_count > 1 && (
                    <div className="flex items-center justify-center gap-4">
                      <button disabled={page === 0} onClick={() => setPage(p => p-1)} className="btn-apple-secondary p-2"><ChevronLeft size={14}/></button>
                      <span className="text-xs font-bold">{page + 1} / {renderResult.page_count}</span>
                      <button disabled={page === renderResult.page_count - 1} onClick={() => setPage(p => p + 1)} className="btn-apple-secondary p-2"><ChevronRight size={14}/></button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center space-y-3 opacity-30">
                  <Maximize2 size={40} className="mx-auto" />
                  <p className="text-xs font-medium">Generate to see preview</p>
                </div>
              )}
            </div>

            {renderResult && (
              <div className="p-4 border-t border-white/5 grid grid-cols-2 gap-3">
                <button onClick={() => handleExport("pdf")} className="btn-apple-secondary py-2 text-xs">
                  <FileText size={14} /> Export PDF
                </button>
                <button onClick={() => handleExport("png")} className="btn-apple-secondary py-2 text-xs">
                  <Img size={14} /> Export PNG
                </button>
              </div>
            )}
          </div>

          {/* Settings Inspector */}
          <div className="flex-1 apple-card flex flex-col gap-6 overflow-y-auto">
            <section>
              <h4 className="title-section">Physical Paper</h4>
              <div className="grid grid-cols-2 gap-2">
                {PAPERS.map(p => (
                  <button 
                    key={p.id} 
                    onClick={() => setPaperStyle({ type: p.id as PaperType })}
                    className={clsx(
                      "py-2.5 rounded-apple-sm text-xs font-bold transition-all",
                      paperStyle.type === p.id 
                        ? "bg-apple-blue text-white shadow-lg shadow-apple-blue/20"
                        : "bg-white/5 text-apple-gray-300 hover:bg-white/10"
                    )}
                  >
                    {p.l}
                  </button>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                {PAPERS_COLORS.map(c => (
                  <button 
                    key={c} 
                    onClick={() => setPaperStyle({ color: c })}
                    className={clsx(
                      "w-8 h-8 rounded-full border-2 transition-all",
                      paperStyle.color === c ? "border-apple-blue scale-110 shadow-lg" : "border-white/10"
                    )}
                    style={{ background: c }}
                  />
                ))}
              </div>
            </section>

            <section>
              <h4 className="title-section">Ink Realism</h4>
              <div className="space-y-5">
                {[
                  { l: "Size Variation", v: sizeVar, set: setSizeVar, min: 0, max: 0.4, step: 0.01, u: "%" },
                  { l: "Natural Rotation", v: rotVar, set: setRotVar, min: 0, max: 15, step: 0.5, u: "°" },
                  { l: "Vertical Jitter", v: vjit, set: setVjit, min: 0, max: 12, step: 0.5, u: "px" },
                  { l: "Font Scale", v: fscale, set: setFscale, min: 0.5, max: 2.0, step: 0.05, u: "x" },
                ].map(s => (
                  <div key={s.l}>
                    <div className="flex justify-between text-[11px] font-bold uppercase tracking-tight mb-2">
                      <span className="text-apple-gray-300">{s.l}</span>
                      <span className="text-white">{s.v.toFixed(2)}{s.u}</span>
                    </div>
                    <input 
                      type="range" 
                      min={s.min} max={s.max} step={s.step} value={s.v}
                      onChange={e => s.set(parseFloat(e.target.value))}
                      className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-apple-blue"
                    />
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h4 className="title-section">Ink Color</h4>
              <div className="flex gap-3">
                {INK_COLORS.map(c => (
                  <button 
                    key={c} 
                    onClick={() => setInkColor(c)}
                    className={clsx(
                      "w-8 h-8 rounded-full border-2 transition-all shadow-sm",
                      inkColor === c ? "border-apple-blue scale-110" : "border-white/10"
                    )}
                    style={{ background: c }}
                  />
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
