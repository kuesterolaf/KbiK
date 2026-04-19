import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# --- DIAGNOSE-BOX ---
with st.expander("System-Check (nur für Fehlersuche)"):
    if "connections" in st.secrets:
        st.write("✅ Bereich 'connections' gefunden.")
        if "gsheets" in st.secrets["connections"]:
            st.write(f"✅ 'gsheets' Konfiguration vorhanden.")
            st.write(f"Bot-Email: {st.secrets['connections']['gsheets'].get('client_email', 'FEHLT')}")
    else:
        st.error("❌ 'connections' Bereich in den Secrets fehlt!")

# VERBINDUNG
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Verbindungsfehler")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

st.title("⚽ Kicken beginnt im Kopf")

# --- EINGABE ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("spiel_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%d.%m.%Y"),
            "Kind": name, "Team": team, "Typ": "Lesen", "Details": ergebnis, "Punkte": pkt
        }])
        
        try:
            df_neu = pd.concat([df, neuer_eintrag], ignore_index=True)
            conn.update(data=df_neu)
            st.sidebar.success("✅ Gespeichert!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Schreibfehler!")
            st.sidebar.code(str(e))

# --- TABELLE ---
st.header("🏆 Aktueller Spielstand")
if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten vorhanden.")
