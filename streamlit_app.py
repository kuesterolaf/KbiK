import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽")

st.title("⚽ Kicken beginnt im Kopf")
st.subheader("Die offizielle Sommer-Leseliga des FLVW")

# --- DATEN-STRUKTUR ---
if 'liga_daten' not in st.session_state:
    st.session_state.liga_daten = pd.DataFrame(columns=[
        "Datum", "Kind", "Team", "Typ", "Details", "Punkte"
    ])

# Die Teams laut deinem Projekt
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# --- SIDEBAR: SPIELERKABINE ---
st.sidebar.header("👟 Spielerkabine")
st.sidebar.info("Fair Play geht vor! Seid ehrlich beim Eintragen. ")

with st.sidebar.form("lese_form"):
    team_auswahl = st.selectbox("Team wählen:", teams)
    kind_name = st.text_input("Name des Kindes (intern):")
    
    # Punkteliste exakt nach Lesepass-Tabelle 
    option = st.selectbox("Was wurde erreicht?", [
        "30 min Lesen (2 Pkt)",
        "60 min Lesen (4 Pkt)",
        "Buch bis 100 Seiten (4 Pkt)",
        "Buch 101 bis 200 Seiten (8 Pkt)",
        "Buch über 201 Seiten (12 Pkt)",
        "Lieblingsbuch + Mini-Rezension (5 Pkt)"
    ])
    
    submit = st.form_submit_button("Ergebnis eintragen")
    
    if submit:
        # Punktezuordnung laut Tabelle 
        pkt_map = {
            "30 min Lesen (2 Pkt)": 2, 
            "60 min Lesen (4 Pkt)": 4,
            "Buch bis 100 Seiten (4 Pkt)": 4, 
            "Buch 101 bis 200 Seiten (8 Pkt)": 8,
            "Buch über 201 Seiten (12 Pkt)": 12, 
            "Lieblingsbuch + Mini-Rezension (5 Pkt)": 5
        }
        
        neuer_eintrag = {
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": kind_name,
            "Team": team_auswahl,
            "Typ": "Lesen" if "min Lesen" in option else "Bonus",
            "Details": option,
            "Punkte": pkt_map[option]
        }
        
        st.session_state.liga_daten = pd.concat([st.session_state.liga_daten, pd.DataFrame([neuer_eintrag])], ignore_index=True)
        st.sidebar.success(f"Eintrag für {team_auswahl} gespeichert!")

# --- LOGIK: WOCHEN-DECKELUNG & TABELLE ---
df = st.session_state.liga_daten.copy()

def berechne_team_punkte(team_df):
    # Bonus (Bücher/Rezension) zählt immer voll 
    bonus = team_df[team_df["Typ"] == "Bonus"]["Punkte"].sum()
    
    # Lese-Minuten werden pro Kind/Woche auf maximal 20 Pkt gedeckelt 
    lese_df = team_df[team_df["Typ"] == "Lesen"]
    if not lese_df.empty:
        wochen_lese_pkt = lese_df.groupby(["Kind", "Datum"])["Punkte"].sum().clip(upper=20).sum()
    else:
        wochen_lese_pkt = 0
    return bonus + wochen_lese_pkt

# --- HAUPTBEREICH ANZEIGE ---
st.header("🏆 Die aktuelle Tabelle")
if not df.empty:
    team_scores = []
    for t in teams:
        score = berechne_team_punkte(df[df["Team"] == t])
        team_scores.append({"Team": t, "Punkte": int(score)})
    
    tabelle_df = pd.DataFrame(team_scores).sort_values(by="Punkte", ascending=False).reset_index(drop=True)
    tabelle_df.index += 1
    st.table(tabelle_df)
    
    # Gesamtfortschritt
    gesamt = tabelle_df["Punkte"].sum()
    st.metric("Punkte insgesamt", f"{gesamt}")
    st.progress(min(gesamt / 1000, 1.0))
else:
    st.info("Noch keine Ergebnisse. Der Anpfiff ist erfolgt – viel Spaß beim Lesen! [cite: 33]")

# --- INFOS AUS DEM LESEPASS ---
with st.expander("📝 Regeln & Punktesystem"):
    st.write("**Punkte-Regeln:**")
    st.write("- **Lesen (Minuten):** Maximal 20 Punkte pro Woche und Kind. ")
    st.write("- **Bücher & Rezensionen:** Zählen zusätzlich und sind nicht gedeckelt. ")
    st.write("- **Fair Play:** Jede Minute zählt, aber seid ehrlich! [cite: 45, 46, 47]")
