import React, { useEffect, useRef } from "react";
import { useDrawingCanvas } from "@/hooks/useDrawingCanvas";
import { Eraser, RotateCcw, Save, Check, Keyboard, Loader2 } from "lucide-react";
import clsx from "clsx";

const W = 460, H = 190;
const BG = "#FAFAFA"; // Apple soft white

export default function DrawingPad({ char, variantCount, onSave, onNext, onPrev }:{
  char:string; variantCount:number;
  onSave:(b:Blob)=>Promise<void>; onNext:()=>void; onPrev:()=>void;
}) {
  const [saving, setSaving] = React.useState(false);
  const [flash,  setFlash]  = React.useState(false);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const { canvasRef, hasContent, clear, undo, getBlob } = useDrawingCanvas({
    width: W, height: H, strokeColor: "#1D1D1F", strokeWidth: 5, backgroundColor: BG,
  });

  useEffect(() => {
    const ov = overlayRef.current; if(!ov) return;
    const ctx = ov.getContext("2d")!;
    ctx.clearRect(0,0,W,H);
    
    // Apple-style subtle baseline guide
    const aY=0.15*H, mY=0.42*H, bY=0.72*H, dY=0.90*H;
    const line=(y:number, color:string, dash:number[]=[])=>{
      ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle=color; ctx.lineWidth=1;
      ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); ctx.setLineDash([]);
    };

    line(aY, "rgba(0,0,0,0.05)", [4, 4]);
    line(mY, "rgba(0,0,0,0.05)", [4, 4]);
    line(bY, "rgba(0, 122, 255, 0.4)"); // Apple Blue for baseline
    line(dY, "rgba(0,0,0,0.05)", [4, 4]);
    
    ctx.font = "bold 9px sans-serif"; ctx.fillStyle = "rgba(0,0,0,0.2)"; ctx.textAlign = "left";
    ctx.fillText("ASCENDER", 10, aY - 4); 
    ctx.fillText("BASELINE", 10, bY - 4);

    // Placeholder character
    const sz = Math.round((bY - aY) * 1.1);
    ctx.save(); 
    ctx.globalAlpha = 0.04; 
    ctx.fillStyle = "#000";
    ctx.font = `bold ${sz}px Inter, sans-serif`; 
    ctx.textAlign = "center"; 
    ctx.textBaseline = "alphabetic";
    ctx.fillText(char, W/2, bY); 
    ctx.restore();

    // Center point
    ctx.beginPath(); ctx.arc(W/2, bY, 3, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0, 122, 255, 0.2)"; ctx.fill();
  }, [char]);

  const handleSave = async () => {
    if(!hasContent || saving) return;
    setSaving(true);
    try { 
      await onSave(await getBlob()); 
      setFlash(true); 
      clear(); 
      setTimeout(() => setFlash(false), 700); 
    }
    finally { setSaving(false); }
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if(e.key === "Enter") handleSave();
      if(e.key === "Escape") clear();
      if(e.key === "ArrowRight" && !hasContent) onNext();
      if(e.key === "ArrowLeft" && !hasContent) onPrev();
      if((e.ctrlKey || e.metaKey) && e.key === "z"){ e.preventDefault(); undo(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [hasContent, handleSave, clear, onNext, onPrev, undo]);

  return (
    <div className="flex flex-col items-center gap-6 animate-scale-in">
      {/* Canvas Container */}
      <div className="relative rounded-apple overflow-hidden shadow-2xl border border-white/10" style={{width:W, height:H}}>
        <canvas ref={canvasRef} width={W} height={H} className="absolute inset-0" style={{width:W, height:H, touchAction:"none", cursor:"crosshair"}}/>
        <canvas ref={overlayRef} width={W} height={H} className="absolute inset-0 pointer-events-none" style={{width:W, height:H}}/>
        
        {/* Save Flash Effect */}
        {flash && (
          <div className="absolute inset-0 flex items-center justify-center bg-apple-system-green/10 backdrop-blur-sm animate-fade-in pointer-events-none">
            <div className="w-16 h-16 rounded-full bg-apple-system-green/20 flex items-center justify-center shadow-lg">
              <Check size={32} className="text-apple-system-green" />
            </div>
          </div>
        )}

        {/* Floating Instruction */}
        {!hasContent && (
          <div className="absolute inset-0 flex items-end justify-center pb-4 pointer-events-none">
            <span className="text-[10px] font-bold text-apple-blue/40 uppercase tracking-widest">Draw on the blue baseline</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="w-full flex items-center gap-3" style={{maxWidth: W}}>
        <button 
          onClick={undo} 
          disabled={!hasContent} 
          className="btn-apple-secondary px-4 py-2 text-xs disabled:opacity-20"
        >
          <RotateCcw size={14} /> Undo
        </button>
        <button 
          onClick={clear} 
          disabled={!hasContent} 
          className="btn-apple-secondary px-4 py-2 text-xs disabled:opacity-20"
        >
          <Eraser size={14} /> Clear
        </button>
        
        <div className="flex-1" />

        <button 
          onClick={handleSave} 
          disabled={!hasContent || saving}
          className={clsx(
            "btn-apple-primary px-8 min-w-[120px]",
            (!hasContent || saving) && "opacity-40 grayscale"
          )}
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <><Save size={16} /> Save</>}
        </button>
      </div>

      {/* Keyboard Shortcuts */}
      <div className="flex gap-6 items-center px-6 py-2 rounded-full bg-white/5 border border-white/5">
        <Shortcut keyLabel="Enter" action="Save" />
        <Shortcut keyLabel="Esc" action="Clear" />
        <div className="w-px h-3 bg-white/10" />
        <Shortcut keyLabel="← →" action="Navigate" />
      </div>
    </div>
  );
}

function Shortcut({ keyLabel, action }: { keyLabel: string, action: string }) {
  return (
    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-tight text-apple-gray-400">
      <kbd className="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 text-white font-mono">{keyLabel}</kbd>
      <span>{action}</span>
    </div>
  );
}
