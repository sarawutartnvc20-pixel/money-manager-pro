import html
import os
import importlib

import pandas as pd
import streamlit as st

# โมดูลภายในโปรเจกต์
import logic as lg
import sheets_client as db
import image_manager as im
import slip_reader as sr

for _m in (lg, db, im, sr):
    try:
        importlib.reload(_m)
    except Exception:
        pass

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
    """แสดงรูปสลิป รองรับทั้ง Cloudinary URL และ path ในเครื่อง"""
    if slip_val is None or str(slip_val).strip() in ("", "nan"):
        st.caption(f"⚪ ไม่มี{caption}")
        return
    slip_str = str(slip_val).strip()
    if slip_str.startswith(("http://", "https://")):
        st.image(slip_str, caption=caption, width=220)
        st.markdown(f"[🔍 เปิดรูปเต็ม]({slip_str})")
    elif os.path.exists(slip_str):
        st.image(slip_str, caption=caption, width=220)
    else:
        st.caption(f"📁 {caption}: `{os.path.basename(slip_str)}` (ไฟล์อยู่ในเครื่องเดิม)")


def slip_reads(files, do_read: bool, tag: str):
    """แสดง thumbnail + ยอดที่ AI อ่านได้ คืนค่า list[(hash, amount|None)]"""
    out = []
    for i, f in enumerate(files):
        h = sr.file_hash(f)
        st.image(f, width=170)
        if not do_read:
            out.append((h, None))
            continue
        with st.spinner("🤖 AI กำลังอ่านยอด..."):
            amount, err = sr.read_amount(f)
        if amount:
            st.markdown(f'<span class="mm-amt ok">✓ อ่านได้ {fmt(amount)} ฿</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="mm-amt no">อ่านยอดไม่ได้ — กรอกเองด้านล่าง</span>', unsafe_allow_html=True)
            if err:
                st.caption(f"รายละเอียด: {err[:160]}")
            if st.button("🔄 ให้ AI อ่านใหม่", key=f"reread_{tag}_{i}_{h[:8]}"):
                sr.forget(f)
                st.rerun()
        out.append((h, amount))
    return out


def apply_reads(reads, state_key: str, applied_key: str):
    """เอายอดจากสลิปไปใส่ช่องกรอก (ครั้งเดียวต่อชุดสลิป ผู้ใช้แก้เองได้)"""
    known = [a for _, a in reads if a]
    if not known:
        return
    sig = tuple((h, a) for h, a in reads)
    # ใส่ยอดเมื่อสลิปเปลี่ยน หรือช่องกรอกถูกรีเซ็ต (เช่น สลับประเภทบริการไปมา)
    if st.session_state.get(applied_key) != sig or state_key not in st.session_state:
        st.session_state[state_key] = float(round(sum(known), 2))
        st.session_state[applied_key] = sig


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

        # ---------- Step 2 ----------
        with st.container(border=True):
            step(2, "อัปโหลดสลิป", "AI อ่านยอดและสรุปให้ทันที")
            ai_ok = sr.is_ready()
            auto_ai = st.toggle("🤖 อ่านยอดจากสลิปอัตโนมัติ (Gemini)", value=ai_ok, disabled=not ai_ok,
                                key=K("auto_ai"),
                                help=None if ai_ok else "ใส่ GEMINI_API_KEY ใน secrets.toml ก่อน")
            has_out = service != "เช่าจอดูบอล"
            slot_in, slot_out = (st.columns(2) if has_out else (st.container(), None))

            with slot_in:
                st.markdown("**💚 สลิปเงินเข้า** <span class='mm-tag'>สูงสุด 2 ใบ</span>", unsafe_allow_html=True)
                in_files = st.file_uploader("สลิปเงินเข้า", type=IMG_TYPES, accept_multiple_files=True,
                                            key=K("in_files"), label_visibility="collapsed") or []
                if len(in_files) > 2:
                    st.warning("ใช้ได้สูงสุด 2 ใบ ระบบจะใช้ 2 ใบแรก")
                    in_files = in_files[:2]
                # การแลกไอดีใช้เรทตายตัว ไม่ต้องอ่านยอดเข้า (ประหยัดโควต้า AI)
                in_reads = slip_reads(in_files, auto_ai and service != "การแลกไอดี", "in")

            out_file, out_reads = None, []
            if has_out:
                with slot_out:
                    st.markdown("**❤️ สลิปเงินออก** <span class='mm-tag'>ถ้าโอนให้ผู้ขายแล้ว</span>",
                                unsafe_allow_html=True)
                    out_file = st.file_uploader("สลิปเงินออก", type=IMG_TYPES, key=K("out_file"),
                                                label_visibility="collapsed")
                    out_reads = slip_reads([out_file] if out_file else [], auto_ai, "out")

            if service != "การแลกไอดี":
                apply_reads(in_reads, K("income"), K("in_applied"))
            apply_reads(out_reads, K("out_amount"), K("out_applied"))

        # ---------- Step 3 ----------
        with st.container(border=True):
            step(3, "ยอดเงิน & รายละเอียด")
            st.session_state.setdefault(K("income"), 0.0)
            st.session_state.setdefault(K("out_amount"), 0.0)
            is_yok = is_no_note = False
            include_fee = False
            exchange_rate = 60
            out_amount = 0.0

            if service == "รับกลางไอดี":
                income = st.number_input("💰 ยอดเงินเข้าทั้งหมด (บาท)", min_value=0.0, step=10.0,
                                         format="%.2f", key=K("income"))
                mode = st.radio(
                    "ยอดที่ลูกค้าโอนมา",
                    ["exclude", "include"], horizontal=True, key=K("fee_mode"),
                    format_func=lambda m: "ยังไม่รวมค่ากลาง" if m == "exclude" else "รวมค่ากลางแล้ว",
                    help="ยังไม่รวม: เทียบเรทจากยอดที่โอนมาเลย (1,491 → เรท 80)\n\n"
                         "รวมแล้ว: หักค่ากลาง/ค่าโยกออกก่อนแล้วค่อยเทียบเรท (1,500 → 1,440 → เรท 60)",
                )
                include_fee = mode == "include"
                c1, c2 = st.columns(2)
                is_yok = c1.checkbox(f"🔄 โยกเฟส/โยกเมล (+{fmt(lg.YOK_FEE)})", key=K("yok"))
                is_no_note = c2.checkbox(f"✍️ ลืมเขียนโน๊ต (+{fmt(lg.NO_NOTE_FEE)})", key=K("nonote"))
                out_amount = st.number_input("💸 ยอดโอนออกจริง (ใส่ 0 ถ้ายังไม่ได้โอน ระบบจะคำนวณให้)",
                                             min_value=0.0, step=10.0, format="%.2f", key=K("out_amount"))
                note = st.text_input("📌 ชื่อลูกค้า / รหัสไอดี", key=K("note"),
                                     placeholder="เช่น FC Mobile บัญชีคุณบาส")
                calc = lg.compute_middleman(income, is_yok, is_no_note, include_fee, out_amount)

            elif service == "การแลกไอดี":
                exchange_rate = st.radio("เรทค่าแลกไอดี", [60, 200], horizontal=True, key=K("ex_rate"),
                                         format_func=lambda x: f"🏷️ {x} บาท")
                c1, c2 = st.columns(2)
                is_yok = c1.checkbox(f"🔄 โยกเฟส/โยกเมล (+{fmt(lg.YOK_FEE)})", key=K("yok_ex"))
                is_no_note = c2.checkbox(f"✍️ ลืมเขียนโน๊ต (+{fmt(lg.NO_NOTE_FEE)})", key=K("nonote_ex"))
                out_amount = st.number_input("💸 ยอดโอนออก (ถ้ามี)", min_value=0.0, step=10.0,
                                             format="%.2f", key=K("out_amount"))
                note = st.text_input("📌 รายละเอียด", key=K("note"),
                                     placeholder="เช่น แลกบัญชี A กับ บัญชี B")
                calc = lg.compute_exchange(exchange_rate, is_yok, is_no_note, out_amount)
                income = calc.income

            else:
                income = st.number_input("💰 ยอดเงินเข้าทั้งหมด (บาท)", min_value=0.0, step=10.0,
                                         format="%.2f", key=K("income"))
                note = st.text_input("📌 ช่องที่เช่า / แมตช์", key=K("note"),
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
            if is_yok:
                rows.append(f'<div class="mm-row sm"><span>ค่าโยกเฟส/เมล</span><span>{fmt(lg.YOK_FEE)} ฿</span></div>')
            if is_no_note:
                rows.append(f'<div class="mm-row sm"><span>ลืมเขียนโน๊ต</span><span>{fmt(lg.NO_NOTE_FEE)} ฿</span></div>')

            if calc.income > 0:
                if fr.warning:
                    alt = f" (ถ้าคิด {fmt(fr.alt_fee)} ฿ ยอดไอดีจะเกินเรท)" if fr.alt_fee else ""
                    notes.append(("warn", f"⚠️ {fr.warning}: ใช้ {fmt(fr.base_fee)} ฿{alt}"))
                if calc.from_slip:
                    if abs(calc.diff) < 0.01:
                        parts = [f"ค่ากลาง {fmt(calc.base_fee)}"]
                        if is_yok: parts.append(f"โยก {fmt(lg.YOK_FEE)}")
                        if is_no_note: parts.append(f"โน๊ต {fmt(lg.NO_NOTE_FEE)}")
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
                        if not is_yok and abs(calc.diff - lg.YOK_FEE) < 0.01:
                            hints.append("ส่วนต่างเท่าค่าโยก 40 — ลืมติ๊กโยกเฟส/เมลหรือเปล่า?")
                        if not is_no_note and abs(calc.diff - lg.NO_NOTE_FEE) < 0.01:
                            hints.append("ส่วนต่างเท่าค่าลืมโน๊ต 5 — ลืมติ๊กหรือเปล่า?")
                        if hints:
                            msg += "<br>💡 " + "<br>💡 ".join(hints)
                        notes.append(("warn", msg))
                else:
                    notes.append(("info", f"ℹ️ ต้องโอนให้ผู้ขาย <b>{fmt(calc.expense)} ฿</b> "
                                          f"— อัปโหลดสลิปเงินออกเพื่อเช็กยอดอัตโนมัติ"))

        elif service == "การแลกไอดี":
            rows.append(f'<div class="mm-row sm"><span>เรทค่าแลกไอดี</span><span>{fmt(calc.base_fee)} ฿</span></div>')
            if calc.extra_fee:
                rows.append(f'<div class="mm-row sm"><span>ค่าบริการเสริม</span><span>{fmt(calc.extra_fee)} ฿</span></div>')
            rows.append(f'<div class="mm-row"><span>💸 ยอดโอนออก</span><b>{fmt(calc.expense)} ฿</b></div>')
        else:
            rows.append('<div class="mm-row"><span>💸 ยอดโอนออก</span><b>0 ฿</b></div>')

        note_html = "".join(f'<div class="mm-note {k}">{m}</div>' for k, m in notes)
        st.markdown(
            f'<div class="mm-card"><h4>{SERVICE_ICON[service]} สรุปรายการ · {esc(service)}</h4>'
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
                    new_id = db.get_next_id(db.load_data(fresh=True))
                    in1 = in_files[0] if len(in_files) > 0 else None
                    in2 = in_files[1] if len(in_files) > 1 else None
                    url_in1 = im.upload_image(in1, subfolder="incoming", prefix=f"{new_id}_in1") if in1 else ""
                    url_in2 = im.upload_image(in2, subfolder="incoming", prefix=f"{new_id}_in2") if in2 else ""
                    url_out = im.upload_image(out_file, subfolder="outgoing", prefix=f"{new_id}_out") if out_file else ""

                    parts = []
                    if service == "รับกลางไอดี":
                        parts.append(f"ค่ากลาง {fmt(calc.base_fee)}")
                        if include_fee:
                            parts.append("ยอดรวมค่ากลางแล้ว")
                    if service == "การแลกไอดี":
                        parts.append(f"เรทแลก {exchange_rate}฿")
                    if service in ("รับกลางไอดี", "การแลกไอดี"):
                        if is_yok: parts.append(f"โยกไอดี (+{fmt(lg.YOK_FEE)})")
                        if is_no_note: parts.append(f"ลืมโน๊ต (+{fmt(lg.NO_NOTE_FEE)})")
                    if service == "รับกลางไอดี" and calc.from_slip and abs(calc.diff or 0) >= 0.01:
                        parts.append(f"ส่วนต่างจากเรท {calc.diff:+,.2f}")
                    if note.strip():
                        parts.append(note.strip())

                    ok = db.append_row({
                        "ID": new_id,
                        "วันที่": lg.now_th().strftime("%Y-%m-%d %H:%M"),
                        "ประเภท": service,
                        "รายละเอียด": " | ".join(parts),
                        "ยอดเข้า": round(calc.income, 2),
                        "ยอดออก": round(calc.expense, 2),
                        "กำไร": round(calc.profit, 2),
                        "สถานะโอนออก": "โอนแล้ว",
                        "สลิปเข้า": url_in1,
                        "สลิปเข้า 2": url_in2,
                        "สลิปออก": url_out,
                    })
                if ok:
                    st.session_state["form_nonce"] = nonce + 1   # ล้างฟอร์มและสลิป
                    flash(f"🎉 บันทึก #{new_id} ({service}) เข้า {fmt(calc.income)} ฿ · กำไร {fmt(calc.profit)} ฿ เรียบร้อย",
                          balloons=True)
                    st.rerun()
                else:
                    st.error("❌ ส่งข้อมูลไป Google Sheets ไม่สำเร็จ")

        with st.expander("📋 ตารางเรทค่ากลาง"):
            lo = 0
            lines = []
            for limit, fee in lg.FEE_TIERS:
                lines.append(f"| {fmt(lo)} – {fmt(limit)} | {fmt(fee)} ฿ |")
                lo = limit + 1
            lines.append(f"| {fmt(lo)} ขึ้นไป | {int(lg.PERCENT_RATE * 100)}% |")
            st.markdown("| ยอดไอดี | ค่ากลาง |\n|---|---|\n" + "\n".join(lines) +
                        f"\n\nค่าโยกเฟส/โยกเมล **+{fmt(lg.YOK_FEE)}** (ไม่รวมค่ากลาง) · ลืมเขียนโน๊ต **+{fmt(lg.NO_NOTE_FEE)}**")


# ============================================================
# TAB 2 : ประวัติรายวัน
# ============================================================
def record_card(row, key_prefix: str):
    rid = int(row["ID"])
    t = row["dt"].strftime("%H:%M") if pd.notna(row["dt"]) else "--:--"
    typ = str(row["ประเภท"])
    title = (f"{SERVICE_ICON.get(typ, '•')} #{rid} · {t} · {typ} · เข้า {fmt(row['ยอดเข้า'])} · "
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
                if st.button("ยืนยันลบ", type="primary", key=f"{key_prefix}_del_{rid}"):
                    if db.delete_row(rid):
                        flash(f"🗑️ ลบรายการ #{rid} แล้ว")
                        st.rerun()
                    else:
                        st.error("ลบไม่สำเร็จ")

        i1, i2, i3 = st.columns(3)
        with i1:
            render_slip_item(row["สลิปเข้า"], "สลิปเข้า 1")
        with i2:
            render_slip_item(row["สลิปเข้า 2"], "สลิปเข้า 2")
        with i3:
            render_slip_item(row["สลิปออก"], "สลิปออก")

        if st.toggle("📷 แนบ/เปลี่ยนสลิป", key=f"{key_prefix}_tg_{rid}"):
            u1, u2, u3 = st.columns(3)
            r1 = u1.file_uploader("สลิปเข้า 1", type=IMG_TYPES, key=f"{key_prefix}_u1_{rid}")
            r2 = u2.file_uploader("สลิปเข้า 2", type=IMG_TYPES, key=f"{key_prefix}_u2_{rid}")
            r3 = u3.file_uploader("สลิปออก", type=IMG_TYPES, key=f"{key_prefix}_u3_{rid}")
            if st.button("💾 บันทึกสลิป", key=f"{key_prefix}_save_{rid}"):
                changed = False
                for f, colname, sub, pre in ((r1, "สลิปเข้า", "incoming", "in1"),
                                             (r2, "สลิปเข้า 2", "incoming", "in2"),
                                             (r3, "สลิปออก", "outgoing", "out")):
                    if f:
                        url = im.upload_image(f, subfolder=sub, prefix=f"{rid}_{pre}")
                        if url and db.update_cell(rid, colname, url):
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
        f1, f2 = st.columns([1.6, 1])
        q = f1.text_input("🔍 ค้นหาทุกวัน (ID / ชื่อลูกค้า / รายละเอียด)", key="hist_q", placeholder="พิมพ์เพื่อค้นหา...")
        ftype = f2.selectbox("ประเภท", ["ทั้งหมด"] + lg.SERVICES, key="hist_type")

        base = df_all if ftype == "ทั้งหมด" else df_all[df_all["ประเภท"] == ftype]

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
                for _, r in day_df.sort_values(["dt", "ID"], ascending=False).iterrows():
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
        export = df_all.drop(columns=["dt", "day", "year", "month"], errors="ignore").sort_values("ID")
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
    s_cols = st.columns(3)
    for col, svc in zip(s_cols, lg.SERVICES):
        t = lg.totals(mdf[mdf["ประเภท"] == svc] if not mdf.empty else None)
        col.markdown(
            f'<div class="mm-svc" style="border-top:3px solid {SERVICE_ACC[svc]}">'
            f'<div class="t">{SERVICE_ICON[svc]} {svc}</div>'
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

    table = pd.DataFrame({
        "เดือน": ms["month"].map(lambda m: lg.th_month(year, m)),
        "รายการ": ms["count"],
        "เงินเข้า": ms["in"], "เงินออก": ms["out"], "กำไร": ms["profit"],
    })
    total_row = pd.DataFrame([{"เดือน": "รวมทั้งปี", "รายการ": ytot["count"], "เงินเข้า": ytot["in"],
                               "เงินออก": ytot["out"], "กำไร": ytot["profit"]}])
    table = pd.concat([table, total_row], ignore_index=True)
    st.dataframe(table.style.format({"เงินเข้า": "{:,.2f}", "เงินออก": "{:,.2f}", "กำไร": "{:,.2f}"}),
                 hide_index=True, height=490)

    b1, b2 = st.columns(2)
    with b1:
        stretch(st.download_button, f"📥 ดาวน์โหลดสรุปปี {year + 543} (.csv)",
                data=table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"monthly_summary_{year}.csv", mime="text/csv")
    with b2:
        if stretch(st.button, "📤 อัปเดตแท็บ “สรุปรายเดือน” ใน Google Sheets",
                   help="เขียนตารางสรุป 12 เดือนของทุกปีลงแท็บแยก ใช้คิดภาษีได้ทันที"):
            rows_out = [["ปี (ค.ศ.)", "ปี (พ.ศ.)", "เดือน", "จำนวนรายการ", "เงินเข้า", "เงินออก", "กำไร"]]
            for y in sorted(years):
                ys = lg.monthly_summary(df_all, y)
                for _, r in ys.iterrows():
                    rows_out.append([y, y + 543, lg.TH_MONTHS_FULL[int(r["month"]) - 1], int(r["count"]),
                                     round(float(r["in"]), 2), round(float(r["out"]), 2), round(float(r["profit"]), 2)])
                rows_out.append([y, y + 543, "รวมทั้งปี", int(ys["count"].sum()), round(float(ys["in"].sum()), 2),
                                 round(float(ys["out"].sum()), 2), round(float(ys["profit"].sum()), 2)])
            if db.write_monthly_summary(rows_out):
                st.success(f"✅ อัปเดตแท็บ “{db.MONTHLY_SHEET}” แล้ว")
