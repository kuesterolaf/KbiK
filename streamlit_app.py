import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# --- SYSTEM-CHECK (Expander) ---
with st.expander("System-Status prüfen"):
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        st.success(f"✅ Bot erkannt: {st.secrets['connections']['gsheets'].get('client_email')}")
    else:
        st.error("❌ Secrets nicht gefunden oder falsch formatiert!")

# VERBINDUNG AUFBAUEN
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Daten lesen (Wichtig: ttl=0 damit wir immer frische Daten haben)
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Verbindung zum Sheet fehlgeschlagen")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

st.title("⚽ Kicken beginnt im Kopf")

# --- SEITENLEISTE: EINGABE ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("spiel_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        # Punkte zuweisen
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        
        # Neuen Eintrag als DataFrame erstellen
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%d.%m.%Y"),
            "Kind": name,
            "Team": team,
            "Typ": "Lesen",
            "Details": ergebnis,
            "Punkte": pkt
        }])
        
        try:
            # DATEN ANFÜGEN & HOCHLADEN
            # Wir nutzen hier .update() und steuern gezielt "Sheet1" an
            df_neu = pd.concat([df, neuer_eintrag], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_neu)
            
            st.sidebar.success("✅ Erfogreich gespeichert!")
            st.rerun() # App neu laden um Tabelle zu aktualisieren
        except Exception as e:
            st.sidebar.error("❌ Schreibfehler!")
            st.sidebar.code(str(e))

# --- HAUPTBEREICH: TABELLE ---
st.header("🏆 Aktueller Spielstand")
if not df.empty:
    # Ranking berechnen
    ranking = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
    st.table(ranking)
    
    with st.expander("Alle Details anzeigen"):
        st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Einträge vorhanden. Sei der Erste!")
