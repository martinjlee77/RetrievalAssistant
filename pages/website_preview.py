import streamlit as st
import streamlit.components.v1 as components

st.title("VeritasLogic.ai Website Preview")
st.write("Website options and complete build:")

# Create tabs for the options and final version
tab1, tab2, tab3, tab4 = st.tabs(["Option 1: High Contrast", "Option 2: Subtle Contrast", "Option 3: Monochromatic", "Complete Website"])

with tab1:
    st.subheader("Option 1: High Contrast")
    st.write("**Colors:** #64B5F6 (vibrant blue) + #A7CCD1 (gray-blue) accents")
    st.write("Strong visual contrast for calls to action with lighter accents for balance.")
    
    try:
        with open("website_option1_high_contrast.html", "r") as f:
            html_content1 = f.read()
        
        components.html(html_content1, width=None, height=1000, scrolling=True)
        
        st.download_button(
            label="Download Option 1",
            data=html_content1,
            file_name="veritaslogic_option1_high_contrast.html",
            mime="text/html",
            key="download1"
        )
        
    except FileNotFoundError:
        st.error("Option 1 file not found.")

with tab2:
    st.subheader("Option 2: Subtle Contrast")
    st.write("**Colors:** #42A5F5 (darker blue) + #8AB4D2 (blue-gray) accents")
    st.write("More subtle contrast maintaining a unified color scheme.")
    
    try:
        with open("website_option2_subtle_contrast.html", "r") as f:
            html_content2 = f.read()
        
        components.html(html_content2, width=None, height=1000, scrolling=True)
        
        st.download_button(
            label="Download Option 2",
            data=html_content2,
            file_name="veritaslogic_option2_subtle_contrast.html",
            mime="text/html",
            key="download2"
        )
        
    except FileNotFoundError:
        st.error("Option 2 file not found.")

with tab3:
    st.subheader("Option 3: Monochromatic with Texture")
    st.write("**Colors:** White accents only with gradient overlays and transparency effects")
    st.write("Sophisticated monochromatic approach using texture, shadows, and subtle gradients.")
    
    try:
        with open("website_option3_monochromatic.html", "r") as f:
            html_content3 = f.read()
        
        components.html(html_content3, width=None, height=1000, scrolling=True)
        
        st.download_button(
            label="Download Option 3",
            data=html_content3,
            file_name="veritaslogic_option3_monochromatic.html",
            mime="text/html",
            key="download3"
        )
        
    except FileNotFoundError:
        st.error("Option 3 file not found.")

with tab4:
    st.subheader("Complete Production Website")
    st.write("**Full-featured website** with all sections, contact forms, and enhanced content")
    st.write("Based on Option 3 with complete build-out including pricing, testimonials, and contact functionality.")
    
    try:
        with open("veritaslogic_complete_website.html", "r") as f:
            html_content4 = f.read()
        
        components.html(html_content4, width=None, height=1200, scrolling=True)
        
        st.download_button(
            label="Download Complete Website",
            data=html_content4,
            file_name="veritaslogic_complete_website.html",
            mime="text/html",
            key="download4"
        )
        
    except FileNotFoundError:
        st.error("Complete website file not found.")

st.markdown("---")
st.info("These are design options for the VeritasLogic.ai commercial website. The Complete Website tab shows the full production-ready version with all features implemented.")