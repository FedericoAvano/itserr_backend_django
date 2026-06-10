import spacy
from spacy.matcher import Matcher
from typing import List

# --- Setup del modello NLP ---
try:
    NLP = spacy.load("it_core_news_sm")
except OSError:
    print("ERRORE CRITICO: Modello SpaCy 'it_core_news_sm' non trovato. Assicurati che sia installato.")
    NLP = None


# --- Liste di parole chiave per l'analisi contestuale ---
RITROVAMENTO_VERBI = ["ritrovato", "scoperto", "proveniente", "trovato",
                      "ritrovamento", "provenienza", "rinvenuto", "reperto"]
CUSTODIA_VERBI = ["custodito", "conservato", "esposto", "museo", "galleria",
                  "custodia", "conservazione"]
PRODUZIONE_NOMI = ["produzione", "manifattura", "fabbricazione", "origine",
                   "creazione"]
ENTITA_DA_ESCLUDERE = ["GPE", "LOC", "ORG", "PER", "MISC", "FAC"] 
LUOGHI_GENERICI = ["sito", "zona", "località", "città", "paese", "archeologico"] 

def analizza_testo_annotazione(testo: str) -> dict:
    """
    Esegue l'analisi NLP usando testo con maiuscole per migliorare il NER.
    Implementa forzatura sequenziale per i luoghi di scavo problematici.
    """
    if not NLP:
        return {"errore": "Modello NLP non caricato correttamente."}

    # CRITICO: Usa il testo originale per migliorare il Named Entity Recognition (NER)
    doc = NLP(testo)
    
    risultati = {
        "evento_produzione_luogo": None,
        "evento_scavo_luogo": None,
        "evento_custodia_luogo": None,
        "oggetto_rilevato_tipologia": [],
    }

    matcher = Matcher(NLP.vocab)
    
    # 1. Pattern per Luogo di Produzione (usa LOWER per trovare le parole chiave)
    produzione_pattern = [
        {"LOWER": {"IN": PRODUZIONE_NOMI}},
        {"POS": {"IN": ["ADP", "DET"]}, "OP": "?"},
        {"POS": "ADJ"}
    ]
    matcher.add("PRODUZIONE", [produzione_pattern])
    
    entita_token_testo = set()
    entita_luogo_mappa = {}
    
    # 2. Pre-processing Entità: Mappatura completa per i nomi composti
    for ent in doc.ents:
        if ent.label_ in ENTITA_DA_ESCLUDERE:
            luogo_completo = ent.text.strip()
            for token in ent:
                entita_luogo_mappa[token.i] = luogo_completo 
                entita_token_testo.add(token.text)
                 
    
    # 3. Estrazione Luoghi (Logica Drastica: Priorità assoluta a NER, poi Forzatura Sequenziale)
    for token in doc:
        if token.lemma_ in RITROVAMENTO_VERBI + CUSTODIA_VERBI:
            
            luogo_candidato = None
            
            # --- Check 1 (NER AGGRESSIVO): Cerca l'entità di luogo/organizzazione più vicina ---
            best_ent_dist = 999
            best_ent_text = None
            
            for ent in doc.ents:
                if ent.start >= token.i and ent.label_ in ["GPE", "LOC", "ORG"]:
                    distance = ent.start - token.i 
                    
                    if distance < 8 and ent.text.lower() not in LUOGHI_GENERICI:
                        
                        if token.lemma_ in CUSTODIA_VERBI and ent.label_ == "ORG" and 'museo' in ent.text.lower():
                            luogo_candidato = entita_luogo_mappa.get(ent.start, ent.text.strip())
                            break 
                            
                        elif distance < best_ent_dist:
                            best_ent_dist = distance
                            best_ent_text = entita_luogo_mappa.get(ent.start, ent.text.strip())
            
            if luogo_candidato is None:
                luogo_candidato = best_ent_text

            # --- Check 2 (FORZATURA FINALE PER SCAVO): Cerca Nomi Propri/Luoghi in Prossimità Sequenziale ---
            # Questo ignora il parsing e il NER che falliscono e cerca un PROPN dopo il verbo
            if not luogo_candidato and token.lemma_ in RITROVAMENTO_VERBI:
                start_index = token.i + 1
                end_index = min(len(doc), token.i + 7)  # Aumentiamo la finestra a 7
                
                for i in range(start_index, end_index):
                    prossimo_token = doc[i]
                    
                    # Massima priorità: un nome proprio (PROPN) o un'entità luogo/ORG/GPE
                    if prossimo_token.pos_ == "PROPN" or prossimo_token.i in entita_luogo_mappa:
                         
                         candidato_raw = entita_luogo_mappa.get(prossimo_token.i, prossimo_token.text.strip())
                         
                         # Se non è generico, usalo
                         if candidato_raw.lower() not in LUOGHI_GENERICI:
                             luogo_candidato = candidato_raw
                             break
                    
                    # Fallback per Nomi Comuni non generici
                    elif prossimo_token.pos_ == "NOUN":
                         if prossimo_token.text.lower() not in LUOGHI_GENERICI and prossimo_token.text.lower() not in ["vaso"]:
                             luogo_candidato = prossimo_token.text.strip()
                             break


            # --- Assegnazione dei Risultati e Pulizia Speciale ---
            if luogo_candidato:
                if luogo_candidato.lower() in LUOGHI_GENERICI:
                    continue

                if luogo_candidato.lower().startswith("di "):
                    luogo_candidato = luogo_candidato[3:].strip()
                
                if luogo_candidato.lower() == "hong" or luogo_candidato.lower() == "kong":
                     luogo_candidato = "Hong Kong"

                luogo_candidato = luogo_candidato.capitalize()
                
                if token.lemma_ in RITROVAMENTO_VERBI and risultati["evento_scavo_luogo"] is None:
                    risultati["evento_scavo_luogo"] = luogo_candidato
                
                elif token.lemma_ in CUSTODIA_VERBI and risultati["evento_custodia_luogo"] is None:
                    risultati["evento_custodia_luogo"] = luogo_candidato


    # 4. Applicazione Matcher (Pattern Produzione)
    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        match_name = NLP.vocab.strings[match_id]
        if match_name == "PRODUZIONE":
            aggettivo_produzione = ""
            for token in span:
                if token.pos_ == "ADJ": 
                    aggettivo_produzione = token.text.capitalize()
                    break
            if aggettivo_produzione:
                risultati["evento_produzione_luogo"] = aggettivo_produzione

                
    # 5. Identificazione di Oggetti/Tipologia (Pulizia Aggressiva e Corretta)
    LUOGHI_DA_ESCLUDERE = {"pompei", "napoli", "kong"}
    all_keywords = {kw for sublist in [RITROVAMENTO_VERBI, CUSTODIA_VERBI, PRODUZIONE_NOMI] for kw in sublist}

    for token in doc:
        # Estraiamo SOLO i sostantivi comuni (NOUN)
        if token.pos_ == "NOUN" and len(token.text) > 3:
            
            if token.text.lower() not in all_keywords and token.text not in entita_token_testo and token.text.lower() not in LUOGHI_GENERICI:
                risultati["oggetto_rilevato_tipologia"].append(token.text.lower())
        
        # Filtro Esplicito per Nomi Propri di Luogo che contaminano la lista
        token_text_lower = token.text.lower() 
        if token.pos_ == "PROPN" and token_text_lower in LUOGHI_DA_ESCLUDERE:
            continue
        
    risultati["oggetto_rilevato_tipologia"] = list(set(risultati["oggetto_rilevato_tipologia"]))
    return risultati