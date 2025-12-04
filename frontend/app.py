import streamlit as st

st.set_page_config(layout="wide")

home_page = st.Page("pages/home.py", title="Home", icon=":material/home:")
projects_page = st.Page("pages/projects.py", title="Projects", icon=":material/list:")

pg = st.navigation([home_page, projects_page])
pg.run()