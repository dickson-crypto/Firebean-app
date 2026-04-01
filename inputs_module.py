import streamlit as st
from PIL import Image, ImageOps
import io
import base64

# Attempt HEIC registration
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except: pass

class InputEngine:
    def __init__(self):
        self.SOW = [
            "Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", 
            "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", 
            "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", 
            "Event Planning", "Event Production", "RSVP Management", "Talent Management", 
            "On-site Operation", "Technical Support"
        ]

    def render_identity(self):
        st.markdown('<div class="sec-header">Brand Identity</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        cl = c1.text_input("Client", value=st.session_state.form_data.get("client", ""))
        pr = c2.text_input("Project", value=st.session_state.form_data.get("project", ""))
        vn = c3.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
        d1, d2 = st.columns(2)
        yr = d1.selectbox("Year", [str(y) for y in range(2026, 2011, -1)], index=0)
        mo = d2.selectbox("Month", ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], index=3)
        return cl, pr, vn, yr, mo

    def render_framework(self):
        st.markdown('<div class="sec-header">Strategic Framework</div>', unsafe_allow_html=True)
        cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
        cat_cols = st.columns(4)
        sel_cat = [o for i, o in enumerate(cat_opts) if cat_cols[i%4].checkbox(o, key=f"c_{o}", value=(o in st.session_state.form_data.get("category", [])))]
        
        wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
        wwd_cols = st.columns(3)
        sel_wwd = [o for i, o in enumerate(wwd_opts) if wwd_cols[i%3].checkbox(o, key=f"w_{o}", value=(o in st.session_state.form_data.get("what_we_do", [])))]
        
        st.markdown('<div class="sec-header">Scope of Work (18-Point Matrix)</div>', unsafe_allow_html=True)
        sow_cols = st.columns(3)
        sel_sow = [o for i, o in enumerate(self.SOW) if sow_cols[i%3].checkbox(o, key=f"s_{o}", value=(o in st.session_state.form_data.get("scope", [])))]
        return sel_cat, sel_wwd, sel_sow

    def render_assets(self):
        st.markdown('<div class="sec-header">Visual Assets Hub</div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1, 1, 2])
        lb = a1.file_uploader("Logo Black", key="l_b")
        lw = a2.file_uploader("Logo White", key="l_w")
        ph = a3.file_uploader("Gallery (Max 8)", accept_multiple_files=True, key="p_g")
        
        enc = []
        if ph:
            p_cols = st.columns(4)
            for idx, p in enumerate(ph[:8]):
                with p_cols[idx%4]:
                    img = Image.open(p)
                    # Mobile Orientation handling
                    w, h = img.size
                    st.image(img, caption="Portrait" if h > w else "Landscape", width="stretch")
                    if st.checkbox("HERO", key=f"h_{idx}", value=(st.session_state.hero_index == idx)):
                        st.session_state.hero_index = idx
                    buf = io.BytesIO(); img.save(buf, format='PNG')
                    enc.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
        return lb, lw, ph, enc

    def process_for_sync(self, file):
        if not file: return None
        try:
            img = Image.open(file)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1200, 1200))
            buf = io.BytesIO()
            img.convert('RGB').save(buf, format='JPEG', quality=75)
            return {"data": base64.b64encode(buf.getvalue()).decode('utf-8'), "mimeType": "image/jpeg", "ext": "jpg"}
        except: return None
