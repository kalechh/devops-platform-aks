import requests
import random
import time
import threading
from datetime import datetime
import logging

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
    handlers=[
        logging.FileHandler("load_test.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()  # Optional: keep this for console logs too
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://hamzakalech.com/api/event"

def random_event():
    return {
        "description": "Load test event",
        "date": "2025-06-01",
        "Number_of_tickets": random.randint(10, 100),
        "additional_notes": "Simulated load",
        "place": "Online"
    }

def simulate_user():
    try:
        r1 = requests.get(f"{BASE_URL}/retrieve-all-events", timeout=5)
        all_ids = [e["idEvent"] for e in r1.json()] if r1.ok else []

        new_event = random_event()
        r2 = requests.post(f"{BASE_URL}/addevent", json=new_event, timeout=5)
        logger.info(f"POST /addevent status: {r2.status_code}")

        if all_ids:
            event_id = random.choice(all_ids)
            r3 = requests.get(f"{BASE_URL}/retrieve-event/{event_id}", timeout=5)
            logger.info(f"GET /retrieve-event/{event_id} status: {r3.status_code}")

        if all_ids and random.random() < 0.5:
            event_id = random.choice(all_ids)
            r4 = requests.delete(f"{BASE_URL}/remove-event/{event_id}", timeout=5)
            logger.info(f"DELETE /remove-event/{event_id} status: {r4.status_code}")

        logger.info("✅ User simulation complete.")

    except Exception as e:
        logger.error(f"❌ Error: {e}")

def user_session(end_time):
    while time.time() < end_time:
        simulate_user()
        time.sleep(random.uniform(1, 3))  # Simulate user think time

def run_phase(concurrent_users, duration_sec, label):
    logger.info(f"⚙️  Starting phase: {label} | Users: {concurrent_users} | Duration: {duration_sec // 60} min")
    end_time = time.time() + duration_sec
    threads = []
    for i in range(concurrent_users):
        t = threading.Thread(target=user_session, args=(end_time,), name=f"{label}-User-{i+1}")
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    logger.info(f"⏹️  Completed phase: {label}")

def orchestrate_load_test():
    logger.info("🚀 Starting structured load simulation...\n")
    run_phase(15, 1800, "Medium Load")   # 30 min
    run_phase(5, 1800, "Light Load")    # 30 min
    run_phase(30, 900, "Heavy Load")    # 15 min
    run_phase(15, 1800, "Medium Load")   # 30 min
    run_phase(5, 900, "Light Load")     # 15 min
    logger.info("\n✅ All load phases completed.")

if __name__ == "__main__":
    orchestrate_load_test()
