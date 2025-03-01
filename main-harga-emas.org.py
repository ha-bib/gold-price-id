import json
import os
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logging
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'gold_price_scraper.log')),
        logging.StreamHandler()
    ]
)

def fetch_gold_prices():
    try:
        # URL for gold price data
        url = "https://www.indogold.id/harga-emas-hari-ini"
        
        # Send a request with a user agent to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize data dictionary
        processed_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "update_date": datetime.now().strftime("%d %B %Y %H:%M:%S"),
            "sources": {}
        }
        
        # Fetch ANTAM gold prices
        antam_data = fetch_antam_prices(soup)
        if antam_data:
            processed_data["sources"]["ANTAM"] = {
                "prices": antam_data
            }
        
        # Fetch UBS gold prices
        ubs_data = fetch_ubs_prices(soup)
        if ubs_data:
            processed_data["sources"]["UBS"] = {
                "prices": ubs_data
            }
        
        # Fetch SEMAR gold prices
        semar_data = fetch_semar_gold_prices()
        if semar_data:
            processed_data["sources"]["SEMAR"] = {
                "prices": semar_data["prices"]
            }
        
        return processed_data
    
    except requests.RequestException as e:
        logging.error(f"Error fetching gold prices: {e}", exc_info=True)
        return None

def fetch_antam_prices(soup):
    try:
        # Find the ANTAM table by ID "tab3"
        antam_table = soup.find('div', id='tab3').find('table')
        
        if not antam_table:
            logging.error("ANTAM table not found")
            return None
        
        # Initialize prices dictionary
        antam_prices = {}
        
        # Iterate over rows in the table
        for row in antam_table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                weight = cols[0].text.strip().replace(' gram', '').replace('.0', '').replace(',', '').strip()
                sell_price = cols[1].text.strip().replace('Rp', '').replace('.', '').replace(',', '').strip()
                buyback_price = cols[2].text.strip().replace('Rp', '').replace('.', '').replace(',', '').strip()
                
                # Normalize weight (replace . with empty string and ensure two digits)
                if '.' in weight:
                    weight = weight.replace('.', '')  # Remove decimal point
                    if len(weight) == 1:  # If single digit, prefix with 0
                        weight = f"0{weight}"
                
                if weight and buyback_price and sell_price:
                    antam_prices[f"{weight}gr"] = {
                        'price': sell_price,
                        'buyback': buyback_price
                    }
        
        return antam_prices
    
    except Exception as e:
        logging.error(f"Error fetching ANTAM prices: {e}", exc_info=True)
        return None

def fetch_ubs_prices(soup):
    try:
        # Find the UBS table by ID "tab0"
        ubs_table = soup.find('div', id='tab0').find('table')
        
        if not ubs_table:
            logging.error("UBS table not found")
            return None
        
        # Initialize prices dictionary
        ubs_prices = {}
        
        # Iterate over rows in the table
        for row in ubs_table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                weight = cols[0].text.strip().replace(' gram', '').replace('.0', '').replace(',', '').strip()
                sell_price = cols[1].text.strip().replace('Rp', '').replace('.', '').replace(',', '').strip()
                buyback_price = cols[2].text.strip().replace('Rp', '').replace('.', '').replace(',', '').strip()
                
                # Normalize weight (replace . with empty string and ensure two digits)
                if '.' in weight:
                    weight = weight.replace('.', '')  # Remove decimal point
                    if len(weight) == 1:  # If single digit, prefix with 0
                        weight = f"0{weight}"
                
                if weight and buyback_price and sell_price:
                    ubs_prices[f"{weight}gr"] = {
                        'price': sell_price,
                        'buyback': buyback_price
                    }
        
        return ubs_prices
    
    except Exception as e:
        logging.error(f"Error fetching UBS prices: {e}", exc_info=True)
        return None

def fetch_semar_gold_prices():
    # Fetch gold prices from SEMAR API
    try:
        url = "https://goldprice.semar.co.id/home/triple/smg_press/smg/smg_press_24k"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        processed_data = {
            "prices": {}
        }
        
        # Process prices for each weight
        for weight, details in data["detail"].items():
            if details["smg_press_24k"]:  # Only include non-empty prices
                processed_data["prices"][f"{weight}"] = {
                    "price": details["smg_press_24k"].replace('.', ''),
                    "buyback": details["buyback_smg_press_24k"].replace('.', '')
                }
        
        return processed_data
    
    except requests.RequestException as e:
        logging.error(f"Error fetching SEMAR gold prices: {e}", exc_info=True)
        return None

def save_gold_data(data, base_path=None):
    # Use project-relative path if not specified
    if base_path is None:
        base_path = os.path.join(os.path.dirname(__file__), 'harga-log')
    
    # Create directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    # Generate filename with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    filename = f"gold_prices_{current_date}.json"
    filepath = os.path.join(base_path, filename)
    
    # Save data to JSON file, overwriting if it exists
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved gold price data to {filepath}")
    except Exception as e:
        logging.error(f"Error saving gold price data: {e}")

def generate_file_list():
    # Generate a JSON file listing all gold price JSON files in the harga-log directory.
    # Sorts files by date in ascending order.
    try:
        # Directory path for gold price logs
        log_dir = os.path.join(os.path.dirname(__file__), 'harga-log')
        
        # Find all JSON files matching the gold prices pattern
        json_files = [
            f for f in os.listdir(log_dir) 
            if f.startswith('gold_prices_') and f.endswith('.json')
        ]
        
        # Sort files by date
        sorted_files = sorted(json_files, key=lambda x: 
            datetime.strptime(x.replace('gold_prices_', '').replace('.json', ''), '%Y-%m-%d')
        )
        
        # Create file list JSON
        file_list_path = os.path.join(log_dir, 'file-list.json')
        with open(file_list_path, 'w') as f:
            json.dump(sorted_files, f, indent=2)
        
        logging.info(f"Generated file list with {len(sorted_files)} files")
    
    except Exception as e:
        logging.error(f"Error generating file list: {e}", exc_info=True)

def main():
    logging.info("Starting gold price scraping...")
    
    # Fetch and process data
    raw_data = fetch_gold_prices()
    
    if raw_data is None:
        logging.error("Failed to fetch gold prices. Exiting.")
        return
    
    # Save data
    save_gold_data(raw_data)
    
    # Generate file list
    generate_file_list()
    
    logging.info("Gold price scraping completed successfully.")

if __name__ == "__main__":
    main()