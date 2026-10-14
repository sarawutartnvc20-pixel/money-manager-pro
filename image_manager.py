import io
import logging
import os
import re
from datetime import datetime

import cloudinary
import cloudinary.uploader
import streamlit as st
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_SUBFOLDERS = {"incoming", "outgoing"}
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000          # กัน decompression bomb
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

last_error = ""


def is_cloudinary_configured() -> bool:
    """ตรวจว่า Cloudinary ตั้งค่า API Secret จริงหรือไม่"""
    try:
        conf = st.secrets.get("cloudinary", {})
        secret = str(conf.get("api_secret", "")).strip()
        if not secret or "<" in secret:
            return False
        if "cloudinary://" in secret:
            match = re.search(r'cloudinary://([^:]+):([^@]+)@(.+)', secret)
            return bool(match and "<" not in match.group(2))
        return True
    except Exception:
        return False


def configure_cloudinary() -> bool:
    try:
        conf = st.secrets["cloudinary"]
        cloud_name = str(conf.get("cloud_name", "")).strip()
        api_key = str(conf.get("api_key", "")).strip()
        api_secret = str(conf.get("api_secret", "")).strip()

        if "cloudinary://" in api_secret:   # กรณีวาง CLOUDINARY_URL ทั้งบรรทัดลงในช่อง api_secret
            match = re.search(r'cloudinary://([^:]+):([^@]+)@(.+)', api_secret)
            if match:
                api_key = api_key or match.group(1).strip()
                api_secret = match.group(2).strip()
                cloud_name = cloud_name or match.group(3).strip()

        if not cloud_name or not api_key or not api_secret or "<" in api_secret:
            return False
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        return True
    except Exception:
        logger.warning("Cloudinary config error")
        return False


def _read_validated(file):
    """อ่านไฟล์ที่อัปโหลด ตรวจว่าเป็นรูปจริง (jpg/png/webp) และขนาดไม่เกินกำหนด
    คืนค่า (bytes, นามสกุลที่ปลอดภัย) — ไม่เชื่อชื่อไฟล์/นามสกุลที่ผู้ใช้ส่งมา"""
    data = file.getvalue() if hasattr(file, "getvalue") else file.read()
    if len(data) > MAX_BYTES:
        raise ValueError("ไฟล์ใหญ่เกิน 10 MB")
    img = Image.open(io.BytesIO(data))
    fmt = img.format
    img.verify()
    if fmt not in ALLOWED_FORMATS:
        raise ValueError("รองรับเฉพาะไฟล์ JPG / PNG / WEBP")
    return data, ALLOWED_FORMATS[fmt]


def upload_image(file, subfolder="incoming", prefix="slip"):
    """
    อัปโหลดรูปไป Cloudinary (คืนค่า HTTPS URL) ถ้าไม่พร้อมจะเก็บในโฟลเดอร์ slips/ ของเครื่อง
    คืนค่า "" เมื่อไฟล์ไม่ผ่านการตรวจหรืออัปโหลดไม่สำเร็จ (เหตุผลอยู่ใน im.last_error)
    """
    global last_error
    last_error = ""
    if not file:
        return ""
    if subfolder not in ALLOWED_SUBFOLDERS:
        subfolder = "incoming"

    try:
        data, ext = _read_validated(file)
    except Exception as e:
        last_error = f"ไฟล์รูปไม่ถูกต้อง: {e}"
        return ""

    if configure_cloudinary():
        try:
            response = cloudinary.uploader.upload(
                io.BytesIO(data), folder="money_manager_pro", resource_type="image",
                allowed_formats=["jpg", "png", "webp"],
            )
            url = response.get("secure_url", "")
            if url:
                return url
        except Exception as e:
            logger.warning("Cloudinary upload error: %s", type(e).__name__)

    try:
        safe_prefix = re.sub(r"[^A-Za-z0-9_\-]", "_", str(prefix))[:40]
        os.makedirs(f"slips/{subfolder}", exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"slips/{subfolder}/{safe_prefix}_{stamp}_{os.urandom(3).hex()}.{ext}"
        with open(path, "wb") as f:
            f.write(data)
        return path
    except Exception as e:
        logger.warning("Local save error: %s", e)
        last_error = "บันทึกรูปไม่สำเร็จ"
        return ""


def get_image_url(path):
    if not path:
        return None
    s = str(path).strip()
    return s if s.startswith("https://") else None
