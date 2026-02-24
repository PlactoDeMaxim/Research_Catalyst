"""
Rule-Based Plan Generation Engine

Generates research phases and milestones from topic, domain, and deadline.
Designed with a pluggable interface so it can be swapped with an LLM engine later.
"""

from datetime import datetime, timedelta
import uuid

from modules.planner.models.planner_model import Phase, Milestone


# ── Phase templates by domain ──
# Each domain maps to a list of phases, each with milestone templates.
# "general" is the fallback for any unrecognized domain.

PHASE_TEMPLATES: dict[str, list[dict]] = {
    "general": [
        {
            "title": "Foundation",
            "description": "Define scope, review existing work, and establish research direction.",
            "milestones": [
                {"title": "Define Research Question", "description": "Articulate the core research question and scope."},
                {"title": "Literature Review", "description": "Identify and review 15-20 relevant papers in the domain."},
                {"title": "Gap Analysis", "description": "Document the research gap and position your contribution."},
            ],
        },
        {
            "title": "Development",
            "description": "Design and build the proposed methodology or approach.",
            "milestones": [
                {"title": "Methodology Design", "description": "Design the proposed approach, framework, or model architecture."},
                {"title": "Implementation", "description": "Implement the core methodology, tools, or prototype."},
                {"title": "Preliminary Testing", "description": "Run initial tests to validate the approach."},
            ],
        },
        {
            "title": "Experimentation",
            "description": "Execute experiments and analyze results.",
            "milestones": [
                {"title": "Experiment Setup", "description": "Prepare datasets, environment, and evaluation metrics."},
                {"title": "Run Experiments", "description": "Execute all planned experiments and collect results."},
                {"title": "Results Analysis", "description": "Analyze results, create tables, charts, and comparisons."},
            ],
        },
        {
            "title": "Writing",
            "description": "Draft the research paper or thesis.",
            "milestones": [
                {"title": "Draft Introduction & Related Work", "description": "Write the introduction and related work sections."},
                {"title": "Draft Methodology & Results", "description": "Write methodology, experiments, and results sections."},
                {"title": "Draft Conclusion & Abstract", "description": "Write conclusion, abstract, and finalize all sections."},
            ],
        },
        {
            "title": "Publication",
            "description": "Review, revise, and submit for publication.",
            "milestones": [
                {"title": "Internal Review", "description": "Submit for peer/advisor review and collect feedback."},
                {"title": "Revision & Polish", "description": "Incorporate feedback, fix issues, polish the manuscript."},
                {"title": "Final Submission", "description": "Format for the target venue and submit."},
            ],
        },
    ],
    "machine_learning": [
        {
            "title": "Foundation",
            "description": "Survey the field and define the ML research direction.",
            "milestones": [
                {"title": "Research Question & Hypothesis", "description": "Define the ML problem, hypothesis, and scope."},
                {"title": "Literature Survey", "description": "Review SOTA approaches, benchmarks, and key papers."},
                {"title": "Baseline Selection", "description": "Select baseline models and evaluation metrics."},
            ],
        },
        {
            "title": "Data & Infrastructure",
            "description": "Prepare datasets and training infrastructure.",
            "milestones": [
                {"title": "Dataset Collection & Preprocessing", "description": "Collect, clean, and preprocess datasets."},
                {"title": "Training Pipeline Setup", "description": "Set up training scripts, GPU environment, logging."},
            ],
        },
        {
            "title": "Model Development",
            "description": "Design, implement, and iterate on the model.",
            "milestones": [
                {"title": "Architecture Design", "description": "Design the model architecture and training strategy."},
                {"title": "Model Implementation", "description": "Implement the model in PyTorch/TensorFlow."},
                {"title": "Hyperparameter Tuning", "description": "Tune hyperparameters and run ablation studies."},
            ],
        },
        {
            "title": "Experimentation",
            "description": "Run comprehensive experiments and comparisons.",
            "milestones": [
                {"title": "Benchmark Experiments", "description": "Run experiments on standard benchmarks."},
                {"title": "Ablation Studies", "description": "Analyze contribution of each component."},
                {"title": "Comparison with SOTA", "description": "Compare results against SOTA baselines."},
            ],
        },
        {
            "title": "Writing & Submission",
            "description": "Write the paper and submit.",
            "milestones": [
                {"title": "Paper Draft", "description": "Write all sections: intro, method, experiments, conclusion."},
                {"title": "Figures & Tables", "description": "Create publication-quality visualizations."},
                {"title": "Review & Submit", "description": "Internal review, revision, and submission."},
            ],
        },
    ],
    "biology": [
        {
            "title": "Foundation",
            "description": "Define research hypothesis and review literature.",
            "milestones": [
                {"title": "Hypothesis Formulation", "description": "Articulate the biological hypothesis to test."},
                {"title": "Literature Review", "description": "Review existing studies and identify the research gap."},
                {"title": "Ethics & Approvals", "description": "Obtain necessary ethical approvals and permissions."},
            ],
        },
        {
            "title": "Experimental Design",
            "description": "Design experiments and prepare materials.",
            "milestones": [
                {"title": "Protocol Design", "description": "Design experimental protocols and controls."},
                {"title": "Material Preparation", "description": "Prepare reagents, samples, and equipment."},
            ],
        },
        {
            "title": "Data Collection",
            "description": "Execute experiments and collect data.",
            "milestones": [
                {"title": "Run Experiments", "description": "Execute planned experiments following protocols."},
                {"title": "Data Recording", "description": "Record all observations and measurements systematically."},
            ],
        },
        {
            "title": "Analysis & Writing",
            "description": "Analyze data and write the manuscript.",
            "milestones": [
                {"title": "Statistical Analysis", "description": "Perform statistical analysis on collected data."},
                {"title": "Paper Draft", "description": "Draft the manuscript with all sections."},
                {"title": "Review & Submit", "description": "Peer review, revise, and submit to journal."},
            ],
        },
    ],
    "data_science": [
        {
            "title": "Foundation",
            "description": "Define the data science problem and review prior work.",
            "milestones": [
                {"title": "Problem Definition", "description": "Articulate the data science question and success criteria."},
                {"title": "Literature & Prior Work Review", "description": "Survey prior approaches and relevant tools/techniques."},
                {"title": "Data Source Identification", "description": "Identify and assess candidate data sources."},
            ],
        },
        {
            "title": "Data Engineering",
            "description": "Acquire, clean, and prepare the data.",
            "milestones": [
                {"title": "Data Acquisition & Ingestion", "description": "Collect raw data from sources and build ingestion pipelines."},
                {"title": "Data Cleaning & Transformation", "description": "Handle missing values, outliers, and feature engineering."},
                {"title": "Exploratory Data Analysis", "description": "Visualize distributions, correlations, and patterns."},
            ],
        },
        {
            "title": "Modeling",
            "description": "Build and evaluate predictive models.",
            "milestones": [
                {"title": "Baseline Model", "description": "Train a simple baseline model for comparison."},
                {"title": "Advanced Modeling", "description": "Train and tune advanced models (ensemble, neural, etc.)."},
                {"title": "Model Evaluation", "description": "Evaluate using appropriate metrics, cross-validation, and error analysis."},
            ],
        },
        {
            "title": "Writing & Presentation",
            "description": "Document findings and present results.",
            "milestones": [
                {"title": "Results Documentation", "description": "Write up findings with visualizations and tables."},
                {"title": "Paper Draft & Review", "description": "Draft the full paper and submit for review."},
            ],
        },
    ],
    "cybersecurity": [
        {
            "title": "Foundation",
            "description": "Define the security research problem and survey the landscape.",
            "milestones": [
                {"title": "Threat Model Definition", "description": "Define the threat model, attack surface, and research scope."},
                {"title": "Literature Survey", "description": "Review existing vulnerabilities, defenses, and related research."},
            ],
        },
        {
            "title": "Development",
            "description": "Build tools, exploits, or defenses.",
            "milestones": [
                {"title": "Environment Setup", "description": "Set up testbeds, VMs, and sandboxed environments."},
                {"title": "Tool / Defense Implementation", "description": "Implement the proposed tool, attack, or defense mechanism."},
            ],
        },
        {
            "title": "Evaluation",
            "description": "Test effectiveness and measure results.",
            "milestones": [
                {"title": "Security Testing", "description": "Execute tests against real-world or simulated scenarios."},
                {"title": "Performance & Impact Analysis", "description": "Measure detection rates, false positives, overhead, etc."},
                {"title": "Comparison with Existing Work", "description": "Compare against baseline tools and state-of-the-art."},
            ],
        },
        {
            "title": "Writing & Disclosure",
            "description": "Document findings and handle responsible disclosure.",
            "milestones": [
                {"title": "Paper Draft", "description": "Write the paper covering threat model, approach, and results."},
                {"title": "Review & Submit", "description": "Internal review, responsible disclosure, and submission."},
            ],
        },
    ],
    "software_engineering": [
        {
            "title": "Foundation",
            "description": "Define the SE research question and review prior studies.",
            "milestones": [
                {"title": "Research Question Formulation", "description": "Define the SE problem and formulate research questions."},
                {"title": "Systematic Literature Review", "description": "Conduct a systematic review of related SE research."},
            ],
        },
        {
            "title": "Study Design",
            "description": "Design the empirical study or tool.",
            "milestones": [
                {"title": "Methodology Design", "description": "Design the study methodology (survey, case study, experiment, tool)."},
                {"title": "Tool / Prototype Development", "description": "Build the prototype or instrument for the study."},
                {"title": "Pilot Study", "description": "Run a small-scale pilot to validate the approach."},
            ],
        },
        {
            "title": "Data Collection & Analysis",
            "description": "Gather data and analyze results.",
            "milestones": [
                {"title": "Data Collection", "description": "Collect data from repositories, surveys, or experiments."},
                {"title": "Statistical Analysis", "description": "Perform quantitative and qualitative analysis."},
            ],
        },
        {
            "title": "Writing & Publication",
            "description": "Write and submit the paper.",
            "milestones": [
                {"title": "Paper Draft", "description": "Write all sections of the research paper."},
                {"title": "Review & Submit", "description": "Peer review, revise, and submit to venue."},
            ],
        },
    ],
}

# ── Domain aliases: map related domains to their best template ──
_DOMAIN_ALIASES: dict[str, str] = {
    "deep_learning": "machine_learning",
    "nlp": "machine_learning",
    "computer_vision": "machine_learning",
    "robotics": "machine_learning",
    "biomedical_engineering": "biology",
    "physics": "general",
    "chemistry": "general",
    "mathematics": "general",
    "electrical_engineering": "general",
    "mechanical_engineering": "general",
}


def _distribute_dates(
    start: datetime,
    end: datetime,
    total_milestones: int,
) -> list[str]:
    """Distribute due dates evenly from start to end."""
    if total_milestones <= 0:
        return []
    if total_milestones == 1:
        return [end.strftime("%Y-%m-%d")]

    delta = (end - start) / total_milestones
    return [
        (start + delta * (i + 1)).strftime("%Y-%m-%d")
        for i in range(total_milestones)
    ]


def generate_plan(
    topic: str,
    domain: str,
    deadline: str,
) -> tuple[list[Phase], list[Milestone]]:
    """
    Generate a research plan (phases + milestones) using rule-based templates.

    This function implements the "engine interface":
        generate_plan(topic, domain, deadline) → (phases, milestones)

    To swap to LLM: replace this function's body with an API call.
    """
    # Pick template — resolve aliases first
    resolved = _DOMAIN_ALIASES.get(domain, domain)
    templates = PHASE_TEMPLATES.get(resolved, PHASE_TEMPLATES["general"])

    # Compute dates
    start_date = datetime.now()
    try:
        end_date = datetime.fromisoformat(deadline)
    except (ValueError, TypeError):
        end_date = start_date + timedelta(days=180)  # default: 6 months

    # Count total milestones
    total = sum(len(p["milestones"]) for p in templates)
    dates = _distribute_dates(start_date, end_date, total)

    phases: list[Phase] = []
    all_milestones: list[Milestone] = []
    date_idx = 0

    for p_order, phase_tmpl in enumerate(templates):
        phase = Phase(
            title=phase_tmpl["title"],
            description=phase_tmpl["description"],
            order=p_order,
            milestones=[],
        )

        for m_order, m_tmpl in enumerate(phase_tmpl["milestones"]):
            # Contextualize the milestone titles with the topic
            title = m_tmpl["title"]
            desc = m_tmpl["description"]
            if topic:
                desc = f"{desc} Topic: {topic}."

            milestone = Milestone(
                id=str(uuid.uuid4()),
                title=title,
                description=desc,
                due_date=dates[date_idx] if date_idx < len(dates) else "",
                completed=False,
                phase=phase_tmpl["title"],
                order=date_idx,
            )
            phase.milestones.append(milestone)
            all_milestones.append(milestone)
            date_idx += 1

        phases.append(phase)

    return phases, all_milestones
