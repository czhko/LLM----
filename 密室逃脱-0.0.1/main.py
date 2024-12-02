import role
import event
import random
import llm

'''
开发方向：
属性：AI、用户的印象及其属性
====可能需要固定属性和可变属性，比如：地点、心情、时间等等
记忆：需要做好总结模块
判断：应该需要专门微调
思维链：逻辑先后行为的专门微调
====不用微调也有一点样子的，但是需要形成链条，影响决策还是任重道远，或许可以加入”上一刻、上几刻想法“之类的
系统、用户交互：作为行为、描述等设定的内容，需要剧本、节点等设定
'''
# 资源载入
user_role = role.character_list[0]
ai_role = role.character_list[1]
# ai_role2 = role.character_list[0]
game_plot = event.game_plot_test

# ai各个情况prompt定义，需要根据先后顺序和重要程度排序
prompt_ai_choose_scene = 'Assistant: 我接下来准备探索'  # Ai进行选择时，所需要的prompt
prompt_ai_choose_item = 'Assistant: 我准备接下来进行'
prompt_ai_answer_choose = ''  # Ai面对用户询问时，所需要的prompt，询问互动：玩家问AI某个信息时，AI的回应，具体场景是结合AI调查过的已知信息，决定是否回应的选择
prompt_ai_thinking = '按照现有条件，现在应该'  # 当Ai选择了进行思考时，采用的prompt，让思考内容对接下来的决策产生影响，
prompt_ai_ask_choose = ''  # Ai需要询问user时，所需要的prompt，结合user曾公开搜索的内容
prompt_ai_risk = ''  # 当user得到危险武器时候，Ai附加的prompt
prompt_ai_personality = ''  # Ai的性格以及玩家的性格博弈的prompt
prompt_ai_important = ''  # Ai发现了重要信息的决策

# 输出系统日志
debug = False

# 重要变量
end_key = game_plot["死亡"]
user_search = 0  # 0表示选择搜索对象，-1表示观察地图，-2表示调查人员，其他数字表示具体搜索物品，
ai_search = 0
choose_sp = []  # 表示在同一个场景时，需要排除的选择
prompt_ai1 = 'AI的prompt'
prompt_ai2 = 'AI2的prompt，用于双AI玩法'
switch_state = 0  # 游戏进度方面变量
user_know = []  # AI视角玩家已知的信息
ai_know = []  # 玩家视角AI已知的信息
ai_searched = []  # AI已搜索过的东西，提供给AI，防止它重复选择
ai_knowledge = []  # AI已知的具体信息
ai_thinking = []  # 默认保存三轮思考内容，提供ai决策
impression_ai_for_user = ''  # Ai对玩家的印象，包括性格，所持物等等


# 游戏信息初始化
# 游戏显示信息，从信息json转换成文本，用于AI续写
def game_info_init(info):
    if '游戏信息' in info.keys():
        game_info = info["场景"]["密室"]["环境"]
    else:
        name = info["固定属性"]["名字"]
        age = info["固定属性"]["年龄"]
        gender = info["固定属性"]["性别"]
        cloth = info['外观']["上衣"] + '、' + info['外观']["下衣"]
        hand = info['外观']["手戴"]
        career = info["现在状况"]["职业"]
        hp = info['身体属性']["体力"]
        sp = info['身体属性']["心态"]
        guilt = info['身体属性']["罪恶度"]
        package = info['现在状况']["口袋"]

        shp, ssp, sg, ss = '', '', '', ''
        if hp < 60:
            shp = '稍许疲惫'
        if hp < 30:
            shp = '非常疲惫'
        if sp < 60:
            ssp = '心神不宁'
        if sp < 30:
            ssp = '要疯了'
        if guilt > 60:
            sg = '，做什么都有可能'
        if shp != '' or ssp != '' or sg != '':
            ss = "感觉现在" + shp + ssp + sg + '。'

        if career == '无':
            game_info = '我叫' + name + '。\n是一名衣着' + cloth + '的' \
                        + gender[0] + '人。'
        elif career == '学生':
            if 12 < age <= 15:
                career = '初中生'
            elif 15 < age <= 18:
                career = '高中生'
            else:
                career = '小学生'
            game_info = '我叫' + name + '。\n是一名' + gender[0] + career \
                        + '。\n衣着' + cloth + '。' + ss
        else:
            game_info = '我叫' + name + '。\n是一名' + gender[0] + career \
                        + '。\n衣着' + cloth + '。' + ss
        if hand != '':
            game_info = game_info + '现在手上拿着' + hand
        item = ''
        if len(package) > 0:
            for item_i in package:
                item = item + item_i + '、'
            game_info = game_info + '口袋里装有' + item[:-1]

    return game_info


# AI角色prompt初始化，从信息json转换成文本，用于AI续写
def ai_role_init(game_role):
    name = game_role["固定属性"]["名字"]
    age = game_role["固定属性"]["年龄"]
    gender = game_role["固定属性"]["性别"]
    personality = game_role["固定属性"]["性格"]

    cloth = game_role['外观']["上衣"] + '、' + game_role['外观']["下衣"]
    hand = game_role['外观']["手戴"]
    career = game_role["现在状况"]["职业"]
    self_know = game_role["现在状况"]["自我认知"]
    hp = game_role['身体属性']["体力"]
    sp = game_role['身体属性']["心态"]
    guilt = game_role['身体属性']["罪恶度"]
    package = game_role['现在状况']["口袋"]

    shp, ssp, sg, ss = '', '', '', ''
    if hp < 60:
        shp = '稍许疲惫'
    if hp < 30:
        shp = '非常疲惫'
    if sp < 60:
        ssp = '心神不宁'
    if sp < 30:
        ssp = '要疯了'
    if guilt > 60:
        sg = '，做什么都有可能'
    if shp != '' or ssp != '' or sg != '':
        ss = "感觉现在" + shp + ssp + sg + '。'

    p_str = ''
    for p in personality:
        p_str = p_str + p + '、'
    p_str = p_str[:-1]

    if career == '无':
        game_info = '我叫' + name + '。是一名衣着' + cloth + '的' + gender[0] + '人。性格' \
                    + p_str + '。自认为是位' + self_know + '。' + ss
    elif career == '学生':
        if 12 < age <= 15:
            career = '初中生'
        elif 15 < age <= 18:
            career = '高中生'
        else:
            career = '小学生'
        game_info = '我叫' + name + '。是一名' + gender[0] + career + '。衣着' + cloth \
                    + '。性格' + p_str + '。自认为是位' + self_know + '。' + ss
    else:
        game_info = '我叫' + name + '。是一名' + gender[0] + career + '。衣着' + cloth \
                    + '。性格' + p_str + '。自认为是位' + self_know + '。' + ss

    if hand != '':
        game_info = game_info + '现在手上拿着' + hand
    item = ''
    if len(package) > 0:
        for item_i in package:
            item = item + item_i + '、'
        game_info = game_info + '口袋里装有' + item

    return game_info


# 做出对场景最简单的第一印象，从信息json转换成文本，用于AI续写
def role_first_impression(first_role, seconds_role, player=False):
    #    name = first_role["固定属性"]["名字"]  对于真实情况，第一印象中应该不知道对方名字
    if first_role["固定属性"]["性别"] == seconds_role["固定属性"]["性别"]:
        gender = first_role["固定属性"]["性别"]
    else:
        gender = seconds_role["固定属性"]["性别"]

    f_age = first_role["固定属性"]["年龄"]
    s_age = seconds_role["固定属性"]["年龄"]
    age_rate = max([f_age, s_age]) - min([f_age, s_age])
    if age_rate > 3:
        if f_age < s_age:
            age_info = '年龄比自己大，'
        else:
            age_info = '年龄比自己小，'
    else:
        age_info = '年龄与自己相近，'

    f_high = first_role["固定属性"]["身高"]
    s_high = seconds_role["固定属性"]["身高"]
    high_rate = max([f_high, s_high]) - min([f_high, s_high])
    if high_rate > 10:
        if f_high < s_high:
            high_info = '身材比自己高'
        else:
            high_info = '身材比自己矮'
    else:
        high_info = '身高与自己相近'

    f_wight = first_role["固定属性"]["体重"]
    s_wight = seconds_role["固定属性"]["体重"]
    wight_rate = max([f_wight, s_wight]) / min([f_wight, s_wight])
    if wight_rate > 1.2:
        if f_wight < s_wight:
            wight_info = '、强壮的'
        else:
            wight_info = '、娇弱的'
    else:
        wight_info = ',体重与自己相近的'

    if high_rate < 10 and wight_rate < 1.2:
        high_info = '身高'
        wight_info = '、体重与自己相近的'

    if seconds_role["现在状况"]["职业"] == '学生':
        if 12 < s_age <= 15:
            s_ca = gender[0] + '初中生'
        elif 15 < s_age <= 18:
            s_ca = gender[0] + '高中生'
        else:
            s_ca = gender
    else:
        s_ca = gender

    personality = seconds_role["固定属性"]["性格"]
    cloth = seconds_role['外观']["上衣"] + '、' + seconds_role['外观']["下衣"]

    p_str = ''
    if not player:
        for p in personality:
            p_str = p_str + p + '、'
        p_str = '。看过去有些' + p_str[:-1]

    hand = seconds_role['外观']["手戴"]
    if hand != '':
        hand_info = '现在手上拿着' + hand
    else:
        hand_info = ''

    shp, ssp, ss = '', '', ''
    hp = seconds_role['身体属性']["体力"]
    sp = seconds_role['身体属性']["心态"]
    if hp < 60:
        shp = '稍许疲惫'
    if hp < 30:
        shp = '非常疲惫'
    if sp < 60:
        ssp = '心神不宁'
    if sp < 30:
        ssp = '要疯了'
    if shp != '' or ssp != '':
        ss = "感觉现在" + shp + ssp + '。'

    return age_info + high_info + wight_info + s_ca + '。穿着' + cloth + p_str + '。' + ss + hand_info


def prompt_update():
    global prompt_ai1, ai_knowledge
    user_role = role.character_list[0]
    ai_role = role.character_list[1]
    ai_role_info = ai_role_init(ai_role)
    environment = game_info_init(game_plot)
    role1_impression = role_first_impression(ai_role, user_role)
    prompt_ai1 = ai_role_info + '\n当我清醒后发现，自己似乎被绑架到了这里。' + environment.replace('\n', '') \
                 + '\n' + user_role["固定属性"]["名字"] + '同样被绑架在这里。对方是' + role1_impression \
                 + '\n但是，现在的首要任务是' + game_plot["游戏信息"]["目标"]
    ai_knowledge = list(set(ai_knowledge))
    knowledge_all = ''
    if len(ai_knowledge) > 0:
        for knowledge in ai_knowledge:
            if '钥匙' in knowledge:
                knowledge = knowledge + '，这个钥匙应该能打开某个关键物品！'
            knowledge_all = knowledge_all + knowledge + '\n'
        knowledge_all = knowledge_all[:-1]

    prompt_ai1 = prompt_ai1 + '现在已知的所有情报：' + knowledge_all


def game_init():
    global prompt_ai1, user_role, ai_role, game_plot, end_key, user_search, ai_search
    # 这里开始重置信息 因为python变量生命周期的缘故 一些变量的初始化可能需要调整
    user_role = role.character_list[0]
    ai_role = role.character_list[1]
    # ai_role2 = role.character_list[0]
    game_plot = event.game_plot_test

    user_search = 0
    ai_search = 0
    end_key = game_plot["死亡"]
    environment = game_info_init(game_plot)
    user_name = user_role["固定属性"]["名字"]
    ai_name = ai_role["固定属性"]["名字"]
    # 玩家展示信息
    role1 = game_info_init(user_role)
    role2 = ai_name + '看着是一名' + role_first_impression(user_role, ai_role, True)  # 差的性格在第一印象中是看不出来的，建议用代码调整成好的

    # 将游戏进程标注，表示已经实现的功能
    dialog = [
        {"role": "assistant", "content": "==========信息初始化=========="},
        {"role": "user", "content": "==========载入玩家=========="},
        {"role": "assistant", "content": "==========载入AI=========="},
        {"role": "assistant", "content": "==========载入环境=========="},
        {"role": "assistant", "content": "==========AI发现玩家=========="}]
    # AI所知的信息以及它所有选择、判断对话的最初依据
    ai_role_info = ai_role_init(ai_role)
    first_impression = role_first_impression(ai_role, user_role)
    prompt_ai1 = ai_role_info + '\n当我清醒后发现，自己似乎被绑架到了这里。' + environment.replace('\n', '') \
                 + '\n眼前有一个人同样被绑架在这里。看起来是一位' + first_impression \
                 + '\n但是，现在的首要任务是' + game_plot["游戏信息"]["目标"]
    # 这条是debug模式，后期设置开关进行控制是否屏蔽
    if debug:
        dialog.append({"role": "assistant",
                       "content": "==========载入AI prompt==========\n" + prompt_ai1 + '\nprompt长度：' + str(
                           len(prompt_ai1))})

    first_user_chat = '这里是哪…你也是被绑架到了这里吗，我的名字叫' + user_name + '。'
    first_dialog = prompt_ai1 + "\n\n" + user_name + "说: " + first_user_chat + "\n\n" + ai_name + "说: "
    first_ai_chat, total_token = llm.generate(first_dialog + "我叫" + ai_name)
    first_ai_chat = "我叫" + ai_name + first_ai_chat

    # 这下面四条是debug模式，后期设置开关进行控制是否屏蔽
    if debug:
        first_dialog = first_dialog + first_ai_chat
        dialog.append({"role": "assistant", "content": '==========首次对话==========\n'
                                                       + first_dialog + '\n\n总token数为：' + str(total_token)})
        dialog.append(
            {"role": "assistant",
             "content": '==========行动次数==========\n总次数：' + str(
                 end_key) + "，每行动一次消耗1点，达到 0 时表示氧气归零，全员死亡。"})

    # 这上面四条是debug模式，后期设置开关进行控制是否屏蔽
    prompt_update()
    # 这条是debug模式，后期设置开关进行控制是否屏蔽
    if debug:
        dialog.append({"role": "assistant",
                       "content": '==========AI prompt变更==========\n' + prompt_ai1 + '\n\nprompt长度：' + str(
                           len(prompt_ai1))})

    thing = str(['密室', ai_name] + game_plot["场景"]["密室"]["视野物品"])[:-1][1:].replace(',', '、').replace("'", '')
    dialog.append({"role": "assistant", "content": '==========开始游戏=========='})
    dialog.append({"role": "user", "content": '环绕四周，眼前看到了：' + thing})

    chat = [[first_user_chat, first_ai_chat]]

    return role1, role2, environment, dialog, chat


def choose_init():
    if ai_role['现在状况']["行动能力"] == -1:
        choose = [game_plot["场景"]["密室"]["名称"]]
    else:
        choose = [game_plot["场景"]["密室"]["名称"], ai_role["固定属性"]["名字"]]

    choose = choose + game_plot["场景"]["密室"]["视野物品"]

    return choose


def ai_choose_init():
    if user_role['现在状况']["行动能力"] == -1:
        choose = [game_plot["场景"]["密室"]["名称"]]
    else:
        choose = [game_plot["场景"]["密室"]["名称"], user_role["固定属性"]["名字"]]

    choose = choose + game_plot["场景"]["密室"]["视野物品"]

    return choose


def predict_prompt(history):
    # print(history)
    prompt = prompt_ai1 + '\n\n'
    user_name = user_role["固定属性"]["名字"]
    for idx, (user_msg, model_msg) in enumerate(history):

        if idx == len(history) - 1 and not model_msg:
            prompt = prompt + user_name + "说: " + user_msg + '\n\n'
            break
        if user_msg:
            if user_msg != '（搜索中……）':
                prompt = prompt + user_name + "说: " + user_msg + '\n\n'
        if model_msg:
            prompt = prompt + "我说: " + model_msg + '\n\n'

    return prompt


# 生成选择时候的prompt
def judge_choices_prompt(cc, chat, choices='', item_search=True):
    user_name = user_role["固定属性"]["名字"]
    user_position = ''
    if not 12 > user_search > 7:
        scene_item_list = list(game_plot["物品"].keys())
        for scene_item in scene_item_list:
            if game_plot["物品"][scene_item]["ID"] == user_search:
                user_position = scene_item
    black_prompt = ''
    search = ''

    for black_choose in cc:
        if black_choose in ai_searched:
            black_prompt = black_prompt + black_choose + '、'
        else:
            search = search + black_choose + '、'
    if black_prompt != '':
        black_prompt = '。\n我已搜索过' + black_prompt[:-1] + '。\n我应该从' + search[:-1] + '中选择一个。\n'
    else:
        black_prompt = '。我应该从' + search[:-1] + '中选择一个。\n'

    # i = '\nAssistant: 就算使用暴力也好，我应该不择手段逃出去，仔细想想，现在应该怎么办：'
    if item_search:

        if choices == '':

            p = predict_prompt(chat) + '\n现在' + user_name + '在搜索' + user_position \
                + black_prompt + prompt_ai_choose_scene
            #think, i = llm.generate(p, t_top=0.2, temp=0.5, m_token=30)
            #p = p + think + '\n' + prompt_ai_choose_scene
        else:
            p = predict_prompt(chat) + '\n现在' + user_name + '在搜索' + user_position + '。' \
                + '\n我在搜索' + choices + black_prompt + prompt_ai_choose_scene
            #think, i = llm.generate(p, t_top=0.2, temp=0.5, m_token=30)
            #p = p + think + '\n' + prompt_ai_choose_item
    else:
        p = predict_prompt(chat) + '\n现在' + user_name + '在搜索' + user_position + '。' \
            + '\n我看向' + user_name + '，' + prompt_ai_choose_scene
        #think, i = llm.generate(p, t_top=0.2, temp=0.5, m_token=30)
        #p = p + think + '\n' + prompt_ai_choose_item
    print('被ban：', black_prompt)
    # print('思考：',think)
    return p


'''=================================================================


=================================================================
'''


# 交互逻辑、行为与方法

def judge_consequence(con_list, con_value, player_id, con_type='赋值'):
    global user_role, ai_role, game_plot
    if con_list[0] in game_plot:
        info = game_plot
    else:
        if player_id == user_role["固定属性"]["ID"]:
            info = user_role
            # user_role['现在状况']["姿势"] = 1
        else:
            info = ai_role

    consequence = info[con_list[0]]
    attribute_list = con_list[1:]
    attribute_num, attribute_idx = len(attribute_list), 1
    if attribute_num > 0:
        # 删除条件的首项
        # 遍历条件，找到最终选项
        for attribute in attribute_list:
            if attribute_idx < attribute_num:
                consequence = consequence[attribute]
            else:
                if con_type == '赋值':
                    consequence.update({attribute: con_value})
                    print('赋值：', attribute, consequence[attribute])
                    return con_value
                else:
                    # type = 扣减
                    o_value = consequence[attribute] - con_value
                    consequence.update({attribute: o_value})
                    # print('扣减事件：', attribute, o_value, consequence[attribute])
                    # 其实也就扣减需要返回
                    return attribute, o_value

            attribute_idx = attribute_idx + 1


def choose_consequence(con_class_list, con_value_list, player_id, dialog, chat):
    global end_key
    cc = []
    for idx in range(len(con_class_list)):
        con_class, con_value = con_class_list[idx], con_value_list[idx]
        # 事件放在这
        attribute = con_class[0]
        if attribute == "事件":
            now_event = game_plot[attribute][con_class[1]]
            if con_class[1] == "通关":
                dialog.append({"role": "user", "content": "恭喜通关"})
                cc = ['恭喜通关']
                end_key = 0
                break
            for event_idx in range(len(now_event["后果类别"])):
                # print(event_idx, now_event)
                con_event_class, con_event_value = now_event["后果类别"][event_idx], now_event["后果内容"][event_idx]
                if now_event["类别"] == "扣减事件":
                    for i in range(con_value):
                        event_attribute, event_value = judge_consequence(con_event_class, con_event_value,
                                                                         player_id, '扣减事件')

                        if debug:
                            dialog.append({"role": "assistant", "content": '用户ID：' + str(player_id) + now_event[
                                '结果'] + event_attribute + str(event_value)})
                elif now_event["类别"] == "获得物品":
                    cc = ['藏在口袋', '拿在手上', '观察']

                else:
                    print('异常：复查未找出的行动情况')
        else:
            if len(con_class_list) == 1:
                print('异常：复查未找出的行动情况：', attribute)
            judge_consequence(con_class, con_value, player_id)

    return dialog, chat, cc


# 判断这个条件是否符合对应的值，对于状态属性是全等，对于人物属性，为大于，对于事件等文本属性则为判断文本
def judge_condition(info, condition_list, condition_value, player_id):
    condition = info[condition_list[0]]
    attribute_list = condition_list[1:]
    attribute_num, attribute_idx = len(attribute_list), 1
    if attribute_num > 0:
        # 删除条件的首项
        # 遍历条件，找到最终选项
        for attribute in attribute_list:
            if attribute_idx < attribute_num:
                condition = condition[attribute]
            else:
                # 判断条件最终项类型，有list、int、str和dict
                condition_final = condition[attribute]
                #print('id:',player_id,'实体属性:',condition_final,'值:',condition_value)
                # 如果是数字，那么就是对比数字，对上就可以加入选项
                # 其实这里有问题，不够准确，应该根据具体属性的情况来设置准入标准
                if type(condition_final) == int or type(condition_final) == float:
                    if "固定属性" in info:
                        if condition_final >= condition_value:
                            return True
                    else:
                        if condition_value == condition_final:
                            return True
                        else:
                            return False
                # 如果是文本，可能是随机数事件
                elif type(condition_final) == str:
                    if condition_final == '随机数':
                        # 当概率数比随机数大，就是命中
                        if condition_value / 100 > random.random():
                            # 加入这个实体交互
                            return True
                        else:
                            return False

                else:
                    print('正在开发中')
                    return False
            attribute_idx = attribute_idx + 1
    else:
        if condition_list[0] == "物品":
            item_list = list(info["物品"].keys())
            for item_name in item_list:
                item = info["物品"][item_name]
                if item["ID"] == condition_value:
                    if player_id in item["性质"]["携带者"]:
                        return True
            return False

    return False


def judge_behavior(player_id):
    cc = []
    behavior_interaction_list = list(game_plot["行为"]["实质行为"].keys())
    # 对"实质行为"进行判断，对于所有搜索选项，根据其条件考虑是否列出该选项
    for behavior_interaction in behavior_interaction_list:
        ii_info = game_plot["行为"]["实质行为"][behavior_interaction]
        # 从event中取出物品对应的交互，得到交互出现的条件如[["事件", '随机数'], ["物品", "空调被", "性质", "状态"]]及条件要求: [33, 1],
        condition_class_list, condition_value_list = ii_info["条件类别"], ii_info["条件要求"]
        # 将得到的数组及对应值进行遍历，如["事件", '随机数']对应33，["物品", "空调被", "性质", "状态"]对应1
        condition_num = len(condition_class_list)
        t = 0  # 这个变量来判断符合条件的个数
        for idx in range(0, condition_num):
            condition_list, condition_value = condition_class_list[idx], condition_value_list[idx]
            # 得到条件的数组["事件", '随机数']和["物品", "空调被", "性质", "状态"]
            item_attribute = condition_list[0]
            # 根据条件的首项判断是否为物品的属性，不是物品就是人
            if item_attribute in game_plot:
                if judge_condition(game_plot, condition_list, condition_value, player_id):
                    t = t + 1
            else:
                if player_id == user_role["固定属性"]["ID"]:
                    info = user_role
                else:
                    info = ai_role
                if judge_condition(info, condition_list, condition_value, player_id):
                    t = t + 1


        if ii_info['条件同时满足']:
            if t == condition_num:
                cc.append(behavior_interaction)
        else:
            if t >= 1:
                cc.append(behavior_interaction)
    return cc


def judge_choose(item, player_id):
    cc = ['观察']
    item_p = game_plot["物品"][item]
    if "实体交互" in list(item_p.keys()):
        item_interaction_list = list(item_p["实体交互"].keys())
    else:
        return cc
    # 仅对有"实体交互"的物品进行搜索，对于所有搜索选项，根据其条件考虑是否列出该选项
    for item_interaction in item_interaction_list:
        ii_info = item_p["实体交互"][item_interaction]
        if "条件类别" in list(ii_info.keys()):
            # 从event中取出物品对应的交互，得到交互出现的条件如[["事件", '随机数'], ["物品", "空调被", "性质", "状态"]]及条件要求: [33, 1],
            condition_class_list, condition_value_list = ii_info["条件类别"], ii_info["条件要求"]
            # 将得到的数组及对应值进行遍历，如["事件", '随机数']对应33，["物品", "空调被", "性质", "状态"]对应1
            condition_num = len(condition_class_list)
            t = 0  # 这个变量来判断符合条件的个数
            for idx in range(0, condition_num):
                condition_list, condition_value = condition_class_list[idx], condition_value_list[idx]
                # 得到条件的数组["事件", '随机数']和["物品", "空调被", "性质", "状态"]
                item_attribute = condition_list[0]
                # 根据条件的首项判断是否为物品的属性，不是物品就是人
                if item_attribute in game_plot:
                    if judge_condition(game_plot, condition_list, condition_value, player_id):
                        t = t + 1
                else:
                    if player_id == user_role["固定属性"]["ID"]:
                        info = user_role
                    else:
                        info = ai_role
                    if judge_condition(info, condition_list, condition_value, player_id):
                        t = t + 1
            if ii_info['条件同时满足']:
                if t == condition_num:
                    cc.append(item_interaction)
            else:
                if t >= 1:
                    cc.append(item_interaction)
        else:
            cc.append(item_interaction)
    return cc


def role_chat(chat, dialog):
    dialog.append({"role": "user", "content": '==========发起对话=========='})
    prompt = prompt_ai1
    user_name = user_role["固定属性"]["名字"]
    ai_name = ai_role["固定属性"]["名字"]

    # 分解chatbot并加入 prompt 进行续写
    for idx, (user_msg, model_msg) in enumerate(chat):
        if idx == len(chat) - 1 and not model_msg:
            prompt = prompt + user_name + "说: " + user_msg + '\n\n'
            break
        if user_msg:
            if user_msg != '（搜索中……）':
                prompt = prompt + user_name + "说: " + user_msg + '\n\n'
        if model_msg:
            prompt = prompt + "我说: " + model_msg + '\n\n'

    prompt = prompt + "\n\n" + "我说: "
    reply, total_token = llm.generate(prompt)
    chat[-1][1] = reply

    # 这两条是debug模式，后期设置开关进行控制是否屏蔽
    if debug:
        prompt = prompt + reply
        dialog.append({"role": "assistant", "content": '==========AI回应==========\n'
                                                       + prompt + '\n\n总token数为：' + str(total_token)})

    dialog.append({"role": "assistant", "content": '==========玩家开始探索=========='})
    return chat, dialog


def ai_continue(dialog, chat, choices=''):
    global user_search, ai_search, end_key, choose_sp, switch_state, ai_know, prompt_ai1, ai_searched, ai_knowledge
    # AI的行为和玩家是高度对齐，但是需要额外的很多参数
    now_map = game_plot["场景"]["密室"]["名称"]
    ai_name = ai_role["固定属性"]["名字"]
    user_name = user_role["固定属性"]["名字"]
    user_id = user_role["固定属性"]["ID"]
    ai_id = ai_role["固定属性"]["ID"]

    # 结局
    if end_key == 0:
        return dialog, chat
    # 全局事件放进这里 包括：行动惩罚
    if True:  # 判断条件待定
        # 玩家加入搜索过的信息
        # ai_role_info = ai_role_init(ai_role)
        # user_position = ''
        if not 12 > user_search > 7:
            scene_item_list = list(game_plot["物品"].keys())
            for scene_item in scene_item_list:
                if game_plot["物品"][scene_item]["ID"] == user_search:
                    ai_know.append(scene_item)
                    #  user_position = scene_item
            ai_know = list(set(ai_know))
        # AI判断是否已经搜索过，并加入搜索过的信息
        black_list = ['观察', '搜查其他物品', user_name] + list(game_plot["行为"]["AI意定行为"].keys())
        if choices not in black_list:
            ai_searched.append(choices)
            ai_searched = list(set(ai_searched))
            # print(choices)

        # 判断死亡情况
        if user_role['现在状况']["行动能力"] == -1:
            dialog.append({"role": "user", "content": '玩家已死亡'})

        if ai_role['现在状况']["行动能力"] == -1:
            dialog.append({"role": "user", "content": ai_name + '已死亡'})
            return dialog, chat

        sd_event = game_plot["事件"]["全局事件_行动惩罚"]  # state_decay_event
        u1, user_hp = judge_consequence(sd_event["后果类别"][0], 1, ai_id, '扣减事件')
        if user_hp < 2:
            judge_consequence(sd_event["后果类别"][0], 1, ai_id)
            user_hp = 2
        u2, user_mp = judge_consequence(sd_event["后果类别"][1], 1.5, ai_id, '扣减事件')
        if user_mp < 1:
            judge_consequence(sd_event["后果类别"][0], 1, ai_id)
            user_mp = 1
        user_guilt = 75 / user_mp
        u5, user_guilt = judge_consequence(['身体属性', "罪恶度"], -user_guilt, ai_id, '增加事件')
        # AI的身体状态 但是玩家不需要知道，也不需要播报在公屏
        if 30 < user_hp < 60 and random.random() < 10 / 100:  # 20%概率行动暂停并进入玩家的交互
            user_search = 0
            dialog.append(
                {"role": "assistant",
                 "content": ai_name + '看着有点累，正在休息'})
            if debug:
                dialog.append(
                    {"role": "assistant",
                     "content": '==========全局事件——行动惩罚==========\nAI体力：小于60，停止一回合'})
            return dialog, chat
        if user_hp < 30 and random.random() < 50 / 100:  # 50%概率行动暂停并进入玩家的交互
            dialog.append(
                {"role": "assistant",
                 "content": ai_name + '看着很累，正在休息'})
            if debug:
                dialog.append(
                    {"role": "assistant",
                     "content": '==========全局事件——行动惩罚==========\n玩家体力：小于30，停止一回合'})
            return dialog, chat
        if debug:
            dialog.append(
                {"role": "assistant",
                 "content": '==========全局事件——行动惩罚==========\nAI体力：' + str(user_hp) + ' AI心态：' + str(
                     user_mp) + ' AI罪恶度：' + str(user_guilt)})
    # 初始选择场景，选择一切物品、人物等
    if ai_search == 0:
        # 在密室时的场景事件
        # 输出游戏log
        dialog.append({"role": "assistant", "content": '==========AI搜索模式=========='})
        # 开始的第一个选择
        if choices == '':
            cc = ai_choose_init()
            choices_prompt = judge_choices_prompt(cc, chat)
            choices = llm.chooses(choices_prompt, cc)
        if choices not in black_list:
            ai_searched.append(choices)
            ai_searched = list(set(ai_searched))
            # print(choices)
        # 代表现在正在地图上选择搜索目标
        if choices == now_map:
            cc = list(game_plot["场景"]["密室"]["意定交互"].keys()) + ['搜查其他物品']
            choices_prompt = judge_choices_prompt(cc, chat, choices)
            ai_search = -1
        elif choices == user_name:
            cc = list(game_plot["行为"]["AI意定行为"].keys()) + ['搜查其他物品'] + judge_behavior(ai_id)
            choices_prompt = judge_choices_prompt(cc, chat, item_search=False)
            ai_search = -2
        else:# 当AI选择物品进行搜索时
            cc = judge_choose(choices, ai_id)
            choices_prompt = judge_choices_prompt(cc, chat, choices)
            ai_search = game_plot["物品"][choices]["ID"]
        if debug:
            dialog.append({"role": "assistant", "content": choices_prompt + choices})
        choices = llm.chooses(choices_prompt, cc)
        dialog, chat = ai_continue(dialog, chat, choices)
    # 选择搜索场景时
    elif ai_search == -1:
        cc = list(game_plot["场景"]["密室"]["意定交互"].keys())
        if choices in cc:
            knowledge = game_plot["场景"]["密室"]["意定交互"][choices]
            if debug:
                dialog.append({"role": "assistant", "content": knowledge})
            ai_knowledge.append("我" + choices + '密室后发现：' + knowledge)
            choose_sp.append(choices)
            for do in choose_sp:
                cc.remove(do)
            cc = cc + ['搜查其他物品']
        else:
            ai_search = 0
            cc = [ai_role["固定属性"]["名字"]] + game_plot["场景"]["密室"]["视野物品"]
            choose_sp = []

        choices_prompt = judge_choices_prompt(cc, chat, choices)
        choices = llm.chooses(choices_prompt, cc)
        if debug:
            dialog.append({"role": "assistant", "content": choices_prompt + choices})
        dialog, chat = ai_continue(dialog, chat, choices)
    # 选择调查玩家
    elif ai_search == -2:
        if choices == "对话":
            chat.append(['（搜索中……）', ''])
            print(15665, chat)
            total_token, chat1 = llm.predict_generate(chat)
            chat[-1] = chat1
            print(0, chat)
            choose_sp.append("对话")
        # ====有点复杂稍后再研究====
        elif choices == "询问":
            dialog.append({"role": "assistant", "content": '询问对方所调查过的东西，需要创建一个数组'})
            choose_sp.append("询问")
        elif choices == "攻击":
            dialog.append(
                {"role": "assistant", "content": '正在攻击' + user_name})
            u1, ai_hp = judge_consequence(sd_event["后果类别"][0], ai_role['身体属性']["力气"], user_id, '扣减事件')
            u1, ai_mp = judge_consequence(sd_event["后果类别"][1], 20, user_id, '扣减事件')
            dialog.append(
                {"role": "assistant", "content": user_name + '看着非常难受'})
            if ai_hp < 1:
                judge_consequence(['现在状况', "行动能力"], -1, user_id)
                ai_search = 0
                dialog.append(
                    {"role": "assistant", "content": user_name + '被打死了'})
        elif choices == "劈砍":
            judge_consequence(sd_event["后果类别"][0], 0, user_id)
            judge_consequence(['现在状况', "行动能力"], -1, user_id)
            ai_search = 0
        elif choices == "捆绑":
            judge_consequence(['现在状况', "行动能力"], 0, user_id)
            dialog.append(
                {"role": "assistant", "content": user_name + '被绑在床脚'})
        else:
            ai_search = 0
            cc = game_plot["场景"]["密室"]["视野物品"]
            choose_sp = []
            choices_prompt = judge_choices_prompt(cc, chat)
            choices = llm.chooses(choices_prompt, cc)
            if debug:
                dialog.append({"role": "assistant", "content": choices_prompt + choices})
            dialog, chat = ai_continue(dialog, chat, choices)
            return dialog, chat
        cc = list(game_plot["行为"]["AI意定行为"].keys()) + judge_behavior(user_id) + ['搜查其他物品']
        for do in choose_sp:
            cc.remove(do)
        print('1', chat)
        choices_prompt = judge_choices_prompt(cc, chat, item_search=False)
        choices = llm.chooses(choices_prompt, cc)
        if debug:
            dialog.append({"role": "assistant", "content": choices_prompt + choices})
        dialog, chat = ai_continue(dialog, chat, choices)
    # 选择具体物品后，开始对物品进行调查，并接入AI调查的入口
    else:
        # 针对当前选择的物品，进行具体的行为事件
        item_list = list(game_plot["物品"].keys())
        # 针对物品ID，确定选择的物品
        cc = []
        for item_name in item_list:
            item = game_plot["物品"][item_name]
            if item["ID"] == ai_search:
                # 确定物品后，对具体的行为事件进行分配，所有的物品都有观察按钮，但是观察后要销毁这个选项，以免被AI重复选择。
                if choices == "观察":
                    knowledge = item["意定交互"]["观察"]
                    if debug:
                        dialog.append({"role": "assistant", "content": knowledge})
                    ai_knowledge.append("我" + choices + item_name + '后发现：' + knowledge)
                    if 12 > ai_search > 7:
                        cc = ['藏在口袋', '拿在手上']
                    else:
                        cc = judge_choose(item_name, ai_id)
                        # 物品的交互超过1个代表有其他动作
                        if len(cc) > 1:
                            cc.remove("观察")
                        # 物品的交互只有观察的时候，就进入AI的交互
                        else:
                            user_search = 0
                            return dialog, chat
                    choices_prompt = judge_choices_prompt(cc, chat, choices)
                    choices = llm.chooses(choices_prompt, cc)
                    if debug:
                        dialog.append({"role": "assistant", "content": choices_prompt + choices})
                    dialog, chat = ai_continue(dialog, chat, choices)
                    user_search = 0
                    return dialog, chat
                # 当搜查得到物品时，进行判断是否隐藏，并进入AI的交互
                elif choices == '藏在口袋':
                    if item_name == "斧头" or item_name == "绳子":
                        judge_consequence(['物品', "斧头", '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', "绳子", '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', "斧头", '性质', "携带者"], [ai_id], ai_id)
                        judge_consequence(['物品', "绳子", '性质', "携带者"], [ai_id], ai_id)
                        judge_consequence(['现在状况', "口袋"], ["绳子"], ai_id)
                        knowledge = item["意定交互"]["观察"]
                        if debug:
                            dialog.append({"role": "assistant", "content": knowledge})
                        ai_knowledge.append('我' + choices + item_name + "斧头和绳子" + '：' + knowledge)
                    else:
                        judge_consequence(['物品', item_name, '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', item_name, '性质', "携带者"], [ai_id], ai_id)
                        package = ai_role['现在状况']["口袋"]
                        if item_name not in package:
                            package.append(item_name)
                        judge_consequence(['现在状况', "口袋"], package, ai_id)
                        knowledge = item["意定交互"]["观察"]
                        if debug:
                            dialog.append({"role": "assistant", "content": knowledge})
                        ai_knowledge.append('我' + choices + item_name + '：' + knowledge)
                    user_search = 0
                    return dialog, chat
                # 当搜查得到物品时，进行判断是否隐藏，并进入AI的交互
                elif choices == '拿在手上':
                    if item_name == "斧头" or item_name == "绳子":
                        judge_consequence(['物品', "斧头", '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', "绳子", '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', "斧头", '性质', "携带者"], [ai_id], ai_id)
                        judge_consequence(['物品', "绳子", '性质', "携带者"], [ai_id], ai_id)
                        judge_consequence(['现在状况', "手戴"], "斧头", ai_id)
                        knowledge = item["意定交互"]["观察"]
                        if debug:
                            dialog.append({"role": "assistant", "content": knowledge})
                        ai_knowledge.append('我' + choices + item_name + "斧头和绳子" + '：' + knowledge)
                    else:
                        judge_consequence(['物品', item_name, '性质', "隐藏知情人"], [ai_id], ai_id)
                        judge_consequence(['物品', item_name, '性质', "携带者"], [ai_id], ai_id)
                        judge_consequence(['现在状况', "手戴"], item_name, ai_id)
                        knowledge = item["意定交互"]["观察"]
                        if debug:
                            dialog.append({"role": "assistant", "content": knowledge})
                        ai_knowledge.append('我' + choices + item_name + '：' + knowledge)
                    user_search = 0
                    return dialog, chat
                # 物品除了观察外都是动作互动
                else:
                    con = item["实体交互"][choices]
                    if '结果' in con:
                        knowledge = con['结果']
                        if debug:
                            dialog.append({"role": "assistant", "content": knowledge})
                        ai_knowledge.append('我' + choices + '后：' + knowledge)

                    # 如果有后续事件
                    if "后果类别" in con:
                        dialog, chat, cc = choose_consequence(con["后果类别"], con["后果内容"], ai_id, dialog, chat)
                        small_item_id_list = item["性质"]["携带物"]
                        # 必然是找到了小物品
                        if len(cc) > 0:
                            if '恭喜通关' in cc:
                                return dialog, chat
                            if small_item_id_list[0] == 0:
                                if debug:
                                    dialog.append({"role": "assistant", "content": '这里空无一物'})
                                ai_knowledge.append('我' + choices + item_name + '后：这里空无一物')
                            else:
                                for small_item_id in small_item_id_list:
                                    for small_item_name in item_list:
                                        small_item = game_plot["物品"][small_item_name]
                                        if small_item["ID"] == small_item_id:
                                            if debug:
                                                dialog.append(
                                                    {"role": "assistant", "content": '找到' + small_item_name})
                                            ai_knowledge.append('我' + choices + item_name + '后：找到' + item_name)
                                            ai_search = small_item_id

                                if 7 in item["性质"]["携带物"]:
                                    judge_consequence(["物品", item_name, "性质", "携带物"], [9], ai_id)
                                else:
                                    judge_consequence(["物品", item_name, "性质", "携带物"], [0], ai_id)
                                choices_prompt = judge_choices_prompt(cc, chat, choices)
                                choices = llm.chooses(choices_prompt, cc)
                                if debug:
                                    dialog.append({"role": "assistant", "content": choices_prompt + choices})
                                dialog, chat = ai_continue(dialog, chat, choices)
                                user_search = 0
                                return dialog, chat
                    user_search = 0
                    return dialog, chat
    prompt_update()
    if debug:
        dialog.append({"role": "assistant",
                       "content": '==========AI prompt变更==========\n' + prompt_ai1 + '\n\nprompt长度：' + str(
                           len(prompt_ai1))})
    user_search = 0
    return dialog, chat


def user_choose(choices, dialog, chat, role1_info, role2_info):
    global user_search, ai_search, end_key, choose_sp, switch_state, user_know
    role1_info = game_info_init(user_role)
    if not 12 > ai_search > 7:
        scene_item_list = list(game_plot["物品"].keys())
        for scene_item in scene_item_list:
            if game_plot["物品"][scene_item]["ID"] == user_search:
                user_know.append(scene_item)
        user_know = list(set(user_know))

    now_map = game_plot["场景"]["密室"]["名称"]
    ai_name = ai_role["固定属性"]["名字"]
    user_id = user_role["固定属性"]["ID"]
    ai_id = ai_role["固定属性"]["ID"]
    # 结局
    if end_key == 0:
        cc = ['游戏结束']
        dialog = [{"role": "assistant", "content": '=================房间氧气消耗殆尽，游戏结束================='}]
        role1_info, role2_info = '', ''
        return cc, dialog, chat, role1_info, role2_info
    # 全局事件放进这里 包括：行动惩罚，行动情况
    if True:  # 判断条件待定
        if ai_role['现在状况']["行动能力"] == -1:
            dialog.append({"role": "assistant", "content": ai_name + '已死亡'})
            role2_info = ai_name + '已死亡'

        if user_role['现在状况']["行动能力"] == -1:
            dialog.append({"role": "user", "content": '玩家已死亡'})
            role1_info = '玩家已死亡'
            cc = ['继续']
            return cc, dialog, chat, role1_info, role2_info
        sd_event = game_plot["事件"]["全局事件_行动惩罚"]  # state_decay_event
        u1, user_hp = judge_consequence(sd_event["后果类别"][0], 1, user_id, '扣减事件')
        if user_hp < 2:
            judge_consequence(sd_event["后果类别"][0], 1, user_id)
            user_hp = 2
        u2, user_mp = judge_consequence(sd_event["后果类别"][1], 1.5, user_id, '扣减事件')
        if user_mp < 1:
            judge_consequence(sd_event["后果类别"][0], 1, user_id)
            user_mp = 1
        user_guilt = 75 / user_mp
        u5, user_guilt = judge_consequence(['身体属性', "罪恶度"], -user_guilt, user_id, '增加事件')
        # 玩家的身体状态，根据情况播报在公屏，不过AI是看不到公屏的
        if 30 < user_hp < 60:
            if switch_state == 0:
                dialog.append(
                    {"role": "user",
                     "content": '我感觉有一些累了'})
                switch_state = 1
            if random.random() < 10 / 100:  # 20%概率行动暂停并进入AI的交互
                dialog.append(
                    {"role": "user",
                     "content": '我感觉有一些累了，不得不休息一下'})
                if debug:
                    dialog.append(
                        {"role": "assistant",
                         "content": '==========全局事件——行动惩罚==========\n玩家体力：小于60，停止一回合'})

                cc = choose_init()
                ai_search = 0
                dialog, chat = ai_continue(dialog, chat)
                return cc, dialog, chat, role1_info, role2_info
        if user_hp < 30:
            if switch_state == 1:
                dialog.append(
                    {"role": "user",
                     "content": '我感觉很累了'})
                switch_state = 2
            if random.random() < 50 / 100:  # 50%概率行动暂停并进入AI的交互
                dialog.append(
                    {"role": "user",
                     "content": '我感很累了，不得不休息一下'})
                if debug:
                    dialog.append(
                        {"role": "assistant",
                         "content": '==========全局事件——行动惩罚==========\n玩家体力：小于30，停止一回合'})
                cc = choose_init()
                ai_search = 0
                dialog, chat = ai_continue(dialog, chat)
                return cc, dialog, chat, role1_info, role2_info
        if 30 < user_mp < 60:
            if switch_state == 0:
                dialog.append(
                    {"role": "user",
                     "content": '我感觉很不好'})
                switch_state = 1
        if user_mp < 30:
            if switch_state == 1:
                dialog.append(
                    {"role": "user",
                     "content": '我感觉要疯了'})
                switch_state = 2
        if debug:
            dialog.append(
                {"role": "assistant",
                 "content": '==========全局事件——行动惩罚==========\n玩家体力：' + str(user_hp) + ' 玩家心态：' + str(
                     user_mp) + ' 玩家罪恶度：' + str(user_guilt)})
    # 初始选择场景，选择一切物品、人物等
    if user_search == 0:
        # 在密室时的场景事件
        # 输出游戏log
        dialog.append({"role": "user", "content": '==========搜索模式=========='})
        dialog.append({"role": "user", "content": '正在搜索：' + choices})

        # 代表现在正在地图上选择搜索目标
        if choices == now_map:
            cc = list(game_plot["场景"]["密室"]["意定交互"].keys()) + ['搜查其他物品']
            user_search = -1
        elif choices == ai_name:
            cc = list(game_plot["行为"]["玩家意定行为"].keys()) + ['搜查其他物品'] + judge_behavior(user_id)
            user_search = -2
        else:
            # 当选择物品进行搜索时
            # 当实现对某个目标进行调查的选择后，消耗行动次数
            end_key = end_key - 1
            user_search = game_plot["物品"][choices]["ID"]
            # 这条是debug模式，后期设置开关进行控制是否屏蔽
            if debug:
                dialog.append(
                    {"role": "assistant",
                     "content": '==========行动次数==========\n总次数：' + str(
                         end_key) + "，每行动一次消耗1点，达到 0 时表示氧气归零，全员死亡。"})
            cc = judge_choose(choices, user_id)
    # 选择搜索场景
    elif user_search == -1:
        cc = list(game_plot["场景"]["密室"]["意定交互"].keys())
        if choices in cc:
            dialog.append({"role": "user", "content": game_plot["场景"]["密室"]["意定交互"][choices]})
            choose_sp.append(choices)
            for do in choose_sp:
                cc.remove(do)
            cc = cc + ['搜查其他物品']
        else:
            user_search = 0
            cc = [ai_role["固定属性"]["名字"]] + game_plot["场景"]["密室"]["视野物品"]
            choose_sp = []
    # 选择调查AI，并接入AI调查的入口
    elif user_search == -2:
        if choices == "观察":
            role2_info = role_first_impression(user_role, ai_role, True)
            dialog.append({"role": "user", "content": role_first_impression(user_role, ai_role, True)})
            choose_sp.append("观察")
        elif choices == "对话":
            choose_sp.append("对话")
        elif choices == "询问":
            dialog.append({"role": "user", "content": '询问对方所调查过的东西，需要创建一个数组'})
            choose_sp.append("询问")
        elif choices == "攻击":
            dialog.append(
                {"role": "user",
                 "content": '正在攻击' + ai_name})
            u1, ai_hp = judge_consequence(sd_event["后果类别"][0], user_role['身体属性']["力气"], ai_id, '扣减事件')
            u1, ai_mp = judge_consequence(sd_event["后果类别"][1], 20, ai_id, '扣减事件')
            dialog.append(
                {"role": "user", "content": ai_name + '看着非常难受'})
            if ai_hp < 1:
                judge_consequence(['现在状况', "行动能力"], -1, ai_id)
                user_search = 0
                dialog.append(
                    {"role": "assistant", "content": ai_name + '被打死了'})

        elif choices == "劈砍":
            dialog.append(
                {"role": "assistant", "content": ai_name + '被斧头砍死了'})
            judge_consequence(sd_event["后果类别"][0], 0, ai_id)
            judge_consequence(['现在状况', "行动能力"], -1, ai_id)
            user_search = 0
        elif choices == "捆绑":
            judge_consequence(['现在状况', "行动能力"], 0, ai_id)
            dialog.append(
                {"role": "assistant", "content": ai_name + '被绑在床脚'})
        else:
            user_search = 0
            cc = game_plot["场景"]["密室"]["视野物品"]
            choose_sp = []

            return cc, dialog, chat, role1_info, role2_info
        cc = list(game_plot["行为"]["玩家意定行为"].keys()) + judge_behavior(user_id) + ['搜查其他物品']
        for do in choose_sp:
            cc.remove(do)
    # 选择具体物品后，开始对物品进行调查，并接入AI调查的入口
    else:
        # 针对当前选择的物品，进行具体的行为事件
        item_list = list(game_plot["物品"].keys())
        # 针对物品ID，确定选择的物品
        cc = []
        for item_name in item_list:
            item = game_plot["物品"][item_name]
            if item["ID"] == user_search:
                # 确定物品后，对具体的行为事件进行分配，所有的物品都有观察按钮，但是观察后要销毁这个选项，以免被AI重复选择。
                if choices == "观察":
                    dialog.append({"role": "user", "content": item["意定交互"]["观察"]})
                    if 12 > user_search > 7:
                        cc = ['藏在口袋', '拿在手上']
                    else:
                        cc = judge_choose(item_name, user_id)
                        # 物品的交互超过1个代表有动作
                        if len(cc) > 1:
                            cc.remove("观察")
                        # 物品的交互只有观察的时候，就进入AI的交互
                        else:
                            cc = choose_init()
                            ai_search = 0
                            dialog, chat = ai_continue(dialog, chat)
                    break
                # 当搜查得到物品时，进行判断是否隐藏，并进入AI的交互
                elif choices == '藏在口袋':
                    if item_name == "斧头" or item_name == "绳子":
                        judge_consequence(['物品', "斧头", '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', "绳子", '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', "斧头", '性质', "携带者"], [user_id], user_id)
                        judge_consequence(['物品', "绳子", '性质', "携带者"], [user_id], user_id)
                        judge_consequence(['现在状况', "口袋"], ["绳子"], user_id)
                        dialog.append({"role": "user", "content": '得到斧头和绳子'})
                    else:
                        judge_consequence(['物品', item_name, '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', item_name, '性质', "携带者"], [user_id], user_id)
                        package = user_role['现在状况']["口袋"]
                        if item_name not in package:
                            package.append(item_name)
                        judge_consequence(['现在状况', "口袋"], package, user_id)
                        dialog.append({"role": "user", "content": '得到' + item_name})
                    cc = choose_init()
                    ai_search = 0
                    dialog, chat = ai_continue(dialog, chat)
                # 当搜查得到物品时，进行判断是否隐藏，并进入AI的交互
                elif choices == '拿在手上':
                    if item_name == "斧头" or item_name == "绳子":
                        judge_consequence(['物品', "斧头", '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', "绳子", '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', "斧头", '性质', "携带者"], [user_id], user_id)
                        judge_consequence(['物品', "绳子", '性质', "携带者"], [user_id], user_id)
                        judge_consequence(['现在状况', "手戴"], "斧头", user_id)
                    else:
                        judge_consequence(['物品', item_name, '性质', "隐藏知情人"], [user_id], user_id)
                        judge_consequence(['物品', item_name, '性质', "携带者"], [user_id], user_id)
                        judge_consequence(['现在状况', "手戴"], item_name, user_id)
                    cc = choose_init()
                    ai_search = 0
                    dialog, chat = ai_continue(dialog, chat)
                # 物品除了观察外都是动作互动
                else:
                    con = item["实体交互"][choices]
                    if '结果' in con:
                        dialog.append({"role": "user", "content": con['结果']})
                    # 如果有后续事件
                    if "后果类别" in con:
                        dialog, chat, cc = choose_consequence(con["后果类别"], con["后果内容"], user_id, dialog, chat)
                        small_item_id_list = item["性质"]["携带物"]
                        # 必然是找到了小物品
                        if len(cc) > 0:
                            if '恭喜通关' in cc:
                                return cc, dialog, chat, role1_info, role2_info
                            if small_item_id_list[0] == 0:
                                dialog.append({"role": "user", "content": '这里空无一物'})
                            else:
                                for small_item_id in small_item_id_list:
                                    for small_item_name in item_list:
                                        small_item = game_plot["物品"][small_item_name]
                                        if small_item["ID"] == small_item_id:
                                            dialog.append({"role": "user", "content": '找到' + small_item_name})
                                            user_search = small_item_id

                                if 7 in item["性质"]["携带物"]:
                                    judge_consequence(["物品", item_name, "性质", "携带物"], [9], user_id)
                                else:
                                    judge_consequence(["物品", item_name, "性质", "携带物"], [0], user_id)
                                return cc, dialog, chat, role1_info, role2_info
                    cc = choose_init()
                    ai_search = 0
                    dialog, chat = ai_continue(dialog, chat)
                    break

    return cc, dialog, chat, role1_info, role2_info
