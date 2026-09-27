# ============================================================
# sheets_client.py — ตัวเชื่อมต่อกับ Google Sheets (Service Account)
# ใช้ gspread + google-auth ในการเข้าถึง Google Sheets API
# ============================================================
import json
import logging
import threading

import gspread
import pandas as pd
import streamlit as st

# gspread มักยิง warning ที่ไม่จำเป็นออกมาในเทอร์มินัล (เช่น token refresh)
logging.getLogger("gspread").setLevel(logging.ERROR)

# ชื่อคอลัมน์หลักของฐานข้อมูล (ต้องตรงกับแถวที่ 1 ใน Google Sheets)
COLUMNS = ["ID", "วันที่", "ประเภท", "รายละเอียด", "ยอดเข้า", "ยอดออก", "กำไร", "สถานะโอนออก", "สลิปเข้า", "สลิปออก"]

# ชื่อคอลัมน์ที่เป็นข้อความและควรอ่านมาเป็น string ทั้งหมด (กันปัญหาค่าว่างเป็น NaN)
STRING_COLS = ["path_in", "path_out", "สลิปเข้า", "สลิปออก"]

# ตัว Lock สำหรับกันการเขียนข้อมูลชนกัน (เมื่อหลายแท็บ/หลายคนใช้พร้อมกัน)
_lock = threading.Lock()

# แคชระดับโมดูล (ไม่ผูกกับ session) เพื่อลดการยิง API ตลอดเวลา
_cached_client = None
_cached_spreadsheet = None
_cached_sheet = None
_cached_sheet_key = None


def _get_secrets():
    """ดึงค่าการเชื่อมต่อจาก st.secrets (local: .streamlit/secrets.toml)"""
    try:
        return st.secrets["gspreads_connection"]
    except Exception:
        # ผู้ใช้ยังไม่ได้ตั้งค่า secrets
        return None


def _get_service_account_info():
    """
    รวบรวมข้อมูล Service Account จาก st.secrets
    รองรับ 2 รูปแบบ:
      1) ทั้งไฟล์ JSON ย่อ (แนะนำ): st.secrets["gspreads_connection"] = { "type": "service_account", ... }
      2) แค่ private_key เป็น string
    """
    conn = _get_secrets()
    if not conn:
        return None
    return dict(conn)


def get_gsheet():
    """
    เชื่อมต่อ Google Sheets ด้วย Service Account แล้วคืน object worksheet ที่ใช้งาน
    การเชื่อมต่อถูกแคชไว้เพื่อไม่ต้องเชื่อมต่อใหม่ทุกครั้งที่ rerun
    """
    global _cached_client, _cached_spreadsheet, _cached_sheet, _cached_sheet_key

    if _cached_sheet is not None:
        return _cached_sheet

    info = _get_service_account_info()
    if not info:
        st.error(
            "❌ ยังไม่พบการตั้งค่าเชื่อมต่อ Google Sheets\n\n"
            "กรุณาเพิ่มข้อมูล Service Account ในไฟล์ `.streamlit/secrets.toml` "
            "ดูวิธีทำได้ที่ `README_GOOGLE_SHEETS.md` ในโปรเจกต์"
        )
        st.stop()

    try:
        # สร้าง client จากข้อมูล Service Account
        _cached_client = gspread.service_account_from_dict(info)

        # เปิดไฟล์สเปรดชีตจาก URL (นำมาจาก secrets)
        spreadsheet_url = info.get("spreadsheet_url", "")
        if not spreadsheet_url:
            st.error("❌ ไม่พบ `spreadsheet_url` ใน `st.secrets` — กรุณาเพิ่ม URL ของ Google Sheets")
            st.stop()

        _cached_spreadsheet = _cached_client.open_by_url(spreadsheet_url)

        # เลือก worksheet ที่ต้องการใช้ (ชื่อ "Transactions")
        _cached_sheet_key = _cached_spreadsheet.title
        try:
            _cached_sheet = _cached_spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            # ถ้ายังไม่มี worksheet ชื่อ "Transactions" ให้สร้างใหม่พร้อมหัวตาราง
            _cached_sheet = _cached_spreadsheet.add_worksheet(
                title="Transactions", rows=1000, cols=len(COLUMNS)
            )
            _cached_sheet.append_row(COLUMNS)

        return _cached_sheet
    except Exception as e:
        # แก้ไข: ให้แสดง Error แบบละเอียดเพื่อการ Debug
        st.error(f"❌ เชื่อมต่อ Google Sheets ไม่สำเร็จ: {str(e)}")
        st.stop()


def load_data() -> pd.DataFrame:
    """
    โหลดข้อมูลทั้งหมดจาก Google Sheets มาเป็น pandas DataFrame
    - รองรับคอลัมน์เก่า (path_in/path_out) และคอลัมน์ใหม่ (สลิปเข้า/สลิปออก)
    - ถ้าไม่มีข้อมูลเลย จะคืน DataFrame เปล่าที่มีโครงสร้างถูกต้อง
    """
    with _lock:
        sh = get_gsheet()
        try:
            records = sh.get_all_records(expected_headers=COLUMNS)
        except gspread.exceptions.GSpreadException:
            # หากหัวตารางไม่ตรง ลองอ่านแบบไม่บังคับหัวตาราง
            records = sh.get_all_values()

        # กรณีไม่มีข้อมูล (มีแต่หัวตาราง) หรือหัวตารางไม่ถูกต้อง
        if not records:
            df = pd.DataFrame(columns=COLUMNS)
        else:
            df = pd.DataFrame(records)
            # จัดการคอลัมน์ที่หายไป/เกินมา
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df = df[COLUMNS]

        # เติมค่า NaN → ค่าว่าง, และแปลงเป็น string สำหรับคอลัมน์ path
        for col in ["สลิปเข้า", "สลิปออก"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        # แปลงคอลัมน์ตัวเลขให้เป็นตัวเลขจริง
        for col in ["ยอดเข้า", "ยอดออก", "กำไร"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
        return df


def append_row(row_dict: dict):
    """เพิ่มแถวใหม่ 1 แถวเข้า Google Sheets (ตามลำดับคอลัมน์ COLUMNS)"""
    with _lock:
        sh = get_gsheet()
        values = [row_dict.get(col, "") for col in COLUMNS]
        sh.append_row(values, value_input_option="USER_ENTERED")


def update_cell(row_id: int, column_name: str, value):
    """
    อัปเดตค่า 1 cell ตาม row ID
    row_id: ID ของรายการ (คอลัมน์แรกของ sheet)
    column_name: ชื่อคอลัมน์ที่ต้องการแก้ (เช่น 'สถานะโอนออก', 'สลิปออก')
    """
    with _lock:
        sh = get_gsheet()
        df = load_data()
        # หาตำแหน่งแถวใน sheet (แถวที่ 1 คือหัวตาราง → +1)
        try:
            row_index = df.index[df["ID"] == row_id].tolist()[0] + 2
        except IndexError:
            return False
        col_index = COLUMNS.index(column_name) + 1
        sh.update_cell(row_index, col_index, value)
        return True


def delete_row(row_id: int):
    """ลบแถวที่มี ID ตรงกันออกจาก Google Sheets"""
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
    """สร้าง ID ตัวถัดไป = ค่า max ของ ID + 1 (กันเลข ID ซ้ำ/กระโดด)"""
    if df.empty or df["ID"].max() <= 0:
        return 1
    return int(df["ID"].max()) + 1