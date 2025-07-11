# export_image_app.py (Contact Sheet Builder v2.0.6 – Final Lite Build)

import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Config
st.set_page_config(page_title="🖼️ ContactSheets Lite (v2.0.6)", layout="wide")
st.markdown("""
<style>
button[kind="primary"] { background-color: #4B8BBE; color: white; border-radius: 4px; }
button[kind="secondary"] { background-color: transparent; border: 1px solid #ccc; }
[data-testid="stImage"] img { border-radius: 4px; }
.rejection-button { position: absolute; top: 6px; right: 10px; background: rgba(0,0,0,0.6); color: white; border: none; font-size: 14px; cursor: pointer; z-index: 2; }
.image-container { position: relative; }
</style>
""", unsafe_allow_html=True)

st.title("🖼️ ContactSheets Lite – Finalized")

if "images" not in st.session_state:
    st.session_state.images = []
    st.session_state.rejected = set()
    st.session_state.offset = 0

source = st.radio("Select Image Source:", ["CSV Upload", "Paste Image URLs", "Upload Local Files"], horizontal=True)
image_df = pd.DataFrame(columns=["Media Number", "URL"])

if source == "CSV Upload":
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df = df.rename(columns={"Media Link": "URL"})
        df = df[df["URL"].notna() & df["URL"].str.endswith((".jpg", ".jpeg"))]
        df = df[df["URL"].str.contains("http")]
        df = df.sort_values(["Your Share", "Sales Count"], ascending=False).drop_duplicates("Media Number")
        image_df = df[["Media Number", "URL"]].head(54)

elif source == "Paste Image URLs":
    url_input = st.text_area("Paste one image URL per line")
    if url_input.strip():
        urls = [u for u in url_input.strip().split("
") if u.endswith((".jpg", ".jpeg"))]
        image_df = pd.DataFrame({"Media Number": range(len(urls)), "URL": urls[:54]})

elif source == "Upload Local Files":
    files = st.file_uploader("Upload JPEG files", type=["jpg", "jpeg"], accept_multiple_files=True)
    if files:
        image_df = pd.DataFrame({"Media Number": range(len(files)), "URL": files[:54]})

if image_df.empty:
    st.stop()

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

st.subheader("Preview & Reject")
preview_limit = 18
visible_images = image_df[~image_df["Media Number"].isin(st.session_state.rejected)]
paginated = visible_images.iloc[st.session_state.offset:st.session_state.offset + preview_limit]

cols = st.columns(4)
for i, row in paginated.iterrows():
    with cols[i % 4]:
        img = fetch_img(row["URL"])
        if img and img.width > img.height:
            img.thumbnail((300, 300))
            reject_key = f"reject_{i}"
            if st.button("❌", key=reject_key):
                st.session_state.rejected.add(row["Media Number"])
            st.image(img, use_container_width=True)
        else:
            st.session_state.rejected.add(row["Media Number"])
