import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image

# นำเข้าตัวเชื่อมต่อ Google Sheets และ Cloudinary
import sheets_client as db
import image_manager as im

# ============================================================
# 1. Page Config & CSS
# ============================================================
st.set_page_config(page_title="Money Manager Pro", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .data-container { background-color: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; color: #1E88E5 !important; }
    div[data-testid="stMetricLabel"] { font-size: 1rem !important; font-weight: 500 !important; }
    .status-paid { color: #28a745; font-weight: bold; }
    .status-pending { color: #dc3545; font-weight: bold; }
    button[kind="primary"] { width: 100%; }
    @media only screen and (max-width: 640px) {
        .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.6rem; padding-right: 0.6rem; }
        h1 { font-size: 1.6rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
        div[data-testid="stButton"] > button { min-height: 48px; }
    }
</style>
""", unsafe_allow_html=True)

st.title("💰 ระบบจัดการยอดกลาง & ดูบอล (Cloud Version)")

# Gemini Config
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("❌ ไม่พบ GEMINI_API_KEY ใน Secrets")
    GEMINI_API_KEY = ""

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============================================================
# 2. Business Logic & AI
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
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(["Return ONLY the number of the transfer amount in this image. Do not include currency symbols or commas.", image])
        amount_str = "".join(c for c in response.text if c.isdigit() or c == '.')
        return float(amount_str) if amount_str else None
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# ============================================================
# 3. UI Tabs
# ============================================================
tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการเข้า", "🗂️ ประวัติและคิว", "📊 สรุปรายรับ-กำไร"])

with tab1:
    st.header("📝 บันทึกรายการเข้า")
    col_input, col_preview = st.columns([1, 1], gap="large")
    
    with col_input:
        st.markdown("### 📥 ข้อมูลการโอนเข้า")
        with st.expander("⚙️ ตั้งค่าบริการ", expanded=True):
            service_type = st.selectbox("เลือกบริการ", ["รับกลางไอดี", "เช่าจอดูบอล"])
            is_yok = st.checkbox("มีบริการโยกไอดี (+40.-)") if service_type == "รับกลางไอดี" else False
            is_no_note = st.checkbox("ลืมเขียนโน๊ต (+5.-)") if service_type == "รับกลางไอดี" else False
        
        with st.expander("🖼️ อัปโหลดสลิป", expanded=True):
            up1 = st.file_uploader("เลือกสลิปโอนเข้า (ใบที่ 1)", type=['jpg','jpeg','png'], key="in1")
            if up1:
                st.image(up1, width=200)
                if st.button("🔍 อ่านยอดใบที่ 1"):
                    res = read_slip_with_ai(Image.open(up1))
                    if res: st.session_state['inc_detected'] = res
            
            up2 = st.file_uploader("เลือกสลิปโอนเข้า (ใบที่ 2 - ถ้ามี)", type=['jpg','jpeg','png'], key="in2")
            if up2: st.image(up2, width=200)
            
            income = st.number_input("ยอดเงินเข้า", value=st.session_state.get('inc_detected', 0.0))
            
            if service_type == "รับกลางไอดี":
                st.divider()
                up_out = st.file_uploader("เลือกสลิปโอนออก (ถ้ามี)", type=['jpg','jpeg','png'], key="out_initial")

    with col_preview:
        st.markdown("### 🔍 ตรวจสอบยอด")
        if service_type == "รับกลางไอดี":
            fee = calculate_middleman_fee(income)
            extra = (40 if is_yok else 0) + (5 if is_no_note else 0)
            profit, expense = fee + extra, income - (fee + extra)
        else:
            profit, expense = income, 0
        
        st.markdown(f"""<div class="data-container">
            <p>💰 <b>ยอดเงินเข้า:</b> {income:,.2f} ฿</p>
            <p>💸 <b>ยอดต้องโอนออก:</b> {expense:,.2f} ฿</p>
            <hr>
            <p style="font-size:1.3rem; color:#1E88E5; font-weight:bold;">📈 กำไรสุทธิ: {profit:,.2f} ฿</p>
            </div>""", unsafe_allow_html=True)
        
        # บันทึกข้อมูล
        if st.button("✅ บันทึกรายการ", type="primary"):
            with st.spinner("กำลังบันทึกข้อมูลและอัปโหลดรูป..."):
                # อัปโหลดรูปไปยัง Cloudinary
                url_in1 = im.upload_image(up1) if up1 else ""
                url_in2 = im.upload_image(up2) if up2 else ""
                url_out = im.upload_image(up_out) if (service_type == "รับกลางไอดี" and up_out) else ""
                
                # เตรียมข้อมูล
                df_current = db.load_data()
                new_id = db.get_next_id(df_current)
                
                # กำหนดสถานะโอนออก
                # ถ้าเป็น "เช่าจอดูบอล" ให้ถือว่าโอนแล้ว (เพราะไม่มีการโอนออกยอดกลาง) 
                # หรือ ถ้ามีสลิปโอนออก ก็ถือว่าโอนแล้ว
                status = "โอนแล้ว" if (service_type == "เช่าจอดูบอล" or url_out != "") else "ยังไม่โอน"
                
                row_data = {
                    "ID": new_id,
                    "วันที่": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "ประเภท": service_type,
                    "รายละเอียด": f"โยก:{is_yok}, NoNote:{is_no_note}" if service_type == "รับกลางไอดี" else "",
                    "ยอดเข้า": income,
                    "ยอดออก": expense,
                    "กำไร": profit,
                    "สถานะโอนออก": status,
                    "สลิปเข้า": url_in1,
                    "สลิปเข้า 2": url_in2,
                    "สลิปออก": url_out
                }
                
                if db.append_row(row_data):
                    st.success(f"บันทึกรายการ ID {new_id} สำเร็จ!")
                    st.balloons()
                else:
                    st.error("เกิดข้อผิดพลาดในการบันทึกข้อมูล")
                
                st.rerun()

with tab2:
    st.header("🗂️ ประวัติและคิวการโอน")
    df = db.load_data()
    
    if df.empty:
        st.info("ยังไม่มีข้อมูลในระบบ")
    else:
        # --- ส่วนคิวโอนเงิน ---
        pending_df = df[df["สถานะโอนออก"] == "ยังไม่โอน"]
        if not pending_df.empty:
            st.markdown("### 🔴 รายการค้างโอน")
            st.dataframe(pending_df[["ID", "วันที่", "ประเภท", "ยอดออก"]], use_container_width=True, hide_index=True)
            
            with st.expander("✔️ ยืนยันการโอนออก"):
                c_id, c_up = st.columns([1, 2])
                with c_id:
                    t_id = st.number_input("ใส่ ID รายการ", min_value=1, step=1)
                with c_up:
                    t_up = st.file_uploader("อัปโหลดสลิปโอนออก", type=['jpg','jpeg','png'], key="confirm_up")
                
                if st.button("✅ ยืนยันการโอน"):
                    if t_id in df["ID"].values:
                        url_out = im.upload_image(t_up) if t_up else ""
                        if db.update_cell(t_id, "สถานะโอนออก", "โอนแล้ว") and db.update_cell(t_id, "สลิปออก", url_out):
                            st.success(f"ยืนยันการโอน ID {t_id} เรียบร้อย!")
                            st.rerun()
                        else:
                            st.error("อัปเดตข้อมูลไม่สำเร็จ")
                    else:
                        st.error("ไม่พบ ID นี้ในระบบ")

        st.divider()
        
        # --- ส่วนประวัติทั้งหมด ---
        st.markdown("### 📂 ประวัติรายการ")
        # เรียง ID จากมากไปน้อย
        df_sorted = df.sort_values("ID", ascending=False)
        
        # แสดงผลแบบการ์ด
        for _, row in df_sorted.iterrows():
            status_class = "status-paid" if row["สถานะโอนออก"] == "โอนแล้ว" else "status-pending"
            
            with st.expander(f"ID {row['ID']} | {row['วันที่']} | {row['ประเภท']}"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**ยอดเข้า:** {row['ยอดเข้า']:,.2f} ฿")
                col2.write(f"**ยอดออก:** {row['ยอดออก']:,.2f} ฿")
                col3.markdown(f"**สถานะ:** <span class='{status_class}'>{row['สถานะโอนออก']}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**กำไร:** {row['กำไร']:,.2f} ฿")
                
                # แสดงรูปภาพสลิป
                im_col1, im_col2, im_col3 = st.columns(3)
                if row["สลิปเข้า"]:
                    im_col1.image(row["สลิปเข้า"], caption="สลิปเข้า 1", width=150)
                if row["สลิปเข้า 2"]:
                    im_col2.image(row["สลิปเข้า 2"], caption="สลิปเข้า 2", width=150)
                if row["สลิปออก"]:
                    im_col3.image(row["สลิปออก"], caption="สลิปออก", width=150)
                
                if st.button(f"🗑️ ลบรายการ ID {row['ID']}", key=f"del_{row['ID']}"):
                    if db.delete_row(row['ID']):
                        st.success("ลบรายการแล้ว")
                        st.rerun()

with tab3:
    st.header("📊 สรุปรายรับ-กำไร")
    df = db.load_data()
    
    if not df.empty:
        df["วันที่"] = pd.to_datetime(df["วันที่"])
        now = datetime.now()
        
        # กรองข้อมูล
        df_today = df[df["วันที่"].dt.date == now.date()]
        df_month = df[df["วันที่"].dt.month == now.month]
        df_month = df_month[df_month["วันที่"].dt.year == now.year]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("กำไรวันนี้", f"{df_today['กำไร'].sum():,.2f} ฿")
        m2.metric("กำไรเดือนนี้", f"{df_month['กำไร'].sum():,.2f} ฿")
        m3.metric("ยอดเงินเข้าสะสม", f"{df['ยอดเข้า'].sum():,.2f} ฿")
        
        st.divider()
        st.markdown("### 📉 ตารางสรุป")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("ไม่มีข้อมูลสำหรับแสดงผล")
