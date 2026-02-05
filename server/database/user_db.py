"""
User Database Operations
Gestisce operazioni database lato utente (autenticazione, creazione frigo)

Classe stateless: tutti gli ID vengono passati come parametri.
Questo permette di gestire richieste concorrenti da utenti diversi.
"""

from typing import Optional, List, Dict
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from .connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger('database')


class UserDatabase(DatabaseConnection):
    """
    Query database per autenticazione e operazioni utente
    
    Classe stateless: user_id e fridge_id vengono passati come parametri.
    """
    
    def __init__(self, use_pool: bool = True):
        """
        Inizializza gestore query per operazioni utente
        
        Args:
            use_pool: Se True usa connection pooling
        """
        super().__init__(use_pool)
        logger.info("UserDatabase initialized")
    
    def user_exists(self, user_id: int) -> bool:
        """
        Verifica se utente esiste
        
        Args:
            user_id: ID utente
        
        Returns:
            bool: True se esiste
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT ID FROM Users WHERE ID = %s"
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Error as e:
            logger.error(f"Error checking user existence: {e}")
            return False
    
    def create_fridge(self, user_id: int, position: str) -> Optional[int]:
        """
        Crea nuovo frigo nel database
        
        Args:
            user_id: ID utente proprietario
            position: Posizione frigo (es. "Cucina")
        
        Returns:
            int: fridge_id del frigo creato, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO Fridges (user_ID, position)
                    VALUES (%s, %s)
                """
                cursor.execute(query, (user_id, position))
                fridge_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                
                logger.info(f"Frigo {fridge_id} creato per user {user_id}, posizione: {position}")
                return fridge_id
        except Error as e:
            logger.error(f"Error creating fridge: {e}")
            return None
    
    def get_fridge_owner(self, fridge_id: int) -> Optional[int]:
        """
        Recupera user_ID proprietario del frigo
        
        Args:
            fridge_id: ID frigo
        
        Returns:
            int: user_ID o None se frigo non esiste
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT user_ID FROM Fridges WHERE ID = %s"
                cursor.execute(query, (fridge_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    return result[0]
                return None
        except Error as e:
            logger.error(f"Error getting fridge owner: {e}")
            return None
    
    def get_user_fridges(self, user_id: int) -> List[Dict]:
        """
        Recupera tutti i frighi di un utente
        
        Args:
            user_id: ID utente
        
        Returns:
            List[Dict]: Lista frigo con ID, position, created_at
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT ID, position, created_at
                    FROM Fridges
                    WHERE user_ID = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                cursor.close()
                logger.info(f"Retrieved {len(results)} fridges for user {user_id}")
                return results
        except Error as e:
            logger.error(f"Error getting user fridges: {e}")
            return []
    
    def get_fridge_info(self, fridge_id: int) -> Optional[Dict]:
        """
        Recupera informazioni complete di un frigo
        
        Args:
            fridge_id: ID del frigo
        
        Returns:
            Dict: Info frigo (ID, user_ID, position, created_at) o None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT *
                    FROM Fridges
                    WHERE ID = %s
                """
                cursor.execute(query, (fridge_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    logger.info(f"Fridge {result['ID']} info retrieved")
                return result
        except Error as e:
            logger.error(f"Error getting fridge info: {e}")
            return None
    
    def update_fridge_position(self, fridge_id: int, position: str) -> bool:
        """
        Aggiorna posizione del frigo
        
        Args:
            fridge_id: ID del frigo
            position: Nuova posizione (es. "Cucina", "Garage")
        
        Returns:
            bool: True se aggiornato, False se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    UPDATE Fridges
                    SET position = %s
                    WHERE ID = %s
                """
                cursor.execute(query, (position, fridge_id))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                
                if affected > 0:
                    logger.info(f"Fridge {fridge_id} position updated to: {position}")
                    return True
                return False
        except Error as e:
            logger.error(f"Error updating fridge position: {e}")
            return False
    
    def delete_fridge(self, fridge_id: int, user_id: int) -> bool:
        """
        Elimina frigo dal database
        
        Args:
            fridge_id: ID del frigo da eliminare
            user_id: ID utente che richiede l'eliminazione
        
        Returns:
            bool: True se eliminato, False se errore o utente non autorizzato
        """
        # Verifica che l'utente sia il proprietario del frigo
        if not self.verify_fridge_ownership(fridge_id, user_id):
            logger.warning(f"User {user_id} attempted to delete fridge {fridge_id} but is not the owner")
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "DELETE FROM Fridges WHERE ID = %s"
                cursor.execute(query, (fridge_id,))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                
                if affected > 0:
                    logger.info(f"Fridge {fridge_id} deleted by user {user_id}")
                    return True
                return False
        except Error as e:
            logger.error(f"Error deleting fridge: {e}")
            return False
    
    def verify_fridge_ownership(self, fridge_id: int, user_id: int) -> bool:
        """
        Verifica che un frigo appartenga a un utente specifico
        
        Args:
            fridge_id: ID del frigo
            user_id: ID utente da verificare
        
        Returns:
            bool: True se il frigo appartiene all'utente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT COUNT(*) 
                    FROM Fridges 
                    WHERE ID = %s AND user_ID = %s
                """
                cursor.execute(query, (fridge_id, user_id))
                result = cursor.fetchone()
                cursor.close()
                return result[0] > 0 if result else False
        except Error as e:
            logger.error(f"Error verifying fridge ownership: {e}")
            return False
    
    # ========================================
    # USER MANAGEMENT (Registration & Auth)
    # ========================================
    
    def create_user(self, email: str, password: str) -> Optional[int]:
        """
        Crea nuovo utente nel database
        
        Args:
            email: Email utente (univoca)
            password: Password in chiaro (verrà hashata)
        
        Returns:
            int: user_id dell'utente creato, None se errore o email già esistente
        """
        try:
            # Hash password prima di salvare
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO Users (email, password)
                    VALUES (%s, %s)
                """
                cursor.execute(query, (email, password_hash))
                user_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                
                logger.info(f"User {user_id} created with email: {email}")
                return user_id
        except Error as e:
            # Gestisci errore email duplicata (UNIQUE constraint)
            if e.errno == 1062:  # Duplicate entry
                logger.warning(f"Email already exists: {email}")
                return None
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Recupera utente tramite email
        
        Args:
            email: Email utente
        
        Returns:
            Dict: Dati utente (ID, email, password_hash) o None se non trovato
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = "SELECT ID, email, password FROM Users WHERE email = %s"
                cursor.execute(query, (email,))
                result = cursor.fetchone()
                cursor.close()
                return result
        except Error as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def verify_user_credentials(self, email: str, password: str) -> Optional[int]:
        """
        Verifica credenziali utente (login)
        
        Args:
            email: Email utente
            password: Password in chiaro
        
        Returns:
            int: user_id se credenziali valide, None altrimenti
        """
        try:
            user = self.get_user_by_email(email)
            
            if not user:
                logger.warning(f"Login failed: user not found ({email})")
                return None
            
            # Verifica password hash
            if check_password_hash(user['password'], password):
                logger.info(f"Login successful for user {user['ID']} ({email})")
                return user['ID']
            else:
                logger.warning(f"Login failed: wrong password ({email})")
                return None
                
        except Exception as e:
            logger.error(f"Error verifying credentials: {e}")
            return None    
    def delete_user_account(self, user_id: int) -> bool:
        """
        Elimina account utente (CASCADE elimina anche frighi e dati correlati)
        
        Args:
            user_id: ID utente da eliminare
        
        Returns:
            bool: True se eliminato con successo
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "DELETE FROM Users WHERE ID = %s"
                cursor.execute(query, (user_id,))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                
                if affected > 0:
                    logger.info(f"User {user_id} account deleted (CASCADE)")
                    return True
                return False
        except Error as e:
            logger.error(f"Error deleting user account: {e}")
            return False
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """
        Statistiche globali utente (tutti i frighi)
        
        Args:
            user_id: ID utente
        
        Returns:
            Dict: {
                'total_fridges': int,
                'total_measurements': int,
                'total_alerts': int,
                'total_products': int,
                'total_product_movements': int
            }
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Conta frighi
                cursor.execute("SELECT COUNT(*) FROM Fridges WHERE user_ID = %s", (user_id,))
                total_fridges = cursor.fetchone()[0] or 0
                
                # Conta misurazioni totali
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM Measurements m
                    JOIN Fridges f ON m.fridge_ID = f.ID
                    WHERE f.user_ID = %s
                """, (user_id,))
                total_measurements = cursor.fetchone()[0] or 0
                
                # Conta alert totali
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM Alerts a
                    JOIN Fridges f ON a.fridge_ID = f.ID
                    WHERE f.user_ID = %s
                """, (user_id,))
                total_alerts = cursor.fetchone()[0] or 0
                
                # Conta prodotti correnti (non rimossi)
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ProductsFridge pf
                    JOIN Fridges f ON pf.fridge_ID = f.ID
                    WHERE f.user_ID = %s
                      AND pf.removed_in IS NULL
                """, (user_id,))
                total_products = cursor.fetchone()[0] or 0
                
                # Conta movimenti prodotti totali
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ProductsMovements pm
                    JOIN Fridges f ON pm.fridge_ID = f.ID
                    WHERE f.user_ID = %s
                """, (user_id,))
                total_product_movements = cursor.fetchone()[0] or 0
                
                cursor.close()
                
                return {
                    'total_fridges': total_fridges,
                    'total_measurements': total_measurements,
                    'total_alerts': total_alerts,
                    'total_products': total_products,
                    'total_product_movements': total_product_movements
                }
        except Error as e:
            logger.error(f"Error getting user statistics: {e}")
            return {
                'total_fridges': 0,
                'total_measurements': 0,
                'total_alerts': 0,
                'total_products': 0,
                'total_product_movements': 0
            }