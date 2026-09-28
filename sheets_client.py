import logging
import threading
import gspread
import pandas as pd
import streamlit as st

logging.getLogger("gspread").setLevel(logging.ERROR)

# ลำดับคอลัมน์ที่ต้องการ
COL_MAP = {
    "ID": 0, "วันที่": 1, "ประเภท": 2, "รายละเอียด": 3, 
    "ยอดเข้า": 4, "ยอดออก": 5, "กำไร": 6, 
    "สถานะโอนออก": 7, "สลิปเข้า": 8, "สลิปเข้า 2": 9, "สลิปออก": 10
}

_lock = threading.Lock()

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
        if sh is None: return pd.DataFrame(columns=list(COL_MAP.keys()))
        
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
            
            return df_final
        except Exception as e:
            st.error(f"❌ Load Error: {e}")
            return pd.DataFrame(columns=list(COL_MAP.keys()))

def append_row(row_dict: dict):
    with _lock:
        sh = get_gsheet()
        if sh is None: return False
        values = [row_dict.get(col, "") for col in COL_MAP.keys()]
        sh.append_row(values, value_input_option="USER_ENTERED")
        return True

def update_cell(row_id: int, column_name: str, value):
    with _lock:
        sh = get_gsheet()
        if sh is None: return False
        df = load_data()
        try:
            row_index = df.index[df["ID"] == row_id].tolist()[0] + 2
            col_index = COL_MAP.get(column_name)
            if col_index is None: return False
            sh.update_cell(row_index, col_index + 1, value)
            return True
        except Exception:
            return False

def delete_row(row_id: int):
    with _lock:
        sh = get_gsheet()
        if sh is None: return False
        df = load_data()
        try:
            row_index = df.index[df["ID"] == row_id].tolist()[0] + 2
            sh.delete_rows(row_index)
            return True
        except Exception:
            return False

def get_next_id(df: pd.DataFrame) -> int:
    if df.empty or df["ID"].max() <= 0:
        return 1
    return int(df["ID"].max()) + 1
