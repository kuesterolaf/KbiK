import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. KONFIGURATION & KONSTANTEN ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# Wichtig: Diese Variable muss vor der Logik definiert sein!
LIMIT_MINUTEN = 20 
SPALTEN = ["Datum", "Vorname", "Nachname", "Team", "Typ", "Details", "Punkte"]

# --- 2. DESIGN UPGRADE (CSS) ---
st.markdown("""
    <style>
    /* Sidebar: FLVW-Rot und weiße Schrift für alles */
    [data-testid="stSidebar"] { 
        background-color: #E31E24 !important; 
    }
    [data-testid="stSidebar"] * { 
        color: white !important; 
    }
    /* Spezieller Fix für Radio-Buttons, Checkboxen und Texte in der Sidebar */
    [data-testid="stSidebar"] .stRadio label p, 
    [data-testid="stSidebar"] label p, 
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] [data-testid="stMetricValue"] { 
        color: white !important; 
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] div:first-child, 
    [data-testid="stSidebar"] [data-baseweb="checkbox"] div:first-child { 
        border-color: white !important; 
    }
    /* Eingabefelder in der Sidebar: Weißer Hintergrund, dunkler Text für Lesbarkeit */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] [data-baseweb="select"] div { 
        background-color: white !important; 
        color: #31333F !important; 
    }

    /* Zentrierter Header & Logo-Abstände */
    .header-container { text-align: center; margin-top: -40px; }
    .tight-title { margin-top: -15px !important; line-height: 1.1; font-weight: bold; }
    .tight-subtitle { margin-top: -10px !important; color: #666; font-style: italic; }

    /* Metriken & Buttons */
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        border: 1px solid #f0f2f6; 
    }
    div.stButton > button:first-child { 
        background-color: #ffffff !important; 
        color: #E31E24 !important; 
        border: none !important; 
        font-weight: bold !important; 
        width: 100%; 
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATENBANK-ANBINDUNG ---
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
            df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y', errors='coerce')
            df['KW'] = df['Datum_dt'].dt.isocalendar().week
            df['Jahr'] = df['Datum_dt'].dt.isocalendar().year
            df["Punkte"] = pd.to_numeric(df["Punkte"], errors='coerce').fillna(0)
            df['Full_ID'] = df['Vorname'].astype(str).str.lower().str.strip() + " " + df['Nachname'].astype(str).str.lower().str.strip()
        return df, ws
    except Exception: return pd.DataFrame(columns=SPALTEN), None

df, worksheet = load_data()

# --- 4. RANKING-LOGIK ---
def get_capped_ranking(df_full):
    if df_full.empty or "Team" not in df_full.columns: return pd.DataFrame()
    df_full['Kind_ID'] = df_full['Vorname'].astype(str) + " " + df_full['Nachname'].astype(str)
    mask_min = df_full["Details"].str.contains("min|Min", na=False, case=False)
    
    # Minuten mit Cap
    df_min = df_full[mask_min].copy()
    if not df_min.empty:
        m_sum = df_min.groupby(['Jahr', 'KW', 'Kind_ID', 'Team'])['Punkte'].sum().reset_index()
        m_sum['Punkte'] = m_sum['Punkte'].clip(upper=LIMIT_MINUTEN)
        p_min = m_sum.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    else: p_min = pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    # Bücher ohne Cap
    df_extra = df_full[~mask_min].copy()
    p_extra = df_extra.groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index() if not df_extra.empty else pd.DataFrame(columns=["Kind_ID", "Team", "Punkte"])
    
    total = pd.concat([p_min, p_extra]).groupby(['Kind_ID', 'Team'])['Punkte'].sum().reset_index()
    if total.empty: return pd.DataFrame()
    
    stats = total.groupby('Team').agg(Gesamt=('Punkte', 'sum'), Spieler=('Kind_ID', 'nunique')).reset_index()
    stats['Durchschnitt'] = (stats['Gesamt'] / stats['Spieler']).round(2)
    return stats[['Team', 'Durchschnitt', 'Spieler']].sort_values("Durchschnitt", ascending=False)

# --- 5. HAUPTBEREICH: HEADER ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
with col_logo2:
    # Prüft nacheinander die möglichen Logo-Dateinamen
    if os.path.exists("KbiK-Logo.jpg"):
        st.image("KbiK-Logo.jpg", use_container_width=True)
    elif os.path.exists("flvw-logo.png"):
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

# --- 7. SIDEBAR: EINGABE ---
st.sidebar.header("👟 Spieler Kabine")
st.sidebar.info("**So sammelst du Punkte:**\n1. Name & Team eingeben.\n2. Lesezeit oder Buch wählen.\n3. Haken setzen & 'Eintragen'.")

v_name = st.sidebar.text_input("Vorname:", key="v_final").strip()
n_name = st.sidebar.text_input("Nachname:", key="n_final").strip()
t_liste = ["-- Bitte wählen --", "Ahaus/Coesfeld I", "Ahaus/Coesfeld II", "Arnsberg/Soest", "Beckum", "Bielefeld", "Bochum", "Detmold", "Dortmund", "Gelsenkirchen", "Gütersloh", "Hagen", "Herford", "Herne", "Hochsauerlandkreis", "Höxter", "Lemgo", "Lippstadt", "Lübbecke/Minden", "Lüdenscheid/Iserlohn", "Münster I", "Münster II", "Olpe", "Paderborn", "Recklinghausen", "Siegen/Wittgenstein", "Steinfurt", "Tecklenburg", "Unna/Hamm"]
team_choice = st.sidebar.selectbox("Dein Stützpunkt:", t_liste, key="t_final")

if v_name and n_name and team_choice != "-- Bitte wählen --":
    current_id = f"{v_name.lower()} {n_name.lower()}"
    kw, jahr = datetime.now().isocalendar()[1], datetime.now().isocalendar()[0]
    
    akt_m = 0
    if not df.empty and 'Full_ID' in df.columns:
        akt_m = df[(df['Full_ID'] == current_id) & (df["KW"] == kw) & (df["Jahr"] == jahr) & (df["Details"].str.contains("min|Min"))]["Punkte"].sum()
    
    st.sidebar.metric("Deine Wochen-Punkte", f"{int(akt_m)} / {LIMIT_MINUTEN}")
    kat = st.sidebar.radio("Was meldest du?", ["Lesezeit (Minuten)", "Buch abgeschlossen 🏆"], key="k_final")
    
    with st.sidebar.form("entry_form"):
        if kat == "Lesezeit (Minuten)":
            auswahl = st.selectbox("Dauer:", ["30 min gelesen (2 Pkt)", "60 min gelesen (4 Pkt)"], key="m_final")
            p = 2 if "30" in auswahl else 4
        else:
            auswahl = st.selectbox("Umfang:", ["Buch bis 100 S. (5 Pkt)", "Buch bis 200 S. (10 Pkt)", "Buch über 200 S. (15 Pkt)"], key="b_final")
            p = 5 if "100" in auswahl else 10 if "bis 200" in auswahl else 15
            
        confirm = st.checkbox("Ich bestätige meine Angaben.")
        if st.form_submit_button("Eintragen"):
            if not confirm:
                st.error("Bitte Haken setzen!")
            elif kat == "Lesezeit (Minuten)" and (akt_m + p) > LIMIT_MINUTEN:
                st.error("Wochenlimit erreicht!")
            elif worksheet:
                worksheet.append_row([datetime.now().strftime("%d.%m.%Y"), v_name, n_name, team_choice, "Lesen", auswahl, p])
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
    else:
        st.write("Warte auf Daten...")

with col_tab2:
    st.subheader("📜 Letzte Aktivitäten", anchor=False)
    if not df.empty:
        st.dataframe(df.iloc[::-1][["Datum", "Team", "Details", "Punkte"]].head(10), use_container_width=True, hide_index=True)

# --- 9. FUSSZEILE ---
st.markdown("---")
with st.expander("⚖️ Datenschutz & Impressum"):
    st.write("**Verantwortlich:** FLVW. Daten werden nur für den Wettbewerb genutzt.")
st.info("ℹ️ Team-Power: Durchschnittliche Punkte pro Spieler.")
