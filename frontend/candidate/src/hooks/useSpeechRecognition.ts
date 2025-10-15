import { useState, useEffect, useRef } from 'react'

export function useSpeechRecognition(language: string = 'it-IT') {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [isSupported, setIsSupported] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    // Check if browser supports speech recognition
    const SpeechRecognition = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition
    
    if (SpeechRecognition) {
      setIsSupported(true)
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true
      recognitionRef.current.interimResults = true
      recognitionRef.current.lang = language
      recognitionRef.current.maxAlternatives = 1

      recognitionRef.current.onresult = (event: any) => {
        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptPiece = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcriptPiece + ' '
          } else {
            interimTranscript += transcriptPiece
          }
        }

        // Update transcript with final results
        if (finalTranscript) {
          setTranscript(prev => prev + finalTranscript)
        }
      }

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        setError(`Errore riconoscimento vocale: ${event.error}`)
        setIsListening(false)
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current.onstart = () => {
        setError(null)
      }
    } else {
      setIsSupported(false)
      setError('Il tuo browser non supporta il riconoscimento vocale')
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [language])

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      try {
        setTranscript('')
        setError(null)
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        console.error('Failed to start speech recognition:', err)
        setError('Impossibile avviare il riconoscimento vocale')
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop()
        setIsListening(false)
      } catch (err) {
        console.error('Failed to stop speech recognition:', err)
      }
    }
  }

  const resetTranscript = () => {
    setTranscript('')
    setError(null)
  }

  return {
    isListening,
    transcript,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript
  }
}
