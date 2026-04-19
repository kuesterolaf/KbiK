import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
SPALTEN = ["Datum", "Kind", "Team", "Typ", "Details", "Punkte"]

# --- DATA ---
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
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT SPEZIAL-DECKELUNG ---
def get_capped_ranking(df_full):
    if df_full.empty or "Kind" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Punkte"])
    
    # 1. Trennung der Typen
    # Typ 'Minuten' wird gedeckelt
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    # Typ 'Buch' und 'Bonus' werden NICHT gedeckelt
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    # 2. Deckelung nur für Minuten (max 20 pro Woche/Kind)
    if not df_min.empty:
        min_sum = df_min.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
        min_sum['Punkte'] = min_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        team_min = min_sum.groupby('Team')['Punkte'].sum().reset_index()
    else:
        team_min = pd.DataFrame(columns=["Team", "Punkte"])
        
    # 3. Extra-Punkte (Bücher & Bonus) voll summieren
    team_extra = df_extra.groupby('Team')['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Team", "Punkte"])
    
    final = pd.concat([team_min, team_extra]).groupby('Team')['Punkte'].sum().reset_index()
    return final.sort_values("Punkte", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Name:").strip()
team = st.sidebar.selectbox("Team:", ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])

if name and team != "-- Bitte wählen --":
    # Namens-Team-Check
    hist = df[df["Kind"].str.lower() == name.lower()]
    if not hist.empty and hist["Team"].iloc[0] != team:
        st.sidebar.error(f"Du spielst bereits für {hist['Team'].iloc[0]}!")
    else:
        kw = datetime.now().isocalendar()[1]
        jahr = datetime.now().isocalendar()[0]
        
        # Aktuelle Minuten-Punkte berechnen
        akt_min = 0
        if not df.empty:
            akt_min = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_min)} / {LIMIT_MINUTEN}")
        
        with st.sidebar.form("entry"):
            kat = st.radio("Was willst du eintragen?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                p = 2 if "30" in auswahl else 4
                disabled = akt_min >= LIMIT_MINUTEN
            else:
                auswahl = st.selectbox("Buch-Größe:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15
                disabled = False # Bücher gehen immer!

            if st.form_submit_button("Eintragen"):
                if kat == "Lesezeit (Minuten)" and (akt_min + p) > LIMIT_MINUTEN:
                    st.error(f"Limit überschritten! Nur noch {int(LIMIT_MINUTEN - akt_min)} Pkt möglich.")
                else:
                    if worksheet.row_count == 0 or not worksheet.get_all_values():
                        worksheet.append_row(SPALTEN)
                    worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", auswahl, p])
                    st.sidebar.success("Eingetragen!")
                    st.rerun()

# --- ANZEIGE ---
c1, c2 = st.columns([1, 1.2])
with c1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    st.table(ranking.set_index("Team"))

with c2:
    st.subheader("📜 Letzte Team-Aktivitäten")
    if not df.empty:
        display_df = df.iloc[::-1][["Datum", "Team", "Details", "Punkte"]].head(10)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
