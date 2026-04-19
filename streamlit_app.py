import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
SPALTEN = ["Datum", "Kind", "Team", "Typ", "Details", "Punkte"]

# --- DATA CONNECTION ---
@st.cache_resource
def get_client():
    s = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(s, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def load_data():
    client = get_client()
    sh = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    if not data:
        df = pd.DataFrame(columns=SPALTEN)
    else:
        df = pd.DataFrame(data)
        # Spalten sicherstellen
        for col in SPALTEN:
            if col not in df.columns:
                df[col] = 0
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT QUOTIENT ---
def get_capped_ranking(df_full):
    if df_full.empty or "Kind" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # 1. Trennung: Minuten (gedeckelt) vs. Bücher (ungedeckelt)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    # 2. Deckelung der Minuten (max 20 pro Woche/Kind)
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    else:
        p_min = pd.DataFrame(columns=["Kind", "Team", "Punkte"])
        
    # 3. Bücher-Punkte
    p_extra = df_extra.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind", "Team", "Punkte"])
    
    # 4. Zusammenführen & Quotient berechnen
    total = pd.concat([p_min, p_extra]).groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("### Gemeinsam zum Sieg! 📖🏆")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Name (Vor- & Nachname):").strip()
teams = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team = st.sidebar.selectbox("Dein Team:", teams)

if name and team != "-- Bitte wählen --":
    hist = df[df["Kind"].str.lower() == name.lower()]
    if not hist.empty and hist["Team"].iloc[0] != team:
        st.sidebar.error(f"Du bist bereits im Team '{hist['Team'].iloc[0]}' registriert!")
    else:
        kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
        akt_m = 0
        if not df.empty:
            akt_m = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
        
        with st.sidebar.form("entry_form"):
            kat = st.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:",
