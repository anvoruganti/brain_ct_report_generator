"""Streamlit frontend application."""

import streamlit as st
from utils.api_client import APIClient

st.set_page_config(
    page_title="Brain CT Report Generator",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Brain CT Report Generator")
st.markdown("Generate clinical reports from Brain CT images using MONAI and LLM")

api_client = APIClient()

tab1, tab2 = st.tabs(["From Kheops", "Upload DICOM"])

with tab1:
    st.header("Generate Report from Kheops Album")

    album_token = st.text_input("Album Token", type="password", help="Enter your Kheops album token")

    if st.button("Fetch Studies", disabled=not album_token):
        try:
            with st.spinner("Fetching studies..."):
                studies = api_client.get_studies(album_token)
                st.session_state["studies"] = studies
                st.session_state["album_token"] = album_token
                st.success(f"Found {len(studies)} studies")
        except Exception as e:
            st.error(f"Error fetching studies: {str(e)}")

    if "studies" in st.session_state and st.session_state["studies"]:
        study_options = {
            f"{s.get('study_id', 'Unknown')} - {s.get('study_description', 'No description')}": s.get("study_id")
            for s in st.session_state["studies"]
        }
        selected_study_label = st.selectbox("Select Study", list(study_options.keys()))

        if selected_study_label:
            study_id = study_options[selected_study_label]

            if st.button("Fetch Series"):
                try:
                    with st.spinner("Fetching series..."):
                        series = api_client.get_series(study_id, st.session_state["album_token"])
                        st.session_state["series"] = series
                        st.session_state["selected_study_id"] = study_id
                        st.success(f"Found {len(series)} series")
                except Exception as e:
                    st.error(f"Error fetching series: {str(e)}")

            if "series" in st.session_state and st.session_state["series"]:
                series_options = {
                    f"{s.get('series_id', 'Unknown')} - {s.get('modality', 'Unknown')}": s.get("series_id")
                    for s in st.session_state["series"]
                }
                selected_series_label = st.selectbox("Select Series", list(series_options.keys()))

                if selected_series_label and st.button("Generate Report"):
                    series_id = series_options[selected_series_label]
                    try:
                        with st.spinner("Generating report... This may take a few minutes."):
                            result = api_client.generate_report_from_kheops(
                                st.session_state["album_token"],
                                study_id,
                                series_id,
                            )
                            st.session_state["report_result"] = result
                            st.success("Report generated successfully!")

                            display_report(result)
                    except Exception as e:
                        st.error(f"Error generating report: {str(e)}")

with tab2:
    st.header("Upload DICOM File")

    uploaded_file = st.file_uploader("Choose a DICOM file", type=["dcm", "dicom"])

    if uploaded_file and st.button("Generate Report"):
        try:
            with st.spinner("Generating report... This may take a few minutes."):
                dicom_bytes = uploaded_file.read()
                result = api_client.generate_report_from_dicom(dicom_bytes, uploaded_file.name)
                st.session_state["report_result"] = result
                st.success("Report generated successfully!")

                display_report(result)
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")

if "report_result" in st.session_state:
    st.sidebar.header("Latest Report")
    st.sidebar.json(st.session_state["report_result"])


def display_report(result: dict):
    """Display the generated report."""
    st.header("Generated Report")

    report = result.get("report", {})
    diagnosis = result.get("diagnosis", {})

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Clinical Report")
        if report.get("clinical_history"):
            st.write("**Clinical History:**")
            st.write(report["clinical_history"])

        if report.get("findings"):
            st.write("**Findings:**")
            st.write(report["findings"])

    with col2:
        st.subheader("Diagnosis")
        if diagnosis.get("abnormalities"):
            st.write("**Detected Abnormalities:**")
            for abnormality in diagnosis["abnormalities"]:
                st.write(f"- {abnormality}")

        if diagnosis.get("confidence_scores"):
            st.write("**Confidence Scores:**")
            for key, value in diagnosis["confidence_scores"].items():
                st.write(f"- {key}: {value:.2%}")

    if report.get("impression"):
        st.subheader("Impression")
        st.write(report["impression"])

    if report.get("recommendations"):
        st.subheader("Recommendations")
        st.write(report["recommendations"])
