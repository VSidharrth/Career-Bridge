# CareerBridge

CareerBridge is a role-based hiring platform built with FastAPI, Jinja2 templates, Tailwind CSS, MongoDB, PyMongo, and JWT authentication.

The platform supports three user roles:
- Candidate
- Recruiter
- Admin

It provides resume-based skill extraction, job matching, and end-to-end application tracking.

## 1. What This Project Does

CareerBridge connects candidates and recruiters in a single web app.

Candidates can:
- Register and log in
- Maintain their profile
- Upload resume (PDF or DOCX)
- Auto-extract skills from resume
- Browse jobs ranked by skill match
- Apply for jobs
- Track application status

Recruiters can:
- Register and log in
- Create, edit, and delete jobs
- View applicants for each job
- See candidate-job match scores
- Update application status

Admins can:
- View platform stats
- View and filter users
- Block or unblock users
- View and delete jobs

## 2. Tech Stack

- Backend: FastAPI
- Templates: Jinja2
- Styling: Tailwind CSS (via CDN) + custom CSS
- Database: MongoDB with PyMongo
- Authentication: JWT in HTTP-only cookies
- Password hashing: bcrypt via passlib
- Resume parsing: pdfplumber and python-docx

## 3. Core Application Flow

1. User registers as candidate or recruiter.
2. User logs in, server sets an HTTP-only access_token cookie.
3. Role-based routes determine available pages and actions.
4. Candidates upload resumes, skills are extracted and saved to profile.
5. Jobs are matched and sorted using candidate skills vs job required skills.
6. Recruiters review applicants and update application statuses.
7. Admin oversees users and jobs.

## 4. Authentication and Authorization

Authentication model:
- JWT is created at login and stored in an HTTP-only cookie.
- On each request, cookie is decoded and current user is loaded.

Authorization model:
- Candidate routes require role == candidate.
- Recruiter routes require role == recruiter.
- Admin routes require role == admin.

Additional guards:
- Blocked users cannot authenticate as active users.
- Ownership checks prevent recruiters from changing applications on jobs they do not own.
- Invalid ObjectId inputs are handled safely to avoid server errors.

## 5. Skill Matching Logic

Matching is done using set intersection:
- candidate_skills and job_skills are normalized to lowercase.
- Match score = (intersection_count / total_job_required_skills) * 100.
- Jobs are sorted by descending match score.

This keeps matching simple, fast, and explainable.

## 6. Resume Parsing Logic

Supported formats:
- PDF
- DOCX

Flow:
1. Candidate uploads file.
2. File extension and size are validated.
3. Text is extracted from file.
4. A skills dictionary is used for keyword matching.
5. Extracted skills are merged with existing profile skills.

Current extraction method is keyword-based (not ML), which is lightweight and easy to maintain.

## 7. MongoDB Collections and Data Design

### users
Holds account and role data.

Typical fields:
- _id (ObjectId)
- name
- email
- password_hash
- role (candidate, recruiter, admin)
- blocked (bool)
- created_at

### profiles
Holds candidate-specific profile data.

Typical fields:
- _id (ObjectId)
- user_id (string version of users._id)
- phone
- location
- bio
- skills (list[str])
- resume_path
- experience
- education

### jobs
Holds recruiter job postings.

Typical fields:
- _id (ObjectId)
- recruiter_id (string version of users._id)
- title
- company
- location
- type
- description
- skills_required (list[str])
- salary_range
- is_active (bool)
- created_at

### applications
Holds job applications from candidates.

Typical fields:
- _id (ObjectId)
- job_id (string version of jobs._id)
- candidate_id (string version of users._id)
- resume_path
- cover_letter
- status (applied, shortlisted, hired, rejected)
- applied_at

Indexes currently include:
- users.email unique
- profiles.user_id unique
- applications(job_id, candidate_id) unique

## 8. Route Map

### Public and common pages
- GET / -> home
- GET /jobs -> list jobs
- GET /jobs/{job_id} -> job detail

### Auth
- GET /login
- POST /login
- GET /register
- POST /register
- GET /logout

### Candidate
- GET /candidate/dashboard
- GET /candidate/profile
- POST /candidate/profile
- POST /candidate/resume
- GET /candidate/applications
- POST /jobs/{job_id}/apply

### Recruiter
- GET /recruiter/dashboard
- GET /recruiter/post-job
- POST /recruiter/post-job
- GET /recruiter/edit-job/{job_id}
- POST /recruiter/edit-job/{job_id}
- POST /recruiter/delete-job/{job_id}
- GET /recruiter/applicants/{job_id}
- POST /recruiter/update-status

### Admin
- GET /admin/dashboard
- POST /admin/block-user/{user_id}
- POST /admin/delete-job/{job_id}

## 9. Project Structure

app/
- main.py: FastAPI startup, router registration, default admin creation
- config.py: settings from environment variables
- database.py: Mongo connection and index creation

app/auth/
- routes.py: login/register/logout handlers
- utils.py: password hashing and JWT helpers
- dependencies.py: current user lookup from cookie token

app/routes/
- pages.py: home page
- jobs.py: browse, detail, apply
- candidate.py: candidate dashboard, profile, resume upload, applications
- recruiter.py: recruiter dashboard, job CRUD, applicants, status update
- admin.py: admin dashboard, user blocking, job deletion

app/services/
- matching.py: skill match score and sorting helpers
- resume_parser.py: PDF/DOCX text extraction and skill detection

app/templates/
- base.html and role-specific page templates

app/static/
- css/style.css: custom styling
- uploads/: resume uploads (runtime content)

## 10. Local Setup and Run

### Prerequisites
- Python 3.11+
- MongoDB running locally or remotely

### Setup
1. Create and activate a virtual environment.

Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Mac/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create environment file.

```bash
copy .env.example .env
```

4. Update .env values.

5. Start the app.

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. Open in browser:
- http://localhost:8000

## 11. Environment Variables

Configured in app/config.py:

- MONGO_URI
	MongoDB connection string.

- DB_NAME
	Database name.

- SECRET_KEY
	JWT signing key. Use a long random value.

- ALGORITHM
	JWT algorithm (default HS256).

- TOKEN_EXPIRY_HOURS
	Access token lifetime.

- COOKIE_SECURE
	true in HTTPS production, false for local HTTP.

- MAX_FILE_SIZE
	Maximum resume upload size in bytes (default 10 MB).

- ADMIN_EMAIL
	Default admin account email created on startup if no admin exists.

- ADMIN_PASSWORD
	Default admin account password.

## 12. First-Time Functional Test

Use this quick validation sequence:

1. Register recruiter account.
2. Login as recruiter and post jobs.
3. Logout.
4. Register candidate account.
5. Login as candidate.
6. Update profile and upload resume.
7. Browse jobs and apply.
8. Check candidate applications page.
9. Logout and login as recruiter.
10. Open applicants page and update status.
11. Login as admin and verify user/job management.

## 13. Security Notes

- Passwords are hashed with bcrypt.
- JWT is stored in HTTP-only cookie.
- Role checks protect all role-sensitive routes.
- Blocked accounts are prevented from normal access.
- Resume type and size validation is applied.
- ObjectId parsing is guarded to reduce malformed-request crashes.

## 14. Known Limitations

- Resume extraction is keyword-based and may miss context-heavy skills.
- Uploaded resumes are stored on local filesystem.
- No automated test suite included yet.