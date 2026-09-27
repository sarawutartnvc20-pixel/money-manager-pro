import cloudinary
import cloudinary.uploader
import streamlit as st

# ตั้งค่า Cloudinary จาก secrets
def configure_cloudinary():
    try:
        conf = st.secrets["cloudinary"]
        cloudinary.config( 
            cloud_name = conf["cloud_name"], 
            api_key = conf["api_key"], 
            api_secret = conf["api_secret"] 
        )
        return True
    except Exception as e:
        st.error(f"❌ ไม่สามารถตั้งค่า Cloudinary ได้: {e}")
        return False

def upload_image(file):
    """
    อัปโหลดรูปภาพไปยัง Cloudinary และคืนค่าเป็น URL ของรูป
    """
    if not configure_cloudinary():
        return None
        
    try:
        # อัปโหลดไฟล์ (ส่งเป็น bytes จาก streamlit uploaded_file)
        # ใช้ folder เพื่อแยกประเภทใน Cloudinary
        response = cloudinary.uploader.upload(
            file, 
            folder="money_manager_pro"
        )
        # คืนค่า secure_url (https)
        return response.get("secure_url")
    except Exception as e:
        st.error(f"❌ อัปโหลดรูปภาพล้มเหลว: {e}")
        return None

def get_image_url(path):
    """
    ตรวจสอบว่า path เป็น URL หรือไม่ ถ้าเป็น path local ให้แจ้งเตือน 
    (ในระบบใหม่ทุกอย่างจะเป็น URL อยู่แล้ว)
    """
    if not path:
        return None
    if path.startswith("http"):
        return path
    # ถ้าเป็น path เก่า (slips/...) จะไม่สามารถแสดงผลบน cloud ได้
    return None
