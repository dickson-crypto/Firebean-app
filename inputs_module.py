# VERSION: v18.5.6
# TIMESTAMP: 2026-04-02 09:14:00 HKT

import streamlit as st
from PIL import Image, ImageOps
import io
import base64

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

class InputEngine:
    def __init__(self):
        self.SOW = [
            "Concept Development", "Branding Strategy", "PR Consulting", "Media Relations", 
            "Theme Design", "Visual Identity", "UI/UX Design", "Social Media Content", 
            "Influencer Seeding", "Video Production", "Motion Graphics", "Interactive Installation", 
            "Event Planning", "Event Production", "RSVP Management", "Talent Management", 
            "On-site Operation", "Technical Support"
        ]

    def _apply_module_css(self):
        """Internal module fix to ensure labels are visible in Light Mode."""
        is_dark = st.session_state.get('dark_mode', False)
        # Force text colors based on mode
        txt = "#FFFFFF" if is_dark else "#121212"
        sub = "#AAAAAA" if is_dark else "#555555"
        
        st.markdown(f"""
            <style>
                .sub-label {{ 
                    color: {sub} !important; 
                    font-size: 14px; 
                    font-weight: 700; 
                    margin-bottom: 10px; 
                    text-transform: uppercase; 
                }}
                /* Force all Streamlit widget labels in this module */
                label[data-testid="stWidgetLabel"] p {{ 
                    color: {txt} !important; 
                    font-weight: 500 !important; 
                }}
            </style>
        """, unsafe_allow_html=True)

    def render_identity(self):
        self._apply_module_css()
        st.markdown('<div class="sec-header">Brand Identity</div>', unsafe_allow_html=True)
                
        c1, c2, c3 = st.columns(3)
        cl = c1.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
        pr = c2.text_input("Project", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Launch")
        vn = c3.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
        
        d1, d2 = st.columns(2)
        yr = d1.selectbox("Year", [str(y) for y in range(2026, 2011, -1)], index=0)
        mo = d2.selectbox("Month", ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], index=3)
        return cl, pr, vn, yr, mo

    def render_framework(self):
        st.markdown('<div class="sec-header">Strategic Framework</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sub-label">Who we help</div>', unsafe_allow_html=True)
        cats = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
        c_cols = st.columns(4)
        sel_cat = [o for i, o in enumerate(cats) if c_cols[i%4].checkbox(o, key=f"cat_{o}", value=(o in st.session_state.form_data.get("category", [])))]
        
        st.markdown('<div class="sub-label">What we do</div>', unsafe_allow_html=True)
        wwds = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
        w_cols = st.columns(3)
        sel_wwd = [o for i, o in enumerate(wwds) if w_cols[i%3].checkbox(o, key=f"wwd_{o}", value=(o in st.session_state.form_data.get("what_we_do", [])))]
        
        st.markdown('<div class="sec-header">Scope of Work (18-Point Matrix)</div>', unsafe_allow_html=True)
        s_cols = st.columns(3)
        sel_sow = [o for i, o in enumerate(self.SOW) if s_cols[i%3].checkbox(o, key=f"sow_{o}", value=(o in st.session_state.form_data.get("scope", [])))]
        return sel_cat, sel_wwd, sel_sow

    def render_assets(self):
        st.markdown('<div class="sec-header">Visual Assets Hub</div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1, 1, 2])
        
        with a1:
            st.markdown('<div class="sub-label">Logo Black</div>', unsafe_allow_html=True)
            lb = st.file_uploader("B", key="l_black", label_visibility="collapsed")
            if lb: st.image(lb, use_container_width=True)
            
        with a2:
            st.markdown('<div class="sub-label">Logo White</div>', unsafe_allow_html=True)
            lw = st.file_uploader("W", key="l_white", label_visibility="collapsed")
            if lw:
                st.markdown('<div style="background-color:#2A2A2A; padding:15px; border-radius:8px; display: flex; align-items: center; justify-content: center;">', unsafe_allow_html=True)
                st.image(lw, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
        with a3:
            st.markdown('<div class="sub-label">Gallery (Max 8)</div>', unsafe_allow_html=True)
            ph = st.file_uploader("G", accept_multiple_files=True, key="p_gallery", label_visibility="collapsed")
        
        encoded = []
        if ph:
            st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)
            p_cols = st.columns(4)
            for idx, p in enumerate(ph[:8]):
                with p_cols[idx%4]:
                    img = Image.open(p)
                    st.image(img, caption="Portrait" if img.height > img.width else "Landscape", use_container_width=True)
                    if st.checkbox("HERO", key=f"hero_{idx}", value=(st.session_state.hero_index == idx)): st.session_state.hero_index = idx
                    buf = io.BytesIO(); img.save(buf, format='PNG'); encoded.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
        return lb, lw, ph, encoded

    def process_for_db(self, file):
        if not file: return None
        try:
            img = Image.open(file); img = ImageOps.exif_transpose(img); img.thumbnail((1200, 1200))
            buf = io.BytesIO(); img.convert('RGB').save(buf, format='JPEG', quality=75)
            return {"data": base64.b64encode(buf.getvalue()).decode('utf-8'), "mimeType": "image/jpeg", "ext": "jpg"}
        except Exception: return None
