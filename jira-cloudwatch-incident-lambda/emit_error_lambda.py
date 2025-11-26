import logging
import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info("healthcheck ok")
    # Simulated real-world errors for alarm testing
    logger.error(
        "payment_api_timeout: upstream timed out after 15s; order_id=12345; user_id=abc; retryable=true"
    )
    logger.error(
        "db_pool_exhausted: cannot acquire connection within 5s; pool_size=20; waiters=12; shard=orders-east"
    )
    logger.error(
        "s3_put_failed: bucket=app-uploads key=orders/12345.json err=AccessDenied"
    )
    return {"status": "done", "ts": time.time()}
