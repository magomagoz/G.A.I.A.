import os
from datetime import datetime
import json
import streamlit as st
import pandas as pd
from utils import elabora_dati, calcola_metriche, genera_suggerimenti

st.set_page_config(page_title="Diabete Dashboard", layout="wide")
st.image("banner.png")
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
    st.subheader("🍽️ Calcolatore Pasti Avanzato")
    
    # 1. Menu a tendina per il tipo di pasto
    tipo_pasto = st.selectbox("Momento della giornata", ["Colazione", "Pranzo", "Cena", "Spuntino"])
    
    # 2. Caricamento del database alimenti
    # Creiamo un dizionario di default nel caso il file non esista ancora
    try:
        with open('alimenti.json', 'r') as f:
            db_alimenti = json.load(f)
    except FileNotFoundError:
        db_alimenti = {"Barretta Kinder": 12, "Succo di frutta": 20, "Panino medio": 45, "Mela": 15}
    
    # Trasformiamo il dizionario in un DataFrame Pandas per la tabella
    df_alimenti = pd.DataFrame(list(db_alimenti.items()), columns=["Alimento", "Carboidrati (g)"])
    # Aggiungiamo una colonna di Checkbox all'inizio, impostata su False di default
    df_alimenti.insert(0, "Seleziona", False)
    
    st.write("Seleziona gli alimenti dal menu:")
    
    # 3. Tabella interattiva con quadratini da flaggare
    edited_df = st.data_editor(
        df_alimenti,
        hide_index=True, # Nasconde i numeri di riga per estetica
        use_container_width=True,
        column_config={
            "Seleziona": st.column_config.CheckboxColumn("Aggiungi", default=False),
            "Alimento": st.column_config.TextColumn("Alimento", disabled=True),
            "Carboidrati (g)": st.column_config.NumberColumn("Carboidrati (g)", disabled=True)
        }
    )
    
    # Input per il rapporto Insulina:Carboidrati
    ic = st.number_input("Tuo rapporto I:C (es. 1 U ogni 10g)", value=10)
    
    # 4. Tasto di calcolo
    if st.button("Calcola glucosio e bolo"):
        # Filtriamo solo le righe dove "Seleziona" è True
        alimenti_selezionati = edited_df[edited_df["Seleziona"] == True]
        
        if alimenti_selezionati.empty:
            st.warning("Per favore, flagga almeno un alimento dalla tabella.")
        else:
            # Calcolo dei totali
            tot_carbs = alimenti_selezionati["Carboidrati (g)"].sum()
            dose_suggerita = tot_carbs / ic
            
            # Mostriamo i risultati
            st.markdown("---")
            st.write(f"**Riepilogo {tipo_pasto}:**")
            st.write(f"📝 **Alimenti scelti:** {', '.join(alimenti_selezionati['Alimento'].tolist())}")
            st.write(f"🍬 **Totale Carboidrati:** {tot_carbs} g")
            st.success(f"💉 **Dose suggerita:** {dose_suggerita:.1f} unità di Novorapid")
            
            # --- NUOVA SEZIONE: SALVATAGGIO LOG ---
            nuovo_record = pd.DataFrame([{
                "Data_Ora": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Tipo_Pasto": tipo_pasto,
                "Alimenti": ', '.join(alimenti_selezionati['Alimento'].tolist()),
                "Carboidrati_g": tot_carbs,
                "Rapporto_IC": ic,
                "Dose_Suggerita_U": round(dose_suggerita, 1)
            }])
            
            log_file = "log_pasti.csv"
            # Se il file esiste, aggiungiamo la riga (append), altrimenti lo creiamo
            if os.path.exists(log_file):
                nuovo_record.to_csv(log_file, mode='a', header=False, index=False)
            else:
                nuovo_record.to_csv(log_file, mode='w', header=True, index=False)
                
            st.info("💾 Pasto salvato automaticamente nel tuo Diario Digitale!")

# --- AGGIORNAMENTO TAB 3 ---
with tab3:
    st.subheader("📈 Analisi Trend e Diario Pasti")
    
    if os.path.exists("log_pasti.csv"):
        df_log = pd.read_csv("log_pasti.csv")
        st.write("**Il tuo storico pasti:**")
        st.dataframe(df_log, use_container_width=True)
    else:
        st.write("Nessun pasto registrato finora. Usa il Calcolatore per iniziare!")
        
    st.markdown("---")
    st.write("*Prossimamente: Qui incroceremo l'orario del pasto con la curva glicemica del file Libre.*")

