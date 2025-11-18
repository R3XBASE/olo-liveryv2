# ==================== TELEGRAM BOT HANDLERS ====================
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

# Import database modules
try:
    from database.db import Database, UserDB, ProductDB, TransactionDB, LiveryDB, InjectionDB, SettingsDB
    from livery.injection import LiveryInjector
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database.db import Database, UserDB, ProductDB, TransactionDB, LiveryDB, InjectionDB, SettingsDB
    from livery.injection import LiveryInjector

from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

# ========== CONVERSATION STATES ==========
SELECT_CAR, SELECT_LIVERY, CONFIRM_INJECT = range(3)

class BotHandlers:
    def __init__(self, db: Database, injector: LiveryInjector, admin_ids: list):
        self.db = db
        self.injector = injector
        self.admin_ids = admin_ids
        
        # Database layer
        self.user_db = UserDB(db)
        self.product_db = ProductDB(db)
        self.transaction_db = TransactionDB(db)
        self.livery_db = LiveryDB(db)
        self.injection_db = InjectionDB(db)
        self.settings_db = SettingsDB(db)
    
    async def _ensure_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin"""
        if update.effective_user.id not in self.admin_ids:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return False
        return True
    
    # ========== USER COMMANDS ==========
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create or get user
        await self.user_db.get_or_create_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
            [InlineKeyboardButton("🎨 Browse Liveries", callback_data="browse_liveries")],
            [InlineKeyboardButton("💳 Buy Points", callback_data="buy_points")],
            [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 Welcome {user.first_name}!\n\n"
            "This bot allows you to inject game liveries using points.\n\n"
            "1000 points = 1 livery injection\n\n"
            "What would you like to do?",
            reply_markup=reply_markup
        )
    
    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        user = update.effective_user
        balance = await self.user_db.get_user_balance(user.id)
        
        await update.message.reply_text(
            f"💰 Your Balance\n\n"
            f"Points: {balance:,}\n\n"
            f"1000 points = 1 livery injection"
        )
    
    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile"""
        user_data = await self.user_db.get_user(update.effective_user.id)
        injections_today = await self.injection_db.get_user_injections_today(update.effective_user.id)
        
        text = (
            f"👤 Your Profile\n\n"
            f"ID: {user_data['telegram_id']}\n"
            f"Username: @{user_data['username'] or 'N/A'}\n"
            f"Points: {user_data['points']:,}\n"
            f"Injections Today: {injections_today}\n"
            f"Member Since: {user_data['created_at'].strftime('%Y-%m-%d')}"
        )
        
        await update.message.reply_text(text)
    
    # ========== CALLBACK QUERIES ==========
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "balance":
            balance = await self.user_db.get_user_balance(query.from_user.id)
            await query.edit_message_text(
                f"💰 Your Balance\n\n"
                f"Points: {balance:,}\n\n"
                f"1000 points = 1 livery injection"
            )
        
        elif query.data == "browse_liveries":
            await self.show_cars(query, context)
        
        elif query.data == "buy_points":
            await self.show_products(query)
        
        elif query.data == "profile":
            user_data = await self.user_db.get_user(query.from_user.id)
            injections_today = await self.injection_db.get_user_injections_today(query.from_user.id)
            
            text = (
                f"👤 Your Profile\n\n"
                f"ID: {user_data['telegram_id']}\n"
                f"Username: @{user_data['username'] or 'N/A'}\n"
                f"Points: {user_data['points']:,}\n"
                f"Injections Today: {injections_today}\n"
                f"Member Since: {user_data['created_at'].strftime('%Y-%m-%d')}"
            )
            await query.edit_message_text(text)
        
        elif query.data == "back_main":
            keyboard = [
                [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
                [InlineKeyboardButton("🎨 Browse Liveries", callback_data="browse_liveries")],
                [InlineKeyboardButton("💳 Buy Points", callback_data="buy_points")],
                [InlineKeyboardButton("👤 Profile", callback_data="profile")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👋 Main Menu\n\nWhat would you like to do?",
                reply_markup=reply_markup
            )
        
        elif query.data.startswith("car_"):
            car_code = query.data.split("_", 1)[1]
            await self.show_liveries(query, car_code)
        
        elif query.data.startswith("livery_"):
            livery_id = query.data.split("_", 1)[1]
            await self.show_livery_confirm(query, livery_id)
        
        elif query.data.startswith("inject_"):
            livery_id = query.data.split("_", 1)[1]
            await self.execute_injection(query, livery_id)
        
        elif query.data.startswith("buy_"):
            product_id = int(query.data.split("_")[1])
            await self.create_transaction(query, product_id)
    
    async def show_cars(self, query, context):
        """Show available cars"""
        cars_data = await self.livery_db.get_cars_grouped()
        
        if not cars_data:
            await query.edit_message_text("❌ No cars available yet.")
            return
        
        keyboard = []
        for car_code, car_info in sorted(cars_data.items()):
            car_name = car_info['carName']
            livery_count = len(car_info['liveries'])
            keyboard.append([
                InlineKeyboardButton(
                    f"🚗 {car_name} ({livery_count})",
                    callback_data=f"car_{car_code}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🚗 Select a Car\n\nChoose a car to see available liveries:",
            reply_markup=reply_markup
        )
    
    async def show_liveries(self, query, car_code):
        """Show liveries for car"""
        cars_data = await self.livery_db.get_cars_grouped()
        
        if car_code not in cars_data:
            await query.edit_message_text("❌ Car not found.")
            return
        
        car_info = cars_data[car_code]
        car_name = car_info['carName']
        liveries = car_info['liveries']
        
        if not liveries:
            await query.edit_message_text("❌ No liveries available for this car.")
            return
        
        keyboard = []
        for livery in liveries[:8]:  # Limit to 8 per page
            keyboard.append([
                InlineKeyboardButton(
                    f"🎨 {livery['livery_name'][:30]}",
                    callback_data=f"livery_{livery['livery_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="browse_liveries")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎨 Liveries for {car_name}\n\n"
            f"Select a livery to inject:",
            reply_markup=reply_markup
        )
    
    async def show_livery_confirm(self, query, livery_id):
        """Show livery details and confirm"""
        livery = await self.livery_db.get_livery(livery_id)
        
        if not livery:
            await query.answer("❌ Livery not found")
            return
        
        injection_cost = await self.settings_db.get_injection_cost()
        user_balance = await self.user_db.get_user_balance(query.from_user.id)
        
        keyboard = []
        
        if user_balance >= injection_cost:
            keyboard.append([
                InlineKeyboardButton("✅ Inject Now", callback_data=f"inject_{livery_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("💳 Buy Points", callback_data="buy_points")
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="browse_liveries")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎨 {livery['livery_name']}\n"
            f"🚗 {livery['car_name']}\n\n"
            f"💰 Cost: {injection_cost:,} points\n"
            f"💵 Your Balance: {user_balance:,} points\n\n"
            f"{'✅ You have enough points!' if user_balance >= injection_cost else '❌ Insufficient points'}",
            reply_markup=reply_markup
        )
    
    async def execute_injection(self, query, livery_id):
        """Execute livery injection"""
        await query.answer()
        await query.edit_message_text("⏳ Injecting livery...")
        
        try:
            livery = await self.livery_db.get_livery(livery_id)
            user_data = await self.user_db.get_user(query.from_user.id)
            injection_cost = await self.settings_db.get_injection_cost()
            
            if not user_data['playfab_token']:
                await query.edit_message_text(
                    "❌ Error: No PlayFab token configured.\n"
                    "Please contact an admin to set up your account."
                )
                return
            
            # Check balance
            if user_data['points'] < injection_cost:
                await query.edit_message_text(
                    f"❌ Insufficient points.\n"
                    f"You need {injection_cost:,} points but have {user_data['points']:,}"
                )
                return
            
            # Execute injection
            success, response = await self.injector.inject_async(
                livery_id,
                user_data['playfab_token'],
                user_data['playfab_token']
            )
            
            if success:
                # Deduct points
                await self.user_db.deduct_points(query.from_user.id, injection_cost)
                
                # Log injection
                await self.injection_db.log_injection(
                    telegram_id=query.from_user.id,
                    livery_id=livery_id,
                    livery_name=livery['livery_name'],
                    playfab_token=user_data['playfab_token'],
                    status='success',
                    points_deducted=injection_cost,
                    response_data=response,
                    execution_time_ms=response.get('execution_time_ms')
                )
                
                new_balance = user_data['points'] - injection_cost
                await query.edit_message_text(
                    f"✅ Injection Successful!\n\n"
                    f"🎨 {livery['livery_name']}\n"
                    f"💰 Points Used: {injection_cost:,}\n"
                    f"💵 New Balance: {new_balance:,}"
                )
            else:
                await self.injection_db.log_injection(
                    telegram_id=query.from_user.id,
                    livery_id=livery_id,
                    livery_name=livery['livery_name'],
                    playfab_token=user_data['playfab_token'],
                    status='failed',
                    error_message=response.get('error')
                )
                
                await query.edit_message_text(
                    f"❌ Injection Failed\n\n"
                    f"Error: {response.get('error')}\n\n"
                    f"Your points were not deducted."
                )
        
        except Exception as e:
            logger.error(f"Injection error: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_products(self, query):
        """Show topup products"""
        products = await self.product_db.get_all_products()
        
        if not products:
            await query.edit_message_text("❌ No products available.")
            return
        
        keyboard = []
        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"💎 {product['name']} - Rp{product['price_idr']:,}",
                    callback_data=f"buy_{product['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="balance")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💳 Topup Packages\n\n"
            "Select a package to purchase:",
            reply_markup=reply_markup
        )
    
    async def create_transaction(self, query, product_id):
        """Create transaction"""
        product = await self.product_db.get_product(product_id)
        
        if not product:
            await query.answer("❌ Product not found")
            return
        
        tx = await self.transaction_db.create_transaction(query.from_user.id, product_id)
        
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data="buy_points")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧾 Transaction Details\n\n"
            f"Package: {product['name']}\n"
            f"Points: {product['points']:,}\n"
            f"Amount: Rp{product['price_idr']:,}\n"
            f"Transaction ID: {str(tx['transaction_uuid'])[:8]}...\n\n"
            f"Status: ⏳ Pending Admin Confirmation\n\n"
            f"Please send the payment to admin and provide this transaction ID.",
            reply_markup=reply_markup
        )
    
    # ========== ADMIN COMMANDS ==========
    
    async def admin_addpoints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /addpoints <telegram_id> <amount>"""
        if not await self._ensure_admin(update, context):
            return
        
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /addpoints <telegram_id> <amount>"
                )
                return
            
            telegram_id = int(args[0])
            amount = int(args[1])
            
            await self.user_db.add_points(telegram_id, amount)
            
            await update.message.reply_text(
                f"✅ Added {amount:,} points to user {telegram_id}"
            )
        
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments")
    
    async def admin_setpoints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /setpoints <telegram_id> <amount>"""
        if not await self._ensure_admin(update, context):
            return
        
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Usage: /setpoints <telegram_id> <amount>"
                )
                return
            
            telegram_id = int(args[0])
            amount = int(args[1])
            
            await self.user_db.set_points(telegram_id, amount)
            
            await update.message.reply_text(
                f"✅ Set points for user {telegram_id} to {amount:,}"
            )
        
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments")
    
    async def admin_createproduct(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /createproduct <name> <points> <price_idr>"""
        if not await self._ensure_admin(update, context):
            return
        
        try:
            args = context.args
            if len(args) < 3:
                await update.message.reply_text(
                    "Usage: /createproduct <name> <points> <price_idr>"
                )
                return
            
            name = args[0]
            points = int(args[1])
            price = int(args[2])
            
            product = await self.product_db.create_product(name, points, price)
            
            await update.message.reply_text(
                f"✅ Created product: {product['name']}\n"
                f"Points: {product['points']:,}\n"
                f"Price: Rp{product['price_idr']:,}"
            )
        
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments")
    
    async def admin_confirmtx(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /confirmtx <uuid>"""
        if not await self._ensure_admin(update, context):
            return
        
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text(
                    "Usage: /confirmtx <uuid>"
                )
                return
            
            tx_uuid = args[0]
            success = await self.transaction_db.confirm_transaction(tx_uuid, update.effective_user.id)
            
            if success:
                tx = await self.transaction_db.get_transaction(tx_uuid)
                await update.message.reply_text(
                    f"✅ Transaction confirmed!\n"
                    f"User ID: {tx['telegram_id']}\n"
                    f"Points Added: {tx['points']:,}"
                )
            else:
                await update.message.reply_text("❌ Transaction not found or already confirmed")
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def admin_listusers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /listusers"""
        if not await self._ensure_admin(update, context):
            return
        
        users = await self.user_db.get_all_users()
        
        text = "👥 All Users\n\n"
        for user in users[:20]:  # Show first 20
            text += f"ID: {user['telegram_id']}\n"
            text += f"Username: @{user['username'] or 'N/A'}\n"
            text += f"Points: {user['points']:,}\n"
            text += f"Created: {user['created_at'].strftime('%Y-%m-%d')}\n\n"
        
        if len(users) > 20:
            text += f"... and {len(users) - 20} more users"
        
        await update.message.reply_text(text)
    
    async def admin_injectionlog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /injectionlog <telegram_id>"""
        if not await self._ensure_admin(update, context):
            return
        
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text(
                    "Usage: /injectionlog <telegram_id>"
                )
                return
            
            telegram_id = int(args[0])
            injections = await self.injection_db.get_user_injections(telegram_id, 10)
            
            text = f"📋 Injection Log for User {telegram_id}\n\n"
            
            if not injections:
                text += "No injections found"
            else:
                for inj in injections:
                    status = "✅" if inj['status'] == 'success' else "❌"
                    text += f"{status} {inj['livery_name']}\n"
                    text += f"Time: {inj['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            
            await update.message.reply_text(text)
        
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments")
