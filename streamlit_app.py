import streamlit as st
import pandas as pd
from datetime import datetime
import base64

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# Hilfsfunktion für die Logos
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except:
        return None

img_kbik = get_image_base64("KbiK-Logo.jpg")
img_flvw = get_image_base64("Logo-FLVW (1).svg")

# --- HEADER: LOGOS AUF EXAKT EINER LINIE ---
if img_kbik and img_flvw:
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0px;">
            <img src="data:image/jpeg;base64,{img_kbik}" style="height: 100px;">
            <div style="text-align: center;">
                <h1 style="margin: 0; color: #1E3A8A;">⚽ Kicken beginnt im Kopf</h1>
                <p style="margin: 0; font-weight: bold; color: #555;">Die offizielle Sommer-Leseliga des FLVW</p>
            </div>
            <img src="data:image/svg+xml;base64,{img_flvw}" style="height: 100px;">
        </div>
        <hr style="margin-top: 0px;">
        """,
        unsafe_allow_html=True
    )
else:
    st.title("⚽ Kicken beginnt im Kopf")
    st.info("Hinweis: Laden Sie noch 'KbiK-Logo.jpg' und 'Logo-FLVW (1).svg' bei GitHub hoch.")

# --- DATEN-STRUKTUR ---
if 'liga_daten' not in st.session_state:
    st.session_state.liga_daten = pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

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
    
    if submit:
        pkt_map = {
            "30 min Lesen (2 Pkt)": 2, "60 min Lesen (4 Pkt)": 4,
            "Buch bis 100 Seiten (4 Pkt)": 4, "Buch 101 bis 200 Seiten (8 Pkt)": 8,
            "Buch über 201 Seiten (12 Pkt)": 12, "Lieblingsbuch + Mini-Rezension (5 Pkt)": 5
        }
        neuer_eintrag = {
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": kind_name, "Team": team_auswahl,
            "Typ": "Lesen" if "min Lesen" in option else "Bonus",
            "Details": option, "Punkte": pkt_map[option]
        }
        st.session_state.liga_daten = pd.concat([st.session_state.liga_daten, pd.DataFrame([neuer_eintrag])], ignore_index=True)
        st.sidebar.success(f"Tor für {team_auswahl}!")

# --- TABELLE & LOGIK ---
df = st.session_state.liga_daten.copy()

def berechne_team_punkte(team_df):
    bonus = team_df[team_df["Typ"] == "Bonus"]["Punkte"].sum()
    lese_df = team_df[team_df["Typ"] == "Lesen"]
    if not lese_df.empty:
        # Deckelung auf 20 Pkt pro Woche/Kind laut Entwurf 
        wochen_lese_pkt = lese_df.groupby(["Kind", "Datum"])["Punkte"].sum().clip(upper=20).sum()
    else:
        wochen_lese_pkt = 0
    return bonus + wochen_lese_pkt

main_col, stat_col = st.columns([2, 1])

with main_col:
    st.header("🏆 Die aktuelle Tabelle")
    if not df.empty:
        team_scores = [{"Team": t, "Punkte": int(berechne_team_punkte(df[df["Team"] == t]))} for t in teams]
        tabelle_df = pd.DataFrame(team_scores).sort_values(by="Punkte", ascending=False).reset_index(drop=True)
        tabelle_df.index += 1
        st.table(tabelle_df)
    else:
        st.info("Der Anpfiff ist erfolgt – viel Spaß beim Lesen!")

with stat_col:
    st.header("📊 Statistik")
    if not df.empty:
        gesamt = sum([berechne_team_punkte(df[df["Team"] == t]) for t in teams])
        st.metric("Punkte insgesamt", f"{int(gesamt)}")
        st.write("**Stadion-Ziel (1000 Pkt):**")
        st.progress(min(gesamt / 1000, 1.0))

# --- REGELN ---
with st.expander("📝 Regeln & Punktesystem"):
    st.write("**Fair Play:** Seid ehrlich beim Eintragen! [cite: 166, 167]")
    st.write("**Punkte:**")
    st.write("- **Lesen:** Maximal 20 Punkte pro Woche und Kind. ")
    st.write("- **Bücher:** Seitenabhängige Punkte zählen immer voll. [cite: 177, 198]")
