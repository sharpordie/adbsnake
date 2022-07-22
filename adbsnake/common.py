from abc import ABC
from asyncio import sleep
from dataclasses import dataclass
from os import remove
from os.path import abspath, basename, dirname, exists, getsize, join
from re import findall
from types import TracebackType
from typing import Optional, Type

import cv2
from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import DeviceAuthError, InvalidResponseError, TcpTimeoutException
from lxml.etree import Element, fromstring


@dataclass
class PackageInfo:
    current: bool
    present: bool
    elderly: int
    version: str


class Common(ABC):

    def __init__(self, address: str, storage: Optional[str] = None):
        self.manager = AdbDeviceTcpAsync(address)
        self.storage = storage or dirname(abspath(__file__))

    async def __aenter__(self):
        return self

    async def __aexit__(self, group: Optional[Type[BaseException]], value: Optional[BaseException], trace: Optional[TracebackType]):
        await self.detach()

    async def accord(self, package: str, consent: str):
        await self.invoke(f"pm grant {package} android.permission.{consent.upper()}")

    async def attach(self) -> bool:
        try:
            await self.manager.connect(rsa_keys=[await self.keygen()], auth_timeout_s=0.1)
            return True
        except (DeviceAuthError, InvalidResponseError) as e:
            raise e
        except TcpTimeoutException:
            return False

    async def create(self, distant: str):
        await self.invoke(f"mkdir -p \'{dirname(distant)}\' ; touch \'{distant}\'")

    async def detach(self):
        await self.manager.close()

    async def detect(self, picture: str) -> Optional[tuple[int, int]]:
        await self.remove("/sdcard/capture.png")
        await self.invoke("screencap -p /sdcard/capture.png")
        fetched = await self.obtain("/sdcard/capture.png")
        if fetched is not None:
            # img = cv2.imread(fetched)
            # factors = np.unique(img.view(np.dtype((np.void, img.dtype.itemsize * img.shape[2])))).view(img.dtype).reshape(-1, img.shape[2])
            # formula = cv2.TM_SQDIFF if len(factors) <= 1000 else cv2.TM_CCOEFF_NORMED
            formula = cv2.TM_CCOEFF_NORMED
            capture = cv2.cvtColor(cv2.imread(fetched), cv2.COLOR_RGB2GRAY)
            element = cv2.cvtColor(cv2.imread(picture), cv2.COLOR_RGB2GRAY)
            remove(fetched)
            results = cv2.matchTemplate(capture, element, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(results)
            # max_val = 1 - (min_val / 10_000_000) if formula == cv2.TM_SQDIFF else max_val
            if max_val >= 0.8:
                h, w = element.shape
                results = max_loc[0] + (w / 2), max_loc[1] + (h / 2)
                return int(results[0]), int(results[1])
        return None

    async def enable(self, package: str, enabled: bool):
        await self.invoke(f"pm {'enable' if enabled else 'disable-user --user 0'} '{package}'")

    async def escape(self):
        for _ in range(0, 2):
            await self.repeat("keycode_back", repeats=8)
        await self.repeat("keycode_wakeup")
        await self.invoke("sleep 2")

    async def finish(self, package: str):
        if (await self.gather(package)).present:
            await self.invoke(f"sleep 2 ; am force-stop '{package}' ; sleep 2")

    async def gather(self, package: str) -> PackageInfo:
        return PackageInfo(
            bool((await self.invoke(f"pidof '{package}'")).strip()),
            bool((await self.invoke(f"pm path '{package}'")).strip()),
            1000,
            "1.0.0"
        )

    async def insert(self, content: str, cleared: bool = False):
        if cleared:
            await self.repeat("keycode_move_end")
            await self.repeat("keycode_del", 100)
        await self.invoke(f"input text '{content}'")

    async def invoke(self, command: str) -> str:
        return await self.manager.shell(command, read_timeout_s=30.0)

    async def keygen(self, refresh: bool = False) -> PythonRSASigner:
        pvt_key = join(self.storage, "adbkey")
        pub_key = pvt_key + ".pub"
        if refresh or not exists(pub_key) or not exists(pvt_key):
            if exists(pub_key):
                remove(pub_key)
            if exists(pvt_key):
                remove(pvt_key)
            keygen(pvt_key)
        with open(pub_key) as f:
            pub_bin = f.read()
        with open(pvt_key) as f:
            pvt_bin = f.read()
        return PythonRSASigner(pub_bin, pvt_bin)

    async def launch(self, package: str):
        await self.invoke(f"sleep 2 ; monkey -p '{package}' 1 ; sleep 2")

    async def locate(self, pattern: str) -> Optional[tuple[int, int]]:
        if (element := await self.scrape(pattern)) is not None:
            content = element.get("bounds")
            results = [int(s) for s in (findall("\\d+", content))]
            return int((results[0] + results[2]) / 2), int((results[1] + results[3]) / 2)
        return None

    async def obtain(self, distant: str) -> Optional[str]:
        storage = join(self.storage, basename(distant))
        await self.manager.pull(distant, storage)
        return storage if exists(storage) else None

    async def reboot(self):
        await self.manager.reboot()
        await sleep(4)
        while not await self.attach():
            await sleep(2)
        await sleep(8)

    async def remove(self, distant: str):
        await self.invoke(f"rm -rf {distant}")

    async def render(self) -> str:
        await self.remove(fetched := "/sdcard/window_dump.xml")
        while "dumped" not in await self.invoke("uiautomator dump"):
            package = "com.android.vending"
            await self.enable(package, enabled=True)
            await self.launch(package)
            await self.finish(package)
        return (await self.invoke(f"cat {fetched}")).strip()

    async def repeat(self, keycode: str, repeats: int = 1):
        await self.invoke(f"input keyevent $(printf '{keycode.upper()} %.0s' $(seq 1 {repeats}))")

    async def scrape(self, pattern: str) -> Optional[Element]:
        await self.repeat("keycode_dpad_up", 100)
        content = await self.render()
        while len(element := fromstring(bytes(await self.render(), encoding="utf-8")).xpath(pattern)) < 1:
            await self.repeat("keycode_dpad_down", 8)
            if content == (content := await self.render()):
                break
        return next(iter(element), None)

    async def search(self, pattern: str, maximum: int = 1) -> Optional[list[str]]:
        spawned = await self.invoke(f"find {pattern} -maxdepth 0 2>/dev/null | head -{maximum}")
        results = spawned.strip() or None
        return results.split("\n") if results is not None else None

    async def select(self, payload: str) -> bool:
        results = await self.detect(payload) if exists(payload) else await self.locate(payload)
        if results is not None:
            await self.invoke(f"input tap {results[0]} {results[1]}")
            return True
        return False

    async def unpack(self, archive: str, deposit: str):
        if exists(archive):
            await self.invoke(f"mkdir -p \'{deposit}\'")
            await self.upload(archive, f"{deposit}/{basename(archive)}")
            await self.invoke(f"cd '{deposit}' ; unzip -o '{basename(archive)}'")
            await self.remove(f"{deposit}/{basename(archive)}")

    async def update(self, package: str):
        if exists(package):
            distant = join("/sdcard", basename(package))
            await self.upload(package, distant)
            await self.invoke(f"cat {distant} | pm install -S {getsize(package)}")
            await self.remove(distant)

    async def upload(self, storage: str, distant: str):
        await self.manager.push(storage, distant)

    async def vanish(self, package):
        await self.finish(package)
        await self.invoke(f"pm uninstall '{package}'")
