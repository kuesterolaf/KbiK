import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. KONFIGURATION & KONSTANTEN ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

LIMIT_MINUTEN = 20 
SPALTEN = ["Datum", "Vorname", "Nachname", "Team", "Typ", "Details", "Punkte"]

# --- 2. DESIGN UPGRADE (CSS) ---
st.markdown("""
    <style>
    /* Sidebar Grunddesign */
    [data-testid="stSidebar"] { 
        background-color: #E31E24 !important; 
    }
    [data-testid="stSidebar"] * { 
        color: white !important; 
    }
    
    /* Metrik in Sidebar (Punkteanzeige) */
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0px !important;
    }
    
    /* Eingabefelder Sidebar */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] [data-baseweb="select"] div { 
        background-color: white !important; 
        color: #31333F !important; 
    }

    /* Header Zentrierung */
    .header-container { text-align: center; width: 100%; }
    .tight-title { margin-top: -15px !important; line-height: 1.1; text-align: center; color: #31333F !important; }
    .tight-subtitle { margin-top: -10px !important; color: #666 !important; text-align: center; }

    /* Metriken Hauptbereich */
    [data-testid="stMain"] [data-testid="stMetric"] { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #f0f2f6; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMain"] [data-testid="stMetric"] * { color: #31333F !important; }

    /* --- DER FORM-BUTTON FIX --- */
    [data-testid="stSidebar"] button[kind="primaryFormSubmit"], 
    [data-testid="stSidebar"] button[kind="secondaryFormSubmit"],
    [data-testid="stSidebar"] .stButton > button {
        background-color: white !important;
        border: 2px solid #31333F !important;
        border-radius: 5px !important;
        width: 100% !important;
        height: 3em !important;
    }

    [data-testid="stSidebar"] button p, 
    [data-testid="stSidebar"] button span {
        color: #E31E24 !important;
        font-weight: bold !important;
    }
    
    [data-testid="stSidebar"] button:hover {
        background-color: #f0f2f6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATENBANK-FUNKTIONEN ---
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
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            # ID für den Abgleich (Kleinbuchstaben & bereinigt)
            df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
        return df, ws
    except Exception: return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- 4. RANKING-LOGIK ---
def get_capped_ranking(df_full):
    if df_full.empty or "Team" not in df_full.columns: return pd.DataFrame()
    df_full['Kind_ID'] = df_full['Vorname'].astype(str).str.strip() + " " + df_full['Nachname'].astype(str).str.strip()
    mask_min = df_full["Details"].str.contains("min|Min", na=False, case=False)
    df_min = df_full[mask_min].copy()
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else: p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    df_extra = df_full[~mask_min].copy()
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    if total.empty: return pd.DataFrame()
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- 5. HAUPTBEREICH: HEADER ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 1.5, 1])
with col_logo2:
    if os.path.exists("flvw-logo.png"):
        st.image("flvw-logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center;'>⚽</h1>", unsafe_allow_html=True)

st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.markdown('<h1 class="tight-title">Kicken beginnt im Kopf</h1>', unsafe_allow_html=True)
st.markdown('<h3 class="tight-subtitle">Die Sommer-Leseliga des FLVW</h3>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("---")

# --- 6. METRIKEN ---
if not df.empty:
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Gelesene Bücher 📚", len(df[~df["Details"].str.contains("min|Min")]))
    with m2: 
        ges_min = int(df[df['Details'].str.contains('min|Min')]['Punkte'].sum() * 15)
        st.metric("Leseminuten gesamt ⏱️", f"{ges_min} min")
    with m3: st.metric("Aktive Spieler 🏃‍♂️", df['Full_ID'].nunique() if 'Full_ID' in df.columns else 0)
    st.markdown("---")

# --- 7. SIDEBAR (MIT INFOTEXT) ---
st.sidebar.header("👟 Spieler-Kabine")
st.sidebar.info("""
**So sammelst du Punkte:**
1. Trage deinen Namen ein & wähle dein Team.
2. Wähle Lesezeit oder ein fertiges Buch.
3. Bestätige deine Angaben und klicke auf 'Eintragen'.

*Hinweis: Lesezeit ist auf 20 Punkte pro Woche begrenzt.*
""")

v_input = st.sidebar.text_input("Vorname:", key="v_in").strip()
n_input = st.sidebar.text_input("Nachname:", key="n_in").strip()
t_liste = ["-- Bitte wählen --", "Ahaus/Coesfeld I", "Ahaus/Coesfeld II", "Arnsberg/Soest", "Beckum", "Bielefeld", "Bochum", "Detmold", "Dortmund", "Gelsenkirchen", "Gütersloh", "Hagen", "Herford", "Herne", "Hochsauerlandkreis", "Höxter", "Lemgo", "Lippstadt", "Lübbecke/Minden", "Lüdenscheid/Iserlohn", "Münster I", "Münster II", "Olpe", "Paderborn", "Recklinghausen", "Siegen/Wittgenstein", "Steinfurt", "Tecklenburg", "Unna/Hamm"]
team_choice = st.sidebar.selectbox("Dein Stützpunkt:", t_liste, key="t_in")

if v_input and n_input and team_choice != "-- Bitte wählen --":
    search_id = f"{v_input.lower()} {n_input.lower()}"
    kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
    
    # NEU: Team-Abgleich prüfen
    assigned_team = None
    if not df.empty:
        prev_entries = df[df['Full_ID'] == search_id]
        if not prev_entries.empty:
            assigned_team = prev_entries.iloc[0]['Team']

    # Wochenpunkte für das Limit prüfen
    akt_m = 0
    if not df.empty:
        akt_m = df[(df['Full_ID'] == search_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min|Min"))]["Punkte"].sum()
    
    st.sidebar.metric("Deine Wochen-Punkte (Zeit)", f"{int(akt_m)} / {LIMIT_MINUTEN}")
    
    # Validierung: Hat der Spieler ein anderes Team gewählt?
    if assigned_team and assigned_team != team_choice:
        st.sidebar.error(f"Achtung! Du bist bereits für das Team **{assigned_team}** registriert. Du kannst dein Team nicht wechseln.")
    else:
        kat = st.sidebar.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"])
        
        with st.sidebar.form("entry_form", clear_on_submit=True):
            if kat == "Lesezeit (Minuten)":
                auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"])
                p = 2 if "30" in auswahl else 4
            else:
                auswahl = st.selectbox("Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"])
                p = 5 if "100" in auswahl else 10 if "200" in auswahl else 15
                
            confirm = st.checkbox("Ich bestätige meine Angaben.")
            if st.form_submit_button("Eintragen"):
                if not confirm:
                    st.error("Bitte Haken setzen!")
                elif kat == "Lesezeit (Minuten)" and (akt_m + p) > LIMIT_MINUTEN:
                    st.error(f"Limit erreicht! Du hast diese Woche bereits {int(akt_m)} Punkte.")
                elif worksheet:
                    worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), v_input, n_input, team_choice, "Lesen", auswahl, p])
                    st.sidebar.success("Gespeichert!")
                    st.cache_resource.clear()
                    st.rerun()

# --- 8. TABELLEN ---
col_tab1, col_tab2 = st.columns([1, 1.2])
with col_tab1:
    st.subheader("🏆 Team-Tabelle", anchor=False)
    ranking_data = get_capped_ranking(df)
    if not ranking_data.empty: 
        st.table(ranking_data.set_index("Team").style.format({"Durchschnitt": "{:.2f}"}))
    else: st.write("Noch keine Daten vorhanden.")

with col_tab2:
    st.subheader("📜 Letzte Aktivitäten", anchor=False)
    if not df.empty:
        st.dataframe(df.iloc[::-1][["Datum", "Team", "Details", "Punkte"]].head(10), use_container_width=True, hide_index=True)

st.markdown("---")
with st.expander("⚖️ Datenschutz & Impressum"):
    st.write("**Verantwortlich:** FLVW. Daten werden nur für den Wettbewerb genutzt.")
