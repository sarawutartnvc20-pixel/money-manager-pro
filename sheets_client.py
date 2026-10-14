import logging
import threading
import gspread
import pandas as pd
import streamlit as st

logging.getLogger("gspread").setLevel(logging.ERROR)

# ลำดับคอลัมน์มาตรฐาน 11 คอลัมน์ (คงเดิม เพื่อไม่ให้สูตรภาษีใน Google Sheets พัง)
COL_MAP = {
    "ID": 0, "วันที่": 1, "ประเภท": 2, "รายละเอียด": 3,
    "ยอดเข้า": 4, "ยอดออก": 5, "กำไร": 6,
    "สถานะโอนออก": 7, "สลิปเข้า": 8, "สลิปเข้า 2": 9, "สลิปออก": 10
}
TEXT_COLS = ["วันที่", "ประเภท", "รายละเอียด", "สถานะโอนออก", "สลิปเข้า", "สลิปเข้า 2", "สลิปออก"]
MONTHLY_SHEET = "สรุปรายเดือน"

# ใช้ RLock (Reentrant Lock) เพื่อป้องกันปัญหา Deadlock เมื่อมีการเรียกฟังก์ชันซ้อนกัน
_lock = threading.RLock()


@st.cache_resource(show_spinner=False)
def _open_spreadsheet():
    """เชื่อมต่อครั้งเดียวแล้วใช้ซ้ำ (เร็วกว่าการ login ใหม่ทุกครั้ง)"""
    conn = st.secrets["gspreads_connection"]
    client = gspread.service_account_from_dict(dict(conn))
    return client.open_by_url(conn["spreadsheet_url"])


def get_gsheet():
    try:
        spreadsheet = _open_spreadsheet()
        try:
            return spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            return spreadsheet.get_worksheet(0)
    except Exception as e:
        _open_spreadsheet.clear()
        st.error(f"❌ Connection Error: {e}")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_values() -> list:
    """ดึงค่าดิบทั้งชีท (cache 60 วินาที และล้างทุกครั้งที่มีการเขียนข้อมูล)
    ใช้ UNFORMATTED_VALUE เพื่อให้ได้ตัวเลขจริง ไม่โดน format เช่น '1,500.00' หรือวันที่แบบ พ.ศ."""
    sh = get_gsheet()
    if sh is None:
        raise RuntimeError("ไม่สามารถเชื่อมต่อ Google Sheets ได้")
    return sh.get_all_values(value_render_option="UNFORMATTED_VALUE")


def clear_cache():
    try:
        _fetch_values.clear()
    except Exception:
        pass


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(COL_MAP.keys()))


def load_data(fresh: bool = False) -> pd.DataFrame:
    with _lock:
        try:
            if fresh:
                clear_cache()
            all_values = _fetch_values()
        except Exception as e:
            st.error(f"❌ Load Error: {e}")
            return _empty_df()

        try:
            if not all_values or len(all_values) < 2:
                return _empty_df()

            data = [r for r in all_values[1:] if any(str(c).strip() for c in r)]
            if not data:
                return _empty_df()
            df_raw = pd.DataFrame(data)

            final_data = {}
            for col_name, idx in COL_MAP.items():
                if idx < len(df_raw.columns):
                    final_data[col_name] = df_raw.iloc[:, idx].values
                else:
                    final_data[col_name] = [""] * len(df_raw)

            df_final = pd.DataFrame(final_data)
            for col in ["ยอดเข้า", "ยอดออก", "กำไร"]:
                cleaned = df_final[col].map(lambda v: str(v).replace(",", "").replace("฿", "").strip()
                                            if isinstance(v, str) else v)
                df_final[col] = pd.to_numeric(cleaned, errors="coerce").fillna(0.0).astype(float)
            df_final["ID"] = pd.to_numeric(df_final["ID"], errors="coerce").fillna(0).astype(int)

            # คอลัมน์วันที่เก็บค่าดิบไว้ (อาจเป็นเลข serial) -> logic.parse_sheet_datetime จะแปลงให้
            for col in TEXT_COLS:
                if col == "วันที่":
                    df_final[col] = df_final[col].map(lambda v: "" if v is None else v)
                else:
                    df_final[col] = df_final[col].map(lambda v: "" if v is None else str(v))

            return df_final
        except Exception as e:
            st.error(f"❌ Load Error: {e}")
            return _empty_df()


def append_row(row_dict: dict) -> bool:
    with _lock:
        sh = get_gsheet()
        if sh is None:
            return False
        try:
            values = []
            for col in COL_MAP.keys():
                val = row_dict.get(col, "")
                if val is None or (not isinstance(val, str) and pd.isna(val)):
                    val = ""
                values.append(val)

            # คำนวณแถวถัดไปที่แน่นอนโดยนับจากคอลัมน์ A (ID)
            # เพื่อป้องกันปัญหา append_row ตรวจจับ tableRange คลาดเคลื่อนแล้วเขียนทับแถวเดิม
            col_a = sh.col_values(1)
            next_row = len(col_a) + 1

            range_name = f"A{next_row}:K{next_row}"
            sh.update(range_name=range_name, values=[values], value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ Append Error: {e}")
            return False
        finally:
            clear_cache()


def _find_row(sh, row_id: int):
    all_ids = sh.col_values(1)
    target_str = str(row_id)
    for i, val in enumerate(all_ids[1:], start=2):
        v = str(val).strip()
        if v == target_str or v == f"{target_str}.0":
            return i
    return None


def update_cell(row_id: int, column_name: str, value) -> bool:
    with _lock:
        sh = get_gsheet()
        if sh is None:
            return False
        col_index = COL_MAP.get(column_name)
        if col_index is None:
            return False
        try:
            i = _find_row(sh, row_id)
            if i is None:
                return False
            sh.update_cell(i, col_index + 1, "" if value is None else value)
            return True
        except Exception as e:
            st.error(f"❌ Update Error: {e}")
            return False
        finally:
            clear_cache()


def delete_row(row_id: int) -> bool:
    """ลบแถวออกจาก Google Sheet"""
    with _lock:
        sh = get_gsheet()
        if sh is None:
            return False
        try:
            i = _find_row(sh, row_id)
            if i is None:
                return False
            sh.delete_rows(i)
            return True
        except Exception as e:
            st.error(f"❌ Delete Error: {e}")
            return False
        finally:
            clear_cache()


def get_next_id(df: pd.DataFrame) -> int:
    if df.empty or "ID" not in df.columns or df["ID"].max() <= 0:
        return 1
    return int(df["ID"].max()) + 1


def write_monthly_summary(rows: list) -> bool:
    """เขียน/อัปเดตแท็บ 'สรุปรายเดือน' ใน Google Sheets (ใช้ยื่นภาษีได้ง่าย)
    rows = [[header...], [row...], ...]  — เขียนทับทั้งแท็บ"""
    with _lock:
        try:
            spreadsheet = _open_spreadsheet()
            try:
                ws = spreadsheet.worksheet(MONTHLY_SHEET)
            except gspread.WorksheetNotFound:
                ws = spreadsheet.add_worksheet(title=MONTHLY_SHEET, rows=200, cols=10)
            ws.clear()
            ws.update(range_name="A1", values=rows, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ เขียนสรุปรายเดือนไม่สำเร็จ: {e}")
            return False
