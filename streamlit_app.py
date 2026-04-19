import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# --- EXPERTEN-DIAGNOSE ---
if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
    st.success(f"✅ Verbindung erkannt für: {st.secrets['connections']['gsheets'].get('client_email', 'E-Mail fehlt!')}")
else:
    st.error("❌ Secrets wurden geladen, aber der Bereich [connections.gsheets] fehlt oder ist falsch eingerückt!")

# VERBINDUNG
conn = st.connection("gsheets", type=GSheetsConnection)

# DATEN LADEN
try:
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Fehler beim Laden")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

st.title("⚽ Leseliga Live-Ticker")

# FORMULAR
with st.sidebar.form("input_form"):
    name = st.text_input("Name:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min (2 Pkt)", "60 min (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        neuer_eintrag = pd.DataFrame([{"Datum": datetime.now().strftime("%d.%m.%Y"), "Kind": name, "Team": team, "Punkte": pkt}])
        
        try:
            df_final = pd.concat([df, neuer_eintrag], ignore_index=True)
            conn.update(data=df_final)
            st.success("Gespeichert!")
            st.rerun()
        except Exception as e:
            st.error("Schreibfehler Details:")
            st.code(str(e))

# TABELLE
st.table(df)
    
    st.subheader("Einzelne Einträge")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten in der Tabelle gefunden.")
