# analyzer/icp_generator/icp_creator.py
import json
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from interviewer.llm_service import AZURE_DEPLOYMENT_NAME
from interviewer.llm_service import get_llm_response, get_structured_llm_response
from . import prompts_icp

ICP_MODEL = AZURE_DEPLOYMENT_NAME

def _slugify(text: str) -> str:
    """Crea uno slug da un testo per usarlo come skill_id."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-_/]", "", text)
    text = re.sub(r"[\s/_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")

# ----- Modelli Pydantic per strutturare l'ICP -----

class TechnicalSkill(BaseModel):
    """Skill tecnica richiesta esplicitamente dall'annuncio."""
    name: str = Field(description="Nome della skill tecnica (es. 'Python', 'Salesforce', 'Machine Learning')")
    description: Optional[str] = Field(default=None, description="Descrizione opzionale della skill se necessario per chiarezza")

class SoftSkill(BaseModel):
    """Skill trasversale richiesta esplicitamente dall'annuncio (escluse le lingue)."""
    name: str = Field(description="Nome della skill trasversale (es. 'Problem Solving', 'Teamwork', 'Leadership')")
    description: Optional[str] = Field(default=None, description="Descrizione opzionale della skill se necessario per chiarezza")

class Activity(BaseModel):
    """Attività o responsabilità operativa attesa per il ruolo (NON un requisito)."""
    description: str = Field(description="Descrizione dell'attività o responsabilità")

class IdealCandidateProfile(BaseModel):
    """Profilo del candidato ideale strutturato con requisiti e attività separate."""
    technical_skills: List[TechnicalSkill] = Field(
        default_factory=list,
        description="Lista delle competenze tecniche richieste esplicitamente dall'annuncio"
    )
    soft_skills: List[SoftSkill] = Field(
        default_factory=list,
        description="Lista delle competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)"
    )
    activities: List[Activity] = Field(
        default_factory=list,
        description="Lista delle responsabilità principali e attività operative attese (NON requisiti)"
    )

def _icp_to_formatted_text(icp: IdealCandidateProfile, language: str = "it") -> str:
    """
    Converte la struttura ICP in testo formattato per retrocompatibilità con moduli downstream.
    """
    lines = []
    
    if language == "it":
        lines.append("Ideal Candidate Profile")
        lines.append("")
        
        if icp.technical_skills:
            lines.append("Competenze tecniche richieste esplicitamente dall'annuncio")
            for skill in icp.technical_skills:
                if skill.description:
                    lines.append(f"o {skill.name}: {skill.description}")
                else:
                    lines.append(f"o {skill.name}")
            lines.append("")
        
        if icp.soft_skills:
            lines.append("Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)")
            for skill in icp.soft_skills:
                if skill.description:
                    lines.append(f"o {skill.name}: {skill.description}")
                else:
                    lines.append(f"o {skill.name}")
            lines.append("")
        
        if icp.activities:
            lines.append("Responsabilità principali e attività operative attese")
            for activity in icp.activities:
                lines.append(f"o {activity.description}")
            lines.append("")
    else:  # en
        lines.append("Ideal Candidate Profile")
        lines.append("")
        
        if icp.technical_skills:
            lines.append("Technical skills explicitly required by the posting")
            for skill in icp.technical_skills:
                if skill.description:
                    lines.append(f"o {skill.name}: {skill.description}")
                else:
                    lines.append(f"o {skill.name}")
            lines.append("")
        
        if icp.soft_skills:
            lines.append("Soft skills explicitly required by the posting (excluding languages)")
            for skill in icp.soft_skills:
                if skill.description:
                    lines.append(f"o {skill.name}: {skill.description}")
                else:
                    lines.append(f"o {skill.name}")
            lines.append("")
        
        if icp.activities:
            lines.append("Main responsibilities and expected operational activities")
            for activity in icp.activities:
                lines.append(f"o {activity.description}")
            lines.append("")
    
    return "\n".join(lines)

def extract_canonical_skills_from_icp(icp: IdealCandidateProfile) -> List[dict]:
    """
    Estrae la lista canonica delle skills dall'ICP strutturato.
    Questa è la UNICA fonte di verità per le skills in tutto il processo.
    
    Args:
        icp: Oggetto IdealCandidateProfile validato
        
    Returns:
        Lista di dizionari con struttura:
        [{"skill_id": "...", "skill_name": "...", "skill_type": "technical|soft"}]
    """
    canonical_skills = []
    
    # Estrai technical skills
    for skill in icp.technical_skills:
        skill_name = skill.name.strip()
        if not skill_name:
            continue
        skill_id = _slugify(skill_name)
        if not skill_id:
            continue
        canonical_skills.append({
            "skill_id": skill_id,
            "skill_name": skill_name,
            "skill_type": "technical"
        })
    
    # Estrai soft skills
    for skill in icp.soft_skills:
        skill_name = skill.name.strip()
        if not skill_name:
            continue
        skill_id = _slugify(skill_name)
        if not skill_id:
            continue
        canonical_skills.append({
            "skill_id": skill_id,
            "skill_name": skill_name,
            "skill_type": "soft"
        })
    
    print(f"  - [Canonical Skills] Estratte {len(canonical_skills)} skills: "
          f"{sum(1 for s in canonical_skills if s['skill_type'] == 'technical')} tecniche, "
          f"{sum(1 for s in canonical_skills if s['skill_type'] == 'soft')} trasversali")
    
    return canonical_skills

def generate_and_extract_icp(job_description_text: str, hr_special_needs: str = "", language: str = "it") -> Tuple[str | None, IdealCandidateProfile | None]:
    """
    Genera l'ICP dalla JD e lo estrae. Integra le Indicazioni Speciali HR.
    Ora usa output strutturato JSON con validazione Pydantic.
    
    Returns:
        Tupla (icp_text, icp_structured):
        - icp_text: Testo formattato per retrocompatibilità
        - icp_structured: Oggetto IdealCandidateProfile strutturato (None se errore)
    """
    print("  - [Agente ICP] Creazione del prompt...")
    icp_prompt = prompts_icp.create_icp_generation_prompt(job_description_text, hr_special_needs, language)

    print(f"  - [Agente ICP] Invio della richiesta al modello '{ICP_MODEL}' con output strutturato...")
    
    # Ottieni lo schema JSON per la tool call
    output_schema = IdealCandidateProfile.model_json_schema()
    
    structured_response_str = get_structured_llm_response(
        prompt=icp_prompt,
        model=ICP_MODEL,
        system_prompt=prompts_icp.SYSTEM_PROMPT[language],
        tool_name="save_icp",
        tool_schema=output_schema,
        temperature=0.4,
        max_tokens=2500
    )

    if not structured_response_str:
        print("  - [Agente ICP] Errore: nessuna risposta strutturata ricevuta dall'LLM.")
        return None, None

    try:
        print("  - [Agente ICP] Validazione della struttura ICP con Pydantic...")
        parsed_json = json.loads(structured_response_str)
        validated_icp = IdealCandidateProfile.model_validate(parsed_json)
        
        print(f"  - [Agente ICP] Validazione completata: {len(validated_icp.technical_skills)} skill tecniche, "
              f"{len(validated_icp.soft_skills)} skill trasversali, {len(validated_icp.activities)} attività")
        
        # Converti in testo formattato per retrocompatibilità
        formatted_text = _icp_to_formatted_text(validated_icp, language)
        
        print("  - [Agente ICP] Estrazione completata.")
        return formatted_text, validated_icp
        
    except json.JSONDecodeError as e:
        print(f"  - [Agente ICP] Errore nel parsing JSON: {e}")
        return None, None
    except Exception as e:
        print(f"  - [Agente ICP] Errore durante la validazione Pydantic: {e}")
        return None, None