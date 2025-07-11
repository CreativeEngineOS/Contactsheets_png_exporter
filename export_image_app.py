# export_image_app.py (Interactive Contact Sheet - Selection Mode)

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
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

# Selection UI
st.subheader("Select images to include in your contact sheet")
selected_rows = []
rejected_ids = set()
headers = {"User-Agent": "Mozilla/5.0"}
cols = st.columns(4)
loaded = 0
max_images = 36
image_states = {}

for i, (_, row) in enumerate(unique_df.iterrows()):
    if loaded >= max_images:
        break
    media_id = str(row["Media Number"])
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"

    try:
        r = requests.get(img_url, headers=headers, timeout=5)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            w, h = img.size
            if h >= w:
                continue
            img.thumbnail((300, 300))

            with cols[loaded % 4]:
                st.image(img, use_container_width=True)
                col1, col2 = st.columns([6, 1])
                with col1:
                    selected = st.checkbox(f"✔️ Use {media_id}", key=f"select_{i}")
                with col2:
                    reject = st.button("❌", key=f"reject_{i}")
                if reject:
                    rejected_ids.add(media_id)
                elif selected:
                    selected_rows.append(row)
            loaded += 1
    except:
        continue

if loaded == 0:
    st.warning("No suitable landscape images found.")
    st.stop()
elif loaded < max_images:
    st.info(f"End of available images. {loaded} loaded.")

if len(selected_rows) < 1:
    st.warning("Select at least one image to generate the contact sheet.")
    st.stop()

# Generate Contact Sheet with top 12
top_images = pd.DataFrame(selected_rows).head(12)
canvas_width, canvas_height = 1280, 960
cols, rows = 4, 3
padding = 10
thumb_w = (canvas_width - (cols + 1) * padding) // cols
thumb_h = (canvas_height - (rows + 1) * padding) // rows
canvas = Image.new("RGBA", (canvas_width, canvas_height), color=(255, 255, 255, 0))

for i, (_, row) in enumerate(top_images.iterrows()):
    img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
    try:
        r = requests.get(img_url, headers=headers, timeout=5)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (thumb_w, thumb_h), color=(204, 204, 204, 255))
    except:
        img = Image.new("RGBA", (thumb_w, thumb_h), color=(204, 204, 204, 255))

    x = padding + (i % cols) * (thumb_w + padding)
    y = padding + (i // cols) * (thumb_h + padding)
    canvas.paste(img, (x, y), mask=img if img.mode == "RGBA" else None)

# Show & download
st.image(canvas, caption="🖼️ Final Contact Sheet Preview", use_container_width=True)
buf = BytesIO()
canvas.save(buf, format="PNG")
st.download_button("⬇️ Download Contact Sheet", data=buf.getvalue(), file_name="custom_contact_sheet.png", mime="image/png")
