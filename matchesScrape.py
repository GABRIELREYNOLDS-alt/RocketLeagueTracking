from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

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

# 3. Wait until the stats table is present
WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sessions"))
)

soup = BeautifulSoup(driver.page_source, "html.parser")
all_match_data = []

sessions = soup.find_all("table", class_="session")

for session_index, session in enumerate(sessions, start=1):
    matches = session.find_all("div", class_="match")
    for match in matches:
        category_div = match.find("div", class_="match__metadata--playlist")
        category = category_div.text.strip() if category_div else None
        if category is None or category.lower() == "multiple":
            continue

        result_div = match.find("div", class_="match__metadata--result")
        if result_div:
            result_text = result_div.get_text(separator=" ", strip=True)
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
                gs_part = gs_text.split()[0]
                try:
                    goals_str, shots_str = [x.strip() for x in gs_part.split("/")]
                    goals = int(goals_str)
                    shots = int(shots_str)
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

        all_match_data.append({
            "session": session_index,
            "category": category,
            "outcome": outcome,
            "mvp": is_mvp,
            "goals": goals,
            "shots": shots,
            "assists": assists,
            "saves": saves,
            "mmr": mmr,
        })

# Now all_match_data contains match info grouped by session index
for match in all_match_data:
    print(f"{match['category']}, {match['outcome']}, {match['mvp']}, {match['goals']}, {match['shots']}, {match['assists']}, {match['saves']}, {match['mmr']}")


