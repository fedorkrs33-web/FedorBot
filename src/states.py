from aiogram.fsm.state import State, StatesGroup

class ProverbStates(StatesGroup):
    waiting_for_text = State()
    editing_proverb = State()

class PromptStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_new_prompt = State()          # Для добавления промта