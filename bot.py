async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    text = update.message.text.strip()
    step = u.get("step")

    # ===== custom property =====
    if step == "property_custom":
        u["property"] = text
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")
        return

    # ===== city =====
    if step == "city":
        u["city"] = text
        u["step"] = "district"
        await update.message.reply_text("🗺 В якому районі?")
        return

    # ===== district =====
    if step == "district":
        u["district"] = text
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")
        return

    # ===== for whom =====
    if step == "for_whom":
        u["for_whom"] = text
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")
        return

    # ===== job =====
    if step == "job":
        u["job"] = text
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? (Так / Ні)")
        return

    # ===== children =====
    if step == "children":
        u["children"] = text
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи маєте тваринок? Якщо так — напишіть які.")
        return

    # ===== pets =====
    if step == "pets":
        u["pets"] = text
        u["step"] = "parking"
        await update.message.reply_text(
            "🚗 Чи потрібне паркування?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")]
            ])
        )
        return

    # ===== move in =====
    if step == "move_in":
        u["move_in"] = text
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")
        return

    # ===== view time =====
    if step == "view_time":
        u["view_time"] = text
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")
        return

    # ===== wishes =====
    if step == "wishes":
        u["wishes"] = text
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")
        return

    # ===== budget =====
    if step == "budget":
        u["budget"] = text
        u["step"] = "location"
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
            ])
        )
        return

    # ===== custom location =====
    if step == "location_custom":
        u["location"] = text
        u["step"] = "view_format"
        await ask_view_format(update.message)
        return

    # ===== name (FINAL STEP) =====
    if step == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1

        u["name"] = text
        u["req_id"] = str(REQUEST_COUNTER)

        await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            summary(u),
            reply_markup=status_keyboard(u["req_id"]),
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом **24–48 годин**.\n\n"
            "🔗 Долучайтесь до групи з пропозиціями житла:\n"
            "https://t.me/+IhcJixOP1_QyNjM0",
            parse_mode="Markdown"
        )

        users.pop(uid, None)
        return
