# Guida alla Configurazione delle Interviste

## Panoramica

Il sistema di configurazione delle interviste permette agli HR di personalizzare la durata e la complessità dei colloqui attraverso due parametri principali:

- **Reasoning Steps**: Numero di passaggi logici nell'intervista
- **Max Attempts**: Numero massimo di tentativi per ogni step

## Come Funziona

### Reasoning Steps
I **Reasoning Steps** sono i passaggi logici che l'agente AI intervistatore segue per guidare il candidato attraverso la risoluzione del case study. Ogni step:

- Testa competenze specifiche richieste dalla posizione
- Guida il candidato verso la soluzione del problema
- Valuta le risposte in base a criteri predefiniti
- Permette al candidato di fare domande per chiarimenti

**Range**: 2-10 steps
**Default**: 4 steps

### Max Attempts
I **Max Attempts** rappresentano il numero massimo di tentativi che l'agente intervistatore concede al candidato per completare ogni reasoning step. Se il candidato non riesce entro i tentativi massimi:

- L'agente passa al prossimo reasoning step
- Il candidato può ancora continuare l'intervista
- La valutazione finale terrà conto dei tentativi falliti

**Range**: 2-15 tentativi
**Default**: 5 tentativi

## Calcolo della Durata

La durata stimata dell'intervista viene calcolata automaticamente:

```
Durata (minuti) = (Reasoning Steps × Max Attempts × 1.5) + 5
```

Dove:
- **1.5 minuti** è il tempo stimato per ogni tentativo
- **5 minuti** sono riservati per setup e conclusioni

### Esempi di Durata

| Reasoning Steps | Max Attempts | Durata Stimata |
|----------------|--------------|----------------|
| 2 | 3 | 14 minuti |
| 4 | 5 | 35 minuti |
| 6 | 7 | 68 minuti |
| 8 | 10 | 125 minuti |

## Calcolo delle Domande Massime

Il numero massimo di domande che il candidato può fare viene calcolato come:

```
Max Questions = (Reasoning Steps × 2) + 3
```

Dove:
- **2 domande** per ogni reasoning step
- **3 domande** base per setup e chiarimenti

### Esempi di Domande

| Reasoning Steps | Domande Massime |
|----------------|----------------|
| 2 | 7 domande |
| 4 | 11 domande |
| 6 | 15 domande |
| 8 | 19 domande |

## Configurazione per Tenant

Ogni azienda (tenant) può avere la propria configurazione personalizzata:

- Le configurazioni sono salvate su MongoDB
- Ogni tenant ha la sua configurazione indipendente
- I valori di default vengono creati automaticamente per nuovi tenant
- Le modifiche si applicano immediatamente a tutte le nuove posizioni create

## Come Configurare

1. **Accedi al Dashboard HR**
2. **Vai alla sezione "Posizioni"**
3. **Clicca su "Configura Interviste"**
4. **Regola i parametri** usando gli slider
5. **Salva la configurazione**

## Impatto sulla Generazione dei Case

Quando HR configura i parametri:

1. **Nuove posizioni** useranno automaticamente la configurazione corrente
2. **Case study esistenti** non vengono modificati
3. **Il sistema genera** il numero corretto di reasoning steps
4. **L'agente intervistatore** segue i limiti configurati

## Best Practices

### Per Interviste Brevi (15-30 minuti)
- Reasoning Steps: 2-3
- Max Attempts: 3-4
- Ideale per: screening iniziali, posizioni junior

### Per Interviste Standard (30-60 minuti)
- Reasoning Steps: 4-5
- Max Attempts: 5-6
- Ideale per: posizioni mid-level, valutazioni approfondite

### Per Interviste Lunghe (60+ minuti)
- Reasoning Steps: 6-8
- Max Attempts: 7-10
- Ideale per: posizioni senior, ruoli critici

## Note Tecniche

- Il sistema aggiunge automaticamente uno **step 0** per testare le capacità di impostazione del ragionamento
- I reasoning steps sono numerati da 1 a N (dove N è il numero configurato)
- Lo step 0 viene sempre generato automaticamente dal prompt
- I parametri vengono applicati durante la generazione dei case study, non durante l'intervista

## Troubleshooting

### La configurazione non si salva
- Verifica che l'utente abbia i permessi HR
- Controlla la connessione al backend
- Verifica che i valori siano nel range consentito

### Le nuove posizioni non usano la configurazione
- Assicurati che la configurazione sia stata salvata
- Le posizioni esistenti non vengono aggiornate automaticamente
- Crea una nuova posizione per testare la configurazione

### Durata stimata non corretta
- La durata è solo una stima basata su 1.5 minuti per tentativo
- I candidati possono completare l'intervista più velocemente o più lentamente
- La durata reale dipende dal comportamento del candidato
