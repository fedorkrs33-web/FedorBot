import { drizzle } from "drizzle-orm/sqlite3";
   import Database from "sqlite3";
   import { messages } from "./schema";

   // Создаем подключение к SQLite
   const sqlite = new Database.Database("./telegram-bot.db");

   // Экспортируем экземпляр Drizzle ORM
   export const db = drizzle(sqlite, { schema: { messages } });

   // Экспортируем саму базу данных
   export default sqlite;

