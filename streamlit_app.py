import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
SPALTEN = ["Datum", "Vorname", "Nachname", "Team", "Typ", "Details", "Punkte"]

# --- DATA CONNECTION ---
@st.cache_resource
def get_client():
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(s, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception:
        return None

def load_data():
    client = get_client()
    if not client: return pd.DataFrame(columns=SPALTEN), None
    try:
        sh = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        if not data:
            df = pd.DataFrame(columns=SPALTEN)
        else:
            df = pd.DataFrame(data)
            # Datentypen für Berechnungen sicherstellen
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            if "Vorname" in df.columns and "Nachname" in df.columns:
                df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        return df, ws
    except Exception:
        return pd.DataFrame(columns=SPALTEN), None

# Daten laden
df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING ---
def get_capped_ranking(df_full):
    if df_full.empty or "Vorname" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # Eindeutige Kind-ID
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    
    # Trennung Minuten (mit Cap) und Rest
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else:
        p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
        
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    # Gesamtberechnung
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("---")

# SIDEBAR
st.sidebar.header("👟 Spieler Kabine")
v_name = st.sidebar.text_input("Vorname:", key="v_in").strip()
n_name = st.sidebar.text_input("Nachname:", key="n_in").strip()
t_liste = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team_choice = st.sidebar.selectbox("Dein Team:", t_liste, key="t_sel")

if v_name and n_name and team_choice != "-- Bitte wählen --":
    current_id = f"{v_name.lower()} {n_name.lower()}"
    
    # Team-Kontrolle
    can_proceed = True
    if not df.empty and 'Full_ID' in df.columns:
        existing = df[df['Full_ID'] == current_id]
        if not existing.empty and existing['Team'].iloc[0] != team_choice:
            st.sidebar.error(f"Du bist bereits bei {existing['Team'].iloc[0]} gemeldet!")
            can_proceed = False

    if can_proceed:
        # Wochen-Punkte anzeigen
        kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
        akt_m = 0
        if not df.empty and 'Full_ID' in df.columns:
            akt_m = df[(df['Full_ID'] == current_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
        
        kat = st.sidebar.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"], key="kat_r")
        
        with st.sidebar.form("entry_form"):
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "6
