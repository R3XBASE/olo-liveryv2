# Admin Guide - Managing the Bot

## User & Points Management

### Adding Points to User
\`\`\`
/addpoints 123456789 5000
\`\`\`
Adds 5000 points to user with ID 123456789.

### Setting Points (Exact Amount)
\`\`\`
/setpoints 123456789 10000
\`\`\`
Sets user's points to exactly 10000 (replaces current amount).

## Product Management

### Creating Topup Packages
\`\`\`
/createproduct "Special50K" 50000 50000
\`\`\`
Creates a new package:
- Name: "Special50K"
- Points: 50000
- Price: Rp50000

### Managing Existing Products
Edit directly in database:
\`\`\`sql
UPDATE products SET is_active = FALSE WHERE name = '10K Points';
\`\`\`

## Transaction Management

### Confirming Purchases
1. User initiates purchase via `/buy`
2. User shows transaction ID to admin
3. Admin receives payment
4. Admin confirms: `/confirmtx <uuid>`
5. User gets points automatically

Example:
\`\`\`
/confirmtx a1b2c3d4-e5f6-47f8-9a0b-1c2d3e4f5a6b
\`\`\`

### Viewing Pending Transactions
\`\`\`sql
SELECT * FROM transactions WHERE status = 'pending' ORDER BY created_at ASC;
\`\`\`

## Monitoring & Debugging

### Check Injection History
\`\`\`
/injectionlog 123456789
\`\`\`
Shows last 10 injections for user.

### List All Users
\`\`\`
/listusers
\`\`\`
Shows all registered users with their balances.

### View All Transactions
\`\`\`sql
SELECT t.*, p.name FROM transactions t 
JOIN products p ON t.product_id = p.id 
ORDER BY t.created_at DESC;
\`\`\`

### Check Injection Success Rate
\`\`\`sql
SELECT status, COUNT(*) 
FROM injections 
GROUP BY status;
\`\`\`

## Maintenance

### Clear Old Data
\`\`\`sql
-- Delete injections older than 90 days
DELETE FROM injections WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete old transactions
DELETE FROM transactions WHERE created_at < NOW() - INTERVAL '30 days' AND status = 'confirmed';
\`\`\`

### Database Health Check
\`\`\`sql
-- Check database size
SELECT 
  schemaname,
  SUM(pg_total_relation_size(schemaname||'.'||tablename)) / 1024 / 1024 AS size_mb
FROM pg_tables
GROUP BY schemaname;

-- Analyze tables for performance
ANALYZE;
\`\`\`

## Security

### Change Admin IDs
Update in Vercel environment:
1. Go to Project Settings → Environment Variables
2. Edit `ADMIN_IDS`
3. Redeploy

### Reset PlayFab Tokens
\`\`\`sql
UPDATE users SET playfab_token = NULL WHERE telegram_id = 123456789;
\`\`\`

### Disable Specific Users
\`\`\`sql
UPDATE users SET playfab_token = NULL WHERE telegram_id = 123456789;
\`\`\`

## Backup Strategy

Export database regularly:
\`\`\`bash
# Install pgAdmin or use Neon dashboard backup feature
\`\`\`

Store backups securely and test restoration monthly.
