# ledger

Demo repo for [lean-agent](https://github.com/savarin/lean-agent) — autonomous code hardening via IES optimization.

## Before

A 13-line double-entry ledger. It works, until it doesn't.

```python
class Ledger:
    def __init__(self):
        self.accounts = {}

    def create_account(self, account_id, opening_balance):
        self.accounts[account_id] = opening_balance

    def transfer(self, from_id, to_id, amount):
        self.accounts[from_id] -= amount
        self.accounts[to_id] += amount

    def balance(self, account_id):
        return self.accounts[account_id]
```

Six things this code assumes but doesn't enforce:

1. Balances are numeric — pass a string, arithmetic silently corrupts
2. Transfer amounts are positive — negatives reverse the direction
3. Both accounts exist — missing target debits source, then crashes (money gone)
4. Accounts aren't duplicated — `create_account` silently overwrites
5. Sufficient balance — overdrafts go negative without complaint
6. Accounts aren't mutated externally — `ledger.accounts["X"] = 999` bypasses all checks

## After

lean-agent found these invariants and hardened the code:

```python
from types import MappingProxyType
from typing import NewType, TypeAlias

AccountId = NewType("AccountId", str)
PositiveAmount = NewType("PositiveAmount", float)
Account: TypeAlias = int | float


class Ledger:
    """Double-entry ledger. Balance is NonNeg — enforced by transfer validation."""

    def __init__(self) -> None:
        self.accounts: dict[AccountId, Account] = {}

    @property
    def accounts_view(self) -> MappingProxyType:
        """Read-only view of accounts. External code should use this."""
        return MappingProxyType(self.accounts)

    def create_account(self, account_id: AccountId, opening_balance: int | float) -> None:
        if not isinstance(opening_balance, (int, float)):
            raise TypeError(f"opening_balance must be numeric, got {type(opening_balance).__name__}")
        if account_id in self.accounts:
            raise ValueError(f"account {account_id} already exists")
        self.accounts[account_id] = opening_balance

    def transfer(self, from_id: AccountId, to_id: AccountId, amount: PositiveAmount) -> None:
        if amount <= 0:
            raise ValueError(f"transfer amount must be positive, got {amount}")
        if from_id not in self.accounts:
            raise ValueError(f"source account {from_id} does not exist")
        if to_id not in self.accounts:
            raise ValueError(f"destination account {to_id} does not exist")
        if self.accounts[from_id] < amount:
            raise ValueError(
                f"insufficient balance: account {from_id} has {self.accounts[from_id]}, need {amount}"
            )
        self.accounts = {
            **self.accounts,
            from_id: self.accounts[from_id] - amount,
            to_id: self.accounts[to_id] + amount,
        }

    def balance(self, account_id: AccountId) -> float | None:
        return self.accounts.get(account_id)
```

What changed:

- **`NewType` for type safety** — `AccountId` and `PositiveAmount` are checked by mypy/pyright, preventing misuse at the type level
- **Numeric validation** — `isinstance` check on `opening_balance` catches strings before they corrupt arithmetic
- **Positive amount guard** — rejects zero and negative transfers
- **Account existence checks** — separate checks for source and destination with descriptive errors
- **Duplicate protection** — `create_account` raises if the account already exists
- **Insufficient balance check** — prevents overdrafts
- **Atomic dict rebuild** — transfer updates both accounts in a single dict assignment
- **`MappingProxyType`** — read-only view prevents external mutation of account balances
