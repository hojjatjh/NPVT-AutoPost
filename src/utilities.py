from src.config import OWNERS

def is_owner(user_id: int) -> bool:
    return user_id in OWNERS

async def safe_answer_callback(event, text: str, alert: bool = False):
    try:
        await event.answer(text, alert=alert)
    except:
        try:
            await event.edit(text)
        except:
            pass

def show_logo():
    print("""
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⠀⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡟⢹⡇⠀⠀⠀⠀⠀⠀⠀
    ⠀⠀⢴⠒⠲⢦⣄⠠⢰⡏⠀⢸⡇⣀⣤⡴⢶⣶⠀⠀
    ⠀⠀⠈⢧⡀⠀⠈⠫⣿⠀⠀⣼⠟⠉⢀⣠⠞⠁⠀⠀
    ⠀⠀⠀⠈⣳⣤⣀⠀⢹⣄⣼⠥⣶⣒⠛⠻⣶⣤⡀⠀
    ⠀⢀⣴⠞⠉⢀⣠⢽⣟⣋⡤⠼⠁⠉⢳⠎⣹⣈⠹⣦
    ⣠⣟⣁⣠⡶⠋⣵⠋⠀⠈⠃⢀⣤⡀⠠⠊⠀⣼⡻⣿
    ⠉⠉⠿⣿⠻⡟⠉⠐⠂⢰⡞⢺⡇⣷⠐⠀⠁⢀⡇⣿
    ⠀⠀⠐⣿⠀⠳⡶⠒⡁⠀⡙⠺⣄⡟⠈⠁⣀⣹⢆⡟
    ⠀⠀⠀⠘⢷⣰⡗⠚⣇⡴⡇⢰⠀⠁⠐⠄⠹⡾⢿⡇
    ⠀⠀⠀⠀⠀⠙⠷⣦⣀⣶⣷⣸⡆⢀⣧⠀⣠⢇⣿⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠶⣤⣙⠛⣾⠳⣣⡾⠃⠀
    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠛⠛⠉⠀⠀⠀
    Strawberries NPVT (1.0.0)
    """)