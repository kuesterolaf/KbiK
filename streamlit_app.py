import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="FLVW Sommer-Leseliga", page_icon="⚽", layout="wide")

# Verbindung (identisch)
@st.cache_resource
def get_client():
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(s, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception: return None

def load_data():
    client = get_client()
    if not client: return pd.DataFrame(), None
    try:
        sh = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(), ws
        
        df = pd.DataFrame(data)
        
        # --- ROBUSTE BEREINIGUNG ---
        # Entfernt Leerzeichen aus Spaltennamen (verhindert Mismatch)
        df.columns = [c.strip() for c in df.columns]
        
        # Datum konvertieren
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        
        # Punkte radikal in Zahlen umwandeln
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        
        # Eindeutige ID bauen
        if "Vorname" in df.columns and "Nachname" in df.columns:
            df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        
        return df, ws
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame(), None

df, worksheet = load_data()

# --- RANKING LOGIK ---
def get_capped_ranking(df_full):
    if df_full.empty or "Team" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # Kind-ID für eindeutige Spieler
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    
    # 1. Deckelung der Minuten-Punkte (max 20 pro Woche/Kind)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    if not df_min.empty:
        # Gruppieren nach Jahr, KW und Kind, dann auf 20 deckeln
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=20)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else:
        p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
        
    # 2. Buch-Punkte (ohne Deckel)
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    # 3. Zusammenführen
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    
    # 4. Team-Schnitt berechnen
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI ANZEIGE ---
st.title("⚽ FLVW Sommer-Leseliga")
st.markdown("---")

if df.empty:
    st.warning("⚠️ Das Google Sheet scheint leer zu sein oder die Spaltennamen stimmen nicht.")
    st.info("Erwartete Spalten: Datum, Vorname, Nachname, Team, Typ, Details, Punkte")
else:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("🏆 Tabelle", anchor=False)
        ranking = get_capped_ranking(df)
        st.dataframe(ranking.set_index("Team"), use_container_width=True)
    
    with c2:
        st.subheader("📜 Live-Ticker", anchor=False)
        ticker = df.iloc[::-1][["Datum", "Team", "Details", "Punkte"]].head(10)
        st.table(ticker)

# ... (Sidebar-Code bleibt gleich wie zuvor)
