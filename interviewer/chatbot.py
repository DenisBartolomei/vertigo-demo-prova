# interviewer/chatbot.py
from interviewer.llm_service import AZURE_DEPLOYMENT_NAME, AZURE_CLASSIFICATION_DEPLOYMENT_NAME
from .llm_service import get_llm_response
from . import prompts
import json
import os
from datetime import datetime

class SmartCaseStudyChatbot:
    # --- CONFIGURAZIONE DEI MODELLI ---
    # TEST: Usa il classification deployment per tutto il colloquio
    INTERVIEWER_MODEL = AZURE_CLASSIFICATION_DEPLOYMENT_NAME  # Era: AZURE_DEPLOYMENT_NAME
    CLASSIFICATION_MODEL = AZURE_CLASSIFICATION_DEPLOYMENT_NAME
    USE_CLASSIFICATION_CLIENT = True  # Flag per usare il client di classificazione

    def __init__(self, steps: dict, case_title: str, case_text: str, case_id: str, max_attempts: int = 5, max_questions: int = 10, language: str = "it"):
        self.steps = steps
        self.case_title = case_title
        self.case_text = case_text
        self.case_id = case_id
        self.max_attempts = max_attempts
        self.max_questions = max_questions
        self.language = language  # Store language for multi-language support
        self.questions_asked_count = 0
        self.current_step_id = None
        self.completed_step_ids = set()
        self.attempts_on_current_step = 0
        self.conversation_history = []
        self.is_finished = False

    def _save_conversation_history(self):
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.case_id}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            print(f"\n[INFO] Conversazione salvata in: {filepath}")
        except Exception as e:
            print(f"\n[ERRORE] Impossibile salvare la conversazione: {e}")

    def start_interview(self) -> str:
        self.current_step_id = 0
        step_zero_info = self.steps[self.current_step_id]
        skills_str = ", ".join([s.get('skill_name', '') for s in step_zero_info.get('skills_to_test', []) if s.get('skill_name')])
        prompt = prompts.create_start_prompt(
            self.case_title,
            self.case_text,
            step_zero_info.get('description', 'N/D'),
            skills_str,
            self.language
        )
        initial_message = get_llm_response(
            prompt=prompt, 
            model=self.INTERVIEWER_MODEL, 
            system_prompt=prompts.SYSTEM_PROMPT[self.language],
            use_classification_client=self.USE_CLASSIFICATION_CLIENT,
            temperature=0.7
        )
        self.conversation_history.append({"role": "assistant", "content": initial_message})
        return initial_message

    def _is_user_input_a_question(self, user_input: str) -> bool:
        prompt = prompts.create_input_classification_prompt(user_input, self.language)
        classification_system_prompts = {
            "it": "Sei un classificatore di testo estremamente preciso e letterale. Il tuo unico scopo è restituire una delle due opzioni fornite.",
            "en": "You are an extremely precise and literal text classifier. Your sole purpose is to return one of the two options provided."
        }
        response = get_llm_response(
            prompt=prompt,
            model=self.CLASSIFICATION_MODEL, 
            system_prompt=classification_system_prompts.get(self.language, classification_system_prompts["it"]),
            use_classification_client=True,  # Usa il client di classificazione (gpt-4.1-mini)
            temperature=0.0,
            max_tokens=10
        )
        return "DOMANDA_SUL_CASO" in response.upper() or "QUESTION_ABOUT_CASE" in response.upper()

    def _answer_candidate_question(self, user_question: str) -> str:
        self.questions_asked_count += 1
        remaining_q = self.max_questions - self.questions_asked_count
        current_step_info = self.steps[self.current_step_id]
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])
        answer_prompt = prompts.create_answer_to_candidate_question_prompt(
            case_text=self.case_text,
            current_step_description=current_step_info.get('description', ''),
            user_question=user_question,
            history_text=history_text,
            language=self.language
        )
        answer = get_llm_response(
            prompt=answer_prompt,
            model=self.INTERVIEWER_MODEL,
            system_prompt=prompts.SYSTEM_PROMPT[self.language],
            use_classification_client=self.USE_CLASSIFICATION_CLIENT
        )
        remaining_msg = f"\n\n*(Hai ancora {remaining_q} domande a disposizione.)*" if self.language == "it" else f"\n\n*(You still have {remaining_q} questions available.)*"
        answer += remaining_msg
        return answer

    def process_user_response(self, user_input: str) -> str:
        if self.is_finished:
            finished_msg = {
                "it": "Il colloquio è terminato. Grazie per la tua partecipazione! Riceverai l'esito appena avremo valutato il tuo esercizio",
                "en": "The interview has ended. Thank you for your participation! You will receive the outcome as soon as we have evaluated your exercise"
            }
            return finished_msg.get(self.language, finished_msg["it"])
        self.conversation_history.append({"role": "user", "content": user_input})
        if self._is_user_input_a_question(user_input):
            if self.questions_asked_count < self.max_questions:
                response = self._answer_candidate_question(user_input)
            else:
                no_questions_msg = {
                    "it": "Hai esaurito le domande a tua disposizione. Per favore, procedi ora con la tua analisi.",
                    "en": "You have exhausted your available questions. Please proceed now with your analysis."
                }
                response = no_questions_msg.get(self.language, no_questions_msg["it"])
        else:
            self.attempts_on_current_step += 1
            is_step_accomplished = self._evaluate_step_completion()
            if is_step_accomplished:
                self.completed_step_ids.add(self.current_step_id)
                response = self._transition_to_next_step()
            else:
                if self.attempts_on_current_step >= self.max_attempts:
                    self.completed_step_ids.add(self.current_step_id)
                    response = self._conclude_step_and_transition()
                else:
                    response = self._provide_guidance()
        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    def _evaluate_step_completion(self) -> bool:
        current_step = self.steps[self.current_step_id]
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history[-8:]])

        # Contesto + Criterio + Skill da verificare
        step_full_context = f"Titolo: {current_step.get('title', 'N/D')}\nDescrizione: {current_step.get('description', 'N/D')}"
        skills_str = ", ".join([s.get('skill_name', '') for s in current_step.get('skills_to_test', []) if s.get('skill_name')])

        no_criteria_msg = {
            "it": "Nessun criterio specifico fornito.",
            "en": "No specific criteria provided."
        }
        prompt = prompts.create_evaluation_prompt(
            step_context=step_full_context,
            criteria=current_step.get('criteria', no_criteria_msg.get(self.language, no_criteria_msg["it"])),
            skills_to_test=skills_str,
            history_text=history_text,
            language=self.language
        )

        evaluation = get_llm_response(
            prompt=prompt, 
            model=self.INTERVIEWER_MODEL,
            system_prompt=prompts.SYSTEM_PROMPT[self.language],
            use_classification_client=self.USE_CLASSIFICATION_CLIENT,
            temperature=0.2, 
            max_tokens=10
        )
        return "TRUE" in evaluation.upper()

    def _select_next_step(self) -> int | None:
        available_steps = [step for id, step in self.steps.items() if id not in self.completed_step_ids]
        if not available_steps: 
            return None
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])
        # Includi anche le skill per ogni step tra le opzioni
        def _skills(step):
            return ", ".join([s.get('skill_name', '') for s in step.get('skills_to_test', []) if s.get('skill_name')]) or "N/D"
        options_text = "\n".join([f"ID: {s['id']}, Titolo: {s['title']}, Skill: {_skills(s)}" for s in available_steps])
        prompt = prompts.create_next_step_selection_prompt(options_text, history_text, self.language)
        logical_assistant_prompts = {
            "it": "Sei un assistente logico.",
            "en": "You are a logical assistant."
        }
        try:
            next_id_str = get_llm_response(
                prompt=prompt, model=self.INTERVIEWER_MODEL,
                system_prompt=logical_assistant_prompts.get(self.language, logical_assistant_prompts["it"]),
                use_classification_client=self.USE_CLASSIFICATION_CLIENT,
                temperature=0.1, max_tokens=5
            )
            next_id = int(''.join(filter(str.isdigit, next_id_str)))
            valid_ids = [s['id'] for s in available_steps]
            return next_id if next_id in valid_ids else available_steps[0]['id']
        except (ValueError, IndexError): 
            return available_steps[0]['id']

    def _transition_to_next_step(self):
        next_step_id = self._select_next_step()
        if next_step_id is None:
            self.is_finished = True
            self._save_conversation_history()
            return prompts.SUCCESSFUL_FINISH_MESSAGE[self.language]
        current_step_info = self.steps[self.current_step_id]
        next_step_info = self.steps[next_step_id]
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])
        prompt = prompts.create_successful_transition_prompt(
            current_step_info.get('title', ''),
            next_step_info.get('title', ''),
            next_step_info.get('description', ''),
            history_text,
            self.language
        )
        self.current_step_id = next_step_id
        self.attempts_on_current_step = 0
        return get_llm_response(prompt=prompt, model=self.INTERVIEWER_MODEL, system_prompt=prompts.SYSTEM_PROMPT[self.language], use_classification_client=self.USE_CLASSIFICATION_CLIENT)

    def _conclude_step_and_transition(self):
        next_step_id = self._select_next_step()
        if next_step_id is None:
            self.is_finished = True
            self._save_conversation_history()
            return prompts.FORCED_FINISH_MESSAGE[self.language]

        current_step_info = self.steps[self.current_step_id]
        next_step_info = self.steps[next_step_id]

        no_criteria_msg = {
            "it": "Nessun criterio specifico.",
            "en": "No specific criteria."
        }
        skills_str = ", ".join([s.get('skill_name', '') for s in current_step_info.get('skills_to_test', [])])
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])

        prompt = prompts.create_failed_transition_prompt(
            current_step_info.get('title', ''),
            current_step_info.get('criteria', no_criteria_msg.get(self.language, no_criteria_msg["it"])),
            skills_str,
            next_step_info.get('title', ''),
            next_step_info.get('description', ''),
            history_text,
            self.language
        )
        self.current_step_id = next_step_id
        self.attempts_on_current_step = 0
        return get_llm_response(prompt=prompt, model=self.INTERVIEWER_MODEL, system_prompt=prompts.SYSTEM_PROMPT[self.language], use_classification_client=self.USE_CLASSIFICATION_CLIENT)

    def _provide_guidance(self):
        current_step_info = self.steps[self.current_step_id]
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])

        no_criteria_msg = {
            "it": "Nessun criterio specifico.",
            "en": "No specific criteria."
        }
        skills_str = ", ".join([s.get('skill_name', '') for s in current_step_info.get('skills_to_test', [])])

        prompt = prompts.create_guidance_prompt(
            current_step_info.get('title', ''),
            current_step_info.get('criteria', no_criteria_msg.get(self.language, no_criteria_msg["it"])),
            skills_str,
            history_text,
            self.language
        )
        return get_llm_response(prompt=prompt, model=self.INTERVIEWER_MODEL, system_prompt=prompts.SYSTEM_PROMPT[self.language], use_classification_client=self.USE_CLASSIFICATION_CLIENT, temperature=0.7)