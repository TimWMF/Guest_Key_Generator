# Guest Key Generator

This tool connects via SSH to a GL.iNet Mango router to update the guest Wi-Fi password, generates a QR code for the new password, and sends it via Telegram.

## Features

- Securely generates a strong, random guest Wi-Fi password.
- Connects to a GL.iNet Mango router via SSH and updates the guest Wi-Fi password.
- Generates a QR code for easy Wi-Fi access.
- Sends the new password and QR code to a specified Telegram chat using a bot.
- Logs all actions for traceability and debugging.

## Requirements

- Python 3.8+
- A GL.iNet Mango router with SSH access enabled
- A Telegram bot token and chat ID
- The following Python packages (see `requirements.txt`):
  - `paramiko`, `python-telegram-bot`, `qrcode`, `python-dotenv`, etc.

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TimWMF/Guest_Key_Generator.git
   cd Guest_Key_Generator
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python3 -m venv venv-guest-key
   source venv-guest-key/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file in the project root with the following variables:**
   ```env
   GLINET_HOST=your_router_ip
   GLINET_USER=your_router_username
   GLINET_PASSWORD=your_router_password
   GUEST_WIFI_SECTION_NAME=guest2g
   GUEST_WIFI_SSID=YourGuestSSID
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

   **Note:** Never commit your `.env` file. It is already included in `.gitignore`.

## Usage

### 1. Start the Telegram Bot Listener

This script listens for commands on Telegram and triggers the password change process.

```bash
python src/bot_listener.py
```

- Use `/start` in your Telegram chat to check the bot is running.
- Use `/changer_mdp` to trigger a guest Wi-Fi password change.

### 2. Manual Password Change (for testing)

You can run the password changer directly for testing:

```bash
python src/Wifi_pwd_changer.py
```

## Security

- **No secrets are stored in the codebase.** All sensitive information is loaded from environment variables.
- **.env and log files are excluded from version control** via `.gitignore`.

## License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.

---

## About

Code that generates a guest key for a GL.iNet Mango and sends the updated code via Telegram bot with a QR Code.
