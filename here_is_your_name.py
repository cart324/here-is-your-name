import discord
from discord.ext import commands
import os
import sys
import shutil
import stat
import traceback

client = discord.Bot(intents=discord.Intents.all())

client.load_extension("cogs.somethings")


def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


paths_list = [["here-is-your-name/cogs", "cogs"]]  # [옮길 파일 위치, 옮겨질 위치]


@client.command()
async def restart(ctx):
    try:
        await ctx.respond('봇이 재시작됩니다.')
        if os.path.exists("here-is-your-name"):
            shutil.rmtree("here-is-your-name", onerror=on_rm_error)
        os.system("git clone https://github.com/cart324/here-is-your-name")
        for paths in paths_list:
            for (path, dirs, files) in os.walk(paths[0]):
                for file_name in files:
                    if os.path.exists(paths[1] + "/" + file_name):
                        os.remove(paths[1] + "/" + file_name)
                    shutil.move(paths[0] + "/" + file_name, paths[1] + "/" + file_name)
        shutil.rmtree("here-is-your-name", onerror=on_rm_error)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception:
        error_log = traceback.format_exc(limit=None, chain=True)
        cart = client.get_user(344384179552780289)
        await cart.send("```" + "\n" "사용자 = " + ctx.author.name + "\n" + str(error_log) + "```")


with open('token.txt', 'r') as f:
    token = f.read()

client.run(token)
