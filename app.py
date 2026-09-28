import streamlit as st
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai
from PIL import Image
import base64

# นำเข้าตัวเชื่อมต่อ Google Sheets และ Cloudinary
import sheets_client as db
import image_manager as im

# ============================================================
# 1. การตั้งค่าหน้าเว็บ (Page Config)
# ============================================================
st.set_page_config(
    page_title="Money Manager Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .data-container {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] { 
        font-size: 1.8rem !important; 
        font-weight: 700 !important; 
        color: #1E88E5 !important; 
    }
    div[data-testid="stMetricLabel"] { 
        font-size: 1rem !important; 
        font-weight: 500 !important; 
    }
    .status-paid { color: #28a745; font-weight: bold; }
    .status-pending { color: #dc3545; font-weight: bold; }
    div[data-testid="stExpander"] details { width: 100%; }
    div[data-testid="stExpander"] summary { width: 100%; cursor: pointer; }
    button[kind="primary"] { width: 100%; }
    @media only screen and (max-width: 640px) {
        .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.6rem; padding-right: 0.6rem; }
        h1 { font-size: 1.6rem !important; }
        h2, h3 { font-size: 1.15rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button { min-height: 48px; }
        .stTabs [data-testid="stHorizontalBlock"] { gap: 0.2rem; }
        .stTabs [data-baseweb="tab"] { font-size: 0.8rem; padding: 8px 10px; }
        .stTabs [data-baseweb="tab-list"] { gap: 0px; }
        div[data-testid="stImage"] img { max-width: 100%; height: auto; }
        div[data-testid="stDataFrame"] { height: auto !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("💰 ระบบจัดการยอดกลาง & ดูบอล (Cloud Version)")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = "AQ.Ab8RN6Jdk2tLfdGyn5o_QSeki1L8DZvB0RXHd8WdKM---2BoyA" 

genai.configure(api_key=GEMINI_API_KEY)

# ============================================================
# 2. Logic คำนวณ (Business Logic)
# ============================================================
def calculate_middleman_fee(price):
    if price <= 1490: return 60
    elif price <= 2490: return 80
    elif price <= 3990: return 100
    elif price <= 5990: return 120
    elif price <= 7990: return 140
    elif price <= 9999: return 160
    else: return price * 0.02

def read_slip_with_ai(image):
    try:
        prompt = "Return ONLY the number of the transfer amount in this image."
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([prompt, image])
        res_text = response.text
        amount_str = "".join(c for c in res_text if c.isdigit() or c == '.')
        if amount_str: return float(amount_str)
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการอ่านสลิป: {e}")
        return None

# ============================================================
# 3. หน้าจอการทำงาน (UI Layout)
# ============================================================
tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการเข้า", "🗂️ ประวัติและคิว", "📊 สรุปรายรับ-กำไร"])

with tab1:
    st.header("📝 บันทึกรายการเข้า")
    with st.container():
        col_input, col_preview = st.columns([1, 1], gap="large")
        with col_input:
            st.markdown("### 📥 ข้อมูลการโอนเข้า")
            with st.expander("⚙️ ตั้งค่าบริการ", expanded=True):
                service_type = st.selectbox("เลือกบริการ", ["รับกลางไอดี", "เช่าจอดูบอล"])
                is_yok = False
                is_no_note = False
                if service_type == "รับกลางไอดี":
                    c_opt1, c_opt2 = st.columns(2)
                    with c_opt1: is_yok = st.checkbox("มีบริการโยกไอดี (+40.-)")
                    with c_opt2: is_no_note = st.checkbox("ลืมเขียนโน๊ต (+5.-)")
            
            with st.expander("🖼️ อัปโหลดสลิป", expanded=True):
                uploaded_file1 = st.file_uploader("เลือกสลิปโอนเข้า (ใบที่ 1)", type=['jpg', 'jpeg', 'png'], key="slip_in_1")
                if uploaded_file1:
                    img1 = Image.open(uploaded_file1)
                    st.image(img1, width=200)
                    if st.button("🔍 ให้ AI อ่านยอด (ใบที่ 1)"):
                        with st.spinner("กำลังอ่านสลิป..."):
                            detected_amount = read_slip_with_ai(img1)
                            if detected_amount: st.session_state['detected_income'] = detected_amount
                    st.session_state['uploaded_slip_in1'] = uploaded_file1
                
                uploaded_file2 = st.file_uploader("เลือกสลิปโอนเข้า (ใบที่ 2 - ถ้ามี)", type=['jpg', 'jpeg', 'png'], key="slip_in_2")
                if uploaded_file2:
                    img2 = Image.open(uploaded_file2)
                    st.image(img2, width=200)
                    st.session_state['uploaded_slip_in2'] = uploaded_file2
                
                income = st.number_input("ยอดที่ AI อ่านได้ (แก้ไขได้)", value=st.session_state.get('detected_income', 0.0))
                
                if service_type == "รับกลางไอดี":
                    st.divider()
                    uploaded_out = st.file_uploader("เลือกสลิปโอนออก (ถ้ามี)", type=['jpg', 'jpeg', 'png'])
                    if uploaded_out: st.session_state['uploaded_slip_out'] = uploaded_out
                    elif 'uploaded_slip_out' in st.session_state: del st.session_state['uploaded_slip_out']

        with col_preview:
            st.markdown("### 🔍 ตรวจสอบยอดก่อนบันทึก")
            if service_type == "รับกลางไอดี":
                fee = calculate_middleman_fee(income)
                extra_fee = (40 if is_yok else 0) + (5 if is_no_note else 0)
                profit = fee + extra_fee
                expense = income - fee - extra_fee
            else:
                fee, profit, expense = 0, income, 0
            
            st.markdown(f"""
            <div class="data-container">
                <p style="margin-bottom: 10px; font-size: 1.1rem;">💰 <b>ยอดเงินเข้า:</b> {income:,.2f} ฿</p>
                <p style="margin-bottom: 10px; font-size: 1.1rem;">💸 <b>ยอดต้องโอนออก:</b> {expense:,.2f} ฿</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                <p style="font-size: 1.3rem; color: #1E88E5; font-weight: bold;">📈 กำไรสุทธิ: {profit:,.2f} ฿</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ ยืนยันและบันทึกเข้าฐานข้อมูล", use_container_width=True):
                with st.spinner("กำลังบันทึกข้อมูล..."):
                    df = db.load_data()
                    new_id = db.get_next_id(df)
                    
                    path_in1 = ""
                    if 'uploaded_slip_in1' in st.session_state:
                        path_in1 = im.upload_image(st.session_state['uploaded_slip_in1'])
                        del st.session_state['uploaded_slip_in1']
                    
                    path_in2 = ""
                    if 'uploaded_slip_in2' in st.session_state:
                        path_in2 = im.upload_image(st.session_state['uploaded_slip_in2'])
                        del st.session_state['uploaded_slip_in2']
                    
                    path_out = ""
                    if 'uploaded_slip_out' in st.session_state:
                        path_out = im.upload_image(st.session_state['uploaded_slip_out'])
                        del st.session_state['uploaded_slip_out']
                    
                    status = "โอนแล้ว" if (service_type == "เช่าจอดูบอล" or path_out != "") else "ยังไม่โอน"
                    
                    row_dict = {
                        "ID": new_id,
                        "วันที่": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ประเภท": service_type,
                        "รายละเอียด": "",
                        "ยอดเข้า": income,
                        "ยอดออก": expense,
                        "กำไร": profit,
                        "สถานะโอนออก": status,
                        "สลิปเข้า": path_in1,
                        "สลิปเข้า 2": path_in2,
                        "สลิปออก": path_out
                    }
                    if db.append_row(row_dict):
                        st.success("✅ บันทึกลง Google Sheets & Cloudinary เรียบร้อย!")
                        st.balloons()
                    else:
                        st.error("❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล")
                    
                    st.rerun()

with tab2:
    st.header("📜 จัดการประวัติและคิวการโอนเงิน")
    df = db.load_data()
    if not df.empty:
        pending_queue = df[df['สถานะโอนออก'] == "ยังไม่โอน"]
        if not pending_queue.empty:
            st.markdown("### 🔴 รายการค้างโอน (Pending Queue)")
            with st.container():
                st.markdown('<div class="data-container" style="border-left: 5px solid #dc3545;">', unsafe_allow_html=True)
                st.dataframe(pending_queue[['ID', 'วันที่', 'ประเภท', 'ยอดออก', 'สถานะโอนออก']], use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_//... (rest of the code edited below)
