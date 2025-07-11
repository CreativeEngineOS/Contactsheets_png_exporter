# export_image_app.py (Interactive Contact Sheet - Selection Mode)

import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheet PNG Export (Interactive)", layout="wide")
st.title("🖼️ Export Interactive Contact Sheet (Top Images Grid)")

# Upload CSV
df_file = st.file_uploader("Upload your processed CSV", type=["csv"])
if not df_file:
    st.stop()

# Load and normalize CSV
df = pd.read_csv(df_file)

# Drop placeholder or empty rows
if "Media Number" in df.columns:
    df = df[df["Media Number"].notna()]

# Rename relevant columns
column_map = {
    "Media Link":     "URL",
    "Your Share":     "Total Earnings",
    "Your Share (%)": "Sales Count",
}
df = df.rename(columns=column_map)

# Ensure required columns exist
for col in ["Media Number", "Description", "URL", "Sales Count", "Total Earnings"]:
    if col not in df.columns:
        df[col] = "" if col in ["Description", "URL"] else 0

# Compute rating (lean logic)
def get_star_rating(count, earnings):
    base = min(int(count), 4)
    if float(earnings) > 200:
        base += 1
    return base

df["Rating"] = df.apply(lambda row: get_star_rating(row["Sales Count"], row["Total Earnings"]), axis=1)

# Deduplicate and select top-rated
unique_df = df.sort_values("Rating", ascending=False).drop_duplicates("Media Number")

# Image previews with checkboxes
st.subheader("Select images to include in your contact sheet")
selected_rows = []
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

cols = st.columns(4)
loaded = 0
max_images = 36
for i, (_, row) in enumerate(unique_df.iterrows()):
    if loaded >= max_images:
        break
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
    try:
        response = requests.get(img_url, headers=headers, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            w, h = img.size
            # Skip vertical or square images
            if h >= w:
                continue
            img.thumbnail((300, 300))
            with cols[loaded % 4]:
                if st.checkbox(f"Select {row['Media Number']}", key=i):
                    selected_rows.append(row)
                st.image(img, use_container_width=True)
            loaded += 1
        else:
            continue
    except:
        continue

if loaded == 0:
    st.warning("No suitable landscape images found.")
    st.stop()
elif loaded < max_images:
    st.info(f"End of available images. {loaded} loaded.")

# Only continue if we have enough images
if len(selected_rows) < 1:
    st.warning("Select at least one image to generate the contact sheet.")
    st.stop()

# Rebuild DataFrame and limit to 12 images
top_images = pd.DataFrame(selected_rows).head(12)

# Canvas layout: 4 columns x 3 rows = 12 images max
canvas_width = 1280
canvas_height = 960
cols, rows = 4, 3
thumb_padding = 10
thumb_w = (canvas_width - (cols + 1) * thumb_padding) // cols
thumb_h = (canvas_height - (rows + 1) * thumb_padding) // rows
canvas = Image.new("RGBA", (canvas_width, canvas_height), color=(255, 255, 255, 0))  # Transparent background

# Paste selected images
for i, (_, row) in enumerate(top_images.iterrows()):
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
    try:
        response = requests.get(img_url, headers=headers, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (thumb_w, thumb_h), color=(204, 204, 204, 255))
    except:
        img = Image.new("RGBA", (thumb_w, thumb_h), color=(204, 204, 204, 255))

    x = thumb_padding + (i % cols) * (thumb_w + thumb_padding)
    y = thumb_padding + (i // cols) * (thumb_h + thumb_padding)
    canvas.paste(img, (x, y), mask=img if img.mode == "RGBA" else None)

# Display and download
st.image(canvas, caption="🖼️ Final Contact Sheet Preview", use_container_width=True)
buf = BytesIO()
canvas.save(buf, format="PNG")
st.download_button("⬇️ Download Contact Sheet", data=buf.getvalue(), file_name="custom_contact_sheet.png", mime="image/png")
