"""
slip_reader.py — ให้ Gemini อ่านยอดเงินจากสลิป
- รองรับ SDK ใหม่ (google-genai) และ SDK เดิม (google-generativeai)
- ลองหลายรุ่นอัตโนมัติ เพราะ gemini-2.0-flash ถูกปิดไปแล้วในปี 2026
- ตั้งรุ่นเองได้ใน secrets.toml:  GEMINI_MODEL = "gemini-2.5-flash"
- cache ผลตาม hash ของรูป -> สลิปเดิมไม่ยิง API ซ้ำ
"""
import hashlib
import io
import re

import streamlit as st
from PIL import Image

DEFAULT_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

PROMPT = (
    "This image is a Thai bank / PromptPay transfer slip. "
    "Reply with ONLY the transferred amount in Thai Baht as a plain number "
    "(examples: 1500 or 1500.50). No currency symbol, no commas, no words. "
    "If the image is not a transfer slip or the amount is unreadable, reply NONE."
)


def api_key() -> str:
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def is_ready() -> bool:
    return bool(api_key())


def _models() -> list:
    first = []
    try:
        m = str(st.secrets.get("GEMINI_MODEL", "")).strip()
        if m:
            first.append(m)
    except Exception:
        pass
    working = st.session_state.get("_gemini_working_model")
    if working:
        first.insert(0, working)
    seen, out = set(), []
    for m in first + DEFAULT_MODELS:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


@st.cache_resource(show_spinner=False)
def _client(key: str):
    try:
        from google import genai as new_genai  # google-genai
        return ("new", new_genai.Client(api_key=key))
    except ImportError:
        import google.generativeai as old_genai  # google-generativeai (เลิกพัฒนาแล้ว)
        old_genai.configure(api_key=key)
        return ("old", old_genai)


def _ask(img: Image.Image) -> str:
    kind, client = _client(api_key())
    last_err = None
    for model in _models():
        try:
            if kind == "new":
                resp = client.models.generate_content(model=model, contents=[PROMPT, img])
            else:
                resp = client.GenerativeModel(model).generate_content([PROMPT, img])
            st.session_state["_gemini_working_model"] = model
            return (getattr(resp, "text", "") or "").strip()
        except Exception as e:  # รุ่นไม่มี/ถูกปิด -> ลองรุ่นถัดไป
            last_err = e
            continue
    raise RuntimeError(f"เรียก Gemini ไม่สำเร็จทุกรุ่น ({', '.join(_models())}): {last_err}")


def parse_amount(text: str):
    if not text or "NONE" in text.upper():
        return None
    m = re.search(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", ""))
        return v if v > 0 else None
    except ValueError:
        return None


def file_bytes(file) -> bytes:
    if hasattr(file, "getvalue"):
        return file.getvalue()
    if hasattr(file, "seek"):
        file.seek(0)
    return file.read()


def file_hash(file) -> str:
    return hashlib.md5(file_bytes(file)).hexdigest()


def read_amount(file):
    """คืนค่า (ยอดเงิน หรือ None, ข้อความ error หรือ None) — cache ตาม hash ของไฟล์"""
    cache = st.session_state.setdefault("_slip_cache", {})
    h = file_hash(file)
    if h in cache:
        return cache[h]
    if not is_ready():
        return (None, "ยังไม่ได้ตั้งค่า GEMINI_API_KEY")
    try:
        img = Image.open(io.BytesIO(file_bytes(file)))
        img.load()
        amount = parse_amount(_ask(img))
        result = (amount, None if amount else "AI อ่านยอดไม่ได้ กรุณากรอกเอง")
    except Exception as e:
        # เก็บ error ไว้ด้วย เพื่อไม่ให้ยิง API ซ้ำทุกครั้งที่หน้า rerun (กดปุ่ม 'อ่านใหม่' เพื่อลองอีกครั้ง)
        result = (None, str(e))
    cache[h] = result
    return result


def forget(file):
    """ลบผล cache ของไฟล์นี้ (ใช้กับปุ่ม 'อ่านใหม่')"""
    cache = st.session_state.get("_slip_cache", {})
    cache.pop(file_hash(file), None)
