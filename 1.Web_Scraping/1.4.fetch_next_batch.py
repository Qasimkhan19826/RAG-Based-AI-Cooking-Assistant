import os
import re
import json
import html
import csv
import requests
from bs4 import BeautifulSoup

# ==========================================
# STEP 1: FILE PATHS
# ==========================================

HTML_FILE = "htmls/youtube_channel.html"
JSON_FILE = "htmls/youtube_videos.json"
CSV_FILE = "htmls/youtube_videos.csv"

os.makedirs("htmls", exist_ok=True)

# ==========================================
# STEP 2: READ THE SAVED CHANNEL HTML
# ==========================================

with open(HTML_FILE, "r", encoding="utf-8") as file:
    original_html = file.read()

soup = BeautifulSoup(original_html, "html.parser")

script_text = None

for script in soup.find_all("script"):
    text = script.string or script.get_text()

    if "var ytInitialData =" in text:
        script_text = text
        break

if script_text is None:
    raise ValueError("ytInitialData was not found in saved HTML.")


# Extract the complete JSON object safely.
start = script_text.find("{")

if start == -1:
    raise ValueError("Could not find the initial JSON object.")

depth = 0
inside_string = False
escaped = False
end = None

for i in range(start, len(script_text)):
    char = script_text[i]

    if inside_string:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            inside_string = False
    else:
        if char == '"':
            inside_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                end = i + 1
                break

if end is None:
    raise ValueError("Could not find the end of the JSON object.")

data = json.loads(script_text[start:end])

print("Saved channel HTML loaded successfully.")


# ==========================================
# STEP 3: FIND THE VIDEO GRID TOKEN
# ==========================================

def find_video_grid(obj):
    if isinstance(obj, dict):

        if "richGridRenderer" in obj:
            yield obj["richGridRenderer"]

        for value in obj.values():
            yield from find_video_grid(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from find_video_grid(item)


grid_renderers = list(find_video_grid(data))

video_grid = None
token = None

for renderer in grid_renderers:
    contents = renderer.get("contents", [])

    for item in contents:
        continuation = item.get(
            "continuationItemRenderer", {}
        )

        endpoint = continuation.get(
            "continuationEndpoint", {}
        )

        command = endpoint.get("continuationCommand", {})

        if command.get("token"):
            video_grid = renderer
            token = command["token"]
            break

    if token:
        break

if not token:
    raise ValueError(
        "No video-grid continuation token found. "
        "There may be no further batch in the saved HTML."
    )

print("Video-grid continuation token found.")


# ==========================================
# STEP 4: GET REQUEST DETAILS
# ==========================================

api_key_match = re.search(
    r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"',
    original_html
)

version_match = re.search(
    r'"clientVersion"\s*:\s*"([^"]+)"',
    original_html
)

if not api_key_match or not version_match:
    raise ValueError(
        "API key or client version not found in saved HTML."
    )

api_key = api_key_match.group(1)
client_version = version_match.group(1)


# ==========================================
# STEP 5: REQUEST ONE NEXT BATCH
# ==========================================

url = "https://www.youtube.com/youtubei/v1/browse"

payload = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": client_version
        }
    },
    "continuation": token
}

response = requests.post(
    url,
    params={"key": api_key},
    json=payload,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)

print("HTTP status:", response.status_code)
response.raise_for_status()

next_data = response.json()

print("Next batch response received.")


# ==========================================
# STEP 6: SAVE THIS BATCH SEPARATELY
# ==========================================

# Find an unused batch number so earlier batches
# are not overwritten.
batch_number = 1

while os.path.exists(
    f"htmls/youtube_next_batch_{batch_number:03d}.json"
):
    batch_number += 1

batch_json_file = (
    f"htmls/youtube_next_batch_{batch_number:03d}.json"
)

batch_html_file = (
    f"htmls/youtube_next_batch_{batch_number:03d}.html"
)

# Save the original response as JSON.
with open(batch_json_file, "w", encoding="utf-8") as file:
    json.dump(next_data, file, ensure_ascii=False, indent=2)

# Save a readable HTML copy of the response.
# Note: the response data itself is JSON, not a
# complete YouTube webpage.
with open(batch_html_file, "w", encoding="utf-8") as file:
    file.write(
        "<!DOCTYPE html>\n"
        "<html><head><meta charset='utf-8'>"
        "<title>YouTube Next Batch</title></head><body>"
        "<h2>YouTube continuation response</h2>"
        "<pre>"
        + html.escape(
            json.dumps(next_data, ensure_ascii=False, indent=2)
        )
        + "</pre></body></html>"
    )

print("Saved batch JSON:", batch_json_file)
print("Saved batch HTML:", batch_html_file)


# ==========================================
# STEP 7: HELPER FUNCTIONS FOR VIDEO DATA
# ==========================================

def duration_to_seconds(duration):
    if not duration:
        return None

    parts = [int(part) for part in duration.split(":")]

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    return None


def find_video_entries(obj):
    if isinstance(obj, dict):

        if obj.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            yield obj

        for value in obj.values():
            yield from find_video_entries(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from find_video_entries(item)


def extract_videos(source_data):
    videos = []

    for video in find_video_entries(source_data):
        metadata = video.get("metadata", {})
        lockup = metadata.get("lockupMetadataViewModel", {})

        title = (
            lockup.get("title", {}).get("content", "")
        ).strip()

        video_id = video.get("contentId", "")

        if not video_id or not title:
            continue

        duration = ""

        thumbnail = (
            video.get("contentImage", {})
            .get("thumbnailViewModel", {})
        )

        for overlay in thumbnail.get("overlays", []):
            bottom = overlay.get(
                "thumbnailBottomOverlayViewModel", {}
            )

            for badge in bottom.get("badges", []):
                badge_data = badge.get(
                    "thumbnailBadgeViewModel", {}
                )

                text = badge_data.get("text", "")

                if re.fullmatch(
                    r"\d{1,2}:\d{2}(?::\d{2})?", text
                ):
                    duration = text
                    break

            if duration:
                break

        rows = (
            lockup.get("metadata", {})
            .get("contentMetadataViewModel", {})
            .get("metadataRows", [])
        )

        views = ""
        upload_age = ""

        for row in rows:
            for part in row.get("metadataParts", []):
                label = part.get("accessibilityLabel", "")
                content = (
                    part.get("text", {}).get("content", "")
                )

                if "view" in label.lower():
                    views = content
                elif "ago" in label.lower():
                    upload_age = label

        videos.append({
            "title": title,
            "video_id": video_id,
            "duration": duration,
            "duration_seconds": duration_to_seconds(duration),
            "views": views,
            "upload_age": upload_age,
            "video_url": (
                f"https://www.youtube.com/watch?v={video_id}"
            )
        })

    return videos


# ==========================================
# STEP 8: EXTRACT THE NEW VIDEOS
# ==========================================

new_videos = extract_videos(next_data)

print("Videos found in this batch:", len(new_videos))

if not new_videos:
    print(
        "No matching video entries found. "
        "Inspect the saved batch JSON because YouTube's "
        "response structure may differ."
    )


# ==========================================
# STEP 9: LOAD EXISTING VIDEO IDs
# ==========================================

if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        existing_videos = json.load(file)
else:
    existing_videos = []

if not isinstance(existing_videos, list):
    raise ValueError(
        "Existing JSON must contain a list of video records."
    )

existing_ids = {
    video.get("video_id")
    for video in existing_videos
    if video.get("video_id")
}

# Keep only video IDs not already stored.
unique_new_videos = []
batch_ids = set()

for video in new_videos:
    video_id = video["video_id"]

    if video_id not in existing_ids and video_id not in batch_ids:
        unique_new_videos.append(video)
        batch_ids.add(video_id)

print("New unique videos:", len(unique_new_videos))


# ==========================================
# STEP 10: UPDATE THE JSON FILE
# ==========================================

# A valid JSON array cannot be extended by simply
# appending another object to the end of the file.
# Read the old list, merge new records, then save it.
if unique_new_videos:
    existing_videos.extend(unique_new_videos)

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(
            existing_videos,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("Updated JSON:", JSON_FILE)
else:
    print("JSON unchanged; no new videos to add.")


# ==========================================
# STEP 11: APPEND NEW ROWS TO THE CSV FILE
# ==========================================

fieldnames = [
    "title",
    "video_id",
    "duration",
    "duration_seconds",
    "views",
    "upload_age",
    "video_url"
]

if unique_new_videos:
    csv_exists = os.path.exists(CSV_FILE)
    csv_has_data = csv_exists and os.path.getsize(CSV_FILE) > 0

    with open(
        CSV_FILE,
        "a",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        # Write the header only if the file is new or empty.
        if not csv_has_data:
            writer.writeheader()

        writer.writerows(unique_new_videos)

    print("Appended new rows to CSV:", CSV_FILE)
else:
    print("CSV unchanged; no new videos to add.")


# ==========================================
# STEP 12: SUMMARY
# ==========================================

print("\n========== SUMMARY ==========")
print("Batch number:", batch_number)
print("Videos received:", len(new_videos))
print("New videos added:", len(unique_new_videos))
print("Total records in JSON:", len(existing_videos))
print("Next batch saved:", batch_json_file)
print("=============================")
