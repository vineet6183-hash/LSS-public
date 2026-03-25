"""
Microsoft Graph API client for LSS Invoice Automation
Handles authentication and all API calls: read mail, download attachments,
send email, and access OneDrive files.
"""

import os
import base64
import logging
import requests
import msal

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self):
        self.tenant_id = os.environ["AZURE_TENANT_ID"]
        self.client_id = os.environ["AZURE_CLIENT_ID"]
        self.client_secret = os.environ["AZURE_CLIENT_SECRET"]
        self.user_email = os.environ["USER_EMAIL"]
        self.token = None
        self._authenticate()

    def _authenticate(self):
        app = msal.ConfidentialClientApplication(
            self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise Exception(
                f"Graph API authentication failed: {result.get('error_description', result)}"
            )
        self.token = result["access_token"]
        logger.info("Authenticated with Microsoft Graph API")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _get(self, url, **kwargs):
        r = requests.get(url, headers=self._headers(), **kwargs)
        r.raise_for_status()
        return r

    def _patch(self, url, json_data):
        r = requests.patch(url, headers=self._headers(), json=json_data)
        r.raise_for_status()
        return r

    def _post(self, url, json_data):
        r = requests.post(url, headers=self._headers(), json=json_data)
        r.raise_for_status()
        return r

    def _put(self, url, data):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream"
        }
        r = requests.put(url, headers=headers, data=data)
        r.raise_for_status()
        return r

    # -------------------------------------------------------------------------
    # Mail
    # -------------------------------------------------------------------------

    def get_mail_folder_id(self, folder_name):
        """Return the ID of a top-level mail folder by display name."""
        url = f"{GRAPH_BASE}/users/{self.user_email}/mailFolders"
        params = {"$filter": f"displayName eq '{folder_name}'"}
        r = self._get(url, params=params)
        folders = r.json().get("value", [])
        if not folders:
            raise Exception(
                f"Mail folder '{folder_name}' not found for {self.user_email}"
            )
        logger.info(f"Found mail folder '{folder_name}' (id={folders[0]['id'][:8]}...)")
        return folders[0]["id"]

    def get_unread_messages(self, folder_id):
        """Return all unread messages from a folder, handling pagination."""
        url = f"{GRAPH_BASE}/users/{self.user_email}/mailFolders/{folder_id}/messages"
        params = {
            "$filter": "isRead eq false",
            "$select": "id,subject,from,receivedDateTime,isRead,categories,hasAttachments",
            "$top": "100"
        }
        all_messages = []
        while url:
            r = self._get(url, params=params)
            data = r.json()
            all_messages.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
            params = None  # nextLink already encodes all params
        logger.info(f"Retrieved {len(all_messages)} unread messages")
        return all_messages

    def get_attachments(self, message_id):
        """List attachments for a message (metadata only, no content bytes)."""
        url = f"{GRAPH_BASE}/users/{self.user_email}/messages/{message_id}/attachments"
        params = {"$select": "id,name,contentType,size"}
        r = self._get(url, params=params)
        return r.json().get("value", [])

    def get_attachment_content(self, message_id, attachment_id):
        """Download the raw bytes of a specific attachment."""
        url = (
            f"{GRAPH_BASE}/users/{self.user_email}/messages/{message_id}"
            f"/attachments/{attachment_id}/$value"
        )
        headers = {"Authorization": f"Bearer {self.token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.content

    def mark_as_read(self, message_id, categories=None):
        """Mark a message as read and optionally set Outlook categories."""
        data = {"isRead": True}
        if categories:
            data["categories"] = categories
        url = f"{GRAPH_BASE}/users/{self.user_email}/messages/{message_id}"
        self._patch(url, data)

    def send_mail_with_attachment(self, to_email, subject, body, filename, file_bytes):
        """Send an email with a single file attachment via Graph API sendMail."""
        content_b64 = base64.b64encode(file_bytes).decode("utf-8")
        url = f"{GRAPH_BASE}/users/{self.user_email}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": to_email}}
                ],
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": filename,
                        "contentBytes": content_b64
                    }
                ]
            }
        }
        self._post(url, payload)
        logger.info(f"Email sent to {to_email} with attachment: {filename}")

    # -------------------------------------------------------------------------
    # OneDrive
    # -------------------------------------------------------------------------

    def download_onedrive_file(self, onedrive_path):
        """Download a file from the user's OneDrive by path relative to drive root."""
        url = f"{GRAPH_BASE}/users/{self.user_email}/drive/root:/{onedrive_path}:/content"
        headers = {"Authorization": f"Bearer {self.token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.content

    def upload_onedrive_file(self, onedrive_path, file_bytes):
        """Upload (replace) a file on the user's OneDrive by path relative to drive root."""
        url = f"{GRAPH_BASE}/users/{self.user_email}/drive/root:/{onedrive_path}:/content"
        self._put(url, file_bytes)
        logger.info(f"Uploaded to OneDrive: {onedrive_path}")
