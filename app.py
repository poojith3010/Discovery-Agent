import os
import io
import time
import json
import logging
import zipfile
import streamlit as st
import pandas as pd
import plotly.express as px

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("streamlit_app")

# Import the service functions
from main import run_level_1_service
from main_l2 import run_level_2_service, AUTOMATION_USE_CASES
from main_l3 import run_level_3_service

# 1. Page Configuration & Theme
st.set_page_config(
    page_title="Discovery Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to force deep dark-theme aesthetics and soften standard elements
st.markdown("""
<style>
    /* Force main dark background colors */
    .stApp {
        background-color: #0E1117 !important;
        color: #E2E8F0 !important;
    }
    
    /* Hide default headers and footers */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Set container margins */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metrics grid customization to match dark cards */
    div[data-testid="metric-container"] {
        background-color: #1A1C24 !important;
        border: 1px solid #2D313E !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Premium custom card style */
    .saas-card {
        background-color: #1A1C24;
        border: 1px solid #2D313E;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease-in-out, border-color 0.2s;
    }
    .saas-card:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    
    /* Badge tags */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 6px;
        text-transform: uppercase;
    }
    .badge-green { background-color: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.2); }
    .badge-orange { background-color: rgba(249, 115, 22, 0.15); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.2); }
    .badge-red { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
    .badge-blue { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); }
    
    /* Soften Streamlit Expanders */
    div[data-testid="stExpander"] {
        background-color: #1A1C24 !important;
        border: 1px solid #2D313E !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Typography customizations */
    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# 2. Header Area
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="font-weight: 800; font-size: 2.8rem; letter-spacing: -0.025em; background: linear-gradient(135deg, #06B6D4, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🔍 Discovery Agent
    </h1>
    <p style="color: #94A3B8; font-size: 1.1rem; max-width: 600px; margin: 0.3rem auto 0 auto; font-weight: 500;">
        Enterprise System Detection • Architecture Intelligence
    </p>
</div>
""", unsafe_allow_html=True)

# Vendor mappings for detail rendering
VENDOR_MAP = {
    "salesforce": "Salesforce Inc.",
    "netsuite": "Oracle Corporation",
    "jira": "Atlassian Corporation",
    "slack": "Salesforce Inc. (Slack)",
    "coupa": "Coupa Software",
    "trello": "Atlassian Corporation (Trello)",
    "mongodb": "MongoDB Inc."
}

# Define Tab Sections
tab1, tab2, tab3 = st.tabs([
    "Level 1: System Detection", 
    "Level 2: Gap Analysis", 
    "Level 3: Code Generation"
])

# ==============================================================================
# TAB 1: System Detection
# ==============================================================================
with tab1:
    st.subheader("Document Ingestion & Discovery Ingestion")
    
    uploaded_files = st.file_uploader(
        "Drag and drop files to detect software systems (PDF, DOCX, MD, TXT):",
        type=["txt", "md", "pdf"],
        accept_multiple_files=True
    )
    
    analyze_clicked = st.button("Analyze Documents", type="primary", use_container_width=True)
    
    if uploaded_files and analyze_clicked:
        import tempfile
        import os
        from unstructured.partition.auto import partition

        document_texts = []
        source_names = []
        
        with st.status("Ingesting and processing corpus...", expanded=True) as status:
            for file in uploaded_files:
                status.update(label=f"Partitioning & parsing: {file.name}...")
                
                # Write bytes to temporary file on disk (Windows lock-safe delete=False pattern)
                with tempfile.NamedTemporaryFile(delete=False, suffix=file.name) as temp_file:
                    temp_file.write(file.getvalue())
                    temp_path = temp_file.name
                
                try:
                    elements = partition(filename=temp_path)
                    text = "\n".join([str(el) for el in elements])
                    
                    if text.strip():
                        document_texts.append(text)
                        source_names.append(file.name)
                        status.write(f"✓ Successfully parsed: {file.name}")
                    else:
                        status.write(f"⚠️ Empty readable content: {file.name}")
                except Exception as e:
                    logger.error(f"Error parsing file '{file.name}': {e}")
                    status.write(f"❌ Failed to parse: {file.name}")
                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass
            
            if document_texts:
                status.update(label="Executing discovery models & deduplication engine...")
                try:
                    start_time = time.time()
                    inventory_dict = run_level_1_service(document_texts, source_names)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    # Store in session state
                    st.session_state.inventory_dict = inventory_dict
                    st.session_state.processing_time = elapsed_ms
                    st.session_state.gap_analysis_dict = None  # Reset Level 2 & 3
                    st.session_state.generated_code = None
                    
                    status.update(label="Ingestion and system extraction completed!", state="complete")
                    st.success("Analysis complete!")
                except Exception as e:
                    status.update(label="Agent run failed!", state="error")
                    st.error(f"Error running pipeline: {e}")
            else:
                st.error("No documents were parsed. Please check file formatting.")

    # Render Level 1 UI when data is present in state
    if "inventory_dict" in st.session_state and st.session_state.inventory_dict:
        inventory_dict = st.session_state.inventory_dict
        systems = inventory_dict.get("systems", [])
        
        # 1. Metrics Row
        st.markdown("### Process Metrics")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        total_systems = len(systems)
        unique_categories = len(set(sys.get("category", "") for sys in systems))
        
        avg_confidence = 0.0
        if total_systems > 0:
            avg_confidence = round(sum(sys.get("confidence_score", 0) for sys in systems) / total_systems, 1)
            
        processing_time = st.session_state.get("processing_time", 0)
        
        m_col1.metric("Systems Detected", f"{total_systems}")
        m_col2.metric("Categories", f"{unique_categories}")
        m_col3.metric("Avg Confidence", f"{avg_confidence}%")
        m_col4.metric("Processing Time", f"{processing_time} ms")
        
        # 2. Split Screen: System Catalog Table (Left) & Plotly Chart (Right)
        st.markdown("### Inventory & Analysis")
        layout_col1, layout_col2 = st.columns([1, 1])
        
        with layout_col1:
            st.markdown("#### System Inventory Table")
            df_data = []
            for sys in systems:
                vendor = VENDOR_MAP.get(sys.get("name", "").lower(), sys.get("name", "Unknown"))
                df_data.append({
                    "System": sys.get("name"),
                    "Vendor": vendor,
                    "Category": sys.get("category"),
                    "Confidence": f"{sys.get('confidence_score')}%"
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        with layout_col2:
            st.markdown("#### Confidence Analysis Chart")
            if total_systems > 0:
                df_chart = pd.DataFrame([
                    {
                        "System": sys.get("name"),
                        "Confidence": sys.get("confidence_score")
                    }
                    for sys in systems
                ]).sort_values(by="Confidence", ascending=True)
                
                fig = px.bar(
                    df_chart,
                    x="Confidence",
                    y="System",
                    orientation="h",
                    color="Confidence",
                    color_continuous_scale=[[0, "rgb(239, 68, 68)"], [0.6, "rgb(249, 115, 22)"], [1.0, "rgb(6, 182, 212)"]],
                    range_x=[0, 100],
                    labels={"Confidence": "Confidence Score (%)"}
                )
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=10, b=10),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No systems to display.")

        # 3. Evidence Explorer & Export
        st.markdown("### Evidence Explorer & Export")
        for sys in systems:
            with st.expander(f"📁 Source Evidence: {sys.get('name')}"):
                col_left, col_right = st.columns([1, 3])
                with col_left:
                    st.write("**Details:**")
                    st.write(f"- Category: `{sys.get('category')}`")
                    st.write(f"- Authentication: `{sys.get('auth_method')}`")
                    st.write(f"- Criticality: `{sys.get('criticality')}`")
                    
                    sys_json = json.dumps(sys, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=sys_json,
                        file_name=f"{sys.get('name').lower()}_inventory.json",
                        mime="application/json",
                        key=f"dl_{sys.get('name').lower()}",
                        use_container_width=True
                    )
                with col_right:
                    st.json(sys)
    else:
        st.info("Ingest documents and run discovery to view detected system data.")

# ==============================================================================
# TAB 2: Gap Analysis
# ==============================================================================
with tab2:
    st.subheader("Integration Gaps & Use Case Mapping")
    
    if "inventory_dict" not in st.session_state or not st.session_state.inventory_dict:
        st.warning("⚠️ Please complete the **Level 1: System Detection** tab first.")
    else:
        st.write("Specify use cases for analysis (one per line):")
        use_cases_text = st.text_area(
            "Automation Use Cases",
            value="\n".join(AUTOMATION_USE_CASES),
            height=150,
            label_visibility="collapsed"
        )
        use_cases_list = [line.strip() for line in use_cases_text.split("\n") if line.strip()]
        
        run_gap_clicked = st.button("Run Architecture Gap Analysis", type="primary", use_container_width=True)
        
        if run_gap_clicked:
            with st.spinner("Executing gap prioritization models..."):
                try:
                    gap_analysis_dict = run_level_2_service(st.session_state.inventory_dict, use_cases_list)
                    st.session_state.gap_analysis_dict = gap_analysis_dict
                    st.session_state.generated_code = None  # Reset level 3
                    st.success("Gap analysis complete!")
                except Exception as e:
                    st.error(f"Error running gap analysis: {e}")
                    
        # Render Level 2 UI when data exists in state
        if "gap_analysis_dict" in st.session_state and st.session_state.gap_analysis_dict:
            gaps_report = st.session_state.gap_analysis_dict
            gaps = gaps_report.get("prioritized_gaps", [])
            use_case_mappings = gaps_report.get("use_case_mappings", [])
            
            # Map System Confidences from Level 1
            sys_confidence = {}
            for sys in st.session_state.inventory_dict.get("systems", []):
                sys_confidence[sys["name"].lower()] = sys["confidence_score"]
                
            # Compute Risk Metrics
            total_gaps = len(gaps)
            complex_gaps = sum(1 for g in gaps if g.get("estimated_effort") == "Complex" and g.get("status") == "Missing")
            
            critical_risks = 0
            for g in gaps:
                if g.get("status") == "Missing":
                    # Get associated confidence
                    src_c = sys_confidence.get(g.get("source_system", "").lower(), 100)
                    dst_c = sys_confidence.get(g.get("destination_system", "").lower(), 100)
                    min_c = min(src_c, dst_c)
                    
                    if g.get("estimated_effort") == "Complex" or min_c < 70:
                        critical_risks += 1
                        
            # 1. Metrics Grid
            st.markdown("### Risk Metrics")
            g_col1, g_col2, g_col3 = st.columns(3)
            g_col1.metric("Total Gaps Identified", f"{total_gaps}")
            g_col2.metric("Complex Integrations", f"{complex_gaps}")
            g_col3.metric("Critical Risks", f"{critical_risks}")
            
            # 2. DataFrame Catalog & Plotly Scatter Chart
            st.markdown("### Prioritized Gaps & Impact Analysis")
            g_layout1, g_layout2 = st.columns([1, 1])
            
            with g_layout1:
                st.markdown("#### Gap Table")
                df_gap_data = []
                for g in gaps:
                    df_gap_data.append({
                        "Source": g.get("source_system"),
                        "Destination": g.get("destination_system"),
                        "Status": g.get("status"),
                        "Effort": g.get("estimated_effort"),
                        "Sequencing Note": g.get("dependency_note")
                    })
                df_gap = pd.DataFrame(df_gap_data)
                st.dataframe(df_gap, use_container_width=True, hide_index=True)
                
            with g_layout2:
                st.markdown("#### Risk Analysis Chart")
                # Prepare scatter data
                df_scatter_data = []
                for g in gaps:
                    # Resolve impact score from mapping
                    impact = 5
                    for mapping in use_case_mappings:
                        involved = [s.lower() for s in mapping.get("involved_systems", [])]
                        if g.get("source_system", "").lower() in involved and g.get("destination_system", "").lower() in involved:
                            impact = max(impact, mapping.get("business_impact_score", 5))
                            
                    src_c = sys_confidence.get(g.get("source_system", "").lower(), 100)
                    dst_c = sys_confidence.get(g.get("destination_system", "").lower(), 100)
                    min_c = min(src_c, dst_c)
                    
                    if min_c >= 95:
                        conf_level = "High"
                    elif min_c >= 70:
                        conf_level = "Medium"
                    else:
                        conf_level = "Low"
                        
                    df_scatter_data.append({
                        "Integration": f"{g.get('source_system')} ➔ {g.get('destination_system')}",
                        "Estimated Effort": g.get("estimated_effort"),
                        "Business Impact": impact,
                        "Confidence Level": conf_level
                    })
                    
                if df_scatter_data:
                    df_scatter = pd.DataFrame(df_scatter_data)
                    fig_scatter = px.scatter(
                        df_scatter,
                        x="Estimated Effort",
                        y="Business Impact",
                        color="Confidence Level",
                        size="Business Impact",
                        hover_name="Integration",
                        color_discrete_map={"High": "#06B6D4", "Medium": "#3B82F6", "Low": "#EF4444"},
                        category_orders={"Estimated Effort": ["Low", "Medium", "High", "Complex"]},
                        range_y=[0, 11]
                    )
                    fig_scatter.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.info("No gap data to plot.")

            # 3. Detailed Gap Explorer
            st.markdown("### Detailed Gap Explorer")
            for idx, g in enumerate(gaps):
                src_sys = g.get("source_system", "")
                dst_sys = g.get("destination_system", "")
                
                # Check confidence level
                src_c = sys_confidence.get(src_sys.lower(), 100)
                dst_c = sys_confidence.get(dst_sys.lower(), 100)
                min_c = min(src_c, dst_c)
                
                status_str = g.get("status")
                status_badge = "badge-green" if status_str == "Available" else "badge-red"
                effort_str = g.get("estimated_effort")
                effort_badge = "badge-red" if effort_str == "Complex" else ("badge-orange" if effort_str == "High" else ("badge-blue" if effort_str == "Medium" else "badge-green"))
                
                with st.expander(f"🔗 Link: {src_sys} ➔ {dst_sys}"):
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <span class="badge {status_badge}">Status: {status_str}</span>
                        <span class="badge {effort_badge}">Effort: {effort_str}</span>
                        <span class="badge badge-gray">Min Confidence: {min_c}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Highlight critical dependency risk warnings
                    if status_str == "Missing" and (effort_str == "Complex" or min_c < 70):
                        st.error(
                            f"🚨 **Dependency Risk Alert:** This missing integration link involves a system with "
                            f"Low Confidence ({min_c}%) or is flagged as Complex. Direct architecture verification is required."
                        )
                        
                    st.write(f"**Description / Sequencing Note:**")
                    st.write(g.get("dependency_note"))

# ==============================================================================
# TAB 3: Code Generation
# ==============================================================================
with tab3:
    st.subheader("Integration Connector Generation")
    
    if "gap_analysis_dict" not in st.session_state or not st.session_state.gap_analysis_dict:
        st.warning("⚠️ Please complete the **Level 2: Gap Analysis** tab first.")
    else:
        gaps = st.session_state.gap_analysis_dict.get("prioritized_gaps", [])
        missing_gaps = [g for g in gaps if g.get("status") == "Missing"]
        
        if not missing_gaps:
            st.success("🎉 All integration systems are configured and 'Available'. No code generation is necessary!")
        else:
            st.write(f"Scaffolding files can be compiled for the following **{len(missing_gaps)} missing integration(s)**:")
            for g in missing_gaps:
                st.markdown(f"- `{g.get('source_system')} ➔ {g.get('destination_system')}` (Effort: `{g.get('estimated_effort')}`)")
                
            code_gen_clicked = st.button("Generate Integration Code", type="primary", use_container_width=True)
            
            if code_gen_clicked:
                with st.status("Initializing Senior Integration Engineer code compilers...", expanded=True) as status:
                    try:
                        results = run_level_3_service(st.session_state.gap_analysis_dict)
                        st.session_state.generated_code = results
                        status.update(label="All connector scaffolds compiled successfully!", state="complete")
                        st.success("Scaffolding files generated!")
                    except Exception as e:
                        status.update(label="Generation failed!", state="error")
                        st.error(f"Error compiling connectors: {e}")
                        
            # Render Generation Results
            if "generated_code" in st.session_state and st.session_state.generated_code:
                code_results = st.session_state.generated_code
                
                # Zipping files in memory for download
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for item in code_results:
                        src = item["source_system"].lower()
                        dst = item["destination_system"].lower()
                        folder_name = f"{src}_to_{dst}/"
                        
                        zip_file.writestr(folder_name + item["connector_filename"], item["connector_code"])
                        zip_file.writestr(folder_name + item["yaml_filename"], item["yaml_content"])
                        zip_file.writestr(folder_name + "README.md", item["readme_content"])
                        zip_file.writestr(folder_name + "requirements.txt", item["requirements_content"])
                        zip_file.writestr(folder_name + item["tests_filename"], item["tests_code"])
                
                zip_buffer.seek(0)
                
                st.markdown("### Export Scaffolding Pack")
                st.download_button(
                    label="Download All Connectors (ZIP)",
                    data=zip_buffer,
                    file_name="generated_connectors.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                st.markdown("### Generated Code Explorer")
                for item in code_results:
                    expander_label = f"📦 Connector: {item['source_system']} to {item['destination_system']}"
                    with st.expander(expander_label):
                        code_tabs = st.tabs(["Python", "YAML", "README"])
                        
                        with code_tabs[0]:
                            st.caption(f"Filename: `{item['connector_filename']}`")
                            st.code(item["connector_code"], language="python")
                            
                        with code_tabs[1]:
                            st.caption(f"Filename: `{item['yaml_filename']}`")
                            st.code(item["yaml_content"], language="yaml")
                            
                        with code_tabs[2]:
                            st.markdown(item["readme_content"])
