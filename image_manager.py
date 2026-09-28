import os
import re
from datetime import datetime
import cloudinary
import cloudinary.uploader
import streamlit as st

def is_cloudinary_configured() -> bool:
    """ตรวจสอบว่า Cloudinary มีการตั้งค่า API Secret จริงหรือไม่"""
    try:
        conf = st.secrets.get("cloudinary", {})
        secret = str(conf.get("api_secret", "")).strip()
        if not secret or "<your_api_secret>" in secret or "<" in secret:
            return False
        if "cloudinary://" in secret:
            match = re.search(r'cloudinary://([^:]+):([^@]+)@(.+)', secret)
            if match and "<" not in match.group(2):
                return True
            return False
        return True
    except Exception:
        return False

def configure_cloudinary():
    """ตั้งค่าเชื่อมต่อ Cloudinary โดยรองรับการตัดแต่งและ parse URL อัตโนมัติ"""
    try:
        conf = st.secrets["cloudinary"]
        cloud_name = str(conf.get("cloud_name", "")).strip()
        api_key = str(conf.get("api_key", "")).strip()
        api_secret = str(conf.get("api_secret", "")).strip()

        # กรณีผู้ใช้วาง CLOUDINARY_URL ทั้งบรรทัดลงในช่อง api_secret
        if "cloudinary://" in api_secret:
            match = re.search(r'cloudinary://([^:]+):([^@]+)@(.+)', api_secret)
            if match:
                if not api_key:
                    api_key = match.group(1).strip()
                api_secret = match.group(2).strip()
                if not cloud_name:
                    cloud_name = match.group(3).strip()

        # หากยังเป็นค่า placeholder หรือเว้นว่าง จะไม่อนุญาตให้อัปโหลด
        if not cloud_name or not api_key or not api_secret or "<" in api_secret:
            return False

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        return True
    except Exception as e:
        print(f"Cloudinary config error: {e}")
        return False

def upload_image(file, subfolder="incoming", prefix="slip"):
    """
    อัปโหลดรูปภาพไปยัง Cloudinary (คืนค่าเป็น HTTPS URL)
    หาก Cloudinary ยังไม่พร้อม จะเซฟลงโฟลเดอร์ slips/ ในเครื่องอัตโนมัติ เพื่อให้แสดงผลในประวัติได้ทันที
    """
    if not file:
        return ""

    # 1. พยายามอัปโหลดขึ้น Cloudinary ถ้าการตั้งค่าพร้อม
    if configure_cloudinary():
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            response = cloudinary.uploader.upload(
                file,
                folder="money_manager_pro"
            )
            secure_url = response.get("secure_url", "")
            if secure_url:
                return secure_url
        except Exception as e:
            print(f"❌ Cloudinary Upload Error: {e}")

    # 2. Local Fallback: บันทึกไฟล์ลงโฟลเดอร์ slips/ ในเครื่อง
    try:
        if hasattr(file, "seek"):
            file.seek(0)
        os.makedirs(f"slips/{subfolder}", exist_ok=True)
        orig_name = getattr(file, "name", "slip.jpg")
        ext = orig_name.split(".")[-1] if "." in orig_name else "jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rnd = os.urandom(2).hex()
        save_path = f"slips/{subfolder}/{prefix}_{timestamp}_{rnd}.{ext}"
        
        content = file.getbuffer() if hasattr(file, "getbuffer") else file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        return save_path
    except Exception as e:
        print(f"❌ Local Save Error: {e}")
        return ""

def get_image_url(path):
    """ตรวจสอบความถูกต้องของ URL สลิป"""
    if not path:
        return None
    path_str = str(path).strip()
    if path_str.startswith("http://") or path_str.startswith("https://"):
        return path_str
    return None
