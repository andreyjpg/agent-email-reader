import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from readers.gmail_reader import gmail_check

async def email_check():
    new_emails = await gmail_check
    if new_emails.
    

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(email_check, 'interval', seconds=5)
    scheduler.start()

    await asyncio.Event().wait()

asyncio.run(main())