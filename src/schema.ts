import { sqliteTable, text, integer, boolean, timestamp } from "drizzle-orm/sqlite-core";
import { z } from "zod";

export const messages = sqliteTable("messages", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  messageId: integer("message_id"),
  chatId: text("chat_id").notNull(),
  username: text("username"),
  firstName: text("first_name"),
  content: text("content").notNull(),
  fromBot: boolean("from_bot").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const messageInsertSchema = z.object({
  messageId: z.number(),
  chatId: z.string(),
  username: z.string().nullable(),
  firstName: z.string().nullable(),
  content: z.string(),
  fromBot: z.boolean(),
});