export interface CharacterVariant {
  character: string; variant_index: number;
  image_path: string; width: number; height: number; baseline_offset: number;
}
export interface HandwritingProfile {
  id: string; name: string; created_at: string; updated_at: string;
  characters: Record<string, CharacterVariant[]>;
  avg_char_width: number; avg_char_height: number; line_height: number;
  word_spacing: number; char_spacing: number; slant_deg: number; ink_color: string;
}
export interface ProfileSummary {
  id: string; name: string; created_at: string;
  characters_trained: number; variants_total: number;
}
export type PaperType = "lined"|"blank"|"grid"|"dot";
export interface PaperStyle {
  type: PaperType;
  color: string; line_color: string;
  margin_left: number; margin_top: number; width: number; height: number;
}
export interface RenderSettings {
  profile_id: string; text: string; paper: PaperStyle;
  size_variation: number; rotation_variation: number; vertical_jitter: number;
  spacing_variation: number; ink_pressure_variation: number;
  word_break_probability: number; font_size_scale: number;
}
export interface RenderResult {
  render_id: string; page_count: number; preview_urls: string[];
  width: number; height: number;
}
export interface CalibrationProfile {
  id: string; name: string;
  points: CalibrationPoint[];
  write_area_x: number; write_area_y: number;
  write_area_width: number; write_area_height: number;
  line_height_px: number; zoom_level: number;
  transform_matrix: number[][];
  created_at: string;
}
export interface CalibrationPoint {
  label: "top_left" | "top_right" | "bottom_right" | "bottom_left";
  x: number;
  y: number;
}
export interface CalibrationComputeResult {
  computed: boolean;
  line_height_px: number;
  write_area_width: number;
  write_area_height?: number;
}
export type WriteSpeed = "slow"|"normal"|"fast";
export interface WriteRequest {
  profile_id: string; calibration_id: string; text: string;
  speed: WriteSpeed; font_size_scale: number;
  size_variation: number; rotation_variation: number; vertical_jitter: number;
  point_delay_s: number;
  pressure: number;
  scaling_factor?: number;
}
export interface WriteStatus {
  job_id: string; status: "idle"|"running"|"paused"|"done"|"error"|"cancelled";
  progress: number; chars_done: number; chars_total: number;
  current_line: number; message: string;
}
export type AppScreen = "landing"|"editor"|"trainer"|"onenote"|"settings";
