import os
import subprocess
import tempfile
import json

temp_dir = "/tmp"

def execute_python(code):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", dir=temp_dir) as f:
            f.write(code.encode())
            file_path = f.name

        result = subprocess.run(
            ["python", file_path],
            capture_output=True,
            text=True,
            timeout=30  # Increased timeout for batch
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if e.stdout else ""
        return {
            "success": False,
            "stdout": stdout,
            "stderr": "Error: Execution timed out after 30 seconds."
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Error: {str(e)}"
        }

def main():
    submissions_json = os.environ.get("SUBMISSIONS", "[]")
    submissions = json.loads(submissions_json)

    results = []
    for sub in submissions:
        language = sub.get("language", "python")
        code = sub.get("code", "")

        if language == "python":
            result = execute_python(code)
        else:
            result = {
                "success": False,
                "stdout": "",
                "stderr": "Unsupported language"
            }
        
        results.append(result)

    print(json.dumps(results))

if __name__ == "__main__":
    main()