"""
Language detection utility for automatic language identification from text.
Supports Italian and English detection for the recruitment process.
"""

def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    
    Args:
        text: The text to analyze (e.g., job description)
        
    Returns:
        "it" for Italian, "en" for English. Defaults to "it" if detection fails.
    """
    if not text or not text.strip():
        print("  - [Language Detector] Empty text provided, defaulting to Italian")
        return "it"
    
    try:
        # Lazy import to avoid dependency issues if not installed
        from langdetect import detect, LangDetectException
        
        detected_lang = detect(text)
        
        # Map detected language to supported languages
        if detected_lang == "en":
            print(f"  - [Language Detector] Detected language: English")
            return "en"
        elif detected_lang == "it":
            print(f"  - [Language Detector] Detected language: Italian")
            return "it"
        else:
            print(f"  - [Language Detector] Detected '{detected_lang}', defaulting to Italian")
            return "it"
            
    except ImportError:
        print("  - [Language Detector] WARNING: langdetect library not installed, defaulting to Italian")
        print("  - Install with: pip install langdetect")
        return "it"
    except LangDetectException as e:
        print(f"  - [Language Detector] Detection failed: {e}, defaulting to Italian")
        return "it"
    except Exception as e:
        print(f"  - [Language Detector] Unexpected error: {e}, defaulting to Italian")
        return "it"


def validate_language(language: str) -> str:
    """
    Validate and normalize a language code.
    
    Args:
        language: Language code to validate
        
    Returns:
        Validated language code ("it" or "en"). Defaults to "it" if invalid.
    """
    if language and language.lower() in ["en", "english"]:
        return "en"
    elif language and language.lower() in ["it", "italian", "italiano"]:
        return "it"
    else:
        print(f"  - [Language Detector] Invalid language '{language}', defaulting to Italian")
        return "it"

