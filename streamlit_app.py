import streamlit as st
import pandas as pd

# --- KONFIGURATION & STYLING ---
st.set_page_config(page_title="Kicken beginnt im Kopf", page_icon="⚽")

# Individuelles CSS für Fußball-Vibe
st.markdown("""
    <style>
    .main { background-color: #f0f8f0; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 20px; }
    h1 { color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚽ Kicken beginnt im Kopf")
st.subheader("Die Sommer-Leseliga für Champions")

# --- DATEN-BACKEND (Simulation) ---
# In der finalen Version verbinden wir das mit einem Google Sheet
if 'liga_daten' not in st.session_state:
    st.session_state.liga_daten = pd.DataFrame(columns=["Kind", "Team", "Tore"])

teams = ["Eintracht Vorleser", "FC Bücherwurm", "Rasenball Lesen", "SpVgg Buchdeckel"]

# --- SIDEBAR: SPIELERKABINE (Eingabe) ---
st.sidebar.header("👟 Spielerkabine")
st.sidebar.write("Eltern: Tragt hier die Treffer eurer Kinder ein.")

with st.sidebar.form("treffer_form"):
    team_auswahl = st.selectbox("Team wählen:", teams)
    kind_name = st.text_input("Name des Kindes (intern):")
    aktion = st.radio("Was wurde geschafft?", ["15 Min. Lesen (1 Tor)", "Buch beendet (5 Tore)"])
    
    submit = st.form_submit_button("Treffer verbuchen!")
    
    if submit:
        tore = 1 if "15 Min" in aktion else 5
        neuer_eintrag = {"Kind": kind_name, "Team": team_auswahl, "Tore": tore}
        st.session_state.liga_daten = pd.concat([st.session_state.liga_daten, pd.DataFrame([neuer_eintrag])], ignore_index=True)
        st.sidebar.success(f"Tor für {team_auswahl}!")

# --- HAUPTPREICH: TABELLE & STADION ---
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🏆 Die Liga-Tabelle")
    if not st.session_state.liga_daten.empty:
        # Gruppierung nach Team
        tabelle = st.session_state.liga_daten.groupby("Team")["Tore"].sum().reset_index()
        tabelle = tabelle.sort_values(by="Tore", ascending=False).reset_index(drop=True)
        tabelle.index += 1 # Rangliste bei 1 starten lassen
        st.table(tabelle)
    else:
        st.info("Der Anpfiff ist erfolgt! Wartet auf die ersten Tore...")

with col2:
    st.header("🏟️ Stadion-Ziel")
    gesamt_tore = st.session_state.liga_daten["Tore"].sum()
    ziel = 500  # Beispielhaftes Saisonziel
    fortschritt = min(gesamt_tore / ziel, 1.0)
    
    st.metric("Tore insgesamt", f"{int(gesamt_tore)}")
    st.progress(fortschritt)
    st.write(f"Gemeinsames Ziel: {ziel} Tore")

# --- TEAM-DYNAMIK (Grafik) ---
if not st.session_state.liga_daten.empty:
    st.write("---")
    st.header("📊 Team-Vergleich")
    st.bar_chart(data=tabelle, x="Team", y="Tore")
