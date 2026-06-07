import os
import json
import logging
from dotenv import load_dotenv
from agent_l3 import run_code_generation_agent

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main_l3")

def main():
    logger.info("Initializing Level 3 Integration Code Generation Agent...")
    
    # Check if gap analysis output from Level 2 exists
    gaps_file = "gap_analysis_output.json"
    gaps_path = os.path.join(os.path.dirname(__file__), gaps_file)
    
    if not os.path.exists(gaps_path):
        logger.error(
            f"Required Level 2 output file not found: {gaps_path}. "
            "Please run 'main_l2.py' first to generate the gaps analysis."
        )
        return

    try:
        # Load gap analysis report
        logger.info(f"Loading gap analysis report from {gaps_path}...")
        with open(gaps_path, "r", encoding="utf-8") as f:
            gaps_report = json.load(f)

        gaps = gaps_report.get("prioritized_gaps", [])
        missing_gaps = [g for g in gaps if g.get("status") == "Missing"]
        
        logger.info(f"Loaded {len(gaps)} total gaps. Identified {len(missing_gaps)} missing integration(s) to generate.")

        if not missing_gaps:
            logger.info("No missing integrations found to process. Exiting.")
            return

        # Prepare output directory
        base_output_dir = os.path.join(os.path.dirname(__file__), "generated_connectors")
        os.makedirs(base_output_dir, exist_ok=True)
        logger.info(f"Connector output target folder: {base_output_dir}")

        for idx, gap in enumerate(missing_gaps, 1):
            src = gap.get("source_system")
            dst = gap.get("destination_system")
            note = gap.get("dependency_note", "")
            
            logger.info(f"--- Generating Connector [{idx}/{len(missing_gaps)}]: {src} -> {dst} ---")
            
            # Execute Level 3 agent code generation
            integration_files = run_code_generation_agent(src, dst, note)
            
            # Create a dedicated directory for this connector gap
            connector_folder_name = f"{src.lower()}_to_{dst.lower()}"
            connector_dir = os.path.join(base_output_dir, connector_folder_name)
            os.makedirs(connector_dir, exist_ok=True)
            
            # Write Python connector file
            py_filepath = os.path.join(connector_dir, integration_files.connector_filename)
            logger.info(f"Writing Python connector code to {py_filepath}...")
            with open(py_filepath, "w", encoding="utf-8") as f:
                f.write(integration_files.connector_code)
                
            # Write Agent YAML file
            yaml_filepath = os.path.join(connector_dir, integration_files.yaml_filename)
            logger.info(f"Writing Agent YAML configuration to {yaml_filepath}...")
            with open(yaml_filepath, "w", encoding="utf-8") as f:
                f.write(integration_files.yaml_content)
                
            # Write README instruction file
            readme_filepath = os.path.join(connector_dir, "README.md")
            logger.info(f"Writing README installation guide to {readme_filepath}...")
            with open(readme_filepath, "w", encoding="utf-8") as f:
                f.write(integration_files.readme_content)

            # Write requirements.txt manifest
            req_filepath = os.path.join(connector_dir, "requirements.txt")
            logger.info(f"Writing dependency manifest to {req_filepath}...")
            with open(req_filepath, "w", encoding="utf-8") as f:
                f.write(integration_files.requirements_content)

            # Write automated unit test file
            test_filepath = os.path.join(connector_dir, integration_files.tests_filename)
            logger.info(f"Writing automated unit tests to {test_filepath}...")
            with open(test_filepath, "w", encoding="utf-8") as f:
                f.write(integration_files.tests_code)

            logger.info(f"Successfully generated files in directory: {connector_dir}")

        logger.info("Level 3 Integration Code Generation completed successfully!")
        
    except Exception as e:
        logger.exception(f"An error occurred during Level 3 code generation: {e}")
        raise

if __name__ == "__main__":
    main()
