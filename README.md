# LAKSHYA AI - B2B Revenue Intelligence Platform MVP

A demo platform showcasing AI-powered revenue intelligence capabilities for the Indian B2B market.

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL (SQLite fallback for local dev)
- Pydantic v2

**Frontend:**
- React (Vite)
- TailwindCSS
- React Router
- Recharts

**AI:**
- Anthropic Claude API (claude-sonnet-4)
- OpenAI Whisper API (audio transcription)

## Setup Instructions

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Edit `.env` with your configuration (API keys, database URL, etc.)

6. Run database migrations:
```bash
alembic upgrade head
```

7. Seed demo data:
```bash
python seed_data.py
```

8. Start the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

## Default Login Credentials

After seeding, use:
- Email: `admin@lakshya.ai`
- Password: `admin123`

## Demo Mode Notes

🎭 **Demo Mode Active** - The following modules use simulated/seed data for MVP demonstration:

- **Company Intelligence Graph**: Uses synthesized company data (not live MCA/GST/Udyam scraping)
- **Tally Integration**: Uses CSV upload simulation (not live Tally API)
- **WhatsApp Integration**: Uses text paste/file upload (not live WhatsApp Business API)

Real integrations require additional data pipelines and API approvals planned for production version.

## Project Structure

```
lakshya-ai/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── db.py              # Database connection
│   │   ├── routers/           # API route handlers
│   │   └── services/          # Business logic & AI extraction
│   ├── alembic/               # Database migrations
│   ├── requirements.txt
│   └── seed_data.py           # Demo data generator
└── frontend/
    ├── src/
    │   ├── pages/             # Page components
    │   ├── components/        # Reusable components
    │   └── api/               # API client
    └── package.json
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
