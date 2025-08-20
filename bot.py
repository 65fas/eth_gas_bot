import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables from the .env file
load_dotenv()

# Fetch all our secrets from the environment
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # Your new Telegram token

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
    # This function can take a moment, so send a "typing" action to let the user know it's working.
    await update.message.reply_chat_action(action="typing")
    gas_info = get_average_gas_price()
    await update.message.reply_text(gas_info, parse_mode='HTML') # 'HTML' allows for <b>bold</b> text.

def main():
    """Runs the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers for commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("gas", gas_command))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling() # This keeps the bot running and listening for commands.

if __name__ == "__main__":
    main()
