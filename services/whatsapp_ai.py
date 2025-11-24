"""
WhatsApp AI conversation logic
"""
from typing import Dict, Any, Optional, List, Tuple
from backend.models.whatsapp import WhatsappConfig, KnockoutRule, WhatsappStatus
from interviewer.llm_service import get_llm_response
import re


def build_system_prompt(config: WhatsappConfig, candidate_name: str = "Candidato") -> str:
    """
    Costruisce il system prompt per l'AI basato sulla configurazione del tenant
    """
    tone_descriptions = {
        "formal": "professionale e formale",
        "friendly": "amichevole e cordiale",
        "enthusiastic": "entusiasta e motivante"
    }
    
    tone_desc = tone_descriptions.get(config.tone, "amichevole")
    
    # Costruisci lista regole knock-out
    knockout_text = ""
    if config.knockout_rules:
        knockout_text = "\n\nREQUISITI OBBLIGATORI (Knock-out):\n"
        for i, rule in enumerate(config.knockout_rules, 1):
            knockout_text += f"{i}. Domanda: {rule.question}\n"
            knockout_text += f"   Risposta attesa deve contenere: {rule.expected_answer}\n"
            knockout_text += f"   Se fallisce, rispondi: {rule.rejection_message}\n"
    
    # Costruisci lista domande screening
    screening_text = ""
    if config.screening_questions:
        screening_text = "\n\nDOMANDE DI SCREENING da porre al candidato:\n"
        for i, question in enumerate(config.screening_questions, 1):
            screening_text += f"{i}. {question}\n"
    
    # Costruisci knowledge base
    kb_text = ""
    if config.knowledge_base:
        kb_text = "\n\nINFORMAZIONI SULLA POSIZIONE (usa queste per rispondere alle domande del candidato):\n"
        for key, value in config.knowledge_base.items():
            if value:
                kb_text += f"- {key.upper()}: {value}\n"
    
    system_prompt = f"""Sei {config.bot_name}, un assistente AI recruiter per un'azienda. Stai parlando via WhatsApp con {candidate_name}.

Il tuo obiettivo è:
1. Verificare i requisiti obbligatori (knock-out). Se il candidato non li possiede, ringrazia e chiudi gentilmente la conversazione.
2. Porre domande di screening per qualificare il candidato.
3. Rispondere alle domande del candidato sulla posizione usando le informazioni fornite.

STILE DI COMUNICAZIONE:
- Tono: {tone_desc}
- Usa qualche emoji occasionale (ma non esagerare)
- Sii conciso: messaggi WhatsApp devono essere brevi (max 2-3 frasi)
- Non scrivere mail lunghe, sono messaggi chat
- Sii professionale ma accessibile
{knockout_text}{screening_text}{kb_text}

IMPORTANTE:
- Se il candidato fallisce un requisito obbligatorio, chiudi immediatamente la conversazione con il messaggio di rifiuto
- Procedi con le domande di screening solo se tutti i requisiti obbligatori sono soddisfatti
- Se il candidato fa domande sulla posizione, rispondi usando le informazioni nella Knowledge Base
- Quando hai finito tutte le domande di screening, ringrazia il candidato e concludi la conversazione positivamente
"""
    
    return system_prompt


def check_knockout_rules(
    user_message: str,
    rules: List[KnockoutRule]
) -> Optional[Tuple[bool, str]]:
    """
    Verifica se il messaggio dell'utente fallisce una regola knock-out
    
    Returns:
        None se passa, oppure (False, rejection_message) se fallisce
    """
    user_lower = user_message.lower().strip()
    
    for rule in rules:
        expected_lower = rule.expected_answer.lower().strip()
        
        # Verifica se la risposta contiene la parola chiave attesa
        if expected_lower in user_lower:
            # Passa: contiene la risposta attesa
            continue
        else:
            # Potrebbe essere una risposta negativa
            # Controlla se contiene esplicitamente "no", "non", "non ho", ecc.
            negative_patterns = ["no", "non", "non ho", "non possiedo", "non ho la", "non ho il"]
            if any(pattern in user_lower for pattern in negative_patterns):
                # Fallisce: risposta negativa
                return (False, rule.rejection_message)
    
    # Se siamo qui, tutte le regole sono passate (o non ci sono regole)
    return None


def analyze_message_intent(user_message: str, language: str = "it") -> str:
    """
    Analizza l'intento del messaggio: è una risposta a una domanda o una domanda del candidato?
    
    Returns:
        "answer" se è una risposta, "question" se è una domanda del candidato
    """
    # Pattern semplici per rilevare domande
    question_patterns = [
        r'\?',  # Contiene punto interrogativo
        r'^(quanto|quando|dove|come|perché|perchè|chi|cosa|quale|quali)',
        r'^(posso|puoi|vorrei|mi puoi|potresti)',
        r'^(info|informazioni|dettagli|sapere)'
    ]
    
    user_lower = user_message.lower().strip()
    
    for pattern in question_patterns:
        if re.search(pattern, user_lower):
            return "question"
    
    # Default: assume sia una risposta
    return "answer"


def generate_ai_response(
    config: WhatsappConfig,
    conversation_history: List[Dict[str, str]],
    candidate_name: str = "Candidato"
) -> str:
    """
    Genera una risposta AI basata sulla configurazione e la storia della conversazione
    """
    system_prompt = build_system_prompt(config, candidate_name)
    
    # Costruisci il prompt con la storia della conversazione
    conversation_text = ""
    for msg in conversation_history[-5:]:  # Ultimi 5 messaggi per contesto
        role = msg.get("sender", msg.get("role", "user"))
        content = msg.get("text", msg.get("content", ""))
        if role == "user":
            conversation_text += f"Candidato: {content}\n"
        else:
            conversation_text += f"Bot: {content}\n"
    
    # Ultimo messaggio dell'utente
    last_user_message = ""
    if conversation_history:
        last_msg = conversation_history[-1]
        if last_msg.get("sender") == "user" or last_msg.get("role") == "user":
            last_user_message = last_msg.get("text", last_msg.get("content", ""))
    
    prompt = f"""Stai conversando via WhatsApp con {candidate_name}.

Storia recente della conversazione:
{conversation_text}

Ultimo messaggio del candidato: {last_user_message}

Genera una risposta appropriata. Sii conciso (max 2-3 frasi), usa un tono {config.tone}, e se necessario usa qualche emoji.
"""
    
    try:
        response = get_llm_response(
            prompt=prompt,
            model="gpt-4",  # Usa il deployment configurato
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200  # Limita per messaggi brevi
        )
        return response.strip()
    except Exception as e:
        print(f"Errore generazione risposta AI: {e}")
        return "Mi scuso, c'è stato un problema tecnico. Puoi ripetere la tua domanda?"


def process_whatsapp_message(
    config: WhatsappConfig,
    user_message: str,
    conversation_history: List[Dict[str, str]],
    candidate_name: str = "Candidato"
) -> Tuple[str, Optional[WhatsappStatus], bool]:
    """
    Processa un messaggio WhatsApp e genera la risposta appropriata
    
    Returns:
        (response_text, new_status, is_qualified)
        - response_text: Testo della risposta da inviare
        - new_status: Nuovo stato (None se non cambia, o WhatsappStatus se cambia)
        - is_qualified: True se il candidato è qualificato, False se squalificato, None se ancora in screening
    """
    # 1. Verifica regole knock-out (solo se non sono già state verificate)
    # Assumiamo che le regole vengano verificate in sequenza durante la conversazione
    # Per semplicità, verifichiamo sempre se ci sono regole non ancora verificate
    
    # Conta quante regole sono già state verificate (guardando la storia)
    verified_rules = 0
    for msg in conversation_history:
        if msg.get("sender") == "bot" and "knockout_verified" in msg.get("metadata", {}):
            verified_rules += 1
    
    # Se ci sono regole non ancora verificate, verifica la prossima
    if verified_rules < len(config.knockout_rules):
        next_rule = config.knockout_rules[verified_rules]
        result = check_knockout_rules(user_message, [next_rule])
        
        if result and not result[0]:  # Fallita
            return (result[1], WhatsappStatus.DISQUALIFIED, False)
        else:
            # Passata, procedi alla prossima regola o alle domande di screening
            if verified_rules + 1 >= len(config.knockout_rules):
                # Tutte le regole passate, procedi con screening
                pass
    
    # 2. Analizza intento
    intent = analyze_message_intent(user_message, config.language)
    
    if intent == "question":
        # Il candidato sta facendo una domanda, rispondi usando la KB
        response = generate_ai_response(config, conversation_history, candidate_name)
        return (response, None, None)
    else:
        # Il candidato sta rispondendo a una domanda
        # Verifica se abbiamo finito tutte le domande di screening
        answered_questions = sum(1 for msg in conversation_history if msg.get("sender") == "user")
        
        if answered_questions >= len(config.screening_questions):
            # Screening completato
            response = "Perfetto! Grazie per le tue risposte. Ti contatteremo a breve per il prossimo step del processo di selezione. A presto! 👋"
            return (response, WhatsappStatus.QUALIFIED, True)
        else:
            # Continua con le prossime domande
            response = generate_ai_response(config, conversation_history, candidate_name)
            return (response, None, None)

