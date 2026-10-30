import requests
import os
import json
import pandas as pd
import joblib 

def create_embeddings(text_list):
    r = requests.post("http://localhost:11434/api/embed", # Than add this api/embeddings Refernce:(From ollama documentation ).
              json={
                  "model":"bge-m3",
                  "input":text_list
              })

    embedding = r.json()['embeddings']
    return embedding


# At first we will read all our jsons files .
# print(jsons)
jsons = os.listdir("newjsons")
chunk_id = 0 # For Creating chunk id .

my_dicts = [] # Empty list to store dictonaries 
for json_file in jsons:
    with open(f"newjsons/{json_file}") as f: # Loading and reading all jsons
        content = json.load(f)
    print(f"Creating embeddings for {json_file}")

    embeddings = create_embeddings([c['text'] for c in content['chunks']])# Taking all embeddings at once, It is a list comprehension Which gives me list of all the 'text' of the json than i will pass this to the function create_embedding() function ,it creates all embeddings at once     .At final i will use i enumerate()

    # What is enumerate(),it gives you index and your's iterable . 
    # The for loop goes through the original chunks one by one, allowing you to attach the correct embedding to each chunk by using enumerator .
    for i, chunk in enumerate(content['chunks']): 
        chunk['chunk_id'] = chunk_id
        chunk['embedding']=  embeddings[i]
        chunk_id += 1
        my_dicts.append(chunk)
        # print(chunk) # This extract all the chunks for the json file's

        # Add on Using temporary conditional statement .
        # if(i==3): # Read 5 chunks for now
        #     break

    # break
# We process our text in a batch for faster embedding creation .



# print(my_dicts)

# Creating our DataFrame 
df = pd.DataFrame.from_records(my_dicts) # from_records() is used convert list of dictionaries into a DataFrame 
# print(df)

# Saving DataFrame into joblib 
joblib.dump(df,'embeddings.joblib')




# e = create_embeddings(["I like parties" ,"I like Monday"]) 
# print(e) # For testing

