---
name: search_norma
description: Guida step by step per ricercare con il giusto ragionamento informazioni in ambito fiscale italiano. Usa questa skill quando c'è da cercare informazioni di natura fiscale italiana. Include strategia di web search su fonti ufficiali.
---

# Metodo di ricerca e ragionamento dell’Agenzia delle Entrate nelle risposte a interpello

## Guida step by step per replicare il processo anche in altri casi

### Obiettivo: costruire una skill in Claude che ragioni in modo simile all’Agenzia

---

## 1. Scopo del metodo

Quando l’Agenzia delle Entrate risponde a un interpello, non ragiona come un consulente che prova a esplorare tutte le possibili strategie.
Ragiona invece come un sistema **normativo, gerarchico e deterministico**.

Questo significa che:

- parte dalla **norma**
- individua il **concetto fiscale rilevante**
- collega il caso concreto alla **categoria giuridico-tributaria corretta**
- esclude tutto ciò che è una **mera questione di fatto**
- arriva a una conclusione il più possibile **vincolata al testo normativo e alla prassi**

L’obiettivo di questa guida è trasformare questo metodo in un processo replicabile da una persona non specializzata e, soprattutto, in una logica implementabile in una **skill di Claude**.

---

## 1.1 Strumenti di ricerca disponibili

Per eseguire il metodo, la skill utilizza **web search** per reperire fonti normative e di prassi aggiornate. La ricerca web è uno strumento operativo integrato in più step del processo.

### Fonti web autorizzate (LISTA ESCLUSIVA)

**IMPORTANTE: la skill deve cercare ESCLUSIVAMENTE sui seguenti domini. Non è consentito utilizzare blog, studi professionali, forum o qualsiasi altro sito non presente in questa lista.**

Ogni chiamata a **WebSearch** DEVE includere il parametro `allowed_domains` con i soli domini pertinenti alla ricerca. Non effettuare mai ricerche senza questo filtro.

#### Fonti normative e di prassi (priorità massima)

1. **normattiva.it** — testo vigente di leggi, decreti, TUIR, codici
2. **agenziaentrate.gov.it** — circolari, risoluzioni, risposte a interpello, provvedimenti
3. **def.finanze.it** (Documentazione Economica e Finanziaria) — relazioni illustrative e tecniche
4. **gazzettaufficiale.it** — testo originale di leggi e decreti
5. **fiscooggi.it** (rivista telematica dell’Agenzia) — commenti e approfondimenti ufficiali
6. **giustizia-tributaria.it** — giurisprudenza tributaria di merito e legittimità

#### Fonti contabili

7. **fondazioneoic.eu** — principi contabili nazionali OIC (consultare in particolare: https://www.fondazioneoic.eu/principi-contabili-category/2024/)
8. Per i principi contabili internazionali **IAS/IFRS**, consultare la guida presente nelle risorse locali della skill (vedi sezione "Risorse locali" sotto)

#### Fonti di approfondimento fiscale

9. **ipsoa.it** — notizie e approfondimenti fiscali di carattere generale

### Risorse locali della skill

La cartella `resources/` della skill contiene documenti di riferimento da consultare quando necessario:

- **`resources/2007-04-23_Guida.pdf`** — Guida ai principi contabili internazionali IAS/IFRS. Consultare con il tool `Read` quando il caso richiede l’applicazione o il richiamo di principi contabili internazionali.

Prima di cercare sul web informazioni su OIC o IAS/IFRS, verifica se la risposta è già disponibile nelle risorse locali.

### Regole per la web search

- **SOLO FONTI AUTORIZZATE** — ogni WebSearch DEVE usare `allowed_domains` limitato ai domini della lista sopra. Non è mai consentito cercare su siti non elencati. Se un risultato di ricerca punta a un sito non autorizzato, ignorarlo e non usare WebFetch su di esso.
- **Cerca sempre in italiano** — le query devono essere formulate in lingua italiana
- **Usa termini normativi precisi** — es. "art. 88 TUIR sopravvenienze attive", non "tassazione risarcimenti"
- **Verifica la vigenza** — controlla sempre che la norma trovata sia vigente e non abrogata
- **Cerca per estremi** — quando conosci anno/numero della norma o della circolare, cerca direttamente per estremi (es. "circolare 4/E 2023 agenzia entrate")
- **Massimo 3-5 ricerche per step** — non fare ricerche esplorative eccessive; ogni ricerca deve avere un obiettivo preciso
- **Leggi sempre la pagina trovata** — dopo la ricerca, usa WebFetch per leggere il contenuto effettivo della fonte prima di trarne conclusioni
- **Mai citare fonti non autorizzate** — nella risposta finale, le Sources devono contenere esclusivamente URL dai domini autorizzati

---

# 2. Principio generale del metodo

La logica dell’Agenzia può essere riassunta così:

> **Non si parte dal caso per cercare una soluzione.
> Si parte dalla norma per capire in quale categoria normativa rientra il caso.**

Questa differenza è fondamentale.

### Approccio consulenziale

- parte dal problema pratico
- ipotizza scenari alternativi
- valuta margini di ottimizzazione
- apre possibilità

### Approccio Agenzia delle Entrate

- parte dalla disposizione normativa
- definisce la regola
- classifica il fatto dentro la regola
- chiude la conclusione

---

# 3. Struttura generale del ragionamento

Il processo può essere diviso in **7 step**.

---

## STEP 1 — Identificare il quesito esatto

### Obiettivo

Capire **qual è la domanda fiscale precisa** a cui bisogna rispondere.

### Perché è importante

L’Agenzia risponde solo al quesito formulato.
Non amplia spontaneamente il perimetro.

### Cosa fare

Bisogna riscrivere la domanda in forma chiara e sintetica.

### Domande da porsi

- Il contribuente chiede **se una norma si applica**?
- Chiede **come si calcola una base imponibile**?
- Chiede **quando imputare fiscalmente un componente**?
- Chiede **come qualificare un componente reddituale**?

### Esempio

Nel caso del contributo di solidarietà:

**Quesito reale:**
Il ristoro ricevuto nel 2022 rileva ai fini della base imponibile del contributo di solidarietà 2023?

### Output dello step

Una frase breve:

> “Bisogna stabilire se il componente positivo ricevuto nel 2022 concorre alla base imponibile del contributo di solidarietà temporaneo.”

---

## STEP 2 — Individuare la norma primaria che governa il caso

### Obiettivo

Trovare la **fonte normativa principale** da cui parte il ragionamento.

### Perché è importante

L’Agenzia non parte dai principi generali astratti, ma dalla norma che disciplina direttamente il tributo o l’istituto.

### Cosa fare

Individuare:

1. la norma che istituisce il tributo o disciplina il beneficio
2. i commi/articoli che definiscono:
   - soggetti passivi
   - base imponibile
   - criterio di calcolo
   - eventuali esclusioni

### Come cercare con web search

1. **Se conosci già gli estremi della norma** → cerca direttamente:
   - Query: `"legge 197/2022 art 1 commi 115-121"`
   - `allowed_domains`: `["normattiva.it", "gazzettaufficiale.it"]`
2. **Se NON conosci la norma** → parti dal tema fiscale:
   - Query: `"contributo di solidarietà temporaneo" normativa 2022 2023`
   - `allowed_domains`: `["normattiva.it", "agenziaentrate.gov.it", "gazzettaufficiale.it"]`
3. **Dopo aver trovato la norma** → usa WebFetch per leggere il testo integrale dell'articolo/comma
4. **Verifica vigenza** → controlla che la norma non sia stata abrogata o modificata

### Esempio

Nel caso esaminato:

- **art. 1, commi 115–121, legge 197/2022**

Questa è la norma primaria.

### Output dello step

Una scheda del tipo:

- **Norma primaria:** art. 1, commi 115–121, legge 197/2022
- **Tema:** contributo di solidarietà temporaneo
- **Punto chiave da estrarre:** come si determina la base imponibile
- **Fonte verificata:** [URL normattiva.it o Gazzetta Ufficiale]

---

## STEP 3 — Estrarre la regola normativa “madre”

### Obiettivo

Capire **quale formula normativa governa la risposta**.

### Perché è importante

La risposta ufficiale ruota quasi sempre intorno a una regola base.
Una volta trovata quella regola, il resto del ragionamento è solo applicazione.

### Cosa fare

Leggere la norma primaria e tradurla in una regola semplice.

### Come usare la web search

Se nello Step 2 non hai ancora letto il testo integrale della norma:

1. Usa WebFetch sull'URL di normattiva.it trovato nello Step 2
2. Estrai i commi rilevanti
3. Se il testo è troppo lungo o poco chiaro, cerca anche la **relazione illustrativa**:
   - Query: `"relazione illustrativa" "[nome legge o decreto]" site:def.finanze.it OR site:camera.it`

### Esempio

Dal comma 116 emerge questa regola:

> Il contributo si applica sulla quota del reddito complessivo IRES del periodo precedente che eccede del 10% la media dei quattro periodi precedenti.

Tradotto in modo operativo:

- guardo il reddito imponibile 2022
- lo confronto con la media dei redditi imponibili 2018–2021
- applico l’aliquota sulla parte eccedente

### Output dello step

Una formula o regola in linguaggio semplice:

> “La base imponibile del contributo dipende dal reddito imponibile IRES dei cinque periodi considerati.”

---

## STEP 4 — Cercare la prassi che spiega come leggere quella norma

### Obiettivo

Verificare se esistono **circolari, risposte, relazioni illustrative o tecniche** che chiariscono come interpretare la norma primaria.

### Perché è importante

L’Agenzia usa spesso la propria prassi per:

- confermare il significato della norma
- precisare il metodo di calcolo
- indicare il dato dichiarativo da usare
- chiudere dubbi interpretativi

### Cosa fare

Recuperare:

- circolari
- risposte a interpello precedenti
- relazioni illustrative
- relazioni tecniche

### Come cercare la prassi con web search

Questo è lo step dove la web search è **più critica**. Segui questa sequenza, usando SEMPRE `allowed_domains` per limitare ai soli siti autorizzati:

#### A. Cercare circolari dell'Agenzia delle Entrate

- Query: `circolare [numero]/E [anno] [tema]`
- `allowed_domains`: `["agenziaentrate.gov.it"]`

#### B. Cercare risposte a interpello

- Query: `risposta interpello [numero] [anno] [tema]`
- `allowed_domains`: `["agenziaentrate.gov.it"]`

#### C. Cercare risoluzioni

- Query: `risoluzione [tema] agenzia entrate`
- `allowed_domains`: `["agenziaentrate.gov.it"]`

#### D. Cercare relazioni illustrative/tecniche

- Query: `"relazione illustrativa" "[legge/decreto]"`
- `allowed_domains`: `["def.finanze.it"]`

#### E. Ricerca di approfondimento su FiscoOggi o IPSOA

- Query: `"[tema fiscale]"`
- `allowed_domains`: `["fiscooggi.it"]` per prassi ufficiale, oppure `["ipsoa.it"]` per approfondimenti generali

#### F. Leggere il contenuto trovato

- Dopo ogni ricerca, usa **WebFetch** per leggere il testo della circolare/risposta trovata
- Non basarti solo sugli snippet dei risultati di ricerca: leggi la fonte
- **Verifica che l'URL appartenga a un dominio autorizzato** prima di usare WebFetch

#### G. Se la RAG interna ha già trovato prassi

- Confronta i risultati della web search con quelli della RAG per verificare coerenza
- La web search può trovare prassi più recente non ancora indicizzata nella RAG

#### H. Principi contabili (se necessari)

- **OIC nazionali**: `allowed_domains`: `["fondazioneoic.eu"]` — consultare https://www.fondazioneoic.eu/principi-contabili-category/2024/
- **IAS/IFRS internazionali**: consultare prima la guida locale in `resources/2007-04-23_Guida.pdf` con il tool Read, poi eventualmente cercare su fonti autorizzate

### Esempio

Nel caso specifico:

- **circolare 4/E del 23 febbraio 2023**

La circolare chiarisce che rileva:

- il reddito determinato ai fini IRES
- facendo riferimento al **rigo RF63**
- al lordo di perdite pregresse e ACE

### Output dello step

Una frase che collega norma e prassi:

> “La base imponibile è ancorata al reddito imponibile IRES risultante dal quadro RF, rigo RF63, con gli aggiustamenti indicati dalla circolare.”

---

## STEP 5 — Collegare il caso concreto alle categorie del TUIR

### Obiettivo

Capire **in quale categoria fiscale rientra il fatto concreto**.

### Perché è importante

L’Agenzia non si chiede genericamente “che cos’è economicamente questo importo?”.Si chiede invece:

> “In quale categoria del TUIR cade questo componente?”

### Cosa fare

Prendere il fatto concreto e cercare:

- se è un ricavo
- se è una sopravvenienza attiva
- se è una plusvalenza
- se è un risarcimento sostitutivo di reddito
- se è un costo deducibile
- se è una sopravvenienza passiva
- ecc.

### Domanda guida

> “Questo elemento, secondo il TUIR, dove si colloca?”

### Come usare la web search per il TUIR

1. **Cercare l'articolo TUIR rilevante**:
   - Query: `”art. [numero] TUIR” “[parola chiave]”`
   - `allowed_domains`: `[“normattiva.it”]`
   - Es.: `”art. 88 TUIR” “sopravvenienze attive”`
2. **Leggere il testo vigente** con WebFetch su normattiva.it
3. **Se il collegamento non è ovvio**, cercare prassi di classificazione:
   - Query: `”[tipo componente]” “TUIR” qualificazione fiscale`
   - `allowed_domains`: `[“agenziaentrate.gov.it”, “fiscooggi.it”]`

### Esempio

Nel caso del ristoro:

- il pagamento ha natura di **risarcimento**
- bisogna verificare se è **sostitutivo di reddito**
- l’art. 6 TUIR dice che i proventi sostitutivi di reddito seguono il regime del reddito sostituito
- il componente può quindi concorrere alla formazione del reddito imponibile
- l’Agenzia lo ricollega anche alle regole sulle **sopravvenienze attive** ex art. 88 TUIR

### Output dello step

Una classificazione precisa:

> “Il ristoro è trattato come componente positivo fiscalmente rilevante, riconducibile al reddito imponibile IRES secondo le regole del TUIR.”

---

## STEP 6 — Verificare se la questione è interpretativa o di fatto

### Obiettivo

Capire se l’Agenzia può rispondere davvero al punto sollevato oppure se si tratta di una questione che considera inammissibile.

### Perché è importante

Questo è uno degli aspetti più importanti da replicare in una skill.

L’Agenzia distingue tra:

### A. Questioni interpretative

Sono ammissibili.
Esempi:

- una norma si applica o no?
- un componente rientra o no nella base imponibile?
- quale disposizione regola il caso?

### B. Questioni di fatto

Spesso non sono ammissibili.
Esempi:

- in quale anno andava contabilizzato?
- quale fosse la corretta imputazione temporale concreta
- se la scrittura contabile adottata sia giusta
- quale sia la reale natura economica, se dipende da elementi fattuali da verificare

### Cosa fare

Per ogni dubbio, chiedersi:

- sto interpretando una norma?
- oppure sto valutando fatti, contabilità, documenti, tempi di imputazione?

### Esempio

Nel caso esaminato:

**Quesito ammissibile:**
Il risarcimento concorre alla base imponibile del contributo?

**Quesito non ammissibile:**
Il componente andava imputato al 2018 o al 2022?

L’Agenzia dice:

- sul primo punto risponde
- sul secondo no, perché è una valutazione di fatto contabile/fiscale

### Output dello step

Una classificazione binaria:

- **questione interpretativa:** sì
- **questione di fatto:** sì/no
- **se di fatto:** limitare o bloccare la risposta

---

## STEP 7 — Applicare la regola in modo automatico e concludere

### Obiettivo

Chiudere il ragionamento in modo lineare, senza aprire scenari inutili.

### Perché è importante

La risposta dell’Agenzia non lascia normalmente spazio a molte ipotesi alternative.
Una volta individuata la regola, la applica in modo quasi meccanico.

### Metodo

La conclusione segue questo schema:

1. la norma dice come si forma la base imponibile
2. la prassi chiarisce che conta il reddito imponibile IRES
3. il componente in esame è fiscalmente rilevante secondo il TUIR
4. quindi entra nella base imponibile

### Esempio sintetico

- La base imponibile del contributo è costruita sul reddito imponibile IRES
- Il risarcimento sostitutivo di reddito concorre al reddito imponibile IRES
- Quindi concorre alla base imponibile del contributo

### Output dello step

Una conclusione breve, chiusa e normativa:

> “Poiché il componente concorre alla formazione del reddito imponibile IRES secondo il TUIR, esso rileva anche ai fini della base imponibile del contributo di solidarietà.”

---

# 4. Schema riutilizzabile per altri casi

Di seguito uno schema generale da usare ogni volta.

---

## Template operativo generale

### Step 1 — Definisci il quesito

Scrivi in una frase:

- cosa bisogna stabilire
- rispetto a quale norma
- su quale componente o operazione

### Step 2 — Trova la norma primaria

Individua:

- legge
- articolo/commi
- parte che contiene la regola

### Step 3 — Estrai la regola fondamentale

Traduci la norma in una formula semplice:

- cosa entra
- cosa esce
- come si calcola
- quale elemento conta davvero

### Step 4 — Cerca la prassi interpretativa

Verifica:

- circolari
- interpelli precedenti
- relazioni illustrative/tecniche

### Step 5 — Classifica fiscalmente il fatto

Chiediti:

- questo importo/operazione nel TUIR cos’è?
- ricavo?
- sopravvenienza?
- plusvalenza?
- costo?
- indennizzo?
- elemento escluso?

### Step 6 — Separa interpretazione da fatto

Chiediti:

- sto interpretando una norma?
- oppure sto accertando una circostanza concreta?

Se è un fatto:

- segnala il limite
- non trasformarlo in affermazione normativa certa

### Step 7 — Concludi con deduzione lineare

Scrivi:

- premessa normativa
- classificazione fiscale
- conseguenza finale

---

# 5. Regole pratiche per non sbagliare

## Regola 1 — Non partire dal buon senso economico

L’Agenzia non decide sulla base di ciò che “sembra giusto” economicamente.Decide in base a:

- norma
- prassi
- classificazione fiscale

## Regola 2 — Non aprire scenari se la norma è già chiara

Se una norma e una circolare chiudono il punto, non bisogna costruire alternative teoriche.

## Regola 3 — Non confondere imputazione contabile e interpretazione normativa

Molti errori nascono qui.

Domanda da fare sempre:

> “Sto discutendo il significato di una norma o la correttezza di una registrazione contabile?”

## Regola 4 — La categoria TUIR è il ponte tra fatto e conclusione

Il passaggio decisivo è quasi sempre:

- prendere il fatto
- trovare la sua categoria nel TUIR
- applicare la conseguenza

## Regola 5 — La conclusione deve essere corta e obbligata

Se hai fatto bene i passaggi precedenti, la conclusione finale dovrebbe essere quasi inevitabile.

---

# 6. Come trasformare questo metodo in una skill di Claude

## Obiettivo della skill

Far sì che Claude:

- non risponda in modo troppo libero o consulenziale
- segua un ragionamento simile a quello dell’Agenzia
- distingua tra norma, prassi e fatto
- produca risposte ordinate, replicabili e prudenti

---

## Struttura logica della skill

### Fase A — Comprensione del quesito

La skill deve identificare:

- il tributo o istituto fiscale
- il dubbio preciso
- il componente o operazione rilevante

### Fase B — Ricerca gerarchica delle fonti (con web search — SOLO domini autorizzati)

Ordine suggerito — per ciascuna fonte, usa **WebSearch** (con `allowed_domains`) per cercare e **WebFetch** per leggere:

1. **norma primaria** → `allowed_domains`: `["normattiva.it", "gazzettaufficiale.it"]` → WebFetch del testo
2. **prassi ufficiale** → `allowed_domains`: `["agenziaentrate.gov.it"]` → WebFetch del documento
3. **TUIR / norme sistematiche collegate** → `allowed_domains`: `["normattiva.it"]` → WebFetch
4. **precedenti di interpello** → `allowed_domains`: `["agenziaentrate.gov.it"]` → WebFetch
5. **relazioni illustrative/tecniche** → `allowed_domains`: `["def.finanze.it"]` → WebFetch
6. **approfondimenti ufficiali** → `allowed_domains`: `["fiscooggi.it"]` → WebFetch
7. **notizie fiscali generali** → `allowed_domains`: `["ipsoa.it"]` → WebFetch
8. **principi contabili nazionali OIC**, solo se necessari → `allowed_domains`: `["fondazioneoic.eu"]`
9. **principi contabili internazionali IAS/IFRS**, solo se necessari → consultare prima `resources/2007-04-23_Guida.pdf` con il tool Read
10. **giurisprudenza tributaria** → `allowed_domains`: `["giustizia-tributaria.it"]` → WebFetch

### Fase C — Classificazione del tema

La skill deve classificare il problema come:

- interpretazione normativa
- qualificazione fiscale
- questione di fatto
- tema contabile
- tema probatorio

### Fase D — Mapping normativo

La skill deve collegare il fatto a una categoria del TUIR.

Esempio:

- risarcimento → art. 6 TUIR
- componente positivo → art. 88 TUIR
- reddito imponibile → artt. 83 e seguenti TUIR

### Fase E — Decisione finale

La skill deve produrre una conclusione basata su questa regola:

> se il componente concorre al reddito imponibile secondo il TUIR, e la base imponibile del tributo è ancorata a quel reddito, allora il componente rileva anche per quel tributo.

### Fase F — Gestione dei limiti

Se emerge una questione di fatto:

- la skill deve segnalarlo espressamente
- evitare conclusioni assolute
- distinguere il profilo interpretativo da quello fattuale

---

# 7. Prompt framework per la skill

Di seguito una possibile struttura di prompt logico.

## Istruzioni di comportamento della skill

La skill deve ragionare nel seguente ordine:

1. individuare il quesito preciso
2. individuare la norma primaria rilevante
3. estrarre la regola normativa sulla base imponibile o sul trattamento fiscale
4. cercare eventuale prassi ufficiale che chiarisca la norma
5. classificare il componente o il fatto secondo il TUIR o altre norme fiscali rilevanti
6. distinguere tra profili interpretativi e questioni di fatto
7. concludere solo sul profilo interpretativo
8. segnalare separatamente eventuali aspetti non decidibili perché fattuali o contabili

---

## Formato di output consigliato per la skill

### 1. Quesito

Descrizione sintetica del dubbio fiscale.

### 2. Norma primaria

Articoli/commi rilevanti.

### 3. Regola normativa

Sintesi della regola applicabile.

### 4. Prassi rilevante

Circolari, interpelli o documenti di supporto.

### 5. Qualificazione fiscale del caso

Inquadramento del componente secondo il TUIR.

### 6. Distinzione tra norma e fatto

Indicazione di ciò che è interpretabile e ciò che è solo accertabile in fatto.

### 7. Conclusione

Risposta lineare e motivata.

---

# 8. Mini esempio applicato al caso del contributo di solidarietà

## 1. Quesito

Stabilire se il ristoro percepito nel 2022 concorra alla base imponibile del contributo di solidarietà temporaneo 2023.

## 2. Norma primaria

Art. 1, commi 115–121, legge 197/2022.

## 3. Regola normativa

La base imponibile del contributo è costruita sul reddito imponibile IRES del 2022 confrontato con la media dei quattro periodi precedenti.

## 4. Prassi rilevante

Circolare 4/E del 2023: rileva il reddito imponibile IRES, con riferimento al quadro RF.

## 5. Qualificazione fiscale del caso

Il risarcimento sostitutivo di reddito concorre al reddito imponibile ai sensi del TUIR; il componente può rilevare come sopravvenienza attiva.

## 6. Distinzione tra norma e fatto

- interpretazione ammissibile: se il componente imponibile rilevi nel contributo
- questione di fatto: in quale esercizio andasse imputato concretamente

## 7. Conclusione

Se il ristoro concorre al reddito imponibile IRES del periodo considerato, allora concorre anche alla base imponibile del contributo di solidarietà.

---

# 9. Formula finale da ricordare

## Regola sintetica replicabile

> **Norma primaria → prassi → classificazione TUIR → filtro tra interpretazione e fatto → conclusione automatica**

Con web search integrata (SOLO domini autorizzati, sempre con `allowed_domains`):

> **WebSearch norma (`["normattiva.it", "gazzettaufficiale.it"]`) → WebFetch testo → WebSearch prassi (`["agenziaentrate.gov.it"]`) → WebFetch circolare/interpello → WebSearch TUIR (`["normattiva.it"]`) → classificazione → conclusione**

Se servono principi contabili: **OIC** su `["fondazioneoic.eu"]`, **IAS/IFRS** da `resources/2007-04-23_Guida.pdf`.
Per approfondimenti: **FiscoOggi** su `["fiscooggi.it"]`, **IPSOA** su `["ipsoa.it"]`.

Oppure, in forma ancora più semplice:

> **Prima trovi la regola (cercando e leggendo la norma online su siti ufficiali).
> Poi trovi la categoria fiscale del fatto (cercando e leggendo il TUIR).
> Infine applichi la regola solo a ciò che è giuridicamente interpretabile.
> Mai usare fonti non autorizzate.**

---

# 10. Conclusione operativa

Per replicare il modo in cui ragiona l’Agenzia delle Entrate, una skill in Claude non deve:

- inventare scenari
- ragionare in modo troppo libero
- trasformare dubbi contabili in conclusioni normative

Deve invece:

- seguire un percorso gerarchico
- partire dalla norma
- usare la prassi come guida
- qualificare fiscalmente il fatto
- distinguere con rigore tra interpretazione e accertamento del fatto

Questo è il modo migliore per costruire una skill robusta, affidabile e coerente con la logica delle risposte ufficiali.

---
