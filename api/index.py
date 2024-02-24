from flask import Flask, jsonify
import requests
from lxml import html
import re
import pandas as pd

app = Flask(__name__)

def fetch_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    with requests.get(url, headers=headers) as response:
        if response.status_code == 200:
            return pd.read_html(response.content, attrs={'id': "mainTable"})[0]
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            return None

def extract_ipo_data(df):
    df[['Company Name', 'GMP', 'Estimated Listing Gain']] = df['IPO'].str.extract(r'(.*)GMP:₹(\d+) \(([\d.]+%)\)[O]')
    df = df.rename(columns={'RII': 'Retail Subs Ratio'})
    return df

def create_api_response(df):
    subset_columns = ['Company Name', 'IPO Price', 'GMP', 'Estimated Listing Gain', 'Close Date', 'Retail Subs Ratio']
    subset_df = df[subset_columns].copy()
    result_dict = subset_df.to_dict(orient='records')

    return {
        'ipo_data': result_dict,
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
        open_ipo = main_table[main_table['IPO'].str.endswith('O')].copy()
        open_ipo = extract_ipo_data(open_ipo)

        api_response = create_api_response(open_ipo)
        return jsonify(api_response)
    else:
        return jsonify({'message': 'Failed to fetch data', 'status': 'error'}), 500


@app.route('/fetch_upcoming')
def retrieve_upcoming_ipo():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"

    # Send an HTTP request to the webpage
    response = requests.get(url)

    if response.status_code == 200:
        # Parse the HTML content using lxml
        tree = html.fromstring(response.content)
    
        # Find the table element
        table_element = tree.xpath('//table[@id="mainTable"]')[0]
    
        # Extract rows from the table
        rows = table_element.xpath('.//tr')
    
        results = []
        for row in rows:
            row_dict = {}
            columns = row.xpath('.//td')
            if columns:
                if "Upcoming" in columns[0].text_content():
                    for each in columns:
                        data_label = each.get('data-label')
                        if data_label == "IPO":
                            row_dict["Company_Name"] = each.text_content().split("Upcoming")[0]
                        elif data_label in {"Open", "Close", "Est Listing", "Price"}:
                            row_dict[data_label] = each.text_content()
                    results.append(row_dict)
    if results == []:
        return {"Message" : "No Upcoming IPO, Please Check Tomorrow!"}
    return results
