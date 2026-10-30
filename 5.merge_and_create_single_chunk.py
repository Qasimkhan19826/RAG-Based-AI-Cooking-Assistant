import os
import json

my_dicts = []

for filename in os.listdir("jsons"):
    if filename.endswith(".json"):

        file_path = os.path.join("jsons", filename)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Get all chunks of the recipe
        chunks = data["chunks"]

        # Merge all chunks into one
        merged_chunk = {
            "number": chunks[0]["number"],
            "title": chunks[0]["title"],
            "start": chunks[0]["start"],
            "end": chunks[-1]["end"],
            "text": " ".join(c["text"] for c in chunks)
        }

        # Save as a single chunk
        new_data = {
            "chunks": [merged_chunk],
            "text": merged_chunk["text"]
        }

        # Create output directory
        os.makedirs("newjsons", exist_ok=True)

        # Save JSON file
        with open(os.path.join("newjsons", filename), "w", encoding="utf-8") as json_file:
            json.dump(new_data, json_file, indent=4, ensure_ascii=False)