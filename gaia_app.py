import streamlit as st
import pandas as pd
from utils import elabora_dati, calcola_metriche, genera_suggerimenti

st.set_page_config(page_title="Monitoraggio Glicemico", layout="wide")

st.title("📊 Dashboard Glicemica")

# Sidebar per i parametri
st.sidebar.header("Parametri")
target_min = st.sidebar.number_input("Target Minimo (mg/dL)", value=70)
target_max = st.sidebar.number_input("Target Massimo (mg/dL)", value=180)

uploaded_file = st.file_uploader("Carica il file CSV di FreeStyle Libre", type="csv")

if uploaded_file is not None:
    # Elaborazione
    df_raw = pd.read_csv(uploaded_file, skiprows=1) # Usiamo skiprows=1 come identificato nel tuo file
    df = elabora_dati(df_raw)
    
    # Metriche in alto
    metriche = calcola_metriche(df, target_min, target_max)
    col1, col2, col3 = st.columns(3)
    col1.metric("TIR (Time in Range)", f"{metriche['TIR']:.1f}%")
    col2.metric("Tempo in Ipo", f"{metriche['Percentuale Ipo']:.1f}%")
    col3.metric("Tempo in Iper", f"{metriche['Percentuale Iper']:.1f}%")
    
    # Suggerimenti clinici
    st.subheader("💡 Analisi e Suggerimenti")
    suggerimenti = genera_suggerimenti(df, target_min, target_max)
    for s in suggerimenti:
        st.info(s)
else:
    st.write("Per favore, carica il file CSV per iniziare l'analisi.")
