import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽", layout="wide")

# Header (Altes Design)
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚽ Kicken beginnt im Kopf</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Die offizielle Sommer-Leseliga des FLVW</p>", unsafe_allow_html=True)
st.markdown("---")

# Verbindung herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

# Daten laden
def get_data():
    try:
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame(columns=["Datum", "Kind", "Team", "Typ", "Details", "Punkte"])

df = get_data()
teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# Sidebar Eingabe
st.sidebar.header("👟 Spielerkabine")
with st.sidebar.form("input_form", clear_on_submit=True):
    team = st.selectbox("Team:", teams)
    name = st.text_input("Name des Kindes:")
    wahl = st.selectbox("Ergebnis:", [
        "30 min Lesen (2 Pkt)", "60 min Lesen (4 Pkt)",
        "Buch bis 100 S. (4 Pkt)", "Buch bis 200 S. (8 Pkt)",
        "Buch über 200 S. (12 Pkt)", "Rezension (5 Pkt)"
    ])
    submit = st.form_submit_button("Eintragen")

    if submit and name:
        punkte = 2 if "30 min" in wahl else 4 if "60 min" in wahl or "100 S." in wahl else 8 if "200 S." in wahl else 12 if "über 200" in wahl else 5
        
        neue_zeile = pd.DataFrame([{
            "Datum": datetime.now().strftime("%Y-%W"),
            "Kind": name, "Team": team,
            "Typ": "Lesen" if "min" in wahl else "Bonus",
            "Details": wahl, "Punkte": punkte
        }])
        
        try:
            # Daten zusammenfügen und ans Sheet senden
            df_neu = pd.concat([df, neue_zeile], ignore_index=True)
            conn.update(data=df_neu)
            st.sidebar.success("Gespeichert!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Fehler beim Schreiben!")
            st.sidebar.write("Bitte stelle sicher, dass das Google Sheet auf 'Jeder mit Link = Editor' steht.")

# Berechnung
def calc_score(t_name):
    t_df = df[df["Team"] == t_name]
    if t_df.empty: return 0
    t_df["Punkte"] = pd.to_numeric(t_df["Punkte"], errors='coerce').fillna(0)
    # Lese-Punkte deckeln (20 pro Kind/Woche)
    lese = t_df[t_df["Typ"] == "Lesen"]
    score_lese = lese.groupby(["Kind", "Datum"])["Punkte"].sum().clip(upper=20).sum() if not lese.empty else 0
    # Bonus-Punkte (Bücher)
    score_bonus = t_df[t_df["Typ"] == "Bonus"]["Punkte"].sum()
    return int(score_lese + score_bonus)

# Layout (Tabelle links, Statistik rechts)
c1, c2 = st.columns([2, 1])

with c1:
    st.header("🏆 Tabelle")
    results = [{"Team": t, "Punkte": calc_score(t)} for t in teams]
    tabelle = pd.DataFrame(results).sort_values("Punkte", ascending=False).reset_index(drop=True)
    tabelle.index += 1
    st.table(tabelle)

with c2:
    st.header("📊 Gesamt")
    total = sum([r["Punkte"] for r in results])
    st.metric("Punkte", total)
    st.progress(min(total/1000, 1.0))
