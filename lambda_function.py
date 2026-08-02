import subprocess
import logging
import random
from ufc_scraper.services.supabase_manager import SupabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):

    if 'task' in event:
        task_type = event.get('task')
        logger.info(f"[TASK:{task_type}] Task triggered.")

        try:
            if task_type == 'upcoming':
                logger.info(f"[TASK:{task_type}] Starting scraper...")
                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=upcoming",
                    "--loglevel", "INFO"
                    ], check=True)

                logger.info(f"[TASK:{task_type}] Scraper finished.")
                return {"statusCode": 200, "body": f"Scheduled task '{task_type}' completed"}

            elif task_type == 'event_scan':
                logger.info(f"[TASK:{task_type}] Starting event scan...")
                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=event_scan",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Event scan finished.")
                return {"statusCode": 200, "body": f"Scheduled task '{task_type}' completed"}

            elif task_type == 'step_function_loop':
                event_url = event.get('event_url')
                event_id = event.get('event_id')

                if not event_url or not event_id:
                    return {"statusCode": 400, "body": "Missing event_id or event_url"}

                logger.info(f"[TASK:{task_type}] Scraping live event: {event_id}")

                subprocess.run([
                    "scrapy", "crawl", "smart",
                    "-a", "mode=live",
                    "-a", f"event_url={event_url}",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Scraper finished for '{event_id}'.")

                current_status = SupabaseManager().get_event_status(event_id)

                if current_status == "completed":
                    logger.info(f"[TASK:{task_type}] Event {event_id} is COMPLETED.")
                    return {"statusCode": 200, "step_status": "COMPLETED", "wait_seconds": 0}
                else:
                    wait_time = random.randint(90, 150)
                    logger.info(f"[TASK:{task_type}] Event {event_id} is still {current_status.upper()}. Returning IN_PROGRESS with jitter: {wait_time}s.")
                    return {"statusCode": 200, "step_status": "IN_PROGRESS", "wait_seconds": wait_time}

            elif task_type == 'fighter_scrape':
                fighter_id = event.get('fighter_id')
                profile_url = event.get('profile_url')

                if not profile_url or not fighter_id:
                     logger.warning(f"[TASK:{task_type}] Missing profile_url or fighter_id. Skipping.")
                     return {"statusCode": 400, "body": "Missing data"}

                logger.info(f"[TASK:{task_type}] Scraping fighter: {fighter_id} from {profile_url}")

                subprocess.run([
                    "scrapy", "crawl", "fighter",
                    "-a", f"profile_url={profile_url}",
                    "-a", f"fighter_id={fighter_id}",
                    "--loglevel", "INFO"
                ], check=True)

                logger.info(f"[TASK:{task_type}] Scrape finished for fighter {fighter_id}.")
                return {"statusCode": 200, "body": f"Scrape finished for {fighter_id}"}

            else:
                return {"statusCode": 400, "body": "Undefined task"}

        except subprocess.CalledProcessError as e:
            logger.error(f"[TASK:{task_type}] Spider failed: {str(e)}")
            raise e

    else:
        logger.warning("Unknown event structure.")
        return {"statusCode": 400, "body": "Unknown event"}
