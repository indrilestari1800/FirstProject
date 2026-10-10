import cloudscraper
from bs4 import BeautifulSoup

TARGET_URL = "https://oii.la/mNyeXyUXi"

def search():
    scraper = cloudscraper.create_scraper()
    response = scraper.get(TARGET_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form")

    url = form.get("action","")
    print(url)
    tag_inputs = form.find_all("input")
    payloads = []

    for tag_input in tag_inputs:
        name = tag_input.get("name","")
        value = tag_input.get("value","")
        payloads.append({"name":name, "value":value})

        print(name,value)



    open("response.txt","w").write(str(form))

search()