# Improvement Targets

Baseline IES: 0.0000 (0/24)
Theoretical max IES: 1.0000

## Theoretical maximum table

| Check function | Max returnable score | Score-2 reachable? | What triggers score 3 |
|---|---|---|---|
| check_01_transfer_acct_exist | 3 | Yes | NewType/TypedDict/custom __getitem__ on accounts container |
| check_02_balance_acct_exist | 3 | Yes | Optional return type + .get() pattern |
| check_03_transfer_amt_positive | 3 | Yes | Annotated[..., Gt(0)] or PositiveAmount NewType on amount param |
| check_04_duplicate_acct_guard | 3 | Yes | Immutable container (frozendict) or returns new Ledger |
| check_05_overdraft_protection | 3 | Yes | Balance type that prevents going negative |
| check_06_balance_type_safety | 3 | Yes | Type annotation + isinstance enforcement |
| check_07_transfer_atomicity | 3 | Yes | Immutable update (returns new Ledger) or single-expression update |
| check_08_acct_id_type_safety | 3 | Yes | NewType AccountId |

## Strategic assessment

This repo is 100% unguarded — every invariant is at level 0. The risk concentrates
in `transfer()`: 5 of 8 invariants touch it, and the non-atomic mutation pattern means
a single KeyError can destroy funds. The cheapest path is validated (score 2) guards
on all methods — simple `if`/`raise` blocks. For one target, attempt structural
enforcement via NewType + type annotations to reach score 3.

## Phase 1 targets (execute sequentially)

### Target 1: acct_id_type_safety (0→1→3)
**Invariant:** Account ID parameters are constrained to a specific type
**Category:** Type safety
**Strategy:** structural (NewType)
**Where:** `grep -n "class Ledger" src/ledger.py`
**What:** Add `AccountId = NewType("AccountId", str)` and annotate all account_id/from_id/to_id params
**Test:** N/A (static enforcement)

### Target 2: balance_type_safety (0→2→3)
**Invariant:** opening_balance must be numeric
**Category:** Type safety
**Strategy:** validated → structural
**Where:** `grep -n "def create_account" src/ledger.py`
**What:** Add type annotation `int | float` + isinstance check
**Test:** Passing string as balance should raise TypeError

### Target 3: transfer_acct_exist (0→2)
**Invariant:** Both accounts must exist before transfer mutates state
**Category:** Input validation
**Strategy:** validated
**Where:** `grep -n "def transfer" src/ledger.py`
**What:** Add `if from_id not in self.accounts` / `if to_id not in self.accounts` raising ValueError
**Test:** Transfer with nonexistent account should raise

### Target 4: balance_acct_exist (0→2)
**Invariant:** Account must exist before balance query
**Category:** Input validation
**Strategy:** validated
**Where:** `grep -n "def balance" src/ledger.py`
**What:** Add `if account_id not in self.accounts` raising ValueError
**Test:** Balance query on nonexistent account should raise

### Target 5: duplicate_acct_guard (0→2)
**Invariant:** Cannot create account with existing ID
**Category:** State machine
**Strategy:** validated
**Where:** `grep -n "def create_account" src/ledger.py`
**What:** Add `if account_id in self.accounts` raising ValueError
**Test:** Double-create should raise

### Target 6: transfer_amt_positive (0→2)
**Invariant:** Transfer amount must be positive
**Category:** Input validation
**Strategy:** validated
**Where:** `grep -n "def transfer" src/ledger.py`
**What:** Add `if amount <= 0` raising ValueError
**Test:** Negative/zero transfer should raise

### Target 7: overdraft_protection (0→2)
**Invariant:** Source account must have sufficient balance
**Category:** Contract consistency
**Strategy:** validated
**Where:** `grep -n "def transfer" src/ledger.py`
**What:** Add `if self.accounts[from_id] < amount` raising ValueError after existence check
**Test:** Overdraft transfer should raise

### Target 8: transfer_atomicity (0→2)
**Invariant:** Transfer completes fully or has no effect
**Category:** State machine
**Strategy:** validated
**Where:** `grep -n "def transfer" src/ledger.py`
**What:** Pre-validate both accounts exist + sufficient balance BEFORE any mutation. All checks precede all mutations.
**Test:** Failed transfer should leave balances unchanged

## Phase 2 ideas (explore after Phase 1)
- Promote transfer_atomicity 2→3 via immutable Ledger (returns new state)
- Promote balance_acct_exist 2→3 via Optional return type
- Promote overdraft_protection 2→3 via NonNegativeBalance type
- Add `__repr__` / `__eq__` for debugging (not IES, but useful)
