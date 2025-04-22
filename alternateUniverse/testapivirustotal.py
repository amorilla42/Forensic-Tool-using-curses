import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

apikey = os.getenv("APIVIRUSTOTAL")

filetoanalyze = "f010af5a2b987cd20272c57689d6794fae202540177229c13d9449c4e6bb9994"

url = "https://www.virustotal.com/api/v3/files/" + filetoanalyze

headers = {"accept": "application/json", 
           "x-apikey": apikey}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    formatted_response = json.loads(response.text)
    print(json.dumps(formatted_response, indent=4))
else:
    print(f"Error: {response.status_code}")
print(response.text)