"""
Utility per convertire JSON in formato TOON per input ai modelli LLM.
Gestisce fallback automatico a JSON originale in caso di errore.
"""

import json
from typing import Union

try:
    from py_toon_format import encode
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False
    print("⚠️ ATTENZIONE: py-toon-format non disponibile. Verrà usato JSON originale.")


def convert_json_to_toon(json_data: Union[dict, str]) -> str:
    """
    Converte dati JSON (dict o stringa) in formato TOON.
    
    Args:
        json_data: Dati da convertire. Può essere un dict Python o una stringa JSON.
    
    Returns:
        Stringa in formato TOON se la conversione riesce, altrimenti stringa JSON originale.
    
    Note:
        Se la libreria py-toon-format non è disponibile o la conversione fallisce,
        ritorna il JSON originale serializzato con logging sulla console.
    """
    if not TOON_AVAILABLE:
        # Se la libreria non è disponibile, serializza come JSON
        if isinstance(json_data, dict):
            return json.dumps(json_data, indent=2, ensure_ascii=False)
        return json_data if isinstance(json_data, str) else json.dumps(json_data, indent=2, ensure_ascii=False)
    
    try:
        # Se è una stringa JSON, parsala prima
        if isinstance(json_data, str):
            try:
                parsed_data = json.loads(json_data)
            except json.JSONDecodeError:
                # Se non è JSON valido, ritorna la stringa originale
                print(f"⚠️ [TOON Converter] Stringa non è JSON valido, ritorno originale")
                return json_data
        else:
            parsed_data = json_data
        
        # Converti a TOON
        toon_string = encode(parsed_data)
        return toon_string
        
    except Exception as e:
        # In caso di errore, logga e ritorna JSON originale
        print(f"⚠️ [TOON Converter] Errore durante conversione TOON: {e}")
        print(f"   Fallback a JSON originale")
        
        # Serializza come JSON
        if isinstance(json_data, dict):
            return json.dumps(json_data, indent=2, ensure_ascii=False)
        elif isinstance(json_data, str):
            # Verifica se è già JSON valido
            try:
                json.loads(json_data)
                return json_data
            except json.JSONDecodeError:
                return json.dumps(json_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(json_data, indent=2, ensure_ascii=False)




