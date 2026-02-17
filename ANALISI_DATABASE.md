# Analisi Database Daze - Stazioni di Ricarica EV

**Database:** PostgreSQL 14.19 (dump da AWS)
**Schema:** `dazeapi`
**Dimensione dump:** ~20 MB | ~186.000 righe totali
**Data analisi:** 2026-02-17

---

## 1. Panoramica

Il database modella l'infrastruttura di ricarica per veicoli elettrici di **Daze**. Si compone di **15 tabelle** organizzate attorno a tre entita' principali:

| Entita' | Descrizione | Righe |
|---------|-------------|-------|
| **Users** | Utenti registrati nella piattaforma | 20.174 |
| **Networks** | Siti/location di ricarica con configurazione rete elettrica | 23.813 |
| **EVSEs** | Singole unita' di ricarica (colonnine) | 16.530 |

---

## 2. Schema Completo - Tutte le Tabelle

### 2.1 `configs` (1 riga)
Configurazione globale dell'applicazione.

| Colonna | Tipo | Note |
|---------|------|------|
| id | integer | PK |
| name | varchar | NOT NULL |
| value | jsonb | NOT NULL |

### 2.2 `users` (20.174 righe)
Utenti registrati. Autenticazione gestita via **AWS Cognito**.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| email | varchar | NOT NULL, UNIQUE, indicizzato |
| cognito_id | text | NOT NULL - link ad AWS Cognito |
| name | text | nullable |
| surname | text | nullable |
| address | text | nullable |
| cap | text | nullable |
| city | text | nullable |
| province | text | nullable |
| phone | text | nullable |
| language | text | nullable |
| country | text | nullable |
| user_type | integer | NOT NULL - tipo utente (codice numerico) |
| vat_number | text | nullable - P.IVA |
| is_debuggable | boolean | NOT NULL |
| super_admin | boolean | NOT NULL |
| cancellation_requested | boolean | NOT NULL |
| created_on | timestamptz | NOT NULL |
| updated_on | timestamptz | NOT NULL |

### 2.3 `networks` (23.813 righe)
Siti di ricarica. La tabella piu' ricca con 32 colonne: configurazione rete elettrica, fotovoltaico, accumulo, pricing, tariffe smart.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK |
| name | text | NOT NULL |
| address | text | NOT NULL |
| city | text | NOT NULL |
| zip_code | text | NOT NULL |
| country | text | NOT NULL |
| network_type | integer | NOT NULL - tipo rete |
| grid_is_three_phase | boolean | NOT NULL - rete trifase |
| supply_max_power | integer | NOT NULL - potenza max fornitura |
| chargers_max_power | integer | NOT NULL - potenza max caricatori |
| is_photovoltaic | boolean | NOT NULL - ha fotovoltaico |
| is_photovoltaic_three_phase | boolean | NOT NULL |
| is_accumulation | boolean | NOT NULL - ha accumulo energia |
| accumulation_max_power | integer | nullable |
| arera | boolean | NOT NULL - regolamentazione ARERA |
| is_deleted | boolean | NOT NULL - soft delete |
| slave_number | integer | NOT NULL |
| energy_cost_mul_by_thousand | integer | nullable - costo energia (x1000) |
| smart_tariff_enabled | boolean | NOT NULL |
| eco_mode_enabled | boolean | NOT NULL |
| network_recharge_modality | integer | NOT NULL |
| timezone | text | NOT NULL |
| self_consumption_enabled_out_of_time_slot | boolean | NOT NULL |
| ems_configuration | integer | NOT NULL - config Energy Management System |
| three_phase_auto_switch_enabled | boolean | NOT NULL |
| currency | varchar(3) | NOT NULL |
| integration_partner_id | integer | nullable, FK -> integration_partners |
| created_on | timestamptz | NOT NULL |
| updated_on | timestamptz | NOT NULL |
| price_activation_mul_by_thousand | integer | nullable - prezzo attivazione (x1000) |
| price_energy_mul_by_thousand | integer | nullable - prezzo energia (x1000) |
| price_minute_charging_mul_by_thousand | integer | nullable - prezzo al minuto ricarica (x1000) |
| price_minute_post_charging_mul_by_thousand | integer | nullable - prezzo al minuto post-ricarica (x1000) |

### 2.4 `evses` (16.530 righe)
Electric Vehicle Supply Equipment - le singole unita' di ricarica.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| serial_number | varchar(11) | NOT NULL, UNIQUE, indicizzato |

### 2.5 `network_evses` (15.215 righe)
Associazione N:M tra network e caricatori.

| Colonna | Tipo | Note |
|---------|------|------|
| network_id | uuid | PK (composita), FK -> networks |
| evse_id | uuid | PK (composita), FK -> evses |

### 2.6 `user_networks` (22.794 righe)
Associazione utenti-network con ruolo.

| Colonna | Tipo | Note |
|---------|------|------|
| user_id | uuid | PK (composita), FK -> users |
| network_id | uuid | PK (composita), FK -> networks |
| role | integer | NOT NULL - ruolo utente nella rete |

### 2.7 `user_evses` (24.905 righe)
Associazione utenti-caricatori (ownership).

| Colonna | Tipo | Note |
|---------|------|------|
| user_id | uuid | PK (composita), FK -> users |
| evse_id | uuid | PK (composita), FK -> evses |

### 2.8 `rfids` (6.519 righe)
Tessere/tag RFID per autenticazione alla colonnina.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| serial_number | varchar | NOT NULL, UNIQUE |
| name | varchar | nullable |
| associated_to_user | uuid | nullable, FK -> users |
| updated_on | timestamptz | nullable |
| created_on | timestamptz | NOT NULL |

### 2.9 `rfid_in_networks` (6.251 righe)
Autorizzazioni RFID per network specifiche.

| Colonna | Tipo | Note |
|---------|------|------|
| rfid_id | uuid | PK (composita), FK -> rfids |
| network_id | uuid | PK (composita), FK -> networks |

### 2.10 `rfid_whitelists` (5.920 righe)
Whitelist RFID versionate per singola EVSE.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| version | integer | NOT NULL |
| is_sent | boolean | DEFAULT false, NOT NULL |
| is_obsolete | boolean | DEFAULT false, NOT NULL |
| evse_id | uuid | NOT NULL, FK -> evses |
| created_on | timestamptz | NOT NULL |

### 2.11 `rfid_in_whitelists` (36.205 righe)
Membership RFID nelle whitelist. La tabella junction piu' grande.

| Colonna | Tipo | Note |
|---------|------|------|
| rfid_id | uuid | PK (composita), FK -> rfids |
| rfid_whitelist_id | uuid | PK (composita), FK -> rfid_whitelists |

### 2.12 `eco_schedules` (7.258 righe)
Programmazione fasce orarie eco-mode per network.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| day | integer | NOT NULL - giorno della settimana (0-6) |
| start | time | NOT NULL |
| "end" | time | NOT NULL |
| network_id | uuid | NOT NULL, FK -> networks |

### 2.13 `vehicles` (5 righe)
Veicoli elettrici registrati (funzionalita' in fase iniziale).

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| name | text | NOT NULL |
| kwh | numeric | NOT NULL - capacita' batteria |
| user_id | uuid | NOT NULL, FK -> users |

### 2.14 `vehicle_charge_settings` (28 righe)
Programmazione ricarica per veicolo.

| Colonna | Tipo | Note |
|---------|------|------|
| id | uuid | PK, auto-generato |
| day | integer | NOT NULL |
| "time" | time | NOT NULL |
| percentage | integer | NOT NULL |
| vehicle_id | uuid | NOT NULL, FK -> vehicles |

### 2.15 `integration_partners` (2 righe)
Partner esterni integrati.

| Colonna | Tipo | Note |
|---------|------|------|
| id | integer | PK, GENERATED ALWAYS AS IDENTITY |
| name | text | NOT NULL |
| app_client_id | text | NOT NULL, UNIQUE |

---

## 3. Diagramma Relazioni (ER)

```
users (20.174)
  |
  |-- M:N --> evses (16.530)              via user_evses (24.905)
  |-- M:N --> networks (23.813)           via user_networks (22.794) [con role]
  |-- 1:N --> vehicles (5)
  |             \-- 1:N --> vehicle_charge_settings (28)
  |-- 1:N --> rfids (6.519)               via rfids.associated_to_user

networks (23.813)
  |
  |-- M:N --> evses                        via network_evses (15.215)
  |-- 1:N --> eco_schedules (7.258)
  |-- N:1 --> integration_partners (2)
  |-- M:N --> rfids                        via rfid_in_networks (6.251)

evses (16.530)
  |
  \-- 1:N --> rfid_whitelists (5.920)
                \-- M:N --> rfids          via rfid_in_whitelists (36.205)

configs (1) -- configurazione globale standalone
```

---

## 4. Volumi Dati

| Tabella | Righe | % del totale |
|---------|-------|-------------|
| rfid_in_whitelists | 36.205 | 19.5% |
| user_evses | 24.905 | 13.4% |
| networks | 23.813 | 12.8% |
| user_networks | 22.794 | 12.3% |
| users | 20.174 | 10.9% |
| evses | 16.530 | 8.9% |
| network_evses | 15.215 | 8.2% |
| eco_schedules | 7.258 | 3.9% |
| rfids | 6.519 | 3.5% |
| rfid_in_networks | 6.251 | 3.4% |
| rfid_whitelists | 5.920 | 3.2% |
| integration_partners | 2 | <0.1% |
| configs | 1 | <0.1% |
| vehicle_charge_settings | 28 | <0.1% |
| vehicles | 5 | <0.1% |
| **TOTALE** | **~185.620** | **100%** |

---

## 5. Osservazioni Chiave per la BI

### 5.1 Punti di forza del dataset
- **Base utenti significativa:** 20.174 utenti con dati anagrafici e geolocalizzazione
- **Rete infrastrutturale ampia:** 23.813 network / 16.530 EVSE
- **Dati di pricing presenti:** 4 dimensioni di prezzo sulle network (attivazione, energia, minuto ricarica, minuto post-ricarica)
- **Dati geografici:** indirizzo, citta', CAP, paese su networks e users
- **Configurazione tecnica ricca:** fotovoltaico, trifase, accumulo, EMS, smart tariff
- **Timestamp di creazione/aggiornamento** su entita' principali

### 5.2 Limitazioni importanti

> **ATTENZIONE: Non ci sono dati transazionali di ricarica nel dump.**

Il database contiene solo dati **anagrafici e di configurazione**. **Mancano completamente**:
- **Sessioni di ricarica** (transazioni, kWh erogati, durata, costi)
- **Dati di consumo energetico** in tempo reale o storico
- **Fatturazione e pagamenti**
- **Log di stato delle EVSE** (online/offline/guasto)
- **Metriche di utilizzo** (frequenza d'uso, orari di punta)

Questo limita significativamente le analisi BI possibili. **Per una BI completa servirebbero i dati delle sessioni di ricarica.**

### 5.3 Analisi BI realizzabili con i dati attuali

Nonostante le limitazioni, si possono costruire diversi report utili:

#### A. Analisi Infrastruttura
- Distribuzione geografica delle network (mappa per citta'/CAP/paese)
- Mix tecnologico: % reti trifase vs monofase
- Penetrazione fotovoltaico e accumulo
- Distribuzione potenza massima fornitura e caricatori
- Rapporto EVSE per network (densita' colonnine per sito)

#### B. Analisi Utenti
- Crescita utenti nel tempo (via `created_on`)
- Distribuzione geografica utenti
- Rapporto utenti per network / per EVSE
- Segmentazione per `user_type`
- Tasso di cancellazione (`cancellation_requested`)
- Analisi ruoli (`user_networks.role`)

#### C. Analisi Pricing
- Distribuzione prezzi per tipo (attivazione, energia, minuto, post-ricarica)
- Reti con pricing configurato vs non configurato
- Analisi costo energia per area geografica
- Confronto modalita' di ricarica (`network_recharge_modality`)

#### D. Analisi RFID
- Copertura RFID: utenti con RFID vs senza
- Distribuzione RFID per network
- Analisi whitelist: versioning e aggiornamenti

#### E. Analisi Smart Features
- Adozione smart tariff per network
- Adozione eco-mode e schedulazione
- Configurazione EMS
- Trifase auto-switch

### 5.4 Codici numerici da decodificare

I seguenti campi usano codici interi invece di enum. Sara' necessario ottenere la mappatura:

| Campo | Tabella | Valori probabili |
|-------|---------|-------------------|
| `network_type` | networks | Tipo di installazione (residenziale, commerciale, pubblico?) |
| `network_recharge_modality` | networks | Modalita' ricarica (libera, a pagamento, RFID?) |
| `ems_configuration` | networks | Configurazione Energy Management System |
| `role` | user_networks | Ruolo utente nella rete (admin, operatore, utente?) |
| `user_type` | users | Tipo utente (privato, business, installer?) |
| `day` | eco_schedules | Giorno settimana (0=lunedi' o 0=domenica?) |

---

## 6. Raccomandazioni per il Progetto BI

### Priorita' 1 - Dati mancanti critici
1. **Richiedere il dump delle sessioni di ricarica** - Questo e' il dato piu' importante per la BI
2. **Ottenere la mappatura dei codici numerici** (network_type, user_type, role, ecc.)
3. **Verificare se esistono tabelle di billing/fatturazione** non incluse nel dump

### Priorita' 2 - Dashboard realizzabili subito
1. Dashboard distribuzione geografica infrastruttura
2. Dashboard crescita utenti e infrastruttura nel tempo
3. Dashboard configurazione pricing
4. Dashboard mix tecnologico (fotovoltaico, trifase, accumulo)

### Priorita' 3 - Architettura BI suggerita
- **ETL:** Script Python/dbt per trasformare i dati dal PostgreSQL
- **Data Warehouse:** PostgreSQL dedicato o servizio managed (es. Redshift, BigQuery)
- **Dashboard:** Metabase (open source) o Superset per visualizzazione
- **Aggiornamento:** Pipeline periodica dal DB produzione
