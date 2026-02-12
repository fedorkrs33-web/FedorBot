import { Bot } from "grammy";
import { db } from "./db";
import { messages, messageInsertSchema } from "./schema";
import { eq } from "drizzle-orm";

// Получаем токен из переменных окружения
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

if (!BOT_TOKEN) {
  console.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения");
  process.exit(1);
}

// Создаем экземпляр бота
const bot = new Bot(BOT_TOKEN);

// Обработка команды /start
bot.command("start", (ctx) => {
  ctx.reply("Привет! Я новый Telegram-бот на grammy и Drizzle ORM");
});

// Обработка текстовых сообщений
bot.on("message:text", async (ctx) => {
  const message = ctx.message;
  const from = message.from;

  try {
    // Валидируем данные перед сохранением
    const validatedData = messageInsertSchema.parse({
      messageId: message.message_id,
      chatId: message.chat.id.toString(),
      username: from.username ?? null,
      firstName: from.first_name ?? null,
      content: message.text,
      fromBot: false,
    });

    // Сохраняем сообщение в базу данных
    await db.insert(messages).values(validatedData);
    
    console.log(`Сообщение от ${from.first_name} сохранено в базу данных`);
    
  } catch (error) {
    console.error("Ошибка при сохранении сообщения:", error);
    // Не останавливаем бота при ошибке сохранения
  }

  // Отвечаем на сообщение
  await ctx.reply(`Получено ваше сообщение: "${message.text}"");
});

// Обработка ошибок бота
bot.catch((err) => {
  console.error(`Ошибка бота:`, err.ctx.update, '\n', err.error);
});

// Функция для отправки сообщения
export async function sendMessage(chatId: string, text: string): Promise<boolean> {
  try {
    await bot.api.sendMessage(chatId, text);
    
    // Сохраняем исходящее сообщение
    await db.insert(messages).values({
      messageId: 0, // Временное значение, Telegram API не возвращает ID отправленных сообщений напрямую
      chatId: chatId,
      content: text,
      fromBot: true,
    });
    
    return true;
  } catch (error) {
    console.error("Ошибка при отправке сообщения:", error);
    return false;
  }
}

// Экспортируем бота для использования в других модулях
export default bot;