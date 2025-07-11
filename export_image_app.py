# export_image_app.py (Interactive Contact Sheet)

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

df = df.rename(columns={
    "Media Link": "URL",
    "Your Share": "Total Earnings",
    "Your Share (%)": "Sales Count",
})

for col in ["Media Number", "Description", "URL", "Sales Count", "Total Earnings"]:
    if col not in df.columns:
        df[col] = "" if col in ["Description", "URL"] else 0

# Rating
def get_star_rating(count, earnings):
    base = min(int(count), 4)
    if float(earnings) > 200:
        base += 1
    return base

df["Rating"] = df.apply(lambda row: get_star_rating(row["Sales Count"], row["Total Earnings"]), axis=1)
unique_df = df.sort_values("Rating", ascending=False).drop_duplicates("Media Number")

# Session State Setup
PRELOAD_LIMIT = 18
LOAD_MORE_COUNT = 12

if "loaded_index" not in st.session_state:
    st.session_state.loaded_index = 0
if "loaded_images" not in st.session_state:
    st.session_state.loaded_images = []
if "image_state" not in st.session_state:
    st.session_state.image_state = {}

# Load Next Batch
def load_next_batch(count):
    headers = {"User-Agent": "Mozilla/5.0"}
    new_images = []
    loaded_ids = {mid for mid, _, _ in st.session_state.loaded_images}
    rejected_ids = {k for k, v in st.session_state.image_state.items() if v == "rejected"}

    while len(new_images) < count and st.session_state.loaded_index < len(unique_df):
        row = unique_df.iloc[st.session_state.loaded_index]
        st.session_state.loaded_index += 1
        media_id = str(row["Media Number"])

        if media_id in loaded_ids or media_id in rejected_ids:
            continue

        img_url = str(row.URL).strip().rstrip("/") + "/picture/photo"
        try:
            r = requests.get(img_url, headers=headers, timeout=5)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGBA")
                w, h = img.size
                if h >= w:
                    continue
                img.thumbnail((300, 300))
                new_images.append((media_id, row, img))
        except:
            continue

    st.session_state.loaded_images.extend(new_images)
    for media_id, _, _ in new_images:
        st.session_state.image_state[media_id] = "active"

# Initial Load
if st.session_state.loaded_index == 0:
    load_next_batch(PRELOAD_LIMIT)

# Confirm Selection
def reset_grid():
    st.session_state.loaded_images = [item for item in st.session_state.loaded_images if st.session_state.image_state[item[0]] != "rejected"]
    st.session_state.image_state = {media_id: "active" for media_id, _, _ in st.session_state.loaded_images}

st.markdown("### Reject images to curate your contact sheet")
if st.button("✅ Confirm Selects"):
    reset_grid()

# Display Grid
cols = st.columns(4)
remaining = [img for img in st.session_state.loaded_images if st.session_state.image_state[img[0]] != "rejected"]
count = 0
for i in range(len(remaining)):
    media_id, row, img = remaining[i]
    with cols[count % 4]:
        container = st.container()
        with container:
            # Reject button as overlay
            st.markdown(f"""
                <div style="position: relative;">
                    <img src="data:image/png;base64,{img_to_base64(img)}" style="width: 100%; border: 1px solid #ccc;" />
                    <form action="#" method="post">
                        <button style="
                            position: absolute;
                            top: 6px;
                            right: 6px;
                            background: #d00;
                            color: white;
                            border: none;
                            border-radius: 50%;
                            width: 24px;
                            height: 24px;
                            font-weight: bold;
                            cursor: pointer;">×</button>
                    </form>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"Reject {media_id}", key=f"reject_{media_id}"):
                st.session_state.image_state[media_id] = "rejected"
    count += 1

# ➕ Suggest More Images Button if needed
remaining_active = [row for media_id, row, _ in st.session_state.loaded_images if st.session_state.image_state.get(media_id) != "rejected"]

if len(remaining_active) < 12 and st.session_state.loaded_index < len(unique_df):
    col = cols[count % 4]
    with col:
        if st.button("➕ Suggest More Images"):
            load_next_batch(LOAD_MORE_COUNT)

# Warning if over
if len(remaining_active) > 12:
    st.warning(f"You have selected {len(remaining_active)} images. Please reject {len(remaining_active) - 12} more.")

# Final Export
if len(remaining_active) <= 12 and len(remaining_active) > 0:
    st.subheader("🖼️ Selects")
    top_images = pd.DataFrame(remaining_active).head(12)
    canvas_width, canvas_height = 1280, 960
    cols, rows = 4, 3
    padding = 10
    thumb_w = (canvas_width - (cols + 1) * padding) // cols
    thumb_h = (canvas_height - (rows + 1) * padding) // rows
    canvas = Image.new("RGBA", (canvas_width, canvas_height), color=(255, 255, 255, 0))
    headers = {"User-Agent": "Mozilla/5.0"}

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

    st.image(canvas, caption="🖼️ Selects", use_container_width=True)
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    st.download_button("⬇️ Download Contact Sheet", data=buf.getvalue(), file_name="custom_contact_sheet.png", mime="image/png")

# Helper: image to base64
def img_to_base64(img):
    import base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
