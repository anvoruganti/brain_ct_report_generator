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

st.header("Upload DICOM Series")

st.info("📁 Upload one or multiple DICOM files from a series. The system will analyze all images and generate a comprehensive report.")

# Allow multiple file upload
uploaded_files = st.file_uploader(
    "Choose DICOM file(s)", 
    type=["dcm", "dicom"],
    accept_multiple_files=True,
    help="Select one or multiple Brain CT DICOM files from your computer (e.g., a complete series)"
)

if uploaded_files:
    total_size = sum(f.size for f in uploaded_files)
    st.info(
        f"📄 Selected {len(uploaded_files)} file(s): "
        f"{', '.join([f.name for f in uploaded_files[:3]])}"
        f"{' ...' if len(uploaded_files) > 3 else ''} "
        f"({total_size / 1024 / 1024:.2f} MB total)"
    )
    
    # Show file list
    with st.expander("📋 View Selected Files", expanded=False):
        for idx, file in enumerate(uploaded_files, 1):
            st.write(f"{idx}. {file.name} ({file.size / 1024:.2f} KB)")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_button = st.button("🚀 Generate Report", type="primary", use_container_width=True)
    
    if generate_button:
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("🔄 Processing DICOM series and generating report... This may take a few minutes."):
                status_text.text(f"📤 Uploading {len(uploaded_files)} file(s)...")
                progress_bar.progress(0.1)
                
                # Read all files
                dicom_files_data = []
                for idx, uploaded_file in enumerate(uploaded_files):
                    dicom_bytes = uploaded_file.read()
                    dicom_files_data.append((dicom_bytes, uploaded_file.name))
                    progress_bar.progress(0.1 + (idx + 1) / len(uploaded_files) * 0.3)
                
                status_text.text(f"🔍 Analyzing {len(uploaded_files)} image(s) with MONAI model...")
                progress_bar.progress(0.4)
                
                # Generate report (API handles single vs multiple files)
                result = api_client.generate_report_from_dicom_series(
                    [data[0] for data in dicom_files_data],
                    [data[1] for data in dicom_files_data]
                )
                
                progress_bar.progress(0.9)
                status_text.text("📝 Generating clinical report with LLM...")
                
                st.session_state["report_result"] = result
                progress_bar.progress(1.0)
                status_text.text("✅ Report generated successfully!")
                
                st.success(f"✅ Successfully processed {len(uploaded_files)} image(s) and generated report!")
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
            
            # Show series processing info
            if metadata.get("total_images_processed"):
                st.divider()
                st.write(f"**Total Images Processed:** {metadata['total_images_processed']}")
                if metadata.get("total_images_uploaded"):
                    st.write(f"**Total Images Uploaded:** {metadata['total_images_uploaded']}")

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
