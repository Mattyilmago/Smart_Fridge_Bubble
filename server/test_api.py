#!/usr/bin/env python3
"""
Smart Fridge API - Interactive Tester
Script interattivo per testare tutte le API del server
"""

import requests
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# Configurazione
BASE_URL = "http://localhost:5000"
TIMEOUT = 10

# Storage per token (in memoria durante la sessione)
session_data = {
    'user_tokens': [],      # Lista di tutti i token utente generati
    'fridge_tokens': [],    # Lista di tutti i token frigo generati
    'user_id': None,
    'fridge_id': None
}


# === UTILITY FUNCTIONS ===

def print_header(text: str):
    """Stampa un header evidenziato"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text: str):
    """Stampa messaggio di successo"""
    print(f"✓ {text}")


def print_error(text: str):
    """Stampa messaggio di errore"""
    print(f"✗ {text}")


def print_info(text: str):
    """Stampa informazione"""
    print(f"ℹ {text}")


def print_response(response: requests.Response):
    """Stampa la risposta HTTP in modo leggibile"""
    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    try:
        data = response.json()
        print(f"\nResponse Body (JSON):")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(f"\nResponse Body (Text):")
        print(response.text[:500])  # Primi 500 caratteri


def get_input(prompt: str, default: str = None) -> str:
    """Ottiene input dall'utente con valore di default opzionale"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def select_token(token_type: str) -> Optional[str]:
    """Permette di selezionare un token tramite menu numerico"""
    if token_type == 'user':
        tokens = session_data['user_tokens']
        title = 'USER TOKEN'
    else:
        tokens = session_data['fridge_tokens']
        title = 'FRIDGE TOKEN'
    
    if not tokens:
        print_info(f"Nessun {title.lower()} disponibile in sessione")
        return None
    
    print(f"\n{title} disponibili:")
    for i, token in enumerate(tokens, 1):
        preview = token[:40] + '...' if len(token) > 40 else token
        print(f"{i}. {preview}")
    print("0. Inserisci manualmente")
    
    choice = get_input("Scelta", "1")
    
    if choice == "0":
        return get_input(f"Inserisci {title}")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tokens):
            return tokens[idx]
        else:
            print_error("Scelta non valida, uso ultimo token")
            return tokens[-1]
    except ValueError:
        print_error("Input non valido, uso ultimo token")
        return tokens[-1] if tokens else None


def wait_continue():
    """Aspetta che l'utente prema invio"""
    input("\nPremi INVIO per continuare...")


# === API FUNCTIONS ===

# --- AUTENTICAZIONE UTENTI ---

def register_user():
    """POST /auth/registerUser - Registra nuovo utente"""
    print_header("REGISTRA NUOVO UTENTE")
    
    email = get_input("Email")
    password = get_input("Password")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/registerUser",
            json={"email": email, "password": password},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            token = response.text.strip('"')
            session_data['user_tokens'].append(token)
            print_success(f"Utente registrato! Token salvato in sessione (#{len(session_data['user_tokens'])})")
            print_info(f"Token: {token[:50]}...")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def is_authorized_user():
    """GET /auth/isAuthorizedUser - Valida user_token"""
    print_header("VALIDA USER TOKEN")
    
    token = select_token('user')
    if not token:
        token = get_input("User Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/isAuthorizedUser",
            params={"user_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            new_token = response.text.strip('"')
            if new_token != token and new_token not in session_data['user_tokens']:
                session_data['user_tokens'].append(new_token)
            print_success("Token valido (eventualmente rinnovato)")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def renew_user():
    """POST /auth/renewUser - Rinnova user_token scaduto"""
    print_header("RINNOVA USER TOKEN")
    
    token = select_token('user')
    if not token:
        token = get_input("User Token (scaduto)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/renewUser",
            json={"user_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            new_token = response.text.strip('"')
            session_data['user_tokens'].append(new_token)
            print_success(f"Token rinnovato! Salvato come #{len(session_data['user_tokens'])}")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- AUTENTICAZIONE FRIGORIFERI ---

def register_frigo():
    """POST /auth/registerFridge - Registra nuovo frigo"""
    print_header("REGISTRA NUOVO FRIGORIFERO")
    
    print_info("Seleziona User Token del proprietario:")
    user_token = select_token('user')
    if not user_token:
        user_token = get_input("User Token")
    
    position = get_input("Posizione (es. 'Cucina')")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/registerFridge",
            json={
                "user_token": user_token,
                "position": position
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            token = response.text.strip('"')
            session_data['fridge_tokens'].append(token)
            print_success(f"Frigorifero registrato! Token salvato in sessione (#{len(session_data['fridge_tokens'])})")
            print_info(f"Token: {token[:50]}...")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def is_authorized_frigo():
    """GET /auth/isAuthorizedFridge - Valida fridge_token"""
    print_header("VALIDA FRIDGE TOKEN")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/isAuthorizedFridge",
            params={"fridge_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            new_token = response.text.strip('"')
            if new_token != token and new_token not in session_data['fridge_tokens']:
                session_data['fridge_tokens'].append(new_token)
            print_success("Token valido (eventualmente rinnovato)")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def renew_frigo():
    """POST /auth/renewFridge - Rinnova fridge_token"""
    print_header("RINNOVA FRIDGE TOKEN")
    
    print_info("Seleziona User Token del proprietario:")
    user_token = select_token('user')
    if not user_token:
        user_token = get_input("User Token")
    
    # Prima otteniamo la lista dei frigo per facilitare la scelta
    print_info("\nRecupero lista frigoriferi...")
    try:
        fridges_response = requests.get(
            f"{BASE_URL}/api/users/fridges",
            params={"user_token": user_token},
            timeout=TIMEOUT
        )
        
        if fridges_response.status_code == 200:
            fridges_data = fridges_response.json()
            fridges = fridges_data.get('fridges', [])
            
            if fridges:
                print("\nFrigoriferi disponibili:")
                for i, fridge in enumerate(fridges, 1):
                    print(f"{i}. ID: {fridge['ID']} - Posizione: {fridge['position']}")
                print("0. Inserisci manualmente")
                
                choice = get_input("Scegli frigo", "1")
                
                if choice == "0":
                    fridge_id = get_input("Fridge ID da rinnovare")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(fridges):
                            fridge_id = str(fridges[idx]['ID'])
                        else:
                            fridge_id = str(fridges[0]['ID'])
                    except ValueError:
                        fridge_id = str(fridges[0]['ID'])
            else:
                print_info("Nessun frigorifero trovato")
                fridge_id = get_input("Fridge ID da rinnovare")
        else:
            print_info("Impossibile recuperare lista frigo")
            fridge_id = get_input("Fridge ID da rinnovare")
    except:
        fridge_id = get_input("Fridge ID da rinnovare")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/renewFridge",
            json={
                "user_token": user_token,
                "fridge_id": int(fridge_id)
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            new_token = response.text.strip('"')
            session_data['fridge_tokens'].append(new_token)
            print_success(f"Token rinnovato! Salvato come #{len(session_data['fridge_tokens'])}")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- GESTIONE UTENTI ---

def get_user_fridges():
    """GET /api/users/fridges - Lista frigoriferi dell'utente"""
    print_header("FRIGORIFERI DELL'UTENTE")
    
    token = select_token('user')
    if not token:
        token = get_input("User Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/users/fridges",
            params={"user_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- DATI FRIGORIFERO ---

def send_measurement():
    """POST /api/fridges/measurement - Invia misura temperatura/potenza"""
    print_header("INVIA MISURAZIONE")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    temperature = float(get_input("Temperatura (°C)", "5.0"))
    power = float(get_input("Potenza (W)", "100.0"))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/fridges/measurement",
            json={
                "fridge_token": token,
                "temperature": temperature,
                "power": power
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_measurements():
    """GET /api/fridges/measurements/history - Ottiene storico misurazioni"""
    print_header("STORICO MISURAZIONI")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    hours = get_input("Ore di storico", "48")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/measurements/history",
            params={
                "fridge_token": token,
                "hours": hours
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def send_alert():
    """POST /api/fridges/alert - Invia un alert"""
    print_header("INVIA ALERT")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    # Categorie disponibili
    categories = [
        "door_open",
        "door_closed",
        "door_left_open",
        "high_temp",
        "critic_temp",
        "low_temp",
        "critic_power",
        "sensor_offline"
    ]
    
    print("\nCategorie disponibili:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    print("0. Inserisci manualmente")
    
    choice = get_input("Scegli categoria", "1")
    
    if choice == "0":
        category = get_input("Categoria")
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                category = categories[idx]
            else:
                category = categories[0]
        except ValueError:
            category = categories[0]
    
    message = get_input("Messaggio")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/fridges/alert",
            json={
                "fridge_token": token,
                "category": category,
                "message": message
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_alerts():
    """GET /api/fridges/alerts/recent - Ottiene alert recenti"""
    print_header("ALERT RECENTI")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    hours = get_input("Ore di storico", "48")
    category = get_input("Categoria (opzionale, INVIO per tutte)", "")
    
    try:
        params = {
            "fridge_token": token,
            "hours": hours
        }
        if category:
            params['category'] = category
        
        response = requests.get(
            f"{BASE_URL}/api/fridges/alerts/recent",
            params=params,
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- DASHBOARD E STATISTICHE ---

def get_dashboard():
    """GET /api/fridges/dashboard - Dashboard completa frigo"""
    print_header("DASHBOARD FRIGORIFERO")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/dashboard",
            params={"fridge_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_temp_stats():
    """GET /api/fridges/measurements/temperature/stats - Statistiche temperatura"""
    print_header("STATISTICHE TEMPERATURA")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    hours = get_input("Ore di storico", "24")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/measurements/temperature/stats",
            params={
                "fridge_token": token,
                "hours": hours
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_power_stats():
    """GET /api/fridges/measurements/power/stats - Statistiche potenza"""
    print_header("STATISTICHE POTENZA")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    hours = get_input("Ore di storico", "24")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/measurements/power/stats",
            params={
                "fridge_token": token,
                "hours": hours
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_user_statistics():
    """GET /api/users/statistics - Statistiche globali utente"""
    print_header("STATISTICHE UTENTE")
    
    token = select_token('user')
    if not token:
        token = get_input("User Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/users/statistics",
            params={"user_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- GESTIONE PRODOTTI ---

def add_product_movement():
    """POST /api/fridges/product/movement - Aggiungi/rimuovi prodotto"""
    print_header("MOVIMENTO PRODOTTO")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    product_id = get_input("Product ID")
    quantity = get_input("Quantità (negativo per rimuovere)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/fridges/product/movement",
            json={
                "fridge_token": token,
                "product_id": int(product_id),
                "quantity": int(quantity)
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def get_current_products():
    """GET /api/fridges/products/current - Prodotti nel frigo"""
    print_header("PRODOTTI CORRENTI")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/products/current",
            params={"fridge_token": token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def search_product():
    """GET /api/fridges/product/search - Cerca prodotto"""
    print_header("CERCA PRODOTTO")
    
    token = select_token('fridge')
    if not token:
        token = get_input("Fridge Token")
    
    name = get_input("Nome prodotto")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/fridges/product/search",
            params={
                "fridge_token": token,
                "name": name
            },
            timeout=TIMEOUT
        )
        
        print_response(response)
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


# --- GESTIONE DATABASE ---

def delete_fridge():
    """DELETE /api/users/fridge/<id> - Elimina frigorifero"""
    print_header("ELIMINA FRIGORIFERO")
    
    print_info("Seleziona User Token:")
    user_token = select_token('user')
    if not user_token:
        user_token = get_input("User Token")
    
    # Recupera lista frigo
    print_info("\nRecupero lista frigoriferi...")
    try:
        fridges_response = requests.get(
            f"{BASE_URL}/api/users/fridges",
            params={"user_token": user_token},
            timeout=TIMEOUT
        )
        
        if fridges_response.status_code == 200:
            fridges_data = fridges_response.json()
            fridges = fridges_data.get('fridges', [])
            
            if fridges:
                print("\nFrigoriferi disponibili:")
                for i, fridge in enumerate(fridges, 1):
                    print(f"{i}. ID: {fridge['ID']} - Posizione: {fridge['position']}")
                print("0. Inserisci manualmente")
                
                choice = get_input("Scegli frigo da eliminare", "1")
                
                if choice == "0":
                    fridge_id = get_input("Fridge ID")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(fridges):
                            fridge_id = str(fridges[idx]['ID'])
                        else:
                            fridge_id = str(fridges[0]['ID'])
                    except ValueError:
                        fridge_id = str(fridges[0]['ID'])
            else:
                print_info("Nessun frigorifero trovato")
                return wait_continue()
        else:
            fridge_id = get_input("Fridge ID")
    except:
        fridge_id = get_input("Fridge ID")
    
    # Conferma
    confirm = get_input(f"\n⚠️  ATTENZIONE: Eliminare frigo {fridge_id}? (si/no)", "no")
    if confirm.lower() != "si":
        print_info("Operazione annullata")
        return wait_continue()
    
    try:
        response = requests.delete(
            f"{BASE_URL}/api/users/fridge/{fridge_id}",
            json={"user_token": user_token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            # Rimuovi token frigo dalla sessione se presente
            print_success("Frigorifero eliminato!")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def delete_account():
    """DELETE /api/users/account - Elimina account utente"""
    print_header("ELIMINA ACCOUNT UTENTE")
    
    print_info("Seleziona User Token:")
    user_token = select_token('user')
    if not user_token:
        user_token = get_input("User Token")
    
    # Conferma doppia
    print("\n" + "=" * 60)
    print("⚠️  ATTENZIONE: QUESTA OPERAZIONE È IRREVERSIBILE!")
    print("Tutti i frigoriferi e dati associati saranno eliminati.")
    print("=" * 60)
    
    confirm1 = get_input("\nDigita 'ELIMINA' per confermare", "")
    if confirm1 != "ELIMINA":
        print_info("Operazione annullata")
        return wait_continue()
    
    confirm2 = get_input("Sei sicuro? (si/no)", "no")
    if confirm2.lower() != "si":
        print_info("Operazione annullata")
        return wait_continue()
    
    try:
        response = requests.delete(
            f"{BASE_URL}/api/users/account",
            json={"user_token": user_token},
            timeout=TIMEOUT
        )
        
        print_response(response)
        
        if response.status_code == 200:
            # Pulisci token dalla sessione
            if user_token in session_data['user_tokens']:
                session_data['user_tokens'].remove(user_token)
            print_success("Account eliminato!")
        
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def view_database_tables():
    """Visualizza contenuto tabelle database usando API debug (SELECT *)"""
    print_header("VISUALIZZA TABELLE DATABASE")
    
    # Ottieni lista tabelle disponibili
    try:
        response = requests.get(
            f"{BASE_URL}/api/debug/tables",
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            tables = data.get('tables', [])
        else:
            print_error(f"Impossibile recuperare lista tabelle: {response.status_code}")
            wait_continue()
            return
    except Exception as e:
        print_error(f"Errore connessione: {e}")
        wait_continue()
        return
    
    print("\nTabelle disponibili:")
    for i, table in enumerate(tables, 1):
        print(f"{i}. {table}")
    print("0. Torna indietro")
    
    choice = get_input("\nScegli tabella da visualizzare", "0")
    
    if choice == "0":
        return
    
    try:
        choice_int = int(choice)
        
        if choice_int < 1 or choice_int > len(tables):
            print_error("Scelta non valida")
            wait_continue()
            return
        
        table_name = tables[choice_int - 1]
        
        print_header(f"TABELLA: {table_name}")
        
        # Chiedi parametri di paginazione
        limit = get_input("Limite righe da visualizzare (max 1000)", "100")
        offset = get_input("Offset (salta le prime N righe)", "0")
        
        # Prima ottieni il conteggio totale
        try:
            count_response = requests.get(
                f"{BASE_URL}/api/debug/table/{table_name}/count",
                timeout=TIMEOUT
            )
            
            if count_response.status_code == 200:
                count_data = count_response.json()
                total_count = count_data.get('count', 0)
                print_info(f"Totale righe nella tabella: {total_count}")
            else:
                total_count = "Sconosciuto"
                
        except Exception as e:
            print_error(f"Errore conteggio: {e}")
            total_count = "Sconosciuto"
        
        # Recupera i dati
        print_info(f"\nRecupero dati da {table_name}...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/debug/table/{table_name}",
                params={
                    'limit': limit,
                    'offset': offset
                },
                timeout=TIMEOUT
            )
            
            print_response(response)
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get('data', [])
                count = data.get('count', 0)
                
                print_success(f"\n{count} righe recuperate (Total: {total_count})")
                
                if rows:
                    print("\nDati:")
                    print(json.dumps(rows, indent=2, ensure_ascii=False))
                else:
                    print_info("Nessun dato trovato")
            
        except Exception as e:
            print_error(f"Errore: {e}")
            
    except ValueError:
        print_error("Input non valido")
    except Exception as e:
        print_error(f"Errore: {e}")
    
    wait_continue()


def delete_all_data():
    """ELIMINA TUTTI I DATI DEL DATABASE - OPERAZIONE IRREVERSIBILE"""
    print_header("⚠️  ELIMINA TUTTI I DATI DATABASE ⚠️")
    
    print("\n" + "=" * 60)
    print("██████████████████ ATTENZIONE ██████████████████")
    print("=" * 60)
    print()
    print("Questa operazione eliminerà TUTTI i dati del database:")
    print("  - Tutti gli account utente")
    print("  - Tutti i frigoriferi")
    print("  - Tutte le misurazioni")
    print("  - Tutti gli alert")
    print("  - Tutti i prodotti e movimenti")
    print()
    print("QUESTA OPERAZIONE È IRREVERSIBILE!")
    print("=" * 60)
    
    # Prima conferma
    confirm1 = get_input("\n⚠️  Digita 'ELIMINA TUTTO' per procedere", "")
    if confirm1 != "ELIMINA TUTTO":
        print_info("Operazione annullata")
        return wait_continue()
    
    # Seconda conferma
    confirm2 = get_input("\n⚠️  Sei ASSOLUTAMENTE sicuro? (SI CONFERMO/no)", "no")
    if confirm2 != "SI CONFERMO":
        print_info("Operazione annullata")
        return wait_continue()
    
    # Terza conferma finale
    print("\n⚠️  ULTIMA CONFERMA:")
    confirm3 = get_input("Digita il numero di utenti da eliminare (tutti)", "")
    
    print_info("\nEliminazione di tutti gli account utente in corso...")
    
    deleted_count = 0
    errors = 0
    
    # Elimina tutti i token utente salvati
    user_tokens_copy = session_data['user_tokens'].copy()
    
    for i, user_token in enumerate(user_tokens_copy, 1):
        try:
            print(f"\nEliminazione account {i}/{len(user_tokens_copy)}...")
            
            response = requests.delete(
                f"{BASE_URL}/api/users/account",
                json={"user_token": user_token},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                deleted_count += 1
                print_success(f"Account {i} eliminato")
            else:
                errors += 1
                print_error(f"Errore nell'eliminazione account {i}: {response.status_code}")
                
        except Exception as e:
            errors += 1
            print_error(f"Errore: {e}")
    
    # Pulisci tutti i token dalla sessione
    session_data['user_tokens'].clear()
    session_data['fridge_tokens'].clear()
    session_data['user_id'] = None
    session_data['fridge_id'] = None
    
    print("\n" + "=" * 60)
    print_success(f"Eliminazione completata!")
    print(f"Account eliminati: {deleted_count}")
    if errors > 0:
        print_error(f"Errori: {errors}")
    print(f"Token rimossi dalla sessione: {len(user_tokens_copy)}")
    print("=" * 60)
    
    wait_continue()


# === MENU FUNCTIONS ===

def menu_auth_users():
    """Menu autenticazione utenti"""
    while True:
        print_header("AUTENTICAZIONE UTENTI")
        print("1. Registra nuovo utente")
        print("2. Valida user_token")
        print("3. Rinnova user_token")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            register_user()
        elif choice == "2":
            is_authorized_user()
        elif choice == "3":
            renew_user()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_auth_fridges():
    """Menu autenticazione frigoriferi"""
    while True:
        print_header("AUTENTICAZIONE FRIGORIFERI")
        print("1. Registra nuovo frigo")
        print("2. Valida fridge_token")
        print("3. Rinnova fridge_token")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            register_frigo()
        elif choice == "2":
            is_authorized_frigo()
        elif choice == "3":
            renew_frigo()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_users():
    """Menu gestione utenti"""
    while True:
        print_header("GESTIONE UTENTI")
        print("1. Lista frigoriferi")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            get_user_fridges()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_fridges():
    """Menu dati frigoriferi"""
    while True:
        print_header("DATI FRIGORIFERI")
        print("1. Invia misurazione (temp + potenza)")
        print("2. Visualizza storico misurazioni")
        print("3. Invia alert")
        print("4. Visualizza storico alerts")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            send_measurement()
        elif choice == "2":
            get_measurements()
        elif choice == "3":
            send_alert()
        elif choice == "4":
            get_alerts()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_dashboard():
    """Menu dashboard e statistiche"""
    while True:
        print_header("DASHBOARD & STATISTICHE")
        print("1. Dashboard frigorifero")
        print("2. Statistiche temperatura")
        print("3. Statistiche potenza")
        print("4. Statistiche utente (tutti i frigo)")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            get_dashboard()
        elif choice == "2":
            get_temp_stats()
        elif choice == "3":
            get_power_stats()
        elif choice == "4":
            get_user_statistics()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_products():
    """Menu gestione prodotti"""
    while True:
        print_header("GESTIONE PRODOTTI")
        print("1. Aggiungi/Rimuovi prodotto")
        print("2. Visualizza prodotti correnti")
        print("3. Cerca prodotto per nome")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            add_product_movement()
        elif choice == "2":
            get_current_products()
        elif choice == "3":
            search_product()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def menu_database():
    """Menu gestione database"""
    while True:
        print_header("GESTIONE DATABASE")
        print("1. Visualizza tabelle database")
        print("2. Elimina frigorifero")
        print("3. Elimina account utente")
        print("4. ⚠️  ELIMINA TUTTI I DATI")
        print("0. Torna al menu principale")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            view_database_tables()
        elif choice == "2":
            delete_fridge()
        elif choice == "3":
            delete_account()
        elif choice == "4":
            delete_all_data()
        elif choice == "0":
            break
        else:
            print_error("Scelta non valida")
            wait_continue()


def show_session_info():
    """Mostra i dati della sessione corrente"""
    print_header("INFORMAZIONI SESSIONE")
    
    print(f"\nUser Tokens ({len(session_data['user_tokens'])} disponibili):")
    if session_data['user_tokens']:
        for i, token in enumerate(session_data['user_tokens'], 1):
            preview = token[:50] + '...' if len(token) > 50 else token
            print(f"  {i}. {preview}")
    else:
        print("  Nessun token utente salvato")
    
    print(f"\nFridge Tokens ({len(session_data['fridge_tokens'])} disponibili):")
    if session_data['fridge_tokens']:
        for i, token in enumerate(session_data['fridge_tokens'], 1):
            preview = token[:50] + '...' if len(token) > 50 else token
            print(f"  {i}. {preview}")
    else:
        print("  Nessun token frigo salvato")
    
    print(f"\nUser ID: {session_data['user_id'] or 'Non impostato'}")
    print(f"Fridge ID: {session_data['fridge_id'] or 'Non impostato'}")
    wait_continue()


def main_menu():
    """Menu principale"""
    while True:
        print_header("SMART FRIDGE API - TEST INTERATTIVO")
        print(f"Server: {BASE_URL}")
        print()
        print("1. 👤 Autenticazione Utenti")
        print("2. 🧊 Autenticazione Frigoriferi")
        print("3. 📱 Gestione Utenti")
        print("4. 📊 Dati Frigoriferi")
        print("5. 📈 Dashboard & Statistiche")
        print("6. 🛒 Gestione Prodotti")
        print("7. 🗑️  Gestione Database")
        print("8. ℹ️  Info Sessione")
        print("0. 🚪 Esci")
        
        choice = get_input("\nScelta")
        
        if choice == "1":
            menu_auth_users()
        elif choice == "2":
            menu_auth_fridges()
        elif choice == "3":
            menu_users()
        elif choice == "4":
            menu_fridges()
        elif choice == "5":
            menu_dashboard()
        elif choice == "6":
            menu_products()
        elif choice == "7":
            menu_database()
        elif choice == "8":
            show_session_info()
        elif choice == "0":
            print("\n👋 Arrivederci!")
            sys.exit(0)
        else:
            print_error("Scelta non valida")
            wait_continue()


# === MAIN ===

if __name__ == "__main__":
    try:
        # Verifica connessione server
        print_info(f"Verifico connessione a {BASE_URL}...")
        response = requests.get(f"{BASE_URL}/", timeout=3)
        if response.status_code == 200:
            print_success("Server raggiungibile!\n")
        else:
            print_error(f"Server risponde con status {response.status_code}\n")
    except Exception as e:
        print_error(f"Impossibile raggiungere il server: {e}")
        print_info("Assicurati che il server sia avviato su http://localhost:5000")
        sys.exit(1)
    
    # Avvia menu principale
    main_menu()
