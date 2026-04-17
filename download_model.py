import whisper
import os
import urllib.request
import certifi

# Sometimes certifi is needed, whisper uses urllib
os.environ['SSL_CERT_FILE'] = certifi.where()

print("Downloading base model...")
url = whisper._MODELS["base"]
os.makedirs("./models", exist_ok=True)
whisper._download(url, "./models", False)
print("Download complete.")
