"""
Weekly report generator. Entry point for the Monday GitHub Actions cron job.
Schedule: 0 8 * * 1 (Monday 8am UTC)

Steps:
  1. Query last 7 days of job postings
  2. Compute aggregates
  3. Generate narrative via Groq
  4. Store report in weekly_reports table
  5. Send HTML email to REPORT_RECIPIENT
"""

import os
import sys
import json
import logging
from datetime import date, datetime, timedelta
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("weekly_report")

from sqlalchemy import func, text
from app.database import SessionLocal, engine
from app.jmi_models import JMIBase, JobPosting, SkillTrend, WeeklyReport

JMIBase.metadata.create_all(bind=engine)


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _prev_week_start() -> date:
    return _current_week_start() - timedelta(weeks=1)


def _build_report(db) -> dict:
    week_start = _current_week_start()
    week_end = datetime.combine(week_start + timedelta(days=7), datetime.min.time())
    week_start_dt = datetime.combine(week_start, datetime.min.time())

    jobs_this_week = db.query(JobPosting).filter(
        JobPosting.scraped_at >= week_start_dt,
        JobPosting.scraped_at < week_end,
    ).all()

    total = len(jobs_this_week)
    logger.info("Jobs this week: %d", total)

    # By role category
    role_counts = Counter(j.role_category for j in jobs_this_week if j.role_category)

    # Top hiring companies
    company_counts = Counter(j.company for j in jobs_this_week)
    top_companies = company_counts.most_common(15)

    # Top skills
    all_skills = []
    for j in jobs_this_week:
        all_skills.extend(j.skills_required or [])
    skill_counts = Counter(s.lower() for s in all_skills)
    top_skills = skill_counts.most_common(20)

    # Skill trends (this week vs last week)
    this_week_trends = {
        r.skill: r.mention_count
        for r in db.query(SkillTrend).filter(SkillTrend.week_start == week_start).all()
    }
    prev_week_trends = {
        r.skill: r.mention_count
        for r in db.query(SkillTrend).filter(SkillTrend.week_start == _prev_week_start()).all()
    }
    skill_deltas = {}
    for skill, count in this_week_trends.items():
        prev = prev_week_trends.get(skill, 0)
        if prev > 0:
            skill_deltas[skill] = round((count - prev) / prev * 100, 1)
        else:
            skill_deltas[skill] = 100.0

    rising = sorted(
        [(s, d) for s, d in skill_deltas.items() if d > 0],
        key=lambda x: x[1], reverse=True
    )[:10]
    falling = sorted(
        [(s, d) for s, d in skill_deltas.items() if d < 0],
        key=lambda x: x[1]
    )[:5]

    # Salary ranges by seniority
    salary_by_seniority: dict[str, list] = defaultdict(list)
    for j in jobs_this_week:
        if j.seniority and j.salary_min and j.salary_max:
            avg = (j.salary_min + j.salary_max) / 2
            salary_by_seniority[j.seniority].append(avg)
    salary_summary = {
        s: {
            "avg": round(sum(v) / len(v)),
            "count": len(v),
        }
        for s, v in salary_by_seniority.items() if v
    }

    # Remote vs onsite
    remote_count = sum(1 for j in jobs_this_week if j.remote)
    onsite_count = total - remote_count

    # Visa sponsoring companies
    visa_companies = list({
        j.company for j in jobs_this_week
        if j.visa_sponsorship is True
    })[:20]

    return {
        "week_start": str(week_start),
        "total_jobs": total,
        "by_role_category": dict(role_counts),
        "top_companies": [{"company": c, "count": n} for c, n in top_companies],
        "top_skills": [{"skill": s, "count": n} for s, n in top_skills],
        "skills_rising": [{"skill": s, "pct_change": d} for s, d in rising],
        "skills_falling": [{"skill": s, "pct_change": d} for s, d in falling],
        "salary_by_seniority": salary_summary,
        "remote_count": remote_count,
        "onsite_count": onsite_count,
        "visa_companies": visa_companies,
    }


def _generate_narrative(report: dict) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        top_skills = ", ".join(s["skill"] for s in report["top_skills"][:10])
        top_companies = ", ".join(c["company"] for c in report["top_companies"][:5])
        rising = ", ".join(f"{s['skill']} (+{s['pct_change']}%)" for s in report["skills_rising"][:5])

        prompt = f"""Write a concise 3-paragraph market intelligence summary for ML/DS job seekers based on this data:

Week of: {report['week_start']}
Total new jobs: {report['total_jobs']}
Top hiring companies: {top_companies}
Most in-demand skills: {top_skills}
Rising skills: {rising}
Remote: {report['remote_count']} jobs, Onsite: {report['onsite_count']} jobs

Paragraph 1: Overall market health and volume.
Paragraph 2: Key skill trends and what they signal.
Paragraph 3: Strategic advice for job seekers this week.

Write in professional but conversational tone. Be specific and data-driven."""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("Narrative generation failed: %s", e)
        return f"Unable to generate narrative this week. {report['total_jobs']} new ML/DS jobs were scraped."


def _render_html(report: dict, narrative: str) -> str:
    week = report["week_start"]
    total = report["total_jobs"]
    remote_pct = round(report["remote_count"] / max(total, 1) * 100)

    top_companies_html = "".join(
        f'<tr><td style="padding:6px 12px">{c["company"]}</td>'
        f'<td style="padding:6px 12px;text-align:right;font-weight:600">{c["count"]}</td></tr>'
        for c in report["top_companies"][:10]
    )

    top_skills_rows = ""
    for s in report["top_skills"][:15]:
        skill = s["skill"]
        count = s["count"]
        delta_info = next(
            (d for d in report["skills_rising"] + report["skills_falling"] if d["skill"] == skill),
            None
        )
        arrow = ""
        if delta_info:
            pct = delta_info["pct_change"]
            if pct > 0:
                arrow = f'<span style="color:#10b981">↑ {pct}%</span>'
            else:
                arrow = f'<span style="color:#ef4444">↓ {abs(pct)}%</span>'
        top_skills_rows += (
            f'<tr><td style="padding:6px 12px">{skill}</td>'
            f'<td style="padding:6px 12px;text-align:right">{count}</td>'
            f'<td style="padding:6px 12px;text-align:right">{arrow}</td></tr>'
        )

    narrative_html = "".join(
        f'<p style="margin:0 0 14px;line-height:1.7">{p.strip()}</p>'
        for p in narrative.split("\n\n") if p.strip()
    )

    visa_html = ""
    if report["visa_companies"]:
        visa_html = (
            '<h3 style="margin:0 0 8px;font-size:16px">Visa-Sponsoring Companies</h3>'
            '<p style="margin:0 0 20px;color:#94a3b8">'
            + ", ".join(report["visa_companies"]) + "</p>"
        )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e2e8f0">
<div style="max-width:680px;margin:0 auto;padding:24px">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f 0%,#2d1b4e 100%);border-radius:16px;padding:32px;margin-bottom:24px;text-align:center">
    <div style="font-size:13px;color:#7dd3fc;font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Job Market Intelligence</div>
    <h1 style="margin:0 0 8px;font-size:28px;font-weight:700;color:#fff">Weekly ML/DS Report</h1>
    <div style="color:#94a3b8;font-size:14px">Week of {week}</div>
  </div>

  <!-- Stats grid -->
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:24px">
    <div style="background:#1e293b;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:#38bdf8">{total}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">New Jobs</div>
    </div>
    <div style="background:#1e293b;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:#a78bfa">{len(report["top_companies"])}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Companies</div>
    </div>
    <div style="background:#1e293b;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:#34d399">{remote_pct}%</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Remote</div>
    </div>
    <div style="background:#1e293b;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:28px;font-weight:700;color:#fb923c">{len(report["top_skills"])}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">Skills Tracked</div>
    </div>
  </div>

  <!-- Narrative -->
  <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="margin:0 0 16px;font-size:18px;font-weight:600">Market Summary</h2>
    {narrative_html}
  </div>

  <!-- Top Companies -->
  <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="margin:0 0 16px;font-size:18px;font-weight:600">Top Hiring Companies</h2>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="border-bottom:1px solid #334155">
        <th style="padding:6px 12px;text-align:left;color:#64748b;font-weight:500;font-size:13px">Company</th>
        <th style="padding:6px 12px;text-align:right;color:#64748b;font-weight:500;font-size:13px">Jobs</th>
      </tr></thead>
      <tbody>{top_companies_html}</tbody>
    </table>
  </div>

  <!-- Top Skills -->
  <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="margin:0 0 16px;font-size:18px;font-weight:600">Most In-Demand Skills</h2>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="border-bottom:1px solid #334155">
        <th style="padding:6px 12px;text-align:left;color:#64748b;font-weight:500;font-size:13px">Skill</th>
        <th style="padding:6px 12px;text-align:right;color:#64748b;font-weight:500;font-size:13px">Mentions</th>
        <th style="padding:6px 12px;text-align:right;color:#64748b;font-weight:500;font-size:13px">Trend</th>
      </tr></thead>
      <tbody>{top_skills_rows}</tbody>
    </table>
  </div>

  <!-- Visa -->
  {visa_html}

  <!-- Footer -->
  <div style="text-align:center;color:#475569;font-size:12px;padding-top:16px;border-top:1px solid #1e293b">
    Powered by your own agent &bull; Built by Shiven Paudyal
  </div>
</div>
</body>
</html>"""


def run():
    logger.info("=== Weekly report generation started ===")
    db = SessionLocal()

    try:
        report = _build_report(db)
        narrative = _generate_narrative(report)
        report["narrative"] = narrative

        week_start = date.fromisoformat(report["week_start"])

        # Upsert weekly report
        existing = db.query(WeeklyReport).filter(WeeklyReport.week_start == week_start).first()
        if existing:
            existing.report_json = report
            existing.total_jobs = report["total_jobs"]
            existing.generated_at = datetime.utcnow()
        else:
            db.add(WeeklyReport(
                week_start=week_start,
                report_json=report,
                total_jobs=report["total_jobs"],
            ))

        db.flush()

        # Send email
        recipient = os.getenv("REPORT_RECIPIENT", "shivenpaudyal9@gmail.com")
        html = _render_html(report, narrative)
        subject = f"ML Job Market Intelligence — Week of {report['week_start']}"

        try:
            from mailer.sender import send_report
            send_report(to_email=recipient, subject=subject, html_content=html)

            # Update sent timestamp
            row = db.query(WeeklyReport).filter(WeeklyReport.week_start == week_start).first()
            if row:
                row.email_sent_at = datetime.utcnow()

            logger.info("Report emailed to %s", recipient)
        except Exception as e:
            logger.error("Email send failed (report still stored): %s", e)

        db.commit()
        logger.info("=== Weekly report complete ===")

    except Exception as e:
        db.rollback()
        logger.exception("Weekly report failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
