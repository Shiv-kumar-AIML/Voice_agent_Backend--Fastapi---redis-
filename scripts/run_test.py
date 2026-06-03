import difflib, py_compile, sys

query = 'capcisum'
products = [
    'CAPSICUM GREEN PER KG',
    'CAPSICUM RED PER KG',
    'CAPSICUM YELLOW PER KG',
    'CARROT WASHED PER 500G',
    'APPLES GREEN PER KG',
    'COKE CTN',
]

def score(query, name):
    q = query.lower()
    n = name.lower()
    full = difflib.SequenceMatcher(None, q, n).ratio()
    tokens = n.split()
    word = max((difflib.SequenceMatcher(None, q, t).ratio() for t in tokens), default=0)
    return max(full, word)

results = [(round(score(query, p), 3), p) for p in products]
results.sort(reverse=True)
for s, n in results:
    print(f'{"PASS" if s >= 0.4 else "FAIL"} {s:.3f}  {n}')

print()
files = [
    'main.py', 'api/customer.py', 'api/products.py',
    'api/cart.py', 'api/order.py', 'services/resolver_service.py',
    'models/schemas.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK  {f}')
    except py_compile.PyCompileError as e:
        print(f'ERR {f}: {e}')
        sys.exit(1)
print('\nAll syntax OK')
