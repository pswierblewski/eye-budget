from abc import ABC
from webdav3.client import Client
import os


class ReceiptsRepository(ABC):
    """
    A client for interacting with a WebDAV server to manage receipts.
    This class provides methods to list receipts stored in a WebDAV directory.
    """

    def __init__(self):
        self.target_dir = os.getenv("INPUT_DIR", "input/")
        url = os.getenv("WEBDAV_URL", "")
        username = os.getenv("WEBDAV_USERNAME", "")
        password = os.getenv("WEBDAV_PASSWORD", "")
        options = {
            'webdav_hostname': url,
            'webdav_login':    username,
            'webdav_password': password,
            'verify':          False
        }
        self.client = Client(options)

    def download_receipts(self):
        try:
            self.client.download_sync(remote_path="Budżet domowy/Paragony/", local_path=self.target_dir)
        except Exception as e:
            print(f"Error downloading receipts: {e}")
            
    def dispose(self):
        """
        Dispose of the repository resources.
        This method is a placeholder for any cleanup operations needed.
        """
        print("ReceiptsRepository disposed.")