import os, json, csv
from datetime import datetime
from services.bank_service import BankService

BACKUP_DIR = "backups"

def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)

def export_transactions_json(user_id: int) -> str:
    ensure_backup_dir()
    txns = BankService.get_transactions(user_id)

    data = [
        {
            "transaction_type": t[0],
            "amount": float(t[1]),
            "previous_balance": float(t[2]),
            "new_balance": float(t[3]),
            "created_at": str(t[4]),
        }
        for t in txns
    ]

    filename = f"transactions_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join(BACKUP_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path

def export_transactions_csv(user_id: int) -> str:
    ensure_backup_dir()
    txns = BankService.get_transactions(user_id)

    filename = f"transactions_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(BACKUP_DIR, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_type", "amount", "previous_balance", "new_balance", "created_at"])
        for t in txns:
            writer.writerow([t[0], t[1], t[2], t[3], t[4]])

    return path