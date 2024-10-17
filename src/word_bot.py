from discord import Client, MessageType, Intents, Message
import os
from copy import deepcopy
from src.english_processing import get_word_of_the_day, shortest_available_stem

token = os.environ['TOKEN']
channel_id = int(os.environ['CHANNEL_ID'])

EMOJI_ID = 1259346961627086918

intents = Intents.default()
intents.message_content = True

class WordOfTheDayInfo:
    def __init__(self, msg_id, user_id, date_time):
        self.msg_id = msg_id
        self.user_id = user_id
        self.date_time = date_time

class WordBot(Client):

    def _determine_word_of_the_day(self, message: Message) -> str | WordOfTheDayInfo:
        word = get_word_of_the_day(message.content)
        if word is not None:
            stem = shortest_available_stem(word)

            if stem in self._words:
                return self._words[stem]
            else:
                return stem
                
    async def on_ready(self):
        self._words = {}
        wotd_channel = self.get_channel(channel_id)
        async for message in wotd_channel.history(limit=None, oldest_first=True):
            if message.author != self.user.id and message.type == MessageType.default:
                res = self._determine_word_of_the_day(message)
                if type(res) is str:
                    self._words[res] = WordOfTheDayInfo(message.id, message.author.id, deepcopy(message.created_at))

    async def on_message(self, message: Message):

        if message.channel.id == channel_id and message.type == MessageType.default: #author's note: surely there's a better way.
            
            #don't bother checking the bot's own messages
            if message.author.id == self.user.id:
                return
            
            res = self._determine_word_of_the_day(message)
            if type(res) is str:
                if res:
                    self._words[res] = WordOfTheDayInfo(message.id, message.author.id, deepcopy(message.created_at))
                    await message.add_reaction(self.get_emoji(EMOJI_ID))
            elif res is not None:
                original_message = await message.channel.fetch_message(res.msg_id)
                await message.reply(":bangbang:Recycled word alert:bangbang:\n {} already said [{}]({})"
                                        .format(original_message.author.mention, original_message.content, original_message.jump_url))
                
client = WordBot(intents=intents)
client.run(token)
            
        
        