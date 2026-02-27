import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
import requests


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_action_run_link() -> str:
    explicit = os.getenv("ACTION_RUN_LINK", "").strip()
    if explicit:
        return explicit

    server_url = os.getenv("GITHUB_SERVER_URL", "").strip()
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if server_url and repository and run_id:
        return f"{server_url}/{repository}/actions/runs/{run_id}"

    raise ValueError(
        "Missing ACTION_RUN_LINK and GitHub context vars (GITHUB_SERVER_URL, "
        "GITHUB_REPOSITORY, GITHUB_RUN_ID)."
    )


def main() -> None:
    payload = {
        "action_run_link": build_action_run_link(),
        "email": required_env("EMAIL"),
        "name": required_env("NAME"),
        "repository_link": required_env("REPOSITORY_LINK"),
        "resume_link": required_env("RESUME_LINK"),
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
    }

    canonical_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    # Helpful for CI verification: this is exactly what gets signed and sent.
    print(f"CANONICAL_JSON: {canonical_json}")
    json_body = canonical_json.encode("utf-8")
    secret = os.getenv("SIGNING_SECRET", "hello-there-from-b12")
    signature = hmac.new(secret.encode("utf-8"), json_body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": f"sha256={signature}",
    }

    response = requests.post(
        "https://b12.io/apply/submission",
        data=json_body,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        result = response.json()
        receipt = result.get("receipt")
        if not receipt:
            raise ValueError(f"Successful response missing receipt: {result}")
        print(f"RECEIPT: {receipt}")
        return

    print(f"Error: {response.status_code}")
    print(response.text)
    raise SystemExit(1)


if __name__ == "__main__":
    main()