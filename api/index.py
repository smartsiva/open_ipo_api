from flask import Flask
import requests
from lxml import html
import re

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "Welcome To IPO Alerts, Try /fetch_mainline or /fetch_upcoming"
    

@app.route('/fetch_mainline')
def retrieve_mainline_data():
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
            # Check if the row has the class 'color-green'
            if 'color-green' in row.get('class', ''):
                row_dict = {}

                # Extract columns from the row
                columns = row.xpath('.//td')
                for each in columns:
                    data_label = each.get('data-label')
                    if data_label == "IPO":
                        # Use regular expressions to extract specific information
                        row_dict["company_name"] = re.search(r'(.+?)Open', each.text_content()).group(1) if re.search(
                            r'(.+?)Open', each.text_content()) else None
                        row_dict["subscription_ratio"] = re.search(r'Sub:(.+?)\)', each.text_content()).group(
                            1) if re.search(
                            r'Sub:(.+?)\)', each.text_content()) else None
                    else:
                        row_dict[data_label] = each.text_content()

                results.append(row_dict)
        if results == []:
            return {"Message" : "No Mainline IPO is Currently Open, Please Check Tomorrow!"}
        return results

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
