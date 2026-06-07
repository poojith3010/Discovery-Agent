import os
import json
import logging
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from agent import get_llm
from schemas_l2 import GapAnalysisReport, UseCaseMapping, IntegrationGap, DataFlow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("discovery_agent_l2")

def generate_mock_gap_analysis(inventory_json: dict, use_cases: List[str]) -> GapAnalysisReport:
    """
    Deterministically simulates the Software Architect's integration gap analysis
    when API keys are not provided.
    """
    logger.info("Executing mock gap analysis fallback for Level 2 use cases...")
    
    # Extract existing systems from inventory
    existing_system_names = {sys["name"].lower(): sys["name"] for sys in inventory_json.get("systems", [])}
    
    # Initialize lists
    use_case_mappings = []
    prioritized_gaps = []
    
    # Define mapping rules for the mock use cases
    # 1. Salesforce Opportunity to NetSuite Invoice
    use_case_mappings.append(
        UseCaseMapping(
            use_case_name="Salesforce Opportunity to NetSuite Invoice Sync",
            involved_systems=["Salesforce", "NetSuite"],
            data_flows=[
                DataFlow(
                    source_system="Salesforce",
                    destination_system="NetSuite",
                    entity_type="Customer",
                    trigger_event="Opportunity Closed Won"
                ),
                DataFlow(
                    source_system="Salesforce",
                    destination_system="NetSuite",
                    entity_type="Invoice",
                    trigger_event="Opportunity Closed Won"
                )
            ],
            business_impact_score=9
        )
    )
    
    # 2. Jira bug creation to Slack messaging
    use_case_mappings.append(
        UseCaseMapping(
            use_case_name="High-Priority Jira Bug Alert to Slack",
            involved_systems=["Jira", "Slack"],
            data_flows=[
                DataFlow(
                    source_system="Jira",
                    destination_system="Slack",
                    entity_type="Alert Log",
                    trigger_event="High Priority Ticket Created"
                )
            ],
            business_impact_score=7
        )
    )
    
    # 3. NetSuite Payment status notifications to Slack
    use_case_mappings.append(
        UseCaseMapping(
            use_case_name="NetSuite Payment Alerts to Slack",
            involved_systems=["NetSuite", "Slack"],
            data_flows=[
                DataFlow(
                    source_system="NetSuite",
                    destination_system="Slack",
                    entity_type="Alert Log",
                    trigger_event="Payment Status Processed"
                )
            ],
            business_impact_score=8
        )
    )

    # 4. Coupa procurement request syncing to Salesforce
    use_case_mappings.append(
        UseCaseMapping(
            use_case_name="Coupa Procurement Sandbox Sync to Salesforce",
            involved_systems=["Coupa", "Salesforce"],
            data_flows=[
                DataFlow(
                    source_system="Coupa",
                    destination_system="Salesforce",
                    entity_type="Customer Profile",
                    trigger_event="Procurement Sandbox Request Raised"
                )
            ],
            business_impact_score=4
        )
    )

    # 5. Trello task board synchronization to Jira
    use_case_mappings.append(
        UseCaseMapping(
            use_case_name="Trello Personal Tasks Sync to Jira",
            involved_systems=["Trello", "Jira"],
            data_flows=[
                DataFlow(
                    source_system="Trello",
                    destination_system="Jira",
                    entity_type="Ticket Sync",
                    trigger_event="Personal Card Updated"
                )
            ],
            business_impact_score=2
        )
    )

    # Define Gaps based on use cases. Sort gaps by business_impact_score of the blocked use case
    prioritized_gaps.append(
        IntegrationGap(
            source_system="Salesforce",
            destination_system="NetSuite",
            status="Missing",
            estimated_effort="High",
            dependency_note="Integration must exist before Salesforce Opportunity to NetSuite Invoice Sync can be automated. Blocks critical invoicing workflow."
        )
    )
    prioritized_gaps.append(
        IntegrationGap(
            source_system="NetSuite",
            destination_system="Slack",
            status="Missing",
            estimated_effort="Medium",
            dependency_note="Required before NetSuite Payment Alerts to Slack can be automated. Key payment notification dependency."
        )
    )
    prioritized_gaps.append(
        IntegrationGap(
            source_system="Jira",
            destination_system="Slack",
            status="Missing",
            estimated_effort="Low",
            dependency_note="Required before High-Priority Jira Bug Alert to Slack can be automated. Low effort webhook connection."
        )
    )
    prioritized_gaps.append(
        IntegrationGap(
            source_system="Coupa",
            destination_system="Salesforce",
            status="Missing",
            estimated_effort="Complex",
            dependency_note="Required before Coupa Procurement Sandbox Sync to Salesforce can be automated. HIGH RISK: Coupa was flagged as Low Confidence (45%) in Level 1; sandbox and API schema are unverified."
        )
    )
    prioritized_gaps.append(
        IntegrationGap(
            source_system="Trello",
            destination_system="Jira",
            status="Missing",
            estimated_effort="Medium",
            dependency_note="Required before Trello Personal Tasks Sync to Jira can be automated. Low priority since Trello is not officially supported by IT."
        )
    )

    return GapAnalysisReport(
        use_case_mappings=use_case_mappings,
        prioritized_gaps=prioritized_gaps
    )

def run_gap_analysis(inventory_json: dict, use_cases: List[str]) -> GapAnalysisReport:
    """
    Executes the integration gap analysis using the LangChain pipeline.
    Falls back to deterministic mock simulation if API keys are missing.
    """
    try:
        llm = get_llm()
    except ValueError as e:
        logger.warning(
            "API keys are not configured. Running Level 2 agent in Local Mock Simulation Mode..."
        )
        return generate_mock_gap_analysis(inventory_json, use_cases)

    structured_llm = llm.with_structured_output(GapAnalysisReport)

    system_prompt = (
        "You are an expert Enterprise Software Architect.\n"
        "Your task is to analyze the provided System Inventory and a list of Automation Use Cases "
        "to map dependencies, trace data flows, identify missing integrations (gaps), "
        "estimate implementation effort, and produce a prioritized gap report.\n\n"
        "Follow these rules during analysis:\n"
        "1. USE CASE MAPPING & DATA FLOWS:\n"
        "   - Map each use case to the systems involved. Systems names must match those in the System Inventory.\n"
        "   - Trace the exact directional data flow: source_system -> destination_system.\n"
        "   - Extract the entity_type being transferred (e.g., Customer, Invoice, Ticket, Log).\n"
        "   - Identify the trigger_event starting the flow.\n"
        "   - Assign a business_impact_score (1-10) based on how critical and frequent this workflow is. Invoicing and finance flows are typically High (8-10); alerts are Medium (5-7); personal/unsupported tools are Low (1-4).\n"
        "2. GAP IDENTIFICATION & EFFORT ESTIMATION:\n"
        "   - Identify integrations that do not exist or are required to satisfy the use cases. Mark status as 'Missing' (or 'Available' if stated in the inventory to exist already).\n"
        "   - Estimate the effort to build the integration: Low, Medium, High, or Complex.\n"
        "   - Highlight dependency constraints. Format: 'Integration X must exist before use case Y can be automated.'\n"
        "   - If a required integration involves a system that was flagged in the inventory as Low Confidence (confidence_score < 70%), classify the integration effort as 'Complex' and include a dependency warning in the dependency_note.\n"
        "3. GAP PRIORITIZATION:\n"
        "   - Sort the prioritized_gaps list in descending order of priority, placing integrations blocking the highest impact use cases first."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", (
            "Analyze the following data:\n\n"
            "System Inventory:\n{inventory}\n\n"
            "Automation Use Cases:\n{use_cases}"
        ))
    ])

    chain = prompt_template | structured_llm

    logger.info("Executing LangChain structured gap analysis...")
    formatted_use_cases = "\n".join(f"- {uc}" for uc in use_cases)
    result = chain.invoke({
        "inventory": json.dumps(inventory_json, indent=2),
        "use_cases": formatted_use_cases
    })

    if not isinstance(result, GapAnalysisReport):
        raise TypeError(f"Expected GapAnalysisReport response from model, got: {type(result)}")

    return result
