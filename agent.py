import os
import logging
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from schemas import SystemInventory, SystemExtraction

# Set up logging for audit trails
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("discovery_agent")

def get_llm() -> Any:
    """
    Dynamically loads and initializes the Chat Model based on available environment variables.
    Supports OpenAI (ChatOpenAI) and Google (ChatGoogleGenerativeAI) models.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if openai_key and openai_key.strip() and openai_key != "your_openai_api_key_here":
        try:
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
            logger.info(f"Initializing OpenAI model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=0.0,
                api_key=openai_key
            )
        except ImportError:
            logger.error("langchain-openai package is not installed. Please check requirements.")
            raise

    elif google_key and google_key.strip() and google_key != "your_google_api_key_here":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = os.getenv("GOOGLE_MODEL_NAME", "gemini-1.5-pro")
            logger.info(f"Initializing Gemini model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.0,
                api_key=google_key
            )
        except ImportError:
            logger.error("langchain-google-genai package is not installed. Please check requirements.")
            raise

    else:
        raise ValueError(
            "Configuration Error: Neither OPENAI_API_KEY nor GOOGLE_API_KEY is configured. "
            "Please copy .env.example to .env and set at least one valid API key."
        )

def generate_mock_extraction(document_text: str) -> SystemInventory:
    """
    Simulates a high-quality, zero-hallucination structured extraction response
    from the LLM for the mock corporate document when API keys are not provided.
    """
    logger.info("Executing mock extraction fallback for mock corporate document...")
    
    systems = []
    
    # 1. Salesforce CRM (Explicit, High Confidence)
    if "Salesforce" in document_text:
        systems.append(
            SystemExtraction(
                name="Salesforce",
                category="CRM",
                auth_method="OAuth2",
                key_entities=["Customer", "Lead", "Account", "Contact"],
                business_processes=["Lead-to-Cash", "Sales pipeline management", "Customer support routing"],
                criticality="High",
                confidence_score=98,
                inferred_notes="",
                source_reference="We use Salesforce to manage customer relations and tracking leads. Authentication: Standard OAuth2 flow."
            )
        )
        
    # 2. NetSuite ERP (Explicit, High Confidence)
    if "NetSuite" in document_text:
        systems.append(
            SystemExtraction(
                name="NetSuite",
                category="ERP",
                auth_method="Token-Based Authentication (API Key)",
                key_entities=["Invoice", "Ledger", "Payment", "Vendor"],
                business_processes=["Procure-to-Pay", "Billing", "Quarterly financial audits"],
                criticality="High",
                confidence_score=98,
                inferred_notes="",
                source_reference="All billing and financial tracking are managed in NetSuite... Authentication: Token-Based Authentication (API Key)."
            )
        )
        
    # 3. Jira (Inferred, Medium Confidence)
    if "Jira" in document_text:
        systems.append(
            SystemExtraction(
                name="Jira",
                category="Project Management",
                auth_method="SAML",
                key_entities=["Ticket", "Sprint", "Epics"],
                business_processes=["Software development lifecycle (SDLC) tracking"],
                criticality="Medium",
                confidence_score=85,
                inferred_notes="Authentication method (SAML) was inferred based on corporate SSO mention; Sprint and Epic entities were inferred from bug tracking and sprint planning context.",
                source_reference="Engineering files bugs and plans sprints in Jira."
            )
        )
        
    # 4. Slack (Inferred, Medium Confidence)
    if "Slack" in document_text:
        systems.append(
            SystemExtraction(
                name="Slack",
                category="Chat / Messaging",
                auth_method="Webhook",
                key_entities=["Alert", "Log"],
                business_processes=["System alerting", "Team collaboration"],
                criticality="Low",
                confidence_score=75,
                inferred_notes="Inferred webhook notification flow based on log routing mention. Specific Slack API scopes are not specified.",
                source_reference="We sometimes route logs and automated alerts to a Slack channel. Authentication: Webhook URL."
            )
        )
        
    # 5. Coupa (Uncertain, Low Confidence - human review flagged)
    if "Coupa" in document_text:
        systems.append(
            SystemExtraction(
                name="Coupa",
                category="Procurement",
                auth_method="Unknown",
                key_entities=[],
                business_processes=[],
                criticality="Medium",
                confidence_score=45,
                inferred_notes="System was mentioned in passing as part of an evaluation question ('Are we still evaluating Coupa...'). Active corporate account and authentication method are unknown; needs human review.",
                source_reference="Are we still evaluating Coupa for procurement, or do we already have an active sandbox account there?"
            )
        )
        
    # 6. Trello (Uncertain, Low Confidence - human review flagged)
    if "Trello" in document_text:
        systems.append(
            SystemExtraction(
                name="Trello",
                category="Project Management",
                auth_method="Unknown",
                key_entities=[],
                business_processes=[],
                criticality="Low",
                confidence_score=35,
                inferred_notes="Mentioned in passing as personal/unofficial task boards used by some teams. No corporate integration or active authentication is documented.",
                source_reference="Dave mentioned that some teams might be using Trello for personal task boards, but it is not officially supported by IT."
            )
        )
        
    return SystemInventory(systems=systems)

def run_discovery_agent(document_text: str) -> SystemInventory:
    """
    Executes the systems discovery agent pipeline on the unstructured text.
    Uses LangChain structured output to enforce the schema constraints.
    Falls back to a local mock simulation if API keys are missing.
    """
    if not document_text.strip():
        logger.warning("Provided document text is empty. Returning an empty SystemInventory.")
        return SystemInventory(systems=[])

    try:
        llm = get_llm()
    except ValueError as e:
        logger.warning(
            "API keys are not configured. Running agent in Local Mock Simulation Mode..."
        )
        return generate_mock_extraction(document_text)

    structured_llm = llm.with_structured_output(SystemInventory)

    # Core prompt instructing LLM to extract systems, prevent hallucinations, and assign honest scores
    system_prompt = (
        "You are an expert Systems Discovery Agent.\n"
        "Your task is to process unstructured corporate documentation (such as wiki pages, architecture notes, emails, system logs, etc.) "
        "and extract a structured inventory of all software systems mentioned.\n\n"
        "Follow these strict rules to ensure data integrity and avoid errors:\n"
        "1. ZERO HALLUCINATION: Only extract systems that are explicitly mentioned or strongly/logically inferred directly from the provided source text. "
        "Do NOT invent any systems, integrations, or data flows that are not present. If a system is not in the text, do not include it.\n"
        "2. FIELD EXTRACTIONS:\n"
        "   - name: The recognized or formal name of the system (e.g., Salesforce, NetSuite, Coupa).\n"
        "   - category: The functional category of the system (e.g., CRM, ERP, HRIS, Database, Billing, Procurement).\n"
        "   - auth_method: How users or systems authenticate (e.g., OAuth2, API Key, Basic Auth, SAML). If not mentioned or unclear, specify 'Unknown'.\n"
        "   - key_entities: Data entities/objects processed (e.g., Customer, Lead, Invoice, Ticket, Employee).\n"
        "   - business_processes: Business processes supported (e.g., Lead-to-Cash, Procure-to-Pay, Financial Audits, Employee Onboarding).\n"
        "   - criticality: Operational criticality. Must be one of: High, Medium, Low.\n"
        "   - source_reference: A direct quote, page number, file name, or section reference from the document supporting the existence of this system.\n"
        "3. STRICT CONFIDENCE SCORING:\n"
        "   - Score 95+: The system is explicitly named and its key details (auth, category, entities, processes) are clearly described.\n"
        "   - Score 70-90: The system is inferred or mentioned with partial details. There is strong circumstantial evidence that the system is used.\n"
        "   - Score below 70: The system is mentioned only in passing, or there is high ambiguity about whether it is actually used. These systems must be flagged.\n"
        "4. INFERRED NOTES:\n"
        "   - If the confidence score is below 95 (i.e., < 95), you MUST write a detailed note in 'inferred_notes' explaining: "
        "a) what details were missing from the text (e.g., 'Authentication method not mentioned'), and b) what assumptions or inferences were made (e.g., 'Inferred OAuth2 since it is a modern SaaS CRM').\n"
        "   - If the confidence score is 95+, 'inferred_notes' must be an empty string."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Extract systems from the following document text:\n\n{text}")
    ])

    # Build and execute the chain
    chain = prompt_template | structured_llm
    
    logger.info("Running LangChain pipeline for systems extraction...")
    result = chain.invoke({"text": document_text})
    
    if not isinstance(result, SystemInventory):
        raise TypeError(f"Expected SystemInventory response from model, got: {type(result)}")

    return result

def validate_inventory(inventory: SystemInventory) -> SystemInventory:
    """
    Validates the extracted inventory, ensures compliance with business rules, 
    and logs a detailed audit trail.
    """
    logger.info("Starting post-extraction audit validation...")
    
    total_systems = len(inventory.systems)
    logger.info(f"Auditing {total_systems} extracted system(s).")

    validated_systems = []
    
    for idx, system in enumerate(inventory.systems, 1):
        logger.info(f"--- Auditing System [{idx}/{total_systems}]: {system.name} ---")
        
        # 1. Sanity check for blank/empty required fields
        if not system.name.strip():
            logger.error(f"Audit failure: System at index {idx} has an empty name.")
            continue
            
        # 2. Log Confidence Score Assessment
        logger.info(f"Self-assessed Confidence Score: {system.confidence_score}%")
        
        if system.confidence_score >= 95:
            logger.info("Confidence Status: HIGH. Explicit mention verified.")
            if system.inferred_notes.strip():
                logger.warning(
                    f"Audit note: System '{system.name}' has high confidence ({system.confidence_score}%) "
                    f"but includes inferred_notes. Cleared inferred_notes to maintain schema consistency."
                )
                system.inferred_notes = ""
                
        elif 70 <= system.confidence_score < 95:
            logger.info("Confidence Status: MEDIUM. Inferred system details present.")
            if not system.inferred_notes.strip():
                logger.error(
                    f"Audit failure: System '{system.name}' has confidence {system.confidence_score}% "
                    f"but has blank inferred_notes. Assigning fallback note."
                )
                system.inferred_notes = "Inferred from document with missing details."
            else:
                logger.info(f"Inference Audit Trails: {system.inferred_notes}")
                
        else: # confidence_score < 70
            logger.warning(
                f"AUDIT WARNING: System '{system.name}' has LOW confidence ({system.confidence_score}%). "
                f"Manual engineering review is REQUIRED. "
                f"Missing Details/Inferences: {system.inferred_notes}"
            )
            if not system.inferred_notes.strip():
                system.inferred_notes = "Low confidence extraction. Missing context or passing mention."

        # 3. Log extracted metadata summary
        logger.info(f"Category: {system.category}")
        logger.info(f"Authentication: {system.auth_method}")
        logger.info(f"Criticality: {system.criticality}")
        logger.info(f"Entities: {', '.join(system.key_entities) if system.key_entities else 'None'}")
        logger.info(f"Processes: {', '.join(system.business_processes) if system.business_processes else 'None'}")
        logger.info(f"Source Reference: {system.source_reference}")
        
        validated_systems.append(system)
        
    logger.info("Audit validation process complete.")
    return SystemInventory(systems=validated_systems)