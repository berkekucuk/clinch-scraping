# Clinch Scraping Project

A hobby project that scrapes UFC/MMA data for clinch-app and stores it in Supabase. Built with Scrapy and deployed serverlessly on AWS Lambda.

## ⚠️ Ethical Disclaimer

**This project is purely a hobby project and has no commercial purpose.**

It is configured to place minimal load on servers by using appropriate delays, limiting concurrent requests, and running infrequently via scheduled triggers.

---

## Architecture Overview

All triggers are fully automated. Two Supabase webhooks and one EventBridge cron rule all feed into the same **AWS Step Functions** state machine, which dispatches to Lambda based on the `task` field.

```
  ┌──────────────────────┐   ┌──────────────────────────────┐   ┌────────────────────────┐
  │    AWS EventBridge    │   │     Supabase DB Webhook      │   │  Supabase DB Webhook   │
  │   (every 3 hours)     │   │  (new event row inserted OR  │   │  (new fighter row      │
  │                       │   │   datetime_utc field changed) │   │   inserted)            │
  └──────────┬────────────┘   └──────────────┬───────────────┘   └────────────┬───────────┘
  task: upcoming              task: step_function_loop             task: fighter_scrape
             │                              │                                  │
             └──────────────────────────────┴──────────────────────────────────┘
                                            │
                                            ▼
                               ┌────────────────────────┐
                               │    AWS Step Functions   │
                               │    DetermineTaskType    │
                               │      (Choice State)     │
                               └──────┬────────┬─────┬──┘
                                      │        │     │
                       ───────────────┘        │     └───────────────
                       │                       │                     │
                       ▼                       ▼                     ▼
          ┌────────────────────┐  ┌─────────────────────────┐  ┌──────────────────┐
          │  RunUpcomingScraper│  │   WaitUntilEventStart    │  │ RunFighterScraper│
          │  (Lambda: upcoming)│  │  (waits for event time)  │  │ (Lambda: fighter)│
          └─────────┬──────────┘  └───────────┬─────────────┘  └────────┬─────────┘
                    │                         │                          │
                    ▼                         ▼                          ▼
                ✅ Done             ┌──────────────────────┐         ✅ Done
                                   │    RunLiveScraper     │
                                   │  (Lambda: live loop)  │◄──────────────┐
                                   └──────────┬────────────┘               │
                                              │                            │
                                              ▼                            │
                                     ┌─────────────────┐                   │
                                     │ CheckIfCompleted │                   │
                                     └──────┬──────┬───┘                   │
                                            │      │                       │
                                   COMPLETED│      │IN_PROGRESS            │
                                            │      ▼                       │
                                            │  WaitForRandomSeconds        │
                                            │   (90–150s jitter)  ─────────┘
                                            ▼
                                        ✅ Done
```

---

## Scraping Flow

### 1. Scheduled Mode (`upcoming`)
Runs every 3 hours. Uses a **Hybrid Quota** — scrapes at most 6 event pages per run:
- **New events** (not in DB) are prioritized first.
- **Oldest-updated upcoming events** fill the remaining quota.

This rotation ensures all upcoming events are eventually refreshed without hammering Cloudflare.

```
Tapology Event List Page
        │
        ▼ (parse up to 6 events)
┌───────────────────┐
│  SmartSpider      │  ──→  EventPageParser  ──→  DatabasePipeline  ──→  Supabase
│  (upcoming mode)  │         (per fight)           (bulk upsert)
└───────────────────┘
  Events  │  Fights  │  Fighters  │  Participations
```

### 2. Live Mode (`step_function_loop`)
Triggered when a live event is detected. AWS Step Functions polls Lambda every ~2 minutes until the event status changes to `completed`.

### 3. Fighter Detail Mode (`fighter_scrape`)
Triggered by a **Supabase database webhook** whenever a new fighter row is inserted. Scrapes the fighter's profile page to enrich the record with bio data (nationality, height, weight, etc.).

---

## Anti-Bot Strategy

The project uses several techniques to minimize detection:

| Technique | How |
|---|---|
| **TLS/HTTP2 Fingerprinting** | `scrapy-impersonate` mimics real browser handshakes via `curl_cffi` |
| **Random Browser Rotation** | `RandomBrowserMiddleware` picks a different browser profile on every retry |
| **Conservative Rate** | `CONCURRENT_REQUESTS=1`, `DOWNLOAD_DELAY=2s` |
| **Retry Resilience** | `RETRY_TIMES=8` — retries with a new fingerprint on every 403 |
| **Jitter** | Step Function wait time is randomized (90–150s) to avoid clock-pattern detection |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Scraping Framework | Scrapy + scrapy-impersonate |
| Database | Supabase (PostgreSQL) |
| Deployment | Docker + AWS Lambda |
| Orchestration | AWS Step Functions + EventBridge |
| CI/CD | GitHub Actions |
