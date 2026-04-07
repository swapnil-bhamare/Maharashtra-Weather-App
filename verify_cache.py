import requests
import time

URL = "http://127.0.0.1:5000/weather"

def test_search(city):
    print(f"Searching for {city}...")
    start = time.time()
    res = requests.post(URL, json={"city": city})
    end = time.time()
    print(f"Response: {res.status_code}")
    print(f"Data: {res.json().get('success')}")
    print(f"Time taken: {round(end - start, 2)}s")
    return res.json()

if __name__ == "__main__":
    # First search (likely API call)
    test_search("Mumbai")
    
    # Second search (should be cache hit)
    print("\nSecond search (should be instant)...")
    test_search("Mumbai")

    # Third search (different city)
    print("\nSearching for a new city (Pune)...")
    test_search("Pune")
