"""Generate demo_seed.json with 800 realistic ML/DS job postings."""
import json, uuid, random, sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COMPANIES = [
    {"name": "Stripe",       "domain": "stripe.com",        "url": "https://stripe.com/jobs",                        "visa": True},
    {"name": "Airbnb",       "domain": "airbnb.com",         "url": "https://careers.airbnb.com",                    "visa": True},
    {"name": "OpenAI",       "domain": "openai.com",         "url": "https://openai.com/careers",                    "visa": True},
    {"name": "Anthropic",    "domain": "anthropic.com",      "url": "https://www.anthropic.com/careers",             "visa": True},
    {"name": "Databricks",   "domain": "databricks.com",     "url": "https://www.databricks.com/company/careers",    "visa": True},
    {"name": "Snowflake",    "domain": "snowflake.com",      "url": "https://careers.snowflake.com",                 "visa": True},
    {"name": "Meta",         "domain": "meta.com",           "url": "https://www.metacareers.com",                   "visa": True},
    {"name": "Google",       "domain": "google.com",         "url": "https://careers.google.com",                   "visa": True},
    {"name": "Amazon",       "domain": "amazon.com",         "url": "https://www.amazon.jobs",                      "visa": True},
    {"name": "Microsoft",    "domain": "microsoft.com",      "url": "https://careers.microsoft.com",                "visa": True},
    {"name": "Netflix",      "domain": "netflix.com",        "url": "https://jobs.netflix.com",                     "visa": False},
    {"name": "Uber",         "domain": "uber.com",           "url": "https://www.uber.com/us/en/careers",           "visa": True},
    {"name": "Pinterest",    "domain": "pinterest.com",      "url": "https://www.pinterestcareers.com",             "visa": True},
    {"name": "Roblox",       "domain": "roblox.com",         "url": "https://careers.roblox.com",                   "visa": True},
    {"name": "Discord",      "domain": "discord.com",        "url": "https://discord.com/jobs",                     "visa": True},
    {"name": "Figma",        "domain": "figma.com",          "url": "https://www.figma.com/careers",               "visa": True},
    {"name": "Coinbase",     "domain": "coinbase.com",       "url": "https://www.coinbase.com/careers",             "visa": True},
    {"name": "Instacart",    "domain": "instacart.com",      "url": "https://instacart.careers",                    "visa": True},
    {"name": "DoorDash",     "domain": "doordash.com",       "url": "https://careers.doordash.com",                 "visa": True},
    {"name": "Dropbox",      "domain": "dropbox.com",        "url": "https://jobs.dropbox.com",                    "visa": True},
    {"name": "Palantir",     "domain": "palantir.com",       "url": "https://www.palantir.com/careers",             "visa": True},
    {"name": "Scale AI",     "domain": "scale.com",          "url": "https://scale.com/careers",                   "visa": True},
    {"name": "Hugging Face", "domain": "huggingface.co",     "url": "https://apply.workable.com/hugging-face",      "visa": True},
    {"name": "Datadog",      "domain": "datadoghq.com",      "url": "https://www.datadoghq.com/careers",           "visa": True},
    {"name": "MongoDB",      "domain": "mongodb.com",        "url": "https://www.mongodb.com/careers",             "visa": True},
    {"name": "Cloudflare",   "domain": "cloudflare.com",     "url": "https://www.cloudflare.com/careers",          "visa": True},
    {"name": "Twilio",       "domain": "twilio.com",         "url": "https://www.twilio.com/en-us/company/jobs",   "visa": True},
    {"name": "Robinhood",    "domain": "robinhood.com",      "url": "https://careers.robinhood.com",               "visa": False},
    {"name": "Brex",         "domain": "brex.com",           "url": "https://www.brex.com/careers",                "visa": True},
    {"name": "Ramp",         "domain": "ramp.com",           "url": "https://ramp.com/careers",                    "visa": True},
    {"name": "Plaid",        "domain": "plaid.com",          "url": "https://plaid.com/careers",                   "visa": True},
    {"name": "Rippling",     "domain": "rippling.com",       "url": "https://www.rippling.com/careers",            "visa": True},
    {"name": "Notion",       "domain": "notion.so",          "url": "https://www.notion.so/careers",               "visa": True},
    {"name": "Duolingo",     "domain": "duolingo.com",       "url": "https://careers.duolingo.com",                "visa": True},
    {"name": "Samsara",      "domain": "samsara.com",        "url": "https://www.samsara.com/company/careers",     "visa": True},
    {"name": "Asana",        "domain": "asana.com",          "url": "https://asana.com/jobs",                      "visa": True},
    {"name": "Carta",        "domain": "carta.com",          "url": "https://carta.com/careers",                   "visa": True},
    {"name": "Gusto",        "domain": "gusto.com",          "url": "https://gusto.com/about/careers",             "visa": False},
    {"name": "Atlassian",    "domain": "atlassian.com",      "url": "https://www.atlassian.com/company/careers",   "visa": True},
    {"name": "Airtable",     "domain": "airtable.com",       "url": "https://airtable.com/careers",               "visa": True},
]

ROLE_CONFIGS = {
    "ml_engineer": {
        "titles": [
            "Machine Learning Engineer", "Senior ML Engineer", "Staff ML Engineer",
            "Principal ML Engineer", "ML Engineer II", "ML Platform Engineer",
            "Applied ML Engineer", "ML Infrastructure Engineer",
            "Senior Machine Learning Engineer", "ML Engineer, Recommendations",
            "Machine Learning Engineer, NLP", "ML Engineer, Search",
        ],
        "skills": [
            (["Python", "PyTorch", "TensorFlow", "SQL", "AWS"], ["Kubernetes", "Spark"]),
            (["Python", "PyTorch", "Kubernetes", "MLflow", "Docker"], ["Ray", "Triton"]),
            (["Python", "TensorFlow", "Spark", "GCP", "Airflow"], ["Scala", "BigQuery"]),
            (["Python", "PyTorch", "Ray", "CUDA", "Linux"], ["C++", "ONNX"]),
            (["Python", "Transformers", "LLMs", "RAG", "FastAPI"], ["LangChain", "Pinecone"]),
            (["Python", "PyTorch", "Embeddings", "Vector DBs", "AWS"], ["FAISS", "Weaviate"]),
        ],
    },
    "data_scientist": {
        "titles": [
            "Data Scientist", "Senior Data Scientist", "Staff Data Scientist",
            "Principal Data Scientist", "Data Scientist II", "Applied Data Scientist",
            "Research Data Scientist", "Data Science Manager",
            "Data Scientist, Growth", "Data Scientist, Trust",
            "Senior Data Scientist, Product Analytics",
        ],
        "skills": [
            (["Python", "SQL", "R", "Pandas", "Scikit-learn"], ["Tableau", "Spark"]),
            (["Python", "SQL", "Statistics", "A/B Testing", "Tableau"], ["R", "Looker"]),
            (["Python", "SQL", "Spark", "Databricks", "dbt"], ["Airflow", "BigQuery"]),
            (["Python", "SQL", "Causal Inference", "Experimentation", "Statsmodels"], ["R", "Stan"]),
            (["Python", "SQL", "NLP", "LLMs", "Hugging Face"], ["PyTorch", "Transformers"]),
        ],
    },
    "mlops": {
        "titles": [
            "MLOps Engineer", "ML Platform Engineer", "Senior MLOps Engineer",
            "ML Infrastructure Engineer", "Staff MLOps Engineer",
            "ML DevOps Engineer", "Platform Engineer, ML", "ML Reliability Engineer",
        ],
        "skills": [
            (["Python", "Kubernetes", "Docker", "Terraform", "AWS"], ["Helm", "ArgoCD"]),
            (["Python", "Kubeflow", "Airflow", "MLflow", "GCP"], ["Seldon", "KServe"]),
            (["Python", "Spark", "Kafka", "Flink", "Azure"], ["Databricks", "Delta Lake"]),
            (["Python", "Ray", "Prometheus", "Grafana", "Linux"], ["eBPF", "Rust"]),
        ],
    },
    "analytics": {
        "titles": [
            "Analytics Engineer", "Senior Analytics Engineer", "Data Analyst",
            "Senior Data Analyst", "Business Intelligence Engineer",
            "Staff Analytics Engineer", "Growth Analyst",
            "Analytics Engineer, Marketing", "Data Analyst, Product",
        ],
        "skills": [
            (["SQL", "Python", "dbt", "Looker", "Tableau"], ["Airflow", "Spark"]),
            (["SQL", "Python", "Snowflake", "dbt", "Airflow"], ["Fivetran", "Sigma"]),
            (["SQL", "Python", "BigQuery", "Looker", "Fivetran"], ["dbt", "Mode"]),
            (["SQL", "Python", "Redshift", "Mode", "Excel"], ["PowerBI", "Chartio"]),
        ],
    },
    "applied_scientist": {
        "titles": [
            "Applied Scientist", "Senior Applied Scientist", "Research Scientist",
            "Applied Research Scientist", "Staff Applied Scientist",
            "Applied AI Scientist", "Applied Scientist, NLP",
            "Applied Scientist, Computer Vision",
        ],
        "skills": [
            (["Python", "PyTorch", "NLP", "Transformers", "Statistics"], ["TensorFlow", "JAX"]),
            (["Python", "PyTorch", "Computer Vision", "CUDA", "C++"], ["OpenCV", "TensorRT"]),
            (["Python", "JAX", "Reinforcement Learning", "Mathematics"], ["C++", "CUDA"]),
            (["Python", "PyTorch", "LLMs", "RLHF", "Evaluation"], ["Transformers", "vLLM"]),
        ],
    },
    "research": {
        "titles": [
            "Research Engineer", "Research Scientist", "Senior Research Scientist",
            "ML Research Engineer", "AI Research Scientist",
            "Fundamental Research Scientist", "Research Engineer, RL",
        ],
        "skills": [
            (["Python", "PyTorch", "Research", "Statistics", "Mathematics"], ["JAX", "C++"]),
            (["Python", "JAX", "Deep Learning", "Mathematics", "C++"], ["CUDA", "Triton"]),
            (["Python", "PyTorch", "NLP", "LLMs", "PhD"], ["Transformers", "vLLM"]),
        ],
    },
}

SENIORITY_MAP = {
    "intern": (80000, 130000), "junior": (115000, 165000),
    "mid": (155000, 225000),   "senior": (185000, 310000),
    "staff": (245000, 390000), "principal": (290000, 430000),
}

LOCATIONS = [
    "San Francisco, CA", "San Francisco, CA", "New York, NY", "New York, NY",
    "Seattle, WA", "Austin, TX", "Boston, MA", "Los Angeles, CA",
    "Chicago, IL", "Denver, CO", "Atlanta, GA", "San Jose, CA",
    "Remote", "Remote", "Remote", "Remote",
    "Hybrid - San Francisco, CA", "Hybrid - New York, NY", "Hybrid - Seattle, WA",
]

def infer_seniority(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["intern", "phd intern", "new grad"]): return "intern"
    if "principal" in t or "distinguished" in t: return "principal"
    if "staff" in t: return "staff"
    if any(x in t for x in ["senior", "sr.", "sr "]): return "senior"
    if any(x in t for x in [" ii", " iii", " 2"]): return "mid"
    if any(x in t for x in ["junior", "jr.", "entry"]): return "junior"
    return random.choice(["mid", "mid", "senior"])

def generate(n: int = 800, seed: int = 42) -> list:
    random.seed(seed)
    now = datetime(2026, 4, 20)
    jobs = []

    for _ in range(n):
        company = random.choice(COMPANIES)
        role_cat = random.choice(list(ROLE_CONFIGS.keys()))
        cfg = ROLE_CONFIGS[role_cat]
        title = random.choice(cfg["titles"])
        seniority = infer_seniority(title)
        location = random.choice(LOCATIONS)
        remote = "Remote" in location

        req, nice = random.choice(cfg["skills"])

        sal_range = SENIORITY_MAP.get(seniority, (155000, 225000))
        show_salary = random.random() > 0.4
        if show_salary:
            sal_min = random.randint(sal_range[0], int(sal_range[0] + (sal_range[1] - sal_range[0]) * 0.5))
            sal_max = sal_min + random.randint(25000, 75000)
        else:
            sal_min = sal_max = None

        days_ago = random.randint(1, 58)
        posted = now - timedelta(days=days_ago)
        scraped = posted + timedelta(hours=random.randint(2, 50))

        if company["visa"]:
            visa = True if random.random() > 0.15 else random.choice([True, None])
        else:
            visa = False if random.random() > 0.3 else None

        jobs.append({
            "id": f"demo-{str(uuid.uuid4())[:8]}",
            "source": "demo",
            "source_url": company["url"],
            "company": company["name"],
            "title": title,
            "location": location,
            "remote": remote,
            "description_raw": (
                f"{title} at {company['name']}. We are looking for someone with strong experience in "
                f"{', '.join(req[:3])}. You will work on cutting-edge ML systems at scale."
            ),
            "skills_required": list(req),
            "skills_nice_to_have": list(nice),
            "seniority": seniority,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": "USD",
            "visa_sponsorship": visa,
            "scraped_at": scraped.isoformat(),
            "posted_at": posted.isoformat(),
            "role_category": role_cat,
            "is_demo": True,
        })

    return jobs


if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_seed.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    jobs = generate(800)
    with open(out_path, "w") as f:
        json.dump(jobs, f, separators=(",", ":"))
    print(f"Generated {len(jobs)} demo jobs -> {out_path}")
