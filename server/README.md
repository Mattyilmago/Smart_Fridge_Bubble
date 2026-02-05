# Smart Fridge Server

Server Flask per gestione autenticazione e comunicazione con frigoriferi intelligenti.

## Setup Rapido

### 1. Requisiti
- Python 3.8+
- MySQL database (già configurato su Aruba)

### 2. Installazione
```bash
# Clone repository
cd server/

# Crea virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt
```

### 3. Configurazione

Crea file `.env` nella root del progetto:
```env
# Copia da .env e modifica i valori
JWT_SECRET_KEY=tua-chiave-segreta-min-32-caratteri
DB_PASSWORD=tua-password-database
```

**IMPORTANTE**: 
- Cambia `JWT_SECRET_KEY` con una chiave casuale sicura
- Non committare mai il file `.env` su git

### 4. Avvio Server
```bash
# Sviluppo
python app.py

# Produzione (con Gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## API Endpoints

### Autenticazione Utenti

#### POST /auth/registerUser
Registra nuovo utente

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Errors:**
- `400` - Email o password mancanti/invalidi
- `409` - Email già registrata
- `500` - Errore database

---

#### GET /auth/isAuthorizedUser
Valida user_token

**Query Params:**
- `user_token` - Token JWT utente da validare

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
(stesso token se valido, nuovo token se in scadenza)

**Errors:**
- `401` - Token scaduto o invalido

---

#### POST /auth/renewUser
Rinnova user_token scaduto

**Request:**
```json
{
  "user_token": "eyJhbGc..."
}
```

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Errors:**
- `401` - Token invalido
- `404` - Utente non trovato

---

### Autenticazione Frighi

#### POST /auth/registerFridge
Registra nuovo frigo

**Request:**
```json
{
  "user_token": "eyJhbGc...",
  "position": "Cucina"
}
```

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Errors:**
- `401` - Token utente invalido
- `404` - Utente non trovato
- `500` - Errore database

---

#### GET /auth/isAuthorizedFridge
Valida token frigo

**Query Params:**
- `fridge_token` - Token JWT da validare

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
(stesso token se valido, nuovo token se in scadenza)

**Errors:**
- `401` - Token scaduto o invalido

---

#### POST /auth/renewFridge
Rinnova token frigo scaduto

**Request:**
```json
{
  "user_token": "eyJhbGc...",
  "fridge_id": 42
}
```

**Response (200):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Errors:**
- `401` - Token utente invalido
- `403` - Frigo appartiene ad altro utente
- `404` - Frigo non trovato

---

## API Users (Lato Utente)
Gestione frighi da parte dell'utente via app mobile.

### GET /api/users/fridges
Recupera tutti i frighi dell'utente

**Query Params:**
- `user_token` - Token JWT utente

**Response (200):**
```json
{
  "success": true,
  "fridges": [
    {
      "ID": 1,
      "position": "Cucina",
      "created_at": "2026-01-15 10:30:00"
    }
  ]
}
```

---

### GET /api/users/fridge/<fridge_id>
Recupera informazioni dettagliate di un frigo

**Query Params:**
- `user_token` - Token JWT utente

**Response (200):**
```json
{
  "success": true,
  "fridge": {
    "ID": 1,
    "user_ID": 42,
    "position": "Cucina",
    "created_at": "2026-01-15 10:30:00"
  }
}
```

**Errors:**
- `403` - Frigo appartiene ad altro utente
- `404` - Frigo non trovato

---

### PUT /api/users/fridge/<fridge_id>/position
Aggiorna posizione frigo

**Request:**
```json
{
  "user_token": "eyJ...",
  "position": "Garage"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Posizione aggiornata"
}
```

---

### DELETE /api/users/fridge/<fridge_id>
Elimina un frigo

**Request:**
```json
{
  "user_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Frigo eliminato"
}
```

---

## API Fridges (Lato Frigo)
Operazioni eseguite dal Raspberry Pi del frigo.

### POST /api/fridges/measurement
Inserisce nuova misurazione (temperatura + potenza)

**Request:**
```json
{
  "fridge_token": "eyJ...",
  "temperature": 4.5,
  "power": 120.3,
  "timestamp": "2026-02-05 14:30:00"  // optional
}
```

**Response (201):**
```json
{
  "success": true,
  "measurement_id": 123
}
```

---

### GET /api/fridges/measurements/history
Recupera storico misurazioni

**Query Params:**
- `fridge_token` - Token JWT frigo
- `hours` - Ore di storico (default: 48)

**Response (200):**
```json
{
  "success": true,
  "measurements": [
    {
      "timestamp": "2026-02-05 14:30:00",
      "temperature": 4.5,
      "power": 120.3
    }
  ]
}
```

---

### GET /api/fridges/measurements/temperature/stats
Statistiche temperatura

**Query Params:**
- `fridge_token` - Token JWT frigo
- `hours` - Ore di storico (default: 48)

**Response (200):**
```json
{
  "success": true,
  "stats": {
    "count": 100,
    "average": 4.2,
    "min": 3.8,
    "max": 5.1
  }
}
```

---

### GET /api/fridges/measurements/power/stats
Statistiche consumo

(Stesso formato di temperature/stats)

---

### POST /api/fridges/alert
Inserisce nuovo alert

**Request:**
```json
{
  "fridge_token": "eyJ...",
  "category": "high_temp",
  "message": "Temperatura alta rilevata",
  "timestamp": "2026-02-05 14:30:00"  // optional
}
```

**Response (201):**
```json
{
  "success": true,
  "alert_id": 456
}
```

---

### GET /api/fridges/alerts/recent
Recupera alert recenti

**Query Params:**
- `fridge_token` - Token JWT frigo
- `hours` - Ore di storico (default: 24)
- `category` - Filtra per categoria (optional)

**Response (200):**
```json
{
  "success": true,
  "alerts": [
    {
      "ID": 1,
      "timestamp": "2026-02-05 14:30:00",
      "category": "high_temp",
      "message": "Temperatura alta"
    }
  ]
}
```

---

### GET /api/fridges/alerts/critical
Recupera solo alert critici

**Query Params:**
- `fridge_token` - Token JWT frigo
- `hours` - Ore di storico (default: 24)

---

### POST /api/fridges/door
Registra evento porta (aperta/chiusa)

**Request:**
```json
{
  "fridge_token": "eyJ...",
  "is_open": true
}
```

**Response (201):**
```json
{
  "success": true,
  "alert_id": 789
}
```

---

### POST /api/fridges/product/movement
Registra movimento prodotto (aggiunta/rimozione)

**Request:**
```json
{
  "fridge_token": "eyJ...",
  "product_id": 5,
  "quantity": 2,  // positivo=aggiunta, negativo=rimozione
  "timestamp": "2026-02-05 14:30:00"  // optional
}
```

**Response (201):**
```json
{
  "success": true,
  "movement_id": 321
}
```

---

### GET /api/fridges/products/current
Recupera prodotti attualmente nel frigo

**Query Params:**
- `fridge_token` - Token JWT frigo

**Response (200):**
```json
{
  "success": true,
  "products": [
    {
      "fridge_product_id": 1,
      "product_id": 5,
      "name": "Latte",
      "brand": "Granarolo",
      "category": "Latticini",
      "quantity": 2,
      "added_in": "2026-02-03 10:00:00"
    }
  ]
}
```

---

### GET /api/fridges/products/movements/history
Storico movimenti prodotti

**Query Params:**
- `fridge_token` - Token JWT frigo
- `hours` - Ore di storico (default: 168 = 7 giorni)

---

### GET /api/fridges/product/search
Cerca prodotto per nome (per YOLO detection)

**Query Params:**
- `fridge_token` - Token JWT frigo
- `name` - Nome prodotto

**Response (200):**
```json
{
  "success": true,
  "product": {
    "ID": 5,
    "name": "Latte",
    "brand": "Granarolo",
    "category": "Latticini"
  }
}
```

**Errors:**
- `404` - Prodotto non trovato

---

## Struttura Progetto
```
server/
├── app.py              # Entry point
├── config.py           # Configurazione
├── .env                # Variabili ambiente (non in git)
├── requirements.txt    # Dipendenze
│
├── api/                # API Routes
│   ├── __init__.py
│   ├── auth/           # Autenticazione JWT
│   │   ├── __init__.py
│   │   └── routes.py   # Route auth
│   ├── users/          # API lato utente
│   │   ├── __init__.py
│   │   └── routes.py   # Route gestione frighi (user)
│   └── fridges/        # API lato frigo
│       ├── __init__.py
│       └── routes.py   # Route measurements/alerts/products
│
├── database/           # Database
│   ├── __init__.py
│   ├── connection.py   # Connection pooling
│   ├── user_db.py      # Query utente/frigo
│   └── fridge_db.py    # Query measurements/alerts/products
│
├── utils/              # Utilities
│   ├── __init__.py
│   ├── logger.py       # Logger
│   ├── errors.py       # Gestione errori
│   ├── jwt_utils.py    # JWT utilities
│   └── request_auth.py # Request auth helpers
│
└── logs/               # Log files
    └── server.log
```

---

## Configurazione Rate Limiting

Rate limits di default (modificabili in `.env`):

- `/registerFrigo`: 10 richieste/ora
- `/renewFrigo`: 20 richieste/ora  
- `/isAuthorized`: 200 richieste/giorno

---

## Logging

I log sono salvati in `logs/server.log` con rotazione automatica:
- Dimensione max: 10MB
- File backup: 5

Formato:
```
[2026-02-05 15:30:45] [auth] [INFO] Frigo 42 registrato per user 123
```

---

## Testing
```bash
# Test connessione database
cd database/
python queries.py

# Test endpoint (con curl)
curl http://localhost:5000/health
```

---

## Deploy Produzione

### Con Gunicorn (consigliato)
```bash
# Installa gunicorn
pip install gunicorn

# Avvia server
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile logs/access.log app:app
```

### Con systemd (Linux)

Crea `/etc/systemd/system/smartfridge.service`:
```ini
[Unit]
Description=Smart Fridge Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/server
Environment="PATH=/path/to/server/venv/bin"
ExecStart=/path/to/server/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable smartfridge
sudo systemctl start smartfridge
```

---

## Troubleshooting

### Errore "JWT_SECRET_KEY must be set"
- Assicurati che il file `.env` esista
- Verifica che `JWT_SECRET_KEY` sia impostata e diversa dal placeholder

### Errore connessione database
- Verifica credenziali in `.env`
- Controlla che MySQL sia accessibile dall'IP del server
- Testa connessione: `python database/queries.py`

### Rate limit troppo restrittivo
- Modifica valori in `.env`:
```env
  RATE_LIMIT_REGISTER_PER_HOUR=50
  RATE_LIMIT_IS_AUTHORIZED_PER_DAY=1000
```
```

---

## Riepilogo Finale

Struttura completa creata:
```
server/
├── .env
├── .gitignore
├── requirements.txt
├── README.md
├── config.py
├── app.py
│
├── auth/
│   ├── __init__.py
│   ├── jwt_utils.py
│   └── routes.py
│
├── database/
│   ├── __init__.py
│   ├── db_manager.py
│   └── queries.py
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── errors.py
│
└── logs/  (creata automaticamente)