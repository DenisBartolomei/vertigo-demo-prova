"""
WhatsApp AI conversation logic
"""
from typing import Dict, Any, Optional, List, Tuple
from backend.models.whatsapp import WhatsappConfig, WhatsappStatus
from interviewer.llm_service import get_llm_response, get_structured_llm_response
import re
import json

# Import prompt library
from services.whatsapp_prompts import (
    TONE_DESCRIPTIONS,
    get_main_system_prompt,
    CV_CONTEXT_TEMPLATE,
    KNOCKOUT_REQUIREMENTS_HEADER,
    KNOCKOUT_REQUIREMENTS_FOOTER,
    get_knockout_check_system_prompt,
    get_knockout_check_prompt,
    get_phase_prompt_greeting,
    get_phase_prompt_knockout,
    get_phase_prompt_qualified,
    get_phase_prompt_qualified_whatsapp,
    get_phase_prompt_complete,
    get_phase_prompt_rejection,
    get_phase_prompt_answer_question,
    get_withdrawal_ask_motivation_prompt,
    get_withdrawal_received_motivation_prompt,
    get_qualified_whatsapp_with_requirements_prompt,
    get_qualified_whatsapp_no_requirements_prompt,
    get_interrupted_late_message_prompt,
    get_interrupted_followup_prompt,
    get_rejection_with_reason_prompt,
    WITHDRAWAL_PATTERNS,
    QUESTION_PATTERNS,
    WITHDRAWAL_ASK_PATTERNS,
    FINAL_GOODBYE_PATTERNS,
    GOODBYE_PATTERNS,
    WITHDRAWAL_BOT_PATTERNS
)


def build_conversational_system_prompt(
    config: WhatsappConfig, 
    candidate_name: str = "Candidato",
    position_name: Optional[str] = None,
    knockout_requirements: Optional[List[str]] = None,
    position_ral: Optional[str] = None,
    position_sede: Optional[str] = None,
    position_smart_working: Optional[str] = None,
    cv_text: Optional[str] = None
) -> str:
    """
    Costruisce il system prompt per una conversazione naturale e personalizzata.
    Usa i template dalla libreria whatsapp_prompts.py
    NOTA: cv_analysis_report rimosso per risparmio token
    """
    tone_desc = TONE_DESCRIPTIONS.get(config.tone, "amichevole e genuino")
    position_display = position_name or "questa posizione"
    
    # Costruisci contesto CV (solo testo CV, no analisi per risparmio token)
    cv_context = ""
    if cv_text:
        cv_excerpt = cv_text[:2000] + "..." if len(cv_text) > 2000 else cv_text
        cv_context = CV_CONTEXT_TEMPLATE.format(cv_excerpt=cv_excerpt)
    
    # Costruisci lista requisiti obbligatori
    knockout_text = ""
    if knockout_requirements:
        knockout_text = KNOCKOUT_REQUIREMENTS_HEADER
        for i, requirement in enumerate(knockout_requirements, 1):
            knockout_text += f"  {i}. {requirement}\n"
        knockout_text += KNOCKOUT_REQUIREMENTS_FOOTER
    
    # Info posizione
    position_info = ""
    if position_ral or position_sede or position_smart_working:
        position_info = "\n\nINFORMAZIONI SULLA POSIZIONE (usa se il candidato chiede):\n"
        if position_ral:
            position_info += f"- Retribuzione: {position_ral}\n"
        if position_sede:
            position_info += f"- Sede di lavoro: {position_sede}\n"
        if position_smart_working:
            position_info += f"- Smart working: {position_smart_working}\n"
    
    # Knowledge base aziendale
    kb_text = ""
    if config.knowledge_base:
        kb_text = "\n\nINFO AZIENDALI (usa se il candidato chiede):\n"
        for key, value in config.knowledge_base.items():
            if value:
                kb_text += f"- {key}: {value}\n"
    
    return get_main_system_prompt(
        bot_name=config.bot_name,
        candidate_name=candidate_name,
        position_name=position_display,
        tone_desc=tone_desc,
        cv_context=cv_context,
        knockout_text=knockout_text,
        position_info=position_info,
        kb_text=kb_text
    )


def check_knockout_requirements(
    user_message: str,
    requirements: List[str],
    conversation_history: List[Dict[str, str]],
    language: str = "it"
) -> Optional[Tuple[bool, str]]:
    """
    Usa l'AI per verificare se il candidato possiede i requisiti obbligatori.
    Analizza la conversazione per determinare lo stato.
    NOTA: cv_analysis_report rimosso per risparmio token
    
    Returns:
        (True, None) = tutti i requisiti verificati positivamente
        (False, rejection_message) = manca un requisito fondamentale
        None = servono più informazioni, continua la conversazione
    """
    if not requirements:
        return (True, None)  # Nessun requisito = passa
    
    # Costruisci il contesto della conversazione (tutti i messaggi)
    conversation_context = ""
    for msg in conversation_history:
        role = msg.get("sender", msg.get("role", "user"))
        content = msg.get("text", msg.get("content", ""))
        if role == "user":
            conversation_context += f"Candidato: {content}\n"
        else:
            conversation_context += f"Recruiter: {content}\n"
    
    # Prompt per l'AI per verificare i requisiti
    requirements_text = "\n".join([f"{i+1}. {req}" for i, req in enumerate(requirements)])

    system_prompt = get_knockout_check_system_prompt(requirements_text)
    prompt = get_knockout_check_prompt("", conversation_context, user_message)
    
    try:
        tool_schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["verified", "rejected", "need_more_info"],
                    "description": "verified = tutti i requisiti ok, rejected = manca requisito, need_more_info = servono chiarimenti"
                },
                "missing_requirement": {
                    "type": "string",
                    "description": "Solo se status=rejected: quale requisito manca"
                },
                "reason": {
                    "type": "string", 
                    "description": "Breve spiegazione della decisione"
                }
            },
            "required": ["status"]
        }
        
        response_json = get_structured_llm_response(
            prompt=prompt,
            model="gpt-4.1-mini",
            system_prompt=system_prompt,
            tool_name="evaluate_requirements",
            tool_schema=tool_schema,
            temperature=0.2, # Più deterministico
            use_classification_client=True
        )
        
        if response_json:
            result = json.loads(response_json)
            status = result.get("status", "need_more_info")
            
            print(f"📋 Knockout check result: {result}")
            
            if status == "verified":
                return (True, None)
            elif status == "rejected":
                missing = result.get("missing_requirement", "un requisito fondamentale")
                return (False, missing)
            else:
                # need_more_info
                return None
        
        return None
        
    except Exception as e:
        print(f"Errore verifica requisiti AI: {e}")
        # In caso di errore, chiedi più info
        return None


def analyze_message_intent(user_message: str, language: str = "it", conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Analizza l'intento del messaggio per ottimizzare il contesto da passare all'AI.
    Usa i pattern dalla libreria whatsapp_prompts.py
    
    Returns:
        "question" - Domanda informativa (RAL, sede, benefits, processo) → usa contesto info aziendali
        "answer" - Risposta a verifica knockout → usa contesto CV/knockout
        "withdrawal" - Intenzione di ritirarsi dalla candidatura
        "withdrawal_reason" - Messaggio che contiene la motivazione del ritiro (dopo che abbiamo chiesto)
    """
    user_lower = user_message.lower().strip()
    
    # 0. Controlla se stiamo aspettando una motivazione di ritiro
    if conversation_history:
        bot_messages = [msg for msg in conversation_history if msg.get("sender") == "bot"]
        if bot_messages:
            last_bot_msg = bot_messages[-1].get("text", "").lower()
            # Controlla se il messaggio del bot parla di ritiro/motivazione
            if any(phrase in last_bot_msg for phrase in WITHDRAWAL_ASK_PATTERNS):
                # E il messaggio NON è un saluto finale
                is_final_goodbye = any(bye in last_bot_msg for bye in FINAL_GOODBYE_PATTERNS)
                if not is_final_goodbye:
                    print(f"📝 Intent: WITHDRAWAL_REASON (risposta a richiesta motivazione)")
                    return "withdrawal_reason"
    
    # 1. Pattern per RITIRO candidatura (priorità alta)
    for pattern in WITHDRAWAL_PATTERNS:
        if re.search(pattern, user_lower):
            print(f"📝 Intent: WITHDRAWAL (pattern: {pattern})")
            return "withdrawal"
    
    # 2. Pattern per DOMANDE INFORMATIVE su posizione/azienda
    for pattern in QUESTION_PATTERNS:
        if re.search(pattern, user_lower):
            print(f"📝 Intent: QUESTION (pattern: {pattern})")
            return "question"
    
    # 3. Default: assume sia una RISPOSTA a verifica knockout
    print(f"📝 Intent: ANSWER (risposta a verifica)")
    return "answer"


def generate_conversational_response(
    config: WhatsappConfig,
    conversation_history: List[Dict[str, str]],
    candidate_name: str = "Candidato",
    position_name: Optional[str] = None,
    knockout_requirements: Optional[List[str]] = None,
    position_ral: Optional[str] = None,
    position_sede: Optional[str] = None,
    position_smart_working: Optional[str] = None,
    cv_text: Optional[str] = None,
    phase: str = "greeting",
    interview_url: Optional[str] = None,
    specific_instruction: Optional[str] = None
) -> str:
    """
    Genera una risposta AI conversazionale e naturale basata sul contesto completo.
    Usa i prompt dalla libreria whatsapp_prompts.py
    NOTA: cv_analysis_report rimosso per risparmio token
    """
    system_prompt = build_conversational_system_prompt(
        config, 
        candidate_name,
        position_name=position_name,
        knockout_requirements=knockout_requirements,
        position_ral=position_ral,
        position_sede=position_sede,
        position_smart_working=position_smart_working,
        cv_text=cv_text
    )
    
    # Costruisci il prompt con la storia della conversazione
    conversation_text = ""
    for msg in conversation_history[-8:]:  # Ultimi 8 messaggi per contesto
        role = msg.get("sender", msg.get("role", "user"))
        content = msg.get("text", msg.get("content", ""))
        if role == "user":
            conversation_text += f"Candidato: {content}\n"
        else:
            conversation_text += f"Tu: {content}\n"
    
    # Costruisci istruzioni specifiche per fase usando la libreria prompt
    phase_instructions = {
        "greeting": get_phase_prompt_greeting(candidate_name),
        "knockout": get_phase_prompt_knockout(conversation_text),
        "qualified": get_phase_prompt_qualified(interview_url or ""),
        "qualified_whatsapp": get_phase_prompt_qualified_whatsapp(),
        "complete": get_phase_prompt_complete(interview_url or "", conversation_text),
        "rejection": get_phase_prompt_rejection(),
        "answer_question": get_phase_prompt_answer_question(conversation_text)
    }
    
    instruction = phase_instructions.get(phase, phase_instructions["complete"])
    if specific_instruction:
        instruction = specific_instruction
    
    prompt = f"""{instruction}

Genera ORA la tua risposta (solo il testo del messaggio, nient'altro):"""
    
    try:
        response = get_llm_response(
            prompt=prompt,
            model="gpt-4.1-mini",
            system_prompt=system_prompt,
            temperature=0.8,  # Più creatività per essere naturale
            max_tokens=250,
                use_classification_client=True
        )
        cleaned_response = response.strip()
        
        # Rimuovi saluti ripetuti se non siamo nella fase greeting
        # Controlla se ci sono già messaggi bot nella conversazione (escludendo il template)
        bot_messages = [msg for msg in conversation_history if msg.get("sender") == "bot"]
        if phase != "greeting" and len(bot_messages) > 0:
            # Rimuovi saluti comuni all'inizio del messaggio
            import re
            # Pattern per saluti comuni (Ciao, Ciao [Nome], Salve, ecc.)
            greeting_patterns = [
                r'^ciao\s+[^!]*[!.]?\s*',
                r'^ciao[!.]?\s*',
                r'^salve[!.]?\s*',
                r'^buongiorno[!.]?\s*',
                r'^buonasera[!.]?\s*',
            ]
            for pattern in greeting_patterns:
                cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.IGNORECASE)
            cleaned_response = cleaned_response.strip()
        
        return cleaned_response
    except Exception as e:
        print(f"Errore generazione risposta AI: {e}")
        return "Mi scuso, c'è stato un problema tecnico. Puoi riprovare tra poco? 🙏"


def get_conversation_state(conversation_history: List[Dict[str, str]], config: WhatsappConfig, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analizza lo stato corrente della conversazione per capire a che punto siamo.
    
    Flusso:
    1. GREETING: Prima risposta dell'utente al template
    2. KNOCKOUT: Verifica requisiti (può durare più messaggi)
    3. COMPLETE: Candidato qualificato, ha ricevuto il link
    4. INTERRUPTED: Candidato ha interrotto la candidatura
    
    Returns:
        {
            "phase": "greeting" | "knockout" | "complete" | "interrupted",
            "knockout_verified": bool
        }
    """
    # Conta i messaggi bot e user
    bot_messages = [msg for msg in conversation_history if msg.get("sender") == "bot"]
    user_messages = [msg for msg in conversation_history if msg.get("sender") == "user"]
    
    print(f"📊 Conversation state check: {len(bot_messages)} bot msgs, {len(user_messages)} user msgs")
    
    # Controlla se la sessione è già stata interrotta
    if session_data:
        ws_status = session_data.get("whatsapp_status")
        ws_result = session_data.get("whatsapp_screening_result")
        if ws_status == "interrupted" or ws_result == "interrupted":
            print(f"   → Phase: INTERRUPTED (candidatura già interrotta)")
            return {
                "phase": "interrupted",
                "knockout_verified": False
            }
        
        # IMPORTANTE: Se il candidato è già qualificato, NON tornare mai a fase knockout
        if ws_status == "qualified" or ws_status == "qualified_whatsapp" or ws_result == "qualified":
            print(f"   → Phase: QUALIFIED (candidato già qualificato - solo domande informative)")
            return {
                "phase": "qualified",
                "knockout_verified": True  # Già verificato, non richiedere più
            }
    
    # Se è il primo messaggio dell'utente (risposta al template), siamo in fase greeting
    if len(user_messages) <= 1:
        print(f"   → Phase: GREETING (prima risposta utente)")
        return {
            "phase": "greeting",
            "knockout_verified": False
        }
    
    # Cerca nei messaggi bot se abbiamo già inviato il link del colloquio
    # Questo indica che siamo in fase COMPLETE
    for msg in bot_messages:
        msg_text = msg.get("text", "").lower()
        if "interview/" in msg_text or "colloquio" in msg_text and ("link" in msg_text or "http" in msg_text):
            print(f"   → Phase: COMPLETE (link colloquio già inviato)")
            return {
                "phase": "complete",
                "knockout_verified": True
            }
    
    # Cerca nei messaggi bot se abbiamo già chiuso per ritiro/interruzione
    for msg in bot_messages:
        msg_text = msg.get("text", "").lower()
        if any(p in msg_text for p in GOODBYE_PATTERNS) and any(p in msg_text for p in WITHDRAWAL_BOT_PATTERNS):
            print(f"   → Phase: INTERRUPTED (messaggio di chiusura per ritiro trovato)")
            return {
                "phase": "interrupted",
                "knockout_verified": False
            }
    
    # Altrimenti siamo ancora in fase KNOCKOUT (verifica requisiti)
    print(f"   → Phase: KNOCKOUT (verifica requisiti in corso)")
    return {
        "phase": "knockout",
        "knockout_verified": False
    }


def process_whatsapp_message(
    config: WhatsappConfig,
    user_message: str,
    conversation_history: List[Dict[str, str]],
    candidate_name: str = "Candidato",
    interview_token: Optional[str] = None,
    position_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    cv_text: Optional[str] = None,
    position_data: Optional[Dict[str, Any]] = None,
    session_data: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[WhatsappStatus], Optional[bool], Optional[str]]:
    """
    Processa un messaggio WhatsApp e genera una risposta CONVERSAZIONALE usando l'AI.
    L'AI ha accesso a CV, analisi CV, requisiti della posizione e info aziendali.
    
    Flusso: GREETING -> KNOCKOUT (conversazionale) -> QUALIFIED/REJECTED
    
    Returns:
        (response_text, new_status, is_qualified, interruption_reason)
    """
    import os
    
    # 0. Controlla se c'è un ritiro in corso nella sessione (PRIORITÀ ALTA)
    # Se c'è un ritiro in corso, gestisci solo quello e NON verificare requisiti
    withdrawal_in_progress = False
    if session_data:
        withdrawal_in_progress = session_data.get("_withdrawal_in_progress", False)
    
    if withdrawal_in_progress:
        print(f"🔄 Ritiro in corso rilevato nella sessione - gestisco solo la motivazione")
        # Il candidato sta fornendo la motivazione del ritiro
        withdrawal_reason = user_message.strip()[:200]  # Max 200 caratteri
        print(f"📝 Motivazione ritiro ricevuta: {withdrawal_reason}")
        
        response = generate_conversational_response(
            config, conversation_history, candidate_name,
            phase="rejection",
            specific_instruction=get_withdrawal_received_motivation_prompt(withdrawal_reason)
        )
        # Salva la motivazione esatta del candidato nel formato corretto
        return (response, WhatsappStatus.INTERRUPTED, False, f"ritiro: {withdrawal_reason}")
    
    # 1. Analizza l'intento del messaggio per ottimizzare il contesto
    intent = analyze_message_intent(user_message, config.language, conversation_history)
    print(f"🎯 Intento rilevato: {intent}")
    
    # Controlla se c'è un ritiro pendente nella posizione (legacy, per retrocompatibilità)
    withdrawal_pending = False
    if position_data:
        withdrawal_pending = position_data.get("_withdrawal_pending", False)
    
    # Se il candidato sta fornendo la MOTIVAZIONE del ritiro (dopo che gliel'abbiamo chiesta)
    # O se abbiamo un ritiro pendente nel DB
    if intent == "withdrawal_reason" or withdrawal_pending:
        # Salva la motivazione fornita dal candidato
        withdrawal_reason = user_message.strip()[:200]  # Max 200 caratteri
        print(f"📝 Motivazione ritiro ricevuta: {withdrawal_reason}")
        
        response = generate_conversational_response(
            config, conversation_history, candidate_name,
            phase="rejection",
            specific_instruction=get_withdrawal_received_motivation_prompt(withdrawal_reason)
        )
        # Salva la motivazione esatta del candidato
        return (response, WhatsappStatus.INTERRUPTED, False, f"ritiro: {withdrawal_reason}")
    
    # Se il candidato vuole ritirarsi, CHIUDI DIRETTAMENTE con richiesta motivazione integrata
    # IMPORTANTE: Questo è un ritiro VOLONTARIO, non per mancanza requisiti
    if intent == "withdrawal":
        print(f"🔄 Ritiro volontario rilevato - chiedo motivazione e marco flag nella sessione")
        response = generate_conversational_response(
            config, conversation_history, candidate_name,
            phase="rejection",
            specific_instruction=get_withdrawal_ask_motivation_prompt(candidate_name)
        )
        # Chiudiamo SUBITO con stato INTERRUPTED - motivazione generica temporanea
        # Il flag _withdrawal_in_progress verrà salvato nel router per indicare che stiamo aspettando la motivazione
        return (response, WhatsappStatus.INTERRUPTED, False, "ritiro_candidato")
    
    # Estrai dati posizione
    knockout_requirements = []
    position_ral = None
    position_sede = None
    position_smart_working = None
    position_name = None
    workflow_type = "full"  # Default: flusso completo con colloquio AI
    
    if position_data:
        knockout_requirements = position_data.get("knockout_requirements", []) or []
        position_ral = position_data.get("ral")
        position_sede = position_data.get("sede")
        position_smart_working = position_data.get("smart_working")
        position_name = position_data.get("position_name", "questa posizione")
        workflow_type = position_data.get("workflow_type", "full")
    
    # Determina lo stato corrente della conversazione
    # Passa session_data per verificare stato qualificato/interrotto
    state = get_conversation_state(conversation_history, config, session_data)
    
    print(f"📱 WhatsApp AI - State: {state}, Position: {position_name}, Knockout: {len(knockout_requirements)} requisiti")
    print(f"   CV Text: {'Sì (' + str(len(cv_text)) + ' chars)' if cv_text else 'No'}")
    
    candidate_frontend_url = os.getenv("CANDIDATE_FRONTEND_URL", "https://vertigo-candidate.web.app")
    interview_url = f"{candidate_frontend_url}/interview/{interview_token}" if interview_token else None
    
    # Conta messaggi utente per limitare CV alle prime interazioni
    user_messages = [m for m in conversation_history if m.get("sender") == "user"]
    include_cv_context = len(user_messages) <= 3  # Prime 3 interazioni per knockout
    
    print(f"📊 CV Context: {len(user_messages)} messaggi utente → {'Incluso' if include_cv_context else 'Escluso'} (limite: 3)")
    
    # ========================================
    # CONTESTI SEPARATI PER OTTIMIZZAZIONE TOKEN
    # ========================================
    
    # CONTESTO QUESTION: per rispondere a domande informative (RAL, sede, benefits)
    # NON include CV - solo info aziendali e posizione
    question_context = {
        "config": config,
        "conversation_history": conversation_history,
        "candidate_name": candidate_name,
        "position_name": position_name,
        "position_ral": position_ral,
        "position_sede": position_sede,
        "position_smart_working": position_smart_working,
        "cv_text": None,  # NO CV - non serve per rispondere a domande
        "knockout_requirements": knockout_requirements,
        "interview_url": interview_url
    }
    
    # CONTESTO KNOCKOUT: per verificare requisiti con riferimento al CV
    # Include CV, NO info dettagliate posizione (non servono per la verifica)
    knockout_context = {
        "config": config,
        "conversation_history": conversation_history,
        "candidate_name": candidate_name,
        "position_name": position_name,
        "knockout_requirements": knockout_requirements,
        "cv_text": cv_text if include_cv_context else None,
        "position_ral": None,
        "position_sede": None,
        "position_smart_working": None,
        "interview_url": interview_url
    }
    
    # CONTESTO COMPLETO: per fasi che richiedono tutto (qualified, complete)
    full_context = {
        "config": config,
        "conversation_history": conversation_history,
        "candidate_name": candidate_name,
        "position_name": position_name,
        "knockout_requirements": knockout_requirements,
        "position_ral": position_ral,
        "position_sede": position_sede,
        "position_smart_working": position_smart_working,
        "cv_text": cv_text if include_cv_context else None,
        "interview_url": interview_url
    }
    
    print(f"📦 Contesti pronti: question={bool(question_context)}, knockout={bool(knockout_context)}, full={bool(full_context)}")
    
    # ========================================
    # GESTIONE DOMANDE INFORMATIVE (PRIORITÀ ALTA)
    # ========================================
    # Se il candidato fa una domanda informativa (RAL, sede, benefits, ecc.)
    # rispondiamo E allo stesso tempo riprendiamo il flusso knockout
    # IMPORTANTE: Se c'è un ritiro in corso, NON gestire domande come knockout
    
    if intent == "question" and state["phase"] != "greeting" and not withdrawal_in_progress:
        print(f"💬 Gestione DOMANDA INFORMATIVA + RIPRESA KNOCKOUT")
        # Per rispondere E riprendere knockout, serve un contesto ibrido
        # che abbia sia info posizione che knockout requirements
        hybrid_context = {
            "config": config,
            "conversation_history": conversation_history,
            "candidate_name": candidate_name,
            "position_name": position_name,
            "position_ral": position_ral,
            "position_sede": position_sede,
            "position_smart_working": position_smart_working,
            "knockout_requirements": knockout_requirements,
            "cv_text": cv_text if include_cv_context else None,
            "interview_url": interview_url
        }
        response = generate_conversational_response(
            **hybrid_context, 
            phase="answer_question"
        )
        # Non cambia stato - dopo la risposta continua con la verifica knockout
        return (response, None, None, None)
    
    # ========================================
    # FASI STANDARD DEL FLUSSO
    # ========================================
    
    # IMPORTANTE: Se il candidato è già qualificato, gestisci solo domande informative
    # NON richiedere mai più i requisiti knockout
    if state["phase"] == "qualified" or state["knockout_verified"] == True:
        print(f"✅ Candidato già qualificato - gestisco solo domande informative")
        
        # Se l'intent è una domanda, rispondi solo a quella
        if intent == "question":
            print(f"💬 Domanda informativa da candidato qualificato")
            response = generate_conversational_response(**question_context, phase="answer_question")
            return (response, None, None, None)
        else:
            # Se non è una domanda, reindirizza gentilmente a domande informative
            print(f"💬 Messaggio non-domanda da candidato qualificato - reindirizzo a domande")
            response = generate_conversational_response(
                **question_context,
                phase="complete",
                specific_instruction="Il candidato è già qualificato. Se ha fatto una domanda, rispondi. Altrimenti, invitalo gentilmente a fare domande sulla posizione o sul processo se ha bisogno di informazioni."
            )
            return (response, None, None, None)
    
    # 1. FASE GREETING: Prima risposta dell'utente (dopo il template)
    if state["phase"] == "greeting":
        if knockout_requirements:
            # Usa knockout_context per iniziare la verifica con riferimento al CV
            print(f"👋 GREETING con knockout - usa knockout_context (con CV)")
            response = generate_conversational_response(**knockout_context, phase="greeting")
            return (response, None, None, None)
        else:
            # Nessun requisito knockout - qualifica direttamente
            if workflow_type == "whatsapp_only":
                print(f"👋 GREETING senza knockout - QUALIFIED_WHATSAPP (solo pre-screening)")
                response = generate_conversational_response(
                    **full_context, 
                    phase="qualified_whatsapp",
                    specific_instruction=get_qualified_whatsapp_no_requirements_prompt()
                )
                return (response, WhatsappStatus.QUALIFIED_WHATSAPP, True, None)
            else:
                print(f"👋 GREETING senza knockout - vai a QUALIFIED (flusso completo)")
                response = generate_conversational_response(**full_context, phase="qualified")
                return (response, WhatsappStatus.QUALIFIED, True, None)
    
    # 2. FASE KNOCKOUT: Verifica requisiti obbligatori in modo conversazionale
    # IMPORTANTE: Se c'è un ritiro in corso, NON verificare i requisiti
    if state["phase"] == "knockout" and knockout_requirements and not withdrawal_in_progress:
        print(f"🔍 KNOCKOUT - usa knockout_context (con CV)")
        
        # Prima verifica se il candidato fallisce un requisito usando AI
        result = check_knockout_requirements(
            user_message,
            knockout_requirements,
            conversation_history,
            config.language
        )
        
        if result and not result[0]:  # Fallita verifica requisiti
            # IMPORTANTE: Questo è mancanza requisiti, NON ritiro volontario
            # Assicuriamoci che non ci sia confusione con ritiro volontario
            # Genera messaggio di rifiuto personalizzato
            rejection_response = generate_conversational_response(
                **knockout_context, 
                phase="rejection",
                specific_instruction=get_rejection_with_reason_prompt(result[1])
            )
            # Formato: "mancanza_requisiti: [requisito mancante]" per distinguerlo da "ritiro: [motivazione]"
            missing_req = result[1] or "requisito fondamentale"
            return (rejection_response, WhatsappStatus.INTERRUPTED, False, f"mancanza_requisiti: {missing_req}")
        
        # Se result è None, potremmo aver bisogno di più info - continua la conversazione
        if result is None:
            # L'AI valuta se abbiamo abbastanza info sui requisiti
            response = generate_conversational_response(**knockout_context, phase="knockout")
            return (response, None, None, None)
        
        # Requisiti verificati positivamente! Qualifica in base al workflow
        if workflow_type == "whatsapp_only":
            print(f"✅ Tutti i requisiti verificati - QUALIFIED_WHATSAPP (solo pre-screening)")
            response = generate_conversational_response(
                **full_context, 
                phase="qualified_whatsapp",
                specific_instruction=get_qualified_whatsapp_with_requirements_prompt()
            )
            return (response, WhatsappStatus.QUALIFIED_WHATSAPP, True, None)
        else:
            print(f"✅ Tutti i requisiti verificati - passa a QUALIFIED (flusso completo)")
            response = generate_conversational_response(**full_context, phase="qualified")
            return (response, WhatsappStatus.QUALIFIED, True, None)
    
    # 3. FASE COMPLETE: Il candidato è già stato qualificato
    if state["phase"] == "complete":
        print(f"🎉 COMPLETE - usa question_context per eventuali domande")
        # In questa fase rispondiamo a domande, quindi usiamo question_context
        response = generate_conversational_response(**question_context, phase="complete")
        return (response, None, None, None)
    
    # 4. FASE INTERRUPTED: La candidatura è già stata interrotta
    if state["phase"] == "interrupted":
        print(f"🚫 INTERRUPTED - candidatura già chiusa")
        # Il candidato scrive dopo che la candidatura è stata interrotta
        # Potrebbe essere una motivazione tardiva o solo un messaggio di follow-up
        
        # Se il messaggio sembra una motivazione (non è una domanda o un saluto)
        msg_lower = user_message.lower().strip()
        is_just_greeting = any(g in msg_lower for g in ["ciao", "ok", "grazie", "va bene", "capito"])
        
        if not is_just_greeting and len(user_message) > 10:
            # Potrebbe essere una motivazione tardiva - aggiornala
            print(f"📝 Aggiornamento motivazione tardiva: {user_message[:50]}...")
            response = generate_conversational_response(
                config, conversation_history, candidate_name,
                phase="complete",
                specific_instruction=get_interrupted_late_message_prompt()
            )
            # Ritorna con la nuova motivazione
            return (response, None, None, f"ritiro: {user_message.strip()[:200]}")
        else:
            # Semplice follow-up - rispondi brevemente
            response = generate_conversational_response(
                config, conversation_history, candidate_name,
                phase="complete",
                specific_instruction=get_interrupted_followup_prompt()
            )
            return (response, None, None, None)
    
    # Fallback: genera risposta conversazionale per continuare knockout
    print(f"🔄 Fallback - continua knockout")
    response = generate_conversational_response(**knockout_context, phase="knockout")
    return (response, None, None, None)

