
import requests
from bs4 import BeautifulSoup

url = "http://www.ufcstats.com/fighter-details/cd3d7e37ff2d679c" # Ricky Turcios
print(f"Fetching {url}...")
resp = requests.get(url)
soup = BeautifulSoup(resp.content, 'html.parser')

print("\n--- Searching for SLpM ---")
elements = soup.find_all(string=lambda text: "SLpM" in text if text else False)
for el in elements:
    print(f"Found element: '{el}'")
    print(f"Parent: {el.parent}")
    print(f"Parent Class: {el.parent.get('class')}")
    print(f"Full Text of Parent: '{el.parent.get_text()}'")
    print("-" * 20)

print("\n--- History Table Debug ---")
table = soup.find('table', class_='b-fight-details__table')
if table:
    rows = table.find_all('tr')
    if len(rows) > 1:
        cols = rows[1].find_all('td')
        print(f"Col 0 (Result): '{cols[0].get_text().strip()}'")
        print(f"Col 1 (Opponent): '{cols[1].get_text().strip()}'")
