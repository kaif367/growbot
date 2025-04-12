import os
import socket
import json
import requests
import re
import time
from datetime import datetime, timedelta
from colorama import init, Fore, Style
import telebot
from telebot.apihelper import ApiTelegramException
import sys
import base64  # For basic encryption of stored passwords
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Initialize colorama
init(autoreset=True)

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
DATA_DIR = os.path.join(APP_PATH, "data")

# Create data directory if it doesn't exist
try:
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    
    # Test write access to the DATA_DIR
    test_file = os.path.join(DATA_DIR, "test_write.tmp")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
except Exception as e:
    print(Fore.RED + f"Error accessing data directory: {str(e)}" + Style.RESET_ALL)
    print(Fore.YELLOW + "Application may have limited functionality due to permission issues." + Style.RESET_ALL)
    # Try to use a user-specific location as fallback
    try:
        user_home = os.path.expanduser("~")
        DATA_DIR = os.path.join(user_home, "GrowupSignalsData")
        os.makedirs(DATA_DIR, exist_ok=True)
        print(Fore.GREEN + f"Using alternative data directory: {DATA_DIR}" + Style.RESET_ALL)
    except:
        # Last resort fallback to current directory
        DATA_DIR = os.path.join(os.getcwd(), "data")
        os.makedirs(DATA_DIR, exist_ok=True)

# Paths for settings and credentials
CREDENTIALS_FILE = os.path.join(DATA_DIR, "saved_credentials.json")
DEFAULT_SETTINGS_FILE = os.path.join(DATA_DIR, "default_settings.json")
AUTO_BOT_SETTINGS_FILE = os.path.join(DATA_DIR, "auto_bot_settings.json")

def load_credentials():
    """Load saved credentials from file"""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
                # Decode stored password
                if creds.get("password"):
                    try:
                        creds["password"] = base64.b64decode(creds["password"].encode()).decode()
                    except:
                        # If there's an error decoding, return empty to force re-login
                        print(Fore.RED + "Error loading saved credentials, please login again." + Style.RESET_ALL)
                        return {}
                return creds
        except Exception as e:
            print(Fore.RED + f"Error loading credentials: {str(e)}" + Style.RESET_ALL)
            # If there's any error loading, try to remove the corrupt file
            try:
                os.remove(CREDENTIALS_FILE)
                print(Fore.YELLOW + "Corrupt credentials file removed. Please login again." + Style.RESET_ALL)
            except:
                pass
            return {}
    return {}

def save_credentials(username, password, save_login=False):
    """Save credentials to file if user opts to"""
    creds = {"username": username, "save_login": save_login}
    if save_login:
        # Basic encoding of password (not secure, but better than plaintext)
        creds["password"] = base64.b64encode(password.encode()).decode()
    
    try:
        # Make sure the directory exists
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f)
        return True
    except Exception as e:
        print(Fore.RED + f"Error saving credentials: {str(e)}" + Style.RESET_ALL)
        return False

def change_password(username, old_password, new_password):
    """Change user password"""
    if username in USERS and USERS[username]["password"] == old_password:
        USERS[username]["password"] = new_password
        # If credentials are saved, update saved password
        creds = load_credentials()
        if creds.get("username") == username and creds.get("save_login"):
            save_credentials(username, new_password, True)
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
                    if save_credentials(username, password, True):
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

def load_settings():
    """Load settings from file"""
    try:
        with open(DEFAULT_SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
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
    """Configure settings for auto bot"""
    clear_screen_except_banner()
    display_banner()
    
    current_settings = load_auto_bot_settings()
    
    print(Fore.CYAN + "Enter your preferred auto bot settings:" + Style.RESET_ALL)
    
    # Update pairs
    pairs = input(f"Enter pairs (current: {current_settings.get('pairs', '')}): ").strip()
    if pairs:
        current_settings['pairs'] = pairs
        
    # Update start time
    start_time = input(f"Enter start time (current: {current_settings.get('start_time', '')}): ").strip()
    if start_time:
        current_settings['start_time'] = start_time

    # Update end time
    end_time = input(f"Enter end time (current: {current_settings.get('end_time', '')}): ").strip()
    if end_time:
        current_settings['end_time'] = end_time
        
    # Update days
    days = input(f"Enter number of days (current: {current_settings.get('days', '')}): ").strip()
    if days:
        current_settings['days'] = days
        
    # Update mode
    mode = input(f"Enter mode (Blackout/Normal) (current: {current_settings.get('mode', '')}): ").strip().lower()
    if mode in ['blackout', 'normal']:
        current_settings['mode'] = mode
        
    # Update minimum percentage
    min_percentage = input(f"Enter minimum percentage (current: {current_settings.get('min_percentage', '')}): ").strip()
    if min_percentage:
        current_settings['min_percentage'] = min_percentage
        
    # Update filter value
    filter_value = input(f"Enter filter value (1 Human or 2 Future Trend) (current: {current_settings.get('filter', '')}): ").strip()
    if filter_value in ['1', '2']:
        current_settings['filter'] = filter_value
        
    # Update separate trend
    separate_trend = input(f"Separate results by trend? (1 for yes) (current: {current_settings.get('separate_trend', '')}): ").strip()
    if separate_trend in ['0', '1']:
        current_settings['separate_trend'] = separate_trend
        
    # Update send before time
    send_before = input(f"Enter minutes before to send signal (current: {current_settings.get('send_before', '1')}): ").strip()
    if send_before and send_before.isdigit():
        current_settings['send_before'] = send_before
    
    # Update timezone
    print("\nSelect Timezone:")
    for tz_id, tz_info in TIMEZONE_OPTIONS.items():
        print(f"{tz_id}. {tz_info['name']} ({tz_info['display']})")
    timezone = input(f"Enter timezone number (current: {current_settings.get('timezone', '')}): ").strip()
    if timezone in TIMEZONE_OPTIONS:
        current_settings['timezone'] = timezone
    
    # Update Telegram Settings
    print("\nTelegram Settings:")
    bot_token = input(f"Enter Telegram Bot Token (current: {current_settings.get('bot_token', '')}): ").strip()
    if bot_token:
        current_settings['bot_token'] = bot_token
        
    channel_id = input(f"Enter Telegram Channel ID/Username (current: {current_settings.get('channel_id', '')}): ").strip()
    if channel_id:
        current_settings['channel_id'] = channel_id

    # Save the updated settings
    save_auto_bot_settings(current_settings)
    print(Fore.GREEN + "\nAuto bot settings saved successfully!" + Style.RESET_ALL)
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
        default_settings = load_settings()
        
        # Update Telegram settings in default settings
        default_settings['telegram_bot_token'] = settings['bot_token']
        default_settings['telegram_channel'] = settings['channel_id']
        
        # Save updated default settings
        with open(DEFAULT_SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=4)
        
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
    with open(DEFAULT_SETTINGS_FILE, 'w') as f:
        json.dump(current_settings, f, indent=4)
    
    DEFAULT_SETTINGS = current_settings
    print(Fore.GREEN + "\n✅ Settings saved successfully!" + Style.RESET_ALL)
    time.sleep(2)

def reset_to_default():
    """Reset all settings to default values"""
    clear_screen_except_banner()
    display_banner()
    
    print(Fore.YELLOW + "\n⚠️ Warning: This will reset ALL settings to default values!" + Style.RESET_ALL)
    print(Fore.CYAN + "\nDefault values will be:" + Style.RESET_ALL)
    print(Fore.YELLOW + """
Trading Settings:
• Pairs: NZDCAD_otc
• Start Time: 00:00
• End Time: 23:49
• Days: 3
• Mode: normal
• Min Percentage: 100
• Filter: 2 (Future Trend)
• Separate Trend: 1
• Timezone: 1 (India)

Signal Message Settings:
• Alert Title: UPCOMING SIGNAL ALERT
• CALL Image URL: https://i.ibb.co/Q8L6mk5/Growth.png
• PUT Image URL: https://i.ibb.co/1vsFM2N/Growth-1.png
• Signal Rules: Default rules""" + Style.RESET_ALL)
    
    confirm = input(Fore.RED + "\nPress 'y' to confirm reset (This cannot be undone): " + Style.RESET_ALL).strip().lower()
    
    if confirm == 'y':
        # Default settings
        default_settings = {
            "pairs": "NZDCAD_otc",
            "start_time": "00:00",
            "end_time": "23:49",
            "days": "3",
            "mode": "normal",
            "min_percentage": "100",
            "filter_value": "2",
            "separate": "1",
            "timezone": "1",
            "telegram_bot_token": "",
            "telegram_channel": ""
        }
        
        # Default auto bot settings
        default_auto_settings = {
            "pairs": "NZDCAD_otc",
            "start_time": "00:00",
            "end_time": "23:49",
            "days": "3",
            "mode": "normal",
            "min_percentage": "100",
            "filter": "2",
            "separate_trend": "1",
            "timezone": "1",
            "bot_token": "",
            "channel_id": "",
            "send_before": "1",
            "alert_title": "UPCOMING SIGNAL ALERT",
            "call_image_url": "https://i.ibb.co/Q8L6mk5/Growth.png",
            "put_image_url": "https://i.ibb.co/1vsFM2N/Growth-1.png",
            # Fixed settings that cannot be changed
            "call_emoji": "🟢",
            "put_emoji": "🔴",
            "martingale_steps": "1 Step",
            "bot_signature": "Generated by GrowUp Future Signals",
            "signal_rules": ["If the previous candle is weak, the signal should be avoided", "Follow Trend"]
        }
        
        # Update global DEFAULT_SETTINGS
        global DEFAULT_SETTINGS
        DEFAULT_SETTINGS = default_settings.copy()
        
        # Save default settings
        with open(DEFAULT_SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=4)
            
        with open(AUTO_BOT_SETTINGS_FILE, 'w') as f:
            json.dump(default_auto_settings, f, indent=4)
            
        print(Fore.GREEN + "\n✅ All settings have been reset to default values!" + Style.RESET_ALL)
        
        # Verify the reset
        try:
            # Reload settings to verify
            loaded_settings = load_settings()
            loaded_auto_settings = load_auto_bot_settings()
            
            if loaded_settings == default_settings and loaded_auto_settings == default_auto_settings:
                print(Fore.GREEN + "✅ Settings reset verified successfully!" + Style.RESET_ALL)
            else:
                print(Fore.RED + "⚠️ Warning: Some settings may not have reset properly." + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"⚠️ Error verifying settings reset: {str(e)}" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "\nReset cancelled." + Style.RESET_ALL)
    
    hit_enter_to_continue()

def get_device_mac():
    return "VERIFIED"  # Return a dummy value

def hit_enter_to_continue():
    """Prompt user to hit enter to go back to the menu."""
    print(Fore.CYAN + "\nHIT ENTER TO GO BACK OR CONTINUE..." + Style.RESET_ALL)
    try:
        input()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print(Fore.YELLOW + "\nOperation cancelled." + Style.RESET_ALL)
        pass

def clear_screen_except_banner():
    """Clear the screen."""
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except:
        # If the command fails, print newlines as fallback
        print("\n" * 100)

def customize_signal_message():
    """Customize the signal message format and appearance"""
    clear_screen_except_banner()
    display_banner()
    
    current_settings = load_auto_bot_settings()
    
    print(Fore.CYAN + "\nSignal Message Customization" + Style.RESET_ALL)
    print(Fore.YELLOW + "═" * 50 + Style.RESET_ALL)
    
    # Alert title
    alert_title = input(f"Enter alert title (current: {current_settings.get('alert_title', 'UPCOMING SIGNAL ALERT')}): ").strip()
    if alert_title:
        current_settings['alert_title'] = alert_title
    elif 'alert_title' not in current_settings:
        current_settings['alert_title'] = "UPCOMING SIGNAL ALERT"
    
    print(Fore.YELLOW + "\n--- Signal Images ---" + Style.RESET_ALL)
    # Call image URL
    call_image_url = input(f"Enter CALL signal image URL (current: {current_settings.get('call_image_url', 'https://i.ibb.co/Q8L6mk5/Growth.png')}): ").strip()
    if call_image_url:
        current_settings['call_image_url'] = call_image_url
    elif 'call_image_url' not in current_settings:
        current_settings['call_image_url'] = "https://i.ibb.co/Q8L6mk5/Growth.png"
    
    # Put image URL
    put_image_url = input(f"Enter PUT signal image URL (current: {current_settings.get('put_image_url', 'https://i.ibb.co/1vsFM2N/Growth-1.png')}): ").strip()
    if put_image_url:
        current_settings['put_image_url'] = put_image_url
    elif 'put_image_url' not in current_settings:
        current_settings['put_image_url'] = "https://i.ibb.co/1vsFM2N/Growth-1.png"
    
    # Fixed settings that cannot be changed
    current_settings['call_emoji'] = "🟢"  # Fixed CALL emoji
    current_settings['put_emoji'] = "🔴"   # Fixed PUT emoji
    current_settings['martingale_steps'] = "1 Step"  # Fixed martingale steps
    current_settings['bot_signature'] = "Generated by GrowUp Future Signals"  # Fixed signature
    
    print(Fore.YELLOW + "\n--- Signal Rules ---" + Style.RESET_ALL)
    current_rules = current_settings.get('signal_rules', ["If the previous candle is weak, the signal should be avoided", "Follow Trend"])
    
    print("Current rules:")
    for i, rule in enumerate(current_rules):
        print(f"{i+1}. {rule}")
    
    new_rules = []
    rule_num = 1
    while True:
        rule = input(f"Rule {rule_num} (leave empty to finish): ").strip()
        if not rule:
            break
        new_rules.append(rule)
        rule_num += 1
    
    if new_rules:
        current_settings['signal_rules'] = new_rules
    elif 'signal_rules' not in current_settings:
        current_settings['signal_rules'] = ["If the previous candle is weak, the signal should be avoided", "Follow Trend"]

    # Save the updated settings
    save_auto_bot_settings(current_settings)
    print(Fore.GREEN + "\n✅ Signal message customization saved successfully!" + Style.RESET_ALL)
    hit_enter_to_continue()

def main():
    """Main function with all features"""
    # Initialize important directories at startup
    try:
        # Create signals directory if it doesn't exist
        signals_dir = os.path.join(APP_PATH, "Signals")
        os.makedirs(signals_dir, exist_ok=True)
        
        # Ensure data directory exists and is writable
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        print(Fore.RED + f"Error initializing directories: {str(e)}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Some features may not work correctly." + Style.RESET_ALL)
        time.sleep(3)
    
    while True:
        try:
            clear_screen_except_banner()
            display_banner()
            
            # Load saved settings at startup
            global DEFAULT_SETTINGS
            DEFAULT_SETTINGS = load_settings()

            print(Fore.CYAN + "\nMain Menu:")
            print(Fore.YELLOW + "1. Login")
            print(Fore.YELLOW + "2. Software Info")
            print(Fore.YELLOW + "3. Exit")
            
            try:
                choice = input(Fore.YELLOW + "\nEnter your choice (1-3): " + Style.RESET_ALL).strip()
            except KeyboardInterrupt:
                choice = "3"  # Default to exit
                
            if choice == "1":
                login_info = login()
                if login_info:
                    username, expire_time = login_info  # Unpack the returned tuple
                    
                    while True:
                        if not check_session(username):
                            break
                        
                        try:
                            clear_screen_except_banner()
                            display_banner()
                            
                            print(Fore.CYAN + f"\nWelcome, {username}! Your license is valid until: {expire_time}\n")
                            print(Fore.CYAN + "\nSignal Menu:")
                            print(Fore.YELLOW + "1. Fetch Signals")
                            print(Fore.YELLOW + "2. Default Settings")
                            print(Fore.YELLOW + "3. Show Available Pairs")
                            print(Fore.YELLOW + "4. Auto Send Signals")
                            print(Fore.YELLOW + "5. Configure Auto Bot Settings")
                            print(Fore.YELLOW + "6. Customize Signal Message")
                            print(Fore.YELLOW + "7. Reset All Settings to Default")
                            print(Fore.YELLOW + "8. Logout")
                            
                            sub_choice = input(Fore.YELLOW + "\nEnter your choice (1-8): " + Style.RESET_ALL).strip()
                            
                            if sub_choice == "1":
                                fetch_signals()
                                hit_enter_to_continue()
                            elif sub_choice == "2":
                                save_default_settings()
                                hit_enter_to_continue()
                            elif sub_choice == "3":
                                display_pairs()
                                hit_enter_to_continue()
                            elif sub_choice == "4":
                                auto_send_signals()
                            elif sub_choice == "5":
                                configure_auto_bot_settings()
                                hit_enter_to_continue()
                            elif sub_choice == "6":
                                customize_signal_message()
                            elif sub_choice == "7":
                                reset_to_default()
                            elif sub_choice == "8":
                                print(Fore.RED + "Logging out..." + Style.RESET_ALL)
                                time.sleep(2)
                                break
                        except Exception as e:
                            print(Fore.RED + f"Error in signal menu: {str(e)}" + Style.RESET_ALL)
                            hit_enter_to_continue()
                            
            elif choice == "2":
                display_pairs()
                hit_enter_to_continue()
            elif choice == "3":
                clear_screen_except_banner()
                display_banner()
                show_copyright()
                print(Fore.RED + "\nExiting program..." + Style.RESET_ALL)
                time.sleep(2)
                sys.exit()
            else:
                print(Fore.RED + "Invalid choice. Please try again." + Style.RESET_ALL)
                hit_enter_to_continue()
        except Exception as e:
            print(Fore.RED + f"An unexpected error occurred: {str(e)}" + Style.RESET_ALL)
            hit_enter_to_continue()


if __name__ == "__main__":
    DEFAULT_SETTINGS = {
        "pairs": "BRLUSD_otc,USDPKR_otc",
        "start_time": "09:00",
        "end_time": "18:00",
        "days": "3",
        "mode": "blackout",
        "min_percentage": "80",
        "filter_value": "1",
        "separate": "1",
        "timezone": "1"  # Default to India timezone
    }
    main()
