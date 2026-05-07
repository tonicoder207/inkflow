"""InkFlow v3 — All data models"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid

# ── Profile ───────────────────────────────────────────────────────────────────

class CharacterVariant(BaseModel):
    character: str
    variant_index: int
    image_path: str
    width: int
    height: int
    baseline_offset: int = 0

class HandwritingProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    created_at: str
    updated_at: str
    characters: dict[str, list[CharacterVariant]] = {}
    avg_char_width: float = 30.0
    avg_char_height: float = 40.0
    line_height: float = 60.0
    word_spacing: float = 20.0
    char_spacing: float = 4.0
    slant_deg: float = 0.0
    ink_color: str = "#1a1a2e"

class ProfileSummary(BaseModel):
    id: str
    name: str
    created_at: str
    characters_trained: int
    variants_total: int

# ── Render ────────────────────────────────────────────────────────────────────

class PaperStyle(BaseModel):
    type: str = "lined"
    color: str = "#fdf6e3"
    line_color: str = "#c8d6e5"
    margin_left: int = 80
    margin_top: int = 80
    width: int = 2480
    height: int = 3508

class RenderSettings(BaseModel):
    profile_id: str
    text: str
    paper: PaperStyle = Field(default_factory=PaperStyle)
    size_variation: float = 0.12
    rotation_variation: float = 4.0
    vertical_jitter: float = 3.0
    spacing_variation: float = 0.15
    ink_pressure_variation: float = 0.1
    word_break_probability: float = 0.02
    font_size_scale: float = 1.0
    line_height_override: Optional[float] = None

class RenderResult(BaseModel):
    render_id: str
    page_count: int
    preview_urls: list[str]
    width: int
    height: int

# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    render_id: str
    format: str = "pdf"
    dpi: int = 300

class ExportResult(BaseModel):
    download_url: str
    filename: str
    size_bytes: int
    filepath: str = ""

# ── OneNote / Writing ─────────────────────────────────────────────────────────

class CalibrationPoint(BaseModel):
    label: str   # "top_left" | "top_right" | "bottom_right" | "bottom_left"
    x: int
    y: int

class CalibrationProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Standard"
    points: list[CalibrationPoint] = []
    write_area_x: int = 0
    write_area_y: int = 0
    write_area_width: int = 1200
    write_area_height: int = 800
    line_height_px: int = 40
    zoom_level: float = 1.0
    transform_matrix: list[list[float]] = []
    created_at: str = ""
    scaling_factor: float = 1.0

class WriteRequest(BaseModel):
    profile_id: str
    calibration_id: str
    text: str
    speed: str = "normal"      # slow | normal | fast
    font_size_scale: float = 1.0
    size_variation: float = 0.10
    rotation_variation: float = 3.0
    vertical_jitter: float = 2.0
    point_delay_s: float = 0.005
    pressure: float = 0.7
    scaling_factor: float = 1.0

class WriteStatus(BaseModel):
    job_id: str
    status: str        # idle | running | paused | done | error
    progress: float    # 0.0 .. 1.0
    chars_done: int
    chars_total: int
    current_line: int
    message: str = ""
