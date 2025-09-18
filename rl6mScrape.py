from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import random

# Set up headless browser
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=chrome_options
)

with open('rl6murls.txt', 'r') as file:
    urls = file.readlines()
    
urls = [url.strip() for url in urls]
count = 0

all_series_data = []
for url in urls:
    driver = webdriver.Chrome()

    driver.get(url)
    
    time.sleep(3)
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Extract username from profile
    try:
        username_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3"))
        )
        username = username_element.text.strip()
        username = username.replace(" - Match History", "")
    except Exception as e:
        print("Could not find username:", e)
        username = None
            
    # Wait until the stats table is present
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.history-table"))
    )

    # Parse HTML to extract all session tables
    soup = BeautifulSoup(driver.page_source, "html.parser")
    sessions = soup.find_all("table")

    # Get current time
    now = datetime.now()

    outcome = ""
    for session_index, session in enumerate(sessions, start=1):
        Series = session.find_all("tr") 
        # print(Series)
        for series in Series[1:]:
            players = []
            seriesData = series.find_all("td")
            id = seriesData[0].get_text()
            if len(seriesData) == 1 and id == 'No data available':
                continue
            occurrence = seriesData[1].get_text()
            delta = int(re.search(r'\d+', occurrence).group())
            if occurrence[1] == 'h':
                date = now - timedelta(hours=delta)
            elif occurrence[1] == 'd':
                date = now - timedelta(days=delta)
            elif occurrence[1] == 'w':
                date = now - timedelta(weeks=delta)
            elif occurrence[1] == 'm':
                date = now - timedelta(months=delta)
            else:
                date = now - timedelta(days=delta*365)
            date_stamp = date.strftime("%Y-%m-%d")
            time_stamp = date.strftime("%H:%M")
            
            for player in seriesData[2:8]:
                style = player.get('style') 
                if style != None:
                    username = player.get_text()
                    if style == 'background-color: green':
                        outcome = 'win'
                    else:
                        outcome = 'loss'
                players.append(player.get_text())
            
                
            MatchUserID = id + username    
            all_series_data.append({
                "username": username,
                "outcome": outcome,
                "date_stamp": date_stamp,
                "time_stamp": time_stamp,
                "player1": players[0],
                "player2": players[1],
                "player3": players[2],
                "player4": players[3],
                "player5": players[4],
                "player6": players[5],
                "MatchUserID": MatchUserID
            })  

    # Path to API key
    SERVICE_ACCOUNT_FILE = './keys/rlsheet-470421-bfaed8e9f142.json'

    # Define the scope for uploading to google sheets
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # Authenticate and create client
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    columns = [
        "username", "outcome", "date_stamp", "time_stamp", "player1",
         "player2", "player3", "player4", "player5", "player6", "MatchUserID"
    ]

    # Open the spreadsheet by its name
    spreadsheet = client.open("RLData")

    # Access the specific worksheet (tab) named "DB"
    worksheet = spreadsheet.worksheet("DB6M")

    # Get all existing entry hashes from the sheet
    existing_ids = set()
    existing_data = worksheet.get_all_values()

    # Skip header, get only the entry_hash column
    for row in existing_data[1:]:
        existing_ids.add(row[-1])
            
    # Prepare only new entries
    new_entries = []
    for series in all_series_data:
        if series["MatchUserID"] not in existing_ids:
            row = [series[col] if series[col] is not None else '' for col in columns]
            new_entries.append(row)

    # Insert new entries at the top (after header), in reverse order
    # so most recent shows at top in correct order
    for row in reversed(new_entries):
        worksheet.insert_row(row, index=2)  # index=2: insert just below header
        print("Inserted:", row)
        count = count + 1
        if count > 25:
            time.sleep(130)
            count = 0

    driver.close()

