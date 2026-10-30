import json
from pathlib import Path

file_path = Path("htmls/youtube_next_batch_005.json")

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

action = data["onResponseReceivedActions"][0]

print("Action keys:", list(action.keys()))

items = action["appendContinuationItemsAction"]["continuationItems"]

for i, item in enumerate(items):
    video = item.get("richItemRenderer", {})

    if video:
        print(f"\nItem {i}: richItemRenderer keys")
        print(list(video.keys()))

# Search the saved response for continuation-related keys.
def find_continuation_keys(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if "continuation" in key.lower():
                print(f"\nFound: {path}.{key}")
                if isinstance(value, (dict, list)):
                    print(json.dumps(value, indent=2)[:1500])
                else:
                    print(value)

            find_continuation_keys(value, f"{path}.{key}")

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            find_continuation_keys(value, f"{path}[{i}]")

print("\n--- Searching for continuation keys ---")
find_continuation_keys(data)

# This tells me there is no-next patch 