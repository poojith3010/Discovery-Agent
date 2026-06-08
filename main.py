import os
import time
import json
import logging
from typing import List
from dotenv import load_dotenv
import typer
from rich.logging import RichHandler
from unstructured.partition.auto import partition
from agent import run_discovery_agent, validate_inventory
from schemas import SystemInventory, SystemExtraction

# Load env variables from .env file
load_dotenv()

# Setup logging with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
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

def run_level_1_service(document_texts: List[str], source_names: List[str] = None) -> dict:
    """
    Service function for Level 1 system discovery.
    Accepts a list of document strings, runs systems extraction, deduplicates,
    and returns a validated system inventory dictionary.
    """
    logger.info(f"Starting Level 1 Service with {len(document_texts)} documents.")
    all_extracted_systems = []
    
    for idx, text in enumerate(document_texts):
        if not text.strip():
            continue
        
        doc_name = source_names[idx] if (source_names and idx < len(source_names)) else f"Doc {idx + 1}"
        logger.info(f"Running discovery agent on document {idx + 1}/{len(document_texts)}: {doc_name}...")
        
        try:
            document_inventory = run_discovery_agent(text)
            for system in document_inventory.systems:
                # Annotate source references
                if not system.source_reference.strip():
                    system.source_reference = f"Document: {doc_name}"
                else:
                    system.source_reference = f"[{doc_name}] {system.source_reference}"
                all_extracted_systems.append(system)
        except Exception as e:
            logger.error(f"Error executing discovery on document '{doc_name}': {e}", exc_info=True)
            raise e
            
        # Pause to respect API rate limits if there are more documents
        if idx < len(document_texts) - 1:
            logger.info("Pausing for 15 seconds to respect API rate limits...")
            time.sleep(15)
            
    logger.info(f"Service aggregation complete. Discovered {len(all_extracted_systems)} systems total.")
    master_inventory = SystemInventory(systems=all_extracted_systems)
    
    logger.info("Running robust deduplication on service systems inventory...")
    deduplicated_inventory = deduplicate_inventory(master_inventory)
    
    logger.info("Running audit validation on service systems inventory...")
    validated_inventory = validate_inventory(deduplicated_inventory)
    
    return validated_inventory.model_dump()

# Import service functions from higher levels
from main_l2 import run_level_2_service
from main_l3 import run_level_3_service

app = typer.Typer(rich_markup_mode="rich", help="Aivar Discovery Agent - Architecture Intelligence Pipeline")

def check_and_bootstrap_env(input_dir: str):
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
    bootstrap_test_directory(input_dir)

def run_level_1_pipeline(input_dir: str) -> dict:
    check_and_bootstrap_env(input_dir)
    
    # Ingest files from the folder
    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    logger.info(f"Ingesting documents from '{input_dir}'. Found {len(files)} file(s).")

    document_texts = []
    source_names = []
    for file_name in files:
        file_path = os.path.join(input_dir, file_name)
        logger.info(f"Parsing document: {file_path}")
        
        try:
            elements = partition(filename=file_path)
            file_text = "\n".join([str(el) for el in elements])
            if file_text.strip():
                document_texts.append(file_text)
                source_names.append(file_name)
            else:
                logger.warning(f"File '{file_name}' contains no readable text. Skipping.")
        except Exception as e:
            logger.error(f"Error parsing file '{file_name}': {e}", exc_info=True)
            continue

    # Run via service function
    inventory_dict = run_level_1_service(document_texts, source_names)
    
    # Serialize to JSON and output
    output_filename = "inventory_output.json"
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    
    logger.info(f"Writing validated master system inventory to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inventory_dict, f, indent=2, ensure_ascii=False)
        
    logger.info("Discovery ingestion execution completed successfully!")
    return inventory_dict

def run_level_2_pipeline() -> dict:
    inventory_file = "inventory_output.json"
    inventory_path = os.path.join(os.path.dirname(__file__), inventory_file)
    
    if not os.path.exists(inventory_path):
        logger.error(
            f"Required Level 1 output file not found: {inventory_path}. "
            "Please run Level 1 first."
        )
        raise typer.Exit(code=1)

    logger.info(f"Loading system inventory from {inventory_path}...")
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory_json = json.load(f)
        
    logger.info(f"Loaded {len(inventory_json.get('systems', []))} systems from inventory.")

    # Run Level 2 gap analysis service
    report_dict = run_level_2_service(inventory_json)
    
    # Serialize to JSON and output
    output_file = "gap_analysis_output.json"
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    
    logger.info(f"Writing Gap Analysis Report to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
    logger.info("Level 2 Gap Analysis completed successfully!")
    return report_dict

def run_level_3_pipeline() -> List[dict]:
    gaps_file = "gap_analysis_output.json"
    gaps_path = os.path.join(os.path.dirname(__file__), gaps_file)
    
    if not os.path.exists(gaps_path):
        logger.error(
            f"Required Level 2 output file not found: {gaps_path}. "
            "Please run Level 2 first."
        )
        raise typer.Exit(code=1)

    logger.info(f"Loading gap analysis report from {gaps_path}...")
    with open(gaps_path, "r", encoding="utf-8") as f:
        gaps_report = json.load(f)

    # Run Level 3 service function
    connector_results = run_level_3_service(gaps_report)
    
    if not connector_results:
        logger.info("No missing integrations found to process. Exiting.")
        return []

    # Prepare output directory
    base_output_dir = os.path.join(os.path.dirname(__file__), "generated_connectors")
    os.makedirs(base_output_dir, exist_ok=True)
    logger.info(f"Connector output target folder: {base_output_dir}")

    for idx, item in enumerate(connector_results, 1):
        src = item.get("source_system")
        dst = item.get("destination_system")
        
        logger.info(f"--- Writing generated files for Connector [{idx}/{len(connector_results)}]: {src} -> {dst} ---")
        
        # Create a dedicated directory for this connector gap
        connector_folder_name = f"{src.lower()}_to_{dst.lower()}"
        connector_dir = os.path.join(base_output_dir, connector_folder_name)
        os.makedirs(connector_dir, exist_ok=True)
        
        # Write Python connector file
        py_filepath = os.path.join(connector_dir, item["connector_filename"])
        logger.info(f"Writing Python connector code to {py_filepath}...")
        with open(py_filepath, "w", encoding="utf-8") as f:
            f.write(item["connector_code"])
            
        # Write Agent YAML file
        yaml_filepath = os.path.join(connector_dir, item["yaml_filename"])
        logger.info(f"Writing Agent YAML configuration to {yaml_filepath}...")
        with open(yaml_filepath, "w", encoding="utf-8") as f:
            f.write(item["yaml_content"])
            
        # Write README instruction file
        readme_filepath = os.path.join(connector_dir, "README.md")
        logger.info(f"Writing README installation guide to {readme_filepath}...")
        with open(readme_filepath, "w", encoding="utf-8") as f:
            f.write(item["readme_content"])

        # Write requirements.txt manifest
        req_filepath = os.path.join(connector_dir, "requirements.txt")
        logger.info(f"Writing dependency manifest to {req_filepath}...")
        with open(req_filepath, "w", encoding="utf-8") as f:
            f.write(item["requirements_content"])

        # Write automated unit test file
        test_filepath = os.path.join(connector_dir, item["tests_filename"])
        logger.info(f"Writing automated unit tests to {test_filepath}...")
        with open(test_filepath, "w", encoding="utf-8") as f:
            f.write(item["tests_code"])

        logger.info(f"Successfully generated files in directory: {connector_dir}")

    logger.info("Level 3 Integration Code Generation completed successfully!")
    return connector_results

@app.command()
def level1(
    input_dir: str = typer.Option(
        "./test_documents",
        "--input-dir",
        help="Local directory path containing corporate documents to ingest."
    )
):
    """
    [bold green]Level 1: System Extraction & Ingestion[/bold green]

    Runs the Level 1 extraction engine. It:
    * Parses all documents in the specified [italic]--input-dir[/italic] folder.
    * Detects enterprise systems using LLM-based discovery.
    * Deduplicates and aggregates system properties.
    * Saves the output systems inventory catalog to [yellow]inventory_output.json[/yellow].
    """
    try:
        inventory_dict = run_level_1_pipeline(input_dir)
        
        # Display Success Panel
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        output_path = os.path.abspath("inventory_output.json")
        panel_content = (
            f"[bold green]Level 1 Discovery Completed Successfully![/bold green]\n\n"
            f"[bold]Output File Path:[/bold] {output_path}\n"
            f"[bold]Systems Detected:[/bold] {len(inventory_dict.get('systems', []))}\n"
        )
        console.print(Panel(panel_content, title="[bold cyan]Level 1 Ingestion Status[/bold cyan]", border_style="cyan"))
    except Exception as e:
        logger.exception(f"Level 1 pipeline failed: {e}")
        raise typer.Exit(code=1)

@app.command()
def level2():
    """
    [bold blue]Level 2: Enterprise Integration Gap Analysis[/bold blue]

    Runs the Level 2 gap analyzer. It:
    * Loads the system catalog from [yellow]inventory_output.json[/yellow].
    * Evaluates mapping and integration gaps against predefined use cases.
    * Runs risk, confidence, and complexity evaluations.
    * Saves the gap analysis report to [yellow]gap_analysis_output.json[/yellow].
    """
    try:
        report_dict = run_level_2_pipeline()
        
        # Display Success Panel
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        output_path = os.path.abspath("gap_analysis_output.json")
        panel_content = (
            f"[bold green]Level 2 Gap Analysis Completed Successfully![/bold green]\n\n"
            f"[bold]Output File Path:[/bold] {output_path}\n"
            f"[bold]Total Gaps Tracked:[/bold] {len(report_dict.get('prioritized_gaps', []))}\n"
        )
        console.print(Panel(panel_content, title="[bold blue]Level 2 Analysis Status[/bold blue]", border_style="blue"))
    except Exception as e:
        logger.exception(f"Level 2 pipeline failed: {e}")
        raise typer.Exit(code=1)

@app.command()
def level3():
    """
    [bold magenta]Level 3: Autonomous Connector Synthesis[/bold magenta]

    Runs the Level 3 synthesis engine. It:
    * Loads the gap report from [yellow]gap_analysis_output.json[/yellow].
    * Generates code files, tests, YAML configs, and docs for each missing link.
    * Saves all generated connector packages inside the [yellow]generated_connectors/[/yellow] directory.
    """
    try:
        connector_results = run_level_3_pipeline()
        
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        
        if not connector_results:
            console.print(Panel("[bold green]Level 3 completed: No missing integrations to generate.[/bold green]", title="[bold magenta]Level 3 Synthesis Status[/bold magenta]", border_style="magenta"))
            return
            
        base_output_dir = os.path.abspath("generated_connectors")
        paths_list = []
        for item in connector_results:
            src = item.get("source_system", "").lower()
            dst = item.get("destination_system", "").lower()
            paths_list.append(f"  - [yellow]{os.path.join(base_output_dir, f'{src}_to_{dst}')}[/yellow]")
        paths_str = "\n".join(paths_list)
        
        panel_content = (
            f"[bold green]Level 3 Integration Code Generation Completed Successfully![/bold green]\n\n"
            f"[bold]Output Target Folder:[/bold] {base_output_dir}\n"
            f"[bold]Generated Connector Packages:[/bold]\n{paths_str}\n"
        )
        console.print(Panel(panel_content, title="[bold magenta]Level 3 Synthesis Status[/bold magenta]", border_style="magenta"))
    except Exception as e:
        logger.exception(f"Level 3 pipeline failed: {e}")
        raise typer.Exit(code=1)

@app.command(name="run-all")
def run_all(
    input_dir: str = typer.Option(
        "./test_documents",
        "--input-dir",
        help="Local directory path containing corporate documents to ingest."
    )
):
    """
    [bold yellow]Complete Enterprise Pipeline Execution[/bold yellow]

    Executes all three levels sequentially:
    1. [bold green]Level 1[/bold green]: Ingests and extracts systems from --input-dir folder.
    2. [bold blue]Level 2[/bold blue]: Compares catalog against automation use cases and performs gap/risk analysis.
    3. [bold magenta]Level 3[/bold magenta]: Generates complete Python/YAML connector scaffolding packages.
    """
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    console.print(Panel("[bold yellow]*** Initiating Full Discovery & Integration Pipeline ***[/bold yellow]", border_style="yellow"))
    
    try:
        # Run Level 1
        console.print("\n[bold cyan]>>> Running Level 1: System Extraction[/bold cyan]")
        inventory_dict = run_level_1_pipeline(input_dir)
        
        # Run Level 2
        console.print("\n[bold blue]>>> Running Level 2: Gap Analysis[/bold blue]")
        report_dict = run_level_2_pipeline()
        
        # Run Level 3
        console.print("\n[bold magenta]>>> Running Level 3: Code Synthesis[/bold magenta]")
        connector_results = run_level_3_pipeline()
        
        # Combined Success Message
        output_dir = os.path.abspath("generated_connectors")
        paths_list = []
        for item in connector_results:
            src = item.get("source_system", "").lower()
            dst = item.get("destination_system", "").lower()
            paths_list.append(f"  - [yellow]{os.path.join(output_dir, f'{src}_to_{dst}')}[/yellow]")
        paths_str = "\n".join(paths_list) if paths_list else "  - [italic]None[/italic]"
        
        panel_content = (
            f"[bold green]Full Pipeline Run Completed Successfully![/bold green]\n\n"
            f"[bold]Level 1 Output:[/bold] {os.path.abspath('inventory_output.json')} ({len(inventory_dict.get('systems', []))} systems detected)\n"
            f"[bold]Level 2 Output:[/bold] {os.path.abspath('gap_analysis_output.json')} ({len(report_dict.get('prioritized_gaps', []))} gaps tracked)\n"
            f"[bold]Level 3 Output Directory:[/bold] {output_dir}\n"
            f"[bold]Generated Connector Packages:[/bold]\n{paths_str}\n"
        )
        console.print(Panel(panel_content, title="[bold yellow]Pipeline Execution Status[/bold yellow]", border_style="yellow"))
        
    except Exception as e:
        logger.exception(f"Pipeline execution encountered an error: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()

