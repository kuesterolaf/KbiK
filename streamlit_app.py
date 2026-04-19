import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")
LIMIT_MINUTEN = 20
# Aktualisierte Spaltenstruktur
SPALTEN = ["Datum", "Vorname", "Nachname", "Team", "Typ", "Details", "Punkte"]

# --- DATA CONNECTION ---
@st.cache_resource
def get_client():
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(s, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
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
            # Zeit-Daten für Deckelung
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            # Hilfsspalte für Identifikation (Vorname + Nachname)
            if "Vorname" in df.columns and "Nachname" in df.columns:
                df['Full_Name'] = df['Vorname'].astype(str).str.lower() + " " + df['Nachname'].astype(str).str.lower()
        return df, ws
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- LOGIK: TEAM-RANKING MIT QUOTIENT ---
def get_capped_ranking(df_full):
    if df_full.empty or "Vorname" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    
    # Eindeutige ID pro Kind für die Berechnung
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

# --- UI ---
st.title("⚽ Kicken beginnt im Kopf")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("👟 Spieler Kabine")
vorname = st.sidebar.text_input("Vorname:").strip()
nachname = st.sidebar.text_input("Nachname:").strip()
team_liste = ["-- Bitte wählen --", "Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]
team = st.sidebar.selectbox("Dein Team:", team_liste)

if vorname and nachname and team != "-- Bitte wählen --":
    full_name_lower = f"{vorname.lower()} {nachname.lower()}"
    
    # Registrierungs-Check
    if not df.empty and 'Full_Name' in df.columns:
        hist = df[df['Full_Name'] == full_name_lower]
        if not hist.empty and hist["Team"].iloc[0] != team:
            st.sidebar.error(f"Du bist bereits im Team '{hist['Team'].iloc[0]}' registriert!")
            status_ok = False
        else: status_ok = True
    else: status_ok = True

    if status_ok:
        kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
        akt_m = 0
        if not df.empty and 'Full_Name' in df.columns:
            akt_m = df[(df['Full_Name'] == full_name_lower) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum()
        
        st.sidebar.metric("Minuten-Punkte (KW)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
        
        with st.sidebar.form("entry_form"):
            kat = st.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                p = 2 if "30" in auswahl else 4
            else:
                auswahl = st.selectbox("Buch:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15

            if st.form_submit_button("Eintragen"):
                if kat == "Lesezeit (Minuten)" and (akt_m + p) > LIMIT_MINUTEN:
                    st.error("Limit erreicht!")
                elif worksheet:
                    try:
                        heute = datetime.now().strftime("%d.%m.%Y")
                        # Speichert nun Vorname und Nachname in getrennte Zellen
                        worksheet.append_row([heute, vorname, nachname, team, "Lesen", auswahl, p])
                        st.sidebar.success("Gespeichert!")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Speicherfehler: {e}")

# --- ANZEIGE ---
c1, c2 = st.columns([1, 1.2])
with c1:
    st.subheader("🏆 Team-Tabelle")
    ranking = get_capped_ranking(df)
    if not ranking.empty:
        st.table(ranking.set_index("Team").style.format({"Durchschnitt": "{:.2f}"}))
    else:
        st.info("Noch keine Ergebnisse.")

with c2:
    st.subheader("📜 Letzte Aktivitäten")
    if not df.empty:
        # Zeige Vorname (für die Team-Dynamik), aber verstecke den Nachnamen!
        disp = df.iloc[::-1][["Datum", "Vorname", "Team", "Details", "Punkte"]].head(10)
        st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")
st.info("ℹ️ **Datenschutz:** Nachnamen werden hier nicht veröffentlicht. Nur Vorname und Team-Leistung sind sichtbar!")
