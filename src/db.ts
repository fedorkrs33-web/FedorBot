import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import { messages } from "./schema";

// Создаем подключение к SQLite
const sqlite = new Database("./telegram-bot.db");

// Включаем поддержку foreign keys
sqlite.pragma("foreign_keys = ON");

// Создаем таблицу messages, если она не существует
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    chat_id TEXT NOT NULL,
    username TEXT,
    first_name TEXT,
    content TEXT NOT NULL,
    from_bot BOOLEAN DEFAULT false NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Экспортируем экземпляр Drizzle ORM
export const db = drizzle(sqlite, { schema: { messages } });

// Экспортируем саму базу данных для прямого доступа при необходимости
export default sqlite;