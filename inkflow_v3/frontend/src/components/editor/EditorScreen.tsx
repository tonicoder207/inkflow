import React, { useState, useEffect } from "react";
import { useStore } from "@/store";
import { renderText, exportRender, listProfiles, getProfile } from "@/utils/api";
import type { PaperType, ProfileSummary, RenderSettings } from "@/types";
import { ArrowLeft, Play, Download, Loader2, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, Image as Img, FolderOpen, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

const PAPERS = [{id:"lined",l:"Liniert"},{id:"blank",l:"Blanko"},{id:"grid",l:"Kariert"},{id:"dot",l:"Punktiert"}] as const;
const PAPERS_COLORS = ["#fdf6e3","#fafaf9","#f5ead0","#f0f4ff"];
const INK_COLORS    = ["#1a1a2e","#1a3a5c","#2a1a1a","#1a3a1a"];

export default function EditorScreen() {
  const { setScreen, activeProfile, setActiveProfile, editorText, setEditorText,
          paperStyle, setPaperStyle, renderResult, setRenderResult, isRendering, setIsRendering } = useStore();
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [page, setPage]         = useState(0);
  const [zoom, setZoom]         = useState(0.45);
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportDone, setExportDone] = useState<string|null>(null);
  const [inkColor, setInkColor]   = useState("#1a1a2e");
  const [sizeVar, setSizeVar]     = useState(0.12);
  const [rotVar,  setRotVar]      = useState(4.0);
  const [vjit,    setVjit]        = useState(3.0);
  const [fscale,  setFscale]      = useState(1.0);

  useEffect(()=>{ listProfiles().then(setProfiles).catch(()=>{}); },[]);

  const build = (): RenderSettings => ({
    profile_id: activeProfile!.id, text: editorText, paper: paperStyle,
    size_variation: sizeVar, rotation_variation: rotVar, vertical_jitter: vjit,
    spacing_variation: 0.15, ink_pressure_variation: 0.1, word_break_probability: 0.02,
    font_size_scale: fscale,
  });

  const handleRender = async () => {
    if(!activeProfile) return toast.error("Profil wählen");
    if(!editorText.trim()) return toast.error("Text eingeben");
    setIsRendering(true); setRenderResult(null); setPage(0);
    try { setRenderResult(await renderText(build())); }
    catch(e:any) { toast.error(e.message); }
    finally { setIsRendering(false); }
  };

  const handleExport = async (fmt:string) => {
    if(!renderResult) return;
    setExporting(true);
    setExportProgress(0);
    setExportDone(null);

    // Simulate progress animation while waiting
    const progressInterval = setInterval(() => {
      setExportProgress(p => Math.min(p + 8, 90));
    }, 200);

    try {
      const r = await exportRender(renderResult.render_id, fmt);
      clearInterval(progressInterval);
      setExportProgress(100);

      // Success toast with filename and "Open folder" button
      toast.success(
        (t) => (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-emerald-400 shrink-0"/>
              <span className="font-medium">{r.filename}</span>
            </div>
            <button
              onClick={() => {
                try { window.inkflow?.openExportsFolder?.(); } catch {}
                toast.dismiss(t.id);
              }}
              className="flex items-center gap-1.5 text-xs text-accent-gold hover:text-amber-300 transition-colors"
            >
              <FolderOpen size={12}/> Ordner öffnen
            </button>
          </div>
        ),
        { duration: 6000 }
      );

      setExportDone(r.filename);

      // Auto-hide progress after 2s
      setTimeout(() => {
        setExporting(false);
        setExportProgress(0);
        setExportDone(null);
      }, 2000);
    } catch(e:any) {
      clearInterval(progressInterval);
      toast.error(e.message);
      setExporting(false);
      setExportProgress(0);
    }
  };

  return (
    <div className="h-full flex overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 shrink-0 border-r border-white/5 overflow-y-auto flex flex-col gap-4 p-4">
        <div>
          <p className="label">Profil</p>
          <select className="input" value={activeProfile?.id??""} onChange={async e=>{
            if(!e.target.value) return;
            setActiveProfile(await getProfile(e.target.value).catch(()=>null));
          }}>
            <option value="">— Profil wählen —</option>
            {profiles.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <p className="label">Papier</p>
          <div className="grid grid-cols-2 gap-1.5">
            {PAPERS.map(p=>(
              <button key={p.id} onClick={()=>setPaperStyle({type:p.id as PaperType})}
                className={clsx("py-1.5 rounded-lg text-xs transition-all",
                  paperStyle.type===p.id ? "bg-accent-gold/20 text-accent-gold border border-accent-gold/30"
                                         : "bg-white/5 text-ink-300 border border-white/8 hover:bg-white/10")}>
                {p.l}
              </button>
            ))}
          </div>
          <div className="flex gap-1.5 mt-2">
            {PAPERS_COLORS.map(c=>(
              <button key={c} onClick={()=>setPaperStyle({color:c})} title={c}
                className={clsx("w-7 h-7 rounded-lg border-2 transition-all",paperStyle.color===c?"border-accent-gold":"border-white/15")}
                style={{background:c}}/>
            ))}
          </div>
        </div>
        <div>
          <p className="label">Tinte</p>
          <div className="flex gap-1.5">
            {INK_COLORS.map(c=>(
              <button key={c} onClick={()=>setInkColor(c)}
                className={clsx("w-7 h-7 rounded-lg border-2 transition-all",inkColor===c?"border-accent-gold":"border-white/15")}
                style={{background:c}}/>
            ))}
          </div>
        </div>
        <div>
          <p className="label">Realismus</p>
          {[
            {l:"Größenvar.",  v:sizeVar,  set:setSizeVar,  min:0,   max:0.4, step:0.01},
            {l:"Rotation",    v:rotVar,   set:setRotVar,   min:0,   max:15,  step:0.5, u:"°"},
            {l:"V-Jitter",    v:vjit,     set:setVjit,     min:0,   max:12,  step:0.5, u:"px"},
            {l:"Schriftgröße",v:fscale,   set:setFscale,   min:0.5, max:2.0, step:0.05, u:"×"},
          ].map(s=>(
            <div key={s.l} className="mb-2">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-ink-300">{s.l}</span>
                <span className="text-ink-500 font-mono">{s.v.toFixed(2)}{s.u??""}</span>
              </div>
              <input type="range" min={s.min} max={s.max} step={s.step} value={s.v}
                onChange={e=>s.set(parseFloat(e.target.value))}
                className="w-full h-1 rounded-full accent-amber-400 cursor-pointer"/>
            </div>
          ))}
        </div>
      </div>

      {/* Center */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 shrink-0">
          <button onClick={()=>setScreen("landing")} className="btn-ghost text-xs px-2 py-1.5"><ArrowLeft size={13}/></button>
          <div className="h-4 w-px bg-white/10"/>
          <button onClick={handleRender} disabled={!activeProfile||!editorText.trim()||isRendering} className="btn-primary text-xs px-4 py-1.5">
            {isRendering ? <><Loader2 size={13} className="animate-spin"/>Rendere…</> : <><Play size={13}/>Generieren</>}
          </button>
          {renderResult && <>
            <div className="h-4 w-px bg-white/10"/>
            <button onClick={()=>handleExport("pdf")} disabled={exporting} className="btn-ghost text-xs px-3 py-1.5"><FileText size={13}/>PDF</button>
            <button onClick={()=>handleExport("png")} disabled={exporting} className="btn-ghost text-xs px-3 py-1.5"><Img size={13}/>PNG</button>
          </>}
          <span className="ml-auto text-xs text-ink-400">{editorText.length} Zeichen{renderResult?` · ${renderResult.page_count} Seite(n)`:""}</span>
        </div>

        {/* Export progress bar */}
        {exporting && (
          <div className="px-4 py-2 border-b border-white/5 shrink-0 bg-accent-gold/5 animate-fade-in">
            <div className="flex items-center gap-3 text-xs mb-1.5">
              {exportProgress < 100 ? (
                <><Loader2 size={13} className="animate-spin text-accent-gold"/><span className="text-ink-300">Exportiere...</span></>
              ) : (
                <><CheckCircle size={13} className="text-emerald-400"/><span className="text-emerald-400">{exportDone}</span></>
              )}
              <span className="ml-auto text-ink-500 font-mono">{exportProgress}%</span>
            </div>
            <div className="h-1 bg-white/8 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-300 ease-out"
                style={{
                  width: `${exportProgress}%`,
                  background: exportProgress >= 100
                    ? "rgb(52, 211, 153)"
                    : "linear-gradient(90deg, rgba(201,168,76,0.8), rgba(201,168,76,1))"
                }}/>
            </div>
          </div>
        )}

        <div className="flex-1 p-4">
          <textarea className="input h-full resize-none font-serif text-sm leading-relaxed"
            placeholder={"Schreibe hier deinen Text…\n\nZum Beispiel:\nLiebe Maria,\nich hoffe es geht dir gut…"}
            value={editorText} onChange={e=>setEditorText(e.target.value)}/>
        </div>
      </div>

      {/* Preview */}
      <div className="w-80 shrink-0 flex flex-col border-l border-white/5">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-white/5 shrink-0">
          <span className="text-xs text-ink-400">Vorschau</span>
          <div className="flex items-center gap-1">
            <button onClick={()=>setZoom(z=>Math.max(0.2,z-0.1))} className="p-1 rounded text-ink-400 hover:text-white"><ZoomOut size={12}/></button>
            <span className="text-xs text-ink-400 w-10 text-center">{Math.round(zoom*100)}%</span>
            <button onClick={()=>setZoom(z=>Math.min(1.5,z+0.1))} className="p-1 rounded text-ink-400 hover:text-white"><ZoomIn size={12}/></button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-zinc-900/50 flex items-start justify-center p-4">
          {isRendering && <div className="flex flex-col items-center gap-3 mt-20 text-ink-400"><Loader2 size={28} className="animate-spin text-accent-gold"/><p className="text-sm">Rendere…</p></div>}
          {!isRendering && !renderResult && <div className="flex flex-col items-center gap-3 mt-20 text-ink-500 text-center"><FileText size={28} className="text-ink-700"/><p className="text-xs">Text eingeben und „Generieren" klicken</p></div>}
          {!isRendering && renderResult && renderResult.preview_urls.length > 0 && (
            <div className="flex flex-col items-center gap-3">
              <img src={renderResult.preview_urls[page]} alt={`Seite ${page+1}`}
                className="rounded-xl shadow-2xl border border-white/10 animate-fade-in"
                style={{width:`${Math.round(renderResult.width*zoom)}px`,maxWidth:"none"}}/>
              {renderResult.page_count>1 && (
                <div className="flex items-center gap-2 text-xs text-ink-400">
                  <button disabled={page===0} onClick={()=>setPage(p=>p-1)} className="p-1 rounded hover:bg-white/10 disabled:opacity-30"><ChevronLeft size={14}/></button>
                  <span>{page+1}/{renderResult.page_count}</span>
                  <button disabled={page===renderResult.page_count-1} onClick={()=>setPage(p=>p+1)} className="p-1 rounded hover:bg-white/10 disabled:opacity-30"><ChevronRight size={14}/></button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
