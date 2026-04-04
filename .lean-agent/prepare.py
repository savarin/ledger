"""IES evaluation harness for ledger-v2.

Read-only. Examines source code and computes IES.

Usage:
    python3 prepare.py
"""
from pathlib import Path
import ast
import re

REPO = Path("/Users/savarin/Development/python/ledger-v2")
SRC = REPO / "src" / "ledger.py"

# ════════════════════════════════════════════════════════════════════
# AST helpers
# ════════════════════════════════════════════════════════════════════

def _parse_source() -> tuple[str, ast.Module]:
    """Read and parse the source file."""
    content = SRC.read_text()
    tree = ast.parse(content)
    return content, tree


def _extract_method(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef | None:
    """Find a method within a specific class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in ast.walk(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    return item
    return None


def _get_method_source(content: str, tree: ast.Module, class_name: str, method_name: str) -> str | None:
    """Extract source text of a method."""
    method = _extract_method(tree, class_name, method_name)
    if method is None:
        return None
    return ast.get_source_segment(content, method)


def _class_has_method(tree: ast.Module, class_name: str, method_name: str) -> bool:
    """Check if a class has a specific method."""
    return _extract_method(tree, class_name, method_name) is not None


def _method_has_raise(content: str, tree: ast.Module, class_name: str, method_name: str,
                      error_pattern: str) -> bool:
    """Check if a method raises an error matching the pattern."""
    src = _get_method_source(content, tree, class_name, method_name)
    if src is None:
        return False
    return bool(re.search(error_pattern, src))


def _method_has_isinstance_check(content: str, tree: ast.Module, class_name: str,
                                  method_name: str, param_pattern: str) -> bool:
    """Check if a method has isinstance checks matching the pattern."""
    src = _get_method_source(content, tree, class_name, method_name)
    if src is None:
        return False
    return bool(re.search(rf'isinstance\s*\({param_pattern}', src))


def _has_type_annotation(tree: ast.Module, class_name: str, method_name: str,
                          param_name: str) -> bool:
    """Check if a method parameter has a type annotation."""
    method = _extract_method(tree, class_name, method_name)
    if method is None:
        return False
    for arg in method.args.args:
        if arg.arg == param_name and arg.annotation is not None:
            return True
    return False


def _has_return_annotation(tree: ast.Module, class_name: str, method_name: str) -> bool:
    """Check if a method has a return type annotation."""
    method = _extract_method(tree, class_name, method_name)
    if method is None:
        return False
    return method.returns is not None


# ════════════════════════════════════════════════════════════════════
# Check functions
# ════════════════════════════════════════════════════════════════════

def check_01_transfer_account_existence() -> tuple[int, str]:
    """Transfer checks that both from_id and to_id exist before mutating."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "transfer")
    if src is None:
        return 0, "transfer method not found"

    # Score 3: Structural — typed accounts container that prevents KeyError
    # (e.g., method signature requires Account objects, not raw IDs,
    # or accounts is a type that returns a default/raises typed error)
    # Check for NewType/TypedDict/custom mapping that enforces key presence
    class_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Ledger":
            class_src = ast.get_source_segment(content, node)
            break
    if class_src and re.search(r'(?:NewType|TypedDict|__getitem__.*raise\s+\w+Error\b'
                               r'|accounts\s*:\s*dict\[.*,\s*Account\])', class_src):
        return 3, "structural: typed container prevents invalid account access"

    # Score 2: Validated — explicit existence check before mutation
    has_from_check = bool(re.search(
        r'(?:if\s+\w+\s+not\s+in\s+self\.accounts|'
        r'if\s+\w+\s+not\s+in\s+self\.\w+|'
        r'raise\s+(?:KeyError|ValueError|AccountNotFound)|'
        r'self\.accounts\.get\s*\(|'
        r'if\s+not\s+self\.(?:has_account|_has_account|account_exists))',
        src
    ))
    has_to_check = has_from_check  # same pattern covers both if checking for general existence logic
    if has_from_check:
        return 2, "validated: explicit existence check before transfer"

    # Score 1: Convention — comment or docstring mentions existence requirement
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:must exist|account.*exist|valid.*account|check.*exist)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: raw dict access, KeyError on missing account"


def check_02_balance_account_existence() -> tuple[int, str]:
    """Balance query checks that account_id exists."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "balance")
    if src is None:
        return 0, "balance method not found"

    # Score 3: Structural — return type is Option-like or method raises typed error
    # by construction (e.g., returns Account object, not raw value)
    if re.search(r'(?:Optional\[|None\s*\||-> *(?:int|float|Decimal)\s*\|\s*None)',
                 src):
        # Check it actually returns None for missing, not just annotation
        if re.search(r'\.get\s*\(|return\s+None', src):
            return 3, "structural: return type encodes missing-account possibility"

    # Score 2: Validated — explicit check before access
    if re.search(
        r'(?:if\s+\w+\s+not\s+in\s+self\.accounts|'
        r'raise\s+(?:KeyError|ValueError|AccountNotFound)|'
        r'self\.accounts\.get\s*\(|'
        r'if\s+not\s+self\.(?:has_account|_has_account|account_exists))',
        src
    ):
        return 2, "validated: explicit existence check before balance lookup"

    # Score 1: Convention — documented
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:must exist|account.*exist|valid.*account)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: raw dict access, KeyError on missing account"


def check_03_transfer_amount_positive() -> tuple[int, str]:
    """Transfer validates that amount is positive."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "transfer")
    if src is None:
        return 0, "transfer method not found"

    # Score 3: Structural — amount parameter typed as PositiveAmount/NewType
    # or method signature enforces positivity at the type level
    method = _extract_method(tree, "Ledger", "transfer")
    if method:
        for arg in method.args.args:
            if arg.arg == "amount" and arg.annotation:
                ann_src = ast.get_source_segment(content, arg.annotation)
                if ann_src and re.search(r'(?:Positive|PosInt|PosFloat|PositiveAmount|'
                                         r'Annotated\[.*Gt\(0\)|Annotated\[.*gt=0)',
                                         ann_src):
                    return 3, "structural: type-level positivity constraint on amount"

    # Score 2: Validated — runtime check
    if re.search(
        r'(?:if\s+\w*amount\w*\s*<=?\s*0|'
        r'if\s+not\s+\w*amount\w*\s*>|'
        r'if\s+\w*amount\w*\s*<\s*0|'
        r'raise\s+ValueError.*(?:positive|negative|amount)|'
        r'assert\s+\w*amount\w*\s*>)',
        src
    ):
        return 2, "validated: runtime check rejects non-positive amount"

    # Score 1: Convention — documented
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:positive|must be.*>|greater than)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: negative amount silently reverses transfer direction"


def check_04_duplicate_account_guard() -> tuple[int, str]:
    """create_account rejects or warns on duplicate account IDs."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "create_account")
    if src is None:
        return 0, "create_account method not found"

    # Score 3: Structural — accounts container type prevents duplicate keys
    # (e.g., frozenset-based, or create returns new Ledger with added account)
    class_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Ledger":
            class_src = ast.get_source_segment(content, node)
            break
    if class_src and re.search(r'(?:frozendict|FrozenDict|MappingProxyType|'
                               r'__setitem__.*raise|_create_account.*->.*Ledger)',
                               class_src):
        return 3, "structural: immutable or typed container prevents overwrites"

    # Score 2: Validated — explicit duplicate check
    if re.search(
        r'(?:if\s+\w+\s+in\s+self\.accounts|'
        r'raise\s+(?:ValueError|KeyError|AccountExists|DuplicateAccount)|'
        r'if\s+self\.(?:has_account|_has_account|account_exists))',
        src
    ):
        return 2, "validated: explicit duplicate check before creation"

    # Score 1: Convention — documented
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:duplicate|already exist|unique|overwrite)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: silently overwrites existing account balance"


def check_05_overdraft_protection() -> tuple[int, str]:
    """Transfer checks sufficient balance before debiting."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "transfer")
    if src is None:
        return 0, "transfer method not found"

    # Score 3: Structural — balance type cannot go negative
    # (e.g., unsigned int type, or custom Amount type with floor)
    method = _extract_method(tree, "Ledger", "transfer")
    if method:
        for arg in method.args.args:
            if arg.arg == "amount" and arg.annotation:
                ann_src = ast.get_source_segment(content, arg.annotation)
                if ann_src and re.search(r'(?:NonNeg|Unsigned|Natural)', ann_src):
                    return 3, "structural: type prevents negative balance"
    # Also check if accounts use a balance type that prevents going negative
    class_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Ledger":
            class_src = ast.get_source_segment(content, node)
            break
    if class_src and re.search(r'(?:__isub__.*raise|Balance\b.*NonNeg)', class_src):
        return 3, "structural: balance type enforces non-negativity"

    # Score 2: Validated — runtime balance check
    if re.search(
        r'(?:if\s+self\.accounts\[\w+\]\s*<\s*\w*amount|'
        r'if\s+\w*balance\w*\s*<\s*\w*amount|'
        r'if\s+\w*amount\w*\s*>\s*\w*balance|'
        r'raise\s+(?:ValueError|InsufficientFunds|Overdraft)|'
        r'insufficient|overdraft)',
        src, re.IGNORECASE
    ):
        return 2, "validated: runtime check prevents overdraft"

    # Score 1: Convention — documented
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:sufficient|overdraft|enough|balance.*check)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: balance can go negative without warning"


def check_06_balance_type_safety() -> tuple[int, str]:
    """opening_balance is validated as numeric at account creation."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "create_account")
    if src is None:
        return 0, "create_account method not found"

    # Score 3: Structural — type annotation on opening_balance parameter
    method = _extract_method(tree, "Ledger", "create_account")
    if method:
        for arg in method.args.args:
            if arg.arg == "opening_balance" and arg.annotation:
                ann_src = ast.get_source_segment(content, arg.annotation)
                if ann_src and re.search(r'(?:int|float|Decimal|Number|Amount|Numeric)', ann_src):
                    # Type annotation is structural if paired with runtime enforcement
                    # or if the project uses a type checker
                    if re.search(r'isinstance\s*\(\s*\w*opening_balance\w*\s*,', src):
                        return 3, "structural: type annotation + isinstance enforcement"
                    return 2, "validated: type annotation constrains balance type"

    # Score 2: Validated — isinstance check
    if re.search(r'isinstance\s*\(\s*\w*opening_balance\w*\s*,\s*\(?(?:int|float|Decimal)',
                 src):
        return 2, "validated: isinstance check on opening_balance"

    # Score 1: Convention — type hint without enforcement, or documented
    if method:
        for arg in method.args.args:
            if arg.arg == "opening_balance" and arg.annotation:
                return 1, "convention: type annotation present but not enforced at runtime"
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:numeric|number|int|float|type)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: no type check, string/None accepted silently"


def check_07_transfer_atomicity() -> tuple[int, str]:
    """Transfer either completes fully or has no effect (no partial mutation)."""
    content, tree = _parse_source()
    src = _get_method_source(content, tree, "Ledger", "transfer")
    if src is None:
        return 0, "transfer method not found"

    # Score 3: Structural — immutable ledger (returns new state) or
    # single-expression update (no intermediate mutation)
    if re.search(r'(?:->.*Ledger|return\s+Ledger\(|self\.accounts\s*=\s*\{)', src):
        return 3, "structural: immutable update or single-expression state transition"
    # Check for dataclass replace or dict comprehension update
    if re.search(r'(?:replace\s*\(|dataclasses\.replace|copy\(\))', src):
        return 3, "structural: copy-on-write prevents partial mutation"

    # Score 2: Validated — try/except with rollback, or pre-validation of both accounts
    # before any mutation
    if re.search(r'(?:try\s*:.*except.*:\s*.*self\.accounts|rollback|'
                 r'(?:if|assert).*(?:from_id|to_id).*(?:if|assert).*(?:from_id|to_id))',
                 src, re.DOTALL):
        return 2, "validated: try/except with rollback or pre-validation"
    # Pre-check both accounts exist before any mutation
    lines = src.split('\n')
    check_lines = []
    mutate_lines = []
    for i, line in enumerate(lines):
        if re.search(r'(?:if\s+\w+\s+not\s+in|raise\s+|assert\s+)', line):
            check_lines.append(i)
        if re.search(r'self\.accounts\[.*\]\s*[-+]?=', line):
            mutate_lines.append(i)
    if check_lines and mutate_lines and max(check_lines) < min(mutate_lines):
        return 2, "validated: all checks precede all mutations"

    # Score 1: Convention — documented
    if re.search(r'(?:#|"""|\'\'\')\s*.*(?:atomic|rollback|transaction|all.or.nothing)',
                 src, re.IGNORECASE):
        return 1, "convention: documented but not enforced"

    return 0, "unguarded: sequential mutation, KeyError after partial debit destroys funds"


def check_08_account_id_type_safety() -> tuple[int, str]:
    """account_id parameters are validated as the expected type."""
    content, tree = _parse_source()

    # Check across all methods that accept account_id-like params
    methods_to_check = ["create_account", "transfer", "balance"]
    has_annotation = False
    has_isinstance = False
    has_newtype = False

    # Check for NewType or branded AccountId type at module level
    if re.search(r'(?:AccountId\s*=\s*NewType|class\s+AccountId)', content):
        has_newtype = True

    for method_name in methods_to_check:
        method = _extract_method(tree, "Ledger", method_name)
        if method is None:
            continue
        method_src = _get_method_source(content, tree, "Ledger", method_name)
        if method_src is None:
            continue

        for arg in method.args.args:
            if arg.arg in ("account_id", "from_id", "to_id"):
                if arg.annotation:
                    ann_src = ast.get_source_segment(content, arg.annotation)
                    if ann_src and re.search(r'(?:str|AccountId|int)', ann_src):
                        has_annotation = True
                if method_src and re.search(
                    rf'isinstance\s*\(\s*{re.escape(arg.arg)}\s*,',
                    method_src
                ):
                    has_isinstance = True

    # Score 3: Structural — NewType or branded type for account IDs
    if has_newtype:
        return 3, "structural: NewType/branded AccountId prevents type confusion"

    # Score 2: Validated — isinstance check on account ID params
    if has_isinstance:
        return 2, "validated: isinstance check on account ID parameters"

    # Score 1: Convention — type annotations present
    if has_annotation:
        return 1, "convention: type annotations present but not enforced at runtime"

    return 0, "unguarded: no type constraint on account IDs"


# ════════════════════════════════════════════════════════════════════
# Harness
# ════════════════════════════════════════════════════════════════════

INVARIANTS = [
    ("transfer_acct_exist", check_01_transfer_account_existence),
    ("balance_acct_exist", check_02_balance_account_existence),
    ("transfer_amt_positive", check_03_transfer_amount_positive),
    ("duplicate_acct_guard", check_04_duplicate_account_guard),
    ("overdraft_protection", check_05_overdraft_protection),
    ("balance_type_safety", check_06_balance_type_safety),
    ("transfer_atomicity", check_07_transfer_atomicity),
    ("acct_id_type_safety", check_08_account_id_type_safety),
]

LEVEL_NAMES = {3: "structural", 2: "validated", 1: "convention", 0: "unguarded"}


def main() -> None:
    results = []
    for name, check_fn in INVARIANTS:
        score, explanation = check_fn()
        results.append((name, score, explanation))

    print("=" * 78)
    print(f"{'Invariant':<28} {'Score':<6} {'Level':<12} Explanation")
    print("-" * 78)
    for name, score, explanation in results:
        level = LEVEL_NAMES[score]
        print(f"{name:<28} {score:<6} {level:<12} {explanation}")
    print("=" * 78)

    scores = [r[1] for r in results]
    n = len(scores)
    total = sum(scores)
    ies = total / (3 * n) if n > 0 else 0

    print()
    print(f"ies_score: {ies:.4f}")
    print(f"ies_numerator: {total}")
    print(f"ies_denominator: {3 * n}")
    print(f"invariant_count: {n}")
    print(f"structural_count: {sum(1 for s in scores if s == 3)}")
    print(f"validated_count: {sum(1 for s in scores if s == 2)}")
    print(f"convention_count: {sum(1 for s in scores if s == 1)}")
    print(f"unguarded_count: {sum(1 for s in scores if s == 0)}")


if __name__ == "__main__":
    main()
