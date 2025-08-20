import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask  # We need to add this dependency
import threading

# Load environment variables from the .env file
load_dotenv()

# Fetch all our secrets from the environment
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# --- Create a minimal Flask app for health checks ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    """Simple health check endpoint. Render pings this to know the service is alive."""
    return "✅ Ethereum Gas Price Bot is running!", 200

# --- Reuse the same function from the Twitter bot ---
def get_average_gas_price():
    """Fetches the last 10 blocks and calculates average gas price in Gwei."""
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'proxy',
        'action': 'eth_blockNumber',
        'apikey': ETHERSCAN_API_KEY
    }
    
    response = requests.get(url, params=params)
    latest_block_hex = response.json()['result']
    latest_block = int(latest_block_hex, 16)

    gas_prices = []
    
    # Let's just get the last 10 blocks to be faster and avoid rate limits
    for i in range(10):
        block_number_hex = hex(latest_block - i)
        
        params_block = {
            'module': 'proxy',
            'action': 'eth_getBlockByNumber',
            'tag': block_number_hex,
            'boolean': 'true',
            'apikey': ETHERSCAN_API_KEY
        }
        
        block_response = requests.get(url, params=params_block)
        block_data = block_response.json().get('result', {})
        
        # Check if block and transactions exist
        if block_data and 'transactions' in block_data:
            for tx in block_data['transactions']:
                gas_price_gwei = int(tx['gasPrice'], 16) / 1e9
                gas_prices.append(gas_price_gwei)
    
    if not gas_prices:
        return "Sorry, couldn't fetch gas data at the moment. Try again later."
            
    average_gas = sum(gas_prices) / len(gas_prices)
    return f"⛽️ <b>Average Gas Price</b>\n\nOver the last 10 blocks: <code>{round(average_gas, 2)} Gwei</code>\n\n#Ethereum #Gas"

# --- Telegram-specific functions ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    welcome_text = """
    🤖 Hello! I am your Ethereum Gas Price Bot.
    
    Use the command /gas to get the current average network gas price.
    """
    await update.message.reply_text(welcome_text)

async def gas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /gas command."""
    await update.message.reply_chat_action(action="typing")
    gas_info = get_average_gas_price()
    await update.message.reply_text(gas_info, parse_mode='HTML')

def run_flask_app():
    """Runs the Flask web server on the port specified by Render."""
    port = int(os.environ.get("PORT", 10000)) # Render sets $PORT, default to 10000 for local dev
    # Run on 0.0.0.0 to make it accessible externally
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def main():
    """Runs the bot and the web server."""
    print("Starting the bot and health check server...")
    
    # --- Start the Flask server in a separate thread ---
    # This allows it to run alongside the bot without blocking.
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True  # This makes the thread exit when the main program does.
    flask_thread.start()
    
    # --- Start the Telegram Bot ---
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers for commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("gas", gas_command))
    
    # Start the bot
    print("Bot is now polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
