import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# Header
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Die offizielle Sommer-Leseliga des FLVW</p>", unsafe_allow_html=True)
st.markdown("---")

# Verbindung
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Wir lesen das Sheet ohne Cache (ttl=0), um immer live zu sein
        return conn.read(ttl="0s")
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

df_aktuell = load_data()
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# Sidebar
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("lese_form", clear_on_submit=True):
    team_auswahl = st.selectbox("Team wählen:", teams)
    kind_name = st.text_input("Name des Kindes:")
    option = st.selectbox("Was wurde erreicht?", [
        "30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)",
        "Buch bis 100 Seiten (4 Pkt)", "Buch 101 bis 200 Seiten (8 Pkt)",
        "Buch über 201 Seiten (12 Pkt)", "Lieblingsbuch + Mini-Rezension (5 Pkt)"
    ])
    submit = st.form_submit_button("Ergebnis eintragen")
    
    if submit and kind_name:
        pkt_map = {
            "30 min Lesen (2 Pkt)": 2, "60 min Lesen (4 Pkt)": 4,
            "Buch bis 100 Seiten (4 Pkt)": 4, "Buch 101 bis 200 Seiten (8 Pkt)": 8,
            "Buch über 201 Seiten (12 Pkt)": 12, "Lieblingsbuch + Mini-Rezension (5 Pkt)": 5
        }
        
        neuer_eintrag = pd.DataFrame([{
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": kind_name, "Team": team_auswahl,
            "Typ": "Lesen" if "min" in option else "Bonus",
            "Details": option, "Punkte": pkt_map[option]
        }])
        
        try:
            # Kombinieren und hochladen
            df_updated = pd.concat([df_aktuell, neuer_eintrag], ignore_index=True)
            conn.update(data=df_updated)
            st.sidebar.success("TOR! Gespeichert.")
            st.rerun()
        except Exception as e:
            st.sidebar.error("❌ Google blockiert immer noch!")
            st.sidebar.write(f"Technischer Fehler: {e}")
            st.sidebar.info("TIPP: Wenn 'Mitbearbeiter' aktiv ist, versuche im Sheet unter 'Teilen' -> 'Zahnrad-Symbol' den Haken bei 'Editoren können Berechtigungen ändern' zu setzen.")

# Layout & Statistik (Tabelle und Balken)
col_main, col_stat = st.columns([2, 1])

def berechne_punkte(team_df):
    if team_df is None or team_df.empty: return 0
    # Punkte in Zahlen umwandeln
    team_df["Punkte"] = pd.to_numeric(team_df["Punkte"], errors='coerce').fillna(0)
    bonus = team_df[team_df["Typ"] == "Bonus"]["Punkte"].sum()
    lese_df = team_df[team_df["Typ"] == "Lesen"].copy()
    wochen_lese = lese_df.groupby(["Kind", "Datum"])["Punkte"].sum().clip(upper=20).sum() if not lese_df.empty else 0
    return int(bonus + wochen_lese)

with col_main:
    st.header("🏆 Die aktuelle Tabelle")
    scores = []
    for t in teams:
        s = berechne_punkte(df_aktuell[df_aktuell["Team"] == t])
        scores.append({"Team": t, "Punkte": s})
    
    tabelle_df = pd.DataFrame(scores).sort_values("Punkte", ascending=False).reset_index(drop=True)
    tabelle_df.index += 1
    st.table(tabelle_df)

with col_stat:
    st.header("📊 Statistik")
    gesamt = sum([item["Punkte"] for item in scores])
    st.metric("Punkte insgesamt", f"{gesamt}")
    st.progress(min(gesamt / 1000, 1.0))
    st.write(f"Noch {max(1000 - gesamt, 0)} Punkte bis zum Stadion-Ziel!")
