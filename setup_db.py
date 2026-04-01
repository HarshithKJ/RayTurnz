import requests
import json
import urllib3

urllib3.disable_warnings()

print("🚀 Attempting to download ALL 45,000+ Mutual Funds from the live server...")
url = "https://api.mfapi.in/mf"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

try:
    print("📡 Pinging api.mfapi.in...")
    response = requests.get(url, headers=headers, timeout=60, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        print(f"🟢 SUCCESS! The server is awake. Downloaded {len(data)} funds.")
        
        # Build the massive dictionary
        fund_dict = {item['schemeName']: str(item['schemeCode']) for item in data}
        
        # Save the massive database to your hard drive
        with open("mf_database.json", "w") as f:
            json.dump(fund_dict, f)
            
        print("✅ Full database saved! You can now run the Streamlit app.")
        
    elif response.status_code == 502:
        print("❌ ERROR 502: The official Indian Mutual Fund server is STILL down.")
        print("⚠️ We cannot get the 45,000 funds until their IT engineers fix their servers. You will have to use the emergency 10-fund list for now.")
    else:
        print(f"❌ Failed to connect. Status Code: {response.status_code}")
        
except Exception as e:
    print(f"❌ Network/Firewall Error: {e}")