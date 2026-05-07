"""InkFlow v3 — Profile Manager"""
import json, os, shutil
from datetime import datetime
from pathlib import Path

def _profiles_dir() -> Path:
    env = os.environ.get("INKFLOW_PROFILES_DIR")
    if env: return Path(env)
    return Path(__file__).parent.parent.parent / "data" / "profiles"

def _profile_dir(pid): return _profiles_dir() / pid

def _chars_dir(pid, char):
    safe = char.encode("utf-8").hex() if not char.isalnum() else char
    return _profile_dir(pid) / "chars" / safe

def list_profiles():
    from models import ProfileSummary
    pd = _profiles_dir()
    if not pd.exists(): return []
    result = []
    for entry in sorted(pd.iterdir()):
        if not (entry / "profile.json").exists(): continue
        try:
            p = load_profile(entry.name)
            total = sum(len(v) for v in p.characters.values())
            result.append(ProfileSummary(id=p.id, name=p.name,
                created_at=p.created_at,
                characters_trained=len(p.characters),
                variants_total=total))
        except: continue
    return result

def load_profile(pid):
    from models import HandwritingProfile
    f = _profile_dir(pid) / "profile.json"
    if not f.exists(): raise FileNotFoundError(f"Profile '{pid}' not found")
    with open(f, "r", encoding="utf-8") as fp:
        return HandwritingProfile(**json.load(fp))

def save_profile(profile):
    pd = _profile_dir(profile.id)
    pd.mkdir(parents=True, exist_ok=True)
    profile.updated_at = datetime.utcnow().isoformat()
    with open(pd / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)

def create_profile(name):
    from models import HandwritingProfile
    now = datetime.utcnow().isoformat()
    p = HandwritingProfile(name=name, created_at=now, updated_at=now)
    save_profile(p)
    return p

def delete_profile(pid):
    pd = _profile_dir(pid)
    if pd.exists(): shutil.rmtree(pd)

def save_character_variant(pid, char, image_bytes, width, height, baseline_offset=0):
    from models import CharacterVariant
    p = load_profile(pid)
    cd = _chars_dir(pid, char)
    cd.mkdir(parents=True, exist_ok=True)
    existing = p.characters.get(char, [])
    idx = len(existing)
    img_path = str(cd / f"v{idx:03d}.png")
    with open(img_path, "wb") as f: f.write(image_bytes)
    v = CharacterVariant(character=char, variant_index=idx,
        image_path=img_path, width=width, height=height,
        baseline_offset=baseline_offset)
    existing.append(v)
    p.characters[char] = existing
    save_profile(p)
    return v

def get_character_variants(pid, char):
    return load_profile(pid).characters.get(char, [])
