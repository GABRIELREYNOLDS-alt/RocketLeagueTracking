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
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import random
import hashGen

# Set up headless browser
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=chrome_options
)

with open('urls.txt', 'r') as file:
    urls = file.readlines()
    
urls = [url.strip() for url in urls]
count = 0
for url in urls:
    driver = webdriver.Chrome()

    driver.get(url)
    
    time.sleep(3)
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Extract username from profile
    try:
        username_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.trn-ign__username"))
        )
        username = username_element.text.strip()
    except Exception as e:
        print("Could not find username:", e)
        username = None
       
    if username == None:
        try:
            # Wait for the second element (ph-details__name)
            username_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.ph-details__name"))
            )
            # If found, print the name
            username = username_element.text.strip()
            
        except Exception as e:
            # Handle if the ph-details__name element is not found
            print(f"Error finding name on {url}: {e}")
            
    # Wait until the stats table is present
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.sessions"))
    )

    # Parse HTML to extract all session tables
    soup = BeautifulSoup(driver.page_source, "html.parser")
    sessions = soup.find_all("table", class_="session")

    # Get current time
    now = datetime.now()
    date_stamp = now.strftime("%Y-%m-%d")
    time_stamp = now.strftime("%H:%M")

    all_match_data = []
    for session_index, session in enumerate(sessions, start=1):
        matches = session.find_all("div", class_="match") 
        for match in matches:
            category_div = match.find("div", class_="match__metadata--playlist")
            category = category_div.text.strip() if category_div else None
            if category is None:
                continue

            result_div = match.find("div", class_="match__metadata--result")
            if result_div:
                result_text = result_div.get_text(separator=" ", strip=True)
                multiple_games = re.search(r'\d+', result_text)
                if multiple_games:
                    total_games = int(multiple_games.group())
                else:
                    total_games = 1
                if "Win" in result_text:
                    outcome = "Win"
                elif "Defeat" in result_text:
                    outcome = "Loss"
                else:
                    outcome = ""
                is_mvp = "MVP" if "MVP" in result_text else ""
            else:
                outcome = ""
                is_mvp = ""

            mmr_div = match.find("div", class_="match__rating--value")
            if mmr_div:
                mmr_text = mmr_div.text.strip().replace(",", "")
                try:
                    mmr = int(mmr_text)
                except ValueError:
                    mmr = ""
            else:
                mmr = ""

            goals = shots = assists = saves = 0
            stat_divs = match.find_all("div", class_="match__stat")
            for stat in stat_divs:
                label_div = stat.find("div", class_="match__stat--label")
                value_div = stat.find("div", class_="match__stat--value")
                if not label_div or not value_div:
                    continue
                label = label_div.text.strip().lower()

                if label == "goals / shots":
                    gs_text = value_div.text.strip()
                    stats = re.findall(r'\d+', gs_text)
                    try:
                        goals, shots = int(stats[0]), int(stats[1])
                    except Exception:
                        goals = shots = 0

                elif label == "assists":
                    try:
                        assists = int(value_div.text.strip())
                    except ValueError:
                        assists = 0

                elif label == "saves":
                    try:
                        saves = int(value_div.text.strip())
                    except ValueError:
                        saves = 0
            
            entry = ({
                "username": username,
                "category": category,
                "total_games": total_games,
                "outcome": outcome,
                "mvp": is_mvp,
                "goals": goals,
                "shots": shots,
                "assists": assists,
                "saves": saves,
                "mmr": mmr,
            })
            
            entry_hash = hashGen.generate_entry_hash(entry)
            
            all_match_data.append({
                "username": username,
                "category": category,
                "total_games": total_games,
                "outcome": outcome,
                "mvp": is_mvp,
                "goals": goals,
                "shots": shots,
                "assists": assists,
                "saves": saves,
                "mmr": mmr,
                "date_stamp": date_stamp,
                "time_stamp": time_stamp,
                "entry_hash": entry_hash
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
        "username", "category", "total_games", "outcome", "mvp", "goals", "shots",
        "assists", "saves", "mmr", "date_stamp", "time_stamp", "entry_hash"
    ]

    # Open the spreadsheet by its name
    spreadsheet = client.open("RLData")

    # Access the specific worksheet (tab) named "DB"
    worksheet = spreadsheet.worksheet("DB")

    # Get all existing entry hashes from the sheet
    existing_hashes = set()
    existing_data = worksheet.get_all_values()

    # Skip header, get only the entry_hash column
    for row in existing_data[1:]:
        existing_hashes.add(row[-1])
            
    # Prepare only new entries
    new_entries = []
    for match in all_match_data:
        if match["entry_hash"] not in existing_hashes:
            row = [match[col] if match[col] is not None else '' for col in columns]
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


