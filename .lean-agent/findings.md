# Formalization Findings

## Discovered Invariants

### 1. Non-atomic transfer (partial mutation)
**Discovery:** Writing `TransferPrecondition` forced explicit ordering of mutations. The Python code does `accounts[from_id] -= amount` then `accounts[to_id] += amount`. If `to_id` doesn't exist, `KeyError` is raised AFTER the debit — money is destroyed.
**Current enforcement:** unguarded (0)
**Lean evidence:** `transfer_conserves_total` theorem requires both accounts to exist as precondition — without this, conservation doesn't hold.
**Risk:** Silent balance corruption. Source account is debited, destination never credited. No crash on the debit side, so caller may not realize funds were lost.

### 2. Account existence before access
**Discovery:** Defining `Ledger.lookup` as returning `Option Amount` exposed that the Python code uses raw dict access (KeyError on missing) instead of a safe lookup pattern.
**Current enforcement:** unguarded (0)
**Lean evidence:** `Ledger.hasAccount` predicate required in all operation preconditions — Python checks none of them.
**Risk:** KeyError crash on `transfer` or `balance` with non-existent account ID.

### 3. Transfer amount positivity
**Discovery:** Defining `PosAmount` (val > 0) as a separate type revealed that the Python code accepts negative and zero amounts. Negative amounts reverse the transfer direction silently.
**Current enforcement:** unguarded (0)
**Lean evidence:** `PosAmount` structure with `pos : val > 0` constraint — no analog in Python code.
**Risk:** Negative transfer silently moves money in reverse. Zero transfer is a no-op that wastes compute.

### 4. Duplicate account creation (silent overwrite)
**Discovery:** The `Ledger.nodup` field constraint revealed that `create_account` in Python does `accounts[id] = balance`, silently overwriting any existing account and its balance.
**Current enforcement:** unguarded (0)
**Lean evidence:** `create_account_idempotent_or_error` theorem — formalization demands either idempotency or error, Python provides neither.
**Risk:** Accidentally calling `create_account` with a different balance destroys the original balance without warning.

### 5. Overdraft protection (non-negative balance)
**Discovery:** Writing `transfer_preserves_nonneg` required an explicit non-negativity precondition. The Python code has no balance floor.
**Current enforcement:** unguarded (0)
**Lean evidence:** `TransferPrecondition.sufficientBalance` field — `bal >= amt.val` — not checked in Python.
**Risk:** Accounts can go arbitrarily negative. Downstream consumers may assume non-negative balances.

### 6. Balance type safety
**Discovery:** Choosing `Amount := Int` for the Lean spec forced the question: what IS the Python type? The answer is "anything" — no type annotation, no isinstance check. Passing a string as `opening_balance` produces `TypeError` only when arithmetic is attempted in `transfer`, not at account creation.
**Current enforcement:** unguarded (0)
**Lean evidence:** `Amount` type alias — Lean requires a concrete type; Python accepts any.
**Risk:** Type error surfaces far from the source (at transfer time, not at account creation), making debugging hard.

## Lean Spec Summary
- Files: `Spec/Domain.lean`, `Spec/Transfer.lean`
- `lake build`: pass (0 errors, 3 sorry warnings — expected)
- sorry count: 3 (all proofs are sorry — this is expected)
