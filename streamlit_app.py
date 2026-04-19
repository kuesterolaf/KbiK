import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURATION ---
st.set_page_config(page_title="FLVW Sommer-Leseliga", page_icon="⚽", layout="wide")

# Verbindung zum Google Sheet
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
        if not data: return pd.DataFrame(), ws
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]
        df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
        df['KW'] = df['Datum_dt'].dt.isocalendar().week
        df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
        df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        if "Vorname" in df.columns and "Nachname" in df.columns:
            df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        return df, ws
    except Exception: return pd.DataFrame(), None

df, worksheet = load_data()

# --- RANKING LOGIK ---
def get_capped_ranking(df_full):
    if df_full.empty or "Team" not in df_full.columns:
        return pd.DataFrame(columns=["Team", "Durchschnitt", "Spieler"])
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    df_min = df_full[df_full["Details"].str.contains("min", na=False)].copy()
    df_extra = df_full[~df_full["Details"].str.contains("min", na=False)].copy()
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=20)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else: p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- SIDEBAR (SPIELER KABINE) ---
with st.sidebar:
    st.header("👟 Spieler Kabine")
    st.info("Sammle Punkte für deinen Stützpunkt!")
    
    v_name = st.text_input("Vorname:").strip()
    n_name = st.text_input("Nachname:").strip()
    
    t_liste = ["-- Bitte wählen --", "Ahaus/Coesfeld I", "Ahaus/Coesfeld II", "Arnsberg/Soest", "Beckum", "Bielefeld", "Bochum", "Detmold", "Dortmund", "Gelsenkirchen", "Gütersloh", "Hagen", "Herford", "Herne", "Hochsauerlandkreis", "Höxter", "Lemgo", "Lippstadt", "Lübbecke/Minden", "Lüdenscheid/Iserlohn", "Münster I", "Münster II", "Olpe", "Paderborn", "Recklinghausen", "Siegen/Wittgenstein", "Steinfurt", "Tecklenburg", "Unna/Hamm"]
    team_choice = st.selectbox("Dein Stützpunkt:", t_liste)

    if v_name and n_name and team_choice != "-- Bitte wählen --":
        current_id = f"{v_name.lower()} {n_name.lower()}"
        can_proceed = True
        if not df.empty and 'Full_ID' in df.columns:
            existing = df[df['Full_ID'] == current_id]
            if not existing.empty and existing['Team'].iloc[0] != team_choice:
                st.error(f"Bereits gemeldet für: {existing['Team'].iloc[0]}")
                can_proceed = False

        if can_proceed:
            kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
            akt_m = df[(df['Full_ID'] == current_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min"))]["Punkte"].sum() if not df.empty else 0
            st.metric("Deine Wochen-Minuten", f"{int(akt_m)} / 20")
            
            kat = st.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
            
            with st.form("entry_form"):
                if kat == "Lesezeit (Minuten)":
                    auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                    p = 2 if "30" in auswahl else 4
                else:
                    auswahl = st.selectbox("Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                    p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15

                confirm = st.checkbox("Angaben bestätigen")
                if st.form_submit_button("⚽ Punkt für mein Team!"):
                    if not confirm:
                        st.error("Bitte Haken setzen!")
                    elif kat == "Lesezeit (Minuten)" and (akt_m + p) > 20:
                        st.error("Wochenlimit erreicht!")
                    elif worksheet:
                        worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), v_name, n_name, team_choice, "Lesen", auswahl, p])
                        st.cache_resource.clear()
                        st.rerun()

# --- HAUPTBEREICH ---
st.title("⚽ FLVW Sommer-Leseliga")
st.subheader
