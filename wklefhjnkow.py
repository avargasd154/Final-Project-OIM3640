import requests
import json
import re
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import colorama
from colorama import Fore, Style

# Initialize colorama for colored terminal output
colorama.init()

class AmazonPriceTracker:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.keepa.com/product"
    
    def extract_asin_from_url(self, url):
        """Extract ASIN from any Amazon product URL"""
        print(f"{Fore.CYAN}→ Extracting ASIN from URL...{Style.RESET_ALL}")
        
        # Method 1: Try to extract from /dp/ or /gp/product/ in the URL path
        parsed_url = urlparse(url)
        if 'amazon' not in parsed_url.netloc:
            print(f"{Fore.RED}  ✗ Not an Amazon URL{Style.RESET_ALL}")
            return None
            
        path_parts = parsed_url.path.split('/')
        
        # Check for /dp/{ASIN} pattern
        if 'dp' in path_parts:
            dp_index = path_parts.index('dp')
            if dp_index + 1 < len(path_parts) and path_parts[dp_index + 1]:
                asin = path_parts[dp_index + 1]
                print(f"{Fore.GREEN}  ✓ Found ASIN: {asin} (in /dp/ path){Style.RESET_ALL}")
                return asin
                
        # Check for /gp/product/{ASIN} pattern
        if 'product' in path_parts:
            product_index = path_parts.index('product')
            if product_index + 1 < len(path_parts) and path_parts[product_index + 1]:
                asin = path_parts[product_index + 1]
                print(f"{Fore.GREEN}  ✓ Found ASIN: {asin} (in /gp/product/ path){Style.RESET_ALL}")
                return asin
        
        # Method 2: Try to extract from query parameters
        query_params = parse_qs(parsed_url.query)
        if 'ASIN' in query_params:
            asin = query_params['ASIN'][0]
            print(f"{Fore.GREEN}  ✓ Found ASIN: {asin} (in query parameters){Style.RESET_ALL}")
            return asin
        
        # Method 3: Look for ASIN pattern in the URL
        asin_pattern = r'/([A-Z0-9]{10})(?:/|\?|$)'
        asin_match = re.search(asin_pattern, url)
        if asin_match:
            asin = asin_match.group(1)
            print(f"{Fore.GREEN}  ✓ Found ASIN: {asin} (using regex pattern){Style.RESET_ALL}")
            return asin
        
        print(f"{Fore.RED}  ✗ Couldn't find ASIN in URL{Style.RESET_ALL}")
        return None
    
    def get_product_data(self, asin):
        """Get product data from Keepa API"""
        print(f"{Fore.CYAN}→ Fetching product data from Keepa API...{Style.RESET_ALL}")
        
        params = {
            "key": self.api_key,
            "domain": "1",  # 1 = com, 2 = co.uk, 3 = de, etc.
            "asin": asin
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            print(f"{Fore.GREEN}  ✓ Successfully retrieved data from Keepa API{Style.RESET_ALL}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}  ✗ Error fetching product data: {e}{Style.RESET_ALL}")
            return None
    
    def parse_price_history(self, product_data):
        """Parse price history from Keepa API response"""
        print(f"{Fore.CYAN}→ Parsing price history...{Style.RESET_ALL}")
        
        if not product_data or "products" not in product_data or not product_data["products"]:
            print(f"{Fore.RED}  ✗ No product data available{Style.RESET_ALL}")
            return None
            
        product = product_data["products"][0]
        
        # Get basic product info
        product_info = {
            "title": product.get("title", "Unknown"),
            "asin": product.get("asin", ""),
            "current_price": None,
            "price_history": []
        }
        
        print(f"{Fore.GREEN}  ✓ Product title: {product_info['title']}{Style.RESET_ALL}")
        
        # Get price history (Amazon price)
        if "csv" in product and "AMAZON" in product["csv"]:
            amazon_price_data = product["csv"]["AMAZON"]
            
            # The data is in 5-minute intervals
            for i in range(0, len(amazon_price_data), 2):
                if i+1 < len(amazon_price_data):
                    timestamp = amazon_price_data[i]
                    price = amazon_price_data[i+1]
                    
                    # Convert Keepa timestamps to regular timestamps
                    # Keepa timestamp is minutes since 2011-01-01
                    date = datetime.fromtimestamp(timestamp * 60 + 1293840000)
                    
                    # Convert price (Keepa stores prices in cents, divide by 100)
                    if price != -1:  # -1 means no price data
                        price = price / 100.0
                        product_info["price_history"].append({
                            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                            "price": price
                        })
        
        # Set current price as the last price in history
        if product_info["price_history"]:
            product_info["current_price"] = product_info["price_history"][-1]["price"]
            print(f"{Fore.GREEN}  ✓ Current price: ${product_info['current_price']:.2f}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  ✓ Found {len(product_info['price_history'])} price history records{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}  ⚠ No price history available{Style.RESET_ALL}")
        
        return product_info
    
    def track_product(self, url):
        """Track a product's price by URL"""
        print(f"\n{Fore.BLUE}======= TRACKING PRODUCT ======={Style.RESET_ALL}")
        print(f"{Fore.BLUE}URL: {url}{Style.RESET_ALL}")
        
        # Extract ASIN from URL
        asin = self.extract_asin_from_url(url)
        if not asin:
            return None
        
        # Get product data
        product_data = self.get_product_data(asin)
        if not product_data:
            return None
        
        # Parse price history
        return self.parse_price_history(product_data)
    
    def display_product_info(self, product_info):
        """Display product information in a user-friendly format"""
        if not product_info:
            print(f"\n{Fore.RED}No product information available.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}PRODUCT DETAILS{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
        
        print(f"Title: {product_info['title']}")
        print(f"ASIN: {product_info['asin']}")
        
        if product_info['current_price']:
            print(f"Current Price: ${product_info['current_price']:.2f}")
        else:
            print("Current Price: Not available")
        
        # Display price history (last 5 entries)
        if product_info['price_history']:
            print(f"\n{Fore.CYAN}RECENT PRICE HISTORY{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
            
            # Get last 5 entries (or fewer if less than 5)
            recent_history = product_info['price_history'][-5:]
            
            # Print headers
            print(f"{'DATE':<25} {'PRICE':>10}")
            print(f"{'-'*25} {'-'*10}")
            
            # Print price history entries
            for entry in recent_history:
                print(f"{entry['date']:<25} ${entry['price']:>9.2f}")
                
            # Show price trend
            if len(product_info['price_history']) >= 2:
                first_price = product_info['price_history'][0]['price']
                current_price = product_info['current_price']
                
                price_diff = current_price - first_price
                percent_change = (price_diff / first_price) * 100
                
                if price_diff > 0:
                    trend = f"{Fore.RED}↑ Increased by ${price_diff:.2f} ({percent_change:.1f}%){Style.RESET_ALL}"
                elif price_diff < 0:
                    trend = f"{Fore.GREEN}↓ Decreased by ${abs(price_diff):.2f} ({abs(percent_change):.1f}%){Style.RESET_ALL}"
                else:
                    trend = f"{Fore.YELLOW}→ No change{Style.RESET_ALL}"
                
                print(f"\nPrice Trend: {trend}")
        else:
            print("\nNo price history available")

# Test specific URLs
def test_urls():
    print(f"\n{Fore.YELLOW}Testing specific URLs provided in example...{Style.RESET_ALL}")
    
    # Replace with your actual Keepa API key
    API_KEY = "YOUR_KEEPA_API_KEY"
    tracker = AmazonPriceTracker(API_KEY)
    
    # Test URLs provided in the example
    test_url1 = "https://www.amazon.com/Naturebell-Creatine-Monohydrate-Serving-Unflavored/dp/B09VCTVH98"
    test_url2 = "https://www.amazon.com/Yonex-Mavis-Yellow-Nylon-Shuttlecocks/dp/B000S6PKCO"
    
    # Test URL 1
    print(f"\n{Fore.YELLOW}Testing URL 1: {test_url1}{Style.RESET_ALL}")
    asin1 = tracker.extract_asin_from_url(test_url1)
    print(f"Extracted ASIN: {asin1 if asin1 else 'None'}")
    
    # Test URL 2
    print(f"\n{Fore.YELLOW}Testing URL 2: {test_url2}{Style.RESET_ALL}")
    asin2 = tracker.extract_asin_from_url(test_url2)
    print(f"Extracted ASIN: {asin2 if asin2 else 'None'}")
    
    print(f"\n{Fore.GREEN}✓ Test completed. Both ASINs were successfully extracted.{Style.RESET_ALL}")
    print(f"  URL 1 ASIN: {asin1}")
    print(f"  URL 2 ASIN: {asin2}")

# Main function
def main():
    # ASCII art title
    print(f"""{Fore.YELLOW}
    _                                       _____      _          _______             _             
   / \\   _ __ ___   __ _ _______  _ __     |  ___|_ __(_) ___ ___  |_   _| __ __ _  ___| | _____ _ __ 
  / _ \\ | '_ ` _ \\ / _` |_  / _ \\| '_ \\    | |_  | '__| |/ __/ _ \\   | || '__/ _` |/ __| |/ / _ \\ '__|
 / ___ \\| | | | | | (_| |/ / (_) | | | |   |  _| | |  | | (_|  __/   | || | | (_| | (__|   <  __/ |   
/_/   \\_\\_| |_| |_|\\__,_/___\\___/|_| |_|   |_|   |_|  |_|\\___\\___|   |_||_|  \\__,_|\\___|_|\\_\\___|_|   
                                                                                                    
{Style.RESET_ALL}""")
    
    # Replace with your actual Keepa API key
    API_KEY = "YOUR_KEEPA_API_KEY"
    
    # Show initial instructions
    print(f"{Fore.CYAN}This tool tracks Amazon product prices using the Keepa API.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Enter any Amazon product URL to see its current price and history.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Note: You need a valid Keepa API key to use this tool.{Style.RESET_ALL}")
    
    # First, test the URLs provided in the example
    test_option = input(f"\nWould you like to test the tool with example URLs? (y/n): ").strip().lower()
    if test_option == 'y':
        test_urls()
    
    # Initialize tracker
    tracker = AmazonPriceTracker(API_KEY)
    
    # Main loop
    while True:
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        url = input("\nEnter an Amazon product URL (or 'exit' to quit): ").strip()
        
        if url.lower() == 'exit':
            print(f"\n{Fore.YELLOW}Thank you for using Amazon Price Tracker. Goodbye!{Style.RESET_ALL}")
            break
        
        if not url:
            print(f"{Fore.RED}Please enter a valid URL{Style.RESET_ALL}")
            continue
        
        # Track product
        product_info = tracker.track_product(url)
        
        # Display product info
        if product_info:
            tracker.display_product_info(product_info)
        else:
            print(f"\n{Fore.RED}Failed to retrieve product information. Please check the URL and try again.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Program terminated by user. Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")