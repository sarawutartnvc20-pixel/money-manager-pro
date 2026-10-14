"""
logic.py — ตรรกะคำนวณล้วน ๆ (ไม่พึ่ง Streamlit) เพื่อให้ทดสอบได้ง่าย
- เรทค่ากลางแบบขั้นบันได + โหมด "ยอดรวมค่ากลางแล้ว / ยังไม่รวม"
- คำนวณยอดออก/กำไร จากสลิปจริง
- แปลงวันที่จาก Google Sheets ให้ถูกต้อง + สรุปรายวัน/รายเดือน
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import pandas as pd

# ------------------------------------------------------------
# ค่าคงที่
# ------------------------------------------------------------
TZ = ZoneInfo("Asia/Bangkok")

YOK_FEE = 40.0               # ค่าโยกเฟส/โยกเมล FC Mobile (ไม่รวมค่ากลาง)
NO_NOTE_FEE = 5.0            # ลืมเขียนโน๊ต
INF = float("inf")


@dataclass(frozen=True)
class Game:
    """เรทค่ากลางและค่าบริการเสริมของแต่ละเกม — เพิ่มเกมใหม่แค่เพิ่มในดิก GAMES ด้านล่าง"""
    name: str
    icon: str
    color: str
    tiers: tuple                 # ((ยอดไอดีสูงสุดของขั้น, ค่ากลาง), ...)  ขั้นสุดท้ายใส่ INF ได้
    percent: float | None = None  # ถ้ายอดเกินขั้นสุดท้ายให้คิดเป็น % (ใช้เมื่อขั้นสุดท้ายไม่ใช่ INF)
    extras: tuple = ()           # ((key, ป้ายชื่อ, จำนวนเงิน), ...) ติ๊กเพิ่มได้ ไม่รวมค่ากลาง (รับกลางไอดี)
    exchange_rates: tuple = ()   # เรทค่าแลกไอดี เช่น (60, 200)
    exchange_extras: tuple = ()  # ค่าบริการเสริมของการแลกไอดี


GAMES: dict[str, Game] = {
    "FC Mobile": Game(
        "FC Mobile", "⚽", "#2a78d6",
        tiers=((1490, 60), (2490, 80), (3990, 100), (5990, 120), (7990, 140), (9999, 160)),
        percent=0.02,   # 10,000 ขึ้นไป คิด 2%
        extras=(("yok", "🔄 โยกเฟส/โยกเมล", YOK_FEE), ("nonote", "✍️ ลืมเขียนโน๊ต", NO_NOTE_FEE)),
        exchange_rates=(60, 200),
        exchange_extras=(("yok", "🔄 โยกเฟส/โยกเมล", YOK_FEE), ("nonote", "✍️ ลืมเขียนโน๊ต", NO_NOTE_FEE)),
    ),
    "eFootball": Game(
        "eFootball", "🎮", "#e8590c",
        tiers=((600, 20), (1200, 30), (1999, 40), (INF, 50)),
        extras=(("wallet", "👛 โอนวอเลท", 10.0), ("nonote", "✍️ ลืมเขียนโน๊ต", NO_NOTE_FEE)),
        exchange_rates=(50,),
        exchange_extras=(("nonote", "✍️ ลืมเขียนโน๊ต", NO_NOTE_FEE),),
    ),
}
DEFAULT_GAME = "FC Mobile"      # รายการเก่าที่ยังไม่มีชื่อเกมในชีท นับเป็นเกมนี้
FEE_TIERS = GAMES[DEFAULT_GAME].tiers
PERCENT_RATE = GAMES[DEFAULT_GAME].percent

SERVICES = ["รับกลางไอดี", "การแลกไอดี", "เช่าจอดูบอล"]

TH_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
             "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
TH_MONTHS_FULL = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                  "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
TH_WEEKDAYS = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]


def now_th() -> datetime:
    """เวลาปัจจุบันตามเวลาไทย (ไม่ติด tzinfo) — เซิร์ฟเวอร์ Streamlit Cloud ใช้ UTC"""
    return datetime.now(TZ).replace(tzinfo=None)


def today_th() -> date:
    return now_th().date()


# ------------------------------------------------------------
# ค่ากลาง
# ------------------------------------------------------------
def tier_fee(price: float, game: str = DEFAULT_GAME) -> float:
    """ค่ากลางตามตารางเรทของเกม โดยเทียบจาก 'ยอดไอดี' (price)"""
    g = GAMES[game]
    for limit, fee in g.tiers:
        if price <= limit:
            return float(fee)
    if g.percent:
        return round(price * g.percent, 2)
    return float(g.tiers[-1][1])


@dataclass
class FeeResult:
    base_fee: float            # ค่ากลางที่คิด
    price: float               # ยอดที่ใช้เทียบเรท (ยอดไอดี)
    ambiguous: bool = False    # ยอดตกช่วงคาบเกี่ยวระหว่าง 2 เรท
    alt_fee: float | None = None
    warning: str = ""


def calc_middleman_fee(amount: float, extras: float = 0.0, includes_fee: bool = False,
                       game: str = DEFAULT_GAME) -> FeeResult:
    """
    includes_fee=False  (ยอดยังไม่รวมค่ากลาง)  -> เทียบเรทจากยอดที่โอนมาตรง ๆ
                         เช่น FC Mobile โอน 1491 -> เรท 80
    includes_fee=True   (ยอดรวมค่ากลางแล้ว)   -> หักค่ากลาง (และค่าบริการเสริม) ออกก่อนแล้วค่อยเทียบเรท
                         เช่น FC Mobile โอน 1500 -> 1500-60 = 1440 ยังไม่เกิน 1490 -> เรท 60
    """
    g = GAMES[game]
    amount = float(amount or 0)
    if not includes_fee:
        return FeeResult(tier_fee(amount, game), amount)

    net = amount - float(extras or 0)
    lowest = float(g.tiers[0][1])
    if net <= lowest:
        return FeeResult(lowest, max(net - lowest, 0.0),
                         warning="ยอดโอนน้อยกว่าค่ากลางขั้นต่ำ ตรวจสอบยอดอีกครั้ง")

    # 1) หาเรทที่ "ลงตัว" : ค่ากลาง f ที่ทำให้ tier(net - f) == f
    for _, fee in g.tiers:
        if tier_fee(net - fee, game) == fee:
            return FeeResult(float(fee), net - fee)
    if g.percent:
        price = net / (1 + g.percent)
        if price > g.tiers[-1][0]:
            fee = round(net - price, 2)
            return FeeResult(fee, round(price, 2))

    # 2) ยอดตกช่วงคาบเกี่ยว (เช่น FC Mobile 1,551–1,569) : ใช้เรทที่สูงกว่าเพื่อไม่ให้ร้านคิดขาด
    #    และแจ้งเตือนให้เช็กกับลูกค้า
    prev = None
    for _, fee in g.tiers:
        if tier_fee(net - fee, game) <= fee:
            return FeeResult(float(fee), net - fee, ambiguous=True, alt_fee=prev,
                             warning="ยอดอยู่ช่วงคาบเกี่ยวระหว่าง 2 เรท ระบบเลือกเรทที่สูงกว่า")
        prev = float(fee)
    fee = round(net * g.percent / (1 + g.percent), 2) if g.percent else float(g.tiers[-1][1])
    return FeeResult(fee, round(net - fee, 2), ambiguous=True, alt_fee=prev,
                     warning="ยอดอยู่ช่วงคาบเกี่ยวระหว่างเรท ตรวจสอบกับลูกค้า")


@dataclass
class Calc:
    income: float
    expense: float
    profit: float
    base_fee: float = 0.0
    extra_fee: float = 0.0
    expected_profit: float = 0.0
    expected_expense: float = 0.0
    from_slip: bool = False       # ยอดออกมาจากสลิป/กรอกจริง
    diff: float | None = None     # กำไรจริง - กำไรที่ควรได้
    fee: FeeResult | None = None
    other_mode_profit: float | None = None   # กำไรถ้าคิดอีกโหมด (ไว้ช่วยแนะนำ)
    notes: list[str] = field(default_factory=list)


def extras_of(is_yok: bool, is_no_note: bool) -> float:
    return (YOK_FEE if is_yok else 0.0) + (NO_NOTE_FEE if is_no_note else 0.0)


def compute_middleman(income: float, extras: float, includes_fee: bool,
                      actual_out: float | None = None, game: str = DEFAULT_GAME) -> Calc:
    """extras = ผลรวมค่าบริการเสริมที่ติ๊กไว้ (โยก/โน๊ต/วอเลท ฯลฯ)"""
    fr = calc_middleman_fee(income, extras, includes_fee, game)
    expected_profit = fr.base_fee + extras
    expected_expense = max(0.0, income - expected_profit)

    other = calc_middleman_fee(income, extras, not includes_fee, game)
    other_profit = other.base_fee + extras

    c = Calc(income=income, expense=expected_expense, profit=expected_profit,
             base_fee=fr.base_fee, extra_fee=extras,
             expected_profit=expected_profit, expected_expense=expected_expense,
             fee=fr, other_mode_profit=other_profit)
    if actual_out is not None and actual_out > 0:
        c.from_slip = True
        c.expense = float(actual_out)
        c.profit = round(income - actual_out, 2)
        c.diff = round(c.profit - expected_profit, 2)
    return c


def compute_exchange(rate: float, extras: float, actual_out: float | None = None) -> Calc:
    """การแลกไอดี: รายรับ = เรทค่าแลก + ค่าบริการเสริม"""
    income = float(rate) + float(extras or 0)
    out = float(actual_out or 0)
    return Calc(income=income, expense=out, profit=round(income - out, 2),
                base_fee=float(rate), extra_fee=float(extras or 0),
                expected_profit=income, expected_expense=0.0, from_slip=out > 0)


def compute_rental(income: float) -> Calc:
    return Calc(income=income, expense=0.0, profit=income, expected_profit=income)


# ------------------------------------------------------------
# วันที่
# ------------------------------------------------------------
_DMY = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})(?:[ ,T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")
_YMD = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")


def _fix_be(y: int) -> int:
    return y - 543 if y > 2400 else y


def parse_sheet_datetime(val) -> pd.Timestamp:
    """รองรับ: '2026-10-15 04:55', '15/10/2026 4:55:00', ปี พ.ศ., และเลข serial ของ Google Sheets"""
    if val is None:
        return pd.NaT
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if pd.isna(val):
            return pd.NaT
        if 20000 < float(val) < 80000:
            return pd.Timestamp(datetime(1899, 12, 30) + timedelta(days=float(val))).round("min")
        return pd.NaT
    s = str(val).strip()
    if not s:
        return pd.NaT
    try:
        f = float(s)
        if 20000 < f < 80000:
            return parse_sheet_datetime(f)
    except ValueError:
        pass
    m = _YMD.match(s)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        try:
            return pd.Timestamp(_fix_be(int(y)), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0))
        except ValueError:
            return pd.NaT
    m = _DMY.match(s)
    if m:
        d, mo, y, hh, mm, ss = m.groups()
        try:
            return pd.Timestamp(_fix_be(int(y)), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0))
        except ValueError:
            return pd.NaT
    ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.notna(ts) and ts.year > 2400:
        ts = ts.replace(year=ts.year - 543)
    return ts


def with_dates(df: pd.DataFrame) -> pd.DataFrame:
    """เพิ่มคอลัมน์ dt / day / year / month ให้ DataFrame"""
    out = df.copy()
    out["dt"] = pd.to_datetime(out["วันที่"].map(parse_sheet_datetime), errors="coerce")
    # ทำให้คอลัมน์วันที่เป็นรูปแบบเดียวกันทั้งหมด (เช่น ตอนดาวน์โหลด CSV)
    out["วันที่"] = [
        ts.strftime("%Y-%m-%d %H:%M") if pd.notna(ts) else ("" if raw is None else str(raw))
        for ts, raw in zip(out["dt"], out["วันที่"])
    ]
    if "เกม" not in out.columns:
        out["เกม"] = ""
    # รับกลางไอดี/แลกไอดีที่ยังไม่มีชื่อเกม (รายการเก่า) นับเป็น FC Mobile
    out["เกม"] = [
        (g if g in GAMES else DEFAULT_GAME) if t in GAME_SERVICES else (g if g in GAMES else "")
        for t, g in zip(out["ประเภท"], out["เกม"])
    ]
    out["cat"] = [category_of(t, g) for t, g in zip(out["ประเภท"], out["เกม"])]
    out["day"] = out["dt"].dt.date
    out["year"] = out["dt"].dt.year
    out["month"] = out["dt"].dt.month
    return out


GAME_SERVICES = ("รับกลางไอดี", "การแลกไอดี")     # บริการที่แยกตามเกม
EX_PREFIX = "แลก · "
CATEGORIES = list(GAMES) + [EX_PREFIX + g for g in GAMES] + ["เช่าจอดูบอล"]


def category_of(service: str, game: str) -> str:
    """รหัสหมวดสำหรับจัดกลุ่ม: รับกลาง -> ชื่อเกม, แลกไอดี -> 'แลก · ชื่อเกม', อื่น ๆ -> ชื่อบริการ"""
    if service == "รับกลางไอดี":
        return game
    if service == "การแลกไอดี":
        return EX_PREFIX + game
    return service


def category_label(cat: str) -> str:
    if cat in GAMES:
        return f"💎 รับกลาง · {cat}"
    if cat.startswith(EX_PREFIX):
        return f"🔄 แลกไอดี · {cat[len(EX_PREFIX):]}"
    return {"เช่าจอดูบอล": "⚽ เช่าจอดูบอล"}.get(cat, f"• {cat}" if cat else "• อื่น ๆ")


EX_COLORS = {"FC Mobile": "#6250d6", "eFootball": "#c2255c"}


def category_color(cat: str) -> str:
    if cat in GAMES:
        return GAMES[cat].color
    if cat.startswith(EX_PREFIX):
        return EX_COLORS.get(cat[len(EX_PREFIX):], "#6250d6")
    return {"เช่าจอดูบอล": "#1baf7a"}.get(cat, "#94a3b8")


def th_date(d: date, weekday: bool = True, full_month: bool = False) -> str:
    m = (TH_MONTHS_FULL if full_month else TH_MONTHS)[d.month - 1]
    s = f"{d.day} {m} {d.year + 543}"
    return f"{TH_WEEKDAYS[d.weekday()]} {s}" if weekday else s


def th_month(year: int, month: int, full: bool = True) -> str:
    return f"{(TH_MONTHS_FULL if full else TH_MONTHS)[month - 1]} {year + 543}"


# ------------------------------------------------------------
# สรุปยอด
# ------------------------------------------------------------
def totals(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"count": 0, "in": 0.0, "out": 0.0, "profit": 0.0}
    return {
        "count": int(len(df)),
        "in": float(df["ยอดเข้า"].sum()),
        "out": float(df["ยอดออก"].sum()),
        "profit": float(df["กำไร"].sum()),
    }


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """สรุปรายวัน (ต้องผ่าน with_dates มาก่อน) เรียงวันล่าสุดก่อน"""
    d = df.dropna(subset=["dt"])
    if d.empty:
        return pd.DataFrame(columns=["day", "count", "in", "out", "profit"])
    g = d.groupby("day").agg(count=("ID", "size"), **{
        "in": ("ยอดเข้า", "sum"), "out": ("ยอดออก", "sum"), "profit": ("กำไร", "sum")})
    return g.reset_index().sort_values("day", ascending=False).reset_index(drop=True)


def monthly_summary(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """สรุป 12 เดือนของปีที่เลือก (เดือนที่ไม่มีรายการ = 0)"""
    d = df.dropna(subset=["dt"])
    d = d[d["year"] == year]
    base = pd.DataFrame({"month": range(1, 13)})
    if d.empty:
        g = pd.DataFrame(columns=["month", "count", "in", "out", "profit"])
    else:
        g = d.groupby("month").agg(count=("ID", "size"), **{
            "in": ("ยอดเข้า", "sum"), "out": ("ยอดออก", "sum"), "profit": ("กำไร", "sum")}).reset_index()
    m = base.merge(g, on="month", how="left").fillna(0)
    m["count"] = m["count"].astype(int)
    for c in ("in", "out", "profit"):
        m[c] = m[c].astype(float)
    m["label"] = m["month"].map(lambda x: TH_MONTHS[x - 1])
    return m
