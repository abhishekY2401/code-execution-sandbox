"""Deprecated runner.

This file was previously used to execute a single submission.
The system now uses `batch_run_code.py` for both single and batched execution.
"""

raise SystemExit("run_code.py is deprecated. Use batch_run_code.py instead.")

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
            timeout=10
        )

        return result.stdout, result.stderr
    
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if e.stdout else ""
        return stdout, "Error: Execution timed out after 10 seconds."


def main():

    code = os.environ["CODE"]
    language = os.environ["LANGUAGE"]

    if language == "python":
        stdout, stderr = execute_python(code)
    else:
        stdout = ""
        stderr = "Unsupported language"

    result = {
        "stdout": stdout,
        "stderr": stderr
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()