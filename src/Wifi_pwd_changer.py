import paramiko
import secrets
import string
import logging
import os
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import asyncio # Toujours nécessaire pour await dans les fonctions Telegram

# Gardez ces imports spécifiques car le script envoie des messages
import telegram
from telegram import constants

# --- Configuration du Logging ---
# Utilisez un logger avec un nom pour éviter les conflits si plusieurs scripts utilisent logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configurer les handlers uniquement si ce script est exécuté directement
if not logger.handlers: # Évite d'ajouter des handlers multiples si le script est importé
    file_handler = logging.FileHandler("wifi_password_changer.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)


class PasswordGenerator:
    """
    Générateur de mots de passe forts et aléatoires.
    """
    @staticmethod
    def generate_strong_password(length=18):
        if length < 12:
            raise ValueError("La longueur du mot de passe doit être d'au moins 12 caractères pour être forte.")

        # Define custom character sets excluding 'O' and special characters
        # Ensure 'O' is explicitly removed from uppercase letters
        uppercase_chars = ''.join(c for c in string.ascii_uppercase if c != 'O')
        lowercase_chars = string.ascii_lowercase
        digit_chars = string.digits

        # Combine all allowed characters (no special characters, no 'O')
        characters = uppercase_chars + lowercase_chars + digit_chars
        
        # Ensure at least one uppercase (not 'O'), one lowercase, and one digit
        password_chars = [
            secrets.choice(uppercase_chars), # Select from uppercase excluding 'O'
            secrets.choice(lowercase_chars),
            secrets.choice(digit_chars)
        ]
        
        # If the requested length is too short to fulfill the base requirements
        if len(password_chars) > length:
            raise ValueError("La longueur spécifiée est trop courte pour inclure tous les types de caractères requis sans 'O'.")

        # Fill the remaining length with random characters from the allowed set
        password_chars += [secrets.choice(characters) for _ in range(length - len(password_chars))]
        
        secrets.SystemRandom().shuffle(password_chars)
        
        new_password = ''.join(password_chars)
        logger.debug(f"Mot de passe généré (pour débogage) : {new_password}") 
        return new_password



class GlinetWifiManager:
    """
    Gère la connexion SSH au routeur GL.iNet et la modification
    du mot de passe Wi-Fi Guest via les commandes UCI.
    """
    def __init__(self, host, username, password, port=22, guest_section_name="guest2g"): 
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.guest_section_name = guest_section_name 
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
        logger.info(f"Initialisation du gestionnaire Wi-Fi pour {self.host}")

    def connect(self):
        try:
            logger.info(f"Tentative de connexion SSH à {self.host}:{self.port} avec l'utilisateur {self.username}...")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            logger.info("Connexion SSH établie avec succès.")
        except paramiko.AuthenticationException:
            logger.error("Échec de l'authentification SSH. Vérifiez le nom d'utilisateur et le mot de passe.")
            raise
        except paramiko.SSHException as e:
            logger.error(f"Erreur SSH lors de la connexion: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la connexion SSH: {e}")
            raise

    def execute_command(self, command):
        logger.info(f"Exécution de la commande SSH: '{command}'")
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                logger.warning(f"La commande '{command}' a retourné une erreur: {error}")
            if output:
                logger.debug(f"Output de la commande '{command}': {output}") 
            
            return output, error
        except paramiko.SSHException as e:
            logger.error(f"Erreur SSH lors de l'exécution de la commande '{command}': {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'exécution de la commande SSH '{command}': {e}")
            raise

    def set_guest_wifi_password(self, new_password):
        """
        Définit le nouveau mot de passe pour le réseau Wi-Fi Guest via UCI.
        """
        logger.info(f"Tentative de modification du mot de passe pour la section Wi-Fi Guest : {self.guest_section_name}")

        set_cmd = f"uci set wireless.{self.guest_section_name}.key='{new_password}'"
        self.execute_command(set_cmd)

        self.execute_command("uci commit wireless")

        self.execute_command("wifi reload")
        logger.info("Mot de passe Wi-Fi Guest mis à jour et configuration rechargée avec succès.")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Connexion SSH fermée.")

# --- Fonctions pour Telegram (Autonomes) ---
async def send_telegram_message(bot_token, chat_id, message): 
    """Envoie un message texte via le bot Telegram."""
    try:
        bot = telegram.Bot(token=bot_token) # Crée une nouvelle instance de Bot
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=constants.ParseMode.MARKDOWN)
        logger.info("Message Telegram envoyé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message Telegram: {e}")

async def send_telegram_photo(bot_token, chat_id, photo_bytes, caption=None): 
    """Envoie une photo via le bot Telegram."""
    try:
        bot = telegram.Bot(token=bot_token) # Crée une nouvelle instance de Bot
        bio = BytesIO()
        bio.name = 'qrcode.png'
        bio.write(photo_bytes)
        bio.seek(0)
        await bot.send_photo(chat_id=chat_id, photo=bio, caption=caption)
        logger.info("Photo Telegram envoyée avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la photo Telegram: {e}")

def generate_wifi_qrcode(ssid, password):
    """
    Génère un QR code pour la connexion Wi-Fi.
    Format: WIFI:S:<SSID>;T:WPA;P:<Password>;;
    """
    wifi_string = f"WIFI:S:{ssid};T:WPA;P:{password};;"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(wifi_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    logger.info(f"QR Code Wi-Fi généré pour SSID: {ssid}")
    return img_byte_arr

# --- LOGIQUE PRINCIPALE DU SCRIPT DE CHANGEMENT DE MOT DE PASSE ---
async def run_wifi_password_update():
    load_dotenv() 

    glinet_host = os.getenv("GLINET_HOST")
    glinet_user = os.getenv("GLINET_USER")
    glinet_password = os.getenv("GLINET_PASSWORD")
    guest_wifi_section_name = os.getenv("GUEST_WIFI_SECTION_NAME")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    guest_wifi_ssid = os.getenv("GUEST_WIFI_SSID")

    if not all([glinet_host, glinet_user, glinet_password, guest_wifi_section_name, telegram_bot_token, telegram_chat_id, guest_wifi_ssid]):
        logger.error("Veuillez configurer toutes les variables nécessaires dans votre fichier .env.")
        return False

    glinet_manager = None
    new_password = None
    try:
        new_password = PasswordGenerator.generate_strong_password(length=18)
        logger.info(f"Nouveau mot de passe généré : [hidden]")

        glinet_manager = GlinetWifiManager(
            host=glinet_host,
            username=glinet_user,
            password=glinet_password,
            guest_section_name=guest_wifi_section_name
        )
        glinet_manager.connect()
        glinet_manager.set_guest_wifi_password(new_password)
        
        logger.info("Le mot de passe du réseau Wi-Fi Guest a été mis à jour avec succès.")

        # --- Partie Telegram ---
        message_text = (
            f"*Mise à jour du mot de passe Wi-Fi Guest*\n\n"
            f"Le mot de passe du réseau *{guest_wifi_ssid}* a été changé !\n"
            f"Nouveau mot de passe : `{new_password}`\n\n"
            f"Ceci est une notification de votre système automatique de gestion Wi-Fi."
        )
        await send_telegram_message(telegram_bot_token, telegram_chat_id, message_text)
        
        # Génération et envoi du QR code
        qr_code_image_bytes = generate_wifi_qrcode(guest_wifi_ssid, new_password)
        await send_telegram_photo(telegram_bot_token, telegram_chat_id, qr_code_image_bytes,
                            caption=f"QR Code pour le réseau {guest_wifi_ssid} avec le nouveau mot de passe.")

        return True

    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue : {e}", exc_info=True)
        # Tente d'envoyer un message d'erreur si possible
        try:
            await send_telegram_message(telegram_bot_token, telegram_chat_id, f"*Erreur:* Une erreur est survenue lors du changement de mot de passe: `{e}`")
        except Exception as telegram_e:
            logger.error(f"Impossible d'envoyer le message d'erreur Telegram: {telegram_e}")
        return False
    finally:
        if glinet_manager:
            glinet_manager.close()

# --- Point d'entrée du script ---
if __name__ == "__main__":
    logger.info("--- Démarrage du script de changement de mot de passe Wi-Fi Guest ---")
    # Exécute la fonction asynchrone
    success = asyncio.run(run_wifi_password_update())
    if success:
        logger.info("--- Script terminé avec succès ---")
        exit(0)
    else:
        logger.error("--- Le script s'est terminé avec des erreurs ---")
        exit(1)