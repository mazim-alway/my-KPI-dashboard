# publish_page.py
import streamlit as st
import os
import uuid
import datetime
import textwrap
import pandas as pd
from typing import List

from db.queries import (
    ensure_publications_table,
    add_publication,
    get_publications,
    delete_publication,
)

# ----------------------------
# Config — adjust if you want
# ----------------------------
ASSET_DIR = "assets/publications"
IMG_DIR   = os.path.join(ASSET_DIR, "images")
PDF_DIR   = os.path.join(ASSET_DIR, "pdfs")

# Fixed display width for figures in the carousel
CAROUSEL_IMG_WIDTH = 520  # px (tweak this if you want slightly larger/smaller)

# ---------- ResearchGate-like clean cards (dark-friendly) ----------
_PUB_CSS = """
<style>
.pub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px; }
.pub-card { background: var(--panel, #2A2C32); border: 1px solid #2f333b; border-radius: 12px; padding: 14px;
            box-shadow: 0 1px 1px rgba(16,24,40,0.03), 0 1px 2px rgba(16,24,40,0.06); }

/* Unified, non-blurry title + meta for dark mode */
.pub-title { font-weight: 800; font-size: 16px; margin: 10px 0 6px 0; line-height: 1.25; color:#E6E8EB; }
.pub-title a { color:#E6E8EB; text-decoration:none; }
.pub-title a:hover { text-decoration: underline; }
.pub-meta  { font-size: 13px; color:#E6E8EB; margin-bottom: 8px; }  /* authors & venue = clear */

.pub-abstract { font-size: 13px; color: #E6E8EB; opacity: 0.95; }
.pub-tags { display:flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tag { font-size: 11.5px; padding: 4px 8px; border-radius: 999px; border: 1px solid #3a404c; color: #cfd5db; background:#2f343d; }

/* Carousel controls row */
.carousel-row { display:flex; align-items:center; gap:10px; justify-content:center; }
.carousel-btn { display:inline-block; padding:6px 10px; border-radius:8px; border:1px solid #3a404c; background:#2f343d; color:#cfd5db; font-size:12.5px; }
.carousel-btn:disabled { opacity:0.5; }

/* Center helper for images inside cards */
.center-row { display:flex; justify-content:center; }
</style>
"""

def _ensure_dirs():
    os.makedirs(ASSET_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

def _shorten(text: str, width=300):
    if not text:
        return ""
    return textwrap.shorten(text.replace("\n", " "), width=width, placeholder=" …")

def _render_image_carousel(pub_id: int, paths: List[str]):
    """
    Fixed-size, centered image carousel.
    - Uses st.session_state to track index per-publication.
    - Centers the image and constrains width to CAROUSEL_IMG_WIDTH.
    """
    clean_paths = [p for p in paths if p and os.path.exists(p)]
    if not clean_paths:
        # minimal empty spacer to keep layout consistent
        st.markdown('<div class="center-row"><div style="width:520px;height:180px;border:1px dashed #3a404c;border-radius:8px;opacity:.4;"></div></div>', unsafe_allow_html=True)
        return

    key = f"carousel_idx_{pub_id}"
    if key not in st.session_state:
        st.session_state[key] = 0

    n = len(clean_paths)
    idx = st.session_state[key] % n

    # Centered image with fixed width
    colL, colM, colR = st.columns([1, 6, 1])
    with colM:
        st.image(clean_paths[idx], caption=None, width=CAROUSEL_IMG_WIDTH)

    # Prev / Next centered under the image
    cprev, csp, cnext = st.columns([0.15, 0.70, 0.15])
    with cprev:
        if st.button("◀", key=f"prev_{pub_id}"):
            st.session_state[key] = (idx - 1) % n
            st.rerun()
    with cnext:
        if st.button("▶", key=f"next_{pub_id}"):
            st.session_state[key] = (idx + 1) % n
            st.rerun()

def show_publish(username: str | None = None):
    """
    ResearchGate-style publications page:
      - "Add publication" button + form (title, authors, venue, year, abstract, tags, figures, link, PDF)
      - Cards below with fixed-size centered image carousel
      - PDF download if uploaded
      - Sorted by year DESC, then created_at DESC (latest at top)
    """
    ensure_publications_table()
    _ensure_dirs()

    st.title("Publications")
    st.markdown(_PUB_CSS, unsafe_allow_html=True)

    # Load
    rows = get_publications()  # list of dicts
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "id","title","authors","venue","year","abstract","tags",
        "figure_paths","pdf_path","link","created_at","updated_at"
    ])

    # Sort: latest year first, and within the same year latest created_at first
    if not df.empty:
        # to_datetime handles current TEXT timestamps gracefully
        df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
        # ensure year is numeric for sort; if missing, treat as 0
        df["year_num"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values(["year_num", "created_at_dt"], ascending=[False, False], kind="mergesort").drop(columns=["year_num", "created_at_dt"])

    # ---- Toolbar: filters + "Add publication" button ----
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.4, 1.2])
    with c1:
        yopts = ["All"] + (sorted({str(y) for y in df["year"].dropna().astype(str)}) if not df.empty else [])
        ypick = st.selectbox("Year", yopts)
    with c2:
        vopts = ["All"] + (sorted({v for v in df["venue"].dropna().astype(str)}) if not df.empty else [])
        vpick = st.selectbox("Venue", vopts)
    with c3:
        keyword = st.text_input("Search in title/abstract/authors", placeholder="keyword…")
    with c4:
        add_clicked = st.button("➕ Add publication")

    # Simple state: show form or not
    if "show_pub_form" not in st.session_state:
        st.session_state.show_pub_form = False
    if add_clicked:
        st.session_state.show_pub_form = True
    if df.empty:  # auto-open on first visit
        st.session_state.show_pub_form = True

    # ---- Form to add publication ----
    if st.session_state.show_pub_form:
        with st.form("pub_form", clear_on_submit=False):
            st.subheader("Add Publication")

            title = st.text_input("Title *")
            authors = st.text_input("Authors (comma‑separated) *", placeholder="A. Author, B. Coauthor")
            venue = st.text_input("Venue / Journal / Conference *", placeholder="Journal of X")
            year = st.number_input("Year *", min_value=1900, max_value=datetime.date.today().year + 1, step=1, value=datetime.date.today().year)
            link = st.text_input("External Link / DOI", placeholder="https://doi.org/… or full URL")
            tags = st.text_input("Tags (comma‑separated)", placeholder="AI, Manufacturing, Sensors")
            abstract = st.text_area("Abstract", height=180, placeholder="Paste abstract here…")

            figures = st.file_uploader("Figures (PNG/JPG, multiple allowed)", type=["png","jpg","jpeg"], accept_multiple_files=True)
            pdf_file = st.file_uploader("Paper PDF (optional)", type=["pdf"], accept_multiple_files=False)

            colf1, colf2 = st.columns([1, 1])
            with colf1:
                submitted = st.form_submit_button("Save Publication", type="primary")
            with colf2:
                cancel = st.form_submit_button("Cancel")

            if cancel:
                st.session_state.show_pub_form = False
                st.rerun()

            if submitted:
                if not title.strip() or not authors.strip() or not venue.strip() or not str(year).strip():
                    st.warning("Please fill in Title, Authors, Venue and Year.")
                else:
                    # Save figures
                    fig_paths = []
                    for f in (figures or []):
                        ext = os.path.splitext(f.name)[1].lower()
                        name = f"{uuid.uuid4().hex}{ext}"
                        dest = os.path.join(IMG_DIR, name)
                        with open(dest, "wb") as out:
                            out.write(f.getbuffer())
                        fig_paths.append(dest)

                    # Save PDF (optional)
                    pdf_path = ""
                    if pdf_file:
                        name = f"{uuid.uuid4().hex}.pdf"
                        dest = os.path.join(PDF_DIR, name)
                        with open(dest, "wb") as out:
                            out.write(pdf_file.getbuffer())
                        pdf_path = dest

                    # Insert
                    add_publication(
                        title=title.strip(),
                        authors=authors.strip(),
                        venue=venue.strip(),
                        year=int(year),
                        abstract=abstract.strip() if abstract else "",
                        tags=tags.strip() if tags else "",
                        figure_paths=";".join(fig_paths),
                        pdf_path=pdf_path,
                        link=link.strip() if link else ""
                    )

                    st.success("Publication saved.")
                    st.session_state.show_pub_form = False
                    st.rerun()

    st.write("---")
    st.subheader("Overview")

    # ---- Apply filters to df ----
    if not df.empty:
        if ypick != "All":
            df = df[df["year"].astype(str) == ypick]
        if vpick != "All":
            df = df[df["venue"].astype(str) == vpick]
        if keyword.strip():
            k = keyword.lower()
            df = df[
                df["title"].astype(str).str.lower().str.contains(k, na=False)
                | df["abstract"].astype(str).str.lower().str.contains(k, na=False)
                | df["authors"].astype(str).str.lower().str.contains(k, na=False)
            ]

    if df.empty:
        st.info("No publications yet. Click **➕ Add publication** to create your first record.")
        return

    # CSV export
    exp = df[["title","authors","venue","year","tags","link","abstract"]].copy()
    st.download_button(
        "⬇ Download list (CSV)",
        data=exp.to_csv(index=False).encode("utf-8"),
        file_name="publications.csv",
        mime="text/csv"
    )

    # ---- Grid of cards ----
    st.markdown('<div class="pub-grid">', unsafe_allow_html=True)

    for _, r in df.iterrows():
        title = r.get("title","")
        authors = r.get("authors","")
        venue = r.get("venue","")
        year = r.get("year","")
        abstract = r.get("abstract","")
        tags = r.get("tags","")
        link = r.get("link","")
        figure_paths = (r.get("figure_paths","") or "").split(";") if r.get("figure_paths") else []
        pdf_path = r.get("pdf_path","") or ""

        # Card open
        st.markdown('<div class="pub-card">', unsafe_allow_html=True)

        # --- Fixed-size, centered carousel ---
        _render_image_carousel(int(r["id"]), figure_paths)

        # Title (link if available)
        if link:
            st.markdown(f'<div class="pub-title">{link}{title}</a></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="pub-title">{title}</div>', unsafe_allow_html=True)

        # Meta (Authors · Venue (Year)) — not blurred
        st.markdown(f'<div class="pub-meta">{authors} &nbsp;&middot;&nbsp; {venue} ({year})</div>', unsafe_allow_html=True)

        # Abstract (short + expander for full)
        short_abs = _shorten(abstract, width=380)
        if short_abs and short_abs != abstract:
            st.markdown(f'<div class="pub-abstract">{short_abs}</div>', unsafe_allow_html=True)
            with st.expander("Read full abstract"):
                st.write(abstract)
        else:
            st.markdown(f'<div class="pub-abstract">{abstract}</div>', unsafe_allow_html=True)

        # Tags
        if tags.strip():
            chips = " ".join([f'<span class="tag">{t.strip()}</span>' for t in tags.split(",") if t.strip()])
            st.markdown(f'<div class="pub-tags">{chips}</div>', unsafe_allow_html=True)

        # Actions: Download PDF (if uploaded) + Delete
        c1, c2 = st.columns([0.55, 0.45])
        with c1:
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "📄 Download PDF",
                        data=f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )
        with c2:
            if st.button("Delete", key=f"del_{r['id']}"):
                # Best-effort cleanup of files
                for p in figure_paths:
                    try:
                        if p and os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                try:
                    if pdf_path and os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception:
                    pass
                delete_publication(int(r["id"]))
                st.success("Deleted.")
                st.rerun()

        # Card close
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # grid close