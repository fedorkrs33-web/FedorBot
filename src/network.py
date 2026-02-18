# network.py - Адаптирован для интеграции с PolzaAI и БД
import aiohttp
import os
import asyncio
from typing import Dict, Any, Optional, Tuple
import base64
import uuid
import logging
from src.config import Config

logger = logging.getLogger(__name__)

class NetworkError(Exception):
    """Общее исключение для сетевых ошибок"""
    pass



class Network:
    @staticmethod
    async def send_prompt_to_model(model_data: dict, prompt: str) -> str:
        """
        Отправляет промт в указанную модель и возвращает ответ или сообщение об ошибке.

        :param model_data: словарь с данными модели из БД
        :param prompt: текст промта
        :return: строка — ответ или ошибка
        """
        logger.info(f"📤 Отправляю промт в {model_data['name']} (provider: {model_data['provider']})...")

        try:
            
            if model_data["provider"].lower() == "gigachat":
                return await Network._send_to_gigachat(prompt)
            elif model_data["provider"].lower() == "yandex":
                return await Network._send_to_yandex(prompt)
            else:
                # OpenAI-совместимые API
                return await Network._send_openai_compatible(model_data, prompt)

        except Exception as e:
            error_msg = f"❌ Критическая ошибка: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @staticmethod
    async def _send_openai_compatible(model: dict, prompt: str) -> str:
        """Отправка в OpenAI-совместимые API"""
        try:
            # Получаем API-ключ
            api_key = os.getenv(model["api_key_var"])
            if not api_key:
                error_msg = f"🔑 Ключ не найден: {model["api_key_var"]}"
                logger.warning(error_msg)
                return error_msg

            # Имя модели из БД
            model_name = (model["model_name"] or "").strip()
            if not model_name:
                error_msg = "⚠️ Не указано имя модели в БД"
                logger.warning(error_msg)
                return error_msg

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024,
            }

            logger.debug(f"POST {model["api_url"]}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    model["api_url"],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False
                ) as response:
                    logger.debug(f"Status: {response.status}")
                    
                    if response.status == 402:
                        return (
                            "❌ Модель недоступна.<br>"
                            "• Проверьте <a href='https://polza.ai'>баланс на polza.ai</a><br>"
                            "• Или выберите другую модель"
                        )
                    
                    text = await response.text()
                    logger.debug(f"Raw response: {repr(text)}")

                    if response.status in (200, 201):
                        try:
                            data = await response.json()
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if content:
                                logger.info("✅ Ответ получен")
                                return content.strip()
                            return "⚠️ Ответ получен, но пустой"
                        except Exception as e:
                            return f"⚠️ Ошибка парсинга: {e}"
                    else:
                        try:
                            error_detail = (await response.json()).get("error", {}).get("message", text)
                        except:
                            error_detail = text
                        error_msg = f"❌ {response.status}: {error_detail}"
                        logger.error(error_msg)
                        return error_msg

        except asyncio.TimeoutError:
            error_msg = "❌ Ошибка: Таймаут запроса (30 сек)"
            logger.error(error_msg)
            return error_msg
        except aiohttp.ClientError as e:
            error_msg = f"❌ Ошибка подключения: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ Неизвестная ошибка: {str(e)}"
            logger.error(error_msg)
            return error_msg


    @staticmethod
    async def _send_to_gigachat(prompt: str) -> str:
        """Отправка запроса в GigaChat (через Сбер)"""
        try:
            client_id = os.getenv("GIGACHAT_CLIENT_ID")
            client_secret = os.getenv("GIGACHAT_CLIENT_SECRET")
            if not client_id or not client_secret:
                return "❌ Не заданы GIGACHAT_CLIENT_ID или GIGACHAT_CLIENT_SECRET"

            # 1. Получаем access_token
            auth_str = f"{client_id}:{client_secret}"
            encoded = base64.b64encode(auth_str.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {encoded}"
            }
            
            data = {"scope": "GIGACHAT_API_PERS"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                    headers=headers,
                    data=data,
                    ssl=False
                ) as token_response:
                    if token_response.status != 200:
                        error = await token_response.text()
                        logger.error(f"Ошибка токена: {error}")
                        return f"❌ Ошибка авторизации: {error}"

                    token_data = await token_response.json()
                    access_token = token_data.get("access_token")
                    if not access_token:
                        msg = "Не получен access_token"
                        logger.error(msg)
                        return f"❌ {msg}"

                # 2. Отправляем промт
                chat_headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
                
                chat_payload = {
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
                
                async with session.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers=chat_headers,
                    json=chat_payload,
                    ssl=False
                ) as chat_response:
                    if chat_response.status == 200:
                        content = (await chat_response.json()).get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content:
                            logger.info("✅ Ответ от GigaChat получен")
                            return content.strip()
                        return "⚠️ Ответ от GigaChat пуст"
                    else:
                        error = await chat_response.text()
                        logger.error(f"Ошибка GigaChat: {error}")
                        return f"❌ Ошибка GigaChat: {error}"

        except Exception as e:
            error_msg = f"❌ GigaChat: {str(e)}"
            logger.error(error_msg)
            return error_msg
        
    @staticmethod
    async def _send_to_yandex(prompt: str) -> str:
        """Отправка в Yandex GPT через aiohttp (асинхронно) с использованием IAM-токена"""
        try:
            # Получаем креды через вашу функцию
            iam_token, folder_id = Config.get_yandex_credentials()

            if not iam_token or not folder_id:
                error_msg = "❌ Не удалось получить IAM-токен или Folder ID"
                logger.error(error_msg)
                return error_msg

            # Формируем тело запроса
            payload = {
                "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
                "completionOptions": {
                    "temperature": 0.7,
                    "maxTokens": "1024"
                },
                "messages": [
                    {"role": "user", "text": prompt}
                ]
            }

            headers = {
                "Authorization": f"Bearer {iam_token}",
                "Content-Type": "application/json"
            }

            logger.info(f"🌐 Отправляю запрос в Yandex GPT (folder: {folder_id})")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    logger.debug(f"📨 Status: {response.status}")

                    if response.status == 200:
                        try:
                            data = await response.json()
                            text = data["result"]["alternatives"][0]["message"]["text"]
                            logger.info("✅ Ответ от Yandex GPT получен")
                            return text.strip()
                        except (KeyError, IndexError, TypeError) as e:
                            error_msg = "⚠️ Ответ получен, но не удалось извлечь текст"
                            logger.warning(f"{error_msg}: {e}")
                            return error_msg
                    else:
                        try:
                            error_data = await response.json()
                            error_detail = error_data.get("error", {}).get("message", await response.text())
                        except Exception:
                            error_detail = await response.text()
                        error_msg = f"❌ {response.status}: {error_detail}"
                        logger.error(error_msg)
                        return error_msg

        except asyncio.TimeoutError:
            error_msg = "❌ Ошибка: Таймаут запроса к Yandex GPT (30 сек)"
            logger.error(error_msg)
            return error_msg
        except aiohttp.ClientError as e:
            error_msg = f"❌ Ошибка подключения к Yandex GPT: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ Неизвестная ошибка при запросе к Yandex GPT: {str(e)}"
            logger.exception(error_msg)
            return error_msg
