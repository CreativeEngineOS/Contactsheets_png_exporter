# export_contactsheet_lean.py

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheet PNG Export (Lean)", layout="wide")
st.title("🖼️ Export Contact Sheet (Lean Select & Export)")

# Upload CSV
df_file = st.file_uploader("Upload your processed CSV", type=["csv"])
if not df_file:
    st.stop()

# Load and normalize CSV
df = pd.read_csv(df_file)
if "Media Number" in df.columns:
    df = df[df["Media Number"].notna()]

df = df.rename(columns={
    "Media Link": "URL",
    "Your Share": "Total Earnings",
    "Your Share (%)": "Sales Count",
})

for col in ["Media Number", "Description", "URL", "Sales Count", "Total Earnings"]:
    if col not in df.columns:
        df[col] = "" if col in ["Description", "URL"] else 0

def get_star_rating(count, earnings):
    base = min(int(count), 4)
    if float(earnings) > 200:
        base += 1
    return base

df["Rating"] = df.apply(lambda row: get_star_rating(row["Sales Count"], row["Total Earnings"]), axis=1)
unique_df = df.sort_values("Rating", ascending=False).drop_duplicates("Media Number")

# Load top 36 landscape images
headers = {"User-Agent": "Mozilla/5.0"}
loaded_images = []
max_images = 36

for _, row in unique_df.iterrows():
    if len(loaded_images) >= max_images:
        break

    media_id = str(row["Media Number"])
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"

    try:
        r = requests.get(img_url, headers=headers, timeout=5)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            w, h = img.size
            if h >= w:  # Skip vertical or square
                continue
            img.thumbnail((300, 300))
            loaded_images.append((media_id, row, img))
    except:
        continue

if not loaded_images:
    st.warning("No suitable images found.")
    st.stop()

# Session state for image status
if "image_state" not in st.session_state:
    st.session_state.image_state = {media_id: "unselected" for media_id, _, _ in loaded_images}

# Reset grid
if st.button("🔄 Reset Grid"):
    remaining = [item for item in loaded_images if st.session_state.image_state.get(item[0]) != "rejected"]
    st.session_state.image_state = {media_id: "unselected" for media_id, _, _ in remaining}
    loaded_images = remaining

# Display image grid
cols = st.columns(4)
for idx, (media_id, row, img) in enumerate(loaded_images):
    if st.session_state.image_state.get(media_id) != "rejected":
        with cols[idx % 4]:
            st.image(img, use_container_width=True)
            if st.button("❌", key=f"reject_{media_id}"):
                st.session_state.image_state[media_id] = "rejected"

# Get remaining images
final_selection = [row for media_id, row, _ in loaded_images if st.session_state.image_state.get(media_id) != "rejected"]

if len(final_selection) < 1:
    st.warning("You must keep at least one image to export.")
    st.stop()

# Generate PNG Contact Sheet
st.subheader("📷 Final Contact Sheet Preview")

top_images = pd.DataFrame(final_selection).head(12)
canvas_width, canvas_height = 1280, 960
cols, rows = 4, 3
padding = 10
thumb_w = (canvas_width - (cols + 1) * padding) // cols
thumb_h = (canvas_height - (rows + 1) * padding) // rows
canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))

for i, (_, row) in enumerate(top_images.iterrows()):
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
    try:
        r = requests.get(img_url, headers=headers, timeout=5)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (thumb_w, thumb_h), (204, 204, 204, 255))
    except:
        img = Image.new("RGBA", (thumb_w, thumb_h), (204, 204, 204, 255))

    x = padding + (i % cols) * (thumb_w + padding)
    y = padding + (i // cols) * (thumb_h + padding)
    canvas.paste(img, (x, y), mask=img)

# Display and Download
st.image(canvas, caption="🖼️ Contact Sheet", use_container_width=True)
buf = BytesIO()
canvas.save(buf, format="PNG")
st.download_button("⬇️ Download PNG Contact Sheet", data=buf.getvalue(), file_name="contact_sheet.png", mime="image/png")
