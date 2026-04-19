import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- DIAGNOSE (Das löschen wir, wenn es läuft) ---
st.write("Verfügbare Secrets-Bereiche:", list(st.secrets.keys()))

# --- SETUP ---
st.set_page_config(page_title="Kicken beginnt im Kopf", layout="wide")

# VERBINDUNGSAUFBAU
# Hier zwingen wir die App, die "gsheets" Secrets zu nutzen
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Wir lesen die Daten. ttl=0 stellt sicher, dass wir nicht in alten Fehlern hängen
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("⚠️ Die Verbindung klappt noch nicht!")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- TITEL ---
st.title("⚽ Kicken beginnt im Kopf")

# --- EINGABE-BEREICH ---
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("spiel_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Ergebnis:", ["30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)", "Rezension (5 Pkt)"])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        # Punkte berechnen
        pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
        
        # Neue Zeile erstellen
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%d.%m.%Y"),
            "Kind": name,
            "Team": team,
            "Typ": "Lesen",
            "Details": ergebnis,
            "Punkte": pkt
        }])
        
        try:
            # Daten zusammenführen und hochladen
            df_aktualisiert = pd.concat([df, neuer_eintrag], ignore_index=True)
            conn.update(data=df_aktualisiert)
            st.sidebar.success("✅ Tor erzielt! (Gespeichert)")
            st.rerun()
        except Exception as e:
            st.sidebar.error("❌ Schreibfehler!")
            st.sidebar.code(str(e))

# --- TABELLE ANZEIGEN ---
st.header("🏆 Aktueller Spielstand")
if not df.empty:
    # Eine kleine Zusammenfassung nach Teams
    tabelle_auswertung = df.groupby("Team")["Punkte"].sum().reset_index().sort_values("Punkte", ascending=False)
    st.table(tabelle_auswertung)
    
    st.subheader("Einzelne Einträge")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Daten in der Tabelle gefunden.")
