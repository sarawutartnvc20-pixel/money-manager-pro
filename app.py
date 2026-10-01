import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re
from PIL import Image
import google.generativeai as genai

import importlib

# นำเข้าโมดูลเชื่อมต่อ Google Sheets และ Cloudinary
import sheets_client as db
import image_manager as im
try:
    importlib.reload(db)
    importlib.reload(im)
except Exception:
    pass

def check_cloudinary_ready():
    """ตรวจสอบสถานะ Cloudinary อย่างปลอดภัย ป้องกันปัญหา Cache โมดูล"""
    if hasattr(im, "is_cloudinary_configured"):
        return im.is_cloudinary_configured()
    try:
        conf = st.secrets.get("cloudinary", {})
        secret = str(conf.get("api_secret", "")).strip()
        return bool(secret and "<" not in secret and "<your_api_secret>" not in secret)
    except Exception:
        return False

# ============================================================
# 1. การตั้งค่าหน้าเว็บ (Page Config & Custom CSS)
# ============================================================
st.set_page_config(
    page_title="Money Manager Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS ตกแต่ง UI ให้สวยงาม คมชัด และรองรับ Responsive
st.markdown("""
<style>
    /* ระยะขอบหน้าเว็บ */
    .block-container { 
        padding-top: 1.8rem; 
        padding-bottom: 3rem; 
        max-width: 1200px;
    }
    
    /* กล่องข้อมูลสไตล์ Card */
    .data-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }
    
    /* สไตล์สำหรับกล่องแจ้งเตือนรายการค้าง */
    .pending-alert-box {
        background-color: #fff5f5;
        border-left: 5px solid #e53e3e;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 20px;
    }

    /* ปรับแต่ง Metrics */
    div[data-testid="stMetricValue"] { 
        font-size: 1.8rem !important; 
        font-weight: 700 !important; 
        color: #1E88E5 !important; 
    }
    div[data-testid="stMetricLabel"] { 
        font-size: 0.95rem !important; 
        font-weight: 600 !important; 
        color: #4a5568 !important;
    }
    
    /* ป้ายสถานะ */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        text-align: center;
    }
    .status-paid {
        background-color: #def7ec;
        color: #03543f;
        border: 1px solid #84e1bc;
    }
    .status-pending {
        background-color: #fde8e8;
        color: #9b1c1c;
        border: 1px solid #f8b4b4;
    }
    
    /* ปุ่ม Action */
    div[data-testid="stButton"] > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    /* Responsive บนหน้าจอมือถือ */
    @media only screen and (max-width: 640px) {
        .block-container { 
            padding-top: 1rem; 
            padding-bottom: 1.5rem; 
            padding-left: 0.75rem; 
            padding-right: 0.75rem; 
        }
        h1 { font-size: 1.5rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ส่วนหัวของแอป
st.title("💰 Money Manager Pro (Cloud Version)")
st.caption("ระบบจัดการยอดเงินกลาง & ค่าเช่าจอดูบอล • เชื่อมต่อ Google Sheets & Cloudinary")

# ============================================================
# 2. Flash Message Notification (แสดงผลข้อความแจ้งเตือนหลัง Rerun)
# ============================================================
if "flash_message" in st.session_state:
    flash = st.session_state.pop("flash_message")
    msg_type = flash.get("type", "info")
    msg_text = flash.get("text", "")
    
    if msg_type == "success":
        st.success(msg_text)
        if flash.get("balloons"):
            st.balloons()
    elif msg_type == "warning":
        st.warning(msg_text)
    elif msg_type == "error":
        st.error(msg_text)
    else:
        st.info(msg_text)

# ============================================================
# 3. Gemini Config & Business Logic
# ============================================================
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except Exception as e:
        st.warning(f"⚠️ ตั้งค่า Gemini API ไม่สำเร็จ: {e}")

def calculate_middleman_fee(price: float) -> float:
    """คำนวณค่าธรรมเนียมคนกลางตามขั้นบันไดยอดเงิน"""
    if price <= 1490:
        return 60.0
    elif price <= 2490:
        return 80.0
    elif price <= 3990:
        return 100.0
    elif price <= 5990:
        return 120.0
    elif price <= 7990:
        return 140.0
    elif price <= 9999:
        return 160.0
    else:
        return round(price * 0.02, 2)

def read_slip_with_ai(image: Image.Image):
    """ใช้ Gemini 2.0 Flash ตรวจจับยอดเงินที่โอนสำเร็จจากสลิปธนาคาร"""
    if not GEMINI_KEY:
        st.error("❌ ไม่พบ GEMINI_API_KEY ใน secrets.toml")
        return None
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            "Return ONLY the numerical transfer amount in this Thai bank slip image "
            "(for example: 500 or 1500.50). Do not include currency symbols, commas, or letters."
        )
        response = model.generate_content([prompt, image])
        if not response or not response.text:
            return None
        
        # ค้นหาตัวเลขยอดเงินด้วย regex
        match = re.search(r'\d+(?:,\d+)*(?:\.\d+)?', response.text)
        if match:
            num_str = match.group(0).replace(',', '')
            return float(num_str)
        return None
    except Exception as e:
        st.error(f"❌ AI เกิดข้อผิดพลาดในการอ่านสลิป: {e}")
        return None

def render_slip_item(col, slip_val, caption: str):
    """แสดงรูปภาพสลิปอย่างปลอดภัย รองรับทั้ง Cloudinary URL และ Path ในเครื่อง"""
    if not slip_val or str(slip_val).strip() == "" or pd.isna(slip_val):
        col.caption(f"⚪ ไม่มี{caption}")
        return

    slip_str = str(slip_val).strip()
    if slip_str.startswith("http://") or slip_str.startswith("https://"):
        col.image(slip_str, caption=caption, use_container_width=True)
        col.markdown(f"[🔍 เปิดดูรูปเต็ม]({slip_str})", unsafe_allow_html=True)
    elif os.path.exists(slip_str):
        col.image(slip_str, caption=caption, use_container_width=True)
    else:
        col.info(f"📁 {caption}\n(สลิปบันทึกเดิม: `{os.path.basename(slip_str)}`)")

# ============================================================
# 4. แท็บการทำงาน (UI Tabs)
# ============================================================
tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการเข้า", "📂 ประวัติรายการ", "📊 สรุปรายรับ-กำไร"])

# ------------------------------------------------------------
# TAB 1: บันทึกรายการเข้า
# ------------------------------------------------------------
with tab1:
    st.subheader("📝 บันทึกรายการใหม่")
    col_input, col_preview = st.columns([1.1, 0.9], gap="large")
    
    with col_input:
        st.markdown("#### 📥 ข้อมูลการทำรายการ")
        
        # 1. การตั้งค่าบริการ
        with st.expander("⚙️ เลือกประเภทบริการ & ตัวเลือกเสริม", expanded=True):
            service_type = st.selectbox(
                "เลือกบริการ", 
                ["รับกลางไอดี", "การแลกไอดี", "เช่าจอดูบอล"], 
                key="select_service_type"
            )
            
            is_yok = False
            is_no_note = False
            custom_note = ""
            exchange_rate = 60
            
            if service_type == "รับกลางไอดี":
                col_opt1, col_opt2 = st.columns(2)
                with col_opt1:
                    is_yok = st.checkbox("🔄 มีบริการโยกไอดี (+40.-)", key="chk_yok")
                with col_opt2:
                    is_no_note = st.checkbox("✍️ ลืมเขียนโน๊ต (+5.-)", key="chk_no_note")
                
                custom_note = st.text_input(
                    "📌 บันทึกรายละเอียดเพิ่มเติม (ชื่อลูกค้า / รหัสไอดี)", 
                    placeholder="เช่น กลางไอดี RoV บัญชีคุณบาส",
                    key="custom_note_input"
                )
            elif service_type == "การแลกไอดี":
                def on_rate_change():
                    st.session_state["income_exchange"] = float(st.session_state.get("exchange_rate_choice", 60))

                st.markdown("**🎯 เลือกเรทค่าบริการแลกไอดี:**")
                exchange_rate = st.radio(
                    "เรทค่าบริการ", 
                    [60, 200], 
                    horizontal=True, 
                    format_func=lambda x: f"🏷️ {x} บาท", 
                    label_visibility="collapsed",
                    key="exchange_rate_choice",
                    on_change=on_rate_change
                )
                
                col_opt1, col_opt2 = st.columns(2)
                with col_opt1:
                    is_yok = st.checkbox("🔄 มีบริการโยกไอดี (+40.-)", key="chk_yok_ex")
                with col_opt2:
                    is_no_note = st.checkbox("✍️ ลืมเขียนโน๊ต (+5.-)", key="chk_no_note_ex")
                
                custom_note = st.text_input(
                    "📌 บันทึกรายละเอียดเพิ่มเติม (ชื่อลูกค้า / รหัสไอดี)", 
                    placeholder="เช่น แลกไอดี RoV บัญชี A แลกกับ บัญชี B",
                    key="exchange_note_input"
                )
            else:
                custom_note = st.text_input(
                    "📌 บันทึกรายละเอียดเพิ่มเติม (ช่องที่เช่า / แมตช์)", 
                    placeholder="เช่น เช่าจอพรีเมียร์ลีก บัญชีคุณเอ",
                    key="ball_note_input"
                )

        # 2. อัปโหลดสลิป
        with st.expander("🖼️ อัปโหลดสลิปการโอนเงิน", expanded=True):
            st.markdown("**1. สลิปโอนเข้า (ใบที่ 1)**")
            up1 = st.file_uploader(
                "เลือกรูปสลิปเข้าใบที่ 1", 
                type=['jpg', 'jpeg', 'png', 'webp'], 
                key="file_in_1"
            )
            
            if up1:
                # แสดงภาพสลิปขนาดกะทัดรัด
                st.image(up1, width=220, caption="สลิปโอนเข้า (ใบที่ 1)")
                
                # ปุ่ม AI อ่านสลิป
                if st.button("🤖 ให้ AI (Gemini 2.0 Flash) สแกนอ่านยอดเงิน", key="btn_scan_ai"):
                    with st.spinner("AI กำลังวิเคราะห์สลิป..."):
                        if hasattr(up1, "seek"):
                            up1.seek(0)
                        pil_img = Image.open(up1)
                        detected_val = read_slip_with_ai(pil_img)
                        if detected_val is not None and detected_val > 0:
                            st.session_state['detected_income'] = float(detected_val)
                            if service_type == "การแลกไอดี":
                                st.session_state['income_exchange'] = float(detected_val)
                            else:
                                st.session_state['input_income_general'] = float(detected_val)
                            st.toast(f"✅ AI อ่านยอดเงินสำเร็จ: {detected_val:,.2f} ฿", icon="🎉")
                        else:
                            st.warning("⚠️ AI ไม่สามารถตรวจจับยอดเงินได้ชัดเจน กรุณาระบุยอดเงินด้วยตนเอง")

            st.markdown("**2. สลิปโอนเข้า (ใบที่ 2 - ถ้ามี)**")
            up2 = st.file_uploader(
                "เลือกรูปสลิปเข้าใบที่ 2 (กรณีโอนแยกบัญชี)", 
                type=['jpg', 'jpeg', 'png', 'webp'], 
                key="file_in_2"
            )
            if up2:
                st.image(up2, width=220, caption="สลิปโอนเข้า (ใบที่ 2)")

            st.divider()
            
            # ช่องกรอกยอดเงินเข้า
            if service_type == "การแลกไอดี":
                if "income_exchange" not in st.session_state:
                    st.session_state["income_exchange"] = float(exchange_rate)
                income = st.number_input(
                    "💰 ยอดเงินโอนเข้าทั้งหมด (บาท)", 
                    min_value=0.0, 
                    step=10.0, 
                    format="%.2f",
                    key="income_exchange"
                )
            else:
                if "input_income_general" not in st.session_state:
                    st.session_state["input_income_general"] = float(st.session_state.get('detected_income', 0.0))
                income = st.number_input(
                    "💰 ยอดเงินโอนเข้าทั้งหมด (บาท)", 
                    min_value=0.0, 
                    step=10.0, 
                    format="%.2f",
                    key="input_income_general"
                )

            # สลิปโอนออก (ถ้ามีตั้งแต่แรก)
            up_out = None
            if service_type in ["รับกลางไอดี", "การแลกไอดี"]:
                st.divider()
                st.markdown("**3. สลิปโอนออก (ถ้าโอนให้ผู้ขาย/คู่แลกแล้ว)**")
                up_out = st.file_uploader(
                    "เลือกรูปสลิปโอนออก (ถ้ามี)", 
                    type=['jpg', 'jpeg', 'png', 'webp'], 
                    key="file_out_initial"
                )
                if up_out:
                    st.image(up_out, width=220, caption="สลิปโอนออก")

    with col_preview:
        st.markdown("#### 🔍 ตรวจสอบยอดคำนวณ")
        
        # คำนวณค่าธรรมเนียมและกำไร
        if service_type == "รับกลางไอดี":
            base_fee = calculate_middleman_fee(income)
            extra_fee = (40.0 if is_yok else 0.0) + (5.0 if is_no_note else 0.0)
            profit = base_fee + extra_fee
            expense = max(0.0, income - profit)
            initial_status = "โอนแล้ว"
        elif service_type == "การแลกไอดี":
            base_fee = float(exchange_rate)
            extra_fee = (40.0 if is_yok else 0.0) + (5.0 if is_no_note else 0.0)
            profit = base_fee + extra_fee
            expense = max(0.0, income - profit)
            initial_status = "โอนแล้ว"
        else:
            base_fee = 0.0
            extra_fee = 0.0
            profit = income
            expense = 0.0
            initial_status = "โอนแล้ว"

        status_class = "status-paid"

        # แสดงกล่องสรุปผลแบบเรียลไทม์
        extra_fee_html = ""
        if service_type in ["รับกลางไอดี", "การแลกไอดี"]:
            fee_label = "ค่ากลางพื้นฐาน" if service_type == "รับกลางไอดี" else f"เรทค่าแลกไอดี ({exchange_rate}฿)"
            extra_fee_html += (
                f'<div style="display:flex; justify-content:space-between; font-size:0.9rem; color:#718096; margin-bottom:4px;">'
                f'<span>- {fee_label}:</span><span>{base_fee:,.2f} ฿</span></div>'
            )
            if extra_fee > 0:
                extra_fee_html += (
                    f'<div style="display:flex; justify-content:space-between; font-size:0.9rem; color:#718096; margin-bottom:4px;">'
                    f'<span>- ค่าบริการเสริม (โยก/โน๊ต):</span><span>{extra_fee:,.2f} ฿</span></div>'
                )

        preview_card_html = (
            f'<div class="data-card">'
            f'<h4 style="margin-top:0; color:#2d3748; border-bottom:1px solid #edf2f7; padding-bottom:8px;">'
            f'📋 สรุปรายการคำนวณ ({service_type})</h4>'
            f'<div style="display:flex; justify-content:space-between; margin-bottom:8px;">'
            f'<span>💰 <b>ยอดเงินเข้า:</b></span>'
            f'<span style="font-size:1.15rem; font-weight:700;">{income:,.2f} ฿</span></div>'
            f'<div style="display:flex; justify-content:space-between; margin-bottom:8px;">'
            f'<span>💸 <b>ยอดต้องโอนออก (ยอดสุทธิ):</b></span>'
            f'<span style="font-size:1.15rem; font-weight:700; color:#e53e3e;">{expense:,.2f} ฿</span></div>'
            f'{extra_fee_html}'
            f'<hr style="border:0; border-top:1px dashed #cbd5e0; margin:12px 0;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">'
            f'<span style="font-size:1.1rem; color:#1E88E5; font-weight:700;">📈 กำไรสุทธิของร้าน:</span>'
            f'<span style="font-size:1.4rem; color:#1E88E5; font-weight:800;">{profit:,.2f} ฿</span></div>'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<span>📌 สถานะการโอนออก:</span>'
            f'<span class="status-badge {status_class}">{initial_status}</span></div>'
            f'</div>'
        )
        st.markdown(preview_card_html, unsafe_allow_html=True)

        # ปุ่มบันทึกรายการ
        if st.button("💾 ยืนยันและบันทึกรายการเข้าสู่ระบบ", type="primary", use_container_width=True):
            if income <= 0:
                st.warning("⚠️ กรุณาระบุยอดเงินโอนเข้าที่มากกว่า 0 บาท ก่อนทำการบันทึก")
            else:
                with st.spinner("⏳ กำลังบันทึกข้อมูลและรูปภาพสลิป..."):
                    # 1. คำนวณ ID ถัดไป
                    df_current = db.load_data()
                    new_id = db.get_next_id(df_current)
                    
                    # 2. อัปโหลดรูปภาพ (บันทึกขึ้น Cloudinary หรือบันทึกลงเครื่องอัตโนมัติ)
                    url_in1 = im.upload_image(up1, subfolder="incoming", prefix=f"{new_id}_in1") if up1 else ""
                    url_in2 = im.upload_image(up2, subfolder="incoming", prefix=f"{new_id}_in2") if up2 else ""
                    url_out = im.upload_image(up_out, subfolder="outgoing", prefix=f"{new_id}_out") if (service_type in ["รับกลางไอดี", "การแลกไอดี"] and up_out) else ""
                    
                    # 3. จัดการข้อความรายละเอียด
                    details_parts = []
                    if service_type == "การแลกไอดี":
                        details_parts.append(f"เรทแลก {exchange_rate}฿")
                    if service_type in ["รับกลางไอดี", "การแลกไอดี"]:
                        if is_yok: details_parts.append("โยกไอดี (+40)")
                        if is_no_note: details_parts.append("ลืมโน๊ต (+5)")
                    if custom_note.strip():
                        details_parts.append(custom_note.strip())
                    final_details = " | ".join(details_parts)
                    
                    # สถานะโอนออก (บันทึกและยืนยันในรอบเดียว)
                    final_status = "โอนแล้ว"
                    
                    # 4. บันทึกข้อมูล
                    row_data = {
                        "ID": new_id,
                        "วันที่": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ประเภท": service_type,
                        "รายละเอียด": final_details,
                        "ยอดเข้า": income,
                        "ยอดออก": expense,
                        "กำไร": profit,
                        "สถานะโอนออก": final_status,
                        "สลิปเข้า": url_in1,
                        "สลิปเข้า 2": url_in2,
                        "สลิปออก": url_out
                    }
                    
                    success = db.append_row(row_data)
                    if success:
                        # เคลียร์ค่าที่ AI เคยอ่านค้างไว้
                        if 'detected_income' in st.session_state:
                            del st.session_state['detected_income']
                        if 'income_exchange' in st.session_state:
                            del st.session_state['income_exchange']
                        if 'input_income_general' in st.session_state:
                            del st.session_state['input_income_general']
                        
                        st.session_state["flash_message"] = {
                            "type": "success",
                            "text": f"🎉 บันทึกรายการ ID #{new_id} ({service_type}) ยอด {income:,.2f} ฿ เรียบร้อยแล้ว!",
                            "balloons": True
                        }
                        st.rerun()
                    else:
                        st.error("❌ เกิดข้อผิดพลาด ไม่สามารถส่งข้อมูลไปยัง Google Sheets ได้")

# ------------------------------------------------------------
# TAB 2: ประวัติและคิวการโอน
# ------------------------------------------------------------
with tab2:
    st.subheader("📂 ประวัติรายการทั้งหมด")
    
    # ดึงข้อมูลสดจาก Google Sheets
    df = db.load_data()
    
    if df.empty:
        st.info("ℹ️ ยังไม่มีข้อมูลรายการใน Google Sheets หรือกำลังโหลดข้อมูล...")
    else:
        # ตัวกรองข้อมูล
        filter_col1, filter_col2 = st.columns([1, 1.5])
        with filter_col1:
            filter_type = st.selectbox("กรองตามประเภทบริการ", ["ทั้งหมด", "รับกลางไอดี", "การแลกไอดี", "เช่าจอดูบอล"], key="filter_type")
        with filter_col2:
            search_query = st.text_input("🔍 ค้นหา (ID หรือ รายละเอียด)", placeholder="พิมพ์ค้นหา...", key="filter_search")
            
        filtered_df = df.copy()
        if filter_type != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df["ประเภท"] == filter_type]
        if search_query.strip():
            q = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df["ID"].astype(str).str.contains(q, case=False, na=False) |
                filtered_df["รายละเอียด"].str.lower().str.contains(q, case=False, na=False)
            ]
            
        # เรียงลำดับจาก ID ล่าสุดลงไป
        filtered_df = filtered_df.sort_values(by="ID", ascending=False)
        
        st.caption(f"แสดงผล {len(filtered_df)} รายการ (จากทั้งหมด {len(df)} รายการ)")
        
        # แสดงผลรายการแบบการ์ด Expander
        for idx, (_, row) in enumerate(filtered_df.iterrows()):
            row_id = int(row['ID'])
            is_paid = (str(row['สถานะโอนออก']).strip() == "โอนแล้ว")
            status_badge_class = "status-paid" if is_paid else "status-pending"
            status_text = "โอนแล้ว" if is_paid else "ยังไม่โอน"
            
            expander_title = (
                f"ID #{row_id} | 🗓️ {row['วันที่']} | 🏷️ {row['ประเภท']} "
                f"| 💰 เข้า: {row['ยอดเข้า']:,.2f} ฿ | 💸 ออก: {row['ยอดออก']:,.2f} ฿ "
                f"| 📈 กำไร: {row['กำไร']:,.2f} ฿ | 📌 {status_text}"
            )
            
            with st.expander(expander_title, expanded=False):
                c_info1, c_info2, c_info3, c_del = st.columns([1.2, 1.2, 1.2, 0.8])
                with c_info1:
                    st.write(f"**ยอดเงินเข้า:** {row['ยอดเข้า']:,.2f} ฿")
                    st.write(f"**ยอดต้องโอนออก:** {row['ยอดออก']:,.2f} ฿")
                with c_info2:
                    st.write(f"**กำไรสุทธิ:** :blue[{row['กำไร']:,.2f} ฿]")
                    st.markdown(f"**สถานะ:** <span class='status-badge {status_badge_class}'>{status_text}</span>", unsafe_allow_html=True)
                with c_info3:
                    desc_display = row['รายละเอียด'] if row['รายละเอียด'] else "-"
                    st.write(f"**รายละเอียด/โน๊ต:** {desc_display}")
                with c_del:
                    if st.button("🗑️ ลบรายการ", key=f"btn_del_{idx}_{row_id}", use_container_width=True):
                        with st.spinner("กำลังลบข้อมูล..."):
                            if db.delete_row(row_id):
                                st.session_state["flash_message"] = {
                                    "type": "success",
                                    "text": f"🗑️ ลบรายการ ID #{row_id} สำเร็จแล้ว!",
                                    "balloons": False
                                }
                                st.rerun()
                            else:
                                st.error("❌ ลบรายการไม่สำเร็จ")
                
                st.divider()
                st.markdown("**🖼️ รูปภาพสลิปที่บันทึกในรายการนี้:**")
                im_c1, im_c2, im_c3 = st.columns(3)
                with im_c1:
                    render_slip_item(im_c1, row["สลิปเข้า"], "สลิปเข้า (ใบที่ 1)")
                with im_c2:
                    render_slip_item(im_c2, row["สลิปเข้า 2"], "สลิปเข้า (ใบที่ 2)")
                with im_c3:
                    render_slip_item(im_c3, row["สลิปออก"], "สลิปโอนออก")

                # เมนูแนบสลิปเพิ่มเติม / แก้ไขรูปสลิป
                with st.expander("📷 แนบหรืออัปเดตสลิปเพิ่มเติมสำหรับรายการนี้", expanded=False):
                    u_c1, u_c2, u_c3 = st.columns(3)
                    with u_c1:
                        re_up1 = st.file_uploader("แนบสลิปเข้า 1", type=['jpg', 'jpeg', 'png', 'webp'], key=f"re_up1_{idx}_{row_id}")
                    with u_c2:
                        re_up2 = st.file_uploader("แนบสลิปเข้า 2", type=['jpg', 'jpeg', 'png', 'webp'], key=f"re_up2_{idx}_{row_id}")
                    with u_c3:
                        re_up_out = st.file_uploader("แนบสลิปออก", type=['jpg', 'jpeg', 'png', 'webp'], key=f"re_upout_{idx}_{row_id}")
                    
                    if st.button("💾 บันทึกรูปสลิปใหม่", key=f"btn_save_slips_{idx}_{row_id}", use_container_width=True):
                        changed = False
                        if re_up1:
                            u1 = im.upload_image(re_up1, subfolder="incoming", prefix=f"{row_id}_in1")
                            if u1:
                                db.update_cell(row_id, "สลิปเข้า", u1)
                                changed = True
                        if re_up2:
                            u2 = im.upload_image(re_up2, subfolder="incoming", prefix=f"{row_id}_in2")
                            if u2:
                                db.update_cell(row_id, "สลิปเข้า 2", u2)
                                changed = True
                        if re_up_out:
                            u_out = im.upload_image(re_up_out, subfolder="outgoing", prefix=f"{row_id}_out")
                            if u_out:
                                db.update_cell(row_id, "สลิปออก", u_out)
                                changed = True
                        if changed:
                            st.session_state["flash_message"] = {
                                "type": "success",
                                "text": f"✅ อัปเดตรูปสลิป ID #{row_id} สำเร็จแล้ว!",
                                "balloons": False
                            }
                            st.rerun()
                        else:
                            st.warning("⚠️ กรุณาเลือกไฟล์สลิปก่อนกดบันทึก")

        # ปุ่มดาวน์โหลด Excel / CSV
        st.divider()
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ดาวน์โหลดข้อมูลทั้งหมดเป็นไฟล์ Excel (.csv)",
            data=csv_data,
            file_name=f"money_manager_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ------------------------------------------------------------
# TAB 3: สรุปรายรับ-กำไร
# ------------------------------------------------------------
with tab3:
    st.subheader("📊 สรุปรายรับ กำไร และภาพรวมการเงิน")
    
    df_report = db.load_data()
    
    if df_report.empty:
        st.info("ℹ️ ยังไม่มีข้อมูลสำหรับสรุปผลการดำเนินงาน")
    else:
        # แปลงวันที่อย่างปลอดภัย
        df_report["dt"] = pd.to_datetime(df_report["วันที่"], errors="coerce")
        now = datetime.now()
        
        # กรองข้อมูลตามช่วงเวลา
        df_valid_dates = df_report.dropna(subset=["dt"])
        
        df_today = df_valid_dates[df_valid_dates["dt"].dt.date == now.date()]
        df_month = df_valid_dates[
            (df_valid_dates["dt"].dt.month == now.month) & 
            (df_valid_dates["dt"].dt.year == now.year)
        ]
        
        # 1. แผงตัวเลขภาพรวม (Key Metrics)
        st.markdown("#### 📈 สรุปผลกำไรและยอดเงินหมุนเวียน")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("กำไรวันนี้", f"{df_today['กำไร'].sum():,.2f} ฿", f"{len(df_today)} รายการ")
        m2.metric("กำไรเดือนนี้", f"{df_month['กำไร'].sum():,.2f} ฿", f"{len(df_month)} รายการ")
        m3.metric("ยอดเงินเข้าสะสมรวม", f"{df_report['ยอดเข้า'].sum():,.2f} ฿")
        m4.metric("กำไรสุทธิรวมทั้งหมด", f"{df_report['กำไร'].sum():,.2f} ฿", f"รวม {len(df_report)} รายการ")
        
        st.divider()
        
        # 2. แยกตามประเภทบริการ
        st.markdown("#### 🏷️ สรุปแยกตามประเภทบริการ")
        b1, b2, b3 = st.columns(3)
        
        df_mid = df_report[df_report["ประเภท"] == "รับกลางไอดี"]
        df_ex = df_report[df_report["ประเภท"] == "การแลกไอดี"]
        df_ball = df_report[df_report["ประเภท"] == "เช่าจอดูบอล"]
        
        with b1:
            mid_box_html = (
                f'<div class="data-card" style="border-top: 4px solid #1E88E5;">'
                f'<h4 style="margin-top:0; color:#1E88E5;">💎 รับกลางไอดี</h4>'
                f'<p>จำนวนรายการ: <b>{len(df_mid)}</b> รายการ</p>'
                f'<p>ยอดเงินเข้าทั้งหมด: <b>{df_mid["ยอดเข้า"].sum():,.2f} ฿</b></p>'
                f'<p>ยอดที่โอนออกให้ผู้ขาย: <b>{df_mid["ยอดออก"].sum():,.2f} ฿</b></p>'
                f'<p style="font-size:1.15rem; color:#1E88E5; font-weight:700;">'
                f'กำไรสุทธิ: {df_mid["กำไร"].sum():,.2f} ฿</p>'
                f'</div>'
            )
            st.markdown(mid_box_html, unsafe_allow_html=True)
            
        with b2:
            ex_box_html = (
                f'<div class="data-card" style="border-top: 4px solid #8B5CF6;">'
                f'<h4 style="margin-top:0; color:#8B5CF6;">🔄 การแลกไอดี</h4>'
                f'<p>จำนวนรายการ: <b>{len(df_ex)}</b> รายการ</p>'
                f'<p>ยอดเงินเข้าทั้งหมด: <b>{df_ex["ยอดเข้า"].sum():,.2f} ฿</b></p>'
                f'<p>ยอดที่โอนออก: <b>{df_ex["ยอดออก"].sum():,.2f} ฿</b></p>'
                f'<p style="font-size:1.15rem; color:#8B5CF6; font-weight:700;">'
                f'กำไรสุทธิ: {df_ex["กำไร"].sum():,.2f} ฿</p>'
                f'</div>'
            )
            st.markdown(ex_box_html, unsafe_allow_html=True)

        with b3:
            ball_box_html = (
                f'<div class="data-card" style="border-top: 4px solid #10B981;">'
                f'<h4 style="margin-top:0; color:#10B981;">⚽ เช่าจอดูบอล</h4>'
                f'<p>จำนวนรายการ: <b>{len(df_ball)}</b> รายการ</p>'
                f'<p>ยอดเงินเข้าทั้งหมด: <b>{df_ball["ยอดเข้า"].sum():,.2f} ฿</b></p>'
                f'<p>ยอดที่โอนออก: <b>0.00 ฿</b> (ไม่มีโอนออก)</p>'
                f'<p style="font-size:1.15rem; color:#10B981; font-weight:700;">'
                f'กำไรสุทธิ: {df_ball["กำไร"].sum():,.2f} ฿</p>'
                f'</div>'
            )
            st.markdown(ball_box_html, unsafe_allow_html=True)

        st.divider()
        
        # 3. ตารางสรุปข้อมูลทั้งหมด
        st.markdown("#### 📋 ตารางข้อมูลทั้งหมด (Synchronized กับ Google Sheets)")
        table_cols = ["ID", "วันที่", "ประเภท", "รายละเอียด", "ยอดเข้า", "ยอดออก", "กำไร", "สถานะโอนออก"]
        st.dataframe(
            df_report[table_cols].sort_values(by="ID", ascending=False),
            use_container_width=True,
            hide_index=True
        )
