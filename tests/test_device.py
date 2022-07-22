from asyncio import get_event_loop
from os import remove
from os.path import abspath, basename, dirname, exists, join
from urllib.request import urlopen

from lxml.etree import fromstring
from pytest import mark
from pytest_asyncio import fixture

from adbsnake import Device


@fixture(scope="session")
def event_loop():
    return get_event_loop()


@mark.asyncio
@fixture(scope="session")
async def machine() -> Device:
    async with Device("192.168.1.62") as machine:
        await machine.attach()
        yield machine


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_accord(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_attach(machine: Device):
    ...


@mark.asyncio
@mark.parametrize("distant", ["/sdcard/a.txt", "/sdcard/a/a.txt"])
async def test_create(machine: Device, distant: str):
    await machine.create(distant)
    assert (await machine.search(f"'{distant}'"))[0] == distant
    await machine.remove(distant)


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_detach(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_detect(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_enable(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not fully implemented")
async def test_escape(machine: Device):
    await machine.escape()


@mark.asyncio
@mark.parametrize("package", ["com.android.vending"])
@mark.skip(reason="not fully implemented")
async def test_finish(machine: Device, package: str):
    await machine.enable(package, enabled=True)
    await machine.launch(package)
    assert (await machine.gather(package)).current is True
    await machine.finish(package)
    assert (await machine.gather(package)).current is False


@mark.asyncio
@mark.skip(reason="not fully implemented")
async def test_insert(machine: Device):
    await machine.insert("anonymous@example.org")


@mark.asyncio
async def test_invoke(machine: Device):
    assert (await machine.invoke("echo dummy")).strip() == "dummy"


@mark.asyncio
async def test_keygen(machine: Device):
    pvt_key = join(dirname(abspath(__file__)), "adbkey")
    pub_key = pvt_key + ".pub"
    await machine.keygen(dirname(pvt_key))
    assert exists(pvt_key)
    assert exists(pub_key)
    remove(pvt_key)
    remove(pub_key)


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_launch(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_locate(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_obtain(machine: Device):
    ...


@mark.asyncio
async def test_reboot(machine: Device):
    await machine.reboot()
    assert (await machine.invoke("echo dummy")).strip() == "dummy"


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_remove(machine: Device):
    ...


@mark.asyncio
async def test_render(machine: Device):
    fromstring(bytes(await machine.render(), encoding="utf-8"))


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_repeat(machine: Device):
    ...


@mark.asyncio
@mark.parametrize("pattern", ["//*[@text='Français (France)']", "//*[@text='English (United States)']"])
async def test_scrape(machine: Device, pattern: str):
    await machine.invoke("am start -a android.settings.LOCALE_SETTINGS")
    assert await machine.scrape(pattern) is not None
    await machine.repeat("keycode_home")


@mark.asyncio
@mark.parametrize("pattern", ["//*[@text='English']"])
async def test_scrape_with_invalid_pattern(machine: Device, pattern: str):
    await machine.invoke("am start -a android.settings.LOCALE_SETTINGS")
    assert await machine.scrape(pattern) is None
    await machine.repeat("keycode_home")


@mark.asyncio
@mark.parametrize("pattern", ["/sdcard/*", "/*dcard/*"])
async def test_search(machine: Device, pattern: str):
    assert await machine.search(pattern) is not None
    assert len(await machine.search(pattern, maximum=2)) == 2
    assert len(await machine.search(pattern, maximum=5)) == 5


@mark.asyncio
@mark.parametrize("pattern", [".*.", "_*_"])
async def test_search_with_invalid_pattern(machine: Device, pattern: str):
    assert await machine.search(pattern) is None


@mark.asyncio
@mark.parametrize("pattern", ["//*[@text='Français (France)']", "//*[@text='English (United States)']"])
async def test_select(machine: Device, pattern: str):
    await machine.invoke("am start -a android.settings.LOCALE_SETTINGS")
    assert await machine.select(pattern) is True
    await machine.repeat("keycode_home")


@mark.asyncio
@mark.parametrize("address,deposit", [("https://github.com/gorhill/uBlock/archive/refs/heads/master.zip", "/sdcard/deposit")])
async def test_unpack(machine: Device, address: str, deposit: str):
    with open(archive := join(dirname(abspath(__file__)), basename(address)), "wb") as f:
        f.write(urlopen(address).read())
    await machine.unpack(archive, deposit)
    assert await machine.search(f'"{deposit}/{basename(archive)}"') is None
    assert await machine.search(f'"{deposit}/uBlock-master"') is not None
    await machine.remove(deposit)


@mark.asyncio
@mark.skip(reason="not fully implemented")
async def test_update(machine: Device):
    package = "net.kodinerds.maven.kodi"
    archive = "/Users/admin/Projects/hisendal/hisendal/services/net.kodinerds.maven.kodi.arm64-v8a-202206090029-c471b3ef-Matrix.apk"
    await machine.update(archive)
    assert (await machine.gather(package)).present is True
    assert await machine.search(join("/sdcard", basename(archive))) is None


@mark.asyncio
@mark.skip(reason="not implemented")
async def test_upload(machine: Device):
    ...


@mark.asyncio
@mark.skip(reason="not fully implemented")
async def test_vanish(machine: Device):
    package = "net.kodinerds.maven.kodi"
    await machine.vanish(package)
    assert (await machine.gather(package)).present is False
