import discord
from discord.ext import commands
import random
import math
import sqlite3
import os
import matplotlib.pyplot as plt


def dist_accel(aptitude):
    if aptitude == "E":
        return 0.6
    elif aptitude == "F":
        return 0.5
    elif aptitude == "G":
        return 0.4
    else:
        return 1


def tracks(track_type, track_condition):
    if track_condition == "포화":
        return 1.02
    elif track_condition == "다습":
        if track_type == "잔디":
            return 1.02
        else:
            return 1.01
    else:
        return 1


def acceleration(start, target, accel, standard, multiplier, is_mid):
    if not is_mid:
        time = (target - start) / accel
        move = (target + start) / 2 * time
        hp_lost = 20*multiplier*((accel*time + start-standard+12)**3 - (start-standard+12)**3) / (3*accel*144)
    else:
        if target < start:
            accel = -0.8
        time = (target - start) / accel
        move = (target + start) / 2 * time
        hp_lost = 20 * multiplier * ((target - standard + 12)**3 - (start - standard + 12)**3) / (3 * accel * 144)
    return time, move, hp_lost


def constant(speed, move, standard, multiplier):
    if move <= 0:
        return 0, 0
    else:
        time = move / speed
        hp_lost = 20 * multiplier * (speed - standard + 12)**2 * time / 144
        return time, hp_lost


def spurt_cal(remain_hp, race_dist, end_multi, standard, end, spurt):
    spurt_dist = ((remain_hp - (race_dist/3 - 60) * 20 * end_multi * (end - standard + 12)**2 / (end * 144)) /
                  (20*end_multi*((spurt-standard+12)**2 / (spurt*144) - (end-standard+12)**2 / (end*144)))) + 60
    return spurt_dist


def pretreatment(data_list):
    data1, data2, data3 = [], [], []
    for data in data_list:
        data1.append(data[0])
        data2.append(data[1])
        data3.append(data[2])
    return data1, data2, data3


# [속도 보정값, 가속도 보정값, 지구력 보정값]
strategy_dic = {"도주": [[1, 0.98, 0.962], [1, 1, 0.996], 0.95],
                "선행": [[0.978, 0.991, 0.975], [0.985, 1, 0.996], 0.89],
                "선입": [[0.938, 0.998, 0.994], [0.938, 1, 1], 1],
                "추입": [[0.935, 1, 1], [0.931, 1, 0.997], 0.995]}

track_aptitude_dic = {"S": 1.05, "A": 1, "B": 0.9, "C": 0.8, "D": 0.7, "E": 0.5, "F": 0.3, "G": 0.1}
distance_aptitude_dic = {"S": 1.05, "A": 1, "B": 0.9, "C": 0.8, "D": 0.6, "E": 0.4, "F": 0.2, "G": 0.1}
strategy_aptitude_dic = {"S": 1.1, "A": 1, "B": 0.85, "C": 0.75, "D": 0.6, "E": 0.4, "F": 0.2, "G": 0.1}

condition_dic = {"최상": 1.1, "양호": 1.05, "보통": 1, "저조": 0.95, "최악": 0.9}


def calculate(strategy, race_distance, track_type, track_condition, stats, aptitudes, condition, healing):
    strategy_list = strategy_dic.get(strategy)
    stats = stats[1:-1].split(", ")
    aptitudes = aptitudes.split(", ")
    acceleration_multiplier = track_aptitude_dic.get(aptitudes[0]) * dist_accel(aptitudes[1])
    speed_multiplier = distance_aptitude_dic.get(aptitudes[1])
    intelligence_multiplier = strategy_aptitude_dic.get(aptitudes[2])
    condition_multiplier = condition_dic.get(condition)
    stats = map(int, stats)
    stats = [int(x * condition_multiplier) for x in stats]
    stats[4] = int(stats[4] * intelligence_multiplier)
    standard_speed = 22 - race_distance / 1000

    speeds = [standard_speed * strategy_list[0][0],
              standard_speed * strategy_list[0][1],
              standard_speed * strategy_list[0][2] + math.sqrt(500 * stats[0]) * speed_multiplier * 0.002,
              standard_speed * (strategy_list[0][2] + 0.01) * 1.05 + math.sqrt(500 * stats[0])
              * speed_multiplier * 0.002 * 2.05]
    basic_acceleration = 0.0006 * math.sqrt(500 * stats[1]) * acceleration_multiplier
    accels = [basic_acceleration * strategy_list[1][0],
              basic_acceleration * strategy_list[1][1],
              basic_acceleration * strategy_list[1][2]]
    basic_hp = race_distance + stats[2] * strategy_list[2] * 0.8
    hp = basic_hp * (1 + healing * 0.01)
    if 100 - 9000 / stats[4] < 20:
        skill_activation = 20
    else:
        skill_activation = round(100 - 9000 / stats[4], 2)
    excitement_percentage = round((6.5 / math.log10(stats[4] * 0.1 + 1)) ** 2, 2)
    track_hp_multiplier = tracks(track_type, track_condition)
    end_hp_multiplier = track_hp_multiplier * (1 + (200 / math.sqrt(600 * stats[3])))

    # [목표 속도, 가속도]
    accel_factors = [[speeds[0], accels[0]], [speeds[1], accels[1]], [speeds[2], accels[2]], [speeds[3], accels[2]]]
    moves = [race_distance / 6, race_distance / 3 * 2, "종반", "스퍼트"]
    is_mids = [False, True, False, False]
    hp_multipliers = [track_hp_multiplier, track_hp_multiplier, end_hp_multiplier, end_hp_multiplier]
    graphs = []
    time = 0
    remain_hp = hp
    distance = 0
    current_speed = 3
    spurt_dist = 0

    graphs.append([distance, current_speed, remain_hp])  # 스타트 대쉬
    time += (standard_speed * 0.85 - 3) / (24 + accels[0])
    distance += (standard_speed * 0.85 + 3) / 2 * time
    remain_hp -= 20 * track_hp_multiplier * time
    current_speed = standard_speed * 0.85
    graphs.append([distance, current_speed, remain_hp])
    for accel_factor, move, is_mid, hp_multiplier in zip(accel_factors, moves, is_mids, hp_multipliers):
        if move == "종반":
            spurt_dist = spurt_cal(remain_hp, race_distance, end_hp_multiplier, standard_speed, speeds[2], speeds[3])
        cal = acceleration(current_speed, accel_factor[0], accel_factor[1], standard_speed, hp_multiplier, is_mid)
        time += cal[0]
        distance += cal[1]
        remain_hp -= cal[2]
        current_speed = accel_factor[0]
        graphs.append([distance, current_speed, remain_hp])

        if move == "종반":
            if spurt_dist >= (race_distance - distance):
                move = distance
            else:
                move = spurt_dist - distance
        elif move == "스퍼트":
            consume_hp = 20*end_hp_multiplier*(speeds[3]-standard_speed+12)**2 * (race_distance-distance)/speeds[3]/144
            if remain_hp < consume_hp:
                time = remain_hp / (20 * end_hp_multiplier * (speeds[3] - standard_speed + 12) ** 2 / 144)
                distance += speeds[3] * time
                remain_hp = 0
                graphs.append([distance, current_speed, remain_hp])
                break
            else:
                move = race_distance
        move -= distance
        cal = constant(current_speed, move, standard_speed, hp_multiplier)
        time += cal[0]
        distance += move
        remain_hp -= cal[1]
        graphs.append([distance, current_speed, remain_hp])

    if remain_hp == 0:
        time = (-speeds[3] + math.sqrt(speeds[3]**2 + 2 * -1.2 * (race_distance - distance))) / -1.2
        distance = race_distance
        current_speed -= 1.2 * time
        graphs.append([distance, current_speed, remain_hp])

    graph_x, graph_y1, graph_y2 = pretreatment(graphs)
    plt.rcParams['figure.figsize'] = (22, 9)
    plt.rcParams['font.size'] = 20
    fig, speed_ax = plt.subplots()
    speed_ax.plot(graph_x, graph_y1, color='blue')
    speed_ax.set_xlim([0, race_distance])
    speed_ax.set_ylim([0, 25])
    speed_ax.grid(True, axis='y')
    speed_ax.tick_params(axis='both', direction='in', length=5)
    speed_ax.axvline(race_distance / 6, 0, 1, color='gray', linestyle='solid', linewidth=2)
    speed_ax.axvline(race_distance / 3 * 2, 0, 1, color='gold', linestyle='solid', linewidth=2)
    hp_ax = speed_ax.twinx()
    hp_ax.set_ylim([0, hp])
    hp_ax.plot(graph_x, graph_y2, color='orange')
    speeds = [round(x, 3) for x in speeds]
    accels = [round(x, 3) for x in accels]
    return speeds, accels, hp, skill_activation, excitement_percentage, plt


class YesNo(discord.ui.View):
    def __init__(self, db_edit1, db_edit2, embed_text):
        super().__init__()
        self.db_edit1 = db_edit1
        self.db_edit2 = db_edit2
        self.embed_text = embed_text

    @discord.ui.button(label="네", style=discord.ButtonStyle.primary)
    async def yes(self, button, interaction):
        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute(self.db_edit1)
        DB.execute(self.db_edit2)
        data.commit()
        data.close()
        embed = discord.Embed(title="덮어쓰기 성공", color=0xffffff)
        embed.add_field(name="신규 우마무스메 정보", value=self.embed_text, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="아니요", style=discord.ButtonStyle.primary)
    async def no(self, button, interaction):
        await interaction.response.edit_message(embed=None, content="취소되었습니다.", view=None)


class Somethings(discord.Cog):
    def __init__(self, client):
        self.client = client
        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute("CREATE TABLE IF NOT EXISTS umamusume\
                   (user_id int, slot int, strategy text, stat text, aptitude text, healing real, \
                   PRIMARY KEY (user_id, slot))")
        data.commit()
        data.close()

    @discord.slash_command()
    async def dice(self, chat):
        dice_number = ['1', '2', '3', '4', '5', '6']
        await chat.respond(random.choice(dice_number))

    @discord.slash_command()
    async def number(self, chat, *, digits=int()):
        if digits > 2000:
            await chat.send('자릿수는 2000보다 클 수 없습니다.')
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

    @discord.slash_command(guild_ids=[907936221446148138, 792068683580440587])
    async def clear_db(self, chat):
        os.remove('data/user_slot.db')
        await chat.respond("데이터베이스가 초기화 되었습니다.")

    @discord.slash_command(description="엑셀계산기 이식", guild_ids=[907936221446148138, 792068683580440587])
    async def stat(self, chat,
                   strategy: discord.Option(str, "각질을 선택하세요.", choices=["도주", "선행", "선입", "추입"]),
                   race_distance: discord.Option(int, "경주 거리를 입력하세요."),
                   track_type: discord.Option(str, "마장 종류를 선택하세요.", choices=["잔디", "더트"]),
                   track_condition: discord.Option(str, "마장 상태를 선택하세요.", choices=["양호", "다습", "포화", "불량"]),
                   speed: discord.Option(int, "스피드 스탯을 입력하세요."),
                   power: discord.Option(int, "파워 스탯을 입력하세요."),
                   stamina: discord.Option(int, "스태미나 스탯을 입력하세요."),
                   grit: discord.Option(int, "근성 스탯을 입력하세요."),
                   intelligence: discord.Option(int, "지능 스탯을 입력하세요."),
                   track_aptitude: discord.Option(str, "마장 적성을 선택하세요.",
                                                  choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   distance_aptitude: discord.Option(str, "거리 적성을 선택하세요.",
                                                     choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   strategy_aptitude: discord.Option(str, "각질 적성을 선택하세요.",
                                                     choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   condition: discord.Option(str, "컨디션을 선택하세요.", choices=["최상", "양호", "보통", "저조", "최악"]),
                   healing: discord.Option(float, "회복량을 입력하세요.(%)")):

        stats = str([speed, power, stamina, grit, intelligence])
        aptitudes = track_aptitude + ", " + distance_aptitude + ", " + strategy_aptitude
        speeds, accels, hp, skill, excitement, plt = \
            calculate(strategy, race_distance, stats, track_type, track_condition, aptitudes, condition, healing)
        plt.savefig(f'{chat.author.id}.png')
        file = discord.File(f'{chat.author.id}.png', spoiler=False)
        embed = discord.Embed(title="성능 계산 결과", color=0xffffff)
        embed.add_field(name='우마무스메 정보',
                        value=f"경주 거리 : {race_distance} | 각질 : {strategy} | 스탯 : {stats} | \
                              적성 : {aptitude} | 컨디션 : {condition} | 회복량 : {healing}%", inline=False)
        embed.add_field(name='최고 속도', value=f'초반 : {speeds[0]}m/s | 중반 : {speeds[1]}m/s | 종반 : {speeds[2]}m/s \
                                            | 스퍼트 : {speeds[3]}m/s', inline=False)
        embed.add_field(name='가속도', value=f'초반 : {accels[0]}m/s² | 중반 : {accels[1]}m/s² | 스퍼트 : {accels[2]}m/s²',
                        inline=False)
        embed.add_field(name='지구력', value=str(hp), inline=False)
        embed.add_field(name='스킬 발동률', value=str(skill) + "%", inline=False)
        embed.add_field(name='흥분 확률', value=str(excitement) + "%", inline=False)
        await chat.respond(embed=embed, file=file)
        os.remove(f'{chat.author.id}.png')

    @discord.slash_command(description="우마무스메 저장", guild_ids=[907936221446148138, 792068683580440587])
    async def save(self, chat,
                   slot: discord.Option(int, "저장할 슬롯을 골라주세요.", choices=[1, 2, 3, 4, 5]),
                   strategy: discord.Option(str, "각질을 선택하세요.", choices=["도주", "선행", "선입", "추입"]),
                   speed: discord.Option(int, "스피드 스탯을 입력하세요."),
                   power: discord.Option(int, "파워 스탯을 입력하세요."),
                   stamina: discord.Option(int, "스태미나 스탯을 입력하세요."),
                   grit: discord.Option(int, "근성 스탯을 입력하세요."),
                   intelligence: discord.Option(int, "지능 스탯을 입력하세요."),
                   track_aptitude: discord.Option(str, "마장 적성을 선택하세요.",
                                                  choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   distance_aptitude: discord.Option(str, "거리 적성을 선택하세요.",
                                                     choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   strategy_aptitude: discord.Option(str, "각질 적성을 선택하세요.",
                                                     choices=["S", "A", "B", "C", "D", "E", "F", "G"]),
                   healing: discord.Option(float, "회복량을 입력하세요.(%)")):

        stats = [speed, power, stamina, grit, intelligence]
        aptitudes = track_aptitude + ", " + distance_aptitude + ", " + strategy_aptitude
        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute("SELECT * FROM umamusume WHERE user_id=? and slot=?", (chat.author.id, slot))
        exist = DB.fetchone()

        db_edit1 = "DELETE FROM umamusume WHERE user_id='%s' and slot='%s'" % (chat.author.id, slot)
        db_edit2 = "INSERT INTO umamusume VALUES('%s','%s','%s','%s','%s','%s')" % \
                   (chat.author.id, slot, strategy, str(stats), aptitudes, healing)
        embed_text = f"저장 슬롯 : {slot} | 각질 : {strategy} | 스탯 : {stats} | \
                                          적성 : {track_aptitude}, {distance_aptitude}, {strategy_aptitude} | \
                                          회복량 : {healing}%"
        if exist:
            embed = discord.Embed(title="덮어씌우시겠습니까?", color=0xffffff)
            embed.add_field(name='기존 우마무스메 정보',
                            value=f"저장 슬롯 : {str(exist[1])} | 각질 : {exist[2]} | 스탯 : {exist[3]} | \
                                          적성 : {exist[4]} | 회복량 : {exist[5]}%", inline=False)
            embed.add_field(name='신규 우마무스메 정보', value=embed_text, inline=False)
            await chat.respond(embed=embed, view=YesNo(db_edit1, db_edit2, embed_text))
        else:
            DB.execute(db_edit2)
            embed = discord.Embed(title="저장 성공", color=0xffffff)
            embed.add_field(name='우마무스메 정보', value=embed_text, inline=False)
            await chat.respond(embed=embed)
        data.commit()
        data.close()

    @discord.slash_command(description="우마무스메 불러오기", guild_ids=[907936221446148138, 792068683580440587])
    async def load(self, chat,
                   slot: discord.Option(int, "불러올 슬롯을 골라주세요.", choices=[1, 2, 3, 4, 5]),
                   race_distance: discord.Option(int, "경주 거리를 입력하세요."),
                   track_type: discord.Option(str, "마장 종류를 선택하세요.", choices=["잔디", "더트"]),
                   track_condition: discord.Option(str, "마장 상태를 선택하세요.", choices=["양호", "다습", "포화", "불량"]),
                   condition: discord.Option(str, "컨디션을 선택하세요.", choices=["최상", "양호", "보통", "저조", "최악"]),
                   healing: discord.Option(float, "역병을 입력하세요.(%)")):

        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute("SELECT * FROM umamusume WHERE user_id=? and slot=?", (chat.author.id, slot))
        load_data = DB.fetchone()
        if load_data:
            healing = load_data[5] - healing
            speeds, accels, hp, skill, excitement, plt = calculate(load_data[2], race_distance, track_type, track_condition,
                                                                   load_data[3], load_data[4], condition, healing)
            plt.savefig(f'{chat.author.id}.png')
            file = discord.File(f'{chat.author.id}.png', spoiler=False)
            embed = discord.Embed(title="성능 계산 결과", color=0xffffff)
            embed.add_field(name='우마무스메 정보',
                            value=f"저장 슬롯 : {slot} | 경주 거리 : {race_distance} | 각질 : {load_data[2]} | 스탯 : {load_data[3]} \
                                    | 적성 : {load_data[4]} | 컨디션 : {condition} | 회복량 : {healing}%", inline=False)
            embed.add_field(name='최고 속도', value=f'초반 : {speeds[0]}m/s | 중반 : {speeds[1]}m/s | 종반 : {speeds[2]}m/s \
                                                    | 스퍼트 : {speeds[3]}m/s', inline=False)
            embed.add_field(name='가속도', value=f'초반 : {accels[0]}m/s² | 중반 : {accels[1]}m/s² | 스퍼트 : {accels[2]}m/s²',
                            inline=False)
            embed.add_field(name='지구력', value=str(hp), inline=False)
            embed.add_field(name='스킬 발동률', value=str(skill) + "%", inline=False)
            embed.add_field(name='흥분 확률', value=str(excitement) + "%", inline=False)
            await chat.respond(embed=embed, file=file)
            os.remove(f'{chat.author.id}.png')
        else:
            await chat.respond(content=f"{slot}번 슬롯에 저장된 정보가 없습니다.")
        data.close()

    @discord.slash_command(description="저장된 정보 전부 보기", guild_ids=[907936221446148138, 792068683580440587])
    async def view_all(self, chat):
        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute("SELECT * FROM umamusume WHERE user_id=?", (chat.author.id,))
        load_data = DB.fetchall()
        if load_data:
            embed = discord.Embed(title="저장된 우마무스메", color=0xffffff)
            for load in load_data:
                embed.add_field(name=f'{load[1]}번', value=f"각질 : {load[2]} | \
                                스탯 : {load[3]} | 적성 : {load[4]} | 회복량 : {load[5]}%", inline=False)
            await chat.respond(embed=embed)
        else:
            await chat.respond(content="저장된 정보가 없습니다.")
        data.close()

    @discord.slash_command(description="우마무스메 비교", guild_ids=[907936221446148138, 792068683580440587])
    async def compare(self, chat,
                      race_distance: discord.Option(int, "경주 거리를 입력하세요."),
                      slot1: discord.Option(int, "1번으로 불러올 슬롯을 골라주세요.", choices=[1, 2, 3, 4, 5]),
                      condition1: discord.Option(str, "1번의 컨디션을 선택하세요.", choices=["최상", "양호", "보통", "저조", "최악"]),
                      slot2: discord.Option(int, "2번으로 불러올 슬롯을 골라주세요.", choices=[1, 2, 3, 4, 5]),
                      condition2: discord.Option(str, "2번의 컨디션을 선택하세요.", choices=["최상", "양호", "보통", "저조", "최악"])):

        data = sqlite3.connect("data/user_slot.db")
        DB = data.cursor()
        DB.execute("SELECT * FROM umamusume WHERE user_id=? and slot=?", (chat.author.id, slot1))
        slot1_data = DB.fetchone()
        DB.execute("SELECT * FROM umamusume WHERE user_id=? and slot=?", (chat.author.id, slot2))
        slot2_data = DB.fetchone()
        if slot1_data and slot2_data:
            slot1_cal = calculate(slot1_data[2], race_distance, "잔디", "양호",
                                  slot1_data[3], slot1_data[4], condition1, slot1_data[5])
            speeds1, accels1 = slot1_cal[0], slot1_cal[1]
            slot2_cal = calculate(slot2_data[2], race_distance, "잔디", "양호",
                                  slot2_data[3], slot2_data[4], condition2, slot2_data[5])
            speeds2, accels2 = slot2_cal[0], slot2_cal[1]

            embed = discord.Embed(title="성능 비교 결과", color=0xffffff)
            embed.add_field(name='우마무스메 비교',
                            value=f"저장 슬롯 : {slot1} | 경주 거리 : {race_distance} | 각질 : {slot1_data[2]} | \
                                    스탯 : {slot1_data[3]} | 적성 : {slot1_data[4]} | 컨디션 : {condition1} | \
                                    회복량 : {slot1_data[5]}%\n\n \
                                    저장 슬롯 : {slot2} | 경주 거리 : {race_distance} | 각질 : {slot2_data[2]} | \
                                    스탯 : {slot2_data[3]} | 적성 : {slot2_data[4]} | 컨디션 : {condition1} | \
                                    회복량 : {slot2_data[5]}%", inline=False)
            embed.add_field(name='최고 속도 비교',
                            value=f'초반 : {speeds1[0]}m/s | 중반 : {speeds1[1]}m/s | 스퍼트 : {speeds1[3]}m/s\n\n \
                                    초반 : {speeds2[0]}m/s | 중반 : {speeds2[1]}m/s | 스퍼트 : {speeds2[3]}m/s', inline=False)
            embed.add_field(name='가속도 비교',
                            value=f'초반 : {accels1[0]}m/s² | 중반 : {accels1[1]}m/s² | 스퍼트 : {accels1[2]}m/s²\n\n \
                                    초반 : {accels2[0]}m/s² | 중반 : {accels2[1]}m/s² | 스퍼트 : {accels2[2]}m/s²',
                            inline=False)
            await chat.respond(embed=embed)
        else:
            await chat.respond(content="저장된 정보가 없습니다.")
        data.close()


def setup(client):
    client.add_cog(Somethings(client))
