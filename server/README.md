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

### POST /registerFrigo
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

### GET /isAuthorized
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

### POST /renewFrigo
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

## Struttura Progetto
```
server/
├── app.py              # Entry point
├── config.py           # Configurazione
├── .env                # Variabili ambiente (non in git)
├── requirements.txt    # Dipendenze
│
├── auth/               # Autenticazione
│   ├── jwt_utils.py    # JWT utilities
│   └── routes.py       # Route auth
│
├── database/           # Database
│   ├── db_manager.py   # DatabaseManager
│   └── queries.py      # Query auth
│
├── utils/              # Utilities
│   ├── logger.py       # Logger
│   └── errors.py       # Gestione errori
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