import paramiko
import logging
import os
from dotenv import load_dotenv

# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO, # Affiche les informations importantes.
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_wifi_changer.log"), # Les logs dans un fichier.
        logging.StreamHandler() # Les logs aussi dans la console.
    ]
)

class GlinetWifiManager:
    """
    Gère la connexion SSH au routeur GL.iNet et exécute les commandes UCI pour modifier le Wi-Fi.
    """
    def __init__(self, host, username, password, port=22, guest_section_name="guest2g"):
        """
        Initialise le gestionnaire avec les informations de connexion du routeur et le nom de la section Guest.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.guest_section_name = guest_section_name
        self.client = paramiko.SSHClient()
        
        # Pour simplifier la première connexion, mais pour la production, une politique plus stricte est recommandée.
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
        
        logging.info(f"Initialisation du gestionnaire Wi-Fi pour le routeur à {self.host}")

    def connect(self):
        """Tente d'établir une connexion SSH sécurisée avec le routeur."""
        try:
            logging.info(f"Tentative de connexion SSH à {self.host}:{self.port} avec l'utilisateur {self.username}...")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            logging.info("Connexion SSH établie avec succès.")
        except paramiko.AuthenticationException:
            logging.error("Échec de l'authentification SSH. Vérifiez le nom d'utilisateur et le mot de passe dans le fichier .env.")
            raise
        except paramiko.SSHException as e:
            logging.error(f"Erreur SSH lors de la connexion: {e}")
            raise
        except Exception as e:
            logging.error(f"Erreur inattendue lors de la connexion SSH: {e}")
            raise

    def execute_command(self, command):
        """Exécute une commande shell sur le routeur via la connexion SSH."""
        logging.info(f"Exécution de la commande SSH: '{command}'")
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                logging.warning(f"La commande '{command}' a retourné une erreur: {error}")
            if output:
                logging.debug(f"Output de la commande '{command}': {output}") 
            
            return output, error
        except paramiko.SSHException as e:
            logging.error(f"Erreur SSH lors de l'exécution de la commande '{command}': {e}")
            raise
        except Exception as e:
            logging.error(f"Erreur inattendue lors de l'exécution de la commande SSH '{command}': {e}")
            raise

    def set_guest_wifi_password(self, new_password):
        """
        Définit le nouveau mot de passe pour le réseau Wi-Fi Guest en utilisant les commandes UCI.
        """
        logging.info(f"Tentative de modification du mot de passe pour la section Wi-Fi Guest : {self.guest_section_name}")

        # La commande UCI utilise directement le nom de la section pour cibler la clé.
        set_cmd = f"uci set wireless.{self.guest_section_name}.key='{new_password}'"
        self.execute_command(set_cmd)

        # Applique les modifications.
        self.execute_command("uci commit wireless")

        # Recharge la configuration Wi-Fi.
        self.execute_command("wifi reload")
        logging.info("Mot de passe Wi-Fi Guest mis à jour et configuration rechargée avec succès.")

    def close(self):
        """Ferme la connexion SSH active."""
        if self.client:
            self.client.close()
            logging.info("Connexion SSH fermée.")

# --- Fonction principale d'exécution (simplifiée) ---
def run_simple_wifi_update():
    """
    Met à jour le mot de passe du Wi-Fi Guest à une valeur fixe.
    """
    load_dotenv() # Charge les variables d'environnement.

    glinet_host = os.getenv("GLINET_HOST")
    glinet_user = os.getenv("GLINET_USER")
    glinet_password = os.getenv("GLINET_PASSWORD")
    guest_wifi_section_name = os.getenv("GUEST_WIFI_SECTION_NAME") 

    if not all([glinet_host, glinet_user, glinet_password, guest_wifi_section_name]):
        logging.error("Erreur: Les variables de connexion au routeur sont manquantes dans votre fichier .env.")
        return False

    # --- NOUVEAU MOT DE PASSE FIXE ---
    fixed_password = "12345678" 
    logging.info(f"Tentative de définir le mot de passe Wi-Fi Guest à : {fixed_password}")

    glinet_manager = None
    try:
        glinet_manager = GlinetWifiManager(
            host=glinet_host,
            username=glinet_user,
            password=glinet_password,
            guest_section_name=guest_wifi_section_name 
        )

        glinet_manager.connect()
        glinet_manager.set_guest_wifi_password(fixed_password)
        
        logging.info(f"Le mot de passe du réseau Wi-Fi Guest a été mis à jour avec succès à : {fixed_password}")
        return True

    except Exception as e:
        logging.error(f"Une erreur est survenue lors du changement du mot de passe : {e}", exc_info=True) 
    finally:
        if glinet_manager:
            glinet_manager.close()
    return False

# --- Point d'entrée du script ---
if __name__ == "__main__":
    logging.info("--- Démarrage du script SIMPLE de changement de mot de passe Wi-Fi Guest ---")
    success = run_simple_wifi_update()
    if success:
        logging.info("--- Script terminé avec succès ---")
        exit(0)
    else:
        logging.error("--- Le script simple s'est terminé avec des erreurs ---")
        exit(1)