#!/usr/bin/env python3
"""
LambdaCat Stretch Features Demo

This script demonstrates the advanced category theory features in LambdaCat:
1. Limits and colimits in finite categories
2. Adjunctions with law checking
3. Kleisli category builder for registered monads

Run with: python examples/stretch_features_demo.py
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

print("🚀 LambdaCat Stretch Features Demo")
print("=" * 50)

# ============================================================================
# 1. LIMITS AND COLIMITS IN FINITE CATEGORIES
# ============================================================================

print("\n1️⃣ LIMITS IN FINITE CATEGORIES")
print("-" * 30)

from LambdaCat.core import (
    product, equalizer, terminal_object, initial_object,
    obj, arrow, build_presentation, Cat
)
from LambdaCat.core.standard import discrete, terminal_category

# Terminal objects
print("🎯 Terminal Objects:")
C = terminal_category()
terminal = terminal_object(C)
print(f"   Terminal object in terminal category: {terminal}")

D = discrete(["A", "B", "C"])
terminal_discrete = terminal_object(D)
print(f"   Terminal object in discrete category: {terminal_discrete}")

# Products
print("\n📦 Products:")
prod_AA = product(D, "A", "A")
print(f"   Product A×A in discrete category: {prod_AA.cone.apex if prod_AA else 'None'}")

prod_AB = product(D, "A", "B") 
print(f"   Product A×B in discrete category: {prod_AB.cone.apex if prod_AB else 'None'}")

# Equalizers  
print("\n⚖️ Equalizers:")
A, B = obj("A"), obj("B")
f = arrow("f", "A", "B")
g = arrow("g", "A", "B")

p = build_presentation([A, B], [f, g])
E = Cat.from_presentation(p)

eq_same = equalizer(E, "f", "f")  # f = f
print(f"   Equalizer of f with itself: {eq_same.cone.apex if eq_same else 'None'}")

eq_different = equalizer(E, "f", "g")  # f ≠ g (likely)
print(f"   Equalizer of f and g: {eq_different.cone.apex if eq_different else 'None'}")

# ============================================================================
# 2. ADJUNCTIONS WITH LAW CHECKING
# ============================================================================

print("\n2️⃣ ADJUNCTIONS")
print("-" * 15)

from LambdaCat.core import (
    Adjunction, ADJUNCTION_SUITE, free_forgetful_adjunction, run_suite
)

print("🔗 Free-Forgetful Adjunction:")
adj = free_forgetful_adjunction()
print(f"   Adjunction: {adj}")
print(f"   Left adjoint (Free): {adj.left.name}")
print(f"   Right adjoint (Forget): {adj.right.name}")

print("\n⚖️ Adjunction Laws:")
report = run_suite(adj, ADJUNCTION_SUITE)
print(f"   Overall result: {'✅ PASS' if report.ok else '❌ FAIL'}")

for result in report.results:
    status = '✅ PASS' if result.passed else '❌ FAIL'
    print(f"   {result.law}: {status} ({len(result.violations)} violations)")
    
    # Show first violation if any
    if result.violations:
        print(f"      └─ {result.violations[0].message}")

# ============================================================================
# 3. KLEISLI CATEGORY BUILDER
# ============================================================================

print("\n3️⃣ KLEISLI CATEGORY BUILDER")
print("-" * 28)

from LambdaCat.core.fp import (
    kleisli_category_for, get_registered_monads, 
    register_monad, KleisliCat, Kleisli
)
from LambdaCat.core.fp.instances.option import Option
from LambdaCat.core.fp.instances.result import Result

print("📝 Registered Monads:")
registered = get_registered_monads()
for name in sorted(registered.keys()):
    print(f"   ✓ {name}")

print("\n🏗️ Building Kleisli Category:")
kleisli_cat = kleisli_category_for('Option', ['String', 'Int', 'Bool'])
print(f"   Base category: {kleisli_cat}")

# Add safe parsing arrow: String -> Option[Int]
def safe_parse_int(s: str) -> Option[int]:
    """Safely parse string to integer."""
    try:
        return Option.some(int(s))
    except ValueError:
        return Option.none()

parse_arrow = Kleisli(safe_parse_int)
cat_with_parse = kleisli_cat.add_arrow('parse_int', 'String', 'Int', parse_arrow)
print(f"   + parse_int arrow: {cat_with_parse}")

# Add validation arrow: Int -> Option[Bool]
def is_positive(n: int) -> Option[bool]:
    """Check if number is positive."""
    return Option.some(n > 0)

validate_arrow = Kleisli(is_positive)
cat_with_validate = cat_with_parse.add_arrow('is_positive', 'Int', 'Bool', validate_arrow)
print(f"   + is_positive arrow: {cat_with_validate}")

# Compose arrows: String -> Option[Int] -> Option[Bool]
final_cat = cat_with_validate.compose_arrows('is_positive', 'parse_int', 'parse_and_validate')
print(f"   + Composed arrow: {final_cat}")

print("\n🧪 Testing Composed Kleisli Arrow:")
composed = final_cat.arrows['parse_and_validate']

test_cases = ["42", "-5", "0", "invalid", "100"]
for test_input in test_cases:
    result = composed(test_input)
    print(f"   parse_and_validate('{test_input}') = {result}")

# ============================================================================
# 4. REAL-WORLD EXAMPLE: VALIDATION PIPELINE
# ============================================================================

print("\n4️⃣ REAL-WORLD EXAMPLE: VALIDATION PIPELINE")
print("-" * 45)

# Create a more complex validation pipeline using Result monad
result_cat = kleisli_category_for('Result', ['String', 'Email', 'User'])

# Email validation
def validate_email(s: str) -> Result[str, str]:
    """Validate email format."""
    if '@' in s and '.' in s.split('@')[1]:
        return Result.ok(s)
    else:
        return Result.err(f"Invalid email format: {s}")

# User creation
def create_user(email: str) -> Result[dict, str]:
    """Create user from validated email."""
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

print("📧 Email Validation Pipeline:")
email_pipeline = pipeline_cat.arrows['email_to_user']

test_emails = [
    "user@example.com",
    "invalid-email",
    "another@test.org",
    "bad@format",
    "good@domain.co.uk"
]

for email in test_emails:
    result = email_pipeline(email)
    if result.is_ok():
        user = result.value  # Access the internal value
        print(f"   ✅ {email} → User(id={user['id']}, status={user['status']})")
    else:
        error = result.error  # Access the internal error
        print(f"   ❌ {email} → Error: {error}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 50)
print("🎉 STRETCH FEATURES SUMMARY")
print("=" * 50)

print("""
✅ LIMITS & COLIMITS:
   • Terminal/initial objects in finite categories
   • Products and equalizers with universality checking
   • Fail-fast validation for malformed inputs

✅ ADJUNCTIONS:
   • Complete adjunction framework with unit/counit
   • Triangle identity laws with detailed violation reporting
   • Free-forgetful adjunction example

✅ KLEISLI CATEGORIES:
   • Auto-registration of common monads (Option, Result, State, etc.)
   • Dynamic category construction with arrow addition
   • Monadic composition with type safety

🎯 REAL-WORLD APPLICATIONS:
   • Validation pipelines with error handling
   • Computation chains with effects
   • Mathematical modeling and research

All features maintain LambdaCat's core principles:
• Fail-fast (no silent fallbacks)
• Strong typing (mypy --strict)
• Functional design (immutable, composable)
• Law verification (mathematical correctness)
""")

print("🚀 LambdaCat: Complete category theory toolkit for Python!")
