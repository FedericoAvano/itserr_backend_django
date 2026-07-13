 <img width="1425" height="593" alt="Digital ITSERRLogo Color No Background v  01 00" src="https://github.com/user-attachments/assets/c81c1fab-41d0-45bd-80c0-386d678ef941" />

# 3D V.I.S.O.R. 🏛️💻
### Virtual Interface for Scientific Object Reconstruction
*Sviluppato dalla **Dott.ssa Laura Carpentiero** nell'ambito dell'Infrastruttura di Ricerca **ITSERR** (Italian Strengthening of the ESFRI RI RESILIENCE)*

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Backend](https://img.shields.io/badge/Backend-Django%20%2F%20DRF-092E20?logo=django)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2F%20Three.js-61DAFB?logo=react)
![Real-Time](https://img.shields.io/badge/Real--Time-WebSockets%20%2F%20Channels-purple)
![FAIR](https://img.shields.io/badge/Data%20Principles-FAIR-blue)

**3D V.I.S.O.R.** è un'infrastruttura digitale avanzata progettata per centralizzare, arricchire, analizzare e visualizzare modelli 3D e dati testuali provenienti da contesti archeologici eterogenei. Il sistema supera il concetto di database statico, configurandosi come un vero e proprio laboratorio interattivo multi-device orientato alla collaborazione scientifica internazionale.

---

## 📌 Indice
1. [Architettura e Workflow di Sistema](#1-architettura-e-workflow-di-sistema)
2. [Ingestione Dati e Proxy Layer](#2-ingestione-dati-e-proxy-layer)
3. [Pipeline Asset 3D (Bulk Upload)](#3-pipeline-asset-3d-bulk-upload)
4. [Risoluzione Criticità Tecniche](#4-risoluzione-criticità-tecniche)
5. [Stack Tecnologico](#5-stack-tecnologico)
6. [Sistema di Annotazione Semantica](#6-sistema-di-annotazione-semantica)
7. [Fruizione Multi-Device & UI/UX](#7-fruizione-multi-device--uiux)
8. [Autore e Crediti](#8-autore-e-crediti)

---

## 1. Architettura e Workflow di Sistema

Il sistema si basa su un paradigma di **disaccoppiamento funzionale netto** tra Backend e Frontend, garantendo scalabilità e la piena aderenza ai **Principi FAIR** (*Findable, Accessible, Interoperable, Reusable*):

* **Django (Backend):** Agisce come *Single Source of Truth* (Sorgente Unica di Verità). Preserva l'integrità del dato scientifico, gestisce la sicurezza e centralizza le informazioni.
* **React (Frontend):** Funge da Single Page Application (SPA) e laboratorio interattivo lato client. Sfrutta la GPU dell'utente per il rendering grafico distribuito, riducendo al minimo il carico computazionale sul server e garantendo una navigazione fluida.

---

## 2. Ingestione Dati e Proxy Layer

Il backend in Django funge da **Proxy Layer intelligente** e regista del flusso informativo:
* **Interrogazione Live:** Non duplica massivamente i record, ma interroga in tempo reale i repository catalografici esterni (es. schede R.A.).
* **Normalizzazione Semantica:** Tramite i *Serializers* di Django REST Framework (DRF), trasforma dati grezzi ed eterogenei in oggetti JSON standardizzati ed interoperabili.
* **Arricchimento On-the-Fly:** Inietta dinamicamente all'interno del flusso dati i percorsi delle repliche 3D e le annotazioni memorizzate localmente.

---

## 3. Pipeline Asset 3D (Bulk Upload)

Il sistema supporta la gestione di modelli tridimensionali compositi (Geometria `.obj`, Materiali `.mtl`, Texture `.jpg`/`.png`) attraverso due modalità di upload:

* **Caricamento Puntuale:** Controllo granulare e manuale tramite pannello amministrativo per reperti ad alta complessità.
* **Caricamento Massivo (Bulk Upload):** Ingestione di archivi compressi `.zip` strutturati secondo una gerarchia definita:

```text
archivio.zip
└── modelli_3d/
    ├── REPERTO_COD001/
    │   ├── modello.obj
    │   ├── modello.mtl
    │   └── texture.jpg
    └── REPERTO_COD002/
        └── ...
```

## 4. Logica di Matching Automatico

Il backend esegue il parsing del pacchetto, normalizza il nome della cartella in uno slug univoco e lo utilizza come chiave di aggancio. Se lo slug coincide con il codice identificativo ufficiale del reperto (es. `MO1138`), il sistema mappa automaticamente e senza ambiguità l'asset 3D alle relazioni $1:1$ della scheda scientifica nel database.

---

## 5. Risoluzione Criticità Tecniche

* **Sanitizzazione dei file MTL:** All'upload, un algoritmo lato server analizza i file `.mtl` e riscrive dinamicamente i percorsi assoluti locali dei modellatori (es. `C:\Users\...`) convertendoli in path relativi puntanti al *Media Server* di Django.
* **Lazy Loading delle Mesh:** Ottimizzazione dei tempi di rendering in React tramite `Suspense`. I metadati testuali vengono mostrati istantaneamente, mentre il motore grafico *Three.js* carica progressivamente in background l'asset pesante, evitando il blocco del browser.
* **Coerenza Spaziale delle Annotazioni:** Per preservare la precisione scientifica, le coordinate dei punti di interesse vengono salvate in vettori spaziali relativi $(x, y, z)$ agganciati alla geometria nativa della mesh, rimanendo invariate in caso di scaling o rotazione nel viewport.

---

## 6. Stack Tecnologico

| Componente | Tecnologia Utilizzata | Ruolo / Funzionalità |
| :--- | :--- | :--- |
| **Backend Core** | Django & Django REST Framework | Logica di business, persistenza ORM, esibizione di API REST JSON conformi W3C. |
| **Real-time Engine** | Django Channels | Abilitazione del protocollo asincrono bi-direzionale **WebSockets**. |
| **Message Broker** | Redis | In-memory database ad alta velocità per il coordinamento dei messaggi live tra client. |
| **Frontend Core** | React | Architettura SPA, gestione reattiva dello stato dei componenti e dell'interfaccia utente. |
| **3D Rendering** | React Three Fiber (R3F) & Three.js | Bridge per l'integrazione e la manipolazione interattiva di oggetti 3D nel ciclo di vita di React. |
| **3D Utilities** | React Three Drei | Gestione dei controlli di camera (`OrbitControls`) e degli indicatori visivi di caricamento. |
| **Post-Processing** | N8AO, Bloom & ToneMapping | Algoritmi grafici per l'ottimizzazione delle ombre di contatto (lettura di crepe/iscrizioni) e calibrazione fotometrica dei materiali. |
| **Media & Security** | Pillow & Django-cors-headers | Elaborazione delle texture lato server e gestione delle policy cross-origin. |

---

## 7. Sistema di Annotazione Semantica

3D V.I.S.O.R. trasforma la mesh 3D da elemento visivo passivo a spazio di ricerca attiva e stratificata:

* **Annotazione Puntuale:** Sfrutta algoritmi di **Raycasting** in *Three.js* per intercettare l'intersezione millimetrica tra cursore e mesh, ancorando un "pin" spaziale stabile.
* **Annotazione Areale:** Consente di tracciare una *Selection Mask* per perimetrare fenomeni estesi (aree di degrado, decorazioni, intere porzioni testuali iscritte) con feedback visivo di chiusura forma.
* **Analisi Strutturata del Testo:** Un motore di elaborazione lato backend analizza le note discorsive in linguaggio naturale inserite dagli studiosi, estraendo e categorizzando i dati semantici secondo l'ontologia archeologica di progetto.
* **Collaborazione Live:** Grazie all'integrazione *Channels + Redis*, qualsiasi annotazione salvata viene notificata istantaneamente tramite WebSocket a tutti gli utenti connessi sulla stessa mesh, abilitando sessioni di co-working internazionali in tempo reale. Il formato di salvataggio rispetta lo standard **W3C Web Annotation**.

---

## 8. Fruizione Multi-Device & UI/UX

L'interfaccia utente è interamente reattiva (*Responsive Design*) e ottimizzata per l'uso in mobilità e direttamente sul campo archeologico:
* **Layout Adattivo:** Implementato tramite griglie flessibili di *Material UI (MUI)*. I pannelli descrittivi e i form di input si riposizionano automaticamente sui dispositivi mobile per lasciare libero il viewport del modello 3D.
* **Touch Interaction Native:** I controlli della telecamera virtuale intercettano i gesti touch del dispositivo (rotazione, *pinch-to-zoom*, panning).
* **Asset Scaling:** In contesti di bassa connettività (es. durante ricognizioni in situ), il frontend richiede al backend versioni alleggerite e scalate delle texture, preservando la memoria RAM del tablet/smartphone e riducendo il consumo di banda.

---

## 9. Autore e Crediti

Il prototipo, la progettazione concettuale e l'intera infrastruttura software di 3D V.I.S.O.R. sono stati interamente ideati, progettati e sviluppati dalla **Dott.ssa Laura Carpentiero**.

---

### 🇪🇺 Finanziamento e Attribution
> Sviluppato nell'ambito delle attività del WP 10-Retina.
> **"Finanziato dall’Unione europea - Next Generation EU, Missione 4 Componente 2 CUP B53C22001770006".**
