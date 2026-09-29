# -*- coding: utf-8 -*-
"""用本机 Chrome 无头渲染页面并 dump 渲染后的 DOM（Git Bash 重定向有坑，用 Python 捕获 stdout 字节）"""
import subprocess, sys, os

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome-tmp")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def dump(url, out, budget=20000):
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions",
           "--user-agent=" + UA, "--window-size=1440,3000",
           "--virtual-time-budget=%d" % budget,
           "--user-data-dir=" + PROF, "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True)
    data = r.stdout or b""
    with open(out, "wb") as f:
        f.write(data)
    print("URL", url, "BYTES", len(data), "STDERR", r.stderr.decode("utf-8", "ignore")[:200])
    return len(data)


if __name__ == "__main__":
    dump(sys.argv[1], sys.argv[2])
