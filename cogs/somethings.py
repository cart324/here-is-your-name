import discord
from discord.ext import commands
import random
import math


class Somethings(discord.Cog):
    def __init__(self, client):
        self.client = client

    @discord.slash_command()
    async def dice(self, chat):
        dice_number = ['1', '2', '3', '4', '5', '6']
        await chat.respond(random.choice(dice_number))

    @discord.slash_command()
    async def number(self, chat, *, digits=int()):
        if digits > 2000:
            await chat.send('자리수는 2000보다 클 수 없습니다.')
            return
        your_number = ""
        while digits >= 1:
            digits -= 1
            number = random.choice(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'])
            your_number = your_number + number
        await chat.respond(your_number)

    @discord.slash_command()
    async def name(self, chat):
        amount = 20
        your_name = ""
        while amount >= 1:
            amount -= 1
            count = random.randrange(4, 13)
            name = ""
            while count >= 1:
                count -= 1
                plus = random.choice(
                    ["e", "e", "e", "e", "e", "e", "e", "e", "e", "e", "a", "a", "a", "a", "a", "a", "a", "a", "t", "t",
                     "t", "t", "t", "t", "t", "t", "l", "l", "l", "l", "l", "l", "l", "o", "o", "o", "o", "o", "o", "o",
                     "s", "s", "s", "s", "s", "s", "s", "n", "n", "n", "n", "n", "n", "r", "r", "r", "r", "r", "r", "c",
                     "c", "c", "c", "d", "d", "d", "d", "h", "h", "h", "h", "i", "i", "i", "i", "m", "m", "m", "m", "u",
                     "u", "u", "u", "b", "b", "f", "f", "g", "g", "p", "p", "w", "w", "y", "y", "k", "v", "j", "x", "q",
                     "z"])
                name = name + plus
            your_name = your_name + "\n" + name
        await chat.respond(your_name)

    # [속도 보정값, 가속도 보정값, 지구력 보정값]
    strategy_dic = {"도주": [[1, 0.98, 0.962], [1, 1, 0.996], 0.95],
                    "선행": [[0.978, 0.991, 0.975], [0.985, 1, 0.996], 0.89],
                    "선입": [[0.938, 0.998, 0.994], [0.938, 1, 1], 1],
                    "추입": [[0.935, 1, 1], [0.931, 1, 0.997], 0.995]}

    track_aptitude_dic = {"S": 1.05, "A": 1, "B": 0.9, "C": 0.8, "D": 0.7, "E": 0.5, "F": 0.3, "G": 0.1}
    distance_aptitude_dic = {"S": 1.05, "A": 1, "B": 0.9, "C": 0.8, "D": 0.6, "E": 0.4, "F": 0.2, "G": 0.1}
    strategy_aptitude_dic = {"S": 1.1, "A": 1, "B": 0.85, "C": 0.75, "D": 0.6, "E": 0.4, "F": 0.2, "G": 0.1}

    condition_dic = {"최상": 1.1, "양호": 1.05, "보통": 1, "저조": 0.95, "최악": 0.9}

    def dist_accel(self, aptitude):
        if aptitude == "E":
            return 0.6
        elif aptitude == "F":
            return 0.5
        elif aptitude == "G":
            return 0.4
        else:
            return 1

    @discord.slash_command(description="엑셀계산기 이식", guild_ids=[907936221446148138, 792068683580440587])
    async def stat(self, chat,
                   strategy: discord.Option(str, "각질을 선택하세요.", choices=["도주", "선행", "선입", "추입"]),
                   race_distance: discord.Option(int, "경주거리를 입력하세요."),
                   speed: discord.Option(int, "스피드 스탯을 입력하세요."),
                   power: discord.Option(int, "파워 스탯을 입력하세요."),
                   stamina: discord.Option(int, "스태미나 스탯을 입력하세요."),
                   grit: discord.Option(int, "근성 스탯을 입력하세요."),
                   intelligence: discord.Option(int, "지능 스탯을 입력하세요."),
                   track_aptitude: discord.Option(str, "마장 적성을 선택하세요.", choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   distance_aptitude: discord.Option(str, "거리 적성을 선택하세요.", choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   strategy_aptitude: discord.Option(str, "각질 적성을 선택하세요.", choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   condition: discord.Option(str, "컨디션을 선택하세요.", choices=["최상", "양호", "보통", "저조", "최악"]),
                   healing: discord.Option(float, "회복량을 입력하세요.(%)")):

        strategy_list = self.strategy_dic.get(strategy)
        stats = [speed, power, stamina, grit, intelligence]
        acceleration_multiplier = self.track_aptitude_dic.get(track_aptitude) * self.dist_accel(distance_aptitude)
        speed_multiplier = self.distance_aptitude_dic.get(distance_aptitude)
        intelligence_multiplier = self.strategy_aptitude_dic.get(strategy_aptitude)
        condition_multiplier = self.condition_dic.get(condition)

        stats = [int(x * condition_multiplier) for x in stats]
        stats[4] = int(stats[4] * intelligence_multiplier)
        standard_speed = 22 - race_distance / 1000

        speeds = [round(standard_speed * strategy_list[0][0], 2),
                  round(standard_speed * strategy_list[0][1], 2),
                  round(standard_speed * (strategy_list[0][2] + 0.01) * 1.05 + math.sqrt(500 * stats[0]) * speed_multiplier * 0.002 * 2.05, 2)]
        basic_acceleration = 0.0006 * math.sqrt(500 * stats[1] * acceleration_multiplier)
        accels = [round(basic_acceleration * strategy_list[1][0], 4),
                  round(basic_acceleration * strategy_list[1][1], 4),
                  round(basic_acceleration * strategy_list[1][2], 4)]
        basic_hp = race_distance + stats[2] * strategy_list[2] * 0.8
        hp = round(basic_hp * (1 + healing * 0.01), 1)
        if 100 - 9000 / stats[4] < 20:
            skill_activation = 20
        else:
            skill_activation = round(100 - 9000 / stats[4], 2)
        excitement_percentage = round((6.5 / math.log10(stats[4] * 0.1 + 1)) ** 2, 2)

        embed = discord.Embed(title="status", color=0xffffff)
        embed.add_field(name='우마무스메 정보', value=f"경주 거리 : {race_distance} | 각질 : {strategy} | 스탯 : {stats} | "
                                               f"적성 : {track_aptitude}, {distance_aptitude}, {strategy_aptitude} | "
                                               f"컨디션 : {condition} | 회복량 : {healing}%", inline=False)
        embed.add_field(name='최고속도', value=f'초반 : {speeds[0]}m/s | 중반 : {speeds[1]}m/s | 스퍼트 : {speeds[2]}m/s', inline=False)
        embed.add_field(name='가속도', value=f'초반 : {accels[0]}m/s² | 중반 : {accels[1]}m/s² | 스퍼트 : {accels[2]}m/s²', inline=False)
        embed.add_field(name='지구력', value=str(hp), inline=False)
        embed.add_field(name='스킬 발동률', value=str(skill_activation) + "%", inline=False)
        embed.add_field(name='흥분 확률', value=str(excitement_percentage) + "%", inline=False)
        await chat.respond(embed=embed)


def setup(client):
    client.add_cog(Somethings(client))
