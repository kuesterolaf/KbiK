import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# --- GOOGLE CONNECTION ---
@st.cache_resource
def get_gspread_client():
    s = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(
        {
            "type": s["type"],
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": s["private_key"],
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": s["auth_uri"],
            "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"],
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def load_data():
    client = get_gspread_client()
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(url)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    return pd.DataFrame(data), ws

try:
    df, worksheet = load_data()
except Exception as e:
    st.error("Ladefehler!")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("---")

st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    name = st.text_input("Name (Vorname Nachname):").strip()
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    auswahl = st.selectbox("Ergebnis:", [
        "-- Bitte wählen --",
        "30 min gelesen (2 Pkt)", 
        "60 min gelesen (4 Pkt)",
        "Buch bis 100 S. (5 Pkt)", 
        "Buch bis 200 S. (10 Pkt)", 
        "Buch über 200 S. (15 Pkt)"
    ])
    submit = st.form_submit_button("Speichern")

    if submit and name:
        # Check ob Name schon in anderem Team
        hist = df[df["Kind"].str.lower() == name.lower()]
        
        ok = True
        if not hist.empty:
            reg_team = hist["Team"].iloc[0]
            if reg_team != team:
                st.sidebar.error(f"Falsches Team! Registriert: {reg_team}")
                ok = False
        
        if ok:
            pkt = 0
            if "30 min" in auswahl: pkt = 2
            elif "60 min" in auswahl: pkt = 4
            elif "bis 100" in auswahl: pkt = 5
            elif "bis 200" in auswahl and "über" not in auswahl: pkt = 10
            elif "über 200" in auswahl: pkt = 15
            
            if pkt > 0:
                row = [datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", auswahl, pkt]
                try:
                    worksheet.append_row(row)
                    st.sidebar.success("Gespeichert!")
                    st.rerun()
                except:
                    st.sidebar.error("Fehler beim Schreiben!")
            else:
                st.sidebar.warning("Kategorie wählen!")
    elif submit:
        st.sidebar.warning("Name fehlt!")

# --- ANZEIGE ---
c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("🏆 Tabelle")
    if not df.empty:
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        rank = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
        st.table(rank.set_index("Team"))

with c2:
    st.subheader("📜 Letzte Aktivitäten")
    if not df.empty:
        st.dataframe(df.iloc[::-1].head(15), use_container_width=True)
