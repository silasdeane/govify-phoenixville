import requests
from bs4 import BeautifulSoup

def scrape_quicklinks(url, output_file="quicklinks.txt"):
    # Get the page content
    response = requests.get(url)
    response.raise_for_status()  # raise error if the request failed

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find all anchor tags
    links = soup.find_all("a")
    
    with open(output_file, "w", encoding="utf-8") as f:
        for link in links:
            link_text = link.get_text(strip=True)
            href = link.get("href")
            # Only include links with an href attribute
            if href:
                f.write(f"{link_text}: {href}\n")

if __name__ == "__main__":
    url = "https://www.phoenixville.org/QuickLinks.aspx"
    scrape_quicklinks(url)
    print("Quick links have been saved to quicklinks.txt")
