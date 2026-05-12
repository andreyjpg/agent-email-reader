import logging
import asyncio
import re
from google import genai
from google.genai import types
from config import config


class Classifier():
    def __init__(self):
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.model = config.gemini_model
        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        return """
            Eres un clasificador de correos electrónicos / You are an email classifier.

            La empresa se dedica a ventas de equipos para datacenters y oficinas, especializada en
            baterías, UPS y sistemas de abastecimiento de energía /
            The company sells datacenter and office equipment, specialized in batteries, UPS systems
            and power supply solutions.

            Tu única tarea es analizar el asunto y remitente de un correo y responder ÚNICAMENTE con
            una de estas dos palabras / Your only task is to analyze the subject and sender of an email
            and respond ONLY with one of these two words:

            IMPORTANT o/or IGNORE

            CLASIFICAR COMO IMPORTANT / CLASSIFY AS IMPORTANT:
            - Solicitudes de cotización / Quote or pricing requests for any equipment
            - Preguntas sobre disponibilidad, precios o especificaciones técnicas /
            Questions about availability, prices or technical specifications
            - Correos de clientes actuales o potenciales con consultas directas /
            Emails from current or potential clients with direct inquiries
            - Seguimientos de pedidos, órdenes de compra o facturas /
            Order follow-ups, purchase orders or invoices
            - Alertas urgentes de proveedores sobre entregas, stock o precios /
            Urgent supplier alerts about deliveries, stock or price changes
            - Cualquier correo de una persona real que requiera respuesta directa /
            Any email from a real person that requires a direct response
            - Palabras clave en español / Spanish keywords: cotización, cotizar, precio, presupuesto,
            disponibilidad, pedido, orden de compra, factura, urgente, batería, datacenter, inversor
            - Palabras clave en inglés / English keywords: quote, quotation, pricing, budget,
            availability, purchase order, invoice, urgent, battery, UPS, datacenter, power supply,
            inverter, stock, delivery, lead time

            CLASIFICAR COMO IGNORE / CLASSIFY AS IGNORE:
            - Newsletters, boletines o resúmenes informativos / Newsletters or informational digests
            - Publicidad o promociones / Advertising or promotions of any kind
            - Notificaciones automáticas de plataformas / Automated platform notifications
            - Redes sociales o notificaciones de apps / Social media or app notifications
            - Correos masivos / Bulk emails sent to multiple recipients
            - Noticias del sector sin solicitud previa / Industry news or product updates not requested
            - Resúmenes semanales o mensuales / Weekly or monthly summaries of any service

            EN CASO DE DUDA, clasifica como IMPORTANT / WHEN IN DOUBT, classify as IMPORTANT.
            It is better to review one extra email than to miss a sales opportunity.

            El correo puede estar escrito en español, inglés o ambos. Detecta el idioma automáticamente.
            The email can be written in Spanish, English or both. Detect the language automatically.
        """

    def _build_user_message(self, sender: str, subject: str, fragment: str, keywords: list[str]) -> str:
        keywords_section = ""
        if keywords:
            keywords_section = (
                f"Palabras clave adicionales del cliente / Additional client keywords "
                f"(clasificar como IMPORTANT si aparecen / classify as IMPORTANT if present): "
                f"{', '.join(keywords)}\n\n"
            )
        return (
            f"{keywords_section}"
            f"Correo a clasificar / Email to classify:\n"
            f"Remitente / Sender: {sender}\n"
            f"Asunto / Subject: {subject}\n"
            f"Fragmento / Snippet: {fragment}\n\n"
            f"Responde ÚNICAMENTE con / Respond ONLY with: IMPORTANT or IGNORE"
        )

    def _parse_retry_delay(self, error_str: str) -> int:
        match = re.search(r'retry[^0-9]*(\d+)', error_str, re.IGNORECASE)
        return int(match.group(1)) + 5 if match else 60

    async def _classify(self, message: dict, keywords: list[str]) -> str:
        user_message = self._build_user_message(
            sender=message["sender"],
            subject=message["subject"],
            fragment=message["fragment"],
            keywords=keywords,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                ),
            )
        )
        result = response.text.strip()
        logging.info(f"Classification result: {result} | Subject: {message['subject']}")
        return result

    async def llm_chat_creation(self, message: dict, keywords: list[str] = []) -> str:
        try:
            return await self._classify(message, keywords)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = self._parse_retry_delay(err_str)
                logging.warning(f"Gemini rate limit hit, retrying in {wait}s...")
                await asyncio.sleep(wait)
                try:
                    return await self._classify(message, keywords)
                except Exception as retry_err:
                    logging.error(f"Classifier retry failed: {retry_err}")
                    return "IGNORE"
            logging.error(f"Unexpected error in Classifier: {e}")
            return "IGNORE"
