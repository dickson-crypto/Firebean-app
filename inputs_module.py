# VERSION: v18.9.0
# TIMESTAMP: 2026-04-05 01:10:00 HKT

import streamlit as st
from PIL import Image, ImageOps
import io
import base64

class InputEngine:
    def __init__(self):
        # 18-Point Scope of Work Matrix
        self.SOW = ["Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", "Event Planning", "Event Production", "RSVP Management", "Talent Management", "On-site Operation", "Technical Support"]

    def render_identity(self):
        st.markdown('<div class="sec-header">Brand Identity</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        cl = c1.text_input("Client", value=st.session_state.form_data.get("client", ""))
        pr = c2.text_input("Project", value=st.session_state.form_data.get("project", ""))
        vn = c3.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
        d1, d2 = st.columns(2)
        yr = d1.selectbox("Year", [str(y) for y in range(2026, 2011, -1)])
        mo = d2.selectbox("Month", ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], index=3)
        return cl, pr, vn, yr, mo

    def render_framework(self):
        st.markdown('<div class="sec-header">Strategic Framework</div>', unsafe_allow_html=True)
        cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
        c_cols = st.columns(4)
        sel_cat = [o for i, o in enumerate(cat_opts) if c_cols[i%4].checkbox(o, key=f"c_{o}", value=(o in st.session_state.form_data.get("category", [])))]
        wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
        w_cols = st.columns(3)
        sel_wwd = [o for i, o in enumerate(wwd_opts) if w_cols[i%3].checkbox(o, key=f"w_{o}", value=(o in st.session_state.form_data.get("what_we_do", [])))]
        st.markdown('<div class="sec-header">Scope of Work</div>', unsafe_allow_html=True)
        s_cols = st.columns(3)
        sel_sow = [o for i, o in enumerate(self.SOW) if s_cols[i%3].checkbox(o, key=f"s_{o}", value=(o in st.session_state.form_data.get("scope", [])))]
        return sel_cat, sel_wwd, sel_sow

    def render_assets(self):
        st.markdown('<div class="sec-header">Visual Assets</div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1, 1, 2])
        lb = a1.file_uploader("Logo Black", key="l_black")
        lw = a2.file_uploader("Logo White", key="l_white")
        ph = a3.file_uploader("Gallery (Max 8)", accept_multiple_files=True, key="p_gallery")
        
        encoded = []
        if ph:
            # HERO SELECTOR RADIO BUTTONS
            st.markdown('<div style="color:#E2231A; font-weight:900; margin:10px 0;">Select HERO Photo:</div>', unsafe_allow_html=True)
            num = len(ph[:8])
            opts = [f"Photo {i+1}" for i in range(num)]
            choice = st.radio("Hero Selector", options=opts, index=st.session_state.hero_index, horizontal=True, label_visibility="collapsed")
            st.session_state.hero_index = opts.index(choice)
            
            p_cols = st.columns(4)
            for idx, p in enumerate(ph[:8]):
                with p_cols[idx%4]:
                    img = Image.open(p); img = ImageOps.exif_transpose(img); img.thumbnail((500, 500))
                    buf = io.BytesIO(); img.convert('RGB').save(buf, format='JPEG', quality=65)
                    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    # Highlight selected Hero
                    border = "4px solid #E2231A" if st.session_state.hero_index == idx else "none"
                    st.markdown(f'<img src="data:image/jpeg;base64,{b64}" style="width:100%; border-radius:8px; border:{border};">', unsafe_allow_html=True)
                    encoded.append(b64)
        return lb, lw, ph, encoded

    def process_for_db(self, file):
        if not file: return None
        img = Image.open(file); img = ImageOps.exif_transpose(img); img.thumbnail((1200, 1200))
        buf = io.BytesIO(); img.convert('RGB').save(buf, format='JPEG', quality=75)
        return {"data": base64.b64encode(buf.getvalue()).decode('utf-8'), "mimeType": "image/jpeg", "ext": "jpg"}
