# app.py
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import re
# from selenium.webdriver.chrome.service import Service as ChromeService
# from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

@app.route('/')
def main():
    return "hi"

@app.route('/fetch_mainline')
def retrieve_mainline_data():
    def initialise_chrome_driver():
        return webdriver.Chrome()

    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"

    driver = initialise_chrome_driver()
    driver.get(url)

    table_element = driver.find_element(By.ID, 'mainTable')
    rows = table_element.find_elements(By.TAG_NAME, 'tr')

    results = []
    for row in rows:
        if 'color-green' in row.get_attribute('class'):
            row_dict = {}
            columns = row.find_elements(By.TAG_NAME, 'td')
            for each in columns:
                data_label = each.get_attribute("data-label")
                if data_label == "IPO":
                    row_dict["company_name"] = re.search(r'(.+?)Open', each.text).group(1) if re.search(r'(.+?)Open',
                                                                                                        each.text) else None
                    row_dict["subscription_ratio"] = re.search(r'Sub:(.+?)\)', each.text).group(1) if re.search(
                        r'Sub:(.+?)\)', each.text) else None
                else:
                    row_dict[data_label] = each.text
            results.append(row_dict)
    return results

