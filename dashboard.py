import streamlit as st
import requests
import nepali_datetime as nd
import datetime
import json

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Class Progress Tracker", layout="wide")
st.title("📊 Class Progress Tracker")

# --- Subjects Progress ---
st.header("Subjects")
syllabi = requests.get(f"{API_BASE}/syllabi").json()

for subject in syllabi:
    name = subject["subject"]
    progress = requests.get(f"{API_BASE}/progress/{name}").json()
    pct = progress["progress_percent"]
    logged = progress["logged"]
    total = progress["total"]

    # Card-style container
    st.markdown(
        f"""
        <div style="
            background-color:#f0f4f8;
            border-radius:12px;
            padding:20px;
            margin-bottom:20px;
            box-shadow:0 4px 8px rgba(0,0,0,0.05);
        ">
            <h3 style="margin-top:0; font-size:22px; color:#2c3e50;">
                📘 <b>{name}</b>
            </h3>
            <div style="margin-top:10px; margin-bottom:10px;">
                <progress value="{pct}" max="100" style="width:100%; height:20px;"></progress>
                <p style="font-size:14px; color:#555;">Progress: {logged}/{total} sessions</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Logbook icon expander embedded right after the card
    with st.expander("📖 Logbook", expanded=False):
        logbook = requests.get(f"{API_BASE}/logbook/{name}").json()
        st.table(logbook)

# --- Manual Logging ---
st.header("Manual Logging")
if st.button("➕ Log a Session"):
    with st.expander("Fill Session Details"):
        subject = st.selectbox("Subject", [s["subject"] for s in syllabi])
        section = st.selectbox("Section", ["theory", "practical"])
        date_bs = st.text_input("Date (BS)", str(nd.date.today()))
        time_from = st.text_input("Time From", "10:50")
        time_to = st.text_input("Time To", "11:40")
        if st.button("Submit Log"):
            payload = {
                "subject": subject,
                "section": section,
                "date_bs": date_bs,
                "time_from": time_from,
                "time_to": time_to
            }
            res = requests.post(f"{API_BASE}/log_manual", json=payload)
            st.success(res.json())

# --- Backfill ---
st.header("Backfill All Subjects")
with st.form("backfill_form"):
    start_date = st.text_input("Start Date (BS)", "2082-07-12")
    end_date = st.text_input("End Date (BS)", "2082-08-19")
    holidays = st.text_input("Holidays (comma-separated BS dates)", "2082-07-15,2082-08-01")
    backfill_submit = st.form_submit_button("Run Backfill")
    if backfill_submit:
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "holidays": holidays.split(",")
        }
        res = requests.post(f"{API_BASE}/backfill_all", json=payload)
        st.success(res.json())

import streamlit as st

st.markdown(
    """
    <link rel="manifest" href="./manifest.json">
    <script>
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('./service-worker.js');
      }
    </script>
    """,
    unsafe_allow_html=True
)

# --- Today's Classes ---
today_bs = str(nd.date.today())
weekday_name = nd.date.today().strftime("%A")  # e.g. "Thursday"

# Fetch routine safely
routine_raw = requests.get(f"{API_BASE}/routine").json()
if isinstance(routine_raw, str):
    routine = json.loads(routine_raw)
elif isinstance(routine_raw, dict):
    routine = routine_raw.get("routine", [])
elif isinstance(routine_raw, list):
    routine = routine_raw
else:
    routine = []

today_routine = [entry for entry in routine if isinstance(entry, dict) and entry.get("day") == weekday_name]

# Top bar: Holiday button
col1, col2 = st.columns([4, 1])
col1.header("Today's Classes")
holiday = col2.button("🏖️ Mark Today as Holiday", use_container_width=True)

if holiday:
    st.warning("Holiday marked — no classes will be logged today.")
else:
    now = datetime.datetime.now().time()

    for entry in today_routine:
        subject = entry.get("subject")
        section = entry.get("section")
        time_from = datetime.datetime.strptime(entry.get("time_from"), "%H:%M").time()
        time_to = datetime.datetime.strptime(entry.get("time_to"), "%H:%M").time()

        # Card-style container for each class
        st.markdown(
            f"""
            <div style="
                background-color:#ffffff;
                border-radius:12px;
                padding:20px;
                margin-bottom:20px;
                box-shadow:0 4px 8px rgba(0,0,0,0.1);
            ">
                <h3 style="margin-top:0; font-size:20px; color:#2c3e50;">
                    📘 <b>{subject}</b> ({section})
                </h3>
                <p style="font-size:16px; color:#555; margin:5px 0;">
                    ⏰ {entry.get('time_from')} – {entry.get('time_to')}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Highlight current class
        if time_from <= now <= time_to:
            st.markdown(
                f"<div style='background-color:#ffeb3b;padding:15px;font-size:18px;font-weight:bold;text-align:center;border-radius:8px;'>"
                f"⏰ Current Class: {subject} ({section}) {entry.get('time_from')}–{entry.get('time_to')}"
                f"</div>", unsafe_allow_html=True
            )

        # After class ends, show toast + confirmation button (only once per class)
        if now > time_to:
            toast_key = f"{subject}_{time_from}"
            if toast_key not in st.session_state or st.session_state[toast_key] is False:
                st.toast(f"Class {subject} ({section}) {entry.get('time_from')}–{entry.get('time_to')} needs confirmation!")
                st.session_state[toast_key] = False

            if st.button(f"✅ Confirm {subject} ({section}) {entry.get('time_from')}–{entry.get('time_to')} Completed", use_container_width=True):
                payload = {
                    "subject": subject,
                    "section": section,
                    "date_bs": today_bs,
                    "time_from": entry.get("time_from"),
                    "time_to": entry.get("time_to")
                }
                res = requests.post(f"{API_BASE}/log_manual", json=payload)
                st.success(f"Logged {subject} for {today_bs}")
                st.session_state[toast_key] = True