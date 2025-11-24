"""
WhatsApp client for Meta Cloud API integration
"""
import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class WhatsAppClient:
    """Client per interagire con Meta WhatsApp Cloud API"""
    
    def __init__(self):
        self.api_token = os.getenv("WHATSAPP_API_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v19.0")
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        
        if not self.api_token or not self.phone_number_id:
            raise ValueError("WHATSAPP_API_TOKEN e WHATSAPP_PHONE_NUMBER_ID devono essere configurati")
    
    def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "it",
        components: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Invia un Template Message (a pagamento, primo messaggio)
        
        Args:
            to: Numero destinatario in formato internazionale (es. 393331234567)
            template_name: Nome del template approvato da Meta
            language_code: Codice lingua (default: it)
            components: Componenti opzionali per parametri del template
        
        Returns:
            Dict con response da Meta API
        """
        url = f"{self.base_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Errore invio template message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
    
    def send_text_message(
        self,
        to: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Invia un Text Message (gratuito entro 24h dalla risposta utente)
        
        Args:
            to: Numero destinatario in formato internazionale
            text: Testo del messaggio
        
        Returns:
            Dict con response da Meta API (include message_id)
        """
        url = f"{self.base_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": text
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Errore invio text message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """
        Marca un messaggio come letto (opzionale, migliora UX)
        """
        url = f"{self.base_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Errore mark as read: {e}")
            return False
    
    def validate_credentials(self) -> bool:
        """
        Valida che le credenziali siano corrette facendo una chiamata di test
        """
        try:
            # Prova a recuperare info sul numero di telefono
            url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
            headers = {
                "Authorization": f"Bearer {self.api_token}"
            }
            response = requests.get(url, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Errore validazione credenziali: {e}")
            return False

