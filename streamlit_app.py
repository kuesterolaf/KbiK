import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# VERBINDUNG HERSTELLEN (Die robuste Methode)
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

try:
    client = get_gspread_client()
    # Öffnet das Sheet über die URL aus deinen Secrets
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    worksheet = sh.get_worksheet(0) # Das erste Tabellenblatt
    
    # Daten laden
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error("Verbindung zum Google Sheet gescheitert!")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

st.title("⚽ Kicken beginnt im Kopf")

# --- EINGABE ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintrag speichern")

    if submit and name:
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        # Neue Zeile als Liste (muss zur Reihenfolge im Sheet passen!)
        neue_zeile = [datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", ergebnis, pkt]
        
        try:
            worksheet.append_row(neue_zeile)
            st.sidebar.success("✅ Erfogreich im Google Sheet gespeichert!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("❌ Schreibfehler!")
            st.sidebar.code(str(e))

# --- TABELLE ---
if not df.empty:
    st.subheader("🏆 Aktuelle Tabelle")
    # Sicherstellen, dass Punkte Zahlen sind
    df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    ranking = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
    st.table(ranking)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten im Sheet gefunden.")
