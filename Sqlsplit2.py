import os
import re

def split_migra_sql(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r') as f:
        sql_text = f.read()

    # Normalize line endings
    sql_text = sql_text.replace('\r\n', '\n')

    # Split SQL by semicolon followed by optional whitespace and newline (simple heuristic)
    statements = re.split(r';\s*\n', sql_text)

    # Regex to detect statement components (action, object type, object name)
    statement_regex = re.compile(
        r'^(CREATE|ALTER|DROP|COMMENT|GRANT|REVOKE|SET)\s+'
        r'(EXTENSION|ROLE|DATABASE|SCHEMA|TABLE|INDEX|VIEW|MATERIALIZED VIEW|SEQUENCE|FUNCTION|TRIGGER|TYPE|DOMAIN|AGGREGATE|COLUMN|TABLESPACE|USER|CAST|LANGUAGE|CONVERSION|FOREIGN DATA WRAPPER|SERVER|USER MAPPING|EVENT TRIGGER|POLICY|PUBLICATION|SUBSCRIPTION|STATISTICS|TEXT SEARCH CONFIGURATION|TEXT SEARCH DICTIONARY|TEXT SEARCH PARSER|TEXT SEARCH TEMPLATE|TRANSFORMATION|COLLATION|FAMILY|TABLESPACE)?\s*'
        r'"?([\w\.\-]+)"?', re.IGNORECASE)

    counter = 1
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        match = statement_regex.match(stmt)
        if match:
            action = match.group(1).upper()
            obj_type = (match.group(2) or 'UNKNOWN').upper()
            obj_name = (match.group(3) or f'statement_{counter}').replace('.', '_').replace('-', '_')
            filename_prefix = f"{action}_{obj_type}_{obj_name}"
        else:
            filename_prefix = f"statement_{counter}"

        filename = os.path.join(output_dir, f"{filename_prefix}_{counter}.sql")

        # Ensure statement ends with semicolon plus newline
        statement_to_write = stmt
        if not stmt.endswith(';'):
            statement_to_write += ';'
        statement_to_write += '\n'

        with open(filename, 'w') as out_file:
            out_file.write(statement_to_write)

        counter += 1

if __name__ == "__main__":
    migra_output_file = "migra_output.sql"  # Change to your migra output filename
    output_folder = "migra_statements"     # Output directory for split files

    split_migra_sql(migra_output_file, output_folder)
    print(f"Splitting complete. Files saved in folder: {output_folder}")
    
