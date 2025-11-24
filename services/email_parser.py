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

def extract_phone_from_text(cv_text: str) -> Optional[str]:
    """
    Estrae il numero di telefono dal testo del CV usando regex.
    Supporta formati italiani e internazionali.
    
    Args:
        cv_text: Testo estratto dal CV
        
    Returns:
        Numero di telefono trovato (formato internazionale senza +) o None
    """
    if not cv_text or not isinstance(cv_text, str):
        return None
    
    # Pattern per numeri italiani (cellulari e fissi)
    # Formati supportati:
    # - 3331234567 (10 cifre)
    # - +39 333 123 4567
    # - 333-123-4567
    # - 333.123.4567
    # - (333) 123-4567
    # - 06 12345678 (fisso)
    
    # Pattern principale: cerca sequenze di 9-10 cifre (italiani)
    # o numeri con prefisso internazionale
    phone_patterns = [
        r'\+39\s*[0-9]{9,10}',  # +39 seguito da 9-10 cifre
        r'\+39\s*[0-9]{2,3}\s*[0-9]{6,7}',  # +39 con spazi
        r'0[0-9]{9,10}',  # Numero che inizia con 0 (fisso italiano)
        r'3[0-9]{9}',  # Cellulare italiano (inizia con 3)
        r'[0-9]{3}[\s\.\-]?[0-9]{3}[\s\.\-]?[0-9]{4}',  # Formato con separatori
        r'\(0[0-9]{1,2}\)\s*[0-9]{6,8}',  # Formato (06) 12345678
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, cv_text)
        if matches:
            # Prendi il primo match e normalizza
            phone = matches[0].strip()
            
            # Rimuovi spazi, punti, trattini, parentesi
            phone = re.sub(r'[\s\.\-\(\)]', '', phone)
            
            # Se inizia con +39, rimuovilo (lo aggiungeremo dopo se necessario)
            if phone.startswith('+39'):
                phone = phone[3:]
            elif phone.startswith('39'):
                phone = phone[2:]
            
            # Se inizia con 0 (fisso italiano), rimuovilo
            if phone.startswith('0'):
                phone = phone[1:]
            
            # Valida che sia un numero valido (9-10 cifre per italiani)
            if len(phone) >= 9 and len(phone) <= 10 and phone.isdigit():
                # Normalizza a formato internazionale (senza +)
                if not phone.startswith('39'):
                    phone = '39' + phone
                return phone
    
    return None


def is_placeholder_email(email: str) -> bool:
    """
    Verifica se un'email è un placeholder generato automaticamente.
    
    Args:
        email: Indirizzo email da verificare
        
    Returns:
        True se è un placeholder, False altrimenti
    """
    return email.endswith('@batch.local') and email.startswith('pending-')

