import random

def respond_to_message(message):
    greetings = [
        "Привет!",
        "Здравствуйте!",
        "Доброго времени суток"
    ]
    return random.choice(greetings)

# Тестирование
if __name__ == "__main__":
    print(respond_to_message("ау!?"))