import os
import socket
import json
import requests
import re
import time
from datetime import datetime, timedelta
import sys
import base64  # For basic encryption of stored passwords
import codecs
from colorama import init, Fore, Style

def hit_enter_to_continue():
    """Pause execution until user hits enter"""
    input(Fore.YELLOW + "\nPress Enter to continue..." + Style.RESET_ALL)

# Check if running on Termux
IS_TERMUX = os.path.exists('/data/data/com.termux/files/usr/bin/termux-setup-storage')

# Handle UTF-8 encoding for Termux
if IS_TERMUX:
    sys.stdout.reconfigure(encoding='utf-8')

# Initialize color handling
if not IS_TERMUX:
    init()
else:
    # Create dummy color classes for Termux
    class DummyColor:
        def __getattr__(self, name):
            return ''
    Fore = DummyColor()
    Style = DummyColor()

# Handle encoding for Termux
if IS_TERMUX:
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Import telebot only if not on Termux
if not IS_TERMUX:
    import telebot
    from telebot.apihelper import ApiTelegramException
else:
    # Create dummy telebot for Termux
    class DummyTelebot:
        def __init__(self, token):
            pass
        
        def send_message(self, chat_id, text, parse_mode=None):
            print(f"Telegram message would be sent to {chat_id}: {text}")
            return True
    
    telebot = type('', (), {'TeleBot': DummyTelebot})()
    ApiTelegramException = Exception

# Remove msvcrt dependency (Windows-specific)
# import msvcrt  # For keyboard input detection

def get_application_path():
    """Get the path where the application is running from (works in both script and exe)"""
    try:
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle (exe)
            app_path = os.path.dirname(sys.executable)
        else:
            # If the application is run as a script
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        # Ensure app_path is a valid directory that exists
        if not os.path.exists(app_path):
            os.makedirs(app_path, exist_ok=True)
            
        return app_path
    except Exception as e:
        # Fallback to current directory if there's an error
        print(Fore.RED + f"Error determining application path: {str(e)}" + Style.RESET_ALL)
        fallback_path = os.getcwd()
        print(Fore.YELLOW + f"Using fallback path: {fallback_path}" + Style.RESET_ALL)
        return fallback_path

# Constants and paths
APP_PATH = get_application_path()

# Data directory setup
def setup_data_directory():
    if IS_TERMUX:
        # Use Termux home directory
        base_dir = os.path.expanduser('~')
    else:
        # Use standard application directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    data_dir = os.path.join(base_dir, 'GrowupSignalsData')
    
    # Create data directory if it doesn't exist
    try:
        os.makedirs(data_dir, exist_ok=True)
        
        # Test write access
        test_file = os.path.join(data_dir, '.test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        return data_dir
    except (OSError, IOError) as e:
        print(f"Error setting up data directory: {e}")
        # Fallback to current directory
        return os.getcwd()

# Set up data paths
DATA_DIR = setup_data_directory()
CREDENTIALS_FILE = os.path.join(DATA_DIR, 'credentials.json')
DEFAULT_SETTINGS_FILE = os.path.join(DATA_DIR, 'default_settings.json')
AUTO_BOT_SETTINGS_FILE = os.path.join(DATA_DIR, 'auto_bot_settings.json')

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def save_credentials(credentials):
    try:
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False

def change_password(username, old_password, new_password):
    """Change user password"""
    if username in USERS and USERS[username]["password"] == old_password:
        USERS[username]["password"] = new_password
        # If credentials are saved, update saved password
        creds = load_credentials()
        if creds.get("username") == username and creds.get("save_login"):
            save_credentials(creds)
        return True
    return False

def login():
    """Login function with expiration check and saved credentials support."""
    # Load saved credentials
    creds = load_credentials()
    saved_username = creds.get("username")
    saved_password = creds.get("password")
    
    # If we have saved credentials, try them first
    if saved_username and saved_password and creds.get("save_login"):
        try:
            if saved_username in USERS and USERS[saved_username]["password"] == saved_password:
                # Check if the user session has expired
                expire_time = USERS[saved_username]["expire_time"]
                current_time = datetime.now()

                if current_time > expire_time:
                    print(Fore.RED + "\nYour license has expired. Join @growupbinarytrading for more updates.\n" + Style.RESET_ALL)
                    hit_enter_to_continue()
                    return None
                
                print(Fore.GREEN + f"\nAutomatic login successful! Welcome back, {saved_username}!" + Style.RESET_ALL)
                time.sleep(1)  # Short pause to show the message
                return saved_username, expire_time
            else:
                # If saved credentials are invalid, remove them
                print(Fore.YELLOW + "\nSaved credentials are invalid. Please login again." + Style.RESET_ALL)
                if os.path.exists(CREDENTIALS_FILE):
                    try:
                        os.remove(CREDENTIALS_FILE)
                    except:
                        pass
        except Exception as e:
            print(Fore.RED + f"\nError during auto-login: {str(e)}" + Style.RESET_ALL)
            # Reset credentials file in case of error
            if os.path.exists(CREDENTIALS_FILE):
                try:
                    os.remove(CREDENTIALS_FILE)
                except:
                    pass
    
    # If no saved credentials or they're invalid, ask for login
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            username = input(Fore.YELLOW + "Enter username: " + Style.RESET_ALL).strip()
            password = input(Fore.YELLOW + "Enter password: " + Style.RESET_ALL).strip()

            if username in USERS and USERS[username]["password"] == password:
                # Check if the user session has expired
                expire_time = USERS[username]["expire_time"]
                current_time = datetime.now()

                if current_time > expire_time:
                    print(Fore.RED + "\nYour license has expired. Join @growupbinarytrading for more updates.\n" + Style.RESET_ALL)
                    hit_enter_to_continue()
                    return None

                # Ask to save credentials only for manual login
                save_login = input(Fore.YELLOW + "Save login credentials for next time? (y/n): " + Style.RESET_ALL).strip().lower() == 'y'
                if save_login:
                    if save_credentials({"username": username, "password": password, "save_login": save_login}):
                        print(Fore.GREEN + "Credentials saved successfully!" + Style.RESET_ALL)
                    else:
                        print(Fore.YELLOW + "Could not save credentials, but login successful." + Style.RESET_ALL)
                    time.sleep(1)  # Short pause to show the message
                return username, expire_time
            else:
                print(Fore.RED + f"\nInvalid username or password. Attempt {attempt+1}/{max_attempts}\n" + Style.RESET_ALL)
                if attempt < max_attempts - 1:
                    continue
        except Exception as e:
            print(Fore.RED + f"\nError during login: {str(e)}" + Style.RESET_ALL)
            if attempt < max_attempts - 1:
                print("Please try again.")
                continue
    
    print(Fore.RED + "\nToo many failed attempts. Please try again later.\n" + Style.RESET_ALL)
    hit_enter_to_continue()
    return None

def show_copyright():
    print("""
    *************************************************************
    Copyright 2024 Growup Binarytrading. All Rights Reserved.
    This software is protected by copyright law and international treaties.
    Unauthorized use, reproduction, or distribution of this software is prohibited.
    For more information Visit 
    *************************************************************
    ADMIN TELEGRAM : @KaifSaifi001
    Telegram Channel : @GrowupBinaryTrading
    Bot Telegram Channel : @GrowupBinaryBot
    Support Team : @Team_GrowUp
    *************************************************************
    License: MIT License
    This program is licensed under the MIT License.
    *************************************************************
    """)

def display_banner():
    print(Fore.GREEN + """
 ==========================================================================================
|    █████████  ███████████     ███████   █████   ███   █████    █████  ████████████████    |
|   ███░░░░░███░░███░░░░░███  ███░░░░░███░░███   ░███  ░░███    ░░███  ░░███░░███░░░░░███   |
|  ███     ░░░  ░███    ░███ ███     ░░███░███   ░███   ░███     ░███   ░███ ░███    ░███   |
| ░███          ░██████████ ░███      ░███░███   ░███   ░███     ░███   ░███ ░██████████    | 
| ░███    █████ ░███░░░░░███░███      ░███░███   ░███   ░███     ░███   ░███ ░███░░░░░░     |
| ░░███  ░░███  ░███    ░███░░███     ███  ░░░█████░█████░       ░███   ░███ ░███           |
|  ░░█████████  █████   █████░░░███████░     ░░███ ░░███         ░░████████  █████  v2      |
|   ░░░░░░░░░  ░░░░░   ░░░░░   ░░░░░░░        ░░░   ░░░           ░░░░░░░░  ░░░░░           |        
 ===========================================================================================

╔══════════════════════════════════════════════════════════════════════════════════════════╗
                                   TELEGRAM : @GROWUPBINARYTRADING                                                                                                                    
                       SIGNAL GENERATOR V2 TOOL FOR BINARY TRADING
                                         Powered by GROWUP TRADING                                                                                                                                      
     Current Features.                                                                                           
   - Signal Generation with Advance Strategies                                                     
   - Blackout Signals + Normal 
   - Send Signals to Telegram Channels 
   - Multiple Timezone Support                                                                                          
   - Auto Login
   - Advance Filters                                                                                                 
   - Quotex OTC + Live Stocks                                                               
   - 100% Real API                                                                                             
╚══════════════════════════════════════════════════════════════════════════════════════════╝
""")


# List of currency pairs (OTC)
currency_pairs = [
    ("AUDCAD_otc", "AUD/CAD (OTC)"),
    ("AUDCHF_otc", "AUD/CHF (OTC)"),
    ("AUDJPY_otc", "AUD/JPY (OTC)"),
    ("AUDNZD_otc", "AUD/NZD (OTC)"),
    ("AUDUSD_otc", "AUD/USD (OTC)"),
    ("EURUSD_otc", "EUR/USD (OTC)"),
    ("EURGBP_otc", "EUR/GBP (OTC)"),
    ("EURJPY_otc", "EUR/JPY (OTC)"),
    ("EURNZD_otc", "EUR/NZD (OTC)"),
    ("EURSGD_otc", "EUR/SGD (OTC)"),
    ("EURAUD_otc", "EUR/AUD (OTC)"),
    ("EURCAD_otc", "EUR/CAD (OTC)"),
    ("EURCHF_otc", "EUR/CHF (OTC)"),
    ("GBPUSD_otc", "GBP/USD (OTC)"),
    ("GBPAUD_otc", "GBP/AUD (OTC)"),
    ("GBPCAD_otc", "GBP/CAD (OTC)"),
    ("GBPCHF_otc", "GBP/CHF (OTC)"),
    ("GBPJPY_otc", "GBP/JPY (OTC)"),
    ("GBPNZD_otc", "GBP/NZD (OTC)"),
    ("NZDCAD_otc", "NZD/CAD (OTC)"),
    ("NZDCHF_otc", "NZD/CHF (OTC)"),
    ("NZDJPY_otc", "NZD/JPY (OTC)"),
    ("USDCAD_otc", "USD/CAD (OTC)"),
    ("USDCHF_otc", "USD/CHF (OTC)"),
    ("USDCOP_otc", "USD/COP (OTC)"),
    ("USDDZD_otc", "USD/DZD (OTC)"),
    ("USDEGP_otc", "USD/EGP (OTC)"),
    ("USDIDR_otc", "USD/IDR (OTC)"),
    ("USDINR_otc", "USD/INR (OTC)"),
    ("USDJPY_otc", "USD/JPY (OTC)"),
    ("USDMXN_otc", "USD/MXN (OTC)"),
    ("USDNGN_otc", "USD/NGN (OTC)"),
    ("USDPHP_otc", "USD/PHP (OTC)"),
    ("USDPKR_otc", "USD/PKR (OTC)"),
    ("USDTRY_otc", "USD/TRY (OTC)"),
    ("USDZAR_otc", "USD/ZAR (OTC)"),
]

# List of stocks and indices (non-OTC)
stocks_and_indices = [
    ("AXJAUD", "S&P/ASX 200"),
    ("AXP_otc", "American Express (OTC)"),
    ("BA_otc", "Boeing Company (OTC)"),
    ("BRLUSD_otc", "USD/BRL (OTC)"),
    ("BTCUSD_otc", "Bitcoin (OTC)"),
    ("CADCHF_otc", "CAD/CHF (OTC)"),
    ("CADJPY_otc", "CAD/JPY (OTC)"),
    ("CHFJPY_otc", "CHF/JPY (OTC)"),
    ("CHIA50", "FTSE China A50 Index"),
    ("DJIUSD", "Dow Jones"),
    ("F40EUR", "CAC 40"),
    ("FB_otc", "FACEBOOK INC (OTC)"),
    ("FTSGBP", "FTSE 100"),
    ("HSIHKD", "Hong Kong 50"),
    ("IBXEUR", "IBEX 35"),
    ("INTC_otc", "Intel (OTC)"),
    ("IT4EUR", "Italy 40"),
    ("JNJ_otc", "Johnson & Johnson (OTC)"),
    ("JPXJPY", "Nikkei 225"),
    ("MCD_otc", "McDonald's (OTC)"),
    ("MSFT_otc", "Microsoft (OTC)"),
    ("NDXUSD", "NASDAQ 100"),
    ("PFE_otc", "Pfizer Inc (OTC)"),
    ("STXEUR", "EURO STOXX 50"),
    ("UKBrent_otc", "UKBrent (OTC)"),
    ("USCrude_otc", "USCrude (OTC)"),
    ("XAGUSD_otc", "Silver (OTC)"),
    ("XAUUSD_otc", "Gold (OTC)"),
]

def display_pairs():
    """Display available currency pairs and stocks"""
    print(Fore.GREEN + "Available Currency Pairs (OTC):" + Style.RESET_ALL)
    for pair, name in currency_pairs:
        print(f"{Fore.YELLOW}{pair:<15} {Fore.CYAN}--> {name}")
    
    print(Fore.GREEN + "\nAvailable Stocks and Indices:" + Style.RESET_ALL)
    for stock, name in stocks_and_indices:
        print(f"{Fore.YELLOW}{stock:<15} {Fore.CYAN}--> {name}")

# Users Dictionary with expiration time
USERS = {
    "A": {
        "password": "A",
        "expire_time": datetime(2050, 12, 1, 00, 00)  # Set expiration date/time here
    },
    "growupmember": {
        "password": "quotex",
        "expire_time": datetime(2050, 1, 1, 00, 00)
    }
}

def _get_url():
    p1 = 'aHR0cHM6Ly9hbGx0cmFkaW5nYXBpLmNvbS9zaWduYWxfbGlzdF9nZW4vcXhfc2lnbmFsLmpz'
    import base64
    return base64.b64decode(p1).decode()

API_URL = _get_url()

# Pastebin raw URLs
PASTEBIN_MAINTENANCE_URL = "https://pastebin.com/raw/eqmdkZ0E"

def check_maintenance_mode():
    """Check if the software is in maintenance mode"""
    try:
        response = requests.get(PASTEBIN_MAINTENANCE_URL)
        if response.status_code == 200:
            maintenance_data = response.text.strip()
            if "PANNEL ON/OFF" in maintenance_data:
                status = maintenance_data.split("=")[1].strip().replace('"', '')
                if status.upper() != "ON":
                    print(Fore.RED + "\n⚠️ Software is currently under maintenance.")
                    print("Please try again later or contact @Team_GrowUp for support." + Style.RESET_ALL)
                    print(Fore.YELLOW + "\nExiting in:", end=" ")
                    for i in range(5, 0, -1):
                        print(f"{i}...", end=" ", flush=True)
                        time.sleep(1)
                    print(Style.RESET_ALL)
                    return False
            return True
        else:
            # If can't check maintenance status, allow usage
            return True
    except requests.RequestException:
        # If can't connect, allow usage
        return True

def check_mac_in_pastebin(mac_address):
    return True  # Always return True to bypass MAC check

# Helper Functions
def is_connected():
    """Check if the system is connected to the internet."""
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False

def check_session(username):
    """Check if the user's session is still valid."""
    current_time = datetime.now()
    expire_time = USERS[username]["expire_time"]

    if current_time > expire_time:
        print(Fore.RED + "\nYour license has expired. Join @growupbinarytrading for more updates.\n" + Style.RESET_ALL)
        return False
    return True

def set_expiration():
    """Manually set expiration date and time for a user."""
    username = input(Fore.YELLOW + "Enter username to set expiration: " + Style.RESET_ALL).strip()
    if username in USERS:
        date_str = input(Fore.YELLOW + "Enter expiration date (YYYY-MM-DD): " + Style.RESET_ALL).strip()
        time_str = input(Fore.YELLOW + "Enter expiration time (HH:MM): " + Style.RESET_ALL).strip()
        try:
            expiration = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            USERS[username]["expire_time"] = expiration
            print(Fore.GREEN + f"\nExpiration time for {username} set to: {expiration}\n" + Style.RESET_ALL)
        except ValueError:
            print(Fore.RED + "\nInvalid date or time format. Please try again.\n" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\nUsername not found.\n" + Style.RESET_ALL)

# Timezone options
TIMEZONE_OPTIONS = {
    "1": {"name": "India", "offset": -30, "display": "UTC +5:30"},  # 30 mins behind Bangladesh
    "2": {"name": "Bangladesh", "offset": 0, "display": "UTC +6:00"},  # Reference timezone
    "3": {"name": "Pakistan", "offset": -60, "display": "UTC +5:00"}  # 1 hour behind Bangladesh
}

def convert_to_indian_time(signal_time):
    """Converts UTC+6:00 (Bangladesh) time to selected timezone"""
    global DEFAULT_SETTINGS
    
    # Parse the input time (which is in UTC+6:00)
    bd_time = datetime.strptime(signal_time, "%H:%M")
    bd_time = bd_time.replace(year=2025, month=1, day=16)  # Use current date
    
    # Get timezone offset in minutes relative to Bangladesh time
    try:
        timezone_choice = DEFAULT_SETTINGS.get("timezone", "1")  # Default to India if not set
        offset_minutes = TIMEZONE_OPTIONS[timezone_choice]["offset"]
    except (KeyError, TypeError):
        timezone_choice = "1"  # Fallback to India
        offset_minutes = TIMEZONE_OPTIONS["1"]["offset"]
        DEFAULT_SETTINGS["timezone"] = timezone_choice  # Set default
    
    # Convert time by applying the offset relative to Bangladesh time
    converted_time = bd_time + timedelta(minutes=offset_minutes)
    return converted_time.strftime("%H:%M")

def print_table(signals, api_date):
    """Print the signals in a formatted table"""
    try:
        timezone_choice = DEFAULT_SETTINGS.get("timezone", "1")
        timezone_display = TIMEZONE_OPTIONS[timezone_choice]["display"]
        country_name = TIMEZONE_OPTIONS[timezone_choice]["name"]
    except (KeyError, TypeError):
        timezone_choice = "1"  # Fallback to India
        timezone_display = TIMEZONE_OPTIONS["1"]["display"]
        country_name = TIMEZONE_OPTIONS["1"]["name"]
        DEFAULT_SETTINGS["timezone"] = timezone_choice  # Set default
    
    print(Fore.GREEN + " ")
    print(Fore.CYAN + "╔════════✰═══════════╗" + Style.RESET_ALL)
    print(Fore.YELLOW + f"TIMEZONE: {timezone_display} ({country_name})" + Style.RESET_ALL)
    print(Fore.CYAN + "@Growupbinarytrading" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Date: {api_date}" + Style.RESET_ALL)
    print(Fore.GREEN + "  ONLY FOR QUOTEX" + Style.RESET_ALL)
    print(Fore.CYAN + "╚════════✰═══════════╝" + Style.RESET_ALL)
    print(Fore.GREEN + " ")

    # Print the table headers
    print(Fore.GREEN + "+------------+-------------+-------------+" + Style.RESET_ALL)
    print(f"| {Fore.YELLOW}Quotex Pair{Style.RESET_ALL} | {Fore.YELLOW}Time{Style.RESET_ALL} | {Fore.YELLOW}Action{Style.RESET_ALL} |")
    print(Fore.GREEN + "+------------+-------------+-------------+" + Style.RESET_ALL)

    # Print the signal data in table format
    for signal in signals:
        pair = signal['pair']
        time = signal['time']
        action = signal['action']
        color = Fore.GREEN if action == "CALL" else Fore.RED

        print(f"| {pair:<12} | {time} | {color}{action}{Style.RESET_ALL} |")
    
    print(Fore.GREEN + "+------------+-------------+-------------+" + Style.RESET_ALL)
    print(Fore.GREEN + " " + Style.RESET_ALL)
    print(Fore.RED + " RULE : IF ENTRY CANDEL GAPUP OR GAP DOWN TO MUCH THAN DON'T TAKE TRADE. " + Style.RESET_ALL)

def send_to_telegram(message, signal_data=None, send_before=None):
    """Send signal message to Telegram channel"""
    try:
        # Load auto bot settings for customized message format
        auto_settings = load_auto_bot_settings()
        
        bot_token = DEFAULT_SETTINGS.get('telegram_bot_token', '')
        channel = DEFAULT_SETTINGS.get('telegram_channel', '')
        
        if not bot_token or not channel:
            print(Fore.RED + "\nError: Telegram settings not configured." + Style.RESET_ALL)
            return False
            
        # Base URL for Telegram Bot API
        base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # If we have signal data, send image with detailed caption
        if signal_data:
            action = signal_data.get('action', '').upper()
            signal_time = signal_data.get('time', '')
            pair = signal_data.get('pair', '')
            percentage = signal_data.get('percentage', DEFAULT_SETTINGS['min_percentage'])
            
            # Calculate timezone
            tz_option = TIMEZONE_OPTIONS.get(DEFAULT_SETTINGS['timezone'], TIMEZONE_OPTIONS['1'])
            tz_display = tz_option['display']  # This will be in format "UTC +5:30"
            
            # Get customized settings from auto bot settings
            alert_title = auto_settings.get('alert_title', 'UPCOMING SIGNAL ALERT')
            call_emoji = auto_settings.get('call_emoji', '🟢')
            put_emoji = auto_settings.get('put_emoji', '🔴')
            martingale_steps = auto_settings.get('martingale_steps', '1 Step')
            signal_rules = auto_settings.get('signal_rules', ["If the previous candle is weak, the signal should be avoided", "Follow Trend"])
            bot_signature = auto_settings.get('bot_signature', 'Generated by GrowUp Future Signals')
            
            image_url = ""
            emoji = ""
            if action == "CALL":
                image_url = auto_settings.get('call_image_url', 'https://i.ibb.co/Q8L6mk5/Growth.png')
                emoji = call_emoji
            elif action == "PUT":
                image_url = auto_settings.get('put_image_url', 'https://i.ibb.co/1vsFM2N/Growth-1.png')
                emoji = put_emoji
                
            if image_url:
                # Build rules text
                rules_text = ""
                for rule in signal_rules:
                    rules_text += f"{rule}\n"
                
                caption = f"""
{emoji} <b>{alert_title}</b> {emoji}

> <b>⏰ Execution Time: {signal_time} ({tz_display})</b>
> <b>📊 Pair: {pair}</b>
> <b>🔃 Auto Martingle: {martingale_steps}</b>
> <b>📈 Action: {action}</b>

⚠️ <i>Get ready! Signal will execute in {int(send_before)} minutes!</i>
‼️ RULE ‼️ 
{rules_text}
<b>🤖 {bot_signature}</b>"""

                # Send image with caption
                params = {
                    'chat_id': channel,
                    'photo': image_url,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.get(f"{base_url}/sendPhoto", params=params)
                if response.json().get('ok'):
                    return True
                else:
                    print(Fore.RED + f"\nError sending image to Telegram: {response.text}" + Style.RESET_ALL)
                    return False
            
        # If no signal data, just send a text message
        elif message:
            params = {
                'chat_id': channel,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.get(f"{base_url}/sendMessage", params=params)
            if response.json().get('ok'):
                return True
            else:
                print(Fore.RED + f"\nError sending message to Telegram: {response.text}" + Style.RESET_ALL)
                return False
                
        return True
            
    except Exception as e:
        print(Fore.RED + f"\nError sending signal to Telegram: {str(e)}" + Style.RESET_ALL)
        return False

def save_signals_to_file(signals, api_date):
    """Save signals to a text file with Telegram-like formatting"""
    try:
        timezone_choice = DEFAULT_SETTINGS.get("timezone", "1")
        timezone_info = TIMEZONE_OPTIONS[timezone_choice]
        
        # Create Signals directory in the same folder as the executable/script
        signals_dir = os.path.join(APP_PATH, "Signals")
        os.makedirs(signals_dir, exist_ok=True)
        
        # Get current time for filename
        current_time = datetime.now().strftime("%H-%M-%S")
        
        # Get unique pairs from actual signals
        unique_pairs = "_".join(sorted(set(signal['pair'] for signal in signals)))
        filename = f"{unique_pairs}_{api_date.replace('/', '_')}_{current_time}.txt"
        filepath = os.path.join(signals_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"""╔════════✰═══════════╗
⏱️ TIMEZONE: {timezone_info['display']}
🇮🇳 @Growupbinarytrading
  Date: {api_date}
  Time: {current_time}
  Pairs: {unique_pairs.replace('_', ', ')}
 ‼️ONLY FOR QUOTEX‼️
╚════════✰═══════════╝

+------------+-------------+-------------+
| Quotex Pair | Time | Action |
+------------+-------------+-------------+""")

            # Write signals
            for signal in signals:
                pair = signal['pair']
                time = signal['time']
                action = signal['action']
                
                # Add arrow if action is CALL or PUT
                if action in ["CALL", "PUT"]:
                    action_symbol = "🔼" if action == "CALL" else "🔽"
                    action_text = f"{action_symbol} {action}"
                else:
                    action_text = action
                
                f.write(f"\n| {pair:<12} | {time:<11} | {action_text:<6} |")

            # Write footer
            f.write("""
+------------+-------------+-------------+

‼️ RULE ‼️ 
If the previous candle is weak, the signal should be avoided
Follow Trend

🔗 Join @GrowupBinaryTrading
📱 Support: @Team_GrowUp""")
            
        print(Fore.GREEN + f"\n✅ Signals saved to Signals/{filename} successfully!")
        print(Fore.CYAN + f"📂 File location: {filepath}" + Style.RESET_ALL)
        return True
    except Exception as e:
        print(Fore.RED + f"\n❌ Error saving signals to file: {str(e)}" + Style.RESET_ALL)
        return False

def fetch_signals_with_settings(auto_settings, silent_mode=True):
    """Fetch signals using the provided settings"""
    global DEFAULT_SETTINGS
    original_settings = DEFAULT_SETTINGS.copy()
    
    try:
        # Override settings temporarily
        temp_settings = original_settings.copy()
        temp_settings.update({
            'pairs': auto_settings['pairs'],
            'mode': auto_settings['mode'],
            'min_percentage': auto_settings['min_percentage'],
            'filter': auto_settings['filter'],
            'separate_trend': auto_settings['separate_trend'],
            'timezone': auto_settings['timezone']
        })
        DEFAULT_SETTINGS = temp_settings
        
        return fetch_signals(return_signals=True, silent_mode=silent_mode)
    finally:
        # Always restore original settings
        DEFAULT_SETTINGS = original_settings

def fetch_signals(return_signals=False, silent_mode=False):
    """Fetch signals from API"""
    # Initialize params with default settings
    params = {
        "pairs": DEFAULT_SETTINGS["pairs"],
        "start_time": DEFAULT_SETTINGS["start_time"],
        "end_time": DEFAULT_SETTINGS["end_time"],
        "days": DEFAULT_SETTINGS["days"],
        "mode": DEFAULT_SETTINGS["mode"],
        "min_percentage": DEFAULT_SETTINGS["min_percentage"],
        "filter": DEFAULT_SETTINGS["filter_value"],
        "separate": DEFAULT_SETTINGS["separate"]
    }

    if not silent_mode:
        print(Fore.CYAN + "\nCurrent Default Settings:" + Style.RESET_ALL)
        print(Fore.YELLOW + f"Pairs: {DEFAULT_SETTINGS['pairs']}")
        print(Fore.YELLOW + f"Start Time: {DEFAULT_SETTINGS['start_time']}")
        print(Fore.YELLOW + f"End Time: {DEFAULT_SETTINGS['end_time']}")
        print(Fore.YELLOW + f"Days: {DEFAULT_SETTINGS['days']}")
        print(Fore.YELLOW + f"Mode: {DEFAULT_SETTINGS['mode']}")
        print(Fore.YELLOW + f"Min Percentage: {DEFAULT_SETTINGS['min_percentage']}")
        print(Fore.YELLOW + f"Filter Value: {DEFAULT_SETTINGS['filter_value']}")
        print(Fore.YELLOW + f"Separate: {DEFAULT_SETTINGS['separate']}")
        print(Fore.YELLOW + f"Timezone: {TIMEZONE_OPTIONS[DEFAULT_SETTINGS['timezone']]['name']} ({TIMEZONE_OPTIONS[DEFAULT_SETTINGS['timezone']]['display']})\n")

        use_default = input(Fore.YELLOW + "Use default settings? (y/n):\nEnter choice: " + Style.RESET_ALL).strip().lower()
        
        # If user doesn't want to use defaults, ask for custom settings
        if use_default != 'y':
            print(Fore.CYAN + "\nEnter custom settings (press Enter to keep default value):" + Style.RESET_ALL)
            params["pairs"] = input(Fore.YELLOW + f"Enter pairs (default: {DEFAULT_SETTINGS['pairs']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["pairs"]
            params["start_time"] = input(Fore.YELLOW + f"Enter start time (default: {DEFAULT_SETTINGS['start_time']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["start_time"]
            params["end_time"] = input(Fore.YELLOW + f"Enter end time (default: {DEFAULT_SETTINGS['end_time']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["end_time"]
            params["days"] = input(Fore.YELLOW + f"Enter number of days (default: {DEFAULT_SETTINGS['days']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["days"]
            params["mode"] = input(Fore.YELLOW + f"Enter mode (Blackout/Normal) (default: {DEFAULT_SETTINGS['mode']}): " + Style.RESET_ALL).strip().lower() or DEFAULT_SETTINGS["mode"]
            params["min_percentage"] = input(Fore.YELLOW + f"Enter minimum percentage (default: {DEFAULT_SETTINGS['min_percentage']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["min_percentage"]
            params["filter"] = input(Fore.YELLOW + f"Enter filter value (1 Human or 2 Future Trend) (default: {DEFAULT_SETTINGS['filter_value']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["filter_value"]
            params["separate"] = input(Fore.YELLOW + f"Separate results by trend? (1 for yes) (default: {DEFAULT_SETTINGS['separate']}): " + Style.RESET_ALL).strip() or DEFAULT_SETTINGS["separate"]
            
            # Ask if user wants to save these as new defaults
            save_as_default = input(Fore.YELLOW + "\nSave these settings as new defaults? (y/n): " + Style.RESET_ALL).strip().lower()
            if save_as_default == 'y':
                DEFAULT_SETTINGS.update({
                    "pairs": params["pairs"],
                    "start_time": params["start_time"],
                    "end_time": params["end_time"],
                    "days": params["days"],
                    "mode": params["mode"],
                    "min_percentage": params["min_percentage"],
                    "filter_value": params["filter"],
                    "separate": params["separate"]
                })
                with open(DEFAULT_SETTINGS_FILE, 'w') as f:
                    json.dump(DEFAULT_SETTINGS, f, indent=4)
                print(Fore.GREEN + "\nSettings saved as new defaults!" + Style.RESET_ALL)

    if not silent_mode:
        print(Fore.CYAN + "\nFetching signals..." + Style.RESET_ALL)

    if not is_connected():
        if not silent_mode:
            print(Fore.RED + "\nError: No internet connection. Please check your network and try again." + Style.RESET_ALL)
        return None

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()

        if "Signals:" in response.text:
            signal_lines = response.text.split("\n")
            signals = []

            # Extract the date from the raw response
            date_match = re.search(r"Date: (\d{2}/\d{2}/\d{4})", response.text)
            api_date = date_match.group(1) if date_match else "Unknown Date"

            # Process each line to extract signals
            for line in signal_lines:
                if "PA～" in line:
                    parts = line.strip().split("～")
                    if len(parts) >= 4:  # Make sure we have all parts
                        pair = parts[1]
                        time_utc = parts[2]
                        signal_type = parts[3]
                        
                        # Convert to selected timezone
                        time_ist = convert_to_indian_time(time_utc)

                        if "blackout" in DEFAULT_SETTINGS["mode"].lower():
                            signals.append({
                                "pair": pair,
                                "time": time_ist,
                                "action": "N/A",
                                "percentage": DEFAULT_SETTINGS["min_percentage"]
                            })
                        else:
                            action = signal_type.upper() if signal_type else "N/A"
                            signals.append({
                                "pair": pair,
                                "time": time_ist,
                                "action": action,
                                "percentage": DEFAULT_SETTINGS["min_percentage"]
                            })

            if signals:
                if return_signals:
                    return signals
                    
                if not silent_mode:
                    print_table(signals, api_date)
                    save_signals_to_file(signals, api_date)
                
                return signals
            else:
                if not silent_mode:
                    print(Fore.RED + "No signals found that meet the criteria." + Style.RESET_ALL)
                return None
        else:
            if not silent_mode:
                print(Fore.RED + "No signals found in the response." + Style.RESET_ALL)
            return None

    except requests.exceptions.RequestException as e:
        if not silent_mode:
            print(Fore.RED + f"Error occurred while fetching signals: {str(e)}" + Style.RESET_ALL)
        return None

def auto_send_signals():
    """Automatically send signals to Telegram 1 minute before execution time"""
    if not DEFAULT_SETTINGS.get('telegram_bot_token') or not DEFAULT_SETTINGS.get('telegram_channel'):
        print(Fore.RED + "\nError: Telegram settings not configured. Please set them in Default Settings first." + Style.RESET_ALL)
        hit_enter_to_continue()
        return

    # Load auto bot settings
    auto_settings = load_auto_bot_settings()
    send_before = float(auto_settings.get('send_before', '1'))  # Minutes before to send signal
    
    def display_settings():
        """Display current settings"""
        print(Fore.CYAN + "\n📊 Current Auto Bot Settings:" + Style.RESET_ALL)
        print(Fore.YELLOW + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + Style.RESET_ALL)
        print(Fore.CYAN + "Trading Settings:" + Style.RESET_ALL)
        print(f"• Pair(s): {Fore.YELLOW}{auto_settings['pairs']}{Style.RESET_ALL}")
        print(f"• Trading Hours: {Fore.YELLOW}{auto_settings['start_time']} - {auto_settings['end_time']}{Style.RESET_ALL}")
        print(f"• Days Ahead: {Fore.YELLOW}{auto_settings['days']}{Style.RESET_ALL}")
        print(f"• Mode: {Fore.YELLOW}{auto_settings['mode'].title()}{Style.RESET_ALL}")
        print(f"• Min Percentage: {Fore.YELLOW}{auto_settings['min_percentage']}%{Style.RESET_ALL}")
        print(f"• Filter: {Fore.YELLOW}{'Human' if auto_settings['filter'] == '1' else 'Future Trend'}{Style.RESET_ALL}")
        print(f"• Separate Trends: {Fore.YELLOW}{'Yes' if auto_settings['separate_trend'] == '1' else 'No'}{Style.RESET_ALL}")
        
        print(Fore.CYAN + "\nBot Settings:" + Style.RESET_ALL)
        print(f"• Send Signal: {Fore.YELLOW}{send_before} minute(s) before execution{Style.RESET_ALL}")
        print(f"• Timezone: {Fore.YELLOW}{TIMEZONE_OPTIONS[auto_settings['timezone']]['name']} ({TIMEZONE_OPTIONS[auto_settings['timezone']]['display']}){Style.RESET_ALL}")
        
        print(Fore.YELLOW + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + Style.RESET_ALL)
        print(Fore.GREEN + "✅ Bot is running and checking for signals..." + Style.RESET_ALL)
        print(Fore.RED + "🔴 Stop Bot Press Ctrl + C" + Style.RESET_ALL)
    
    def refresh_display(force=False):
        """Helper function to refresh the display"""
        nonlocal last_refresh_time
        current_time = datetime.now()
        
        # Only refresh if forced or enough time has passed (2 minutes)
        if force or (current_time - last_refresh_time).total_seconds() >= 120:
            clear_screen_except_banner()
            display_banner()
            display_settings()
            if next_signal:
                print(Fore.CYAN + "\nNext Signal:" + Style.RESET_ALL)
                print(Fore.YELLOW + f"• Pair: {next_signal[0].get('pair', '')}")
                print(f"• Time: {next_signal[0].get('time', '')}")
                print(f"• Action: {next_signal[0].get('action', '')}")
                print(f"• Minutes until execution: {int(next_signal[2])}" + Style.RESET_ALL)
            last_refresh_time = current_time
    
    clear_screen_except_banner()
    display_banner()
    display_settings()
    
    last_check_time = None
    sent_signals = set()  # Keep track of sent signals to avoid duplicates
    next_signal = None
    last_refresh_time = datetime.now()
    error_count = 0
    
    try:
        while True:
            try:
                current_time = datetime.now()
                
                # Check if current time is within allowed range
                current_time_only = current_time.time()
                start_time = datetime.strptime(auto_settings['start_time'], "%H:%M").time()
                end_time = datetime.strptime(auto_settings['end_time'], "%H:%M").time()
                
                if not (start_time <= current_time_only <= end_time):
                    time.sleep(60)  # Sleep for 1 minute if outside trading hours
                    continue
                
                # Only fetch new signals every 30 seconds
                if last_check_time and (current_time - last_check_time).seconds < 30:
                    time.sleep(0.1)  # Small sleep to prevent high CPU usage
                    continue
                
                signals = fetch_signals_with_settings(auto_settings)
                
                if signals:
                    error_count = 0  # Reset error count on successful fetch
                    # Find the next upcoming signal
                    upcoming_signals = []
                    for signal in signals:
                        try:
                            signal_time_str = signal.get('time', '')
                            if not signal_time_str:
                                continue
                                
                            signal_time = datetime.strptime(signal_time_str, "%H:%M").replace(
                                year=current_time.year,
                                month=current_time.month,
                                day=current_time.day
                            )
                            
                            if signal_time < current_time:
                                signal_time = signal_time + timedelta(days=1)
                            
                            signal_id = f"{signal_time_str}_{signal.get('pair', '')}_{signal.get('action', '')}"
                            time_diff = (signal_time - current_time).total_seconds() / 60
                            
                            if signal_id not in sent_signals:
                                upcoming_signals.append((signal, signal_time, time_diff, signal_id))
                        except ValueError:
                            continue
                    
                    # Sort upcoming signals by time
                    upcoming_signals.sort(key=lambda x: x[1])
                    
                    # Update next signal info
                    if upcoming_signals:
                        new_next_signal = upcoming_signals[0]
                        if new_next_signal != next_signal:
                            next_signal = new_next_signal
                            refresh_display(force=True)  # Force refresh when signal changes
                    
                    # Send signal if it's time
                    if next_signal and next_signal[2] <= send_before and next_signal[2] >= send_before - 0.5:
                        if send_to_telegram(None, next_signal[0], send_before):
                            sent_signals.add(next_signal[3])
                            print(Fore.GREEN + f"\n✅ Signal sent for {next_signal[0].get('pair', '')} | Execute at: {next_signal[0].get('time', '')}" + Style.RESET_ALL)
                            next_signal = None  # Reset next signal after sending
                            refresh_display(force=True)  # Force refresh after sending
                
                # Clean up old signals at midnight
                if current_time.hour == 0 and current_time.minute == 0:
                    sent_signals.clear()
                    
                last_check_time = current_time
                
                # Regular refresh check
                refresh_display()
                
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
                
            except Exception as e:
                error_count += 1
                print(Fore.RED + f"\nError occurred: {str(e)}" + Style.RESET_ALL)
                if error_count >= 3:  # If too many errors, wait longer
                    time.sleep(60)  # Wait 1 minute before retrying
                else:
                    time.sleep(5)  # Short wait for minor errors
                
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nStopping Auto Signal Sender..." + Style.RESET_ALL)
        time.sleep(1)
        return

def load_settings(settings_file):
    if not os.path.exists(settings_file):
        return None
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings from {settings_file}: {e}")
        return None

def save_settings(settings, settings_file):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings to {settings_file}: {e}")
        return False

def load_auto_bot_settings():
    """Load auto bot settings from file"""
    if os.path.exists(AUTO_BOT_SETTINGS_FILE):
        try:
            with open(AUTO_BOT_SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "pairs": "NZDCAD_otc",  # Default pairs
        "start_time": "00:00",  # Default start time
        "end_time": "23:49",    # Default end time
        "days": "3",            # Default number of days
        "mode": "normal",       # Default mode
        "min_percentage": "100", # Default minimum percentage
        "filter": "2",          # Default filter (2 = Future Trend)
        "separate_trend": "1",  # Default separate by trend
        "timezone": "1",        # Default timezone (India)
        "bot_token": "",  # Default bot token
        "channel_id": "",  # Default channel ID
        "send_before": "1"      # Default minutes before to send signal
    }

def configure_auto_bot_settings():
    """Configure auto bot settings"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nConfigure Auto Bot Settings\n" + Style.RESET_ALL)
    
    # Load current settings
    current_settings = load_settings(AUTO_BOT_SETTINGS_FILE) or {}
    
    # Configure settings
    settings = {}
    
    # Auto bot settings
    print(Fore.YELLOW + "\nAuto Bot Settings" + Style.RESET_ALL)
    settings['enabled'] = input(f"{Fore.WHITE}Enable auto bot (0/1) (current: {current_settings.get('enabled', '0')}): {Style.RESET_ALL}").strip() or current_settings.get('enabled', '0')
    
    if settings['enabled'] == '1':
        settings['interval'] = input(f"{Fore.WHITE}Check interval in minutes (current: {current_settings.get('interval', '5')}): {Style.RESET_ALL}").strip() or current_settings.get('interval', '5')
        settings['send_before'] = input(f"{Fore.WHITE}Send signals before expiry (minutes) (current: {current_settings.get('send_before', '2')}): {Style.RESET_ALL}").strip() or current_settings.get('send_before', '2')
        
        # Copy relevant settings from default settings
        default_settings = load_settings(DEFAULT_SETTINGS_FILE) or get_default_settings()
        for key in ['pairs', 'start_time', 'end_time', 'days', 'mode', 'min_percentage', 'filter_value', 'separate', 'timezone']:
            settings[key] = default_settings.get(key, '')
        
        # Telegram settings
        print(Fore.YELLOW + "\nTelegram Settings" + Style.RESET_ALL)
        settings['telegram_bot_token'] = input(f"{Fore.WHITE}Enter Telegram bot token (current: {'********' if current_settings.get('telegram_bot_token') else 'not set'}): {Style.RESET_ALL}").strip() or current_settings.get('telegram_bot_token', '')
        settings['telegram_channel'] = input(f"{Fore.WHITE}Enter Telegram channel ID/username (current: {'********' if current_settings.get('telegram_channel') else 'not set'}): {Style.RESET_ALL}").strip() or current_settings.get('telegram_channel', '')
    
    # Save settings
    if save_settings(settings, AUTO_BOT_SETTINGS_FILE):
        print(Fore.GREEN + "\nAuto bot settings saved successfully!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\nError saving auto bot settings!" + Style.RESET_ALL)
    
    hit_enter_to_continue()

def save_auto_bot_settings(settings):
    """Save auto bot settings to a JSON file and update Default Settings with Telegram info."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(AUTO_BOT_SETTINGS_FILE), exist_ok=True)
    
    # Save auto bot settings
    with open(AUTO_BOT_SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)
    
    # Update Default Settings with Telegram information
    if 'bot_token' in settings and 'channel_id' in settings:
        # Load current default settings
        default_settings = load_settings(DEFAULT_SETTINGS_FILE)
        
        # Update Telegram settings in default settings
        default_settings['telegram_bot_token'] = settings['bot_token']
        default_settings['telegram_channel'] = settings['channel_id']
        
        # Save updated default settings
        save_settings(default_settings, DEFAULT_SETTINGS_FILE)
        
        print(Fore.GREEN + "\nTelegram settings have been updated in both." + Style.RESET_ALL)

def save_default_settings():
    """Save user's preferred settings as default"""
    clear_screen_except_banner()
    display_banner()
    
    global DEFAULT_SETTINGS
    current_settings = DEFAULT_SETTINGS.copy()
    
    print(Fore.CYAN + "\nEnter your preferred default settings:" + Style.RESET_ALL)
    
    # Get pairs input
    pairs = input(Fore.YELLOW + f"Enter pairs (current: {current_settings.get('pairs', 'Not Set')}): " + Style.RESET_ALL).strip()
    if pairs:
        current_settings["pairs"] = pairs
    
    # Get start time
    start_time = input(Fore.YELLOW + f"Enter start time (current: {current_settings.get('start_time', 'Not Set')}): " + Style.RESET_ALL).strip()
    if start_time:
        current_settings["start_time"] = start_time
    
    # Get end time
    end_time = input(Fore.YELLOW + f"Enter end time (current: {current_settings.get('end_time', 'Not Set')}): " + Style.RESET_ALL).strip()
    if end_time:
        current_settings["end_time"] = end_time
    
    # Get number of days
    days = input(Fore.YELLOW + f"Enter number of days (current: {current_settings.get('days', 'Not Set')}): " + Style.RESET_ALL).strip()
    if days:
        current_settings["days"] = days
    
    # Get mode
    mode = input(Fore.YELLOW + f"Enter mode (Blackout/Normal) (current: {current_settings.get('mode', 'Not Set')}): " + Style.RESET_ALL).strip().lower()
    if mode in ['blackout', 'normal']:
        current_settings["mode"] = mode
    
    # Get minimum percentage
    min_percentage = input(Fore.YELLOW + f"Enter minimum percentage (current: {current_settings.get('min_percentage', 'Not Set')}): " + Style.RESET_ALL).strip()
    if min_percentage:
        current_settings["min_percentage"] = min_percentage
    
    # Get filter value
    filter_value = input(Fore.YELLOW + f"Enter filter value (1 Human or 2 Future Trend) (current: {current_settings.get('filter_value', 'Not Set')}): " + Style.RESET_ALL).strip()
    if filter_value in ['1', '2']:
        current_settings["filter_value"] = filter_value
    
    # Get separate trend
    separate = input(Fore.YELLOW + f"Separate results by trend? (1 for yes) (current: {current_settings.get('separate', 'Not Set')}): " + Style.RESET_ALL).strip()
    if separate in ['0', '1']:
        current_settings["separate"] = separate
    
    # Get timezone
    print(Fore.CYAN + "\nSelect Timezone:" + Style.RESET_ALL)
    for tz_id, tz_info in TIMEZONE_OPTIONS.items():
        print(f"{tz_id}. {tz_info['name']} ({tz_info['display']})")
    
    while True:
        timezone = input(Fore.YELLOW + f"Enter timezone number (current: {current_settings.get('timezone', 'Not Set')}): " + Style.RESET_ALL).strip()
        if timezone in TIMEZONE_OPTIONS:
            current_settings["timezone"] = timezone
            break
        print(Fore.RED + "Invalid timezone selection. Please try again." + Style.RESET_ALL)
    
    # Save settings to file
    save_settings(current_settings, DEFAULT_SETTINGS_FILE)
    
    DEFAULT_SETTINGS = current_settings
    print(Fore.GREEN + "\n✅ Settings saved successfully!" + Style.RESET_ALL)
    time.sleep(2)

def reset_to_default():
    """Reset all settings to default values"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nReset to Default Settings\n" + Style.RESET_ALL)
    
    # Get default settings
    default_settings = get_default_settings()
    
    # Show settings that will be reset
    print(Fore.YELLOW + "The following settings will be reset to default values:" + Style.RESET_ALL)
    for key, value in default_settings.items():
        if key not in ['telegram_bot_token', 'telegram_channel']:
            print(f"{Fore.WHITE}{key}: {Fore.CYAN}{value}{Style.RESET_ALL}")
    
    # Confirm reset
    confirm = input(Fore.YELLOW + "\nAre you sure you want to reset all settings to default? (y/n): " + Style.RESET_ALL).strip().lower()
    
    if confirm == 'y':
        # Save default settings
        if save_settings(default_settings, DEFAULT_SETTINGS_FILE):
            print(Fore.GREEN + "\nSettings have been reset to default values!" + Style.RESET_ALL)
            
            # Also reset auto bot settings
            auto_bot_settings = {
                'enabled': '0',
                'interval': '5',
                'send_before': '2'
            }
            save_settings(auto_bot_settings, AUTO_BOT_SETTINGS_FILE)
            
        else:
            print(Fore.RED + "\nError resetting settings to default values!" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "\nReset cancelled." + Style.RESET_ALL)
    
    hit_enter_to_continue()

def get_device_mac():
    return "VERIFIED"  # Return a dummy value

def customize_signal_message():
    """Customize signal message format"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nCustomize Signal Message\n" + Style.RESET_ALL)
    
    # Load current settings
    settings = load_settings(DEFAULT_SETTINGS_FILE) or get_default_settings()
    
    # Signal message settings
    print(Fore.YELLOW + "\nSignal Message Settings" + Style.RESET_ALL)
    
    # Alert title
    settings['alert_title'] = input(f"{Fore.WHITE}Enter alert title (current: {settings.get('alert_title', 'GrowUp Future Signals')}): {Style.RESET_ALL}").strip() or settings.get('alert_title', 'GrowUp Future Signals')
    
    # Signal images
    print(Fore.YELLOW + "\nSignal Images" + Style.RESET_ALL)
    settings['call_image_url'] = input(f"{Fore.WHITE}Enter CALL signal image URL (current: {settings.get('call_image_url', '')}): {Style.RESET_ALL}").strip() or settings.get('call_image_url', '')
    settings['put_image_url'] = input(f"{Fore.WHITE}Enter PUT signal image URL (current: {settings.get('put_image_url', '')}): {Style.RESET_ALL}").strip() or settings.get('put_image_url', '')
    
    # Signal rules
    print(Fore.YELLOW + "\nSignal Rules" + Style.RESET_ALL)
    rules = []
    while True:
        rule = input(f"{Fore.WHITE}Enter signal rule (or press Enter to finish): {Style.RESET_ALL}").strip()
        if not rule:
            break
        rules.append(rule)
    
    if rules:
        settings['signal_rules'] = rules
    elif 'signal_rules' not in settings:
        settings['signal_rules'] = [
            "⚡️ Follow Money Management",
            "⚡️ Trade at your own risk",
            "⚡️ Don't over trade"
        ]
    
    # Fixed settings
    settings['call_emoji'] = "🟢"  # Fixed CALL emoji
    settings['put_emoji'] = "🔴"   # Fixed PUT emoji
    settings['martingale'] = "1 Step"  # Fixed martingale steps
    settings['bot_signature'] = "Generated by GrowUp Future Signals"  # Fixed signature
    
    # Save settings
    if save_settings(settings, DEFAULT_SETTINGS_FILE):
        print(Fore.GREEN + "\nSignal message settings saved successfully!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\nError saving signal message settings!" + Style.RESET_ALL)
    
    hit_enter_to_continue()

def get_default_settings():
    return {
        "pairs": "NZDCAD_otc",  # Default pair
        "start_time": "00:00",  # Default start time
        "end_time": "23:49",    # Default end time
        "days": "3",            # Default number of days
        "mode": "normal",       # Default mode
        "min_percentage": "100", # Default minimum percentage
        "filter_value": "2",    # Default filter (2 = Future Trend)
        "separate": "1",        # Default separate by trend
        "timezone": "1",        # Default timezone (India)
        "telegram_bot_token": "",  # Default bot token
        "telegram_channel": ""  # Default channel ID
    }

def initialize_settings():
    global DEFAULT_SETTINGS
    settings = load_settings(DEFAULT_SETTINGS_FILE)
    if settings is None:
        settings = get_default_settings()
        save_settings(settings, DEFAULT_SETTINGS_FILE)
    DEFAULT_SETTINGS = settings
    return settings

def handle_login():
    """Handle the login process"""
    while True:
        clear_screen()
        print_header()
        print(Fore.CYAN + "\nLogin")
        print(Fore.YELLOW + "Enter your credentials or press Enter to go back to main menu.\n")
        
        username = input(Fore.WHITE + "Username: " + Style.RESET_ALL).strip()
        if not username:
            return
            
        password = input(Fore.WHITE + "Password: " + Style.RESET_ALL).strip()
        if not password:
            return
            
        try:
            if verify_credentials(username, password):
                save_login = input(Fore.YELLOW + "Save login credentials? (y/n): " + Style.RESET_ALL).strip().lower() == 'y'
                if save_login:
                    save_credentials({"username": username, "password": password, "save_login": True})
                print(Fore.GREEN + "\nLogin successful!" + Style.RESET_ALL)
                time.sleep(1)
                return True
            else:
                print(Fore.RED + "\nInvalid credentials. Please try again." + Style.RESET_ALL)
                time.sleep(2)
        except Exception as e:
            print(Fore.RED + f"\nLogin error: {str(e)}" + Style.RESET_ALL)
            time.sleep(2)
    return False

def print_header():
    """Print the application header"""
    print(Fore.GREEN + """
 ██████╗ ██████╗  ██████╗ ██╗    ██╗██╗   ██╗██████╗ 
██╔════╝ ██╔══██╗██╔═══██╗██║    ██║██║   ██║██╔══██╗
██║  ███╗██████╔╝██║   ██║██║ █╗ ██║██║   ██║██████╔╝
██║   ██║██╔══██╗██║   ██║██║███╗██║██║   ██║██╔═══╝ 
╚██████╔╝██║  ██║╚██████╔╝╚███╔███╔╝╚██████╔╝██║     
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚═╝     
                                                       
███████╗██╗   ██╗████████╗██╗   ██╗██████╗ ███████╗   
██╔════╝██║   ██║╚══██╔══╝██║   ██║██╔══██╗██╔════╝   
█████╗  ██║   ██║   ██║   ██║   ██║██████╔╝█████╗     
██╔══╝  ██║   ██║   ██║   ██║   ██║██╔══██╗██╔══╝     
██║     ╚██████╔╝   ██║   ╚██████╔╝██║  ██║███████╗   
╚═╝      ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝   
                                                       
███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗     ███████╗
██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║     ██╔════╝
███████╗██║██║  ███╗██╔██╗ ██║███████║██║     ███████╗
╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║     ╚════██║
███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗███████║
╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚══════╝
""" + Style.RESET_ALL)
    print(Fore.CYAN + "Version 2.0 - Mobile Edition" + Style.RESET_ALL)
    print(Fore.YELLOW + "Copyright © 2024 GrowUp Future Signals. All rights reserved.\n" + Style.RESET_ALL)

def clear_screen():
    """Clear the terminal screen"""
    if IS_TERMUX:
        os.system('clear')
    else:
    os.system('cls' if os.name == 'nt' else 'clear')

def verify_credentials(username, password):
    """Verify user credentials"""
    try:
        # Create a session
        session = requests.Session()
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        session.headers.update(headers)
        
        # Login data
        login_data = {
            'username': username,
            'password': password
        }
        
        # Send login request
        response = session.post('https://api.growupfuturesignals.com/login', json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return True
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"\nConnection error: {str(e)}" + Style.RESET_ALL)
        return False
    except Exception as e:
        print(Fore.RED + f"\nVerification error: {str(e)}" + Style.RESET_ALL)
        return False

def view_current_settings():
    """Display current settings"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nCurrent Settings:\n" + Style.RESET_ALL)
    
    # Load settings
    default_settings = load_settings(DEFAULT_SETTINGS_FILE)
    auto_bot_settings = load_settings(AUTO_BOT_SETTINGS_FILE)
    
    if default_settings:
        print(Fore.YELLOW + "Default Settings:" + Style.RESET_ALL)
        for key, value in default_settings.items():
            print(f"{Fore.WHITE}{key}: {Fore.CYAN}{value}{Style.RESET_ALL}")
    else:
        print(Fore.RED + "No default settings found." + Style.RESET_ALL)
    
    print()
    
    if auto_bot_settings:
        print(Fore.YELLOW + "Auto Bot Settings:" + Style.RESET_ALL)
        for key, value in auto_bot_settings.items():
            if key in ['telegram_bot_token', 'telegram_channel']:
                value = '********' if value else ''
            print(f"{Fore.WHITE}{key}: {Fore.CYAN}{value}{Style.RESET_ALL}")
    else:
        print(Fore.RED + "No auto bot settings found." + Style.RESET_ALL)
    
    hit_enter_to_continue()

def configure_default_settings():
    """Configure default settings"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nConfigure Default Settings\n" + Style.RESET_ALL)
    
    # Load current settings
    current_settings = load_settings(DEFAULT_SETTINGS_FILE) or get_default_settings()
    
    # Configure settings
    settings = {}
    
    # Trading pairs
    print(Fore.YELLOW + "\nTrading Pairs" + Style.RESET_ALL)
    settings['pairs'] = input(f"{Fore.WHITE}Enter pairs (current: {current_settings['pairs']}): {Style.RESET_ALL}").strip() or current_settings['pairs']
    
    # Time settings
    print(Fore.YELLOW + "\nTime Settings" + Style.RESET_ALL)
    settings['start_time'] = input(f"{Fore.WHITE}Enter start time HH:MM (current: {current_settings['start_time']}): {Style.RESET_ALL}").strip() or current_settings['start_time']
    settings['end_time'] = input(f"{Fore.WHITE}Enter end time HH:MM (current: {current_settings['end_time']}): {Style.RESET_ALL}").strip() or current_settings['end_time']
    
    # Trading settings
    print(Fore.YELLOW + "\nTrading Settings" + Style.RESET_ALL)
    settings['days'] = input(f"{Fore.WHITE}Enter number of days (current: {current_settings['days']}): {Style.RESET_ALL}").strip() or current_settings['days']
    settings['mode'] = input(f"{Fore.WHITE}Enter mode (normal/blackout) (current: {current_settings['mode']}): {Style.RESET_ALL}").strip().lower() or current_settings['mode']
    settings['min_percentage'] = input(f"{Fore.WHITE}Enter minimum percentage (current: {current_settings['min_percentage']}): {Style.RESET_ALL}").strip() or current_settings['min_percentage']
    settings['filter_value'] = input(f"{Fore.WHITE}Enter filter value (1=Human/2=Future Trend) (current: {current_settings['filter_value']}): {Style.RESET_ALL}").strip() or current_settings['filter_value']
    settings['separate'] = input(f"{Fore.WHITE}Enter separate trend (0/1) (current: {current_settings['separate']}): {Style.RESET_ALL}").strip() or current_settings['separate']
    
    # Timezone setting
    print(Fore.YELLOW + "\nTimezone Setting" + Style.RESET_ALL)
    settings['timezone'] = input(f"{Fore.WHITE}Enter timezone (1-24) (current: {current_settings['timezone']}): {Style.RESET_ALL}").strip() or current_settings['timezone']
    
    # Telegram settings
    print(Fore.YELLOW + "\nTelegram Settings" + Style.RESET_ALL)
    settings['telegram_bot_token'] = input(f"{Fore.WHITE}Enter Telegram bot token (current: {'********' if current_settings['telegram_bot_token'] else 'not set'}): {Style.RESET_ALL}").strip() or current_settings['telegram_bot_token']
    settings['telegram_channel'] = input(f"{Fore.WHITE}Enter Telegram channel ID/username (current: {'********' if current_settings['telegram_channel'] else 'not set'}): {Style.RESET_ALL}").strip() or current_settings['telegram_channel']
    
    # Save settings
    if save_settings(settings, DEFAULT_SETTINGS_FILE):
        print(Fore.GREEN + "\nSettings saved successfully!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\nError saving settings!" + Style.RESET_ALL)
    
    hit_enter_to_continue()

def main():
    """Main function with all features"""
    try:
        # Initialize settings
        initialize_settings()
        
        while True:
            clear_screen()
            print_header()
            
            print(Fore.CYAN + "\nMain Menu:")
            print(Fore.WHITE + "1. Login")
            print("2. Configure Default Settings")
            print("3. Configure Auto Bot Settings")
            print("4. Start Auto Bot")
            print("5. View Current Settings")
            print("6. Customize Signal Message")
            print("7. Reset to Default Settings")
            print("8. Logout")
            
            choice = input(Fore.YELLOW + "\nEnter your choice (1-8): " + Style.RESET_ALL).strip()
            
            if choice == "1":
                handle_login()
            elif choice == "2":
                configure_default_settings()
            elif choice == "3":
                configure_auto_bot_settings()
            elif choice == "4":
                start_auto_bot()
            elif choice == "5":
                view_current_settings()
            elif choice == "6":
                customize_signal_message()
            elif choice == "7":
                reset_to_default()
            elif choice == "8":
                clear_screen()
                print(Fore.GREEN + "Thank you for using GrowUp Future Signals!" + Style.RESET_ALL)
                break
            else:
                print(Fore.RED + "\nInvalid choice! Please try again." + Style.RESET_ALL)
                hit_enter_to_continue()
                
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\nExiting gracefully..." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"\nAn error occurred: {str(e)}" + Style.RESET_ALL)
        hit_enter_to_continue()

def start_auto_bot():
    """Start the auto bot for signal generation"""
    clear_screen()
    print_header()
    print(Fore.CYAN + "\nStarting Auto Bot\n" + Style.RESET_ALL)
    
    # Load auto bot settings
    settings = load_settings(AUTO_BOT_SETTINGS_FILE)
    if not settings:
        print(Fore.RED + "Error: Auto bot settings not found." + Style.RESET_ALL)
        hit_enter_to_continue()
        return
    
    if settings.get('enabled') != '1':
        print(Fore.RED + "Error: Auto bot is not enabled." + Style.RESET_ALL)
        hit_enter_to_continue()
        return
    
    print(Fore.GREEN + "Auto bot started!" + Style.RESET_ALL)
    print(Fore.YELLOW + "\nPress Ctrl+C to stop." + Style.RESET_ALL)
    
    try:
        while True:
            time.sleep(int(settings.get('interval', 5)) * 60)
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nStopping auto bot..." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"\nError: {str(e)}" + Style.RESET_ALL)
    
    hit_enter_to_continue()


if __name__ == "__main__":
    main()
