import requests
import json
import base64  
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = 'https://portal-hsbc-voiceinput-gcp.fano.ai/speech/recognize'

headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJmYW5vX3NwZWVjaF9kaWFyaXplX3F1b3RhX3N0cmF0ZWd5IjoiZGVmYXVsdCIsImZhbm9fc3BlZWNoX2dlbmVyYXRlX3ZvaWNlcHJpbnRfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfcmVjb2duaXplX3F1b3RhX3N0cmF0ZWd5Ijoic2tpcCIsImZhbm9fc3BlZWNoX3N0cmVhbWluZ19kZXRlY3RfYWN0aXZpdHlfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfc3RyZWFtaW5nX3JlY29nbml6ZV9xdW90YV9zdHJhdGVneSI6ImRlZmF1bHQiLCJmYW5vX3NwZWVjaF9yZXBsYWNlX3BocmFzZXNfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfc3ludGhlc2l6ZV9zcGVlY2hfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiaWF0IjoxNzQ5MTEzNjAxLCJleHAiOjIwNjQ2ODI4NTAsImF1ZCI6ImZhbm8tc3BlZWNoLWdhdGV3YXkiLCJpc3MiOiJodHRwczovL2F1dGguZmFuby5haSIsInN1YiI6ImZhbm8tc3BlZWNoLWdhdGV3YXkifQ.b90NU8e1zs_HlbvosewJN0_GJpEcb2B7qOvA1rNNj8mGDrOM3j_Y_DKZsKi3S2ZgbekxrewW8nPb5KaZR-mpTq46W5T8MMgdBS6r3kGx__2A6sH-NPOzZiqbEfiFOXR5pHQLG7KucgxPSz0J3B_ZmwhT4T-mcxjnhOMx7ALEbFvBh964nlXDXZw9LGGUUbfZjv_CVVKvVD0dklI5HUxr11a1tvoZeugbzzF1VKdyiSp_lp45unoIPqI-rbZf75qclhufS43xaB8Ye0FYlp7khyE_d5gqG9pLj8uu3m1kjq8BUwJRFfcE-c_k6bYbiLDjY1KHLXqv2JQPW03OF_5Z4w',
    'Content-Type': 'application/json'
}

audio_path = 'testset/TC-1/Cantonese-HK/4FEN95kaPIo_noisy_0_4FEN95kaPIo.whisper.auto.gt_audio_17.mp3'

try:
    with open(audio_path, 'rb') as audio_file:
        audio_content = audio_file.read()
        base64_audio_bytes = base64.b64encode(audio_content)
        base64_audio_string = base64_audio_bytes.decode('utf-8')
except FileNotFoundError:
    print(f"Error: The audio file was not found at the path: {audio_path}")
    exit() 

data = {
    "config": {
        "languageCode": "yue"
    },
    "audio": {
        "content": base64_audio_string
    }
}

try:
    response = requests.post(url, headers=headers, json=data, verify=False)

    response.raise_for_status()

    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(response.json())

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
    print(f"Response content: {response.text}")
except requests.exceptions.RequestException as err:
    print(f"An error occurred: {err}")