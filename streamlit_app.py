import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- BASIS KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
SPALTEN = ["Datum", "Kind", "Team", "Typ", "Details", "Punkte"]

# --- VERBINDUNG ZUM GOOGLE SHEET ---
@st.cache_resource
def get_gspread_client():
    s = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(
        {
            "type": s["type"], "project_id": s["project_id"], "private_key_id": s["private_key_id"],
            "private_key": s["private_key"], "client_email": s["client_email"], "client_id": s["client_id"],
            "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"],
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def load_data():
    client = get_gspread_client()
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(url)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    if not data:
        df = pd.DataFrame(columns=SPALTEN)
    else:
        df = pd.DataFrame(data)
        # Zeit-Daten für Deckelung vorbereiten
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
    return df, ws

try:
    df, worksheet = load_data()
except Exception as e:
    st.error(f"Fehler bei der Datenverbindung: {e}")
    df = pd.DataFrame(columns=SPALTEN)

# --- LOGIK: TEAM-RANKING MIT QUOTIENT ---
def get_capped_ranking(df_full):
    if df_full.empty or "Kind" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # Trennung: Minuten (gedeckelt) vs. Rest (Bücher/Bonus - ungedeckelt)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    
    # Deckelung Minuten pro Woche/Kind
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        points_min = m_sum.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    else:
        points_min = pd.DataFrame(columns=["Kind", "Team", "Punkte"])
        
    points_extra = df_extra.groupby(['Kind', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind", "Team", "Punkte"])
    
    # Alles pro Kind zusammenführen
    total_child = pd.concat([points_min, points_extra]).groupby(['Kind', 'Team'])['Punkte'].sum().reset_index()
    
    # Quotient berechnen
    team_stats = total_child.groupby('Team').agg(
        Gesamtpunkte=('Punkte', 'sum'),
        Anzahl_Spieler=('Kind', 'nunique')
    ).reset_index()
    
    team_stats['Durchschnitt'] = (team_stats['Gesamtpunkte'] / team_stats['Anzahl_Spieler']).round(2)
    return team_stats[['Team', 'Durchschnitt', 'Anzahl_Spieler']].rename(columns={'Anzahl_Spieler': 'Spieler'}).sort_values("Durchschnitt", ascending=False)

# --- DESIGN ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("### Werdet Lesemeister! 📖🏆")
st.markdown("---")

# --- SIDEBAR: DISKRETER CHECK-IN ---
st.sidebar.header("👟 Spieler Kabine")
name = st.sidebar.text_input("Name (Vor- & Nachname):").strip()
team_liste = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team = st.sidebar.selectbox("Dein Team:", team_liste)

if name and team != "-- Bitte wählen --":
    hist = df[df["Kind"].str.lower() == name.lower()]
    if not hist.empty and hist["Team"].iloc[0] != team:
        st.sidebar.error(f"Du bist bereits im Team '{hist['Team'].iloc[0]}' registriert!")
    else:
        # Wochen-Stand für Anzeige
        kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
        akt_min = 0
        if not df.empty and "KW" in df.columns:
            akt_min = df[(df["Kind"].str.lower() == name.lower()) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Deine Minuten-Punkte (KW)", f"{int(akt_min)} / {LIMIT_MINUTEN}")
        
        with st.sidebar.form("entry_form"):
            kat = st.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                p = 2 if "30" in auswahl else 4
            else:
                auswahl = st.selectbox("Buch-Größe:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15

            if st.form_submit_button("Eintragen"):
                if kat == "Lesezeit (Minuten)" and (akt_min + p) > LIMIT_MINUTEN:
                    st.error(f"Limit erreicht! Max. noch {int(LIMIT_MINUTEN - akt_min)} Pkt möglich.")
                else:
                    try:
                        worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), name, team, "Lesen", auswahl, p])
                        st.sidebar.success("Super! Punkte verbucht.")
                        st.rerun()
                    except:
                        st.sidebar.error("Fehler beim Speichern!")

# --- ANZEIGE ---
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        st.table(ranking.set_index("Team"))
        st.caption("Berechnung: Durchschnittspunkte pro gemeldetem Spieler.")
    else:
        st.info("Noch keine Ergebnisse.")

with c2:
    st.subheader("📜 Letzte Aktivitäten")
    if not df.empty:
        display_df = df.iloc[::-1][["Datum", "Team", "Details", "Punkte"]].head(10)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.info("ℹ️ **Datenschutz:** Namen von Spielern werden hier nicht veröffentlicht. Nur eure Team-Leistung zählt!")
