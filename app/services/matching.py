def calculate_match_score(candidate_skills: list, job_skills: list) -> int:
    """
    Calculate match score between candidate skills and job requirements.
    Returns percentage (0-100).
    """
    if not job_skills:
        return 0

    candidate_set = set(s.lower().strip() for s in candidate_skills)
    job_set = set(s.lower().strip() for s in job_skills)

    if not job_set:
        return 0

    intersection = candidate_set & job_set
    score = int((len(intersection) / len(job_set)) * 100)
    return min(score, 100)


def get_matched_jobs(candidate_skills: list, jobs: list) -> list:
    """
    Score and sort jobs by match percentage for a candidate.
    Returns list of job dicts with added 'match_score' field.
    """
    scored_jobs = []
    for job in jobs:
        job_skills = job.get("skills_required", [])
        score = calculate_match_score(candidate_skills, job_skills)
        job_copy = dict(job)
        job_copy["match_score"] = score
        scored_jobs.append(job_copy)

    # Sort by match score descending
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_jobs
