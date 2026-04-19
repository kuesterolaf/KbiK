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
    st.error("Daten konnten nicht geladen werden!")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- UI DESIGN ---
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: DER NEUE CHECK-IN PROZESS ---
st.sidebar.header("👟 Spieler Check-in")

# 1. Name und Team eingeben
name = st.sidebar.text_input("Vor- und Nachname des Kindes:").strip()
team = st.sidebar.selectbox("Wähle das Team:", ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])

if name and team != "-- Bitte wählen --":
    # Prüfung der Identität
    historie = df[df["Kind"].str.lower() == name.lower()]
    
    status_ok = True
    if not historie.empty:
        registriertes_team = historie["Team"].iloc[0]
        if registriertes_team != team:
            st.sidebar.error(f"🚫 Fehler: {name} ist bereits im Team '{registriertes_team}' registriert!")
            status_ok = False
        else:
            st.sidebar.success(f"✅ Willkommen zurück, Spieler von {team}!")
    else:
        st.sidebar.info(f"🆕 Neuer Spieler erkannt! Du wirst dem Team '{team}' zugeordnet.")

    # Nur wenn alles passt, erscheint das Punkte-Formular
    if status_ok:
        st.sidebar.markdown("---")
        with st.sidebar.form("punkte_form", clear_on_submit=True):
            auswahl = st.selectbox("Was hast du geschafft?", [
                "-- Bitte wählen --",
                "30 min gelesen (2 Pkt)", 
                "60 min gelesen (4 Pkt)",
                "Buch bis 100 S. (5 Pkt)", 
                "Buch bis 200 S. (10 Pkt)", 
                "Buch über 200 S. (15 Pkt)"
            ])
            submit = st.form_submit_button("Punkte eintragen")

            if submit:
                pkt = 0
                if "30 min" in auswahl: pkt = 2
                elif "60 min" in auswahl: pkt = 4
                elif "bis 100" in auswahl: pkt = 5
                elif "bis 200" in auswahl and "über" not in auswahl: pkt = 10
                elif "über 200" in auswahl: pkt = 15
                
                if pkt > 0:
                    neue_zeile = [datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", auswahl, pkt]
                    try:
                        worksheet.append_row(neue_zeile)
                        st.sidebar.success("⚽ Treffer versenkt! Punkte gespeichert.")
                        st.rerun()
                    except:
                        st.sidebar.error("Fehler beim Speichern!")
                else:
                    st.sidebar.warning("Wähle eine Leistung!")
else:
    st.sidebar.info("Bitte gib Namen und Team ein, um Punkte zu melden.")

# --- ANZEIGE: TABELLE ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🏆 Tabelle")
    if not df.empty:
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        rank = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
        st.table(rank.set_index("Team"))

with col2:
    st.subheader("📜 Letzte Aktivitäten")
    if not df.empty:
        st.dataframe(df.iloc[::-1].head(15), use_container_width=True)
