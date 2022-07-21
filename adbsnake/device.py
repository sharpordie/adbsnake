from adbsnake.common import Common


class Device(Common):

    async def access_locale(self):
        await self.invoke("am start -a android.settings.LOCALE_SETTINGS")
