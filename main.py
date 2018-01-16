# -*- coding:utf-8 -*-


"""

    Xi Gua video Million Heroes

"""

import multiprocessing
import operator
import os
import time
from argparse import ArgumentParser
from datetime import datetime
from functools import partial
from multiprocessing import Event
from multiprocessing import Pipe

from terminaltables import AsciiTable

from config import api_key
from config import api_version
from config import app_id
from config import app_key
from config import app_secret
from config import crop_areas
from config import data_directory
from config import enable_chrome
from config import image_compress_level
from config import prefer
from config import use_monitor
# from core.android import analyze_current_screen_text, get_adb_tool, check_screenshot
# from core.android import save_screen
from core.mac import analyze_current_screen_text
from core.check_words import parse_false
from core.chrome_search import run_browser
from core.crawler.baiduzhidao import baidu_count
from core.crawler.crawl import jieba_initialize, kwquery, crawler_daemon
from core.ocr.baiduocr import get_text_from_image as bai_get_text
from core.ocr.spaceocr import get_text_from_image as ocrspace_get_text

## jieba init
jieba_initialize()

if prefer[0] == "baidu":
    get_text_from_image = partial(bai_get_text,
                                  app_id=app_id,
                                  app_key=app_key,
                                  app_secret=app_secret,
                                  api_version=api_version,
                                  timeout=5)

elif prefer[0] == "ocrspace":
    get_test_from_image = partial(ocrspace_get_text, api_key=api_key)


def parse_args():
    parser = ArgumentParser(description="Million Hero Assistant")
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=5,
        help="default http request timeout"
    )
    return parser.parse_args()


def parse_question_and_answer(text_list):
    question = ""
    start = 0
    for i, keyword in enumerate(text_list):
        question += keyword
        if "?" in keyword:
            start = i + 1
            break
    real_question = question.split(".")[-1]

    for char, repl in [("以下", ""), ("下列", "")]:
        # if real_question.startswith(char):
        real_question = real_question.replace(char, repl, 1)

    question, true_flag = parse_false(real_question)
    return true_flag, real_question, question, text_list[start:]


def pre_process_question(keyword):
    """
    strip charactor and strip ?
    :param question:
    :return:
    """
    now = datetime.today()
    for char, repl in [("“", ""), ("”", ""), ("？", ""), ("《", ""), ("》", ""), ("我国", "中国"),
                       ("今天", now.strftime("%Y年%m月%d日")), ("今年", now.strftime("%Y年")),
                       ("这个月", now.strftime("%Y年%m月"))]:
        keyword = keyword.replace(char, repl)

    keyword = keyword.split(r"．")[-1]
    keywords = keyword.split(" ")
    keyword = "".join([e.strip("\r\n") for e in keywords if e])
    return keyword


def main():
    args = parse_args()
    timeout = args.timeout

    # start crawler
    crawler_noticer = Event()
    crawler_noticer.clear()
    result_noticer = Event()
    result_noticer.clear()
    qreader, qwriter = Pipe()
    stdreader, stdwriter = Pipe()
    crawler = multiprocessing.Process(
        target=crawler_daemon,
        args=(crawler_noticer, qreader, result_noticer, stdwriter)
    )
    crawler.daemon = True
    crawler.start()

    # adb_bin = get_adb_tool()
    # if use_monitor:
    #     os.system("{0} connect 127.0.0.1:62001".format(adb_bin))

    # check_screenshot(filename="screenshot.png", directory=data_directory)

    if enable_chrome:
        closer = Event()
        noticer = Event()
        closer.clear()
        noticer.clear()
        reader, writer = Pipe()
        browser_daemon = multiprocessing.Process(
            target=run_browser, args=(closer, noticer, reader,))
        browser_daemon.daemon = True
        browser_daemon.start()

    def __inner_job():
        start = time.time()
        text_binary = analyze_current_screen_text(
            directory=data_directory,
        )
        keywords = get_text_from_image(
            image_data=text_binary,
        )
        if not keywords:
            print("text not recognize")
            return

        true_flag, real_question, question, answers = parse_question_and_answer(
            keywords)

        # notice crawler to work
        qwriter.send(real_question.strip("?"))
        crawler_noticer.set()

        print('-' * 72)
        print(real_question)
        print('-' * 72)
        print("\n".join(answers))

        # notice browser
        if enable_chrome:
            writer.send(question)
            noticer.set()

        search_question = pre_process_question(question)
        summary = baidu_count(search_question, answers, timeout=timeout)
        summary_li = sorted(
            summary.items(), key=operator.itemgetter(1), reverse=True)
        data = [("选项", "同比")]
        for a, w in summary_li:
            data.append((a, w))
        table = AsciiTable(data)
        print(table.table)

        print("*" * 72)
        if true_flag:
            print("肯定回答(**)： ", summary_li[0][0])
            print("否定回答(  )： ", summary_li[-1][0])
        else:
            print("肯定回答(  )： ", summary_li[0][0])
            print("否定回答(**)： ", summary_li[-1][0])
        print("*" * 72)

        # try crawler
        retry = 4
        while retry:
            if result_noticer.is_set():
                print("~" * 60)
                print(stdreader.recv())
                print("~" * 60)
                break
            retry -= 1
            time.sleep(1)
        result_noticer.clear()

        print("~" * 60)
        print(kwquery(real_question.strip("?")))
        print("~" * 60)

        end = time.time()
        print("use {0} 秒".format(end - start))
        # save_screen(
        #     directory=data_directory
        # )

    print("""
    请选择答题节目:
      1. 百万英雄
      2. 冲顶大会
    """)
    game_type = input("输入节目序号: ")
    if game_type == "1":
        game_type = '百万英雄'
    elif game_type == "2":
        game_type = '冲顶大会'
    else:
        game_type = '百万英雄'

    while True:
        print("""
    请在答题开始前就运行程序，
    答题开始的时候按Enter预测答案
                """)

        print("当前选择答题游戏: {}\n".format(game_type))

        enter = input("按Enter键开始，按ESC键退出...")
        if enter == chr(27):
            break
        try:
            __inner_job()
        except Exception as e:
            print(str(e))

        print("欢迎下次使用")

    if enable_chrome:
        reader.close()
        writer.close()
        closer.set()
        time.sleep(3)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
