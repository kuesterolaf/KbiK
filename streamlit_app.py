import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
# Spaltenstruktur laut deinem aktuellen Google Sheet
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
            # WICHTIG: Datentypen für die Berechnung korrigieren
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            # Eindeutige ID aus Vorname und Nachname erstellen
            if "Vorname" in df.columns and "Nachname" in df.columns:
                df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        return df, ws
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT QUOTIENT ---
def get_capped_ranking(df_full):
    # Prüfung, ob die neuen Spalten vorhanden sind
    if df_full.empty or "Vorname" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # Kind_ID für fairen Vergleich (Vorname + Nachname)
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    
    # Trennung nach Leseminuten (mit Deckelung) und Buch-Punkte (ohne Deckelung)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    if not df_min.empty:
        # Wochenlimit pro Kind anwenden
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else:
        p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
        
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    # Alles zusammenrechnen und durch Spieleranzahl teilen
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI ANZEIGE ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("---")

# Sidebar für Eingaben
st.sidebar.header("👟 Spieler Kabine")
v_name = st.sidebar.text_input("Vorname:").strip()
n_name = st.sidebar.text_input("Nachname:").strip()
t_liste = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team_choice = st.sidebar.selectbox("Dein Team:", t_liste)

# Eingabe-Logik (gekürzt für Übersicht)
if v_name and n_name and team_choice != "-- Bitte wählen --":
    # Hier folgt dein Code zum Speichern (append_row)...
    pass

# --- HAUPTBEREICH: HIER LAG DER FEHLER ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        # Tabelle anzeigen mit 2 Nachkommastellen
        st.table(ranking.set_index("Team").style.format({"Durchschnitt": "{:.2f}"}))
    else:
        st.info("Noch keine berechenbaren Ergebnisse gefunden. Prüfe, ob die Spaltennamen im Sheet 'Vorname' und 'Nachname' heißen.")

with col2:
    st.subheader
