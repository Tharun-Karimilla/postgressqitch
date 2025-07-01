Sqitch Deployment and Rollback Guide
====================================

Overview
--------
This document outlines the deployment and rollback procedures using Sqitch for a single-schema PostgreSQL project. It includes required conventions, steps, best practices, and manual tasks to ensure smooth database version control and delivery.

Directory Structure
-------------------
A typical Sqitch project for a single schema will follow this structure:

project-root/
├── sqitch.plan
├── sqitch.conf
├── deploy/
│   └── change-name.sql
├── revert/
│   └── change-name.sql
├── verify/
│   └── change-name.sql

All change scripts must have corresponding deploy, revert, and optionally verify files.

Initial Setup
-------------
Run the following command to initialize the Sqitch project:

    sqitch init my_project --engine pg

This creates the Sqitch configuration files and sets up the basic directory structure.

Creating Changes
----------------
To add a change to your project:

    sqitch add create_users_table -n "Create users table"

This creates three SQL files:
- deploy/create_users_table.sql
- revert/create_users_table.sql
- verify/create_users_table.sql

You must manually edit these scripts to define your logic.

Specifying Dependencies
-----------------------
To define dependencies between changes (within the same schema):

    sqitch add add_profile_column -n "Add column to users" --requires create_users_table

Dependencies should also be reflected in the `sqitch.plan` file. This ensures correct ordering during deployment.

Deployment Process
------------------
Sqitch deploys only unapplied changes. It checks the `sqitch.changes` table in the target database to determine what is already deployed.

1. Ensure the target database is accessible and the required credentials are available.
2. Run:

       sqitch deploy db:pg://user:pass@host:port/dbname

3. Sqitch will:
   - Check the `sqitch.plan`
   - Compare it with the `sqitch.changes` table
   - Apply new changes in order
   - Run associated verify scripts (if present)

If any deploy or verify step fails, the deployment halts.

Rollback Process
----------------
To rollback the last applied change:

    sqitch revert db:pg://user:pass@host:port/dbname

To rollback to a specific change:

    sqitch revert db:pg://user:pass@host:port/dbname --to change_name

To rollback everything:

    sqitch revert db:pg://user:pass@host:port/dbname --to @ROOT

You can also tag deployments:

    sqitch tag v1.0.0 -n "Initial production release"

Then revert to that tag if needed:

    sqitch revert db:pg://user:pass@host:port/dbname --to @v1.0.0

Verification
------------
Each change can have an optional `verify` script that is run after deployment. This is useful to assert presence of tables, columns, constraints, etc.

Best Practices
--------------
- Always include revert and verify scripts.
- Use `IF NOT EXISTS` and `IF EXISTS` conditions to make deploy and revert scripts idempotent.
- Use `sqitch status` to inspect what has and hasn't been deployed.
- Use `sqitch verify` to validate applied changes.
- Keep the `sqitch.plan` file in logical order; dependencies can override strict sequence.

Pre-Deployment Checks
---------------------
Before deploying to any environment:

1. Lint for missing or incorrect dependencies.
2. Check for any circular references in the plan.
3. Validate that the scripts conform to SQL syntax and standards.
4. Run `sqitch verify` locally on a test instance.
5. Confirm credentials and permissions are set up correctly for the deployment target.

Manual Intervention
-------------------
Occasionally manual steps are required:

- Creating the database and assigning correct roles before first deployment.
- Cleaning up failed deployments using `sqitch revert` if needed.
- Investigating conflicts or changes not reflected correctly due to out-of-band DB changes.

Environment Management
----------------------
Use environment variables or configuration secrets for database credentials. Never commit sensitive values.

Typical deployment URL format:

    db:pg://user:pass@host:port/dbname

Automated Deployment with CI/CD
-------------------------------
Sqitch can be integrated into GitHub Actions or other CI/CD tools.

Ensure the following:
- The database is reachable from the runner.
- Secrets are correctly configured in the CI platform.
- A pre-deploy lint step is run to ensure plan consistency.
- Tagging and rollback policies are enforced as needed.

Useful Commands
---------------
- `sqitch deploy` - Apply new changes.
- `sqitch revert` - Undo applied changes.
- `sqitch status` - See what is deployed or pending.
- `sqitch verify` - Validate applied changes.
- `sqitch log` - View deployment history.
- `sqitch tag` - Mark versions in the plan.

Conclusion
----------
Sqitch provides a robust mechanism for managing PostgreSQL database versioning with full traceability. Following these procedures will ensure safe and auditable deployments across environments.

