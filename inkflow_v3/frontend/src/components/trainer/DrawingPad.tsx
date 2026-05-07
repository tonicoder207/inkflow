import React, { useEffect, useRef } from "react";
import { useDrawingCanvas } from "@/hooks/useDrawingCanvas";
import { Eraser, RotateCcw, Save, Check } from "lucide-react";
import clsx from "clsx";

const W = 460, H = 190;
const BG = "#fdf6e3";

export default function DrawingPad({ char, variantCount, onSave, onNext, onPrev }:{
  char:string; variantCount:number;
  onSave:(b:Blob)=>Promise<void>; onNext:()=>void; onPrev:()=>void;
}) {
  const [saving, setSaving] = React.useState(false);
  const [flash,  setFlash]  = React.useState(false);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const { canvasRef, hasContent, clear, undo, getBlob } = useDrawingCanvas({
    width:W, height:H, strokeColor:"#1a1a2e", strokeWidth:6, backgroundColor:BG,
  });

  useEffect(() => {
    const ov = overlayRef.current; if(!ov) return;
    const ctx = ov.getContext("2d")!;
    ctx.clearRect(0,0,W,H);
    const aY=0.15*H, mY=0.42*H, bY=0.72*H, dY=0.90*H;
    const line=(y:number,color:string,dash:number[]=[])=>{
      ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle=color; ctx.lineWidth=1;
      ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); ctx.setLineDash([]);
    };
    line(aY,"rgba(180,200,220,0.45)",[5,4]);
    line(mY,"rgba(180,200,220,0.55)",[5,4]);
    line(bY,"rgba(90,130,175,0.9)");
    line(dY,"rgba(180,200,220,0.45)",[5,4]);
    ctx.font="9px sans-serif"; ctx.fillStyle="rgba(130,170,205,0.6)"; ctx.textAlign="left";
    ctx.fillText("ascender",6,aY-2); ctx.fillText("x-height",6,mY-2);
    ctx.fillText("baseline",6,bY-2); ctx.fillText("descender",6,dY-2);
    const sz=Math.round((bY-aY)*1.1);
    ctx.save(); ctx.globalAlpha=0.08; ctx.fillStyle="#1a1a3a";
    ctx.font=`${sz}px Georgia,serif`; ctx.textAlign="center"; ctx.textBaseline="alphabetic";
    ctx.fillText(char,W/2,bY); ctx.restore();
    ctx.beginPath(); ctx.arc(W/2,bY,2.5,0,Math.PI*2);
    ctx.fillStyle="rgba(90,130,175,0.3)"; ctx.fill();
  },[char]);

  const handleSave = async () => {
    if(!hasContent||saving) return;
    setSaving(true);
    try { await onSave(await getBlob()); setFlash(true); clear(); setTimeout(()=>setFlash(false),700); }
    finally { setSaving(false); }
  };

  useEffect(()=>{
    const h=(e:KeyboardEvent)=>{
      if(e.key==="Enter")    handleSave();
      if(e.key==="Escape")   clear();
      if(e.key==="ArrowRight"&&!hasContent) onNext();
      if(e.key==="ArrowLeft"&&!hasContent)  onPrev();
      if((e.ctrlKey||e.metaKey)&&e.key==="z"){ e.preventDefault(); undo(); }
    };
    window.addEventListener("keydown",h);
    return ()=>window.removeEventListener("keydown",h);
  },[hasContent,handleSave,clear,onNext,onPrev,undo]);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative rounded-2xl overflow-hidden shadow-xl" style={{width:W,height:H}}>
        <canvas ref={canvasRef} width={W} height={H} className="draw-canvas absolute inset-0" style={{width:W,height:H,touchAction:"none",cursor:"crosshair"}}/>
        <canvas ref={overlayRef} width={W} height={H} className="absolute inset-0 pointer-events-none" style={{width:W,height:H}}/>
        {flash && (
          <div className="absolute inset-0 flex items-center justify-center bg-emerald-400/15 rounded-2xl animate-fade-in pointer-events-none">
            <div className="w-12 h-12 rounded-full bg-emerald-400/20 border border-emerald-400/40 flex items-center justify-center">
              <Check size={24} className="text-emerald-400"/>
            </div>
          </div>
        )}
        {!hasContent && (
          <div className="absolute inset-0 flex items-end justify-center pb-4 pointer-events-none">
            <span className="text-[11px] text-blue-300/40">Schreibe auf der blauen Grundlinie</span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 w-full" style={{maxWidth:W}}>
        <button onClick={undo} disabled={!hasContent} className="btn-ghost text-xs px-3 py-2 disabled:opacity-25">
          <RotateCcw size={12}/>Undo
        </button>
        <button onClick={clear} disabled={!hasContent} className="btn-ghost text-xs px-3 py-2 disabled:opacity-25">
          <Eraser size={12}/>Löschen
        </button>
        <div className="flex-1"/>
        {variantCount>0 && (
          <span className="text-xs text-emerald-400 px-2 py-1 rounded-lg bg-emerald-400/8 border border-emerald-400/15">
            {variantCount}× gespeichert
          </span>
        )}
        <button onClick={handleSave} disabled={!hasContent||saving}
          className={clsx("flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium transition-all",
            hasContent&&!saving ? "bg-accent-gold text-ink-900 shadow-lg hover:bg-amber-400 hover:-translate-y-0.5"
                                : "bg-white/5 text-ink-500 cursor-not-allowed border border-white/8")}>
          {saving ? "…" : <><Save size={13}/>Speichern</>}
        </button>
      </div>
      <div className="flex gap-4 text-[11px] text-ink-600">
        <span><kbd className="bg-white/5 px-1.5 py-0.5 rounded border border-white/10 font-mono">Enter</kbd> Speichern</span>
        <span><kbd className="bg-white/5 px-1.5 py-0.5 rounded border border-white/10 font-mono">Esc</kbd> Löschen</span>
        <span><kbd className="bg-white/5 px-1.5 py-0.5 rounded border border-white/10 font-mono">→ ←</kbd> Wechseln</span>
      </div>
    </div>
  );
}
