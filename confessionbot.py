import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = '8467732523:AAEphPaSVf2yVxCGgaRyTK15ofY59kAvkOA'
CHANNEL_ID = '@ConfessionBD'  # or -100xxxxxxxxxx for private channels
ADMIN_IDS = [1918217865]  # List of admin user IDs who can approve/reject

# Store pending confessions
pending_confessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_text = (
        "🎭 *Welcome to Anonymous Confessions Bot!*\n\n"
        "Share your thoughts, feelings, or secrets anonymously.\n\n"
        "📝 *How to use:*\n"
        "Just send me your confession as a text message, and I'll post it "
        "anonymously to the channel after review.\n\n"
        "Your identity will remain completely anonymous! 🤫"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_confession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming confession messages"""
    user_id = update.message.from_user.id
    confession_text = update.message.text
    
    # Create unique confession ID
    confession_id = f"{user_id}_{update.message.message_id}"
    
    # Store confession for admin approval
    pending_confessions[confession_id] = {
        'user_id': user_id,
        'text': confession_text,
        'username': update.message.from_user.username or 'Unknown'
    }
    
    # Create approval buttons for admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{confession_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{confession_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send to admins for approval
    admin_message = (
        f"📩 *New Confession*\n\n"
        f"{confession_text}\n\n"
        f"_From: {update.message.from_user.first_name}_"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to send to admin {admin_id}: {e}")
    
    # Confirm receipt to user
    await update.message.reply_text(
        "✅ Your confession has been received and sent for review!\n"
        "It will be posted anonymously once approved. 🎭"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval/rejection callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check if user is admin
    if user_id not in ADMIN_IDS:
        await query.answer("You are not authorized to do this.", show_alert=True)
        return
    
    await query.answer()
    
    action, confession_id = query.data.split('_', 1)
    
    if confession_id not in pending_confessions:
        await query.edit_message_text("❌ This confession has already been processed.")
        return
    
    confession = pending_confessions[confession_id]
    
    if action == "approve":
        # Post to channel
        try:
            channel_message = (
                f"🎭 *Anonymous Confession*\n\n"
                f"{confession['text']}\n\n"
                f"_Want to share your confession? Message @YourBotUsername_"
            )
            
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=channel_message,
                parse_mode='Markdown'
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=confession['user_id'],
                    text="✅ Your confession has been posted anonymously! 🎉"
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
            
            await query.edit_message_text(
                f"✅ *Confession Approved and Posted*\n\n{confession['text']}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
            await query.edit_message_text(f"❌ Failed to post: {str(e)}")
    
    elif action == "reject":
        await query.edit_message_text(
            f"❌ *Confession Rejected*\n\n{confession['text']}",
            parse_mode='Markdown'
        )
        
        # Optionally notify user (you can remove this if you want silent rejection)
        try:
            await context.bot.send_message(
                chat_id=confession['user_id'],
                text="Your confession was not approved. Please ensure it follows community guidelines."
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    
    # Remove from pending
    del pending_confessions[confession_id]

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics (admin only)"""
    user_id = update.message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to view statistics.")
        return
    
    stats_text = (
        f"📊 *Bot Statistics*\n\n"
        f"Pending confessions: {len(pending_confessions)}\n"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confession))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Start the bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()