MODEL_NAME = "gpt-4o"

QUESTION_CATEGORIES = (
    (
        "Background",
        "Explore the candidate's professional background and accomplishments to showcase how "
        "their experience resonates with the desired position.",
    ),
    (
        "Technical Knowledge",
        "Probe the candidate's theoretical understanding of key concepts, best practices, and "
        "applications relevant to the role.",
    ),
    (
        "Situational",
        "Assess how the candidate handles various work-related scenarios, their problem-solving, "
        "decision-making, and ability to navigate workplace challenges.",
    ),
    (
        "Brain Teaser",
        "Examine the candidate's creativity and critical thinking, revealing their problem-solving "
        "approach and adaptability to unforeseen challenges.",
    ),
    (
        "Analytical",
        "Test the candidate's ability to analyze data, think critically, and reach conclusions — "
        "showcasing how they apply these skills in decision-making for the role.",
    ),
)

DB_QUESTION_COUNT = 2
GENERATED_QUESTION_COUNT = 4
MAX_FOLLOW_UPS = 2


def get_setup_prompt(
    name: str,
    experience: str,
    skills: str,
    level: str,
    position: str,
    company: str,
    industry: str,
    job_description: str,
    job_requirements: str,
    db_questions: list,
) -> str:
    """System prompt for LLM 1 (Setup): builds the finished 6-question set."""
    role_lines = [f"- Position: {position}"]
    if level:
        role_lines.insert(0, f"- Level: {level}")
    if company:
        role_lines.append(f"- Company: {company}")
    if industry:
        role_lines.append(f"- Industry: {industry}")
    if job_description:
        role_lines.append(f"- Job Description: {job_description}")
    if job_requirements:
        role_lines.append(f"- Job Requirements: {job_requirements}")

    category_lines = "\n".join(f"- {title}: {description}" for title, description in QUESTION_CATEGORIES)
    db_question_lines = "\n".join(
        f'{i}. (bank category: {q["category"]}) "{q["text"]}"' for i, q in enumerate(db_questions, start=1)
    )

    return (
        "You are building the question set for a mock job interview.\n\n"
        "CANDIDATE PROFILE\n"
        f"- Name: {name}\n"
        f"- Experience: {experience}\n"
        f"- Skills: {skills}\n\n"
        "ROLE BEING INTERVIEWED FOR\n"
        f"{chr(10).join(role_lines)}\n\n"
        "QUESTION CATEGORIES\n"
        f"{category_lines}\n\n"
        f"QUESTIONS FROM THE QUESTION BANK ({DB_QUESTION_COUNT})\n"
        f"{db_question_lines}\n\n"
        "YOUR TASK\n"
        f"1. Take the {DB_QUESTION_COUNT} question bank entries above. If either one contains a factual "
        "error, outdated reference, or wording that doesn't make sense, correct it. Otherwise use it "
        "as-is. Their listed bank category is a suggestion, not final.\n"
        f"2. Generate {GENERATED_QUESTION_COUNT} additional questions tailored specifically to this "
        "candidate's stated experience and skills, and to what this role would realistically require.\n"
        f"3. Sort all {DB_QUESTION_COUNT + GENERATED_QUESTION_COUNT} questions (the corrected bank "
        "questions plus the generated ones) into the five categories above. Every category must be "
        "used at least once; one category will end up with two questions since there are "
        f"{DB_QUESTION_COUNT + GENERATED_QUESTION_COUNT} questions and 5 categories.\n"
        "4. Order the final list in a sensible interview flow (e.g. Background first).\n\n"
        f"Return exactly {DB_QUESTION_COUNT + GENERATED_QUESTION_COUNT} questions."
    )


def get_humanizer_prompt(
    current_question: str,
    current_category: str,
    previous_question: str,
    previous_response: str,
    follow_up_allowed: bool,
) -> str:
    """System prompt for LLM 2 (Humanizer): scores the previous answer and

    phrases the current predefined question as either a follow-up or a
    remark + question, depending on that score and on follow_up_allowed.
    Deliberately given only the current question, previous question, and
    previous response — not the full conversation history.
    """
    follow_up_rule = (
        "A follow-up is allowed this turn if you score the previous response above 5."
        if follow_up_allowed
        else "A follow-up is NOT allowed this turn no matter how you score the previous response "
        "(the follow-up budget for this interview is used up, or the last turn was already a "
        "follow-up) — you must produce a remark + predefined question instead."
    )

    return (
        "You are the 'Humanizer' stage of a mock interview pipeline. Your job is to turn the next "
        "predefined interview question into a natural-sounding conversational turn, based on how the "
        "candidate answered the previous question.\n\n"
        f"PREVIOUS QUESTION\n\"{previous_question}\"\n\n"
        f"CANDIDATE'S RESPONSE TO IT\n\"{previous_response}\"\n\n"
        f"NEXT PREDEFINED QUESTION (category: {current_category})\n\"{current_question}\"\n\n"
        "YOUR TASK\n"
        "1. Score the candidate's response to the previous question from 1 to 10.\n"
        f"2. {follow_up_rule}\n"
        "   - If producing a follow-up: rephrase the next predefined question so it reads as a "
        "natural follow-up that builds on what the candidate just said, digging deeper into that "
        "same thread, rather than moving on. Example style: \"Based on your previous experience "
        "working with machine learning models, can you describe a time when you improved the "
        "accuracy of a predictive model?\"\n"
        "   - If not producing a follow-up: write a short (one sentence) remark reacting to the "
        "candidate's previous response, then present the predefined question close to verbatim. "
        "Example style: \"It's impressive that you have experience deploying machine learning "
        "models to production, can you explain the steps you took to ensure the reliability of your "
        "models in a live environment?\"\n"
        "3. Set is_follow_up to match which branch you took.\n"
        "4. Put the finished, ready-to-display text in `message` — nothing else should be shown to "
        "the candidate outside of it."
    )


EVALUATION_SYSTEM_PROMPT = (
    "You are an objective interview evaluation tool. Evaluate the job interview transcript question-by-question. "
    "Do not address the candidate directly, ask follow-up questions, or add conversational filler — "
    "return only the structured evaluation described by the response schema.\n\n"
    "The interview asked one question from each of these categories, in order: "
    f"{', '.join(title for title, _ in QUESTION_CATEGORIES)}. For each question, set `topic` to its "
    "category name from that list.\n\n"
    "PER-QUESTION EVALUATION:\n"
    "- Did the candidate directly answer the specific question?\n"
    "- Did they provide sufficient depth, concrete examples, or structured reasoning (e.g., STAR method)?\n"
    "- Was the response clear, articulate, and appropriate for the target level?\n"
    "Score each question from 1-10, write a 1-2 sentence critique, and list 1-3 short key takeaways "
    "(the specific things worth remembering about that answer, good or bad).\n\n"
    "OVERALL SCORING\n"
    "Score the interview overall from 0-10, plus four supporting criteria, each scored 0-10 "
    "independently of the others:\n"
    "- communication_score: how clear, articulate, and well-structured the candidate's communication "
    "was across all answers.\n"
    "- depth_score: how much concrete depth, detail, and evidence (specific examples, the STAR method) "
    "the candidate's answers contained.\n"
    "- problem_solving_score: the quality of the candidate's reasoning and problem-solving, especially "
    "on the Situational, Brain Teaser, and Analytical questions.\n"
    "- role_fit_score: how well the candidate's background and answers align with what the target role "
    "and industry actually require.\n\n"
    "Ground overall_summary, top strengths, and areas for improvement in specific moments from the "
    "transcript rather than generic praise or criticism."
)


def get_evaluation_user_prompt(conversation_history: str) -> str:
    """Formats the evaluation prompt with conversation history."""
    return (
        "Evaluate the following interview transcript and produce feedback in the required format. "
        "Do not engage in conversation or add anything outside the specified format.\n\n"
        "--- TRANSCRIPT START ---\n"
        f"{conversation_history}\n"
        "--- TRANSCRIPT END ---"
    )
