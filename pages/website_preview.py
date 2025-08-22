import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Website Preview", layout="wide")

st.title("VeritasLogic.ai Website Preview")
st.write("Preview of the website proof of concept")

# Read the HTML file and display it
with open("website_proof_of_concept.html", "r") as f:
    html_content = f.read()

# Display the HTML content
components.html(html_content, height=800, scrolling=True)

st.markdown("---")
st.write("This is a preview of the website proof of concept. The actual website would be deployed separately.")