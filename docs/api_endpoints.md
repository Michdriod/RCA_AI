# Planned API Endpoints
POST /session/start
POST /session/answer  (body: session_id, question_id, answer)
GET  /session/next    (returns next question or final analysis)
GET  /session/{id}    (state)
POST /session/complete (optional external push)
