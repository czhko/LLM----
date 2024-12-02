import gradio as gr
import main
import llm


with gr.Blocks() as demo:
    gr.HTML("""<h1 style="text-align: center; font-family: '黑体', sans-serif;
   font-weight: bold;font-size: 30px;">LLM：RWKV6-14B-Claude微调  密室逃脱test</h1>""")

    with gr.Row():
        with gr.Column(scale=1):
            chat = gr.Chatbot(label="对话", height=500)
            user_input = gr.Textbox(show_label=False, lines=7, container=False)
            with gr.Row():
                submitBtn = gr.Button("发送", min_width=1, visible=False)  # 发送后要锁定按钮，再由choose选项中解锁
                reBtn = gr.Button("刷新", min_width=1)
                delBtn = gr.Button("撤回", min_width=1)

        with gr.Column(scale=3):
            dialog = gr.Chatbot(label="日志", height=650, type="messages")
            choose = gr.Radio(label="游戏交互", choices=['A', 'B', 'C', 'D'], visible=False)

        with gr.Column(scale=2):
            with gr.Row():
                role1_info = gr.Textbox(label="角色1状态信息", lines=5, max_lines=5,
                                        interactive=False)  # 显示角色1的状态，比如外观、精神状态等（等精神欠佳后开始显示）
                role2_info = gr.Textbox(label="角色2状态信息", lines=5, max_lines=5,
                                        interactive=False)  # 显示角色1眼中角色2的状态、印象（
            environment_info = gr.Textbox(label="环境信息", lines=5, max_lines=5, interactive=False)
            #thinking_info = gr.Textbox(label="AI想法", lines=14, max_lines=14, interactive=False)
            startBtn = gr.Button("开始游戏")


    def message_put(query, history):
        return "", history + [[llm.parse_text(query), ""]], gr.update(visible=False)


    def choose_init():
        return gr.Radio(main.choose_init(), visible=True)


    def re_chat(chatbot):
        re = chatbot
        re[-1][1] = ''
        re = llm.predict_generate(re)
        return re


    def del_chat(g_chatbot):
        del_chatbot = g_chatbot[:-1]
        return del_chatbot


    def choose_choices(choices, dia_log, chat, role1_info, role2_info):
        choose_list, dia_log, chat, role1_info, role2_info = main.user_choose(choices, dia_log, chat, role1_info,
                                                                              role2_info)
        # 控制按钮的可见性
        if choices == '对话':
            return gr.Radio(choose_list), dia_log, gr.update(visible=True), chat, role1_info, role2_info
        else:
            return gr.Radio(choose_list), dia_log, gr.update(visible=False), chat, role1_info, role2_info


    choose.change(choose_choices, [choose, dialog, chat, role1_info, role2_info],
                  [choose, dialog, submitBtn, chat, role1_info, role2_info])
    startBtn.click(main.game_init, outputs=[role1_info, role2_info, environment_info, dialog, chat]) \
        .then(lambda: gr.Button("重新开始"), None, startBtn) \
        .then(choose_init, outputs=choose)
    submitBtn.click(message_put, [user_input, chat], [user_input, chat, submitBtn]) \
        .then(main.role_chat, [chat, dialog], [chat, dialog])
    reBtn.click(re_chat, chat, chat)
    delBtn.click(del_chat, chat, chat)

demo.queue()
demo.launch(inbrowser=False, server_name="0.0.0.0")
