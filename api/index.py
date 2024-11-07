from flask import Flask, jsonify
import requests
from lxml import html
import re
import pandas as pd
from flask_cors import CORS
import logging

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
    }

    logging.info(f"Fetching data from {url}")
    with requests.get(url, headers=headers) as response:
        if response.status_code == 200:
            logging.info(f"Successfully fetched data from {url}")
            return pd.read_html(response.content)[0]
        else:
            logging.error(f"Failed to fetch data from {url}. Status Code: {response.status_code}")
            return None

def extract_ipo_data(df):
    logging.info("Extracting IPO data from DataFrame")
    df[['companyName', 'gmp', 'listingGain']] = df['IPO'].str.extract(r'(.*)GMP:₹([\d.]+) \(([\d.]+%)\)(?:O|CT)$')
    df = df.rename(columns={'RII': 'retailSubsRatio',
                            'Close Date': 'closeDate',
                            'IPO Price': 'ipoPrice'})
    logging.info("Successfully extracted IPO data")
    return df

def create_api_response(df):
    logging.info("Creating API response from DataFrame")
    subset_columns = ['companyName', 'gmp', 'listingGain', 'retailSubsRatio', 'closeDate', 'ipoPrice']
    subset_df = df[subset_columns].copy()
    result_dict = subset_df.to_dict(orient='records')

    logging.info("API response successfully created")
    return {
        'ipoData': result_dict,
        'message': 'API Response Successful',
        'status': 'success'
    }

def add_ordinal_suffix(day):
    """Add ordinal suffix to a day number."""
    if day.endswith('11') or day.endswith('12') or day.endswith('13'):
        return f"{day}th"
    elif day.endswith('1'):
        return f"{day}st"
    elif day.endswith('2'):
        return f"{day}nd"
    elif day.endswith('3'):
        return f"{day}rd"
    else:
        return f"{day}th"


def convert_date_range(days, month):
    """Convert date range from 'DD-DD MMM YYYY' to 'Dth MMM YYYY' format."""
    pattern = r'(\d{1,2})-(\d{1,2})'

    match = re.match(pattern, days)
    if match:
        start_day, end_day = match.groups()

        start_date = f"{add_ordinal_suffix(start_day)} {month}"
        end_date = f"{add_ordinal_suffix(end_day)} {month}"

        return start_date,end_date
    else:
        return "-","-"

@app.route("/")
def hello_world():
    logging.info("Accessed root endpoint")
    return "Welcome To IPO Alerts, Try /fetch_mainline or /fetch_upcoming"

@app.route('/fetch_mainline_old', methods=['GET'])
def retrieve_mainline_data():
    url = "https://www.investorgain.com/report/ipo-subscription-live/333/ipo/"
    main_table = fetch_data(url)

    if main_table is not None:
        open_ipo = main_table[main_table['IPO'].str.endswith(('O','CT'))].copy()
        open_ipo = extract_ipo_data(open_ipo)

        api_response = create_api_response(open_ipo)
        logging.info("Mainline IPO data successfully retrieved and sent as response")
        return jsonify(api_response)
    else:
        logging.error("Failed to retrieve mainline IPO data")
        return jsonify({'message': 'Failed to fetch data', 'status': 'error'}), 500

@app.route('/fetch_mainline', methods=['GET'])
def retrieve_mainline_data_2():
    url = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/"
    main_table = fetch_data(url)
    main_table.columns = main_table.iloc[0]
    
    # Remove the first row from the DataFrame
    main_table = main_table.drop(main_table.index[0])
    if main_table is not None:
        transformed_data = []
    
        for index, row in main_table.iterrows():
        # Extract values and convert as needed
            if "mainline" in row['Type'].lower():
                ipo_price = 0 if '–' in row['Price'] or "-" in row['Price'] else row['Price'].replace('₹', '').replace(',', '')
                gmp = 0 if '–' in row['IPO GMP'] or "-" in row['IPO GMP'] else row['IPO GMP'].replace('₹', '').replace(',', '')
                gain = "0%" if '–' in row['Gain'] or "-" in row['Gain'] else row['Gain']
                open_date, close_date = convert_date_range(row['Current IPOs'].split(" ")[-2], row['Current IPOs'].split(" ")[-1])
                ipo_data = {
                    'companyName': " ".join(row['Current IPOs'].split(" ")[:-2]),
                    'gmp': int(gmp), # Remove ₹ and comma
                    'ipoPrice': int(ipo_price),  # Convert to int
                    'listingGain': gain,
                    'retailSubsRatio': 'N/A',  # Assuming a placeholder value for retail subscription ratio
                    'closeDate': close_date,
                    'openDate': open_date# Assuming this is the closing date
                }
    
                transformed_data.append(ipo_data)
    
        # Prepare the final JSON structure
        result = {
            'ipoData': transformed_data,
            'message': 'API Response Successful',
            'status': 'success'
        }
        return jsonify(result)
    
    # Transform and print the JSON
    else:
        jsonify({'message': 'Failed to fetch data', 'status': 'error'}), 500
    
@app.route('/fetch_upcoming')
def retrieve_upcoming_ipo():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"

    # Initialize results to avoid UnboundLocalError
    results = []

    logging.info(f"Fetching upcoming IPO data from {url}")
    # Send an HTTP request to the webpage
    response = requests.get(url)

    if response.status_code == 200:
        logging.info(f"Successfully fetched upcoming IPO data from {url}")
        # Parse the HTML content using lxml
        tree = html.fromstring(response.content)

        # Find the table element
        table_element = tree.xpath('//table[@id="mainTable"]')

        if not table_element:
            logging.warning("Table not found on the webpage")
            return jsonify({'message': 'Table not found', 'status': 'error'}), 404

        table_element = table_element[0]

        # Extract rows from the table
        rows = table_element.xpath('.//tr')

        for row in rows:
            row_dict = {}
            columns = row.xpath('.//td')
            if columns:
                # Extract relevant columns
                if "Upcoming" in columns[0].text_content():
                    for each in columns:
                        data_label = each.get('data-label')
                        if data_label == "IPO":
                            row_dict["Company_Name"] = each.text_content().split("Upcoming")[0]
                        elif data_label in {"Open", "Close", "Est Listing", "Price"}:
                            row_dict[data_label] = each.text_content()
                    results.append(row_dict)

        # If no results found, return a message
        if not results:
            logging.info("No upcoming IPOs found")
            return jsonify({"message": "No Upcoming IPO, Please Check Tomorrow!", "status": "error"}), 404

        # Convert results into API format with 'ipoData'
        api_response = {
            'ipoData': results,
            'message': 'API Response Successful',
            'status': 'success'
        }
        logging.info("Upcoming IPO data successfully retrieved and sent as response")
        return jsonify(api_response)
    else:
        logging.error(f"Failed to fetch upcoming IPO data. Status Code: {response.status_code}")
        return jsonify({"message": "Failed to fetch data", "status": 'error'}), 500
