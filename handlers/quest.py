from telegram import Update
from telegram.ext import ContextTypes

from config.settings import QUEST_DATA
from utils.data_utils import get_user, load_user_data, save_user_data

async def quest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀘스트 시작 및 현재 상태 확인"""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    quest_state = user['quest_state']

    if quest_state['current_quest'] is None:
        quest_id = 'q1'
        users = load_user_data()
        users[str(chat_id)]['quest_state'] = {'current_quest': quest_id, 'stage': 1}
        save_user_data(users)
        
        quest = QUEST_DATA[quest_id]
        stage_data = quest['stages'][1]
        
        await update.message.reply_text(
            f"**📜 새로운 퀘스트: {quest['title']}**\n\n"
            f"{stage_data['description']}\n\n"
            f"**상황:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 행동:**\n{stage_data['action_prompt']}\n"
            f"명령어 `/action [할 말]`을 사용해 대답해주세요."
        )
    else:
        quest_id = quest_state['current_quest']
        stage = quest_state['stage']
        quest = QUEST_DATA[quest_id]
        
        if stage > len(quest['stages']):
            await update.message.reply_text("이미 모든 퀘스트를 완료하셨습니다! 다음 업데이트를 기대해주세요.")
            return

        stage_data = quest['stages'][stage]
        await update.message.reply_text(
            f"**📜 퀘스트 진행 중: {quest['title']} (단계: {stage})**\n\n"
            f"{stage_data['description']}\n\n"
            f"**상황:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 행동:**\n{stage_data['action_prompt']}\n"
            f"명령어 `/action [할 말]`을 사용해 대답해주세요."
        )

async def action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀘스트에서 액션 수행"""
    chat_id = update.effective_chat.id
    user_text = " ".join(context.args)
    
    if not user_text:
        await update.message.reply_text("실행할 행동을 입력해주세요. 예: `/action 안녕하세요`")
        return

    users = load_user_data()
    user = users[str(chat_id)]
    quest_state = user['quest_state']

    if quest_state['current_quest'] is None:
        await update.message.reply_text("진행 중인 퀘스트가 없습니다. `/quest`로 새 퀘스트를 시작하세요.")
        return

    quest_id = quest_state['current_quest']
    stage = quest_state['stage']
    quest = QUEST_DATA[quest_id]
    stage_data = quest['stages'][stage]

    if any(keyword in user_text.lower() for keyword in stage_data['keywords']):
        next_stage = stage + 1
        if next_stage > len(quest['stages']):
            user['quest_state'] = {'current_quest': None, 'stage': 0}
            user['stats']['quests_completed'] += 1
            save_user_data(users)
            await update.message.reply_text(f"🎉 **퀘스트 완료: {quest['title']}** 🎉\n\n축하합니다! 실전 러시아어 경험치가 1 상승했습니다. `/quest`로 다음 퀘스트에 도전하세요!")
        else:
            user['quest_state']['stage'] = next_stage
            save_user_data(users)
            
            next_stage_data = quest['stages'][next_stage]
            await update.message.reply_text(
                f"**✅ 단계 성공!**\n\n"
                f"**📜 다음 단계: {quest['title']} (단계: {next_stage})**\n\n"
                f"{next_stage_data['description']}\n\n"
                f"**상황:**\n`{next_stage_data['bot_message']}`\n\n"
                f"➡️ **당신의 행동:**\n{next_stage_data['action_prompt']}"
            )
    else:
        await update.message.reply_text(f"음... 조금 다른 표현이 필요할 것 같아요. 다시 시도해볼까요?\n\n**힌트:** {stage_data['action_prompt']}") 