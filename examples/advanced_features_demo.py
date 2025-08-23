#!/usr/bin/env python3
"""
Advanced Features Demo

Shows limits, adjunctions, and Kleisli categories in LambdaCat.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

print("Advanced Features Demo")
print("=" * 30)

print("\n1. Limits in Categories")

from LambdaCat.core import Cat, arrow, build_presentation, equalizer, obj, product, terminal_object
from LambdaCat.core.standard import discrete, terminal_category

# Terminal objects
print("Terminal objects:")
C = terminal_category()
terminal = terminal_object(C)
print(f"  Terminal in terminal category: {terminal}")

D = discrete(["A", "B", "C"])
terminal_discrete = terminal_object(D)
print(f"  Terminal in discrete category: {terminal_discrete}")

# Products
print("\nProducts:")
prod_AA = product(D, "A", "A")
print(f"  A×A in discrete category: {prod_AA.cone.apex if prod_AA else 'None'}")

prod_AB = product(D, "A", "B")
print(f"  A×B in discrete category: {prod_AB.cone.apex if prod_AB else 'None'}")

# Equalizers
print("\nEqualizers:")
A, B = obj("A"), obj("B")
f = arrow("f", "A", "B")
g = arrow("g", "A", "B")

p = build_presentation([A, B], [f, g])
E = Cat.from_presentation(p)

eq_same = equalizer(E, "f", "f")  # f = f
print(f"  Equalizer of f with itself: {eq_same.cone.apex if eq_same else 'None'}")

eq_different = equalizer(E, "f", "g")  # f ≠ g
print(f"  Equalizer of f and g: {eq_different.cone.apex if eq_different else 'None'}")

print("\n2. Adjunctions")

from LambdaCat.core import ADJUNCTION_SUITE, free_forgetful_adjunction, run_suite

print("Free-Forgetful Adjunction:")
adj = free_forgetful_adjunction()
print(f"  Left adjoint (Free): {adj.left.name}")
print(f"  Right adjoint (Forget): {adj.right.name}")

print("\nAdjunction Laws:")
report = run_suite(adj, ADJUNCTION_SUITE)
print(f"  Overall: {'PASS' if report.ok else 'FAIL'}")

for result in report.results:
    status = 'PASS' if result.passed else 'FAIL'
    print(f"  {result.law}: {status} ({len(result.violations)} violations)")

    if result.violations:
        print(f"    - {result.violations[0].message}")

print("\n3. Kleisli Categories")

from LambdaCat.core.fp import Kleisli, get_registered_monads, kleisli_category_for
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.fp.instances.result import Result

print("Registered Monads:")
registered = get_registered_monads()
for name in sorted(registered.keys()):
    print(f"  - {name}")

print("\nBuilding Kleisli Category:")
kleisli_cat = kleisli_category_for('Option', ['String', 'Int', 'Bool'])
print(f"  Base category: {kleisli_cat}")

# Add safe parsing arrow: String -> Option[Int]
def safe_parse_int(s: str) -> Option[int]:
    try:
        return Option.some(int(s))
    except ValueError:
        return Option.none()

parse_arrow = Kleisli(safe_parse_int)
cat_with_parse = kleisli_cat.add_arrow('parse_int', 'String', 'Int', parse_arrow)

# Add validation arrow: Int -> Option[Bool]
def is_positive(n: int) -> Option[bool]:
    return Option.some(n > 0)

validate_arrow = Kleisli(is_positive)
cat_with_validate = cat_with_parse.add_arrow('is_positive', 'Int', 'Bool', validate_arrow)

# Compose arrows
final_cat = cat_with_validate.compose_arrows('is_positive', 'parse_int', 'parse_and_validate')

print("\nTesting Composed Arrow:")
composed = final_cat.arrows['parse_and_validate']

test_cases = ["42", "-5", "0", "invalid", "100"]
for test_input in test_cases:
    result = composed(test_input)
    print(f"  parse_and_validate('{test_input}') = {result}")

print("\n4. Email Validation Pipeline")

result_cat = kleisli_category_for('Result', ['String', 'Email', 'User'])

def validate_email(s: str) -> Result[str, str]:
    if '@' in s and '.' in s.split('@')[1]:
        return Result.ok(s)
    else:
        return Result.err(f"Invalid email format: {s}")

def create_user(email: str) -> Result[dict, str]:
    return Result.ok({
        'email': email,
        'id': hash(email) % 10000,
        'status': 'active'
    })

# Build validation pipeline
email_arrow = Kleisli(validate_email)
user_arrow = Kleisli(create_user)

pipeline_cat = (result_cat
    .add_arrow('validate_email', 'String', 'Email', email_arrow)
    .add_arrow('create_user', 'Email', 'User', user_arrow)
    .compose_arrows('create_user', 'validate_email', 'email_to_user'))

email_pipeline = pipeline_cat.arrows['email_to_user']

test_emails = [
    "user@example.com",
    "invalid-email",
    "another@test.org",
]

for email in test_emails:
    result = email_pipeline(email)
    if result.is_ok():
        user = result.value
        print(f"  {email} → User(id={user['id']})")
    else:
        error = result.error
        print(f"  {email} → Error: {error}")

print("\n" + "=" * 30)
print("Features shown:")
print("- Limits (terminal objects, products, equalizers)")
print("- Adjunctions with law checking")
print("- Kleisli categories for registered monads")
print("- Real-world validation pipelines")
print("\nDone!")
