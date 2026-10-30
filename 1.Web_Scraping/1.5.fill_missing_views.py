
import os
import re
import json
import csv
from glob import glob

# ==========================================
# STEP 1: FILE PATHS
# ==========================================

JSON_FILE = "htmls/youtube_videos.json"
CSV_FILE = "htmls/youtube_videos.csv"

# Search saved HTML and JSON files only.
# No requests are sent to YouTube.
SOURCE_FILES = (
    glob("htmls/*.json")
    + glob("htmls/*.html")
)

# ==========================================
# STEP 2: FIND VIEW COUNTS IN SAVED DATA
# ==========================================

def find_views(obj):
    """Find video IDs and view counts in saved data."""

    results = {}

    if isinstance(obj, dict):

        video_id = (
            obj.get("contentId")
            or obj.get("videoId")
        )

        # Search for metadata containing views.
        metadata = obj.get("metadata", {})

        lockup = metadata.get(
            "lockupMetadataViewModel", {}
        )

        rows = (
            lockup.get("metadata", {})
            .get("contentMetadataViewModel", {})
            .get("metadataRows", [])
        )

        views = ""

        for row in rows:
            for part in row.get("metadataParts", []):

                label = part.get("accessibilityLabel", "")
                content = (
                    part.get("text", {}).get("content", "")
                )

                combined = f"{label} {content}"

                if re.search(r"\bviews?\b", combined, re.I):
                    views = content or label
                    break

            if views:
                break

        if video_id and views:
            results[video_id] = views

        # Search nested dictionaries and lists.
        for value in obj.values():
            results.update(find_views(value))

    elif isinstance(obj, list):
        for item in obj:
            results.update(find_views(item))

    return results


# ==========================================
# STEP 3: SCAN EXISTING FILES
# ==========================================

views_by_id = {}

for filename in SOURCE_FILES:

    # Skip the main video list; it may already be incomplete.
    if os.path.basename(filename) == "youtube_videos.json":
        continue

    try:
        if filename.lower().endswith(".json"):
            with open(filename, "r", encoding="utf-8") as file:
                source_data = json.load(file)

        elif filename.lower().endswith(".html"):
            # An HTML batch wrapper may contain JSON inside <pre>.
            from bs4 import BeautifulSoup

            with open(filename, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file.read(), "html.parser")

            pre = soup.find("pre")

            if not pre:
                continue

            source_data = json.loads(pre.get_text())

        else:
            continue

        found = find_views(source_data)
        views_by_id.update(found)

        print(
            f"Scanned {os.path.basename(filename)}: "
            f"{len(found)} view counts found"
        )

    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Skipped {filename}: {error}")


# ==========================================
# STEP 4: UPDATE THE MAIN JSON FILE
# ==========================================

with open(JSON_FILE, "r", encoding="utf-8") as file:
    videos = json.load(file)

updated = 0

for video in videos:
    video_id = video.get("video_id", "")

    if (
        video_id in views_by_id
        and not video.get("views")
    ):
        video["views"] = views_by_id[video_id]
        updated += 1

with open(JSON_FILE, "w", encoding="utf-8") as file:
    json.dump(videos, file, ensure_ascii=False, indent=4)

print(f"\nJSON: filled {updated} missing view counts.")


# ==========================================
# STEP 5: UPDATE THE CSV FILE
# ==========================================

with open(
    CSV_FILE, "r", newline="", encoding="utf-8-sig"
) as file:
    reader = csv.DictReader(file)
    fieldnames = reader.fieldnames
    rows = list(reader)

if not fieldnames or "video_id" not in fieldnames:
    raise ValueError("CSV must contain a video_id column.")

if "views" not in fieldnames:
    fieldnames.append("views")

csv_updated = 0

for row in rows:
    video_id = row.get("video_id", "")

    if (
        video_id in views_by_id
        and not row.get("views", "").strip()
    ):
        row["views"] = views_by_id[video_id]
        csv_updated += 1

with open(
    CSV_FILE, "w", newline="", encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"CSV: filled {csv_updated} missing view counts.")
print("Finished. No YouTube requests were sent.")
