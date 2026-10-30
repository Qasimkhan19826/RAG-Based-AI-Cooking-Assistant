
import re
import json
import requests

from pathlib import Path


# ============================================================
# STEP 1: FILE PATHS
# ============================================================

DATA_DIR = Path("htmls")
HTML_FILE = DATA_DIR / "youtube_channel.html"

DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# STEP 2: READ SAVED HTML
# ============================================================

if not HTML_FILE.exists():
    raise FileNotFoundError(f"Missing original HTML: {HTML_FILE}")

original_html = HTML_FILE.read_text(encoding="utf-8")


# ============================================================
# STEP 3: EXTRACT API KEY AND CLIENT VERSION
# ============================================================

api_key_match = re.search(
    r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"',
    original_html
)

version_match = re.search(
    r'"clientVersion"\s*:\s*"([^"]+)"',
    original_html
)

if not api_key_match or not version_match:
    raise ValueError("API key or client version not found in saved HTML.")

api_key = api_key_match.group(1)
client_version = version_match.group(1)


# ============================================================
# STEP 4: EXTRACT ytInitialData
# ============================================================

match = re.search(r"ytInitialData\s*=\s*", original_html)

if not match:
    raise ValueError("ytInitialData was not found in saved HTML.")

start = original_html.find("{", match.end())

if start == -1:
    raise ValueError("JSON opening brace was not found.")

depth = 0
in_string = False
escaped = False
initial_data = None

for i in range(start, len(original_html)):
    char = original_html[i]

    if in_string:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            in_string = False
    else:
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                initial_data = json.loads(original_html[start:i + 1])
                break

if initial_data is None:
    raise ValueError("Could not extract complete ytInitialData JSON.")


# ============================================================
# STEP 5: HELPER FUNCTIONS
# ============================================================

def walk_dicts(obj):
    """Visit every dictionary inside nested JSON data."""

    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from walk_dicts(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from walk_dicts(item)


def find_grid_token(data):
    """
    Find a continuation token inside a video-grid continuation item.

    Searches the saved response without making another request.
    """

    # First, look inside continuation items anywhere in the response.
    for node in walk_dicts(data):
        renderer = node.get("continuationItemRenderer")

        if not isinstance(renderer, dict):
            continue

        endpoint = renderer.get("continuationEndpoint", {})
        command = endpoint.get("continuationCommand", {})

        if isinstance(command, dict):
            token = command.get("token")

            if token:
                return token

    # Second, inspect appended continuation items.
    for node in walk_dicts(data):
        action = node.get("appendContinuationItemsAction")

        if not isinstance(action, dict):
            continue

        items = action.get("continuationItems", [])

        if not isinstance(items, list):
            continue

        for item in items:
            renderer = item.get("continuationItemRenderer", {})
            endpoint = renderer.get("continuationEndpoint", {})
            command = endpoint.get("continuationCommand", {})

            if isinstance(command, dict):
                token = command.get("token")

                if token:
                    return token

    # No token found.
    return None


# ============================================================
# STEP 6: FIND THE LATEST SAVED BATCH
# ============================================================

batch_pattern = re.compile(r"youtube_next_batch_(\d+)\.json$")
batch_files = []

for path in DATA_DIR.glob("youtube_next_batch_*.json"):
    match = batch_pattern.fullmatch(path.name)

    if match:
        batch_files.append((int(match.group(1)), path))

batch_files.sort(key=lambda item: item[0])


if batch_files:
    last_batch_number, last_batch_file = batch_files[-1]

    with last_batch_file.open("r", encoding="utf-8") as file:
        previous_data = json.load(file)

    continuation_token = find_grid_token(previous_data)

    if not continuation_token:
        raise RuntimeError(
            f"No next continuation token found in {last_batch_file}.\n"
            "No request was sent. The saved response may not contain "
            "another video-grid continuation token."
        )

    next_batch_number = last_batch_number + 1

    print("Previous batch:", last_batch_file)
    print("Next batch number:", next_batch_number)

else:
    # First batch: use the token from the original channel HTML.
    continuation_token = find_grid_token(initial_data)

    if not continuation_token:
        raise RuntimeError(
            "No video-grid continuation token found in original HTML. "
            "No request was sent."
        )

    next_batch_number = 1


# ============================================================
# STEP 7: PREPARE THE YOUTUBE REQUEST
# ============================================================

url = (
    "https://www.youtube.com/youtubei/v1/browse"
    f"?key={api_key}"
)

payload = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": client_version
        }
    },
    "continuation": continuation_token
}

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}


# ============================================================
# STEP 8: SEND ONE REQUEST
# ============================================================

batch_file = (
    DATA_DIR / f"youtube_next_batch_{next_batch_number:03d}.json"
)

# Prevent accidentally overwriting a saved response.
if batch_file.exists():
    raise FileExistsError(
        f"{batch_file} already exists. No request was sent."
    )

print("Sending request to YouTube...")

response = requests.post(
    url,
    json=payload,
    headers=headers,
    timeout=30
)

print("HTTP status:", response.status_code)
response.raise_for_status()

next_data = response.json()

print("Response received successfully.")


# ============================================================
# STEP 9: SAVE RAW RESPONSE AS JSON
# ============================================================

with batch_file.open("w", encoding="utf-8") as file:
    json.dump(next_data, file, ensure_ascii=False, indent=2)

print("Raw response saved:", batch_file)


# ============================================================
# STEP 10: FINAL SUMMARY
# ============================================================

next_token = find_grid_token(next_data)

print("\n========== SUMMARY ==========")
print("Batch processed:", next_batch_number)
print("Raw response saved:", batch_file)

if next_token:
    print("Next continuation token: Found")
    print("Ready for the next batch.")
else:
    print("Next continuation token: Not found")
    print(
        "The saved response may be the last page or use a different "
        "response structure."
    )

print("=============================")
