import os
import re
import sqlparse
import argparse
from collections import defaultdict
from sqlparse.sql import Identifier, Parenthesis
from sqlparse.tokens import Keyword, Name, DDL

def normalize_table(table_name, default_schema="public"):
    return table_name if "." in table_name else f"{default_schema}.{table_name}"

def extract_identifiers(sql):
    tables = set()
    columns = set()

    parsed = sqlparse.parse(sql)
    for stmt in parsed:
        tokens = [t for t in stmt.tokens if not t.is_whitespace]
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.ttype is DDL and token.value.upper() == "CREATE":
                if i + 2 < len(tokens) and tokens[i + 1].match(Keyword, "TABLE"):
                    table_token = tokens[i + 2]
                    if isinstance(table_token, Identifier):
                        tables.add(table_token.get_name().lower())
                    elif table_token.ttype is Name:
                        tables.add(table_token.value.lower())
                    # Extract columns
                    for j in range(i + 3, len(tokens)):
                        if isinstance(tokens[j], Parenthesis):
                            columns.update(extract_columns_from_parens(tokens[j]))
                            break
            elif token.ttype is Keyword and token.value.upper() == "ON":
                if i + 1 < len(tokens):
                    on_target = tokens[i + 1]
                    if isinstance(on_target, Identifier):
                        tables.add(on_target.get_real_name().lower())
            i += 1
    return tables, columns

def extract_columns_from_parens(paren_token):
    columns = set()
    if not isinstance(paren_token, Parenthesis):
        return columns
    content = str(paren_token)[1:-1]  # Strip surrounding ()
    lines = [line.strip().split()[0] for line in content.strip().splitlines() if line and not line.startswith("--")]
    for col in lines:
        if col:
            col_clean = col.replace(",", "").strip('"').lower()
            if col_clean.upper() not in {"PRIMARY", "UNIQUE", "KEY", "CONSTRAINT"}:
                columns.add(col_clean)
    return columns

def read_plan(plan_file):
    steps = []
    dependencies = {}
    with open(plan_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%') or line.startswith('#'):
                continue
            parts = line.split()
            name = parts[0]
            deps = []
            if '[' in line:
                match = re.search(r'\[(.*?)\]', line)
                if match:
                    deps = match.group(1).split()
            steps.append(name)
            dependencies[name] = deps
    return steps, dependencies

def build_usage_maps(steps):
    used_tables = defaultdict(set)
    defined_tables = defaultdict(set)

    for step in steps:
        path = os.path.join("deploy", f"{step}.sql")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            sql = f.read()
            tables, _ = extract_identifiers(sql)
            for table in tables:
                if "create table" in sql.lower() and table in sql.lower():
                    defined_tables[step].add(table)
                else:
                    used_tables[step].add(table)
    return used_tables, defined_tables

def find_missing_requires(steps, dependencies, used_tables, defined_tables):
    warnings = []

    table_to_step = {}
    for step, tables in defined_tables.items():
        for table in tables:
            table_to_step[table] = step

    for step in steps:
        for table in used_tables[step]:
            if table in table_to_step:
                definer = table_to_step[table]
                if definer != step and definer not in dependencies.get(step, []):
                    warnings.append((step, table, definer))

    return warnings

def check_invalid_dependency_order(steps, dependencies):
    errors = []
    step_indices = {step: i for i, step in enumerate(steps)}
    for step, deps in dependencies.items():
        step_index = step_indices.get(step, -1)
        for dep in deps:
            dep_index = step_indices.get(dep, -1)
            if dep_index > step_index:
                errors.append((step, dep, "Declared too early (appears later in plan)"))
    return errors

def detect_untracked_scripts(steps, deploy_dir="deploy"):
    plan_scripts = set(steps)
    actual_scripts = set(f[:-4] for f in os.listdir(deploy_dir) if f.endswith(".sql"))
    missing_in_plan = actual_scripts - plan_scripts
    extra_in_plan = plan_scripts - actual_scripts
    return sorted(missing_in_plan), sorted(extra_in_plan)

def topological_sort(dependencies, steps):
    visited, result, temp = set(), [], set()

    def visit(node):
        if node in temp:
            raise Exception(f"Cycle detected involving {node}")
        if node not in visited:
            temp.add(node)
            for dep in dependencies.get(node, []):
                visit(dep)
            temp.remove(node)
            visited.add(node)
            result.append(node)

    for step in steps:
        if step not in visited:
            visit(step)
    return result


def main():
    parser = argparse.ArgumentParser(description="Lint SQL deployment plan")
    parser.add_argument('--plan_file', type=str, default='sqitch.plan', help='Path to the Sqitch plan file')
    args = parser.parse_args()
    plan_file = args.plan_file

    steps, dependencies = read_plan(plan_file)

    used_tables, defined_tables = build_usage_maps(steps)
    missing_requires = find_missing_requires(steps, dependencies, used_tables, defined_tables)
    dependency_order_errors = check_invalid_dependency_order(steps, dependencies)
    missing_in_plan, extra_in_plan = detect_untracked_scripts(steps)

    print("\n=== Missing Requires ===")
    for step, table, definer in missing_requires:
        if table.startswith("app."):  # Suppress warnings for app.* tables
            continue
        print(f"{step} uses table '{table}' defined in {definer} but does not list it as a dependency.")

    print("\n=== Incorrect Dependency Order in sqitch.plan ===")
    for step, dep, reason in dependency_order_errors:
        print(f"{step} declares dependency on {dep}, which appears later in the plan. {reason}")

    filtered_missing = [m for m in missing_in_plan if not m.startswith("app.")]
    if filtered_missing:
        print("\n Scripts present in `deploy/` but missing from `sqitch.plan`:")
        for m in filtered_missing:
            print(f"  - {m}.sql")

    if extra_in_plan:
        print("\n Scripts in `sqitch.plan` but missing in `deploy/` folder:")
        for e in extra_in_plan:
            print(f"  - {e}")

    try:
        corrected_order = topological_sort(dependencies, steps)
        if corrected_order != steps:
            print("\n Suggested corrected order of `sqitch.plan` based on dependencies:")
            for step in corrected_order:
                print(f"  {step}")
    except Exception as e:
        print(f"\n Error resolving plan order: {e}")

if __name__ == "__main__":
    main()
