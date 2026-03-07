import os
from datetime import datetime
import json
import streamlit as st
import pandas as pd
from utils import (
    elabora_dati, calcola_metriche, genera_suggerimenti, 
    suggerisci_aggiustamento_ic # Assicurati di averla in utils.py
)
import plotly.express as px

st.set_page_config(page_title="Diabete Dashboard", layout="wide")

# CSS per bottoni uniformi
st.markdown("""
    <style>
    div.stButton > button, div.stDownloadButton > button, div.stFileUploader > section {
        background-color: #f0f2f6 !important;
        border: 1px solid #d3d3d3 !important;
        border-radius: 5px !important;
        color: #31333F !important;
        width: 100% !important;
        height: 45px !important;
    }
    </style>
    """, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🍽️ Calcolatore Pasti", "📈 Analisi Trend"])

with tab1:
    uploaded_file = st.file_uploader("Carica il tuo CSV LibreView", type="csv")
    if uploaded_file:
        df = elabora_dati(pd.read_csv(uploaded_file, skiprows=1))
        m = calcola_metriche(df, 70, 180)
        col1, col2, col3 = st.columns(3)
        col1.metric("Time In Range", f"{m['TIR']:.1f}%")
        col2.metric("Ipoglicemie", f"{m['IPO']:.1f}%")
        col3.metric("Iperglicemie", f"{m['IPER']:.1f}%")
        
        st.subheader("🩺 Suggerimenti Clinici")
        for s in genera_suggerimenti(df):
            st.info(s)

with tab2:
    st.subheader("🍽️ Calcolatore Pasti & Bolo")

    with st.expander("⚙️ Parametri Basale e Sensibilità (Toujeo)"):
        col_p1, col_p2 = st.columns(2)
        basale_u = col_p1.number_input("Unità Toujeo (Basale)", value=36, step=1)
        tdi = basale_u * 2 
        ic_calc = round(500 / tdi, 1)
        isf_calc = round(1800 / tdi, 1)
        st.caption(f"Rapporto I:C stimato: 1:{ic_calc} | ISF: {isf_calc} mg/dL")
        target_glicemico = col_p2.number_input("Target Glicemia (mg/dL)", value=120)

    col_a, col_b, col_c, col_d = st.columns([2, 2, 3, 2])
    data_pasto = col_a.date_input("Data", datetime.now().date())
    ora_pasto = col_b.time_input("Ora", datetime.now().time())
    glicemia_pre = col_c.number_input("Glicemia attuale (mg/dL)", value=120)
    trend_libre = col_d.selectbox("Trend Libre", ["➡️ Stabile", "↗️ Salita lenta", "⬆️ Salita veloce", "↘️ Discesa lenta", "⬇️ Discesa veloce"])

    tipo_pasto = st.selectbox("Momento della giornata", ["Colazione", "Pranzo", "Cena", "Spuntino"])

    try:
        with open('alimenti.json', 'r') as f:
            db_alimenti = json.load(f)
    except FileNotFoundError:
        db_alimenti = {"Pane": 50, "Pasta": 70, "Mela": 15}
    
    df_alimenti = pd.DataFrame(list(db_alimenti.items()), columns=["Alimento", "Carboidrati (g)"])
    df_alimenti.insert(0, "Seleziona", False)
    
    edited_df = st.data_editor(df_alimenti, hide_index=True, use_container_width=True)
    
    if st.button("Calcola Dose Consigliata"):
        alimenti_selezionati = edited_df[edited_df["Seleziona"] == True]
        
        if alimenti_selezionati.empty:
            st.warning("Per favore, scegli almeno un alimento.")
        else:
            tot_carbs = alimenti_selezionati["Carboidrati (g)"].sum()
            dose_carboidrati = tot_carbs / ic_calc
        
            modifica_trend = 0.0
            if trend_libre == "⬆️ Salita veloce": modifica_trend = 1.5
            elif trend_libre == "↗️ Salita lenta": modifica_trend = 0.5
            elif trend_libre == "↘️ Discesa lenta": modifica_trend = -0.5
            elif trend_libre == "⬇️ Discesa veloce": modifica_trend = -1.5
            
            correzione = (glicemia_pre - target_glicemico) / isf_calc if glicemia_pre > target_glicemico else 0
            dose_totale = max(0, dose_carboidrati + correzione + modifica_trend)
            
            st.markdown("---")
            st.success(f"💉 Dose consigliata: **{round(dose_totale, 1)} Unità**")
            
            # Salvataggio
            nuovo_record = pd.DataFrame([{
                "Data_Ora": f"{data_pasto} {ora_pasto}",
                "Glicemia_Pre": glicemia_pre,
                "Tipo_Pasto": tipo_pasto,
                "Alimenti": ', '.join(alimenti_selezionati['Alimento'].tolist()),
                "Carboidrati_g": tot_carbs,
                "Rapporto_IC": ic_calc,
                "Dose_Suggerita_U": round(dose_totale, 1)
            }])
            
            log_file = "log_pasti.csv"
            if os.path.exists(log_file):
                nuovo_record.to_csv(log_file, mode='a', header=False, index=False)
            else:
                nuovo_record.to_csv(log_file, mode='w', header=True, index=False)
            st.info("💾 Pasto salvato!")

with tab3:
    st.subheader("📈 Analisi Trend e Gestione Diario")
    col1, col2 = st.columns(2)

    with col1:
        uploaded_csv = st.file_uploader("📥 Importa CSV", type="csv", label_visibility="collapsed")
        if uploaded_csv:
            with open("log_pasti.csv", "wb") as f:
                f.write(uploaded_csv.getbuffer())
            st.rerun()
    
    with col2:
        if os.path.exists("log_pasti.csv"):
            with open("log_pasti.csv", "rb") as f:
                st.download_button("📤 Esporta CSV", data=f, file_name="mio_diario.csv", mime="text/csv")
            
    # 2. Visualizzazione del diario (solo se esiste)
    if os.path.exists("log_pasti.csv"):
        df_diario = pd.read_csv("log_pasti.csv")
        st.write("**Il tuo storico pasti:**")
        st.dataframe(df_diario, use_container_width=True)
            
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

