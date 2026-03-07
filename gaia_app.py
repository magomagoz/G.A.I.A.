import os
from datetime import datetime
import json
import streamlit as st
import pandas as pd
from utils import elabora_dati, calcola_metriche, genera_suggerimenti
import plotly.express as px

st.set_page_config(page_title="Diabete Dashboard", layout="wide")
st.image("banner.png")
#st.title("🩺 Assistente Diabetico")

# Tab Layout
tab1, tab2, tab3 = st.tabs(["Dashboard", "Calcolatore Pasti", "Analisi Trend"])

with tab1:
    uploaded_file = st.file_uploader("Carica il tuo CSV LibreView", type="csv")
    if uploaded_file:
        df = elabora_dati(pd.read_csv(uploaded_file, skiprows=1))
        m = calcola_metriche(df, 70, 180)
        col1, col2, col3 = st.columns(3)
        col1.metric("Time In Range (70-180", f"{m['TIR']:.1f}%")
        col2.metric("Ipoglicemie", f"{m['IPO']:.1f}%")
        col3.metric("Iperglicemie", f"{m['IPER']:.1f}%")
        
        st.subheader("🩺 Suggerimenti Clinici")
        for s in genera_suggerimenti(df):
            st.info(s)

with tab2:
    st.subheader("🍽️ Calcolatore Pasti")
    
    # 1. Input di data, ora e glicemia attuale
    col_a, col_b, col_c = st.columns(3)
    data_pasto = col_a.date_input("Data del pasto", datetime.now().date())
    ora_pasto = col_b.time_input("Ora del pasto", datetime.now().time())
    glicemia_pre = col_c.number_input("Glicemia attuale (mg/dL)", min_value=30, max_value=600, value=150)
    
    tipo_pasto = st.selectbox("Momento della giornata", ["Colazione", "Pranzo", "Cena", "Spuntino"])
    # 2. Caricamento del database alimenti
    # Creiamo un dizionario di default nel caso il file non esista ancora
    try:
        with open('alimenti.json', 'r') as f:
            db_alimenti = json.load(f)
    #except FileNotFoundError:
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
    ic = st.number_input("Tuo rapporto I:C (es. 1 U ogni n gr.)", value=10)
    
    # 4. Tasto di calcolo aggiornato
    if st.button("Calcola glucosio"):
        alimenti_selezionati = edited_df[edited_df["Seleziona"] == True]
        
        if alimenti_selezionati.empty:
            st.warning("Per favore, scegli almeno un alimento dalla tabella.")
        else:
            
            # Calcolo dei totali
            tot_carbs = alimenti_selezionati["Carboidrati (g)"].sum()
            #dose_suggerita = tot_carbs / ic
            dose_carboidrati = tot_carbs / ic

            # LOGICA DI CORREZIONE (opzionale): 
            # Se la glicemia è sopra 150, aggiungiamo una correzione semplificata (es: 1U ogni 50mg/dL sopra il target di 120)
            correzione = 0
            if glicemia_pre > 150:
                correzione = (glicemia_pre - 120) / 50
            
            dose_totale = dose_carboidrati + correzione

            # Mostriamo i risultati
            st.markdown("---")
            st.write(f"**Riepilogo {tipo_pasto}:**")
            st.write(f"📝 **Alimenti scelti:** {', '.join(alimenti_selezionati['Alimento'].tolist())}")
            st.write(f"🍬 **Totale Carboidrati:** {tot_carbs} g")
            if correzione > 0:
                st.write(f"✨ **Correzione glicemia:** +{correzione:.1f} U")
            st.success(f"💉 **Dose totale suggerita:** {dose_totale:.1f} unità di Novorapid")

            #st.success(f"💉 **Dose suggerita:** {dose_suggerita:.1f} unità di Novorapid")
                    
            # --- SALVATAGGIO CON NUOVI DATI ---
            nuovo_record = pd.DataFrame([{
                "Data_Ora": f"{data_pasto} {ora_pasto}",
                "Glicemia_Pre": glicemia_pre,
                "Tipo_Pasto": tipo_pasto,
                "Alimenti": ', '.join(alimenti_selezionati['Alimento'].tolist()),
                "Carboidrati_g": tot_carbs,
                "Rapporto_IC": ic,
                
                "Dose_Suggerita_U": round(dose_totale, 1)
            }])
            
            log_file = "log_pasti.csv"
            # Se il file esiste, aggiungiamo la riga (append), altrimenti lo creiamo
            if os.path.exists(log_file):
                nuovo_record.to_csv(log_file, mode='a', header=False, index=False)
            else:
                nuovo_record.to_csv(log_file, mode='w', header=True, index=False)
                
            st.info("💾 Pasto salvato automaticamente nel tuo Diario Digitale!")

with tab3:
    st.subheader("📈 Analisi Trend Post-Prandiale")
    
    # Verifichiamo se esiste il diario dei pasti
    if os.path.exists("log_pasti.csv"):
        df_log = pd.read_csv("log_pasti.csv")
        
        if not df_log.empty:
            st.write("**Il tuo storico pasti:**")
            st.dataframe(df_log, use_container_width=True)
            
            st.markdown("---")
            st.write("### 🔍 Analizza l'impatto di un pasto")
            
            # Creiamo un menu a tendina leggibile (es: "2023-11-20 13:00 - Pranzo (45g carbs)")
            opzioni_pasto = df_log['Data_Ora'] + " - " + df_log['Tipo_Pasto'] + " (" + df_log['Carboidrati_g'].astype(str) + "g carbs)"
            pasto_scelto = st.selectbox("Seleziona un pasto per vedere se il bolo ha funzionato:", opzioni_pasto)
            
            # Controlliamo che il file Libre (df) sia stato caricato nel Tab 1
            if pasto_scelto and 'df' in locals() and not df.empty:
                # Estraiamo l'orario esatto dalla stringa del menu a tendina
                orario_str = pasto_scelto.split(" - ")[0]
                orario_inizio = pd.to_datetime(orario_str)
                # Definiamo la finestra di analisi: 3 ore dopo il pasto
                orario_fine = orario_inizio + pd.Timedelta(hours=3)
                
                # Filtriamo il dataframe del FreeStyle Libre
                mask = (df['Timestamp'] >= orario_inizio) & (df['Timestamp'] <= orario_fine)
                df_trend = df[mask]
                
                if not df_trend.empty:
                    # --- DISEGNO DEL GRAFICO ---
                    fig = px.line(
                        df_trend, 
                        x='Timestamp', 
                        y='Glucosio', 
                        title=f"Curva Glicemica (3 ore) per {pasto_scelto.split(' - ')[1]}",
                        markers=True # Mette i puntini sui singoli valori misurati
                    )
                    
                    # Aggiungiamo le linee guida del Target (70-180)
                    fig.add_hline(y=180, line_dash="dash", line_color="red", annotation_text="Iper (180)")
                    fig.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Ipo (70)")
                    # Coloriamo la "zona di sicurezza" (Time In Range) di verde chiaro
                    fig.add_hrect(y0=70, y1=180, line_width=0, fillcolor="green", opacity=0.1)
                    
                    fig.update_layout(yaxis_title="Glucosio (mg/dL)", xaxis_title="Orario", hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # --- LOGICA CLINICA AUTOMATICA ---
                    picco_max = df_trend['Glucosio'].max()
                    orario_picco = df_trend.loc[df_trend['Glucosio'].idxmax(), 'Timestamp']
                    
                    colA, colB = st.columns(2)
                    colA.metric("Picco Glicemico Massimo", f"{picco_max} mg/dL")
                    
                    # Calcoliamo quanti minuti dopo il pasto c'è stato il picco
                    minuti_al_picco = int((orario_picco - orario_inizio).total_seconds() / 60)
                    colB.metric("Tempo per raggiungere il picco", f"{minuti_al_picco} min")
                    
                    # Suggerimenti basati sui dati
                    if picco_max > 180:
                        st.warning(f"⚠️ Attenzione: Il picco ha superato il target di 180 mg/dL (è arrivato a {picco_max}).")
                        if minuti_al_picco < 60:
                            st.write("💡 **Analisi:** Il picco è avvenuto molto in fretta (meno di 1 ora). Probabilmente avevi bisogno di un **anticipo del bolo** (aspettare 15-20 min tra iniezione e pasto) o il cibo aveva un altissimo indice glicemico.")
                        else:
                            st.write("💡 **Analisi:** Il bolo (Novorapid) non è stato sufficiente a coprire i carboidrati. Valuta con il medico se ridurre il tuo rapporto I:C in questo orario della giornata.")
                    elif picco_max < 70:
                        st.error("🚨 Ipoglicemia post-prandiale rilevata. La dose di insulina era eccessiva per questo pasto.")
                    else:
                        st.success("✅ Ottimo lavoro! La glicemia è rimasta perfettamente nel target (Time in Range) dopo il pasto. La dose calcolata era esatta.")
                else:
                    st.info("🕒 Nessun dato glicemico trovato nel sensore per le 3 ore successive a questo pasto. Assicurati che il CSV caricato copra questa data e orario.")
            elif 'df' not in locals() or df.empty:
                st.error("Per visualizzare le curve dei pasti devi prima caricare il file CSV della Abbott nel Tab 'Dashboard'.")
    else:
        st.write("Nessun pasto registrato finora. Usa la tabella nel 'Calcolatore Pasti' per registrare il tuo primo pasto!")
    
    st.markdown("---")
    st.write("### 🧠 Analisi Intelligente del Rapporto I:C")
    
    if os.path.exists("log_pasti.csv"):
        df_log = pd.read_csv("log_pasti.csv")
        suggerimenti_ic = suggerisci_aggiustamento_ic(df_log)
        for s in suggerimenti_ic:
            st.warning(s)
    else:
        st.write("Registra almeno 3-4 pasti per attivare l'analisi automatica del rapporto I:C.")
