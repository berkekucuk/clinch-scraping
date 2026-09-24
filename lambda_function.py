import subprocess
import logging
from ufc_scraper.services.supabase_manager import SupabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):

    if 'task' in event:
        task_type = event.get('task')
        logger.info(f"[TASK:{task_type}] Task triggered.")

        try:
            # Scheduled polling mode: keeps upcoming-event data fresh.
            if task_type == 'upcoming':
                logger.info(f"[TASK:{task_type}] Starting scraper...")
                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=upcoming",
                    "--loglevel", "INFO"
                    ], check=True)

                logger.info(f"[TASK:{task_type}] Scraper finished.")
                return {"statusCode": 200, "body": f"Scheduled task '{task_type}' completed"}

            # Scans the event list page for new events not yet in the database.
            elif task_type == 'event_scan':
                logger.info(f"[TASK:{task_type}] Starting event scan...")
                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=event_scan",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Event scan finished.")
                return {"statusCode": 200, "body": f"Scheduled task '{task_type}' completed"}

            # Live mode: scrapes a running event repeatedly until it is completed.
            elif task_type == 'step_function_loop':
                event_url = event.get('event_url')
                event_id = event.get('event_id')
                completed_runs = event.get('completed_runs', 0)

                if not event_url or not event_id:
                    return {"statusCode": 400, "body": "Missing event_id or event_url"}

                logger.info(f"[TASK:{task_type}] Scraping live event: {event_id} (completed_runs: {completed_runs})")

                # 1. Tapology Live Card Scraper
                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=live",
                    "-a", f"event_url={event_url}",
                    "--loglevel", "INFO"
                ], check=True)

                # 2. UFCStats Live Fight Stats Scraper (3-fight sliding window)
                try:
                    subprocess.run([
                        "scrapy", "crawl", "stats",
                        "-a", "mode=live",
                        "-a", f"event_id={event_id}",
                        "--loglevel", "INFO"
                    ], check=True)
                except subprocess.CalledProcessError as e:
                    logger.warning(f"[TASK:{task_type}] Stats live scraper error: {e}")

                logger.info(f"[TASK:{task_type}] Both live scrapers finished for '{event_id}'.")

                current_status = SupabaseManager().get_event_status(event_id)

                if current_status == "completed":
                    if completed_runs < 3:
                        next_run = completed_runs + 1
                        logger.info(f"[TASK:{task_type}] Event {event_id} is COMPLETED, scheduling extra run {next_run}/3.")
                        return {"statusCode": 200, "step_status": "IN_PROGRESS", "completed_runs": next_run}
                    else:
                        logger.info(f"[TASK:{task_type}] Event {event_id} is COMPLETED and all 3 extra runs are done. Finishing loop.")
                        return {"statusCode": 200, "step_status": "COMPLETED", "completed_runs": completed_runs}
                else:
                    logger.info(f"[TASK:{task_type}] Event {event_id} is still {current_status.upper()}. Returning IN_PROGRESS.")
                    return {"statusCode": 200, "step_status": "IN_PROGRESS", "completed_runs": 0}

            # Single mode: scrapes a single event page once.
            elif task_type == 'single':
                event_url = event.get('event_url')

                if not event_url:
                    return {"statusCode": 400, "body": "Missing event_url"}

                logger.info(f"[TASK:{task_type}] Scraping event: {event_url}")

                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=single",
                    "-a", f"event_url={event_url}",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Scraper finished for '{event_url}'.")
                return {"statusCode": 200, "body": f"Scrape finished for {event_url}"}

            # Fighter detail mode: enriches a new fighter row with bio data.
            elif task_type == 'fighter_scrape':
                fighter_id = event.get('fighter_id')
                profile_url = event.get('profile_url')

                if not profile_url or not fighter_id:
                     logger.warning(f"[TASK:{task_type}] Missing profile_url or fighter_id. Skipping.")
                     return {"statusCode": 400, "body": "Missing data"}

                subprocess.run([
                    "scrapy", "crawl", "fighter",
                    "-a", f"profile_url={profile_url}",
                    "-a", f"fighter_id={fighter_id}",
                    "--loglevel", "INFO"
                ], check=True)

                return {"statusCode": 200, "body": f"Scrape finished for {fighter_id}"}

            # Ranking mode: scrapes rankings page.
            elif task_type == 'ranking':
                logger.info(f"[TASK:{task_type}] Starting ranking scraper...")
                subprocess.run([
                    "scrapy", "crawl", "ranking",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Ranking scraper finished.")
                return {"statusCode": 200, "body": f"Scheduled task '{task_type}' completed"}

            else:
                return {"statusCode": 400, "body": "Undefined task"}

        except subprocess.CalledProcessError as e:
            logger.error(f"[TASK:{task_type}] Spider failed: {str(e)}")
            raise e

    else:
        logger.warning("Unknown event structure.")
        return {"statusCode": 400, "body": "Unknown event"}
