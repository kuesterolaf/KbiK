import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- SEITEN-LAYOUT ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# --- VERBINDUNG ZU GOOGLE SHEETS ---
@st.cache_resource
def get_gspread_client():
    s = st.secrets["connections"]["gsheets"]
    credentials = Credentials.from_service_account_info(
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
    return gspread.authorize(credentials)

def load_data():
    client = get_gspread_client()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    worksheet = sh.get_worksheet(0)
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

try:
    df, worksheet = load_data()
except Exception as e:
    st.error("Fehler beim Laden der Daten.")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- HEADER ---
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: EINGABE ---
st.sidebar.header("👟 Spielerkabine")

with st.sidebar.form("input_form", clear_on_submit=True):
    # Name als Textfeld
    eingabe_name = st.text_input("Vorname und Nachname des Kindes:").strip()
    
    # Team als Dropdown (wie gewünscht)
    team_liste = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
    eingabe_team = st.selectbox("Wähle dein Team:", team_liste)
    
    ergebnis = st.selectbox("Was wurde heute erreicht?", [
        "-- Lesezeit --",
        "30 min gelesen (2 Pkt)", 
        "60 min gelesen (4 Pkt)",
        "-- Buch abgeschlossen --",
        "Buch bis 100 Seiten (5 Pkt)", 
        "Buch bis 200 Seiten (10 Pkt)", 
        "Buch über 200 Seiten (15 Pkt)"
    ])
    
    submit = st.form_submit_button("Eintrag speichern")

    if submit and eingabe_name:
        # CHECK: Existiert der Name schon mit einem anderen Team?
        # Wir vergleichen alles in Kleinbuchstaben, um Tippfehler (Groß/Klein) zu ignorieren
        historie = df[df["Kind"].str.lower() == eingabe_name.lower()]
        
        zugriff_erlaubt = True
        if not historie.empty:
            festgelegtes_team = historie["Team"].iloc[0]
            if festgelegtes_team != eingabe_team:
                st.sidebar.error(f"🚫 Stopp! {eingabe_name} ist bereits im Team **{festgelegtes_team}**. Du kannst nicht für ein anderes Team punkten!")
                zugriff_erlaubt = False
        
        if zugriff_erlaubt:
            # Punkte-Zuweisung
            if "30 min" in ergebnis: pkt = 2
            elif "60 min" in ergebnis: pkt = 4
            elif "bis 100" in ergebnis: pkt =
