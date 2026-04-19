import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# MANUELLE VERBINDUNG (Zwingt Streamlit, die Secrets zu nutzen)
@st.cache_resource
def get_connection():
    # Wir ziehen uns die Daten händisch aus den Secrets
    s = st.secrets["connections"]["gsheets"]
    return st.connection("gsheets", 
        type=GSheetsConnection,
        spreadsheet=s["spreadsheet"],
        project_id=s["project_id"],
        private_key_id=s["private_key_id"],
        private_key=s["private_key"],
        client_email=s["client_email"],
        client_id=s["client_id"],
        auth_uri=s["auth_uri"],
        token_uri=s["token_uri"],
        auth_provider_x509_cert_url=s["auth_provider_x509_cert_url"],
        client_x509_cert_url=s["client_x509_cert_url"]
    )

try:
    conn = get_connection()
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Verbindungsfehler!")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

st.title("⚽ Kicken beginnt im Kopf")

# --- EINGABE ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintrag speichern")

    if submit and name:
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%d.%m.%Y"),
            "Kind": name, "Team": team, "Typ": "Lesen", "Details": ergebnis, "Punkte": pkt
        }])
        
        try:
            df_aktualisiert = pd.concat([df, neuer_eintrag], ignore_index=True)
            # Hier schreiben wir explizit mit der erzwungenen Verbindung
            conn.update(data=df_aktualisiert)
            st.sidebar.success("✅ Gespeichert!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("❌ Fehler!")
            st.sidebar.code(str(e))

# --- TABELLE ---
if not df.empty:
    st.table(df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False))
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten vorhanden.")
