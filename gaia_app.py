import pandas as pd
import numpy as np

def analizza_glicemia(df, target_min=70, target_max=180):
    """
    df: DataFrame con colonne ['timestamp', 'glucosio']
    """
    # Calcolo percentuale nel range
    in_range = df[(df['glucosio'] >= target_min) & (df['glucosio'] <= target_max)]
    percentuale_tir = (len(in_range) / len(df)) * 100
    
    # Identificazione criticità
    ipoglicemie = df[df['glucosio'] < target_min]
    iperglicemie = df[df['glucosio'] > target_max]
    
    return percentuale_tir, ipoglicemie, iperglicemie

# Esempio di logica di miglioramento
def suggerisci_migliorie(ipoglicemie, iperglicemie):
    if len(ipoglicemie) > 0:
        print("Suggerimento: Verificare la dose di insulina basale o il timing dei carboidrati.")
    if len(iperglicemie) > 0:
        print("Suggerimento: Controllare il rapporto insulina-carboidrati (IC) o l'attività fisica post-prandiale.")
