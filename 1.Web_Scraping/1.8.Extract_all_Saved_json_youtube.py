
import re
import json
import csv
import html

from pathlib import Path


# ============================================================
# STEP 1: FILE PATHS
# ============================================================

DATA_DIR = Path("htmls")

HTML_FILE = DATA_DIR / "youtube_channel.html"
JSON_FILE = DATA_DIR / "youtube_videos.json"
CSV_FILE = DATA_DIR / "youtube_videos.csv"

DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# STEP 2: HELPER FUNCTIONS
# ============================================================

def walk_dicts(obj):
    """Visit every dictionary in nested JSON data."""

    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from walk_dicts(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from walk_dicts(item)


def extract_text(value):
    """Extract text from common YouTube JSON formats."""

    if isinstance(value, str):
        return html.unescape(value)

    if isinstance(value, dict):
        if isinstance(value.get("simpleText"), str):
            return html.unescape(value["simpleText"])

        if isinstance(value.get("content"), str):
            return html.unescape(value["content"])

        runs = value.get("runs", [])

        if isinstance(runs, list):
            return "".join(
                run.get("text", "")
                for run in runs
                if isinstance(run, dict)
                and isinstance(run.get("text"), str)
            )

    return ""


def duration_to_seconds(duration):
    """Convert 12:34 or 1:02:34 into seconds."""

    if not duration:
        return None

    try:
        parts = [int(part) for part in duration.split(":")]
    except ValueError:
        return None

    if len(parts) == 2:
        return parts[0] * 60 + parts[1]

    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]

    return None


def find_text_by_keys(obj, keys):
    """Find the first useful text value for the specified keys."""

    for node in walk_dicts(obj):
        for key in keys:
            if key not in node:
                continue

            text = extract_text(node[key])

            if text.strip():
                return text.strip()

    return ""


def extract_views(text):
    """Find view counts such as 1,234 views or 12K views."""

    match = re.search(
        r"\b([\d,.]+\s*(?:[KMB])?\s+views?)\b",
        text,
        re.IGNORECASE
    )

    return match.group(1) if match else ""


def get_video_id(video):
    """Support different video ID field names."""

    return (
        video.get("video_id")
        or video.get("videoId")
        or video.get("contentId")
        or ""
    )


# ============================================================
# STEP 3: EXTRACT VIDEOS FROM ANY SUPPORTED JSON STRUCTURE
# ============================================================

def extract_videos(data):
    videos = []
    seen = set()

    for node in walk_dicts(data):

        # Newer YouTube channel layout.
        if "lockupViewModel" in node:
            video_node = node["lockupViewModel"]

        # Older YouTube channel layout.
        elif node.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            video_node = node

        # Other common YouTube video renderers.
        else:
            video_node = None

            for key in (
                "videoRenderer",
                "gridVideoRenderer",
                "compactVideoRenderer"
            ):
                if isinstance(node.get(key), dict):
                    video_node = node[key]
                    break

            if video_node is None:
                continue

        if not isinstance(video_node, dict):
            continue

        video_id = get_video_id(video_node)

        if not video_id or video_id in seen:
            continue

        seen.add(video_id)

        # Extract the title.
        title = find_text_by_keys(video_node, ["title"])

        # Collect text within this video's own data.
        text_parts = []

        for child in walk_dicts(video_node):
            for key in ("text", "simpleText", "content"):
                value = child.get(key)

                if isinstance(value, str):
                    text_parts.append(value)

        combined_text = " ".join(text_parts)

        # Extract duration from thumbnail badges or text.
        duration = ""

        for text_part in text_parts:
            text_part = text_part.strip()

            if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text_part):
                duration = text_part
                break

        # Extract view count and relative upload age.
        views = extract_views(combined_text)

        uploaded = ""

        age_match = re.search(
            r"\b(?:\d+\s+)?(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago\b",
            combined_text,
            re.IGNORECASE
        )

        if age_match:
            uploaded = age_match.group(0)

        videos.append({
            "title": title,
            "video_id": video_id,
            "duration": duration,
            "duration_seconds": duration_to_seconds(duration),
            "views": views,
            "uploaded": uploaded,
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })

    return videos


# ============================================================
# STEP 4: LOAD EXISTING EXTRACTED DATA
# ============================================================

if JSON_FILE.exists():
    with JSON_FILE.open("r", encoding="utf-8") as file:
        existing_videos = json.load(file)

    if not isinstance(existing_videos, list):
        raise ValueError("youtube_videos.json must contain a list.")

else:
    existing_videos = []

# Keep existing records and their available information.
all_videos = {}

for video in existing_videos:
    if not isinstance(video, dict):
        continue

    video_id = get_video_id(video)

    if video_id:
        all_videos[video_id] = video


# ============================================================
# STEP 5: FIND ALL SAVED BATCH JSON FILES
# ============================================================

batch_pattern = re.compile(r"youtube_next_batch_(\d+)\.json$")
batch_files = []

for path in DATA_DIR.glob("youtube_next_batch_*.json"):
    match = batch_pattern.fullmatch(path.name)

    if match:
        batch_files.append((int(match.group(1)), path))

batch_files.sort(key=lambda item: item[0])

print("Saved batch files found:", len(batch_files))


# ============================================================
# STEP 6: EXTRACT FROM ORIGINAL HTML DATA, IF AVAILABLE
# ============================================================

sources = []

if HTML_FILE.exists():
    original_html = HTML_FILE.read_text(encoding="utf-8")

    match = re.search(
        r"ytInitialData\s*=\s*",
        original_html
    )

    if match:
        start = original_html.find("{", match.end())

        if start != -1:
            depth = 0
            in_string = False
            escaped = False

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
                            initial_data = json.loads(
                                original_html[start:i + 1]
                            )
                            sources.append(
                                ("original channel HTML", initial_data)
                            )
                            break


# ============================================================
# STEP 7: LOAD AND EXTRACT EVERY SAVED BATCH
# ============================================================

for number, path in batch_files:
    print(f"Reading {path.name} ...")

    with path.open("r", encoding="utf-8") as file:
        batch_data = json.load(file)

    sources.append((path.name, batch_data))


# ============================================================
# STEP 8: MERGE VIDEOS AND REMOVE DUPLICATES
# ============================================================

total_extracted = 0
new_unique = 0

for source_name, source_data in sources:
    extracted = extract_videos(source_data)

    print(f"  Videos extracted from {source_name}: {len(extracted)}")

    total_extracted += len(extracted)

    for video in extracted:
        video_id = video["video_id"]

        if video_id not in all_videos:
            all_videos[video_id] = video
            new_unique += 1

        else:
            # Fill missing fields without overwriting good old data.
            existing = all_videos[video_id]

            for key, value in video.items():
                if value not in ("", None) and existing.get(key) in ("", None):
                    existing[key] = value


# ============================================================
# STEP 9: REPAIR MISSING VIEWS USING SAVED JSON DATA
# ============================================================

view_lookup = {}

for _, source_data in sources:
    for video in extract_videos(source_data):
        if video["views"]:
            view_lookup[video["video_id"]] = video["views"]

views_repaired = 0

for video_id, video in all_videos.items():
    if not video.get("views") and video_id in view_lookup:
        video["views"] = view_lookup[video_id]
        views_repaired += 1


# ============================================================
# STEP 10: SAVE THE COMPLETE JSON AND CSV
# ============================================================

final_videos = list(all_videos.values())

with JSON_FILE.open("w", encoding="utf-8") as file:
    json.dump(final_videos, file, ensure_ascii=False, indent=2)

fieldnames = [
    "title",
    "video_id",
    "duration",
    "duration_seconds",
    "views",
    "uploaded",
    "upload_age",
    "url",
    "video_url"
]

with CSV_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )

    writer.writeheader()
    writer.writerows(final_videos)

print("Updated CSV:", CSV_FILE)

# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n========== EXTRACTION SUMMARY ==========")
print("Batch JSON files processed:", len(batch_files))
print("Total videos extracted (including duplicates):", total_extracted)
print("New unique videos added:", new_unique)
print("Missing views repaired:", views_repaired)
print("Total unique videos in dataset:", len(final_videos))
print("JSON saved:", JSON_FILE)
print("CSV saved:", CSV_FILE)
print("No YouTube requests were sent.")
print("========================================")

# Congrats ,you done it ,also the t.txt file plays the major role in this 
# We assume the <script> hsa our all data ,than you paste it in txt file ,
# you try to find out the insight from the data.

# Now at last i will warpe the files which is used in Web Scraping.