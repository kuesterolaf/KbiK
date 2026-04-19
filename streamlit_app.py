import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)

# Verbindung
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="0s")

df_sheet = load_data()
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# Sidebar Formular
with st.sidebar.form("lese_form"):
    team_auswahl = st.selectbox("Team wählen:", teams)
    kind_name = st.text_input("Name des Kindes:")
    option = st.selectbox("Was wurde erreicht?", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Buch (Bonus)"])
    submit = st.form_submit_button("Ergebnis eintragen")
    
    if submit and kind_name:
        pkt = 2 if "30 min" in option else 4 if "60 min" in option else 10
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": kind_name, "Team": team_auswahl,
            "Typ": "Lesen" if "min" in option else "Bonus",
            "Details": option, "Punkte": pkt
        }])
        
        try:
            # Hier versuchen wir zu speichern
            updated_df = pd.concat([df_sheet, neuer_eintrag], ignore_index=True)
            conn.update(data=updated_df)
            st.sidebar.success("Gespeichert!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Schreibfehler! Hast du das Sheet für 'Jeder als Editor' freigegeben?")
            st.sidebar.code(str(e))

# Tabelle anzeigen
st.header("🏆 Tabelle")
if not df_sheet.empty:
    # Einfache Summe für die erste Ansicht
    tabelle = df_sheet.groupby("Team")["Punkte"].sum().reset_index()
    st.table(tabelle.sort_values("Punkte", ascending=False))
