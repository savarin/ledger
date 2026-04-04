/-
  Domain types for ledger-v2.

  The Python code uses:
    - accounts: dict[str, float]  (implicit — no type annotations)
    - account_id: any hashable     (implicit)
    - opening_balance: any          (implicit)
    - amount: any                   (implicit)

  Formalizing forces us to declare what the code leaves implicit.
-/
namespace Spec

-- ════════════════════════════════════════════════════════════════════
-- Core types
-- ════════════════════════════════════════════════════════════════════

/-- Account identifier. In Python this is untyped (any hashable). -/
abbrev AccountId := String

/-- Monetary amount. In Python this is untyped (could be string, None, etc.).
    We model as Int to avoid floating-point issues — but the Python code
    uses raw numeric types with no constraint. -/
abbrev Amount := Int

/-- An amount that must be positive. The Python code never checks this.
    Discovery: transfer with amount=0 is a no-op, amount<0 reverses direction. -/
structure PosAmount where
  val : Amount
  pos : val > 0

-- ════════════════════════════════════════════════════════════════════
-- Ledger state
-- ════════════════════════════════════════════════════════════════════

/-- A ledger is a finite map from account IDs to balances.
    The Python code uses a plain dict with no invariants on membership. -/
structure Ledger where
  accounts : List (AccountId × Amount)
  /-- No duplicate account IDs. The Python code silently overwrites on
      duplicate create_account calls — this invariant is unguarded. -/
  nodup : accounts.map Prod.fst |>.Nodup

-- ════════════════════════════════════════════════════════════════════
-- Operations as propositions about state transitions
-- ════════════════════════════════════════════════════════════════════

/-- Lookup an account balance. Returns none if account doesn't exist.
    Python version throws KeyError — no Option/Maybe wrapper. -/
def Ledger.lookup (l : Ledger) (id : AccountId) : Option Amount :=
  l.accounts.lookup id

/-- Predicate: account exists in the ledger. -/
def Ledger.hasAccount (l : Ledger) (id : AccountId) : Prop :=
  l.lookup id ≠ none

end Spec
