#!/usr/bin/env python3
"""
Gmail Workspace Unified Client & Transport Engine
=================================================
Subsystem: 06_scripts_and_tooling / notifications
Provides unified multi-account Gmail API v1 & TLS SMTP/IMAP transport for:
1. lauburu@lauburugrappling.com (Google Workspace domain identity)
2. aaron.t.maher@gmail.com (Personal / Developer Admin identity)

Transports:
- Primary / Enterprise: Gmail REST API v1 over DWD / OAuth2 Bearer Tokens
- Secondary / High-Reliability: Native Python TLS SMTP (Port 587) & IMAP (Port 993)
  with authentic Google App Password authentication.

Zero-Mock Invariant: All health metrics and email operations reflect authentic
network round-trips against Google servers.
"""

import os
import sys
import json
import time
import email
import imaplib
import smtplib
import urllib.request
import urllib.error
import base64
import argparse
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Path resolution
ROOT_DIR = Path("/Volumes/Lauburu-Monorepo")
CONFIG_PATH = ROOT_DIR / "00_core_infrastructure/config/gmail_workspace_config.json"
AUTH_DIR = ROOT_DIR / "00_core_infrastructure/auth"

sys.path.insert(0, str(AUTH_DIR))
try:
    from workspace_dwd_gateway import DWDAuthGateway
except ImportError:
    DWDAuthGateway = None


class GmailWorkspaceClient:
    """Unified Gmail client supporting Google Workspace domain and personal accounts."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        default_account: Optional[str] = None
    ):
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load_config()
        self.default_account = default_account or self.config.get("default_sender", "aaron.t.maher@gmail.com")
        self.dwd_gateway = DWDAuthGateway(subject=self.default_account) if DWDAuthGateway else None

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration with fallback defaults."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except Exception as e:
                print(f"[WARN] Failed to read config at {self.config_path}: {e}", file=sys.stderr)
        return {
            "default_sender": "aaron.t.maher@gmail.com",
            "accounts": {
                "aaron.t.maher@gmail.com": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "app_password": os.getenv("GMAIL_APP_PASSWORD", "vtnqdfqouabaxvau"),
                    "preferred_transport": "smtp_tls"
                },
                "lauburu@lauburugrappling.com": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "app_password": os.getenv("LAUBURU_GMAIL_APP_PASSWORD"),
                    "preferred_transport": "gmail_api_v1"
                }
            }
        }

    def get_account_config(self, account: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves resolved configuration for a specific account."""
        target = account or self.default_account
        accounts = self.config.get("accounts", {})
        acc_cfg = accounts.get(target, {})
        # Check environment variable overrides for app password
        env_key = acc_cfg.get("app_password_env")
        if env_key and os.getenv(env_key):
            acc_cfg["app_password"] = os.getenv(env_key)
        return acc_cfg

    def list_accounts(self) -> List[str]:
        """Returns list of configured Gmail accounts."""
        return list(self.config.get("accounts", {}).keys())

    # ──────────────────────────────────────────────────────────────────────────
    # 1. MESSAGE FACTORY (RFC 2822 / MIME)
    # ──────────────────────────────────────────────────────────────────────────

    def build_mime_message(
        self,
        sender: str,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        priority: str = "1",
        mailer_tag: str = "Lauburu-Mesh-Sentinel-v2.4",
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> MIMEMultipart:
        """Creates an RFC 2822 compliant MIME message."""
        valid_attachments = []
        if attachments:
            for filepath in attachments:
                p = Path(filepath)
                if p.exists() and p.is_file():
                    valid_attachments.append(p)

        if valid_attachments:
            msg = MIMEMultipart("mixed")
            body_container = MIMEMultipart("alternative") if html else None
        else:
            msg = MIMEMultipart("alternative") if html else MIMEMultipart("mixed")
            body_container = None

        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="lauburugrappling.com")
        msg["X-Priority"] = str(priority)
        msg["X-Mailer"] = mailer_tag
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        part_text = MIMEText(body, "plain", "utf-8")
        if body_container is not None:
            body_container.attach(part_text)
            if html:
                part_html = MIMEText(html, "html", "utf-8")
                body_container.attach(part_html)
            msg.attach(body_container)
        else:
            msg.attach(part_text)
            if html:
                part_html = MIMEText(html, "html", "utf-8")
                msg.attach(part_html)

        for p in valid_attachments:
            ctype, encoding = mimetypes.guess_type(str(p))
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(p, "rb") as f:
                part = MIMEBase(maintype, subtype)
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=p.name)
            msg.attach(part)

        return msg

    # ──────────────────────────────────────────────────────────────────────────
    # 2. EMAIL DISPATCH (DUAL TRANSPORT)
    # ──────────────────────────────────────────────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        sender: Optional[str] = None,
        force_transport: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using the optimal available transport:
        1. If force_transport is specified, uses that transport.
        2. Otherwise follows account preferred_transport with automatic fallback.
        """
        sender_email = sender or self.default_account
        acc_cfg = self.get_account_config(sender_email)
        preferred = force_transport or acc_cfg.get("preferred_transport", "smtp_tls")

        msg = self.build_mime_message(
            sender=sender_email,
            to=to,
            subject=subject,
            body=body,
            html=html,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references
        )

        # Execute primary transport
        if preferred == "gmail_api_v1":
            res = self._send_via_rest_api(sender_email, msg)
            if res.get("success"):
                return res
            print(f"[WARN] REST API dispatch failed ({res.get('error')}). Attempting TLS SMTP fallback...", file=sys.stderr)
            return self._send_via_smtp(sender_email, to, msg, acc_cfg)
        else:
            res = self._send_via_smtp(sender_email, to, msg, acc_cfg)
            if res.get("success"):
                return res
            print(f"[WARN] SMTP dispatch failed ({res.get('error')}). Attempting REST API fallback...", file=sys.stderr)
            return self._send_via_rest_api(sender_email, msg)

    def _send_via_smtp(
        self,
        sender: str,
        recipient: str,
        msg: MIMEMultipart,
        acc_cfg: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Direct transmission via Google TLS SMTP server (smtp.gmail.com:587)."""
        host = acc_cfg.get("smtp_host", "smtp.gmail.com")
        port = acc_cfg.get("smtp_port", 587)
        app_pass = acc_cfg.get("app_password")

        if not app_pass:
            return {
                "success": False,
                "transport": "smtp_tls",
                "error": f"No Google App Password configured for {sender}."
            }

        start_t = time.time()
        try:
            server = smtplib.SMTP(host, port, timeout=12)
            server.starttls()
            server.login(sender, app_pass)
            server.sendmail(sender, [recipient], msg.as_string())
            server.quit()
            latency = (time.time() - start_t) * 1000

            return {
                "success": True,
                "transport": "smtp_tls",
                "sender": sender,
                "recipient": recipient,
                "message_id": msg["Message-ID"],
                "subject": msg["Subject"],
                "latency_ms": round(latency, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "transport": "smtp_tls",
                "error": str(e),
                "latency_ms": round((time.time() - start_t) * 1000, 2)
            }

    def _send_via_rest_api(
        self,
        sender: str,
        msg: MIMEMultipart
    ) -> Dict[str, Any]:
        """Direct transmission via official Google Gmail REST API v1."""
        start_t = time.time()
        gateway = self.dwd_gateway or (DWDAuthGateway(subject=sender) if DWDAuthGateway else None)
        if not gateway:
            return {"success": False, "transport": "gmail_api_v1", "error": "DWDAuthGateway unavailable"}

        token_resp = gateway.get_bearer_token(
            scopes=["https://www.googleapis.com/auth/gmail.send"],
            subject=sender
        )
        if not token_resp or not token_resp.get("access_token"):
            return {
                "success": False,
                "transport": "gmail_api_v1",
                "error": "No valid OAuth2 / DWD Bearer token available"
            }

        access_token = token_resp["access_token"]
        raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        payload = json.dumps({"raw": raw_b64}).encode("utf-8")

        url = f"https://gmail.googleapis.com/gmail/v1/users/{sender}/messages/send"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                latency = (time.time() - start_t) * 1000
                return {
                    "success": True,
                    "transport": "gmail_api_v1",
                    "sender": sender,
                    "google_message_id": res_data.get("id"),
                    "thread_id": res_data.get("threadId"),
                    "latency_ms": round(latency, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {
                "success": False,
                "transport": "gmail_api_v1",
                "http_code": e.code,
                "error": err_body,
                "latency_ms": round((time.time() - start_t) * 1000, 2)
            }
        except Exception as e:
            return {
                "success": False,
                "transport": "gmail_api_v1",
                "error": str(e),
                "latency_ms": round((time.time() - start_t) * 1000, 2)
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 3. INBOX QUERY & COMMAND DIRECTIVES
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_inbox(
        self,
        account: Optional[str] = None,
        query: str = "ALL",
        limit: int = 5
    ) -> Dict[str, Any]:
        """Fetches message summaries from inbox over IMAP."""
        target = account or self.default_account
        acc_cfg = self.get_account_config(target)
        app_pass = acc_cfg.get("app_password")

        if not app_pass:
            return {
                "status": "AWAITING_CREDENTIALS",
                "account": target,
                "error": "No App Password configured for IMAP",
                "messages": []
            }

        start_t = time.time()
        try:
            mail = imaplib.IMAP4_SSL(acc_cfg.get("imap_host", "imap.gmail.com"), acc_cfg.get("imap_port", 993))
            mail.login(target, app_pass)
            mail.select("inbox", readonly=True)

            status, data = mail.search(None, query)
            msg_ids = data[0].split()
            total_matches = len(msg_ids)

            selected_ids = msg_ids[-limit:] if total_matches > limit else msg_ids
            selected_ids.reverse()

            messages = []
            for mid in selected_ids:
                res, mdata = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                hdr_text = ""
                for part in mdata:
                    if isinstance(part, tuple):
                        hdr_text += part[1].decode("utf-8", errors="ignore")

                parsed = email.message_from_string(hdr_text)
                messages.append({
                    "id": mid.decode("utf-8"),
                    "from": parsed.get("From", ""),
                    "subject": parsed.get("Subject", ""),
                    "date": parsed.get("Date", "")
                })

            mail.close()
            mail.logout()
            latency = (time.time() - start_t) * 1000

            return {
                "status": "CONNECTED",
                "account": target,
                "total_matches": total_matches,
                "retrieved_count": len(messages),
                "latency_ms": round(latency, 2),
                "messages": messages,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "account": target,
                "error": str(e),
                "latency_ms": round((time.time() - start_t) * 1000, 2),
                "messages": []
            }

    def fetch_unread_directives(self, account: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches unread command emails with subject tag [LAUBURU-COMMAND]."""
        res = self.fetch_inbox(account=account, query='(UNSEEN SUBJECT "[LAUBURU-COMMAND]")', limit=10)
        return res.get("messages", [])

    # ──────────────────────────────────────────────────────────────────────────
    # 4. ZERO-MOCK HEALTH CHECK
    # ──────────────────────────────────────────────────────────────────────────

    def check_account_health(self, account: Optional[str] = None) -> Dict[str, Any]:
        """Performs authentic empirical round-trip probe against Google servers."""
        target = account or self.default_account
        acc_cfg = self.get_account_config(target)
        app_pass = acc_cfg.get("app_password")

        result = {
            "account": target,
            "role": acc_cfg.get("role", "general"),
            "preferred_transport": acc_cfg.get("preferred_transport", "unknown"),
            "app_password_configured": bool(app_pass),
            "imap_status": "OFFLINE",
            "smtp_status": "OFFLINE",
            "inbox_total": None,
            "inbox_unread": None,
            "round_trip_ms": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if not app_pass:
            result["status"] = "AWAITING_CREDENTIALS"
            return result

        start_t = time.time()
        try:
            # 1. IMAP Probe
            mail = imaplib.IMAP4_SSL(acc_cfg.get("imap_host", "imap.gmail.com"), acc_cfg.get("imap_port", 993), timeout=8)
            mail.login(target, app_pass)
            mail.select("inbox", readonly=True)

            _, all_res = mail.search(None, "ALL")
            all_ids = all_res[0].split()
            _, unread_res = mail.search(None, "UNSEEN")
            unread_ids = unread_res[0].split()

            result["inbox_total"] = len(all_ids)
            result["inbox_unread"] = len(unread_ids)
            result["imap_status"] = "AUTHENTICATED"
            mail.close()
            mail.logout()

            # 2. SMTP Probe
            server = smtplib.SMTP(acc_cfg.get("smtp_host", "smtp.gmail.com"), acc_cfg.get("smtp_port", 587), timeout=8)
            server.starttls()
            server.login(target, app_pass)
            server.quit()
            result["smtp_status"] = "AUTHENTICATED"

            result["status"] = "HEALTHY"
            result["round_trip_ms"] = round((time.time() - start_t) * 1000, 2)
        except Exception as e:
            result["status"] = "DEGRADED"
            result["error"] = str(e)
            result["round_trip_ms"] = round((time.time() - start_t) * 1000, 2)

        return result

    def check_all_accounts_health(self) -> Dict[str, Any]:
        """Runs zero-mock empirical health audit across all configured accounts."""
        accounts = self.list_accounts()
        statuses = {}
        for acc in accounts:
            statuses[acc] = self.check_account_health(acc)
        return {
            "subsystem": "Lauburu Multi-Account Gmail Sentinel",
            "accounts_count": len(accounts),
            "accounts": statuses,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 5. MESH OUT-OF-BAND ALERTING
    # ──────────────────────────────────────────────────────────────────────────

    def send_mesh_alert(
        self,
        title: str,
        details: str,
        severity: str = "WARNING",
        to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches urgent out-of-band alert to mesh administrators."""
        recipient = to or self.default_account
        subject = f"[LAUBURU-ALERT][{severity}] {title}"
        body = f"""LAUBURU MESH HARDWARE ALERT
============================
Severity: {severity}
Timestamp: {datetime.now(timezone.utc).isoformat()}
Node Context: L1 Mac Mini Master Sentinel

Details:
{details}

--
Generated automatically by Lauburu Multi-Transport Sentinel v2.4
"""
        return self.send_email(
            to=recipient,
            subject=subject,
            body=body,
            sender=self.default_account
        )


def main():
    parser = argparse.ArgumentParser(description="Lauburu Gmail Workspace Unified CLI")
    parser.add_argument("--status", action="store_true", help="Run live empirical health probe on all accounts")
    parser.add_argument("--inbox", action="store_true", help="Fetch recent inbox messages")
    parser.add_argument("--account", type=str, help="Specify Gmail account to target")
    parser.add_argument("--limit", type=int, default=5, help="Number of messages to list")
    parser.add_argument("--send", action="store_true", help="Send an email")
    parser.add_argument("--to", type=str, help="Recipient address")
    parser.add_argument("--subject", type=str, help="Email subject")
    parser.add_argument("--body", type=str, help="Email body")
    parser.add_argument("--alert", nargs=2, metavar=("TITLE", "DETAILS"), help="Send out-of-band mesh alert")
    args = parser.parse_args()

    client = GmailWorkspaceClient()

    if args.status:
        res = client.check_all_accounts_health()
        print(json.dumps(res, indent=2))
        sys.exit(0)

    if args.inbox:
        res = client.fetch_inbox(account=args.account, limit=args.limit)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    if args.alert:
        res = client.send_mesh_alert(args.alert[0], args.alert[1], severity="HIGH", to=args.to)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)

    if args.send:
        if not args.to or not args.subject or not args.body:
            print("Error: --send requires --to, --subject, and --body", file=sys.stderr)
            sys.exit(1)
        res = client.send_email(
            to=args.to,
            subject=args.subject,
            body=args.body,
            sender=args.account
        )
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)

    print("Gmail Workspace Client CLI ready. Use --status or --inbox.")


if __name__ == "__main__":
    main()
