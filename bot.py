from aiogram import Bot,Dispatcher,F
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton,WebAppInfo,LabeledPrice,PreCheckoutQuery
from aiogram.filters import CommandStart
TOKEN="8308059482:AAF6vQVcBOuKPYCGx27cXvjCDq-USSYz36o"
WEB_APP_URL="https://example.com/index.html"
OPENROUTER_API_KEY="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"
ADMIN_ID=123456789
subs=set()
bot=Bot(TOKEN);dp=Dispatcher()
def get_game_kb(key):return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 Играть",web_app=WebAppInfo(url=f"{WEB_APP_URL}?api={key}"))]])
@dp.message(CommandStart())
async def s(m:Message):
    if m.from_user.id in subs or m.from_user.id==ADMIN_ID: await m.answer("Доступ",reply_markup=get_game_kb(OPENROUTER_API_KEY))
    else: await bot.send_invoice(m.chat.id,title="Подписка",description="Доступ",payload="sub",currency="XTR",prices=[LabeledPrice(label="Sub",amount=100)])
@dp.pre_checkout_query()
async def pc(q:PreCheckoutQuery): await q.answer(ok=True)
@dp.message(F.successful_payment)
async def paid(m:Message): subs.add(m.from_user.id); await m.answer("Оплата получена",reply_markup=get_game_kb(OPENROUTER_API_KEY))
