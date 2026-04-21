import os
import re

# Common tech skills dictionary for keyword matching
SKILLS_DB = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "html", "css", "sass", "less", "tailwind", "bootstrap",
    "react", "angular", "vue", "svelte", "next.js", "nuxt.js", "gatsby",
    "node.js", "express", "fastapi", "django", "flask", "spring", "laravel",
    "rails", "asp.net", ".net", "graphql", "rest api",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "sqlite", "oracle", "cassandra", "dynamodb", "firebase",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "jenkins", "github actions", "ci/cd", "linux", "nginx", "apache",
    "git", "github", "gitlab", "bitbucket",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "data analysis", "data science", "data engineering", "etl",
    "power bi", "tableau", "excel", "jupyter",
    "figma", "sketch", "adobe xd", "photoshop", "illustrator",
    "ui/ux", "responsive design", "wireframing", "prototyping",
    "agile", "scrum", "jira", "confluence", "trello",
    "project management", "team leadership", "communication",
    "problem solving", "critical thinking", "analytical skills",
    "selenium", "cypress", "jest", "pytest", "unit testing",
    "api testing", "postman", "swagger",
    "blockchain", "solidity", "web3",
    "ios", "android", "react native", "flutter", "mobile development",
    "devops", "sre", "microservices", "serverless",
    "cybersecurity", "penetration testing", "oauth", "jwt",
    "hadoop", "spark", "kafka", "airflow",
    "salesforce", "sap", "erp", "crm",
]


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""


def extract_skills(file_path: str) -> list:
    """Extract skills from a resume file (PDF or DOCX)."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        return []

    if not text:
        return []

    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_DB:
        # Use word boundary matching for short skills to avoid false matches
        if len(skill) <= 2:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        else:
            if skill in text_lower:
                found_skills.append(skill)

    # Deduplicate and sort
    return sorted(list(set(found_skills)))
