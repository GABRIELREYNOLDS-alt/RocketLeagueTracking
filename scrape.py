from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".trn-table__container"))
)

# 4. Get fully rendered HTML and parse
html = driver.page_source
driver.quit()
soup = BeautifulSoup(html, "html.parser")

# 5. Find MMR value for "Ranked Doubles 2v2"
mmr_value = None
rows = soup.select("table.trn-table tbody tr")
for row in rows:
    playlist = row.select_one("td.name .playlist")
    if playlist and "Ranked Doubles 2v2" in playlist.text:
        mmr = row.select_one("td.rating .mmr .value")
        if mmr:
            mmr_value = mmr.text.strip()
        break

if mmr_value:
    print("Ranked Doubles 2v2 MMR:", mmr_value)
else:
    print("Could not find MMR for Ranked Doubles 2v2.")
