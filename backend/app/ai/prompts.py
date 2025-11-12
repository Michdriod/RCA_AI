"""Prompt templates for 5 Whys AI interactions.
Provides helper builders to assemble prompts for question generation and final root cause analysis.
The output style encourages concise, clear, non-repetitive questioning.
"""
from __future__ import annotations

from textwrap import dedent
from typing import Sequence, Optional
from pydantic import BaseModel

class QAHistoryItem(BaseModel):
    index: int
    question: str
    answer: str

    def to_line(self) -> str:
        return f"Step {self.index}: Q: {self.question}\nA: {self.answer}".strip()

def _format_history(history: Sequence[QAHistoryItem]) -> str:
    if not history:
        return "(No previous steps)"
    return "\n\n".join(item.to_line() for item in history)

SYSTEM_STYLE_GUIDANCE = dedent(
    """
    You are an expert facilitator applying the 5 Whys root cause analysis technique.
    
    Core RCA Principles:
    - The 5 Whys method aims to discover the UNDERLYING SYSTEMIC CAUSE, not just surface symptoms.
    - Each question should move DOWN one level in the causal chain (from symptom → immediate cause → underlying mechanism → root cause).
    - Focus on "why THIS happened" rather than "what should we do about it."
    - Genuine causal questions cannot be answered with simple yes/no.
    - Avoid blame, vague generalities, or jumping to solutions/recommendations.
    
    Question Quality Guidelines:
    - Questions MUST start with interrogatives: "Why", "What caused", "How did", "What prevented", "What enabled", "Which".
    - Target the MOST IMMEDIATE proximate cause mentioned in the last answer.
    - Stay narrow and specific—avoid broad philosophical or multi-part questions.
    - Each question should advance understanding of the causal mechanism, not restate prior questions.
    - Keep questions under 160 characters for clarity.
    - NEVER ask about vendor strategic motives ("Why did Apple decide...") unless user explicitly provided such information.
    
    Contextual Continuity Rules:
    - ALWAYS reference the problem statement AND full Q/A history before formulating the next question.
    - If the last answer introduces multiple causes, prioritize the one most directly linked to the problem's core impact.
    - If answers become circular or speculative, ask a discriminating question to clarify which mechanism is primary.
    - Never repeat a question already asked; instead, probe a deeper layer within the same causal thread.
    - If answer is UNKNOWN ("I don't know"), pivot to concrete observables (metrics, components, timing, sequence).
    
    Output Discipline:
    - Respond ONLY with the question text (plain text, no formatting, no numbering, no quotes).
    - Do NOT provide answers, commentary, reasoning, JSON, markdown, code fences, or function calls.
    - Do NOT invent or call tools/functions (e.g., no <function=...>, no 'brute_force_search', no argument objects).
    - Do NOT include phrases like 'final_result', 'Summary:', or explanatory labels.
    
    Examples of GOOD questions (contextual, causal, specific):
    - "Why did the database connection pool become exhausted during the morning traffic spike?"
    - "What prevented the auto-scaling policy from triggering before the load increased?"
    - "Why was the cache expiration time set to only 5 minutes instead of a longer duration?"
    - "Which process shows the highest CPU usage when the lag begins?"
    
    Examples of BAD questions (vague, solution-focused, or multi-part):
    - "Why don't we have better monitoring?" (solution, not cause)
    - "What could be the issue?" (vague, not targeted)
    - "Why is the system slow and what should we do?" (multi-part, includes solution)
    - "Why did Apple decide to change the display subsystem?" (vendor motive speculation without user evidence)
    """
).strip()


def build_initial_question_prompt(problem: str) -> str:
    return dedent(
        f"""
        Problem Statement:
        {problem}

        Task: Ask the FIRST 'Why' question to begin root cause exploration.
        
        Step-by-step reasoning process (INTERNAL—do not output this):
        1. Parse the problem statement to identify:
           - Affected system, component, or process
           - Observable failure or degradation (the SYMPTOM)
           - Business/user impact
           - Temporal or environmental context (if provided)
        2. Identify the MOST IMMEDIATE observable effect that demands explanation.
           This is usually the direct manifestation of the problem (e.g., "API latency increased" not "users are unhappy").
        3. Formulate a single causal question targeting WHY this immediate effect occurred.
           Ask about the proximate cause, not distant systemic issues yet.
        4. Ensure the question:
           - Is specific and narrow (not "Why is the system bad?")
           - Cannot be answered with yes/no
           - Does not propose solutions or ask about budgets/resources unless they are the immediate cause
           - Relates directly to the stated problem, not a tangent
        5. Output ONLY the question—no preamble, numbering, reasoning, or explanation.
        
        Example transformations (DO NOT copy these; generate your own based on the actual problem):
        Problem: "Morning API latency spikes between 08:00-09:00 UTC"
        → Good first question: "Why does API latency specifically increase during the 08:00-09:00 UTC window?"
        
        Problem: "Users unable to log in after deployment"
        → Good first question: "Why did user login attempts start failing immediately after the deployment?"
        
        Now generate the first question for the actual problem above.
        
        {SYSTEM_STYLE_GUIDANCE}
        """
    ).strip()


def build_follow_up_question_prompt(
    problem: str,
    history: Sequence[QAHistoryItem],
    last_answer_type: Optional[str] = None,
    pivot_mode: Optional[str] = None
) -> str:
    formatted = _format_history(history)
    last_answer = history[-1].answer if history else "(none)"
    step = (history[-1].index + 1) if history else 1
    
    # Build pivot guidance if needed
    pivot_guidance = ""
    if pivot_mode == "observable":
        pivot_guidance = """
        PIVOT REQUIRED: Last answer was UNKNOWN.
        Instead of asking another abstract "Why", request a concrete observable:
        - What measurable change occurs first (metric, resource usage, timing)?
        - Which specific component, process, or service exhibits abnormal behavior?
        - What event or action immediately precedes the symptom?
        """
    elif pivot_mode == "reproduction":
        pivot_guidance = """
        PIVOT REQUIRED: Multiple consecutive UNKNOWN answers.
        Ask for reproduction pattern:
        - Under which specific conditions does the problem occur?
        - What sequence of actions triggers it?
        - Does it happen consistently or intermittently?
        """
    elif pivot_mode == "metric":
        pivot_guidance = """
        PIVOT REQUIRED: Multiple UNKNOWN answers with insufficient depth.
        Force evidence collection by requesting a measurable metric:
        - CPU %, memory usage, error count, latency, throughput?
        - Which metric spikes or drops when the problem occurs?
        - What are the before/after values?
        """
    elif last_answer_type == "VAGUE":
        pivot_guidance = """
        CAUTION: Last answer was VAGUE (generic, no specific mechanism).
        Ask for concrete specificity:
        - Which exact component, process, or resource is involved?
        - What specific action or configuration caused this?
        - Avoid accepting abstract descriptions; probe for technical detail.
        """
    
    return dedent(
        f"""
        Problem Statement:
        {problem}

        Prior Steps:
        {formatted}

        Most Recent Answer:
        {last_answer}
        
        {pivot_guidance}

        Task: Ask the NEXT 'Why' question (step {step}) to probe deeper into the causal chain.
        
        Critical Context Rules:
        - You are building a CAUSAL CHAIN from symptom → immediate cause → underlying mechanism → root cause.
        - The next question MUST directly address the most recent answer, advancing one level deeper.
        - DO NOT skip levels or jump to distant systemic issues prematurely.
        - DO NOT repeat or rephrase any prior question; each question must advance understanding.
        
        Step-by-step reasoning process (INTERNAL—do not output this):
        1. Review the full Q/A history to understand the causal thread already established.
        2. Analyze the MOST RECENT answer:
           - What immediate cause or mechanism did it identify?
           - Is there a specific condition, action, or configuration mentioned?
           - Are there time/resource/design constraints implied?
        3. Identify the SMALLEST proximate cause within that answer that has NOT been directly questioned yet.
        4. If the chain is becoming circular or the answer is vague:
           - Ask a discriminating question to clarify WHICH mechanism is primary
           - Or request specificity about timing, magnitude, or scope
        5. Formulate a question that:
           - Targets WHY the mechanism/condition in the last answer exists or occurred
           - Stays local to the newly uncovered layer (don't leap to org culture yet if discussing a config setting)
           - Focuses on CAUSE, not solution, policy, blame, or counterfactuals ("what if we had...")
        6. Output ONLY the question—no reasoning, numbering, or explanation.
        
        Example progression (illustrative—do NOT copy):
        Q1: "Why did the API timeout?"
        A1: "Because database queries queued too long."
        → Good Q2: "Why did database queries queue longer than expected?"
        
        Q2: "Why did database queries queue longer than expected?"
        A2: "Because the connection pool was saturated."
        → Good Q3: "Why was the connection pool saturated during that period?"
        
        Q3: "Why was the connection pool saturated during that period?"
        A3: "Because batch jobs were running heavy analytics queries at the same time as user traffic."
        → Good Q4: "Why were batch jobs scheduled to run during peak user traffic hours?"
        
        Now generate the next question for step {step} based on the actual history above.
        
        {SYSTEM_STYLE_GUIDANCE}
        """
    ).strip()


def build_final_analysis_prompt(problem: str, history: Sequence[QAHistoryItem]) -> str:
        formatted = _format_history(history)
        return dedent(
                f"""
                Problem Statement:
                {problem}

                Full 5 Whys History:
                {formatted}

            Task: Produce the final root cause analysis synthesizing the complete causal chain.
            
            Root Cause Analysis Methodology:
            1. Trace the ENTIRE causal chain from symptom (Q1) to deepest underlying cause (Q5).
            2. The ROOT CAUSE is NOT a symptom, NOT a solution, and NOT the last answer verbatim.
               - It is the deepest ACTIONABLE systemic condition that, if addressed, would prevent recurrence.
               - It should answer: "What fundamental condition or gap enabled this entire chain?"
            3. Contributing factors are distinct causal enablers or amplifiers (not restated symptoms).
               - They must be concrete and evidence-based from the Q/A history.
               - Typically 2-5 factors; avoid listing every answer as a factor.
               - OMIT entirely if no valid distinct factors exist (do not force vague ones).
            4. DO NOT speculate beyond the provided Q/A pairs.
            5. DO NOT include solutions, recommendations, or counterfactuals in the summary or factors.
            6. DO NOT include vendor motive speculation unless user explicitly stated it.
            7. ALWAYS produce a root cause summary; NEVER leave it empty or say "insufficient evidence" in the summary field itself.
            
            Factor Vagueness Filter (CRITICAL):
            REJECT these patterns from contributing_factors:
            - Generic adjectives without mechanism: "improved look and feel", "better UI", "enhanced security"
            - Restated symptoms: if it's just rewording the problem, exclude it
            - Solutions or recommendations: "should have done X"
            - Vendor strategic motives: "Apple wanted to...", "design decision to..."
            - Pure restatements: if similar to another factor or the summary, deduplicate
            
            ACCEPT only factors with concrete mechanism references:
            - "High CPU usage in WindowServer process"
            - "Connection pool sized for 50 but peak load requires 200"
            - "Batch job schedule overlaps with user traffic window"
            - "No automatic retry logic for transient failures"
            
            Internal reasoning process (DO NOT OUTPUT):
            1. Map each answer to its position in the causal chain.
            2. Identify where the chain converges on a systemic condition (e.g., lack of process, design flaw, resource constraint).
            3. Collapse redundant or superficial layers; isolate the deepest cause that is still actionable.
            4. Extract contributing factors that materially enabled or amplified that root cause.
            5. Apply vagueness filter: remove any factor lacking a concrete mechanism/component/metric reference.
            6. Validate that summary is concise (one sentence) and factors are distinct (no duplicates or restatements).
            7. If no valid factors remain after filtering, set contributing_factors to an empty array.
            
            Example (illustrative—do NOT copy structure blindly):
            Problem: "Morning API latency spikes"
            History summary: timeout → query queuing → pool saturation → batch jobs during peak → unreviewed legacy schedule
            → Root cause summary: "Batch analytics jobs inherited an unreviewed legacy schedule that overlaps with peak user traffic, causing resource contention."
            → Contributing factors: ["Fixed 08:00 cron for batch jobs aligned with legacy reporting window", "No periodic review process for job schedules after traffic growth", "Connection pool sized for average load without accounting for batch overlap"]
            
            IMPORTANT OUTPUT FORMAT:
            - Return ONLY valid JSON.
            - DO NOT prepend labels like 'Summary:', 'Root Cause:', or add prose before/after the JSON.
            - Schema (STRICT):
                {{
                    "summary": "<single concise sentence describing the root cause>",
                    "contributing_factors": ["<factor 1>", "<factor 2>", ...]
                }}
            
            Rules:
            - "summary": single sentence, no speculation words ("maybe", "might", "possibly"), no solutions, NEVER empty.
            - "contributing_factors": array of 0-6 distinct concrete strings; omit entirely (empty array) if none pass vagueness filter.
            - DO NOT repeat summary text inside contributing_factors.
            - NO additional JSON keys beyond these two.
            - NO tool/function calls, code fences, markdown, or explanatory text outside JSON.
            
            Now produce the root cause analysis JSON for the actual problem above.
                """
        ).strip()

__all__ = [
    "QAHistoryItem",
    "build_initial_question_prompt",
    "build_follow_up_question_prompt",
    "build_final_analysis_prompt",
]
