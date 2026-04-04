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
