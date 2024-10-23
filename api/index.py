from flask import Flask, jsonify
import requests
from lxml import html
import re
import pandas as pd
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

def fetch_data(url):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36'
}

    with requests.get(url, headers=headers) as response:
        if response.status_code == 200:
            return pd.read_html(response.content, attrs={'id': "mainTable"})[0]
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            return None

def extract_ipo_data(df):
    df[['companyName', 'gmp', 'listingGain']] = df['IPO'].str.extract(r'(.*)GMP:₹([\d.]+) \(([\d.]+%)\)(?:O|CT)$')
    df = df.rename(columns={'RII': 'retailSubsRatio',
                            'Close Date': 'closeDate',
                            'IPO Price': 'ipoPrice'})
    return df

def create_api_response(df):
    subset_columns = ['companyName', 'gmp', 'listingGain', 'retailSubsRatio','closeDate', 'ipoPrice']
    subset_df = df[subset_columns].copy()
    result_dict = subset_df.to_dict(orient='records')

    return {
        'ipoData': result_dict,
        'message': 'API Response Successful',
        'status': 'success'
    }

@app.route("/")
def hello_world():
    return "Welcome To IPO Alerts, Try /fetch_mainline or /fetch_upcoming"


@app.route('/fetch_mainline', methods=['GET'])
def retrieve_mainline_data():
    url = "https://www.investorgain.com/report/ipo-subscription-live/333/ipo/"
    main_table = fetch_data(url)

    if main_table is not None:
        open_ipo = main_table[main_table['IPO'].str.endswith(('O','CT'))].copy()
        open_ipo = extract_ipo_data(open_ipo)

        api_response = create_api_response(open_ipo)
        return jsonify(api_response)
    else:
        return jsonify({'message': 'Failed to fetch data', 'status': 'error'}), 500

@app.route('/fetch_upcoming')
def retrieve_upcoming_ipo():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"

    # Initialize results to avoid UnboundLocalError
    results = []

    # Send an HTTP request to the webpage
    response = requests.get(url)

    if response.status_code == 200:
        # Parse the HTML content using lxml
        tree = html.fromstring(response.content)

        # Find the table element
        table_element = tree.xpath('//table[@id="mainTable"]')

        if not table_element:
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
            return jsonify({"message": "No Upcoming IPO, Please Check Tomorrow!", "status": "error"}), 404

        # Convert results into API format with 'ipoData'
        api_response = {
            'ipoData': results,
            'message': 'API Response Successful',
            'status': 'success'
        }
        return jsonify(api_response)
    else:
        return jsonify({"message": "Failed to fetch data", "status": 'error'}), 500

