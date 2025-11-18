-- ==================== DATABASE INITIALIZATION ====================
-- Create all necessary tables for the Telegram Livery Injection Bot
-- Run this script once on your Neon PostgreSQL database

-- Users table - stores user information and points balance
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    points BIGINT DEFAULT 0,
    playfab_token TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table - stores topup packages
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    points BIGINT NOT NULL,
    price_idr BIGINT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table - tracks user purchases
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL,
    product_id INTEGER NOT NULL,
    points BIGINT NOT NULL,
    amount_idr BIGINT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, confirmed, failed, cancelled
    payment_method VARCHAR(100),
    payment_reference VARCHAR(255),
    confirmed_by_admin BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Accounts table - stores PlayFab tokens for injection
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    playfab_token TEXT NOT NULL,
    account_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

-- Liveries cache table - stores available liveries from database
CREATE TABLE IF NOT EXISTS liveries_cache (
    id SERIAL PRIMARY KEY,
    livery_id VARCHAR(255) UNIQUE NOT NULL,
    livery_name VARCHAR(255) NOT NULL,
    car_code VARCHAR(50) NOT NULL,
    car_name VARCHAR(255) NOT NULL,
    points_cost BIGINT DEFAULT 1000,
    is_available BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Injections table - logs all livery injection attempts
CREATE TABLE IF NOT EXISTS injections (
    id SERIAL PRIMARY KEY,
    injection_uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL,
    livery_id VARCHAR(255) NOT NULL,
    livery_name VARCHAR(255) NOT NULL,
    playfab_token TEXT NOT NULL,
    status VARCHAR(50), -- success, failed, pending
    points_deducted BIGINT,
    response_data JSONB,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

-- Admin settings table - configurable bot parameters
CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_by BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_is_admin ON users(is_admin);
CREATE INDEX idx_transactions_telegram_id ON transactions(telegram_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_uuid ON transactions(transaction_uuid);
CREATE INDEX idx_injections_telegram_id ON injections(telegram_id);
CREATE INDEX idx_injections_status ON injections(status);
CREATE INDEX idx_injections_uuid ON injections(injection_uuid);
CREATE INDEX idx_liveries_cache_livery_id ON liveries_cache(livery_id);
CREATE INDEX idx_liveries_cache_car_code ON liveries_cache(car_code);

-- Insert default topup packages
INSERT INTO products (name, points, price_idr, description) VALUES
    ('5K Points', 5000, 5000, '5000 poin = 5x livery injection'),
    ('10K Points', 10000, 10000, '10000 poin = 10x livery injection'),
    ('25K Points', 25000, 25000, '25000 poin = 25x livery injection')
ON CONFLICT (name) DO NOTHING;

-- Insert default admin settings
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
    ('injection_cost_points', '1000', 'Points required per livery injection'),
    ('max_injections_per_day', '10', 'Maximum liveries per user per day'),
    ('bot_maintenance_mode', 'false', 'Set to true to disable bot temporarily'),
    ('webhook_secret', '', 'Secret key for webhook verification')
ON CONFLICT (setting_key) DO NOTHING;
