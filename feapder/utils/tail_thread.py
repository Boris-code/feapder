# -*- coding: utf-8 -*-
"""
Created on 2024/3/19 20:00
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import sys
import threading


class TailThread(threading.Thread):
    """
    所有子线程结束后，主线程才会退出
    """

    def start(self) -> None:
        """
        解决python3.12 RuntimeError: cannot join thread before it is started的报错
        """
        super().start()

        if sys.version_info.minor >= 12 and sys.version_info.major >= 3:
            for thread in threading.enumerate():
                if (
                    thread.daemon
                    or thread is threading.current_thread()
                    or not thread.is_alive()
                ):
                    continue
                thread.join()
