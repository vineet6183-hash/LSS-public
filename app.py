"""
WSGI application for Azure App Service
Provides HTTP endpoints for LSS Invoice Automation
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, request

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the main automation logic
from lss_invoice_automation import main as run_automation

app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("LSS Invoice Automation Flask app initialized")


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        "app": "LSS Invoice Automation",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "health": {
                "url": "/api/health",
                "method": "GET",
                "description": "Health check endpoint"
            },
            "run_automation": {
                "url": "/api/run-lss-automation",
                "method": "POST",
                "description": "Manually trigger LSS automation"
            }
        }
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "app": "LSS Invoice Automation",
            "environment": os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT", "App Service")
        }
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route('/api/run-lss-automation', methods=['POST'])
def run_lss_automation():
    """
    Manual trigger for LSS Invoice Automation

    Returns:
        200: Success
        400: Missing environment variables
        500: Error running automation
    """
    try:
        logger.info(f"Manual trigger received from {request.remote_addr}")

        # Verify all required environment variables
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
            return jsonify({"error": error_msg}), 400

        # Run the automation
        logger.info("Starting LSS Automation...")
        run_automation()

        return jsonify({
            "status": "success",
            "message": "LSS automation completed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        error_msg = f"Error running LSS Automation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": error_msg}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Get application status and configuration"""
    try:
        env_status = {
            "AZURE_TENANT_ID": "✓" if os.environ.get("AZURE_TENANT_ID") else "✗",
            "AZURE_CLIENT_ID": "✓" if os.environ.get("AZURE_CLIENT_ID") else "✗",
            "AZURE_CLIENT_SECRET": "✓" if os.environ.get("AZURE_CLIENT_SECRET") else "✗",
            "USER_EMAIL": "✓" if os.environ.get("USER_EMAIL") else "✗",
            "OUTPUT_EMAIL": "✓" if os.environ.get("OUTPUT_EMAIL") else "✗"
        }

        return jsonify({
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "environment_configured": env_status,
            "all_configured": all(v == "✓" for v in env_status.values())
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not found",
        "message": "Use GET / for API documentation"
    }), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(error)}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
