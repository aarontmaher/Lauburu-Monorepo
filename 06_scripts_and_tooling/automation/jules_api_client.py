#!/usr/bin/env python3
"""
Google Jules API Sovereign Integration & LoRA Distillation Engine.

Integrates with the Google Jules API (https://jules.googleapis.com/v1alpha) to:
1. List and inspect repository sources connected to Jules.
2. Create, monitor, and interact with asynchronous coding sessions (tasks, plans, approvals, messages).
3. Harvest trajectories, execution activities, and generated git diffs.
4. Distill teacher-student training pairs into continuous LoRA datasets
   (continuous_lora_dataset.jsonl & ide_distillation_traces.jsonl)
   governed by Screen Lens Sovereign and Zero-Mock Truth Invariants (Rule 1).
"""

import os
import sys
import json
import time
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

JULES_API_BASE = "https://jules.googleapis.com/v1alpha"
LORA_DATASET_PATH = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
IDE_TRACES_PATH = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/ide_distillation_traces.jsonl")
GCLOUD_BIN = "/Users/aaron/google-cloud-sdk/bin/gcloud"
DEFAULT_USER_PROJECT = "lauburu-net-cloud"


class JulesAuth:
    """Manages credentials for Jules API with zero-mock token resolution."""

    @staticmethod
    def _find_env_key(key_name: str) -> Optional[str]:
        val = os.environ.get(key_name)
        if val:
            return val.strip()

        env_files = [
            Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/.env"),
            Path.home() / ".env",
            Path.home() / ".config" / "jules" / "token",
        ]
        for env_path in env_files:
            if env_path.exists():
                try:
                    for line in env_path.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() == key_name and v.strip():
                                return v.strip().strip("\"'")
                except Exception:
                    pass
        return None

    @classmethod
    def get_oauth_token(cls) -> Optional[str]:
        # Check explicit token env
        token = os.environ.get("JULES_OAUTH_TOKEN")
        if token:
            return token.strip()

        # Check gcloud print-access-token if available
        if os.path.exists(GCLOUD_BIN):
            try:
                proc = subprocess.run(
                    [GCLOUD_BIN, "auth", "print-access-token"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip()
            except Exception:
                pass
        return None

    @classmethod
    def get_headers(cls) -> Tuple[Dict[str, str], str]:
        """
        Returns (headers_dict, auth_type_description).
        Supports:
        1. JULES_API_KEY (direct API key via x-goog-api-key)
        2. OAuth2 Bearer token (via Authorization: Bearer <token> with X-Goog-User-Project)
        3. GEMINI_API_KEY fallback
        """
        jules_key = cls._find_env_key("JULES_API_KEY")
        if jules_key:
            return {
                "x-goog-api-key": jules_key,
                "Content-Type": "application/json",
            }, "API_KEY (x-goog-api-key)"

        oauth_token = cls.get_oauth_token()
        if oauth_token:
            return {
                "Authorization": f"Bearer {oauth_token}",
                "X-Goog-User-Project": DEFAULT_USER_PROJECT,
                "Content-Type": "application/json",
            }, "OAUTH2 (Bearer token + user project)"

        gemini_key = cls._find_env_key("GEMINI_API_KEY") or cls._find_env_key("GOOGLE_API_KEY")
        if gemini_key:
            return {
                "x-goog-api-key": gemini_key,
                "Content-Type": "application/json",
            }, "GEMINI_API_KEY_FALLBACK"

        return {"Content-Type": "application/json"}, "UNAUTHENTICATED"


class JulesClient:
    """Client for Google Jules v1alpha API."""

    def __init__(self):
        self.headers, self.auth_mode = JulesAuth.get_headers()

    def _request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{JULES_API_BASE}/{endpoint.lstrip('/')}"
        encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=encoded_data, headers=self.headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {"status": resp.status}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {"error": err_body}
            return {
                "error": True,
                "status_code": e.code,
                "reason": e.reason,
                "details": err_json,
                "url": url,
            }
        except Exception as e:
            return {
                "error": True,
                "status_code": -1,
                "reason": str(e),
                "url": url,
            }

    def list_sources(self, page_size: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        endpoint = f"sources?pageSize={page_size}"
        if page_token:
            endpoint += f"&pageToken={page_token}"
        return self._request(endpoint)

    def get_source(self, source_name: str) -> Dict[str, Any]:
        clean_name = source_name.lstrip("/")
        return self._request(clean_name)

    def list_sessions(self, page_size: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        endpoint = f"sessions?pageSize={page_size}"
        if page_token:
            endpoint += f"&pageToken={page_token}"
        return self._request(endpoint)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        clean_id = session_id.split("/")[-1]
        return self._request(f"sessions/{clean_id}")

    def create_session(
        self,
        prompt: str,
        source: str,
        starting_branch: str = "main",
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "sourceContext": {
                "source": source if source.startswith("sources/") else f"sources/{source}",
                "githubRepoContext": {
                    "startingBranch": starting_branch,
                },
            },
        }
        if title:
            payload["title"] = title
        return self._request("sessions", method="POST", data=payload)

    def approve_plan(self, session_id: str) -> Dict[str, Any]:
        clean_id = session_id.split("/")[-1]
        return self._request(f"sessions/{clean_id}:approvePlan", method="POST", data={})

    def send_message(self, session_id: str, prompt: str) -> Dict[str, Any]:
        clean_id = session_id.split("/")[-1]
        payload = {"prompt": prompt}
        return self._request(f"sessions/{clean_id}:sendMessage", method="POST", data=payload)

    def list_activities(self, session_id: str, page_size: int = 100) -> Dict[str, Any]:
        clean_id = session_id.split("/")[-1]
        return self._request(f"sessions/{clean_id}/activities?pageSize={page_size}")

    def distill_session_to_lora(self, session_id: str, append_to_lora: bool = True) -> List[Dict[str, Any]]:
        """
        Extracts trajectories, planning logic, and generated diffs from Jules activities
        and transforms them into high-quality Unsloth/QLoRA Instruction/Input/Output pairs.
        """
        session = self.get_session(session_id)
        if session.get("error"):
            print(f"[!] Cannot distill session: {session.get('reason')}")
            return []

        activities_resp = self.list_activities(session_id)
        activities = activities_resp.get("activities", [])

        training_pairs: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        session_title = session.get("title", "Jules Autonomous Session")
        session_prompt = session.get("prompt", "")
        source_name = session.get("sourceContext", {}).get("source", "unknown_source")

        for act in activities:
            act_id = act.get("name", "unknown_act")
            create_time = act.get("createTime", now_iso)
            desc = act.get("description", "")
            artifacts = act.get("artifacts", [])
            plan = act.get("planGenerated", {}).get("plan", "")
            agent_msg = act.get("agentMessage", {}).get("message", "")

            # If there is a plan or artifact or agent message, formulate a training record
            if plan or artifacts or agent_msg or desc:
                instruction = f"Execute autonomous coding task for repository {source_name}: {session_title}"
                input_context = f"User Request: {session_prompt}\nCurrent Plan & Step: {desc or plan}"
                
                output_content = ""
                if plan:
                    output_content += f"### Execution Plan:\n{plan}\n\n"
                if agent_msg:
                    output_content += f"### Agent Action:\n{agent_msg}\n\n"
                for art in artifacts:
                    art_type = art.get("type", "code_patch")
                    art_body = art.get("content", art.get("patch", ""))
                    if art_body:
                        output_content += f"### Artifact ({art_type}):\n{art_body}\n\n"

                if not output_content.strip() and desc:
                    output_content = f"Step Result: {desc}"

                pair_payload = {
                    "timestamp": create_time,
                    "prompt": f"{instruction}\n\nContext:\n{input_context}",
                    "completion": output_content.strip(),
                    "instruction": instruction,
                    "input": input_context,
                    "output": output_content.strip(),
                    "source": "jules_api_v1alpha",
                    "category": "autonomous_software_engineering",
                    "metadata": {
                        "session_id": session_id,
                        "activity_id": act_id,
                        "repo_source": source_name,
                        "sha256": hashlib.sha256(output_content.encode("utf-8")).hexdigest(),
                    },
                }
                training_pairs.append(pair_payload)

        if append_to_lora and training_pairs:
            LORA_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LORA_DATASET_PATH, "a", encoding="utf-8") as f:
                for p in training_pairs:
                    f.write(json.dumps(p) + "\n")

            with open(IDE_TRACES_PATH, "a", encoding="utf-8") as f:
                for p in training_pairs:
                    f.write(json.dumps(p) + "\n")

            print(f"[✓] Successfully distilled {len(training_pairs)} training pairs to {LORA_DATASET_PATH} and {IDE_TRACES_PATH}")

        return training_pairs


def main():
    parser = argparse.ArgumentParser(description="Google Jules API Sovereign Integration & Distillation Engine")
    parser.add_argument("--status", action="store_true", help="Check Jules API connection & auth status")
    parser.add_argument("--list-sources", action="store_true", help="List available code sources")
    parser.add_argument("--list-sessions", action="store_true", help="List active and past Jules sessions")
    parser.add_argument("--get-session", type=str, metavar="SESSION_ID", help="Inspect a specific session")
    parser.add_argument("--create-session", type=str, metavar="PROMPT", help="Create a new task session")
    parser.add_argument("--source", type=str, metavar="SOURCE_ID", help="Source repository identifier for session")
    parser.add_argument("--branch", type=str, default="main", help="Branch to branch off (default: main)")
    parser.add_argument("--title", type=str, default=None, help="Optional session title")
    parser.add_argument("--approve-plan", type=str, metavar="SESSION_ID", help="Approve session execution plan")
    parser.add_argument("--send-message", nargs=2, metavar=("SESSION_ID", "MESSAGE"), help="Send message to session")
    parser.add_argument("--list-activities", type=str, metavar="SESSION_ID", help="List session activities")
    parser.add_argument("--distill-session", type=str, metavar="SESSION_ID", help="Distill session trajectory to LoRA dataset")

    args = parser.parse_args()
    client = JulesClient()

    print(f"[*] Google Jules Client initialized. Auth Mode: {client.auth_mode}")

    if args.status:
        print("[*] Probing Jules API sources endpoint...")
        res = client.list_sources(page_size=5)
        if res.get("error"):
            print(f"[!] API Response Status: {res.get('status_code')} - {res.get('reason')}")
            print(f"[!] Details: {json.dumps(res.get('details'), indent=2)}")
            if res.get("status_code") == 401:
                print("\n[!] Authentic Auth Note:")
                print("    Jules API requires a personal token from https://jules.google.com/settings")
                print("    Export it as: export JULES_API_KEY='<token>' or add to 04_data_and_memory/.env")
        else:
            print("[✓] Jules API is ONLINE and authenticated!")
            print(f"[✓] Found {len(res.get('sources', []))} repository sources.")

    elif args.list_sources:
        res = client.list_sources()
        print(json.dumps(res, indent=2))

    elif args.list_sessions:
        res = client.list_sessions()
        print(json.dumps(res, indent=2))

    elif args.get_session:
        res = client.get_session(args.get_session)
        print(json.dumps(res, indent=2))

    elif args.create_session:
        if not args.source:
            print("[!] Error: --source is required when creating a session (e.g. --source sources/github/owner/repo)")
            sys.exit(1)
        res = client.create_session(prompt=args.create_session, source=args.source, starting_branch=args.branch, title=args.title)
        print(json.dumps(res, indent=2))

    elif args.approve_plan:
        res = client.approve_plan(args.approve_plan)
        print(json.dumps(res, indent=2))

    elif args.send_message:
        sid, msg = args.send_message
        res = client.send_message(session_id=sid, prompt=msg)
        print(json.dumps(res, indent=2))

    elif args.list_activities:
        res = client.list_activities(args.list_activities)
        print(json.dumps(res, indent=2))

    elif args.distill_session:
        pairs = client.distill_session_to_lora(args.distill_session, append_to_lora=True)
        print(f"Distilled {len(pairs)} trajectories.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
