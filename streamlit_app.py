import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SEITE ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# Header
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("---")

# VERBINDUNG ERZWINGEN
# Wir nutzen hier exakt den Namen aus deinen Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# DATEN LADEN (Ohne Zwischenspeicher)
try:
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Konnte Daten nicht laden. Prüfe die Secrets!")
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# TEAMS
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# EINGABE
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    team = st.selectbox("Team:", teams)
    name = st.text_input("Name des Kindes:")
    wahl = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        pkt = 2 if "30" in wahl else 4 if "60" in wahl else 5
        neue_zeile = pd.DataFrame([{
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": name, "Team": team, "Typ": "Lesen", "Details": wahl, "Punkte": pkt
        }])
        
        try:
            # Hier passiert das Schreiben
            df_neu = pd.concat([df, neue_zeile], ignore_index=True)
            conn.update(data=df_neu)
            st.sidebar.success("Eingetragen! Lade Tabelle neu...")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Fehler!")
            st.sidebar.code(str(e)) # Zeigt uns den exakten technischen Fehler

# ANZEIGE
st.header("🏆 Tabelle")
if not df.empty:
    # Einfache Berechnung für die Demo
    tabelle = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
    st.table(tabelle)
else:
    st.info("Noch keine Daten vorhanden.")
