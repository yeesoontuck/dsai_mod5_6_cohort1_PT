import os
import requests

TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TELEGRAM_SEALION_API_KEY = os.getenv('TELEGRAM_SEALION_API_KEY')

def telegram_getwebhookino(bot_name):

    if bot_name == 'gemini_bot':
        BOT_KEY = TELEGRAM_API_KEY
    elif bot_name == 'sealion_bot':
        BOT_KEY = TELEGRAM_SEALION_API_KEY

    try:
        # read current webhook settings for Gemini bot
        response = requests.get(f'https://api.telegram.org/bot{BOT_KEY}/getWebhookInfo')

        if response.status_code != 200:
            raise Exception('Error while getting webhook info')
        
        # {
        #     "ok": true,
        #     "result": {
        #         "url": "https://dsai.spruecutters.com/experimental/telegram_sealion/webhook",
        #         "has_custom_certificate": false,
        #         "pending_update_count": 0,
        #         "last_error_date": 1748259759,
        #         "last_error_message": "Wrong response from the webhook: 502 Bad Gateway",
        #         "max_connections": 40,
        #         "ip_address": "188.114.97.0"
        #     }
        # }
        webhook_info = response.json()['result']
        return webhook_info
    except Exception as e:
        print('Error while getting webhook info', e)



def telegram_setwebhook(bot_name, url):
    if bot_name == 'gemini_bot':
        BOT_KEY = TELEGRAM_API_KEY
    elif bot_name == 'sealion_bot':
        BOT_KEY = TELEGRAM_SEALION_API_KEY

    try:
        # update webhook url

        payload = {
            "url": url,
            "drop_pending_updates": "True"
        }
        
        response = requests.post(f'https://api.telegram.org/bot{BOT_KEY}/setWebhook', data=payload)

        if response.status_code != 200:
            raise Exception('Error while setting webhook info')
    except Exception as e:
        print('Error while setting webhook info', e)