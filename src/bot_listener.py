import logging
import os
import asyncio
import subprocess # Pour lancer le script externe
import sys      # Pour obtenir le chemin de l'exécutable Python
from dotenv import load_dotenv

# Imports spécifiques pour le bot Telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration du Logging pour le bot listener ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot_listener.log"), # Log séparé pour le listener
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__) # Utilise le logger du module

# --- Fonctions du bot Telegram (Handlers) ---

# Fonction utilitaire pour vérifier l'ID de l'utilisateur
def is_authorized_user(chat_id, authorized_chat_id):
    return str(chat_id) == str(authorized_chat_id)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envoie un message lorsque la commande /start est émise."""
    user_id = update.effective_chat.id
    authorized_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if is_authorized_user(user_id, authorized_chat_id):
        await update.message.reply_text(
            f"Bonjour ! Je suis votre bot de gestion de mot de passe Wi-Fi Guest.\n"
            f"Utilisez la commande /changer_mdp pour déclencher le changement de mot de passe du réseau Guest."
        )
    else:
        logger.warning(f"Tentative d'accès non autorisé par l'utilisateur ID: {user_id}")
        await update.message.reply_text("Désolé, vous n'êtes pas autorisé à utiliser ce bot.")

async def change_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gère la commande /changer_mdp pour changer le mot de passe Wi-Fi."""
    user_id = update.effective_chat.id
    authorized_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not is_authorized_user(user_id, authorized_chat_id):
        logger.warning(f"Tentative de changement de mot de passe non autorisée par l'utilisateur ID: {user_id}")
        await update.message.reply_text("Désolé, vous n'êtes pas autorisé à effectuer cette action.")
        return

    await update.message.reply_text("Demande de changement de mot de passe reçue. Lancement du script de mise à jour...")
    logger.info(f"Commande /changer_mdp reçue de l'utilisateur autorisé {user_id}. Lancement du script Wifi_pwd_changer.py...")

    try:
        # Chemin absolu vers le script Wifi_pwd_changer.py
        # On utilise sys.executable pour s'assurer que le bon interpréteur Python de l'environnement virtuel est utilisé.
        script_path = os.path.join(os.path.dirname(__file__), 'Wifi_pwd_changer.py')
        
        # Lance le script en arrière-plan sans attendre sa fin.
        # stdout et stderr sont redirigés pour ne pas bloquer le bot listener.
        # Pour le débogage, vous pouvez les rediriger vers des fichiers temporaires.
        process = subprocess.Popen(
            [sys.executable, script_path], # Utilise sys.executable pour le bon environnement
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True # Pour lire en tant que texte
        )
        
        logger.info(f"Script Wifi_pwd_changer.py lancé en arrière-plan (PID: {process.pid}).")
        # Le script Wifi_pwd_changer.py enverra ses propres notifications de succès/échec.
        # Le bot listener n'a pas besoin de faire de feedback supplémentaire ici.

    except Exception as e:
        logger.error(f"Erreur lors du lancement du script Wifi_pwd_changer.py: {e}", exc_info=True)
        await update.message.reply_text(f"Erreur interne: Impossible de lancer le script de changement de mot de passe. Veuillez consulter les logs.")

# --- Fonction principale pour démarrer le bot ---
def main() -> None: # NOTE: Plus de 'async' ici
    """Démarre le bot listener."""
    load_dotenv() # Charger les variables d'environnement
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN n'est pas défini dans le fichier .env. Le bot listener ne peut pas démarrer.")
        return

    # Créer l'Application et lui passer le token de votre bot.
    application = Application.builder().token(telegram_bot_token).build()

    # Enregistrez vos gestionnaires de commandes.
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("changer_mdp", change_password_command))

    # Lancez le bot en mode polling.
    logger.info("--- Démarrage du bot Telegram listener (polling) ---")
    # run_polling bloque le thread courant et gère la boucle d'événements interne.
    application.run_polling(allowed_updates=Update.ALL_TYPES) # NOTE: Plus de 'await' ici


if __name__ == "__main__":
    main() # NOTE: Plus de 'asyncio.run()' ici