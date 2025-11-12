# RCA Enhancement Implementation Summary

## Changes Implemented

### 1. Answer Classification System
**File**: `backend/app/ai/agent.py`

Added `AnswerType` enum with four categories:
- `UNKNOWN`: "I don't know", "not sure", "can't say", etc.
- `VAGUE`: Generic descriptions without concrete mechanisms
- `MECHANISM`: References specific components, resources, or processes
- `CONTEXT`: Provides conditions/settings but not direct causes

**Method**: `_classify_answer(answer_text)` - Classifies each user answer to guide next question strategy.

### 2. Depth Tracking
**File**: `backend/app/ai/agent.py`

**Method**: `_compute_depth_score(session)` - Counts distinct mechanistic layers by tallying `MECHANISM` type answers. Excludes `UNKNOWN` and vague restatements.

Used to:
- Determine if sufficient causal depth exists before finalization
- Log depth_score in root cause analysis
- Guide pivot logic (force evidence questions if depth < 2 after 3 UNKNOWN answers)

### 3. Enhanced Question Generation
**File**: `backend/app/ai/agent.py`, `backend/app/ai/prompts.py`

**Logic Flow**:
1. Classify last answer before generating next question
2. Track UNKNOWN metrics: `unknown_count`, `unknown_streak`, `evidence_pivots`
3. Determine pivot mode based on classification:
   - After 2 consecutive UNKNOWN → pivot to "reproduction" (ask for reproduction pattern)
   - After 3 total UNKNOWN with depth < 2 → pivot to "metric" (force measurable data request)
   - Any single UNKNOWN → pivot to "observable" (request concrete component/process/metric)
   - If VAGUE → request specificity (concrete component/mechanism)

**Prompt Updates** (`build_follow_up_question_prompt`):
- Accepts `last_answer_type` and `pivot_mode` parameters
- Injects pivot guidance blocks based on mode
- Instructs model to shift from causal "Why" questions to evidence-seeking "What/Which" questions

### 4. Improved Prompt Guidance
**File**: `backend/app/ai/prompts.py`

**SYSTEM_STYLE_GUIDANCE Updates**:
- Added explicit ban on vendor motive speculation ("Why did Apple decide...")
- Added UNKNOWN pivot rule (if answer is unknown, request observables)
- Added "Which" to interrogative start patterns
- Enhanced examples showing good vs bad questions

**Final Analysis Prompt Updates** (`build_final_analysis_prompt`):
- **Factor Vagueness Filter**: Explicit rejection patterns for:
  - Generic adjectives ("improved look and feel", "better UI", "enhanced security")
  - Restated symptoms
  - Solutions/recommendations
  - Vendor strategic motives
  - Pure restatements
- **Acceptance criteria**: Only factors with concrete mechanism/component/metric references
- **Enforcement**: "OMIT entirely if no valid distinct factors exist"
- **No guessing rule**: "ALWAYS produce a root cause summary; NEVER leave it empty"

### 5. Strengthened Root Cause Synthesis
**File**: `backend/app/ai/agent.py`

**Logic** (`analyze_root_cause_async`):
- Computes depth_score before analysis
- Logs depth_score for observability
- Always produces a summary (no "insufficient evidence" in output)
- If summary empty after parsing, constructs minimal fallback from problem statement
- Applies factor filtering (empty array if none pass vagueness test)

**Fallback**: If structured parsing fails, still constructs valid summary from problem context rather than returning empty/error.

### 6. Metrics Expansion
**File**: `backend/app/ai/agent.py`

**New Counters**:
- `unknown_count`: Total UNKNOWN answers across all sessions
- `unknown_streak`: Consecutive UNKNOWN answers in current session (resets on non-UNKNOWN)
- `evidence_pivots`: Count of times pivot logic triggered

**Exposed via**: `get_metrics()` method (used by `/health` endpoint)

**Logged Events**:
- `ai.answer.classified`: Logs answer_type for each classification
- Enhanced `ai.question` event includes: unknown_count, unknown_streak, evidence_pivots
- Enhanced `ai.root_cause` event includes: depth_score

## Key Behavioral Improvements

### Problem: Repetitive vendor motive questions
**Solution**: Banned "Why did [Vendor] decide..." patterns unless user explicitly provided such information.

### Problem: Vague contributing factors ("improved look and feel")
**Solution**: Explicit vagueness filter rejecting generic adjectives without mechanism references.

### Problem: Shallow analysis when user answers "I don't know"
**Solution**: UNKNOWN classification triggers evidence-seeking pivots (observable, reproduction, metric).

### Problem: Speculation when insufficient data
**Solution**: Always produce summary (from causal chain or problem context); omit factors if none valid (empty array).

### Problem: No depth assessment
**Solution**: Track mechanistic layers; log depth_score; use for pivot thresholds.

## Testing

**New Test File**: `backend/tests/test_answer_classification.py`
- Tests all four classification categories
- Tests depth score computation (counts only MECHANISM answers)
- Validates classification patterns (unknown, vague, mechanism, context)

**Existing Tests**: Backward compatible
- Stub already accepts `model_settings` parameter
- No breaking changes to test structure

## Files Modified

1. `backend/app/ai/agent.py` - Added classification, depth tracking, pivot logic, metrics
2. `backend/app/ai/prompts.py` - Enhanced prompts with pivot guidance, vagueness filter, vendor motive ban
3. `backend/tests/test_answer_classification.py` - New test coverage for classification and depth

## Deployment Notes

- No configuration changes required (uses existing AI_TEMPERATURE, AI_TOP_P)
- Metrics automatically exposed via existing `/health` endpoint
- Backward compatible with existing sessions
- No database schema changes

## Expected Improvements

1. **Higher contextual relevance**: Questions adapt based on answer quality
2. **Reduced speculation**: No vendor motive questions without evidence; no vague factors
3. **Better handling of "I don't know"**: Pivots to evidence rather than repeating "Why"
4. **Cleaner factors**: Vagueness filter removes generic restatements
5. **Consistent output**: Always produces root cause summary (no "insufficient evidence" errors)
6. **Observable quality**: Metrics track UNKNOWN patterns and depth for tuning
