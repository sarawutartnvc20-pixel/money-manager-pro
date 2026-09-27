import streamlit as st
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai
from PIL import Image
import base64

# นำเข้าตัวเชื่อมต่อ Google Sheets
import sheets_client as db

# ============================================================
# 1. การตั้งค่าหน้าเว็บ (Page Config)
# ============================================================
st.set_page_config(
    page_title="Money Manager Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS เพื่อให้ UI ดูเป็นมืออาชีพและสะอาดตา ---
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
                uploaded_file = st.file_uploader("เลือกสลิปโอนเข้า", type=['jpg', 'jpeg', 'png'])
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    st.image(img, width=250)
                    if st.button("🔍 ให้ AI อ่านยอด"):
                        with st.spinner("กำลังอ่านสลิป..."):
                            detected_amount = read_slip_with_ai(img)
                            if detected_amount: st.session_state['detected_income'] = detected_amount
                    income = st.number_input("ยอดที่ AI อ่านได้ (แก้ไขได้)", value=st.session_state.get('detected_income', 0.0))
                    st.session_state['uploaded_slip_in'] = uploaded_file
                else:
                    income = 0.0
                
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
                df = db.load_data()
                new_id = db.get_next_id(df)
                
                # จัดการไฟล์สลิป (ยังบันทึกในเครื่อง/cloud storage เดิม)
                path_in = ""
                if 'uploaded_slip_in' in st.session_state:
                    slip_file = st.session_state['uploaded_slip_in']
                    file_ext = slip_file.name.split('.')[-1]
                    path_in = f"slips/incoming/{new_id}_in.{file_ext}"
                    os.makedirs("slips/incoming", exist_ok=True)
                    with open(path_in, "wb") as f: f.write(slip_file.getbuffer())
                    del st.session_state['uploaded_slip_in']
                
                path_out = ""
                if 'uploaded_slip_out' in st.session_state:
                    slip_out_file = st.session_state['uploaded_slip_out']
                    file_ext_out = slip_out_file.name.split('.')[-1]
                    path_out = f"slips/outgoing/{new_id}_out.{file_ext_out}"
                    os.makedirs("slips/outgoing", exist_ok=True)
                    with open(path_out, "wb") as f: f.write(slip_out_file.getbuffer())
                    del st.session_state['uploaded_slip_out']
                
                status = "โอนแล้ว" if (service_type == "เช่าจอดูบอล" or path_out != "") else "ยังไม่โอน"
                
                # บันทึกลง Google Sheets
                row_dict = {
                    "ID": new_id,
                    "วันที่": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "ประเภท": service_type,
                    "รายละเอียด": "",
                    "ยอดเข้า": income,
                    "ยอดออก": expense,
                    "กำไร": profit,
                    "สถานะโอนออก": status,
                    "สลิปเข้า": path_in,
                    "สลิปออก": path_out
                }
                db.append_row(row_dict)
                
                st.toast("✅ บันทึกลง Google Sheets เรียบร้อย!", icon="🎉")
                st.balloons()
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
                st.markdown('</div>', unsafe_allow_html=True)
                
                with st.expander("✔️ ยืนยันการโอนเงินเข้าคิว", expanded=True):
                    c_id, c_slip = st.columns([1, 2])
                    with c_id:
                        pending_ids = sorted(pending_queue['ID'].tolist())
                        target_id = st.selectbox("เลือก ID ที่โอนเรียบร้อยแล้ว", pending_ids, key="confirm_transfer_id")
                    with c_slip:
                        uploaded_slip_out = st.file_uploader("อัปโหลดสลิปโอนออก", type=['jpg', 'jpeg', 'png'], key="confirm_transfer_slip")
                    
                    if st.button("✅ ยืนยันการโอน", use_container_width=True):
                        path_out = ""
                        if uploaded_slip_out:
                            file_ext = uploaded_slip_out.name.split('.')[-1]
                            path_out = f"slips/outgoing/{target_id}_out.{file_ext}"
                            os.makedirs("slips/outgoing", exist_ok=True)
                            with open(path_out, "wb") as f: f.write(uploaded_slip_out.getbuffer())
                        
                        db.update_cell(target_id, "สถานะโอนออก", "โอนแล้ว")
                        db.update_cell(target_id, "สลิปออก", path_out)
                        st.success(f"✅ คิวที่ {target_id} ยืนยันการโอนเรียบร้อย!")
                        st.rerun()
        
        st.divider()
        st.markdown("### 📂 ประวัติรายการทั้งหมด")
        history_df = df.sort_values(by="ID", ascending=False)
        tab_mid, tab_ball = st.tabs(["💎 รับกลางไอดี", "⚽ เช่าจอดูบอล"])
        
        with tab_mid:
            df_mid = history_df[history_df['ประเภท'] == "รับกลางไอดี"]
            if df_mid.empty: st.info("ไม่มีรายการรับกลางไอดี")
            for idx, (index, row) in enumerate(df_mid.iterrows()):
                status_class = "status-paid" if row['สถานะโอนออก'] == "โอนแล้ว" else "status-pending"
                status_text = f'<span class="{status_class}">{row["สถานะโอนออก"]}</span>'
                with st.expander(f"คิวที่ {row['ID']} - {row['วันที่']}"):
                    c1, c2, c3, c4 = st.columns([1,1,1,1])
                    c1.write(f"**ประเภท:** {row['ประเภท']}")
                    c2.write(f"**กำไร:** {row['กำไร']:,.2f} ฿")
                    c3.markdown(f"**สถานะ:** {status_text}", unsafe_allow_html=True)
                    with c4:
                        if st.button(f"🗑️ ลบรายการ", key=f"mid_del_{idx}_{row['ID']}"):
                            if row['สลิปเข้า'] and os.path.exists(row['สลิปเข้า']): os.remove(row['สลิปเข้า'])
                            if row['สลิปออก'] and os.path.exists(row['สลิปออก']): os.remove(row['สลิปออก'])
                            db.delete_row(row['ID'])
                            st.rerun()
                    st.divider()
                    im1, im2 = st.columns(2)
                    with im1:
                        if row['สลิปเข้า'] and os.path.exists(row['สลิปเข้า']):
                            st.image(row['สลิปเข้า'], caption="สลิปโอนเข้า", width=200)
                        else: st.write("❌ ไม่มีสลิปโอนเข้า")
                    with im2:
                        if row['สลิปออก'] and os.path.exists(row['สลิปออก']):
                            st.image(row['สลิปออก'], caption="สลิปโอนออก", width=200)
                        else: st.write("❌ ไม่มีสลิปโอนออก")

        with tab_ball:
            df_ball = history_df[history_df['ประเภท'] == "เช่าจอดูบอล"]
            if df_ball.empty: st.info("ไม่มีรายการเช่าจอดูบอล")
            for idx, (index, row) in enumerate(df_ball.iterrows()):
                status_class = "status-paid" if row['สถานะโอนออก'] == "โอนแล้ว" else "status-pending"
                status_text = f'<span class="{status_class}">{row["สถานะโอนออก"]}</span>'
                with st.expander(f"จอเช่าที่ {row['ID']} - {row['วันที่']}"):
                    c1, c2, c3, c4 = st.columns([1,1,1,1])
                    c1.write(f"**ประเภท:** {row['ประเภท']}")
                    c2.write(f"**กำไร:** {row['กำไร']:,.2f} ฿")
                    c3.markdown(f"**สถานะ:** {status_text}", unsafe_allow_html=True)
                    with c4:
                        if st.button(f"🗑️ ลบรายการ", key=f"ball_del_{idx}_{row['ID']}"):
                            if row['สลิปเข้า'] and os.path.exists(row['สลิปเข้า']): os.remove(row['สลิปเข้า'])
                            if row['สลิปออก'] and os.path.exists(row['สลิปออก']): os.remove(row['สลิปออก'])
                            db.delete_row(row['ID'])
                            st.rerun()
                    st.divider()
                    im1, im2 = st.columns(2)
                    with im1:
                        if row['สลิปเข้า'] and os.path.exists(row['สลิปเข้า']):
                            st.image(row['สลิปเข้า'], caption="สลิปโอนเข้า", width=200)
                        else: st.write("❌ ไม่มีสลิปโอนเข้า")
                    with im2:
                        if row['สลิปออก'] and os.path.exists(row['สลิปออก']):
                            st.image(row['สลิปออก'], caption="สลิปโอนออก", width=200)
                        else: st.write("❌ ไม่มีสลิปโอนออก")

with tab3:
    st.header("📊 รายงานรายรับ-กำไร")
    df = db.load_data()
    if not df.empty:
        df['วันที่'] = pd.to_datetime(df['วันที่'])
        today, this_month = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m")
        df_today = df[df['วันที่'].dt.strftime("%Y-%m-%d") == today]
        df_month = df[df['วันที่'].dt.strftime("%Y-%m") == this_month]
        st.markdown("### 📅 ภาพรวม")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💵 กำไรวันนี้", f"{df_today['กำไร'].sum():,.2f} ฿")
        c2.metric("📆 กำไรเดือนนี้", f"{df_month['กำไร'].sum():,.2f} ฿")
        c3.metric("💰 ยอดโอนเข้าสะสม", f"{df['ยอดเข้า'].sum():,.2f} ฿")
        c4.metric("📈 กำไรสะสมทั้งหมด", f"{df['กำไร'].sum():,.2f} ฿")
        st.divider()
        st.markdown("### 🧾 แยกตามประเภทบริการ")
        df_mid_total = df[df['ประเภท'] == "รับกลางไอดี"]
        df_ball_total = df[df['ประเภท'] == "เช่าจอดูบอล"]
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""<div class="data-container"><h4 style="margin-top:0;">💎 รับกลางไอดี</h4><p>จำนวนคิว: <b>{len(df_mid_total)}</b> คิว</p><p>ยอดเข้ารวม: <b>{df_mid_total['ยอดเข้า'].sum():,.2f} ฿</b></p><p>ยอดโอนออกรวม: <b>{df_mid_total['ยอดออก'].sum():,.2f} ฿</b></p><p style="color:#1E88E5; font-weight:bold; font-size:1.2rem;">กำไรรวม: {df_mid_total['กำไร'].sum():,.2f} ฿</p></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="data-container"><h4 style="margin-top:0;">⚽ เช่าจอดูบอล</h4><p>จำนวนจอเช่า: <b>{len(df_ball_total)}</b> จอ</p><p>ยอดเข้ารวม: <b>{df_ball_total['ยอดเข้า'].sum():,.2f} ฿</b></p><p style="color:#1E88E5; font-weight:bold; font-size:1.2rem;">กำไรรวม: {df_ball_total['กำไร'].sum():,.2f} ฿</p></div>""", unsafe_allow_html=True)
        st.divider()
        st.markdown("### 📆 สรุปกำไรรายวัน (เดือนนี้)")
        df_month_days = df[df['วันที่'].dt.strftime("%Y-%m") == this_month].copy()
        if not df_month_days.empty:
            daily = df_month_days.groupby(df_month_days['วันที่'].dt.strftime("%Y-%m-%d")).agg(จำนวนรายการ=('ID', 'count'), ยอดเข้า=('ยอดเข้า', 'sum'), ยอดออก=('ยอดออก', 'sum'), กำไร=('กำไร', 'sum')).reset_index().rename(columns={'วันที่': 'วัน'})
            daily = daily.sort_values(by='วัน', ascending=False)
            st.dataframe(daily, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีรายการในเดือนนี้")
        st.divider()
        st.markdown("### 🔴 คิวค้างโอนเงิน")
        pending_all = df[df['สถานะโอนออก'] == "ยังไม่โอน"]
        p1, p2 = st.columns(2)
        p1.metric("⏳ จำนวนคิวค้างโอน", f"{len(pending_all)} คิว")
        p2.metric("💸 ยอดเงินค้างโอน", f"{pending_all['ยอดออก'].sum():,.2f} ฿")
    else:
        st.write("ไม่มีข้อมูล")