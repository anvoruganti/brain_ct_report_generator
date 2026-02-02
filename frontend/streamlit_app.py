"""Streamlit frontend application - PoC Version (Local DICOM Upload)."""

import json
import streamlit as st
from utils.api_client import APIClient

st.set_page_config(
    page_title="Brain CT Report Generator - PoC",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Brain CT Report Generator")
st.markdown("**PoC Version** - Upload DICOM files from your computer to generate clinical reports")

api_client = APIClient()

# Health check
try:
    health = api_client.health_check()
    st.sidebar.success("✅ Backend connected")
except Exception as e:
    st.sidebar.error(f"❌ Backend not available: {str(e)}")
    st.sidebar.info("Make sure the FastAPI backend is running on http://localhost:8000")
    st.stop()

st.header("Upload DICOM File")

# Allow multiple file types
uploaded_file = st.file_uploader(
    "Choose a DICOM file", 
    type=["dcm", "dicom"],
    help="Select a Brain CT DICOM file from your computer"
)

if uploaded_file:
    st.info(f"📄 Selected: {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_button = st.button("🚀 Generate Report", type="primary", use_container_width=True)
    
    if generate_button:
        try:
            with st.spinner("🔄 Processing DICOM file and generating report... This may take a few minutes."):
                dicom_bytes = uploaded_file.read()
                result = api_client.generate_report_from_dicom(dicom_bytes, uploaded_file.name)
                st.session_state["report_result"] = result
                st.success("✅ Report generated successfully!")
                display_report(result)
        except Exception as e:
            st.error(f"❌ Error generating report: {str(e)}")
            st.exception(e)

# Display report if available
if "report_result" in st.session_state:
    st.divider()
    display_report(st.session_state["report_result"])


def display_report(result: dict):
    """Display the generated report."""
    st.header("📋 Generated Clinical Report")

    report = result.get("report", {})
    diagnosis = result.get("diagnosis", {})
    metadata = result.get("dicom_metadata", {})

    # Display metadata
    if metadata:
        with st.expander("📊 DICOM Metadata", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if metadata.get("patient_id"):
                    st.write(f"**Patient ID:** {metadata['patient_id']}")
                if metadata.get("patient_name"):
                    st.write(f"**Patient Name:** {metadata['patient_name']}")
            with col2:
                if metadata.get("study_id"):
                    st.write(f"**Study ID:** {metadata['study_id']}")
                if metadata.get("series_id"):
                    st.write(f"**Series ID:** {metadata['series_id']}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏥 Clinical Report")
        if report.get("clinical_history"):
            st.write("**Clinical History:**")
            st.write(report["clinical_history"])

        if report.get("findings"):
            st.write("**Findings:**")
            st.write(report["findings"])

    with col2:
        st.subheader("🔍 Diagnosis")
        if diagnosis.get("abnormalities"):
            st.write("**Detected Abnormalities:**")
            for abnormality in diagnosis["abnormalities"]:
                st.write(f"- {abnormality}")
        else:
            st.info("No abnormalities detected")

        if diagnosis.get("confidence_scores"):
            st.write("**Confidence Scores:**")
            for key, value in diagnosis["confidence_scores"].items():
                st.write(f"- {key}: {value:.2%}")

    if report.get("impression"):
        st.subheader("💭 Impression")
        st.write(report["impression"])

    if report.get("recommendations"):
        st.subheader("💡 Recommendations")
        st.write(report["recommendations"])

    # Download option
    st.download_button(
        label="📥 Download Report as JSON",
        data=json.dumps(result, indent=2, default=str),
        file_name="clinical_report.json",
        mime="application/json"
    )
