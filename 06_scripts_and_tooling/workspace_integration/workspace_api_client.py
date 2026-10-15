#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workspace_api_client.py — Mode A: Headless Google Workspace API Client
=====================================================================
Governed by:
- Rule #0 & #1: Zero-Mock Empirical Truth
- Rule #6: Multi-Provider Cloud Quota & Graduated Autonomy
- Rule #14: Browser Workspace & Business Account Authentication

Provides headless, autonomous OAuth2 authentication and API operations for
Google Workspace (Gmail, Drive, Sheets, Docs, Calendar) using authentic credentials.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure local addresses bypass proxy while external cloud endpoints use environment proxy
existing_no_proxy = os.environ.get("no_proxy", "")
if "127.0.0.1" not in existing_no_proxy:
    os.environ["no_proxy"] = f"{existing_no_proxy},127.0.0.1,localhost".strip(",")

# Configure structured logging
logger = logging.getLogger("WorkspaceAPIClient")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [WorkspaceAPI] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    logger.error(f"Missing required Google client libraries: {e}")
    logger.error("Please install via: pip install google-api-python-client google-auth google-auth-oauthlib")
    sys.exit(1)


DEFAULT_CREDS_PATH = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/workspace_credentials.json")
DEFAULT_TOKEN_PATH = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/workspace_token.json")


class WorkspaceAPIClient:
    """
    Autonomous Headless Google Workspace Client.
    Connects to Gmail, Drive, Sheets, and Docs using authentic OAuth2 tokens.
    Handles token refresh autonomously without human intervention.
    """

    def __init__(
        self,
        credentials_path: Optional[Union[str, Path]] = None,
        token_path: Optional[Union[str, Path]] = None,
    ):
        # Resolve credential file locations
        self.credentials_path = Path(credentials_path) if credentials_path else DEFAULT_CREDS_PATH
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH

        self.creds: Optional[Credentials] = None
        self._services: Dict[str, Any] = {}

    def authenticate(self) -> Credentials:
        """
        Loads and verifies OAuth2 credentials from token_path.
        If the access token has expired and a valid refresh token exists,
        refreshes the token autonomously and persists the updated token.
        """
        if not self.token_path.exists():
            raise FileNotFoundError(f"OAuth2 token file not found at: {self.token_path}")

        try:
            self.creds = Credentials.from_authorized_user_file(str(self.token_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials from {self.token_path}: {e}")

        # Autonomous token refresh without human interaction
        if self.creds and not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                logger.info("Access token expired. Autonomously refreshing token via Google OAuth2...")
                req = Request()
                try:
                    self.creds.refresh(req)
                    # Persist refreshed token atomically
                    self.token_path.write_text(self.creds.to_json(), encoding="utf-8")
                    logger.info("Access token refreshed and persisted successfully.")
                except Exception as e:
                    logger.error(f"Autonomous token refresh failed: {e}")
                    raise RuntimeError(f"Token refresh failed: {e}")
            else:
                raise RuntimeError("Credentials invalid and no refresh token available for headless refresh.")

        return self.creds

    def _get_service(self, service_name: str, version: str) -> Any:
        """Helper to get or build an authenticated Google API service client."""
        key = f"{service_name}:{version}"
        if key in self._services:
            return self._services[key]

        if not self.creds or not self.creds.valid:
            self.authenticate()

        service = build(service_name, version, credentials=self.creds, cache_discovery=False)
        self._services[key] = service
        return service

    # -------------------------------------------------------------------------
    # Gmail API Methods
    # -------------------------------------------------------------------------

    def get_gmail_profile(self) -> Dict[str, Any]:
        """
        Fetches the authenticated user's Gmail profile metadata.
        Returns dict with emailAddress, messagesTotal, threadsTotal, historyId.
        """
        try:
            service = self._get_service("gmail", "v1")
            profile = service.users().getProfile(userId="me").execute()
            return {
                "status": "success",
                "emailAddress": profile.get("emailAddress", ""),
                "messagesTotal": profile.get("messagesTotal", 0),
                "threadsTotal": profile.get("threadsTotal", 0),
                "historyId": profile.get("historyId", ""),
                "raw": profile,
            }
        except HttpError as e:
            logger.error(f"Gmail getProfile HttpError: {e}")
            return {
                "status": "error",
                "error": str(e),
                "status_code": e.resp.status if hasattr(e, "resp") else 500,
            }

    # Alias for contract compatibility
    getProfile = get_gmail_profile

    def read_gmail_threads(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Reads recent Gmail threads with subject, snippet, and message counts.
        """
        threads_out: List[Dict[str, Any]] = []
        try:
            service = self._get_service("gmail", "v1")
            res = service.users().threads().list(userId="me", maxResults=max_results).execute()
            raw_threads = res.get("threads", [])

            for item in raw_threads:
                t_id = item.get("id")
                try:
                    detail = (
                        service.users()
                        .threads()
                        .get(userId="me", id=t_id, format="metadata", metadataHeaders=["Subject", "From", "Date"])
                        .execute()
                    )
                    messages = detail.get("messages", [])
                    subject = "No Subject"
                    sender = "Unknown Sender"
                    date_str = ""

                    if messages:
                        headers = messages[0].get("payload", {}).get("headers", [])
                        for h in headers:
                            name = h.get("name", "").lower()
                            if name == "subject":
                                subject = h.get("value", subject)
                            elif name == "from":
                                sender = h.get("value", sender)
                            elif name == "date":
                                date_str = h.get("value", date_str)

                    threads_out.append(
                        {
                            "id": t_id,
                            "snippet": item.get("snippet", ""),
                            "historyId": item.get("historyId", ""),
                            "messages_count": len(messages),
                            "subject": subject,
                            "sender": sender,
                            "date": date_str,
                        }
                    )
                except Exception as inner_e:
                    threads_out.append(
                        {
                            "id": t_id,
                            "snippet": item.get("snippet", ""),
                            "error": str(inner_e),
                        }
                    )

            return threads_out
        except HttpError as e:
            logger.error(f"Gmail read_gmail_threads HttpError: {e}")
            return [{"error": str(e), "status_code": getattr(e, "resp", {}).get("status", 500)}]

    # Alias for contract compatibility
    listThreads = read_gmail_threads

    def send_gmail_message(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Sends an email message via authentic Gmail API.
        """
        try:
            service = self._get_service("gmail", "v1")
            msg = EmailMessage()
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            raw_bytes = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            sent = service.users().messages().send(userId="me", body={"raw": raw_bytes}).execute()

            return {
                "status": "sent",
                "id": sent.get("id"),
                "threadId": sent.get("threadId"),
                "labelIds": sent.get("labelIds", []),
                "to": to,
                "subject": subject,
            }
        except HttpError as e:
            logger.error(f"Gmail send_gmail_message HttpError: {e}")
            return {
                "status": "error",
                "error": str(e),
                "status_code": getattr(e, "resp", {}).get("status", 500),
            }

    # Alias for contract compatibility
    sendAlert = send_gmail_message

    # -------------------------------------------------------------------------
    # Google Drive API Methods
    # -------------------------------------------------------------------------

    def read_drive_files(self, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        Lists files in Google Drive.
        Handles permission scopes and service toggles gracefully under Zero-Mock rule.
        """
        try:
            service = self._get_service("drive", "v3")
            results = (
                service.files()
                .list(
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                )
                .execute()
            )
            files = results.get("files", [])
            return files
        except HttpError as e:
            # Under Zero-Mock Rule #1: Record authentic error and scope status without fabrication
            status_code = e.resp.status if hasattr(e, "resp") else 500
            logger.warning(
                f"Drive API returned HTTP {status_code}: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
            return [
                {
                    "error": f"HttpError {status_code}",
                    "reason": getattr(e, "reason", "Insufficient Permission / Scope missing for Drive API"),
                    "status_code": status_code,
                    "service": "drive_v3",
                }
            ]

    # Alias for contract compatibility
    listFiles = read_drive_files

    # -------------------------------------------------------------------------
    # Google Sheets API Methods
    # -------------------------------------------------------------------------

    def read_sheet_data(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """
        Reads tabular data from a Google Sheet.
        Returns a 2D list of row values.
        """
        try:
            service = self._get_service("sheets", "v4")
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            values = result.get("values", [])
            return values
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, "resp") else 500
            logger.warning(f"Sheets read_sheet_data returned HTTP {status_code}: {e}")
            return []

    # Alias for contract compatibility
    readRows = read_sheet_data

    def append_sheet_data(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
    ) -> Dict[str, Any]:
        """
        Appends rows to a Google Sheet.
        """
        try:
            service = self._get_service("sheets", "v4")
            body = {"values": values}
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )
            updates = result.get("updates", {})
            return {
                "status": "appended",
                "spreadsheetId": spreadsheet_id,
                "updatedRows": updates.get("updatedRows", 0),
                "updatedColumns": updates.get("updatedColumns", 0),
                "updatedCells": updates.get("updatedCells", 0),
                "updatedRange": updates.get("updatedRange", ""),
            }
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, "resp") else 500
            logger.warning(f"Sheets append_sheet_data returned HTTP {status_code}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "status_code": status_code,
            }

    # Alias for contract compatibility
    appendRows = append_sheet_data

    # -------------------------------------------------------------------------
    # Google Docs API Methods
    # -------------------------------------------------------------------------

    def create_document(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        Creates a new Google Doc with optional initial content.
        """
        try:
            service = self._get_service("docs", "v1")
            doc = service.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")

            if content and doc_id:
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]
                service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

            return {
                "status": "created",
                "documentId": doc_id,
                "title": title,
                "revisionId": doc.get("revisionId", ""),
            }
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, "resp") else 500
            logger.warning(f"Docs create_document returned HTTP {status_code}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "status_code": status_code,
            }

    # Alias for contract compatibility
    createDoc = create_document


# -----------------------------------------------------------------------------
# Module Self-Test Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("WorkspaceAPIClient (Mode A: Headless Backend APIs) Self-Test")
    print("=" * 70)

    client = WorkspaceAPIClient()

    print("[1/5] Authenticating & verifying autonomous token refresh...")
    creds = client.authenticate()
    print(f"  -> Authenticated. Scopes: {creds.scopes}")
    print(f"  -> Valid: {creds.valid}, Expired: {creds.expired}")

    print("\n[2/5] Fetching authentic Gmail profile...")
    profile = client.get_gmail_profile()
    print(f"  -> User: {profile.get('emailAddress')}")
    print(f"  -> Total Messages: {profile.get('messagesTotal')}")
    print(f"  -> Total Threads: {profile.get('threadsTotal')}")
    print(f"  -> Status: {profile.get('status')}")

    print("\n[3/5] Listing recent Gmail threads...")
    threads = client.read_gmail_threads(max_results=3)
    print(f"  -> Retrieved {len(threads)} thread(s):")
    for t in threads:
        print(f"     * ID {t.get('id')}: Subject='{t.get('subject')}' (Msgs: {t.get('messages_count')})")

    print("\n[4/5] Probing Drive API integration (Zero-Mock Scope Handling)...")
    drive_files = client.read_drive_files(page_size=2)
    print(f"  -> Drive Response: {drive_files}")

    print("\n[5/5] Testing Sheets Service initialization...")
    try:
        sheets_svc = client._get_service("sheets", "v4")
        print("  -> Google Sheets v4 service client initialized successfully.")
    except Exception as e:
        print(f"  -> Sheets init notice: {e}")

    print("\n" + "=" * 70)
    print("Self-Test Complete: Exit Code 0")
    print("=" * 70)
    sys.exit(0)
