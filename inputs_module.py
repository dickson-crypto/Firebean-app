# VERSION: v18.5.3
# TIMESTAMP: 2026-04-02 08:07:00 HKT

import streamlit as st
from PIL import Image, ImageOps
import io
import base64

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

    def _apply_module_css(self):
        """Internal module fix to ensure labels are visible in Light Mode."""
        is_dark = st.session_state.get('dark_mode', False)
        text_color = "#FFFFFF" if is_dark else "#121212"
        sub_color = "#AAAAAA" if is_dark else "#777777"
        
        st.markdown(f"""
            <style>
                .sub-label {{ 
                    color: {sub_color} !important; 
                    font-size: 14px; 
                    font-weight: 700; 
                    margin-bottom: 10px; 
                    text-transform: uppercase; 
                }}
                /* Secondary safety for Light Mode labels */
                label[data-testid="stWidgetLabel"] p {{ color: {text_color} !important; }}
            </style>
        """, unsafe_allow_html=True)

    def render_identity(self):
        """Renders Identity Section without Handshake button (now in app.py)."""
        self._apply_module_css()
        st.markdown('<div class="sec-header">Brand Identity</div>', unsafe_allow_html=True)
                
        c1, c2, c3 = st.columns(3)
        cl = c1.text_input("Client", value=st.session_state.form_data.get("client", ""), placeholder="e.g. Levi's")
        pr = c2.text_input("Project", value=st.session_state.form_data.get("project", ""), placeholder="e.g. Launch")
        vn = c3.text_input("Venue", value=st.session_state.form_data.get("venue", ""), placeholder="Location")
        
        d1, d2 = st.columns(2)
        yr = d1.selectbox("Year", [str(y) for y in range(2026, 2011, -1)], index=0)
        mo = d2.selectbox("Month", ["JAN", "FEB", "MAR", "APR", "MAY", "
