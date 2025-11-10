# Prompt Engineering & LLM Configuration for RCA

This document explains the prompt engineering strategy and LLM configuration used to achieve high-accuracy (90%+) root cause analysis through contextual, genuine questions.

## Core Objective

Generate 5 contextual, causal questions that progressively drill down from **symptom → immediate cause → underlying mechanism → root cause**, ensuring each question:
- Directly addresses the problem statement
- Builds on prior Q/A history
- Advances one level deeper in the causal chain
- Avoids repetition, vagueness, or solution-focused language
- Enables accurate root cause identification in exactly 5 steps

## LLM Configuration

### Temperature & Top-P Settings

```bash
AI_TEMPERATURE=0.3   # Range: 0.0-1.0 (default: 0.3)
AI_TOP_P=0.85        # Range: 0.0-1.0 (default: 0.85)
```

**Rationale:**
- **Temperature 0.3**: Lower temperature produces more **deterministic, focused** outputs. For RCA, we prioritize precision and consistency over creative diversity. Values 0.2-0.4 are recommended.
  - Too low (0.0-0.1): May produce repetitive or overly rigid questions
  - Too high (0.7-1.0): Introduces randomness, reduces contextual coherence
  
- **Top-P 0.85**: Nucleus sampling controls diversity by limiting token selection to the top 85% probability mass. This balances:
  - Focus: Avoids low-probability tangential paths
  - Flexibility: Allows some variation when context demands it
  - Recommended range: 0.8-0.9 for analytical tasks

**Impact on Question Quality:**
| Setting | Effect | RCA Suitability |
|---------|--------|----------------|
| Temp: 0.1, Top-P: 0.7 | Highly repetitive, narrow | ❌ Too rigid |
| Temp: 0.3, Top-P: 0.85 | Focused, contextual, consistent | ✅ Optimal |
| Temp: 0.7, Top-P: 0.95 | Creative but less predictable | ⚠️ Risk of drift |
| Temp: 1.0, Top-P: 1.0 | High randomness, speculative | ❌ Unreliable |

### Model Selection

Default: `llama-3.3-70b-versatile` (via Groq)

**Why this model:**
- Strong instruction-following capability
- Good at maintaining context across multi-turn conversations
- Fast inference for real-time Q/A flows
- Handles structured output (JSON) reliably

**Alternative models (configure via `AI_MODEL`):**
- `llama-3.1-70b-versatile`: Slightly older but still strong
- `mixtral-8x7b-32768`: Good for longer context windows
- Avoid smaller models (<13B params) for complex causal reasoning

## Prompt Engineering Strategy

### 1. System Guidance (Applied to All Questions)

```
Core RCA Principles:
- 5 Whys discovers UNDERLYING SYSTEMIC CAUSE, not surface symptoms
- Each question moves DOWN one causal level
- Focus on "why THIS happened" not "what should we do"
- Genuine causal questions cannot be yes/no
- Avoid blame, vague generalities, or jumping to solutions
```

**Key Elements:**
- **RCA Methodology**: Explicit causal chain progression rules
- **Question Quality Standards**: Interrogative start, narrow scope, <160 chars
- **Contextual Continuity**: Always reference problem + full history
- **Output Discipline**: Plain text only, no formatting/tools/JSON

**Good vs Bad Examples Embedded in Prompts:**

✅ **Good Questions** (contextual, causal, specific):
- "Why did the database connection pool become exhausted during the morning traffic spike?"
- "What prevented the auto-scaling policy from triggering before the load increased?"

❌ **Bad Questions** (vague, solution-focused, multi-part):
- "Why don't we have better monitoring?" (solution, not cause)
- "What could be the issue?" (vague, not targeted)

### 2. Initial Question Prompt

**Structure:**
1. **Problem Statement**: User-provided symptom/issue
2. **Step-by-Step Reasoning Process** (internal, not output):
   - Parse problem: system, symptom, impact, context
   - Identify MOST IMMEDIATE observable effect
   - Formulate causal question targeting proximate cause
   - Validate: specific, not yes/no, relates directly to problem
3. **Example Transformations**: Illustrative good first questions
4. **System Guidance**: Full RCA principles

**Why This Works:**
- **Explicit reasoning chain** guides model through analytical process
- **Examples** show desired pattern without copying
- **Problem-specific targeting** prevents generic questions
- **Validation checklist** enforces quality constraints

### 3. Follow-Up Question Prompt

**Enhanced Context Rules:**
```
Critical Context Rules:
- Building a CAUSAL CHAIN from symptom → root cause
- Next question MUST directly address most recent answer
- DO NOT skip levels or jump to distant systemic issues
- DO NOT repeat or rephrase prior questions
```

**Step-by-Step Reasoning (Internal):**
1. Review full Q/A history for established causal thread
2. Analyze most recent answer: mechanism, condition, constraint
3. Identify SMALLEST proximate cause not yet questioned
4. If circular/vague: ask discriminating question for specificity
5. Formulate question targeting WHY that mechanism exists
6. Output only the question

**Progressive Example Chain:**
```
Q1: "Why did the API timeout?"
A1: "Because database queries queued too long."
→ Q2: "Why did database queries queue longer than expected?"

A2: "Because the connection pool was saturated."
→ Q3: "Why was the connection pool saturated during that period?"

A3: "Because batch jobs ran heavy analytics queries simultaneously with user traffic."
→ Q4: "Why were batch jobs scheduled during peak user traffic hours?"

A4: "Because their cron inherited a legacy reporting time never reviewed."
→ Q5: "Why was the job schedule never reviewed after traffic patterns changed?"
```

**Why This Works:**
- **Full history visibility** prevents repetition and ensures continuity
- **Smallest proximate cause** rule keeps progression incremental
- **Discriminating questions** handle ambiguity without speculation
- **Example progression** demonstrates causal chain depth

### 4. Final Analysis Prompt

**Root Cause Methodology:**
```
1. Trace ENTIRE causal chain from symptom (Q1) to deepest cause (Q5)
2. ROOT CAUSE is NOT:
   - A symptom
   - A solution
   - The last answer verbatim
3. ROOT CAUSE IS:
   - Deepest ACTIONABLE systemic condition
   - Answer to: "What fundamental condition enabled this chain?"
4. Contributing factors: distinct causal enablers/amplifiers (2-5 typical)
5. NO speculation beyond provided Q/A pairs
```

**Validation Rules:**
- Summary: single sentence, no speculation ("maybe", "might"), no solutions
- Factors: 2-6 distinct strings, concrete, evidence-based
- NO restating summary inside factors
- Strict JSON output only

**Why This Works:**
- **Explicit root cause definition** prevents symptom confusion
- **Validation constraints** enforce precision and non-speculation
- **Example structure** shows proper factor extraction
- **Strict JSON** enables programmatic consumption

## Anti-Speculation Safeguards

### Removed Problematic Phrases:
- ❌ "If unsure, guess" → Encourages fabrication
- ❌ "Maybe", "might", "possibly" → Speculative language
- ❌ "What if we had..." → Counterfactual distractions

### Added Constraints:
- ✅ "Do NOT invent or speculate beyond provided Q/A history"
- ✅ "If genuinely unavailable, return empty string/list"
- ✅ "Evidence-based from Q/A history only"

## Semantic Deduplication

**Threshold:** 0.85 similarity (SequenceMatcher ratio)
**Max Retries:** 3 attempts with penalty prompts

**Penalty Prompt Structure:**
```
Penalty: Prior attempt duplicated earlier question (similarity=0.92).
Generate a DEEPER, non-redundant causal question targeting a more specific
underlying mechanism. Do NOT rephrase: '<duplicate question>'
```

**Why This Works:**
- **Similarity detection** catches paraphrasing and repetition
- **Penalty guidance** pushes model toward deeper causal layer
- **Negative example** explicitly shows what to avoid
- **Metrics tracking** monitors model quality over time

## Tuning Recommendations

### To Increase Question Depth:
1. Lower temperature to 0.2 (more deterministic)
2. Add more example causal chains in follow-up prompts
3. Strengthen "smallest proximate cause" rule emphasis

### To Reduce Repetition:
1. Increase deduplication threshold to 0.90
2. Add more varied "good question" examples
3. Expand penalty prompt with multiple negative examples

### To Improve Root Cause Accuracy:
1. Add domain-specific examples in final analysis prompt
2. Strengthen "deepest actionable cause" definition
3. Require explicit causal chain mapping in reasoning steps

### To Handle Vague User Answers:
1. Add discriminating question templates in follow-up prompt
2. Train model to request specificity (timing, magnitude, scope)
3. Expand "if circular/vague" guidance with more examples

## Measuring Success

### Key Metrics:
- **Dedup retry rate**: Should be <30% (too high = model forgetting context)
- **Duplicate acceptance rate**: Should be <5% (quality gate)
- **Question length**: 80-160 chars (focused, not verbose)
- **Root cause actionability**: Manual review of summaries

### Quality Gates:
1. ✅ Each question starts with interrogative
2. ✅ No question repeats prior question (>0.85 similarity)
3. ✅ Questions progress logically through causal chain
4. ✅ Root cause summary is actionable (not symptom or solution)
5. ✅ Contributing factors are distinct (not restated summary)

## Future Enhancements

### Embedding-Based Similarity:
Replace `SequenceMatcher` with semantic embeddings (e.g., `sentence-transformers`) for:
- Deeper semantic duplicate detection (catch conceptual overlap beyond string similarity)
- Cross-language support
- Better handling of paraphrasing

### Adaptive Temperature:
Adjust temperature dynamically based on:
- Question depth (lower temp for Q4-Q5 for precision)
- User answer clarity (higher temp if answer is vague, to explore alternatives)
- History coherence (lower temp if chain is strong)

### Domain-Specific Prompts:
Create specialized prompt templates for:
- Infrastructure/DevOps RCA
- Software bug RCA
- Business process RCA
- Customer experience RCA

Each with tailored examples and causal factor taxonomies.

## References

- [Toyota 5 Whys Methodology](https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Temperature & Top-P Explained](https://platform.openai.com/docs/guides/text-generation)
