# Slack Integration Setup

This guide shows you how to set up interactive database analysis via Slack!

## Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name it **"DB Analyst"** and choose your workspace
4. Go to **"OAuth & Permissions"** in the sidebar
5. Under **"Bot Token Scopes"**, add these scopes:
   - `chat:write` - Post messages
   - `channels:history` - Read channel messages
   - `channels:read` - View channels
6. Click **"Install to Workspace"** at the top
7. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)
8. Save it as a Tower secret:

```bash
tower secrets create --environment="prod" \
  --name=DB_ANALYST_SLACK_BOT_TOKEN --value="xoxb-your-token-here"
```

## Step 2: Invite Bot to Channel

In any Slack channel, type:
```
/invite @DB Analyst
```

## Step 3: Get Channel ID

1. Right-click on the channel name in Slack
2. Select **"View channel details"**
3. Scroll down and copy the **Channel ID** (looks like `C01234567`)

## Step 4: Run Your First Analysis

```bash
tower run --environment="prod" \
  --parameter=user_question='What tables exist in the database?' \
  --parameter=slack_channel='C01234567'
```

The bot will post results to that Slack channel!

## Step 5: Continue the Conversation (Thread)

When the bot posts, it will output a `thread_ts` value. Use this to reply in the same thread:

```bash
tower run --environment="prod" \
  --parameter=user_question='Show me the first 5 rows of the users table' \
  --parameter=slack_channel='C01234567' \
  --parameter=slack_thread_ts='1234567890.123456'
```

## Interactive Usage Pattern

1. **Ask question** → Tower runs → Bot posts answer in Slack
2. **See thread_ts** in logs → Copy it
3. **Ask follow-up** with same `thread_ts` → Bot replies in thread
4. **Continue conversation** by re-using the thread_ts!

## Example: Multi-Turn Conversation

```bash
# Initial question
tower run --environment="prod" \
  --parameter=user_question='What tables exist?' \
  --parameter=slack_channel='C01234567'
# Output: thread_ts: 1709856234.123456

# Follow-up 1
tower run --environment="prod" \
  --parameter=user_question='How many users do we have?' \
  --parameter=slack_channel='C01234567' \
  --parameter=slack_thread_ts='1709856234.123456'

# Follow-up 2
tower run --environment="prod" \
  --parameter=user_question='What is the average order value?' \
  --parameter=slack_channel='C01234567' \
  --parameter=slack_thread_ts='1709856234.123456'
```

All answers appear in the same Slack thread! 🎉

## Pro Tips

- **Bookmark** the channel where the bot posts
- **Pin** frequently used thread_ts values in Slack
- **Set up aliases** in your shell for common commands
- **Use Slack threads** to organize different analysis sessions
- **Share threads** with teammates for collaboration

## Future Enhancement: Slack Bot Listener

Want fully automatic responses? You can enhance this with a Slack bot that:
1. Listens for @mentions
2. Triggers Tower runs automatically
3. Passes back the thread_ts

This would make it feel like chatting with the bot in real-time!
