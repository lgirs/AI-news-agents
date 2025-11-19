# Researcher feedback loop

1. Run the Researcher agent on Mondays. It appends a feedback request entry to `data/feedback.json`.
2. Editors open that file and add structured objects to the `responses` array (or drop a standalone JSON file and pass it to `python -m agents.researcher --extra-feedback path/to/file.json`). Example:
```json
{
  "submitted_at": "2024-05-10T08:00:00+00:00",
  "source_id": "new_source",
  "action": "add",
  "payload": {
    "name": "Example AI",
    "url": "https://example.com/rss",
    "ingestion_type": "rss",
    "credibility_score": 0.7,
    "visitor_score": 0.6,
    "business_alignment": 0.8,
    "topics": ["business"],
    "cadence": "weekly"
  }
}
```
3. The next Researcher run ingests responses, updates SQLite/catalog files, and clears the queue. Use `data/feedback_samples.json` as a reference payload when demonstrating the flow or seeding additional outlets during reviews; you can rebuild the SQLite snapshot at any time with `python -m agents.storage seed --catalog data/source_catalog.json`.
4. Archive context (why add/remove) in the same payload so the Researcher log remains auditable.
