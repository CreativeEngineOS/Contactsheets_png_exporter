# export_image_app.py (Lean, Image-Only Contact Sheet - PATCHED)

import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheet PNG Export (Lean Mode)", layout="wide")
st.title("🖼️ Export Lean Contact Sheet (Top 5 Images)")

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
df = df.sort_values("Rating", ascending=False).drop_duplicates("Media Number")
top_images = df.head(5)

# Canvas layout: 1080x720px
canvas_w, canvas_h = 1080, 720
thumb_w = canvas_w // 5
thumb_h = canvas_h

canvas = Image.new("RGB", (canvas_w, canvas_h), color="white")

for i, (_, row) in enumerate(top_images.iterrows()):
    try:
        img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
        response = requests.get(img_url, timeout=5)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img = img.resize((thumb_w, thumb_h))
    except:
        img = Image.new("RGB", (thumb_w, thumb_h), color="#ccc")
    canvas.paste(img, (i * thumb_w, 0))

# Preview and download
st.image(canvas, caption="Lean Contact Sheet (Top 5 Images)", use_container_width=True)
buf = BytesIO()
canvas.save(buf, format="PNG")
st.download_button("⬇️ Download Contact Sheet", data=buf.getvalue(), file_name="lean_contact_sheet.png", mime="image/png")
