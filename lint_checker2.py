import os
import re
import sqlparse
from collections import defaultdict
from sqlparse.sql import Identifier, IdentifierList, Function, Parenthesis
from sqlparse.tokens import Keyword, DDL, Name


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
    content = str(paren_token)[1:-1]
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


def build_reference_map(steps, what='columns'):
    definition_map = defaultdict(set)
    for step in steps:
        path = os.path.join("deploy", f"{step}.sql")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            sql = f.read()
            tables, columns = extract_identifiers(sql)
            if what == 'columns':
                definition_map[step] = columns
            else:
                definition_map[step] = tables
    return definition_map


def find_missing_column_requires(steps, dependencies, column_defs):
    warnings = []
    for i, step in enumerate(steps):
        if step not in column_defs:
            continue
        for column in column_defs[step]:
            for j in range(i):
                prev_step = steps[j]
                if column in column_defs[prev_step]:
                    if prev_step not in dependencies.get(step, []):
                        warnings.append((step, column, prev_step))
    return warnings


plan_file = "sqitch.plan"
steps, dependencies = read_plan(plan_file)
column_defs = build_reference_map(steps, what="columns")
missing_column_reqs = find_missing_column_requires(steps, dependencies, column_defs)
missing_column_reqs[:10]  # preview

