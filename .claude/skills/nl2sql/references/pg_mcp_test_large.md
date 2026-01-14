# pg_mcp_test_large Database Reference

A large ERP (Enterprise Resource Planning) database covering HR, Finance, Inventory, CRM, and Project Management.

## Connection Info

- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: (empty)
- **Database**: pg_mcp_test_large

## Schema: erp

### Module Overview

The ERP system is organized into functional modules:

1. **HR Module**: departments, positions, employees, skills, attendance, leave management
2. **Finance Module**: accounts, journal entries, vendors, invoices, expense reports
3. **Inventory Module**: warehouses, products, stock levels, inventory movements
4. **CRM Module**: customers, contacts, leads, opportunities, tickets
5. **Project Module**: projects, tasks, time entries, project members

---

## HR Module Tables

#### erp.departments
Organizational departments with hierarchy.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Department name |
| code | varchar | NO | | Unique dept code |
| parent_id | integer | YES | | FK to departments.id |
| manager_id | integer | YES | | FK to employees.id |
| budget | numeric | YES | | Annual budget |
| cost_center | varchar | YES | | Cost center code |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.positions
Job positions/titles.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| title | varchar | NO | | Position title |
| department_id | integer | YES | | FK to departments.id |
| min_salary | numeric | YES | | Minimum salary |
| max_salary | numeric | YES | | Maximum salary |
| description | text | YES | | Job description |
| requirements | text | YES | | Job requirements |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.employees
Employee records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| employee_number | varchar | NO | | Unique employee ID |
| first_name | varchar | NO | | First name |
| last_name | varchar | NO | | Last name |
| email | varchar | NO | | Email address |
| phone | varchar | YES | | Phone number |
| hire_date | date | NO | | Hire date |
| birth_date | date | YES | | Birth date |
| department_id | integer | YES | | FK to departments.id |
| position_id | integer | YES | | FK to positions.id |
| manager_id | integer | YES | | FK to employees.id |
| employment_status | employment_status | YES | 'active' | Status |
| employment_type | employment_type | YES | 'full_time' | Type |
| salary | numeric | YES | | Current salary |
| address | text | YES | | Home address |
| city | varchar | YES | | City |
| country | varchar | YES | | Country |
| emergency_contact_name | varchar | YES | | Emergency contact |
| emergency_contact_phone | varchar | YES | | Emergency phone |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |

#### erp.skills
Skill definitions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Skill name |
| category | varchar | YES | | Skill category |
| description | text | YES | | Description |

#### erp.employee_skills
Junction table for employee skills.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| employee_id | integer | NO | | FK to employees.id |
| skill_id | integer | NO | | FK to skills.id |
| proficiency_level | integer | YES | | 1-5 proficiency |
| years_experience | numeric | YES | | Years of experience |
| certified | boolean | YES | false | Has certification |

Primary Key: (employee_id, skill_id)

#### erp.attendance
Daily attendance records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| employee_id | integer | NO | | FK to employees.id |
| work_date | date | NO | | Work date |
| check_in | time | YES | | Check-in time |
| check_out | time | YES | | Check-out time |
| hours_worked | numeric | YES | | Hours worked |
| overtime_hours | numeric | YES | 0 | Overtime hours |
| notes | text | YES | | Notes |

#### erp.leave_balances
Employee leave entitlements.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| employee_id | integer | NO | | FK to employees.id |
| leave_type | leave_type | NO | | Type of leave |
| year | integer | NO | | Year |
| entitled_days | numeric | NO | | Days entitled |
| used_days | numeric | YES | 0 | Days used |
| pending_days | numeric | YES | 0 | Days pending |

#### erp.leave_requests
Leave request records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| employee_id | integer | NO | | FK to employees.id |
| leave_type | leave_type | NO | | Type of leave |
| start_date | date | NO | | Start date |
| end_date | date | NO | | End date |
| days_requested | numeric | NO | | Days requested |
| reason | text | YES | | Reason |
| status | leave_status | YES | 'pending' | Request status |
| approved_by | integer | YES | | FK to employees.id |
| approved_at | timestamptz | YES | | Approval time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

---

## Finance Module Tables

#### erp.accounts
Chart of accounts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| account_number | varchar | NO | | Account number |
| name | varchar | NO | | Account name |
| account_type | account_type | NO | | Account type |
| parent_id | integer | YES | | FK to accounts.id |
| description | text | YES | | Description |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.fiscal_periods
Accounting periods.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Period name |
| start_date | date | NO | | Start date |
| end_date | date | NO | | End date |
| is_closed | boolean | YES | false | Closed status |
| closed_at | timestamptz | YES | | Close time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.journal_entries
General ledger entries.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| entry_number | varchar | NO | | Entry number |
| fiscal_period_id | integer | YES | | FK to fiscal_periods.id |
| entry_date | date | NO | | Entry date |
| description | text | YES | | Description |
| reference | varchar | YES | | Reference |
| is_posted | boolean | YES | false | Posted status |
| posted_by | integer | YES | | FK to employees.id |
| posted_at | timestamptz | YES | | Post time |
| created_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.journal_lines
Line items in journal entries.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| entry_id | integer | NO | | FK to journal_entries.id |
| account_id | integer | NO | | FK to accounts.id |
| transaction_type | transaction_type | NO | | debit/credit |
| amount | numeric | NO | | Amount |
| description | text | YES | | Description |
| cost_center | varchar | YES | | Cost center |

#### erp.vendors
Vendor/supplier records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| code | varchar | NO | | Unique vendor code |
| name | varchar | NO | | Vendor name |
| contact_name | varchar | YES | | Contact person |
| email | varchar | YES | | Email |
| phone | varchar | YES | | Phone |
| address | text | YES | | Address |
| city | varchar | YES | | City |
| country | varchar | YES | | Country |
| tax_id | varchar | YES | | Tax ID |
| payment_terms | integer | YES | 30 | Payment terms (days) |
| account_id | integer | YES | | FK to accounts.id |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.purchase_orders
Purchase order headers.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| po_number | varchar | NO | | PO number |
| vendor_id | integer | NO | | FK to vendors.id |
| order_date | date | NO | | Order date |
| expected_date | date | YES | | Expected delivery |
| subtotal | numeric | NO | | Subtotal |
| tax_amount | numeric | YES | 0 | Tax amount |
| total_amount | numeric | NO | | Total amount |
| status | varchar | YES | 'draft' | PO status |
| approved_by | integer | YES | | FK to employees.id |
| notes | text | YES | | Notes |
| created_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.purchase_order_items
PO line items.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| po_id | integer | NO | | FK to purchase_orders.id |
| product_code | varchar | YES | | Product code |
| description | varchar | NO | | Description |
| quantity | numeric | NO | | Quantity ordered |
| unit_price | numeric | NO | | Unit price |
| total_price | numeric | NO | | Line total |
| received_quantity | numeric | YES | 0 | Qty received |

#### erp.invoices
Invoices (AP and AR).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| invoice_number | varchar | NO | | Invoice number |
| invoice_type | varchar | NO | | AP or AR |
| vendor_id | integer | YES | | FK to vendors.id (AP) |
| customer_id | integer | YES | | FK to customers.id (AR) |
| invoice_date | date | NO | | Invoice date |
| due_date | date | NO | | Due date |
| subtotal | numeric | NO | | Subtotal |
| tax_amount | numeric | YES | 0 | Tax amount |
| total_amount | numeric | NO | | Total amount |
| paid_amount | numeric | YES | 0 | Amount paid |
| status | invoice_status | YES | 'draft' | Invoice status |
| po_id | integer | YES | | FK to purchase_orders.id |
| notes | text | YES | | Notes |
| created_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.invoice_lines
Invoice line items.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| invoice_id | integer | NO | | FK to invoices.id |
| account_id | integer | YES | | FK to accounts.id |
| description | varchar | NO | | Description |
| quantity | numeric | NO | | Quantity |
| unit_price | numeric | NO | | Unit price |
| total_price | numeric | NO | | Line total |

#### erp.expense_reports
Employee expense reports.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| report_number | varchar | NO | | Report number |
| employee_id | integer | NO | | FK to employees.id |
| report_date | date | NO | | Report date |
| total_amount | numeric | NO | | Total amount |
| status | expense_status | YES | 'pending' | Report status |
| approved_by | integer | YES | | FK to employees.id |
| approved_at | timestamptz | YES | | Approval time |
| paid_at | timestamptz | YES | | Payment time |
| notes | text | YES | | Notes |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.expense_items
Expense report line items.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| report_id | integer | NO | | FK to expense_reports.id |
| expense_date | date | NO | | Expense date |
| category | varchar | NO | | Expense category |
| description | varchar | YES | | Description |
| amount | numeric | NO | | Amount |
| receipt_url | varchar | YES | | Receipt URL |
| account_id | integer | YES | | FK to accounts.id |

---

## Inventory Module Tables

#### erp.warehouses
Warehouse locations.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| code | varchar | NO | | Warehouse code |
| name | varchar | NO | | Warehouse name |
| warehouse_type | warehouse_type | YES | 'main' | Type |
| address | text | YES | | Address |
| city | varchar | YES | | City |
| country | varchar | YES | | Country |
| manager_id | integer | YES | | FK to employees.id |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.product_categories
Product categories.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Category name |
| code | varchar | NO | | Category code |
| parent_id | integer | YES | | FK to product_categories.id |
| description | text | YES | | Description |

#### erp.products
Product master data.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| sku | varchar | NO | | Unique SKU |
| name | varchar | NO | | Product name |
| category_id | integer | YES | | FK to product_categories.id |
| unit_of_measure | varchar | YES | 'unit' | UoM |
| unit_cost | numeric | YES | | Unit cost |
| unit_price | numeric | YES | | Unit price |
| min_stock_level | integer | YES | 0 | Min stock |
| max_stock_level | integer | YES | | Max stock |
| reorder_point | integer | YES | | Reorder point |
| reorder_quantity | integer | YES | | Reorder quantity |
| weight_kg | numeric | YES | | Weight |
| dimensions | varchar | YES | | Dimensions |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.stock_levels
Stock by warehouse.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| product_id | integer | NO | | FK to products.id |
| warehouse_id | integer | NO | | FK to warehouses.id |
| quantity_on_hand | numeric | NO | 0 | On-hand quantity |
| quantity_reserved | numeric | NO | 0 | Reserved quantity |
| quantity_on_order | numeric | NO | 0 | On-order quantity |
| last_count_date | date | YES | | Last count date |
| bin_location | varchar | YES | | Bin location |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |

#### erp.inventory_movements
Inventory transactions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| movement_number | varchar | NO | | Movement number |
| movement_type | movement_type | NO | | Movement type |
| product_id | integer | NO | | FK to products.id |
| from_warehouse_id | integer | YES | | Source warehouse |
| to_warehouse_id | integer | YES | | Destination warehouse |
| quantity | numeric | NO | | Quantity moved |
| unit_cost | numeric | YES | | Unit cost |
| reference_type | varchar | YES | | Reference type |
| reference_id | integer | YES | | Reference ID |
| notes | text | YES | | Notes |
| performed_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

---

## CRM Module Tables

#### erp.customers
Customer records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| customer_number | varchar | NO | | Customer number |
| company_name | varchar | NO | | Company name |
| industry | varchar | YES | | Industry |
| website | varchar | YES | | Website |
| phone | varchar | YES | | Phone |
| email | varchar | YES | | Email |
| address | text | YES | | Address |
| city | varchar | YES | | City |
| country | varchar | YES | | Country |
| account_manager_id | integer | YES | | FK to employees.id |
| credit_limit | numeric | YES | | Credit limit |
| payment_terms | integer | YES | 30 | Payment terms (days) |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.contacts
Customer contacts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| customer_id | integer | YES | | FK to customers.id |
| first_name | varchar | NO | | First name |
| last_name | varchar | NO | | Last name |
| title | varchar | YES | | Job title |
| email | varchar | YES | | Email |
| phone | varchar | YES | | Phone |
| mobile | varchar | YES | | Mobile |
| is_primary | boolean | YES | false | Primary contact |
| is_active | boolean | YES | true | Active status |
| notes | text | YES | | Notes |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.leads
Sales leads.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| company_name | varchar | YES | | Company name |
| contact_name | varchar | NO | | Contact name |
| email | varchar | YES | | Email |
| phone | varchar | YES | | Phone |
| source | varchar | YES | | Lead source |
| status | lead_status | YES | 'new' | Lead status |
| assigned_to | integer | YES | | FK to employees.id |
| estimated_value | numeric | YES | | Estimated value |
| notes | text | YES | | Notes |
| converted_customer_id | integer | YES | | FK to customers.id |
| converted_at | timestamptz | YES | | Conversion time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.opportunities
Sales opportunities.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Opportunity name |
| customer_id | integer | YES | | FK to customers.id |
| lead_id | integer | YES | | FK to leads.id |
| stage | opportunity_stage | YES | 'prospecting' | Sales stage |
| probability | integer | YES | | Win probability % |
| expected_amount | numeric | YES | | Expected amount |
| expected_close_date | date | YES | | Expected close date |
| assigned_to | integer | YES | | FK to employees.id |
| description | text | YES | | Description |
| won_reason | text | YES | | Won reason |
| lost_reason | text | YES | | Lost reason |
| closed_at | timestamptz | YES | | Close time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.activities
CRM activities (calls, meetings, etc.).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| activity_type | varchar | NO | | Activity type |
| subject | varchar | NO | | Subject |
| description | text | YES | | Description |
| customer_id | integer | YES | | FK to customers.id |
| contact_id | integer | YES | | FK to contacts.id |
| opportunity_id | integer | YES | | FK to opportunities.id |
| assigned_to | integer | YES | | FK to employees.id |
| due_date | timestamptz | YES | | Due date |
| completed_at | timestamptz | YES | | Completion time |
| created_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.tickets
Support tickets.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| ticket_number | varchar | NO | | Ticket number |
| customer_id | integer | NO | | FK to customers.id |
| contact_id | integer | YES | | FK to contacts.id |
| subject | varchar | NO | | Subject |
| description | text | YES | | Description |
| priority | ticket_priority | YES | 'medium' | Priority |
| status | ticket_status | YES | 'open' | Ticket status |
| assigned_to | integer | YES | | FK to employees.id |
| resolution | text | YES | | Resolution |
| first_response_at | timestamptz | YES | | First response time |
| resolved_at | timestamptz | YES | | Resolution time |
| closed_at | timestamptz | YES | | Close time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.ticket_comments
Ticket comments/responses.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| ticket_id | integer | NO | | FK to tickets.id |
| author_id | integer | YES | | FK to employees.id |
| is_internal | boolean | YES | false | Internal note |
| content | text | NO | | Comment content |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

---

## Project Module Tables

#### erp.projects
Project records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| project_code | varchar | NO | | Project code |
| name | varchar | NO | | Project name |
| description | text | YES | | Description |
| customer_id | integer | YES | | FK to customers.id |
| status | project_status | YES | 'planning' | Project status |
| priority | task_priority | YES | 'medium' | Priority |
| start_date | date | YES | | Start date |
| target_end_date | date | YES | | Target end date |
| actual_end_date | date | YES | | Actual end date |
| budget | numeric | YES | | Budget |
| actual_cost | numeric | YES | 0 | Actual cost |
| manager_id | integer | YES | | FK to employees.id |
| department_id | integer | YES | | FK to departments.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.project_members
Project team members.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| project_id | integer | NO | | FK to projects.id |
| employee_id | integer | NO | | FK to employees.id |
| role | varchar | YES | | Team role |
| allocated_hours | numeric | YES | | Allocated hours |
| start_date | date | YES | | Start date |
| end_date | date | YES | | End date |

Primary Key: (project_id, employee_id)

#### erp.tasks
Project tasks.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| project_id | integer | NO | | FK to projects.id |
| parent_id | integer | YES | | FK to tasks.id |
| name | varchar | NO | | Task name |
| description | text | YES | | Description |
| status | task_status | YES | 'todo' | Task status |
| priority | task_priority | YES | 'medium' | Priority |
| assigned_to | integer | YES | | FK to employees.id |
| estimated_hours | numeric | YES | | Estimated hours |
| actual_hours | numeric | YES | 0 | Actual hours |
| start_date | date | YES | | Start date |
| due_date | date | YES | | Due date |
| completed_at | timestamptz | YES | | Completion time |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### erp.time_entries
Time tracking entries.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| employee_id | integer | NO | | FK to employees.id |
| task_id | integer | YES | | FK to tasks.id |
| project_id | integer | YES | | FK to projects.id |
| entry_date | date | NO | | Entry date |
| hours | numeric | NO | | Hours logged |
| description | text | YES | | Description |
| is_billable | boolean | YES | true | Billable flag |
| is_approved | boolean | YES | false | Approved flag |
| approved_by | integer | YES | | FK to employees.id |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

---

## System Tables

#### erp.audit_log
System audit trail.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | auto | Primary key |
| table_name | varchar | NO | | Table modified |
| record_id | integer | NO | | Record ID |
| action | varchar | NO | | INSERT/UPDATE/DELETE |
| old_values | jsonb | YES | | Previous values |
| new_values | jsonb | YES | | New values |
| changed_by | integer | YES | | FK to employees.id |
| changed_at | timestamptz | YES | CURRENT_TIMESTAMP | Change time |
| ip_address | inet | YES | | Client IP |

#### erp.system_settings
System configuration.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| setting_key | varchar | NO | | Setting key |
| setting_value | text | YES | | Setting value |
| setting_type | varchar | YES | 'string' | Value type |
| description | text | YES | | Description |
| updated_by | integer | YES | | FK to employees.id |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |

---

## Views

#### erp.employee_directory
Employee contact information and org structure.

Columns: id, employee_number, full_name, email, phone, position, department, manager_name, employment_status, employment_type, hire_date, years_employed

#### erp.department_summary
Department statistics.

Columns: id, name, code, parent_department, manager, employee_count, budget, total_salaries, avg_salary

#### erp.account_balances
Account balances from journal entries.

Columns: id, account_number, name, account_type, total_debits, total_credits, balance

#### erp.vendor_summary
Vendor purchase and payment summary.

Columns: id, code, name, country, total_orders, total_order_value, paid_invoices, total_invoiced, outstanding_balance

#### erp.inventory_status
Inventory levels across warehouses.

Columns: id, sku, name, category, unit_of_measure, unit_cost, unit_price, total_on_hand, total_reserved, available, on_order, reorder_point, stock_status, inventory_value

#### erp.customer_summary
Customer overview with sales and support metrics.

Columns: id, customer_number, company_name, industry, country, account_manager, opportunity_count, won_revenue, invoice_count, total_invoiced, outstanding, open_tickets

#### erp.sales_pipeline
Sales pipeline by stage.

Columns: stage, opportunity_count, total_value, avg_probability, weighted_value

#### erp.ticket_statistics
Monthly ticket statistics.

Columns: month, total_tickets, critical_count, high_count, closed_count, avg_first_response_hours, avg_resolution_hours

#### erp.project_status_view
Project status with budget and progress.

Columns: id, project_code, name, customer, status, priority, manager, start_date, target_end_date, budget, actual_cost, budget_used_pct, total_tasks, completed_tasks, completion_pct, total_hours_logged

#### erp.employee_workload
Employee current workload.

Columns: id, name, department, active_tasks, active_projects, hours_last_week, pending_hours

#### erp.ar_aging
Accounts receivable aging report.

Columns: customer, not_due, days_1_30, days_31_60, days_61_90, over_90, total_outstanding

---

## Enum Types

#### erp.account_type
Values: `asset`, `liability`, `equity`, `revenue`, `expense`

#### erp.employment_status
Values: `active`, `on_leave`, `terminated`, `retired`

#### erp.employment_type
Values: `full_time`, `part_time`, `contract`, `intern`

#### erp.expense_status
Values: `pending`, `approved`, `rejected`, `reimbursed`

#### erp.invoice_status
Values: `draft`, `sent`, `paid`, `overdue`, `cancelled`, `refunded`

#### erp.lead_status
Values: `new`, `contacted`, `qualified`, `proposal`, `negotiation`, `won`, `lost`

#### erp.leave_status
Values: `pending`, `approved`, `rejected`, `cancelled`

#### erp.leave_type
Values: `annual`, `sick`, `personal`, `maternity`, `paternity`, `unpaid`

#### erp.movement_type
Values: `receipt`, `issue`, `transfer`, `adjustment`, `return`

#### erp.opportunity_stage
Values: `prospecting`, `qualification`, `proposal`, `negotiation`, `closed_won`, `closed_lost`

#### erp.project_status
Values: `planning`, `active`, `on_hold`, `completed`, `cancelled`

#### erp.task_priority
Values: `low`, `medium`, `high`, `critical`

#### erp.task_status
Values: `todo`, `in_progress`, `review`, `done`, `blocked`

#### erp.ticket_priority
Values: `low`, `medium`, `high`, `urgent`, `critical`

#### erp.ticket_status
Values: `open`, `in_progress`, `waiting`, `resolved`, `closed`

#### erp.transaction_type
Values: `debit`, `credit`

#### erp.warehouse_type
Values: `main`, `regional`, `distribution`, `retail`

---

## Common Query Patterns

### HR Queries
1. **Org chart**: Recursive CTE on employees.manager_id
2. **Department headcount**: Use department_summary view
3. **Leave calendar**: Filter leave_requests by date range
4. **Skills matrix**: Join employees -> employee_skills -> skills

### Finance Queries
1. **Trial balance**: Use account_balances view
2. **Vendor payments**: Join vendors -> invoices where invoice_type = 'AP'
3. **AR aging**: Use ar_aging view
4. **Expense by department**: Join expense_reports -> employees -> departments

### Inventory Queries
1. **Stock status**: Use inventory_status view
2. **Movement history**: Filter inventory_movements by product_id
3. **Reorder list**: Filter products where stock < reorder_point

### CRM Queries
1. **Customer 360**: Use customer_summary view
2. **Sales pipeline**: Use sales_pipeline view
3. **Lead conversion**: Filter leads where converted_customer_id IS NOT NULL
4. **Ticket SLA**: Use ticket_statistics view

### Project Queries
1. **Project dashboard**: Use project_status_view
2. **Resource utilization**: Use employee_workload view
3. **Time tracking**: Aggregate time_entries by project/employee
4. **Task dependencies**: Recursive CTE on tasks.parent_id
