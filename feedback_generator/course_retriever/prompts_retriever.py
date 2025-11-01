def create_query_refinement_prompt(skill_family: str, skill_gaps: list[str], language: str = "it") -> str:
    """
    Trasformazione delle skill families e skill gap in query naturali per ottimizzare la ricerca vettoriale
    """
    # Traformazione delle skill families e skill gap in query natuali per ottimizzare la ricerca vettoriale
    gaps_str = ", ".join(skill_gaps)
    
    prompts = {
        "it": (
            "Il tuo compito è agire come un esperto di formazione. Ricevi una 'famiglia di competenze' e una lista di 'carenze specifiche'. "
            "Trasforma questi input in una singola frase o domanda in linguaggio naturale, chiara e concisa, che descriva la necessità formativa. "
            "Questa frase verrà usata per cercare corsi in un database.\n\n"
            f"Famiglia di Competenze: \"{skill_family}\"\n"
            f"Carenze Specifiche: \"{gaps_str}\"\n\n"
            "Esempio di output: 'Corsi per imparare a gestire campagne pubblicitarie a pagamento su Google e piattaforme social come Meta'.\n\n"
            "Genera solo la frase di ricerca finale, senza testo aggiuntivo."
        ),
        "en": (
            "Your task is to act as a training expert. You receive a 'skills family' and a list of 'specific gaps'. "
            "Transform these inputs into a single sentence or question in natural language, clear and concise, that describes the training need. "
            "This sentence will be used to search for courses in a database.\n\n"
            f"Skills Family: \"{skill_family}\"\n"
            f"Specific Gaps: \"{gaps_str}\"\n\n"
            "Output example: 'Courses to learn how to manage paid advertising campaigns on Google and social platforms like Meta'.\n\n"
            "Generate only the final search phrase, without additional text."
        )
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Course Retriever Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]
