import re
import uuid
from typing import Optional

def extract_email_from_text(cv_text: str) -> str:
    """
    Estrae l'indirizzo email dal testo del CV usando regex.
    
    Args:
        cv_text: Testo estratto dal CV
        
    Returns:
        Email trovata o placeholder se non trovata
    """
    if not cv_text or not isinstance(cv_text, str):
        return f"pending-{uuid.uuid4().hex[:8]}@batch.local"
    
    # Pattern regex per email valide
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    
    # Cerca tutte le email nel testo
    emails = re.findall(email_pattern, cv_text)
    
    if emails:
        # Prendi la prima email trovata
        email = emails[0].lower().strip()
        
        # Validazione aggiuntiva: escludi email generiche o sospette
        generic_patterns = [
            r'example\.com$',
            r'test\.com$',
            r'placeholder',
            r'your-email',
            r'email@domain',
            r'user@company'
        ]
        
        for pattern in generic_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                return f"pending-{uuid.uuid4().hex[:8]}@batch.local"
        
        return email
    else:
        # Nessuna email trovata, genera placeholder
        return f"pending-{uuid.uuid4().hex[:8]}@batch.local"

def is_placeholder_email(email: str) -> bool:
    """
    Verifica se un'email è un placeholder generato automaticamente.
    
    Args:
        email: Indirizzo email da verificare
        
    Returns:
        True se è un placeholder, False altrimenti
    """
    return email.endswith('@batch.local') and email.startswith('pending-')

