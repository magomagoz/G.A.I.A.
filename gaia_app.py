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

div.stButton > button, div.stDownloadButton > button {
    width: 100% !important;
}

st.markdown("""
    <style>
    /* Forza tutti i bottoni e i file_uploader ad avere lo stesso stile */
    div.stButton > button, div.stDownloadButton > button, div.stFileUploader > section {
        background-color: #f0f2f6 !important;
        border: 1px solid #d3d3d3 !important;
        border-radius: 5px !important;
        color: #31333F !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Tab Layout
tab1, tab2, tab3 = st.tabs(["Dashboard", "Calcolatore Pasti", "Analisi Trend"])

with tab1:
    uploaded_file = st.file_uploader("Carica il tuo CSV LibreView", type="csv")
    if uploaded_file:
        df = elabora_dati(pd.read_csv(uploaded_file, skiprows=1))
        m = calcola_metriche(df, 70, 180)
        col1, col2, col3 = st.columns(3)
        col1.metric("Time In Range (70-180)", f"{m['TIR']:.1f}%")
        col2.metric("Ipoglicemie", f"{m['IPO']:.1f}%")
        col3.metric("Iperglicemie", f"{m['IPER']:.1f}%")
        
        st.subheader("🩺 Suggerimenti Clinici")
        for s in genera_suggerimenti(df):
            st.info(s)

with tab2:
    st.subheader("🍽️ Calcolatore Pasti & Bolo")

    # --- SEZIONE PARAMETRI MEDICI (Persistente nell'interfaccia) ---
    with st.expander("⚙️ Parametri Basale e Sensibilità (Toujeo)"):
        col_p1, col_p2 = st.columns(2)
        # Inserisci le tue 36 unità di Toujeo
        basale_u = col_p1.number_input("Unità Toujeo (Basale)", value=36, step=1)
        
        # Calcolo stimato dell'Insulina Totale Giornaliera (TDI)
        # Generalmente la basale è circa il 50% del totale giornaliero
        tdi = basale_u * 2 
        
        # Regola del 500 per I:C e Regola del 1800 per ISF (Fattore di Sensibilità)
        ic_calc = round(500 / tdi, 1)
        isf_calc = round(1800 / tdi, 1)
        
        st.caption(f"Basato su {basale_u}U di Toujeo: il tuo Rapporto I:C stimato è 1:{ic_calc} e il tuo ISF è {isf_calc} mg/dL.")
        target_glicemico = col_p2.number_input("Target Glicemia (mg/dL)", value=120)

    # --- INPUT MISURAZIONE ATTUALE ---
    col_a, col_b, col_c, col_d = st.columns([2, 2, 3, 2])
    data_p = col_a.date_input("Data", datetime.now().date())
    ora_p = col_b.time_input("Ora", datetime.now().time())
    glic_pre = col_c.number_input("Glicemia attuale (mg/dL)", value=120)
    
    # Menu Trend del Libre
    trend_libre = col_d.selectbox("Trend Libre", [
        "➡️ Stabile", "↗️ Salita lenta", "⬆️ Salita veloce", "↘️ Discesa lenta", "⬇️ Discesa veloce"
    ])

    # ... (Qui inserisci la tua tabella degli alimenti filtrata dal JSON) ...

    # --- LOGICA DI CALCOLO DEL BOLO ---
    if st.button("Calcola Dose Consigliata", use_container_width=True):
        # 1. Dose per Carboidrati
        carb_totali = edited_df[edited_df["Seleziona"] == True]["Carboidrati (g)"].sum()
        dose_carb = carb_totali / ic_calc
        
        # 2. Dose di Correzione (se sei sopra il target)
        dose_corr = (glic_pre - target_glicemico) / isf_calc if glic_pre > target_glicemico else 0
        
        # 3. Aggiustamento Trend (Basato sulla tua richiesta di +/- 0.5 o 1.5)
        adj_trend = 0.0
        if trend_libre == "⬆️ Salita veloce": adj_trend = 1.5
        elif trend_libre == "↗️ Salita lenta": adj_trend = 0.5
        elif trend_libre == "↘️ Discesa lenta": adj_trend = -0.5
        elif trend_libre == "⬇️ Discesa veloce": adj_trend = -1.5
        
        dose_finale = max(0, dose_carb + dose_corr + adj_trend)
        
        # Visualizzazione Risultati
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Carboidrati", f"{int(carb_totali)} g")
        c2.metric("Correzione Trend", f"{adj_trend:+.1f} U")
        c3.metric("BOLO TOTALE", f"{round(dose_finale, 1)} U", delta=f"{adj_trend} Trend")
        
        st.success(f"💉 Iniettare **{round(dose_finale, 1)} unità** di Novorapid.")


with tab3:
    st.subheader("📈 Analisi Trend e Gestione Diario")
    
    col1, col2 = st.columns(2)

    # --- IMPORTAZIONE ---
    # Usiamo un placeholder per mantenere lo stile identico
    uploaded_file = col1.file_uploader("📥 Importa Diario", type="csv", label_visibility="collapsed")
    
    if uploaded_file:
        with open("log_pasti.csv", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Diario aggiornato!")
        st.rerun()
    
    # --- ESPORTAZIONE ---
    if os.path.exists("log_pasti.csv"):
        with open("log_pasti.csv", "rb") as f:
            col1.download_button(
                label="📥 Esporta Diario",
                data=f,
                file_name="log_pasti.csv",
                mime="text/csv"
            )
        
    st.markdown("---")
    
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

