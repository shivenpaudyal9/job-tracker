# Job Tracker - Production Architecture

## System Overview
Production-grade job application tracking system with automated email ingestion, intelligent parsing, and Excel export.

## Tech Stack

### Backend
- **FastAPI** - Modern async Python framework
- **SQLAlchemy 2.0** - ORM with async support
- **PostgreSQL** - Primary database
- **Microsoft Graph SDK** - Outlook integration
- **Pydantic v2** - Data validation

### Frontend
- **React 18** + **TypeScript**
- **TanStack Query** - Server state
- **TailwindCSS** - Styling
- **shadcn/ui** - Component library

### Processing
- **OpenAI GPT-4** - LLM fallback for ambiguous emails
- **BeautifulSoup4** - HTML parsing
- **python-magic** - MIME type detection

### Export
- **openpyxl** - Excel generation

## Data Flow

1. **Ingestion**: Microsoft Graph polls Outlook every 5 minutes
2. **Unwrapping**: Extract original email from forwarded content
3. **Classification**: Rule-based + LLM fallback extraction
4. **Matching**: Link emails to applications
5. **Storage**: Upsert to PostgreSQL with deduplication
6. **Export**: Generate Excel with 3 sheets (Applications, Events, Actions)

## Key Design Decisions

### Why PostgreSQL?
- JSONB for flexible metadata storage
- Full-text search for email content
- Robust indexing for matching queries
- ACID compliance for data integrity

### Why Forwarded Email Unwrapper?
- Gmail→Outlook forwarding breaks threading
- "From" header shows forwarding account, not original sender
- Must extract original headers from email body
- Critical for accurate matching

### Why Two-Layer Classification?
- Deterministic rules for common patterns (fast, reliable)
- LLM fallback only when confidence < 0.7 (cost-effective)
- Always store confidence scores for manual review routing

### Why Email Fingerprinting?
- Forwarding changes message-id
- Need stable hash: original_from + subject + date + body_prefix
- Prevents duplicate processing on re-sync

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│  Load Balancer (nginx)                  │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐           ┌───▼────┐
│ React  │           │ FastAPI│
│ Frontend│          │ Backend│
│ (Static)│          │ (API)  │
└────────┘           └───┬────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         ┌────▼─────┐        ┌─────▼──────┐
         │PostgreSQL│        │Background  │
         │          │        │Worker      │
         │          │        │(Celery)    │
         └──────────┘        └────────────┘
```

## Security Considerations

1. **OAuth 2.0** for Microsoft Graph (no password storage)
2. **Encrypted secrets** in environment variables
3. **Rate limiting** on API endpoints
4. **SQL injection prevention** via ORM
5. **CORS** properly configured
6. **Audit logs** for manual review changes

## Scalability

- **Async processing** for email fetching (thousands of emails)
- **Batch upserts** for database writes
- **Connection pooling** for database
- **Caching** for frequently accessed applications
- **Pagination** on all list endpoints

## Monitoring

- **Structured logging** (JSON format)
- **Metrics**: processing time, confidence scores, match rates
- **Alerts**: failed syncs, low confidence spikes
- **Dashboard**: ingestion stats, manual review queue size
