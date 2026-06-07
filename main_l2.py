import os
import json
import logging
from dotenv import load_dotenv
from agent_l2 import run_gap_analysis

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main_l2")

# Define the mock automation use cases
AUTOMATION_USE_CASES = [
    "When a Salesforce Opportunity closes, create a NetSuite customer and invoice.",
    "When a high-priority Jira bug is created, send a Slack message.",
    "When a payment is processed in NetSuite, notify Slack.",
    "When a procurement request is raised in Coupa, sync customer details to Salesforce.",
    "For team task updates on Trello, sync to Jira."
]

def main():
    logger.info("Initializing Level 2 Discovery Agent...")
    
    # Check if inventory output from Level 1 exists
    inventory_file = "inventory_output.json"
    inventory_path = os.path.join(os.path.dirname(__file__), inventory_file)
    
    if not os.path.exists(inventory_path):
        logger.error(
            f"Required Level 1 output file not found: {inventory_path}. "
            "Please run 'main.py' first to generate the systems inventory."
        )
        return

    try:
        # Load Level 1 inventory
        logger.info(f"Loading system inventory from {inventory_path}...")
        with open(inventory_path, "r", encoding="utf-8") as f:
            inventory_json = json.load(f)
            
        logger.info(f"Loaded {len(inventory_json.get('systems', []))} systems from inventory.")

        # Run Level 2 gap analysis
        logger.info("Executing use case mapping and integration gap analysis...")
        report = run_gap_analysis(inventory_json, AUTOMATION_USE_CASES)
        
        # Serialize to JSON and output
        output_file = "gap_analysis_output.json"
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        
        logger.info(f"Writing Gap Analysis Report to {output_path}...")
        
        report_dict = report.model_dump()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        logger.info("Level 2 Gap Analysis completed successfully!")
        
    except Exception as e:
        logger.exception(f"An error occurred during Level 2 gap analysis: {e}")
        raise

if __name__ == "__main__":
    main()
