import asyncio
from dotenv import load_dotenv

load_dotenv()

from ..bank_category_top import top_category_candidate_from_stored_json
from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


def emit_categorization_transaction_updated(pusher, bank_transaction_id: int, candidates: list) -> None:
    top = top_category_candidate_from_stored_json(candidates)
    pusher.trigger(
        "bank-transactions",
        "categorization.transaction_updated",
        {"bank_transaction_id": bank_transaction_id, "ai_top_candidate": top},
    )


@celery_app.task(bind=True, name="tasks.categorize_bank_transactions")
def categorize_bank_transactions_task(self, transaction_ids: list[int]):
    """Celery task: call LLM to assign category candidates to bank transactions.

    Emits Pusher events on channel 'bank-transactions':
      - categorization.progress           {task_id, index, total}
      - categorization.transaction_updated {bank_transaction_id, ai_top_candidate}
      - categorization.done              {task_id, total}
      - categorization.error             {task_id, error}
    """
    task_id = self.request.id
    pusher = PusherService()
    total = len(transaction_ids)
    my_app = App()
    try:
        asyncio.run(
            _categorize_all(
                transaction_ids=transaction_ids,
                my_app=my_app,
                pusher=pusher,
                task_id=task_id,
                total=total,
            )
        )
        pusher.trigger(
            "bank-transactions",
            "categorization.done",
            {"task_id": task_id, "total": total},
        )
    except Exception as exc:
        pusher.trigger(
            "bank-transactions",
            "categorization.error",
            {"task_id": task_id, "error": str(exc)},
        )
        raise
    finally:
        my_app.dispose()


CONCURRENT_LLM_CALLS = 5


async def _categorize_all(transaction_ids, my_app, pusher, task_id, total):
    """Process all bank transactions in parallel, capped at CONCURRENT_LLM_CALLS at a time."""
    sem = asyncio.Semaphore(CONCURRENT_LLM_CALLS)
    db_lock = asyncio.Lock()
    counter = {"value": 0}
    counter_lock = asyncio.Lock()

    async def _process_one(tx_id: int):
        try:
            async with db_lock:
                tx = await asyncio.to_thread(
                    my_app.bank_transactions_repository.get_by_id, tx_id
                )
            if tx is not None:
                async with sem:
                    candidates = await my_app.bank_categorization_service.assign_candidates_async(
                        tx, db_lock
                    )
                async with db_lock:
                    await asyncio.to_thread(
                        my_app.bank_transactions_repository.update_candidates, tx_id, candidates
                    )
                emit_categorization_transaction_updated(pusher, tx_id, candidates)
        except Exception as e:
            print(f"LLM categorization failed for bank_transaction {tx_id}: {e}")

        async with counter_lock:
            counter["value"] += 1
            idx = counter["value"]
        pusher.trigger(
            "bank-transactions",
            "categorization.progress",
            {"task_id": task_id, "index": idx, "total": total},
        )

    await asyncio.gather(*[_process_one(tx_id) for tx_id in transaction_ids])
