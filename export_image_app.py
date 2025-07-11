# export_image_app.py (Contact Sheet Builder v2.0 – Speed & Control Edition)

import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheet Builder (v2.0)", layout="wide")
st.title("🖼️ ContactSheet Builder – Speed & Control Edition")

# Tabs
stage = st.tabs(["📸 Selection", "📥 Selects", "🎯 Export"])

# Load from all 3 sources (to share between tabs)
with stage[0]:
    mode = st.radio("Mode:", ["Lite", "Pro"], horizontal=True)
    source = st.radio("Select Image Source:", ["CSV Upload", "Paste Image URLs", "Upload Local Files"], horizontal=True)
    image_df = pd.DataFrame(columns=["Media Number", "URL"])

    if source == "CSV Upload":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            df = df.rename(columns={"Media Link": "URL"})
            df = df[df["URL"].notna()]
            df = df[df["URL"].str.endswith((".jpg", ".jpeg"))]
            df = df.sort_values(["Your Share", "Sales Count"], ascending=False)
            df = df[df["URL"].str.contains("http")]
            df = df.head(54)
            image_df = df[["Media Number", "URL"]].drop_duplicates("Media Number")

    elif source == "Paste Image URLs":
        url_input = st.text_area("Paste one image URL per line")
        if url_input.strip():
            urls = url_input.strip().split("\n")
            urls = [u for u in urls if u.endswith(('.jpg','.jpeg'))]
            image_df = pd.DataFrame({"Media Number": range(len(urls)), "URL": urls[:54]})

    elif source == "Upload Local Files":
        files = st.file_uploader("Upload JPEG files", type=["jpg", "jpeg"], accept_multiple_files=True)
        if files:
            image_df = pd.DataFrame({"Media Number": range(len(files)), "URL": files[:54]})

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

    st.markdown("---")
    top = st.columns([5, 4, 3])
    with top[0]:
        st.subheader("🔍 Preview and Reject")
    with top[1]:
        visible_images = image_df[~image_df["Media Number"].isin(st.session_state.rejected)]
        preview_limit = 18
        max_offset = max(len(visible_images) - preview_limit, 0)
        page_count = (len(visible_images) + preview_limit - 1) // preview_limit
        current_page = st.session_state.offset // preview_limit + 1
        pages = [str(i+1) for i in range(min(3, page_count))]
        st.markdown(f"Page: &lt; {' , '.join(pages)} &gt;", unsafe_allow_html=True)
    with top[2]:
        selected_df = image_df[~image_df["Media Number"].isin(st.session_state.rejected)]
        selected_count = len(selected_df)
        if selected_count <= 12:
            if st.button("✅ Confirm Selects"):
                st.session_state.loaded = selected_df.copy().head(12)
                st.session_state.offset = 0

    cols = st.columns(4)
    paginated = visible_images.iloc[st.session_state.offset:st.session_state.offset+preview_limit]

    for i, row in paginated.iterrows():
        with cols[i % 4]:
            img = fetch_img(row["URL"])
            if img and img.width > img.height:
                img.thumbnail((300, 300))
                with st.container():
                    if st.button("❌", key=f"reject_{i}"):
                        st.session_state.rejected.add(row["Media Number"])
                    st.image(img, use_container_width=True)
            else:
                st.session_state.rejected.add(row["Media Number"])

    if selected_count > 12:
        st.warning(f"Too many selected! Reject {selected_count - 12} more.")

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.offset > 0:
            if st.button("⬅️ Previous"):
                st.session_state.offset -= preview_limit
    with col2:
        if st.session_state.offset < max_offset:
            if st.button("Suggest More Images ➕"):
                st.session_state.offset += preview_limit

# Selects Tab
with stage[1]:
    st.subheader("📥 Selects")
    if not st.session_state.loaded:
        st.warning("No selects confirmed yet.")
        st.stop()

    st.write("Rearrange these to finalize your Contact Sheet:")
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
