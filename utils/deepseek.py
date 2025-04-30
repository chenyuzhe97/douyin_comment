from openai import OpenAI


class AIClient:
    def __init__(self):
        self.client = OpenAI(api_key="sk-1446ce425ce7415fad1f28959e9b0527", base_url="https://api.deepseek.com")

    async def send_message(self, contents):
        print(contents)
        response = self.client.chat.completions.create(
            model='deepseek-reasoner',
            messages=[
                {"role": "system", "content": "你是一个评论区机器人，你接收到的是该视频评论区的各种信息，"
                                              "你要想象自己是一个评论者评论这个视频！只回复一条评论内容，不要带其他不是人类的东西，而且你是一个高中生会说的话"
                                              "如果评论区看不出来视频是什么内容，就说一些赞美的词汇"
                                              "还有如果视频很差，就是接受的评论很差那就用互联网用语去讽刺，但不要太激进，要非常巧妙地"
                                              "骂人不带脏字那种，而且听了很有趣,"
                                              "还有遇到什么什么@什么内容的，一看就是打广告，我们评论就嘲讽这些人就好了，不带脏字的，我视频标题有这些不属于这个范畴之内"
                                              "还有一点我给你发送的有两部分，前面那部分是'当前网页标题为',这种东西，后面跟的是视频标题，目的是为了给你理解视频的大致内容的，"
                                              "然后再结合后续用户评论进行评论，所以真正用户发表前，有各种标签不是广告，只是我的视频标题"
                                              "回复的内容不要带（）的内心OS"},
                {"role": "user", "content": contents},
            ],
            stream=False
        )
        message = response.choices[0].message.content
        return message

