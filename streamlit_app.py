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
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            if "Vorname" in df.columns and "Nachname" in df.columns:
                df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        return df, ws
    except Exception:
        return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING ---
def get_capped_ranking(df_full):
    if df_full.empty or "Vorname" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else:
        p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
        
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- UI HAUPTBEREICH ---
st.title("⚽ Kicken beginnt im Kopf")
st.subheader("Die Sommer-Leseliga des FLVW", anchor=False)
st.markdown("---")

# STATISTIK-METRIKEN OBEN
if not df.empty:
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Gelesene Bücher 📚", len(df[~df["Details"].str.contains("min")]))
    with m2:
        ges_min = int(df[df['Details'].str.contains('min')]['Punkte'].sum() * 15)
        st.metric("Leseminuten gesamt ⏱️", f"{ges_min} min")
    with m3:
        st.metric("Aktive Spieler 🏃‍♂️", df['Full_ID'].nunique() if 'Full_ID' in df.columns else 0)
    st.markdown("---")

# --- SIDEBAR: SPIELER KABINE ---
st.sidebar.header("👟 Spieler Kabine")

st.sidebar.info("""
**So sammelst du Punkte:**
1. Namen & Stützpunkt eingeben.
2. Lesezeit oder Buch wählen.
3. Haken bei der Bestätigung setzen.
4. 'Eintragen' klicken.
""")

v_name = st.sidebar.text_input("Vorname:", key="v_final").strip()
n_name = st.sidebar.text_input("Nachname:", key="n_final").strip()

t_liste = [
    "-- Bitte wählen --", 
    "Ahaus/Coesfeld I", "Ahaus/Coesfeld II", "Arnsberg/Soest", "Beckum", 
    "Bielefeld", "Bochum", "Detmold", "Dortmund", "Gelsenkirchen", 
    "Gütersloh", "Hagen", "Herford", "Herne", "Hochsauerlandkreis", 
    "Höxter", "Lemgo", "Lippstadt", "Lübbecke/Minden", "Lüdenscheid/Iserlohn", 
    "Münster I", "Münster II", "Olpe", "Paderborn", "Recklinghausen", 
    "Siegen/Wittgenstein", "Steinfurt", "Tecklenburg", "Unna/Hamm"
]
team_choice = st.sidebar.selectbox("Dein Stützpunkt:", t_liste, key="t_final")

if v_name and n_name and team_choice != "-- Bitte wählen --":
    current_id = f"{v_name.lower()} {n_name.lower()}"
    
    can_proceed = True
    if not df.empty and 'Full_ID' in df.columns:
        existing = df[df['Full_ID'] == current_id]
        if not existing.empty and existing['Team'].iloc[0] != team_choice:
            st.sidebar.error(f"Du bist bereits für '{existing['Team'].iloc[0]}' gemeldet!")
            can_proceed = False

    if can_proceed:
        kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
        akt_m = 0
        if not df.empty and 'Full_ID' in df.columns:
            akt_m = df[(df['Full_ID'] == current_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
        kat = st.sidebar.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"], key="k_final")
        
        with st.sidebar.form("entry_form"):
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"], key="m_final")
                p = 2 if "30" in auswahl else 4
            else:
                auswahl = st.selectbox("Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"], key="b_final")
                p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15

            confirm = st.checkbox("Ich bestätige, dass meine Angaben stimmen.")

            if st.form_submit_button("⚽ Punkt für mein Team!"):
                if not confirm:
                    st.error("Bitte setze erst den Haken bei der Bestätigung!")
                elif kat == "Lesezeit (Minuten)" and (akt_m + p) > LIMIT_MINUTEN:
                    st.error("Wochenlimit erreicht!")
                elif worksheet:
                    try:
                        heute = datetime.now().strftime("%d.%m.%Y")
                        worksheet.append_row([heute, v_name, n_name, team_choice, "Lesen", auswahl, p])
                        st.sidebar.success("Gespeichert!")
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception:
                        st.sidebar.error("Fehler beim Speichern!")

        st.sidebar.caption("Tipp: Bei Fehlern melde dich bitte direkt bei deinem Trainer.")

# --- HAUPTBEREICH ANZEIGE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🏆 Team-Tabelle", anchor=False)
    ranking_data = get_capped_ranking(df)
    if not ranking_data.empty:
        st.dataframe(ranking_data.set_index("Team").style.format({"Durchschnitt": "{:.2f}"}), use_container_width=True)
    else:
        st.info("Noch keine Ergebnisse.")

with col2:
    st.subheader("📜 Live-Ticker", anchor=False)
    if not df.empty:
        # Datenschutz: Namen im Ticker ausblenden
        hist_df = df.iloc[::-1][["Datum", "Team", "Details"]].head(10)
        st.table(hist_df)
    else:
        st.write("Warte auf erste Einträge...")

# --- DATENSCHUTZ & IMPRESSUM ---
st.markdown("---")
with st.expander("⚖️ Datenschutz & Impressum"):
    st.write("""
    **Datenschutzhinweis:** Mit der Nutzung dieser App und der Eingabe von Vorname, Nachname und Stützpunkt erklärst du dich einverstanden, dass diese Daten zum Zwecke des Wettbewerbs gespeichert werden. 
    Die Daten werden ausschließlich zur Berechnung des Team-Rankings verwendet und nicht an Dritte weitergegeben. 
    Im öffentlichen Live-Ticker erscheinen keine Namen, um deine Privatsphäre zu schützen.
    
    **Verantwortlich:** Fußball- und Leichtathletik-Verband Westfalen e. V. (FLVW)  
    Jakob-Koenen-Straße 2, 59174 Kamen
    """)
