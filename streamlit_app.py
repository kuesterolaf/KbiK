import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
PUNKTE_LIMIT_LESEN_WOCHE = 20

# --- GOOGLE CONNECTION ---
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
    df = pd.DataFrame(data)
    if not df.empty:
        # Datum umwandeln für Wochen-Check
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        # Punkte numerisch machen
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

try:
    df, worksheet = load_data()
except Exception:
    st.error("Datenverbindung unterbrochen!")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- UI ---
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: CHECK-IN ---
st.sidebar.header("👟 Spieler Check-in")
name_input = st.sidebar.text_input("Vor- und Nachname:").strip()
team_input = st.sidebar.selectbox("Team:", ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])

if name_input and team_input != "-- Bitte wählen --":
    # 1. Team-Check
    historie = df[df["Kind"].str.lower() == name_input.lower()]
    zugriff_ok = True
    
    if not historie.empty:
        reg_team = historie["Team"].iloc[0]
        if reg_team != team_input:
            st.sidebar.error(f"🚫 {name_input} spielt bei {reg_team}!")
            zugriff_ok = False
    
    if zugriff_ok:
        # 2. Wochen-Punkte Check NUR FÜR TYP "Lesen"
        jetzt = datetime.now()
        aktuelle_kw = jetzt.isocalendar()[1]
        aktuelles_jahr = jetzt.isocalendar()[0]
        
        # Wir filtern nur die Einträge vom Typ "Lesen" in der aktuellen Woche
        lese_punkte_woche = 0
        if not historie.empty and 'KW' in df.columns:
            lese_punkte_woche = df[
                (df["Kind"].str.lower() == name_input.lower()) & 
                (df["KW"] == aktuelle_kw) & 
                (df["Jahr"] == aktuelles_jahr) &
                (df["Typ"] == "Lesen") # <--- WICHTIG: Nur Lesen wird gedeckelt
            ]["Punkte"].sum()

        st.sidebar.info(f"Lesepunkte diese Woche: {int(lese_punkte_woche)} / {PUNKTE_LIMIT_LESEN_WOCHE}")

        if lese_punkte_woche >= PUNKTE_LIMIT_LESEN_WOCHE:
            st.sidebar.warning("📖 Leselimit erreicht! Du kannst diese Woche nur noch Bonus-Punkte (Videos/Rezensionen) erhalten.")
        else:
            # 3. Formular (nur wenn Leselimit nicht voll)
            with st.sidebar.form("punkte_form", clear_on_submit=True):
                ergebnis = st.selectbox("Was hast du gelesen?", [
                    "-- Bitte wählen --",
                    "30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)",
                    "Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"
                ])
                submit = st.form_submit_button("Lesepunkte eintragen")

                if submit:
                    pkt = 0
                    if "30 min" in ergebnis: pkt = 2
                    elif "60 min" in ergebnis: pkt = 4
                    elif "bis 100" in ergebnis: pkt = 5
                    elif "bis 200" in ergebnis and "über" not in ergebnis: pkt = 10
                    elif "über 200" in ergebnis: pkt = 15
                    
                    if pkt > 0:
                        if (lese_punkte_woche + pkt) > PUNKTE_LIMIT_LESEN_WOCHE:
                            st.sidebar.error(f"Limit-Überschreitung! Nur noch {int(PUNKTE_LIMIT_LESEN_WOCHE - lese_punkte_woche)} Pkt. aus Lesen möglich.")
                        else:
                            neue_zeile = [datetime.now().strftime("%d.%m.%Y"), name_input, team_input, "Lesen", ergebnis, pkt]
                            worksheet.append_row(neue_zeile)
                            st.sidebar.success("✅ Lesepunkte gespeichert!")
                            st.rerun()
                    else:
                        st.sidebar.warning("Bitte Ergebnis wählen!")
else:
    st.sidebar.info("Bitte Name und Team eingeben.")

# --- TABELLE ---
c1, c2 = st.columns([1, 1.2])
with c1:
    st.subheader("🏆 Gesamttabelle (inkl. Bonus)")
    if not df.empty:
        rank = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
        st.table(rank.set_index("Team"))

with c2:
    st.subheader("📜 Letzte Leistungen")
    if not df.empty:
        st.dataframe(df.iloc[::-1][["Datum", "Kind", "Team", "Typ", "Punkte"]].head(10), use_container_width=True)
