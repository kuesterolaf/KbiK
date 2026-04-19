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
        # Zeit-Daten für Deckelung aufbereiten
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT QUOTIENT (DURCHSCHNITT) ---
def get_capped_ranking(df_full):
    if df_full.empty or "Kind" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # 1. Trennung: Minuten (gedeckelt) vs. Rest (Bücher/Bonus - ungedeckelt)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    # 2. Deckelung der Minuten-Punkte pro Woche/Kind
    if not df_min.empty:
        min_sum = df_min.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
        min_sum['Punkte'] = min_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        # Summe der gedeckelten Minuten pro Kind (über alle Wochen)
        points_min = min_sum.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    else:
        points_min = pd.DataFrame(columns=["Kind", "Team", "Punkte"])
        
    # 3. Extra-Punkte pro Kind (Bücher & Bonus)
    points_extra = df_extra.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind", "Team", "Punkte"])
    
    # 4. Alle Punkte pro Kind zusammenführen
    total_per_child = pd.concat([points_min, points_extra]).groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    
    # 5. Team-Statistik berechnen (Quotient)
    team_stats = total_per_child.groupby('Team').agg(
        Gesamtpunkte=('Punkte', 'sum'),
        Anzahl_Spieler=('Kind', 'nunique')
    ).reset_index()
    
    team_stats['Durchschnitt'] = (team_stats['Gesamtpunkte'] / team_stats['Anzahl_Spieler']).round(2)
    
    # Für die Anzeige umbenennen
    result = team_stats[['Team', 'Durchschnitt', 'Anzahl_Spieler']].rename(columns={'Anzahl_Spieler': 'Spieler'})
    return result.sort_values("Durchschnitt", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("### Werdet Lesemeister! 📖🏆")
st.markdown("---")

# --- SIDEBAR: DISKRETER CHECK-IN ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Dein Name (Vor- & Nachname):").strip()
team_liste = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team = st.sidebar.selectbox("Dein Team:", team_liste)

if name and team != "-- Bitte wählen --":
    # Registrierungs-Check
    hist = df[df["Kind"].str.lower() == name.lower()]
    if not hist.empty and hist["Team"].iloc[0] != team:
        st.sidebar.error(f"Du bist bereits im Team '{hist['Team'].iloc[0]}' registriert!")
    else:
        # Wochen-Stand für Anzeige berechnen
        kw = datetime.now().isocalendar()[1]
        jahr = datetime.now().isocalendar()[0]
        akt_min = 0
        if not df.empty:
            akt_min = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_min)} / {LIMIT_MINUTEN}")
        
        with st.sidebar.form("entry_form"):
            kat = st.radio("Was hast du geschafft?", ["Lesezeit melden", "Buch abgeschlossen 🏆"])
            
            if kat == "Lesezeit melden":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                p = 2 if "30" in auswahl else 4
            else:
                auswahl = st.selectbox("Buch-Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15

            if st.form_submit_button("Für das Team speichern"):
                if kat == "Lese
