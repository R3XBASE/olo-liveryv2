# ==================== DATABASE CONNECTION LAYER ====================
import os
import asyncpg
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

class Database:
    """Async PostgreSQL database connection manager"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            print("✓ Database connected successfully")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close all connections"""
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args):
        """Execute query without returning results"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict]:
        """Fetch single row as dict"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch(self, query: str, *args) -> List[Dict]:
        """Fetch multiple rows as list of dicts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

# ==================== USER OPERATIONS ====================
class UserDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, 
                                 first_name: str = None, last_name: str = None) -> Dict:
        """Get user or create if doesn't exist"""
        user = await self.db.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            telegram_id
        )
        
        if user:
            return user
        
        user = await self.db.fetchrow(
            """INSERT INTO users (telegram_id, username, first_name, last_name)
               VALUES ($1, $2, $3, $4)
               RETURNING *""",
            telegram_id, username, first_name, last_name
        )
        return user
    
    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram_id"""
        return await self.db.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            telegram_id
        )
    
    async def get_user_balance(self, telegram_id: int) -> int:
        """Get user's current points balance"""
        result = await self.db.fetchval(
            "SELECT points FROM users WHERE telegram_id = $1",
            telegram_id
        )
        return result or 0
    
    async def add_points(self, telegram_id: int, amount: int) -> bool:
        """Add points to user"""
        await self.db.execute(
            """UPDATE users SET points = points + $1, updated_at = CURRENT_TIMESTAMP
               WHERE telegram_id = $2""",
            amount, telegram_id
        )
        return True
    
    async def deduct_points(self, telegram_id: int, amount: int) -> bool:
        """Deduct points from user (check balance first)"""
        balance = await self.get_user_balance(telegram_id)
        if balance < amount:
            return False
        
        await self.db.execute(
            """UPDATE users SET points = points - $1, updated_at = CURRENT_TIMESTAMP
               WHERE telegram_id = $2""",
            amount, telegram_id
        )
        return True
    
    async def set_points(self, telegram_id: int, amount: int) -> bool:
        """Set user's points to specific amount (admin only)"""
        await self.db.execute(
            """UPDATE users SET points = $1, updated_at = CURRENT_TIMESTAMP
               WHERE telegram_id = $2""",
            amount, telegram_id
        )
        return True
    
    async def get_all_users(self) -> List[Dict]:
        """Get all users (admin)"""
        return await self.db.fetch("SELECT * FROM users ORDER BY created_at DESC")
    
    async def set_admin(self, telegram_id: int, is_admin: bool) -> bool:
        """Set admin status"""
        await self.db.execute(
            "UPDATE users SET is_admin = $1 WHERE telegram_id = $2",
            is_admin, telegram_id
        )
        return True

# ==================== PRODUCT OPERATIONS ====================
class ProductDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_all_products(self) -> List[Dict]:
        """Get all active products"""
        return await self.db.fetch(
            "SELECT * FROM products WHERE is_active = TRUE ORDER BY points ASC"
        )
    
    async def get_product(self, product_id: int) -> Optional[Dict]:
        """Get product by ID"""
        return await self.db.fetchrow(
            "SELECT * FROM products WHERE id = $1",
            product_id
        )
    
    async def create_product(self, name: str, points: int, price_idr: int, 
                            description: str = None) -> Optional[Dict]:
        """Create new product"""
        return await self.db.fetchrow(
            """INSERT INTO products (name, points, price_idr, description)
               VALUES ($1, $2, $3, $4)
               RETURNING *""",
            name, points, price_idr, description
        )
    
    async def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product (points, price, description, is_active)"""
        allowed_fields = {'points', 'price_idr', 'description', 'is_active'}
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields:
            return False
        
        set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(fields.keys())])
        query = f"UPDATE products SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ${len(fields)+1}"
        
        await self.db.execute(query, *fields.values(), product_id)
        return True

# ==================== TRANSACTION OPERATIONS ====================
class TransactionDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_transaction(self, telegram_id: int, product_id: int) -> Optional[Dict]:
        """Create pending transaction"""
        product = await self.db.fetchrow(
            "SELECT * FROM products WHERE id = $1",
            product_id
        )
        
        if not product:
            return None
        
        return await self.db.fetchrow(
            """INSERT INTO transactions (telegram_id, product_id, points, amount_idr)
               VALUES ($1, $2, $3, $4)
               RETURNING *""",
            telegram_id, product_id, product['points'], product['price_idr']
        )
    
    async def get_transaction(self, tx_uuid: str) -> Optional[Dict]:
        """Get transaction by UUID"""
        return await self.db.fetchrow(
            "SELECT * FROM transactions WHERE transaction_uuid = $1",
            UUID(tx_uuid)
        )
    
    async def confirm_transaction(self, tx_uuid: str, admin_id: int) -> bool:
        """Confirm transaction and add points to user"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # Get transaction
                tx = await conn.fetchrow(
                    "SELECT * FROM transactions WHERE transaction_uuid = $1",
                    UUID(tx_uuid)
                )
                
                if not tx or tx['status'] != 'pending':
                    return False
                
                # Add points to user
                await conn.execute(
                    "UPDATE users SET points = points + $1 WHERE telegram_id = $2",
                    tx['points'], tx['telegram_id']
                )
                
                # Mark transaction as confirmed
                await conn.execute(
                    """UPDATE transactions SET status = 'confirmed', confirmed_by_admin = $1, 
                       confirmed_at = CURRENT_TIMESTAMP WHERE transaction_uuid = $2""",
                    admin_id, UUID(tx_uuid)
                )
                
                return True
    
    async def get_user_transactions(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get user's transaction history"""
        return await self.db.fetch(
            """SELECT t.*, p.name, p.points 
               FROM transactions t
               JOIN products p ON t.product_id = p.id
               WHERE t.telegram_id = $1
               ORDER BY t.created_at DESC
               LIMIT $2""",
            telegram_id, limit
        )
    
    async def get_pending_transactions(self) -> List[Dict]:
        """Get all pending transactions (admin)"""
        return await self.db.fetch(
            """SELECT t.*, p.name, u.username
               FROM transactions t
               JOIN products p ON t.product_id = p.id
               JOIN users u ON t.telegram_id = u.telegram_id
               WHERE t.status = 'pending'
               ORDER BY t.created_at ASC"""
        )

# ==================== LIVERY OPERATIONS ====================
class LiveryDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def cache_liveries(self, liveries_data: Dict) -> int:
        """Cache liveries from database"""
        count = 0
        for car_code, car_data in liveries_data.items():
            car_name = car_data.get('carName', 'Unknown')
            for livery in car_data.get('liveries', []):
                livery_id = livery.get('id')
                livery_name = livery.get('name')
                
                if livery_id and livery_name:
                    await self.db.execute(
                        """INSERT INTO liveries_cache (livery_id, livery_name, car_code, car_name)
                           VALUES ($1, $2, $3, $4)
                           ON CONFLICT (livery_id) DO UPDATE
                           SET livery_name = $2, car_name = $4, last_updated = CURRENT_TIMESTAMP""",
                        livery_id, livery_name, car_code, car_name
                    )
                    count += 1
        
        return count
    
    async def get_cars_grouped(self) -> Dict[str, List[Dict]]:
        """Get all liveries grouped by car"""
        liveries = await self.db.fetch(
            """SELECT DISTINCT car_code, car_name FROM liveries_cache
               ORDER BY car_name ASC"""
        )
        
        result = {}
        for car in liveries:
            car_liveries = await self.db.fetch(
                """SELECT id, livery_id, livery_name FROM liveries_cache
                   WHERE car_code = $1
                   ORDER BY livery_name ASC""",
                car['car_code']
            )
            result[car['car_code']] = {
                'carName': car['car_name'],
                'liveries': car_liveries
            }
        
        return result
    
    async def get_livery(self, livery_id: str) -> Optional[Dict]:
        """Get livery by ID"""
        return await self.db.fetchrow(
            "SELECT * FROM liveries_cache WHERE livery_id = $1",
            livery_id
        )

# ==================== INJECTION OPERATIONS ====================
class InjectionDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def log_injection(self, telegram_id: int, livery_id: str, livery_name: str,
                           playfab_token: str, status: str, points_deducted: int = None,
                           response_data: Dict = None, error_message: str = None,
                           execution_time_ms: int = None) -> Optional[Dict]:
        """Log injection attempt"""
        return await self.db.fetchrow(
            """INSERT INTO injections 
               (telegram_id, livery_id, livery_name, playfab_token, status, 
                points_deducted, response_data, error_message, execution_time_ms)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            telegram_id, livery_id, livery_name, playfab_token, status,
            points_deducted, json.dumps(response_data) if response_data else None,
            error_message, execution_time_ms
        )
    
    async def get_user_injections(self, telegram_id: int, limit: int = 20) -> List[Dict]:
        """Get user's injection history"""
        return await self.db.fetch(
            """SELECT * FROM injections
               WHERE telegram_id = $1
               ORDER BY created_at DESC
               LIMIT $2""",
            telegram_id, limit
        )
    
    async def get_user_injections_today(self, telegram_id: int) -> int:
        """Count injections by user today"""
        count = await self.db.fetchval(
            """SELECT COUNT(*) FROM injections
               WHERE telegram_id = $1 AND status = 'success'
               AND DATE(created_at) = CURRENT_DATE""",
            telegram_id
        )
        return count or 0

# ==================== SETTINGS OPERATIONS ====================
class SettingsDB:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_setting(self, key: str) -> Optional[str]:
        """Get setting value"""
        result = await self.db.fetchval(
            "SELECT setting_value FROM admin_settings WHERE setting_key = $1",
            key
        )
        return result
    
    async def set_setting(self, key: str, value: str, updated_by: int = None) -> bool:
        """Set or update setting"""
        await self.db.execute(
            """INSERT INTO admin_settings (setting_key, setting_value, updated_by)
               VALUES ($1, $2, $3)
               ON CONFLICT (setting_key) DO UPDATE
               SET setting_value = $2, updated_by = $3, updated_at = CURRENT_TIMESTAMP""",
            key, value, updated_by
        )
        return True
    
    async def get_injection_cost(self) -> int:
        """Get current injection cost in points"""
        cost = await self.get_setting('injection_cost_points')
        return int(cost) if cost else 1000
