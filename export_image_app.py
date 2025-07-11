# export_image_app.py (Interactive Contact Sheet - Reject Only)

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="\U0001f5bc️ ContactSheet PNG Export (Interactive)", layout="wide")
st.title("\U0001f5bc️ Export Interactive Contact Sheet (Top Images Grid)")

# Upload CSV
df_file = st.file_uploader("Upload your processed CSV", type=["csv"])
if not df_file:
    st.stop()

# Load and normalize CSV
df = pd.read_csv(df_file)
if "Media Number" in df.columns:
    df = df[df["Media Number"].notna()]

# Rename columns
df = df.rename(columns={
    "Media Link": "URL",
    "Your Share": "Total Earnings",
    "Your Share (%)": "Sales Count",
})

# Ensure required columns
for col in ["Media Number", "Description", "URL", "Sales Count", "Total Earnings"]:
    if col not in df.columns:
        df[col] = "" if col in ["Description", "URL"] else 0

# Rating logic
def get_star_rating(count, earnings):
    base = min(int(count), 4)
    if float(earnings) > 200:
        base += 1
    return base

df["Rating"] = df.apply(lambda row: get_star_rating(row["Sales Count"], row["Total Earnings"]), axis=1)
unique_df = df.sort_values("Rating", ascending=False).drop_duplicates("Media Number")

# Preload logic
PRELOAD_LIMIT = 18
LOAD_MORE_COUNT = 12

if "loaded_index" not in st.session_state:
    st.session_state.loaded_index = 0
if "loaded_images" not in st.session_state:
    st.session_state.loaded_images = []
if "image_state" not in st.session_state:
    st.session_state.image_state = {}

# Helper to fetch and convert image to PIL
headers = {"User-Agent": "Mozilla/5.0"}

def fetch_image(url):
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            return img
    except:
        return None

# Load next batch of images
def load_next_batch(count):
    new_images = []
    seen_ids = {mid for mid, _, _ in st.session_state.loaded_images}
    rejected_ids = {k for k, v in st.session_state.image_state.items() if v == "rejected"}

    while len(new_images) < count and st.session_state.loaded_index < len(unique_df):
        row = unique_df.iloc[st.session_state.loaded_index]
        st.session_state.loaded_index += 1
        media_id = str(row["Media Number"])

        if media_id in seen_ids or media_id in rejected_ids:
            continue

        img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
        img = fetch_image(img_url)
        if img:
            w, h = img.size
            if h >= w:
                continue
            img.thumbnail((300, 300))
            new_images.append((media_id, row, img))

    st.session_state.loaded_images.extend(new_images)
    for media_id, _, _ in new_images:
        st.session_state.image_state[media_id] = "active"

# Initial load
if st.session_state.loaded_index == 0:
    load_next_batch(PRELOAD_LIMIT)

# Reset grid
if st.button("✅ Confirm Selects"):
    st.session_state.loaded_images = [item for item in st.session_state.loaded_images if st.session_state.image_state[item[0]] != "rejected"]
    st.session_state.image_state = {media_id: "active" for media_id, _, _ in st.session_state.loaded_images}

# Display grid
st.subheader("Reject images to curate your contact sheet")
cols = st.columns(4)
visible_images = 0
for idx, (media_id, row, img) in enumerate(st.session_state.loaded_images):
    if st.session_state.image_state.get(media_id) == "rejected":
        continue
    with cols[visible_images % 4]:
        st.image(img, use_container_width=True)
        if st.button("❌", key=f"reject_{media_id}"):
            st.session_state.image_state[media_id] = "rejected"
    visible_images += 1

# Remaining active
remaining = [row for media_id, row, _ in st.session_state.loaded_images if st.session_state.image_state.get(media_id) != "rejected"]

# Suggest More Images
if len(remaining) < 12 and st.session_state.loaded_index < len(unique_df):
    if st.button("➕ Suggest More Images"):
        load_next_batch(LOAD_MORE_COUNT)

# Warning
if len(remaining) > 12:
    st.warning(f"You have selected {len(remaining)} images. Please reject {len(remaining) - 12} more to continue.")

# Final Preview
if len(remaining) <= 12 and len(remaining) > 0:
    st.subheader("🖼️ Selects")
    top_images = pd.DataFrame(remaining).head(12)
    canvas_width, canvas_height = 1280, 960
    cols, rows = 4, 3
    padding = 10
    thumb_w = (canvas_width - (cols + 1) * padding) // cols
    thumb_h = (canvas_height - (rows + 1) * padding) // rows
    canvas = Image.new("RGBA", (canvas_width, canvas_height), color=(255, 255, 255, 0))

    for i, (_, row) in enumerate(top_images.iterrows()):
        img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
        img = fetch_image(img_url)
        if not img:
            img = Image.new("RGBA", (thumb_w, thumb_h), color=(204, 204, 204, 255))
        else:
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)

        x = padding + (i % cols) * (thumb_w + padding)
        y = padding + (i // cols) * (thumb_h + padding)
        canvas.paste(img, (x, y), mask=img if img.mode == "RGBA" else None)

    st.image(canvas, caption="🖼️ Selects", use_container_width=True)
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    st.download_button("⬇️ Download Contact Sheet", data=buf.getvalue(), file_name="custom_contact_sheet.png", mime="image/png")
