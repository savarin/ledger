/-
  Transfer safety properties for ledger-v2.

  The Python transfer method:
    def transfer(self, from_id, to_id, amount):
        self.accounts[from_id] -= amount
        self.accounts[to_id] += amount

  This has NO precondition checks. Formalizing the preconditions
  reveals what the code should enforce but doesn't.
-/
import Spec.Domain

namespace Spec

-- ════════════════════════════════════════════════════════════════════
-- Transfer preconditions (all unguarded in the Python code)
-- ════════════════════════════════════════════════════════════════════

/-- A valid transfer requires:
    1. Source account exists
    2. Destination account exists
    3. Amount is positive
    4. Source has sufficient balance
    5. Source ≠ destination (self-transfer is a no-op but not harmful)

    The Python code checks NONE of these. -/
structure TransferPrecondition (l : Ledger) (from_id to_id : AccountId) (amt : PosAmount) where
  sourceExists : l.hasAccount from_id
  destExists : l.hasAccount to_id
  sufficientBalance : ∃ (bal : Amount), l.lookup from_id = some bal ∧ bal ≥ amt.val

-- ════════════════════════════════════════════════════════════════════
-- Safety theorems (all sorry — value is in the signatures)
-- ════════════════════════════════════════════════════════════════════

/-- Conservation: total balance is unchanged after transfer.
    Discovery: This IS implicitly maintained by the arithmetic (a -= x, b += x),
    BUT only if both accounts exist. If from_id doesn't exist, KeyError
    is raised AFTER to_id might have been credited (partial mutation).
    The Python code mutates accounts[from_id] first, then accounts[to_id].
    If accounts[to_id] raises KeyError, the debit has already happened
    but the credit hasn't — money is destroyed.

    CRITICAL INVARIANT: The two mutations are not atomic. -/
theorem transfer_conserves_total
    (l : Ledger) (from_id to_id : AccountId) (amt : PosAmount)
    (pre : TransferPrecondition l from_id to_id amt) :
    True := by  -- placeholder: total before = total after
  sorry

/-- Non-negativity: if enforced, source balance stays >= 0.
    Discovery: Python code allows overdraft — no balance check. -/
theorem transfer_preserves_nonneg
    (l : Ledger) (from_id to_id : AccountId) (amt : PosAmount)
    (pre : TransferPrecondition l from_id to_id amt)
    (nonneg : ∃ (bal : Amount), l.lookup from_id = some bal ∧ bal ≥ 0) :
    True := by  -- placeholder: new source balance >= 0
  sorry

-- ════════════════════════════════════════════════════════════════════
-- Account creation
-- ════════════════════════════════════════════════════════════════════

/-- create_account overwrites silently if account exists.
    Discovery: No idempotency guard — calling create_account twice
    with different balances silently changes the balance, losing
    the transaction history. -/
theorem create_account_idempotent_or_error :
    True := by  -- placeholder: create on existing should fail or be no-op
  sorry

end Spec
