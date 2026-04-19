import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# --- HEADER IM ALTEN STIL ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold; font-size: 1.2em;'>Die offizielle Sommer-Leseliga des FLVW</p>", unsafe_allow_html=True)
st.markdown("---")

# --- VERBINDUNG ZUM SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])
        return data
    except:
        return pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

df_sheet = load_data()
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# --- SIDEBAR: SPIELERKABINE ---
st.sidebar.header("👟 Spielerkabine")
st.sidebar.info("Fair Play geht vor! Seid ehrlich beim Eintragen.")

with st.sidebar.form("lese_form"):
    team_auswahl = st.selectbox("Team wählen:", teams)
    kind_name = st.text_input("Name des Kindes (intern):")
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
            "Typ": "Lesen" if "min Lesen" in option else "Bonus",
            "Details": option, "Punkte": pkt_map[option]
        }])
        
        updated_df = pd.concat([df_sheet, neuer_eintrag], ignore_index=True)
        conn.update(data=updated_df)
        st.sidebar.success(f"Tor für {team_auswahl}!")
        st.rerun()

# --- LOGIK: BERECHNUNG ---
def berechne_team_punkte(team_df):
    if team_df.empty: return 0
    team_df["Punkte"] = pd.to_numeric(team_df["Punkte"], errors='coerce').fillna(0)
    
    bonus = team_df[team_df["Typ"] == "Bonus"]["Punkte"].sum()
    lese_df = team_df[team_df["Typ"] == "Lesen"].copy()
    
    if not lese_df.empty:
        wochen_lese_pkt = lese_df.groupby(["Kind", "Datum"])["Punkte"].sum().clip(upper=20).sum()
    else:
        wochen_lese_pkt = 0
    return bonus + wochen_lese_pkt

# --- HAUPTBEREICH: ZWEI-SPALTEN-LAYOUT ---
col_main, col_stat = st.columns([2, 1])

with col_main:
    st.header("🏆 Die aktuelle Tabelle")
    team_scores = []
    for t in teams:
        score = berechne_team_punkte(df_sheet[df_sheet["Team"] == t])
        team_scores.append({"Team": t, "Punkte": int(score)})
    
    tabelle_df = pd.DataFrame(team_scores).sort_values(by="Punkte", ascending=False).reset_index(drop=True)
    tabelle_df.index += 1
    st.table(tabelle_df)

with col_stat:
    st.header("📊 Statistik")
    gesamt = sum([s["Punkte"] for s in team_scores])
    st.metric("Punkte insgesamt", f"{gesamt}")
    st.write("**Stadion-Ziel (1000 Pkt):**")
    st.progress(min(gesamt / 1000, 1.0))
    st.write(f"Noch {max(1000 - gesamt, 0)} Punkte bis zum Ziel!")

# --- REGELN ---
st.markdown("---")
with st.expander("📝 Regeln & Punktesystem"):
    st.write("**Punkte-Vergabe:**")
    st.write("- **Lesezeit:** Pro Kind und Woche maximal 20 Punkte.")
    st.write("- **Bücher & Rezensionen:** Diese Punkte zählen immer voll oben drauf.")
    st.write("- **Fair Play:** Seid ehrlich zu euch selbst und den anderen Teams!")
