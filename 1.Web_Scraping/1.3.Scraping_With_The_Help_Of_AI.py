
from bs4 import BeautifulSoup
import json
import re
import csv

INPUT_FILE = "htmls/youtube_channel.html"

# Step 1: Read the saved HTML file
with open(INPUT_FILE, "r", encoding="utf-8") as file:
    html = file.read()

# Step 2: Find the script containing ytInitialData
soup = BeautifulSoup(html, "html.parser")

script_text = None

for script in soup.find_all("script"):
    text = script.string or script.get_text()

    if "var ytInitialData =" in text:
        script_text = text
        break

if script_text is None:
    raise ValueError("ytInitialData was not found in the saved HTML.")

# Step 3: Extract the complete JSON object from the script
start = script_text.find("{")

if start == -1:
    raise ValueError("Could not find the JSON object.")

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

# Step 4: Convert duration into seconds
def duration_to_seconds(duration):
    parts = [int(part) for part in duration.split(":")]

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    return None


# Step 5: Find every lockupViewModel in the data
def find_video_entries(obj):
    if isinstance(obj, dict):
        if obj.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            yield obj

        for value in obj.values():
            yield from find_video_entries(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from find_video_entries(item)


videos = []
seen_ids = set()

for video in find_video_entries(data):

    # Extract title and video ID
    metadata = video.get("metadata", {})
    lockup_metadata = metadata.get(
        "lockupMetadataViewModel", {}
    )

    title = lockup_metadata.get("title", {}).get("content", "")
    video_id = video.get("contentId", "")

    if not video_id or video_id in seen_ids:
        continue

    seen_ids.add(video_id)

    # Extract duration from thumbnail badges
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

            if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text):
                duration = text
                break

        if duration:
            break

    # Extract views and relative upload time
    rows = (
        lockup_metadata.get("metadata", {})
        .get("contentMetadataViewModel", {})
        .get("metadataRows", [])
    )

    views = ""
    upload_age = ""

    for row in rows:
        for part in row.get("metadataParts", []):
            label = part.get("accessibilityLabel", "")
            content = part.get("text", {}).get("content", "")

            if "view" in label.lower():
                views = content
            elif "ago" in label.lower():
                upload_age = label

    # Store all information in one dictionary
    videos.append({
        "title": title.strip(),
        "video_id": video_id,
        "duration": duration,
        "duration_seconds": duration_to_seconds(duration),
        "views": views,
        "upload_age": upload_age,
        "video_url": f"https://www.youtube.com/watch?v={video_id}"
    })

# Step 6: Sort shortest videos first
videos.sort(
    key=lambda video: (
        video["duration_seconds"] is None,
        video["duration_seconds"]
        if video["duration_seconds"] is not None
        else float("inf")
    )
)

# Step 7: Save to JSON
with open("htmls/youtube_videos.json", "w", encoding="utf-8") as file:
    json.dump(videos, file, ensure_ascii=False, indent=4)

# Step 8: Save to CSV
fieldnames = [
    "title",
    "video_id",
    "duration",
    "duration_seconds",
    "views",
    "upload_age",
    "video_url"
]

with open(
    "htmls/youtube_videos.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(videos)

print("Videos extracted:", len(videos))
print("Saved: htmls/youtube_videos.json")
print("Saved: htmls/youtube_videos.csv")

for video in videos:
    print(
        video["duration"],
        video["title"],
        video["video_url"]
    )

# To find the continous token
def find_continuation_tokens(obj):
    if isinstance(obj, dict):
        command = obj.get("continuationCommand")

        if isinstance(command, dict) and command.get("token"):
            yield command["token"]

        for value in obj.values():
            yield from find_continuation_tokens(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from find_continuation_tokens(item)


tokens = list(find_continuation_tokens(data))

print("Continuation tokens found:", len(tokens))

# To identify the correct token
def find_continuations(obj, path="root"):
    if isinstance(obj, dict):

        command = obj.get("continuationCommand")

        if isinstance(command, dict) and command.get("token"):
            print("\nPath:", path)
            print("Nearby keys:", list(obj.keys()))

        for key, value in obj.items():
            find_continuations(value, f"{path}.{key}")

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_continuations(item, f"{path}[{i}]")


find_continuations(data)