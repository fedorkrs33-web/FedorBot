from aiogram.fsm.state import State, StatesGroup

class ProverbStates(StatesGroup):
    waiting_for_text = State()
    editing_proverb = State()