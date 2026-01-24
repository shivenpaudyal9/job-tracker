# Excel Export - Test Data

## File Location

**Path:** `C:\Users\91953\job-tracker-v2\backend\job_applications.xlsx`
**Size:** 6.9 KB

## How to Open

Simply double-click the file or run:
```bash
cd C:\Users\91953\job-tracker-v2\backend
start job_applications.xlsx
```

## Contents

The Excel file contains **3 sheets**:

### Sheet 1: Applications (Main Data)
**6 applications** with 13 columns:

| Company | Job Title | Status | Location | Action Required |
|---------|-----------|--------|----------|----------------|
| Google | Software Engineer | APPLIED_RECEIVED | Remote | No |
| ByteDance | Software Engineer Intern | NEXT_STEP_ASSESSMENT | Remote | No |
| Palo Alto Networks | IT Principal AI Engineer | REJECTED | - | No |
| The Voleon Group | Data Analyst | APPLIED_RECEIVED | Berkeley, CA | No |
| Genworth | Data Analyst | APPLIED_RECEIVED | Richmond, VA | No |
| Meta | Data Scientist | INTERVIEW_SCHEDULED | Menlo Park, CA | No |

**All Columns:**
1. ID
2. Company Name
3. Job Title
4. Location
5. Status
6. Application Date
7. Last Updated
8. Action Required
9. Action Type
10. Action Deadline
11. Event Count
12. Link Count
13. Confidence

### Sheet 2: Events (Timeline)
Currently empty (no events yet since these were manually created)

**Columns:**
- Event ID
- Application (Company + Job Title)
- Event Type
- Status
- Event Date
- Confidence
- Source Email
- Notes

### Sheet 3: Action Queue
Currently empty (no pending actions with deadlines)

**Columns:**
- Application (Company + Job Title)
- Action Type
- Description
- Deadline
- Days Until Deadline
- Status
- Link Count

## Excel Formatting

The Excel file includes:
- **Styled headers** (blue background, white bold text)
- **Auto-sized columns** for readability
- **Status-based highlighting** (overdue actions in red)
- **Frozen top row** for easy scrolling
- **Data filtering enabled** on all sheets

## When Real Emails Are Processed

Once you sync real emails from Outlook, the Excel export will show:

1. **Applications Sheet:**
   - Full extraction data (company, job title, location)
   - Confidence scores per field
   - Latest email date
   - Count of related events and links

2. **Events Sheet:**
   - Complete timeline of all status changes
   - Application confirmations
   - Rejections
   - Assessment invites
   - Interview requests
   - Each linked to the source email

3. **Action Queue Sheet:**
   - Pending assessments with deadlines
   - Interview scheduling requests
   - Offer responses needed
   - Highlighted by urgency (overdue = red)

## Example Real-World Export

After processing your 7 real email examples:

**Applications Sheet** would show:
- Eleven Recruiting - Workday Reporting Analyst (APPLIED_RECEIVED)
- Genworth - Data Analyst (APPLIED_RECEIVED)
- The Voleon Group - Data Analyst (APPLIED_RECEIVED)
- CONFLUX SYSTEMS - Scientific & Regulatory Affairs (REJECTED)
- Palo Alto Networks - IT Principal AI Engineer (REJECTED)
- ByteDance - Software Engineer Intern (NEXT_STEP_ASSESSMENT)

**Events Sheet** would show:
- 7 application confirmation/status events
- Each with confidence scores and source email links

**Action Queue** would show:
- ByteDance - Complete CodeSignal Assessment (if deadline extracted)

## Regenerating the Export

The export can be regenerated anytime:

**Via API:**
```bash
curl -X POST http://localhost:8000/export
```

**Via Python:**
```python
from app.database import SessionLocal
from app.excel_exporter import export_to_excel

db = SessionLocal()
export_to_excel(db, "my_applications.xlsx")
```

## Next Steps

1. **Open the Excel file** to see the format
2. **Set up Microsoft Graph** to sync real Outlook emails
3. **Process your forwarded job emails**
4. **Export again** to see the full system in action with real data

The export is reproducible and can be run daily/weekly to track your job search progress!
