import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError

from telethon.tl.types import Channel, Chat, ChatForbidden

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich import box

console = Console()

LANGS = {
    "en": {
        "banner": "🔹 Telegram Leaver Tool 🔹\nDeveloped by Yassin | Instagram: @yassindeveloper",
        "auth": "Authentication",
        "api_id": "Enter your API ID",
        "api_hash": "Enter your API HASH",
        "phone": "Enter your phone number (e.g., +123456789)",
        "code": "Enter the login code you received",
        "password": "Two-step verification is enabled. Enter your password",
        "fetching": "Fetching your joined chats...",
        "no_chats": "❌ No groups or channels found.",
        "leave_all": "Do you want to leave all chats?",
        "leave_selected": "Enter chat numbers to leave (e.g., 1,3,5)",
        "leaving": "Leaving chats...",
        "left": "✅ Left: ",
        "fail": "⚠️ Failed: ",
        "summary": "Summary",
        "left_count": "✅ Successfully Left",
        "failed_count": "❌ Failed",
        "thank_you": "Thanks for using Telegram Leaver Tool 🚀",
        "cancel": "❗ Operation cancelled by user.",
    },
    "ar": {
        "banner": "🔹 أداة مغادرة قنوات التليجرام 🔹\nبرمجة ياسين | Instagram: @yassindeveloper",
        "auth": "المصادقة",
        "api_id": "أدخل API ID الخاص بك",
        "api_hash": "أدخل API HASH الخاص بك",
        "phone": "أدخل رقم هاتفك (مثال: +964...)",
        "code": "أدخل رمز الدخول الذي وصلك",
        "password": "تم تفعيل التحقق بخطوتين، أدخل كلمة السر",
        "fetching": "جاري جلب المحادثات التي انضممت لها...",
        "no_chats": "❌ لا توجد مجموعات أو قنوات.",
        "leave_all": "هل ترغب بمغادرة جميع المحادثات؟",
        "leave_selected": "أدخل أرقام المحادثات للمغادرة (مثال: 1,3,5)",
        "leaving": "جاري المغادرة...",
        "left": "✅ تم المغادرة: ",
        "fail": "⚠️ فشل: ",
        "summary": "الملخص",
        "left_count": "✅ تم مغادرة",
        "failed_count": "❌ فشل في",
        "thank_you": "شكراً لاستخدامك أداة مغادرة التليجرام 🚀",
        "cancel": "❗ تم إلغاء العملية من قبل المستخدم.",
    }
}


async def main():
    console.print(Rule("[bold green]🌐 Select Language / اختر اللغة[/]"))
    lang_choice = Prompt.ask("Enter [bold cyan]'en'[/] or [bold magenta]'ar'[/]", default="en")
    L = LANGS.get(lang_choice.lower(), LANGS["en"])

    console.print(Panel.fit(L["banner"], title="Yassin CLI", style="bold cyan"))
    console.print(Rule(f"[bold yellow]{L['auth']}[/]"))

    api_id = None
    api_hash = None
    phone = None

    if not os.path.exists("session.session"):
        api_id = Prompt.ask(f"[bold yellow]{L['api_id']}[/]")
        api_hash = Prompt.ask(f"[bold yellow]{L['api_hash']}[/]")
        phone = Prompt.ask(f"[bold yellow]{L['phone']}[/]")

    client = await connect_client(L, api_id, api_hash, phone)
    if not client:
        return

    chats, index_map = await fetch_chats(client, L)

    if not chats:
        console.print(f"[red]{L['no_chats']}[/]")
        await client.disconnect()
        return

    display_chats(chats)

    console.print(Rule("[bold green]Selection / التحديد[/]"))

    if Confirm.ask(f"[bold yellow]{L['leave_all']}[/]"):
        selected = list(index_map.values())
    else:
        selection = Prompt.ask(f"[bold yellow]{L['leave_selected']}[/]")
        nums = [x.strip() for x in selection.split(',')]
        selected = [index_map[n] for n in nums if n in index_map]

    left, failed = await leave_selected_chats(client, selected, L)

    console.print(Rule(f"[bold blue]{L['summary']}[/]"))
    console.print(f"{L['left_count']}: [green]{left}[/] | {L['failed_count']}: [red]{failed}[/]")

    console.print(Panel.fit(L["thank_you"], subtitle="Yassin | @yassindeveloper", style="bold blue"))

    await client.disconnect()


async def connect_client(L, api_id=None, api_hash=None, phone=None):
    if os.path.exists("session.session"):
        client = TelegramClient("session", api_id=0, api_hash="")
        await client.connect()
        if await client.is_user_authorized():
            return client
        else:
            os.remove("session.session")

    client = TelegramClient("session", api_id, api_hash)
    await client.connect()

    try:
        await client.send_code_request(phone)
        code = Prompt.ask(f"[cyan]{L['code']}[/]")
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = Prompt.ask(f"[magenta]{L['password']}[/]", password=True)
            await client.sign_in(password=password)
        return client
    except Exception as e:
        console.print(f"[red]Login failed: {e}[/]")
        return None


async def fetch_chats(client, L):
    chats = []
    index_map = {}

    with console.status(f"[bold cyan]{L['fetching']}[/]", spinner="dots"):
        dialogs = await client.get_dialogs()
        for i, dialog in enumerate(dialogs):
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)) and not isinstance(entity, ChatForbidden):
                if isinstance(entity, Channel):
                    chat_type = "Channel" if entity.broadcast else "Group"
                elif isinstance(entity, Chat):
                    chat_type = "Group"
                else:
                    continue

                chats.append((i + 1, entity.id, entity.title, chat_type))
                index_map[str(i + 1)] = entity

    return chats, index_map


def display_chats(chats):
    table = Table(title="Chats", box=box.ROUNDED, border_style="bright_blue")
    table.add_column("No.", style="bold green", width=6, justify="center")
    table.add_column("Name", style="cyan", overflow="fold")
    table.add_column("Type", style="magenta", justify="center", width=10)
    for i, _, name, chat_type in chats:
        table.add_row(str(i), name, chat_type)
    console.print(table)


async def leave_selected_chats(client, selected, L):
    left_count = 0
    failed_count = 0
    total = len(selected)

    with Progress(
        SpinnerColumn(style="bold green"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]{L['leaving']}[/]", total=total)
        for chat in selected:
            try:
                await client(LeaveChannelRequest(chat))
                console.print(f"{L['left']}[green]{chat.title}[/]")
                left_count += 1
            except FloodWaitError as e:
                console.print(f"[yellow]FloodWait: waiting {e.seconds} seconds...[/]")
                await asyncio.sleep(e.seconds)
                await client(LeaveChannelRequest(chat))
                console.print(f"{L['left']}[green]{chat.title}[/]")
                left_count += 1
            except Exception as e:
                console.print(f"{L['fail']}[red]{chat.title}[/] - {e}")
                failed_count += 1
            progress.advance(task)

    return left_count, failed_count


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(f"\n[red]{LANGS['en']['cancel']}[/]")
