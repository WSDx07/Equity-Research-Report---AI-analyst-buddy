# Research analyst

This CrewAI agent follows the qualitative Research Analyst role in Francis and Zhang, *Can AI match professional analysts? Evidence from a multi-agent system*, 2026, pp. 3–4. It covers the business model, competition, catalysts, developments, and risks. The paper describes web search and SEC filing tools. This first version instead analyzes source text you provide; it does not search or fetch filings. It is a standalone agent and does not replace the existing research workflow.

Create a UTF-8 JSON input file using this shape. Replace the example values with real, dated source text:

```json
{
  "company": "Example Inc.",
  "ticker": "EXAMPLE",
  "analysis_date": "2026-11-03",
  "sources": [
    {
      "id": "filing-1",
      "title": "Example annual report",
      "url": "https://example.com/annual-report",
      "published": "2026-02-01",
      "text": "Paste the relevant source text here."
    }
  ]
}
```

Set `OPENAI_API_KEY` in the workspace `.env` or your environment. The default model is `openai/gpt-4.1-mini`; set `RESEARCH_ANALYST_MODEL` to another OpenAI model if desired. Then run:

```powershell
.\.venv\Scripts\python.exe research_analyst.py sources.json --output research_brief.json
```

If omitted, the analysis date defaults to the local current date. Sources dated after it are rejected. Each finding must identify a supplied source and quote text found in that source; a failure stops the run without writing the brief. These checks do not prove that a quote supports the claim, that its date or URL is correct, or that the evidence is complete. Review the brief and its sources. Model calls may incur provider charges.
