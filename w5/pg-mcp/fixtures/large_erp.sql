-- =============================================================================
-- Large Database: Enterprise ERP System
-- Tables: 35+ | Views: 12+ | Custom Types: 15+ | Indexes: 60+
-- Data: 500-2000+ rows per table
-- Modules: HR, Finance, Inventory, CRM, Projects
-- =============================================================================

-- Drop existing objects
DROP SCHEMA IF EXISTS erp CASCADE;
CREATE SCHEMA erp;
SET search_path TO erp;

-- =============================================================================
-- Custom Types
-- =============================================================================

-- HR Types
CREATE TYPE employment_status AS ENUM ('active', 'on_leave', 'terminated', 'retired');
CREATE TYPE employment_type AS ENUM ('full_time', 'part_time', 'contract', 'intern');
CREATE TYPE leave_type AS ENUM ('annual', 'sick', 'personal', 'maternity', 'paternity', 'unpaid');
CREATE TYPE leave_status AS ENUM ('pending', 'approved', 'rejected', 'cancelled');

-- Finance Types
CREATE TYPE account_type AS ENUM ('asset', 'liability', 'equity', 'revenue', 'expense');
CREATE TYPE transaction_type AS ENUM ('debit', 'credit');
CREATE TYPE invoice_status AS ENUM ('draft', 'sent', 'paid', 'overdue', 'cancelled', 'refunded');
CREATE TYPE expense_status AS ENUM ('pending', 'approved', 'rejected', 'reimbursed');

-- Inventory Types
CREATE TYPE movement_type AS ENUM ('receipt', 'issue', 'transfer', 'adjustment', 'return');
CREATE TYPE warehouse_type AS ENUM ('main', 'regional', 'distribution', 'retail');

-- CRM Types
CREATE TYPE lead_status AS ENUM ('new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost');
CREATE TYPE opportunity_stage AS ENUM ('prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost');
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent', 'critical');
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'waiting', 'resolved', 'closed');

-- Project Types
CREATE TYPE project_status AS ENUM ('planning', 'active', 'on_hold', 'completed', 'cancelled');
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'review', 'done', 'blocked');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical');

-- =============================================================================
-- HR Module Tables
-- =============================================================================

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES departments(id),
    manager_id INTEGER,  -- Will add FK after employees table
    budget DECIMAL(15, 2),
    cost_center VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE departments IS 'Organization departments';

-- Job Positions
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    min_salary DECIMAL(12, 2),
    max_salary DECIMAL(12, 2),
    description TEXT,
    requirements TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Employees
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_number VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    hire_date DATE NOT NULL,
    birth_date DATE,
    department_id INTEGER REFERENCES departments(id),
    position_id INTEGER REFERENCES positions(id),
    manager_id INTEGER REFERENCES employees(id),
    employment_status employment_status DEFAULT 'active',
    employment_type employment_type DEFAULT 'full_time',
    salary DECIMAL(12, 2),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    emergency_contact_name VARCHAR(200),
    emergency_contact_phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE employees IS 'Employee master data';

-- Add FK for department manager
ALTER TABLE departments ADD CONSTRAINT fk_dept_manager FOREIGN KEY (manager_id) REFERENCES employees(id);

-- Employee Skills
CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50),
    description TEXT
);

CREATE TABLE employee_skills (
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level INTEGER CHECK (proficiency_level BETWEEN 1 AND 5),
    years_experience DECIMAL(4, 1),
    certified BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (employee_id, skill_id)
);

-- Leave Requests
CREATE TABLE leave_requests (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type leave_type NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_requested DECIMAL(4, 1) NOT NULL,
    reason TEXT,
    status leave_status DEFAULT 'pending',
    approved_by INTEGER REFERENCES employees(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Leave Balances
CREATE TABLE leave_balances (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type leave_type NOT NULL,
    year INTEGER NOT NULL,
    entitled_days DECIMAL(4, 1) NOT NULL,
    used_days DECIMAL(4, 1) DEFAULT 0,
    pending_days DECIMAL(4, 1) DEFAULT 0,
    UNIQUE(employee_id, leave_type, year)
);

-- Attendance
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    check_in TIME,
    check_out TIME,
    hours_worked DECIMAL(4, 2),
    overtime_hours DECIMAL(4, 2) DEFAULT 0,
    notes TEXT,
    UNIQUE(employee_id, work_date)
);

-- =============================================================================
-- Finance Module Tables
-- =============================================================================

-- Chart of Accounts
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    account_type account_type NOT NULL,
    parent_id INTEGER REFERENCES accounts(id),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE accounts IS 'Chart of accounts for general ledger';

-- Fiscal Periods
CREATE TABLE fiscal_periods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Journal Entries
CREATE TABLE journal_entries (
    id SERIAL PRIMARY KEY,
    entry_number VARCHAR(50) NOT NULL UNIQUE,
    fiscal_period_id INTEGER REFERENCES fiscal_periods(id),
    entry_date DATE NOT NULL,
    description TEXT,
    reference VARCHAR(100),
    is_posted BOOLEAN DEFAULT FALSE,
    posted_by INTEGER REFERENCES employees(id),
    posted_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Journal Entry Lines
CREATE TABLE journal_lines (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    transaction_type transaction_type NOT NULL,
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    description TEXT,
    cost_center VARCHAR(50)
);

-- Vendors
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    tax_id VARCHAR(50),
    payment_terms INTEGER DEFAULT 30,
    account_id INTEGER REFERENCES accounts(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Purchase Orders
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(50) NOT NULL UNIQUE,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    order_date DATE NOT NULL,
    expected_date DATE,
    subtotal DECIMAL(15, 2) NOT NULL,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    approved_by INTEGER REFERENCES employees(id),
    notes TEXT,
    created_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Purchase Order Items
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    po_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_code VARCHAR(50),
    description VARCHAR(500) NOT NULL,
    quantity DECIMAL(12, 3) NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    total_price DECIMAL(15, 2) NOT NULL,
    received_quantity DECIMAL(12, 3) DEFAULT 0
);

-- Invoices (AP & AR)
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    invoice_type VARCHAR(20) NOT NULL CHECK (invoice_type IN ('payable', 'receivable')),
    vendor_id INTEGER REFERENCES vendors(id),
    customer_id INTEGER,  -- Will reference CRM customers
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal DECIMAL(15, 2) NOT NULL,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL,
    paid_amount DECIMAL(15, 2) DEFAULT 0,
    status invoice_status DEFAULT 'draft',
    po_id INTEGER REFERENCES purchase_orders(id),
    notes TEXT,
    created_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Invoice Lines
CREATE TABLE invoice_lines (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(id),
    description VARCHAR(500) NOT NULL,
    quantity DECIMAL(12, 3) NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    total_price DECIMAL(15, 2) NOT NULL
);

-- Expense Reports
CREATE TABLE expense_reports (
    id SERIAL PRIMARY KEY,
    report_number VARCHAR(50) NOT NULL UNIQUE,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    report_date DATE NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status expense_status DEFAULT 'pending',
    approved_by INTEGER REFERENCES employees(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Expense Items
CREATE TABLE expense_items (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES expense_reports(id) ON DELETE CASCADE,
    expense_date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    amount DECIMAL(12, 2) NOT NULL,
    receipt_url VARCHAR(500),
    account_id INTEGER REFERENCES accounts(id)
);

-- =============================================================================
-- Inventory Module Tables
-- =============================================================================

-- Warehouses
CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    warehouse_type warehouse_type DEFAULT 'main',
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    manager_id INTEGER REFERENCES employees(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Product Categories
CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES product_categories(id),
    description TEXT
);

-- Products (Inventory Items)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    category_id INTEGER REFERENCES product_categories(id),
    unit_of_measure VARCHAR(20) DEFAULT 'unit',
    unit_cost DECIMAL(12, 2),
    unit_price DECIMAL(12, 2),
    min_stock_level INTEGER DEFAULT 0,
    max_stock_level INTEGER,
    reorder_point INTEGER,
    reorder_quantity INTEGER,
    weight_kg DECIMAL(10, 3),
    dimensions VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Stock Levels (per warehouse)
CREATE TABLE stock_levels (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity_on_hand DECIMAL(12, 3) NOT NULL DEFAULT 0,
    quantity_reserved DECIMAL(12, 3) NOT NULL DEFAULT 0,
    quantity_on_order DECIMAL(12, 3) NOT NULL DEFAULT 0,
    last_count_date DATE,
    bin_location VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, warehouse_id)
);

-- Inventory Movements
CREATE TABLE inventory_movements (
    id SERIAL PRIMARY KEY,
    movement_number VARCHAR(50) NOT NULL UNIQUE,
    movement_type movement_type NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id),
    from_warehouse_id INTEGER REFERENCES warehouses(id),
    to_warehouse_id INTEGER REFERENCES warehouses(id),
    quantity DECIMAL(12, 3) NOT NULL,
    unit_cost DECIMAL(12, 2),
    reference_type VARCHAR(50),
    reference_id INTEGER,
    notes TEXT,
    performed_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- CRM Module Tables
-- =============================================================================

-- Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_number VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100),
    website VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    account_manager_id INTEGER REFERENCES employees(id),
    credit_limit DECIMAL(15, 2),
    payment_terms INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE customers IS 'CRM customer accounts';

-- Add FK for invoices
ALTER TABLE invoices ADD CONSTRAINT fk_invoice_customer FOREIGN KEY (customer_id) REFERENCES customers(id);

-- Contacts
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    mobile VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Leads
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(200),
    contact_name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    source VARCHAR(100),
    status lead_status DEFAULT 'new',
    assigned_to INTEGER REFERENCES employees(id),
    estimated_value DECIMAL(15, 2),
    notes TEXT,
    converted_customer_id INTEGER REFERENCES customers(id),
    converted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Opportunities
CREATE TABLE opportunities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    lead_id INTEGER REFERENCES leads(id),
    stage opportunity_stage DEFAULT 'prospecting',
    probability INTEGER CHECK (probability BETWEEN 0 AND 100),
    expected_amount DECIMAL(15, 2),
    expected_close_date DATE,
    assigned_to INTEGER REFERENCES employees(id),
    description TEXT,
    won_reason TEXT,
    lost_reason TEXT,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Activities
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(50) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    customer_id INTEGER REFERENCES customers(id),
    contact_id INTEGER REFERENCES contacts(id),
    opportunity_id INTEGER REFERENCES opportunities(id),
    assigned_to INTEGER REFERENCES employees(id),
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Support Tickets
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    contact_id INTEGER REFERENCES contacts(id),
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    priority ticket_priority DEFAULT 'medium',
    status ticket_status DEFAULT 'open',
    assigned_to INTEGER REFERENCES employees(id),
    resolution TEXT,
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Ticket Comments
CREATE TABLE ticket_comments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES employees(id),
    is_internal BOOLEAN DEFAULT FALSE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Project Module Tables
-- =============================================================================

-- Projects
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    customer_id INTEGER REFERENCES customers(id),
    status project_status DEFAULT 'planning',
    priority task_priority DEFAULT 'medium',
    start_date DATE,
    target_end_date DATE,
    actual_end_date DATE,
    budget DECIMAL(15, 2),
    actual_cost DECIMAL(15, 2) DEFAULT 0,
    manager_id INTEGER REFERENCES employees(id),
    department_id INTEGER REFERENCES departments(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE projects IS 'Project management';

-- Project Members
CREATE TABLE project_members (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    role VARCHAR(100),
    allocated_hours DECIMAL(8, 2),
    start_date DATE,
    end_date DATE,
    PRIMARY KEY (project_id, employee_id)
);

-- Project Tasks
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES tasks(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status task_status DEFAULT 'todo',
    priority task_priority DEFAULT 'medium',
    assigned_to INTEGER REFERENCES employees(id),
    estimated_hours DECIMAL(8, 2),
    actual_hours DECIMAL(8, 2) DEFAULT 0,
    start_date DATE,
    due_date DATE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Time Entries
CREATE TABLE time_entries (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    hours DECIMAL(4, 2) NOT NULL CHECK (hours > 0),
    description TEXT,
    is_billable BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by INTEGER REFERENCES employees(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Audit & System Tables
-- =============================================================================

-- Audit Log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by INTEGER REFERENCES employees(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

-- System Settings
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    updated_by INTEGER REFERENCES employees(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- HR Indexes
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_manager ON employees(manager_id);
CREATE INDEX idx_employees_status ON employees(employment_status);
CREATE INDEX idx_employees_hire_date ON employees(hire_date);
CREATE INDEX idx_employees_email ON employees(email);
CREATE INDEX idx_employees_name ON employees(last_name, first_name);
CREATE INDEX idx_leave_requests_employee ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_status ON leave_requests(status);
CREATE INDEX idx_leave_requests_dates ON leave_requests(start_date, end_date);
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, work_date);

-- Finance Indexes
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_journal_entries_date ON journal_entries(entry_date);
CREATE INDEX idx_journal_entries_period ON journal_entries(fiscal_period_id);
CREATE INDEX idx_journal_lines_entry ON journal_lines(entry_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_id);
CREATE INDEX idx_vendors_name ON vendors(name);
CREATE INDEX idx_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_po_date ON purchase_orders(order_date);
CREATE INDEX idx_invoices_type ON invoices(invoice_type);
CREATE INDEX idx_invoices_vendor ON invoices(vendor_id);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_expense_reports_employee ON expense_reports(employee_id);
CREATE INDEX idx_expense_reports_status ON expense_reports(status);

-- Inventory Indexes
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_stock_levels_product ON stock_levels(product_id);
CREATE INDEX idx_stock_levels_warehouse ON stock_levels(warehouse_id);
CREATE INDEX idx_stock_levels_low ON stock_levels(quantity_on_hand) WHERE quantity_on_hand <= 10;
CREATE INDEX idx_inventory_movements_product ON inventory_movements(product_id);
CREATE INDEX idx_inventory_movements_type ON inventory_movements(movement_type);
CREATE INDEX idx_inventory_movements_date ON inventory_movements(created_at);

-- CRM Indexes
CREATE INDEX idx_customers_name ON customers(company_name);
CREATE INDEX idx_customers_account_manager ON customers(account_manager_id);
CREATE INDEX idx_contacts_customer ON contacts(customer_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_assigned ON leads(assigned_to);
CREATE INDEX idx_opportunities_customer ON opportunities(customer_id);
CREATE INDEX idx_opportunities_stage ON opportunities(stage);
CREATE INDEX idx_opportunities_assigned ON opportunities(assigned_to);
CREATE INDEX idx_activities_customer ON activities(customer_id);
CREATE INDEX idx_activities_due_date ON activities(due_date);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned ON tickets(assigned_to);

-- Project Indexes
CREATE INDEX idx_projects_customer ON projects(customer_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_manager ON projects(manager_id);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_time_entries_employee ON time_entries(employee_id);
CREATE INDEX idx_time_entries_task ON time_entries(task_id);
CREATE INDEX idx_time_entries_date ON time_entries(entry_date);

-- Audit Indexes
CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_date ON audit_log(changed_at);

-- Full text search indexes
CREATE INDEX idx_products_name_search ON products USING GIN (to_tsvector('english', name));
CREATE INDEX idx_customers_name_search ON customers USING GIN (to_tsvector('english', company_name));
CREATE INDEX idx_tickets_subject_search ON tickets USING GIN (to_tsvector('english', subject));

-- =============================================================================
-- Views
-- =============================================================================

-- Employee Directory
CREATE VIEW employee_directory AS
SELECT
    e.id,
    e.employee_number,
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    e.phone,
    p.title AS position,
    d.name AS department,
    m.first_name || ' ' || m.last_name AS manager_name,
    e.employment_status,
    e.employment_type,
    e.hire_date,
    DATE_PART('year', AGE(CURRENT_DATE, e.hire_date)) AS years_employed
FROM employees e
LEFT JOIN positions p ON e.position_id = p.id
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN employees m ON e.manager_id = m.id
WHERE e.employment_status = 'active';

-- Department Summary
CREATE VIEW department_summary AS
SELECT
    d.id,
    d.name,
    d.code,
    pd.name AS parent_department,
    m.first_name || ' ' || m.last_name AS manager,
    COUNT(DISTINCT e.id) AS employee_count,
    d.budget,
    SUM(e.salary) AS total_salaries,
    AVG(e.salary)::DECIMAL(12,2) AS avg_salary
FROM departments d
LEFT JOIN departments pd ON d.parent_id = pd.id
LEFT JOIN employees m ON d.manager_id = m.id
LEFT JOIN employees e ON e.department_id = d.id AND e.employment_status = 'active'
GROUP BY d.id, d.name, d.code, pd.name, m.first_name, m.last_name, d.budget;

-- Account Balances
CREATE VIEW account_balances AS
SELECT
    a.id,
    a.account_number,
    a.name,
    a.account_type,
    COALESCE(SUM(CASE WHEN jl.transaction_type = 'debit' THEN jl.amount ELSE 0 END), 0) AS total_debits,
    COALESCE(SUM(CASE WHEN jl.transaction_type = 'credit' THEN jl.amount ELSE 0 END), 0) AS total_credits,
    CASE
        WHEN a.account_type IN ('asset', 'expense') THEN
            COALESCE(SUM(CASE WHEN jl.transaction_type = 'debit' THEN jl.amount ELSE -jl.amount END), 0)
        ELSE
            COALESCE(SUM(CASE WHEN jl.transaction_type = 'credit' THEN jl.amount ELSE -jl.amount END), 0)
    END AS balance
FROM accounts a
LEFT JOIN journal_lines jl ON a.id = jl.account_id
LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.is_posted = TRUE
GROUP BY a.id, a.account_number, a.name, a.account_type;

-- Vendor Summary
CREATE VIEW vendor_summary AS
SELECT
    v.id,
    v.code,
    v.name,
    v.country,
    COUNT(DISTINCT po.id) AS total_orders,
    SUM(po.total_amount) AS total_order_value,
    COUNT(DISTINCT i.id) FILTER (WHERE i.status = 'paid') AS paid_invoices,
    SUM(i.total_amount) FILTER (WHERE i.status != 'cancelled') AS total_invoiced,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.status IN ('sent', 'overdue')) AS outstanding_balance
FROM vendors v
LEFT JOIN purchase_orders po ON v.id = po.vendor_id
LEFT JOIN invoices i ON v.id = i.vendor_id AND i.invoice_type = 'payable'
WHERE v.is_active = TRUE
GROUP BY v.id, v.code, v.name, v.country;

-- Inventory Status
CREATE VIEW inventory_status AS
SELECT
    p.id,
    p.sku,
    p.name,
    pc.name AS category,
    p.unit_of_measure,
    p.unit_cost,
    p.unit_price,
    COALESCE(SUM(sl.quantity_on_hand), 0) AS total_on_hand,
    COALESCE(SUM(sl.quantity_reserved), 0) AS total_reserved,
    COALESCE(SUM(sl.quantity_on_hand - sl.quantity_reserved), 0) AS available,
    COALESCE(SUM(sl.quantity_on_order), 0) AS on_order,
    p.reorder_point,
    CASE
        WHEN COALESCE(SUM(sl.quantity_on_hand), 0) <= p.min_stock_level THEN 'critical'
        WHEN COALESCE(SUM(sl.quantity_on_hand), 0) <= p.reorder_point THEN 'low'
        ELSE 'ok'
    END AS stock_status,
    COALESCE(SUM(sl.quantity_on_hand), 0) * p.unit_cost AS inventory_value
FROM products p
LEFT JOIN product_categories pc ON p.category_id = pc.id
LEFT JOIN stock_levels sl ON p.id = sl.product_id
WHERE p.is_active = TRUE
GROUP BY p.id, p.sku, p.name, pc.name, p.unit_of_measure, p.unit_cost, p.unit_price, p.reorder_point, p.min_stock_level;

-- Customer Summary
CREATE VIEW customer_summary AS
SELECT
    c.id,
    c.customer_number,
    c.company_name,
    c.industry,
    c.country,
    e.first_name || ' ' || e.last_name AS account_manager,
    COUNT(DISTINCT o.id) AS opportunity_count,
    SUM(o.expected_amount) FILTER (WHERE o.stage = 'closed_won') AS won_revenue,
    COUNT(DISTINCT i.id) AS invoice_count,
    SUM(i.total_amount) AS total_invoiced,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.status IN ('sent', 'overdue')) AS outstanding,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status != 'closed') AS open_tickets
FROM customers c
LEFT JOIN employees e ON c.account_manager_id = e.id
LEFT JOIN opportunities o ON c.id = o.customer_id
LEFT JOIN invoices i ON c.id = i.customer_id AND i.invoice_type = 'receivable'
LEFT JOIN tickets t ON c.id = t.customer_id
WHERE c.is_active = TRUE
GROUP BY c.id, c.customer_number, c.company_name, c.industry, c.country, e.first_name, e.last_name;

-- Sales Pipeline
CREATE VIEW sales_pipeline AS
SELECT
    o.stage,
    COUNT(*) AS opportunity_count,
    SUM(o.expected_amount) AS total_value,
    AVG(o.probability)::INTEGER AS avg_probability,
    SUM(o.expected_amount * o.probability / 100) AS weighted_value
FROM opportunities o
WHERE o.stage NOT IN ('closed_won', 'closed_lost')
GROUP BY o.stage
ORDER BY
    CASE o.stage
        WHEN 'prospecting' THEN 1
        WHEN 'qualification' THEN 2
        WHEN 'proposal' THEN 3
        WHEN 'negotiation' THEN 4
    END;

-- Ticket Statistics
CREATE VIEW ticket_statistics AS
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS total_tickets,
    COUNT(*) FILTER (WHERE priority = 'critical') AS critical_count,
    COUNT(*) FILTER (WHERE priority = 'high') AS high_count,
    COUNT(*) FILTER (WHERE status = 'closed') AS closed_count,
    AVG(EXTRACT(EPOCH FROM (first_response_at - created_at))/3600)::DECIMAL(8,2) AS avg_first_response_hours,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600)::DECIMAL(8,2) AS avg_resolution_hours
FROM tickets
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- Project Status
CREATE VIEW project_status_view AS
SELECT
    p.id,
    p.project_code,
    p.name,
    c.company_name AS customer,
    p.status,
    p.priority,
    e.first_name || ' ' || e.last_name AS manager,
    p.start_date,
    p.target_end_date,
    p.budget,
    p.actual_cost,
    CASE WHEN p.budget > 0 THEN (p.actual_cost / p.budget * 100)::INTEGER ELSE 0 END AS budget_used_pct,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'done') AS completed_tasks,
    CASE WHEN COUNT(t.id) > 0
        THEN (COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / COUNT(t.id) * 100)::INTEGER
        ELSE 0
    END AS completion_pct,
    SUM(te.hours) AS total_hours_logged
FROM projects p
LEFT JOIN customers c ON p.customer_id = c.id
LEFT JOIN employees e ON p.manager_id = e.id
LEFT JOIN tasks t ON p.id = t.project_id
LEFT JOIN time_entries te ON p.id = te.project_id
GROUP BY p.id, p.project_code, p.name, c.company_name, p.status, p.priority,
         e.first_name, e.last_name, p.start_date, p.target_end_date, p.budget, p.actual_cost;

-- Employee Workload
CREATE VIEW employee_workload AS
SELECT
    e.id,
    e.first_name || ' ' || e.last_name AS name,
    d.name AS department,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status IN ('todo', 'in_progress')) AS active_tasks,
    COUNT(DISTINCT pm.project_id) AS active_projects,
    SUM(te.hours) FILTER (WHERE te.entry_date >= CURRENT_DATE - INTERVAL '7 days') AS hours_last_week,
    SUM(t.estimated_hours) FILTER (WHERE t.status IN ('todo', 'in_progress')) AS pending_hours
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN tasks t ON e.id = t.assigned_to
LEFT JOIN project_members pm ON e.id = pm.employee_id
LEFT JOIN projects p ON pm.project_id = p.id AND p.status = 'active'
LEFT JOIN time_entries te ON e.id = te.employee_id
WHERE e.employment_status = 'active'
GROUP BY e.id, e.first_name, e.last_name, d.name;

-- Aging Report (AR)
CREATE VIEW ar_aging AS
SELECT
    c.company_name AS customer,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.due_date > CURRENT_DATE) AS not_due,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.due_date BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE) AS days_1_30,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.due_date BETWEEN CURRENT_DATE - 60 AND CURRENT_DATE - 31) AS days_31_60,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.due_date BETWEEN CURRENT_DATE - 90 AND CURRENT_DATE - 61) AS days_61_90,
    SUM(i.total_amount - i.paid_amount) FILTER (WHERE i.due_date < CURRENT_DATE - 90) AS over_90,
    SUM(i.total_amount - i.paid_amount) AS total_outstanding
FROM customers c
JOIN invoices i ON c.id = i.customer_id AND i.invoice_type = 'receivable' AND i.status IN ('sent', 'overdue')
GROUP BY c.id, c.company_name
HAVING SUM(i.total_amount - i.paid_amount) > 0
ORDER BY total_outstanding DESC;

-- =============================================================================
-- Sample Data Generation
-- =============================================================================

DO $$
DECLARE
    dept_count INTEGER := 12;
    emp_count INTEGER := 500;
    customer_count INTEGER := 300;
    product_count INTEGER := 400;
    i INTEGER;
    j INTEGER;
    v_dept_id INTEGER;
    v_emp_id INTEGER;
    v_customer_id INTEGER;
    v_product_id INTEGER;
    v_project_id INTEGER;
    v_warehouse_id INTEGER;
    v_manager_id INTEGER;
BEGIN
    -- ==========================================================================
    -- HR Data
    -- ==========================================================================

    -- Departments (hierarchical)
    INSERT INTO departments (name, code, budget) VALUES
    ('Executive', 'EXEC', 5000000) RETURNING id INTO v_dept_id;
    INSERT INTO departments (name, code, parent_id, budget) VALUES
    ('Finance', 'FIN', v_dept_id, 2000000),
    ('Human Resources', 'HR', v_dept_id, 1500000),
    ('Operations', 'OPS', v_dept_id, 3000000);

    INSERT INTO departments (name, code, parent_id, budget)
    SELECT 'Engineering', 'ENG', v_dept_id, 4000000 RETURNING id INTO v_dept_id;
    INSERT INTO departments (name, code, parent_id, budget) VALUES
    ('Backend', 'ENG-BE', v_dept_id, 1500000),
    ('Frontend', 'ENG-FE', v_dept_id, 1200000),
    ('DevOps', 'ENG-DO', v_dept_id, 1000000);

    INSERT INTO departments (name, code, parent_id, budget)
    SELECT 'Sales', 'SALES', 1, 2500000 RETURNING id INTO v_dept_id;
    INSERT INTO departments (name, code, parent_id, budget) VALUES
    ('Enterprise Sales', 'SALES-ENT', v_dept_id, 1200000),
    ('SMB Sales', 'SALES-SMB', v_dept_id, 800000);

    INSERT INTO departments (name, code, parent_id, budget) VALUES
    ('Customer Success', 'CS', 1, 1800000);

    -- Positions
    INSERT INTO positions (title, department_id, min_salary, max_salary) VALUES
    ('CEO', 1, 300000, 500000),
    ('CFO', 2, 200000, 350000),
    ('VP Engineering', 5, 180000, 280000),
    ('VP Sales', 9, 150000, 250000),
    ('Engineering Manager', 5, 130000, 180000),
    ('Senior Software Engineer', 5, 100000, 150000),
    ('Software Engineer', 5, 70000, 110000),
    ('Junior Engineer', 5, 50000, 75000),
    ('Sales Manager', 9, 90000, 140000),
    ('Account Executive', 9, 60000, 100000),
    ('Sales Representative', 9, 45000, 70000),
    ('Customer Success Manager', 12, 70000, 110000),
    ('Support Specialist', 12, 45000, 65000),
    ('HR Manager', 3, 80000, 120000),
    ('HR Specialist', 3, 50000, 75000),
    ('Finance Manager', 2, 90000, 130000),
    ('Accountant', 2, 55000, 85000),
    ('Operations Manager', 4, 85000, 125000),
    ('DevOps Engineer', 8, 90000, 140000),
    ('Frontend Developer', 7, 80000, 130000),
    ('Backend Developer', 6, 85000, 140000);

    -- Skills
    INSERT INTO skills (name, category) VALUES
    ('Python', 'Programming'), ('JavaScript', 'Programming'), ('TypeScript', 'Programming'),
    ('Java', 'Programming'), ('Go', 'Programming'), ('Rust', 'Programming'),
    ('PostgreSQL', 'Database'), ('MongoDB', 'Database'), ('Redis', 'Database'),
    ('AWS', 'Cloud'), ('Azure', 'Cloud'), ('GCP', 'Cloud'),
    ('Docker', 'DevOps'), ('Kubernetes', 'DevOps'), ('Terraform', 'DevOps'),
    ('React', 'Frontend'), ('Vue.js', 'Frontend'), ('Angular', 'Frontend'),
    ('Project Management', 'Management'), ('Agile/Scrum', 'Management'),
    ('Sales', 'Business'), ('Negotiation', 'Business'), ('CRM', 'Business'),
    ('Data Analysis', 'Analytics'), ('Machine Learning', 'Analytics');

    -- Employees
    FOR i IN 1..emp_count LOOP
        v_dept_id := 1 + (i % 12);

        INSERT INTO employees (
            employee_number, first_name, last_name, email, phone,
            hire_date, birth_date, department_id, position_id,
            employment_status, employment_type, salary, city, country
        ) VALUES (
            'EMP' || LPAD(i::TEXT, 5, '0'),
            CASE (i % 30)
                WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'John' WHEN 3 THEN 'Patricia'
                WHEN 4 THEN 'Robert' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
                WHEN 8 THEN 'William' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'David' WHEN 11 THEN 'Barbara'
                WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
                WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' WHEN 19 THEN 'Karen'
                WHEN 20 THEN 'Christopher' WHEN 21 THEN 'Nancy' WHEN 22 THEN 'Daniel' WHEN 23 THEN 'Lisa'
                WHEN 24 THEN 'Matthew' WHEN 25 THEN 'Betty' WHEN 26 THEN 'Anthony' WHEN 27 THEN 'Margaret'
                WHEN 28 THEN 'Mark' ELSE 'Sandra'
            END,
            CASE (i % 25)
                WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown'
                WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis'
                WHEN 8 THEN 'Rodriguez' WHEN 9 THEN 'Martinez' WHEN 10 THEN 'Hernandez' WHEN 11 THEN 'Lopez'
                WHEN 12 THEN 'Gonzalez' WHEN 13 THEN 'Wilson' WHEN 14 THEN 'Anderson' WHEN 15 THEN 'Thomas'
                WHEN 16 THEN 'Taylor' WHEN 17 THEN 'Moore' WHEN 18 THEN 'Jackson' WHEN 19 THEN 'Martin'
                WHEN 20 THEN 'Lee' WHEN 21 THEN 'Perez' WHEN 22 THEN 'Thompson' WHEN 23 THEN 'White'
                ELSE 'Harris'
            END,
            'employee' || i || '@company.com',
            '+1-555-' || LPAD((1000 + i)::TEXT, 4, '0'),
            CURRENT_DATE - ((random() * 3650 + 30)::INTEGER || ' days')::INTERVAL,
            CURRENT_DATE - ((random() * 15000 + 8000)::INTEGER || ' days')::INTERVAL,
            v_dept_id,
            1 + (i % 21),
            CASE (i % 50) WHEN 0 THEN 'on_leave'::employment_status ELSE 'active'::employment_status END,
            CASE (i % 20)
                WHEN 0 THEN 'part_time'::employment_type
                WHEN 1 THEN 'contract'::employment_type
                WHEN 2 THEN 'intern'::employment_type
                ELSE 'full_time'::employment_type
            END,
            (40000 + random() * 200000)::DECIMAL(12,2),
            CASE (i % 10)
                WHEN 0 THEN 'New York' WHEN 1 THEN 'San Francisco' WHEN 2 THEN 'Austin'
                WHEN 3 THEN 'Seattle' WHEN 4 THEN 'Boston' WHEN 5 THEN 'Chicago'
                WHEN 6 THEN 'Denver' WHEN 7 THEN 'Los Angeles' WHEN 8 THEN 'Miami' ELSE 'Atlanta'
            END,
            'USA'
        )
        RETURNING id INTO v_emp_id;

        -- Add 2-5 skills per employee
        INSERT INTO employee_skills (employee_id, skill_id, proficiency_level, years_experience, certified)
        SELECT v_emp_id, s.id, 1 + (random() * 4)::INTEGER, (random() * 10)::DECIMAL(4,1), random() > 0.7
        FROM skills s
        WHERE s.id IN (
            SELECT id FROM skills ORDER BY random() LIMIT (2 + (i % 4))
        );

        -- Leave balances
        INSERT INTO leave_balances (employee_id, leave_type, year, entitled_days, used_days) VALUES
        (v_emp_id, 'annual', 2025, 20, (random() * 15)::DECIMAL(4,1)),
        (v_emp_id, 'sick', 2025, 10, (random() * 5)::DECIMAL(4,1));
    END LOOP;

    -- Set managers (first 50 employees are potential managers)
    UPDATE employees SET manager_id = 1 + (id % 50) WHERE id > 50;
    UPDATE departments SET manager_id = (SELECT id FROM employees WHERE department_id = departments.id LIMIT 1);

    -- Leave requests (last 6 months)
    INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days_requested, status, approved_by)
    SELECT
        1 + (g % emp_count),
        (ARRAY['annual', 'sick', 'personal']::leave_type[])[1 + (g % 3)],
        CURRENT_DATE - (g || ' days')::INTERVAL,
        CURRENT_DATE - (g || ' days')::INTERVAL + ((1 + g % 5) || ' days')::INTERVAL,
        1 + (g % 5),
        (ARRAY['approved', 'approved', 'approved', 'pending', 'rejected']::leave_status[])[1 + (g % 5)],
        1 + (g % 50)
    FROM generate_series(1, 300) g;

    -- Attendance records (last 30 days)
    INSERT INTO attendance (employee_id, work_date, check_in, check_out, hours_worked, overtime_hours)
    SELECT
        e.id,
        d.work_date,
        '08:00'::TIME + ((random() * 60)::INTEGER || ' minutes')::INTERVAL,
        '17:00'::TIME + ((random() * 120)::INTEGER || ' minutes')::INTERVAL,
        8 + (random() * 2)::DECIMAL(4,2),
        CASE WHEN random() > 0.8 THEN (random() * 3)::DECIMAL(4,2) ELSE 0 END
    FROM employees e
    CROSS JOIN (
        SELECT CURRENT_DATE - g AS work_date
        FROM generate_series(1, 22) g
        WHERE EXTRACT(DOW FROM CURRENT_DATE - g) NOT IN (0, 6)
    ) d
    WHERE e.employment_status = 'active' AND random() > 0.05;

    -- ==========================================================================
    -- Finance Data
    -- ==========================================================================

    -- Chart of Accounts
    INSERT INTO accounts (account_number, name, account_type) VALUES
    ('1000', 'Assets', 'asset'),
    ('1100', 'Cash and Equivalents', 'asset'),
    ('1110', 'Checking Account', 'asset'),
    ('1120', 'Savings Account', 'asset'),
    ('1200', 'Accounts Receivable', 'asset'),
    ('1300', 'Inventory', 'asset'),
    ('1400', 'Fixed Assets', 'asset'),
    ('1410', 'Equipment', 'asset'),
    ('1420', 'Furniture', 'asset'),
    ('2000', 'Liabilities', 'liability'),
    ('2100', 'Accounts Payable', 'liability'),
    ('2200', 'Accrued Expenses', 'liability'),
    ('2300', 'Notes Payable', 'liability'),
    ('3000', 'Equity', 'equity'),
    ('3100', 'Common Stock', 'equity'),
    ('3200', 'Retained Earnings', 'equity'),
    ('4000', 'Revenue', 'revenue'),
    ('4100', 'Sales Revenue', 'revenue'),
    ('4200', 'Service Revenue', 'revenue'),
    ('5000', 'Expenses', 'expense'),
    ('5100', 'Cost of Goods Sold', 'expense'),
    ('5200', 'Salaries Expense', 'expense'),
    ('5300', 'Rent Expense', 'expense'),
    ('5400', 'Utilities Expense', 'expense'),
    ('5500', 'Marketing Expense', 'expense');

    -- Set parent accounts
    UPDATE accounts SET parent_id = (SELECT id FROM accounts WHERE account_number = '1000') WHERE account_number LIKE '1_00' AND account_number != '1000';
    UPDATE accounts SET parent_id = (SELECT id FROM accounts WHERE account_number = '1100') WHERE account_number LIKE '11__' AND account_number != '1100';

    -- Fiscal Periods
    INSERT INTO fiscal_periods (name, start_date, end_date, is_closed)
    SELECT
        'FY2025-Q' || q,
        DATE '2025-01-01' + ((q-1) * 3 || ' months')::INTERVAL,
        (DATE '2025-01-01' + (q * 3 || ' months')::INTERVAL - INTERVAL '1 day')::DATE,
        q < EXTRACT(QUARTER FROM CURRENT_DATE)
    FROM generate_series(1, 4) q;

    -- Vendors
    FOR i IN 1..100 LOOP
        INSERT INTO vendors (code, name, contact_name, email, phone, country, payment_terms) VALUES (
            'VND' || LPAD(i::TEXT, 4, '0'),
            'Vendor Company ' || i,
            'Contact ' || i,
            'vendor' || i || '@supplier.com',
            '+1-555-' || LPAD((2000 + i)::TEXT, 4, '0'),
            CASE (i % 5)
                WHEN 0 THEN 'USA' WHEN 1 THEN 'China' WHEN 2 THEN 'Germany'
                WHEN 3 THEN 'Japan' ELSE 'UK'
            END,
            CASE (i % 4) WHEN 0 THEN 15 WHEN 1 THEN 30 WHEN 2 THEN 45 ELSE 60 END
        );
    END LOOP;

    -- Purchase Orders
    FOR i IN 1..500 LOOP
        INSERT INTO purchase_orders (
            po_number, vendor_id, order_date, expected_date,
            subtotal, tax_amount, total_amount, status, created_by
        ) VALUES (
            'PO-' || TO_CHAR(CURRENT_DATE - (i || ' days')::INTERVAL, 'YYYYMM') || '-' || LPAD(i::TEXT, 4, '0'),
            1 + (i % 100),
            CURRENT_DATE - (i || ' days')::INTERVAL,
            CURRENT_DATE - (i || ' days')::INTERVAL + '14 days'::INTERVAL,
            (random() * 50000 + 500)::DECIMAL(15,2),
            0,
            0,
            CASE (i % 10)
                WHEN 0 THEN 'draft' WHEN 1 THEN 'pending'
                ELSE 'approved'
            END,
            1 + (i % 50)
        );
        -- Update totals
        UPDATE purchase_orders SET
            tax_amount = (subtotal * 0.08)::DECIMAL(15,2),
            total_amount = subtotal * 1.08
        WHERE po_number = 'PO-' || TO_CHAR(CURRENT_DATE - (i || ' days')::INTERVAL, 'YYYYMM') || '-' || LPAD(i::TEXT, 4, '0');
    END LOOP;

    -- Purchase Order Items
    INSERT INTO purchase_order_items (po_id, description, quantity, unit_price, total_price)
    SELECT
        po.id,
        'Item for PO ' || po.id || ' line ' || g,
        (random() * 100 + 1)::INTEGER,
        (random() * 500 + 10)::DECIMAL(12,2),
        0
    FROM purchase_orders po
    CROSS JOIN generate_series(1, 3) g;

    UPDATE purchase_order_items SET total_price = quantity * unit_price;

    -- Expense Reports
    FOR i IN 1..400 LOOP
        INSERT INTO expense_reports (
            report_number, employee_id, report_date, total_amount, status
        ) VALUES (
            'EXP-' || TO_CHAR(CURRENT_DATE - (i || ' days')::INTERVAL, 'YYYYMM') || '-' || LPAD(i::TEXT, 4, '0'),
            1 + (i % emp_count),
            CURRENT_DATE - (i || ' days')::INTERVAL,
            (random() * 2000 + 50)::DECIMAL(12,2),
            CASE (i % 10)
                WHEN 0 THEN 'pending'::expense_status
                WHEN 1 THEN 'rejected'::expense_status
                ELSE 'reimbursed'::expense_status
            END
        );
    END LOOP;

    -- Expense Items
    INSERT INTO expense_items (report_id, expense_date, category, description, amount)
    SELECT
        er.id,
        er.report_date,
        CASE (g % 5)
            WHEN 0 THEN 'Travel' WHEN 1 THEN 'Meals' WHEN 2 THEN 'Supplies'
            WHEN 3 THEN 'Software' ELSE 'Other'
        END,
        'Expense item ' || g,
        (random() * 500 + 20)::DECIMAL(12,2)
    FROM expense_reports er
    CROSS JOIN generate_series(1, 3) g;

    -- ==========================================================================
    -- Inventory Data
    -- ==========================================================================

    -- Warehouses
    INSERT INTO warehouses (code, name, warehouse_type, city, country) VALUES
    ('WH-MAIN', 'Main Warehouse', 'main', 'Chicago', 'USA'),
    ('WH-WEST', 'West Coast DC', 'distribution', 'Los Angeles', 'USA'),
    ('WH-EAST', 'East Coast DC', 'distribution', 'New York', 'USA'),
    ('WH-SOUTH', 'South Region', 'regional', 'Houston', 'USA'),
    ('WH-RETAIL-1', 'Retail Store 1', 'retail', 'San Francisco', 'USA');

    -- Product Categories
    INSERT INTO product_categories (name, code) VALUES
    ('Electronics', 'ELEC'),
    ('Office Supplies', 'OFFC'),
    ('Industrial Equipment', 'INDL'),
    ('Raw Materials', 'RAWM'),
    ('Packaging', 'PACK');

    -- Products
    FOR i IN 1..product_count LOOP
        INSERT INTO products (
            sku, name, category_id, unit_of_measure, unit_cost, unit_price,
            min_stock_level, max_stock_level, reorder_point, reorder_quantity, weight_kg
        ) VALUES (
            'PRD-' || LPAD(i::TEXT, 6, '0'),
            'Product ' || i || ' - ' || CASE (i % 10)
                WHEN 0 THEN 'Component A' WHEN 1 THEN 'Assembly B' WHEN 2 THEN 'Widget C'
                WHEN 3 THEN 'Module D' WHEN 4 THEN 'Part E' WHEN 5 THEN 'Supply F'
                WHEN 6 THEN 'Material G' WHEN 7 THEN 'Item H' WHEN 8 THEN 'Unit I' ELSE 'Kit J'
            END,
            1 + (i % 5),
            CASE (i % 4) WHEN 0 THEN 'unit' WHEN 1 THEN 'kg' WHEN 2 THEN 'box' ELSE 'pallet' END,
            (random() * 200 + 5)::DECIMAL(12,2),
            (random() * 400 + 20)::DECIMAL(12,2),
            5 + (i % 20),
            500 + (i % 1000),
            20 + (i % 50),
            100 + (i % 200),
            (random() * 50)::DECIMAL(10,3)
        )
        RETURNING id INTO v_product_id;

        -- Stock levels per warehouse
        INSERT INTO stock_levels (product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_on_order, bin_location)
        SELECT
            v_product_id,
            w.id,
            (random() * 500)::INTEGER,
            (random() * 50)::INTEGER,
            (random() * 100)::INTEGER,
            'A' || (1 + (v_product_id % 10))::TEXT || '-' || CHR(65 + (w.id % 5)) || (1 + (v_product_id % 50))::TEXT
        FROM warehouses w;
    END LOOP;

    -- Inventory Movements
    INSERT INTO inventory_movements (
        movement_number, movement_type, product_id, from_warehouse_id, to_warehouse_id,
        quantity, unit_cost, notes, performed_by, created_at
    )
    SELECT
        'MOV-' || LPAD(g::TEXT, 8, '0'),
        (ARRAY['receipt', 'issue', 'transfer', 'adjustment']::movement_type[])[1 + (g % 4)],
        1 + (g % product_count),
        CASE WHEN g % 4 IN (1, 2) THEN 1 + (g % 5) ELSE NULL END,
        CASE WHEN g % 4 IN (0, 2) THEN 1 + ((g + 1) % 5) ELSE NULL END,
        (random() * 100 + 1)::INTEGER,
        (random() * 100 + 10)::DECIMAL(12,2),
        'Movement ' || g,
        1 + (g % 50),
        CURRENT_TIMESTAMP - (g || ' hours')::INTERVAL
    FROM generate_series(1, 2000) g;

    -- ==========================================================================
    -- CRM Data
    -- ==========================================================================

    -- Customers
    FOR i IN 1..customer_count LOOP
        INSERT INTO customers (
            customer_number, company_name, industry, website, phone, email,
            city, country, account_manager_id, credit_limit, payment_terms
        ) VALUES (
            'CUS' || LPAD(i::TEXT, 6, '0'),
            'Customer Corp ' || i,
            CASE (i % 8)
                WHEN 0 THEN 'Technology' WHEN 1 THEN 'Healthcare' WHEN 2 THEN 'Finance'
                WHEN 3 THEN 'Manufacturing' WHEN 4 THEN 'Retail' WHEN 5 THEN 'Education'
                WHEN 6 THEN 'Government' ELSE 'Services'
            END,
            'https://customer' || i || '.com',
            '+1-555-' || LPAD((3000 + i)::TEXT, 4, '0'),
            'contact@customer' || i || '.com',
            CASE (i % 10)
                WHEN 0 THEN 'New York' WHEN 1 THEN 'Los Angeles' WHEN 2 THEN 'Chicago'
                WHEN 3 THEN 'Houston' WHEN 4 THEN 'Phoenix' WHEN 5 THEN 'Philadelphia'
                WHEN 6 THEN 'San Antonio' WHEN 7 THEN 'San Diego' WHEN 8 THEN 'Dallas' ELSE 'Seattle'
            END,
            'USA',
            1 + (i % 50),
            (random() * 500000 + 10000)::DECIMAL(15,2),
            CASE (i % 4) WHEN 0 THEN 15 WHEN 1 THEN 30 WHEN 2 THEN 45 ELSE 60 END
        )
        RETURNING id INTO v_customer_id;

        -- Add 1-3 contacts per customer
        FOR j IN 1..LEAST(3, 1 + (i % 3)) LOOP
            INSERT INTO contacts (customer_id, first_name, last_name, title, email, phone, is_primary) VALUES (
                v_customer_id,
                CASE (j % 5) WHEN 0 THEN 'Alex' WHEN 1 THEN 'Jordan' WHEN 2 THEN 'Taylor' WHEN 3 THEN 'Morgan' ELSE 'Casey' END,
                CASE (i % 5) WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown' ELSE 'Jones' END,
                CASE (j % 4) WHEN 0 THEN 'CEO' WHEN 1 THEN 'CTO' WHEN 2 THEN 'Procurement Manager' ELSE 'Director' END,
                'contact' || j || '@customer' || i || '.com',
                '+1-555-' || LPAD((4000 + i * 10 + j)::TEXT, 4, '0'),
                (j = 1)
            );
        END LOOP;
    END LOOP;

    -- Leads
    INSERT INTO leads (
        company_name, contact_name, email, phone, source, status,
        assigned_to, estimated_value, created_at
    )
    SELECT
        'Lead Company ' || g,
        'Lead Contact ' || g,
        'lead' || g || '@prospect.com',
        '+1-555-' || LPAD((5000 + g)::TEXT, 4, '0'),
        CASE (g % 5)
            WHEN 0 THEN 'Website' WHEN 1 THEN 'Referral' WHEN 2 THEN 'Trade Show'
            WHEN 3 THEN 'LinkedIn' ELSE 'Cold Call'
        END,
        (ARRAY['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']::lead_status[])[1 + (g % 7)],
        1 + (g % 50),
        (random() * 100000 + 5000)::DECIMAL(15,2),
        CURRENT_TIMESTAMP - (g * 4 || ' hours')::INTERVAL
    FROM generate_series(1, 600) g;

    -- Opportunities
    INSERT INTO opportunities (
        name, customer_id, stage, probability, expected_amount,
        expected_close_date, assigned_to, created_at
    )
    SELECT
        'Opportunity for Customer ' || (1 + (g % customer_count)),
        1 + (g % customer_count),
        (ARRAY['prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost']::opportunity_stage[])[1 + (g % 6)],
        CASE (g % 6)
            WHEN 0 THEN 10 WHEN 1 THEN 25 WHEN 2 THEN 50 WHEN 3 THEN 75 WHEN 4 THEN 100 ELSE 0
        END,
        (random() * 500000 + 10000)::DECIMAL(15,2),
        CURRENT_DATE + ((random() * 180)::INTEGER || ' days')::INTERVAL,
        1 + (g % 50),
        CURRENT_TIMESTAMP - (g * 6 || ' hours')::INTERVAL
    FROM generate_series(1, 800) g;

    -- Activities
    INSERT INTO activities (
        activity_type, subject, customer_id, assigned_to, due_date, created_by, created_at
    )
    SELECT
        CASE (g % 5)
            WHEN 0 THEN 'Call' WHEN 1 THEN 'Meeting' WHEN 2 THEN 'Email'
            WHEN 3 THEN 'Task' ELSE 'Follow-up'
        END,
        'Activity ' || g || ' for customer',
        1 + (g % customer_count),
        1 + (g % 50),
        CURRENT_TIMESTAMP + ((g % 30 - 15) || ' days')::INTERVAL,
        1 + (g % 50),
        CURRENT_TIMESTAMP - (g * 2 || ' hours')::INTERVAL
    FROM generate_series(1, 1500) g;

    -- Tickets
    INSERT INTO tickets (
        ticket_number, customer_id, subject, description, priority, status,
        assigned_to, created_at
    )
    SELECT
        'TKT-' || LPAD(g::TEXT, 6, '0'),
        1 + (g % customer_count),
        'Support Issue ' || g,
        'Detailed description of the issue ' || g,
        (ARRAY['low', 'medium', 'high', 'urgent', 'critical']::ticket_priority[])[1 + (g % 5)],
        (ARRAY['open', 'in_progress', 'waiting', 'resolved', 'closed']::ticket_status[])[1 + (g % 5)],
        1 + (g % 30),
        CURRENT_TIMESTAMP - (g * 3 || ' hours')::INTERVAL
    FROM generate_series(1, 1000) g;

    -- Ticket comments
    INSERT INTO ticket_comments (ticket_id, author_id, is_internal, content, created_at)
    SELECT
        t.id,
        1 + (g % 50),
        (g % 3 = 0),
        'Comment ' || g || ' on ticket',
        t.created_at + (g || ' hours')::INTERVAL
    FROM tickets t
    CROSS JOIN generate_series(1, 3) g
    WHERE t.id <= 500;

    -- ==========================================================================
    -- Projects Data
    -- ==========================================================================

    -- Projects
    FOR i IN 1..100 LOOP
        INSERT INTO projects (
            project_code, name, description, customer_id, status, priority,
            start_date, target_end_date, budget, manager_id, department_id
        ) VALUES (
            'PRJ-' || LPAD(i::TEXT, 4, '0'),
            'Project ' || i || ' - ' || CASE (i % 5)
                WHEN 0 THEN 'Implementation' WHEN 1 THEN 'Migration' WHEN 2 THEN 'Development'
                WHEN 3 THEN 'Integration' ELSE 'Upgrade'
            END,
            'Description for project ' || i,
            CASE WHEN i % 3 = 0 THEN 1 + (i % customer_count) ELSE NULL END,
            (ARRAY['planning', 'active', 'on_hold', 'completed', 'cancelled']::project_status[])[1 + (i % 5)],
            (ARRAY['low', 'medium', 'high', 'critical']::task_priority[])[1 + (i % 4)],
            CURRENT_DATE - ((random() * 180)::INTEGER || ' days')::INTERVAL,
            CURRENT_DATE + ((random() * 180)::INTEGER || ' days')::INTERVAL,
            (random() * 500000 + 10000)::DECIMAL(15,2),
            1 + (i % 30),
            1 + (i % 12)
        )
        RETURNING id INTO v_project_id;

        -- Project members (3-8 per project)
        INSERT INTO project_members (project_id, employee_id, role, allocated_hours)
        SELECT
            v_project_id,
            (i * 5 + g) % emp_count + 1,
            CASE (g % 4)
                WHEN 0 THEN 'Lead' WHEN 1 THEN 'Developer' WHEN 2 THEN 'Analyst' ELSE 'Tester'
            END,
            (random() * 100 + 20)::DECIMAL(8,2)
        FROM generate_series(1, 3 + (i % 6)) g
        ON CONFLICT DO NOTHING;

        -- Tasks (5-15 per project)
        INSERT INTO tasks (
            project_id, name, description, status, priority,
            assigned_to, estimated_hours, due_date
        )
        SELECT
            v_project_id,
            'Task ' || g || ' for Project ' || i,
            'Task description ' || g,
            (ARRAY['todo', 'in_progress', 'review', 'done', 'blocked']::task_status[])[1 + (g % 5)],
            (ARRAY['low', 'medium', 'high', 'critical']::task_priority[])[1 + (g % 4)],
            (i * 5 + g) % emp_count + 1,
            (random() * 40 + 2)::DECIMAL(8,2),
            CURRENT_DATE + ((g * 7) || ' days')::INTERVAL
        FROM generate_series(1, 5 + (i % 11)) g;
    END LOOP;

    -- Time entries
    INSERT INTO time_entries (
        employee_id, task_id, project_id, entry_date, hours, description, is_billable
    )
    SELECT
        t.assigned_to,
        t.id,
        t.project_id,
        CURRENT_DATE - (g || ' days')::INTERVAL,
        (random() * 8 + 1)::DECIMAL(4,2),
        'Work on task ' || t.id,
        (random() > 0.2)
    FROM tasks t
    CROSS JOIN generate_series(0, 5) g
    WHERE t.status IN ('in_progress', 'review', 'done')
    AND t.assigned_to IS NOT NULL
    LIMIT 5000;

    -- ==========================================================================
    -- Invoices (AR)
    -- ==========================================================================

    INSERT INTO invoices (
        invoice_number, invoice_type, customer_id, invoice_date, due_date,
        subtotal, tax_amount, total_amount, paid_amount, status, created_by
    )
    SELECT
        'INV-' || LPAD(g::TEXT, 6, '0'),
        'receivable',
        1 + (g % customer_count),
        CURRENT_DATE - (g || ' days')::INTERVAL,
        CURRENT_DATE - (g || ' days')::INTERVAL + '30 days'::INTERVAL,
        (random() * 50000 + 1000)::DECIMAL(15,2),
        0,
        0,
        0,
        CASE (g % 10)
            WHEN 0 THEN 'draft'::invoice_status WHEN 1 THEN 'sent'::invoice_status
            WHEN 2 THEN 'overdue'::invoice_status ELSE 'paid'::invoice_status
        END,
        1 + (g % 20)
    FROM generate_series(1, 1000) g;

    UPDATE invoices SET
        tax_amount = (subtotal * 0.08)::DECIMAL(15,2),
        total_amount = subtotal * 1.08,
        paid_amount = CASE WHEN status = 'paid' THEN subtotal * 1.08 ELSE 0 END
    WHERE invoice_type = 'receivable';

    -- Invoice lines
    INSERT INTO invoice_lines (invoice_id, description, quantity, unit_price, total_price)
    SELECT
        i.id,
        'Service/Product line ' || g,
        (random() * 10 + 1)::INTEGER,
        (random() * 1000 + 50)::DECIMAL(12,2),
        0
    FROM invoices i
    CROSS JOIN generate_series(1, 3) g
    WHERE i.invoice_type = 'receivable';

    UPDATE invoice_lines SET total_price = quantity * unit_price;

    -- ==========================================================================
    -- Journal Entries
    -- ==========================================================================

    INSERT INTO journal_entries (
        entry_number, fiscal_period_id, entry_date, description, is_posted, created_by
    )
    SELECT
        'JE-' || LPAD(g::TEXT, 6, '0'),
        1 + (g % 4),
        CURRENT_DATE - (g * 2 || ' days')::INTERVAL,
        'Journal entry ' || g,
        TRUE,
        1 + (g % 20)
    FROM generate_series(1, 500) g;

    -- Journal lines (balanced debits and credits)
    INSERT INTO journal_lines (entry_id, account_id, transaction_type, amount, description)
    SELECT
        je.id,
        CASE WHEN g = 1 THEN 3 ELSE 17 END,  -- Checking (debit) vs Revenue (credit)
        CASE WHEN g = 1 THEN 'debit'::transaction_type ELSE 'credit'::transaction_type END,
        (random() * 10000 + 100)::DECIMAL(15,2),
        'Journal line ' || g || ' for entry ' || je.id
    FROM journal_entries je
    CROSS JOIN generate_series(1, 2) g;

    -- ==========================================================================
    -- System Settings
    -- ==========================================================================

    INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
    ('company_name', 'Enterprise Corp', 'string', 'Company name'),
    ('fiscal_year_start', '01-01', 'string', 'Fiscal year start date (MM-DD)'),
    ('default_currency', 'USD', 'string', 'Default currency code'),
    ('tax_rate', '0.08', 'decimal', 'Default tax rate'),
    ('invoice_prefix', 'INV', 'string', 'Invoice number prefix'),
    ('po_approval_threshold', '10000', 'decimal', 'PO amount requiring approval'),
    ('time_tracking_enabled', 'true', 'boolean', 'Enable time tracking feature'),
    ('max_leave_days', '25', 'integer', 'Maximum annual leave days');

END $$;
