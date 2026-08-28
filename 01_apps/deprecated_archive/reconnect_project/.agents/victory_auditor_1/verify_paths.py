import os
import re

monorepo_root = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo'
target_file = os.path.join(monorepo_root, '01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md')

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract paths in backticks or markdown tables
path_candidates = re.findall(r'`([a-zA-Z0-9_\-./]+(?:\.[a-zA-Z0-9]+|/))`', content)
for match in re.finditer(r'`(0[0-9]_[a-zA-Z0-9_\-./]+|scripts/[a-zA-Z0-9_\-./]+|1[0-2]_[a-zA-Z0-9_\-./]+)`', content):
    path_candidates.append(match.group(1))

# Filter candidates to relative paths within monorepo
monorepo_paths = set()
for p in path_candidates:
    p_clean = p.strip().strip('`').strip('"').strip("'")
    if any(p_clean.startswith(prefix) for prefix in ['00_', '01_', '02_', '03_', '04_', '05_', '06_', '07_', '10_', '11_', '12_', 'scripts/']):
        monorepo_paths.add(p_clean)

print(f'Total monorepo path candidates found: {len(monorepo_paths)}')

results = {'exists': [], 'missing': []}
for p in sorted(monorepo_paths):
    full_path = os.path.join(monorepo_root, p)
    check_path = full_path.rstrip('/')
    if os.path.exists(check_path):
        results['exists'].append(p)
    else:
        results['missing'].append(p)

print('\n--- PATH VERIFICATION RESULTS ---')
print(f'Verified existing: {len(results["exists"])}')
for p in results['exists']:
    print(f'  [PASS] {p}')

if results['missing']:
    print(f'\nUnresolved / Missing paths: {len(results["missing"])}')
    for p in results['missing']:
        print(f'  [MISSING] {p}')
else:
    print('\nALL referenced monorepo paths exist on disk!')
