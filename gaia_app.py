import os
from datetime import datetime
import json
import streamlit as st
import pandas as pd
from utils import (
    elabora_dati, calcola_metriche, genera_suggerimenti, 
    suggerisci_aggiustamento_ic 
)
import plotly.express as px

st.set_page_config(page_title="Diabete Dashboard", layout="wide")

st.image("banner.png")

# 1. Inizializzazione della lista pasti (da mettere all'inizio del file)
if 'pasti_correnti' not in st.session_state:
    st.session_state.pasti_correnti = []

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

tab_profilo, tab1, tab2, tab3 = st.tabs(["👤 **Profilo**", "📊 **Dashboard**", "🍽️ **Calcolatore Pasti**", "📈 **Analisi Trend**"])

with tab_profilo:
    st.subheader("👤 Il tuo Profilo Clinico")
    st.write("Inserisci i tuoi dati. L'app li ricorderà e li userà per suggerirti i parametri di partenza per i calcoli del bolo.")
    
    profilo = {}
    if os.path.exists("profilo.json"):
        with open("profilo.json", "r") as f:
            profilo = json.load(f)
            
    with st.form("form_profilo"):
        colA, colB = st.columns(2)
        nome = colA.text_input("Nome", value=profilo.get("nome", "Elena"))
        sesso = colB.selectbox("Sesso", ["Donna", "Uomo"], index=0 if profilo.get("sesso", "Donna") == "Donna" else 1)
        eta = colA.number_input("Età", min_value=1, max_value=120, value=profilo.get("eta", 22))
        peso = colB.number_input("Peso (kg)", min_value=20.0, max_value=200.0, value=profilo.get("peso", 64.0), step=0.5)
        altezza = colA.number_input("Altezza (cm)", min_value=100, max_value=250, value=profilo.get("altezza", 172))
        basale_attuale = colB.number_input("Unità di Toujeo (Basale) che fai ora", min_value=1, value=profilo.get("basale", 32))
        
        salva_profilo = st.form_submit_button("💾 Salva Profilo e Calcola Parametri")
        
        if salva_profilo:
            tdi_stimato = peso * 0.5
            ic_stimato = 500 / tdi_stimato
            isf_stimato = 1664 / tdi_stimato
            
            nuovo_profilo = {
                "nome": nome,
                "sesso": sesso,
                "eta": eta,
                "peso": peso,
                "altezza": altezza,
                "basale": basale_attuale,
                "ic_calcolato": round(ic_stimato, 1),
                "isf_calcolato": round(isf_stimato, 1)
            }
            
            with open("profilo.json", "w") as f:
                json.dump(nuovo_profilo, f)
                
            st.success(f"✅ Profilo di {nome} salvato con successo!")
            st.info(f"📊 In base al tuo peso di {peso}kg, il fabbisogno insulinico totale (TDI) teorico è di circa {round(tdi_stimato)} unità al giorno.\n\n"
                    f"I tuoi parametri empirici suggeriti sono:\n"
                    f"- **Rapporto I:C:** 1 Unità ogni **{round(ic_stimato, 1)}g** di carboidrati.\n"
                    f"- **ISF (Sensibilità):** 1 Unità abbassa la glicemia di **{round(isf_stimato, 1)} mg/dL**.")

    st.markdown("---")
    st.subheader("⚠️ Area di Manutenzione")
            
    with st.expander("🗑️ Cancella tutti i dati dell'app"):
        st.warning("Questa operazione eliminerà permanentemente il tuo profilo e lo storico.")
        conferma_text = st.text_input("Scrivi 'ELIMINA' per confermare", key="check_elimina")
                
        if st.button("Procedi con la cancellazione", key="btn_elimina_definitivo"):
            if conferma_text == "ELIMINA":
                files_da_eliminare = ["log_pasti.csv", "profilo.json"]
                for file in files_da_eliminare:
                    if os.path.exists(file):
                       os.remove(file)
                st.success("✅ Dati cancellati. Ricarico l'app...")
                st.rerun() 
            else:
               st.error("⚠️ Digita esattamente 'ELIMINA' nel campo sopra per sbloccare il tasto.")

with tab1:
    with st.expander("📂 Clicca per caricare il file CSV"):
        uploaded_file = st.file_uploader("Seleziona file", type="csv", label_visibility="collapsed")

    if uploaded_file:
        df = elabora_dati(pd.read_csv(uploaded_file, skiprows=1))
        m = calcola_metriche(df, 70, 180)
        col1, col2, col3 = st.columns(3)
        col1.metric("**TIME IN RANGE**", f"{m['TIR']:.1f}%")
        col2.metric("**IPOGLICEMIE**", f"{m['IPO']:.1f}%")
        col3.metric("**IPERGLICEMIE**", f"{m['IPER']:.1f}%")
        
        st.subheader("🩺 Suggerimenti Clinici")
        for s in genera_suggerimenti(df):
            st.info(s)
            
with tab2:
    st.subheader("🍽️ Calcolatore Insulina")

    profilo_salvato = {}
    if os.path.exists("profilo.json"):
        with open("profilo.json", "r") as f:
            profilo_salvato = json.load(f)
            
    default_ic = profilo_salvato.get("ic_calcolato", 10.0)
    default_isf = profilo_salvato.get("isf_calcolato", 40.0)

    with st.expander("⚙️ Parametri Personalizzati (Calcolati dal Profilo)"):
        st.write("Questi valori sono precompilati in base al tuo peso, ma puoi modificarli per questo pasto se il medico ti ha dato indicazioni diverse.")
        col_p1, col_p2 = st.columns(2)
        ic_calc = col_p1.number_input("Rapporto I:C (es. 10 = 1U ogni 10g)", value=float(default_ic), step=0.5)
        isf_calc = col_p2.number_input("ISF (Fattore Sensibilità)", value=float(default_isf), step=1.0)
        target_glicemico = col_p1.number_input("Target Glicemia (mg/dL)", value=120)

    col_a, col_b, col_c, col_d = st.columns([2, 2, 3, 2])
    data_pasto = col_a.date_input("Data", datetime.now().date())
    ora_pasto = col_b.time_input("Ora", datetime.now().time())
    glicemia_pre = col_c.number_input("Glicemia attuale (mg/dL)", value=120)
    trend_libre = col_d.selectbox("Trend misurazione", ["➡️ Stabile", "↗️ Salita lenta", "⬆️ Salita veloce", "↘️ Discesa lenta", "⬇️ Discesa veloce"])

    tipo_pasto = st.selectbox("Momento della giornata", ["Colazione", "Pranzo", "Cena", "Spuntino"])

    try:
        with open('alimenti.json', 'r') as f:
            db_alimenti = json.load(f)
    except FileNotFoundError:
        db_alimenti = {"Pane": 50, "Pasta": 70, "Mela": 15}
    
    search_term = st.text_input("🔍 Cerca alimento nel database", "").lower()
    df_alimenti = pd.DataFrame(list(db_alimenti.items()), columns=["Alimento", "Carboidrati_Unitari"])
    
    if search_term:
        df_filtrato = df_alimenti[df_alimenti["Alimento"].str.lower().str.contains(search_term)]
    else:
        df_filtrato = df_alimenti
        
    df_display = df_filtrato.copy() 
    df_display.insert(0, "Seleziona", False)
    df_display["Quantità"] = 1.0 
    
    # Editor dati corretto senza puntini
    edited_df = st.data_editor(
        df_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Seleziona": st.column_config.CheckboxColumn("Seleziona", default=False),
            "Alimento": st.column_config.TextColumn("Alimento", disabled=True),
            "Quantità": st.column_config.NumberColumn("Quantità", min_value=0.1, step=0.5, format="%.1f"),
            "Carboidrati_Unitari": st.column_config.NumberColumn("Carboidrati unitari", disabled=True)
        }
    )
    
    if st.button("➕ Aggiungi alimento selezionato"):
        selezionati = edited_df[edited_df["Seleziona"] == True]
        if not selezionati.empty:
            st.session_state.pasti_correnti.extend(selezionati.to_dict('records'))
            st.rerun() 
        else:
            st.warning("Seleziona almeno un alimento nella tabella.")

    if st.session_state.pasti_correnti:
        df_accumulato = pd.DataFrame(st.session_state.pasti_correnti)
        st.write("📋 **Alimenti nel tuo pasto:**", df_accumulato)
        
        if st.button("💉 **Calcola Dose Finale e Salva**"):
            tot_carbs = (df_accumulato["Carboidrati_Unitari"] * df_accumulato["Quantità"]).sum()
            dose_carboidrati = tot_carbs / ic_calc
            
            modifica_trend = 0.0
            if trend_libre == "⬆️ Salita veloce": modifica_trend = 1.5
            elif trend_libre == "↗️ Salita lenta": modifica_trend = 0.5
            elif trend_libre == "↘️ Discesa lenta": modifica_trend = -0.5
            elif trend_libre == "⬇️ Discesa veloce": modifica_trend = -1.5
                
            correzione = (glicemia_pre - target_glicemico) / isf_calc if glicemia_pre > target_glicemico else 0
            dose_totale = max(0, dose_carboidrati + correzione + modifica_trend)
            
            descrizione = ", ".join([f"{r['Alimento']} (x{r['Quantità']})" for _, r in df_accumulato.iterrows()])

            st.markdown("---")
            st.write(f"**Riepilogo {tipo_pasto}:**")
            st.write(f"📝 **Alimenti scelti:** {descrizione}")
            st.write(f"🍬 **Totale Carboidrati:** {tot_carbs} g")
            if correzione > 0:
                st.write(f"✨ **Correzione glicemia:** +{correzione:.1f} U")
            
            st.markdown("---")
            st.success(f"💉 **Dose totale suggerita: {round(dose_totale, 1)} unità di Novorapid**")

            import plotly.graph_objects as go
            etichette = ['Carboidrati', 'Correzione Glicemia', 'Aggiustamento Trend']
            valori = [dose_carboidrati, correzione, max(0, modifica_trend)] 
            
            fig_bolo = go.Figure(data=[go.Pie(
                labels=etichette, 
                values=valori, 
                hole=.4,
                marker_colors=['#00CC96', '#EF553B', '#636EFA']
            )])
            
            fig_bolo.update_layout(
                title_text="Ripartizione Unità Insulina",
                annotations=[dict(text='Bolo', x=0.5, y=0.5, font_size=20, showarrow=False)],
                showlegend=True,
                height=350,
                margin=dict(l=0, r=0, b=0, t=40)
            )
            st.plotly_chart(fig_bolo, use_container_width=True)
                
            nuovo_record = pd.DataFrame([{
                "Data_Ora": f"{data_pasto} {ora_pasto}",
                "Glicemia_Pre": glicemia_pre,
                "Trend": trend_libre,
                "Tipo_Pasto": tipo_pasto,
                "Alimenti": descrizione,
                "Carboidrati_g": tot_carbs,
                "Rapporto_IC": ic_calc,
                "Dose_Suggerita_U": round(dose_totale, 1)
            }])
                
            log_file = "log_pasti.csv"
            nuovo_record.to_csv(log_file, mode='a', header=not os.path.exists(log_file), index=False)
            st.info("💾 Pasto salvato con successo nel Diario!")

        if st.button("❌ Pulisci lista alimenti e fai un nuovo calcolo"):
            st.session_state.pasti_correnti = []
            st.rerun()
            
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
            
    if os.path.exists("log_pasti.csv"):
        df_log = pd.read_csv("log_pasti.csv")
        
        # Inseriamo la colonna fittizia per eliminare le righe
        df_log.insert(0, "Azioni", False)
        
        st.write("**Il tuo storico pasti:**")
        edited_log = st.data_editor(
            df_log,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Azioni": st.column_config.CheckboxColumn("Elimina riga?", default=False)
            }
        )
                
        if st.button("💾 Conferma eliminazione righe selezionate"):
            # Rimuove le righe flaggate e toglie la colonna 'Azioni' prima di salvare
            df_salvataggio = edited_log[edited_log["Azioni"] == False].drop(columns=["Azioni"])
            df_salvataggio.to_csv("log_pasti.csv", index=False)
            st.rerun()
            
        st.markdown("---")
        st.write("🔍 **Analizza l'impatto di un pasto**")
            
        # Rileggiamo il file pulito per evitare che la colonna "Azioni" crei problemi ai grafici
        df_analisi = pd.read_csv("log_pasti.csv")
        
        if not df_analisi.empty:
            opzioni_pasto = df_analisi['Data_Ora'] + " - " + df_analisi['Tipo_Pasto'] + " (" + df_analisi['Carboidrati_g'].astype(str) + "g carbs)"
            pasto_scelto = st.selectbox("Seleziona un pasto per vedere se il bolo ha funzionato:", opzioni_pasto)
                
            if pasto_scelto and 'df' in locals() and not df.empty:
                orario_str = pasto_scelto.split(" - ")[0]
                orario_inizio = pd.to_datetime(orario_str)
                orario_fine = orario_inizio + pd.Timedelta(hours=3)
                
                mask = (df['Timestamp'] >= orario_inizio) & (df['Timestamp'] <= orario_fine)
                df_trend = df[mask]
                    
                if not df_trend.empty:
                    fig = px.line(
                        df_trend, 
                        x='Timestamp', 
                        y='Glucosio', 
                        title=f"Curva Glicemica (3 ore) per {pasto_scelto.split(' - ')[1]}",
                        markers=True 
                    )
                        
                    fig.add_hline(y=180, line_dash="dash", line_color="red", annotation_text="Iper (180)")
                    fig.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Ipo (70)")
                    fig.add_hrect(y0=70, y1=180, line_width=0, fillcolor="green", opacity=0.1)
                    
                    fig.update_layout(yaxis_title="Glucosio (mg/dL)", xaxis_title="Orario", hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
                        
                    picco_max = df_trend['Glucosio'].max()
                    orario_picco = df_trend.loc[df_trend['Glucosio'].idxmax(), 'Timestamp']
                        
                    colA, colB = st.columns(2)
                    colA.metric("Picco Glicemico Massimo", f"{picco_max} mg/dL")
                        
                    minuti_al_picco = int((orario_picco - orario_inizio).total_seconds() / 60)
                    colB.metric("Tempo per raggiungere il picco", f"{minuti_al_picco} min")
                    
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
        
        st.markdown("---")
        st.write("🧠 **Analisi Intelligente del Rapporto I:C**")
        
        suggerimenti_ic = suggerisci_aggiustamento_ic(df_analisi)
        for s in suggerimenti_ic:
            st.warning(s)
    else:
        st.write("Nessun pasto registrato finora. Usa la tabella nel 'Calcolatore Pasti' per registrare il tuo primo pasto!")
