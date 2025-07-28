import json
import os
import logging
import re
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

def parse_gold_prices(raw_text):
    """
    Parse the complex gold price text and extract prices for different weights
    """
    # Remove newlines and extra spaces
    raw_text = raw_text.replace('\n', ' ').strip()
    
    # Prices for specific weights
    target_weights = ['0.5', '1', '2', '3', '5', '10', '25', '50', '100', '250', '500', '1000']
    
    # Initialize result dictionary
    result = {}
    
    # Regular expression to find price patterns
    price_pattern = r'(\d+(?:\.\d+)?)\s*Rp([\d.]+)\s*Rp([\d.]+)'
    matches = re.findall(price_pattern, raw_text)
    
    for match in matches:
        weight, sell_price, buyback_price = match
        
        # Normalize weight to handle decimal weights specifically for 0.5
        if weight == '0.5':
            normalized_weight = '05gr'
        else:
            normalized_weight = f'{weight}gr'
        
        if weight in target_weights:
            result[normalized_weight] = {
                'price': sell_price,
                'buyback': buyback_price
            }
    
    return result

def fetch_gold_prices():
    try:
        # URL for gold price data
        url = "https://galeri24.co.id/harga-emas"
        
        # Send a request with a user agent to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Log the entire HTML content for debugging
        # logging.debug(f"Received HTML content: {response.text[:1000]}...")  # First 1000 chars
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize data dictionary
        processed_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "update_date": datetime.now().strftime("%d %B %Y %H:%M:%S"),
            "sources": {}
        }
        
        # Find gold price elements
        sources = {
            "GALERI 24": "#GALERI\\ 24",
            "ANTAM": "#ANTAM",
            "UBS": "#UBS"
        }
        
        for source_name, source_selector in sources.items():
            try:
                logging.debug(f"Searching for {source_name} with selector: {source_selector}")
                
                # Find the price element
                price_element = soup.select_one(source_selector)
                
                if price_element:
                    logging.debug(f"Found price element for {source_name}")
                    
                    # Extract full text of the price element
                    full_text = price_element.text.strip()
                    # logging.debug(f"Full text for {source_name}: {full_text}")
                    
                    # Find all rows with price information
                    price_rows = price_element.select('div.grid.grid-cols-5.divide-x')
                    
                    # Initialize prices dictionary for this source
                    source_prices = {}
                    
                    # Process each row
                    for row in price_rows[1:]:  # Skip header row
                        cols = row.find_all('div', class_='p-3')
                        
                        if len(cols) == 3:
                            weight = cols[0].text.strip()
                            sell_price = cols[1].text.strip().replace('Rp', '').replace('.', '')
                            buyback_price = cols[2].text.strip().replace('Rp', '').replace('.', '')
                            
                            # Normalize weight format
                            if weight == '0.5':
                                normalized_weight = '05gr'
                            else:
                                normalized_weight = f"{weight.replace('.', '')}gr"
                            
                            source_prices[normalized_weight] = {
                                'price': sell_price,
                                'buyback': buyback_price
                            }
                    
                    # Store processed data
                    processed_data["sources"][source_name] = {
                        "prices": source_prices
                    }
                    
                    # logging.debug(f"Processed prices for {source_name}: {source_prices}")
                else:
                    logging.error(f"Could not find price element for {source_name}")
            
            except Exception as source_error:
                logging.error(f"Detailed error processing {source_name}: {source_error}", exc_info=True)
        
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
    
    # Git operations
    print("Performing git operations...")
    import subprocess

    try:
        # Change to result directory for git operations
        result_dir = "./"
        
        # Git add all files
        print("Running git add . ")
        subprocess.run(["git", "add", "."], check=True, cwd=result_dir)
        
        # Git commit with timestamp
        from datetime import datetime 
        commit_message = f"Update data (galeri24)"
        print(f"Running git commit with message: {commit_message}")
        subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=result_dir)
        
        # Git push
        print("Running git push")
        subprocess.run(["git", "push"], check=True, cwd=result_dir)
        
        print("Git operations completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
    except Exception as e:
        print(f"Error during git operations: {e}")

    # Exit code
    print("Script finished successfully.")
    exit(0) 

if __name__ == "__main__":
    main()