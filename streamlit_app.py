import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# --- DIAGNOSE-BEREICH ---
with st.expander("System-Check (Falls es hakt)"):
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        st.success(f"✅ Bot-Verbindung konfiguriert: {st.secrets['connections']['gsheets'].get('client_email')}")
    else:
        st.error("❌ Die Secrets sind nicht korrekt hinterlegt oder benannt.")

# --- VERBINDUNG ZUM SHEET ---
try:
    # Erstellt die Verbindung basierend auf [connections.gsheets] in den Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Liest die Daten aus dem Sheet (ttl=0 verhindert alte Daten im Speicher)
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("Verbindung zum Google Sheet fehlgeschlagen.")
    st.code(str(e))
    df = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

# --- HEADER ---
st.markdown("<h1 style='text-align: center;'>⚽ Kicken beginnt im Kopf ⚽</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Die Leseliga-Meisterschaft</h3>", unsafe_allow_html=True)
st.markdown("---")

# --- EINGABE-BEREICH (SIDEBAR) ---
st.sidebar.header("👟 Spielereingabe")
with st.sidebar.form("lese_form", clear_on_submit=True):
    name = st.text_input("Name des Kindes:")
    team = st.selectbox("Team:", ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"])
    ergebnis = st.selectbox("Was wurde geschafft?", [
        "30 min Lesen (2 Pkt)", 
        "60 min Lesen (4 Pkt)", 
        "Rezension geschrieben (5 Pkt)"
    ])
    
    submit = st.form_submit_button("Eintrag speichern")

    if submit:
        if name:
            # Punkte zuweisen
            pkt = 2 if "30" in ergebnis else 4 if "60" in ergebnis else 5
            
            # Neuen Eintrag vorbereiten
            neuer_eintrag = pd.DataFrame([{
                "Datum": datetime.now().strftime("%d.%m.%Y"),
                "Kind": name,
                "Team": team,
                "Typ": "Lesen",
                "Details": ergebnis,
                "Punkte": pkt
            }])
            
            try:
                # Bestehende Daten mit neuem Eintrag kombinieren
                df_aktualisiert = pd.concat([df, neuer_eintrag], ignore_index=True)
                
                # Zurück in das Google Sheet schreiben
                conn.update(data=df_aktualisiert)
                
                st.sidebar.success(f"✅ Tor für {name}! Gespeichert.")
                st.rerun()
            except Exception as e:
                st.sidebar.error("❌ SCHREIBFEHLER!")
                st.sidebar.info("Prüfe, ob der Bot im Google Sheet als 'Mitbearbeiter' hinzugefügt wurde.")
                st.sidebar.code(str(e))
        else:
            st.sidebar.warning("Bitte gib einen Namen ein.")

# --- AUSWERTUNG & TABELLE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🏆 Tabelle")
    if not df.empty:
        # Punkte pro Team zusammenrechnen
        ranking = df.groupby("Team")["Punkte"].sum().reset_index()
        ranking = ranking.sort_values(by="Punkte", ascending=False)
        st.table(ranking.set_index("Team"))
    else:
        st.info("Noch keine Daten vorhanden.")

with col2:
    st.subheader("📊 Letzte Aktivitäten")
    if not df.empty:
        # Die neuesten Einträge oben anzeigen
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.write("Sobald jemand liest, erscheinen hier die Details.")

# --- FUSSZEILE ---
st.markdown("---")
st.caption("Powered by Streamlit & Google Sheets API")
