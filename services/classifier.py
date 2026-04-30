import logging
from google import genai
import asyncio
from config import Config 

class Classifier():
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model = Config.GEMINI_MODEL

    def prompt_creation(self, sender: str, subject: str, fragment: str):
        return f"""
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

            Correo a clasificar / Email to classify:
            Remitente / Sender: {sender}
            Asunto / Subject: {subject}
            Fragmento / Snippet: {fragment}

            Responde ÚNICAMENTE con / Respond ONLY with: IMPORTANT or IGNORE
        """

    async def llm_chat_creation(self, message): 
        try:
            sender = message["sender"]
            subject = message["subject"]
            fragment = message["fragment"]
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=self.prompt_creation(
                        sender=sender,
                        subject=subject,
                        fragment=fragment
                    )
                )
            )
            result = response.text.strip()

            logging.info(f"Classification result: {result} | Subject: {subject}")
            return result
        except Exception as e:
            logging.error(f"Unexpected error in Classifier: {e}")
            return "IGNORE"

