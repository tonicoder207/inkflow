"""InkFlow v3 — Export Engine"""
import io, os, uuid, zipfile
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas as rl_canvas

def _exports_dir():
    env = os.environ.get("INKFLOW_EXPORTS_DIR")
    if env: return Path(env)
    return Path(__file__).parent.parent.parent / "data" / "exports"

def export_pages(pages, fmt="pdf", dpi=300):
    ed = _exports_dir()
    ed.mkdir(parents=True, exist_ok=True)
    eid = str(uuid.uuid4())[:8]
    if fmt == "pdf":   return _pdf(pages, ed, eid, dpi)
    if fmt == "png":   return _images(pages, ed, eid, "PNG", "png")
    if fmt == "jpg":   return _images(pages, ed, eid, "JPEG", "jpg")
    raise ValueError(f"Unknown format: {fmt}")

def _pdf(pages, ed, eid, dpi):
    fname = f"inkflow_{eid}.pdf"
    fpath = ed / fname
    c = None
    tmps = []
    for i, page in enumerate(pages):
        rgb = page.convert("RGB")
        w_pt = rgb.width  / dpi * 72
        h_pt = rgb.height / dpi * 72
        if c is None:
            c = rl_canvas.Canvas(str(fpath), pagesize=(w_pt, h_pt))
        tmp = ed / f"_tmp_{eid}_{i}.jpg"
        rgb.save(str(tmp), "JPEG", quality=98)
        tmps.append(tmp)
        c.setPageSize((w_pt, h_pt))
        c.drawImage(str(tmp), 0, 0, width=w_pt, height=h_pt)
        if i < len(pages)-1: c.showPage()
    if c: c.save()
    for t in tmps:
        try: t.unlink()
        except: pass
    size = fpath.stat().st_size if fpath.exists() else 0
    return {"filepath": str(fpath), "filename": fname, "size_bytes": size}

def _images(pages, ed, eid, pil_fmt, ext):
    if len(pages) == 1:
        fname = f"inkflow_{eid}.{ext}"
        fpath = ed / fname
        img = pages[0].convert("RGB") if pil_fmt == "JPEG" else pages[0]
        img.save(str(fpath), pil_fmt)
        return {"filepath": str(fpath), "filename": fname, "size_bytes": fpath.stat().st_size}
    zname = f"inkflow_{eid}_pages.zip"
    zpath = ed / zname
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, page in enumerate(pages):
            buf = io.BytesIO()
            img = page.convert("RGB") if pil_fmt == "JPEG" else page
            img.save(buf, pil_fmt)
            zf.writestr(f"page_{i+1:02d}.{ext}", buf.getvalue())
    return {"filepath": str(zpath), "filename": zname, "size_bytes": zpath.stat().st_size}
