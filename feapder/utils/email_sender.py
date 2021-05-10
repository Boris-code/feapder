# -*- coding: utf-8 -*-
"""
Created on 2020/2/19 12:57 PM
---------
@summary:
---------
@author: Boris
@email: boris@bzkj.tech
"""

import os
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from feapder.utils.log import log


class EmailSender(object):
    SENDER = "feapder报警系统"

    def __init__(self, username, password, smtpserver="smtp.163.com"):
        self.username = username
        self.password = password
        self.smtpserver = smtpserver
        self.smtp_client = smtplib.SMTP_SSL(smtpserver)
        self.sender = EmailSender.SENDER

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def quit(self):
        self.smtp_client.quit()

    def login(self):
        self.smtp_client.connect(self.smtpserver)
        self.smtp_client.login(self.username, self.password)

    def send(
        self,
        receivers: list,
        title: str,
        content: str,
        content_type: str = "plain",
        filepath: str = None,
    ):
        """

        Args:
            receivers:
            title:
            content:
            content_type: html / plain
            filepath:

        Returns:

        """
        # 创建一个带附件的实例
        message = MIMEMultipart()
        message["From"] = formataddr(
            (self.sender, self.username)
        )  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        message["To"] = formataddr((receivers[0], receivers[0]))  # ",".join(receivers)

        message["Subject"] = Header(title, "utf-8")

        content = MIMEText(content, content_type, "utf-8")
        message.attach(content)

        # 构造附件
        if filepath:
            attach = MIMEText(open(filepath, "rb").read(), "base64", "utf-8")
            attach.add_header(
                "content-disposition",
                "attachment",
                filename=("utf-8", "", os.path.basename(filepath)),
            )
            message.attach(attach)

        msg = message.as_string()
        # 此处直接发送多个邮箱有问题，改成一个个发送
        for receiver in receivers:
            log.debug("发送邮件到 {}".format(receiver))
            self.smtp_client.sendmail(self.username, receiver, msg)
        log.debug("邮件发送成功！！！")
        return True
