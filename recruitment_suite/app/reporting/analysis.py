# File: app/reporting/analysis.py
# Scopo: Contiene funzioni per l'analisi post-screening, come la creazione di dossier e la visualizzazione dei risultati.

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from tqdm import tqdm
import os
import json
import base64
from io import BytesIO
import numpy as np

from recruitment_suite.config import settings
from recruitment_suite.app.utils.esco_fetcher import EscoSkillFetcher

def create_dossiers_for_promoted(promoted_ids: set, all_normalized_profiles: list[dict], skill_fetcher: EscoSkillFetcher) -> list[dict]:
    print("\n--- FASE 4: Creazione Dossier per i promossi ---")
    profile_map = {p[settings.ID_COLUMN]: p for p in all_normalized_profiles}
    dossiers = []
    for cand_id in tqdm(promoted_ids, desc="Creazione Dossier Finali"):
        if cand_id not in profile_map: continue
        profile_data = profile_map[cand_id]
        career, all_skills, esco_experiences_with_duration = [], set(), []
        for exp in profile_data.get('normalized_experiences', []):
            esco_titles = [match.get('esco_title', 'N/A') for match in exp.get('esco_matches', [])]
            duration = exp.get('duration_months', 0)
            for title in esco_titles:
                if title != 'N/A': esco_experiences_with_duration.append({'title': title, 'duration': duration})
            for title in esco_titles: all_skills.update(skill_fetcher.get_skills_for_title(title))
            career.append({"title": exp.get('original_title', 'N/D'), "esco": esco_titles})
        dossiers.append({'id': cand_id, 'career': career, 'esco_experiences': esco_experiences_with_duration, 'skills': sorted(list(all_skills))})
    return dossiers

def print_dossiers(dossier_data: list, score_map: dict):
    print("\n\n" + "="*55 + "\n--- DOSSIER DEI CANDIDATI PROMOSSI DALL'AI ---\n" + "="*55)
    for i, p in enumerate(dossier_data):
        cand_id = p['id']
        print(f"\n#{i+1} | CANDIDATO ID: {cand_id} | Punteggio Affinità: {score_map.get(cand_id, 0.0):.4f}")
        print("\n  Percorso di Carriera Normalizzato:")
        for exp in p.get('career', []): print(f"    - '{exp['title']}' -> [ESCO: {', '.join(exp['esco'])}]")
        print("\n  Pool di Competenze Aggregate (da ESCO):")
        skills_preview = ", ".join(p['skills'][:15]) + ("..." if len(p['skills']) > 15 else "")
        print(f"    {skills_preview}" if p['skills'] else "    Nessuna competenza rilevata.")
        print("-" * 55)

def visualize_results(results_data: list) -> tuple[pd.DataFrame | None, str | None, list[str] | None]:
    """
    Analizza i dati dei profili, genera un grafico delle categorie, estrae le skill
    più comuni e restituisce i dati e gli artefatti.
    Restituisce: (DataFrame, grafico_categorie_base64, lista_top_skills)
    """
    if not results_data:
        print("Nessun dato da visualizzare.")
        return None, None, None

    # --- Logica per caricare la gerarchia ESCO (invariata) ---
    hierarchy_map = {}
    try:
        from recruitment_suite.config import settings
        from services.data_manager import db
        collection_name = settings.MONGO_COLLECTION_ESCO_HIERARCHY
        hierarchy_map = db[collection_name].find_one({})
        if hierarchy_map and '_id' in hierarchy_map:
            del hierarchy_map['_id']
    except Exception:
        hierarchy_map = {}

    def get_most_general_category(title: str) -> str:
        path = hierarchy_map.get(title)
        return path[0] if path else title

    # Inizializza le variabili di ritorno
    category_market_df = None
    chart1_base64 = None
    top_skills_list = None # <<< Nuova variabile per la lista di skill

    # --- Grafico 1: Sunburst Chart per Categorie Professionali ---
    all_past_experiences = [exp for p in results_data for exp in p.get('esco_experiences', [])[1:]]
    if all_past_experiences:
        df_exp = pd.DataFrame(all_past_experiences)
        df_exp['general_category'] = df_exp['title'].apply(get_most_general_category)
        duration_by_category = df_exp.groupby('general_category')['duration'].sum()
        category_market_df = duration_by_category.sort_values(ascending=False)
        
        # Usa TUTTI i dati disponibili, non solo top 10, per il calcolo delle proporzioni
        # Ma prendi solo top 10 per il grafico
        top_10_categories = category_market_df.nlargest(10)
        total_duration_all = category_market_df.sum()  # Usa TUTTI i dati per calcolare le proporzioni
        total_duration_top_10 = top_10_categories.sum()
        
        if total_duration_top_10 > 0:
            # Organizza i dati in 3 gruppi
            # Top 3: Ruoli rilevanti
            # Successivi 4: Ruoli comuni  
            # Ultimi 3: Ruoli a basso impatto
            num_categories = len(top_10_categories)
            
            # Gestione flessibile in base al numero di categorie disponibili
            if num_categories >= 10:
                top_3 = top_10_categories.head(3)
                middle_4 = top_10_categories.iloc[3:7]
                bottom_3 = top_10_categories.iloc[7:10]
            elif num_categories >= 7:
                top_3 = top_10_categories.head(3)
                middle_4 = top_10_categories.iloc[3:7]
                bottom_3 = top_10_categories.iloc[7:] if num_categories > 7 else pd.Series(dtype=float)
            elif num_categories >= 4:
                top_3 = top_10_categories.head(3)
                middle_4 = top_10_categories.iloc[3:]
                bottom_3 = pd.Series(dtype=float)
            elif num_categories >= 1:
                top_3 = top_10_categories.head(min(3, num_categories))
                middle_4 = top_10_categories.iloc[3:] if num_categories > 3 else pd.Series(dtype=float)
                bottom_3 = pd.Series(dtype=float)
            else:
                top_3 = pd.Series(dtype=float)
                middle_4 = pd.Series(dtype=float)
                bottom_3 = pd.Series(dtype=float)
            
            # Crea il Sunburst Chart
            fig1, ax1 = plt.subplots(figsize=(14, 14), facecolor='white')
            ax1.set_aspect('equal')
            ax1.set_xlim(-1.2, 1.2)
            ax1.set_ylim(-1.2, 1.2)
            ax1.axis('off')
            
            # Colori per i 3 livelli
            colors_relevant = ['#2E7D32', '#388E3C', '#43A047']  # Verde scuro per ruoli rilevanti
            colors_common = ['#1976D2', '#1E88E5', '#2196F3', '#42A5F5']  # Blu per ruoli comuni
            colors_low = ['#F57C00', '#FB8C00', '#FF9800']  # Arancione per ruoli a basso impatto
            
            # Raggi degli anelli
            r_inner = 0.0
            r_middle = 0.35
            r_outer = 0.70
            r_group = 1.0
            
            # Calcola l'angolo per unità di durata basato sui top 10 (per il grafico)
            # Ogni categoria nel grafico occupa spazio proporzionale alla sua durata
            angle_per_unit = 360.0 / total_duration_top_10
            current_angle = 0
            
            # Funzione helper per disegnare un settore
            def draw_sector(ax, center, r_inner, r_outer, theta1, theta2, color, alpha=1.0):
                """Disegna un settore (anello)"""
                theta1_rad = np.deg2rad(theta1)
                theta2_rad = np.deg2rad(theta2)
                wedge = mpatches.Wedge(center, r_outer, theta1, theta2, width=r_outer-r_inner, 
                                      facecolor=color, edgecolor='white', linewidth=2, alpha=alpha)
                ax.add_patch(wedge)
                return wedge
            
            # Funzione helper per aggiungere testo
            def add_text(ax, angle, radius, text, fontsize=9, color='white', bold=False):
                """Aggiunge testo a una posizione angolare"""
                angle_rad = np.deg2rad(angle)
                x = radius * np.cos(angle_rad)
                y = radius * np.sin(angle_rad)
                weight = 'bold' if bold else 'normal'
                ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, 
                       color=color, weight=weight, rotation=angle-90 if angle > 90 and angle < 270 else angle+90)
            
            # Livello 1: Ruoli rilevanti (centro)
            if len(top_3) > 0:
                total_top3 = top_3.sum()
                start_angle = current_angle
                for idx, (role, duration) in enumerate(top_3.items()):
                    angle_span = duration * angle_per_unit
                    mid_angle = start_angle + angle_span / 2
                    
                    # Disegna settore
                    draw_sector(ax1, (0, 0), r_inner, r_middle, start_angle, start_angle + angle_span, 
                               colors_relevant[idx % len(colors_relevant)])
                    
                    # Aggiungi testo (troncato se troppo lungo)
                    role_short = role[:25] + '...' if len(role) > 25 else role
                    add_text(ax1, mid_angle, r_middle * 0.5, role_short, fontsize=8, bold=True)
                    
                    start_angle += angle_span
                
                # Etichetta gruppo
                group_mid_angle = current_angle + (total_top3 * angle_per_unit) / 2
                add_text(ax1, group_mid_angle, r_middle * 0.85, 'RUOLI\nRILEVANTI', 
                        fontsize=10, bold=True, color='white')
                
                current_angle += total_top3 * angle_per_unit
            
            # Livello 2: Ruoli comuni (anello medio)
            if len(middle_4) > 0:
                total_middle = middle_4.sum()
                start_angle = current_angle
                
                for idx, (role, duration) in enumerate(middle_4.items()):
                    angle_span = duration * angle_per_unit
                    mid_angle = start_angle + angle_span / 2
                    
                    # Disegna settore
                    draw_sector(ax1, (0, 0), r_middle, r_outer, start_angle, start_angle + angle_span,
                               colors_common[idx % len(colors_common)])
                    
                    # Aggiungi testo
                    role_short = role[:20] + '...' if len(role) > 20 else role
                    add_text(ax1, mid_angle, (r_middle + r_outer) / 2, role_short, fontsize=7)
                    
                    start_angle += angle_span
                
                # Etichetta gruppo
                group_mid_angle = current_angle + (total_middle * angle_per_unit) / 2
                add_text(ax1, group_mid_angle, (r_middle + r_outer) / 2, 'RUOLI\nCOMUNI',
                        fontsize=9, bold=True, color='white')
                
                current_angle += total_middle * angle_per_unit
            
            # Livello 3: Ruoli a basso impatto (anello esterno)
            if len(bottom_3) > 0:
                total_bottom = bottom_3.sum()
                start_angle = current_angle
                
                for idx, (role, duration) in enumerate(bottom_3.items()):
                    angle_span = duration * angle_per_unit
                    mid_angle = start_angle + angle_span / 2
                    
                    # Disegna settore
                    draw_sector(ax1, (0, 0), r_outer, r_group, start_angle, start_angle + angle_span,
                               colors_low[idx % len(colors_low)])
                    
                    # Aggiungi testo
                    role_short = role[:18] + '...' if len(role) > 18 else role
                    add_text(ax1, mid_angle, (r_outer + r_group) / 2, role_short, fontsize=7)
                    
                    start_angle += angle_span
                
                # Etichetta gruppo
                group_mid_angle = current_angle + (total_bottom * angle_per_unit) / 2
                add_text(ax1, group_mid_angle, (r_outer + r_group) / 2, 'RUOLI A\nBASSO IMPATTO',
                        fontsize=9, bold=True, color='white')
            
            # Aggiungi titolo
            ax1.text(0, -1.35, 'Benchmark di Mercato - Distribuzione Ruoli', 
                    ha='center', va='top', fontsize=14, weight='bold', color='#333')
            
            fig1.tight_layout()
            
            buffer = BytesIO()
            fig1.savefig(buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
            buffer.seek(0)
            chart1_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close(fig1)
            
            # Verifica che il grafico sia stato generato correttamente
            if chart1_base64 and len(chart1_base64) > 100:
                print(f"✓ Sunburst Chart delle categorie generato in memoria (Base64, {len(chart1_base64)} caratteri). Dati: {len(top_3)} rilevanti, {len(middle_4)} comuni, {len(bottom_3)} a basso impatto")
            else:
                print(f"⚠ ERRORE: Sunburst Chart non generato correttamente (lunghezza: {len(chart1_base64) if chart1_base64 else 0})")
                chart1_base64 = None

    # >>> MODIFICA: Analisi delle competenze senza creare il grafico <<<
    all_skills = [s for p in results_data for s in p.get('skills', [])]
    if all_skills:
        # Calcola le 15 skill più comuni
        top_15_skills_series = pd.Series(all_skills).value_counts().head(15)
        # Estrai i nomi delle skill (l'indice della Series) in una lista
        top_skills_list = top_15_skills_series.index.tolist()
        print(f"Estraete le {len(top_skills_list)} skill più comuni dal pool di candidati.")
        # Il codice per generare il grafico (fig2, ax2, ecc.) è stato rimosso.

    # Restituisce il DataFrame, il primo grafico e la nuova lista di skill
    return category_market_df, chart1_base64, top_skills_list