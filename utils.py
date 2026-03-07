import pandas as pd
import json

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

def elabora_dati(df):
    # Pulizia nomi colonne e conversione date
    # Nota: Libre usa formati dd-mm-yyyy HH:MM
    df['Timestamp'] = pd.to_datetime(df['Timestamp del dispositivo'], dayfirst=True)
    df = df.sort_values('Timestamp')
    
    # Pulizia colonne numeriche
    df['Glucosio'] = pd.to_numeric(df['Storico del glucosio mg/dL'], errors='coerce')
    df['Novorapid'] = pd.to_numeric(df['Insulina ad azione rapida (unità)'], errors='coerce').fillna(0)
    df['Toujeo'] = pd.to_numeric(df['Insulina ad effetto prolungato (unità)'], errors='coerce').fillna(0)
    
    return df.dropna(subset=['Glucosio'])

def calcola_metriche(df, target_min=70, target_max=180):
    totale = len(df)
    in_range = len(df[(df['Glucosio'] >= target_min) & (df['Glucosio'] <= target_max)])
    ipo = len(df[df['Glucosio'] < target_min])
    iper = len(df[df['Glucosio'] > target_max])
    
    return {
        "TIR": (in_range / totale) * 100,
        "Percentuale Ipo": (ipo / totale) * 100,
        "Percentuale Iper": (iper / totale) * 100
    }

def analisi_notturna(df):
    # Identifica le ore notturne tipiche per la Toujeo (es. 00:00 - 06:00)
    notte = df[df['Timestamp'].dt.hour.isin([0, 1, 2, 3, 4, 5])]
    media_notturna = notte['Glucosio'].mean()
    
    return media_notturna

def genera_suggerimenti(df, target_min=70, target_max=180):
    """
    Analisi delle tendenze per suggerire modifiche.
    """
    # 1. Analisi Basale (Notte: 00:00 - 06:00)
    notte = df[df['Timestamp'].dt.hour.isin([0, 1, 2, 3, 4, 5])]
    media_notte = notte['Glucosio'].mean()
    
    # 2. Analisi Bolo (Post-prandiale: 1-3 ore dopo un pasto)
    # Identifichiamo i momenti in cui sono stati somministrati carboidrati
    pasti = df[df['Carboidrati (grammi)'] > 0]
    # (Qui implementeremo poi il calcolo dello scostamento post-prandiale)
    
    suggerimenti = []
    
    # Logica Basale (Toujeo)
    if media_notte > 140:
        suggerimenti.append("Suggerimento Basale: La media notturna è alta. Valutare con il medico un incremento della Toujeo.")
    elif media_notte < 80:
        suggerimenti.append("Suggerimento Basale: La media notturna è bassa. Rischio ipo notturna, valutare riduzione Toujeo.")
        
    return suggerimenti

