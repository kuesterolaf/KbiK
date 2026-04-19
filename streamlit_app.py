import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_LESEN = 20

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
    df = pd.DataFrame(data)
    if not df.empty:
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT WOCHEN-DECKELUNG PRO KIND ---
def get_capped_ranking(df_full):
    if df_full.empty:
        return pd.DataFrame(columns=["Team", "Punkte"])
    
    # 1. Trenne Lesen und Bonus
    df_lesen = df_full[df_full["Typ"] == "Lesen"].copy()
    df_bonus = df_full[df_full["Typ"] != "Lesen"].copy()
    
    # 2. Deckelung pro Kind pro Woche (max 20 Pkt)
    lese_summen = df_lesen.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
    lese_summen['Punkte'] = lese_summen['Punkte'].clip(upper=LIMIT_LESEN)
    
    # 3. Zusammenführen
    team_lesen = lese_summen.groupby('Team')['Punkte'].sum().reset_index()
    team_bonus = df_bonus.groupby('Team')['Punkte'].sum().reset_index()
    
    final = pd.concat([team_lesen, team_bonus]).groupby('Team')['Punkte'].sum().reset_index()
    return final.sort_values("Punkte", ascending=False)

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("<p style='font-size: 20px;'>Holt euch die Meisterschaft für euer Team! 📖🏆</p>", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: DISKRETER CHECK-IN ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Dein Name:").strip()
team = st.sidebar.selectbox("Dein Team:", ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])

if name and team != "-- Bitte wählen --":
    hist = df[df["Kind"].str.lower() == name.lower()]
    if not hist.empty and hist["Team"].iloc[0] != team:
        st.sidebar.error(f"Du bist bereits im Team '{hist['Team'].iloc[0]}' gemeldet!")
    else:
        # Wochen-Stand für das Kind (Nur in der Sidebar sichtbar!)
        kw_jetzt = datetime.now().isocalendar()[1]
        jahr_jetzt = datetime.now().isocalendar()[0]
        akt_p = 0
        if not df.empty:
            akt_p = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw_jetzt) & (df["Jahr"] == jahr_jetzt) & (df["Typ"] == "Lesen")]["Punkte"].sum()
        
        st.sidebar.metric("Deine Lesepunkte diese Woche", f"{int(akt_p)} / {LIMIT_LESEN}")
        
        if akt_p >= LIMIT_LESEN:
            st.sidebar.warning("Wochenlimit erreicht! Danke für deinen Einsatz für das Team!")
        else:
            with st.sidebar.form("entry"):
                auswahl = st.selectbox("Was hast du gelesen?", ["30 min (2 Pkt)", "60 min (4 Pkt)", "Buch <100 S. (5 Pkt)", "Buch <200 S. (10 Pkt)", "Buch >200 S. (15 Pkt)"])
                if st.form_submit_button("Für das Team eintragen"):
                    p = 2 if "30" in auswahl else 4 if "60" in auswahl else 5 if "<100" in auswahl else 10 if "<200" in auswahl else 15
                    worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", auswahl, p])
                    st.sidebar.success("Super! Deine Punkte zählen für dein Team.")
                    st.rerun()

# --- HAUPTBEREICH: ANONYME ANZEIGE ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        # Wir zeigen nur die reinen Team-Summen
        st.table(ranking.set_index("Team"))
    else:
        st.info("Das Turnier startet gerade...")

with col2:
    st.subheader("📜 Letzte Team-Aktivitäten")
    if not df.empty:
        # WICHTIG: Wir zeigen hier die Spalte 'Kind' NICHT an!
        display_df = df.iloc[::-1][["Datum", "Team", "Typ", "Punkte"]].head(10)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.info("ℹ️ **Datenschutz:** Namen von Spielern werden hier nicht veröffentlicht. Nur eure Team-Leistung zählt!")
