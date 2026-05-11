import { useRef, useEffect, useCallback, useState } from "react";

export function useDrawingCanvas({ width, height, strokeColor="#1a1a2e", strokeWidth=5, backgroundColor="#fdf6e3" }: {
  width:number; height:number; strokeColor?:string; strokeWidth?:number; backgroundColor?:string;
}) {
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const drawing     = useRef(false);
  const lastPos     = useRef<{x:number;y:number}|null>(null);
  const history     = useRef<ImageData[]>([]);
  const [hasContent, setHasContent] = useState(false);

  useEffect(() => {
    const c = canvasRef.current; if(!c) return;
    const ctx = c.getContext("2d")!;
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0,0,width,height);
  }, [width,height,backgroundColor]);

  const getPos = useCallback((e:PointerEvent, c:HTMLCanvasElement) => {
    const r = c.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (width / r.width),
      y: (e.clientY - r.top)  * (height / r.height),
    };
  }, [width, height]);

  const startDraw = useCallback((e:PointerEvent) => {
    e.preventDefault();
    const c = canvasRef.current; if(!c) return;
    c.setPointerCapture(e.pointerId);
    const ctx = c.getContext("2d")!;
    history.current.push(ctx.getImageData(0,0,width,height));
    if(history.current.length>20) history.current.shift();
    drawing.current = true;
    lastPos.current = getPos(e,c);
  },[width,height,getPos]);

  const draw = useCallback((e:PointerEvent) => {
    if(!drawing.current) return;
    const c = canvasRef.current; if(!c) return;
    const ctx = c.getContext("2d")!;
    
    ctx.strokeStyle = strokeColor;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Use coalesced events for high-fidelity tracking (fixes "fast writing" issue)
    const events = (e as any).getCoalescedEvents ? (e as any).getCoalescedEvents() : [e];
    
    let moved = false;
    for (const ev of events) {
      const pos = getPos(ev, c);
      const pressure = ev.pressure > 0 ? ev.pressure : 0.5;
      ctx.lineWidth = strokeWidth * (pressure * 2);

      if (lastPos.current) {
        ctx.beginPath();
        ctx.moveTo(lastPos.current.x, lastPos.current.y);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        moved = true;
      }
      lastPos.current = pos;
    }
    
    if (moved) setHasContent(true);
  },[strokeColor,strokeWidth,getPos]);

  const endDraw = useCallback((e:PointerEvent) => {
    if(!drawing.current) return;
    const c = canvasRef.current;
    if(c && e.pointerId !== undefined) {
      try { c.releasePointerCapture(e.pointerId); } catch(_) {}
    }
    drawing.current = false;
    lastPos.current = null;
  },[]);

  useEffect(() => {
    const c = canvasRef.current; if(!c) return;
    // Use pointer events for unified mouse/touch/pen support
    c.addEventListener("pointerdown", startDraw);
    c.addEventListener("pointermove", draw);
    c.addEventListener("pointerup",   endDraw);
    c.addEventListener("pointerleave",endDraw);
    return () => {
      c.removeEventListener("pointerdown", startDraw);
      c.removeEventListener("pointermove", draw);
      c.removeEventListener("pointerup",   endDraw);
      c.removeEventListener("pointerleave",endDraw);
    };
  },[startDraw,draw,endDraw]);

  const clear = useCallback(() => {
    const c = canvasRef.current; if(!c) return;
    const ctx=c.getContext("2d")!; ctx.fillStyle=backgroundColor; ctx.fillRect(0,0,width,height);
    history.current=[]; setHasContent(false);
  },[backgroundColor,width,height]);

  const undo = useCallback(() => {
    const c = canvasRef.current; if(!c||!history.current.length) return;
    c.getContext("2d")!.putImageData(history.current.pop()!,0,0);
    setHasContent(history.current.length>0);
  },[]);

  const getBlob = useCallback(():Promise<Blob> =>
    new Promise((res,rej) => canvasRef.current?.toBlob(b=>b?res(b):rej(new Error("empty")),"image/png"))
  ,[]);

  return { canvasRef, hasContent, clear, undo, getBlob };
}
