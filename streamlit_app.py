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

# Daten laden Funktion
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
st.markdown("<p style='text-align: center;'>Die große Leseliga-Meisterschaft</p>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: EINGABE ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintrag speichern")

    if submit and name:
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        neue_zeile = [datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", ergebnis, pkt]
        
        try:
            worksheet.append_row(neue_zeile)
            st.sidebar.success(f"✅ Tor für {name}!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Fehler beim Speichern.")

# --- HAUPTBEREICH: TABELLE & STATISTIK ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🏆 Aktuelle Tabelle")
    if not df.empty:
        # Punkte sicherstellen
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        ranking = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
        st.table(ranking.set_index("Team"))
    else:
        st.info("Noch keine Daten vorhanden.")

with col2:
    st.subheader("📜 Letzte Aktivitäten")
    if not df.empty:
        # Die letzten 10 Einträge (umgekehrt sortiert)
        st.dataframe(df.iloc[::-1].head(10), use_container_width=True)

st.markdown("---")
st.caption("⚽ Viel Erfolg beim Lesen und Kicken!")
