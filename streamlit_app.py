import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="FLVW Sommer-Leseliga", page_icon="⚽", layout="wide")

# CSS für ein bisschen FLVW-Flair (Grün/Blau-Töne)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

LIMIT_MINUTEN = 20
SPALTEN = ["Datum", "Vorname", "Nachname", "Team", "Typ", "Details", "Punkte"]

# --- DATA CONNECTION (identisch geblieben) ---
@st.cache_resource
def get_client():
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(s, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception: return None

def load_data():
    client = get_client()
    if not client: return pd.DataFrame(columns=SPALTEN), None
    try:
        sh = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        if not data: df = pd.DataFrame(columns=SPALTEN)
        else:
            df = pd.DataFrame(data)
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            if "Vorname" in df.columns:
                df['Full_ID'] = df['Vorname'].astype(str).lower().strip() + " " + df['Nachname'].astype(str).lower().strip()
        return df, ws
    except Exception: return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- RANKING LOGIK ---
def get_capped_ranking(df_full):
    if df_full.empty: return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else: p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
        
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI HAUPTBEREICH ---
# Header mit Logo-Ersatz durch Emojis
st.markdown("# 🏆 FLVW Sommer-Leseliga")
st.markdown("### *Kicken beginnt im Kopf*")
st.markdown("---")

# --- HIGHLIGHT METRICS (NEU) ---
if not df.empty:
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Bücher gelesen 📚", len(df[~df["Details"].str.contains("min")]))
    with m2:
        st.metric("Leseminuten (Total) ⏱️", f"{int(df[df['Details'].str.contains('min')]['Punkte'].sum() * 15)}") # Schätzung: Punkte * 15min
    with m3:
        st.metric("Aktive Stützpunkte 🏰", df["Team"].nunique())
    st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("👟 Spieler Kabine")
    st.info("Namen & Stützpunkt eingeben, Erfolg wählen und Haken setzen!")
    
    v_name = st.text_input("Vorname:").strip()
    n_name = st.text_input("Nachname:").strip()
    t_liste = ["-- Bitte wählen --", "Ahaus/Coesfeld I", "Ahaus/Coesfeld II", "Arnsberg/Soest", "Beckum", "Bielefeld", "Bochum", "Detmold", "Dortmund", "Gelsenkirchen", "Gütersloh", "Hagen", "Herford", "Herne", "Hochsauerlandkreis", "Höxter", "Lemgo", "Lippstadt", "Lübbecke/Minden", "Lüdenscheid/Iserlohn", "Münster I", "Münster II", "Olpe", "Paderborn", "Recklinghausen", "Siegen/Wittgenstein", "Steinfurt", "Tecklenburg", "Unna/Hamm"]
    team_choice = st.selectbox("Dein Stützpunkt:", t_liste)

    if v_name and n_name and team_choice != "-- Bitte wählen --":
        current_id = f"{v_name.lower()} {n_name.lower()}"
        can_p = True
        if not df.empty:
            ex = df[df['Full_ID'] == current_id]
            if not ex.empty and ex['Team'].iloc[0] != team_choice:
                st.error(f"Registriert bei: {ex['Team'].iloc[0]}")
                can_p = False
        
        if can_p:
            kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
            akt_m = df[(df['Full_ID'] == current_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum() if not df.empty else 0
            st.metric("Deine Wochenpunkte (Minuten)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
            
            kat = st.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            with st.form("entry"):
                if kat == "Lesezeit (Minuten)":
                    auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                    p = 2 if "30" in auswahl else 4
                else:
                    auswahl = st.selectbox("Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                    p = 5 if "100" in auswahl else 10 if "200" in auswahl else 15
                
                conf = st.checkbox("Daten prüfen & bestätigen")
                if st.form_submit_button("⚽ Punkt für mein Team!") and conf:
                    if kat == "Lesezeit (Minuten)" and (akt_m + p) > LIMIT_MINUTEN: st.error("Wochenlimit!")
                    else:
                        worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), v_name, n_name, team_choice, "Lesen", auswahl, p])
                        st.cache_resource.clear()
                        st.rerun()

# --- ANZEIGE ---
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("🏆 Die offizielle Tabelle", anchor=False)
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        # Hervorhebung des Ersten
        st.dataframe(ranking.set_index("Team"), use_container_width=True)
    else: st.info("Warte auf Anpfiff...")

with c2:
    st.subheader("📜 Live-Ticker", anchor=False)
    if not df.empty:
        ticker = df.iloc[::-1][["Datum", "Team", "Details"]].head(10)
        st.table(ticker) # Tabelle sieht im Ticker-Stil oft cleaner aus
    else: st.write("Noch keine Action...")

st.markdown("---")
st.caption("Ein Projekt des FLVW zur Förderung der Lesekompetenz. Bei Fehlern bitte an die Turnierleitung wenden.")
