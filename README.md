# Clinch Scraping Project

A hobby project that scrapes UFC/MMA data for clinch-app and stores it in Supabase. Built with Scrapy and deployed serverlessly on AWS Lambda.

## ⚠️ Ethical Disclaimer

**This project is purely a hobby project and has no commercial purpose.**

It is configured to place minimal load on servers by using appropriate delays, limiting concurrent requests, and running infrequently via scheduled triggers.

---

## Architecture Overview

All triggers are fully automated. An EventBridge cron rule, the Event Date Gatekeeper Lambda invoked by the Supabase events webhook, and the fighter webhook feed into the **AWS Step Functions** state machine, which dispatches to Lambda based on the `task` field.

```
  ┌───────────────────────┐    ┌──────────────────────────────┐     ┌────────────────────────┐
  │   AWS EventBridge     │    │ AWS Lambda: Event Gatekeeper │     │  Supabase DB Webhook   │
  │   (every X hours)     │    │ (Supabase DB webhook)        │     │  (new fighter row      │
  │                       │    │ (insert or datetime update)  │     │   inserted)            │
  └──────────┬────────────┘    └─────────────┬────────────────┘     └────────────┬───────────┘
        task: upcoming             task: step_function_loop            task: fighter_scrape
             │                               │                                   │
             └───────────────────────────────┴───────────────────────────────────┘
                                             │
                                             ▼
                               ┌────────────────────────┐
                               │    AWS Step Functions  │
                               │    DetermineTaskType   │
                               │      (Choice State)    │
                               └──────┬────────┬─────┬──┘
                                      │        │     │
                       ───────────────┘        │     └───────────────
                       │                       │                     │
                       ▼                       ▼                     ▼
          ┌────────────────────┐  ┌─────────────────────────┐  ┌───────────────────┐
          │ RunUpcomingScraper │  │   WaitUntilEventStart   │  │ RunFighterScraper │
          │                    │  │  (waits for event time) │  │                   │
          └─────────┬──────────┘  └───────────┬─────────────┘  └─────────┬─────────┘
                    │                         │                          │
                    ▼                         ▼                          ▼
                ✅ Done            ┌───────────────────────┐           ✅ Done
                                   │    RunLiveScraper     │
                                   │                       │◄──────────────┐
                                   └──────────┬────────────┘               │
                                              │                            │
                                              ▼                            │
                                     ┌──────────────────┐                  │
                                     │ CheckIfCompleted │                  │
                                     └──────┬──────┬────┘                  │
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
Runs every X hours with database-driven polling:
- Once per day, it scrapes the data provider event list and schedules full-page scrapes only for events not already in the database.
- At every other run, it skips the event-list request and refreshes the four least recently updated events whose status is `Upcoming`.

This keeps upcoming-event data fresh while reducing requests to data provider.

### 2. Live Mode (`step_function_loop`)
When a new event is inserted or its `datetime_utc` value changes, Supabase sends a webhook to the Event Date Gatekeeper Lambda. The Lambda starts a Step Functions execution with the `step_function_loop` payload. The state machine waits until the scheduled start time, then invokes Lambda in live mode at intervals determined by jitter until the event status changes to `completed`.

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
| Scraping Framework | Scrapy |
| Database | Supabase (PostgreSQL) |
| Deployment | Docker + AWS Lambda |
| Orchestration | AWS Step Functions + EventBridge |
| CI/CD | GitHub Actions |
