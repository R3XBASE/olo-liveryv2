# Telegram Livery Injection Bot - Deployment Guide

## Prerequisites
- Telegram Bot Token (from @BotFather)
- Neon PostgreSQL database (free tier available at neon.tech)
- Vercel account (free tier available at vercel.com)
- Admin Telegram IDs for authorization

## Step 1: Setup Database (Neon PostgreSQL)

1. Go to [neon.tech](https://neon.tech) and create a free account
2. Create a new project and database
3. Run the initialization script:
   - Copy all queries from `scripts/001_init_database.sql`
   - Execute in Neon SQL Editor
4. Copy the connection URL from Neon dashboard (looks like: `postgresql://user:password@ep-xxx.us-east-1.neon.tech/dbname?sslmode=require`)

## Step 2: Get Telegram Bot Token

1. Open Telegram and chat with @BotFather
2. Send `/newbot` and follow instructions
3. Save the token (format: `123456789:ABCdefGHIjklmnoPQRstuvWXYZ`)

## Step 3: Deploy to Vercel

1. **Install Vercel CLI:**
   \`\`\`bash
   npm i -g vercel
   \`\`\`

2. **Login to Vercel:**
   \`\`\`bash
   vercel login
   \`\`\`

3. **Link this project:**
   \`\`\`bash
   vercel link
   \`\`\`

4. **Set Environment Variables in Vercel Dashboard:**
   - Go to Project Settings → Environment Variables
   - Add:
     - `BOT_TOKEN`: Your bot token from @BotFather
     - `DATABASE_URL`: PostgreSQL URL from Neon
     - `ADMIN_IDS`: Your Telegram ID (get it: send `/start` to @userinfobot)
     - `LIVERIES_DB_URL`: (optional) Liveries database URL

5. **Deploy:**
   \`\`\`bash
   vercel --prod
   \`\`\`

6. **Get your Vercel URL:**
   - Find it in Vercel dashboard (e.g., `https://your-project.vercel.app`)

## Step 4: Set Webhook

Replace `YOUR_VERCEL_URL` and `YOUR_BOT_TOKEN` in this command:

\`\`\`bash
curl -X POST \
  https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://YOUR_VERCEL_URL/api/index.py"}'
\`\`\`

To verify webhook is set:
\`\`\`bash
curl https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo
\`\`\`

## Step 5: Configure PlayFab Tokens

Each user needs a PlayFab token. You can set it via:

### Option A: Admin Command
\`\`\`
/settoken @username playfab_token_here
\`\`\`

### Option B: Direct Database Update
\`\`\`sql
UPDATE users SET playfab_token = 'token_here' WHERE telegram_id = 123456789;
\`\`\`

## Admin Commands

- `/addpoints <telegram_id> <amount>` - Add points to user
- `/setpoints <telegram_id> <amount>` - Set user's points to exact amount
- `/createproduct <name> <points> <price>` - Create topup package
- `/confirmtx <uuid>` - Confirm pending transaction
- `/listusers` - Show all users
- `/injectionlog <telegram_id>` - Show user's injection history

## User Commands

- `/start` - Main menu
- `/balance` - Show points balance
- `/profile` - View profile
- And inline buttons for browsing liveries and buying points

## Troubleshooting

### Bot not responding
1. Check if webhook is correctly set: `https://api.telegram.org/botTOKEN/getWebhookInfo`
2. Verify environment variables in Vercel dashboard
3. Check Vercel function logs for errors

### Database connection errors
- Verify `DATABASE_URL` format
- Check if Neon IP whitelist includes Vercel IPs (usually auto-allowed)
- Test connection: `psql DATABASE_URL`

### Injections failing
- Verify PlayFab token is correct
- Check user has sufficient points
- Review injection logs: `/injectionlog <user_id>`

## Monitoring

View logs in Vercel dashboard:
- Go to Project → Logs (Deployments)
- Or use CLI: `vercel logs`

## Cost

- **Neon PostgreSQL**: Free tier (5 GB storage, 0.5 CPU)
- **Vercel**: Free tier (500,000 requests/month)
- **Total**: $0/month with free tiers
