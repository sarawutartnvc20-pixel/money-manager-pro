import json
import logging
import threading

import gspread
import pandas as pd
import streamlit as st

logging.getLogger("gspread").setLevel(logging.ERROR)

# ลำดับคอลัมน์ที่ต้องการ (อิงตามตำแหน่ง 0, 1, 2...)
COL_MAP = {
    "ID": 0,
    "วันที่": 1,
    "ประเภท": 2,
    "รายละเอียด": 3,
    "ยอดเข้า": 4,
    "ยอดออก": 5,
    "กำไร": 6,
    "สถานะโอนออก": 7,
    "สลิปเข้า": 8,
    "สลิปออก": 9
}

_lock = threading.Lock()
_cached_client = None
_cached_spreadsheet = None
_cached_sheet = None

def _get_secrets():
    try:
        return st.secrets["gspreads_connection"]
    except Exception:
        return None

def get_gsheet():
    global _cached_client, _cached_spreadsheet, _cached_sheet

    if _cached_sheet is not None:
        return _cached_sheet

    info = _get_secrets()
    if not info:
        st.error("❌ ไม่พบการตั้งค่า gspreads_connection ใน secrets")
        st.stop()

    try:
        _cached_client = gspread.service_account_from_dict(info)
        spreadsheet_url = info.get("spreadsheet_url", "")
        _cached_spreadsheet = _cached_client.open_by_url(spreadsheet_url)
        
        # พยายามหาแท็บ Transactions ถ้าไม่เจอให้ใช้แท็บแรกสุด (Index 0)
        try:
            _cached_sheet = _cached_spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            _cached_sheet = _cached_spreadsheet.get_worksheet(0)

        return _cached_sheet
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google Sheets ล้มเหลว: {e}")
        st.stop()

def load_data() -> pd.DataFrame:
    """
    โหลดข้อมูลแบบยืดหยุ่นสูงสุด โดยอิงตามตำแหน่งคอลัมน์ แทนชื่อหัวตาราง
    """
    with _lock:
        sh = get_gsheet()
        try:
            # อ่านข้อมูลทั้งหมดเป็น List ของ List (รวมหัวตาราง)
            all_values = sh.get_all_values()
            if not all_values or len(all_values) < 2:
                # ถ้าไม่มีข้อมูลเลย หรือมีแต่หัวตาราง ให้คืน DF เปล่าที่มีคอลัมน์ถูกต้อง
                return pd.DataFrame(columns=list(COL_MAP.keys()))

            # แยกหัวตารางออก และเอาข้อมูลมาสร้าง DataFrame
            data = all_values[1:] # เริ่มที่แถว 2
            df_raw = pd.DataFrame(data)
            
            # สร้าง DataFrame ใหม่โดยดึงข้อมูลตามตำแหน่งคอลัมน์ที่ระบุไว้ใน COL_MAP
            final_data = {}
            for col_name, idx in COL_MAP.items():
                if idx < len(df_raw.columns):
                    final_data[col_name] = df_raw.iloc[:, idx].values
                else:
                    final_data[col_name] = [""] * len(df_raw)
            
            df_final = pd.DataFrame(final_data)

            # แปลงประเภทข้อมูลให้ถูกต้อง
            for col in ["ยอดเข้า", "ยอดออก", "กำไร"]:
                df_final[col] = pd.to_numeric(df_final[col], errors="coerce").fillna(0.0)
            
            df_final["ID"] = pd.to_numeric(df_final["ID"], errors="coerce").fillna(0).astype(int)
            
            return df_final
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดขณะโหลดข้อมูล: {e}")
            return pd.DataFrame(columns=list(COL_MAP.keys()))

def append_row(row_dict: dict):
    with _lock:
        sh = get_gsheet()
        # ส่งข้อมูลตามลำดับคอลัมน์เป๊ะๆ
        values = [row_dict.get(col, "") for col in COL_MAP.keys()]
        sh.append_row(values, value_input_option="USER_ENTERED")

def update_cell(row_id: int, column_name: str, value):
    with _lock:
        sh = get_gsheet()
        df = load_data()
        try:
            # หา index ของแถวที่มี ID ตรงกัน (บวก 2 เพราะ index เริ่มที่ 0 และมีหัวตาราง)
            row_index = df.index[df["ID"] == row_id].tolist()[0] + 2
        except IndexError:
            return False
        
        col_index = COL_MAP.get(column_name)
        if col_index is None: return False
        
        sh.update_cell(row_index, col_index + 1, value)
        return True

def delete_row(row_id: int):
    with _lock:
        sh = get_gsheet()
        df = load_data()
        try:
            row_index = df.index[df["ID"] == row_id].tolist()[0] + 2
        except IndexError:
            return False
        sh.delete_rows(row_index)
        return True

def get_next_id(df: pd.DataFrame) -> int:
    if df.empty or df["ID"].max() <= 0:
        return 1
    return int(df["ID"].max()) + 1
