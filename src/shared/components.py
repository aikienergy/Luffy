import streamlit as st
import os

def load_css(file_path="assets/style.css"):
    """
    Loads a CSS file and injects it into the Streamlit app.
    Should be called at the very beginning of the app.
    """
    # robust path handling
    if not os.path.exists(file_path):
        # try referencing relative to this file if default path fails
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # assuming src/shared/components.py -> root/assets/style.css
        # ../../assets/style.css
        file_path = os.path.join(base_dir, "../../assets/style.css")
    
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {file_path}")

def stats_card(label, value, subtext=None, variant="default", help_text=None):
    """
    Renders a unified Stats Card.
    
    Args:
        label (str): Title of the metric.
        value (str/float): The value to display.
        subtext (str, optional): Small text below the value (e.g. unit or diff).
        variant (str): 'default', 'success' (Emerald), 'danger' (Red).
        help_text (str, optional): Tooltip text (not implemented in HTML but kept for API compat).
    """
    variant_class = f"variant-{variant}" if variant else ""
    
    html = f"""
    <div class="stats-card {variant_class}">
        <label>{label}</label>
        <span class="value">{value}</span>
        {f'<span class="subtext">{subtext}</span>' if subtext else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def section_header(title, subtitle=None):
    """
    Renders a consistent section header.
    """
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)

def vertical_spacer(height_rem=1.0):
    """
    Renders a controlled vertical spacer.
    """
    st.markdown(f'<div class="spacer-vertical" style="height: {height_rem}rem;"></div>', unsafe_allow_html=True)

class CardContainer:
    """
    Context manager for Shadow Card layout.
    Wraps st.container(border=True) which is styled by CSS to look like a shadow card.
    """
    def __enter__(self):
        self.container = st.container(border=True)
        return self.container.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.container.__exit__(exc_type, exc_value, traceback)

def card_begin():
    # Deprecated for direct usage, but kept for compatibility if needed.
    # Cannot be strictly implemented without context manager in Streamlit.
    st.warning("card_begin helper is deprecated. Use 'with CardContainer():' instead.")

def card_end():
    pass
