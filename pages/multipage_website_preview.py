import streamlit as st
import streamlit.components.v1 as components
import os

st.title("VeritasLogic.ai Complete Multi-Page Website")
st.write("**Production-ready multi-page website with all planned features implemented**")

# Load CSS and JS once and cache it
@st.cache_data
def load_assets():
    try:
        with open("veritaslogic_multipage_website/styles.css", "r") as f:
            css_content = f.read()
        with open("veritaslogic_multipage_website/script.js", "r") as f:
            js_content = f.read()
        return css_content, js_content
    except Exception as e:
        st.error(f"Could not load assets: {e}")
        return "", ""

css_content, js_content = load_assets()

def inject_styles(html_content):
    """Inject CSS and JS into HTML content"""
    if not css_content or not js_content:
        return html_content
    
    styled_content = html_content.replace(
        '<link rel="stylesheet" href="styles.css">',
        f'<style>{css_content}</style>'
    ).replace(
        '<script src="script.js"></script>',
        f'<script>{js_content}</script>'
    )
    return styled_content

# Create tabs for different pages
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "About", "Features", "Pricing", "Blog", "Contact"])

with tab1:
    st.subheader("Homepage (index.html)")
    st.write("**Hero section, trust indicators, feature summary, compliance, human review, blog preview, and CTA**")
    
    try:
        with open("veritaslogic_multipage_website/index.html", "r") as f:
            home_content = f.read()
        
        styled_content = inject_styles(home_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download Homepage",
            data=home_content,
            file_name="index.html",
            mime="text/html",
            key="download_home"
        )
        
    except FileNotFoundError:
        st.error("Homepage file not found.")

with tab2:
    st.subheader("About Us (about.html)")
    st.write("**Founder story, vision, values, team, and recognition sections**")
    
    try:
        with open("veritaslogic_multipage_website/about.html", "r") as f:
            about_content = f.read()
        
        styled_content = inject_styles(about_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download About Page",
            data=about_content,
            file_name="about.html",
            mime="text/html",
            key="download_about"
        )
        
    except FileNotFoundError:
        st.error("About page file not found.")

with tab3:
    st.subheader("Features (features.html)")
    st.write("**Detailed feature showcase, interactive demo, human review, security, and comparison table**")
    
    try:
        with open("veritaslogic_multipage_website/features.html", "r") as f:
            features_content = f.read()
        
        styled_content = inject_styles(features_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download Features Page",
            data=features_content,
            file_name="features.html",
            mime="text/html",
            key="download_features"
        )
        
    except FileNotFoundError:
        st.error("Features page file not found.")

with tab4:
    st.subheader("Pricing (pricing.html)")
    st.write("**Consumption-based pricing, add-ons, volume tiers, cost comparison, and FAQ**")
    
    try:
        with open("veritaslogic_multipage_website/pricing.html", "r") as f:
            pricing_content = f.read()
        
        styled_content = inject_styles(pricing_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download Pricing Page",
            data=pricing_content,
            file_name="pricing.html",
            mime="text/html",
            key="download_pricing"
        )
        
    except FileNotFoundError:
        st.error("Pricing page file not found.")

with tab5:
    st.subheader("Blog (blog.html)")
    st.write("**Separate blog section with full articles, categories, sidebar, and subscription**")
    
    try:
        with open("veritaslogic_multipage_website/blog.html", "r") as f:
            blog_content = f.read()
        
        styled_content = inject_styles(blog_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download Blog Page",
            data=blog_content,
            file_name="blog.html",
            mime="text/html",
            key="download_blog"
        )
        
    except FileNotFoundError:
        st.error("Blog page file not found.")

with tab6:
    st.subheader("Contact (contact.html)")
    st.write("**Trial signup, demo request, enterprise contact, academic pricing, and multiple contact forms**")
    
    try:
        with open("veritaslogic_multipage_website/contact.html", "r") as f:
            contact_content = f.read()
        
        styled_content = inject_styles(contact_content)
        components.html(styled_content, width=None, height=800, scrolling=True)
        
        st.download_button(
            label="Download Contact Page",
            data=contact_content,
            file_name="contact.html",
            mime="text/html",
            key="download_contact"
        )
        
    except FileNotFoundError:
        st.error("Contact page file not found.")

# Complete Website Download
st.markdown("---")
st.subheader("Complete Website Package")

try:
    # Create zip file content information
    files_info = {
        'index.html': 'Homepage with hero, features summary, and CTAs',
        'about.html': 'Founder story, credibility, and team information',
        'features.html': 'Detailed features with interactive demo previews',
        'pricing.html': 'Comprehensive pricing with volume tiers',
        'blog.html': 'Full blog with articles and categories',
        'contact.html': 'Multiple contact forms and trial signup',
        'styles.css': 'Complete CSS with responsive design',
        'script.js': 'JavaScript for interactions and forms'
    }
    
    st.write("**Website includes:**")
    for filename, description in files_info.items():
        if os.path.exists(f"veritaslogic_multipage_website/{filename}"):
            st.write(f"✅ `{filename}` - {description}")
        else:
            st.write(f"❌ `{filename}` - {description}")
    
    # Download individual files
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists("veritaslogic_multipage_website/styles.css"):
            with open("veritaslogic_multipage_website/styles.css", "r") as f:
                css_content = f.read()
            st.download_button(
                label="Download CSS File",
                data=css_content,
                file_name="styles.css",
                mime="text/css",
                key="download_css"
            )
    
    with col2:
        if os.path.exists("veritaslogic_multipage_website/script.js"):
            with open("veritaslogic_multipage_website/script.js", "r") as f:
                js_content = f.read()
            st.download_button(
                label="Download JavaScript File",
                data=js_content,
                file_name="script.js",
                mime="text/javascript",
                key="download_js"
            )

except Exception as e:
    st.error(f"Error accessing website files: {e}")

st.markdown("---")

# Implementation Notes
st.subheader("Implementation Features")
st.write("**✅ All Originally Missing Features Now Implemented:**")

features_implemented = [
    "🏗️ **Proper Multi-Page Structure** - Home, About, Features, Pricing, Blog, Contact",
    "📝 **Dedicated Blog Section** - Full articles, categories, reverse chronological order",
    "👥 **Human-in-the-Loop Feature** - Professional review service prominently featured",
    "🖼️ **Visual Placeholders** - Demo screenshots, professional headshots, memo previews",
    "🔒 **Enterprise Features** - Volume pricing, custom integrations, dedicated forms",
    "📱 **Mobile Responsive** - Full responsive design with mobile navigation",
    "⚡ **Interactive Elements** - Form validation, demo modals, progress animations",
    "🎨 **Professional Typography** - Playfair Display + Inter with full fallbacks",
    "🔧 **Complete JavaScript** - Form handling, animations, error management",
    "💼 **Business Ready** - Trial forms, enterprise contact, academic pricing"
]

for feature in features_implemented:
    st.write(feature)

st.markdown("---")
st.info("**Ready for Deployment**: Complete multi-page website with all originally specified features, professional design, and full functionality.")