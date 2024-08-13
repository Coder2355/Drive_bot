import os, time, asyncio

from telethon import events, Button
from telethon.tl.types import DocumentAttributeVideo
from ethon.telefunc import fast_download
from ethon.pyfunc import video_metadata

from .. import Drone

from trimmer import trim_audio


@Drone.on(events.NewMessage(incoming=True,func=lambda e: e.is_private))
async def compin(event):
    if event.is_private:
        media = event.media
        if media:
            audio = event.file.mime_type
            if 'audio' in audio:
                await event.reply("📽",
                            buttons=[
                                 Button.inline("TRIM", data="trim_audio")
                            ])



  @Drone.on(events.callbackquery.CallbackQuery(data="trim_audio"))
async def atrim(event):
    button = await event.get_message()
    msg = await button.get_reply_message()  
    await event.delete()
    markup = event.client.build_reply_markup(Button.force_reply())
    async with Drone.conversation(event.chat_id) as conv: 
        try:
            xx = await conv.send_message("send me the start time of the video you want to trim from as a reply to this. \n\nIn format hh:mm:ss , for eg: `01:20:69` ", buttons=markup)
            x = await conv.get_reply()
            st = x.text
            await xx.delete()                    
            if not st:               
                return await xx.edit("No response found.")
        except Exception as e: 
            print(e)
            return await xx.edit("An error occured while waiting for the response.")
        try:
            xy = await conv.send_message("send me the end time of the video you want to trim till as a reply to this.  \n\nIn format hh:mm:ss , for eg: `01:20:69` ", buttons=markup)
            y = await conv.get_reply()
            et = y.text
            await xy.delete()                    
            if not et:                
                return await xy.edit("No response found.")
        except Exception as e: 
            print(e)
            return await xy.edit("An error occured while waiting for the response.")
        await trim_audio(event, msg, st, et)
