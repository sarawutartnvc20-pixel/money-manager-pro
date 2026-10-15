import hmac
import html
import os
import time

import pandas as pd
import streamlit as st

# โมดูลภายในโปรเจกต์
import logic as lg
import sheets_client as db
import image_manager as im

# ============================================================
# 1. Page config & Theme
# ============================================================
st.set_page_config(
    page_title="Money Manager Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;500;600;700&family=Noto+Sans+Thai:wght@400;500;600;700&display=swap');

:root {
  --mm-ink: #0f172a;
  --mm-ink-2: #334155;
  --mm-muted: #64748b;
  --mm-line: #e2e8f0;
  --mm-card: #ffffff;
  --mm-green: #16a34a;
  --mm-green-soft: #ecfdf3;
  --mm-red: #dc2626;
  --mm-red-soft: #fef2f2;
  --mm-amber: #b45309;
  --mm-amber-soft: #fffbeb;
  --mm-blue: #2a78d6;
  --mm-blue-soft: #eff6ff;
}

html, body, .stApp, p, li, label, input, textarea, button,
[data-baseweb="select"], [data-baseweb="tab"], .stMarkdown {
  font-family: 'Noto Sans Thai', 'Kanit', system-ui, sans-serif;
}
h1, h2, h3, h4, .mm-hero h1, .mm-kpi .v, .mm-profit .v, .mm-step b {
  font-family: 'Kanit', 'Noto Sans Thai', sans-serif !important;
}

.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- Hero ---------- */
.mm-hero {
  background: linear-gradient(135deg, #0b3b26 0%, #14532d 55%, #15803d 100%);
  color: #fff; border-radius: 18px; padding: 20px 24px; margin-bottom: 14px;
  display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap;
}
.mm-hero h1 { color: #fff; font-size: 1.6rem; margin: 0; padding: 0; line-height: 1.25; }
.mm-hero .sub { color: #bbf7d0; font-size: .92rem; margin-top: 2px; }
.mm-hero .chips { display: flex; gap: 8px; flex-wrap: wrap; }
.mm-chip {
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22);
  border-radius: 999px; padding: 6px 14px; font-size: .9rem; white-space: nowrap;
}
.mm-chip b { font-family: 'Kanit', sans-serif; font-weight: 600; }

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--mm-line); }
.stTabs [data-baseweb="tab"] { padding: 10px 16px; font-size: 1rem; font-weight: 600; }
.stTabs [data-baseweb="tab"] p { font-size: 1rem; }

/* ---------- Step heading ---------- */
.mm-step { display: flex; align-items: center; gap: 10px; margin: 2px 0 10px; }
.mm-step .n {
  width: 28px; height: 28px; border-radius: 50%; background: var(--mm-green); color: #fff;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: .9rem;
  flex: 0 0 auto;
}
.mm-step b { font-size: 1.08rem; color: var(--mm-ink); font-weight: 600; }
.mm-step span.h { color: var(--mm-muted); font-size: .85rem; }

/* ---------- KPI tiles ---------- */
.mm-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 6px 0 14px; }
.mm-kpi {
  background: var(--mm-card); border: 1px solid var(--mm-line); border-radius: 14px;
  padding: 12px 14px 12px 16px; position: relative; overflow: hidden;
}
.mm-kpi::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--acc, #94a3b8); }
.mm-kpi .l { color: var(--mm-muted); font-size: .84rem; font-weight: 500; }
.mm-kpi .v { color: var(--mm-ink); font-size: 1.45rem; font-weight: 600; line-height: 1.35; }
.mm-kpi .s { color: var(--mm-muted); font-size: .8rem; }
.mm-kpi.hl { background: var(--mm-green-soft); border-color: #bbf7d0; }
.up { color: #15803d; } .down { color: #b91c1c; }

/* ---------- Summary card ---------- */
.mm-card { background: var(--mm-card); border: 1px solid var(--mm-line); border-radius: 16px; padding: 18px; }
.mm-card h4 { margin: 0 0 10px; font-size: 1.05rem; color: var(--mm-ink); }
.mm-row { display: flex; justify-content: space-between; gap: 10px; padding: 6px 0; color: var(--mm-ink-2); }
.mm-row b { color: var(--mm-ink); font-family: 'Kanit', sans-serif; font-weight: 600; font-size: 1.08rem; }
.mm-row.sm { font-size: .88rem; color: var(--mm-muted); padding: 2px 0 2px 12px; }
.mm-row > :last-child { white-space: nowrap; flex: 0 0 auto; text-align: right; }
.mm-row.sm > span:last-child { color: var(--mm-ink-2); }
.mm-tag { font-size: .72rem; padding: 1px 8px; border-radius: 999px; background: #f1f5f9; color: var(--mm-ink-2);
          margin-left: 6px; white-space: nowrap; display: inline-block; }
.mm-profit {
  margin-top: 10px; border-radius: 12px; background: var(--mm-green-soft); border: 1px solid #bbf7d0;
  padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;
}
.mm-profit .l { color: #166534; font-weight: 600; }
.mm-profit .v { color: #14532d; font-size: 1.7rem; font-weight: 700; }
.mm-note { border-radius: 10px; padding: 10px 12px; font-size: .9rem; margin-top: 10px; line-height: 1.5; }
.mm-note.ok { background: var(--mm-green-soft); color: #166534; border: 1px solid #bbf7d0; }
.mm-note.warn { background: var(--mm-amber-soft); color: #92400e; border: 1px solid #fde68a; }
.mm-note.info { background: var(--mm-blue-soft); color: #1e40af; border: 1px solid #bfdbfe; }
.mm-note.err { background: var(--mm-red-soft); color: #991b1b; border: 1px solid #fecaca; }

/* ---------- Slip read chip ---------- */
.mm-amt { display: inline-block; margin: 4px 0 8px; padding: 3px 10px; border-radius: 999px; font-size: .85rem; font-weight: 600; }
.mm-amt.ok { background: var(--mm-green-soft); color: #166534; }
.mm-amt.no { background: #f1f5f9; color: var(--mm-muted); font-weight: 500; }

/* ---------- Day header (history) ---------- */
.mm-day { display: flex; justify-content: space-between; align-items: baseline; margin: 14px 0 6px; flex-wrap: wrap; gap: 6px; }
.mm-day b { font-family: 'Kanit', sans-serif; font-size: 1.05rem; color: var(--mm-ink); }
.mm-day span { color: var(--mm-muted); font-size: .88rem; }

/* ---------- Service cards ---------- */
.mm-svc { background: var(--mm-card); border: 1px solid var(--mm-line); border-radius: 14px; padding: 14px 16px; height: 100%; }
.mm-svc .t { font-weight: 600; color: var(--mm-ink); margin-bottom: 6px; font-family: 'Kanit', sans-serif; }
.mm-svc .r { display: flex; justify-content: space-between; color: var(--mm-ink-2); font-size: .9rem; padding: 2px 0; }
.mm-svc .r.p { border-top: 1px dashed var(--mm-line); margin-top: 6px; padding-top: 6px; font-weight: 600; color: var(--mm-ink); }

div[data-testid="stExpander"] details { border-radius: 12px; background: #fff; }
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button { border-radius: 10px; font-weight: 600; }

@media (max-width: 640px) {
  .block-container { padding-left: .8rem; padding-right: .8rem; padding-top: .6rem; }
  .mm-hero { padding: 16px; } .mm-hero h1 { font-size: 1.3rem; }
  .mm-kpi .v { font-size: 1.2rem; }
  .stTabs [data-baseweb="tab"] { padding: 8px 10px; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. Helpers
# ============================================================
IMG_TYPES = ["jpg", "jpeg", "png", "webp"]
SERVICE_ICON = {"รับกลางไอดี": "💎", "การแลกไอดี": "🔄", "เช่าจอดูบอล": "⚽"}
SERVICE_ACC = {"รับกลางไอดี": "#2a78d6", "การแลกไอดี": "#6250d6", "เช่าจอดูบอล": "#1baf7a"}


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def fmt(v, dec: bool = True) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "-"
    s = f"{v:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def stretch(fn, *args, **kwargs):
    """เรียก widget ให้เต็มความกว้าง รองรับทั้ง Streamlit รุ่นใหม่ (width='stretch') และรุ่นเก่า"""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


def kpis(items) -> None:
    """items: list of (label, value, sub, accent_color, highlight)"""
    cells = []
    for it in items:
        label, value, sub, acc = it[0], it[1], it[2], it[3]
        hl = len(it) > 4 and it[4]
        cells.append(
            f'<div class="mm-kpi{" hl" if hl else ""}" style="--acc:{acc}">'
            f'<div class="l">{label}</div><div class="v">{value}</div>'
            f'<div class="s">{sub}</div></div>'
        )
    st.markdown(f'<div class="mm-kpis">{"".join(cells)}</div>', unsafe_allow_html=True)


def step(n, title, hint=""):
    h = f'<span class="h">· {esc(hint)}</span>' if hint else ""
    st.markdown(f'<div class="mm-step"><span class="n">{n}</span><b>{esc(title)}</b>{h}</div>',
                unsafe_allow_html=True)


def flash(text, kind="success", balloons=False):
    st.session_state["flash_message"] = {"type": kind, "text": text, "balloons": balloons}


def render_slip_item(slip_val, caption: str):
    """แสดงรูปสลิป: รับเฉพาะ https:// หรือไฟล์ในโฟลเดอร์ slips/ ของโปรเจกต์ (กันอ่านไฟล์นอกโฟลเดอร์)"""
    if slip_val is None or str(slip_val).strip() in ("", "nan"):
        st.caption(f"⚪ ไม่มี{caption}")
        return
    v = str(slip_val).strip()
    if v.startswith("https://"):
        st.image(v, caption=caption, width=220)
        st.link_button("🔍 เปิดรูปเต็ม", v)
    elif v.startswith("slips/") and ".." not in v and os.path.isfile(v):
        st.image(v, caption=caption, width=220)
    else:
        st.caption(f"📁 {caption}: `{os.path.basename(v)}` (ไฟล์อยู่ในเครื่องเดิม)")


# ============================================================
# 2.5 ล็อกอิน (ป้องกันคนนอกเปิดดู/ลบข้อมูลการเงิน)
# ============================================================
def require_login():
    """ต้องตั้ง APP_PASSWORD ใน Secrets ของ Streamlit — ถ้าไม่ตั้ง แอปจะไม่เปิด (fail-closed)"""
    pw = str(st.secrets.get("APP_PASSWORD", "")).strip()
    if not pw:
        st.error("🔒 ยังไม่ได้ตั้งรหัสผ่าน — เพิ่มบรรทัด `APP_PASSWORD = \"รหัสของคุณ\"` ใน Secrets แล้วรีบูตแอป")
        st.stop()
    if st.session_state.get("_auth_ok"):
        return
    st.markdown('<div class="mm-hero"><div><h1>🔒 Money Manager Pro</h1>'
                '<div class="sub">กรุณาใส่รหัสผ่านเพื่อเข้าใช้งาน</div></div></div>', unsafe_allow_html=True)
    wait = st.session_state.get("_lock_until", 0) - time.time()
    if wait > 0:
        st.error(f"ใส่รหัสผิดหลายครั้ง กรุณารออีก {int(wait) + 1} วินาที")
        st.stop()
    with st.form("login_form"):
        entered = st.text_input("รหัสผ่าน", type="password")
        go = st.form_submit_button("เข้าสู่ระบบ", type="primary")
    if go:
        if hmac.compare_digest(entered.encode("utf-8"), pw.encode("utf-8")):
            st.session_state["_auth_ok"] = True
            st.session_state["_fails"] = 0
            st.rerun()
        time.sleep(1.5)
        fails = st.session_state.get("_fails", 0) + 1
        st.session_state["_fails"] = fails
        if fails >= 5:
            st.session_state["_lock_until"] = time.time() + 60
            st.session_state["_fails"] = 0
        st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()


require_login()


# ============================================================
# 3. Load data (โหลดครั้งเดียวต่อรอบ ใช้ร่วมกันทุกแท็บ)
# ============================================================
df_all = lg.with_dates(db.load_data())
now = lg.now_th()
today = now.date()
today_tot = lg.totals(df_all[df_all["day"] == today]) if not df_all.empty else lg.totals(None)
month_tot = lg.totals(df_all[(df_all["year"] == now.year) & (df_all["month"] == now.month)]) \
    if not df_all.empty else lg.totals(None)

st.markdown(
    f'<div class="mm-hero"><div><h1>💰 Money Manager Pro</h1>'
    f'<div class="sub">รับกลางไอดี · แลกไอดี · เช่าจอดูบอล — บันทึกลง Google Sheets อัตโนมัติ</div></div>'
    f'<div class="chips">'
    f'<span class="mm-chip">📅 {lg.th_date(today)}</span>'
    f'<span class="mm-chip">วันนี้ <b>{fmt(today_tot["profit"])} ฿</b> · {today_tot["count"]} รายการ</span>'
    f'<span class="mm-chip">เดือนนี้ <b>{fmt(month_tot["profit"])} ฿</b></span>'
    f'</div></div>',
    unsafe_allow_html=True,
)

if "flash_message" in st.session_state:
    fl = st.session_state.pop("flash_message")
    {"success": st.success, "warning": st.warning, "error": st.error}.get(fl.get("type"), st.info)(fl.get("text", ""))
    if fl.get("balloons"):
        st.balloons()

tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการ", "📅 ประวัติรายวัน", "📊 สรุปรายเดือน"])

# ============================================================
# TAB 1 : บันทึกรายการ
# ============================================================
with tab1:
    nonce = st.session_state.setdefault("form_nonce", 0)

    def K(name):  # key ของฟอร์ม เปลี่ยนทุกครั้งที่บันทึกเสร็จ -> ล้างฟอร์ม/สลิปอัตโนมัติ
        return f"{name}_{nonce}"

    col_l, col_r = st.columns([1.35, 1], gap="large")

    with col_l:
        # ---------- Step 1 ----------
        with st.container(border=True):
            step(1, "เลือกบริการ")
            service = st.radio(
                "บริการ", lg.SERVICES, horizontal=True, label_visibility="collapsed",
                format_func=lambda s: f"{SERVICE_ICON[s]} {s}", key=K("service"),
            )
            game = lg.DEFAULT_GAME
            if service in lg.GAME_SERVICES:
                st.markdown("**เลือกเกม**")
                game = st.radio("เกม", list(lg.GAMES), horizontal=True, label_visibility="collapsed",
                                format_func=lambda g: f"{lg.GAMES[g].icon} {g}", key=K("game"))
            G = lg.GAMES[game]

        # ---------- Step 2 ----------
        with st.container(border=True):
            step(2, "อัปโหลดสลิป", "ไม่บังคับ — แนบไว้เป็นหลักฐาน")
            has_out = service != "เช่าจอดูบอล"
            slot_in, slot_out = (st.columns(2) if has_out else (st.container(), None))

            with slot_in:
                st.markdown("**💚 สลิปเงินเข้า** <span class='mm-tag'>สูงสุด 2 ใบ</span>", unsafe_allow_html=True)
                in_files = st.file_uploader("สลิปเงินเข้า", type=IMG_TYPES, accept_multiple_files=True,
                                            key=K("in_files"), label_visibility="collapsed") or []
                if len(in_files) > 2:
                    st.warning("ใช้ได้สูงสุด 2 ใบ ระบบจะใช้ 2 ใบแรก")
                    in_files = in_files[:2]
                for f in in_files:
                    st.image(f, width=170)

            out_file = None
            if has_out:
                with slot_out:
                    st.markdown("**❤️ สลิปเงินออก** <span class='mm-tag'>ถ้าโอนให้ผู้ขายแล้ว</span>",
                                unsafe_allow_html=True)
                    out_file = st.file_uploader("สลิปเงินออก", type=IMG_TYPES, key=K("out_file"),
                                                label_visibility="collapsed")
                    if out_file:
                        st.image(out_file, width=170)

            # >>> จุดเสียบระบบอ่านสลิปของคุณ <<<
            # ไฟล์ที่อัปโหลด: in_files (list 0-2 ใบ), out_file (1 ใบหรือ None)
            # อ่านยอดแล้วใส่ช่องกรอกด้านล่างก่อนถึง Step 3 ได้ด้วย:
            #   st.session_state[K("income")]     = ยอดเงินเข้า   (รับกลางไอดี / เช่าจอดูบอล)
            #   st.session_state[K("out_amount")] = ยอดโอนออก
            # (ต้องตั้งค่าก่อนที่ st.number_input ของ Step 3 จะถูกสร้างในรอบนั้น)

        # ---------- Step 3 ----------
        with st.container(border=True):
            step(3, "ยอดเงิน & รายละเอียด")
            st.session_state.setdefault(K("income"), 0.0)
            st.session_state.setdefault(K("out_amount"), 0.0)
            sel_extras = []
            topup = 0.0          # ค่าเสริมที่ลูกค้าโอนเพิ่ม (ลืมเขียนโน๊ต) -> บวกเข้ากำไร
            include_fee = False
            exchange_rate = 0
            out_amount = 0.0

            if service == "รับกลางไอดี":
                income = st.number_input("💰 ยอดเงินเข้าทั้งหมด (บาท)", min_value=0.0, step=10.0,
                                         format="%.2f", key=K("income"))
                mode = st.radio(
                    "ยอดที่ลูกค้าโอนมา",
                    ["exclude", "include"], horizontal=True, key=K("fee_mode"),
                    format_func=lambda m: "ยังไม่รวมค่ากลาง" if m == "exclude" else "รวมค่ากลางแล้ว",
                    help=("ยังไม่รวม: เทียบเรทจากยอดที่โอนมาเลย (1,491 → เรท 80)\n\n"
                          "รวมแล้ว: หักค่ากลาง/ค่าบริการเสริมออกก่อนแล้วค่อยเทียบเรท (1,500 → 1,440 → เรท 60)")
                         if game == "FC Mobile" else
                         ("ยังไม่รวม: เทียบเรทจากยอดที่โอนมาเลย (601 → เรท 30)\n\n"
                          "รวมแล้ว: หักค่ากลาง/ค่าบริการเสริมออกก่อนแล้วค่อยเทียบเรท (620 → 600 → เรท 20)"),
                )
                include_fee = mode == "include"
                ecols = st.columns(max(len(G.extras), 1))
                for ecol, (xk, xlabel, xamt) in zip(ecols, G.extras):
                    if ecol.checkbox(f"{xlabel} (+{fmt(xamt)})", key=K(f"x_{game}_{xk}")):
                        sel_extras.append((xlabel, xamt))
                        if xk in lg.TOPUP_EXTRAS:
                            topup += xamt
                out_amount = st.number_input("💸 ยอดโอนออกจริง (ใส่ 0 ถ้ายังไม่ได้โอน ระบบจะคำนวณให้)",
                                             min_value=0.0, step=10.0, format="%.2f", key=K("out_amount"))
                note = st.text_input("📌 ชื่อลูกค้า / รหัสไอดี", key=K("note"), max_chars=200,
                                     placeholder=f"เช่น {game} บัญชีคุณบาส")
                calc = lg.compute_middleman(income, sum(a for _, a in sel_extras), include_fee,
                                            out_amount, game, topup)

            elif service == "การแลกไอดี":
                exchange_rate = st.radio("เรทค่าแลกไอดี", list(G.exchange_rates), horizontal=True,
                                         key=K(f"ex_rate_{game}"), format_func=lambda x: f"🏷️ {fmt(x)} บาท")
                ecols = st.columns(max(len(G.exchange_extras), 1))
                for ecol, (xk, xlabel, xamt) in zip(ecols, G.exchange_extras):
                    if ecol.checkbox(f"{xlabel} (+{fmt(xamt)})", key=K(f"xe_{game}_{xk}")):
                        sel_extras.append((xlabel, xamt))
                out_amount = st.number_input("💸 ยอดโอนออก (ถ้ามี)", min_value=0.0, step=10.0,
                                             format="%.2f", key=K("out_amount"))
                note = st.text_input("📌 รายละเอียด", key=K("note"), max_chars=200,
                                     placeholder="เช่น แลกบัญชี A กับ บัญชี B")
                calc = lg.compute_exchange(exchange_rate, sum(a for _, a in sel_extras), out_amount)
                income = calc.income

            else:
                income = st.number_input("💰 ยอดเงินเข้าทั้งหมด (บาท)", min_value=0.0, step=10.0,
                                         format="%.2f", key=K("income"))
                note = st.text_input("📌 ช่องที่เช่า / แมตช์", key=K("note"), max_chars=200,
                                     placeholder="เช่น พรีเมียร์ลีก บัญชีคุณเอ")
                calc = lg.compute_rental(income)

    # ---------- Summary ----------
    with col_r:
        rows = [f'<div class="mm-row"><span>💰 ยอดเงินเข้า</span><b>{fmt(calc.income)} ฿</b></div>']
        notes = []

        if service == "รับกลางไอดี":
            src = "จากสลิป" if calc.from_slip else "คำนวณให้"
            rows.append(f'<div class="mm-row"><span>💸 ยอดโอนออกให้ผู้ขาย <span class="mm-tag">{src}</span></span>'
                        f'<b>{fmt(calc.expense)} ฿</b></div>')
            fr = calc.fee
            mode_txt = "ยอดรวมค่ากลางแล้ว" if include_fee else "ยังไม่รวมค่ากลาง"
            rows.append(f'<div class="mm-row sm"><span>ค่ากลาง · ยอดไอดี {fmt(fr.price)} '
                        f'<span class="mm-tag">{mode_txt}</span></span>'
                        f'<span>{fmt(calc.base_fee)} ฿</span></div>')
            for xlabel, xamt in sel_extras:
                rows.append(f'<div class="mm-row sm"><span>{esc(xlabel)}</span><span>{fmt(xamt)} ฿</span></div>')

            if calc.income > 0:
                if fr.warning:
                    alt = f" (ถ้าคิด {fmt(fr.alt_fee)} ฿ ยอดไอดีจะเกินเรท)" if fr.alt_fee else ""
                    notes.append(("warn", f"⚠️ {fr.warning}: ใช้ {fmt(fr.base_fee)} ฿{alt}"))
                if calc.from_slip:
                    if abs(calc.diff) < 0.01:
                        parts = [f"ค่ากลาง {fmt(calc.base_fee)}"]
                        parts += [f"{xl.split(' ', 1)[-1]} {fmt(xa)}" for xl, xa in sel_extras]
                        notes.append(("ok", f"✅ ยอดโอนออกถูกต้อง: เข้า {fmt(calc.income)} − ออก {fmt(calc.expense)} "
                                            f"= {fmt(calc.profit)} ฿ ({' + '.join(parts)})"))
                    else:
                        sign = "มากกว่า" if calc.diff > 0 else "น้อยกว่า"
                        msg = (f"⚠️ ส่วนต่างที่ได้ {fmt(calc.profit)} ฿ {sign}ที่ควรได้ "
                               f"({fmt(calc.expected_profit)} ฿) อยู่ {fmt(abs(calc.diff))} ฿")
                        hints = []
                        if calc.other_mode_profit is not None and abs(calc.other_mode_profit - calc.profit) < 0.01:
                            other = "รวมค่ากลางแล้ว" if not include_fee else "ยังไม่รวมค่ากลาง"
                            hints.append(f"ตรงกับการคิดแบบ “{other}” — ลองเปลี่ยนตัวเลือกด้านซ้าย")
                        chosen = {xl for xl, _ in sel_extras}
                        for xl, _k, xa in [(l, k, a) for k, l, a in G.extras]:
                            if xl not in chosen and abs(calc.diff - xa) < 0.01:
                                hints.append(f"ส่วนต่างเท่า{xl.split(' ', 1)[-1]} {fmt(xa)} — ลืมติ๊กหรือเปล่า?")
                        if hints:
                            msg += "<br>💡 " + "<br>💡 ".join(hints)
                        notes.append(("warn", msg))
                else:
                    notes.append(("info", f"ℹ️ ต้องโอนให้ผู้ขาย <b>{fmt(calc.expense)} ฿</b> "
                                          f"— อัปโหลดสลิปเงินออกเพื่อเช็กยอดอัตโนมัติ"))

        elif service == "การแลกไอดี":
            rows.append(f'<div class="mm-row sm"><span>เรทค่าแลกไอดี</span><span>{fmt(calc.base_fee)} ฿</span></div>')
            for xlabel, xamt in sel_extras:
                rows.append(f'<div class="mm-row sm"><span>{esc(xlabel)}</span><span>{fmt(xamt)} ฿</span></div>')
            rows.append(f'<div class="mm-row"><span>💸 ยอดโอนออก</span><b>{fmt(calc.expense)} ฿</b></div>')
        else:
            rows.append('<div class="mm-row"><span>💸 ยอดโอนออก</span><b>0 ฿</b></div>')

        note_html = "".join(f'<div class="mm-note {k}">{m}</div>' for k, m in notes)
        st.markdown(
            f'<div class="mm-card"><h4>{SERVICE_ICON[service]} สรุปรายการ · {esc(service)}{esc(' · ' + game) if service in lg.GAME_SERVICES else ''}</h4>'
            f'{"".join(rows)}'
            f'<div class="mm-profit"><span class="l">📈 กำไรของร้าน</span><span class="v">{fmt(calc.profit)} ฿</span></div>'
            f'{note_html}</div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if stretch(st.button, "💾 บันทึกรายการ", type="primary", key=K("save")):
            if calc.income <= 0:
                st.warning("⚠️ กรุณาระบุยอดเงินเข้าที่มากกว่า 0 บาท")
            elif calc.profit < 0:
                st.error("❌ ยอดโอนออกมากกว่ายอดเงินเข้า ตรวจสอบตัวเลขอีกครั้ง")
            else:
                with st.spinner("⏳ กำลังบันทึกข้อมูลและสลิป..."):
                    tag = lg.now_th().strftime("%Y%m%d%H%M%S")
                    plan = [(in_files[0] if len(in_files) > 0 else None, "incoming", "in1"),
                            (in_files[1] if len(in_files) > 1 else None, "incoming", "in2"),
                            (out_file, "outgoing", "out")]
                    urls, upload_err = {}, ""
                    for f, sub, pre in plan:
                        if f is None:
                            urls[pre] = ""
                            continue
                        u = im.upload_image(f, subfolder=sub, prefix=f"{tag}_{pre}")
                        if not u:
                            upload_err = im.last_error or "อัปโหลดสลิปไม่สำเร็จ"
                            break
                        urls[pre] = u

                    new_id = None
                    if not upload_err:
                        parts = []
                        if service == "รับกลางไอดี":
                            parts.append(f"ค่ากลาง {fmt(calc.base_fee)}")
                            if include_fee:
                                parts.append("ยอดรวมค่ากลางแล้ว")
                        if service == "การแลกไอดี":
                            parts.append(f"เรทแลก {fmt(exchange_rate)}฿")
                        if service in lg.GAME_SERVICES:
                            parts += [f"{xl.split(' ', 1)[-1]} (+{fmt(xa)})" for xl, xa in sel_extras]
                        if service == "รับกลางไอดี" and calc.from_slip and abs(calc.diff or 0) >= 0.01:
                            parts.append(f"ส่วนต่างจากเรท {calc.diff:+,.2f}")
                        if note.strip():
                            parts.append(note.strip())

                        new_id = db.append_row({
                            "วันที่": lg.now_th().strftime("%Y-%m-%d %H:%M"),
                            "ประเภท": service,
                            "เกม": game if service in lg.GAME_SERVICES else "",
                            "รายละเอียด": " | ".join(parts),
                            "ยอดเข้า": round(calc.income, 2),
                            "ยอดออก": round(calc.expense, 2),
                            "กำไร": round(calc.profit, 2),
                            "สถานะโอนออก": "โอนแล้ว",
                            "สลิปเข้า": urls["in1"],
                            "สลิปเข้า 2": urls["in2"],
                            "สลิปออก": urls["out"],
                        })
                if upload_err:
                    st.error(f"❌ {upload_err} — ยังไม่ได้บันทึกรายการ แก้ไขแล้วกดบันทึกอีกครั้ง")
                elif new_id:
                    st.session_state["form_nonce"] = nonce + 1   # ล้างฟอร์มและสลิป
                    msg = (f"🎉 บันทึก #{new_id} ({service}{' · ' + game if service in lg.GAME_SERVICES else ''}) เข้า {fmt(calc.income)} ฿ · "
                           f"กำไร {fmt(calc.profit)} ฿ เรียบร้อย")
                    if any(u and not u.startswith("https://") for u in urls.values()):
                        flash(msg + " — ⚠️ สลิปถูกเก็บในเครื่องเซิร์ฟเวอร์ชั่วคราว (Cloudinary ยังไม่พร้อม) "
                                    "อาจหายเมื่อรีบูตแอป", "warning")
                    else:
                        flash(msg, balloons=True)
                    st.rerun()
                else:
                    st.error("❌ ส่งข้อมูลไป Google Sheets ไม่สำเร็จ")

        with st.expander("📋 ตารางเรทค่ากลาง"):
            for gname, gm in lg.GAMES.items():
                lo, lines = 0, []
                for limit, fee in gm.tiers:
                    lines.append(f"| {fmt(lo)} ขึ้นไป | {fmt(fee)} ฿ |" if limit == lg.INF
                                 else f"| {fmt(lo)} – {fmt(limit)} | {fmt(fee)} ฿ |")
                    lo = limit + 1
                if gm.percent:
                    lines.append(f"| {fmt(lo)} ขึ้นไป | {int(gm.percent * 100)}% |")
                extra_txt = " · ".join(f"{l.split(' ', 1)[-1]} **+{fmt(a)}**" for _, l, a in gm.extras)
                ex_rates = " / ".join(fmt(r) for r in gm.exchange_rates)
                ex_extra = " · ".join(f"{l.split(' ', 1)[-1]} **+{fmt(a)}**" for _, l, a in gm.exchange_extras)
                st.markdown(f"**{gm.icon} {gname}**\n\n| ยอดไอดี | ค่ากลาง |\n|---|---|\n" + "\n".join(lines) +
                            f"\n\nรับกลาง: {extra_txt} (ไม่รวมค่ากลาง)"
                            f"\n\nแลกไอดี: **{ex_rates} บาท** · {ex_extra}")


# ============================================================
# TAB 2 : ประวัติรายวัน
# ============================================================
def record_card(row, key_prefix: str):
    rid = int(row["ID"])
    rown = int(row["_row"])
    kp = f"{key_prefix}_{rown}"
    t = row["dt"].strftime("%H:%M") if pd.notna(row["dt"]) else "--:--"
    typ = str(row["ประเภท"])
    title = (f"#{rid} · {t} · {lg.category_label(row['cat'])} · เข้า {fmt(row['ยอดเข้า'])} · "
             f"ออก {fmt(row['ยอดออก'])} · กำไร {fmt(row['กำไร'])} ฿")
    with st.expander(title):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(
                f'<div class="mm-row"><span>💰 ยอดเงินเข้า</span><b>{fmt(row["ยอดเข้า"])} ฿</b></div>'
                f'<div class="mm-row"><span>💸 ยอดโอนออก</span><b>{fmt(row["ยอดออก"])} ฿</b></div>'
                f'<div class="mm-row"><span>📈 กำไร</span><b>{fmt(row["กำไร"])} ฿</b></div>'
                f'<div class="mm-row sm"><span>📝 {esc(row["รายละเอียด"]) or "-"}</span></div>',
                unsafe_allow_html=True,
            )
        with c2:
            with st.popover("🗑️ ลบรายการ"):
                st.write(f"ลบรายการ #{rid} ออกจาก Google Sheets?")
                if st.button("ยืนยันลบ", type="primary", key=f"{kp}_del_{rid}"):
                    if db.delete_row(rid, rown):
                        flash(f"🗑️ ลบรายการ #{rid} แล้ว")
                        st.rerun()
                    else:
                        st.error("ลบไม่สำเร็จ — ข้อมูลในชีทอาจถูกแก้จากที่อื่น กด “โหลดข้อมูลล่าสุด” แล้วลองใหม่")

        i1, i2, i3 = st.columns(3)
        with i1:
            render_slip_item(row["สลิปเข้า"], "สลิปเข้า 1")
        with i2:
            render_slip_item(row["สลิปเข้า 2"], "สลิปเข้า 2")
        with i3:
            render_slip_item(row["สลิปออก"], "สลิปออก")

        if st.toggle("📷 แนบ/เปลี่ยนสลิป", key=f"{kp}_tg_{rid}"):
            u1, u2, u3 = st.columns(3)
            r1 = u1.file_uploader("สลิปเข้า 1", type=IMG_TYPES, key=f"{kp}_u1_{rid}")
            r2 = u2.file_uploader("สลิปเข้า 2", type=IMG_TYPES, key=f"{kp}_u2_{rid}")
            r3 = u3.file_uploader("สลิปออก", type=IMG_TYPES, key=f"{kp}_u3_{rid}")
            if st.button("💾 บันทึกสลิป", key=f"{kp}_save_{rid}"):
                changed = False
                for f, colname, sub, pre in ((r1, "สลิปเข้า", "incoming", "in1"),
                                             (r2, "สลิปเข้า 2", "incoming", "in2"),
                                             (r3, "สลิปออก", "outgoing", "out")):
                    if f:
                        url = im.upload_image(f, subfolder=sub, prefix=f"{rid}_{pre}")
                        if not url:
                            st.error(f"❌ {im.last_error or 'อัปโหลดสลิปไม่สำเร็จ'}")
                        elif db.update_cell(rid, colname, url, rown):
                            changed = True
                if changed:
                    flash(f"✅ อัปเดตสลิป #{rid} แล้ว")
                    st.rerun()
                else:
                    st.warning("เลือกไฟล์สลิปก่อนกดบันทึก")


def day_header(d, sub_df):
    tt = lg.totals(sub_df)
    label = "ไม่ทราบวันที่" if d is None else ("วันนี้ · " if d == today else "") + lg.th_date(d, full_month=True)
    st.markdown(
        f'<div class="mm-day"><b>{esc(label)}</b><span>{tt["count"]} รายการ · เข้า {fmt(tt["in"])} · '
        f'ออก {fmt(tt["out"])} · กำไร {fmt(tt["profit"])} ฿</span></div>',
        unsafe_allow_html=True,
    )


with tab2:
    if df_all.empty:
        st.info("ℹ️ ยังไม่มีรายการใน Google Sheets")
    else:
        if st.button("🔄 โหลดข้อมูลล่าสุดจาก Google Sheets", key="refresh_data"):
            db.clear_cache()
            st.rerun()
        f1, f2 = st.columns([1.6, 1])
        q = f1.text_input("🔍 ค้นหาทุกวัน (ID / ชื่อลูกค้า / รายละเอียด)", key="hist_q", placeholder="พิมพ์เพื่อค้นหา...")
        ftype = f2.selectbox("เกม / ประเภท", ["ทั้งหมด"] + lg.CATEGORIES, key="hist_type",
                             format_func=lambda c: c if c == "ทั้งหมด" else lg.category_label(c))

        base = df_all if ftype == "ทั้งหมด" else df_all[df_all["cat"] == ftype]

        if q.strip():
            ql = q.strip().lower()
            res = base[base["ID"].astype(str).str.contains(ql, regex=False) |
                       base["รายละเอียด"].str.lower().str.contains(ql, regex=False, na=False)]
            st.caption(f"พบ {len(res)} รายการ")
            res = res.sort_values(["dt", "ID"], ascending=False, na_position="last")
            for d in sorted(res["day"].dropna().unique(), reverse=True):
                g = res[res["day"] == d]
                day_header(d, g)
                for _, r in g.iterrows():
                    record_card(r, "s")
            undated = res[res["dt"].isna()]
            if not undated.empty:
                day_header(None, undated)
                for _, r in undated.iterrows():
                    record_card(r, "s")
        else:
            days = lg.daily_summary(base)
            day_opts = [today] + [d for d in days["day"].tolist() if d != today]
            has_undated = base["dt"].isna().any()
            if has_undated:
                day_opts.append(None)
            stats = {r["day"]: r for _, r in days.iterrows()}

            def day_label(d):
                if d is None:
                    return "❔ ไม่ทราบวันที่"
                s = stats.get(d)
                n = int(s["count"]) if s is not None else 0
                pre = "📍 วันนี้ · " if d == today else ""
                tail = f" — {n} รายการ · กำไร {fmt(s['profit'])} ฿" if n else " — ยังไม่มีรายการ"
                return f"{pre}{lg.th_date(d)}{tail}"

            sel = st.selectbox("📅 เลือกวัน (รายการของวันก่อน ๆ ถูกเก็บแยกไว้ตามวัน)", day_opts,
                               format_func=day_label, key="hist_day")

            day_df = base[base["dt"].isna()] if sel is None else base[base["day"] == sel]
            tt = lg.totals(day_df)
            kpis([
                ("จำนวนรายการ", f"{tt['count']}", "รายการ", "#94a3b8"),
                ("เงินเข้า", f"{fmt(tt['in'])} ฿", "", "#2a78d6"),
                ("เงินออก", f"{fmt(tt['out'])} ฿", "", "#eb6834"),
                ("กำไร", f"{fmt(tt['profit'])} ฿", "", "#16a34a", True),
            ])

            if day_df.empty:
                st.info("ยังไม่มีรายการของวันนี้ — เริ่มบันทึกได้ที่แท็บ “บันทึกรายการ”"
                        if sel == today else "ไม่มีรายการในวันนี้")
            else:
                present = [c for c in lg.CATEGORIES if (day_df["cat"] == c).any()] + \
                          [c for c in day_df["cat"].unique() if c not in lg.CATEGORIES]
                for c in present:
                    sub = day_df[day_df["cat"] == c]
                    ct = lg.totals(sub)
                    st.markdown(
                        f'<div class="mm-day"><b style="border-left:4px solid {lg.category_color(c)};padding-left:8px">'
                        f'{esc(lg.category_label(c))}</b><span>{ct["count"]} รายการ · เข้า {fmt(ct["in"])} · '
                        f'ออก {fmt(ct["out"])} · กำไร {fmt(ct["profit"])} ฿</span></div>', unsafe_allow_html=True)
                    for _, r in sub.sort_values(["dt", "ID"], ascending=False).iterrows():
                        record_card(r, "d")

            # สรุปรายวันของเดือนเดียวกัน
            ref = sel or today
            mdays = days[days["day"].map(lambda d: d.year == ref.year and d.month == ref.month)]
            if not mdays.empty:
                st.markdown(f"#### 🗓️ สรุปรายวัน · {lg.th_month(ref.year, ref.month)}")
                show = pd.DataFrame({
                    "วันที่": mdays["day"].map(lambda d: lg.th_date(d)),
                    "รายการ": mdays["count"].astype(int),
                    "เงินเข้า": mdays["in"], "เงินออก": mdays["out"], "กำไร": mdays["profit"],
                })
                st.dataframe(show.style.format({"เงินเข้า": "{:,.2f}", "เงินออก": "{:,.2f}", "กำไร": "{:,.2f}"}),
                             hide_index=True)

        st.divider()
        export = df_all.drop(columns=["dt", "day", "year", "month", "_row", "cat"], errors="ignore").sort_values("ID")
        for _c in db.EXPORT_TEXT_COLS:      # กัน CSV Injection เมื่อเปิดด้วย Excel
            export[_c] = export[_c].map(db.safe_text)
        stretch(st.download_button, "📥 ดาวน์โหลดข้อมูลทั้งหมด (.csv เปิดด้วย Excel ได้)",
                data=export.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"money_manager_{now.strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")


# ============================================================
# TAB 3 : สรุปรายเดือน
# ============================================================
with tab3:
    years = sorted({int(y) for y in df_all["year"].dropna().unique()} | {now.year}, reverse=True)
    c1, c2 = st.columns(2)
    year = c1.selectbox("ปี", years, format_func=lambda y: f"พ.ศ. {y + 543} ({y})", key="sum_year")
    ms = lg.monthly_summary(df_all, year)
    if year == now.year:
        default_m = now.month
    elif (ms["count"] > 0).any():
        default_m = int(ms.loc[ms["count"] > 0, "month"].max())   # เดือนล่าสุดที่มีข้อมูล
    else:
        default_m = 12
    month = c2.selectbox("เดือน", list(range(1, 13)), index=default_m - 1,
                         format_func=lambda m: lg.TH_MONTHS_FULL[m - 1] + (" (เดือนนี้)" if year == now.year and m == now.month else ""),
                         key=f"sum_month_{year}")

    cur = ms[ms["month"] == month].iloc[0]
    py, pm = (year, month - 1) if month > 1 else (year - 1, 12)
    prev = lg.totals(df_all[(df_all["year"] == py) & (df_all["month"] == pm)]) if not df_all.empty else lg.totals(None)

    def delta(curv, prevv):
        if not prevv:
            return "เดือนก่อนไม่มีข้อมูล"
        d = curv - prevv
        cls = "up" if d >= 0 else "down"
        arrow = "▲" if d >= 0 else "▼"
        return f'<span class="{cls}">{arrow} {fmt(abs(d))}</span> จากเดือนก่อน'

    is_current = year == now.year and month == now.month
    st.markdown(f"### {'📌 ' if is_current else ''}{lg.th_month(year, month)}"
                f"{' · เดือนปัจจุบัน (นับใหม่อัตโนมัติทุกต้นเดือน)' if is_current else ''}")
    kpis([
        ("💰 เงินเข้า", f"{fmt(cur['in'])} ฿", delta(cur["in"], prev["in"]), "#2a78d6"),
        ("💸 เงินออก", f"{fmt(cur['out'])} ฿", delta(cur["out"], prev["out"]), "#eb6834"),
        ("📈 กำไร", f"{fmt(cur['profit'])} ฿", delta(cur["profit"], prev["profit"]), "#16a34a", True),
        ("🧾 จำนวนรายการ", f"{int(cur['count'])}", f"เดือนก่อน {prev['count']} รายการ", "#94a3b8"),
    ])

    mdf = df_all[(df_all["year"] == year) & (df_all["month"] == month)] if not df_all.empty else df_all
    for i in range(0, len(lg.CATEGORIES), 3):
        chunk = lg.CATEGORIES[i:i + 3]
        for col, cat in zip(st.columns(3), chunk):
            t = lg.totals(mdf[mdf["cat"] == cat] if not mdf.empty else None)
            col.markdown(
                f'<div class="mm-svc" style="border-top:3px solid {lg.category_color(cat)};margin-bottom:10px">'
                f'<div class="t">{esc(lg.category_label(cat))}</div>'
                f'<div class="r"><span>รายการ</span><span>{t["count"]}</span></div>'
                f'<div class="r"><span>เงินเข้า</span><span>{fmt(t["in"])} ฿</span></div>'
                f'<div class="r"><span>เงินออก</span><span>{fmt(t["out"])} ฿</span></div>'
                f'<div class="r p"><span>กำไร</span><span>{fmt(t["profit"])} ฿</span></div></div>',
                unsafe_allow_html=True,
            )

    st.divider()
    ytot = {"in": ms["in"].sum(), "out": ms["out"].sum(), "profit": ms["profit"].sum(), "count": int(ms["count"].sum())}
    st.markdown(f"### 📆 ภาพรวมทั้งปี {year + 543}")
    kpis([
        ("เงินเข้าทั้งปี", f"{fmt(ytot['in'])} ฿", "", "#2a78d6"),
        ("เงินออกทั้งปี", f"{fmt(ytot['out'])} ฿", "", "#eb6834"),
        ("กำไรทั้งปี", f"{fmt(ytot['profit'])} ฿", f"{ytot['count']} รายการ", "#16a34a", True),
    ])

    # กราฟกำไรรายเดือน (ซีรีส์เดียว สีเดียว เน้นเดือนที่เลือก)
    try:
        import altair as alt
        cdf = ms.copy()
        cdf["เดือน"] = cdf["label"]
        cdf["selected"] = cdf["month"] == month
        cdf["กำไร_txt"] = cdf["profit"].map(lambda v: f"{v:,.2f} ฿")
        cdf["เข้า_txt"] = cdf["in"].map(lambda v: f"{v:,.2f} ฿")
        cdf["ออก_txt"] = cdf["out"].map(lambda v: f"{v:,.2f} ฿")
        chart = (
            alt.Chart(cdf)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=26)
            .encode(
                x=alt.X("เดือน:N", sort=list(lg.TH_MONTHS), title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("profit:Q", title="กำไร (บาท)", axis=alt.Axis(format=",.0f", gridOpacity=0.4)),
                color=alt.condition("datum.selected", alt.value("#16a34a"), alt.value("#86c9a0")),
                tooltip=[alt.Tooltip("เดือน:N"), alt.Tooltip("count:Q", title="รายการ"),
                         alt.Tooltip("เข้า_txt:N", title="เงินเข้า"), alt.Tooltip("ออก_txt:N", title="เงินออก"),
                         alt.Tooltip("กำไร_txt:N", title="กำไร")],
            )
            .properties(height=260, title=f"กำไรรายเดือน ปี {year + 543}")
            .configure_view(strokeWidth=0)
        )
        stretch(st.altair_chart, chart)
    except Exception:
        st.bar_chart(ms.set_index("label")["profit"])

    ydf = df_all[df_all["year"] == year] if not df_all.empty else df_all
    piv = ydf.pivot_table(index="month", columns="cat", values="กำไร", aggfunc="sum", fill_value=0.0) \
        if not ydf.empty else pd.DataFrame()

    def cat_profit(m, c):
        return float(piv.loc[m, c]) if (m in piv.index and c in piv.columns) else 0.0

    table = pd.DataFrame({
        "เดือน": ms["month"].map(lambda m: lg.th_month(year, m)),
        "รายการ": ms["count"],
        "เงินเข้า": ms["in"], "เงินออก": ms["out"], "กำไร": ms["profit"],
    })
    for c in lg.CATEGORIES:
        table[f"กำไร · {c}"] = [cat_profit(m, c) for m in ms["month"]]
    total_row = {"เดือน": "รวมทั้งปี", "รายการ": ytot["count"], "เงินเข้า": ytot["in"],
                 "เงินออก": ytot["out"], "กำไร": ytot["profit"]}
    for c in lg.CATEGORIES:
        total_row[f"กำไร · {c}"] = float(table[f"กำไร · {c}"].sum())
    table = pd.concat([table, pd.DataFrame([total_row])], ignore_index=True)
    money_cols = [c for c in table.columns if c not in ("เดือน", "รายการ")]
    st.dataframe(table.style.format({c: "{:,.2f}" for c in money_cols}), hide_index=True, height=490)

    b1, b2 = st.columns(2)
    with b1:
        stretch(st.download_button, f"📥 ดาวน์โหลดสรุปปี {year + 543} (.csv)",
                data=table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"monthly_summary_{year}.csv", mime="text/csv")
    with b2:
        if stretch(st.button, "📤 อัปเดตแท็บ “สรุปรายเดือน” ใน Google Sheets",
                   help="เขียนตารางสรุป 12 เดือนของทุกปีลงแท็บแยก ใช้คิดภาษีได้ทันที"):
            rows_out = [["ปี (ค.ศ.)", "ปี (พ.ศ.)", "เดือน", "จำนวนรายการ", "เงินเข้า", "เงินออก", "กำไร"] + [f"กำไร · {c}" for c in lg.CATEGORIES]]
            for y in sorted(years):
                ys = lg.monthly_summary(df_all, y)
                ydf_y = df_all[df_all["year"] == y] if not df_all.empty else df_all
                pv = ydf_y.pivot_table(index="month", columns="cat", values="กำไร", aggfunc="sum", fill_value=0.0) \
                    if not ydf_y.empty else pd.DataFrame()

                def cp(m, c):
                    return round(float(pv.loc[m, c]), 2) if (m in pv.index and c in pv.columns) else 0.0

                for _, r in ys.iterrows():
                    mo = int(r["month"])
                    rows_out.append([y, y + 543, lg.TH_MONTHS_FULL[mo - 1], int(r["count"]),
                                     round(float(r["in"]), 2), round(float(r["out"]), 2), round(float(r["profit"]), 2)]
                                    + [cp(mo, c) for c in lg.CATEGORIES])
                rows_out.append([y, y + 543, "รวมทั้งปี", int(ys["count"].sum()), round(float(ys["in"].sum()), 2),
                                 round(float(ys["out"].sum()), 2), round(float(ys["profit"].sum()), 2)]
                                + [round(sum(cp(m, c) for m in range(1, 13)), 2) for c in lg.CATEGORIES])
            if db.write_monthly_summary(rows_out):
                st.success(f"✅ อัปเดตแท็บ “{db.MONTHLY_SHEET}” แล้ว")

st.divider()
if st.button("🚪 ออกจากระบบ", key="logout"):
    st.session_state.clear()
    st.rerun()
