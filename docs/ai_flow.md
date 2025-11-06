# AI Flow (5 Whys)
Input: problem_statement
Loop i=1..5: generate_question_async(previous_context)
After 5 answers: analyze_root_cause_async(all_answers) -> root_cause
Store each step in Redis.
