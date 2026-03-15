from flask import Blueprint, request, jsonify, current_app
from app.services.submission_service import create_submission, get_submission, process_pending_batches

submission_bp = Blueprint("submission", __name__)

@submission_bp.route("/submissions", methods=["POST"])
def submit_code():
    current_app.logger.info("Received POST request to /submissions")
    data = request.json
    current_app.logger.debug(f"Request data: {data}")

    language = data.get("language")
    code = data.get("code")

    if not language or not code:
        current_app.logger.warning("Missing language or code in request")
        return jsonify({"error": "Language and code are required"}), 400

    try:
        current_app.logger.info("Calling create_submission")
        submission = create_submission(language, code)
        current_app.logger.info(f"Submission created with ID: {submission.id}, status: {submission.status}")
    except Exception as e:
        current_app.logger.error(f"Error in create_submission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({
        "submission_id": submission.id,
        "status": submission.status
    }), 201

@submission_bp.route("/submissions/<int:submission_id>", methods=["GET"])
def get_status(submission_id):
    current_app.logger.info(f"Received GET request for submission_id: {submission_id}")
    submission = get_submission(submission_id)

    if not submission:
        current_app.logger.warning(f"Submission {submission_id} not found")
        return jsonify({"error": "Not found"}), 404

    current_app.logger.info(f"Returning submission {submission_id} with status: {submission.status}")
    return jsonify({
        "id": submission.id,
        "status": submission.status,
        "output": submission.output,
        "error": submission.error
    })

@submission_bp.route("/process-batches", methods=["POST"])
def process_batches():
    current_app.logger.info("Received POST request to /process-batches")
    try:
        process_pending_batches()
        current_app.logger.info("Batch processing completed")
        return jsonify({"message": "Batch processing initiated"}), 200
    except Exception as e:
        current_app.logger.error(f"Error in process_pending_batches: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500