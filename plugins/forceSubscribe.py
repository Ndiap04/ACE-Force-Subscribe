import time
import logging
from Config import Config
from pyrogram import Client, filters
from sql_helpers import forceSubscribe_sql as sql
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

logging.basicConfig(level=logging.INFO)

static_data_filter = filters.create(lambda _, __, query: query.data == "onUnMuteRequest")
@Client.on_callback_query(static_data_filter)
async def _onUnMuteRequest(client, cb):
  user_id = cb.from_user.id
  chat_id = cb.message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    channel = chat_db.channel
    chat_member = await client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
      if chat_member.restricted_by.id == (await client.get_me()).id:
          try:
            await client.get_chat_member(channel, user_id)
            await client.unban_chat_member(chat_id, user_id)
            if cb.message.reply_to_message.from_user.id == user_id:
              await cb.message.delete()
          except UserNotParticipant:
            await client.answer_callback_query(cb.id, text="⚠️ Bergabunglah dengan 'Channel' kami dan tekan  '✅ UnMute Me' tombol lagi.", show_alert=True)
      else:
        await client.answer_callback_query(cb.id, text="❗ Anda dibisukan oleh admin karena alasan lain.", show_alert=True)
    else:
      if not (await client.get_chat_member(chat_id, (await client.get_me()).id)).status == 'administrator':
        await client.send_message(chat_id, f"❗ **{cb.from_user.mention} sedang mencoba untuk menyuarakan dirinya sendiri tetapi saya tidak dapat menyuarakannya karena saya bukan admin di obrolan ini, tambahkan saya sebagai admin lagi.**\n__#Leaving this chat...__")
        await client.leave_chat(chat_id)
      else:
        await client.answer_callback_query(cb.id, text="⚠️ Peringatan: Jangan klik tombol jika Anda dapat berbicara dengan bebas.", show_alert=True)



@Client.on_message((filters.text | filters.media) & ~filters.private & ~filters.edited, group=1)
async def _check_member(client, message):
  chat_id = message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    user_id = message.from_user.id
    if not (await client.get_chat_member(chat_id, user_id)).status in ("administrator", "creator") and not user_id in Config.SUDO_USERS:
      channel = chat_db.channel
      if channel.startswith("-"):
          channel_url = await client.export_chat_invite_link(int(channel))
      else:
          channel_url = f"https://t.me/{channel}"
      try:
        await client.get_chat_member(channel, user_id)
      except UserNotParticipant:
        try:
          sent_message = await message.reply_text(
              " {} **kamu belum bergabung dengan saluran kami** @kopi_channel silakan bergabung menggunakan tombol di bawah ini dan tekan tombol suarakan saya untuk membunyikan suara anda sendiri.".format(message.from_user.mention, channel, channel),
              disable_web_page_preview=True,
             reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⚠️ Join Channel", url=channel_url)
                ],
                [
                    InlineKeyboardButton("✅ UnMute Me", callback_data="onUnMuteRequest")
                ]
            ]
        )
          )
          await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        except ChatAdminRequired:
          await sent_message.edit("❗ **Saya bukan admin di sini.**\n__Jadikan saya admin dengan izin larangan pengguna dan tambahkan saya lagi.\n#Leaving this chat...__")
          await client.leave_chat(chat_id)
      except ChatAdminRequired:
        await client.send_message(chat_id, text=f"❗ **Saya bukan admin di [channel]({channel_url})**\n__Jadikan saya admin di saluran dan tambahkan saya lagi.\n#Leaving this chat...__")
        await client.leave_chat(chat_id)


@Client.on_message(filters.command(["forcesubscribe", "fsub"]) & ~filters.private)
async def config(client, message):
  user = await client.get_chat_member(message.chat.id, message.from_user.id)
  if user.status == "creator" or user.user.id in Config.SUDO_USERS:
    chat_id = message.chat.id
    if len(message.command) > 1:
      input_str = message.command[1]
      input_str = input_str.replace("@", "")
      if input_str.lower() in ("off", "no", "disable"):
        sql.disapprove(chat_id)
        await message.reply_text("❌ **Berlangganan Paksa berhasil dinonaktifkan.**")
      elif input_str.lower() in ('clear'):
        sent_message = await message.reply_text('**Mengaktifkan semua anggota yang dibisukan oleh saya...**')
        try:
          for chat_member in (await client.get_chat_members(message.chat.id, filter="restricted")):
            if chat_member.restricted_by.id == (await client.get_me()).id:
                await client.unban_chat_member(chat_id, chat_member.user.id)
                time.sleep(1)
          await sent_message.edit('✅ **Membunyikan semua anggota yang dibisukan oleh saya.**')
        except ChatAdminRequired:
          await sent_message.edit('❗ **Saya bukan admin dalam obrolan ini.**\n__Saya tidak dapat membunyikan anggota karena saya bukan admin dalam obrolan ini, jadikan saya admin dengan izin larangan pengguna.__')
      else:
        try:
          await client.get_chat_member(input_str, "me")
          sql.add_channel(chat_id, input_str)
          if input_str.startswith("-"):
              channel_url = await client.export_chat_invite_link(int(input_str))
          else:
              channel_url = f"https://t.me/{input_str}"
          await message.reply_text(f"✅ **Berlangganan Paksa Diaktifkan**\n__Force Subscribe is enabled, all the group members have to subscribe this [channel]({channel_url}) in order to send messages in this group.__", disable_web_page_preview=True)
        except UserNotParticipant:
          await message.reply_text(f"❗ **Bukan Admin di Channel**\n__Saya bukan admin di [channel]({channel_url}). tambahkan saya sebagai admin untuk mengaktifkan ForceSubscribe.__", disable_web_page_preview=True)
        except (UsernameNotOccupied, PeerIdInvalid):
          await message.reply_text(f"❗ **Tidak sah Channel Username/ID.**")
        except Exception as err:
          await message.reply_text(f"❗ **ERROR:** ```{err}```")
    else:
      if sql.fs_settings(chat_id):
        my_channel = sql.fs_settings(chat_id).channel
        if my_channel.startswith("-"):
            channel_url = await client.export_chat_invite_link(int(input_str))
        else:
            channel_url = f"https://t.me/{my_channel}"
        await message.reply_text(f"✅ **Force Subscribe diaktifkan dalam obrolan ini.**\n__For this [Channel]({channel_url})__", disable_web_page_preview=True)
      else:
        await message.reply_text("❌ **Paksa Berlangganan dinonaktifkan dalam obrolan ini.**")
  else:
      await message.reply_text("❗ **Diperlukan Pembuat Grup**\n__Anda harus menjadi pembuat grup untuk melakukan itu.__")
