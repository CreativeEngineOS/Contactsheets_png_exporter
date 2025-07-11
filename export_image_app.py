# export_image_app.py (Experimental Build - Tabbed UI)

import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheet Builder (Fast Mode)", layout="wide")
st.title("🖼️ ContactSheet Builder – Experimental Speed Build")

# Tabs
stage = st.tabs(["📸 Selection", "📥 Selects", "🎯 Export"])

# Load from all 3 sources (to share between tabs)
with stage[0]:
    source = st.radio("Select Image Source:", ["CSV Upload", "Paste Image URLs", "Upload Local Files"], horizontal=True)
    image_df = pd.DataFrame(columns=["Media Number", "URL"])

    if source == "CSV Upload":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            df = df.rename(columns={"Media Link": "URL"})
            df = df[df["URL"].notna()]
            df = df.sort_values("Your Share", ascending=False)
            image_df = df[["Media Number", "URL"]].drop_duplicates("Media Number")

    elif source == "Paste Image URLs":
        url_input = st.text_area("Paste one image URL per line")
        if url_input.strip():
            urls = url_input.strip().split("\n")
            image_df = pd.DataFrame({"Media Number": range(len(urls)), "URL": urls})

    elif source == "Upload Local Files":
        files = st.file_uploader("Upload JPEG files", type=["jpg", "jpeg"], accept_multiple_files=True)
        if files:
            image_df = pd.DataFrame({"Media Number": range(len(files)), "URL": files})

    if image_df.empty:
        st.stop()

    # Session State Init
    if "loaded" not in st.session_state:
        st.session_state.loaded = []
        st.session_state.rejected = set()
        st.session_state.offset = 0

    def fetch_img(source):
        try:
            if isinstance(source, str):
                r = requests.get(source, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    return Image.open(BytesIO(r.content)).convert("RGB")
            else:
                return Image.open(source).convert("RGB")
        except:
            return None

    # Grid preview
    st.markdown("---")
    st.subheader("🔍 Preview and Reject")
    cols = st.columns(4)
    preview_limit = 18

    # Scrollable window logic
    visible_images = image_df[~image_df["Media Number"].isin(st.session_state.rejected)]
    paginated = visible_images.iloc[st.session_state.offset:st.session_state.offset+preview_limit]

    for i, row in paginated.iterrows():
        with cols[i % 4]:
            img = fetch_img(row["URL"])
            if img and img.width > img.height:
                img.thumbnail((300, 300))
                st.image(img, use_container_width=True)
                if st.button("❌", key=f"reject_{i}"):
                    st.session_state.rejected.add(row["Media Number"])
            else:
                st.session_state.rejected.add(row["Media Number"])

    selected_df = image_df[~image_df["Media Number"].isin(st.session_state.rejected)]
    selected_count = len(selected_df)
    st.info(f"Selected: {selected_count} images")

    if selected_count > 12:
        st.warning(f"Too many selected! Reject {selected_count - 12} more.")

    # Pagination controls
    max_offset = max(len(visible_images) - preview_limit, 0)
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.offset > 0:
            if st.button("⬅️ Previous"):
                st.session_state.offset -= preview_limit
    with col2:
        if st.session_state.offset < max_offset:
            if st.button("Next ➡️"):
                st.session_state.offset += preview_limit

    if st.button("✅ Confirm Selects") and selected_count <= 12:
        st.session_state.loaded = selected_df.copy().head(12)
        st.session_state.offset = 0

# Selects Tab
with stage[1]:
    st.subheader("📥 Selects")
    if not st.session_state.loaded:
        st.warning("No selects confirmed yet.")
        st.stop()

    # Show selected thumbs
    st.write("These are your confirmed selects:")
    thumbs = st.columns(4)
    for i, (_, row) in enumerate(st.session_state.loaded.iterrows()):
        with thumbs[i % 4]:
            img = fetch_img(row.URL)
            if img:
                img.thumbnail((200, 200))
                st.image(img, use_container_width=True)

# Export Tab
with stage[2]:
    st.subheader("🎯 Export")
    if not st.session_state.loaded:
        st.warning("Nothing to export.")
        st.stop()

    from PIL import ImageDraw
    canvas = Image.new("RGBA", (1280, 960), (255, 255, 255, 0))
    cols, rows = 4, 3
    padding = 10
    thumb_w = (1280 - (cols + 1) * padding) // cols
    thumb_h = (960 - (rows + 1) * padding) // rows

    for i, (_, row) in enumerate(st.session_state.loaded.iterrows()):
        img = fetch_img(row.URL)
        if not img:
            img = Image.new("RGB", (thumb_w, thumb_h), color=(180, 180, 180))
        else:
            img.thumbnail((thumb_w, thumb_h))
        x = padding + (i % cols) * (thumb_w + padding)
        y = padding + (i // cols) * (thumb_h + padding)
        canvas.paste(img, (x, y))

    st.image(canvas, use_container_width=True)
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    st.download_button("⬇️ Download Contact Sheet", buf.getvalue(), file_name="contact_sheet.png", mime="image/png")
