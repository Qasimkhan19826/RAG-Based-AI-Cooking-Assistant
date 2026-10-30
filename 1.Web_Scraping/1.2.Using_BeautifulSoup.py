# By using beautifulsoup ,i will collect this elements 
# 1.video title,
# 2.Time duration (Important),
# 3.When Uploaded ,
# 4 .Total views. 
# 5.Video_ID


from bs4 import BeautifulSoup

with open("htmls/youtube_channel.html","r",encoding="utf-8") as f:
    content = f.read()

soup = BeautifulSoup(content,"html.parser")

# We inspect the youtube ,At first we will extract the title 

# after inspecting we found this html structure h3.a.span
# Problem occured in the scraped data there are a lot of missing 
# elements like h1 ,h3, are completely missing .

# But i found the title in the script tag ,let's see how i am can 
# extract the data.

scripts =soup.find_all("script")
# print(scripts)
