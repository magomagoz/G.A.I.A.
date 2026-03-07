import pandas as pd
import json

def elabora_dati(df):
    # Il file Libre richiede attenzione alle date e alla pulizia delle celle vuote
    df['Timestamp'] = pd.to_datetime(df['Timestamp del dispositivo'], dayfirst=True)
    df = df.sort_values('Timestamp')
    df['Glucosio'] = pd.to_numeric(df['Storico del glucosio mg/dL'], errors='coerce')
    df['Carboidrati (grammi)'] = pd.to_numeric(df['Carboidrati (grammi)'], errors='coerce').fillna(0)
    return df

def calcola_metriche(df, target_min, target_max):
    valori = df['Glucosio'].dropna()
    totale = len(valori)
    tir = (len(valori[(valori >= target_min) & (valori <= target_max)]) / totale) * 100
    ipo = (len(valori[valori < target_min]) / totale) * 100
    iper = (len(valori[valori > target_max]) / totale) * 100
    return {"TIR": tir, "IPO": ipo, "IPER": iper}

def genera_suggerimenti(df):
    notte = df[df['Timestamp'].dt.hour.isin([0, 1, 2, 3, 4, 5])]
    media_notte = notte['Glucosio'].mean()
    suggerimenti = []
    if media_notte > 140:
        suggerimenti.append("📈 Basale: Media notturna alta. Valutare aumento Toujeo.")
    elif media_notte < 80:
        suggerimenti.append("📉 Basale: Media notturna bassa. Valutare riduzione Toujeo.")
    return suggerimenti

# Carica il database alimenti
def get_carbs(nome_alimento):
    with open('alimenti.json', 'r') as f:
        db = json.load(f)
    return db.get(nome_alimento, 0)

def calcola_bolo_suggerito(alimento, rapporto_ic):
    carbs = get_carbs(alimento)
    # Esempio: se rapporto_ic è 1:10, significa 1 unità ogni 10g di carboidrati
    dose = carbs / rapporto_ic
    return dose

def analisi_notturna(df):
    # Identifica le ore notturne tipiche per la Toujeo (es. 00:00 - 06:00)
    notte = df[df['Timestamp'].dt.hour.isin([0, 1, 2, 3, 4, 5])]
    media_notturna = notte['Glucosio'].mean()
    
    return media_notturna

def analizza_efficacia_bolo(df, soglia_iper=180):
    """
    Analizza cosa succede dopo l'assunzione di carboidrati.
    """
    # Filtra solo i momenti in cui hai mangiato
    pasti = df[df['Carboidrati (grammi)'] > 0]
    
    report = []
    for index, pasto in pasti.iterrows():
        # Prendi i dati glicemici nelle 2 ore successive
        time_limit = pasto['Timestamp'] + pd.Timedelta(hours=2)
        trend_post_pasto = df[(df['Timestamp'] > pasto['Timestamp']) & 
                              (df['Timestamp'] <= time_limit)]
        
        max_glicemia = trend_post_pasto['Glucosio'].max()
        
        if max_glicemia > soglia_iper:
            report.append(f"Attenzione: dopo il pasto delle {pasto['Timestamp'].time()}, la glicemia è salita a {max_glicemia} mg/dL.")
            
    return report
