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
import hashlib
import gspread
from google.oauth2.service_account import Credentials

def generate_entry_hash(entry):
    """
    entry: dict with fields like username, category, outcome, etc.
    """
    # Concatenate the fields into a string (adjust fields as needed)
    hash_input = ",".join([
        entry.get("category", ""),
        entry.get("outcome", ""),
        entry.get("mvp", ""),
        str(entry.get("goals", 0)),
        str(entry.get("shots", 0)),
        str(entry.get("assists", 0)),
        str(entry.get("saves", 0)),
        str(entry.get("mmr", ""))
    ])

    # Generate SHA256 hash (you can use md5 if preferred)
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

# 1. Set up headless browser
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=chrome_options
)

# 2. Navigate to the page
url = "https://rocketleague.tracker.network/rocket-league/profile/steam/76561198094621822/matches"
driver.get(url)

# Extract username from profile
try:
    username_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.trn-ign__username"))
    )
    username = username_element.text.strip()
except Exception as e:
    print("Could not find username:", e)
    username = None

# 3. Wait until the stats table is present
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sessions"))
)

soup = BeautifulSoup(driver.page_source, "html.parser")
all_match_data = []

sessions = soup.find_all("table", class_="session")

for session_index, session in enumerate(sessions, start=1):
    matches = session.find_all("div", class_="match")
    now = datetime.now()
    date_stamp = now.strftime("%Y-%m-%d")
    time_stamp = now.strftime("%H:%M") 
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
                win = None
            is_mvp = "MVP" if "MVP" in result_text else ""
        else:
            win = None
            is_mvp = ""

        mmr_div = match.find("div", class_="match__rating--value")
        if mmr_div:
            mmr_text = mmr_div.text.strip().replace(",", "")
            try:
                mmr = int(mmr_text)
            except ValueError:
                mmr = None
        else:
            mmr = None

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
                    # raw_stat = gs_text.split("(")[0].strip()
                    # goals_str, shots_str = [x.strip() for x in gs_part.split("/")]
                    # goals = int(goals_str)
                    # shots = int(shots_str)
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
        
        entry_hash = generate_entry_hash(entry)
        
        all_match_data.append({
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

# Path to your service account key file
SERVICE_ACCOUNT_FILE = './keys/rlsheet-470421-bfaed8e9f142.json'

# Define the scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Authenticate and create client
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Open the spreadsheet by its name
spreadsheet = client.open("RLData")

# Access the specific worksheet (tab) named "DB"
worksheet = spreadsheet.worksheet("DB")

columns = [
    "category", "total_games", "outcome", "mvp", "goals", "shots",
    "assists", "saves", "mmr", "date_stamp", "time_stamp", "entry_hash"
]

# Now all_match_data contains match info grouped by session index
for match in all_match_data:
    # print(f"{username},{match['category']},{match['total_games']},{match['outcome']},{match['mvp']},{match['goals']},{match['shots']},{match['assists']},{match['saves']},{match['mmr']},{match['date_stamp']},{match['time_stamp']},{match['entry_hash']}")
    row = [match[col] if match[col] is not None else '' for col in columns]
    print(row)
    worksheet.append_row(row, table_range='A1')


