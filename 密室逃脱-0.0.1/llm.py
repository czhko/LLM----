import requests
import main
from datetime import datetime

# 局域网：192.168.1.2
api = 'http://192.168.1.2:65530/api/oai/v1/'


def get_diff_second(start_time, end_time):
    diff = end_time - start_time
    second = round(diff.total_seconds(), 2)
    return second


# 让AI进行倾向选择
def chooses(txt, choices):
    ts = datetime.now()
    chooses_txt = {"choices": choices + ['我他妈的到底为什么不选傻逼！！！'],  # 用一个毫无关联的选项提高其他选择的成功率
                   "input": [txt],
                   "state": "00000000-0000-0000-0000-000000000000"}
    r = requests.post(api + "chooses", json=chooses_txt)
    choose_list = r.json()['data']
    # print(choose_list)
    for i in choose_list:
        if i["rank"] == 0:
            f = i["choice"]
            if f == '我他妈的到底为什么不选傻逼！！！':
                f = chooses(txt, choices)

            te = datetime.now()
            print('===========Embed进行倾向性选择，长度：', len(txt), '个字，用时：', get_diff_second(ts, te), 's', f)
            return f


# AI续写
def generate(prompt, t_top=0.5, temp=1, f_penalty=0.3, p_penalty=0.3, m_token=1000):
    ts = datetime.now()
    chat_message = {"frequency_penalty": f_penalty, "max_tokens": m_token, "presence_penalty": p_penalty,
                    "temperature": temp, "top_p": t_top, "prompt": prompt,
                    "stop": ["\n\n", '\nUser:', '\nAssistant:']}
    r = requests.post(api + "completions", json=chat_message)
    te = datetime.now()
    txt, i = r.json()['choices'][0]['text'], r.json()['usage']['total']
    print('===========Ai续写，长度：', len(prompt), '个字', i, '个token，用时：', get_diff_second(ts, te), 's', txt)
    return txt, i


# AI对话
def chat(messages, t_top=0.5, temp=1, f_penalty=0.3, p_penalty=0.3, m_token=1000):
    ts = datetime.now()
    chat_message = {"frequency_penalty": f_penalty, "max_tokens": m_token, "presence_penalty": p_penalty,
                    "temperature": temp, "top_p": t_top, "messages": messages,
                    "stop": ["\n\n", '\nUser:', '\nAssistant:'],
                    "names": {"assistant": "Assistant", "user": "User"}}

    r = requests.post(api + "chat/completions", json=chat_message)
    te = datetime.now()
    print('===========Ai对话，长度：', len(messages), '句，用时：', get_diff_second(ts, te), 's')
    return r.json()['choices'][0]['message']['content']


# 格式化文本，保证输入字符安全性
def parse_text(text):
    lines = text.split("\n")
    lines = [line for line in lines if line != ""]
    count = 0
    for i, line in enumerate(lines):
        if "```" in line:
            count += 1
            items = line.split('`')
            if count % 2 == 1:
                lines[i] = f'<pre><code class="language-{items[-1]}">'
            else:
                lines[i] = f'<br></code></pre>'
        else:
            if i > 0:
                if count % 2 == 1:
                    line = line.replace("`", r"\`")
                    line = line.replace("<", "&lt;")
                    line = line.replace(">", "&gt;")
                    line = line.replace(" ", "&nbsp;")
                    line = line.replace("*", "&ast;")
                    line = line.replace("_", "&lowbar;")
                    line = line.replace("-", "&#45;")
                    line = line.replace(".", "&#46;")
                    line = line.replace("!", "&#33;")
                    line = line.replace("(", "&#40;")
                    line = line.replace(")", "&#41;")
                    line = line.replace("$", "&#36;")
                lines[i] = "<br>" + line
    text = "".join(lines)

    return text


def predict_chat(history):
    # 将使用调整后的印象进行输出
    prompt = main.prompt_ai1
    messages = [{"role": "Assistant", "content": prompt}]
    # 分解chatbot进行对话
    for idx, (user_msg, model_msg) in enumerate(history):
        if idx == len(history) - 1 and not model_msg:
            messages.append({"role": "User", "content": user_msg})
            break
        if user_msg:
            messages.append({"role": "User", "content": user_msg})
        if model_msg:
            messages.append({"role": "Assistant", "content": model_msg})

    history[-1][1] = chat(messages)
    return history


def predict_generate(history):
    prompt = main.prompt_ai1
    user_name = main.user_role["固定属性"]["名字"]
    for idx, (user_msg, model_msg) in enumerate(history):
        if idx == len(history) - 1 and not model_msg:
            prompt = prompt + user_name + "说: " + user_msg + '\n\n'
            break
        if user_msg:
            if user_msg != '（搜索中……）':
                prompt = prompt + user_name + "说: " + user_msg + '\n\n'
        if model_msg:
            prompt = prompt + "我说: " + model_msg + '\n\n'  # 用续写加入想法    think, i = llm_generate(prompt + "我在心理想: ")
    speak, i = generate(prompt + "\n\n" + "我说: ")

    history[-1][1] = speak

    return history
