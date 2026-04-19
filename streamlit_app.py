import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- BASIS KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# --- VERBINDUNG ZUM GOOGLE SHEET ---
@st.cache_resource
def get_gspread_client():
    s = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(
        {
            "type": s["type"], "project_id": s["project_id"], "private_key_id": s["private_key_id"],
            "private_key": s["private_key"], "client_email": s["client_email"], "client_id": s["client_id"],
            "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
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
except Exception:
    st.error("Datenverbindung unterbrochen!")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- HAUPTSEITE DESIGN ---
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: REGISTRIERUNG & EINGABE ---
st.sidebar.header("👟 Spieler Check-in")

# Schritt 1: Wer meldet sich an?
name_input = st.sidebar.text_input("Vor- und Nachname des Kindes:").strip()
team_input = st.sidebar.selectbox("Wähle dein Team:", ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])

if name_input and team_input != "-- Bitte wählen --":
    # Prüfung gegen vorhandene Daten
    historie = df[df["Kind"].str.lower() == name_input.lower()]
    
    zugriff_erlaubt = True
    if not historie.empty:
        registriertes_team = historie["Team"].iloc[0]
        if registriertes_team != team_input:
            st.sidebar.error(f"🚫 Stopp! {name_input} gehört zum Team '{registriertes_team}'.")
            zugriff_erlaubt = False
        else:
            st.sidebar.success(f"✅ Check-in erfolgreich: {team_input}")
    else:
        st.sidebar.info(f"🆕 Neuer Spieler! Du wirst für '{team_input}' registriert.")

    # Schritt 2: Punkte nur bei Erfolg freischalten
    if zugriff_erlaubt:
        st.sidebar.markdown("---")
        with st.sidebar.form("punkte_form", clear_on_submit=True):
            ergebnis = st.selectbox("Was wurde heute geschafft?", [
                "-- Bitte wählen --",
                "30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)",
                "Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"
            ])
            submit = st.form_submit_button("Ergebnis speichern")

            if submit:
                # Punkte-Logik
                pkt = 0
                if "30 min" in ergebnis: pkt = 2
                elif "60 min" in ergebnis: pkt = 4
                elif "bis 100" in ergebnis: pkt = 5
                elif "bis 200" in ergebnis and "über" not in ergebnis: pkt = 10
                elif "über 200" in ergebnis: pkt = 15
                
                if pkt > 0:
                    neue_zeile = [datetime.now().strftime("%d.%m.%Y"), name_input, team_input, "Lesen", ergebnis, pkt]
                    try:
                        worksheet.append_row(neue_zeile)
                        st.sidebar.success("⚽ Tooor! Punkte wurden gutgeschrieben.")
                        st.rerun()
                    except:
                        st.sidebar.error("Fehler beim Speichern!")
                else:
                    st.sidebar.warning("Bitte wähle ein Ergebnis aus!")
else:
    st.sidebar.warning("Bitte Name und Team eingeben, um fortzufahren.")

# --- TABELLE & AKTIVITÄTEN ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🏆 Aktuelle Tabelle")
    if not df.empty:
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        rank = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
        st.table(rank.set_index("Team"))

with col2:
    st.subheader("📜 Letzte Leistungen")
    if not df.empty:
        st.dataframe(df.iloc[::-1].head(10), use_container_width=True)
