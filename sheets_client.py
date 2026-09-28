import logging
import threading
import gspread
import pandas as pd
import streamlit as st

logging.getLogger("gspread").setLevel(logging.ERROR)

# ลำดับคอลัมน์มาตรฐาน 11 คอลัมน์
COL_MAP = {
    "ID": 0, "วันที่": 1, "ประเภท": 2, "รายละเอียด": 3, 
    "ยอดเข้า": 4, "ยอดออก": 5, "กำไร": 6, 
    "สถานะโอนออก": 7, "สลิปเข้า": 8, "สลิปเข้า 2": 9, "สลิปออก": 10
}

# ใช้ RLock (Reentrant Lock) เพื่อป้องกันปัญหา Deadlock เมื่อมีการเรียกฟังก์ชันซ้อนกัน
_lock = threading.RLock()

def get_gsheet():
    """เชื่อมต่อ Google Sheets แบบสดใหม่ทุกครั้งเพื่อป้องกัน Cache ค้าง"""
    try:
        conn = st.secrets["gspreads_connection"]
        client = gspread.service_account_from_dict(conn)
        spreadsheet = client.open_by_url(conn["spreadsheet_url"])
        try:
            return spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            return spreadsheet.get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

def load_data() -> pd.DataFrame:
    with _lock:
        sh = get_gsheet()
        if sh is None: 
            return pd.DataFrame(columns=list(COL_MAP.keys()))
        
        try:
            all_values = sh.get_all_values()
            if not all_values or len(all_values) < 2:
                return pd.DataFrame(columns=list(COL_MAP.keys()))

            data = all_values[1:]
            df_raw = pd.DataFrame(data)
            
            final_data = {}
            for col_name, idx in COL_MAP.items():
                if idx < len(df_raw.columns):
                    final_data[col_name] = df_raw.iloc[:, idx].values
                else:
                    final_data[col_name] = [""] * len(df_raw)
            
            df_final = pd.DataFrame(final_data)
            for col in ["ยอดเข้า", "ยอดออก", "กำไร"]:
                df_final[col] = pd.to_numeric(df_final[col], errors="coerce").fillna(0.0)
            df_final["ID"] = pd.to_numeric(df_final["ID"], errors="coerce").fillna(0).astype(int)
            
            for col in ["วันที่", "ประเภท", "รายละเอียด", "สถานะโอนออก", "สลิปเข้า", "สลิปเข้า 2", "สลิปออก"]:
                if col in df_final.columns:
                    df_final[col] = df_final[col].fillna("").astype(str)
            
            return df_final
        except Exception as e:
            st.error(f"❌ Load Error: {e}")
            return pd.DataFrame(columns=list(COL_MAP.keys()))

def append_row(row_dict: dict) -> bool:
    with _lock:
        sh = get_gsheet()
        if sh is None: 
            return False
        try:
            values = []
            for col in COL_MAP.keys():
                val = row_dict.get(col, "")
                if val is None or pd.isna(val):
                    val = ""
                values.append(val)
            
            # คำนวณแถวถัดไปที่แน่นอนโดยนับจากคอลัมน์ A (ID)
            # เพื่อป้องกันปัญหา Google Sheets API append_row ตรวจจับ tableRange คลาดเคลื่อนแล้วเขียนทับแถวเดิม
            col_a = sh.col_values(1)
            next_row = len(col_a) + 1
            
            range_name = f"A{next_row}:K{next_row}"
            sh.update(range_name=range_name, values=[values], value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ Append Error: {e}")
            return False

def update_cell(row_id: int, column_name: str, value) -> bool:
    with _lock:
        sh = get_gsheet()
        if sh is None: 
            return False
        col_index = COL_MAP.get(column_name)
        if col_index is None: 
            return False
        try:
            # ค้นหาแถวอย่างรวดเร็วผ่าน Column A (ID)
            all_ids = sh.col_values(1)
            target_str = str(row_id)
            for i, val in enumerate(all_ids[1:], start=2):
                if str(val).strip() == target_str:
                    sh.update_cell(i, col_index + 1, "" if value is None else value)
                    return True
            return False
        except Exception as e:
            st.error(f"❌ Update Error: {e}")
            return False

def update_transfer_status(row_id: int, slip_out_url: str = "") -> bool:
    """อัปเดตสถานะโอนออกและสลิปออกพร้อมกันในคำสั่งเดียวเพื่อความรวดเร็วและแม่นยำ"""
    with _lock:
        sh = get_gsheet()
        if sh is None: 
            return False
        try:
            all_ids = sh.col_values(1)
            target_str = str(row_id)
            for i, val in enumerate(all_ids[1:], start=2):
                if str(val).strip() == target_str:
                    status_col = COL_MAP["สถานะโอนออก"] + 1
                    cells = [
                        gspread.Cell(row=i, col=status_col, value="โอนแล้ว")
                    ]
                    if slip_out_url:
                        slip_col = COL_MAP["สลิปออก"] + 1
                        cells.append(gspread.Cell(row=i, col=slip_col, value=slip_out_url))
                    sh.update_cells(cells)
                    return True
            return False
        except Exception as e:
            st.error(f"❌ Update Error: {e}")
            return False

def delete_row(row_id: int) -> bool:
    """ลบแถวออกจาก Google Sheet อย่างรวดเร็วและปลอดภัย ไม่ติด Deadlock"""
    with _lock:
        sh = get_gsheet()
        if sh is None: 
            return False
        try:
            # ค้นหาเลขแถวโดยตรงจากคอลัมน์ A (ID) ประหยัดเวลาและรวดเร็วกว่าโหลดทั้งตาราง
            all_ids = sh.col_values(1)
            target_str = str(row_id)
            for i, val in enumerate(all_ids[1:], start=2):
                if str(val).strip() == target_str:
                    sh.delete_rows(i)
                    return True
            return False
        except Exception as e:
            st.error(f"❌ Delete Error: {e}")
            return False

def get_next_id(df: pd.DataFrame) -> int:
    if df.empty or "ID" not in df.columns or df["ID"].max() <= 0:
        return 1
    return int(df["ID"].max()) + 1
