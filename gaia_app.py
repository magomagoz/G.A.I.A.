import streamlit as st
import pandas as pd
from utils import elabora_dati, calcola_metriche, genera_suggerimenti

st.set_page_config(page_title="Diabete Dashboard", layout="wide")
st.title("🩺 Assistente Diabetico Personale")

# Tab Layout
tab1, tab2, tab3 = st.tabs(["Dashboard", "Calcolatore Pasti", "Analisi Trend"])

with tab1:
    uploaded_file = st.file_uploader("Carica il tuo CSV LibreView", type="csv")
    if uploaded_file:
        df = elabora_dati(pd.read_csv(uploaded_file, skiprows=1))
        m = calcola_metriche(df, 70, 180)
        col1, col2, col3 = st.columns(3)
        col1.metric("TIR", f"{m['TIR']:.1f}%")
        col2.metric("Ipo", f"{m['IPO']:.1f}%")
        col3.metric("Iper", f"{m['IPER']:.1f}%")
        
        st.subheader("Suggerimenti Clinici")
        for s in genera_suggerimenti(df):
            st.info(s)

with tab2:
    st.subheader("Calcolatore Bolo Rapido")
    cibo = st.selectbox("Seleziona alimento", ["Barretta Kinder (12g)", "Succo di frutta (20g)", "Panino (45g)"])
    ic = st.number_input("Tuo rapporto I:C (es. 10)", value=10)
    if st.button("Calcola"):
        carbs = int(cibo.split('(')[1].replace('g)', ''))
        st.write(f"Dovresti somministrare circa {carbs/ic:.1f} unità di Novorapid.")

with tab3:
    st.write("Qui caricheremo l'analisi storica dei picchi post-prandiali.")
