import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_LESEN = 20
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
        # Falls Sheet leer ist, leeren DataFrame mit korrekten Spalten erzeugen
        df = pd.DataFrame(columns=SPALTEN)
    else:
        df = pd.DataFrame(data)
        # Sicherstellen, dass alle nötigen Spalten da sind
        for col in SPALTEN:
            if col not in df.columns:
                df[col] = ""
        
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    
    return df, ws

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING (ANONYM & GEDEDCKELT) ---
def get_capped_ranking(df_full):
    if df_full.empty or "Kind" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Punkte"])
    
    # 1. Trenne Lesen und Bonus
    df_lesen = df_full[df_full["Typ"] == "Lesen"].copy()
    df_bonus = df_full[df_full["Typ"] != "Lesen"].copy()
    
    # 2. Deckelung pro Kind pro Woche (max 20 Pkt)
    if not df_lesen.empty and "KW" in df_lesen.columns:
        lese_summen = df_lesen.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
        lese_summen['Punkte'] = lese_summen['Punkte'].clip(upper=LIMIT_LESEN)
        team_lesen = lese_summen.groupby('Team')['Punkte'].sum().reset_index()
    else:
        team_lesen = pd.DataFrame(columns=["Team", "Punkte"])
    
    # 3. Bonus-Punkte
    team_bonus = df_bonus.groupby('Team')['Punkte'].sum().reset_index() if not df_bonus.empty else pd.DataFrame(columns=["Team", "Punkte"])
    
    final = pd.concat([team_lesen, team_bonus]).groupby('Team')['Punkte'].sum().reset_index()
    return final.sort_values("Punkte", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("### Gemeinsam zum Sieg! 📖🏆")
st.markdown("---")

# --- SIDEBAR: DISKRETER CHECK-IN ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Dein Name:").strip()
team_auswahl = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team = st.sidebar.selectbox("Dein Team:", team_auswahl)

if name and team != "-- Bitte wählen --":
    # Registrierungs-Check
    if not df.empty and name.lower() in df["Kind"].str.lower().values:
        reg_team = df[df["Kind"].str.lower() == name.lower()]["Team"].iloc[0]
        if reg_team != team:
            st.sidebar.error(f"Du spielst bereits für {reg_team}!")
            status_ok = False
        else:
            status_ok = True
    else:
        status_ok = True

    if status_ok:
        kw_jetzt = datetime.now().isocalendar()[1]
        jahr_jetzt = datetime.now().isocalendar()[0]
        
        akt_p = 0
        if not df.empty and "KW" in df.columns:
            akt_p = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw_jetzt) & (df["Jahr"] == jahr_jetzt) & (df["Typ"] == "Lesen")]["Punkte"].sum()
        
        st.sidebar.metric("Deine Lesepunkte (diese Woche)", f"{int(akt_p)} / {LIMIT_LESEN}")
        
        if akt_p >= LIMIT_LESEN:
            st.sidebar.warning("Wochenlimit erreicht! Super Einsatz!")
        else:
            with st.sidebar.form("entry"):
                ergebnis = st.selectbox("Was hast du geschafft?", ["30 min (2 Pkt)", "60 min (4 Pkt)", "Buch <100 S. (5 Pkt)", "Buch <200 S. (10 Pkt)", "Buch >200 S. (15 Pkt)"])
                if st.form_submit_button("Punkte eintragen"):
                    p = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5 if "<100" in ergebnis else 10 if "<200" in ergebnis else 15
                    # Falls Sheet ganz leer war, zuerst Kopfzeile schreiben
                    if worksheet.row_count == 0 or not worksheet.get_all_values():
                        worksheet.append_row(SPALTEN)
                    
                    worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", ergebnis, p])
                    st.sidebar.success("Eingetragen!")
                    st.rerun()

# --- ANZEIGE (ANONYM) ---
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        st.table(ranking.set_index("Team"))
    else:
        st.info("Noch keine Punkte vergeben.")

with c2:
    st.subheader("📜 Letzte Team-Leistungen")
    if not df.empty:
        # Kind-Spalte wird hier gezielt ausgeblendet
        display_cols = [c for c in ["Datum", "Team", "Typ", "Punkte"] if c in df.columns]
        st.dataframe(df.iloc[::-1][display_cols].head(10), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🔒 Namen sind privat und werden nur zur Berechnung deines Wochenlimits genutzt.")
