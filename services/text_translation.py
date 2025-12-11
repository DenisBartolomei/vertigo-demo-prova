"""Utility per tradurre testi usando il servizio LLM interno."""

from typing import Literal

from interviewer.llm_service import (
    AZURE_DEPLOYMENT_NAME,
    get_llm_response,
    get_llm_response_async,
)

TRANSLATION_SYSTEM_PROMPT = (
    "You are an expert bilingual translator. Translate the provided text into "
    "standard Italian suitable for professional job descriptions. Preserve any "
    "technical terms, code snippets, numbers, and formatting. Respond with the "
    "translated text only."
)


def _build_translation_prompt(text: str) -> str:
    return (
        "Translate the following job description into Italian. "
        "If the text already appears to be Italian, simply return it unchanged.\n\n"
        "Text:\n"
        "```text\n"
        f"{text}\n"
        "```"
    )


def translate_to_italian(text: str, source_language: Literal["it", "en", "auto"] = "auto") -> str:
    """
    Traduci sincronicamente il testo in italiano. Restituisce il testo originale in caso di errori.
    """
    if not text or not text.strip():
        return text

    if source_language == "it":
        return text

    prompt = _build_translation_prompt(text)
    response = get_llm_response(
        prompt=prompt,
        model=AZURE_DEPLOYMENT_NAME,
        system_prompt=TRANSLATION_SYSTEM_PROMPT,
        temperature=0,
    )

    if not response or response.startswith("Errore"):
        return text

    return response.strip()


async def translate_to_italian_async(
    text: str,
    source_language: Literal["it", "en", "auto"] = "auto",
) -> str:
    """
    Traduci asincronicamente il testo in italiano. Restituisce il testo originale in caso di errori.
    """
    if not text or not text.strip():
        return text

    if source_language == "it":
        return text

    prompt = _build_translation_prompt(text)
    response = await get_llm_response_async(
        prompt=prompt,
        model=AZURE_DEPLOYMENT_NAME,
        system_prompt=TRANSLATION_SYSTEM_PROMPT,
        temperature=0,
    )

    if not response or response.startswith("Errore"):
        return text

    return response.strip()










