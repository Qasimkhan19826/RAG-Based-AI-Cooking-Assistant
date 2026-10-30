import numpy as np
import requests
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import json




def create_embeddings(text_list):
    r = requests.post("http://localhost:11434/api/embed", # Than add this api/embeddings Refernce:(From ollama documentation ).
              json={
                  "model":"bge-m3",
                  "input":text_list
              })

    embedding = r.json()['embeddings']
    return embedding

# RAG setup using local LLM from ollama 
def inference(prompt,model):
    r = requests.post("http://localhost:11434/api/generate", 
                  json={
                      "model":model,
                      "prompt":prompt,
                      "stream":True,
                  })

    full_response = ""

    for line in r.iter_lines():
        if line:
            data = json.loads(line)

            text = data.get("response", "")
            print(text, end="", flush=True)
            full_response += text

    print()
    return {"response": full_response}
    # response = r.json()
    # print(response)
    # return response
    
df = joblib.load('embeddings.joblib')

# Creating incoming query 
incoming_query = input("Ask a question : ")
# Creating input into embedding
question_embedding = create_embeddings([incoming_query])[0] # It will give you question embedding and at the other hand we have the columns in the DataFrame of embeddings.
# print(question_embedding) # Good it is converting question into embedding .


# Here ,we will find the cosine similarity of input between the stored embeddings data 

# What is cosine similarity ?
# Cosine similarity is a way to measure how similar two vectors are by comparing the angle between them.

# Find similarties of question_embedding with other embeddings .
# df['embedding'].values it gives you array (As an array of embeddings )

# print(np.vstack(df['embedding'].values)) # np.vstack() It creates 2d vector.
# print(np.vstack(df['embedding']).shape ) # Output:(6, 1024) ,(6 embeddings ,and their dimensions) We want this thing 


# Output:(6,) It means 6 embeddings (print(df['embedding'].values),print(df['embedding'].values)) and 
similarities = cosine_similarity(np.vstack(df['embedding'].values),[question_embedding]).flatten()
# print(similarities)
top_results =  1
max_indeces = similarities.argsort()[::-1][0:top_results] # [::-1] To reverse the array 
# print(max_indeces)
# print(similarities.argsort())
# Adding indeces 
new_df = df.loc[max_indeces]
# print(new_df[["title","number","text"]])

# Output:
# Creating embeddings for 01.2_minut_Mein_taiyar_Bhelpuri_Mumbai_special.json
# Ask a question : Can you give me murmure recipe
# [0.47684452 0.53135716 0.56437724 0.68680471]


# [3 2 1] 
#                                          title number                                               text
# 3  2_minut_Mein_taiyar_Bhelpuri_Mumbai_special      1           I have fried 2 bowl of Murmure on a pan.
# 2  2_minut_Mein_taiyar_Bhelpuri_Mumbai_special      1  If you like my recipe, please like and subscri...
# 1  2_minut_Mein_taiyar_Bhelpuri_Mumbai_special      1                       Today I am making Bhel Puri.
# # Now i am want the similarities indeces ,so i am can pull the data from my original database.
# # So we use np.argsort() : It gives you maximum value index


# Creating prompt for our LLM .
prompt = f'''
You are a cooking assistant for the Indian Kitchen Asma YouTube channel.
I am teaching cooking by using Indian Kitchen Asma youtube channel videos, Here are video subtitle chunks containing video title ,video number ,start time in seconds ,end time in seconds ,the text (which has the main content )at that time :

Rules:
1. If the chunks contain relevant recipe information, explain the available steps clearly.
2. Mention the video title and timestamps in seconds for the relevant steps.
3. If the chunks do not contain enough information, clearly say that the available subtitles do not provide enough details. Do not invent recipe steps.
4. If no relevant recipe chunks are provided, say you can only answer questions about recipes covered by Qasim's supplied videos.

STRICT RULES:
- Keep each line of the answer within approximately 50 characters .
Example:First, heat 2 tablespoons of ghee in a large cooking pan.( This sentence is for illustrative purpose only)
- Never ask the user to repeat or explain their question.
- If relevant subtitle data exists, explain the recipe steps supported by it.
- Include the video title and timestamps in seconds.
- Do not invent ingredients or cooking steps.
- If the subtitle data is irrelevant or insufficient, say so clearly.
- Use text to teach the recipe 
- list the ingredients for the user along with their quantities, if provided. Do not invent ingredients or quantities if they are missing from the data.
- Explain recipe step by step (Not give the whole paragraph like easy).
- Format the entire answer vertically using short paragraphs. avoid wide sentences or horizontally stretched formatting.

{new_df[["title","number","start","end","text"]].to_json(orient="records")}
----------------------------------------------------------------------------
"{incoming_query}"
User asked a question related to the chunks,you have to answer in a human way (don't mention the above format ,it's just for you ) where and how much content is taught in which video (In which video at what timestamp) and guide the user to go to that particular video.If user asks unrelated question ,tell him/her that you can only answer questions related to the given recipes by qasim.


'''


# Improved prompt by chatGpt .
# prompt = f"""
# You are a cooking assistant for the Indian Kitchen Asma YouTube channel.

# Answer the user's question using ONLY the provided subtitle chunks.

# Rules:
# 1. If the chunks contain relevant recipe information, explain the available steps clearly.
# 2. Mention the video title and timestamps in seconds for the relevant steps.
# 3. If the chunks do not contain enough information, clearly say that the available subtitles do not provide enough details. Do not invent recipe steps.
# 4. If no relevant recipe chunks are provided, say you can only answer questions about recipes covered by Qasim's supplied videos.

# SUBTITLE CHUNKS:
# {new_df[["title", "number", "start", "end", "text"]].to_json(orient="records")}

# USER QUESTION:
# {incoming_query}

# STRICT RULES:
# - Never ask the user to repeat or explain their question.
# - If relevant subtitle data exists, explain the recipe steps supported by it.
# - Include the video title and timestamps in seconds.
# - Do not invent ingredients or cooking steps.
# - If the subtitle data is irrelevant or insufficient, say so clearly.
# - Answer directly.

# Write a direct, helpful answer. Do not ask the user what their question is.
# """ 




# .to_json(orient="records")
# orient specifies the format of the JSON output.
# "records" means each DataFrame row becomes one JSON object.
# Each column name becomes a key, and its cell value becomes the corresponding value.

# Printing the result in more enhance way.
# iterrows() is a Pandas method that lets you iterate through a DataFrame one row at a time.
# for index ,item in new_df.iterrows():
#     print(index,item['number'],item['title'],item['text'],item['start'],item['end'])

# Checking our prompt is working or not .
with open("prompt.txt","w") as f :
    f.write(prompt)

# Giving user input to our local LLM
# Model 1 :llama3.2:3b  Good Performance
# Model 2 :qwen2.5:3b Ok Performance
# Model 3 :qwen3:4b Very Poor ,not suitable for normal laptop.


response = inference(prompt,"llama3.2:3b")['response']
# print(response)

with open("response.txt","w") as f :
    f.write(response)
