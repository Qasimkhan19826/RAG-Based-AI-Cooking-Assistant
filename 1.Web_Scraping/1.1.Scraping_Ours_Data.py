# Before using whisper we will discuss our new stratigies .

# Speech to text is a very complex process ,we try it 
# and failed it takes a lot of time just for 13;00 min 
# audio falied at 19:00 min model loading time 19 seconds 
# which is fail in Google colab with powerful runtime 

# New Strategy is :
# 1. We will collect data audio from our youtube channel .
# 2. We will write a prgram to fetch our all video details.
# 3. Than we will sort the audio in ascending order based on 
# time duration.
# 4. We will pick the less length duration audio .
# 5. At Final we list about 20 audios .

# Than we will extract 10 sec of the audio,
# We use 10 sec audio to write our whisper code in
# our laptop .

# Here ,I am will write a program 
# Which extracts the 1.video title, 2.Time duration (Important),
# 3.When Uploaded ,4 .Total views. 

# 1.But why we are writing the program to extract the data .
# because we have 418 number of videos in our youtube channel.

'''
My Logic 
import requests

a = requests.get("https://www.youtube.com/@IndianKitchen-fe7gk/videos")

# print(a.text)

with open(f"htmls/youtube_channel.html","w") as f:
    f.write(a.text)
'''


import requests
import os


url = "https://www.youtube.com/@IndianKitchen-fe7gk/videos"

a = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

a.raise_for_status()

os.makedirs("htmls", exist_ok=True)

with open("htmls/youtube_channel.html", "w", encoding="utf-8") as f:
    f.write(a.text)

print("HTML page saved successfully!")
print("Status code:", a.status_code)
print("HTML characters:", len(a.text))



