import logging
import threading
import gspread
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)
logging.getLogger("gspread").setLevel(logging.ERROR)

# ลำดับคอลัมน์มาตรฐาน 11 คอลัมน์ (คงเดิม เพื่อไม่ให้สูตรภาษีใน Google Sheets พัง)
COL_MAP = {
    "ID": 0, "วันที่": 1, "ประเภท": 2, "รายละเอียด": 3,
    "ยอดเข้า": 4, "ยอดออก": 5, "กำไร": 6,
    "สถานะโอนออก": 7, "สลิปเข้า": 8, "สลิปเข้า 2": 9, "สลิปออก": 10
}
TEXT_COLS = ["วันที่", "ประเภท", "รายละเอียด", "สถานะโอนออก", "สลิปเข้า", "สลิปเข้า 2", "สลิปออก"]
EXPORT_TEXT_COLS = ["ประเภท", "รายละเอียด", "สถานะโอนออก", "สลิปเข้า", "สลิปเข้า 2", "สลิปออก"]
MONTHLY_SHEET = "สรุปรายเดือน"

# ใช้ RLock เพื่อป้องกันการเขียนชนกันภายในแอปเดียวกัน
_lock = threading.RLock()


def safe_text(v):
    """กัน Formula Injection: ข้อความที่ขึ้นต้นด้วย = + - @ จะถูกตีความเป็นสูตรใน Sheets/Excel
    (เช่น =IMPORTXML(...) ส่งข้อมูลออกนอกชีทได้) จึงใส่ ' นำหน้าให้เป็นข้อความธรรมดา"""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def _fail(msg: str, exc: Exception):
    """เก็บรายละเอียดจริงไว้ใน log เซิร์ฟเวอร์ แต่แสดงข้อความทั่วไปให้ผู้ใช้ (ไม่รั่วข้อมูลระบบ)"""
    logger.exception("%s: %s", msg, exc)
    st.error(f"❌ {msg} (ดูรายละเอียดใน Logs ของ Streamlit)")


@st.cache_resource(show_spinner=False)
def _open_spreadsheet():
    """เชื่อมต่อครั้งเดียวแล้วใช้ซ้ำ"""
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
        try:
            _open_spreadsheet.clear()
        except Exception:
            pass
        _fail("เชื่อมต่อ Google Sheets ไม่สำเร็จ", e)
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_values() -> list:
    """ดึงค่าดิบทั้งชีท (cache 60 วินาที และล้างทุกครั้งที่มีการเขียนข้อมูล)
    UNFORMATTED_VALUE -> ได้ตัวเลขจริง ไม่โดน format เช่น '1,500.00' หรือวันที่แบบ พ.ศ."""
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
    return pd.DataFrame(columns=list(COL_MAP.keys()) + ["_row"])


def load_data(fresh: bool = False) -> pd.DataFrame:
    """คอลัมน์ _row = เลขแถวจริงใน Google Sheets ใช้ลบ/แก้ถูกแถวแม้ ID ซ้ำกัน"""
    with _lock:
        try:
            if fresh:
                clear_cache()
            all_values = _fetch_values()
        except Exception as e:
            _fail("โหลดข้อมูลไม่สำเร็จ", e)
            return _empty_df()

        try:
            if not all_values or len(all_values) < 2:
                return _empty_df()

            rows = [(i + 2, r) for i, r in enumerate(all_values[1:])
                    if any(str(c).strip() for c in r)]
            if not rows:
                return _empty_df()
            df_raw = pd.DataFrame([r for _, r in rows])

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

            for col in TEXT_COLS:
                if col == "วันที่":   # เก็บค่าดิบ (อาจเป็นเลข serial) ให้ logic.parse_sheet_datetime แปลง
                    df_final[col] = df_final[col].map(lambda v: "" if v is None else v)
                else:
                    df_final[col] = df_final[col].map(lambda v: "" if v is None else str(v))
            df_final["_row"] = [n for n, _ in rows]
            return df_final
        except Exception as e:
            _fail("อ่านข้อมูลจากชีทไม่สำเร็จ", e)
            return _empty_df()


def append_row(row_dict: dict):
    """เพิ่มแถวใหม่ — กำหนด ID ภายใน lock จากข้อมูลล่าสุดในชีท (กัน ID ซ้ำ)
    คืนค่า ID ใหม่ หรือ None ถ้าล้มเหลว"""
    with _lock:
        sh = get_gsheet()
        if sh is None:
            return None
        try:
            col_a = sh.col_values(1)
            ids = []
            for x in col_a[1:]:
                try:
                    ids.append(int(float(str(x).strip())))
                except ValueError:
                    pass
            new_id = max(ids, default=0) + 1
            row_dict = dict(row_dict, ID=new_id)

            values = []
            for col in COL_MAP.keys():
                val = row_dict.get(col, "")
                if val is None or (not isinstance(val, str) and pd.isna(val)):
                    val = ""
                values.append(safe_text(val))

            # คำนวณแถวถัดไปเองจากคอลัมน์ A (ไม่เชื่อ tableRange ของ append_row ซึ่งเคยเขียนทับแถวเดิม)
            next_row = max(len(col_a) + 1, 2)
            sh.update(range_name=f"A{next_row}:K{next_row}", values=[values],
                      value_input_option="USER_ENTERED")
            return new_id
        except Exception as e:
            _fail("บันทึกลง Google Sheets ไม่สำเร็จ", e)
            return None
        finally:
            clear_cache()


def _find_row(sh, row_id: int, row_num=None):
    """หาเลขแถวของ ID — ถ้าระบุ row_num จะเช็กว่าแถวนั้น ID ตรงจริง (ไม่ตรง = ข้อมูลเปลี่ยนไปแล้ว คืน None)"""
    col_a = sh.col_values(1)
    target = str(int(row_id))

    def same(v):
        v = str(v).strip()
        return v == target or v == f"{target}.0"

    if row_num:
        row_num = int(row_num)
        if 2 <= row_num <= len(col_a) and same(col_a[row_num - 1]):
            return row_num
        return None
    for i, val in enumerate(col_a[1:], start=2):
        if same(val):
            return i
    return None


def update_cell(row_id: int, column_name: str, value, row_num=None) -> bool:
    with _lock:
        sh = get_gsheet()
        col_index = COL_MAP.get(column_name)
        if sh is None or col_index is None:
            return False
        try:
            i = _find_row(sh, row_id, row_num)
            if i is None:
                return False
            sh.update_cell(i, col_index + 1, "" if value is None else safe_text(value))
            return True
        except Exception as e:
            _fail("อัปเดตข้อมูลไม่สำเร็จ", e)
            return False
        finally:
            clear_cache()


def delete_row(row_id: int, row_num=None) -> bool:
    with _lock:
        sh = get_gsheet()
        if sh is None:
            return False
        try:
            i = _find_row(sh, row_id, row_num)
            if i is None:
                return False
            sh.delete_rows(i)
            return True
        except Exception as e:
            _fail("ลบรายการไม่สำเร็จ", e)
            return False
        finally:
            clear_cache()


def write_monthly_summary(rows: list) -> bool:
    """เขียน/อัปเดตแท็บ 'สรุปรายเดือน' (ข้อมูลที่ระบบคำนวณเอง ไม่มีข้อความจากผู้ใช้)"""
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
            _fail("เขียนสรุปรายเดือนไม่สำเร็จ", e)
            return False
