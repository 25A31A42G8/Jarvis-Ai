from ddgs import DDGS

query = "latest technology news"

results = DDGS().text(
    query,
    region="in-en",
    max_results=3
)

for result in results:
    print("\nTITLE:", result["title"])
    print("URL:", result["href"])
    print("INFO:", result["body"])