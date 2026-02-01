from aiogram.filters import CommandObject, CommandStart
from loguru import logger
from aiogram.types import Message
from aiogram.dispatcher.router import Router

from app.database import connection
from app.users.dao import UserDAO
from app.users.schemas import TelegramIDModel, UserModel
from app.users.utils import get_refer_id_or_none

user_router = Router()


@user_router.message(CommandStart())
@connection()
async def cmd_start(message: Message, command: CommandObject, session, **kwargs):
    try:
        user_id = message.from_user.id
        user_info = await UserDAO.find_one_or_none(session=session,
                                                   filters=TelegramIDModel(telegram_id=user_id))

        if user_info:
            await message.answer(f"👋 Привет, {message.from_user.full_name}! Выберите необходимое действие")
            return

        # Определение реферального ID
        ref_id = get_refer_id_or_none(command_args=command.args, user_id=user_id)
        values = UserModel(telegram_id=user_id,
                           username=message.from_user.username,
                           first_name=message.from_user.first_name,
                           last_name=message.from_user.last_name,
                           referral_id=ref_id)
        await UserDAO.add(session=session, values=values)
        # Формирование сообщения
        ref_message = f" Вы успешно закреплены за пользователем с ID {ref_id}" if ref_id else ""
        msg = f"🎉 <b>Благодарим за регистрацию!{ref_message}</b>."

        await message.answer(msg)

    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /start для пользователя {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже.")
