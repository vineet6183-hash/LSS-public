"""
Azure Functions entry point for LSS Invoice Automation
Provides both scheduled and HTTP-triggered execution
"""

import azure.functions as func
import logging
import os
from datetime import datetime

# Import the main automation logic
from lss_invoice_automation import main as run_automation

app = func.FunctionApp()

logger = logging.getLogger("LSS_Automation")


@app.schedule_trigger(arg_name="myTimer", schedule="0 14 * * 1-5")
def lss_automation_timer(myTimer: func.TimerRequest) -> None:
    """
    Timer-triggered function to run LSS Invoice Automation
    Runs every weekday at 9 AM EST (14:00 UTC)
    Cron schedule: "0 14 * * 1-5" means:
    - 0: minute 0
    - 14: hour 14 UTC (9 AM EST)
    - *: every day
    - *: every month
    - 1-5: Monday through Friday
    """
    if myTimer.past_due:
        logger.info("Timer is past due!")

    try:
        logger.info(f"LSS Automation started at {datetime.utcnow()}")

        # Verify all required environment variables are set
        required_vars = [
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
            "USER_EMAIL"
        ]

        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

        # Run the automation
        run_automation()

        logger.info("LSS Automation completed successfully")

    except Exception as e:
        logger.error(f"Error running LSS Automation: {str(e)}", exc_info=True)
        raise


@app.route(route="run-lss-automation", methods=["POST"])
def lss_automation_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to manually run LSS Invoice Automation

    Usage:
        POST https://<function-app>.azurewebsites.net/api/run-lss-automation

    Returns:
        202 Accepted - if automation started successfully
        400 Bad Request - if required environment variables are missing
        500 Internal Server Error - if an error occurred
    """
    try:
        logger.info(f"Manual trigger received from {req.remote_addr}")

        # Verify all required environment variables are set
        required_vars = [
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
            "USER_EMAIL"
        ]

        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            return func.HttpResponse(error_msg, status_code=400)

        # Run the automation asynchronously
        logger.info("Starting LSS Automation via HTTP trigger")
        run_automation()

        return func.HttpResponse(
            "LSS automation completed successfully",
            status_code=200
        )

    except Exception as e:
        error_msg = f"Error running LSS Automation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return func.HttpResponse(error_msg, status_code=500)


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for monitoring

    Returns basic status information
    """
    try:
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "function_app": os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT", "unknown")
        }

        return func.HttpResponse(
            str(status),
            status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            f"Health check failed: {str(e)}",
            status_code=500
        )
