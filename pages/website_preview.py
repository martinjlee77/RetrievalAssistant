import streamlit as st
import streamlit.components.v1 as components

st.title("VeritasLogic.ai Website Preview")
st.write("Preview of the website proof of concept")

# Read the HTML file and display it
try:
    with open("website_proof_of_concept.html", "r") as f:
        html_content = f.read()
    
    # Display the HTML content with full width and height
    components.html(html_content, width=None, height=1200, scrolling=True)
    
    st.markdown("---")
    st.info("💡 This is a proof of concept for the VeritasLogic.ai commercial website. The actual website would be deployed separately from this Streamlit app.")
    
    # Add download button for the HTML file
    st.download_button(
        label="Download HTML File",
        data=html_content,
        file_name="veritaslogic_website.html",
        mime="text/html"
    )
    
except FileNotFoundError:
    st.error("Website proof of concept file not found. Please make sure 'website_proof_of_concept.html' exists in the root directory.")