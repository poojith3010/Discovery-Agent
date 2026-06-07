import os
import time
import json
import logging
import argparse
from dotenv import load_dotenv
from unstructured.partition.auto import partition
from agent import run_discovery_agent, validate_inventory
from schemas import SystemInventory, SystemExtraction

# Load env variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

# Default mock document text used to bootstrap files if the directory is empty
DEFAULT_MOCK_DOC = """
# Aivar Innovations - Internal Systems Architecture Notes & Sprint Sync

## 1. Customer Relationship Management (CRM)
We use Salesforce to manage customer relations and tracking leads.
- Authentication: Standard OAuth2 flow.
- Key Entities: Customer, Lead, Account, Contact.
- Business Processes: Lead-to-Cash, Sales pipeline management, Customer support routing.
- Criticality: High (sales cannot operate without it).
- Status: Active.

## 2. ERP and Finance
All billing and financial tracking are managed in NetSuite, which acts as our general ledger and financial source of truth.
- Authentication: Token-Based Authentication (API Key).
- Key Entities: Invoice, Ledger, Payment, Vendor.
- Business Processes: Procure-to-Pay, Billing, Quarterly financial audits.
- Criticality: High.

## 3. Engineering & Bug Tracking
Engineering files bugs and plans sprints in Jira. It is highly valued for project management.
- Authentication: The docs do not explicitly state, but we probably use SAML SSO or individual user API keys.
- Key Entities: Ticket, Sprint, Epics.
- Business Processes: Software development lifecycle (SDLC) tracking.
- Criticality: Medium.

## 4. Messaging
We sometimes route logs and automated alerts to a Slack channel.
- Authentication: Webhook URL.
- Criticality: Low.

## 5. Miscellaneous Mentions
- During the sync, Sarah asked: "Are we still evaluating Coupa for procurement, or do we already have an active sandbox account there?" Nobody was sure.
- Dave mentioned that some teams might be using Trello for personal task boards, but it is not officially supported by IT.
"""

def bootstrap_test_directory(directory_path: str):
    """
    Creates the test directory and generates a sample text document
    if the directory does not exist or is empty.
    """
    os.makedirs(directory_path, exist_ok=True)
    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    
    if not files:
        logger.info(f"Target directory '{directory_path}' is empty. Bootstrapping with sample text documents...")
        # Write main sync notes
        notes_path = os.path.join(directory_path, "architecture_notes.txt")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_MOCK_DOC)
            
        # Write a smaller additional markdown file to test multi-file aggregation
        extra_path = os.path.join(directory_path, "additional_systems.md")
        with open(extra_path, "w", encoding="utf-8") as f:
            f.write("# Legacy Systems\nWe also maintain a legacy MongoDB database for user profiles (criticality Low, auth via Basic Auth, entities: UserProfile).")
            
        logger.info(f"Generated sample files: {os.listdir(directory_path)}")

def deduplicate_inventory(raw_inventory: SystemInventory) -> SystemInventory:
    """
    Accepts a SystemInventory containing raw extracted systems, groups them by name
    (case-insensitive), merges duplicates according to specific hierarchy/combining rules,
    and returns a clean, deduplicated SystemInventory.
    """
    groups = {}
    for system in raw_inventory.systems:
        key = system.name.strip().lower()
        if not key:
            continue
        if key not in groups:
            groups[key] = []
        groups[key].append(system)

    deduplicated_systems = []
    criticality_map = {"High": 3, "Medium": 2, "Low": 1}

    for key, group in groups.items():
        if len(group) == 1:
            # If there's only one system with this name, add it directly
            deduplicated_systems.append(group[0])
            continue

        # Merge logic
        # 1. Keep highest confidence_score
        merged_confidence = max(sys.confidence_score for sys in group)

        # Representative system: highest confidence, ties broken by order of appearance
        best_sys = max(group, key=lambda s: s.confidence_score)
        merged_name = best_sys.name
        merged_category = best_sys.category

        # 2. Keep the most definitive auth_method (non-empty and not "unknown" case-insensitive takes precedence)
        auth_methods = [sys.auth_method.strip() for sys in group]
        definitive_methods = [a for a in auth_methods if a and a.lower() != "unknown"]
        if definitive_methods:
            merged_auth_method = definitive_methods[0]
        else:
            merged_auth_method = "Unknown"

        # 3. Keep the highest criticality (High > Medium > Low)
        merged_criticality = max(
            (sys.criticality for sys in group),
            key=lambda c: criticality_map.get(c.capitalize(), 0)
        ).capitalize()

        # 4. Combine and deduplicate key_entities and business_processes
        seen_entities = set()
        merged_entities = []
        for sys in group:
            for entity in sys.key_entities:
                val = entity.strip()
                if val and val.lower() not in seen_entities:
                    seen_entities.add(val.lower())
                    merged_entities.append(entity)

        seen_processes = set()
        merged_processes = []
        for sys in group:
            for process in sys.business_processes:
                val = process.strip()
                if val and val.lower() not in seen_processes:
                    seen_processes.add(val.lower())
                    merged_processes.append(process)

        # 5. Concatenate the source_reference strings
        seen_refs = set()
        unique_refs = []
        for sys in group:
            ref = sys.source_reference.strip()
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                unique_refs.append(ref)
        merged_source_ref = "; ".join(unique_refs)

        # 6. If the new merged confidence_score is >= 95, clear the inferred_notes
        if merged_confidence >= 95:
            merged_inferred_notes = ""
        else:
            # Combine non-empty inferred notes
            notes_list = []
            for sys in group:
                note = sys.inferred_notes.strip()
                if note and note not in notes_list:
                    notes_list.append(note)
            merged_inferred_notes = "; ".join(notes_list) if notes_list else "Inferred details from multiple sources."

        # Re-build the merged SystemExtraction object
        merged_system = SystemExtraction(
            name=merged_name,
            category=merged_category,
            auth_method=merged_auth_method,
            key_entities=merged_entities,
            business_processes=merged_processes,
            criticality=merged_criticality,
            confidence_score=merged_confidence,
            inferred_notes=merged_inferred_notes,
            source_reference=merged_source_ref
        )
        deduplicated_systems.append(merged_system)

    return SystemInventory(systems=deduplicated_systems)

def main():
    parser = argparse.ArgumentParser(description="Discovery Agent Ingestion Pipeline (Level 1)")
    parser.add_argument(
        "--input_dir",
        type=str,
        default="./test_documents",
        help="Local directory path containing corporate documents to ingest."
    )
    args = parser.parse_args()

    logger.info("Initializing Level 1 Discovery Agent Ingestion Pipeline...")
    
    # Check/Generate .env file if missing
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    if not (openai_key or google_key) or openai_key == "your_openai_api_key_here" or google_key == "your_google_api_key_here":
        logger.warning("No valid API keys found in environment variables or .env file.")
        logger.info("Checking for a local .env file...")
        if not os.path.exists(".env"):
            logger.info("Creating a local template .env file from .env.example...")
            with open(".env.example", "r") as f_in:
                content = f_in.read()
            with open(".env", "w") as f_out:
                f_out.write(content)
        logger.info("Proceeding in Local Mock Simulation Mode...")

    # Ensure documents exist to read
    bootstrap_test_directory(args.input_dir)

    all_extracted_systems = []
    
    try:
        # Ingest files from the folder
        files = [f for f in os.listdir(args.input_dir) if os.path.isfile(os.path.join(args.input_dir, f))]
        logger.info(f"Ingesting documents from '{args.input_dir}'. Found {len(files)} file(s).")

        for file_name in files:
            file_path = os.path.join(args.input_dir, file_name)
            logger.info(f"Parsing document: {file_path}")
            
            try:
                # Use unstructured auto partition to extract text content
                elements = partition(filename=file_path)
                file_text = "\n".join([str(el) for el in elements])
                
                if not file_text.strip():
                    logger.warning(f"File '{file_name}' contains no readable text. Skipping.")
                    continue
                
                # Execute Level 1 systems discovery
                logger.info(f"Running discovery agent on content from '{file_name}'...")
                document_inventory = run_discovery_agent(file_text)
                
                # Annotate source document references
                for system in document_inventory.systems:
                    # Append the source document filename to the reference path
                    if not system.source_reference.strip():
                        system.source_reference = f"Document: {file_name}"
                    else:
                        system.source_reference = f"[{file_name}] {system.source_reference}"
                    
                    all_extracted_systems.append(system)
                    
            except Exception as e:
                logger.error(f"Error parsing or executing discovery on file '{file_name}': {e}", exc_info=True)
                # Continue processing other files instead of crashing
                continue

            # Pause to respect API rate limits
            logger.info("Pausing for 15 seconds to respect API rate limits...")
            time.sleep(15)

        # Aggregation
        logger.info(f"Aggregation complete. Discovered {len(all_extracted_systems)} system extractions total.")
        master_inventory = SystemInventory(systems=all_extracted_systems)

        # Deduplicate system inventory before audit validation
        logger.info("Running robust deduplication on master system inventory...")
        deduplicated_inventory = deduplicate_inventory(master_inventory)
        logger.info(f"Deduplication complete. Reduced {len(all_extracted_systems)} extractions to {len(deduplicated_inventory.systems)} unique systems.")

        # Validate and audit master inventory
        validated_inventory = validate_inventory(deduplicated_inventory)
        
        # Serialize to JSON and output
        output_filename = "inventory_output.json"
        output_path = os.path.join(os.path.dirname(__file__), output_filename)
        
        logger.info(f"Writing validated master system inventory to {output_path}...")
        
        inventory_dict = validated_inventory.model_dump()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(inventory_dict, f, indent=2, ensure_ascii=False)
            
        logger.info("Discovery ingestion execution completed successfully!")
        
    except Exception as e:
        logger.exception(f"An error occurred during discovery execution: {e}")
        raise

if __name__ == "__main__":
    main()
