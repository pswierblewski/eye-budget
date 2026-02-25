from src.clients.base import BudgetClient
from src.data import TransactionModel
from src.repositories.client_syncs import ClientSyncsRepository
from src.repositories.receipts_scans import ReceiptsScansRepository


class ClientSyncService:
    def __init__(
        self,
        receipts_scans_repository: ReceiptsScansRepository,
        client_syncs_repository: ClientSyncsRepository,
    ):
        self._receipts_scans_repository = receipts_scans_repository
        self._client_syncs_repository = client_syncs_repository

    def sync_scan(
        self,
        scan_id: int,
        transaction_model: TransactionModel,
        clients: list[BudgetClient],
        attachment_path: str | None = None,
    ) -> None:
        """
        Sends a single scan to all provided clients that haven't received it yet.
        Records success or failure in client_syncs for each client.
        """
        for client in clients:
            if self._client_syncs_repository.is_synced(scan_id, client.get_name()):
                print(f"Scan {scan_id} already synced to {client.get_name()}, skipping.")
                continue
            try:
                external_id = client.submit_transaction(transaction_model)
                if attachment_path:
                    client.attach_file(external_id, attachment_path)
                self._client_syncs_repository.record_success(scan_id, client.get_name(), external_id)
                print(f"Scan {scan_id} synced to {client.get_name()} (external_id={external_id}).")
            except Exception as e:
                self._client_syncs_repository.record_failure(scan_id, client.get_name(), e)
                print(f"Failed to sync scan {scan_id} to {client.get_name()}: {e}")

    def sync_all_unsynced(self, clients: list[BudgetClient]) -> dict:
        """
        Iterates all processed scans and sends each one to every client that
        hasn't received it yet. Used by the POST /receipts/sync-clients endpoint.

        Returns a summary dict with counts per client.
        """
        scans = self._receipts_scans_repository.get_processed_scans()
        print(f"Found {len(scans)} processed scans to consider for sync.")

        summary: dict[str, dict] = {
            client.get_name(): {"synced": 0, "skipped": 0, "failed": 0}
            for client in clients
        }

        for scan in scans:
            for client in clients:
                name = client.get_name()
                if self._client_syncs_repository.is_synced(scan.id, name):
                    summary[name]["skipped"] += 1
                    continue
                try:
                    external_id = client.submit_transaction(scan.transaction_model)
                    self._client_syncs_repository.record_success(scan.id, name, external_id)
                    summary[name]["synced"] += 1
                    print(f"Scan {scan.id} synced to {name} (external_id={external_id}).")
                except Exception as e:
                    self._client_syncs_repository.record_failure(scan.id, name, e)
                    summary[name]["failed"] += 1
                    print(f"Failed to sync scan {scan.id} to {name}: {e}")

        return summary

    def dispose(self) -> None:
        print("ClientSyncService disposed.")
