# celery_config.py
"""
Celery Configuration for Production
"""

# Task execution settings
task_acks_late = True
task_reject_on_worker_lost = True
task_track_started = True

# Worker settings
worker_prefetch_multiplier = 1  # Process one task at a time
worker_max_tasks_per_child = 50  # Restart worker after 50 tasks (memory management)
worker_disable_rate_limits = False

# Result backend settings
result_expires = 3600  # Results expire after 1 hour
result_persistent = True

# Task routing
task_routes = {
    'scraper.*': {'queue': 'scraping'},
}

# Concurrency settings
worker_concurrency = 3  # Maximum 3 concurrent scraping jobs (adjust based on laptop resources)

# Logging
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
