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

  const getPos = (e:PointerEvent, c:HTMLCanvasElement) => {
    const r = c.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (width / r.width),
      y: (e.clientY - r.top)  * (height / r.height),
    };
  };

  const startDraw = useCallback((e:PointerEvent) => {
    e.preventDefault();
    const c = canvasRef.current; if(!c) return;
    // Capture pointer for reliable tracking even outside canvas
    c.setPointerCapture(e.pointerId);
    const ctx = c.getContext("2d")!;
    history.current.push(ctx.getImageData(0,0,width,height));
    if(history.current.length>20) history.current.shift();
    drawing.current = true;
    lastPos.current = getPos(e,c);
  },[width,height]);

  const draw = useCallback((e:PointerEvent) => {
    e.preventDefault();
    if(!drawing.current) return;
    const c = canvasRef.current; if(!c) return;
    const ctx = c.getContext("2d")!;
    ctx.strokeStyle = strokeColor;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Pressure sensitivity: pressure > 0 means pen/stylus, 0 means mouse
    const pressure = e.pressure > 0 ? e.pressure : 0.5;
    ctx.lineWidth = strokeWidth * (pressure * 2);

    const pos = getPos(e,c);
    if(lastPos.current) {
      ctx.beginPath();
      ctx.moveTo(lastPos.current.x, lastPos.current.y);
      // Quadratic Bezier through midpoint for smooth curves
      const mx = (lastPos.current.x + pos.x) / 2;
      const my = (lastPos.current.y + pos.y) / 2;
      ctx.quadraticCurveTo(lastPos.current.x, lastPos.current.y, mx, my);
      ctx.stroke();
    }
    lastPos.current = pos;
    setHasContent(true);
  },[strokeColor,strokeWidth]);

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
