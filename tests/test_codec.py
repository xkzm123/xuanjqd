from __future__ import annotations

import hashlib

from xuanjqd.codec import extract_id, id_code, signin_url, verify_url


def test_id_code_matches_md5():
    assert id_code(136991) == "47e371f28cccfe63295a174b07170c87"
    assert id_code(136991) == hashlib.md5(b"136991").hexdigest()


def test_signin_url_format():
    url = signin_url(136995)
    assert url.startswith("http://job.hdu.edu.cn/teachin/qrcode?id=136995")
    assert "id_code=47e371f28cccfe63295a174b07170c87" not in url  # 不同 id 不同 md5
    assert url.endswith("&signin=1")


def test_custom_template():
    url = signin_url(42, base="https://example.com/s", template="{base}/{id}/{code}")
    assert url.startswith("https://example.com/s/42/")


def test_extract_id_variants():
    assert extract_id(136995) == 136995
    assert extract_id("136995") == 136995
    assert extract_id("https://job.hdu.edu.cn/teachin/view?id=136995") == 136995
    assert extract_id("http://job.hdu.edu.cn/teachin/qrcode?id=136995&id_code=x&signin=1") == 136995
    assert extract_id("https://job.hdu.edu.cn/teachin/view/136995") == 136995
    assert extract_id("乱码") is None


def test_verify_url_roundtrip():
    url = signin_url(136995)
    assert verify_url(url)
    assert verify_url(url, 136995)
    assert not verify_url(url, 1)
    assert not verify_url("http://x/y?id=1")
